"""Tests for the console shell v2: three people, role checks on every call, Approvals, Runs, controls and static files."""
import http.client
import json
import os
import tempfile
import unittest

from agents.finance.travel_booking import service
from control_plane.guardrails import role_scopes
from web_console.console_api import Console, route
from web_console.serve import serve_in_thread

TRIP = "flights for 2 people Mumbai to Pune on 2026-10-28, back on 2026-10-29"
ADMIN, CSM, GROWTH = "P01", "P05", "P03"
STATIC = os.path.join(os.path.dirname(__file__), "..", "web_console", "static")


class ShellCase(unittest.TestCase):
    def setUp(self):
        self._dir, self._empty = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.addCleanup(self._empty.cleanup)
        self.console = Console(self._dir.name, routes_dir=self._empty.name, pages_dir=self._empty.name)
        self.addCleanup(self.console.close)

    def get(self, path, viewer=None, **q):
        query = {k: [v] for k, v in q.items()}
        if viewer:
            query["viewer"] = [viewer]
        return route(self.console, "GET", path, query, None)

    def post(self, path, viewer, body=None):
        return route(self.console, "POST", path, {}, {**(body or {}), "viewer": viewer})

    def held_booking(self, who=GROWTH):
        r = service.request_trip(self.console.cos, who, TRIP)
        self.assertTrue(r["ok"], r)
        return r["approval_id"]


class PeopleAndPages(ShellCase):
    def test_exactly_three_people_with_first_name_and_role(self):
        status, out = self.get("/api/console/people")
        self.assertEqual(status, 200)
        self.assertEqual([(p["person_id"], p["name"], p["role_label"]) for p in out["people"]],
                         [("P01", "Ammar", "Admin"), ("P05", "Akbar", "CSM"), ("P03", "Anthony", "Growth")])

    def test_each_role_home_lists_only_its_pages(self):
        for pid, role in role_scopes.DEMO_PEOPLE:
            status, out = self.get("/api/console/pages", pid)
            self.assertEqual(status, 200)
            self.assertCountEqual([p["id"] for p in out["pages"]], role_scopes.PAGES[role])
            self.assertEqual(out["privacy"], "Nothing here is used to rate people.")

    def test_home_works_when_no_plugin_pages_exist(self):
        _, out = self.get("/api/console/pages", ADMIN)
        by_id = {p["id"]: p for p in out["pages"]}
        self.assertTrue(by_id["home"]["present"] and by_id["approvals"]["present"] and by_id["runs"]["present"])
        self.assertFalse(by_id["finance"]["present"])
        self.assertIsNone(by_id["finance"]["script"])
        self.assertEqual(self.get("/api/console/home", ADMIN)[0], 200)

    def test_unknown_or_missing_viewer_gets_403(self):
        for viewer in (None, "P99", "P02", "system", "C01"):
            for path in ("/api/console/pages", "/api/console/approvals", "/api/run"):
                self.assertEqual(self.get(path, viewer)[0], 403, (viewer, path))

    def test_unknown_route_is_404(self):
        self.assertEqual(self.get("/api/today", ADMIN)[0], 404)
        self.assertEqual(self.get("/api/memory", ADMIN)[0], 404)


class RoleChecks(ShellCase):
    def test_runs_page_and_controls_are_admin_only(self):
        for who in (CSM, GROWTH):
            self.assertEqual(self.get("/api/console/runs", who)[0], 403)
            self.assertEqual(self.post("/api/console/next_day", who)[0], 403)
            self.assertEqual(self.post("/api/console/reset", who)[0], 403)
        self.assertEqual(self.get("/api/console/runs", ADMIN)[0], 200)

    def test_growth_has_no_approvals_page(self):
        self.assertEqual(self.get("/api/console/approvals", GROWTH)[0], 403)
        self.assertEqual(self.post("/api/console/approvals/decide", GROWTH, {"approval_id": "A1", "approve": True})[0], 403)

    def test_run_story_follows_the_role(self):
        run = self.console.cos.run("finance_watch", ADMIN, "devx-internal")
        self.assertEqual(self.get("/api/run", ADMIN, id=run.run_id)[0], 200)
        status, out = self.get("/api/run", CSM, id=run.run_id)
        self.assertEqual(status, 403)
        self.assertNotIn("walkthrough", out)
        self.assertEqual(self.get("/api/run", ADMIN, id="R9999")[0], 404)


class Approvals(ShellCase):
    def test_a_booking_shows_only_for_admin(self):
        aid = self.held_booking()
        _, admin = self.get("/api/console/approvals", ADMIN)
        self.assertEqual([a["approval_id"] for a in admin["approvals"]], [aid])
        _, csm = self.get("/api/console/approvals", CSM)
        self.assertEqual(csm["approvals"], [])

    def test_csm_cannot_decide_a_booking(self):
        aid = self.held_booking(CSM)
        status, out = self.post("/api/console/approvals/decide", CSM, {"approval_id": aid, "approve": True})
        self.assertEqual(status, 403)
        self.assertEqual(self.console.cos.approvals.get(aid)["status"], "pending")

    def test_admin_approves_and_it_books_once(self):
        aid = self.held_booking()
        status, out = self.post("/api/console/approvals/decide", ADMIN, {"approval_id": aid, "approve": True})
        self.assertEqual(status, 200, out)
        self.assertEqual(out["executed"]["status"], "booked")
        self.assertTrue(out["executed"]["result"].startswith("SIM-"))
        self.assertEqual(self.post("/api/console/approvals/decide", ADMIN, {"approval_id": aid, "approve": True})[0], 409)

    def test_deny_books_nothing(self):
        aid = self.held_booking()
        status, out = self.post("/api/console/approvals/decide", ADMIN, {"approval_id": aid, "approve": False})
        self.assertEqual((status, out["status"]), (200, "rejected"))
        self.assertIsNone(out["executed"])


class Controls(ShellCase):
    def test_next_day_pause_and_reset(self):
        before = self.console.cos.clock.today
        out = self.post("/api/console/next_day", ADMIN)[1]
        self.assertTrue(out["ok"])
        self.assertNotEqual(self.console.cos.clock.today, before)
        self.assertTrue(self.post("/api/console/pause", ADMIN)[1]["paused"])
        self.assertFalse(self.post("/api/console/resume", ADMIN)[1]["paused"])
        self.post("/api/console/reset", ADMIN)
        self.assertEqual(self.console.cos.clock.today, before)

    def test_next_day_brings_new_sources_into_the_brain_once(self):
        brain = self.console.cos.brain
        self.assertIsNotNone(brain.source_by_ref("SRC28"))   # history is in the brain at build
        self.assertIsNone(brain.source_by_ref("SRC29"))
        first = self.post("/api/console/next_day", ADMIN)[1]["inbox"]
        self.assertEqual((first["arrived"], first["ingested"], first["failed"]), (2, 2, 0))
        for ref in ("SRC29", "SRC31"):
            src = brain.source_by_ref(ref)
            self.assertTrue(brain.brain_items(src["area_id"], state=None, source_id=src["source_id"]), ref)  # facts were extracted
        self.assertIsNone(brain.source_by_ref("SRC30"))
        second = self.post("/api/console/next_day", ADMIN)[1]["inbox"]
        self.assertEqual((second["arrived"], second["ingested"]), (1, 1))
        self.assertIsNotNone(brain.source_by_ref("SRC30"))
        self.assertEqual(self.post("/api/console/next_day", ADMIN)[1]["inbox"]["arrived"], 0)

    def test_clock_survives_a_restart(self):
        self.post("/api/console/next_day", ADMIN)
        day = self.console.cos.clock.today
        again = Console(self._dir.name, routes_dir=self._empty.name, pages_dir=self._empty.name)
        self.addCleanup(again.close)
        self.assertEqual(again.cos.clock.today, day)


class StaticFilesAndServer(unittest.TestCase):
    def test_v1_pages_and_routes_are_gone(self):
        for name in ("console.js", "../department_scenarios.py", "../agent_cards.py", "../permissions.py"):
            self.assertFalse(os.path.exists(os.path.join(STATIC, name)), name)
        self.assertTrue(os.path.exists(os.path.join(STATIC, "shell.js")))

    def test_light_by_default_with_a_dark_toggle(self):
        with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertIn('content="light"', html)
        self.assertIn('id="dark"', html)
        self.assertIn("shell.js", html)

    def test_real_server_serves_pages_api_and_refuses_traversal(self):
        with tempfile.TemporaryDirectory() as state, tempfile.TemporaryDirectory() as empty:
            server, thread = serve_in_thread(state, routes_dir=empty, pages_dir=empty)
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)

            def fetch(method, path, body=None):
                conn.request(method, path, body=json.dumps(body) if body else None)
                res = conn.getresponse()
                return res.status, res.read()

            self.assertEqual(fetch("GET", "/")[0], 200)
            self.assertEqual(fetch("GET", "/shell.js")[0], 200)
            self.assertEqual(fetch("GET", "/../serve.py")[0], 404)
            self.assertEqual(fetch("GET", "/%2e%2e/serve.py")[0], 404)
            self.assertEqual(fetch("GET", "/pages/../../serve.py")[0], 404)
            self.assertEqual(len(json.loads(fetch("GET", "/api/console/people")[1])["people"]), 3)
            self.assertEqual(fetch("GET", "/api/console/runs?viewer=P05")[0], 403)
            self.assertEqual(fetch("POST", "/api/console/next_day", {"viewer": "P03"})[0], 403)
            conn.close()


if __name__ == "__main__":
    unittest.main()
