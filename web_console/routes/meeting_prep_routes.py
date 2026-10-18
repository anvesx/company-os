"""Meeting prep page: the viewer's next client meetings and the brief for one of them (contract C8)."""
import json

from agents.meeting_prep.project_brief.pack import enrich_brief
from connectors.project_brain_tools import item_view
from guardrails import role_scopes

PAGE = {"id": "meeting_prep", "title": "Meeting prep", "order": 30, "icon": "calendar"}
AGENT = "meeting_prep"


def _allowed(cos, viewer):
    role = role_scopes.console_role(cos.directory, viewer)
    if role is None or not role_scopes.may_see(role, "project_items"):
        return None
    return role, role_scopes.readable_areas(cos.directory, viewer)


def _events(cos, viewer, areas, event_id=None):
    rows = cos.data_conn.execute(
        "SELECT e.*, c.name AS client_name, p.name AS project_name FROM calendar_events e "
        "JOIN clients c ON c.client_id = e.client_id LEFT JOIN projects p ON p.project_id = e.project_id "
        "WHERE e.project_id IS NOT NULL AND e.start_at >= ? ORDER BY e.start_at", (cos.clock.today,)).fetchall()
    out = []
    for r in rows:
        if r["client_id"] not in areas or (event_id and r["event_id"] != event_id):
            continue
        if viewer not in json.loads(r["attendees"] or "[]") and not _is_admin(cos, viewer):
            continue
        out.append(r)
    return out


def _is_admin(cos, viewer):
    return role_scopes.console_role(cos.directory, viewer) == "admin"


def _enrich_from_store(brief, sb):
    items = {}
    for name, points in brief.items():
        for p in points if isinstance(points, list) else []:
            for cite in (p.get("cites") or []) if isinstance(p, dict) else []:
                item = sb.get_brain_item(cite) if cite not in items else None
                if item is not None:
                    items[cite] = item_view(sb, item)
    return enrich_brief(brief, items)


def routes(console):
    cos = console.cos

    def upcoming(q, body, viewer):
        access = _allowed(cos, viewer)
        if access is None:
            return 403, {"ok": False, "error": "Your role cannot open project briefs."}
        _, areas = access
        sb = cos.brain.scoped(areas)
        events = [{"event_id": r["event_id"], "title": r["title"], "start_at": r["start_at"], "client_id": r["client_id"],
                   "client_name": r["client_name"], "project_id": r["project_id"], "project_name": r["project_name"],
                   "unconfirmed_count": sb.unconfirmed_count(r["client_id"], r["project_id"])}
                  for r in _events(cos, viewer, areas)]
        return 200, {"ok": True, "events": events[:10]}

    def brief(q, body, viewer):
        access = _allowed(cos, viewer)
        if access is None:
            return 403, {"ok": False, "error": "Your role cannot open project briefs."}
        event_id = str((body or {}).get("event_id") or "")
        events = _events(cos, viewer, access[1], event_id)
        if not event_id or not events:
            return 404, {"ok": False, "error": "That meeting is not one of your upcoming client meetings."}
        event = events[0]
        with console.lock:
            result = cos.run(AGENT, viewer, event["client_id"], inputs={"event_id": event_id})
            sb = cos.brain.scoped(access[1])
            if result.status != "done":
                return 200, {"ok": False, "error": f"The brief could not be made: {result.reason or result.status}."}
            try:
                data = json.loads(result.final_text[result.final_text.find("{"):result.final_text.rfind("}") + 1])
            except ValueError:
                data = {}
            data = _enrich_from_store(data, sb)
            count = sb.unconfirmed_count(event["client_id"], event["project_id"])
        data["unconfirmed_count"] = count
        return 200, {"ok": True, "quiet": not data, "run_id": result.run_id, "event_id": event_id, "title": event["title"],
                     "start_at": event["start_at"], "project_name": event["project_name"], "brief": data,
                     "unconfirmed_line": f"{count} unconfirmed items"}

    return {("GET", "/api/meeting_prep/upcoming"): upcoming, ("POST", "/api/meeting_prep/brief"): brief}
