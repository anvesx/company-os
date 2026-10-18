"""Data for the Project progress pages. Every view of a snapshot goes through progress_for, so roles stay respected."""
import json
import re

from connectors.client_request_tools import client_request_tools
from connectors.git_tools import git_tools
from connectors.progress_views import FULL_ROLES, OWN_ROLES, progress_for

from .client_requests_page import request_cards
from .connector_calls import read_tool

FLAG_LABEL = {"unbilled_work": "Unbilled work", "scope_rework": "Rework", "behind_deadline": "Behind deadline"}
STATUS_WORD = {"on track": "On track", "at risk": "At risk", "behind": "Behind"}
NO_SNAPSHOT = "No progress snapshot exists yet for this project."
DECISIONS_SHOWN, DAYS_IN_MONTH = 6, 30.4


def _span(days):
    return f"about {round(days / DAYS_IN_MONTH)} months" if days >= 60 else f"{days} days"


def _waited(console, rows, as_of):
    """Days that tasks waited on the client, per project id (from the project_profile tool)."""
    tools, out = client_request_tools(console.cos.data_conn), {}
    for client_id in sorted({r["client_id"] for r in rows}):
        for p in read_tool(tools, "project_profile", client_id, {}, as_of).get("projects", []):
            out[p["project_id"]] = p["blocked_days"]["task_days_waited_on_client"]
    return out


def _headline(snap, waited):
    pace, status = snap["pace"], snap["status"]
    late, word = pace.get("days_late"), STATUS_WORD[snap["status"]]
    if late is None:
        first = f"{word}: not enough merged work yet to forecast a finish date."
    elif late <= 0:
        first = f"{word}: on pace to finish by the planned end."
    elif status == "behind":
        first = f"Behind by {_span(late)} at the current pace."
    else:
        first = f"{word}: finishing {_span(late)} after the planned end at the current pace."
    return first + (f" {waited} days were spent waiting on the client." if waited else "")


def _row(snap, client_names, waited):
    pace = snap["pace"]
    return {"project_id": snap["project_id"], "project_name": snap["project_name"], "client_id": snap["client_id"],
            "client_name": client_names.get(snap["client_id"]), "status": snap["status"],
            "scope_pct": pace["merged_pct"], "time_pct": pace["elapsed_pct"],
            "planned_end_on": pace["planned_end_on"], "projected_finish": pace["projected_finish"],
            "days_late": pace["days_late"], "snapshot_on": snap["as_of"],
            "flags": [{"signal": f["signal"], "label": FLAG_LABEL.get(f["signal"], f["signal"])} for f in snap["flags"]],
            "waited_days": waited.get(snap["project_id"], 0), "headline": _headline(snap, waited.get(snap["project_id"], 0))}


def _client_names(console):
    return {r["client_id"]: r["name"] for r in console.cos.data_conn.execute("SELECT client_id, name FROM clients")}


def _my_clients(console, person_id):
    names, allowed = _client_names(console), console._allowed_areas(person_id)
    return [{"client_id": k, "name": v} for k, v in sorted(names.items()) if k in allowed]


def progress_list(console, person_id):
    if not console.cos.directory.get(person_id):
        return {"ok": False, "error": "Unknown person."}
    as_of = console.cos.clock.today
    view = progress_for(person_id, console.cos.memory, console.cos.directory, console.cos.data_conn, as_of)
    out = {"ok": True, "as_of": as_of, "role": view["role"], "view": view["view"], "clients": _my_clients(console, person_id),
           "projects": [], "other_projects": [], "lines": [], "totals": None}
    names = _client_names(console)
    if view["view"] == "team_totals":
        out["totals"], out["empty"] = view["totals"], view["totals"]["projects"] == 0
        out["clients"] = []
        return out
    if view["view"] in ("full", "own_detail"):
        waited = _waited(console, view["projects"], as_of)
        out["projects"] = [_row(s, names, waited) for s in view["projects"]]
        out["other_projects"] = view.get("other_projects", [])
    else:
        out["lines"] = view["projects"]
    out["empty"] = not (out["projects"] or out["other_projects"] or out["lines"])
    return out


PREFIX = re.compile(r"^\s*(feat|fix|chore|refactor|docs|style|test|perf|build|ci)(\([^)]*\))?!?:\s*", re.I)
TICKET = re.compile(r"\s*[\[(]?(?:\b[A-Z]{2,}-\d+\b|#\d+\b)[\])]?\s*")


def plain_feature(title):
    """A pull request title as plain feature words: no prefix such as feat:, no ticket id, first letter capital."""
    text = TICKET.sub(" ", PREFIX.sub("", str(title))).strip(" -:")
    return text[:1].upper() + text[1:]


def _unbilled(console, project_id, client_id, as_of):
    reply = read_tool(git_tools(console.cos.data_conn), "unlinked_merged_prs", client_id,
                      {"project_id": project_id, "limit": 100}, as_of)
    names = [plain_feature(p["title"]) for p in reply.get("prs", []) if not p["chore"]]
    return list(dict.fromkeys(n for n in names if n))


def _flag_view(console, snap, flag):
    signal, pace = flag["signal"], snap["pace"]
    out = {"signal": signal, "label": FLAG_LABEL.get(signal, signal), "severity": flag.get("severity"), "items": []}
    if signal == "unbilled_work":
        out["items"] = _unbilled(console, snap["project_id"], snap["client_id"], snap["as_of"])
        out["evidence"] = f"{len(out['items'])} things were built that are not in the signed scope."
    elif signal == "scope_rework":
        item = next((i for i in snap["scope"] if i["id"] == flag.get("scope_item_id")), None)
        out["evidence"] = (f"{item['title'].capitalize()} was changed {item['revisions']} times after client feedback."
                           if item else "A scope item was changed many times after client feedback.")
        out["scope_item_id"] = flag.get("scope_item_id")
    else:
        out["evidence"] = (f"{pace['elapsed_pct']}% of the time is used and {pace['merged_pct']}% of the scope is done."
                           + (f" The forecast finish is {pace['projected_finish']}, the planned end is {pace['planned_end_on']}."
                              if pace["projected_finish"] else ""))
    return out


def _tasks_by_scope(console, project_id, as_of):
    """Tasks under each SOW scope item: title, assignee name, status and due date (read for an already allowed project)."""
    rows = console.cos.data_conn.execute(
        "SELECT s.scope_item_id, k.task_id, k.title, k.assignee_id, k.status, k.due_on, k.done_on FROM task_scope s "
        "JOIN tasks k ON k.task_id = s.task_id WHERE k.project_id = ? ORDER BY k.due_on, k.task_id", (project_id,))
    out = {}
    for r in rows:
        done = bool(r["done_on"]) and r["done_on"] <= as_of
        status = "done" if done else ("doing" if r["status"] in ("doing", "done") else "todo")
        out.setdefault(r["scope_item_id"], []).append({
            "task_id": r["task_id"], "title": r["title"], "assignee": console._name(r["assignee_id"]) if r["assignee_id"] else None,
            "status": status, "due_on": r["due_on"]})
    return out


def _scope_view(console, snap):
    tasks = _tasks_by_scope(console, snap["project_id"], snap["as_of"])
    scope, done_all, all_tasks = [], 0, 0
    for i in snap["scope"]:
        mine = tasks.get(i["id"], [])
        done = sum(t["status"] == "done" for t in mine)
        done_all, all_tasks = done_all + done, all_tasks + len(mine)
        scope.append({"id": i["id"], "title": i["title"], "status": i["status"], "est": i["est"], "tasks": mine,
                      "tasks_done": done, "tasks_total": len(mine), "pct": round(100 * done / len(mine)) if mine else 0,
                      "live": i["in_prod"], "revisions": i["revisions"]})
    total = {"tasks_done": done_all, "tasks_total": all_tasks, "pct": round(100 * done_all / all_tasks) if all_tasks else 0}
    return scope, total


def _project_decisions(console, person_id, snap):
    conn = console.cos.data_conn
    meetings = {r["meeting_id"]: r for r in conn.execute(
        "SELECT meeting_id, project_id, title FROM meetings WHERE client_id = ?", (snap["client_id"],))}
    scoped = console.cos.memory.scoped(console._allowed_areas(person_id))
    rows = []
    for i in scoped.items(snap["client_id"], kinds=["decision"], status="active"):
        meeting = meetings.get(str(i["source"]).replace("meeting:", ""))
        if meeting and meeting["project_id"] not in (None, snap["project_id"]):
            continue
        rows.append({"text": i["text"], "on": i["created_at"][:10], "meeting": meeting["title"] if meeting else None})
    return sorted(rows, key=lambda r: r["on"], reverse=True)[:DECISIONS_SHOWN]


def _project_risks(console, person_id, snap):
    role = console._role(person_id)
    if not (role == "ceo" or console.cos.policy.may_start(role, "project_risk")):
        return []
    out = []
    for c in console.cos.memory.cases(area_id=snap["client_id"], agent="project_risk"):
        signal, _, target = c["subject"].partition(":")
        if c["status"] != "open" or target != snap["project_id"]:
            continue
        try:
            text = json.loads(c["evidence"]).get("text", "")
        except (TypeError, ValueError, AttributeError):
            text = ""
        out.append({"case_id": c["case_id"], "run_id": c["run_id"], "label": signal.replace("_", " ").capitalize(),
                    "severity": c["severity"], "text": text})
    return out


def progress_project(console, person_id, project_id):
    if not console.cos.directory.get(person_id):
        return {"ok": False, "error": "Unknown person."}
    as_of = console.cos.clock.today
    view = progress_for(person_id, console.cos.memory, console.cos.directory, console.cos.data_conn, as_of)
    if view["view"] == "team_totals":
        return {"ok": False, "refused": True, "error": "HR sees team totals only, so there is no page for one project."}
    snap = next((s for s in view["projects"] if view["view"] in ("full", "own_detail") and s["project_id"] == project_id), None)
    if snap is None:
        return _without_detail(console, person_id, view, project_id)
    names = _client_names(console)
    waited = _waited(console, [snap], as_of)
    row = _row(snap, names, waited)
    cards = [c for c in request_cards(console, person_id, [project_id]) if c["column"] in ("stuck", "failed", "asked", "reminded")]
    scope, total = _scope_view(console, snap)
    return {"ok": True, "detail": True, "as_of": as_of, "project": {**row, "csm_name": console._name(snap["csm_id"]),
            "lead_name": console._name(snap["lead_id"])}, "scope": scope, "scope_counts": snap["scope_counts"],
            "total": total, "flags": [_flag_view(console, snap, f) for f in snap["flags"]],
            "requests": cards, "decisions": _project_decisions(console, person_id, snap),
            "risks": _project_risks(console, person_id, snap)}


def _without_detail(console, person_id, view, project_id):
    """A project the viewer sees only as a status line, has no snapshot yet, or may not see."""
    lines = view["projects"] if view["view"] == "status_lines" else view.get("other_projects", [])
    line = next((x for x in lines if x["project_id"] == project_id), None)
    if line:
        return {"ok": True, "detail": False, "line": line,
                "note": "Your role sees the status line of this project, not the detail."}
    proj = console.cos.data_conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
    if proj is None:
        return {"ok": False, "error": "I could not find that project."}
    own = view["role"] in FULL_ROLES or (view["role"] in OWN_ROLES and person_id in (proj["csm_id"], proj["lead_id"]))
    if proj["client_id"] in console._allowed_areas(person_id) and own:
        return {"ok": True, "detail": False, "no_snapshot": True, "note": NO_SNAPSHOT,
                "line": {"project_id": project_id, "project_name": proj["name"], "client_id": proj["client_id"],
                         "client_name": _client_names(console).get(proj["client_id"])}}
    return {"ok": False, "refused": True, "error": "You may not see this project, or it has no progress snapshot yet."}


def refresh_progress(console, person_id, client_id):
    """Run delivery_progress for one client as the viewer. A refused run comes back with its plain reason."""
    if not console.cos.data_conn.execute("SELECT 1 FROM clients WHERE client_id = ?", (client_id,)).fetchone():
        return {"ok": False, "error": "Choose a client first."}
    return console.run_agent("delivery_progress", person_id, client_id, {"as_of": console.cos.clock.today})
