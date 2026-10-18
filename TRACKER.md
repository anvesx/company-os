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
| Browser check of each role | I2 | Wave 3 |
| Brain inbox reads any document type: Excel and CSV, PDF (with OCR for scans), PowerPoint, Google exports, images. Each fact still links to its exact place (sheet and cell, page and line, slide) | (planned) | Owner's plan, Oct 19. Today: Fathom, Word, email, chat, live calls |

## Done

| Date | What | Ticket |
|---|---|---|
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
| Oct 19 | The web console is only for experiments: to see progress visually and try things out. It is not the final product. | How people will reach the agents (Slack, email or another tool) is still open |
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
| How will people reach the agents in the final product (Slack, email or another tool)? The web console is only an experiment | Pratham |
| Confirm the rule for which recordings go into the brain | Pratham |
| Check how Fathom webhooks work before connecting real data (polling every 10 minutes is the fallback) | Lead |
| Which travel API to use for real fares and bookings | Pratham |
| Add meaning-based search (embeddings) next to topic keywords when real data arrives | Lead |
