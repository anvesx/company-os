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
     "intro": "CSMs are DevX's project managers. Meeting prep tells the CSM what to settle before a client call.",
     "notes": ["People, bandwidth and allocation already live in DevX's own console (console.devxlabs.ai/employees). "
               "This console does not repeat that."],
     "scenarios": [
         _s("csm-prep", "Prep me for my client call",
            "Client sync with Finvault Pay on 2026-10-21.",
            "Look for the questions to settle in the private brief.",
            "meeting_prep", "P06", "C02", {"event_id": "EV113"}),
         _s("csm-approvals", "My approvals", "Follow-ups the agents propose wait for a CSM to approve.",
            "Open the Approvals page, then approve or deny one.", None, None, None, link="approvals",
            for_agents=("meeting_prep",)),
     ]},
    {"id": "cto", "title": "CTO", "view_as": "P02",
     "intro": "See what every agent run did, what it cost, how often the saved-prefix cache helped, and what the guardrails allowed, denied or held.",
     "notes": ["The live panel below updates after every run. Use Home or Departments to create runs first."],
     "scenarios": [
         _s("cto-refused-role", "See how a refusal looks",
            "An engineer (Arjun Singh) tries to start the finance watch agent. Only the finance lead, the CEO and the R&D lead may.",
            "Look for a refused run with the reason in plain words. This one runs as Arjun on purpose.",
            "finance_watch", "P11", "devx-internal", as_named=True),
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
    "meeting_prep": {"area_id": "C02", "as_of": "2026-10-19", "event_id": "EV113",
                     "what": "Finvault Pay has a client sync (EV113) on 2026-10-21"},
}


def demo_for(agent):
    """The prefilled form values and the one plain line that explains them, or None if the agent has no demo."""
    d = AGENT_DEMOS.get(agent)
    if d is None:
        return None
    return {**d, "line": f"Showing {d['as_of']}, when {d['what']}. Change the date to try other days."}
