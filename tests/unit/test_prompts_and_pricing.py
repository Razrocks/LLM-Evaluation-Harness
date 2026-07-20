"""Prompt-spec hashing/rendering determinism and honest cost computation."""

from __future__ import annotations

from pathlib import Path

from ai_eval.datasets import load_cases_dir
from ai_eval.pricing import PriceTable, cost_for_usage, load_price_table
from ai_eval.prompts import load_prompt_spec, render_prompt

REPO = Path(__file__).resolve().parents[2]
CASES = {c.case_id: c for c in load_cases_dir(REPO / "datasets/reference/request_triage/v1/cases")}
CASE = CASES["request_triage_001"]
SPEC = load_prompt_spec(REPO / "prompts" / "reference", "request_triage", "v1")


def test_prompt_spec_is_content_addressed() -> None:
    again = load_prompt_spec(REPO / "prompts" / "reference", "request_triage", "v1")
    assert SPEC.content_hash == again.content_hash
    assert SPEC.ref == "request_triage.v1"


def test_rendering_is_deterministic() -> None:
    a = render_prompt(SPEC, CASE.input)
    b = render_prompt(SPEC, CASE.input)
    assert a.user == b.user
    assert a.request_hash == b.request_hash


def test_rendered_prompt_contains_case_facts() -> None:
    rendered = render_prompt(SPEC, CASE.input)
    assert CASE.input["message"] in rendered.user
    assert CASE.input["received_at"] in rendered.user
    assert CASE.input["reference_timezone"] in rendered.user
    for doc in CASE.input["documents"]:
        assert doc["document_id"] in rendered.user


def test_document_order_does_not_change_the_prompt() -> None:
    """Documents are sorted, so input ordering can't silently change the request hash."""
    reversed_input = dict(CASE.input)
    reversed_input["documents"] = list(reversed(CASE.input["documents"]))
    assert (
        render_prompt(SPEC, reversed_input).request_hash
        == render_prompt(SPEC, CASE.input).request_hash
    )


def test_different_case_changes_request_hash() -> None:
    other = CASES["request_triage_002"]
    assert (
        render_prompt(SPEC, other.input).request_hash
        != render_prompt(SPEC, CASE.input).request_hash
    )


# --- cost ---------------------------------------------------------------------------------

TABLE = PriceTable(
    price_table_id="t", version="v1", effective_date="2026-07-01",
    prices={"m1": {"input_per_1k": 1.0, "output_per_1k": 2.0}},  # type: ignore[dict-item]
)


def test_cost_from_recorded_usage() -> None:
    cost = cost_for_usage(TABLE, "m1", {"input_tokens": 1000, "output_tokens": 500})
    assert cost == 1.0 + 1.0  # 1k in @1.0 + 0.5k out @2.0


def test_cost_is_none_without_a_table() -> None:
    assert cost_for_usage(None, "m1", {"input_tokens": 10, "output_tokens": 10}) is None


def test_cost_is_none_for_unknown_model() -> None:
    assert cost_for_usage(TABLE, "unknown", {"input_tokens": 10, "output_tokens": 10}) is None


def test_cost_is_none_without_token_counts() -> None:
    assert cost_for_usage(TABLE, "m1", None) is None
    assert cost_for_usage(TABLE, "m1", {"input_tokens": None, "output_tokens": 5}) is None


def test_price_table_is_content_addressed() -> None:
    assert TABLE.content_hash == TABLE.model_copy(deep=True).content_hash


def test_shipped_example_table_loads_and_is_marked_placeholder() -> None:
    table = load_price_table(REPO / "configs" / "price_tables" / "example.v1.json")
    assert table.prices
    # The shipped table must never be mistaken for real pricing.
    assert "PLACEHOLDER" in (table.source or "")
