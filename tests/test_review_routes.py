"""Check page routes: optional list with raw and clean lines, Confirm, Edit, Drop, route from hold (Admin only), role limits."""
import unittest

from tests.console_stub import ConsoleStub
from web_console.routes import review_routes

ADMIN, CSM, GROWTH = "P01", "P05", "P03"


class ReviewRoutesCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stub = ConsoleStub()
        cls.addClassCleanup(cls.stub.close)
        cls.table = review_routes.routes(cls.stub)
        cls.b = cls.stub.cos.brain

    def call(self, method, name, viewer, q=None, body=None):
        return self.table[(method, f"/api/review/{name}")](q or {}, body, viewer)

    def source(self, area, ref, raw, clean=None):
        sid = self.b.add_source(area, "chat", ref, raw, origin_ref=ref, occurred_at="2026-10-01T10:00", participants=[],
                                language="hinglish", lines=[{"line_no": 1, "speaker": "Dr", "text": "Namaste"}, {"line_no": 2, "speaker": "Dr", "text": raw}])
        self.b.set_clean_lines(sid, [{"line_no": 1, "clean_text": "Hello"}, {"line_no": 2, "clean_text": clean or raw}])
        return sid

    def unconfirmed(self, area, ref, topic="reminders", text="We need reminders on WhatsApp."):
        sid = self.source(area, ref, "Reminder WhatsApp pe chahiye", text)
        return self.b.add_brain_item(area, "requirement", text, topic=topic, source_id=sid, line_from=2,
                                     line_to=2, quote_raw="Reminder WhatsApp pe chahiye", quote_clean=text, confidence=0.4)

    def test_page_is_registered_for_the_review_slot(self):
        self.assertEqual(review_routes.PAGE["id"], "review")
        self.assertEqual(set(self.table), {("GET", "/api/review/list"), ("POST", "/api/review/decide"), ("POST", "/api/review/route_source")})

    def test_list_shows_raw_and_clean_lines_side_by_side(self):
        item_id = self.unconfirmed("C04", "R-LIST")
        code, out = self.call("GET", "list", CSM, {"scope": "all"})
        self.assertEqual(code, 200)
        entry = next(r for r in out["reviews"] if r["item"] and r["item"]["item_id"] == item_id)
        line = next(l for l in entry["lines"] if l["line_no"] == 2)
        self.assertEqual((line["raw"], line["clean"]), ("Reminder WhatsApp pe chahiye", "We need reminders on WhatsApp."))
        self.assertEqual(entry["item"]["state"], "unconfirmed")
        self.assertIn("optional", out["note"])

    def test_growth_does_not_see_a_client_area_of_the_csm(self):
        self.unconfirmed("C04", "R-GROWTH")
        _, out = self.call("GET", "list", GROWTH, {"scope": "all"})
        self.assertTrue(all(r["area_id"] != "C04" for r in out["reviews"]))
        code, out = self.call("POST", "decide", GROWTH, body={"review_id": self.b.reviews(["C04"])[0]["review_id"], "accept": True})
        self.assertEqual(code, 404)

    def test_confirm_edit_and_drop(self):
        a = self.unconfirmed("C04", "R-D0", "access-credentials", "Sandbox login must be shared with the doctors.")
        b_ = self.unconfirmed("C04", "R-D1", "payments", "Payments by UPI are required.")
        c = self.unconfirmed("C04", "R-D2", "training", "A short workshop for clinic staff.")
        ids = {r["item_id"]: r["review_id"] for r in self.b.reviews(["C04"])}
        rid = ids.__getitem__
        code, out = self.call("POST", "decide", CSM, body={"review_id": rid(a), "accept": True})
        self.assertEqual((code, out["ok"]), (200, True))
        self.assertEqual(self.b.get_brain_item(a)["state"], "active")
        code, out = self.call("POST", "decide", CSM, body={"review_id": rid(b_), "accept": True, "edited": {"text": "Reminders by WhatsApp only."}})
        self.assertEqual(self.b.get_brain_item(b_)["text"], "Reminders by WhatsApp only.")
        code, out = self.call("POST", "decide", CSM, body={"review_id": rid(c), "accept": False})
        self.assertEqual(self.b.get_brain_item(c)["state"], "dropped")
        code, out = self.call("POST", "decide", CSM, body={"review_id": rid(a), "accept": True})
        self.assertEqual(code, 400)  # already decided

    def test_bad_requests_get_a_plain_error(self):
        code, out = self.call("POST", "decide", CSM, body={"review_id": "nope", "accept": True})
        self.assertEqual((code, out["ok"]), (404, False))
        self.assertIn("error", out)
        item = self.unconfirmed("C04", "R-BAD")
        review = next(r["review_id"] for r in self.b.reviews(["C04"]) if r["item_id"] == item)
        code, out = self.call("POST", "decide", CSM, body={"review_id": review})
        self.assertEqual(code, 400)

    def test_contradiction_is_listed_as_changed_with_the_older_item(self):
        sid = self.source("C08", "R-CON", "Budget 14 lakh")
        old = self.b.add_brain_item("C08", "money", "Budget INR 14 lakh", topic="budget", source_id=sid, line_from=1, line_to=1,
                                    quote_raw="x", quote_clean="x", confidence=0.9, said_at="2026-10-01")
        new = self.b.add_brain_item("C08", "money", "Budget INR 18 lakh", topic="budget", source_id=sid, line_from=2, line_to=2,
                                    quote_raw="y", quote_clean="y", confidence=0.9, said_at="2026-10-02")
        self.b.resolve_contradiction(old, new)
        _, out = self.call("GET", "list", GROWTH, {"scope": "all"})
        entry = next(r for r in out["reviews"] if r["kind"] == "contradiction" and r["item"]["item_id"] == new)
        self.assertEqual(entry["older"]["item_id"], old)
        self.assertEqual(self.b.get_brain_item(old)["state"], "superseded")  # already resolved; the page is optional

    def test_hold_sources_are_for_admin_only(self):
        sid = self.source("hold", "R-HOLD", "Unknown client mail")
        _, admin = self.call("GET", "list", ADMIN, {"scope": "all"})
        self.assertIn(sid, [r["source"]["source_id"] for r in admin["reviews"] if r["kind"] == "unrouted"])
        _, csm = self.call("GET", "list", CSM, {"scope": "all"})
        self.assertNotIn(sid, [r["source"]["source_id"] for r in csm["reviews"]])
        code, out = self.call("POST", "route_source", CSM, body={"source_id": sid, "area_id": "C04"})
        self.assertEqual(code, 403)
        code, out = self.call("POST", "route_source", ADMIN, body={"source_id": sid, "area_id": "C04"})
        self.assertEqual((code, out["ok"]), (200, True))
        self.assertEqual(self.b.get_source(sid)["area_id"], "C04")
        code, out = self.call("POST", "route_source", ADMIN, body={"source_id": sid, "area_id": "C04"})
        self.assertEqual(code, 404)  # no longer on hold

    def test_route_to_a_non_client_area_is_refused(self):
        sid = self.source("hold", "R-HOLD2", "Another mail")
        code, out = self.call("POST", "route_source", ADMIN, body={"source_id": sid, "area_id": "devx-internal"})
        self.assertEqual((code, out["ok"]), (400, False))

    def test_accepting_runs_the_linker_when_it_exists(self):
        item = self.unconfirmed("C07", "R-LINK", "reminders")
        review = next(r["review_id"] for r in self.b.reviews(["C07"]) if r["item_id"] == item)
        code, out = self.call("POST", "decide", ADMIN, body={"review_id": review, "accept": True})
        self.assertEqual(code, 200)
        self.assertEqual(out["linker"], "done" if "brain_linker" in self.stub.cos.packs else None)


if __name__ == "__main__":
    unittest.main()
