# Architecture

## Goal

Choose model tiers under a task budget, stop when a confidence evaluator accepts an answer, and store cost estimates.

## Request path

Task -> complexity floor -> model tier list -> reserve estimated tokens -> model call -> estimated cost ledger -> confidence gate -> early exit or escalation.

## Components

- `src/cost_aware_agent_router/engine.py`: policy and state transitions for this project.
- `src/cost_aware_agent_router/llm.py`: injected model protocol and HTTPS OpenAI-compatible adapter with timeouts and retry for transient transport failures.
- `tests/test_engine.py`: deterministic behavior and failure tests.
- `.github/workflows/ci.yml`: install and test gate.


## State and failure behavior

Pricing in this example is illustrative and must be updated from your provider's current price sheet. Costs and tokens are estimates, and a provider response can exceed a reserve. The system does not promise a particular percentage saving.

The LLM adapter times out after 30 seconds and retries transient HTTP failures twice. Model output is untrusted input and is parsed or validated at the project boundary.

## Operations checklist

1. Set secrets through a secret manager and rotate them regularly.
2. Put the service or integrating application behind TLS and authentication.
3. Persist and back up the SQLite decision ledger. Reconcile estimated token costs with provider billing before financial reporting.
4. Run `pytest -q` in CI before deployment.
5. Define workload specific evaluation cases, latency objectives, and rollback criteria before serving real users.

## Routing and accounting

Each `Model` declares price per million input/output tokens, quality tier, and maximum output tokens. A task supplies its USD budget, estimated complexity, and a confidence evaluator. The router starts at the least expensive allowed tier, reserves a worst case output allowance, calls the model, records its measured or estimated usage, and stops when confidence is at least 0.8. Otherwise it may escalate within the remaining budget.

The OpenAI compatible adapter requests `max_completion_tokens` and parses provider `prompt_tokens` and `completion_tokens`. If an injected adapter lacks usage data, the ledger marks the record as estimated. The `decisions` table enables per-model count and spend analytics. Prices must be configured from the current provider sheet. A reserve is a pre-call estimate: provider tokenization, hidden reasoning tokens, and pricing changes mean it is not a financial hard cap. Reconcile with provider billing before reporting savings.

## Product interfaces and trust boundary

The installed console command and local browser call the same product operation in `src/*/__main__.py`; the browser does not replace the engine's validation or state transitions. `src/*/web.py` serves HTML and a JSON action endpoint with a one-megabyte request limit and a per-process CSRF token. It binds to loopback by default. A non-loopback bind requires `AGENT_WEB_TOKEN` of at least 16 characters, checked on every action request. The page never embeds the access token; an operator enters it in the browser. Treat the browser as an operator interface and place TLS plus identity-aware access control in front of any public endpoint. The non-root container is described in `DEPLOYMENT.md`.
