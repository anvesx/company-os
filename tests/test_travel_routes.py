"""Travel page routes and the round-trip search: own requests, Admin sees all, round trips with both flight numbers."""
import unittest

from agents.finance.travel_booking.policy_ranking import load_policy
from control_plane.guardrails import role_scopes
from tests.console_stub import ConsoleStub
from web_console.routes import travel_routes

TEXT = "flights for 3 people Mumbai to Pune on 2026-10-28, back on 2026-10-29"


class TravelRoutesTests(unittest.TestCase):
    def setUp(self):
        self.stub = ConsoleStub()
        self.addCleanup(self.stub.close)
        self.r = travel_routes.routes(self.stub)

    def call(self, method, path, viewer, body=None):
        return self.r[(method, path)]({}, body, viewer)

    def test_every_console_role_may_open_the_page(self):
        for role in role_scopes.CONSOLE_ROLES:
            self.assertTrue(role_scopes.may_open_page(role, travel_routes.PAGE["id"]))

    def test_round_trips_show_both_flights_and_totals_and_wait_for_approval(self):
        status, out = self.call("POST", "/api/travel/request", "P05", {"text": TEXT})
        self.assertEqual((status, out["ok"], out["status"]), (200, True, "held"))
        trips = out["round_trips"]
        self.assertEqual(len(trips), 3)
        self.assertEqual([t["fare_inr"] for t in trips], sorted(t["fare_inr"] for t in trips))
        window = load_policy()["depart_window"]
        for t in trips:
            self.assertEqual(t["fare_inr"], t["outbound"]["fare_inr"] + t["return"]["fare_inr"])
            self.assertEqual(t["total_inr"], t["fare_inr"] * 3)
            for leg in (t["outbound"], t["return"]):
                self.assertTrue(window["from"] <= leg["depart_time"] <= window["to"])
                self.assertIn(leg["flight_no"], out["letter"])
        self.assertIn("a person", out["letter"])
        self.assertEqual(self.stub.cos.memory.conn.execute("SELECT COUNT(*) FROM travel_bookings").fetchone()[0], 0)
        self.assertEqual(len(self.stub.cos.approvals.pending()), 1)

    def test_one_way_request_has_no_round_trips(self):
        out = self.call("POST", "/api/travel/request", "P03", {"request": "flights for 2 people Delhi to Mumbai on 2026-11-03"})[1]
        self.assertEqual((out["status"], out["round_trips"], len(out["flights"])), ("held", [], 3))

    def test_choose_a_round_trip_then_booking_totals_match(self):
        out = self.call("POST", "/api/travel/request", "P05", {"text": TEXT})[1]
        pick, hotel = out["round_trips"][1], out["hotels"][0]
        status, c = self.call("POST", "/api/travel/choose", "P05",
                              {"request_id": out["request_id"], "flight_option_id": pick["option_id"], "hotel_option_id": hotel["option_id"]})
        self.assertEqual((status, c["total_inr"]), (200, pick["total_inr"] + hotel["total_inr"]))
        bad = self.call("POST", "/api/travel/choose", "P05",
                        {"request_id": out["request_id"], "flight_option_id": out["flights"][0]["option_id"],
                         "hotel_option_id": hotel["option_id"]})
        self.assertEqual((bad[0], bad[1]["ok"]), (400, False))

    def test_csm_and_growth_see_only_their_own_admin_sees_all(self):
        mine = self.call("POST", "/api/travel/request", "P05", {"text": TEXT})[1]
        other = self.call("POST", "/api/travel/request", "P03", {"text": "flights for 2 people Delhi to Mumbai on 2026-11-03"})[1]
        ids = lambda viewer: {x["request_id"] for x in self.call("GET", "/api/travel/requests", viewer)[1]["requests"]}
        self.assertEqual(ids("P05"), {mine["request_id"]})
        self.assertEqual(ids("P03"), {other["request_id"]})
        self.assertEqual(ids("P01"), {mine["request_id"], other["request_id"]})
        self.assertFalse(self.call("GET", "/api/travel/requests", "P05")[1]["all_requests"])
        self.assertTrue(all(x["requester_name"] for x in self.call("GET", "/api/travel/requests", "P01")[1]["requests"]))

    def test_nobody_can_choose_on_another_persons_request(self):
        mine = self.call("POST", "/api/travel/request", "P05", {"text": TEXT})[1]
        status, c = self.call("POST", "/api/travel/choose", "P03", {"request_id": mine["request_id"],
                              "flight_option_id": mine["round_trips"][0]["option_id"], "hotel_option_id": mine["hotels"][0]["option_id"]})
        self.assertEqual((status, c["ok"]), (400, False))

    def test_empty_and_bad_requests_give_plain_errors(self):
        self.assertEqual(self.call("POST", "/api/travel/request", "P05", {"text": " "})[0], 400)
        out = self.call("POST", "/api/travel/request", "P05", {"text": "2 people Mumbai to Goa on 2026-10-28"})[1]
        self.assertEqual((out["ok"], out["status"]), (False, "refused"))


if __name__ == "__main__":
    unittest.main()
