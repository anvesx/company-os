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


class ProgressPages(ConsoleCase):
    def refresh_all(self):
        for client in ("C01", "C02", "C03", "C04", "C05"):
            self.assertTrue(self.console.progress_refresh("P01", client)["ok"])

    def test_empty_list_says_so_and_offers_a_refresh_per_client(self):
        out = self.console.progress("P05")
        self.assertEqual((out["view"], out["empty"]), ("own_detail", True))
        self.assertEqual([c["client_id"] for c in out["clients"]], ["C01", "C04", "C06"])

    def test_refresh_button_runs_delivery_progress_as_the_viewer(self):
        out = self.console.progress_refresh("P05", "C01")
        self.assertEqual((out["run"]["agent"], out["run"]["caller_id"], out["status"]), ("delivery_progress", "P05", "done"))
        self.assertEqual(out["snapshots_saved"], 2)
        self.assertEqual(len(self.console.progress("P05")["projects"]), 2)
        self.assertEqual(self.console.run_detail(out["run"]["run_id"])["snapshots_saved"], 2)

    def test_refresh_refused_for_a_role_that_may_not_start_it(self):
        out = self.console.progress_refresh("P11", "C01")
        self.assertEqual(out["status"], "refused")
        self.assertIn("not allowed", out["reason"])
        self.assertFalse(self.console.progress_refresh("P01", "nope")["ok"])

    def test_ceo_sees_all_hr_sees_no_names_growth_sees_one_line_each(self):
        self.refresh_all()
        ceo = self.console.progress("P01")
        self.assertEqual((ceo["view"], len(ceo["projects"])), ("full", 6))
        row = next(p for p in ceo["projects"] if p["project_id"] == "PR02")
        self.assertEqual(row["status"], "on track")
        self.assertEqual({"scope_pct", "time_pct", "projected_finish", "planned_end_on", "flags", "waited_days",
                          "snapshot_on"} - set(row), set())
        hr = self.console.progress("P90")
        self.assertEqual(hr["view"], "team_totals")
        self.assertEqual(hr["projects"] + hr["lines"], [])
        text = json.dumps(hr)
        for name in ("POS Rollout", "Tailorbird", "Neha", "Kabir"):
            self.assertNotIn(name, text)
        self.assertEqual(hr["totals"]["projects"], 6)
        growth = self.console.progress("P04")
        self.assertEqual((growth["view"], len(growth["lines"]), growth["projects"]), ("status_lines", 6, []))
        self.assertEqual(set(growth["lines"][0]), {"client_id", "client_name", "project_id", "project_name", "status"})

    def test_a_csm_sees_detail_for_own_projects_and_an_engineer_only_status_lines(self):
        self.refresh_all()
        csm = self.console.progress("P05")
        self.assertEqual({p["project_id"] for p in csm["projects"]}, {"PR01", "PR02", "PR05"})
        self.assertEqual(self.console.progress("P11")["view"], "status_lines")
        page = self.console.progress_project("P11", "PR01")
        self.assertEqual((page["ok"], page["detail"]), (True, False))

    def test_project_page_has_plain_scope_tasks_flags_and_no_pr_details(self):
        self.refresh_all()
        page = self.console.progress_project("P05", "PR02")
        self.assertTrue(page["detail"])
        self.assertIn("days were spent waiting on the client", page["project"]["headline"])
        item = page["scope"][0]
        self.assertEqual({"title", "status", "est", "tasks", "pct", "live"} - set(item), set())
        self.assertEqual({"title", "assignee", "status", "due_on"} - set(item["tasks"][0]), set())
        self.assertEqual({t["status"] for s in page["scope"] for t in s["tasks"]} - {"todo", "doing", "done"}, set())
        self.assertEqual(page["total"]["tasks_total"], sum(s["tasks_total"] for s in page["scope"]))
        flag = next(f for f in page["flags"] if f["signal"] == "unbilled_work")
        self.assertIn("not in the signed scope", flag["evidence"])
        self.assertIn("Loyalty points banner on cart", flag["items"])
        blob = json.dumps(page)
        for banned in ("feat:", "prs_merged", "pr_id", "lines_changed", "branch"):
            self.assertNotIn(banned, blob)
        self.assertTrue(page["decisions"])
        self.assertIn("Neha Iyer", page["project"]["csm_name"])

    def test_project_page_is_refused_for_hr_and_for_a_csm_not_on_it(self):
        self.refresh_all()
        self.assertTrue(self.console.progress_project("P90", "PR02")["refused"])
        self.assertTrue(self.console.progress_project("P05", "PR03")["refused"])
        self.assertFalse(self.console.progress_project("P01", "PR99")["ok"])

    def test_project_page_without_a_snapshot_offers_a_refresh(self):
        page = self.console.progress_project("P05", "PR02")
        self.assertEqual((page["ok"], page["detail"], page["no_snapshot"]), (True, False, True))

    def test_project_page_lists_client_requests_and_open_risk_flags(self):
        self.refresh_all()
        self.run_ok("csm-over-sow")
        page = self.console.progress_project("P01", "PR03")
        self.assertEqual([c["column"] for c in page["requests"]], ["failed"])
        self.assertEqual([r["label"] for r in page["risks"]][:1], ["Hours over sow"])

    def test_plain_feature_removes_prefixes_and_ticket_ids(self):
        self.assertEqual(plain_feature("feat(cart): loyalty banner [ABC-123]"), "Loyalty banner")
        self.assertEqual(plain_feature("fix: #45 broken link"), "Broken link")

    def test_routes(self):
        status, out = route(self.console, "POST", "/api/progress/refresh", {}, {"person_id": "P01", "client_id": "C02"})
        self.assertEqual((status, out["status"]), (200, "done"))
        self.assertTrue(route(self.console, "GET", "/api/progress", {"person": ["P01"]}, None)[1]["projects"])
        self.assertTrue(route(self.console, "GET", "/api/progress/project", {"person": ["P01"], "id": ["PR03"]}, None)[1]["detail"])


class ClientRequestsBoard(ConsoleCase):
    def cards(self, person):
        board = self.console.client_requests(person)
        return {c["id"]: c["cards"] for c in board["columns"]}, board

    def test_board_has_six_columns_and_the_safety_line(self):
        cols, board = self.cards("P01")
        self.assertEqual([c["id"] for c in board["columns"]], ["asked", "reminded", "stuck", "granted", "verified", "failed"])
        self.assertEqual(board["safety"], "Agents never ask for passwords in chat; client messages wait for the CSM's approval.")
        self.assertEqual([c["request_id"] for c in cols["stuck"]], ["RQ044"])
        self.assertEqual([c["request_id"] for c in cols["failed"]], ["RQ042"])
        stuck = cols["stuck"][0]
        self.assertEqual((stuck["owner_name"], stuck["days_open"]), ("Nandini Sethi", 20))
        self.assertEqual(stuck["blocks"][0]["task_id"], "T290")
        self.assertIn("Access denied", cols["failed"][0]["check_detail"])

    def test_who_sees_the_board(self):
        self.assertEqual({p["project_id"] for p in self.console.client_requests("P05")["projects"]},
                         {"PR01", "PR02", "PR05", "PR07"})
        self.assertEqual([p["project_id"] for p in self.console.client_requests("P11")["projects"]], ["PR01"])
        for person in ("P90", "P04", "P07"):
            board = self.console.client_requests(person)
            self.assertEqual(board["projects"], [])
            self.assertIn("This board is for", board["note"])

    def test_form_runs_the_agent_and_opens_a_run_with_its_letter(self):
        board = self.console.client_requests("P11")
        self.assertTrue(board["may_ask"])
        self.assertIn("theme_access", [k["kind"] for k in board["kinds"]])
        out = self.console.client_request_ask("P11", "theme_access", "PR01", "T001", "Need theme access on the store")
        self.assertEqual((out["ok"], out["run"]["agent"], out["run"]["caller_id"]), (True, "client_requests", "P11"))
        self.assertEqual(out["messages"][0]["to_name"], "Arjun Singh")
        self.assertIn("Need theme access on the store", out["messages"][0]["text"])

    def test_form_checks_its_input(self):
        ask = self.console.client_request_ask
        self.assertFalse(ask("P11", "nonsense", "PR01", None, "x")["ok"])
        self.assertFalse(ask("P11", "theme_access", "PR03", None, "x")["ok"])
        self.assertFalse(ask("P11", "theme_access", "PR01", "T290", "x")["ok"])
        self.assertFalse(ask("P90", "theme_access", "PR01", None, "x")["ok"])

    def test_route_for_the_form_and_the_board(self):
        body = {"person_id": "P11", "kind": "dns_record", "project_id": "PR01", "task_id": "", "details": "Need DNS"}
        status, out = route(self.console, "POST", "/api/client_requests/ask", {}, body)
        self.assertEqual((status, out["ok"]), (200, True))
        self.assertEqual(route(self.console, "GET", "/api/client_requests", {"person": ["P11"]}, None)[0], 200)


class LettersAndStory(ConsoleCase):
    def test_delivery_progress_run_reports_how_many_snapshots_it_saved(self):
        out = self.console.run_agent("delivery_progress", "P01", "C01", {"as_of": "2026-10-19"})
        self.assertEqual(out["snapshots_saved"], 2)
        self.assertIsNone(self.run_ok("fin-duplicate")["snapshots_saved"])
        self.assertIn("Saved a progress snapshot for", page_script())


class Approvals(ConsoleCase):
    def test_a_csm_cannot_approve_for_a_client_they_do_not_work_on(self):
        self.run_ok("csm-over-sow")  # Finvault Pay (C02), CSM P06
        approval = self.pending()[0]["approval_id"]
        self.assertNotIn("C02", self.console.cos.directory.client_access("P05"))
        out = self.console.decide(approval, True, "P05")
        self.assertTrue(out["refused"])
        self.assertTrue(self.console.decide(approval, True, "P06")["ok"])


class RunMeNowDefaults(ConsoleCase):
    def test_client_requests_keeps_today(self):
        card = self.cards().get("client_requests")
        if card:
            self.assertIsNone(card["demo"])


class LettersAndStoryProgress(ConsoleCase):
    def test_decided_what_to_say_has_plain_sentences_and_no_key_names(self):
        out = self.console.progress_refresh("P01", "C01")
        step = out["walkthrough"]["steps"][2]
        self.assertTrue(step["sentences"])
        joined = " ".join(step["sentences"])
        self.assertIn("Ecommerce Revamp is on track", joined)
        for raw in ("headlines", "unbilled_work", "unbilled work", "flags", "severity"):
            self.assertNotIn(raw, joined)
        self.assertEqual(len(step["sentences"]), 3)
        self.assertNotIn("Titles:", joined)
        self.assertIn("s.sentences", page_script())
