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
    "project_risk": {
        "title": "Project risk",
        "department": "CSMs",
        "summary": "Looks for trouble on client projects early and tells the project's CSM in a private message.",
        "watches": [
            "Hours logged are over 115% of the SOW estimate while 30% or more of tasks are open.",
            "The client has written nothing in the shared channel for 14 days or more (not on paused projects).",
            "5 or more open tasks are past their due date.",
            "One person logged over 55 hours a week for 3 weeks in a row (a flag only).",
            "A SOW change the client has not accepted adds more hours than are left.",
        ],
        "acts": "Every day on a timer, for each client. A CSM, project lead, CEO or R&D lead can also ask. If nothing is wrong, it stays quiet.",
        "tells": "The project's CSM, in one private message. A flag that names one person goes only to that project's CSM.",
        "never": [
            "Build a people, bandwidth or allocation report. DevX's existing console (console.devxlabs.ai/employees) does that.",
            "Message anyone outside DevX, or read another client's data.",
            "Create a task on its own. A follow-up waits for a CSM or the CEO to approve.",
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
    "fraud_watch": {
        "title": "Store watch",
        "department": "CSMs (retail client)",
        "summary": "Compares each staff member at the retail client's stores with their store's normal, and tells the client's CSM.",
        "watches": [
            "Many cash refunds by one person.",
            "Discounts approved by the person who asked for them.",
            "Repeated free remakes by one person.",
        ],
        "acts": "Every day on a timer, or when the retail client's CSM or the CEO asks. If nothing is unusual, it stays quiet.",
        "tells": "The retail client's DevX CSM. Store managers are client staff, so agents may not message them.",
        "never": [
            "Accuse anyone or say what a person meant to do. It says 'unusual pattern' and shows the evidence.",
            "Use words such as fraud or theft.",
            "Read any other client's data.",
        ],
    },
    "hiring_forecast": {
        "title": "Hiring forecast",
        "department": "HR",
        "summary": "Forecasts which team runs short of hours in the next 4 to 8 weeks and when to start hiring.",
        "watches": [
            "Current hours booked per team (from time logs).",
            "Hours left on active projects' SOWs.",
            "Won deals and late-stage proposals that will bring new work.",
            "Which teams have spare hours.",
        ],
        "acts": "On a timer, or when HR or the CEO asks.",
        "tells": "The CEO and the team's manager. HR sees team-level numbers only.",
        "never": [
            "Show one person's hours or pay. Teams only.",
            "Message anyone outside DevX.",
        ],
    },
    "delivery_progress": {
        "title": "Delivery progress",
        "department": "CSMs",
        "summary": "Works out how far each client project really is against the signed scope, from code evidence and not from what people report.",
        "watches": [
            "Each scope item: not started, in progress, done or at risk.",
            "The finish date at the current pace, against the planned end.",
            "Merged work that links to no task or scope item (unbilled work).",
            "A scope item changed 4 or more times after client meetings (rework).",
            "30% or more of the calendar used while the merged share is far behind.",
        ],
        "acts": "Every day on a timer for each client, and when a code change is merged. A CSM, project lead, CEO or R&D lead can also ask.",
        "tells": "The project's CSM, in one private message. It also saves a progress snapshot per project into company memory.",
        "never": [
            "Measure or rank individual developers. No counts or lines per person.",
            "Message anyone outside DevX, or read another client's data.",
            "Send the same flag again within 7 days.",
        ],
    },
    "client_requests": {
        "title": "Client requests",
        "department": "CSMs and developers",
        "summary": "Chases the things developers need from clients, such as store access, DNS, cloud roles, keys and decisions, so work is not blocked.",
        "watches": [
            "What developers need from clients: Shopify access, DNS changes, cloud roles, keys and decisions.",
            "Requests that have been waiting too long for an answer.",
            "Whether the access a client gave really works.",
        ],
        "acts": "Once a day in a batch. After the CSM approves, it asks the client once with clear steps, then reminds and escalates.",
        "tells": "Developers and CSMs.",
        "never": [
            "Copy or store a password.",
            "Ask the client before the CSM approves.",
            "Send many separate messages to the client in one day.",
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
