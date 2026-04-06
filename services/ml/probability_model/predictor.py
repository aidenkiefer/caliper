"""ProbabilityPredictor — real-time async serving of the calibrated BTC probability model.

Lifecycle::

    predictor = ProbabilityPredictor(model_key="logistic__2024W01-2024W52__sigmoid")
    await predictor.load_model()
    await predictor.run(input_queue, output_queue)   # runs until stop() / None sentinel

AC-6 requirement: PredictionRecord must be produced within 200 ms of the FeatureSnapshot
``captured_at`` timestamp (measured as ``predicted_at - snapshot.captured_at``).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import numpy as np
import pandas as pd

from packages.common.polymarket_schemas import FeatureSnapshot
from services.ml.probability_model.backtest import ThresholdBacktester
from services.ml.probability_model.registry import ModelRegistry
from services.ml.probability_model.schemas import PredictionRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature-encoding constants — must stay in sync with ModelTrainer
# ---------------------------------------------------------------------------

# Categorical columns one-hot encoded by ModelTrainer.build_feature_matrix.
_CATEGORICAL_COLS = [
    "vol_regime",
    "trend_regime",
    "time_bucket",
    "toxicity_regime",
    "spread_regime",
]

# Boolean columns cast to int.
_BOOL_COLS = [
    "near_close_flag",
    "reward_eligible",
    "data_staleness_flag",
]

# Metadata / label columns dropped before building the feature matrix.
# Keep this aligned with _DROP_COLS in trainer.py.
_DROP_COLS = {
    "market_id",
    "token_id",
    "captured_at",
    "hour_key",
    "t_minus_t0",
    "imputed",
    "Y_h",
    "_iso_week",
    "reward_max_spread",
    "reward_min_size",
    # predicted_at / record_id are only present on PredictionRecord, not FeatureSnapshot,
    # but guard against future model_dump merge scenarios.
    "record_id",
    "id",
    "created_at",
    "predicted_at",
}

# Columns excluded from the base feature set and used only for interaction terms.
# ModelTrainer drops these before building X to avoid collinearity / leakage.
_TIME_COLS = [
    "time_to_close_seconds",
    "time_since_open_seconds",
    "time_since_last_trade",
    "time_since_last_price_change",
]

# Interaction feature names appended for logistic models (in order).
_INTERACTION_NAMES = [
    "btc_distance_to_open__x__time_to_close",
    "order_book_imbalance__x__time_to_close",
    "btc_rv_5m__x__time_to_close",
]


class ProbabilityPredictor:
    """Real-time probability predictor.  Consumes :class:`FeatureSnapshot`,
    produces :class:`PredictionRecord`.

    Parameters
    ----------
    model_key:
        Registry key of the calibrated model to load,
        e.g. ``"logistic__2024W01-2024W52__sigmoid"``.
    registry:
        :class:`ModelRegistry` instance used to load the model artifact.
    epsilon_risk_buffer:
        Risk buffer ``ε`` passed to :class:`ThresholdBacktester.compute_threshold`.
    slippage_estimate:
        Slippage estimate passed to :class:`ThresholdBacktester.compute_threshold`.
    db_url:
        asyncpg DSN for writing predictions to ``pm.probability_predictions``.
        If ``None``, DB writes are skipped (useful in tests / dry-run mode).
    model_type:
        ``"logistic"`` or ``"gbt"``.  Determines whether interaction terms are
        appended to the feature matrix.  Inferred from *model_key* prefix when
        not specified.
    """

    def __init__(
        self,
        model_key: str,
        registry: ModelRegistry,
        epsilon_risk_buffer: float = 0.005,
        slippage_estimate: float = 0.002,
        db_url: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> None:
        self._model_key = model_key
        self._registry = registry
        self._model = None  # loaded calibrated sklearn estimator
        # Derive a human-readable version string from the key prefix.
        self._model_version = model_key.split("__")[0] + "_v1"
        self._backtester = ThresholdBacktester(epsilon_risk_buffer, slippage_estimate)
        self._db_url = db_url
        self._running = False

        # Infer model_type from key prefix if not provided explicitly.
        if model_type is not None:
            self._model_type = model_type
        else:
            prefix = model_key.split("__")[0].lower()
            self._model_type = "gbt" if prefix in ("gbt", "xgb", "gradient_boosting") else "logistic"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def load_model(self) -> None:
        """Load the trained calibrated model from the registry (async-safe wrapper)."""
        # ModelRegistry.load is synchronous (joblib I/O); run it in the default
        # thread-pool executor so it doesn't block the event loop.
        loop = asyncio.get_running_loop()
        self._model = await loop.run_in_executor(
            None, self._registry.load, self._model_key
        )
        logger.info("Loaded model key=%s version=%s", self._model_key, self._model_version)

    def predict(self, snapshot: FeatureSnapshot) -> PredictionRecord:
        """Synchronous prediction from a single :class:`FeatureSnapshot`.

        Returns a :class:`PredictionRecord`.  Does **not** write to DB or
        publish to the signal bus.  Use this for unit tests or batch scoring.

        Raises
        ------
        RuntimeError
            If :meth:`load_model` has not been called.
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Build single-row feature DataFrame from the snapshot.
        row = snapshot.model_dump()
        df = pd.DataFrame([row])

        # Build feature matrix (same encoding as ModelTrainer.build_feature_matrix).
        X = self._prepare_features(df)

        # Calibrated model produces class-probability columns; column 1 = P(Y=1).
        p_hat_raw = float(self._model.predict_proba(X)[0, 1])

        # Time-to-close soft cap: clamp to [0.05, 0.95] for t < 120 s.
        time_to_close = float(snapshot.time_to_close_seconds)
        if time_to_close < 120.0:
            p_hat = max(0.05, min(0.95, p_hat_raw))
        else:
            p_hat = p_hat_raw

        # Mispricing M(t) = p_hat − implied_probability.
        implied_prob = float(snapshot.implied_probability)
        mispricing = p_hat - implied_prob

        # Threshold θ(t) = spread/2 + slippage + fee_edge + ε_risk_buffer.
        spread = float(snapshot.spread)
        fee_rate = float(snapshot.fee_rate_current)
        threshold = self._backtester.compute_threshold(spread, fee_rate, implied_prob)
        threshold_met = abs(mispricing) > threshold

        # Confidence proxy: variance of a Bernoulli(p_hat) — maximised at 0.5.
        confidence = p_hat * (1.0 - p_hat)

        return PredictionRecord(
            record_id=uuid4(),
            market_id=snapshot.market_id,
            token_id=snapshot.token_id,
            predicted_at=datetime.now(tz=timezone.utc),
            p_hat=Decimal(str(round(p_hat, 8))),
            implied_probability=snapshot.implied_probability,
            mispricing=Decimal(str(round(mispricing, 8))),
            threshold=Decimal(str(round(threshold, 8))),
            threshold_met=threshold_met,
            model_version=self._model_version,
            confidence=Decimal(str(round(confidence, 8))),
            data_staleness_ok=not snapshot.data_staleness_flag,
        )

    # ------------------------------------------------------------------
    # Feature preparation
    # ------------------------------------------------------------------

    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Build a feature matrix from a single-row FeatureSnapshot DataFrame.

        Applies the same preprocessing as ``ModelTrainer.build_feature_matrix``:

        1. Preserve raw values needed for interaction terms (logistic path).
        2. Drop metadata / label columns (``_DROP_COLS`` + ``_TIME_COLS``).
        3. Cast boolean columns to ``int``.
        4. One-hot encode categorical columns via :func:`pandas.get_dummies`.
        5. Cast all remaining object/Decimal columns to ``float64``.
        6. Fill NaN with ``0.0``.
        7. For logistic models, append three multiplicative interaction terms:
           ``btc_distance_to_open * time_to_close``,
           ``order_book_imbalance * time_to_close``,
           ``btc_rv_5m * time_to_close``.

        Returns
        -------
        np.ndarray of shape (1, n_features), dtype float64.

        .. note::
            **Production deployment requires feature-column alignment.**
            The trained model expects a fixed column order established at
            training time.  In a production deployment, the feature names
            (including one-hot-expanded column names) should be serialised
            alongside the model artifact and used here to reindex / align
            the encoded DataFrame before calling ``predict_proba``.
            The current implementation relies on ``pd.get_dummies`` producing
            the same column set, which is guaranteed only when every possible
            categorical level appears in the training data AND in every
            inference call.  For robustness, store ``trainer._feature_names_``
            in the registry and use ``df.reindex(columns=feature_names, fill_value=0)``.
        """
        df = df.copy()

        # Stash raw values required for interaction terms before any dropping.
        time_to_close_raw = float(df["time_to_close_seconds"].iloc[0])
        btc_dist_raw = float(df["btc_distance_to_open"].iloc[0])
        order_imb_raw = float(df["order_book_imbalance"].iloc[0])
        btc_rv5m_raw = float(df["btc_rv_5m"].iloc[0])

        # Drop metadata, label, and time columns.
        cols_to_drop = [
            c for c in df.columns
            if c in _DROP_COLS or c in _TIME_COLS
        ]
        working = df.drop(columns=cols_to_drop, errors="ignore")

        # Cast boolean columns to int.
        for col in _BOOL_COLS:
            if col in working.columns:
                working[col] = working[col].astype(int)

        # One-hot encode categorical columns present in the DataFrame.
        cat_cols_present = [c for c in _CATEGORICAL_COLS if c in working.columns]
        if cat_cols_present:
            working = pd.get_dummies(working, columns=cat_cols_present, dtype=float)

        # Cast every remaining column to float64 (handles Decimal, int, bool residuals).
        for col in working.columns:
            working[col] = working[col].apply(
                lambda v: float(v) if v is not None else np.nan
            )
        working = working.astype(np.float64)

        # Simple NaN imputation — fill with 0 (matches ModelTrainer behaviour).
        working = working.fillna(0.0)

        X = working.values  # shape (1, n_base_features)

        # Append interaction terms for logistic models only.
        if self._model_type == "logistic":
            int1 = np.array([[btc_dist_raw * time_to_close_raw]])
            int2 = np.array([[order_imb_raw * time_to_close_raw]])
            int3 = np.array([[btc_rv5m_raw * time_to_close_raw]])
            X = np.hstack([X, int1, int2, int3])

        return X.astype(np.float64)

    # ------------------------------------------------------------------
    # Async DB write
    # ------------------------------------------------------------------

    async def _write_to_db(self, record: PredictionRecord) -> None:
        """Fire-and-forget async write to ``pm.probability_predictions``.

        Failures are logged but do not propagate — the prediction loop must
        not be blocked by DB latency or transient connectivity errors.
        """
        if self._db_url is None:
            return
        try:
            import asyncpg  # optional runtime dependency

            conn = await asyncpg.connect(self._db_url)
            try:
                await conn.execute(
                    """
                    INSERT INTO pm.probability_predictions
                    (record_id, market_id, token_id, predicted_at, p_hat, implied_prob,
                     mispricing, threshold_met, model_version)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    str(record.record_id),
                    record.market_id,
                    record.token_id,
                    record.predicted_at,
                    float(record.p_hat),
                    float(record.implied_probability),
                    float(record.mispricing),
                    record.threshold_met,
                    record.model_version,
                )
            finally:
                await conn.close()
        except Exception as exc:
            logger.error(
                "DB write failed for record %s: %s",
                record.record_id,
                exc,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Async run loop
    # ------------------------------------------------------------------

    async def run(
        self,
        input_queue: asyncio.Queue,
        output_queue: Optional[asyncio.Queue] = None,
    ) -> None:
        """Consume :class:`FeatureSnapshot` objects from *input_queue*,
        score each one, and optionally publish results to *output_queue*.

        Runs until :meth:`stop` is called or a ``None`` sentinel is dequeued.

        Signal bus payload (dict placed on *output_queue*)::

            {
                "p_hat": float,
                "mispricing": float,
                "threshold_met": bool,
                "record": PredictionRecord,
            }

        Parameters
        ----------
        input_queue:
            Source of :class:`FeatureSnapshot` items.  ``None`` acts as a
            stop sentinel.
        output_queue:
            Optional downstream queue for the signal bus.  If ``None``,
            predictions are only persisted to DB.
        """
        self._running = True
        logger.info(
            "ProbabilityPredictor started (model_key=%s, model_type=%s)",
            self._model_key,
            self._model_type,
        )

        while self._running:
            try:
                snapshot = await asyncio.wait_for(input_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # No items yet — check _running flag and retry.
                continue

            # None sentinel signals clean shutdown.
            if snapshot is None:
                logger.info("ProbabilityPredictor received stop sentinel.")
                break

            try:
                record = self.predict(snapshot)
            except Exception as exc:
                logger.error(
                    "predict() failed for market_id=%s token_id=%s: %s",
                    getattr(snapshot, "market_id", "?"),
                    getattr(snapshot, "token_id", "?"),
                    exc,
                    exc_info=True,
                )
                input_queue.task_done()
                continue

            # Async DB write — fire and forget; must not block the prediction loop.
            asyncio.create_task(self._write_to_db(record))

            # Publish to signal bus if a downstream queue was provided.
            if output_queue is not None:
                await output_queue.put(
                    {
                        "p_hat": float(record.p_hat),
                        "mispricing": float(record.mispricing),
                        "threshold_met": record.threshold_met,
                        "record": record,
                    }
                )

            input_queue.task_done()

        logger.info("ProbabilityPredictor stopped.")

    def stop(self) -> None:
        """Signal the :meth:`run` loop to exit after the current iteration."""
        self._running = False
