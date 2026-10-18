"""Integration tests: one demo day runs end to end, and the exams runner scores every available pack."""
import shutil
import tempfile
import unittest

from evaluation.run_all_exams import close_all, run_all
from run_demo import available_agents, run_day


class DemoDayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = tempfile.mkdtemp(prefix="company_os_test_")
        cls.day = run_day(state_dir=cls.state)

    @classmethod
    def tearDownClass(cls):
        close_all(cls.day["cos"])
        shutil.rmtree(cls.state, ignore_errors=True)

    def statuses(self):
        return [r["status"] for r in self.day["runs"]]

    def test_day_runs_without_failed_runs(self):
        self.assertTrue(self.day["runs"])
        self.assertNotIn("failed", self.statuses())

    def test_people_receive_messages(self):
        self.assertGreaterEqual(len(self.day["messages"]), 1)

    def test_one_run_is_held_for_approval(self):
        self.assertIn("held", self.statuses())
        self.assertGreaterEqual(len(self.day["approvals"]), 1)

    def test_one_run_is_quiet(self):
        self.assertIn("quiet", self.statuses())

    def test_engineer_is_refused(self):
        self.assertEqual(self.day["refusal"]["status"], "refused")
        self.assertIn("refused", self.statuses())

    def test_cost_numbers_add_up(self):
        c = self.day["cost"]
        self.assertGreater(c["calls"], 0)
        self.assertEqual(c["cache_hits"] + c["cache_writes"], c["calls"])


class ExamRunnerTests(unittest.TestCase):
    def test_every_available_pack_has_a_result(self):
        rows = run_all()
        available = set(available_agents()[0])
        scored = {r["agent"] for r in rows if r["passed"] is not None}
        self.assertTrue(available <= scored)
        self.assertTrue({"meeting_prep", "finance_watch", "spend_advisor"} <= scored)
        self.assertTrue(all(r["passed"] for r in rows if r["passed"] is not None), rows)


if __name__ == "__main__":
    unittest.main()
