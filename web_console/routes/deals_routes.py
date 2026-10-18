"""Deals and playbooks page routes (contract C8): my deals by stage, the deal brief, the playbook library."""
import json

from control_plane.connectors.deal_brain_tools import playbook_view
from control_plane.guardrails import role_scopes

PAGE = {"id": "deals", "title": "Deals and playbooks", "order": 40, "icon": "users"}
STAGES = ("discovery", "proposal", "closing")


def _error(message, status=400):
    return status, {"ok": False, "error": message}


def routes(console):
    cos = console.cos

    def _role(viewer):
        return role_scopes.console_role(cos.directory, viewer)

    def _my_deals(viewer, role):
        areas = role_scopes.readable_areas(cos.directory, viewer)
        deals = cos.brain.scoped(areas).deals(sorted(a for a in areas if a.startswith("C")))
        deals = [d for d in deals if d["stage"] in STAGES and (role == "admin" or d["owner_id"] == viewer)]
        show_value = role_scopes.may_see(role, "deal_value")
        return [{**{k: d[k] for k in ("deal_id", "area_id", "name", "industry", "stage", "tags")},
                 "value_inr": d["value_inr"] if show_value else None} for d in deals]

    def deal_list(q, body, viewer):
        role = _role(viewer)
        if not role_scopes.may_see(role, "deal_items"):
            return _error("This role cannot see deals.", 403)
        deals = _my_deals(viewer, role)
        return 200, {"ok": True, "stages": list(STAGES), "deals": deals}

    def deal_brief(q, body, viewer):
        role = _role(viewer)
        if not role_scopes.may_see(role, "deal_items"):
            return _error("This role cannot see deals.", 403)
        deal = next((d for d in _my_deals(viewer, role) if d["deal_id"] == (body or {}).get("deal_id")), None)
        if deal is None:
            return _error("That deal is not one of your open deals.", 404)
        with console.lock:  # the area comes from our own record, never from the request
            result = cos.run("deal_brief", viewer, deal["area_id"], inputs={"deal_id": deal["deal_id"]})
        if result.status != "done" or not result.final_text:
            return 200, {"ok": False, "error": result.reason or "No brief was made for this deal.", "run_id": result.run_id}
        return 200, {"ok": True, "run_id": result.run_id, "brief": json.loads(result.final_text), "deal": deal}

    def playbooks(q, body, viewer):
        if not role_scopes.may_see(_role(viewer), "library"):
            return _error("This role cannot read the playbook library.", 403)
        library = cos.brain.scoped([role_scopes.LIBRARY_AREA])
        return 200, {"ok": True, "playbooks": [{**playbook_view(p), "revenue_inr": p["revenue_inr"]} for p in library.playbooks()],
                     "checklist": [{k: c[k] for k in ("topic", "question", "why")} for c in library.checklist()]}

    return {("GET", "/api/deals/list"): deal_list, ("POST", "/api/deals/brief"): deal_brief,
            ("GET", "/api/deals/playbooks"): playbooks}
