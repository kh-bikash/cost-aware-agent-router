import json

import pytest

from cost_aware_agent_router.__main__ import execute


def test_product_route_records_useful_decision(tmp_path, monkeypatch):
    catalog = tmp_path / "models.json"
    catalog.write_text(
        json.dumps(
            [
                {
                    "name": "small",
                    "input_per_million_usd": 0.1,
                    "output_per_million_usd": 0.1,
                    "quality_tier": 1,
                    "max_output_tokens": 100,
                }
            ]
        )
    )

    class FakeLLM:
        def complete(self, messages, *, model=None):
            return "Risks are listed."

    monkeypatch.setattr(
        "cost_aware_agent_router.__main__.OpenAICompatibleLLM.from_env",
        lambda: FakeLLM(),
    )
    db = str(tmp_path / "costs.sqlite3")
    result = execute(
        "route",
        {
            "prompt": "List risks",
            "budget_usd": "0.01",
            "complexity": "1",
            "required_terms": "risks",
        },
        db=db,
        models_path=str(catalog),
    )
    assert result["model"] == "small" and result["confidence"] == 1.0
    assert (
        execute("analytics", {}, db=db, models_path=str(catalog))[0]["decisions"] == 1
    )


def test_product_rejects_negative_catalog_prices(tmp_path):
    catalog = tmp_path / "models.json"
    catalog.write_text(
        json.dumps(
            [
                {
                    "name": "bad",
                    "input_per_million_usd": -1,
                    "output_per_million_usd": 0,
                    "quality_tier": 1,
                }
            ]
        )
    )
    with pytest.raises(ValueError, match="invalid model catalog"):
        execute(
            "analytics",
            {},
            db=str(tmp_path / "costs.sqlite3"),
            models_path=str(catalog),
        )
