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
3. Persist SQLite files on durable storage and back them up; migrate to a managed database for high write volume or multiple replicas.
4. Run `pytest -q` in CI before deployment.
5. Define workload specific evaluation cases, latency objectives, and rollback criteria before serving real users.
