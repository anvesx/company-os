# gateway

**Role in the harness:** The AI gateway: the only path from the runtime to a model. It routes the call, simulates the prompt cache, prices every call and enforces budgets.

The AI gateway. It is the only path from our code to a model. The runtime holds a `Gateway`, never a backend.

Files:
- `model_gateway.py`: `Gateway`, `BudgetExceeded`, `TransientModelError`.
- `model_prices.py`: price table (USD per million tokens) and `cost_usd(model, usage)`.
- `prompt_cache.py`: `PromptCache` simulates the 5-minute prompt cache; a miss names what changed.
- `cost_ledger.py`: `CostLedger` records every call and holds budgets (`agent:<name>`, `caller:<id>`).
- `fake_model.py`: `FakeModel(brains)`, a deterministic model for tests and demos.
- `claude_cli_model.py`: `ClaudeCliModel`, a real model through `claude -p`. Tests use a fake runner and never call it.
- `fixed_clock.py`: `FixedClock`, a clock that moves only with `advance(minutes)`.

Use:
```python
gw = Gateway({"fake": FakeModel({"my_agent": brain})})
gw.ledger.set_budget("agent:my_agent", 1.00)
reply = gw.call(req, agent="my_agent", caller_id="P01", area_id="C01", run_id="r1")
```
A backend is any object with `complete(req, agent) -> ModelReply`. The gateway picks it by `req.model`.
`input_tokens` in the ledger is the uncached part only. Cache read and write tokens are priced separately.

## Use a real model

Any agent can run with a real Claude model. Only the gateway backend changes.
```python
cos = build_company_os(real_model="claude-cli")           # registers ClaudeCliModel under "claude-cli"
cos.run("finance_watch", "P07", "devx-internal", model="claude-cli")
```
- It calls `claude -p --output-format json --model sonnet` and uses the person's own Claude plan. No API key is read.
- The prompt holds the system text, the tool list (JSON schema) and the conversation. The model must answer with JSON: `{"tool_calls": [...]}` or `{"final": "<text>"}`.
- A reply that cannot be read gets one retry with the parse error. A timeout, a non-zero exit or a second bad reply raises `TransientModelError`, and the runtime retries.
- Usage comes from the CLI. If the CLI gives none, it is estimated as characters / 4 (`ClaudeCliModel.estimated_calls` counts these).
- Cost is priced as `sonnet-5-5` (the `claude-cli` alias in `model_prices.py`).
- Tests pass a fake `runner=`, so they never start the CLI.
- Vertex (or any other host) would be one more backend of the same shape: a class with `complete(req, agent)`, passed in `extra_backends`.

## Files in this folder

| File | What it does |
|---|---|
| `claude_cli_model.py` | Real model through the `claude -p` CLI (the person's Claude plan). JSON text protocol for tools, one retry on a bad reply, injectable runner. Not called in tests. |
| `cost_ledger.py` | Cost ledger: one row per model call, plus budgets per agent or per caller. |
| `fake_model.py` | Fake model for tests and demos. A brain per agent stands in for the model's judgement. |
| `fixed_clock.py` | A tiny clock for tests and demos. Time moves only when advance() is called. |
| `model_gateway.py` | AI gateway: the only path to a model. Routes by model name, counts cache and cost, enforces budgets. |
| `model_prices.py` | Model price table (USD per million tokens) and the cost of one call. |
| `prompt_cache.py` | Simulated prompt cache: tells whether the system + tools prefix would be a cache hit. |
