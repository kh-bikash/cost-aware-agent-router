# Cost Aware Agent Router

Choose model tiers under a task budget, stop when a confidence evaluator accepts an answer, and store cost estimates.

## Quick start

Requires Python 3.11 or newer. From this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
pytest -q
```

For live model calls, set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` and `OPENAI_BASE_URL` as shown in `.env.example`. The test suite uses stubs and needs no model key.

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

Task -> complexity floor -> model tier list -> reserve estimated tokens -> model call -> estimated cost ledger -> confidence gate -> early exit or escalation.

See [ARCHITECTURE.md](ARCHITECTURE.md) for components, state, failure behavior, and operations.

## Deployment and safety

Pricing in this example is illustrative and must be updated from your provider's current price sheet. Costs and tokens are estimates, and a provider response can exceed a reserve. The system does not promise a particular percentage saving.

Install this as a library in an authenticated application or worker. Supply the LLM adapter through dependency injection. Keep secrets in environment variables, never in source control.

## Verification

`pytest -q` runs deterministic tests. GitHub Actions runs the same suite on pushes and pull requests.

## License

MIT. See [LICENSE](LICENSE).
