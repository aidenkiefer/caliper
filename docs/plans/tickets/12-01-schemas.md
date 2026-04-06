# Ticket: 12-01-schemas

## Task
Define `FeatureSnapshot` and `FeatureRecord` Pydantic models for the unified feature pipeline, add the `services/features/polymarket/` package scaffold, and update `packages/common/polymarket_schemas.py` with the new types.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/features/polymarket/__init__.py`
- Create: `services/features/polymarket/schemas.py`
- Modify: `packages/common/polymarket_schemas.py` (add `FeatureSnapshot`, `FeatureRecord`)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-12-feature-layer-spec.md` (sections: Feature Families, Architecture → FeatureSnapshot Schema)

### Optional read-only references
- `packages/common/polymarket_schemas.py` (existing patterns — extend, don't replace)
- `packages/common/schemas.py` (Pydantic base patterns)

### Example files (read-only, optional)
- `services/polymarket/schemas.py` (existing internal schema patterns)

## Agent type
backend-agent

## Skill pack
None required (Pydantic schema definition)

## Context + tool budget
- Max file reads: 5
- Max grep/glob operations: 3
- Max total tool calls: 10

## Done criteria

**`FeatureSnapshot` in `packages/common/polymarket_schemas.py`:**
- All 28 fields from the spec schema section are present with correct Python types
- `mid_price`, `spread`, `spread_bps`, etc. typed as `Decimal`
- `vol_regime` typed as `Literal["low", "medium", "high"]`
- `trend_regime` typed as `Literal["trending", "mean_reverting", "neutral"]`
- `time_bucket` typed as `Literal["early", "mid", "late"]`
- `toxicity_regime` typed as `Literal["low", "medium", "high"]`
- `spread_regime` typed as `Literal["tight", "normal", "wide"]`
- `near_close_flag: bool`, `reward_eligible: bool`
- `reward_max_spread: Optional[Decimal]`, `reward_min_size: Optional[Decimal]`
- `captured_at: datetime` (UTC)
- `data_staleness_flag: bool = False` (set True if any source exceeds 30s lag — spec risk note)

**`FeatureRecord` in `packages/common/polymarket_schemas.py`:**
- Wraps `FeatureSnapshot` with `id: UUID`, `created_at: datetime` for DB round-trips

**`services/features/polymarket/schemas.py`:**
- Re-exports `FeatureSnapshot` and `FeatureRecord` from `packages.common.polymarket_schemas`
- Adds `SourceTimestamps` dataclass (clob_ts, binance_ts, futures_ts) for staleness tracking inside the builder

**`services/features/polymarket/__init__.py`:**
- Module docstring: "Polymarket unified feature pipeline (Sprint 12)"
- Exports `FeatureSnapshot`

**`docs/plans/PROGRESS.md`** updated with a brief dated note
