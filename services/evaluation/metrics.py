from __future__ import annotations

import math
import statistics
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from services.evaluation.schemas import StrategyMetrics
from services.simulation.schemas import SimFill


def _daily_pnl(hourly_pnl: List[Decimal]) -> List[Decimal]:
    """Group hourly PnL into 24-hour windows and sum each window."""
    daily = []
    for i in range(0, len(hourly_pnl), 24):
        window = hourly_pnl[i:i + 24]
        daily.append(sum(window, Decimal(0)))
    return daily


def _max_drawdown(pnl_series: List[Decimal]) -> tuple[Decimal, int]:
    """
    Returns (max_drawdown_as_positive_decimal, max_drawdown_duration_hours).
    max_drawdown: maximum peak-to-trough decline in cumulative PnL.
    duration: longest consecutive sequence of hours below the previous peak.
    """
    if not pnl_series:
        return Decimal(0), 0
    cumulative = []
    running = Decimal(0)
    for p in pnl_series:
        running += p
        cumulative.append(running)
    peak = cumulative[0]
    max_dd = Decimal(0)
    max_dur = 0
    current_dur = 0
    for val in cumulative:
        if val >= peak:
            peak = val
            current_dur = 0
        else:
            dd = peak - val
            if dd > max_dd:
                max_dd = dd
            current_dur += 1
            if current_dur > max_dur:
                max_dur = current_dur
    return max_dd, max_dur


def compute_metrics(
    strategy_id: str,
    pnl_series: List[Decimal],
    fills: List[SimFill],
    period_start: datetime,
    period_end: datetime,
    risk_free_rate: Decimal = Decimal("0"),
    baseline_results: Optional[Dict[str, Decimal]] = None,
) -> StrategyMetrics:
    """Compute all StrategyMetrics from an hourly PnL series and fills."""
    total_pnl = sum(pnl_series, Decimal(0))
    daily = _daily_pnl(pnl_series)
    data_points = len(daily)

    # Sharpe ratio (annualized)
    if data_points >= 2:
        daily_floats = [float(d) for d in daily]
        mean_d = statistics.mean(daily_floats)
        std_d = statistics.stdev(daily_floats)
        if std_d > 0:
            sharpe = Decimal(str(round((mean_d - float(risk_free_rate)) / std_d * math.sqrt(252), 6)))
        else:
            sharpe = Decimal("0")
    else:
        sharpe = Decimal("0")

    sharpe_confidence = "low" if data_points < 20 else ("medium" if data_points <= 60 else "high")

    # Sortino ratio (annualized) — downside std only
    if data_points >= 2:
        daily_floats = [float(d) for d in daily]
        mean_d = statistics.mean(daily_floats)
        neg = [d for d in daily_floats if d < 0]
        if len(neg) >= 2:
            down_std = statistics.stdev(neg)
        elif len(neg) == 1:
            down_std = abs(neg[0])
        else:
            down_std = 0.0
        sortino = Decimal(str(round(mean_d / down_std * math.sqrt(252), 6))) if down_std > 0 else Decimal("0")
    else:
        sortino = Decimal("0")

    # Max drawdown and duration
    max_dd, max_dd_hours = _max_drawdown(pnl_series)

    # Calmar ratio
    calmar = (total_pnl / max_dd) if max_dd > 0 else Decimal("0")

    # Win rate
    pos_hours = sum(1 for p in pnl_series if p > 0)
    win_rate = Decimal(pos_hours) / Decimal(max(len(pnl_series), 1))

    # Profit factor
    gross_profit = sum((p for p in pnl_series if p > 0), Decimal(0))
    gross_loss = abs(sum((p for p in pnl_series if p < 0), Decimal(0)))
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = Decimal("9999")

    # Consistency score: fraction of rolling 7-day (168h) windows with positive PnL
    window_size = 168
    if len(pnl_series) >= window_size:
        windows = [pnl_series[i:i + window_size] for i in range(len(pnl_series) - window_size + 1)]
        pos_windows = sum(1 for w in windows if sum(w, Decimal(0)) > 0)
        consistency_score = Decimal(pos_windows) / Decimal(len(windows))
    else:
        consistency_score = Decimal("1") if total_pnl > 0 else Decimal("0")

    # Stability score: 1 - std(rolling_7d_pnl) / mean(rolling_7d_pnl)
    if len(daily) >= 2:
        rolling_7d = []
        for i in range(0, len(daily), 7):
            rolling_7d.append(sum(daily[i:i + 7], Decimal(0)))
        if len(rolling_7d) >= 2:
            r_floats = [float(x) for x in rolling_7d]
            r_mean = statistics.mean(r_floats)
            r_std = statistics.stdev(r_floats)
            if abs(r_mean) > 0:
                stability = Decimal(str(round(max(0.0, min(1.0, 1.0 - r_std / abs(r_mean))), 6)))
            else:
                stability = Decimal("0")
        else:
            stability = Decimal("0")
    else:
        stability = Decimal("0")

    # Volume metrics from fills
    total_volume = sum(f.fill_price * f.fill_size for f in fills) if fills else Decimal(0)
    fill_rate = Decimal("0")  # not computable from fills alone; caller must pass if needed
    maker_count = sum(1 for f in fills if f.maker_fill)
    maker_fill_rate = Decimal(maker_count) / Decimal(max(len(fills), 1)) if fills else Decimal("0")

    # Baseline regret
    br = baseline_results or {}
    regret_vs_hold_cash = total_pnl - br.get("hold_cash", Decimal(0))
    regret_vs_buy_and_hold = total_pnl - br.get("buy_and_hold", Decimal(0))
    regret_vs_random = total_pnl - br.get("random_mm", Decimal(0))

    return StrategyMetrics(
        strategy_id=strategy_id,
        period_start=period_start,
        period_end=period_end,
        total_pnl=total_pnl,
        pnl_components={},
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        win_rate=win_rate,
        profit_factor=profit_factor,
        max_drawdown=max_dd,
        max_drawdown_duration_hours=max_dd_hours,
        consistency_score=consistency_score,
        stability_score=stability,
        total_volume_usd=total_volume,
        fill_rate=fill_rate,
        maker_fill_rate=maker_fill_rate,
        regret_vs_hold_cash=regret_vs_hold_cash,
        regret_vs_buy_and_hold=regret_vs_buy_and_hold,
        regret_vs_random=regret_vs_random,
        sharpe_confidence=sharpe_confidence,
        data_points=data_points,
    )
