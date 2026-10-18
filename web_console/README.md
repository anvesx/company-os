# web_console

**Role in the harness:** The console shell: a local website with a three-person role switcher, plug-in pages, Home, Approvals and Runs. Every call is checked on the server.

**Note:** the web console is only for experiments, to see progress visually and try things out. It is not the final product.

## Run it

From `company-os/`:

```
python3 -m web_console.serve [--port 8800] [--reset]
```

Standard library only. One process holds one `CompanyOS`. The demo date and pause switch are saved in `state/`. `--reset` starts clean.

## People and pages

The role switcher offers exactly three people (`DEMO_PEOPLE` in `guardrails/role_scopes.py`): Ammar (Admin, P01), Akbar (CSM, P05), Anthony (Growth, P03).
Each role sees only the pages in `role_scopes.PAGES`. Every API call carries `viewer`; the server refuses an unknown viewer or a page the role may not open with 403 and runs nothing.

| Role | Pages |
|---|---|
| Admin | Home, Brain, Review, Meeting prep, Deals, Live call, Finance, Travel, Approvals, Runs |
| CSM | Home, Brain, Review, Meeting prep, Live call, Travel, Approvals |
| Growth | Home, Brain, Review, Deals, Live call, Travel |

## Plug-ins (contract C8)

Add a page with `routes/<page>_routes.py` (`PAGE`, `routes(console)`) and `static/pages/<page>.js` (and `.css`). The page id must be in `role_scopes.PAGES`. A missing, broken or unknown module is skipped. A page with no module yet shows a placeholder card. A plug-in cannot replace a shell route.

## Shell endpoints

`GET /api/console/people`, `GET /api/console/pages`, `GET /api/run?id=` (run story), `GET /api/console/home`, `GET /api/console/approvals`, `POST /api/console/approvals/decide`, `GET /api/console/runs`. Admin-only demo controls: `POST /api/console/next_day`, `pause`, `resume`, `reset`; `GET /api/console/state`.
Approving a booking calls `booking_after_approval`. Next day also fires `InboxTrigger` when `triggers.inbox_trigger` imports.

## Files

| File | What it does |
|---|---|
| `serve.py` | Local web server: static files plus the JSON API. |
| `console_api.py` | The `Console`, plug-in discovery and the checked `route()`. |
| `routes/core_routes.py` | The shell's own routes. |
| `run_walkthrough.py` | Turns a run's logged steps into the six-step story. |
| `DESIGN.md` | Colours, type, components, pages. |
| `static/index.html`, `shell.js`, `console.css` | The page, its logic and its styling (light by default, dark toggle). |
| `static/pages/` | Page scripts from the plug-ins. |

The v1 pages and their helpers are in `experiments/web_console_v1/`.
