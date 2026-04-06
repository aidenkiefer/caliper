from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

from statsmodels.tsa.stattools import grangercausalitytests
from scipy import stats

from services.ml.probability_model.schemas import LagTestResult


class LagTestRunner:
    """Runs four lead-lag tests on historical M(t) and p_PM(t) series.

    The mispricing signal is M(t) = p_hat(t) - p_PM(t).
    The hypothesis: M(t) > 0 predicts upward moves in p_PM(t + τ), i.e.,
    the model leads the market.

    Expected df columns:
        - 'mispricing'          : M(t) = p_hat - implied_probability
        - 'implied_probability' : p_PM(t)
        - 'predicted_at'        : timezone-aware or naive datetime timestamp
    """

    HORIZONS_SECONDS: list[int] = [10, 30, 60, 120, 300]

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_all(
        self,
        df: pd.DataFrame,
        period_start: datetime,
        period_end: datetime,
    ) -> list[LagTestResult]:
        """Run all 4 tests and return list of LagTestResult objects."""
        return [
            self.test_cross_correlation(df, period_start, period_end),
            self.test_granger_causality(df, period_start, period_end),
            self.test_event_study(df, period_start, period_end),
            self.test_persistence_curve(df, period_start, period_end),
        ]

    # ------------------------------------------------------------------
    # Test 1: Cross-correlation
    # ------------------------------------------------------------------

    def test_cross_correlation(
        self,
        df: pd.DataFrame,
        period_start: datetime,
        period_end: datetime,
    ) -> LagTestResult:
        """Test 1: corr(M(t), Δp_PM(t+τ)) for each horizon τ.

        Returns LagTestResult with results = {
            "horizons_seconds": [10, 30, 60, 120, 300],
            "correlations": [corr_10s, corr_30s, corr_60s, corr_120s, corr_300s],
            "n_obs": int,
            "peak_horizon_s": int,
        }
        """
        try:
            work = df.copy()
            work = work.sort_values("predicted_at").reset_index(drop=True)
            work["predicted_at"] = pd.to_datetime(work["predicted_at"])
            work = work.set_index("predicted_at")
            work.index = work.index.tz_localize(None) if work.index.tzinfo is not None else work.index

            mispricing = work["mispricing"].astype(float)
            implied = work["implied_probability"].astype(float)

            correlations: list[float] = []
            for tau in self.HORIZONS_SECONDS:
                shifted = implied.shift(-1, freq=f"{tau}s")
                aligned = pd.concat(
                    [mispricing, shifted.reindex(mispricing.index, method="nearest", tolerance=f"{tau}s")],
                    axis=1,
                )
                aligned.columns = ["m", "p_shifted"]
                aligned["delta_p"] = aligned["p_shifted"] - implied.reindex(mispricing.index)
                clean = aligned[["m", "delta_p"]].dropna()
                if len(clean) < 2:
                    correlations.append(float("nan"))
                else:
                    corr = float(np.corrcoef(clean["m"].values, clean["delta_p"].values)[0, 1])
                    correlations.append(corr)

            n_obs = len(mispricing.dropna())
            valid_corrs = [(h, c) for h, c in zip(self.HORIZONS_SECONDS, correlations) if not np.isnan(c) and c > 0]
            peak_horizon = max(valid_corrs, key=lambda x: x[1])[0] if valid_corrs else self.HORIZONS_SECONDS[0]

            return LagTestResult(
                run_at=datetime.now(tz=timezone.utc),
                test_type="cross_correlation",
                period_start=period_start,
                period_end=period_end,
                results={
                    "horizons_seconds": self.HORIZONS_SECONDS,
                    "correlations": [None if np.isnan(c) else c for c in correlations],
                    "n_obs": n_obs,
                    "peak_horizon_s": peak_horizon,
                },
            )
        except Exception as exc:
            return LagTestResult(
                run_at=datetime.now(tz=timezone.utc),
                test_type="cross_correlation",
                period_start=period_start,
                period_end=period_end,
                results={"error": str(exc), "n_obs": 0},
            )

    # ------------------------------------------------------------------
    # Test 2: Granger causality
    # ------------------------------------------------------------------

    def test_granger_causality(
        self,
        df: pd.DataFrame,
        period_start: datetime,
        period_end: datetime,
        max_lag: int = 6,
    ) -> LagTestResult:
        """Test 2: Granger causality using statsmodels VAR.

        Returns LagTestResult with results = {
            "max_lag": int,
            "granger_pvalue_by_lag": {lag: pvalue},
            "min_pvalue": float,
            "is_significant_at_05": bool,
        }
        """
        try:
            work = df.copy()
            work = work.sort_values("predicted_at").reset_index(drop=True)
            work["implied_probability"] = work["implied_probability"].astype(float)
            work["mispricing"] = work["mispricing"].astype(float)

            # First differences of implied_probability
            delta_p_pm = work["implied_probability"].diff().dropna()
            m = work["mispricing"].iloc[1:].reset_index(drop=True)
            delta_p_pm = delta_p_pm.reset_index(drop=True)

            data = pd.concat([delta_p_pm, m], axis=1)
            data.columns = ["delta_p_pm", "M"]
            data = data.dropna()

            # grangercausalitytests expects [y, x]: test whether x (M) Granger-causes y (delta_p_pm)
            gc_results = grangercausalitytests(data[["delta_p_pm", "M"]].values, maxlag=max_lag, verbose=False)

            pvalue_by_lag: dict[str, float] = {}
            for lag in range(1, max_lag + 1):
                pval = float(gc_results[lag][0]["ssr_ftest"][1])
                pvalue_by_lag[str(lag)] = pval

            min_pvalue = min(pvalue_by_lag.values())

            return LagTestResult(
                run_at=datetime.now(tz=timezone.utc),
                test_type="granger",
                period_start=period_start,
                period_end=period_end,
                results={
                    "max_lag": max_lag,
                    "granger_pvalue_by_lag": pvalue_by_lag,
                    "min_pvalue": min_pvalue,
                    "is_significant_at_05": min_pvalue < 0.05,
                },
            )
        except Exception as exc:
            return LagTestResult(
                run_at=datetime.now(tz=timezone.utc),
                test_type="granger",
                period_start=period_start,
                period_end=period_end,
                results={"error": str(exc), "n_obs": 0},
            )

    # ------------------------------------------------------------------
    # Test 3: Event study
    # ------------------------------------------------------------------

    def test_event_study(
        self,
        df: pd.DataFrame,
        period_start: datetime,
        period_end: datetime,
        theta: float = 0.05,
    ) -> LagTestResult:
        """Test 3: Event study near close.

        For each hour, compute average Δp_PM response in windows T-10m, T-5m,
        T-2m, T-1m conditional on large initial mispricing |M(t_0)| > theta.

        Returns LagTestResult with results = {
            "theta": theta,
            "windows": ["T-10m", "T-5m", "T-2m", "T-1m"],
            "avg_delta_ppm": [float, float, float, float],
            "ci_lower": [float, float, float, float],
            "ci_upper": [float, float, float, float],
            "n_hours": int,
        }
        """
        try:
            work = df.copy()
            work["predicted_at"] = pd.to_datetime(work["predicted_at"])
            work = work.sort_values("predicted_at").reset_index(drop=True)
            work["implied_probability"] = work["implied_probability"].astype(float)
            work["mispricing"] = work["mispricing"].astype(float)

            # Normalize timestamps to naive for arithmetic
            if work["predicted_at"].dt.tz is not None:
                work["predicted_at"] = work["predicted_at"].dt.tz_localize(None)

            windows_labels = ["T-10m", "T-5m", "T-2m", "T-1m"]
            windows_seconds = [600, 300, 120, 60]

            # Group by hour
            work["hour"] = work["predicted_at"].dt.floor("h")
            groups = work.groupby("hour")

            event_deltas: list[list[float]] = [[] for _ in windows_labels]

            for hour_ts, grp in groups:
                grp = grp.sort_values("predicted_at").reset_index(drop=True)
                if len(grp) == 0:
                    continue

                # t_0 = first snapshot of the hour
                t0_row = grp.iloc[0]
                t0_ts = t0_row["predicted_at"]
                t0_ppm = t0_row["implied_probability"]
                t0_m = t0_row["mispricing"]

                if abs(t0_m) <= theta:
                    continue

                # For each window, find the closest snapshot to t_0 + offset
                for i, offset_s in enumerate(windows_seconds):
                    target_ts = t0_ts + pd.Timedelta(seconds=offset_s)
                    time_diff = (grp["predicted_at"] - target_ts).abs()
                    nearest_idx = time_diff.idxmin()
                    nearest_row = grp.loc[nearest_idx]
                    delta = float(nearest_row["implied_probability"]) - float(t0_ppm)
                    event_deltas[i].append(delta)

            n_hours = len(event_deltas[0]) if event_deltas else 0

            avg_delta_ppm: list[Optional[float]] = []
            ci_lower: list[Optional[float]] = []
            ci_upper: list[Optional[float]] = []

            for deltas in event_deltas:
                if len(deltas) == 0:
                    avg_delta_ppm.append(None)
                    ci_lower.append(None)
                    ci_upper.append(None)
                elif len(deltas) == 1:
                    avg_delta_ppm.append(float(deltas[0]))
                    ci_lower.append(float(deltas[0]))
                    ci_upper.append(float(deltas[0]))
                else:
                    arr = np.array(deltas, dtype=float)
                    mean = float(arr.mean())
                    se = float(arr.std(ddof=1) / np.sqrt(len(arr)))
                    df_t = len(arr) - 1
                    lo, hi = stats.t.interval(0.95, df=df_t, loc=mean, scale=se)
                    avg_delta_ppm.append(mean)
                    ci_lower.append(float(lo))
                    ci_upper.append(float(hi))

            return LagTestResult(
                run_at=datetime.now(tz=timezone.utc),
                test_type="event_study",
                period_start=period_start,
                period_end=period_end,
                results={
                    "theta": theta,
                    "windows": windows_labels,
                    "avg_delta_ppm": avg_delta_ppm,
                    "ci_lower": ci_lower,
                    "ci_upper": ci_upper,
                    "n_hours": n_hours,
                },
            )
        except Exception as exc:
            return LagTestResult(
                run_at=datetime.now(tz=timezone.utc),
                test_type="event_study",
                period_start=period_start,
                period_end=period_end,
                results={"error": str(exc), "n_obs": 0},
            )

    # ------------------------------------------------------------------
    # Test 4: Persistence curve
    # ------------------------------------------------------------------

    def test_persistence_curve(
        self,
        df: pd.DataFrame,
        period_start: datetime,
        period_end: datetime,
    ) -> LagTestResult:
        """Test 4: Mispricing persistence half-life.

        Returns LagTestResult with results = {
            "horizons_seconds": [10, 30, 60, 120, 300],
            "persistence_ratios": [float, ...],
            "half_life_seconds": float | None,
            "n_obs": int,
        }
        """
        try:
            work = df.copy()
            work["predicted_at"] = pd.to_datetime(work["predicted_at"])
            work = work.sort_values("predicted_at").reset_index(drop=True)
            work["mispricing"] = work["mispricing"].astype(float)

            if work["predicted_at"].dt.tz is not None:
                work["predicted_at"] = work["predicted_at"].dt.tz_localize(None)

            work = work.set_index("predicted_at")
            m_series = work["mispricing"]

            n_obs = int((m_series.abs() > 0).sum())
            persistence_ratios: list[float] = []

            for tau in self.HORIZONS_SECONDS:
                shifted = m_series.shift(-1, freq=f"{tau}s")
                aligned = pd.concat(
                    [
                        m_series,
                        shifted.reindex(m_series.index, method="nearest", tolerance=f"{tau}s"),
                    ],
                    axis=1,
                )
                aligned.columns = ["m_t", "m_t_tau"]
                # Only include rows where |M(t)| > 0
                valid = aligned[aligned["m_t"].abs() > 0].dropna()
                if len(valid) == 0:
                    persistence_ratios.append(float("nan"))
                else:
                    ratios = valid["m_t_tau"].abs() / valid["m_t"].abs()
                    persistence_ratios.append(float(ratios.mean()))

            # Compute half-life by linear interpolation where ratio crosses 0.5
            half_life: Optional[float] = None
            horizons = self.HORIZONS_SECONDS
            for i in range(len(horizons) - 1):
                r0 = persistence_ratios[i]
                r1 = persistence_ratios[i + 1]
                if np.isnan(r0) or np.isnan(r1):
                    continue
                if r0 >= 0.5 and r1 <= 0.5:
                    # Linear interpolation between horizons[i] and horizons[i+1]
                    h0, h1 = float(horizons[i]), float(horizons[i + 1])
                    half_life = h0 + (h1 - h0) * (r0 - 0.5) / (r0 - r1)
                    break

            return LagTestResult(
                run_at=datetime.now(tz=timezone.utc),
                test_type="persistence",
                period_start=period_start,
                period_end=period_end,
                results={
                    "horizons_seconds": self.HORIZONS_SECONDS,
                    "persistence_ratios": [None if np.isnan(r) else r for r in persistence_ratios],
                    "half_life_seconds": half_life,
                    "n_obs": n_obs,
                },
            )
        except Exception as exc:
            return LagTestResult(
                run_at=datetime.now(tz=timezone.utc),
                test_type="persistence",
                period_start=period_start,
                period_end=period_end,
                results={"error": str(exc), "n_obs": 0},
            )
