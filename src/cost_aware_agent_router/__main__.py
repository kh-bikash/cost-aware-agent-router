"""Budgeted model routing with an explicit price catalog."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from .engine import CostRouter, Model
from .llm import OpenAICompatibleLLM
from .web import serve

WEB_ACTIONS = {
    "route": [
        ("prompt", "Task prompt", "textarea", True),
        ("budget_usd", "Budget in USD", "number", True),
        ("complexity", "Complexity 0 to 10", "number", True),
        ("required_terms", "Required output terms, comma separated", "text", True),
    ],
    "analytics": [],
}


class _OfflineLLM:
    def complete(self, messages, *, model=None):
        raise RuntimeError("Set OPENAI_API_KEY before routing a live task")


def execute(action: str, values: dict, *, db: str, models_path: str) -> object:
    data = json.loads(Path(models_path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("price catalog must contain a nonempty model array")
    models = [Model(**entry) for entry in data]
    llm = OpenAICompatibleLLM.from_env() if action == "route" else _OfflineLLM()
    router = CostRouter(llm, models, db)
    if action == "analytics":
        return [
            {"model": model, "decisions": count, "estimated_cost_usd": cost}
            for model, count, cost in router.analytics()
        ]
    if action != "route":
        raise ValueError("unknown action")
    terms = values["required_terms"]
    if isinstance(terms, str):
        terms = [term.strip() for term in terms.split(",") if term.strip()]
    if not terms:
        raise ValueError("provide at least one required output term")

    def coverage(_prompt: str, answer: str) -> float:
        return sum(term.lower() in answer.lower() for term in terms) / len(terms)

    decision = router.route(
        values.get("task_id") or uuid.uuid4().hex,
        values["prompt"],
        budget_usd=float(values["budget_usd"]),
        complexity=int(values["complexity"]),
        confidence_fn=coverage,
    )
    return {
        **decision.__dict__,
        "acceptance_check": "required-term coverage",
        "required_terms": terms,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Budgeted LLM routing")
    parser.add_argument("--models", required=True, help="JSON price catalog")
    parser.add_argument("--db", default="costs.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("route")
    run.add_argument("prompt")
    run.add_argument("--budget-usd", type=float, required=True)
    run.add_argument("--complexity", type=int, required=True)
    run.add_argument(
        "--required-term", dest="required_terms", action="append", required=True
    )
    run.add_argument("--task-id")
    commands.add_parser("analytics")
    browser = commands.add_parser("serve")
    browser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    if args.command == "serve":
        serve(
            "Cost Aware Agent Router",
            WEB_ACTIONS,
            lambda action, values: execute(
                action, values, db=args.db, models_path=args.models
            ),
            port=args.port,
        )
    else:
        print(
            json.dumps(
                execute(args.command, vars(args), db=args.db, models_path=args.models),
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
