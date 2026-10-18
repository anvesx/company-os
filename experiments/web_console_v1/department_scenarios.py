"""The "Try it" scenarios for each department: which agent runs, as whom, on which client, with which dates."""

# Dates were picked from the planted cases (company_data/answer_keys.json) so something real shows up.


def _s(sid, title, situation, look_for, agent, caller_id, area_id, inputs=None, **extra):
    return {"id": sid, "title": title, "situation": situation, "look_for": look_for, "agent": agent,
            "caller_id": caller_id, "area_id": area_id, "inputs": inputs or {}, **extra}


DEPARTMENTS = [
    {"id": "finance", "title": "Finance", "view_as": "P07",
     "intro": "Finance watch reads DevX's books and tells the finance lead about money that needs a look. It never moves money.",
     "notes": [], "scenarios": [
         _s("fin-duplicate", "Duplicate invoice",
            "A vendor sends the same bill twice within 10 days, and DevX could pay twice.",
            "Look for INV020 and INV023 from the same vendor, same amount, a few days apart.",
            "finance_watch", "P07", "devx-internal", {"as_of": "2026-06-15"}),
         _s("fin-new-vendor", "New vendor paid a lot",
            "A vendor set up in the last 30 days gets a payment over 5 lakh INR.",
            "Look for PAY030 to a vendor that was created only days before.",
            "finance_watch", "P07", "devx-internal", {"as_of": "2026-07-31"}),
         _s("fin-budget", "Budget overrun",
            "A team spends more than its budget in one month and category.",
            "Look for the design team's hardware spend in August 2026.",
            "finance_watch", "P07", "devx-internal", {"as_of": "2026-08-31"}),
         _s("fin-travel", "Travel share of salary",
            "A team's travel in a month is over 20% of what the team costs in pay. Only team totals are shown.",
            "Look for the growth team in September 2026.",
            "finance_watch", "P07", "devx-internal", {"as_of": "2026-09-14"}),
         _s("fin-save-travel", "Where can we save on travel?",
            "The CEO asks where travel money goes. The agent gives the cost split, a verdict for every trip and what a cheaper booking would have saved.",
            "Look for the trip totals line, the biggest savings with dates and amounts, and the policy suggestions.",
            "spend_advisor", "P07", "devx-internal", {"question": "Where can we save on travel?"}),
         _s("fin-quiet", "A quiet day",
            "Most days nothing needs a look. The agent then stays quiet and makes no model call.",
            "Look for a run marked quiet, with no message sent.",
            "finance_watch", "P07", "devx-internal", {"as_of": "2026-05-20"}),
     ]},
    {"id": "hr", "title": "HR", "view_as": "P90",
     "intro": "Hiring forecast shows which team runs short of hours soon, given signed work and won deals. HR sees team numbers only, never one person's hours or pay.",
     "notes": ["Privacy: the agent reports teams, not people."],
     "scenarios": [
         _s("hr-short", "Which team runs short in 4 to 8 weeks?",
            "Won deals will start soon. Does a team have too little time for them?",
            "Look for a team that is over-allocated when the won deals start.",
            "hiring_forecast", "P90", "devx-internal", {"as_of": "2026-10-19"}),
         _s("hr-when", "When should we start hiring?",
            "Hiring takes about 4 weeks, so the start date is earlier than the short week.",
            "Look for a suggested hiring start date next to the short team.",
            "hiring_forecast", "P90", "devx-internal", {"as_of": "2026-10-19"}),
         _s("hr-spare", "Which team has spare hours?",
            "A team with free hours can take new work or help another team.",
            "Look for the team with 15% or more of its usable hours free.",
            "hiring_forecast", "P90", "devx-internal", {"as_of": "2026-10-19"}),
     ],
     "planned": [{"title": "Team knowledge agent (new joinee KT)",
                  "text": "Planned, not built yet. It would help a new joinee learn a project from past meetings and decisions."}]},
    {"id": "growth", "title": "Growth", "view_as": "P04",
     "intro": "Meeting prep tells you what to settle with a client before your call, so requirements are agreed early.",
     "notes": [], "scenarios": [
         _s("growth-ev113", "Prep me for my client call (EV113)",
            "Client sync with Finvault Pay on 2026-10-21 about the Mobile Wallet.",
            "Look for questions to settle, each pointing to an earlier meeting item.",
            "meeting_prep", "P04", "C02", {"event_id": "EV113"}),
         _s("growth-ev114", "Prep me for my client call (EV114)",
            "Sprint review with Tailorbird Menswear on 2026-10-22 about the POS rollout.",
            "Look for open questions and what changed since last time.",
            "meeting_prep", "P03", "C01", {"event_id": "EV114"}),
     ]},
    {"id": "csm", "title": "CSMs", "view_as": "P06",
     "intro": "CSMs are DevX's project managers. Agents watch client projects and tell the CSM in private.",
     "notes": ["People, bandwidth and allocation already live in DevX's own console (console.devxlabs.ai/employees). "
               "This console does not repeat that. Here you see only what the agents flag for you.",
               "Privacy: a flag that names one person goes only to that project's CSM."],
     "scenarios": [
         _s("csm-over-sow", "Project is over its SOW hours",
            "Hours logged are well over the signed estimate while many tasks are still open.",
            "Look for Mobile Wallet (PR03): evidence in numbers, why it matters, a next step.",
            "project_risk", "P06", "C02"),
         _s("csm-silent", "Client has gone silent",
            "The client wrote nothing in the shared channel for 14 days or more on an active project.",
            "Look for Supplier Portal (PR04) and the number of days silent.",
            "project_risk", "P06", "C03"),
         _s("csm-overdue", "Many overdue tasks",
            "Five or more open tasks are past their due date.",
            "Look for Patient Booking App (PR05) and the list of late tasks.",
            "project_risk", "P05", "C04"),
         _s("csm-overload", "Overload alert (as a flag)",
            "One person logged over 55 hours a week for 3 weeks. The agent only raises a flag. "
            "The full bandwidth view lives in the existing DevX console.",
            "Look for the flag that names one person. It goes only to this project's CSM.",
            "project_risk", "P05", "C01", {"as_of": "2026-10-05"}),
         _s("csm-sow-change", "SOW change impact",
            "A change the client has not accepted would add more hours than are left.",
            "Look for the flag about a SOW change on Mobile Wallet (PR03).",
            "project_risk", "P06", "C02"),
         _s("csm-prep", "Prep me for my client call",
            "Client sync with Finvault Pay on 2026-10-21.",
            "Look for the questions to settle in the private brief.",
            "meeting_prep", "P06", "C02", {"event_id": "EV113"}),
         _s("csm-store", "Store activity at the retail client",
            "The store watch compares staff with their store's normal and tells the client's CSM.",
            "Look for an unusual-pattern note with evidence, and no accusation.",
            "fraud_watch", "P05", "C01"),
         _s("csm-approvals", "My approvals", "Follow-ups the agents propose wait for a CSM to approve.",
            "Open the Approvals page, then approve or deny one.", None, None, None, link="approvals",
            for_agents=("project_risk", "delivery_progress", "client_requests", "meeting_prep")),
     ]},
    {"id": "cto", "title": "CTO", "view_as": "P02",
     "intro": "See what every agent run did, what it cost, how often the saved-prefix cache helped, and what the guardrails allowed, denied or held.",
     "notes": ["The live panel below updates after every run. Use Home or Departments to create runs first."],
     "scenarios": [
         _s("cto-refused-role", "See how a refusal looks",
            "An engineer (Arjun Singh) tries to start the project risk agent. Only CSMs, project leads, the CEO and the CTO may.",
            "Look for a refused run with the reason in plain words. This one runs as Arjun on purpose.",
            "project_risk", "P11", "C02", as_named=True),
         _s("cto-refused-area", "A refusal for another client",
            "A growth person asks for a client they do not work with.",
            "Look for a refused run: no access to that client's area.",
            "meeting_prep", "P03", "C03", {"event_id": "EV111"}, as_named=True, listed=False),
     ]},
]


def find_scenario(scenario_id):
    for dept in DEPARTMENTS:
        for s in dept["scenarios"]:
            if s["id"] == scenario_id:
                return s
    return None


def all_scenarios():
    return [s for d in DEPARTMENTS for s in d["scenarios"]]


# The form on the Agents page opens on these, so "Run me now" finds something real. A person can change any field.
AGENT_DEMOS = {
    "finance_watch": {"area_id": "devx-internal", "as_of": "2026-06-15",
                      "what": "a vendor sends the same bill twice (INV020 and INV023)"},
    "hiring_forecast": {"area_id": "devx-internal", "as_of": "2026-10-19",
                        "what": "won deals start soon and a team may run short of hours"},
    "meeting_prep": {"area_id": "C02", "as_of": "2026-10-19", "event_id": "EV113",
                     "what": "Finvault Pay has a client sync (EV113) on 2026-10-21"},
    "project_risk": {"area_id": "C02", "as_of": "2026-10-19",
                     "what": "Mobile Wallet is over its SOW hours"},
    "fraud_watch": {"area_id": "C01", "as_of": "2026-10-19",
                    "what": "a store has an unusual discount pattern"},
    "delivery_progress": {"area_id": "C01", "as_of": "2026-08-26",
                          "what": "three merged PRs on Ecommerce Revamp match no scope item"},
    # client_requests has no scenario yet, so its form keeps today's date.
}


def demo_for(agent):
    """The prefilled form values and the one plain line that explains them, or None if the agent has no demo."""
    d = AGENT_DEMOS.get(agent)
    if d is None:
        return None
    return {**d, "line": f"Showing {d['as_of']}, when {d['what']}. Change the date to try other days."}
