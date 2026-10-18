"""Tests for plug-in discovery (contract C8): modules found in a folder, missing pages skipped, role gate before any handler."""
import os
import sys
import tempfile
import textwrap
import unittest

from tests.console_stub import ConsoleStub
from web_console.console_api import Console, route

SAMPLE = textwrap.dedent('''
    CALLS = []
    PAGE = {"id": "finance", "title": "Finance", "order": 60, "icon": "coin"}
    def routes(console):
        def total(q, body, viewer):
            CALLS.append(viewer)
            return 200, {"ok": True, "viewer": viewer, "area": q.get("area")}
        return {("GET", "/api/finance/total"): total}
''')
UNKNOWN_PAGE = 'PAGE = {"id": "secret", "title": "Secret", "order": 1, "icon": "bot"}\ndef routes(console):\n    return {("GET", "/api/secret/x"): lambda q, b, v: (200, {"ok": True})}\n'


class PluginCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.routes, self.pages, self.state = (os.path.join(self.tmp.name, d) for d in ("routes", "pages", "state"))
        os.makedirs(self.routes)
        os.makedirs(self.pages)

    def write(self, folder, name, text):
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            f.write(text)

    def build(self):
        console = Console(self.state, routes_dir=self.routes, pages_dir=self.pages)
        self.addCleanup(console.close)
        return console

    def call(self, console, viewer, path="/api/finance/total", **q):
        query = {k: [v] for k, v in q.items()}
        query["viewer"] = [viewer]
        return route(console, "GET", path, query, None)


class Discovery(PluginCase):
    def test_finds_a_route_module_and_a_page_script_made_in_a_temp_folder(self):
        self.write(self.routes, "finance_routes.py", SAMPLE)
        self.write(self.pages, "finance.js", "CompanyOS.registerPage({id: 'finance'});")
        self.write(self.pages, "finance.css", ".finance-x { color: var(--ink); }")
        console = self.build()
        self.assertEqual(list(console.plugins), ["finance"])
        row = next(p for p in console.pages_for("P01") if p["id"] == "finance")
        self.assertEqual((row["script"], row["css"], row["present"], row["title"]), ("pages/finance.js", "pages/finance.css", True, "Finance"))
        status, out = self.call(console, "P01", area="C01")
        self.assertEqual((status, out["viewer"], out["area"]), (200, "P01", "C01"))

    def test_a_missing_page_is_skipped_and_listed_as_not_present(self):
        console = self.build()
        self.assertEqual(console.plugins, {})
        row = next(p for p in console.pages_for("P01") if p["id"] == "meeting_prep")
        self.assertFalse(row["present"])
        self.assertIsNone(row["script"])

    def test_a_broken_module_or_an_unknown_page_id_is_skipped(self):
        self.write(self.routes, "broken_routes.py", "raise RuntimeError('boom')")
        self.write(self.routes, "secret_routes.py", UNKNOWN_PAGE)
        self.write(self.routes, "nopage_routes.py", "x = 1")
        self.write(self.pages, "secret.js", "")
        console = self.build()
        self.assertEqual(console.plugins, {})
        self.assertEqual(self.call(console, "P01", "/api/secret/x")[0], 404)

    def test_the_real_routes_folder_loads_without_error(self):
        console = Console(self.state)
        self.addCleanup(console.close)
        self.assertEqual(console.people()[0]["name"], "Ammar")


class RoleGate(PluginCase):
    def test_a_route_of_a_page_the_role_may_not_open_is_403_and_runs_nothing(self):
        self.write(self.routes, "finance_routes.py", SAMPLE)
        console = self.build()
        module = sys.modules["console_plugin_finance_routes"].CALLS
        module.clear()
        for viewer in ("P05", "P03"):
            status, out = self.call(console, viewer)
            self.assertEqual(status, 403)
            self.assertFalse(out["ok"])
        self.assertEqual(module, [])
        self.assertEqual(self.call(console, "P01")[0], 200)
        self.assertEqual(module, ["P01"])

    def test_an_unknown_viewer_is_403_and_runs_nothing(self):
        self.write(self.routes, "finance_routes.py", SAMPLE)
        console = self.build()
        calls = sys.modules["console_plugin_finance_routes"].CALLS
        calls.clear()
        for viewer in ("P99", "P02", ""):
            self.assertEqual(self.call(console, viewer)[0], 403)
        self.assertEqual(calls, [])

    def test_a_plugin_cannot_replace_a_shell_route(self):
        self.write(self.routes, "finance_routes.py", SAMPLE.replace("/api/finance/total", "/api/console/runs"))
        console = self.build()
        status, out = self.call(console, "P01", "/api/console/runs")
        self.assertIn("summary", out)


class Stub(unittest.TestCase):
    def test_the_stub_exposes_cos_lock_and_run_story(self):
        stub = ConsoleStub()
        self.addCleanup(stub.close)
        run = stub.cos.run("finance_watch", "P01", "devx-internal")
        self.assertTrue(stub.run_story(run.run_id)["ok"])
        stub.lock.acquire()
        stub.lock.release()


if __name__ == "__main__":
    unittest.main()
