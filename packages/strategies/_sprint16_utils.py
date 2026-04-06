from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional, Tuple

_TICK = Decimal("0.01")


def to_decimal(value: Any, default: Optional[Decimal] = None) -> Optional[Decimal]:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_to_tick(value: Any, tick: Decimal = _TICK) -> Decimal:
    decimal_value = to_decimal(value, Decimal("0")) or Decimal("0")
    return (decimal_value / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick


def clamp_decimal(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def get_snapshot_midpoint(snapshot: Any) -> Optional[Decimal]:
    for name in ("mid_price", "midpoint", "mid"):
        value = getattr(snapshot, name, None)
        if value is not None:
            return to_decimal(value)
    return None


def get_snapshot_spread(snapshot: Any) -> Optional[Decimal]:
    return to_decimal(getattr(snapshot, "spread", None))


def get_snapshot_time_to_close_seconds(snapshot: Any) -> Optional[float]:
    value = getattr(snapshot, "time_to_close_seconds", None)
    if value is None:
        return None
    return float(value)


def get_snapshot_inventory_yes(snapshot: Any) -> Decimal:
    for name in ("inventory_yes", "inventory", "position", "q_t"):
        value = getattr(snapshot, name, None)
        if value is not None:
            return to_decimal(value, Decimal("0")) or Decimal("0")
    return Decimal("0")


def get_reward_eligible(snapshot: Any) -> bool:
    return bool(getattr(snapshot, "reward_eligible", False))


def get_reward_max_spread(snapshot: Any) -> Optional[Decimal]:
    return to_decimal(getattr(snapshot, "reward_max_spread", None))


def get_regime_label(regime_state: Any) -> Optional[str]:
    if regime_state is None:
        return None
    if isinstance(regime_state, str):
        return regime_state
    label = getattr(regime_state, "primary_regime", None)
    if label is None:
        return None
    return str(label)


def get_prediction_edge(record: Any) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    if record is None:
        return None, None
    mispricing = getattr(record, "mispricing", getattr(record, "M_t", getattr(record, "edge", None)))
    threshold = getattr(record, "threshold", getattr(record, "theta_t", getattr(record, "edge_threshold", None)))
    return to_decimal(mispricing), to_decimal(threshold)


def edge_confidence(mispricing: Optional[Decimal], threshold: Optional[Decimal]) -> Decimal:
    if mispricing is None or threshold is None:
        return Decimal("0")
    magnitude = abs(mispricing)
    denominator = magnitude + abs(threshold)
    if denominator == 0:
        return Decimal("1")
    return clamp_decimal(magnitude / denominator, Decimal("0"), Decimal("1"))


def reward_size_multiplier(
    spread: Optional[Decimal],
    reward_eligible: bool,
    reward_max_spread: Optional[Decimal],
) -> Decimal:
    if not reward_eligible or spread is None or reward_max_spread is None or reward_max_spread <= 0:
        return Decimal("1")
    multiplier = Decimal("1") - (spread / reward_max_spread)
    return clamp_decimal(multiplier, Decimal("0"), Decimal("1"))


def make_maker_quotes(
    midpoint: Decimal,
    spread: Decimal,
    inventory_yes: Decimal,
    phi: Decimal,
    spread_multiplier: Decimal = Decimal("1"),
    bid_factor: Decimal = Decimal("1"),
    ask_factor: Decimal = Decimal("1"),
) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
    center = midpoint - (phi * inventory_yes)
    effective_spread = spread * spread_multiplier
    half_spread = effective_spread / Decimal("2")
    bid_price = round_to_tick(center - (half_spread * bid_factor))
    ask_price = round_to_tick(center + (half_spread * ask_factor))
    return bid_price, ask_price, center, effective_spread


def now_utc() -> datetime:
    return datetime.now(timezone.utc)

