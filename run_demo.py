"""One simulated working day on the dummy company: triggers fire, agents run, people get messages."""
import shutil
import tempfile

from connectors.event_lookup import event_area
from contract.types import Task
from evaluation.run_all_exams import close_all
from triggers.calendar_trigger import CalendarTrigger
from triggers.dispatch import dispatch
from triggers.request_trigger import parse_request
from triggers.timer_trigger import TimerTrigger
from wiring.agent_registry import available_agents as registry_available
from wiring.build_company_os import build_company_os


def available_agents():
    """Packs that can be built now, and (name, reason) pairs for the rest."""
    ok, missing = registry_available()
    return ok, list(missing.items())


def _first_line(text, width=70):
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return line if len(line) <= width else line[:width - 3] + "..."


def _schedule(cos, agents):
    """Daily rows: finance watch for DevX."""
    rows = []
    if "finance_watch" in agents:
        rows.append({"agent": "finance_watch", "area_id": "devx-internal", "every": "daily"})
    return rows


def _outcome(cos, result):
    """Return (status, one-line outcome) for one run."""
    if result.status == "refused":
        return "refused", result.reason or "the way-in check said no"
    if result.status == "done" and result.final_text == "quiet":
        return "quiet", "nothing to report, no model call"
    if result.status == "failed":
        return "failed", result.reason or _first_line(result.final_text)
    sent = [m for m in cos.outbox.messages() if m["run_id"] == result.run_id]
    waiting = [a for a in cos.approvals.pending() if a["run_id"] == result.run_id]
    parts = [f"{len(sent)} message(s) sent"]
    if waiting:
        parts.append(f"{len(waiting)} approval(s) waiting")
    return result.status, ", ".join(parts)


def run_day(agents=None, state_dir=None):
    """Run the day. Returns a dict with the runs, messages, approvals, refusal and cost numbers."""
    names = tuple(agents) if agents else available_agents()[0]
    cos = build_company_os(names, state_dir=state_dir)
    runs, triggers = [], []

    def start(task, label):
        result = cos.runner.run(cos.packs[task.agent], task)
        status, line = _outcome(cos, result)
        runs.append({"trigger": label, "agent": task.agent, "area": task.area_id, "caller": task.caller_id,
                     "status": status, "outcome": line, "run_id": result.run_id})
        return result

    timer_tasks = TimerTrigger(_schedule(cos, names)).due(cos.clock)
    triggers.append(f"timer: {len(timer_tasks)} daily run(s) due")
    dispatch(timer_tasks, lambda t: start(t, "timer"))

    if "meeting_prep" in names:
        calendar = CalendarTrigger(cos.data_conn)
        cal_tasks, hours = calendar.due(cos.clock, within_hours=24), 24
        if not cal_tasks:  # nothing tomorrow: look 72 hours ahead so the demo shows the calendar path
            cal_tasks, hours = calendar.due(cos.clock, within_hours=72), 72
        triggers.append(f"calendar: {len(cal_tasks)} client meeting(s) in the next {hours} hours")
        dispatch(cal_tasks, lambda t: start(t, "calendar"))
        asker = cos.directory.csm_of("C02")
        ask = parse_request("prep me for EV113", asker, event_area=event_area(cos.data_conn))
        triggers.append(f"request: {asker} asks 'prep me for EV113'")
        start(ask, "request")

    refusal = None
    if "finance_watch" in names:
        lead = cos.directory.people_by_role("finance_lead")[0]
        held = Task(agent="finance_watch", caller_id=lead, area_id="devx-internal", trigger_kind="request",
                    inputs={"as_of": "2026-06-15"}, prompt="show me finance watch")
        triggers.append(f"request: finance lead {lead} asks for finance watch as of 2026-06-15")
        start(held, "request")
        engineer = cos.directory.people_by_role("engineer")[0]
        task = Task(agent="finance_watch", caller_id=engineer, area_id="devx-internal", trigger_kind="request",
                    prompt="show me finance watch")
        triggers.append(f"request: engineer {engineer} asks for finance watch")
        res = start(task, "request")
        refusal = {"caller": engineer, "status": res.status, "reason": res.reason}

    messages = cos.outbox.messages()
    entries = cos.ledger.entries
    cache = [e["cache"] for e in entries]
    cost = {"calls": len(entries), "cache_hits": cache.count("hit"), "cache_writes": cache.count("write"),
            "usd": round(sum(e["cost_usd"] for e in entries), 4)}
    return {"date": cos.clock.today, "agents": names, "triggers": triggers, "runs": runs, "messages": messages,
            "approvals": cos.approvals.pending(), "refusal": refusal, "cost": cost, "cos": cos}


def print_day(day):
    cos = day["cos"]
    name = lambda pid: f"{pid} {p['name']}" if (p := cos.directory.get(pid)) else pid
    print(f"One day at the dummy company: {day['date']}")
    print("\nTriggers")
    for t in day["triggers"]:
        print(f"  {t}")
    print("\nRuns (trigger, agent, area, status, outcome)")
    for r in day["runs"]:
        print(f"  {r['trigger']:<8} {r['agent']:<15} {r['area']:<13} {r['status']:<8} {r['outcome']}")
    print("\nMessages people received (who, kind, first line)")
    for m in day["messages"]:
        print(f"  {name(m['to_person_id'])} | {m['kind']} | {_first_line(m['text'])}")
    print(f"\nApprovals waiting: {len(day['approvals'])}")
    for a in day["approvals"]:
        print(f"  {a['approval_id']} {a['agent']} {a['tool']}: {_first_line(a['reason'])}")
    if day["refusal"]:
        r = day["refusal"]
        print(f"\nRefusal example: engineer {r['caller']} asked for finance watch -> {r['status']} ({r['reason']})")
    c = day["cost"]
    print(f"\nCost and cache: {c['calls']} model calls, {c['cache_hits']} cache hits, "
          f"{c['cache_writes']} cache writes, ${c['usd']:.4f} total")


def main():
    state = tempfile.mkdtemp(prefix="company_os_demo_")
    try:
        _, skipped = available_agents()
        day = run_day(state_dir=state)
        print_day(day)
        if skipped:
            print("\nNot built yet, skipped: " + ", ".join(name for name, _ in skipped))
        close_all(day["cos"])
    finally:
        shutil.rmtree(state, ignore_errors=True)


if __name__ == "__main__":
    main()
