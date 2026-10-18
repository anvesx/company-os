"""The console's JSON endpoints as plain Python: one Console object holds the Company OS, and route() maps URLs to it."""
import json
import os
import re
import threading
from collections import Counter, defaultdict

from company_memory import AreaDenied
from connectors.event_lookup import event_area
from lifecycle_kit.approved_actions import execute_approved
from triggers.calendar_trigger import CalendarTrigger
from triggers.dispatch import dispatch
from triggers.request_trigger import parse_request
from triggers.timer_trigger import TimerTrigger
from wiring.agent_registry import AGENTS as AGENT_PACKAGES, available_agents as registry_available
from wiring.build_company_os import ALL_AGENTS, build_company_os

from .agent_cards import CARDS, PLANNED, ROLE_LABELS
from .department_scenarios import DEPARTMENTS, demo_for, find_scenario
from .permissions import offered_scenarios, permissions_for, run_error, scenario_offered
from .real_samples import SAMPLES_FILE, load_real_samples
from .run_walkthrough import TOOL_PLAIN, build_walkthrough, human, plain_reason

STATE_FILE = "console_state.json"
STATE_DB_FILES = ("company_memory.db", "people_surface.db", STATE_FILE)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ASK_EXAMPLES = ["prep me for EV113", "prepare for EV114"]
QUESTION_LIMIT = 500
ASK_HELP = "I can understand requests like these today: " + "; ".join(f"'{e}'" for e in ASK_EXAMPLES) + "."


def available_agents():
    """Agents whose pack can be imported now. Others (still being built) are listed with the reason."""
    return registry_available()


class Console:
    def __init__(self, state_dir, reset=False, samples_path=SAMPLES_FILE):
        self.state_dir = str(state_dir)
        self.samples_path = samples_path
        self.lock = threading.RLock()
        self.cos = None
        self._build(reset)

    # ---- build, reset, saved state
    def _state_path(self):
        return os.path.join(self.state_dir, STATE_FILE)

    def _saved(self):
        try:
            with open(self._state_path()) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _save(self):
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self._state_path(), "w") as f:
            json.dump({"now": self.cos.clock.now, "paused": self.cos.way_in.paused,
                       "calendar_seen": sorted(self.calendar._seen)}, f)

    def _close(self):
        if self.cos is None:
            return
        for conn in (self.cos.memory.conn, self.cos.outbox.conn, self.cos.approvals.conn, self.cos.data_conn):
            try:
                conn.close()
            except Exception:
                pass

    def _build(self, reset):
        self._close()
        if reset:
            for name in STATE_DB_FILES:
                try:
                    os.remove(os.path.join(self.state_dir, name))
                except FileNotFoundError:
                    pass
        saved = {} if reset else self._saved()
        self.agents, self.unavailable = available_agents()
        kwargs = {"now": saved["now"]} if saved.get("now") else {}
        self.cos = build_company_os(self.agents, state_dir=self.state_dir, **kwargs)
        if saved.get("paused"):
            self.cos.way_in.pause()
        self.timer = TimerTrigger(self._schedule())
        self.calendar = CalendarTrigger(self.cos.data_conn)
        self.calendar._seen = set(saved.get("calendar_seen", []))
        self._save()

    def _schedule(self):
        rows = []
        if "finance_watch" in self.agents:
            rows.append({"agent": "finance_watch", "area_id": "devx-internal", "every": "daily"})
        return rows

    def reset(self):
        with self.lock:
            self._build(True)
            return {"ok": True, "now": self.cos.clock.now}

    def close(self):
        self._close()

    # ---- people and names
    def _name(self, person_id):
        p = self.cos.directory.get(person_id) if person_id else None
        return p["name"] if p else (person_id or "someone")

    def _role(self, person_id):
        return self.cos.directory.role(person_id)

    def people(self):
        rows = self.cos.data_conn.execute(
            "SELECT person_id, name, role, team FROM people WHERE is_devx = 1 ORDER BY person_id").fetchall()
        return [{"person_id": r["person_id"], "name": r["name"], "role": r["role"], "team": r["team"],
                 "role_label": ROLE_LABELS.get(r["role"], human(r["role"]))} for r in rows]

    def state(self):
        c = self.cos
        return {"now": c.clock.now, "today": c.clock.today, "paused": c.way_in.paused,
                "agents": list(self.agents), "unavailable": self.unavailable,
                "areas": [{"area_id": a["area_id"], "name": a["name"], "kind": a["kind"]} for a in c.memory.areas()
                          if a["kind"] != "hold"]}

    # ---- agent cards and scenarios
    def agent_cards(self):
        out = []
        for name in ALL_AGENTS:
            card = dict(CARDS.get(name) or self._fallback_card(name), agent=name, available=name in self.agents,
                        demo=demo_for(name))
            pack = self.cos.packs.get(name)
            if pack:
                card["who_may_start"] = sorted(ROLE_LABELS.get(r, r) for r in pack.starter_roles)
                card["who_may_approve"] = sorted(ROLE_LABELS.get(r, r) for r in pack.approver_roles)
                card["tools"] = [{"name": s.name, "plain": TOOL_PLAIN.get(s.name, human(s.name)), "needs_approval": s.risky}
                                 for s in pack.tools()]
            else:
                card["status_note"] = "Being built. This agent is not installed yet."
            out.append(card)
        return {"agents": out, "planned": PLANNED}

    @staticmethod
    def _fallback_card(name):
        """A plain card for an agent that has no entry in CARDS yet: the first paragraph of its README."""
        summary = ""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, *AGENT_PACKAGES.get(name, f"agents.{name}").split("."), "README.md")
        try:
            with open(path) as f:
                paras = [p.strip() for p in f.read().split("\n\n") if p.strip() and not p.lstrip().startswith("#")]
            summary = paras[0].replace("\n", " ") if paras else ""
        except OSError:
            pass
        return {"title": human(name).capitalize(), "department": "", "summary": summary,
                "watches": [], "acts": "", "tells": "", "never": []}

    def _title(self, agent):
        return (CARDS.get(agent) or {}).get("title") or human(agent).capitalize()

    def scenarios(self, person_id=None):
        """All departments, or with a person only the scenarios that person may run (tabs without any are left out)."""
        depts = []
        for d in DEPARTMENTS:
            scenarios = []
            for s in d["scenarios"]:
                if person_id and not scenario_offered(self, person_id, s):
                    continue
                status = ("link" if s.get("link") else "ready" if s["agent"] in self.agents else "being_built")
                caller = s["caller_id"] if (not person_id or s.get("as_named")) else person_id
                scenarios.append({**s, "status": status, "agent_title": self._title(s["agent"]) if s.get("agent") else "",
                                  "caller_name": self._name(caller) if caller else ""})
            if scenarios or not person_id:
                depts.append({**d, "scenarios": scenarios})
        return {"departments": depts}

    def permissions(self, person_id):
        return permissions_for(self, person_id)

    # ---- running agents
    def _run_payload(self, result):
        run_id = result.run_id
        run = self.cos.memory.get_run(run_id)
        walk = self._walkthrough(run)
        approvals = [self._approval_view(a, None) for a in self._approvals_of_run(run_id)]
        return {"ok": True, "run": self._run_row(run), "status": walk["outcome"], "reason": plain_reason(result.reason),
                "walkthrough": walk, "messages": self._letters_of(run_id), "approvals": approvals}

    def _letters_of(self, run_id):
        """Every letter a run wrote, oldest first, with the receiver's name and the agent's title."""
        return [{**m, "to_name": self._name(m["to_person_id"]), "agent_title": self._title(m["agent"])}
                for m in self.cos.outbox.messages() if m["run_id"] == run_id]

    def _clean_inputs(self, inputs):
        out = {}
        for key in ("as_of", "event_id", "question", "from", "to"):
            value = str((inputs or {}).get(key) or "").strip()
            if not value:
                continue
            if key in ("as_of", "from", "to") and not DATE.match(value):
                raise ValueError("Dates look like 2026-10-19 (year-month-day).")
            out[key] = value.upper() if key == "event_id" else value[:QUESTION_LIMIT] if key == "question" else value
        return out

    def run_agent(self, agent, caller_id, area_id, inputs=None):
        with self.lock:
            if agent not in self.agents:
                why = "being built" if agent in ALL_AGENTS else "not known"
                return {"ok": False, "error": f"The {human(agent)} agent is {why}, so it cannot run yet."}
            try:
                clean = self._clean_inputs(inputs)
            except ValueError as e:
                return {"ok": False, "error": str(e)}
            if agent == "spend_advisor":   # the advisor answers as of the demo date, not the fixed default
                clean.setdefault("as_of", str(self.cos.clock.now)[:10])
            result = self.cos.run(agent, caller_id, area_id, trigger_kind="request", inputs=clean)
            return self._run_payload(result)

    def run_scenario(self, scenario_id, person_id=None):
        """Without a person the scenario runs as its named caller. With one it runs as that person, if it is offered."""
        s = find_scenario(scenario_id)
        if s is None or not s.get("agent"):
            return {"ok": False, "error": "That scenario cannot be run."}
        if person_id is None or s.get("as_named"):
            if person_id is not None and not scenario_offered(self, person_id, s):
                return {"ok": False, "error": f"{self._name(person_id)} is not offered this example. Nothing was run."}
            return self.run_agent(s["agent"], s["caller_id"], s["area_id"], s["inputs"])
        if not scenario_offered(self, person_id, s):
            return {"ok": False, "error": f"{self._name(person_id)} is not offered this scenario. Nothing was run."}
        return self.run_agent(s["agent"], person_id, s["area_id"], s["inputs"])

    def check_start(self, person_id, agent, area_id):
        """For the API: None when this person may start this agent on this area, else the plain error."""
        return run_error(self, person_id, agent, area_id)

    def check_ask(self, text, person_id):
        """For the API: the error when a request in words points at an agent or area this person may not use."""
        task = parse_request((text or "").strip(), person_id, event_area(self.cos.data_conn)) if text else None
        return run_error(self, person_id, "meeting_prep", task.area_id) if task else None

    def ask(self, text, caller_id):
        with self.lock:
            text = (text or "").strip()
            task = parse_request(text, caller_id, event_area(self.cos.data_conn)) if text else None
            if task is None:
                return {"ok": False, "understood": False, "error": "I did not understand that. " + ASK_HELP}
            event_id = task.inputs["event_id"]
            known = self.cos.data_conn.execute("SELECT 1 FROM calendar_events WHERE event_id = ?", (event_id,)).fetchone()
            if not known:
                return {"ok": False, "understood": True, "error": f"I could not find a calendar event called {event_id}."}
            if "meeting_prep" not in self.agents:
                return {"ok": False, "understood": True, "error": "The meeting prep agent is not installed."}
            result = self.cos.runner.run(self.cos.packs["meeting_prep"], task)
            payload = self._run_payload(result)
            payload["understood"] = f"Meeting prep for {event_id} (client area {task.area_id})"
            return payload

    def finance_ask(self, text, person_id):
        """The Ask finance box: run the spend advisor on a question in words. The text is data for the agent."""
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "Type a question first, for example: where is our travel money going?"}
        return self.run_agent("spend_advisor", person_id, "devx-internal", {"question": text})

    # ---- inbox
    def inbox(self, person_id):
        if not self.cos.directory.get(person_id):
            return {"ok": False, "error": "Unknown person."}
        msgs = sorted(self.cos.outbox.messages(person_id), key=lambda m: m["msg_id"], reverse=True)
        return {"ok": True, "person": self._name(person_id), "messages": [
            {**m, "agent_title": self._title(m["agent"])} for m in msgs]}

    # ---- approvals
    def _all_approvals(self):
        rows = self.cos.approvals.conn.execute("SELECT * FROM approvals ORDER BY approval_id").fetchall()
        return [self.cos.approvals._row(r) for r in rows]

    def _approvals_of_run(self, run_id):
        return [a for a in self._all_approvals() if a["run_id"] == run_id]

    def _can_approve(self, person_id, row):
        """Returns (allowed, plain reason). Policy first, then the person must work on that area."""
        role = self._role(person_id)
        if not person_id or role is None:
            return False, "Choose a person first."
        if not self.cos.policy.may_approve(role, row["agent"]):
            who = self.cos.packs[row["agent"]].approver_roles if row["agent"] in self.cos.packs else ()
            names = " or ".join(sorted(ROLE_LABELS.get(r, r) for r in who))
            return False, (f"A {ROLE_LABELS.get(role, role)} may not approve this. Allowed: {names}.")
        run = self.cos.memory.get_run(row["run_id"]) or {}
        if run.get("area_id") not in self.cos.directory.client_access(person_id):
            return False, "This action is about a client this person does not work on."
        return True, ""

    def _approval_view(self, a, person_id):
        ok, why = self._can_approve(person_id, a) if person_id else (None, "")
        run = self.cos.memory.get_run(a["run_id"]) or {}
        executed = None
        for s in self.cos.memory.run_steps(a["run_id"]):
            if s["step"] == "approved_action" and s["detail"].get("approval_id") == a["approval_id"]:
                executed = s["detail"].get("result")
        return {"approval_id": a["approval_id"], "run_id": a["run_id"], "agent": a["agent"],
                "agent_title": self._title(a["agent"]),
                "what": TOOL_PLAIN.get(a["tool"], human(a["tool"])), "title": a["args"].get("title", ""),
                "area_id": run.get("area_id"), "owner": self._name(a["args"].get("owner_id")),
                "why_held": plain_reason(a["reason"]), "status": a["status"], "requested_at": a["requested_at"],
                "decided_by": self._name(a["decided_by"]) if a["decided_by"] else None, "decided_at": a["decided_at"],
                "executed": executed, "can_decide": ok, "cannot_because": why}

    def approvals(self, person_id=None):
        rows = [self._approval_view(a, person_id) for a in self._all_approvals()]
        if person_id:
            rows = [r for r in rows if r["can_decide"]]
        rows.sort(key=lambda r: (r["status"] != "pending", r["approval_id"]))
        return {"ok": True, "approvals": rows, "pending": sum(r["status"] == "pending" for r in rows)}

    def decide(self, approval_id, approve, by_person_id):
        with self.lock:
            row = self.cos.approvals.get(approval_id)
            if row is None:
                return {"ok": False, "error": "I could not find that approval."}
            allowed, why = self._can_approve(by_person_id, row)
            if not allowed:
                return {"ok": False, "refused": True, "error": why}
            try:
                self.cos.approvals.decide(approval_id, bool(approve), by_person_id)
            except ValueError:
                return {"ok": False, "error": f"{approval_id} was already decided. A request can be decided only once."}
            executed = None
            if approve:
                executed = execute_approved(approval_id, self.cos.approvals, self.cos.runtime.registry, self.cos.memory)
            return {"ok": True, "status": "approved" if approve else "rejected", "executed": executed,
                    "approval": self._approval_view(self.cos.approvals.get(approval_id), by_person_id)}

    # ---- runs
    def _quiet_runs(self):
        rows = self.cos.memory.conn.execute("SELECT DISTINCT run_id FROM run_steps WHERE step = 'quiet'")
        return {r[0] for r in rows}

    def _run_row(self, run, quiet=None):
        quiet = self._quiet_runs() if quiet is None else quiet
        status = run["status"] or "running"
        label = "quiet" if run["run_id"] in quiet else status
        return {**run, "status_label": label, "caller_name": self._name(run["caller_id"]),
                "agent_title": self._title(run["agent"]),
                "area_name": next((a["name"] for a in self.cos.memory.areas() if a["area_id"] == run["area_id"]),
                                  run["area_id"])}

    def runs(self, limit=200):
        quiet = self._quiet_runs()
        rows = sorted(self.cos.memory.runs(), key=lambda r: r["run_id"], reverse=True)[:limit]
        return {"runs": [self._run_row(r, quiet) for r in rows]}

    def _walkthrough(self, run):
        mem = self.cos.memory
        cases = [c for c in mem.cases() if c["run_id"] == run["run_id"]]
        return build_walkthrough(run, mem.run_steps(run["run_id"]), cases=cases,
                                 approvals=[self._approval_view(a, None) | {"args": a["args"]}
                                            for a in self._approvals_of_run(run["run_id"])],
                                 name_of=self._name)

    def run_detail(self, run_id):
        run = self.cos.memory.get_run(run_id)
        if run is None:
            return {"ok": False, "error": "I could not find that run."}
        return {"ok": True, "run": self._run_row(run), "walkthrough": self._walkthrough(run),
                "messages": self._letters_of(run_id)}

    # ---- memory
    def _allowed_areas(self, person_id):
        return set(self.cos.directory.client_access(person_id)) - {"hold", "system"} if person_id else set()

    def memory_areas(self, person_id):
        allowed = self._allowed_areas(person_id)
        scoped = self.cos.memory.scoped(allowed)
        areas = []
        for a in self.cos.memory.areas():
            if a["area_id"] in allowed:
                counts = Counter(i["kind"] for i in scoped.items(a["area_id"]))
                areas.append({**a, "counts": dict(counts), "total": sum(counts.values())})
        return {"ok": True, "areas": areas, "hidden": len([a for a in self.cos.memory.areas()
                                                           if a["kind"] == "client" and a["area_id"] not in allowed])}

    LINK_WORDS = {"supersedes": ("replaces", "replaced by"), "answers": ("answers", "answered by"),
                  "refines": ("refines", "refined by"), "follows_up": ("follows up", "followed up by"),
                  "about": ("is about", "has notes")}

    def _link_tags(self, item, area_id):
        """Small tags such as 'answers I0501'. Only links to items in the same area are shown."""
        tags = []
        for link in self.cos.memory.links_of(item["item_id"]):
            outgoing = link["from_id"] == item["item_id"]
            other = link["to_id"] if outgoing else link["from_id"]
            other_item = self.cos.memory.get_item(other)
            if other_item and other_item["area_id"] == area_id and link["rel"] in self.LINK_WORDS:
                tags.append({"word": self.LINK_WORDS[link["rel"]][0 if outgoing else 1], "other": other})
        return tags

    def memory(self, person_id, area_id, kind=None, limit=100):
        allowed = self._allowed_areas(person_id)
        scoped = self.cos.memory.scoped(allowed)
        try:
            items = scoped.items(area_id, kinds=kind or None)
        except AreaDenied:
            return {"ok": False, "refused": True,
                    "error": f"{self._name(person_id)} may not see the area {area_id}. "
                             "People see only the clients they work on, plus DevX internal."}
        if not kind:
            items = [i for i in items if i["kind"] != "transcript"]
        total = len(items)
        items = sorted(items, key=lambda i: (i["created_at"], i["item_id"]), reverse=True)[:int(limit)]
        shown = [{**i, "text": i["text"][:400] + ("..." if len(i["text"]) > 400 else ""), "links": self._link_tags(i, area_id)}
                 for i in items]
        role = self._role(person_id)
        cases = []
        for c in self.cos.memory.cases(area_id=area_id):
            if role == "ceo" or self.cos.policy.may_start(role, c["agent"]):
                evidence = c["evidence"]
                try:
                    evidence = json.loads(evidence)
                except (TypeError, ValueError):
                    pass
                cases.append({**c, "evidence": evidence, "agent_title": self._title(c["agent"])})
        return {"ok": True, "area_id": area_id, "total": total, "items": shown, "cases": cases}

    # ---- cost, cache, guardrails
    def costs(self):
        entries = self.cos.ledger.entries
        by_agent = defaultdict(lambda: {"calls": 0, "cost_usd": 0.0, "hits": 0, "writes": 0})
        for e in entries:
            row = by_agent[e["agent"]]
            row["calls"] += 1
            row["cost_usd"] += e["cost_usd"]
            row["hits" if e["cache"] == "hit" else "writes"] += 1
        calls = len(entries)
        hits = sum(r["hits"] for r in by_agent.values())
        runs = self.cos.memory.runs()
        per_run = sorted((r for r in runs if (r["cost_usd"] or 0) > 0), key=lambda r: r["run_id"], reverse=True)[:20]
        verdicts, decisions = Counter(), []
        for r in self.cos.memory.conn.execute(
                "SELECT run_id, step, detail FROM run_steps WHERE step IN ('tool', 'refused') ORDER BY run_id, seq"):
            d = json.loads(r["detail"])
            if r["step"] == "refused":
                verdicts["refused runs"] += 1
                decisions.append({"run_id": r["run_id"], "verdict": "refused", "what": "Start the run",
                                  "reason": plain_reason(d.get("reason"))})
                continue
            v = {"allow": "allowed", "deny": "denied", "ask": "held"}.get(d.get("verdict"), "allowed")
            verdicts[v] += 1
            if v != "allowed":
                decisions.append({"run_id": r["run_id"], "verdict": v, "what": TOOL_PLAIN.get(d.get("name"), d.get("name")),
                                  "reason": plain_reason(d.get("reason"))})
        status = Counter(self._run_row(r)["status_label"] for r in runs)
        return {"model_calls": calls, "total_cost_usd": sum(e["cost_usd"] for e in entries),
                "cache_hits": hits, "cache_hit_rate": (hits / calls) if calls else 0.0,
                "by_agent": [{"agent": a, "agent_title": self._title(a), **v}
                             for a, v in sorted(by_agent.items())],
                "per_run": [{"run_id": r["run_id"], "agent": r["agent"], "cost_usd": r["cost_usd"],
                             "tokens_in": r["tokens_in"], "tokens_out": r["tokens_out"], "status": r["status"]}
                            for r in per_run],
                "run_count": len(runs), "run_status": dict(status), "guardrail_counts": dict(verdicts),
                "guardrail_decisions": decisions[-30:][::-1]}

    # ---- today: the viewer's home page
    ROLE_DEPTS = {"finance_lead": ["finance"], "growth": ["growth"], "csm": ["growth"], "project_lead": ["growth"],
                  "rnd_lead": ["cto", "growth", "finance"], "ceo": ["finance", "growth"]}

    def _picks(self, person_id):
        role = self._role(person_id)
        depts = self.ROLE_DEPTS.get(role, ["csm"])
        listed = [(d["id"], s) for d in self.scenarios(person_id)["departments"] for s in d["scenarios"]
                  if s["status"] == "ready" and not s.get("as_named")]
        order = ([s for _, s in listed if s["caller_id"] == person_id]
                 + [s for d, s in listed if d in depts] + [s for _, s in listed])
        out, seen = [], set()
        for s in order:
            if s["id"] not in seen:
                seen.add(s["id"])
                out.append({k: s[k] for k in ("id", "title", "situation", "agent", "agent_title")})
        return out[:6]

    def _feed_line(self, run, label, msgs, apprs):
        title = self._title(run["agent"])
        if label == "quiet":
            return f"{title}: quiet, nothing new"
        if label == "refused":
            return f"{title} was refused at the door"
        if label == "failed":
            return f"{title} stopped before sending anything"
        if msgs and all(m.get("kind") == "finance_answer" for m in msgs):
            return f"{title} answered a question for {', '.join(dict.fromkeys(m['to_name'] for m in msgs))}"
        told = defaultdict(int)
        for m in msgs:
            told[m["to_name"]] += max(1, len(re.findall(r"^\d+\.\s", m["text"], re.M)))
        parts = [f"told {n} about {c} flag{'s' if c != 1 else ''}" for n, c in told.items()]
        waiting = sum(a["status"] == "pending" for a in apprs)
        if waiting:
            parts.append(f"{waiting} action{'s' if waiting != 1 else ''} waiting for approval")
        return f"{title} " + (", ".join(parts) if parts else "finished")

    def today(self, person_id):
        if not person_id or not self.cos.directory.get(person_id):
            return {"ok": False, "error": "Unknown person."}
        allowed = self._allowed_areas(person_id)
        quiet = self._quiet_runs()
        runs = sorted((r for r in self.cos.memory.runs() if r["area_id"] in allowed), key=lambda r: r["run_id"],
                      reverse=True)
        msgs, apprs = defaultdict(list), defaultdict(list)
        for m in self.cos.outbox.messages():
            msgs[m["run_id"]].append({**m, "to_name": self._name(m["to_person_id"])})
        views = [self._approval_view(a, person_id) for a in self._all_approvals()]
        for v in views:
            apprs[v["run_id"]].append(v)
        feed, latest = [], {}
        for r in runs:
            row = self._run_row(r, quiet)
            line = self._feed_line(r, row["status_label"], msgs[r["run_id"]], apprs[r["run_id"]])
            item = {"run_id": r["run_id"], "agent": r["agent"], "agent_title": row["agent_title"],
                    "started_at": r["started_at"], "status_label": row["status_label"], "line": line}
            latest.setdefault(r["agent"], item)
            if len(feed) < 12:
                feed.append(item)
        mine = [v for v in views if v["status"] == "pending" and v["can_decide"]]
        status = {}
        for name in ALL_AGENTS:
            it = latest.get(name)
            waiting = [v for v in mine if v["agent"] == name]
            if name not in self.agents:
                status[name] = {"kind": "calm", "text": "Being built"}
            elif waiting:
                status[name] = {"kind": "wait", "text": "Waiting for your approval"}
            elif it is None:
                status[name] = {"kind": "calm", "text": "Has not run yet"}
            elif it["status_label"] == "quiet":
                status[name] = {"kind": "calm", "text": "Quiet today"}
            elif it["status_label"] in ("refused", "failed"):
                status[name] = {"kind": "stop", "text": f"Last run was {it['status_label']}"}
            else:
                status[name] = {"kind": "ok", "text": it["line"][len(it["agent_title"]) + 1:].capitalize()}
        hour = int(str(self.cos.clock.now)[11:13] or 9)
        person = next((p for p in self.people() if p["person_id"] == person_id), {})
        inbox = len(self.cos.outbox.messages(person_id))
        return {"ok": True, "person": person, "part_of_day": "morning" if hour < 12 else "afternoon" if hour < 18 else "evening",
                "needs_you": mine, "feed": feed, "picks": self._picks(person_id), "agent_status": status,
                "inbox_count": inbox}

    # ---- real-Claude samples
    def real_samples(self):
        data = load_real_samples(self.samples_path)
        return {"ok": True, "available": data is not None, **(data or {})}

    # ---- clock, triggers, pause
    def next_day(self):
        with self.lock:
            c = self.cos
            c.clock.advance(24 * 60)
            tasks = self.timer.due(c.clock) + self.calendar.due(c.clock)
            tasks = [t for t in tasks if t.agent in c.packs]
            for t in tasks:
                t.inputs.setdefault("as_of", c.clock.today)
            results = dispatch(tasks, lambda t: c.runner.run(c.packs[t.agent], t))
            self._save()
            quiet = self._quiet_runs()
            fired = [self._run_row(c.memory.get_run(r.run_id), quiet) for r in results]
            return {"ok": True, "now": c.clock.now, "fired": fired,
                    "summary": dict(Counter(f["status_label"] for f in fired))}

    def set_paused(self, paused):
        with self.lock:
            (self.cos.way_in.pause if paused else self.cos.way_in.resume)()
            self._save()
            return {"ok": True, "paused": self.cos.way_in.paused}


def _bad(message, status=400):
    return status, {"ok": False, "error": message}


def route(console, method, path, query, body):
    """Map one request to a Console call. Returns (http status, JSON-ready object)."""
    q = lambda key, default="": (query.get(key) or [default])[0]
    body = body or {}
    try:
        if method == "GET":
            gets = {
                "/api/state": console.state, "/api/people": lambda: {"people": console.people()},
                "/api/agents": console.agent_cards, "/api/scenarios": lambda: console.scenarios(q("person") or None),
                "/api/inbox": lambda: console.inbox(q("person")),
                "/api/approvals": lambda: console.approvals(q("person") or None),
                "/api/runs": console.runs, "/api/run": lambda: console.run_detail(q("id")),
                "/api/memory/areas": lambda: console.memory_areas(q("person")),
                "/api/memory": lambda: console.memory(q("person"), q("area"), q("kind") or None, q("limit", "100")),
                "/api/costs": console.costs, "/api/today": lambda: console.today(q("person")),
                "/api/real_samples": console.real_samples,
                "/api/permissions": lambda: console.permissions(q("person")),
            }
            if path not in gets:
                return _bad("Unknown page.", 404)
            return 200, gets[path]()
        def not_offered(error):
            return {"ok": False, "error": error, "not_offered": True} if error else None

        posts = {
            "/api/run": lambda: not_offered(console.check_start(body.get("caller_id"), body.get("agent"), body.get("area_id")))
            or console.run_agent(body.get("agent"), body.get("caller_id"), body.get("area_id"), body.get("inputs")),
            "/api/scenarios/run": lambda: console.run_scenario(body.get("id"), body.get("person_id")),
            "/api/finance/ask": lambda: not_offered(console.check_start(body.get("person_id"), "spend_advisor", "devx-internal"))
            or console.finance_ask(body.get("text"), body.get("person_id")),
            "/api/ask": lambda: not_offered(console.check_ask(body.get("text"), body.get("caller_id")))
            or console.ask(body.get("text"), body.get("caller_id")),
            "/api/approvals/decide": lambda: console.decide(body.get("approval_id"), bool(body.get("approve")),
                                                            body.get("by_person_id")),
            "/api/next_day": console.next_day, "/api/pause": lambda: console.set_paused(True),
            "/api/resume": lambda: console.set_paused(False), "/api/reset": console.reset,
        }
        if method != "POST" or path not in posts:
            return _bad("Unknown action.", 404)
        out = posts[path]()
        return (403 if isinstance(out, dict) and out.get("not_offered") else 200), out
    except Exception as e:  # show a short message instead of breaking the page
        return _bad(f"Something went wrong: {type(e).__name__}: {e}", 500)
