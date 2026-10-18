"""The console shell as plain Python: one Console holds the Company OS, finds page plug-ins (C8) and checks every call."""
import importlib
import importlib.util
import json
import os
import sys
import threading
from collections import Counter

from control_plane.guardrails import role_scopes
from lifecycle_kit.approved_actions import execute_approved
from control_plane.triggers.calendar_trigger import CalendarTrigger
from control_plane.triggers.dispatch import dispatch
from control_plane.triggers.timer_trigger import TimerTrigger
from wiring.agent_registry import available_agents
from wiring.build_company_os import build_company_os

from . import routes as _routes_package
from .run_walkthrough import TOOL_PLAIN, build_walkthrough, human, plain_reason

HERE = os.path.dirname(os.path.abspath(__file__))
ROUTES_DIR = os.path.join(HERE, "routes")
PAGES_DIR = os.path.join(HERE, "static", "pages")
MANIFEST = os.path.join(os.path.dirname(HERE), "company_data", "brain_sources", "manifest.json")
STATE_FILE = "console_state.json"
STATE_DB_FILES = ("company_memory.db", "people_surface.db", STATE_FILE)
ROLE_LABELS = {"admin": "Admin", "csm": "CSM", "growth": "Growth"}
ALL_PAGE_IDS = frozenset(p for pages in role_scopes.PAGES.values() for p in pages)
ADMIN_ONLY_TOOLS = ("book_travel",)
CORE_MODULE = "core_routes"


class Plugin:
    """One discovered page: its PAGE card, its routes and the script and css it ships (any may be missing)."""

    def __init__(self, page, routes=None, script=None, css=None):
        self.page, self.routes, self.script, self.css = page, routes or {}, script, css


def _load_module(routes_dir, name):
    if os.path.realpath(routes_dir) == os.path.realpath(ROUTES_DIR):
        return importlib.import_module(f"web_console.routes.{name}")
    spec = importlib.util.spec_from_file_location(f"console_plugin_{name}", os.path.join(routes_dir, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def discover_plugins(console, routes_dir=ROUTES_DIR, pages_dir=PAGES_DIR):
    """Find route modules and page scripts by page id. A missing, broken or unknown page is skipped."""
    found = {}
    names = sorted(f[:-3] for f in os.listdir(routes_dir) if f.endswith("_routes.py")) if os.path.isdir(routes_dir) else []
    for name in (n for n in names if n != CORE_MODULE):
        try:
            module = _load_module(routes_dir, name)
            page, table = dict(module.PAGE), module.routes(console)
            if page["id"] in ALL_PAGE_IDS and page["id"] not in found:
                found[page["id"]] = Plugin(page, table)
        except Exception:
            continue
    for f in sorted(os.listdir(pages_dir)) if os.path.isdir(pages_dir) else []:
        pid = f[:-3] if f.endswith(".js") else None
        if pid in ALL_PAGE_IDS:
            plugin = found.setdefault(pid, Plugin({"id": pid, "title": human(pid).capitalize(), "order": 500, "icon": "bot"}))
            plugin.script = f"pages/{f}"
            plugin.css = f"pages/{pid}.css" if os.path.isfile(os.path.join(pages_dir, pid + ".css")) else None
    return found


class Console:
    def __init__(self, state_dir, reset=False, routes_dir=ROUTES_DIR, pages_dir=PAGES_DIR, seed_brain=True):
        self.state_dir = str(state_dir)
        self.seed_brain = seed_brain
        self.routes_dir, self.pages_dir = routes_dir, pages_dir
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
        self.cos = build_company_os(self.agents, state_dir=self.state_dir, seed_brain=self.seed_brain, **kwargs)
        if saved.get("paused"):
            self.cos.way_in.pause()
        self.timer = TimerTrigger(self._schedule())
        self.calendar = CalendarTrigger(self.cos.data_conn)
        self.calendar._seen = set(saved.get("calendar_seen", []))
        self.inbox_trigger = self._make_inbox_trigger()
        self._save()
        self._load_plugins()

    def _make_inbox_trigger(self):
        try:
            from control_plane.triggers.inbox_trigger import InboxTrigger
            return InboxTrigger(MANIFEST)
        except Exception:
            return None

    def _load_plugins(self):
        """Plug-ins get the console after it is built, so a handler sees the fresh `cos` after a reset."""
        from .routes import core_routes
        self.plugins = discover_plugins(self, self.routes_dir, self.pages_dir)
        self.route_table = {}
        for key, handler in core_routes.routes(self).items():
            self.route_table[key] = (core_routes.ROUTE_PAGES.get(key[1]), handler)
        for pid, plugin in self.plugins.items():
            for key, handler in plugin.routes.items():
                self.route_table.setdefault(key, (pid, handler))

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

    # ---- people and roles: only the three demo people exist for the console
    def _name(self, person_id):
        p = self.cos.directory.get(person_id) if person_id else None
        return p["name"] if p else (person_id or "someone")

    def role_of(self, person_id):
        """The console role (admin, csm, growth) of one of the three demo people, else None."""
        if person_id not in dict(role_scopes.DEMO_PEOPLE) or not self.cos.directory.get(person_id):
            return None
        return role_scopes.console_role(self.cos.directory, person_id)

    def people(self):
        out = []
        for pid, _ in role_scopes.DEMO_PEOPLE:
            role = self.role_of(pid)
            full = self._name(pid)
            out.append({"person_id": pid, "name": full.split(" ")[0], "full_name": full, "role": role,
                        "role_label": ROLE_LABELS.get(role, role)})
        return out

    def pages_for(self, person_id):
        """The pages this role may open, in order, with the script and css each ships (None when not built yet)."""
        role = self.role_of(person_id)
        rows = []
        for pid in role_scopes.PAGES.get(role, ()):
            plugin = self.plugins.get(pid)
            core = pid in CORE_PAGES
            page = plugin.page if plugin else {"title": CORE_PAGES.get(pid, (human(pid).capitalize(), 500, "bot"))[0],
                                              "order": CORE_PAGES.get(pid, (0, 500, "bot"))[1],
                                              "icon": CORE_PAGES.get(pid, (0, 0, "bot"))[2]}
            rows.append({"id": pid, "title": page["title"], "order": page["order"], "icon": page["icon"],
                         "script": plugin.script if plugin else None, "css": plugin.css if plugin else None,
                         "builtin": core, "present": core or bool(plugin and (plugin.script or plugin.routes))})
        return sorted(rows, key=lambda r: r["order"])

    # ---- run stories
    def _title(self, agent):
        return human(agent).capitalize()

    def _quiet_runs(self):
        rows = self.cos.memory.conn.execute("SELECT DISTINCT run_id FROM run_steps WHERE step = 'quiet'")
        return {r[0] for r in rows}

    def _run_row(self, run, quiet=None):
        quiet = self._quiet_runs() if quiet is None else quiet
        status = run["status"] or "running"
        label = "quiet" if run["run_id"] in quiet else status
        entries = [e for e in self.cos.ledger.entries if e["run_id"] == run["run_id"]]
        return {**run, "status_label": label, "caller_name": self._name(run["caller_id"]),
                "agent_title": self._title(run["agent"]), "cache_hits": sum(e["cache"] == "hit" for e in entries),
                "model_calls": len(entries),
                "area_name": next((a["name"] for a in self.cos.memory.areas() if a["area_id"] == run["area_id"]),
                                  run["area_id"])}

    def _letters_of(self, run_id):
        return [{**m, "to_name": self._name(m["to_person_id"]), "agent_title": self._title(m["agent"])}
                for m in self.cos.outbox.messages() if m["run_id"] == run_id]

    def _walkthrough(self, run):
        mem = self.cos.memory
        cases = [c for c in mem.cases() if c["run_id"] == run["run_id"]]
        approvals = [self._approval_view(a, None) | {"args": a["args"]} for a in self._approvals_of_run(run["run_id"])]
        return build_walkthrough(run, mem.run_steps(run["run_id"]), cases=cases, approvals=approvals, name_of=self._name)

    def run_detail(self, run_id):
        run = self.cos.memory.get_run(run_id)
        if run is None:
            return {"ok": False, "error": "I could not find that run."}
        return {"ok": True, "run": self._run_row(run), "walkthrough": self._walkthrough(run),
                "messages": self._letters_of(run_id)}

    def may_see_run(self, person_id, run_id):
        """Admin sees every run. Others see runs they started or runs in an area they may read."""
        role, run = self.role_of(person_id), self.cos.memory.get_run(run_id)
        if run is None or role is None:
            return True if role else False
        shared = role_scopes.readable_areas(self.cos.directory, person_id) - {role_scopes.INTERNAL_AREA}
        return role_scopes.may_see(role, "runs_all") or run["caller_id"] == person_id or run["area_id"] in shared

    def runs(self, limit=200):
        quiet = self._quiet_runs()
        rows = sorted(self.cos.memory.runs(), key=lambda r: r["run_id"], reverse=True)[:limit]
        entries = self.cos.ledger.entries
        hits = sum(e["cache"] == "hit" for e in entries)
        return {"ok": True, "runs": [self._run_row(r, quiet) for r in rows],
                "summary": {"run_count": len(self.cos.memory.runs()), "model_calls": len(entries), "cache_hits": hits,
                            "total_cost_usd": sum(e["cost_usd"] for e in entries),
                            "status": dict(Counter(self._run_row(r, quiet)["status_label"] for r in self.cos.memory.runs()))}}

    # ---- approvals
    def _all_approvals(self):
        rows = self.cos.approvals.conn.execute("SELECT * FROM approvals ORDER BY approval_id").fetchall()
        return [self.cos.approvals._row(r) for r in rows]

    def _approvals_of_run(self, run_id):
        return [a for a in self._all_approvals() if a["run_id"] == run_id]

    def _can_approve(self, person_id, row):
        """(allowed, plain reason). Bookings need an Admin; the pack's approver roles and the person's areas decide the rest."""
        role = self.role_of(person_id)
        if role is None:
            return False, "Choose a person first."
        if row["tool"] in ADMIN_ONLY_TOOLS and role != "admin":
            return False, "Only an Admin may approve a booking."
        if not self.cos.policy.may_approve(self.cos.directory.role(person_id), row["agent"]):
            return False, f"A {ROLE_LABELS[role]} may not approve this."
        run = self.cos.memory.get_run(row["run_id"]) or {}
        if run.get("area_id") not in role_scopes.readable_areas(self.cos.directory, person_id):
            return False, "This action is about an area this person does not work on."
        return True, ""

    def _approval_view(self, a, person_id):
        ok, why = self._can_approve(person_id, a) if person_id else (None, "")
        run = self.cos.memory.get_run(a["run_id"]) or {}
        executed = None
        for s in self.cos.memory.run_steps(a["run_id"]):
            if s["step"] == "approved_action" and s["detail"].get("approval_id") == a["approval_id"]:
                executed = s["detail"].get("result")
        return {"approval_id": a["approval_id"], "run_id": a["run_id"], "agent": a["agent"],
                "agent_title": self._title(a["agent"]), "tool": a["tool"],
                "what": TOOL_PLAIN.get(a["tool"], human(a["tool"]).capitalize()), "title": a["args"].get("title", ""),
                "args": {k: v for k, v in a["args"].items() if k != "owner_id"},
                "area_id": run.get("area_id"), "why_held": plain_reason(a["reason"]), "status": a["status"],
                "requested_at": a["requested_at"], "decided_by": self._name(a["decided_by"]) if a["decided_by"] else None,
                "decided_at": a["decided_at"], "executed": executed, "can_decide": ok, "cannot_because": why}

    def approvals(self, person_id):
        """Only the held actions this person may decide, and the ones already decided among them."""
        rows = [v for v in (self._approval_view(a, person_id) for a in self._all_approvals()) if v["can_decide"]]
        rows.sort(key=lambda r: (r["status"] != "pending", r["approval_id"]))
        return {"ok": True, "approvals": rows, "pending": sum(r["status"] == "pending" for r in rows)}

    def decide(self, approval_id, approve, by_person_id):
        with self.lock:
            row = self.cos.approvals.get(approval_id)
            if row is None:
                return 404, {"ok": False, "error": "I could not find that approval."}
            allowed, why = self._can_approve(by_person_id, row)
            if not allowed:
                return 403, {"ok": False, "refused": True, "error": why}
            try:
                self.cos.approvals.decide(approval_id, bool(approve), by_person_id)
            except ValueError:
                return 409, {"ok": False, "error": f"{approval_id} was already decided. A request can be decided only once."}
            executed = self._execute(approval_id, row) if approve else None
            return 200, {"ok": True, "status": "approved" if approve else "rejected", "executed": executed,
                         "approval": self._approval_view(self.cos.approvals.get(approval_id), by_person_id)}

    def _execute(self, approval_id, row):
        if row["tool"] == "book_travel":
            from agents.finance.travel_booking.service import booking_after_approval
            out = booking_after_approval(self.cos, approval_id)
            return {"status": out["status"], "result": out.get("booking_ref") or out.get("reason", "")}
        return execute_approved(approval_id, self.cos.approvals, self.cos.runtime.registry, self.cos.memory)

    # ---- clock, triggers, pause
    def _fire_inbox(self, clock):
        """Sources whose arrival time has come go into the brain through the pipeline. A failed source is counted, not raised."""
        if self.inbox_trigger is None:
            return {"arrived": 0, "ingested": 0, "failed": 0}
        from control_plane.company_brain.pipeline import ingest_file, read_manifest_file
        rows, done, failed = self.inbox_trigger.due(clock), 0, 0
        for r in rows:
            try:
                ingest_file(self.cos, kind=r["kind"], content=read_manifest_file(r, MANIFEST), filename=r["file"],
                            hint_area=r.get("hint_area"), origin_ref=r["origin_ref"], received_at=r["arrives_at"])
                done += 1
            except Exception:
                failed += 1
        return {"arrived": len(rows), "ingested": done, "failed": failed}

    def next_day(self):
        with self.lock:
            c = self.cos
            c.clock.advance(24 * 60)
            tasks = [t for t in self.timer.due(c.clock) + self.calendar.due(c.clock) if t.agent in c.packs]
            for t in tasks:
                t.inputs.setdefault("as_of", c.clock.today)
            results = dispatch(tasks, lambda t: c.runner.run(c.packs[t.agent], t))
            inbox = self._fire_inbox(c.clock)
            self._save()
            quiet = self._quiet_runs()
            fired = [self._run_row(c.memory.get_run(r.run_id), quiet) for r in results]
            return {"ok": True, "now": c.clock.now, "fired": fired, "inbox": inbox,
                    "summary": dict(Counter(f["status_label"] for f in fired))}

    def set_paused(self, paused):
        with self.lock:
            (self.cos.way_in.pause if paused else self.cos.way_in.resume)()
            self._save()
            return {"ok": True, "paused": self.cos.way_in.paused}

    def run_story(self, run_id):
        return self.run_detail(run_id)


CORE_PAGES = {"home": ("Home", 0, "home"), "approvals": ("Approvals", 900, "check"), "runs": ("Runs", 910, "pulse")}


def _bad(status, message):
    return status, {"ok": False, "error": message}


def route(console, method, path, query, body):
    """Map one request to a handler. The viewer and the page are checked here, before any handler runs."""
    flat = {k: v[0] for k, v in (query or {}).items() if v}
    body = body if isinstance(body, dict) else {}
    try:
        if (method, path) == ("GET", "/api/console/people"):
            return 200, {"ok": True, "people": console.people()}
        entry = console.route_table.get((method, path))
        if entry is None:
            return _bad(404, "Unknown page.")
        page_id, handler = entry
        viewer = flat.get("viewer") or body.get("viewer")
        role = console.role_of(viewer)
        if role is None:
            return _bad(403, "Choose one of the three people first. Nothing was run.")
        if page_id and not role_scopes.may_open_page(role, page_id):
            return _bad(403, f"A {ROLE_LABELS[role]} may not open this page. Nothing was run.")
        status, out = handler(flat, body or None, viewer)
        return status, out
    except Exception as e:  # show a short message instead of breaking the page
        return _bad(500, f"Something went wrong: {type(e).__name__}: {e}")
