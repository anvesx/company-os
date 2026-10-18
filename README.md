# Company OS

Company OS is a team of always-on AI agents for a services company. The agents share one company brain, follow company guardrails, and ask a person before anything risky.

This repo is a working prototype. It runs on dummy company data, so anyone can run it and its tests on a laptop. Real company systems are not connected yet.

## What it does

**Two agents:**

| Agent | What it does | Who uses it |
|---|---|---|
| Finance agent | Watches invoices, payments, budgets and travel spend. For every past trip it shows the real cheaper flight and hotel that were available. It also books new trips: it finds the best 3 options by travel policy, and the booking waits for an Admin's approval. | Admin |
| Meeting prep agent | Before a client call, it prepares the CSM with the questions to ask, open requirements and blockers. Before a deal call, it prepares Growth with lessons from similar past clients, ideas to close the deal and a kickoff checklist. During a live call, it suggests what to ask next. | CSM, Growth |

**One company brain.** Meeting transcripts (Hindi, English or Hinglish), Word documents, emails and chats go into one company memory automatically. Four internal agents work on every source:

1. **Cleaner** turns the text into clean English and keeps the original.
2. **Extractor** finds decisions, requirements, blockers, questions, commitments and money.
3. **Linker** attaches each fact to the right project or deal, and marks old decisions as replaced.
4. **Playbook writer** keeps one lesson record per past client, with names removed.

Every fact links back to the exact line it came from. Nobody has to approve anything. A fact the brain is not sure of is stored with the label "unconfirmed".

**Three roles.** Each person sees only what their role allows. The rule is enforced on the data, not only hidden in the screen.

| Role | Example person | Sees |
|---|---|---|
| Admin | Ammar Khan, CEO | Everything |
| CSM | Akbar Ali | Their own client projects |
| Growth | Anthony Fernandes | Their own deals and the past-client lessons library |

## How it is built

- **Our own thin runtime** (`runtime/`), not a ready-made agent harness. Our agents need about 6 of the 25 features in DeepSeek's harness (dsh). We copy parts from dsh when we need them. For example, compaction is adapted from dsh, under its MIT licence (see `THIRD_PARTY_NOTICES.md`).
- **Code finds, the model explains.** Plain code finds the problems. The AI model only writes the explanation and the next step. A quiet day makes no model call.
- **Check before act.** Every action passes the guardrails before it reaches a person.
- **A fake model by default.** Tests and exams use a deterministic fake model. Real Claude (Sonnet) is an option through the `claude` CLI.

## Folders

| Folder | What it holds |
|---|---|
| `agents/` | The two agents: `finance/` and `meeting_prep/` |
| `company_brain/` | The company brain: inbox, store, search and its internal agents |
| `company_memory/` | The memory database: one area per client, an append-only run log |
| `company_data/` | The dummy company: people, clients, projects, deals, trips, transcripts |
| `connectors/` | Read-only tools that agents use to read company data |
| `guardrails/` | The checks: who may start a run, what each action may do, the three roles |
| `runtime/` | The agent loop, tool registry and compaction |
| `gateway/` | The model gateway: prompt cache, cost ledger, fake model, real Claude |
| `lifecycle_kit/` | The steps every agent run follows: record, understand, decide, check, act, remember |
| `triggers/` | What starts a run: a timer, a calendar event, a new source, a person asking |
| `people_surface/` | Private letters and approval requests to people |
| `web_console/` | The web console for each role |
| `evaluation/` | Replay exams that score each agent |
| `experiments/` | Earlier agents kept for later (project risk, store watch, hiring forecast, delivery progress, client requests) |
| `tests/` | All tests |

## Run it

Needs Python 3.11 or later. No packages to install.

```
python3 -m company_data.generate_dummy_data      # build the dummy company
python3 -m unittest discover -s tests -t .       # run all tests
python3 -m evaluation.run_all_exams              # score every agent
python3 run_demo.py                              # one simulated day
python3 -m web_console.serve                     # then open http://localhost:8800
```

## Status

Work in progress. See `TRACKER.md` for what is done, what is in progress, what is next, and the decisions made. The full plan is in `PLAN_v2.md`, and the build tickets are in `TICKETS_v2.md`.
