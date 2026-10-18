"""Turns one run's logged steps into the six-step story in plain words, with guardrail verdicts shown clearly."""
import json
import re

ACTION_TOOLS = ("send_private_message", "create_followup_task")
VERDICT_WORD = {"allow": "allowed", "deny": "denied", "ask": "held"}

TOOL_PLAIN = {
    "invoices_window": "Invoices from the last weeks",
    "payments_window": "Recent payments, with how old each vendor was",
    "budget_vs_spend": "Budget against spend, per team",
    "travel_share_of_salary": "Travel spend against team pay totals",
    "client_channel_activity": "When the client last wrote in the shared channel",
    "recent_client_messages": "Recent client messages (treated as data, never as orders)",
    "upcoming_meeting": "The calendar event and who is invited",
    "project_open_items": "Open questions and tasks from earlier meetings",
    "project_recent_decisions": "Decisions from recent meetings",
    "spend_breakdown": "Company cost by category, with travel split into flights, trains and hotels",
    "trip_savings": "Savings found on trips: late bookings, business seats, repeat trips, hotels above the city rate",
    "trip_verdicts": "A verdict for every trip: cheaper option existed, or best option chosen",
    "travel_by_team": "Travel cost per team",
    "send_client_message": "Send a message to the client",
    "send_private_message": "Send a private message",
    "create_followup_task": "Write a follow-up task into company memory",
}
KEY_LABEL = {"evidence": "What we see", "why_it_matters": "Why it matters", "next_step": "Next step",
             "severity": "How serious", "summary": "In short", "why": "Why", "reason": "Reason"}
TITLE_KEYS = ("text", "title", "signal", "kind", "team", "topic")
ID_ONLY = re.compile(r"^[\w-]{1,20}$")
SKIP_KEYS = ("cites", "ids", "amount_inr", "project_id", "topic", "facts")


def human(text):
    return str(text).replace("_", " ")


def plain_reason(reason):
    """Explain a refusal or denial in everyday words. Unknown reasons are shown as they are."""
    r = str(reason or "")
    if "paused" in r:
        return "All agents are paused. Use the switch at the top of the page to resume them."
    m = re.match(r"role '(.+)' may not start agent '(.+)'", r)
    if m:
        return f"A person with the role {human(m.group(1))} is not allowed to start the {human(m.group(2))} agent."
    m = re.match(r"caller has no access to area '(.+)'", r)
    if m:
        return (f"This person does not work on that client ({m.group(1)}), so they may not see its data. "
                "Only people on a client's projects, the CEO and the R&D lead can.")
    if "unknown caller" in r:
        return "The system does not know this person."
    if "unknown agent" in r:
        return "The system does not know this agent."
    if "budget" in r:
        return "The money budget for this agent or person is used up."
    if "system may only" in r:
        return "The system timer may only start scheduled or calendar runs."
    if "risky action" in r:
        return "This action changes something, so a person must approve it first."
    return r


def _json_of(text):
    """Find the first JSON object inside a text (results may carry an outside-data wrapper)."""
    s, e = str(text).find("{"), str(text).rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(text[s:e + 1])
    except ValueError:
        return None


def _read_summary(result):
    data = _json_of(result)
    if not isinstance(data, dict):
        return ""
    if "error" in data:
        return f"Reply: {data['error']}"
    counts = [f"{len(v)} {human(k)}" for k, v in data.items() if isinstance(v, list)]
    return ", ".join(counts)


def _items_of(data):
    """Render a model answer (JSON) as a list of {title, points} blocks plus plain lines."""
    blocks, lines, lists = [], [], []
    if not isinstance(data, dict):
        return blocks, lines, lists
    for key, value in data.items():
        if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            for item in value:
                title = next((str(item[k]) for k in TITLE_KEYS if item.get(k)), human(key))
                if item.get("ids"):
                    title += f" ({', '.join(map(str, item['ids']))})"
                points = [[KEY_LABEL.get(k, human(k).capitalize()), str(v)] for k, v in item.items()
                          if isinstance(v, (str, int, float)) and k not in SKIP_KEYS and str(v) != title
                          and k not in TITLE_KEYS]
                blocks.append({"title": human(title), "group": human(key), "points": points})
        elif isinstance(value, list) and value:
            lists.append({"label": human(key).capitalize(), "items": [str(v) for v in value]})
        elif isinstance(value, (str, int, float)) and value != "":
            lines.append(f"{KEY_LABEL.get(key, human(key).capitalize())}: {value}")
    return blocks, lines, lists


SENTENCE_KEYS = ("headline", "evidence", "summary", "text", "message", "title", "why", "why_it_matters", "next_step")
SENTENCE_MAX = 200


def _first_line(text):
    """The first line of a finding, cut at its first sentence when it runs long. A 'Titles:' tail is dropped."""
    line = re.sub(r"\s*Titles?:.*$", "", str(text).strip().split("\n")[0], flags=re.S).strip()
    if len(line) > SENTENCE_MAX:
        first = re.match(r"^(.{20,}?[.!?])(?:\s|$)", line)
        line = first.group(1) if first else line[:SENTENCE_MAX].rsplit(" ", 1)[0] + "..."
    return line


def _sentences_of(data):
    """Plain sentences for what the model decided: the headline or first line of each finding, never key names."""
    heads, findings, extras = [], [], []
    if not isinstance(data, dict):
        return []
    for value in data.values():
        if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            for item in value:
                text = next((item[k] for k in SENTENCE_KEYS if isinstance(item.get(k), str) and item[k].strip()), None)
                if text:
                    findings.append(_first_line(text))
        elif isinstance(value, list):
            extras += [_first_line(v) for v in value if isinstance(v, str) and v.strip()]
        elif isinstance(value, str) and value.strip() and not ID_ONLY.match(value.strip()):
            heads.append(_first_line(value))
    found = heads + findings
    return [s for s in dict.fromkeys(found or extras) if s]


def _step(n, title, state, lines=None, **extra):
    return {"n": n, "title": title, "state": state, "lines": lines or [], **extra}


def _read_step(reads):
    items = []
    for s in reads:
        d = s["detail"]
        verdict = VERDICT_WORD.get(d.get("verdict"), "allowed")
        what = TOOL_PLAIN.get(d.get("name"), human(d.get("name")))
        note = plain_reason(d.get("reason")) if verdict != "allowed" else _read_summary(d.get("result", ""))
        items.append({"text": what, "verdict": verdict, "note": note})
    state = "ok" if items else "skipped"
    return _step(1, "What it read", state, ["Each read passed the every-action check."] if items else [], items=items)


def _found_step(understood, quiet, cases):
    if quiet:
        return _step(2, "What the code found", "quiet", ["Nothing needed a look today."])
    if not understood:
        return _step(2, "What the code found", "skipped", [])
    items = [{"text": human(c["subject"]).replace(":", ": "), "note": f"Severity: {c['severity']}"} for c in cases]
    lines = [f"The code found {len(items)} item(s). Code does the counting, so the numbers are exact."] if items \
        else ["The code collected the facts it needs from what it read (step 1) and prepared them for the model."]
    return _step(2, "What the code found", "ok", lines, items=items)


def _model_step(calls, quiet, final_text):
    if quiet:
        return _step(3, "What the model concluded", "quiet", ["No model call was made. This saves cost."])
    if not calls:
        return _step(3, "What the model concluded", "skipped", [])
    cost = sum(c["detail"].get("cost_usd", 0) for c in calls)
    hits = sum(1 for c in calls if c["detail"].get("cache_hit"))
    meta = (f"{len(calls)} model call(s), {sum(c['detail'].get('tokens_in', 0) for c in calls)} tokens in, "
            f"{sum(c['detail'].get('tokens_out', 0) for c in calls)} tokens out, cost ${cost:.4f}, "
            f"saved-prefix hits (cache): {hits} of {len(calls)}")
    data = _json_of(final_text or calls[-1]["detail"].get("text", ""))
    blocks, lines, lists = _items_of(data)
    sentences = _sentences_of(data)
    if data is None and calls[-1]["detail"].get("text"):
        lines = [calls[-1]["detail"]["text"][:400]]
    if data is None and lines:
        sentences = [_first_line(lines[0])]
    return _step(3, "What the model concluded", "ok", lines, blocks=blocks, lists=lists, sentences=sentences, meta=meta, cost_usd=cost,
                 cache_hits=hits, model_calls=len(calls))


def _check_step(opened, refused, check, acts, failed_reason):
    verdicts = []
    for s in acts:
        d = s["detail"]
        verdicts.append({"what": TOOL_PLAIN.get(d.get("name"), human(d.get("name"))),
                         "verdict": VERDICT_WORD.get(d.get("verdict"), "allowed"),
                         "reason": plain_reason(d.get("reason"))})
    if refused:
        d = refused["detail"]
        return _step(4, "What was checked before sending", "refused",
                     ["Way-in check: refused. " + plain_reason(d.get("reason"))], verdicts=[
                         {"what": "Start this run", "verdict": "denied", "reason": plain_reason(d.get("reason"))}])
    lines = ["Way-in check: allowed." if opened else ""]
    state = "ok"
    if check is not None:
        problems = check["detail"].get("problems", [])
        if problems:
            state = "failed"
            lines += ["Safety check found a problem, so nothing was sent:"] + list(problems)
        else:
            lines.append("Safety check passed: every number and id matches what the code found.")
    elif failed_reason:
        state = "failed"
        lines.append(failed_reason)
    if any(v["verdict"] == "denied" for v in verdicts):
        lines.append("The every-action check denied at least one action (see below).")
    if any(v["verdict"] == "held" for v in verdicts):
        lines.append("The every-action check held at least one action for a person.")
    return _step(4, "What was checked before sending", state, [x for x in lines if x], verdicts=verdicts)


def _told_step(acts, approvals, name_of):
    items, pending = [], list(approvals)
    for s in acts:
        d = s["detail"]
        args, verdict = d.get("args", {}), d.get("verdict")
        if d.get("name") == "send_private_message":
            who = name_of(args.get("to_person_id"))
            if verdict == "allow":
                items.append({"text": f"Told {who} in private ({human(args.get('kind', 'note'))})",
                              "verdict": "allowed", "message": args.get("text", "")})
            else:
                items.append({"text": f"Message to {who} was blocked", "verdict": "denied",
                              "note": plain_reason(d.get("reason"))})
        elif d.get("name") == "create_followup_task":
            match = next((a for a in pending if a["args"] == args), None)
            if match:
                pending.remove(match)
            status = (match or {}).get("status", "pending")
            items.append({"text": f"Follow-up waiting for approval: {args.get('title', '')}",
                          "verdict": "held" if verdict == "ask" else VERDICT_WORD.get(verdict, "allowed"),
                          "approval_id": (match or {}).get("approval_id"), "approval_status": status,
                          "note": plain_reason(d.get("reason")) if verdict != "allow" else ""})
    state = "held" if any(i["verdict"] == "held" for i in items) else ("ok" if items else "skipped")
    lines = [] if items else ["Nobody was told."]
    return _step(5, "Who was told, or what is waiting for approval", state, lines, items=items)


def _saved_step(remember, cases, approved_steps):
    lines, items = [], []
    if cases:
        lines.append(f"{len(cases)} case(s) saved to company memory so the team can look back.")
        items += [{"text": f"{c['case_id']}: {human(c['subject']).replace(':', ': ')}", "note": f"Severity: {c['severity']}"} for c in cases]
    if remember and not cases:
        lines += [f"{human(k).capitalize()}: {v if not isinstance(v, list) else ', '.join(map(str, v))}"
                  for k, v in remember.items()]
    for s in approved_steps:
        d = s["detail"]
        lines.append(f"After approval by {d.get('approved_by')}: {d.get('result')}")
    lines.append("The run log (every step you see here) is saved and cannot be changed.")
    return _step(6, "What was saved", "ok", lines, items=items)


def build_walkthrough(run, steps, *, cases=(), approvals=(), name_of=str) -> dict:
    """run: a memory `runs` row; steps: its run_steps; cases and approvals: those of this run."""
    by = lambda name: [s for s in steps if s["step"] == name]
    first = lambda name: (by(name) or [None])[0]
    tools = by("tool")
    acts = [s for s in tools if s["detail"].get("name") in ACTION_TOOLS]
    reads = [s for s in tools if s["detail"].get("name") not in ACTION_TOOLS]
    refused, quiet = first("refused"), bool(by("quiet"))
    closed = first("closed")
    final_text = (closed["detail"].get("final_text") if closed else "") or ""
    failed_reason = (first("model_failed") or {"detail": {}})["detail"].get("reason", "")
    understood = (first("understand") or {"detail": {}})["detail"]
    outcome = "refused" if refused else "quiet" if quiet else (run.get("status") or "running")
    steps_out = [
        _read_step(reads),
        _found_step(understood if by("understand") else None, quiet, list(cases)),
        _model_step(by("model_call"), quiet, final_text),
        _check_step(bool(first("opened")), refused, first("check"), acts, failed_reason),
        _told_step(acts, approvals, name_of),
        _saved_step((first("remember") or {"detail": {}})["detail"], list(cases), by("approved_action")),
    ]
    if refused:
        for s in steps_out:
            if s["n"] != 4:
                s["state"], s["lines"], s["items"] = "skipped", ["Not reached: the run was refused at the way in."], []
    headline = {
        "refused": "Refused at the way in. " + plain_reason((refused or {"detail": {}})["detail"].get("reason")),
        "quiet": "Quiet run: the code found nothing to report, so no model was called and nobody was told.",
        "held": "Done, but at least one action is waiting for a person to approve it.",
        "done": "Done. The agent read, checked, told the right people and saved what it did.",
        "failed": "Stopped before anything was sent. " + (failed_reason or "The safety check found a problem."),
    }.get(outcome, f"Run status: {outcome}.")
    return {"run_id": run["run_id"], "agent": run["agent"], "area_id": run["area_id"], "caller_id": run["caller_id"],
            "trigger_kind": run["trigger_kind"], "outcome": outcome, "headline": headline,
            "started_at": run["started_at"], "cost_usd": run.get("cost_usd") or 0.0, "steps": steps_out}
