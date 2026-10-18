"""Tests for the Live call routes through the console stand-in (contract C8)."""
import unittest

from agents.meeting_prep.live_copilot.call_brain_seed import seed_history
from tests.console_stub import ConsoleStub
from web_console.routes import live_routes


class LiveRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stub = ConsoleStub()
        seed_history(cls.stub.cos)
        cls.r = live_routes.routes(cls.stub)

    @classmethod
    def tearDownClass(cls):
        cls.stub.close()

    def call(self, method, path, viewer, body=None):
        return self.r[(method, path)]({}, body, viewer)

    def test_page_and_route_names(self):
        self.assertEqual(live_routes.PAGE["id"], "live")
        self.assertEqual(set(self.r), {("GET", "/api/live/calls"), ("POST", "/api/live/start"),
                                       ("POST", "/api/live/hear"), ("POST", "/api/live/end")})

    def test_calls_depend_on_the_viewer(self):
        ids = lambda v: [c["call_id"] for c in self.call("GET", "/api/live/calls", v)[1]["calls"]]
        self.assertEqual(ids("P03"), ["LC01"])
        self.assertEqual(ids("P05"), ["LC02"])
        self.assertEqual(ids("P01"), ["LC01", "LC02"])

    def test_play_a_call_to_the_end(self):
        code, start = self.call("POST", "/api/live/start", "P05", {"call_id": "LC02"})
        self.assertEqual(code, 200, start)
        sid, found = start["session_id"], []
        for line in start["lines"]:
            code, reply = self.call("POST", "/api/live/hear", "P05", {"session_id": sid, "line_no": line["line_no"]})
            self.assertEqual(code, 200)
            found += reply["suggestions"]
        self.assertEqual([s["kind"] for s in found], ["contradiction"])
        code, end = self.call("POST", "/api/live/end", "P05", {"session_id": sid})
        self.assertTrue(end["ok"] and end["summary"])
        self.assertEqual(self.call("POST", "/api/live/hear", "P05", {"session_id": sid, "line_no": 1})[0], 404)

    def test_other_people_cannot_join_or_use_a_session(self):
        self.assertEqual(self.call("POST", "/api/live/start", "P05", {"call_id": "LC01"})[0], 403)
        _, start = self.call("POST", "/api/live/start", "P05", {"call_id": "LC02"})
        self.assertEqual(self.call("POST", "/api/live/hear", "P03", {"session_id": start["session_id"], "line_no": 1})[0], 404)

    def test_bad_input_gives_plain_errors(self):
        code, reply = self.call("POST", "/api/live/start", "P05", {"call_id": "nope"})
        self.assertEqual((code, reply["ok"]), (403, False))
        _, start = self.call("POST", "/api/live/start", "P05", {"call_id": "LC02"})
        code, reply = self.call("POST", "/api/live/hear", "P05", {"session_id": start["session_id"], "line_no": "x"})
        self.assertEqual((code, reply["ok"]), (400, False))


if __name__ == "__main__":
    unittest.main()
