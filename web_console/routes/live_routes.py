"""Live call page routes (contract C8): list the calls, start one, hear a line, end it."""
import uuid

from agents.meeting_prep.live_copilot.live_session import LiveSession, Refused
from connectors.live_call_tools import list_calls
from guardrails import role_scopes

PAGE = {"id": "live", "title": "Live call", "order": 55, "icon": "pulse"}


def _sessions(console):
    return console.__dict__.setdefault("_live_sessions", {})


def _may_join(console, viewer, call):
    return role_scopes.console_role(console.cos.directory, viewer) == "admin" or call["viewer_id"] == viewer


def routes(console):
    def calls(q, body, viewer):
        with console.lock:
            rows = [c for c in list_calls(console.cos.data_conn) if _may_join(console, viewer, c)]
        return 200, {"ok": True, "calls": rows}

    def start(q, body, viewer):
        call_id = (body or {}).get("call_id")
        with console.lock:
            try:
                session = LiveSession.start(console.cos, viewer, call_id)
            except Refused as e:
                return 403, {"ok": False, "error": str(e)}
            sid = uuid.uuid4().hex[:12]
            _sessions(console)[sid] = (viewer, session)
            call = session.call
            return 200, {"ok": True, "session_id": sid, "run_id": session.run_id, "title": call["title"],
                         "client_name": call["client_name"], "viewer_id": call["viewer_id"],
                         "lines": [{k: l[k] for k in ("line_no", "t_sec", "speaker", "speaker_id", "lang", "text", "clean_text")}
                                   for l in call["lines"]]}

    def _find(body, viewer):
        entry = _sessions(console).get((body or {}).get("session_id"))
        if entry is None or entry[0] != viewer:
            return None
        return entry[1]

    def hear(q, body, viewer):
        with console.lock:
            session = _find(body, viewer)
            if session is None:
                return 404, {"ok": False, "error": "That call session was not found. Start the call again."}
            try:
                n = int((body or {}).get("line_no"))
                return 200, {"ok": True, **session.hear(n)}
            except (TypeError, ValueError) as e:
                return 400, {"ok": False, "error": f"Send a line number of this call. {e}"}

    def end(q, body, viewer):
        with console.lock:
            session = _find(body, viewer)
            if session is None:
                return 404, {"ok": False, "error": "That call session was not found. Start the call again."}
            result = session.end()
            _sessions(console).pop(body["session_id"], None)
            return 200, {"ok": True, **result}

    return {("GET", "/api/live/calls"): calls, ("POST", "/api/live/start"): start,
            ("POST", "/api/live/hear"): hear, ("POST", "/api/live/end"): end}
