import pytest
from cost_aware_agent_router.engine import BudgetExceeded, CostRouter, Model


class Stub:
    def __init__(self):
        self.models = []

    def complete(self, messages, *, model=None):
        self.models.append(model)
        return "answer"


def test_early_exit_and_analytics(tmp_path):
    stub = Stub()
    models = [Model("cheap", 1, 1, 1), Model("strong", 5, 5, 2)]
    router = CostRouter(stub, models, tmp_path / "cost.db")
    decision = router.route("t", "hello", budget_usd=0.01, complexity=1, confidence_fn=lambda *_: 0.9)
    assert decision.model == "cheap" and decision.early_exit
    assert router.analytics()[0][1] == 1
    with pytest.raises(BudgetExceeded):
        router.route("t2", "hello", budget_usd=0.00000001, complexity=1, confidence_fn=lambda *_: 1)


def test_provider_usage_drives_ledger(tmp_path):
    class Metered:
        def complete_with_usage(self, messages, *, model=None, max_output_tokens=512):
            from cost_aware_agent_router.llm import Completion
            return Completion("answer", 100, 50, "provider")
    router = CostRouter(Metered(), [Model("metered", 1, 2, 1, 100)], tmp_path / "cost.db")
    result = router.route("task", "short", budget_usd=0.01, complexity=0, confidence_fn=lambda *_: 1)
    assert result.usage_source == "provider"
    assert result.estimated_cost_usd == (100 + 50 * 2) / 1_000_000
