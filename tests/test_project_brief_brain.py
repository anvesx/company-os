"""Tests for the v2 project brief: brain items, citations, unconfirmed labels, changed decisions, scope and the route."""
import json
import threading
import unittest
from types import SimpleNamespace

from agents.meeting_prep.project_brief.replay_exam import KEY_PATH, seed_project_brain
from web_console.routes import meeting_prep_routes
from wiring.build_company_os import build_company_os

AGENT = "meeting_prep"


class ProjectBriefBrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(KEY_PATH) as f:
            cls.key = json.load(f)
        cls.cos = build_company_os(agents=(AGENT,))
        cls.ids = seed_project_brain(cls.cos, cls.key)
        low = cls.cos.brain.source_lines(cls.cos.brain.sources(["C04"])[0]["source_id"])[2]["text"]
        cls.cos.brain.add_brain_item("C04", "requirement", "Maybe a second language later.", topic="language-support",
                                     source_id=cls.cos.brain.sources(["C04"])[0]["source_id"], line_from=3, line_to=3,
                                     quote_raw=low, quote_clean=low, confidence=0.4, project_id="PR05")
        cls.result = cls.cos.run(AGENT, "P05", "C04", inputs={"event_id": "EV115"})
        cls.brief = json.loads(cls.result.final_text)
        cls.message = next(m["text"] for m in cls.cos.outbox.messages() if m["to_person_id"] == "P05" and m["kind"] == "brief")

    def cited(self):
        return {c for v in self.brief.values() if isinstance(v, list) for p in v if isinstance(p, dict) for c in p.get("cites", [])}

    def test_brief_cites_every_must_cite_item(self):
        self.assertEqual(self.result.status, "done", self.result.reason)
        need = {self.ids[k] for k in self.key["brain"]["project_brief"][0]["must_cite_keys"]}
        self.assertLessEqual(need, self.cited())

    def test_every_new_point_names_source_date_and_line(self):
        for name in ("open_requirements", "blockers", "recent_decisions"):
            self.assertTrue(self.brief[name], name)
            for p in self.brief[name]:
                self.assertTrue(p["cites"])
                self.assertTrue(p["sources"])
                self.assertTrue(all(s["source_id"] and s["line_from"] and s["date"] for s in p["sources"]), p)
        self.assertIn("line 14", self.message)

    def test_superseded_decision_shows_old_and_new(self):
        changed = [d["text"] for d in self.brief["changed_decisions"] if d["text"].startswith("Changed on 2026-10-")]
        self.assertTrue(changed)
        self.assertTrue(all(" → " in t for t in changed))
        self.assertIn("Changed on", self.message)

    def test_unconfirmed_item_is_labelled_and_counted(self):
        flagged = [p for p in self.brief["open_requirements"] if p.get("unconfirmed")]
        self.assertEqual(len(flagged), 1)
        self.assertIn("Unconfirmed: Maybe a second language later.", self.message)
        self.assertEqual(self.brief["unconfirmed_count"], 1)
        self.assertIn("1 unconfirmed items", self.message)

    def test_superseded_item_is_not_listed_as_current(self):
        old = self.ids["SRC25-2"]
        listed = {c for name in ("recent_decisions", "open_requirements", "blockers") for p in self.brief[name] for c in p["cites"]}
        self.assertNotIn(old, listed)

    def test_a_decision_never_sits_under_blockers(self):
        decision_id = self.ids["SRC25-9"]
        self.assertIn(decision_id, {c for p in self.brief["recent_decisions"] for c in p["cites"]})
        self.assertNotIn(decision_id, {c for p in self.brief["blockers"] for c in p["cites"]})
        understood = {"open_items": [], "recent_decisions": [], "attendees": [{"person_id": "P05", "is_devx": True}],
                      "brain": {"items": [{"item_id": "D1", "kind": "decision"}, {"item_id": "B1", "kind": "blocker"}]}}
        bad = {"questions": [], "blockers": [{"text": "Reminders by WhatsApp only", "cites": ["D1"]}]}
        good = {"questions": [], "blockers": [{"text": "Approval is pending", "cites": ["B1"]}]}
        pack = self.cos.packs[AGENT]
        self.assertTrue(any("not a blocker" in p for p in pack.check(None, bad, understood)))
        self.assertEqual(pack.check(None, good, understood), [])

    def test_agent_has_no_finance_or_library_access(self):
        tools = {s["detail"]["name"] for s in self.cos.memory.run_steps(self.result.run_id) if s["step"] == "tool"}
        self.assertIn("project_brain_items", tools)
        self.assertTrue(tools <= {"upcoming_meeting", "project_open_items", "project_recent_decisions",
                                  "project_brain_items", "recent_client_messages", "send_private_message"})
        self.assertFalse(self.cos.packs[AGENT].reads_library)
        with self.assertRaises(Exception):
            self.cos.brain.scoped(["C04"]).playbooks()


class MeetingPrepRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(KEY_PATH) as f:
            key = json.load(f)
        cos = build_company_os(agents=(AGENT,))
        seed_project_brain(cos, key)
        cls.routes = meeting_prep_routes.routes(SimpleNamespace(cos=cos, lock=threading.RLock(), run_story=None))

    def call(self, method, path, viewer, body=None):
        return self.routes[(method, path)]({}, body, viewer)

    def test_upcoming_lists_only_the_viewers_meetings(self):
        status, reply = self.call("GET", "/api/meeting_prep/upcoming", "P05")
        self.assertEqual((status, reply["ok"]), (200, True))
        self.assertEqual({e["event_id"] for e in reply["events"]}, {"EV115", "EV114"})

    def test_brief_returns_cited_points(self):
        status, reply = self.call("POST", "/api/meeting_prep/brief", "P05", {"event_id": "EV115"})
        self.assertTrue(reply["ok"], reply)
        self.assertEqual(reply["unconfirmed_line"], "0 unconfirmed items")
        self.assertTrue(all(p["sources"] for p in reply["brief"]["blockers"]))

    def test_growth_cannot_open_project_briefs(self):
        self.assertEqual(self.call("GET", "/api/meeting_prep/upcoming", "P03")[0], 403)

    def test_meeting_of_another_csm_is_refused(self):
        self.assertEqual(self.call("POST", "/api/meeting_prep/brief", "P05", {"event_id": "EV113"})[0], 404)


if __name__ == "__main__":
    unittest.main()
