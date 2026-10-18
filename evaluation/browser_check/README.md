# Browser check of each role

Date: 19 Oct 2026 (demo date). Server: `python3 -m web_console.serve --port 8802`, brain seeded as normal. Browser: Chrome, 1440 px wide, light mode, driven through the Chrome DevTools bridge. No console errors and no failed requests were seen in the walk.

## Results

| Person | Page | Works? | What was seen | Screenshot |
|---|---|---|---|---|
| Ammar (Admin) | Home | Yes | Cards for Check, Deals, Approvals, Runs. Demo controls shown. | `admin_home.png` |
| Ammar | Brain inbox | Yes | Hinglish text added. Cleaner (1 not translated), Extractor (1 unconfirmed), Linker ran. Playbook writer showed "waiting" (no lesson to write). | `admin_brain.png`, `admin_brain_hinglish.png` |
| Ammar | Check | Yes | Review items with original and English lines. | `admin_review.png` |
| Ammar | Meeting prep | Yes | Three upcoming meetings with unconfirmed counts. | `admin_meeting_prep.png` |
| Ammar | Deals | Yes | All four deals and the playbook library. | `admin_deals.png` |
| Ammar | Live call | Yes | Both calls offered (Anthony and Akbar). | `admin_live.png` |
| Ammar | Finance | Yes | 18 trip cards. TR016 shows cheaper hotels, TR018 cheaper flights. | `admin_finance.png`, `admin_finance_trip.png` |
| Ammar | Travel | Yes | Request for 2 people, Mumbai to Pune, with return. Best 3 round trips and best 3 hotels, held for an Admin. | `admin_travel.png`, `admin_travel_request.png` |
| Ammar | Approvals | Yes | Pending "Book travel" card. Approve gave booking `SIM-C947AD6C`; Travel then showed "Booked". | `admin_approvals_pending.png`, `admin_approvals_done.png` |
| Ammar | Runs | Yes | Run table. One run opened step by step in the side panel. | `admin_runs.png`, `admin_runs_story.png` |
| Akbar (CSM) | Home, Brain inbox, Check | Yes | Own areas only. | `csm_home.png`, `csm_brain.png`, `csm_review.png` |
| Akbar | Meeting prep | Yes | MedBridge brief (PR05): 29 source links, "Changed on 2026-10-10" line, "2 unconfirmed items". | `csm_meeting_prep.png`, `csm_meeting_prep_brief.png` |
| Akbar | Live call | Yes | LC02 played. Contradiction card: reminders agreed as WhatsApp on Sep 30, client now says SMS. Call summary and run link shown. | `csm_live_contradiction.png` |
| Akbar | Travel | Yes | Sees only his own requests. | `csm_travel.png` |
| Akbar | Approvals | Yes | "Nothing waits for you." | `csm_approvals.png` |
| Anthony (Growth) | Home, Brain inbox, Check | Yes | Own areas only. | `growth_home.png`, `growth_brain.png`, `growth_review.png` |
| Anthony | Deals | Yes | Own deals only. CareNest brief: 2 similar clients, 3 ideas, 3 risks, 7 kickoff questions. | `growth_deals.png`, `growth_deal_brief.png` |
| Anthony | Live call | Yes | LC01 played. Six suggestions (gaps and follow-ups) and a summary. | `growth_live.png` |
| Anthony | Travel | Yes | Own requests only. | `growth_travel.png` |

## Forbidden checks

| Check | Result |
|---|---|
| Akbar nav has no Finance or Runs | Pass |
| Anthony nav has no Finance or Runs | Pass |
| Forced `#finance` and `#runs` in the address bar (both roles) | Pass, sent back to Home (`forbidden_growth_forced_finance.png`) |
| `curl` CSM to `/api/finance/findings` | 403 |
| `curl` Growth to `/api/meeting_prep/upcoming` | 403 |
| `curl` Growth POST `/api/meeting_prep/brief` | 403 |
| `curl` CSM POST `/api/finance/ask`, CSM GET `/api/console/runs`, Growth GET `/api/finance/trips` | 403 |

## Fixed in this check

1. **Approvals showed "Denied" after Approve.** `api()` in `web_console/static/shell.js` overwrites `status` with the HTTP code, so the card never saw "approved". Now it uses the button pressed.
2. **Side panel stayed open across pages and people.** An Admin run story still covered the page after switching to Akbar. `render()` in `shell.js` now closes the panel.
3. **"1 person" was refused.** `agents/finance/travel_booking/request_parser.py` accepted "persons" but not "person". Now both work.
4. **Refused travel request had an empty title ("to , , people").** `web_console/static/pages/travel.js` now shows the text the person typed.

## Fix list (not fixed)

- Home says "112 runs, $0.0000 spent" and "0 model calls", but run rows show costs such as $0.0106. Check how the cost total is added up. Unverified cause.
- Meeting prep "Changed decisions" lists three decisions with no "Changed on" line or source. Check whether they are really replaced decisions.
- The MedBridge brief for Akbar quotes "Growth call" lines (a deal transcript). Check that this is allowed by the memory scopes.
- Travel shows "1 people" for one traveller.
- The Travel nav item uses the robot icon.
- Not checked: 390 px width and dark mode (the ticket I2 asks for both).
