"""Tests for the web console: the API functions called directly, and one real server on a free port."""
import http.client
import json
import os
import re
import tempfile
import unittest
from unittest import mock
from urllib.request import urlopen

from web_console import console_api
from web_console.progress_page import plain_feature
from web_console.real_samples import load_real_samples
from web_console.console_api import Console, route
from web_console.department_scenarios import all_scenarios
from web_console.serve import serve_in_thread

STEP_TITLES = ["What it read", "What the code found", "What the model concluded",
               "What was checked before sending", "Who was told, or what is waiting for approval", "What was saved"]


class InboxAndScenarios(ConsoleCase):
    def test_every_available_scenario_gives_six_steps_or_quiet_or_refused(self):
        listed = {s["id"]: s for d in self.console.scenarios()["departments"] for s in d["scenarios"]}
        ran = 0
        for sc in all_scenarios():
            if listed[sc["id"]]["status"] != "ready":
                continue
            with self.subTest(scenario=sc["id"]):
                payload = self.run_ok(sc["id"])
                walk = payload["walkthrough"]
                self.assertEqual([s["title"] for s in walk["steps"]], STEP_TITLES)
                self.assertIn(walk["outcome"], ("done", "held", "quiet", "refused"))
                if walk["outcome"] == "refused":
                    self.assertIn("Refused", walk["headline"])
                    self.assertTrue(payload["reason"])
                elif walk["outcome"] == "quiet":
                    self.assertEqual(walk["steps"][2]["state"], "quiet")
                else:
                    self.assertTrue(all(walk["steps"][n]["state"] != "skipped" for n in (0, 1, 2, 3, 5)))
                ran += 1
        self.assertGreaterEqual(ran, 15)

    def test_planted_cases_show_up_and_quiet_day_is_quiet(self):
        subjects = lambda sid: [i["text"] for i in self.run_ok(sid)["walkthrough"]["steps"][1]["items"]]
        self.assertTrue(any("INV020" in t for t in subjects("fin-duplicate")))
        self.assertTrue(any("PAY030" in t for t in subjects("fin-new-vendor")))
        self.assertTrue(any("budget overrun" in t for t in subjects("fin-budget")))
        self.assertTrue(any("travel share" in t for t in subjects("fin-travel")))
        self.assertTrue(any("overloaded engineer" in t for t in subjects("csm-overload")))
        self.assertEqual(self.run_ok("fin-quiet")["walkthrough"]["outcome"], "quiet")

    def test_an_agent_that_is_not_installed_shows_as_being_built(self):
        without = tuple(a for a in console_api.ALL_AGENTS if a != "hiring_forecast")
        with mock.patch.object(console_api, "available_agents", return_value=(without, {"hiring_forecast": "missing"})):
            console = Console(self._dir.name, reset=True)
            self.addCleanup(console.close)
        status = {s["id"]: s["status"] for d in console.scenarios()["departments"] for s in d["scenarios"]}
        self.assertEqual(status["hr-short"], "being_built")
        self.assertEqual(status["fin-duplicate"], "ready")
        self.assertFalse(console.run_scenario("hr-short")["ok"])
        card = next(a for a in console.agent_cards()["agents"] if a["agent"] == "hiring_forecast")
        self.assertFalse(card["available"])


class Approvals(ConsoleCase):
    def test_approvals_list_follows_role_and_client(self):
        self.run_ok("fin-duplicate")
        self.run_ok("csm-over-sow")
        ids = lambda who: {a["agent"] for a in self.console.approvals(who)["approvals"]}
        self.assertEqual(ids("P01"), {"finance_watch", "project_risk"})
        self.assertEqual(ids("P07"), {"finance_watch"})
        self.assertEqual(ids("P06"), {"project_risk"})
        self.assertEqual(ids("P05"), set())
        self.assertEqual(ids("P90"), set())


class RunMeNowDefaults(ConsoleCase):
    def test_each_agent_opens_on_a_demo_date_and_plain_line(self):
        cards = self.cards()
        for name in ("finance_watch", "hiring_forecast", "meeting_prep", "project_risk", "fraud_watch",
                     "delivery_progress"):
            demo = cards[name]["demo"]
            self.assertRegex(demo["as_of"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(demo["line"].startswith(f"Showing {demo['as_of']}, when "), demo["line"])
            self.assertTrue(demo["line"].endswith("Change the date to try other days."))
        self.assertEqual(cards["meeting_prep"]["demo"]["event_id"], "EV113")
        self.assertEqual((cards["delivery_progress"]["demo"]["area_id"], cards["delivery_progress"]["demo"]["as_of"]),
                         ("C01", "2026-08-26"))

    def test_ceo_can_still_pick_any_area_and_date(self):
        areas = [a["area_id"] for a in self.console.state()["areas"]]
        self.assertIn("devx-internal", areas)
        self.assertGreater(len(areas), 2)
        out = self.console.run_agent("project_risk", "P01", "C03", {"as_of": "2026-10-01"})
        self.assertTrue(out["ok"])


class TodayAndCards(ConsoleCase):
    def test_today_hides_runs_of_clients_the_viewer_does_not_work_on(self):
        self.run_ok("csm-over-sow")
        self.run_ok("fin-duplicate")
        areas = {f["agent"] for f in self.console.today("P11")["feed"]}
        self.assertNotIn("project_risk", areas)
        self.assertIn("finance_watch", areas)
        self.assertEqual(self.console.today("P11")["needs_you"], [])


class LettersAndStory(ConsoleCase):
    def test_every_letter_of_the_run_is_in_the_run_detail_with_names(self):
        self.run_ok("csm-over-sow")
        run_id = self.console.runs()["runs"][0]["run_id"]
        detail = self.console.run_detail(run_id)
        self.assertTrue(detail["messages"])
        letter = detail["messages"][0]
        self.assertEqual((letter["to_name"], letter["kind"], letter["agent_title"]), ("Kabir Shah", "flag", "Project risk"))
        self.assertIn("The letters it wrote", page_script())

    def test_every_scenario_story_reads_without_json_keys(self):
        for sid in ("fin-duplicate", "csm-over-sow", "hr-short", "growth-ev113"):
            sentences = self.run_ok(sid)["walkthrough"]["steps"][2]["sentences"]
            self.assertTrue(sentences, sid)
            self.assertFalse([s for s in sentences if re.match(r"^[a-z_]+$", s)], sid)


class Permissions(ConsoleCase):
    def test_concrete_people(self):
        perm = lambda who: self.console.permissions(who)
        self.assertEqual(len(perm("P01")["areas"]), 7)
        self.assertEqual(perm("P01")["departments"], ["finance", "hr", "growth", "csm", "cto"])
        self.assertEqual(perm("P06")["agent_areas"]["project_risk"], ["C02", "C03", "C05"])
        self.assertEqual(perm("P11")["agents"], ["client_requests"])
        self.assertEqual(perm("P11")["agent_areas"], {"client_requests": ["C01"]})
        self.assertEqual((perm("P90")["agents"], perm("P90")["departments"]), (["hiring_forecast"], ["hr"]))
        self.assertEqual((perm("P07")["agents"], perm("P07")["agent_areas"]), (["finance_watch", "spend_advisor"],
                                                                    {"finance_watch": ["devx-internal"], "spend_advisor": ["devx-internal"]}))
        self.assertFalse(perm("P11")["can_ask_in_words"])
        self.assertFalse(perm("nobody")["ok"])

    def test_department_tabs_and_scenarios_follow_what_the_viewer_may_run(self):
        tabs = lambda who: {d["id"]: [s["id"] for s in d["scenarios"]] for d in self.console.scenarios(who)["departments"]}
        self.assertEqual(set(tabs("P01")), {"finance", "hr", "growth", "csm", "cto"})
        self.assertEqual(tabs("P01")["cto"], ["cto-refused-role"])
        self.assertEqual(self.console.scenarios("P11")["departments"], [])
        self.assertEqual(set(tabs("P07")), {"finance"})
        self.assertEqual(set(tabs("P90")), {"hr"})
        csm = tabs("P06")
        self.assertEqual(set(csm), {"growth", "csm"})
        self.assertNotIn("csm-overdue", csm["csm"])  # that client is not on this CSM's list
        self.assertIn("csm-over-sow", csm["csm"])
        self.assertIn("csm-approvals", csm["csm"])
        self.assertNotIn("csm-approvals", tabs("P90").get("csm", []))
        named = next(s for d in self.console.scenarios("P01")["departments"] for s in d["scenarios"] if s["id"] == "cto-refused-role")
        self.assertEqual(named["caller_name"], "Arjun Singh")
        shown = next(s for d in self.console.scenarios("P06")["departments"] for s in d["scenarios"] if s["id"] == "csm-over-sow")
        self.assertEqual(shown["caller_name"], "Kabir Shah")

    def test_hidden_actions_called_anyway_get_an_error_and_nothing_runs(self):
        post = lambda path, body: route(self.console, "POST", path, {}, body)
        status, out = post("/api/run", {"agent": "project_risk", "caller_id": "P05", "area_id": "C02"})
        self.assertEqual((status, out["ok"]), (403, False))
        self.assertIn("Nothing was run", out["error"])
        self.assertEqual(post("/api/run", {"agent": "finance_watch", "caller_id": "P11", "area_id": "devx-internal"})[0], 403)
        self.assertEqual(post("/api/run", {"agent": "finance_watch", "caller_id": "P07", "area_id": "C01"})[0], 403)
        status, out = post("/api/scenarios/run", {"id": "csm-over-sow", "person_id": "P11"})
        self.assertFalse(out["ok"])
        self.assertEqual(post("/api/ask", {"text": "prep me for EV111", "caller_id": "P03"})[0], 403)
        self.assertEqual(post("/api/progress/refresh", {"person_id": "P11", "client_id": "C01"})[0], 403)
        self.assertEqual(self.console.runs()["runs"], [])
        self.assertEqual(post("/api/run", {"agent": "project_risk", "caller_id": "P06", "area_id": "C02"})[0], 200)
