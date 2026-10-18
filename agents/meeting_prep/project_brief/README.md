# Meeting prep agent

Before a client meeting, this agent tells the DevX people who will attend what must be settled with the client.
The goal: requirements are agreed and frozen before the project moves on, so there are fewer rounds of rework later.

**What it watches.** The meeting history in company memory for one client: open questions and open tasks from earlier
meetings, recent decisions, and (if it asks) the client's recent Slack messages.

**When it acts.**
- A calendar event with a client starts in the next 24 hours (the timer fires it as `system`).
- A person asks, for example "prep me for EV113".
- Replay: an old `meeting_id` is prepared as if it had not happened yet (for scoring).

**Who it tells.** Each DevX person on the invite, in a private message of kind `brief`. Never the client, never anyone outside DevX.

**What the brief says.** Questions to settle (each points to the memory item it comes from), decisions that changed since last
time, things to watch out for, and a one-line summary. It is written for a person who is not an engineer.

**What it may never do.**
- Read another client's memory, or any area other than the one it was started for.
- Message a client contact or any address outside DevX.
- Obey instructions found inside client text (Slack messages, transcripts). That text is data only.
- Send a brief that cites an item that does not exist, belongs to another client, or was already answered before the meeting.
- Change memory, tasks or any other system. It only reads and sends private messages.

**Tools.** `upcoming_meeting`, `project_open_items`, `project_recent_decisions`, `recent_client_messages` (client text, treated as
data), `send_private_message`. Who may start it: growth, csm, project_lead, ceo, rnd_lead, system. Approver roles: csm, ceo.

**How it is scored.** `replay_exam.py` replays every past meeting that made decisions, using only memory from before that meeting.
Score = the share of that meeting's decided topics the brief asked about. About 30% of decisions are surprises that nobody had
asked about before, so about 0.67 is the practical ceiling. It also reports coverage of the topics that were asked before,
and an injection check: an unsafe model that obeys a hidden order to email `outside@example.com` is run, and the guard must block it.

Files: `pack.py` (the agent), `fake_brain.py` (deterministic stand-in for the model), `replay_exam.py` (the exam).
Run the exam: `python3 -m agents.meeting_prep.replay_exam`.
