# Cost Aware Agent Router

## About

This app helps decide which model should handle a task when you have a spending limit. Give it a task, a budget, and a catalog of models with prices and capability tiers. It starts with a model that fits the task and budget, checks whether the answer meets your acceptance rule, and only moves to a stronger model when there is budget left. It records the decision so you can inspect cost over time.

### What you can do

- Set a per-task USD budget and a minimum model tier.
- Route a prompt through a price catalog you control.
- Stop early when an evaluator accepts the answer.
- Read a ledger of model choices, token usage, and estimated cost.

The CLI and local browser are usable with your own model provider and current price catalog. The included catalog is an example, not live pricing. Required-term checks are a simple acceptance rule, not proof that an answer is factually correct. The product has no public hosted URL yet, and it does not claim a measured percentage of savings.

## Quick start

Requires Python 3.11 or newer. From this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
pytest -q
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
```

For live model calls, set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` and `OPENAI_BASE_URL` as shown in `.env.example`. The test suite uses stubs and needs no model key.

The installed `cost-router` command accepts a JSON price catalog, task budget, complexity, and required output terms. Copy `examples/models.example.json`, replace model IDs and prices with your provider's current values, then run `cost-router --models models.json route "Write a summary including risks" --budget-usd 0.02 --complexity 2 --required-term risks`. Use `cost-router --models models.json analytics` to inspect the durable decision ledger. Run `cost-router --models models.json serve --port 8080` for a local browser interface. Required-term coverage is a deterministic acceptance check, not factual confidence; add an independent evaluator when quality matters.

```python
from cost_aware_agent_router.engine import CostRouter, Model
from cost_aware_agent_router.llm import OpenAICompatibleLLM

models = [Model("gpt-4.1-mini", 0.4, 1.6, 1), Model("gpt-4.1", 2.0, 8.0, 2)]
router = CostRouter(OpenAICompatibleLLM.from_env(), models, "cost.sqlite3")
result = router.route("task-123", "Summarize this short memo", budget_usd=0.02, complexity=1,
                      confidence_fn=lambda prompt, answer: 0.9 if answer.strip() else 0.0)
print(result, router.analytics())
```

## Architecture

```mermaid
flowchart LR
    CLI[Command line] --> Task
    Browser[Browser interface] --> Task
    Task[Task and USD budget] --> Tier[Complexity and tier policy]
    Prices[Configured model prices] --> Tier
    Tier --> Reserve[Output token reservation]
    Reserve --> LLM[Selected model]
    LLM --> Usage[Provider usage or estimate]
    Usage --> Ledger[(SQLite cost ledger)]
    Usage --> Confidence[Confidence evaluator]
    Confidence -->|Accepted| Answer[Answer and cost]
    Confidence -->|Low confidence and budget remains| Tier
    Reserve -->|No model fits| Reject[Budget exceeded]
```

| Component | Responsibility |
|---|---|
| Model catalog | Declares tiers, token prices, and output limits. |
| Router | Reserves budget and escalates only when confidence is low. |
| Ledger | Stores per-decision usage source, token counts, and cost. |

Task -> complexity floor -> model tier list -> reserve estimated tokens -> model call -> estimated cost ledger -> confidence gate -> early exit or escalation.

See [ARCHITECTURE.md](ARCHITECTURE.md) for components, state, failure behavior, and operations.

## Deployment and safety

See [DEPLOYMENT.md](DEPLOYMENT.md) for the non-root container, token-protected browser, data mounts, and release checks.

Pricing in this example is illustrative and must be updated from your provider's current price sheet. Costs and tokens are estimates, and a provider response can exceed a reserve. The system does not promise a particular percentage saving.

The SQLite ledger migrates older decision tables by adding provider usage columns on startup; existing historical rows remain available for analytics.

Install this as a library in an authenticated application or worker. Supply the LLM adapter through dependency injection. Keep secrets in environment variables, never in source control.

## Verification

`pytest -q` runs deterministic tests. GitHub Actions runs the same suite on pushes and pull requests.

## License

MIT. See [LICENSE](LICENSE).
