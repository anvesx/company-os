"""Brain routes: drop, list and open a source, with the role rule enforced on the data."""
import base64
import threading
import unittest
from types import SimpleNamespace

from evaluation.run_all_exams import close_all
from guardrails import role_scopes
from web_console.routes import brain_routes

from tests.brain_test_support import make_cos

ADMIN, CSM, GROWTH = "P01", "P05", "P03"


class BrainRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cos = make_cos()
        cls.handlers = brain_routes.routes(SimpleNamespace(cos=cls.cos, lock=threading.RLock(), run_story=lambda r: {}))

    @classmethod
    def tearDownClass(cls):
        close_all(cls.cos)

    def call(self, verb, name, viewer, q=None, body=None):
        return self.handlers[(verb, f"/api/brain/{name}")](q or {}, body, viewer)

    def drop(self, viewer, **body):
        return self.call("POST", "drop", viewer, body=body)

    def test_page_is_one_every_role_may_open(self):
        self.assertTrue(all(role_scopes.may_open_page(r, brain_routes.PAGE["id"]) for r in role_scopes.CONSOLE_ROLES))

    def test_csm_drops_text_for_own_client(self):
        code, r = self.drop(CSM, kind="paste", text="We need payment by UPI.", hint_area="C04")
        self.assertEqual((code, r["ok"], r["visible"]), (200, True, True))
        self.assertEqual(r["steps"][1]["status"], "done")
        _, seen = self.call("GET", "source", CSM, q={"id": r["source_id"]})
        self.assertEqual(len(seen["items"]), 1)
        self.assertEqual(seen["items"][0]["line_from"], 1)
        self.assertEqual([s["agent"] for s in seen["steps"]], ["brain_cleaner", "brain_extractor"])

    def test_a_file_is_read_from_base64(self):
        code, r = self.drop(CSM, filename="chat.txt", hint_area="C04",
                            content_b64=base64.b64encode(b"[12/10/26, 10:05] Nandini Sethi: We need UPI payment\n").decode())
        self.assertEqual((code, r["ok"]), (200, True))

    def test_hint_for_a_client_the_viewer_cannot_open_is_refused(self):
        code, r = self.drop(GROWTH, kind="paste", text="We need payment.", hint_area="C04")
        self.assertEqual(code, 403)
        self.assertFalse(r["ok"])

    def test_other_roles_cannot_open_the_source(self):
        _, r = self.drop(CSM, kind="paste", text="We need payment by UPI.", hint_area="C04")
        self.assertEqual(self.call("GET", "source", GROWTH, q={"id": r["source_id"]})[0], 404)
        ids = lambda who: {x["source_id"] for x in self.call("GET", "sources", who)[1]["sources"]}
        self.assertNotIn(r["source_id"], ids(GROWTH))
        self.assertIn(r["source_id"], ids(ADMIN))

    def test_bad_input_gets_a_plain_error(self):
        self.assertEqual(self.drop(CSM, kind="paste", text="  ")[0], 400)
        self.assertEqual(self.drop(CSM, kind="paste", content_b64="@@@")[0], 400)
        self.assertEqual(self.drop(CSM, kind="movie", text="x")[0], 400)

    def test_hold_sources_are_for_admin_only(self):
        _, r = self.drop(ADMIN, kind="paste", text="Nobody knows the client here. We need a launch date.")
        self.assertTrue(r["held"])
        self.assertNotIn(r["source_id"], {x["source_id"] for x in self.call("GET", "sources", CSM)[1]["sources"]})
        self.assertEqual(self.call("POST", "assign", CSM, body={"source_id": r["source_id"], "area_id": "C04"})[0], 403)
        code, moved = self.call("POST", "assign", ADMIN, body={"source_id": r["source_id"], "area_id": "C04"})
        self.assertEqual((code, moved["steps"][1]["status"]), (200, "done"))

    def test_a_drop_routed_out_of_view_says_nothing_about_where(self):
        code, r = self.drop(GROWTH, kind="paste", text="Hello Nandini Sethi, we need UPI payment.")
        self.assertEqual(code, 200)
        self.assertNotIn("area_id", r)


if __name__ == "__main__":
    unittest.main()
