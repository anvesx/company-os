"""Records one real-Claude run per agent on its demo scenario, for the console's "real Claude version" view.

Uses the person's Claude plan through the `claude` CLI, so it only runs with --yes.
Usage: python3 -m evaluation.record_real_samples --yes [agent ...]
"""
import json
import os
import sys
import tempfile
import time

from gateway.claude_cli_model import ClaudeCliModel
from web_console.console_api import Console
from web_console.department_scenarios import demo_for
from wiring.build_company_os import ALL_AGENTS

OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_console", "real_model_samples.json")
CEO = "P01"
# Client requests has no console demo yet: its daily round on the day the stuck request is first detectable.
EXTRA_DEMOS = {"client_requests": {"area_id": "C04", "as_of": "2026-10-08", "trigger_kind": "timer", "caller_id": "system"}}


def record(agent, console):
    demo = demo_for(agent) or EXTRA_DEMOS.get(agent)
    if demo is None:
        return {"status": "skipped", "reason": "no demo scenario for this agent"}
    inputs = {k: v for k, v in demo.items() if k in ("as_of", "event_id")}
    trigger, caller = demo.get("trigger_kind", "request"), demo.get("caller_id", CEO)
    started = time.time()
    result = console.cos.run(agent, caller, demo["area_id"], trigger_kind=trigger, inputs=inputs, model="claude-cli")
    payload = console._run_payload(result)
    calls = sum(1 for s in console.cos.memory.run_steps(result.run_id) if s["step"] == "model_call")
    return {"area_id": demo["area_id"], "as_of": inputs.get("as_of"), "inputs": inputs, "trigger_kind": trigger,
            "status": payload["status"], "reason": payload["reason"], "final_text": result.final_text,
            "letters": [{"to": m["to_person_id"], "to_name": m["to_name"], "kind": m["kind"], "text": m["text"]}
                        for m in payload["messages"]],
            "approvals": [{"tool": a.get("tool"), "reason": a.get("reason")} for a in payload["approvals"]],
            "walkthrough": payload["walkthrough"], "calls": calls, "seconds": round(time.time() - started, 1)}


def main(argv):
    if "--yes" not in argv:
        print("This calls real Claude on your plan. Run again with --yes to record.")
        return 1
    agents = [a for a in argv if not a.startswith("--")] or list(ALL_AGENTS)
    console = Console(tempfile.mkdtemp(prefix="real_samples_"), reset=True)
    console.cos.gateway._backends["claude-cli"] = ClaudeCliModel()
    try:
        with open(OUT_PATH) as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {"samples": {}}
    for agent in agents:
        print(f"recording {agent} ...", flush=True)
        try:
            data["samples"][agent] = record(agent, console)
        except Exception as e:  # keep going: one agent failing should not lose the others
            data["samples"][agent] = {"status": "error", "reason": f"{type(e).__name__}: {e}"}
        s = data["samples"][agent]
        print(f"  {s.get('status')} {s.get('reason', '')[:120]} | letters {len(s.get('letters', []))} "
              f"| calls {s.get('calls')} | {s.get('seconds')}s", flush=True)
    data["model"] = "claude-cli (sonnet)"
    data["generated_at"] = time.strftime("%Y-%m-%d")
    with open(OUT_PATH, "w") as f:
        json.dump(data, f, indent=1)
    print("saved", OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
