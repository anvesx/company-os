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

- **Our own thin runtime** (`core/`), not a ready-made agent harness. Our agents need 7 of the 25 features in DeepSeek's harness (dsh): the agent loop, retries, a cache-safe prompt order, a tool pipeline with checks, a session log, output caps and compaction. Our base has all 7. When we need more later, such as browser control, subagents or skills, we can use dsh directly or write our own code. Compaction follows dsh's design, under its MIT licence (see `THIRD_PARTY_NOTICES.md`).
- **Code finds, the model explains.** Plain code finds the problems. The AI model only writes the explanation and the next step. A quiet day makes no model call.
- **Check before act.** Every action passes the guardrails before it reaches a person.
- **A fake model by default.** Tests and exams use a deterministic fake model. Real Claude (Sonnet) is an option through the `claude` CLI.

## Folders

| Folder | What it holds |
|---|---|
| `core/` | The core harness: agent loop, tool registry, compaction, model gateway, prompt cache, fake model, real Claude, cost ledger |
| `control_plane/` | The control plane: `guardrails/`, `company_memory/`, `company_brain/`, `people_surface/`, `triggers/`, `connectors/` |
| `contract/` | The boundary between the core and everything else |
| `agents/` | The two agents: `finance/` and `meeting_prep/` |
| `company_data/` | The dummy company: people, clients, projects, deals, trips, transcripts |
| `lifecycle_kit/` | The steps every agent run follows: record, understand, decide, check, act, remember |
| `wiring/` | Builds the company OS: joins the core, the control plane and the agents |
| `web_console/` | An experimental web console for each role (see the note below) |
| `evaluation/` | Replay exams that score each agent |
| `experiments/` | Earlier agents kept for later (project risk, store watch, hiring forecast, delivery progress, client requests) |
| `tests/` | All tests |

The core never imports `control_plane/`, `agents/`, `lifecycle_kit/`, `web_console/` or `company_data/`. `tests/test_layer_boundary.py` checks this.

## Run it

Needs Python 3 (tested with 3.14). No packages to install.

```
python3 -m company_data.generate_dummy_data      # build the dummy company
python3 -m unittest discover -s tests -t .       # run all tests (541 pass, under 2 minutes)
python3 -m evaluation.run_all_exams              # 10 exams, one per agent
python3 run_demo.py                              # one simulated day
python3 -m web_console.serve                     # then open http://localhost:8800
```

**The 10 exams.** Meeting prep (project brief), deal brief, live call helper, finance watch, spend advisor, travel booking, and the four brain agents (Cleaner, Extractor, Linker, Playbook writer). All pass.

**The honest exam.** Three exams read the brain: project brief, deal brief and live call helper. `run_all_exams` runs each of them twice and prints both results side by side:

- *Seeded from answer key:* the brain is filled directly from the answer keys.
- *Through real pipeline:* the brain is filled by the real pipeline. All 31 sources go through the inbox, Cleaner, Extractor, Linker and Playbook writer, with no help from the answer keys.

Both results are saved in `evaluation/latest_scores.json`. The pass bars are the same for both.

**Real Claude samples (optional, uses your Claude plan).** `python3 -m evaluation.record_real_samples --yes` records five Sonnet samples (project brief, deal brief, Cleaner on a Hinglish source, live call end summary, finance trip card) in `web_console/real_model_samples.json`. It makes about 5 to 7 model calls. Without `--yes` it does nothing.

**About the web console.** The web console is only for experiments. It lets us see the progress visually and try things out. It is not the final product, and it is not a decision about how people will use Company OS. The real way people reach the agents (for example Slack, email or another tool) is still open.

## Status

Work in progress. See `TRACKER.md` for what is done, what is in progress, what is next, and the decisions made. The full plan is in `PLAN_v2.md`, and the build tickets are in `TICKETS_v2.md`. The plan for running agents 24/7 is in `PLAN_24x7.md`.
