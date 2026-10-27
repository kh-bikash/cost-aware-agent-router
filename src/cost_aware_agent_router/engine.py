from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from .llm import LLM


@dataclass(frozen=True)
class Model:
    name: str
    input_per_million_usd: float
    output_per_million_usd: float
    quality_tier: int
    max_output_tokens: int = 512


@dataclass(frozen=True)
class Decision:
    model: str
    answer: str
    estimated_cost_usd: float
    confidence: float
    early_exit: bool
    usage_source: str


class BudgetExceeded(Exception):
    pass


class CostRouter:
    def __init__(
        self,
        llm: LLM,
        models: list[Model],
        db_path: str | Path,
        *,
        token_estimator=None,
    ):
        self.llm, self.models, self.db_path = (
            llm,
            sorted(models, key=lambda m: (m.quality_tier, m.input_per_million_usd)),
            str(db_path),
        )
        self.token_estimator = token_estimator or (
            lambda text: max(1, (len(text) + 3) // 4)
        )
        if not models:
            raise ValueError("At least one model is required")
        if any(
            not model.name
            or model.input_per_million_usd < 0
            or model.output_per_million_usd < 0
            or model.quality_tier < 1
            or model.max_output_tokens < 1
            for model in models
        ):
            raise ValueError("invalid model catalog entry")
        with self._db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY, task_id TEXT, model TEXT, cost_usd REAL, confidence REAL, usage_source TEXT, input_tokens INTEGER, output_tokens INTEGER, created_at REAL)"
            )
            columns = {row[1] for row in db.execute("PRAGMA table_info(decisions)")}
            for name, kind in (
                ("usage_source", "TEXT"),
                ("input_tokens", "INTEGER"),
                ("output_tokens", "INTEGER"),
            ):
                if name not in columns:
                    db.execute(f"ALTER TABLE decisions ADD COLUMN {name} {kind}")

    def _db(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def route(
        self,
        task_id: str,
        prompt: str,
        *,
        budget_usd: float,
        complexity: int,
        confidence_fn,
    ) -> Decision:
        if not 0 <= complexity <= 10 or budget_usd <= 0:
            raise ValueError("invalid complexity or budget")
        spent = 0.0
        input_tokens = self.token_estimator(prompt)
        candidates = [
            m for m in self.models if m.quality_tier >= min(3, complexity // 4 + 1)
        ]
        if not candidates:
            candidates = [self.models[-1]]
        for index, model in enumerate(candidates):
            reserve = (
                input_tokens * model.input_per_million_usd
                + model.max_output_tokens * model.output_per_million_usd
            ) / 1_000_000
            if spent + reserve > budget_usd:
                continue
            if hasattr(self.llm, "complete_with_usage"):
                completion = self.llm.complete_with_usage(
                    [{"role": "user", "content": prompt}],
                    model=model.name,
                    max_output_tokens=model.max_output_tokens,
                )
                answer = completion.text
                used_input = completion.input_tokens or input_tokens
                used_output = completion.output_tokens or self.token_estimator(answer)
                usage_source = completion.usage_source
            else:
                answer = self.llm.complete(
                    [{"role": "user", "content": prompt}], model=model.name
                )
                used_input, used_output, usage_source = (
                    input_tokens,
                    self.token_estimator(answer),
                    "estimated",
                )
            actual_estimate = (
                used_input * model.input_per_million_usd
                + used_output * model.output_per_million_usd
            ) / 1_000_000
            spent += actual_estimate
            confidence = max(0.0, min(1.0, float(confidence_fn(prompt, answer))))
            with self._db() as db:
                db.execute(
                    "INSERT INTO decisions(task_id,model,cost_usd,confidence,usage_source,input_tokens,output_tokens,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (
                        task_id,
                        model.name,
                        actual_estimate,
                        confidence,
                        usage_source,
                        used_input,
                        used_output,
                        time.time(),
                    ),
                )
            if confidence >= 0.8 or index == len(candidates) - 1:
                return Decision(
                    model.name,
                    answer,
                    spent,
                    confidence,
                    confidence >= 0.8 and index < len(candidates) - 1,
                    usage_source,
                )
        raise BudgetExceeded("No model fits remaining task budget")

    def analytics(self) -> list[tuple[str, int, float]]:
        with self._db() as db:
            return db.execute(
                "SELECT model,count(*),sum(cost_usd) FROM decisions GROUP BY model ORDER BY model"
            ).fetchall()
