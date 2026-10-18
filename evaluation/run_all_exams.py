"""Runs every agent pack's replay exam (its judge(raw) if it has one), prints one table and saves evaluation/latest_scores.json."""
import importlib
import json
import os

from wiring.agent_registry import AGENTS
from wiring.build_company_os import ALL_AGENTS, build_company_os

SCORES_PATH = os.path.join(os.path.dirname(__file__), "latest_scores.json")


def _generic(r):
    """Fallback for an exam with no judge(raw): pass when nothing is missed and nothing is a false alarm."""
    ok = r.get("missed", 0) == 0 and r.get("false_alarms", 0) == 0
    return "planted cases found, no false alarms", json.dumps({k: v for k, v in r.items() if isinstance(v, (int, float))}), ok


def close_all(cos):
    """Close the databases of one Company OS (the exam may have opened others on its own)."""
    for part in (cos.data_conn, cos.memory, cos.outbox, cos.approvals):
        if hasattr(part, "close"):
            part.close()


def run_all(agents=ALL_AGENTS):
    """Run each available pack's exam in its own fresh Company OS. Returns a list of result rows."""
    rows = []
    for name in agents:
        try:
            exam = importlib.import_module(f"{AGENTS[name]}.replay_exam")
            importlib.import_module(f"{AGENTS[name]}.pack")
        except ImportError as e:
            rows.append({"agent": name, "measured": "-", "result": f"skipped, not ready ({e})", "passed": None, "raw": None})
            continue
        cos = build_company_os(agents=(name,))
        try:
            raw = exam.run_exam(cos)
        finally:
            close_all(cos)
        measured, text, ok = getattr(exam, "judge", _generic)(raw)
        rows.append({"agent": name, "measured": measured, "result": text, "passed": bool(ok), "raw": _slim(raw)})
    return rows


def _slim(raw):
    """Keep the summary numbers, drop long per-case lists."""
    return {k: v for k, v in raw.items() if not isinstance(v, list) or len(v) <= 5}


def print_table(rows):
    cols = ("agent", "what is measured", "result", "pass")
    data = [(r["agent"], r["measured"], r["result"], "skip" if r["passed"] is None else ("PASS" if r["passed"] else "FAIL"))
            for r in rows]
    widths = [max(len(str(x[i])) for x in data + [cols]) for i in range(4)]
    for line in [cols] + data:
        print("  ".join(str(c).ljust(w) for c, w in zip(line, widths)).rstrip())


def main():
    rows = run_all()
    print_table(rows)
    with open(SCORES_PATH, "w") as fh:
        json.dump(rows, fh, indent=1, default=str)
    print(f"\nSaved {SCORES_PATH}")
    return 0 if all(r["passed"] is not False for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
