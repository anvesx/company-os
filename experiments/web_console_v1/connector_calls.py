"""Calls a connector read tool outside an agent run, for the console pages. The tool still checks the area itself."""
import json
from types import SimpleNamespace


def read_tool(tools, name, area_id, args, as_of):
    """Run one read tool for one client area as of a date. Returns its JSON reply, or {} when the tool refuses."""
    tool = next(t for t in tools if t.name == name)
    ctx = SimpleNamespace(task=SimpleNamespace(area_id=area_id, inputs={"as_of": as_of}))
    reply = json.loads(tool.fn({**args, "as_of": as_of}, ctx))
    return {} if "error" in reply else reply
