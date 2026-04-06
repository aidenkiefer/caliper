"""Fee-aware threshold strategy backtest using the Sprint 13 SimulationRunner.

ThresholdBacktester segments predictions by (vol_regime, time_bucket, fee_regime)
and runs a separate SimulationRunner for each segment.

Signal logic:
    if M(t) > θ(t):  BUY YES at best_ask (taker)
    elif M(t) < -θ(t): BUY NO at best_bid (taker)
    else: ABSTAIN

    θ(t) = spread(t)/2 + slippage_estimate + fee_edge + ε_risk_buffer
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

from services.simulation.runner import SimulationRunner, SimStrategy
from services.simulation.schemas import SimEvent, SimOrder, SimResult
from services.simulation.execution.simulator import ExecutionConfig
from services.simulation.execution.fee_engine import FeeRegime
from services.simulation.adverse.selection import AdverseSelectionModel


# ---------------------------------------------------------------------------
# ThresholdStrategy — implements SimStrategy protocol
# ---------------------------------------------------------------------------

class ThresholdStrategy:
    """Implements SimStrategy protocol for the threshold signal.

    Looks up the prediction keyed by the event's timestamp ISO string,
    computes θ(t), and emits a taker BUY order (YES or NO) or nothing.
    """

    strategy_id: str = "threshold_backtest_v1"

    def __init__(
        self,
        predictions_map: Dict[str, Dict[str, Any]],
        epsilon: float,
        slippage: float,
    ) -> None:
        """
        Args:
            predictions_map: {timestamp_isoformat: {
                "mispricing": float,
                "spread": float,
                "fee_rate": float,
                "p_hat": float,
                "token_id": str,
            }}
            epsilon: risk buffer added to threshold.
            slippage: slippage estimate added to threshold.
        """
        self._preds = predictions_map
        self._epsilon = epsilon
        self._slippage = slippage

    # ------------------------------------------------------------------
    # SimStrategy protocol
    # ------------------------------------------------------------------

    def generate_sim_orders(
        self,
        event: SimEvent,
        book: Any,  # SimulatedOrderBook
    ) -> List[SimOrder]:
        """Generate BUY YES, BUY NO, or no order based on M(t) vs θ(t)."""
        key = event.timestamp.isoformat()
        pred = self._preds.get(key)
        if pred is None:
            return []

        mispricing = float(pred["mispricing"])
        spread = float(pred["spread"])
        fee_rate = float(pred["fee_rate"])

        theta = spread / 2 + self._slippage + fee_rate + self._epsilon

        if abs(mispricing) <= theta:
            # ABSTAIN
            return []

        # Determine side and price
        if mispricing > theta:
            side = "BUY"
            # Buy YES at best_ask — taker
            best_ask = book.best_ask()
            if best_ask is None:
                return []
            price = best_ask
        else:
            # mispricing < -theta → buy NO (sell YES)
            side = "SELL"
            # Buy NO at best_bid — taker
            best_bid = book.best_bid()
            if best_bid is None:
                return []
            price = best_bid

        order = SimOrder(
            order_id=str(uuid.uuid4()),
            market_id=event.market_id,
            token_id=event.token_id,
            side=side,
            order_type="taker",
            price=price if isinstance(price, Decimal) else Decimal(str(price)),
            size=Decimal("1"),
            submit_time=event.timestamp,
            post_only=False,
        )
        return [order]


# ---------------------------------------------------------------------------
# ThresholdBacktester
# ---------------------------------------------------------------------------

# Cutoff date for fee regime split
_FEE_CUTOFF = date(2026, 3, 30)


class ThresholdBacktester:
    """Fee-aware threshold strategy backtest using the Sprint 13 SimulationRunner.

    Segments results by: fee_regime, vol_regime, time_bucket.

    Workflow:
        1. build_sim_events(df) — convert DataFrame rows to SimEvent objects.
        2. run_backtest(predictions_df, market_created_at, market_id) —
           segments data, runs SimulationRunner per segment, returns List[SimResult].
        3. segment_results(results, labels) — combine into summary DataFrame.
    """

    def __init__(
        self,
        epsilon_risk_buffer: float = 0.005,
        slippage_estimate: float = 0.002,
        random_seed: int = 42,
    ) -> None:
        self._epsilon = epsilon_risk_buffer
        self._slippage = slippage_estimate
        self._seed = random_seed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_threshold(
        self,
        spread: float,
        fee_rate: float,
        implied_prob: float,  # noqa: ARG002 — reserved for future vol-scaling
    ) -> float:
        """θ(t) = spread/2 + slippage + fee_edge + ε_risk_buffer.

        fee_edge = fee_rate (rough edge proxy).
        implied_prob is accepted for interface completeness but not used in this
        base formulation; subclasses may extend it.
        """
        return spread / 2 + self._slippage + fee_rate + self._epsilon

    def build_sim_events(self, df: pd.DataFrame) -> List[SimEvent]:
        """Convert predictions DataFrame rows to SimEvent objects.

        Each row becomes a SimEvent with event_type="snapshot",
        payload containing all prediction columns.
        """
        events: List[SimEvent] = []
        for _, row in df.iterrows():
            payload: Dict[str, Any] = {
                "p_hat": float(row["p_hat"]),
                "implied_probability": float(row["implied_probability"]),
                "mispricing": float(row["mispricing"]),
                "spread": float(row["spread"]),
                "fee_rate_current": float(row["fee_rate_current"]),
                "vol_regime": str(row["vol_regime"]),
                "time_bucket": str(row["time_bucket"]),
            }
            # Optionally carry through any extra columns
            for col in df.columns:
                if col not in payload and col not in ("predicted_at", "token_id"):
                    try:
                        payload[col] = row[col]
                    except Exception:
                        pass

            ts = row["predicted_at"]
            if not isinstance(ts, datetime):
                ts = pd.Timestamp(ts).to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            event = SimEvent(
                event_id=str(uuid.uuid4()),
                timestamp=ts,
                event_type="snapshot",
                market_id="",          # filled in by run_backtest
                token_id=str(row.get("token_id", "")),
                payload=payload,
            )
            events.append(event)
        return events

    def run_backtest(
        self,
        predictions_df: pd.DataFrame,
        market_created_at: datetime,
        market_id: str,
    ) -> List[SimResult]:
        """Run the threshold strategy on the predictions DataFrame.

        Segments data by (vol_regime, time_bucket) AND (pre/post Mar-30 fee regime)
        and runs a separate SimulationRunner for each non-empty segment.

        Returns a list of SimResult objects (one per segment combination).
        """
        if predictions_df.empty:
            return []

        df = predictions_df.copy()

        # Normalise timestamp column
        if not pd.api.types.is_datetime64_any_dtype(df["predicted_at"]):
            df["predicted_at"] = pd.to_datetime(df["predicted_at"], utc=True)
        elif df["predicted_at"].dt.tz is None:
            df["predicted_at"] = df["predicted_at"].dt.tz_localize("UTC")

        # Add trade_date for fee regime split
        df["_trade_date"] = df["predicted_at"].dt.date

        # Classify each row into pre / post fee regime
        df["_fee_regime_name"] = df["_trade_date"].apply(
            lambda d: "post_mar30" if d >= _FEE_CUTOFF and market_created_at.date() >= _FEE_CUTOFF else "pre_mar30"
        )

        results: List[SimResult] = []

        # Segment by (vol_regime, time_bucket, fee_regime_name)
        group_keys = ["vol_regime", "time_bucket", "_fee_regime_name"]
        for group_values, seg_df in df.groupby(group_keys, sort=True):
            vol_regime, time_bucket, fee_regime_name = group_values

            if seg_df.empty:
                continue

            # Select fee regime for this segment (use the first trade date's regime)
            first_trade_date: date = seg_df["_trade_date"].iloc[0]
            fee_regime = FeeRegime.for_date(market_created_at, first_trade_date)

            # Build predictions_map keyed by ISO timestamp
            predictions_map: Dict[str, Dict[str, Any]] = {}
            for _, row in seg_df.iterrows():
                ts = row["predicted_at"]
                if hasattr(ts, "isoformat"):
                    key = ts.isoformat()
                else:
                    key = str(ts)
                predictions_map[key] = {
                    "mispricing": float(row["mispricing"]),
                    "spread": float(row["spread"]),
                    "fee_rate": float(row["fee_rate_current"]),
                    "p_hat": float(row["p_hat"]),
                    "token_id": str(row.get("token_id", "")),
                }

            # Build SimEvents for this segment (stamped with market_id)
            events = self._build_events_for_segment(seg_df, market_id)
            if not events:
                continue

            strategy = ThresholdStrategy(
                predictions_map=predictions_map,
                epsilon=self._epsilon,
                slippage=self._slippage,
            )

            exec_config = ExecutionConfig(
                network_delay_ms=50.0,
                delay_distribution="lognormal",
                max_orders_per_second=10,
                paper_mode=True,
                random_seed=self._seed,
            )

            adverse = AdverseSelectionModel(
                baseline_informed=Decimal("0.05"),
                peak_informed=Decimal("0.40"),
                ramp_start_minutes=10,
                random_seed=self._seed,
            )

            run_id = str(uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{market_id}:{vol_regime}:{time_bucket}:{fee_regime_name}",
            ))

            runner = SimulationRunner(
                events=events,
                strategy=strategy,
                execution_config=exec_config,
                fee_regime=fee_regime,
                adverse_selection=adverse,
                lr_pool_per_hour=Decimal("50"),
                run_id=run_id,
            )

            result = runner.run()
            # Attach segment metadata via config dict (non-destructive extension)
            result.config["segment"] = {
                "vol_regime": vol_regime,
                "time_bucket": time_bucket,
                "fee_regime_name": fee_regime_name,
            }
            results.append(result)

        return results

    def segment_results(
        self,
        results: List[SimResult],
        labels: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        """Combine SimResults into a summary DataFrame with segment labels.

        Args:
            results: list of SimResult from run_backtest.
            labels:  list of dicts (same length as results) with segment metadata.
                     If empty, segment labels are extracted from result.config["segment"].

        Returns a DataFrame with one row per SimResult.
        """
        rows = []
        for i, result in enumerate(results):
            # Base metrics from SimResult
            row: Dict[str, Any] = {
                "run_id": result.run_id,
                "market_id": result.market_id,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "fill_count": result.fill_count,
                "fill_rate": float(result.fill_rate),
                "maker_fill_rate": float(result.maker_fill_rate),
                "total_pnl": float(result.total_pnl),
            }

            # PnL components
            for k, v in result.pnl_components.items():
                row[f"pnl_{k}"] = float(v)

            # Segment labels — prefer explicit labels, fall back to config
            if labels and i < len(labels):
                row.update(labels[i])
            elif "segment" in result.config:
                row.update(result.config["segment"])

            rows.append(row)

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_events_for_segment(
        self,
        seg_df: pd.DataFrame,
        market_id: str,
    ) -> List[SimEvent]:
        """Build SimEvent list for a segment DataFrame, with market_id set."""
        events: List[SimEvent] = []
        for _, row in seg_df.iterrows():
            payload: Dict[str, Any] = {
                "p_hat": float(row["p_hat"]),
                "implied_probability": float(row["implied_probability"]),
                "mispricing": float(row["mispricing"]),
                "spread": float(row["spread"]),
                "fee_rate_current": float(row["fee_rate_current"]),
                "vol_regime": str(row["vol_regime"]),
                "time_bucket": str(row["time_bucket"]),
            }

            ts = row["predicted_at"]
            if not isinstance(ts, datetime):
                ts = pd.Timestamp(ts).to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            event = SimEvent(
                event_id=str(uuid.uuid4()),
                timestamp=ts,
                event_type="snapshot",
                market_id=market_id,
                token_id=str(row.get("token_id", "")),
                payload=payload,
            )
            events.append(event)

        # Sort by timestamp for deterministic replay order
        events.sort(key=lambda e: e.timestamp)
        return events
