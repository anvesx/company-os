# runtime

**Role in the harness:** Our thin agent runtime: the loop that calls the model through the gateway, runs tools through the plugin hooks, and logs every step.

Our thin agent runtime. It implements `contract.plugin_contract.Host`, so plugins and agent packs never import it directly.

Files:
- `agent_loop.py`: `Runtime(gateway, memory_store, way_in_gate, plugins=(), max_steps=12, retries=2, clock=None)`.
- `tool_registry.py`: holds tool specs, returns them sorted by name (keeps the cached prefix stable).
- `tool_output_cap.py`: `cap_output` cuts a tool result to 8,000 characters and adds a note.

Flow of `run_task(task)`: `open_run` (way-in gate, start run) -> `run_loop` -> `close_run`.
Each loop step: build request, `before_request`, gateway call (retry `TransientModelError` up to `retries`),
`after_reply`, then for each tool call `before_tool` (deny, ask or allow), run, cap, `after_tool`.
- deny: the tool does not run; the result is `denied: <reason>`.
- ask: the tool does not run; the run ends with status `held`.
- Unknown tool or tool exception: the result is `error: ...`.
Every model call and tool call is written with `memory_store.log_step`.

The lifecycle kit uses `open_run`, `run_loop`, `invoke_tool` and `close_run` to run one task in steps.
`invoke_tool` runs the same hooks as a model tool call.
The memory object needs `start_run`, `log_step`, `end_run`, `scoped`. The way-in gate needs `admit(task) -> Decision`.

## Files in this folder

| File | What it does |
|---|---|
| `agent_loop.py` | Our thin agent runtime: the loop, the tool checks, and the run log. Implements the contract's Host. |
| `tool_output_cap.py` | Cap a tool result so one tool cannot flood the model's context. |
| `tool_registry.py` | Holds the tool specs. The list sent to the model is sorted by name so the cached prefix stays stable. |

## Compaction (`compaction.py`)

`compact_if_needed(messages, *, window_tokens, model_call, threshold=0.8, keep_recent=6)` returns `(messages, CompactionNote | None)`.
- Below `threshold * window_tokens` (estimate: 4 characters per token) it returns the messages unchanged.
- Above it, the first message and the last `keep_recent` messages stay. The cut moves earlier so a tool result keeps its tool call.
- The middle becomes one user message: a summary from `model_call(messages) -> str` plus a code-made list of decision lines, ids and numbers.
- It never touches the system prompt or tool list, so the prompt cache stays valid. Design adapted from dsh (see `THIRD_PARTY_NOTICES.md`).
- If `model_call` raises, the error goes up. The loop is not changed here; I1 adds the hook.
