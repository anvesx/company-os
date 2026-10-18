# web_console

**Role in the harness:** Web console: a local website where non-engineers use the real agents on the dummy company, read their messages, approve actions and see how each run worked.

## Run it

From `company-os/`:

```
python3 -m web_console.serve [--port 8800] [--reset]
```

Open http://localhost:8800. Standard library only. One process holds one `CompanyOS` built with `build_company_os(state_dir="web_console/state")`.
The simulated date and pause switch are saved in the state folder. `--reset` (or the Reset button) starts clean.
Agents that are not installed yet (for example a pack still being built) show as "being built". Real Claude is off (a note in the rail): it would use your Claude plan, so ask first.

## What each screen does

The look, colours and rules are in `DESIGN.md`. Pages (left rail; a menu button on phones):

| Screen | What it does |
|---|---|
| Top bar | Demo date and **Go to next day**, the "Viewing as" person (picker), the agents on or paused switch, **Reset demo** |
| Today | Greeting, **Ask finance** (for CEO, finance lead and R&D lead), things that need you (approvals), what your agents did (click for the run story), scenario tiles for your role, ask in words, a 5-step tour |
| Agents | One profile card per agent from the API (a new agent appears by itself, grey until it has a colour): what it watches, when it acts, who it tells, what it never does, today's status, **Run me now** |
| Departments | Finance, Growth, CSMs, CTO. Finance also has the **Ask finance** box. Each situation has **Try it**; the CTO tab also shows cost, cache and guardrail decisions |
| Inbox | Letters for the viewed person, newest first, filter by agent |
| Approvals | Held actions with Approve and Deny, checked against who may decide. Decided ones fold into a list |
| Runs | Table of all runs; click one for the run story |
| Company memory | Items and saved cases by client area, grouped by kind. Areas the person cannot see are locked |

**What each role sees.** The console offers only what the "Viewing as" person may do. The rules are never copied: they come from `policy.may_start`, `policy.may_approve` and `directory.client_access` (`/api/permissions?person=`).

| Role | Agents, Departments, Run forms |
|---|---|
| CEO | All agents, all department tabs, all areas |
| R&D lead | Agents the policy allows, all areas, the CTO tab |
| CSM, project lead | Meeting prep, only their own clients |
| Growth | Meeting prep, own clients |
| Finance lead | Finance watch and spend advisor |
| Engineer, designer, HR | No agents to start |

Approvals lists only what the person may decide. The CTO tab keeps one "See how a refusal looks" example. It runs as a named engineer on purpose and says so. A hidden action called through the API anyway gets HTTP 403 and an error ("Nothing was run"); the way-in check stays as the safety net.

Running anything opens the right-hand drawer: a vertical timeline of the run in plain steps with guardrail verdict chips, then the letters produced and any approval to decide.

The drawer also shows every letter the run wrote ("to Neha Iyer, flag") and, when `real_model_samples.json` exists, a "See the real Claude version" toggle (also on the agent cards). That file is recorded once with real Claude and is read as it is. If it is missing, nothing is shown.

People, bandwidth and allocation are not rebuilt here. DevX already has them at console.devxlabs.ai/employees.

## Ask finance

A text box ("Ask about company spending, for example: where is our travel money going?") with three quick picks (Travel this quarter, Where can we save?, Cost by category). It shows only for people who may start `spend_advisor` (`agents` in `/api/permissions`, also `can_ask_finance`). It runs the agent as the viewed person, as of the demo date, and opens the answer letter and the run story in the drawer. The Finance page also has the tile "Where can we save on travel?".

## New endpoints

`POST /api/finance/ask` (`person_id`, `text`): runs `spend_advisor`; 403 and "Nothing was run" when the person may not start it; a plain error for an empty question.

`GET /api/permissions?person=`, `GET /api/real_samples`. `GET /api/scenarios?person=` lists only the scenarios that person may run, and `POST /api/scenarios/run` takes `person_id` and runs as that person.

## Files in this folder

| File | What it does |
|---|---|
| `serve.py` | Local web server: static files plus the JSON API. Thin; all logic is in `console_api.py`. |
| `console_api.py` | The console as plain Python: run agents, ask in words, approvals, runs, memory, cost, next day, pause, and `/api/today` (the viewer's home page: approvals, activity feed, scenario picks, agent status). |
| `department_scenarios.py` | The "Try it" scenarios for each department (agent, caller, client, dates). |
| `run_walkthrough.py` | Turns a run's logged steps into the six-step story in plain words, with guardrail verdicts. |
| `permissions.py` | What one person may do: agents, areas, scenarios, department tabs, Ask finance. Built from the guardrail policy and the people directory. |
| `connector_calls.py` | Calls a connector read tool outside an agent run, for the pages above. |
| `real_samples.py` | Loads `real_model_samples.json` (the recorded real-Claude runs), or nothing when it is missing. |
| `agent_cards.py` | Plain-language text for each agent card, and role names. An agent with no card gets a grey one built from its README. |
| `DESIGN.md` | The visual design: colours, type, components, pages, do and don't. |
| `static/index.html` | The one page: rail, top bar, drawer shell. |
| `static/console.css` | Styling from DESIGN.md, light and dark, responsive. |
| `static/console.js` | The page logic in plain JavaScript, with inline SVG icons. Only external call: Google Fonts (Bricolage Grotesque, Instrument Sans) with system fallbacks. |
| `state/` | Created when the server runs: the console's own memory and message files. Not used by tests. |

The Progress, Client requests and HR pages moved to `experiments/web_console_v1/`. `routes/` and `static/pages/` are the place for new page plug-ins.
