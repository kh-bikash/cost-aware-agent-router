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
