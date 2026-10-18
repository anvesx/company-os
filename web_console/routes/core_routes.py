"""The shell's own routes: people, pages, run story, Approvals, Runs and the demo controls (clock, pause, reset)."""
PAGE = {"id": "home", "title": "Home", "order": 0, "icon": "home"}
# Path to the page that gates it. None means any of the three people; the handler then checks the data itself.
ROUTE_PAGES = {"/api/console/pages": None, "/api/run": None, "/api/console/home": "home",
               "/api/console/approvals": "approvals", "/api/console/approvals/decide": "approvals",
               "/api/console/runs": "runs", "/api/console/next_day": "runs", "/api/console/pause": "runs",
               "/api/console/resume": "runs", "/api/console/reset": "runs", "/api/console/state": None}


def routes(console):
    def pages(q, body, viewer):
        return 200, {"ok": True, "pages": console.pages_for(viewer), "privacy": "Nothing here is used to rate people."}

    def state(q, body, viewer):
        return 200, {"ok": True, "now": console.cos.clock.now, "today": console.cos.clock.today,
                     "paused": console.cos.way_in.paused}

    def run_story(q, body, viewer):
        run_id = q.get("id", "")
        if console.cos.memory.get_run(run_id) is None:
            return 404, {"ok": False, "error": "I could not find that run."}
        if not console.may_see_run(viewer, run_id):
            return 403, {"ok": False, "error": "This run is not one this person may open."}
        return 200, console.run_detail(run_id)

    def home(q, body, viewer):
        mine = [a for a in console.approvals(viewer)["approvals"] if a["status"] == "pending"]
        return 200, {"ok": True, "pending_approvals": len(mine)}

    def approvals(q, body, viewer):
        return 200, console.approvals(viewer)

    def decide(q, body, viewer):
        return console.decide((body or {}).get("approval_id"), bool((body or {}).get("approve")), viewer)

    def runs(q, body, viewer):
        return 200, console.runs()

    def reset(q, body, viewer):
        return 200, console.reset()

    return {("GET", "/api/console/pages"): pages, ("GET", "/api/console/state"): state, ("GET", "/api/run"): run_story,
            ("GET", "/api/console/home"): home, ("GET", "/api/console/approvals"): approvals,
            ("POST", "/api/console/approvals/decide"): decide, ("GET", "/api/console/runs"): runs,
            ("POST", "/api/console/next_day"): lambda q, b, v: (200, console.next_day()),
            ("POST", "/api/console/pause"): lambda q, b, v: (200, console.set_paused(True)),
            ("POST", "/api/console/resume"): lambda q, b, v: (200, console.set_paused(False)),
            ("POST", "/api/console/reset"): reset}
