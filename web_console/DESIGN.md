# Company OS console: design

The console is where people at DevX (growth, HR, finance, CSMs, the CTO) meet their AI colleagues. It should feel like walking onto a team floor where each agent is a colleague with a face, a job and today's work, not like an admin panel. Plain words, calm layout, one memorable element: the agents themselves.

Sources: Anthropic `frontend-design` skill (process, restraint, copy), `ui-ux-pro-max` (contrast, icons, states), `awesome-design-md` (this file's format). See `agent-harness/24x7-agents/research/` for the research note.

## 1. Theme
Light and airy by default, like a bright office. Dark mode follows `prefers-color-scheme` with the same roles. Generous space, few borders, information grouped by whitespace and type, not by boxes.

## 2. Colour roles (CSS variables in `console.css`)
| Token | Light | Use |
|---|---|---|
| `--paper` | `#F5F7F4` | page background (soft sage-white) |
| `--surface` | `#FFFFFF` | raised things only: drawers, message letters, menus |
| `--ink` | `#1B2235` | main text |
| `--ink-soft` | `#5A6378` | secondary text (4.5:1 on paper) |
| `--line` | `#E3E7E1` | the few dividers that remain |
| `--focus` | `#2F6FDE` | focus rings and links |

Status (always with an icon and a word, never colour alone): `--ok #2E7D4F` (done, allowed), `--wait #8A5CF6` (held, waiting for a person), `--warn #B26B00` (flag), `--stop #C53030` (refused, denied), `--calm #6B7489` (quiet day).

**Agent colours** (each agent's identity; used on its avatar, its name and the thin edge of its messages, nowhere else):
meeting prep `#6D5BD0` violet · project risk `#D97706` amber · finance watch `#1F8A5B` green · store watch `#C2417A` rose · hiring forecast `#2F6FDE` blue · delivery progress `#0E8C8C` teal · client requests `#E0662B` orange · spend advisor `#0F766E` deep green.

## 3. Type
- Headings: **Bricolage Grotesque** (600 to 700), loaded from Google Fonts with `system-ui` fallback. Friendly, a little playful, readable.
- Everything else: **Instrument Sans** (400, 500, 600), fallback `system-ui, sans-serif`.
- No monospace except ids inside small inline code. Agent messages are set in the body font, like a letter.
- Scale (px): 13 small, 15 body, 17 lead, 20 h3, 26 h2, 36 h1. Line height 1.55 body, 1.2 headings. Text columns max 70 characters.
- Sentence case everywhere. No all-caps labels, no tracked eyebrows.

## 4. Components and states
- **Agent avatar**: a soft rounded-square (radius 14px) filled with the agent colour, holding a simple white line icon for its job (calendar, pulse, rupee coin, storefront, people, git branch, key, pie chart). Sizes 32, 48, 88. Beside it: the agent's name and one-line job. This is the one bold element.
- **Agent profile card** (Agents page): large avatar, name, "What I watch", "When I act", "Who I tell", "What I never do", today's status ("Quiet today", "Told Kabir about 2 flags", "Waiting for your approval"), and a "Run me now" button.
- **Letter** (a message an agent sent): white surface, 3px left edge in the agent colour, header row "Project risk → Kabir Shah · flag" with avatar and time, then the text. Lines starting with "Evidence:", "Why it matters:", "Next step:" get a bold label; numbered findings become a list. Long letters collapse after 8 lines with "Show the full message".
- **Status chip**: icon + word: ✓ Done, ⏸ Waiting for approval, ⚑ Flag, ✕ Refused, ◌ Quiet. Shape: pill, 13px, tinted background of the status colour at 12%.
- **Run story** (the six steps): a vertical timeline. Each step: a small circle with its icon on a thin line, a plain title ("Read the books", "Found 1 duplicate invoice", "Decided what to say", "Checked before sending", "Told Anjali, 1 action waits for approval", "Saved to memory"), one or two lines of detail, and guardrail verdicts as chips (✓ allowed, ✕ denied with the reason, ⏸ held). Quiet runs show "Nothing new, so no model call" and stop.
- **Approval**: a letter-like card with what the agent wants to do in one sentence, why, and two buttons: "Approve" (primary) and "Deny". After a click, the card animates to its result ("Approved by Anjali, done" or "Denied") in place. If the viewer may not approve, say who can.
- **Drawer**: running a scenario opens a right-side drawer (480px, full height on mobile) that shows the run story and the letters it produced. Slide in 200ms; respect reduced motion.
- **Buttons**: primary = ink background, white text, radius 10px; secondary = transparent with ink text and a 1px line. Labels say exactly what happens: "Run finance watch", "Approve", "Go to next day". No arrows appended to labels.
- **Empty states**: one sentence and one action. Inbox empty: "Nothing for Meera yet. Run the hiring forecast to see what HR receives." with a button.

## 5. Layout and spacing
- 4px base; spacing steps 4, 8, 12, 16, 24, 32, 48, 64.
- Left rail (232px): the product name "Company OS", then one link per page the viewed role may open (Home first), then the Dark mode switch. On small screens the rail becomes a bottom sheet menu.
- Top bar: the page title on the left. On the right the role switcher: a chip with the first name and role ("Ammar · Admin"), opening a menu of exactly three people (Ammar Admin, Akbar CSM, Anthony Growth). Admin also sees the demo date, "Go to next day", the agents on or paused switch and "Reset demo".
- Content max width 1120px, left aligned.
- Family colours: Meeting prep violet `#6D5BD0`, Finance green `#1F8A5B`, Company brain teal `#0E8C8C`. Each page card on Home gets the colour of its family on its left edge.

## 6. Pages
- Pages are plug-ins (contract C8). The shell lists a role's pages from `/api/console/pages`, loads each page script and calls `render`. A page whose module is not built yet shows a small "not ready yet" card.
- **Home**: a greeting, the privacy line ("Nothing here is used to rate people."), then one card per allowed page from its `homeCard`.
- **Approvals**: approval cards for held actions this person may decide (bookings: Admin only). Decided ones fold into a "Decided" list.
- **Runs** (Admin): counts, then a table (agent, area, result chip, time, cost, cache hits). A click opens the six-step run story in the drawer.
- Every page shows only what the viewed person may open. Hidden things are left out, and the server refuses them with 403.

## 7. Do and don't
Do: whitespace over borders; one accent per agent; plain verbs; show refusals with the reason in words; keyboard focus rings; 44px touch targets.
Don't: identical boxed cards for every section; gradients; all-caps or tracked labels; monospace message bodies; emoji as icons; "→" in button labels; motion on page load; colour-only status.

## 8. Responsive
Check at 375, 768, 1024 and 1440px. Below 900px the rail collapses to a menu button and the drawer becomes full screen.

## 9. Icons
Inline SVG, 1.75px stroke, 20px, Lucide-style, drawn in `shell.js` as a small icon map (calendar, pulse, coin, store, users, branch, key, check, x, pause, flag, inbox, home, book, settings, chevron, play, search).
