"""Data for the Client requests page: a board per project, and the form that starts the client_requests agent."""
from agents.client_requests.pack import STUCK_DAYS
from agents.client_requests.request_playbooks import KINDS
from connectors.client_request_tools import client_request_tools

from .connector_calls import read_tool

COLUMNS = [("asked", "Asked"), ("reminded", "Reminded"), ("stuck", f"Stuck ({STUCK_DAYS} days or more)"),
           ("granted", "Granted"), ("verified", "Verified"), ("failed", "Failed check")]
SAFETY_LINE = "Agents never ask for passwords in chat; client messages wait for the CSM's approval."
BOARD_ROLES = ("csm", "project_lead", "ceo", "rnd_lead", "engineer", "designer")
DETAILS_MAX = 600


def _kind_label(kind):
    return kind.replace("_", " ").capitalize()


def visible_projects(console, person_id):
    """Projects whose board this person may see: all for CEO and R&D lead, own for CSM and lead, theirs for makers."""
    role, conn = console._role(person_id), console.cos.data_conn
    if role not in BOARD_ROLES:
        return []
    allowed = console._allowed_areas(person_id)
    rows = conn.execute("SELECT p.*, c.name AS client_name FROM projects p JOIN clients c ON c.client_id = p.client_id "
                        "ORDER BY p.project_id").fetchall()
    if role in ("csm", "project_lead"):
        rows = [r for r in rows if person_id in (r["csm_id"], r["lead_id"])]
    elif role in ("engineer", "designer"):
        mine = {r[0] for r in conn.execute(
            "SELECT project_id FROM tasks WHERE assignee_id = ? UNION SELECT t.project_id FROM time_logs l "
            "JOIN tasks t ON t.task_id = l.task_id WHERE l.person_id = ?", (person_id, person_id))}
        rows = [r for r in rows if r["project_id"] in mine]
    return [{"project_id": r["project_id"], "name": r["name"], "client_id": r["client_id"],
             "client_name": r["client_name"]} for r in rows if r["client_id"] in allowed]


def _column(r):
    if r["status"] == "granted":
        return "granted"
    if r["status"] == "verified":
        return "verified"
    if r["status"] == "failed_verification":
        return "failed"
    return "stuck" if (r["days_open"] or 0) >= STUCK_DAYS else "reminded" if r["status"] == "reminded" else "asked"


def request_cards(console, person_id, project_ids=None):
    """One card per request, for the projects this person may see (optionally only some of them)."""
    as_of, tools, conn = console.cos.clock.today, client_request_tools(console.cos.data_conn), console.cos.data_conn
    task_title = {r["task_id"]: r["title"] for r in conn.execute("SELECT task_id, title FROM tasks")}
    cards = []
    for p in visible_projects(console, person_id):
        if project_ids is not None and p["project_id"] not in project_ids:
            continue
        args = {"project_id": p["project_id"]}
        reply = read_tool(tools, "open_client_requests", p["client_id"], {**args, "state": "all", "limit": 60, "events": False}, as_of)
        fails = {c["request_id"]: c["detail"] for c in read_tool(
            tools, "access_check_results", p["client_id"], {**args, "days": 120, "result": "fail"}, as_of).get("checks", [])}
        for r in reply.get("requests", []):
            if r["status"] == "cancelled":
                continue
            owner = console.cos.directory.get(r["owner_contact_id"]) if r["owner_contact_id"] else None
            cards.append({"request_id": r["request_id"], "title": r["title"], "kind": r["kind"],
                          "kind_label": _kind_label(r["kind"]), "project_id": p["project_id"], "project_name": p["name"],
                          "status": r["status"], "column": _column(r), "owner_name": owner["name"] if owner else None,
                          "days_open": r["days_open"], "granted_on": r["granted_on"], "reminders_sent": r["reminders_sent"],
                          "secret_in_chat": r["secret_in_chat"], "check_detail": fails.get(r["request_id"]),
                          "blocks": [{"task_id": b["task_id"], "title": task_title.get(b["task_id"], b["task_id"]),
                                      "days": b["days"], "still_blocked": b["still_blocked"]} for b in r["blocked_tasks"]]})
    return cards


def client_requests_board(console, person_id):
    if not console.cos.directory.get(person_id):
        return {"ok": False, "error": "Unknown person."}
    projects = visible_projects(console, person_id)
    out = {"ok": True, "safety": SAFETY_LINE, "projects": projects, "as_of": console.cos.clock.today,
           "columns": [{"id": cid, "title": title, "cards": []} for cid, title in COLUMNS]}
    if not projects:
        out["note"] = ("This board is for CSMs, project leads, the CEO, the R&D lead and the engineers and designers "
                       "who work on a project.")
        return out
    by_col = {c["id"]: c for c in out["columns"]}
    for card in request_cards(console, person_id):
        by_col[card["column"]]["cards"].append(card)
    for col in out["columns"]:
        col["cards"].sort(key=lambda c: -(c["days_open"] or 0))
    out["may_ask"] = bool(console.cos.policy.may_start(console._role(person_id), "client_requests"))
    out["kinds"] = [{"kind": k, "label": _kind_label(k)} for k in KINDS]
    open_tasks = {}
    for r in console.cos.data_conn.execute("SELECT task_id, project_id, title FROM tasks WHERE status != 'done' ORDER BY task_id"):
        open_tasks.setdefault(r["project_id"], []).append({"task_id": r["task_id"], "title": r["title"]})
    for p in projects:
        p["tasks"] = open_tasks.get(p["project_id"], [])
    return out


def ask_client(console, person_id, kind, project_id, task_id, details):
    """Start the client_requests agent for one developer request. The result is the usual run payload."""
    project = next((p for p in visible_projects(console, person_id) if p["project_id"] == project_id), None)
    if kind not in KINDS:
        return {"ok": False, "error": "Choose what you need from the client."}
    if project is None:
        return {"ok": False, "error": "Choose one of your projects."}
    if task_id and not console.cos.data_conn.execute(
            "SELECT 1 FROM tasks WHERE task_id = ? AND project_id = ?", (task_id, project_id)).fetchone():
        return {"ok": False, "error": "That task is not part of this project."}
    inputs = {"kind": kind, "project_id": project_id, "details": str(details or "").strip()[:DETAILS_MAX]}
    if task_id:
        inputs["task_id"] = task_id
    with console.lock:
        result = console.cos.run("client_requests", person_id, project["client_id"], trigger_kind="request", inputs=inputs)
        return console._run_payload(result)
