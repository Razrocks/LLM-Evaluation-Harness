# Price tables

Cost is **never** estimated from live provider pricing. It is computed from a run's *recorded*
token usage against a **versioned price table**, and the table's id + hash are pinned in the run
manifest. That is why a historical run's cost never silently changes when a provider updates
prices (see the source-of-truth boundary in [`../../docs/system-boundary.md`](../../docs/system-boundary.md)).

## Status

Empty by design at the first checkpoint (M0–M4). The recorded fixture targets make no provider
calls, so there is no token usage to price. Consequently:

- `cost_per_case_usd` is reported as **`null`** with denominator `0` and the missing-data rule
  *"requires a versioned price table; omitted when absent, never estimated"*.
- The default gate policy deliberately contains **no cost rule** — a threshold rule over an
  absent metric correctly evaluates to `INVALID`, and an offline run should not be unjudgeable
  for a metric that cannot exist yet.

## When these arrive (M5)

Each file will be a versioned table like `anthropic_2026_07.v1.json` mapping
`model revision -> {input_per_1k, output_per_1k, cache_read_per_1k, currency}`, referenced by
`price_table_id` / `price_table_hash` in the run manifest. Cost rules
(`cost_per_case_usd <= budget`) are added to the gate at that point, when the numbers are real.
