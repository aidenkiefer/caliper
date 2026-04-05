from __future__ import annotations

import json
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from services.simulation.schemas import SimFill, SimResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    run_id: str
    validated_at: datetime
    fill_rate_sim: Decimal
    fill_rate_real: Decimal
    fill_rate_within_10pct: bool    # abs(sim - real) / real <= 0.10
    slippage_mean: Decimal
    slippage_std: Decimal
    pnl_correlation: Optional[Decimal]  # Pearson r of sim vs real PnL hourly series
    determinism_ok: bool
    notes: List[str] = field(default_factory=list)


class SimulationValidator:
    """
    Validates simulation results against known historical data.
    AC-5: fill rate within 10% of actual.
    AC-1: determinism check (same input → byte-identical output).
    """

    def __init__(self, db_url: Optional[str] = None) -> None:
        self._db_url = db_url

    def check_determinism(self, runner) -> tuple[bool, "SimResult"]:
        """Run runner.run() twice. Compare serialized JSON. Return (is_deterministic, first_result)."""
        result1 = runner.run()
        result2 = runner.run()
        json1 = result1.model_dump_json()
        json2 = result2.model_dump_json()
        ok = json1 == json2
        if not ok:
            logger.warning("Determinism check FAILED: simulation produced different output on two runs")
        return ok, result1

    def validate_fill_rate(self, sim_result: SimResult, real_fill_rate: Decimal) -> bool:
        """
        Returns True if |sim_fill_rate - real_fill_rate| / real_fill_rate <= 0.10 (AC-5).
        Uses a small epsilon to avoid divide-by-zero when real_fill_rate is 0.
        """
        denominator = max(real_fill_rate, Decimal("0.0001"))
        relative_error = abs(sim_result.fill_rate - real_fill_rate) / denominator
        return relative_error <= Decimal("0.10")

    def compute_slippage_stats(self, sim_fills: List[SimFill]) -> Tuple[Decimal, Decimal]:
        """
        Compute mean and std of slippage_vs_mid for taker fills only.
        Returns (Decimal(0), Decimal(0)) if no taker fills.
        """
        taker_slippages = [
            f.slippage_vs_mid
            for f in sim_fills
            if not f.maker_fill
        ]
        if not taker_slippages:
            return Decimal(0), Decimal(0)
        floats = [float(s) for s in taker_slippages]
        mean_f = statistics.mean(floats)
        std_f = statistics.stdev(floats) if len(floats) > 1 else 0.0
        return Decimal(str(round(mean_f, 8))), Decimal(str(round(std_f, 8)))

    def _pearson_correlation(
        self,
        xs: List[Decimal],
        ys: List[Decimal],
    ) -> Optional[Decimal]:
        """Pearson correlation using statistics.correlation (Python 3.10+)."""
        if len(xs) != len(ys) or len(xs) < 2:
            return None
        try:
            r = statistics.correlation([float(x) for x in xs], [float(y) for y in ys])
            return Decimal(str(round(r, 6)))
        except Exception as exc:
            logger.warning("Pearson correlation failed: %s", exc)
            return None

    def validate(
        self,
        runner,
        real_fill_rate: Decimal,
        real_pnl_series: Optional[List[Decimal]] = None,
    ) -> ValidationResult:
        """
        Full validation: determinism, fill rate, slippage, optional PnL correlation.
        """
        determinism_ok, sim_result = self.check_determinism(runner)  # 2 runs total, not 3
        fill_rate_ok = self.validate_fill_rate(sim_result, real_fill_rate)
        slippage_mean, slippage_std = self.compute_slippage_stats(sim_result.fills)

        pnl_correlation: Optional[Decimal] = None
        if real_pnl_series is not None and len(real_pnl_series) >= 2:
            # PnL correlation requires SimResult to expose an hourly series.
            # Currently SimResult only has total_pnl; correlation is deferred
            # until hourly PnL breakdown is added to SimResult.
            logger.debug("PnL correlation requested but SimResult has no hourly series; returning None")
            pnl_correlation = None

        notes: List[str] = []
        if not fill_rate_ok:
            notes.append(
                f"Fill rate divergence: sim={sim_result.fill_rate}, real={real_fill_rate}"
            )
        if not determinism_ok:
            notes.append("Determinism check failed")

        return ValidationResult(
            run_id=sim_result.run_id,
            validated_at=datetime.now(tz=timezone.utc),
            fill_rate_sim=sim_result.fill_rate,
            fill_rate_real=real_fill_rate,
            fill_rate_within_10pct=fill_rate_ok,
            slippage_mean=slippage_mean,
            slippage_std=slippage_std,
            pnl_correlation=pnl_correlation,
            determinism_ok=determinism_ok,
            notes=notes,
        )

    async def save_to_db(self, result: ValidationResult, db_url: str) -> None:
        """Insert ValidationResult into pm.simulation_validation."""
        import asyncpg
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """
                INSERT INTO pm.simulation_validation
                    (run_id, validated_at, fill_rate_sim, fill_rate_real,
                     slippage_mean, slippage_std, pnl_correlation, determinism_ok)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                result.run_id,
                result.validated_at,
                float(result.fill_rate_sim),
                float(result.fill_rate_real),
                float(result.slippage_mean),
                float(result.slippage_std),
                float(result.pnl_correlation) if result.pnl_correlation is not None else None,
                result.determinism_ok,
            )
        finally:
            await conn.close()
