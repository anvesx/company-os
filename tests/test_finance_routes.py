"""Finance page routes: Admin only, findings with records, trip cards, a spend question."""
import unittest

from control_plane.guardrails import role_scopes
from tests.console_stub import ConsoleStub
from web_console.routes import finance_routes


class FinanceRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stub = ConsoleStub()
        cls.r = finance_routes.routes(cls.stub)

    @classmethod
    def tearDownClass(cls):
        cls.stub.close()

    def call(self, method, path, viewer, body=None, q=None):
        return self.r[(method, path)](q or {}, body, viewer)

    def test_page_card_matches_the_role_table(self):
        self.assertTrue(role_scopes.may_open_page("admin", finance_routes.PAGE["id"]))
        self.assertFalse(role_scopes.may_open_page("csm", finance_routes.PAGE["id"]))
        self.assertFalse(role_scopes.may_open_page("growth", finance_routes.PAGE["id"]))

    def test_csm_and_growth_are_refused_on_every_route(self):
        for viewer in ("P05", "P03"):
            for method, path in self.r:
                status, out = self.call(method, path, viewer, {"question": "x"})
                self.assertEqual((status, out["ok"]), (403, False), (viewer, path))

    def test_trips_carry_paid_against_cheaper_options(self):
        status, out = self.call("GET", "/api/finance/trips", "P01")
        self.assertEqual((status, out["ok"]), (200, True))
        card = next(t for t in out["trips"] if t["trip_id"] == "TR015")
        self.assertEqual(card["cheaper_flights"][0]["flight_no"], "TRG 341")
        self.assertTrue(out["spend_by_team"])
        one = self.call("GET", "/api/finance/trips", "P01", q={"trip_id": "TR012"})[1]
        self.assertEqual([t["trip_id"] for t in one["trips"]], ["TR012"])

    def test_check_then_findings_with_source_records(self):
        self.assertTrue(self.call("POST", "/api/finance/check", "P01")[1]["ok"])
        out = self.call("GET", "/api/finance/findings", "P01")[1]
        self.assertTrue(out["ok"])
        for f in out["findings"]:
            self.assertTrue(f["records"] and f["why_it_matters"] and f["next_step"])
        invoices = [rec for f in out["findings"] for rec in f["records"] if rec["type"] == "Invoice"]
        self.assertTrue(all("vendor" in rec["detail"] and "amount_inr" in rec["detail"] for rec in invoices))

    def test_ask_answers_for_admin_and_rejects_an_empty_question(self):
        status, out = self.call("POST", "/api/finance/ask", "P01", {"question": "Where can we save on travel?"})
        self.assertEqual((status, out["ok"]), (200, True))
        self.assertIn("A cheaper flight:", out["answer"])
        self.assertEqual(self.call("POST", "/api/finance/ask", "P01", {"question": "  "})[0], 400)


if __name__ == "__main__":
    unittest.main()
