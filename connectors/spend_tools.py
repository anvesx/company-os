"""Read tools for the spend advisor: company cost by category, trip savings and verdicts, travel by team. Team totals only."""
from .tool_reply import DATE_RE, ToolInputError, build_tool, days_before, days_between, str_arg

AREA = "devx-internal"
DEFAULT_DAYS = 90
SALARY_MONTH_DAYS = 30
LATE_DAYS, EARLY_FROM, EARLY_TO = 3, 14, 7     # booked 3 days or less ahead; a cheaper fare 14 to 7 days before
MIN_SAVING_SHARE = 0.30                        # "much cheaper": 30% or more below what was paid
SHORT_FLIGHT_HOURS = 2.5
SAME_CITY_DAYS = 7
HOTEL_OVER_SHARE = 0.10
RULES = ("late_booking", "business_short_flight", "same_city_trips", "hotel_above_city_rate")


def _ok(area_id):
    return area_id == AREA


def _date_arg(args, name):
    value = str_arg(args, name)
    if value is not None and not DATE_RE.match(value):
        raise ToolInputError(f"{name} must look like YYYY-MM-DD")
    return value


def _window(args, as_of):
    """The from and to dates: to is never after as_of; from defaults to 90 days before to."""
    end = min(_date_arg(args, "to") or as_of, as_of)
    start = _date_arg(args, "from") or days_before(end, DEFAULT_DAYS)
    if start > end:
        raise ToolInputError("from is after to")
    return start, end


def _pct(part, whole):
    return round(part * 100 / whole, 1) if whole else 0.0


def _rows(conn, sql, *params):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ---- cost by category ------------------------------------------------------------------------------------------

def _breakdown(conn, start, end):
    days = days_between(end, start) + 1
    pay = conn.execute("SELECT COALESCE(SUM(monthly_salary_inr), 0) FROM people WHERE is_devx = 1").fetchone()[0]
    items = [("salaries", "Salaries, all teams", round(pay * days / SALARY_MONTH_DAYS))]
    for r in _rows(conn, "SELECT v.category AS c, SUM(i.amount_inr) AS s FROM invoices i JOIN vendors v USING(vendor_id) "
                         "WHERE i.date BETWEEN ? AND ? GROUP BY v.category", start, end):
        items.append(("vendor_invoices", f"Vendor invoices: {r['c']}", r["s"]))
    travel = 0
    for r in _rows(conn, "SELECT category AS c, SUM(amount_inr) AS s FROM expenses WHERE date BETWEEN ? AND ? "
                         "GROUP BY category", start, end):
        if r["c"] == "travel":
            travel = r["s"]
        else:
            items.append(("expenses", f"Expenses: {r['c']}", r["s"]))
    legs = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN t.mode = 'flight' THEN t.fare_inr END), 0), "
        "COALESCE(SUM(CASE WHEN t.mode = 'train' THEN t.fare_inr END), 0) FROM trips t JOIN expenses e USING(expense_id) "
        "WHERE e.date BETWEEN ? AND ?", (start, end)).fetchone()
    hotels = conn.execute("SELECT COALESCE(SUM(h.total_inr), 0) FROM hotel_stays h JOIN trips t USING(trip_id) "
                          "JOIN expenses e USING(expense_id) WHERE e.date BETWEEN ? AND ?", (start, end)).fetchone()[0]
    other = travel - legs[0] - legs[1] - hotels
    for key, label, amount in (("flights", "Travel: flights", legs[0]), ("trains", "Travel: trains", legs[1]),
                               ("hotels", "Travel: hotels", hotels), ("other_travel", "Travel: local and other", other)):
        if amount:
            items.append((key, label, amount))
    total = sum(a for _, _, a in items)
    cats = [{"key": k, "label": label, "amount_inr": a, "share_pct": _pct(a, total)}
            for k, label, a in sorted(items, key=lambda x: (-x[2], x[1]))]
    salaries = items[0][2]
    travel_block = {"total_inr": travel, "share_pct": _pct(travel, total),
                    "share_of_non_salary_pct": _pct(travel, total - salaries),
                    "flights_inr": legs[0], "flights_share_pct": _pct(legs[0], total),
                    "trains_inr": legs[1], "trains_share_pct": _pct(legs[1], total),
                    "hotels_inr": hotels, "hotels_share_pct": _pct(hotels, total),
                    "other_inr": other, "other_share_pct": _pct(other, total)}
    return {"from": start, "to": end, "total_inr": total, "categories": cats, "travel": travel_block}


def make_spend_breakdown(data_conn):
    def handler(args, area_id, as_of, ctx):
        start, end = _window(args, as_of)
        return _breakdown(data_conn, start, end)
    return build_tool(
        "spend_breakdown", "Company cost from `from` to `to` (default: last 90 days to as_of) by category: salaries as one total, "
        "vendor invoices by category, expenses by category, and travel split into flights, trains and hotels. "
        "Each with amount and share of the total.", {"from": {"type": "string"}, "to": {"type": "string"}},
        handler, area_ok=_ok, area_label=AREA)


# ---- trip savings ----------------------------------------------------------------------------------------------

def _all_savings(conn, as_of):
    """Every saving on trips that departed by as_of. Each has rule, trip_id, date, paid_inr, saving_inr and the facts."""
    trips = _rows(conn, "SELECT * FROM trips WHERE depart_on <= ? ORDER BY depart_on, trip_id", as_of)
    fares = {}
    for o in _rows(conn, "SELECT o.* FROM fare_options o JOIN trips t USING(trip_id) WHERE t.depart_on <= ?", as_of):
        fares.setdefault(o["trip_id"], []).append(o)
    out = []
    for t in trips:
        opts = fares.get(t["trip_id"], [])
        ahead = days_between(t["depart_on"], t["booked_on"])
        early = [o for o in opts if o["mode"] == t["mode"] and o["cabin"] == t["cabin"]
                 and EARLY_TO <= days_between(t["depart_on"], o["seen_on"]) <= EARLY_FROM]
        if ahead <= LATE_DAYS and "urgent" not in (t["note"] or "").lower() and early:
            best = min(early, key=lambda o: (o["fare_inr"], o["seen_on"], o["option_id"]))
            if t["fare_inr"] - best["fare_inr"] >= MIN_SAVING_SHARE * t["fare_inr"]:
                out.append({"rule": "late_booking", "trip_id": t["trip_id"], "team": t["team"], "date": t["depart_on"],
                            "paid_inr": t["fare_inr"], "cheaper_inr": best["fare_inr"],
                            "saving_inr": t["fare_inr"] - best["fare_inr"], "available_on": best["seen_on"],
                            "carrier": best["carrier"], "booked_on": t["booked_on"], "booked_days_before": ahead,
                            "to_city": t["to_city"]})
        if t["mode"] == "flight" and t["cabin"] == "business" and t["duration_hours"] < SHORT_FLIGHT_HOURS:
            econ = [o for o in opts if o["mode"] == "flight" and o["cabin"] == "economy" and o["seen_on"] == t["booked_on"]]
            best = min(econ, key=lambda o: (o["fare_inr"], o["option_id"])) if econ else None
            if best and best["fare_inr"] < t["fare_inr"]:
                out.append({"rule": "business_short_flight", "trip_id": t["trip_id"], "team": t["team"],
                            "date": t["depart_on"], "paid_inr": t["fare_inr"], "cheaper_inr": best["fare_inr"],
                            "saving_inr": t["fare_inr"] - best["fare_inr"], "available_on": best["seen_on"],
                            "carrier": best["carrier"], "flight_hours": t["duration_hours"], "to_city": t["to_city"]})
    for i, a in enumerate(trips):
        for b in trips[i + 1:]:
            if days_between(b["depart_on"], a["depart_on"]) > SAME_CITY_DAYS:
                break
            if a["team"] == b["team"] and a["to_city"] == b["to_city"]:
                out.append({"rule": "same_city_trips", "trip_id": b["trip_id"], "other_trip_id": a["trip_id"],
                            "team": b["team"], "date": b["depart_on"], "other_date": a["depart_on"],
                            "paid_inr": a["fare_inr"] + b["fare_inr"], "saving_inr": min(a["fare_inr"], b["fare_inr"]),
                            "cheaper_inr": max(a["fare_inr"], b["fare_inr"]), "to_city": b["to_city"]})
    for s in _rows(conn, "SELECT s.*, t.depart_on, t.team, c.policy_rate_inr FROM hotel_stays s JOIN trips t USING(trip_id) "
                         "JOIN city_hotel_rates c USING(city) WHERE t.depart_on <= ?", as_of):
        if s["rate_inr"] > s["policy_rate_inr"] * (1 + HOTEL_OVER_SHARE):
            alts = _rows(conn, "SELECT * FROM hotel_options WHERE stay_id = ? AND hotel != ? ORDER BY rate_inr, option_id",
                         s["stay_id"], s["hotel"])
            out.append({"rule": "hotel_above_city_rate", "trip_id": s["trip_id"], "team": s["team"],
                        "date": s["depart_on"], "paid_inr": s["total_inr"], "city": s["city"], "nights": s["nights"],
                        "rate_inr": s["rate_inr"], "policy_rate_inr": s["policy_rate_inr"],
                        "saving_inr": (s["rate_inr"] - s["policy_rate_inr"]) * s["nights"],
                        "cheaper_inr": s["policy_rate_inr"] * s["nights"],
                        "cheaper_hotel": alts[0]["hotel"] if alts else None,
                        "cheaper_hotel_rate_inr": alts[0]["rate_inr"] if alts else None})
    return sorted(out, key=lambda x: (-x["saving_inr"], x["date"], x["trip_id"], x["rule"]))


def _savings_in(conn, start, end, as_of):
    return [x for x in _all_savings(conn, as_of) if start <= x["date"] <= end]


def make_trip_savings(data_conn):
    def handler(args, area_id, as_of, ctx):
        start, end = _window(args, as_of)
        found = _savings_in(data_conn, start, end, as_of)
        by_rule = {r: {"count": sum(x["rule"] == r for x in found),
                       "saving_inr": sum(x["saving_inr"] for x in found if x["rule"] == r)} for r in RULES}
        return {"from": start, "to": end, "total_saving_inr": sum(x["saving_inr"] for x in found), "by_rule": by_rule,
                "savings": found}
    return build_tool(
        "trip_savings", "Savings found on trips that left from `from` to `to` (default: last 90 days to as_of). Each has the trip id, "
        "date, what was paid, the cheaper option and when it was available, the amount that could have been saved and the "
        "rule. Rules: late_booking, business_short_flight, same_city_trips, hotel_above_city_rate. A late booking marked "
        "urgent is not a saving.", {"from": {"type": "string"}, "to": {"type": "string"}},
        handler, area_ok=_ok, area_label=AREA)


def make_trip_verdicts(data_conn):
    def handler(args, area_id, as_of, ctx):
        trip_id = str_arg(args, "trip_id")
        if trip_id:
            start, end = "2000-01-01", as_of
        else:
            start, end = _window(args, as_of)
        sql = ("SELECT t.trip_id, t.depart_on AS date, t.fare_inr + COALESCE((SELECT SUM(total_inr) FROM hotel_stays h "
               "WHERE h.trip_id = t.trip_id), 0) AS cost_inr FROM trips t WHERE t.depart_on BETWEEN ? AND ?")
        params = [start, end]
        if trip_id:
            sql, params = sql + " AND t.trip_id = ?", params + [trip_id]
        saved = {}
        for x in _savings_in(data_conn, start, end, as_of):
            saved.setdefault(x["trip_id"], []).append(x)
        trips = []
        for r in _rows(data_conn, sql + " ORDER BY t.depart_on, t.trip_id", *params):
            mine = saved.get(r["trip_id"], [])
            trips.append({**r, "verdict": "cheaper_option_existed" if mine else "best_option_chosen",
                          "saving_inr": sum(x["saving_inr"] for x in mine), "rules": sorted({x["rule"] for x in mine})})
        cheaper = [t for t in trips if t["saving_inr"]]
        return {"from": start, "to": end, "trip_count": len(trips), "best_option_count": len(trips) - len(cheaper),
                "cheaper_option_count": len(cheaper), "total_saving_inr": sum(t["saving_inr"] for t in cheaper),
                "trips": trips}
    return build_tool(
        "trip_verdicts", "A verdict for every trip that left from `from` to `to` (default: last 90 days to as_of), or for one "
        "`trip_id`: cheaper_option_existed (with the saving and rules) or best_option_chosen (no cheaper fare or hotel "
        "was available at booking time). Also the counts and total saving.",
        {"from": {"type": "string"}, "to": {"type": "string"}, "trip_id": {"type": "string"}},
        handler, area_ok=_ok, area_label=AREA)


# ---- travel by team --------------------------------------------------------------------------------------------

def make_travel_by_team(data_conn):
    def handler(args, area_id, as_of, ctx):
        start, end = _window(args, as_of)
        teams = _rows(data_conn,
                      "SELECT e.team, SUM(e.amount_inr) AS travel_inr, "
                      "COALESCE(SUM((SELECT SUM(fare_inr) FROM trips t WHERE t.expense_id = e.expense_id AND t.mode = 'flight')), 0) AS flights_inr, "
                      "COALESCE(SUM((SELECT SUM(fare_inr) FROM trips t WHERE t.expense_id = e.expense_id AND t.mode = 'train')), 0) AS trains_inr, "
                      "COALESCE(SUM((SELECT SUM(h.total_inr) FROM hotel_stays h JOIN trips t USING(trip_id) "
                      "WHERE t.expense_id = e.expense_id)), 0) AS hotels_inr, "
                      "COALESCE(SUM((SELECT COUNT(*) FROM trips t WHERE t.expense_id = e.expense_id)), 0) AS trips "
                      "FROM expenses e WHERE e.category = 'travel' AND e.date BETWEEN ? AND ? GROUP BY e.team "
                      "ORDER BY travel_inr DESC, e.team", start, end)
        total = sum(t["travel_inr"] for t in teams)
        for t in teams:
            t["other_inr"] = t["travel_inr"] - t["flights_inr"] - t["trains_inr"] - t["hotels_inr"]
            t["share_of_travel_pct"] = _pct(t["travel_inr"], total)
        return {"from": start, "to": end, "travel_total_inr": total, "teams": teams}
    return build_tool(
        "travel_by_team", "Travel cost per team from `from` to `to` (default: last 90 days to as_of): total, flights, trains, "
        "hotels, other, trip count and share of all travel. Team totals only.",
        {"from": {"type": "string"}, "to": {"type": "string"}}, handler, area_ok=_ok, area_label=AREA)


def spend_tools(data_conn):
    return [make_spend_breakdown(data_conn), make_trip_savings(data_conn), make_trip_verdicts(data_conn),
            make_travel_by_team(data_conn)]
