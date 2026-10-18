# Tracker

What is done, what is in progress, what is next, and the decisions made. Update this file with every change. Newest first in each section. Times are IST.

Last updated: Oct 19, 2026.

## In progress

| What | Ticket | Notes |
|---|---|---|
| Integration: one full run through the real brain pipeline, compaction hook in the agent loop, real-Sonnet samples, fixes found in Wave 2 | I1 | Started Oct 19 |

## Next

| What | Ticket | Notes |
|---|---|---|
| Split into `core/` and `control_plane/` folders, with a boundary test | R2 | After I1 |
| Browser check of each role | I2 | Wave 3 |
| Control plane server, to run for real: a scheduler for timers, a webhook for new Fathom recordings, a job queue with retries, approvals and letters through Slack or email, hosting | (planned) | After the demo. Today the control-plane logic runs on a simulated clock with dummy data |
| Approvals that expire after a set time (idea from Grok Bot) | (idea) | Not planned yet |
| Brain inbox reads any document type: Excel and CSV, PDF (with OCR for scans), PowerPoint, Google exports, images. Each fact still links to its exact place (sheet and cell, page and line, slide) | (planned) | Owner's plan, Oct 19. Today: Fathom, Word, email, chat, live calls |

## Done

| Date | What | Ticket |
|---|---|---|
| Oct 19 | Research: Grok Bot inside vs Company OS. Direction sound; ideas to copy: approvals that expire, teach mode, limits on routines (`docs/research/grok-bot-internals-vs-company-os.md`) | (research) |
| Oct 19 | Wave 2: Cleaner, Extractor, Linker and Playbook writer (the brain's four agents); CSM project brief; Growth deal brief; live call helper; finance v2 with real cheaper flights and hotels and round-trip booking; console shell with three people. 526 tests pass; all 10 exams pass | S1 to S7 |
| Oct 19 | Wave 1 integration: full suite green (410 tests); exams pass for meeting prep, finance watch, spend advice and travel booking; names changed to Ammar, Akbar and Anthony; job title "R&D lead" renamed to CTO | (lead) |
| Oct 19 | Repo created at `anvesx/company-os` (private) | |
| Oct 19 | Compaction in `runtime/compaction.py`, adapted from dsh commit `687f282` (MIT) | R1 |
| Oct 19 | Travel booking agent: best 3 options by policy; booking waits for Admin approval. Exam 8 of 8 | F4 |
| Oct 19 | Brain store: inbox, readers, router, search, unconfirmed items, meeting filter | F2 |
| Oct 19 | Three roles enforced on the data: Admin, CSM, Growth | F3 |
| Oct 19 | Dummy data v2: 31 sources (Fathom, Word, email, chat) in Hindi, English and Hinglish; 4 past and 2 live deals; 105 answer-key items | F1 |
| Oct 19 | Only the finance and meeting prep agents stay. The other five agents moved to `experiments/` | X0 |
| Oct 19 | Plan and tickets for v2 | `PLAN_v2.md`, `TICKETS_v2.md` |
| Oct 18 | v1 prototype: 8 agents, guardrails, company memory, web console, exams | `RESULTS.md` |

## Decisions

| Date | Decision | Why |
|---|---|---|
| Oct 19 | Split the code into `core/` (core harness) and `control_plane/`, with `contract/` between them and a test that the core never imports the control plane | Makes the two layers visible and keeps the core swappable (for dsh or another harness) |
| Oct 19 | Explain Company OS as two layers: the core harness (how one agent thinks and acts during a run) and the control plane (how the company runs many agents safely, always on) | The core harness is small; most of the value is in the control plane |
| Oct 19 | All research goes in the repo, in `docs/research/` | One place for the team to read why decisions were made |
| Oct 19 | Keep Python for the core (brain, agents, guardrails, document readers). If we need dsh features later, run dsh as a separate TypeScript service behind our contract. | Python was inherited from the first prototype, not chosen on purpose; checked Oct 19. Python needs no packages and is strong for documents (Excel, PDF, OCR). dsh is TypeScript, so we rewrite its ideas in Python. Revisit if the maintaining team mostly writes TypeScript |
| Oct 19 | The web console is only for experiments: to see progress visually and try things out. It is not the final product. | How people will reach the agents (Slack, email or another tool) is still open |
| Oct 19 | Count compaction as one of the 7 dsh features our base has, like the other six | Code we take from dsh is our own code too: use dsh directly, or write our own |
| Oct 19 | Every Fathom recording goes into the brain automatically. Nobody approves anything. Unsure facts are stored as "unconfirmed". When two statements conflict, the newer one wins and the older one is marked "superseded". | A required review step would be a hassle, and people would stop doing it |
| Oct 19 | Only these recordings go in automatically: a meeting with at least one attendee from outside DevX, or a meeting whose title matches a known client. An internal meeting goes in only if `#brain` is in its title. | Keeps one-on-ones and HR talks out of company memory. Default; the owner may change it |
| Oct 19 | Three roles: Admin (Ammar Khan), CSM (Akbar Ali), Growth (Anthony Fernandes). The console shows one person per role. | Show each view from one person's point of view |
| Oct 19 | Growth reads lessons from past clients with names removed, never another client's raw transcripts | Keeps client data separate |
| Oct 19 | Meeting prep and finance are each a family of three small agents | Each agent gets only its own tools. For example, travel booking cannot read the books |
| Oct 19 | Keep our own base. It has the 7 dsh features we need, compaction included. For more later (browser control, subagents, skills, a web app), use dsh directly or write our own code. | Code is a commodity. The value is our memory, guardrails and data. dsh is MIT licensed |
| Oct 19 | Keep only the finance agent (with travel booking) and the meeting prep agent | Focus. Finance watch was the first pick of 56% in the simulated focus group |
| Oct 19 | The finance agent shows the actual cheaper flights and hotels (airline, flight number, time, fare; hotel name, rate) | "A cheaper option existed" is not useful on its own |
| Oct 18 | Our own thin runtime, not dsh, as the base | Our agents need 7 of dsh's 25 features. What they need most is not in dsh |
| Oct 18 | The learning loop is designed but not built yet | Owner's call |

## Open questions

| Question | Owner |
|---|---|
| Which language does the team that will maintain Company OS mostly write? If TypeScript, revisit the Python decision | Pratham |
| How will people reach the agents in the final product (Slack, email or another tool)? The web console is only an experiment | Pratham |
| Confirm the rule for which recordings go into the brain | Pratham |
| Check how Fathom webhooks work before connecting real data (polling every 10 minutes is the fallback) | Lead |
| Which travel API to use for real fares and bookings | Pratham |
| Add meaning-based search (embeddings) next to topic keywords when real data arrives | Lead |
