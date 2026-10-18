"""Check page routes (contract C8). The page is optional: nothing waits for it and nothing is sent to anyone."""
import importlib

from control_plane.guardrails import role_scopes

PAGE = {"id": "review", "title": "Check", "order": 30, "icon": "check"}
KIND_LABEL = {"low_confidence": "Not sure about this item", "translation": "A line could not be translated",
              "contradiction": "A newer statement replaced an older one", "unrouted": "Not yet sorted to a client"}
CONTEXT_LINES = 1


def _role(cos, viewer):
    return role_scopes.console_role(cos.directory, viewer)


def _areas(cos, viewer):
    """Client areas the viewer may read; hold only for Admin. The library holds no review rows."""
    role = _role(cos, viewer)
    areas = set(role_scopes.readable_areas(cos.directory, viewer)) - {role_scopes.LIBRARY_AREA}
    if not role_scopes.may_see(role, "hold_area"):
        areas.discard("hold")
    return areas


def _lines(brain, source_id, line_from, line_to):
    rows = brain.source_lines(source_id)
    lo, hi = max(1, line_from - CONTEXT_LINES), line_to + CONTEXT_LINES
    return [{"line_no": r["line_no"], "speaker": r["speaker"], "raw": r["text"], "clean": r["clean_text"] or r["text"],
             "translated": r["clean_text"] is not None and r["clean_text"] != r["text"],
             "context": not line_from <= r["line_no"] <= line_to} for r in rows if lo <= r["line_no"] <= hi]


def _item_view(item):
    return {k: item[k] for k in ("item_id", "kind", "text", "topic", "state", "confirmed")} | \
        {"confidence": item["facts"].get("confidence"), "evidence": item["evidence"]}


def _entry(cos, review, area_names):
    brain, source = cos.brain, cos.brain.get_source(review["source_id"])
    item = brain.get_brain_item(review["item_id"]) if review["item_id"] else None
    proposed = review["proposed"]
    if item and item["evidence"]:
        span = (item["evidence"][0]["line_from"], item["evidence"][0]["line_to"])
    else:
        span = (proposed.get("line_from", 1), proposed.get("line_to", proposed.get("line_from", 1)))
    older = brain.get_brain_item(proposed["older"]) if review["kind"] == "contradiction" and proposed.get("older") else None
    return {"review_id": review["review_id"], "kind": review["kind"], "label": KIND_LABEL.get(review["kind"], review["kind"]),
            "reason": review["reason"], "status": review["status"], "confidence": review["confidence"],
            "area_id": review["area_id"], "area_name": area_names.get(review["area_id"], review["area_id"]),
            "assigned_to": review["assigned_to"], "due_on": review["due_on"], "overdue": review["overdue"],
            "source": {"source_id": source["source_id"], "title": source["title"], "kind": source["kind"],
                       "occurred_at": source["occurred_at"]},
            "item": _item_view(item) if item else None, "older": _item_view(older) if older else None,
            "proposed": None if item else proposed, "lines": _lines(brain, source["source_id"], *span)}


def _unrouted(cos, source):
    lines = cos.brain.source_lines(source["source_id"])[:4]
    return {"review_id": None, "kind": "unrouted", "label": KIND_LABEL["unrouted"], "reason": "no client matched this source",
            "status": "pending", "area_id": "hold", "area_name": "Not yet sorted", "source": {
                "source_id": source["source_id"], "title": source["title"], "kind": source["kind"], "occurred_at": source["occurred_at"]},
            "item": None, "older": None, "proposed": None, "overdue": False,
            "lines": [{"line_no": r["line_no"], "speaker": r["speaker"], "raw": r["text"], "clean": r["clean_text"] or r["text"],
                       "translated": False, "context": False} for r in lines]}


def routes(console):
    cos_of = lambda: console.cos

    def list_reviews(q, body, viewer):
        cos, role = cos_of(), _role(cos_of(), viewer)
        if role is None:
            return 403, {"ok": False, "error": "You do not have a console role."}
        areas = _areas(cos, viewer)
        status = q.get("status", "pending")
        mine = q.get("scope", "mine") != "all"
        names = {a["area_id"]: a["name"] for a in cos.memory.areas()} if hasattr(cos.memory, "areas") else {}
        with console.lock:
            rows = cos.brain.reviews(sorted(areas), status=None if status == "all" else status,
                                     assigned_to=viewer if mine else None)
            entries = [_entry(cos, r, names) for r in rows if r["kind"] != "unrouted"]
            if "hold" in areas and status in ("pending", "all"):  # unrouted sources are listed from the hold area itself
                entries += [_unrouted(cos, s) for s in cos.brain.sources(["hold"]) if s["status"] == "held"]
        return 200, {"ok": True, "scope": "mine" if mine else "all", "count": len(entries), "reviews": entries,
                     "note": "This page is optional. Everything is already stored and in use."}

    def _after_accept(cos, review, item_id):
        if item_id is None or "brain_linker" not in cos.packs:
            return None
        result = cos.run("brain_linker", "system", review["area_id"], trigger_kind="event", inputs={"source_id": review["source_id"]})
        return result.status

    def decide(q, body, viewer):
        cos, body = cos_of(), body or {}
        review = cos.brain.get_review(body.get("review_id") or "")
        if review is None or review["area_id"] not in _areas(cos, viewer):
            return 404, {"ok": False, "error": "That item was not found."}
        if not isinstance(body.get("accept"), bool):
            return 400, {"ok": False, "error": "Say if you confirm (true) or drop (false) this item."}
        edited = body.get("edited") or None
        if edited and not isinstance(edited, dict):
            return 400, {"ok": False, "error": "The edit must be a set of fields."}
        with console.lock:
            try:
                item_id = cos.brain.decide_review(review["review_id"], body["accept"], viewer, edited=edited)
            except (ValueError, KeyError) as e:
                return 400, {"ok": False, "error": str(e)}
            linked = _after_accept(cos, review, item_id) if body["accept"] else None
        return 200, {"ok": True, "review_id": review["review_id"], "status": "accepted" if body["accept"] else "rejected",
                     "item_id": item_id or review["item_id"], "linker": linked}

    def route_source(q, body, viewer):
        cos, body = cos_of(), body or {}
        if not role_scopes.may_see(_role(cos, viewer), "hold_area"):
            return 403, {"ok": False, "error": "Only an Admin can sort a source to a client."}
        source = cos.brain.get_source(body.get("source_id") or "")
        if source is None or source["area_id"] != "hold":
            return 404, {"ok": False, "error": "That source is not waiting to be sorted."}
        with console.lock:
            try:
                cos.brain.reassign_source(source["source_id"], body.get("area_id"))
            except ValueError as e:
                return 400, {"ok": False, "error": str(e)}
            with cos.brain.conn:
                cos.brain.conn.execute("UPDATE brain_review_queue SET status = 'accepted', decided_by = ?, decided_at = ?"
                                       " WHERE source_id = ? AND kind = 'unrouted' AND status = 'pending'",
                                       (viewer, cos.memory._now(), source["source_id"]))
            steps = None
            try:
                steps = importlib.import_module("control_plane.company_brain.pipeline").process_source(cos, source["source_id"])
            except ImportError:
                pass
        return 200, {"ok": True, "source_id": source["source_id"], "area_id": body["area_id"],
                     "processed": steps["steps"] if steps else None}

    return {("GET", "/api/review/list"): list_reviews, ("POST", "/api/review/decide"): decide,
            ("POST", "/api/review/route_source"): route_source}
