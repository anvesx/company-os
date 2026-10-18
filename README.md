# Company OS prototype

A small, working version of the plan in `../agent-harness/harness-decision/harness-decision.html`: our own thin agent runtime, guardrails on the way in and on every action, one company memory, and four agent packs, all running on dummy company data.

**Read in this order:** this file → `TICKETS.md` (how the work was split) → `SPEC.md` (interfaces) → `RESULTS.md` (what we learned).

## Folders

| Folder | What it does |
|---|---|
| `company_data/` | The dummy company: CRM leads, growth calls, SOWs, projects, meetings, Slack, books, store POS. Stands in for the real tools |
| `connectors/` | Reads the company tools for agents, and loads meetings into company memory |
| `company_memory/` | The shared memory: decisions, questions, tasks, runs, run steps, cases, scores. One area per client |
| `triggers/` | What starts a run: a timer, a calendar event, or a person asking |
| `guardrails/` | The way-in check (who asks, may they, budget) and the every-action check (tools, client areas, approvals, outside text) |
| `runtime/` | Our thin agent runtime: the loop that calls the model and runs tools |
| `gateway/` | The AI gateway: the only path to a model. Prompt cache, cost ledger, budgets, fake model |
| `contract/` | Shared types and the 6-function plugin contract; conformance tests any core must pass |
| `lifecycle_kit/` | The steps every agent follows: record, understand, decide, check, act, remember |
| `agents/` | The agent packs: meeting prep, project risk, finance watch, store watch, hiring forecast, delivery progress, client requests, spend advisor |
| `people_surface/` | Where agents reach people: private messages and the approval queue |
| `evaluation/` | Replay exams that score each agent against planted cases |
| `web_console/` | A local website to use and watch the agents: inbox, ask an agent, approvals, runs, memory |
| `tests/` | Unit tests for every folder |

## Run it

From this folder:

```
python3 -m company_data.generate_dummy_data      # build the dummy company
python3 -m unittest discover -s tests -t .       # run all tests
python3 run_demo.py                              # one simulated day: triggers, agents, messages
python3 -m evaluation.run_all_exams              # score every agent
python3 -m web_console.serve                     # open http://localhost:8800
```

Standard library only (Python 3.14). The model is a deterministic fake by default; `gateway/claude_cli_model.py` can use a real model later.
