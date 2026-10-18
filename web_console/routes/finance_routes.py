"""Finance page routes (contract C8, Admin only): watch findings with their records, trip cards, and a spend question."""
import json

from connectors.spend_tools import make_trip_alternatives
from guardrails import role_scopes

PAGE = {"id": "finance", "title": "Finance", "order": 60, "icon": "coin"}
AREA = "devx-internal"
QUESTION_LIMIT = 500
RECORD_SQL = {"INV": ("SELECT i.invoice_id, i.invoice_no, v.name AS vendor, i.amount_inr, i.date, i.status FROM invoices i "
                      "JOIN vendors v USING(vendor_id) WHERE i.invoice_id = ?", "Invoice"),
              "PAY": ("SELECT p.payment_id, p.invoice_id, v.name AS vendor, p.amount_inr, p.date FROM payments p "
                      "JOIN vendors v USING(vendor_id) WHERE p.payment_id = ?", "Payment")}


def _error(message, status=400):
    return status, {"ok": False, "error": message}


def routes(console):
    cos = console.cos

    def _admin(viewer):
        return role_scopes.may_see(role_scopes.console_role(cos.directory, viewer), "finance")

    def _record(rid):
        """One source record for a finding id: an invoice, a payment, or a team and month key."""
        spec = RECORD_SQL.get(rid[:3])
        row = cos.data_conn.execute(spec[0], (rid,)).fetchone() if spec else None
        if row:
            return {"id": rid, "type": spec[1], "detail": dict(row)}
        return {"id": rid, "type": "Budget line" if ":" in rid else "Record", "detail": {"key": rid}}

    def findings(q, body, viewer):
        if not _admin(viewer):
            return _error("Finance is for Admin only.", 403)
        out = []
        for c in cos.memory.cases(area_id=AREA, agent="finance_watch"):
            ev = json.loads(c["evidence"]) if isinstance(c["evidence"], str) else c["evidence"]
            out.append({"case_id": c["case_id"], "run_id": c["run_id"], "severity": c["severity"], "status": c["status"],
                        "kind": ev.get("kind"), "amount_inr": ev.get("amount_inr"), "evidence": ev.get("evidence"),
                        "why_it_matters": ev.get("why_it_matters"), "next_step": ev.get("next_step"),
                        "records": [_record(i) for i in ev.get("ids", [])]})
        return 200, {"ok": True, "findings": out}

    def trips(q, body, viewer):
        if not _admin(viewer):
            return _error("Finance is for Admin only.", 403)
        args = {k: q[k] for k in ("trip_id", "from", "to") if q.get(k)}
        tool = make_trip_alternatives(cos.data_conn)
        data = json.loads(tool.fn({"from": "2000-01-01", **args}, _ctx(viewer, cos.clock.today)))
        if "error" in data:
            return _error(data["error"])
        split = [dict(r) for r in cos.data_conn.execute(
            "SELECT team, SUM(amount_inr) AS travel_inr FROM expenses WHERE category = 'travel' GROUP BY team "
            "ORDER BY travel_inr DESC, team")]
        saving = sum(f["saving_inr"] for t in data["trips"] for f in t["cheaper_flights"][:1]) \
            + sum(h["saving_inr"] for t in data["trips"] for h in t["cheaper_hotels"][:1])
        return 200, {"ok": True, "trips": data["trips"], "spend_by_team": split, "top_option_saving_inr": saving}

    def ask(q, body, viewer):
        if not _admin(viewer):
            return _error("Finance is for Admin only.", 403)
        question = str((body or {}).get("question") or "").strip()[:QUESTION_LIMIT]
        if not question:
            return _error("Type a question first.")
        with console.lock:
            result = cos.run("spend_advisor", viewer, AREA, inputs={"question": question, "as_of": cos.clock.today})
        if result.status != "done" or not result.final_text:
            return 200, {"ok": False, "error": result.reason or "No answer was made.", "run_id": result.run_id}
        return 200, {"ok": True, "run_id": result.run_id, "answer": json.loads(result.final_text)["answer"]}

    def check_books(q, body, viewer):
        if not _admin(viewer):
            return _error("Finance is for Admin only.", 403)
        with console.lock:
            result = cos.run("finance_watch", viewer, AREA, inputs={"as_of": cos.clock.today})
        return 200, {"ok": result.status in ("done", "quiet"), "run_id": result.run_id, "status": result.status}

    return {("GET", "/api/finance/findings"): findings, ("GET", "/api/finance/trips"): trips,
            ("POST", "/api/finance/ask"): ask, ("POST", "/api/finance/check"): check_books}


def _ctx(viewer, as_of):
    from contract.types import RunContext, Task
    return RunContext("CONSOLE", Task("spend_advisor", viewer, AREA, "request", inputs={"as_of": as_of}), None)
