"""Brain inbox page routes (contract C8): drop a file, list sources, open one source with its lines, items and run steps."""
import base64
import binascii

from control_plane.company_memory import AreaDenied
from control_plane.company_brain import pipeline
from control_plane.company_brain.inbox import KINDS
from control_plane.company_brain.write_tools import untranslated_lines
from control_plane.guardrails import role_scopes

PAGE = {"id": "brain", "title": "Brain inbox", "order": 20, "icon": "inbox"}
MAX_BYTES = 2_000_000
EXTENSIONS = {".json": "fathom", ".docx": "docx", ".eml": "email", ".txt": "chat"}
AGENT_STEPS = ("brain_cleaner", "brain_extractor", "brain_linker", "brain_playbook")
NOT_FOUND = (404, {"ok": False, "error": "That source was not found."})


def _err(code, message):
    return code, {"ok": False, "error": message}


def _areas(cos, viewer):
    """Client and hold areas this person may read. The library and internal areas are never brain sources."""
    return sorted(role_scopes.readable_areas(cos.directory, viewer) - {role_scopes.LIBRARY_AREA, "devx-internal"})


def _kind(body):
    kind = (body.get("kind") or "").lower()
    if kind == "paste":
        kind = "plain"
    if not kind:
        name = (body.get("filename") or "").lower()
        kind = next((k for ext, k in EXTENSIONS.items() if name.endswith(ext)), "plain")
    return kind


def _content(body, kind):
    if body.get("content_b64"):
        try:
            data = base64.b64decode(body["content_b64"], validate=True)
        except (binascii.Error, ValueError):
            return None, "The file could not be read. Try again."
    elif isinstance(body.get("text"), str) and body["text"].strip():
        data = body["text"].encode("utf-8")
    else:
        return None, "Add a file or paste some text."
    if len(data) > MAX_BYTES:
        return None, "That file is too large. The limit is 2 MB."
    if kind in ("docx", "email"):
        return data, None
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, "That file is not text. Use a Fathom JSON, Word, email or chat file."


def _source_row(cos, brain, source):
    return {"source_id": source["source_id"], "title": source["title"], "kind": source["kind"],
            "area_id": source["area_id"], "status": source["status"], "language": source["language"],
            "occurred_at": source["occurred_at"], "received_at": source["received_at"], "origin_ref": source["origin_ref"],
            "lines": len(brain.source_lines(source["source_id"])),
            "items": len(brain.brain_items([source["area_id"]], source_id=source["source_id"]))}


def _run_steps(cos, source):
    """Runs of the four agents on this source, found from the source id in their logged tool calls."""
    out = []
    for agent in AGENT_STEPS:
        for run in cos.memory.runs(agent):
            if run["area_id"] != source["area_id"]:
                continue
            steps = cos.memory.run_steps(run["run_id"])
            if not any(s["step"] == "tool" and s["detail"].get("args", {}).get("source_id") == source["source_id"] for s in steps):
                continue
            summary = next((s["detail"].get("summary") for s in reversed(steps) if s["step"] == "remember"), None)
            out.append({"agent": agent, "run_id": run["run_id"], "status": run["status"],
                        "summary": summary or ("nothing to do" if any(s["step"] == "quiet" for s in steps) else run["status"]),
                        "warnings": sum(1 for s in steps if s["step"] == "warning")})
    return out


def routes(console):
    cos = console.cos

    def drop(q, body, viewer):
        body = body or {}
        areas = _areas(cos, viewer)
        hint = body.get("hint_area") or None
        if hint and hint not in areas:
            return _err(403, "You cannot add files to that client.")
        kind = _kind(body)
        if kind not in KINDS:
            return _err(400, "That kind of file is not supported.")
        content, problem = _content(body, kind)
        if problem:
            return _err(400, problem)
        with console.lock:
            try:
                result = pipeline.ingest_file(cos, kind=kind, content=content, filename=body.get("filename"),
                                              hint_area=hint, submitted_by=viewer)
            except (ValueError, KeyError) as e:
                return _err(400, f"The file could not be stored: {e}")
        if result.get("source_id") is None:
            return _err(400, "This file was skipped: " + str(result.get("skipped", "nothing to store")) + ".")
        if result["area_id"] not in areas:  # routed somewhere this person cannot open: say nothing about where
            return 200, {"ok": True, "visible": False, "message": "The file is stored. You cannot open it here."}
        return 200, {"ok": True, "visible": True, "source_id": result["source_id"], "area_id": result["area_id"],
                     "routed_by": result["routed_by"], "duplicate": bool(result.get("duplicate")),
                     "held": bool(result.get("held")), "steps": result["steps"]}

    def sources(q, body, viewer):
        brain = cos.brain.scoped(_areas(cos, viewer))
        rows = [_source_row(cos, brain, s) for s in brain.sources()]
        rows.sort(key=lambda r: (r["received_at"], r["source_id"]), reverse=True)
        return 200, {"ok": True, "sources": rows}

    def source(q, body, viewer):
        brain = cos.brain.scoped(_areas(cos, viewer))
        try:
            src = brain.get_source(q.get("id", ""))
        except AreaDenied:
            return NOT_FOUND
        if src is None:
            return NOT_FOUND
        gaps = set(untranslated_lines(cos.brain, src))
        lines = [{"line_no": l["line_no"], "speaker": l["clean_speaker"] or l["speaker"], "raw": l["text"],
                  "clean": l["clean_text"], "untranslated": l["line_no"] in gaps} for l in brain.source_lines(src["source_id"])]
        items = [{"item_id": i["item_id"], "kind": i["kind"], "topic": i["topic"], "text": i["text"], "state": i["state"],
                  "confirmed": i["confirmed"], "confidence": i["facts"]["confidence"],
                  "line_from": i["evidence"][0]["line_from"], "line_to": i["evidence"][0]["line_to"]}
                 for i in brain.brain_items([src["area_id"]], source_id=src["source_id"])]
        return 200, {"ok": True, "source": _source_row(cos, brain, src), "lines": lines, "items": items,
                     "steps": _run_steps(cos, src)}

    def assign(q, body, viewer):
        if role_scopes.console_role(cos.directory, viewer) != "admin":
            return _err(403, "Only an Admin can sort a source from the hold area.")
        body = body or {}
        with console.lock:
            try:
                cos.brain.reassign_source(body.get("source_id", ""), body.get("area_id", ""))
            except (KeyError, ValueError) as e:
                return _err(400, f"The source could not be moved: {e}")
            result = pipeline.process_source(cos, body["source_id"])
        return 200, {"ok": True, **result}

    return {("POST", "/api/brain/drop"): drop, ("GET", "/api/brain/sources"): sources,
            ("GET", "/api/brain/source"): source, ("POST", "/api/brain/assign"): assign}
