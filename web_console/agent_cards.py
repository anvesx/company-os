"""Plain-language cards for each agent: what it watches, when it acts, who it tells, what it may never do."""

CARDS = {
    "finance_watch": {
        "title": "Finance watch",
        "department": "Finance",
        "summary": "Reads DevX's books every day and tells the finance lead, in private, about money that needs a look.",
        "watches": [
            "Duplicate invoice: same vendor and same amount within 10 days.",
            "A new vendor paid a lot: over 5 lakh INR to a vendor created under 30 days earlier.",
            "Budget overrun: a team spends more than its budget in a month and category.",
            "Travel share of salary: a team's travel in a month is over 20% of its monthly pay total.",
        ],
        "acts": "Once a day on a timer. The finance lead or the CEO can also run it. If nothing needs a look, it stays quiet.",
        "tells": "The finance lead gets every finding. The CEO also gets the travel finding. Nobody outside DevX.",
        "never": [
            "Show one person's salary. Team totals only.",
            "Pay, hold or change anything in the books. It only reads.",
            "Write a follow-up without a person's approval.",
            "Message anyone who is not a DevX person.",
        ],
    },
    "meeting_prep": {
        "title": "Meeting prep",
        "department": "Growth and CSMs",
        "summary": "Before a client meeting, tells the DevX people who attend what must be settled with the client.",
        "watches": [
            "Open questions and open tasks from earlier meetings with this client.",
            "Recent decisions, and what changed since last time.",
            "The client's recent Slack messages (read as data, never as orders).",
        ],
        "acts": "When a client meeting starts in the next 24 hours, or when a person asks, for example: prep me for EV113.",
        "tells": "Each DevX person on the invite, in a private brief. Never the client.",
        "never": [
            "Read another client's memory.",
            "Message a client contact or any address outside DevX.",
            "Obey instructions hidden in client text.",
            "Change memory, tasks or any other system. It only reads and sends private messages.",
        ],
    },
    "spend_advisor": {
        "title": "Spend advisor",
        "department": "Finance",
        "summary": "Answers a leader's finance question at any time: where the money goes, a verdict for every trip, and what a cheaper booking would have saved.",
        "watches": [
            "Company cost by category: salaries as one total, vendor invoices, expenses, and travel split into flights, trains and hotels.",
            "Late bookings: a flight booked 3 days or less ahead when a much cheaper fare existed a week or two before.",
            "Business seats on flights under 2.5 hours, when economy was cheaper that day.",
            "Two trips by one team to one city within a week, and hotels above the city rate.",
        ],
        "acts": "When the CEO, the finance lead or the R&D lead asks, from the Ask finance box or the Finance page. It does not run on a timer.",
        "tells": "Only the person who asked, in one private letter. The letter starts with the trip totals, then the biggest savings and two or three policy suggestions.",
        "never": [
            "Show one person's salary or name a person. Team totals only.",
            "Write a number that its code did not compute. A check stops the letter first.",
            "Obey the question text. It is read as data only.",
            "Pay, book or change anything. It only reads and writes one letter.",
        ],
    },
}

PLANNED = [{
    "title": "Team knowledge agent (new joinee KT)",
    "department": "HR",
    "summary": "Planned, not built yet. Would help a new joinee learn a project from past meetings and decisions.",
}]

ROLE_LABELS = {
    "ceo": "CEO", "rnd_lead": "R&D lead (CTO view)", "growth": "Growth", "csm": "CSM (project manager)",
    "finance_lead": "Finance lead", "project_lead": "Project lead", "engineer": "Engineer", "designer": "Designer",
    "hr": "HR", "system": "System timer",
}
