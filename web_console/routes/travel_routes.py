"""Travel page routes (contract C8): ask for a trip, see requests (own; Admin all), choose options. Booking waits for an Admin."""
from agents.finance.travel_booking import service
from guardrails import role_scopes

PAGE = {"id": "travel", "title": "Travel", "order": 70, "icon": "plane"}


def _error(message, status=400):
    return status, {"ok": False, "error": message}


def routes(console):
    cos = console.cos

    def _role(viewer):
        return role_scopes.console_role(cos.directory, viewer)

    def _name(person_id):
        p = cos.directory.get(person_id)
        return p["name"] if p else person_id

    def request_trip(q, body, viewer):
        if not role_scopes.may_see(_role(viewer), "travel_own"):
            return _error("This role cannot ask for travel.", 403)
        body = body or {}
        asked = body.get("request") if body.get("request") is not None else body.get("text")
        if not asked or (isinstance(asked, str) and not asked.strip()):
            return _error("Say where, when and how many people, for example: 2 people Mumbai to Pune on 2026-10-28, back on 2026-10-29.")
        with console.lock:
            result = service.request_trip(cos, viewer, asked)
        return 200, result

    def my_requests(q, body, viewer):
        role = _role(viewer)
        if not role_scopes.may_see(role, "travel_own"):
            return _error("This role cannot see travel.", 403)
        rows = service.requests_for(cos, viewer, all_requests=role_scopes.may_see(role, "travel_all"))
        for r in rows:
            r["requester_name"] = _name(r["requester_id"])
        return 200, {"ok": True, "all_requests": role_scopes.may_see(role, "travel_all"), "requests": rows}

    def choose(q, body, viewer):
        if not role_scopes.may_see(_role(viewer), "travel_own"):
            return _error("This role cannot choose travel options.", 403)
        body = body or {}
        with console.lock:
            result = service.choose_options(cos, body.get("request_id"), body.get("flight_option_id"),
                                            body.get("hotel_option_id") or None, viewer)
        if not result["ok"]:
            return 400, {"ok": False, "error": result["reason"]}
        return 200, result

    return {("POST", "/api/travel/request"): request_trip, ("GET", "/api/travel/requests"): my_requests,
            ("POST", "/api/travel/choose"): choose}
