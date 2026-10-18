"""Replay exam: ask the spend advisor about each planted saving's day; score found, missed and false alarms.

Only this file and the tests read the answer key.
"""
import json
import os

from company_data import DB_PATH
from wiring.build_company_os import build_company_os

KEY_PATH = os.path.join(os.path.dirname(DB_PATH), "answer_keys.json")
AGENT, AREA, CALLER = "spend_advisor", "devx-internal", "P01"
QUESTION = "Where can we save on travel?"


def _answer(cos, day):
    """The letter and the saving lines the agent gave for one day. A failed run gives nothing."""
    result = cos.run(AGENT, CALLER, AREA, inputs={"question": QUESTION, "from": day, "to": day, "as_of": day})
    if result.status != "done":
        return ""
    return json.loads(result.final_text)["answer"]


def run_exam(cos=None) -> dict:
    cos = cos or build_company_os(agents=(AGENT,))
    with open(KEY_PATH) as fh:
        key = json.load(fh)["spend_advisor"]
    amounts = {"late_booking": "Booking a week earlier", "business_short_flight": "Economy would have saved",
               "same_city_trips": "One trip could have done both", "hotel_above_city_rate": "city rate is"}
    found, missed, false_alarms = [], [], []
    for case in key["cases"]:
        text = _answer(cos, case["first_detectable_on"])
        lines = [ln for ln in text.splitlines() if ln.startswith(case["trip_ids"][0] + " (") and amounts[case["signal"]] in ln]
        (found if lines else missed).append(case["case_id"])
    for la in key["look_alikes"]:
        text = _answer(cos, la["first_detectable_on"])
        tid = la["trip_ids"][0]
        flagged = [ln for ln in text.splitlines() if ln.startswith(tid + " (") and "No cheaper alternative" not in ln]
        if flagged:
            false_alarms.append(la["case_id"])
    metrics = {"cases": len(key["cases"]), "found": len(found), "missed": len(missed),
               "look_alikes": len(key["look_alikes"]), "false_alarms": len(false_alarms),
               "recall": round(len(found) / len(key["cases"]), 3)}
    for name, value in metrics.items():
        cos.memory.add_score("replay", AGENT, name, value, detail={"missed": missed, "false_alarms": false_alarms})
    return {**metrics, "found_ids": found, "missed_ids": missed, "false_alarm_list": false_alarms}


if __name__ == "__main__":
    print(json.dumps(run_exam(), indent=1))
