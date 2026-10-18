"""Loads the recorded real-Claude runs (real_model_samples.json) so the console can show them beside the fake brain."""
import json
import os

SAMPLES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_model_samples.json")
SAMPLE_KEYS = ("area_id", "as_of", "inputs", "status", "reason", "final_text", "letters", "approvals", "walkthrough",
               "calls", "seconds")


def load_real_samples(path=None):
    """The recorded samples as a dict, or None when the file is missing or unreadable (then the console shows nothing)."""
    try:
        with open(path or SAMPLES_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    samples = data.get("samples") if isinstance(data, dict) else None
    if not isinstance(samples, dict) or not samples:
        return None
    clean = {}
    for agent, s in samples.items():
        if not isinstance(s, dict):
            continue
        item = {k: s.get(k) for k in SAMPLE_KEYS}
        item["letters"] = [dict(m, agent=agent) for m in (s.get("letters") or []) if isinstance(m, dict)]
        item["approvals"] = s.get("approvals") or []
        walk = s.get("walkthrough")
        item["walkthrough"] = dict(walk, agent=walk.get("agent") or agent) if isinstance(walk, dict) and walk.get("steps") else None
        clean[agent] = item
    return {"generated_at": data.get("generated_at"), "model": data.get("model"), "samples": clean} if clean else None
