"""Versioned price tables and cost computation.

Cost is derived from a run's **recorded token usage** against a **versioned price table** whose
id and hash are pinned in the run manifest. This is why a historical run's cost never changes
when a provider updates its pricing page.

Cost is ``None`` whenever it cannot be computed honestly — no table, unknown model, or missing
token counts. It is never estimated, interpolated, or defaulted to zero.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ai_eval.domain import content_hash


class ModelPrice(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    input_per_1k: float = Field(ge=0)
    output_per_1k: float = Field(ge=0)


class PriceTable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price_table_id: str
    version: str
    currency: str = "USD"
    effective_date: str
    source: str | None = None
    notes: str | None = None
    #: model identifier -> per-1k-token prices
    prices: dict[str, ModelPrice] = Field(default_factory=dict)

    @property
    def ref(self) -> str:
        return f"{self.price_table_id}.{self.version}"

    @property
    def content_hash(self) -> str:
        return content_hash(self.model_dump(mode="json"))


def load_price_table(path: Path) -> PriceTable:
    return PriceTable.model_validate(json.loads(path.read_text(encoding="utf-8")))


def cost_for_usage(
    table: PriceTable | None,
    model: str | None,
    usage: dict[str, object] | None,
) -> float | None:
    """Cost in the table's currency, or ``None`` when it cannot be computed honestly."""
    if table is None or not model:
        return None
    price = table.prices.get(model)
    if price is None:
        return None
    if not usage:
        return None
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    return (input_tokens / 1000.0) * price.input_per_1k + (
        output_tokens / 1000.0
    ) * price.output_per_1k
