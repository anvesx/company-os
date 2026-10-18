"""Deals page routes: who sees what, the brief call, the library."""
import json
import unittest

from control_plane.company_brain.sample_content import seed_sample
from tests.console_stub import ConsoleStub
from web_console.routes import deals_routes


class DealsRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stub = ConsoleStub()
        seed_sample(cls.stub.cos.brain, cls.stub.cos.data_conn)
        cls.r = deals_routes.routes(cls.stub)

    @classmethod
    def tearDownClass(cls):
        cls.stub.close()

    def call(self, method, path, viewer, body=None):
        return self.r[(method, path)]({}, body, viewer)

    def test_page_id_is_allowed_for_growth(self):
        from control_plane.guardrails import role_scopes
        self.assertTrue(role_scopes.may_open_page("growth", deals_routes.PAGE["id"]))
        self.assertFalse(role_scopes.may_open_page("csm", deals_routes.PAGE["id"]))

    def test_growth_lists_own_deals_with_value(self):
        status, out = self.call("GET", "/api/deals/list", "P03")
        self.assertEqual((status, out["ok"]), (200, True))
        self.assertEqual({d["deal_id"] for d in out["deals"]}, {"L20", "L21"})
        self.assertTrue(all(d["value_inr"] for d in out["deals"]))

    def test_csm_is_refused_everywhere(self):
        for method, path in (("GET", "/api/deals/list"), ("POST", "/api/deals/brief"), ("GET", "/api/deals/playbooks")):
            status, out = self.call(method, path, "P05", {"deal_id": "L20"})
            self.assertEqual((status, out["ok"]), (403, False), path)

    def test_brief_for_own_deal(self):
        status, out = self.call("POST", "/api/deals/brief", "P03", {"deal_id": "L20"})
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["brief"]["deal_id"], "L20")
        self.assertTrue(out["brief"]["kickoff_questions"])

    def test_brief_refuses_a_deal_that_is_not_theirs_or_unknown(self):
        for deal_id in ("L22", "L05", "nope", None):
            status, out = self.call("POST", "/api/deals/brief", "P03", {"deal_id": deal_id})
            self.assertEqual((status, out["ok"]), (404, False), deal_id)

    def test_playbooks_have_five_sections_and_no_contact_names(self):
        status, out = self.call("GET", "/api/deals/playbooks", "P03")
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["playbooks"]), 2)
        for pb in out["playbooks"]:
            self.assertEqual(len(pb["sections"]), 5)
            self.assertNotIn("area_id", pb)
        names = [r["name"] for r in self.stub.cos.data_conn.execute("SELECT name FROM people WHERE is_devx = 0")]
        text = json.dumps(out)
        self.assertFalse(any(n in text for n in names))

    def test_admin_sees_the_deals_too(self):
        status, out = self.call("GET", "/api/deals/list", "P01")
        self.assertTrue(out["ok"])
        self.assertTrue({"L20", "L21"} <= {d["deal_id"] for d in out["deals"]})


if __name__ == "__main__":
    unittest.main()
