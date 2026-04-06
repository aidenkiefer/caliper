# Ticket: 16-02-universe-builder-gamma-filters

## Task
Implement `UniverseBuilder` to discover eligible Polymarket BTC hourly markets via Gamma and apply inclusion/exclusion filters (AC-2).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/ranking/universe.py
- services/ranking/schemas.py
- services/ranking/__init__.py
- tests/unit/ranking/test_universe_builder.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md
- services/polymarket/adapters/gamma_client.py

### Optional read-only references
- services/polymarket/market_discovery.py (existing hourly-btc helpers)

## Skill pack (optional, keep small)
- Required: `async-python-patterns`
- Optional: `risk-manager`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `UniverseBuilder.build()` returns a list of `CandidateMarket` with:
  - inclusion filters enforced (active, not closed, fee/reward eligible, hourly BTC)
  - exclusion filters enforced: `min_volume_usd`, `max_spread_pct`
- Unit tests cover AC-2 with synthetic market metadata (no real Gamma calls).
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-02 completion.

