"""Panel dataset builder for the BTC probability model.

Constructs the training dataset (one row per feature snapshot) with Y_h labels
derived from btc_distance_to_open proxy and walk-forward CV splits.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
import pandas as pd

from packages.common.polymarket_schemas import FeatureSnapshot
from services.ml.probability_model.schemas import WalkForwardFold

# Number of weeks held out as test set (never touched during CV)
_TEST_WEEKS = 2


def _to_utc(dt: datetime) -> pd.Timestamp:
    """Convert *dt* to a UTC-aware :class:`pd.Timestamp`.

    Handles both naive datetimes (localises to UTC) and already timezone-aware
    datetimes (converts to UTC).  Compatible with pandas < 2.0 and >= 2.0,
    which changed the behaviour of ``pd.Timestamp(dt, tz=...)`` when *dt* is
    already timezone-aware (raising ``TypeError`` in pandas >= 2.0).
    """
    ts = pd.Timestamp(dt)
    return ts.tz_convert("UTC") if ts.tzinfo is not None else ts.tz_localize("UTC")


def _hour_key(captured_at: datetime) -> str:
    """Truncate a UTC datetime to the hour and return an ISO string."""
    ts = captured_at.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    return ts.isoformat()


class PanelBuilder:
    """Builds the panel dataset used to train and evaluate the probability model.

    Parameters
    ----------
    db_url:
        asyncpg-compatible PostgreSQL connection string.  If *None*, falls back to
        the ``DATABASE_URL`` environment variable.  Only required when calling
        :meth:`load_from_db`; pure in-memory methods work without a DB connection.
    """

    def __init__(self, db_url: Optional[str] = None) -> None:
        self._db_url = db_url or os.environ.get("DATABASE_URL")

    # ------------------------------------------------------------------
    # DB loading
    # ------------------------------------------------------------------

    async def load_from_db(
        self,
        market_id: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Query ``pm.features`` for *market_id* in [*start*, *end*) and return a panel DataFrame.

        The returned DataFrame has the same schema as :meth:`build_panel` output.
        Rows are fetched as raw records and converted via :class:`FeatureSnapshot`.

        Parameters
        ----------
        market_id:
            Polymarket market identifier.
        start:
            Inclusive lower bound on ``captured_at`` (UTC).
        end:
            Exclusive upper bound on ``captured_at`` (UTC).
        """
        import asyncpg  # lazy import so the module is importable without asyncpg installed

        if not self._db_url:
            raise ValueError(
                "No DATABASE_URL configured.  Pass db_url to PanelBuilder or set "
                "the DATABASE_URL environment variable."
            )

        query = """
            SELECT *
            FROM pm.features
            WHERE market_id = $1
              AND captured_at >= $2
              AND captured_at < $3
            ORDER BY captured_at ASC
        """

        conn = await asyncpg.connect(self._db_url)
        try:
            rows = await conn.fetch(query, market_id, start, end)
        finally:
            await conn.close()

        snapshots: List[FeatureSnapshot] = [
            FeatureSnapshot.model_validate(dict(row)) for row in rows
        ]
        return self.build_panel(snapshots)

    # ------------------------------------------------------------------
    # Panel construction
    # ------------------------------------------------------------------

    def build_panel(self, snapshots: List[FeatureSnapshot]) -> pd.DataFrame:
        """Convert a list of :class:`FeatureSnapshot` objects into a labeled panel DataFrame.

        Each snapshot becomes one row.  ``Y_h`` is computed from the **final**
        snapshot of each hour using ``btc_distance_to_open > 0`` as a proxy label.
        For the most-recent (potentially incomplete) hour, ``Y_h`` is set to
        ``np.nan`` to avoid any lookahead bias.

        Added columns
        -------------
        hour_key       : str   — ISO hour string identifying the hourly interval
        t_minus_t0     : float — seconds since hour open (= time_since_open_seconds)
        time_to_close  : float — seconds remaining    (= time_to_close_seconds)
        Y_h            : float — 1.0 / 0.0 / NaN (NaN for incomplete current hour)
        imputed        : bool  — False for all real snapshots (True set by imputer)
        """
        if not snapshots:
            return pd.DataFrame()

        records = []
        for snap in snapshots:
            row = snap.model_dump()
            # Ensure captured_at is UTC-aware for consistent hour_key computation
            captured_at = snap.captured_at
            if captured_at.tzinfo is None:
                captured_at = captured_at.replace(tzinfo=timezone.utc)
            row["hour_key"] = _hour_key(captured_at)
            row["t_minus_t0"] = float(snap.time_since_open_seconds)
            row["time_to_close"] = float(snap.time_to_close_seconds)
            row["imputed"] = False
            records.append(row)

        df = pd.DataFrame(records)

        # --- Y_h proxy labeling: use last snapshot's btc_distance_to_open per hour ---
        # Identify which hour is the most-recent (potentially still open)
        all_hour_keys = df["hour_key"].unique()
        latest_hour = max(all_hour_keys, key=lambda hk: pd.Timestamp(hk))

        # For each closed hour, get the last snapshot's btc_distance_to_open.
        # For the most-recent hour, only mark Y_h as NaN when the hour is still
        # genuinely open (time_to_close_seconds > 1 on the last snapshot).
        # If the final snapshot shows the hour is closed (time_to_close_seconds
        # <= 1) we can safely derive the proxy label from that snapshot.
        hour_labels: dict[str, float] = {}
        for hk, group in df.groupby("hour_key"):
            last_row = group.sort_values("t_minus_t0").iloc[-1]
            if hk == latest_hour:
                # Only withhold the label if the hour may be incomplete
                time_to_close = float(last_row.get("time_to_close", 999))
                if time_to_close > 1:
                    # Hour still open — no lookahead, mark unknown
                    hour_labels[hk] = np.nan
                else:
                    # Hour closed by the time of the last snapshot; use proxy label
                    distance = float(last_row.get("btc_distance_to_open", 0))
                    hour_labels[hk] = 1.0 if distance > 0.0 else 0.0
            else:
                distance = float(last_row["btc_distance_to_open"])
                hour_labels[hk] = 1.0 if distance > 0.0 else 0.0

        df["Y_h"] = df["hour_key"].map(hour_labels)

        return df

    # ------------------------------------------------------------------
    # Binance label override
    # ------------------------------------------------------------------

    def attach_binance_labels(
        self,
        df: pd.DataFrame,
        klines: dict[str, int],
    ) -> pd.DataFrame:
        """Override ``Y_h`` with real Binance 1h kline labels.

        Parameters
        ----------
        df:
            Panel DataFrame produced by :meth:`build_panel`.
        klines:
            Mapping of ``hour_key`` → ``Y_h`` (0 or 1) from Binance kline data.
            Any ``hour_key`` not present in *klines* retains its existing ``Y_h``.
        """
        df = df.copy()
        mask = df["hour_key"].isin(klines)
        df.loc[mask, "Y_h"] = df.loc[mask, "hour_key"].map(klines).astype(float)
        return df

    # ------------------------------------------------------------------
    # Walk-forward CV
    # ------------------------------------------------------------------

    def build_walk_forward_folds(
        self,
        df: pd.DataFrame,
        min_train_weeks: int = 4,
    ) -> List[WalkForwardFold]:
        """Build walk-forward CV folds from the panel DataFrame.

        Logic
        -----
        - Groups data by ISO week (Monday-anchored).
        - The final ``_TEST_WEEKS`` weeks are withheld as the hold-out test set
          and are **never** included in any fold.
        - Folds roll one week at a time: fold *k* trains on weeks [0, k+1) and
          validates on week k+1.
        - Only folds with at least *min_train_weeks* training weeks are returned.

        Parameters
        ----------
        df:
            Panel DataFrame with a ``captured_at`` column (datetime or str).
        min_train_weeks:
            Minimum number of training weeks required before a fold is emitted.

        Returns
        -------
        List[WalkForwardFold]
            Ordered by fold_index ascending.
        """
        if df.empty:
            return []

        df = df.copy()
        # Ensure captured_at is a proper datetime with UTC timezone
        if not pd.api.types.is_datetime64_any_dtype(df["captured_at"]):
            df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True)
        elif df["captured_at"].dt.tz is None:
            df["captured_at"] = df["captured_at"].dt.tz_localize("UTC")

        # Assign ISO week label (year-week string for stable grouping)
        df["_iso_week"] = df["captured_at"].dt.to_period("W")

        sorted_weeks = sorted(df["_iso_week"].unique())

        if len(sorted_weeks) <= _TEST_WEEKS:
            # Not enough data for any fold; everything would be test
            return []

        # CV weeks exclude the final _TEST_WEEKS
        cv_weeks = sorted_weeks[: len(sorted_weeks) - _TEST_WEEKS]

        if len(cv_weeks) < min_train_weeks + 1:
            # Need at least min_train_weeks + 1 val week to produce any fold
            return []

        folds: List[WalkForwardFold] = []
        fold_index = 0

        # Fold k: train on cv_weeks[0..k], validate on cv_weeks[k+1]
        for k in range(min_train_weeks - 1, len(cv_weeks) - 1):
            train_weeks = cv_weeks[: k + 1]
            val_week = cv_weeks[k + 1]

            train_mask = df["_iso_week"].isin(train_weeks)
            val_mask = df["_iso_week"] == val_week

            train_df = df[train_mask]
            val_df = df[val_mask]

            if train_df.empty or val_df.empty:
                continue

            train_start = pd.Timestamp(cv_weeks[0].start_time).tz_localize("UTC").to_pydatetime()
            train_end = pd.Timestamp(cv_weeks[k].end_time).tz_localize("UTC").to_pydatetime()
            val_start = pd.Timestamp(val_week.start_time).tz_localize("UTC").to_pydatetime()
            val_end = pd.Timestamp(val_week.end_time).tz_localize("UTC").to_pydatetime()

            folds.append(
                WalkForwardFold(
                    fold_index=fold_index,
                    train_start=train_start,
                    train_end=train_end,
                    val_start=val_start,
                    val_end=val_end,
                )
            )
            fold_index += 1

        return folds

    # ------------------------------------------------------------------
    # Test set accessor
    # ------------------------------------------------------------------

    def get_test_set(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return the final ``_TEST_WEEKS`` weeks of data as the held-out test set.

        This slice must **not** be used during training or hyperparameter tuning.
        """
        if df.empty:
            return df.copy()

        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["captured_at"]):
            df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True)
        elif df["captured_at"].dt.tz is None:
            df["captured_at"] = df["captured_at"].dt.tz_localize("UTC")

        df["_iso_week"] = df["captured_at"].dt.to_period("W")
        sorted_weeks = sorted(df["_iso_week"].unique())

        if len(sorted_weeks) < _TEST_WEEKS:
            return df.drop(columns=["_iso_week"])

        test_weeks = sorted_weeks[-_TEST_WEEKS:]
        result = df[df["_iso_week"].isin(test_weeks)].drop(columns=["_iso_week"])
        return result.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Fold splitter
    # ------------------------------------------------------------------

    def split_by_fold(
        self,
        df: pd.DataFrame,
        fold: WalkForwardFold,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Return ``(train_df, val_df)`` for the given :class:`WalkForwardFold`.

        Rows are selected by ``captured_at`` falling within the inclusive bounds
        stored on the fold.

        Parameters
        ----------
        df:
            Full panel DataFrame.
        fold:
            A fold produced by :meth:`build_walk_forward_folds`.
        """
        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["captured_at"]):
            df["captured_at"] = pd.to_datetime(df["captured_at"], utc=True)
        elif df["captured_at"].dt.tz is None:
            df["captured_at"] = df["captured_at"].dt.tz_localize("UTC")

        # Ensure fold bounds are timezone-aware for comparison.
        # _to_utc handles both naive and already-tz-aware datetimes safely
        # across pandas < 2.0 and >= 2.0.
        train_start = _to_utc(fold.train_start)
        train_end   = _to_utc(fold.train_end)
        val_start   = _to_utc(fold.val_start)
        val_end     = _to_utc(fold.val_end)

        train_mask = (df["captured_at"] >= train_start) & (df["captured_at"] <= train_end)
        val_mask = (df["captured_at"] >= val_start) & (df["captured_at"] <= val_end)

        train_df = df[train_mask].reset_index(drop=True)
        val_df = df[val_mask].reset_index(drop=True)

        return train_df, val_df
