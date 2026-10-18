"""What one person may do in the console. Every answer comes from the guardrail policy and the people directory."""
INTERNAL_AGENTS = ("finance_watch", "spend_advisor")
INTERNAL_AREA = "devx-internal"
COST_ROLES = ("ceo", "rnd_lead")


def _role(console, person_id):
    role = console._role(person_id) if person_id else None
    return None if role in (None, "system") else role


def may_start(console, person_id, agent):
    role = _role(console, person_id)
    return bool(role and console.cos.policy.may_start(role, agent))


def allowed_areas(console, person_id):
    """Existing areas (not the hold area) that the directory lets this person read."""
    allowed = console.cos.directory.client_access(person_id) if _role(console, person_id) else set()
    return [a for a in console.state()["areas"] if a["area_id"] in allowed]


def agent_areas(console, person_id, agent):
    """Area ids this person may point this agent at: DevX internal for internal agents, else allowed client areas."""
    if not may_start(console, person_id, agent):
        return []
    areas = allowed_areas(console, person_id)
    if agent in INTERNAL_AGENTS:
        return [a["area_id"] for a in areas if a["area_id"] == INTERNAL_AREA]
    return [a["area_id"] for a in areas if a["kind"] == "client"]


def run_error(console, person_id, agent, area_id):
    """A plain sentence when this person may not start this agent on this area, else None."""
    name = console._name(person_id)
    if _role(console, person_id) is None:
        return "Choose a person first."
    if not may_start(console, person_id, agent):
        return f"{name} does not start the {console._title(agent).lower()} agent, so it is not offered. Nothing was run."
    if area_id not in agent_areas(console, person_id, agent):
        return f"{name} does not work on that area, so it is not offered. Nothing was run."
    return None


def scenario_offered(console, person_id, s):
    if s.get("listed") is False:
        return False
    if s.get("link"):
        role = _role(console, person_id)
        return bool(role and any(console.cos.policy.may_approve(role, a) for a in s.get("for_agents", console.agents)))
    if not s.get("agent"):
        return False
    if s.get("as_named"):
        return _role(console, person_id) in COST_ROLES
    return run_error(console, person_id, s["agent"], s["area_id"]) is None


def offered_scenarios(console, person_id):
    from .department_scenarios import all_scenarios
    return [s["id"] for s in all_scenarios() if scenario_offered(console, person_id, s)]


def permissions_for(console, person_id):
    if not console.cos.directory.get(person_id):
        return {"ok": False, "error": "Unknown person."}
    role = _role(console, person_id)
    person = next((p for p in console.people() if p["person_id"] == person_id), {})
    agents = [a for a in console.agents if may_start(console, person_id, a)]
    scenarios = offered_scenarios(console, person_id)
    from .department_scenarios import DEPARTMENTS
    return {"ok": True, "person_id": person_id, "name": person.get("name"), "role": role,
            "role_label": person.get("role_label"), "agents": agents,
            "areas": allowed_areas(console, person_id),
            "agent_areas": {a: agent_areas(console, person_id, a) for a in agents},
            "approve_agents": [a for a in console.agents if role and console.cos.policy.may_approve(role, a)],
            "scenarios": scenarios,
            "departments": [d["id"] for d in DEPARTMENTS if any(s["id"] in scenarios for s in d["scenarios"])],
            "can_ask_in_words": may_start(console, person_id, "meeting_prep"),
            "can_ask_finance": may_start(console, person_id, "spend_advisor"),
            "sees_costs": role in COST_ROLES}
