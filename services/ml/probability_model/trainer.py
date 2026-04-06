"""ModelTrainer for the BTC probability model.

Trains and calibrates logistic regression (Platt scaling) and gradient boosted
tree models over panel DataFrames produced by :mod:`dataset`.  Evaluation
metrics include Brier score, Expected Calibration Error (ECE), AUC, and a
reliability diagram.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import cross_val_score

from services.ml.probability_model.schemas import (
    BrierDecomposition,
    CalibrationBin,
    CalibrationReport,
    ModelType,
    WalkForwardFold,
)

# Minimum number of labeled rows required to proceed with training.
# 24 h/day × 7 days/week × 4 weeks = 672 rows (per the ticket spec).
_MIN_TRAIN_ROWS = 672

# Categorical columns that should be one-hot encoded.
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

# Columns to drop before building the feature matrix (non-feature / metadata).
_DROP_COLS = {
    # identity / timing
    "market_id",
    "token_id",
    "captured_at",
    # panel builder additions
    "hour_key",
    "t_minus_t0",
    "imputed",
    # label
    "Y_h",
    # internal helpers that may be added by PanelBuilder / test code
    "_iso_week",
    # reward helpers — optional, keep None-valued ones out
    "reward_max_spread",
    "reward_min_size",
}

# Logistic model interaction feature names (for documentation / debugging).
_INTERACTION_NAMES = [
    "btc_distance_to_open__x__time_to_close",
    "order_book_imbalance__x__time_to_close",
    "btc_rv_5m__x__time_to_close",
]

# Default C grid searched during cross-validation.
_C_GRID = [0.001, 0.01, 0.1, 1.0, 10.0]


def _compute_brier_decomposition(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> dict[str, float]:
    """Murphy (1973) Brier score decomposition: Reliability - Resolution + Uncertainty."""
    y_bar = float(y_true.mean())
    bin_edges = np.linspace(0, 1, n_bins + 1)
    n = len(y_true)
    reliability = 0.0
    resolution = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i+1])
        if mask.sum() == 0:
            continue
        n_k = mask.sum()
        obs_k = float(y_true[mask].mean())
        pred_k = float(y_prob[mask].mean())
        reliability += (n_k / n) * (pred_k - obs_k) ** 2
        resolution += (n_k / n) * (obs_k - y_bar) ** 2
    uncertainty = y_bar * (1.0 - y_bar)
    return {
        "reliability": round(reliability, 8),
        "resolution": round(resolution, 8),
        "uncertainty": round(uncertainty, 8),
    }


def _compute_ece(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> tuple[float, list[dict[str, float]]]:
    """Compute Expected Calibration Error and reliability diagram bins.

    Parameters
    ----------
    y_true:
        Ground-truth binary labels (0/1).
    y_prob:
        Predicted probabilities in [0, 1].
    n_bins:
        Number of equal-width bins.

    Returns
    -------
    ece : float
    bins : list of dicts with keys bin_midpoint, observed_freq, predicted_freq
    """
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    bins: list[dict[str, float]] = []
    for i in range(n_bins):
        mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i + 1])
        if mask.sum() == 0:
            bins.append(
                {
                    "bin_midpoint": float((bin_edges[i] + bin_edges[i + 1]) / 2),
                    "observed_freq": 0.0,
                    "predicted_freq": 0.0,
                }
            )
            continue
        obs = float(y_true[mask].mean())
        pred = float(y_prob[mask].mean())
        ece += (mask.sum() / len(y_true)) * abs(pred - obs)
        bins.append(
            {
                "bin_midpoint": float((bin_edges[i] + bin_edges[i + 1]) / 2),
                "observed_freq": obs,
                "predicted_freq": pred,
            }
        )
    return float(ece), bins


class ModelTrainer:
    """Trains and calibrates the BTC probability models.

    Supports two model types:

    - ``"logistic"``: regularized logistic regression with Platt scaling
      (sigmoid calibration via :class:`sklearn.calibration.CalibratedClassifierCV`).
    - ``"gbt"``: gradient boosted trees with isotonic regression calibration
      (implemented in Task 14-04).

    Parameters
    ----------
    model_type:
        One of ``"logistic"`` or ``"gbt"``.
    random_state:
        Seed for all stochastic components.
    """

    def __init__(
        self,
        model_type: ModelType = "logistic",
        random_state: int = 42,
    ) -> None:
        self.model_type: ModelType = model_type
        self.random_state = random_state
        self._model_version = f"{model_type}_v1"

    # ------------------------------------------------------------------
    # Feature matrix construction
    # ------------------------------------------------------------------

    def build_feature_matrix(
        self,
        df: pd.DataFrame,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Extract feature matrix *X* and label vector *y* from a panel DataFrame.

        Rows where ``Y_h`` is ``NaN`` are dropped before processing.

        For ``model_type="logistic"``, three multiplicative interaction terms are
        appended after the base encoded features:

        - ``btc_distance_to_open * time_to_close``
        - ``order_book_imbalance * time_to_close``
        - ``btc_rv_5m * time_to_close``

        Decimal columns are cast to float before multiplication.

        Categorical columns (``vol_regime``, ``trend_regime``, ``time_bucket``,
        ``toxicity_regime``, ``spread_regime``) are one-hot encoded via
        :func:`pandas.get_dummies`.  Boolean columns (``near_close_flag``,
        ``reward_eligible``, ``data_staleness_flag``) are cast to ``int``.

        Returns
        -------
        X : np.ndarray of shape (n_samples, n_features), dtype float64
        y : np.ndarray of shape (n_samples,), dtype int
        """
        df = df.copy()

        # Drop rows with no label.
        df = df[df["Y_h"].notna()].reset_index(drop=True)

        # Preserve raw interaction source columns before encoding/dropping.
        time_to_close_raw = df["time_to_close"].astype(float).values
        btc_dist_raw = df["btc_distance_to_open"].apply(float).values
        order_imb_raw = df["order_book_imbalance"].apply(float).values
        btc_rv5m_raw = df["btc_rv_5m"].apply(float).values

        # Extract labels.
        y = df["Y_h"].astype(int).values

        # Drop metadata / label columns.
        drop_cols = [c for c in _DROP_COLS if c in df.columns]
        # Also drop time_to_close from the base feature set to avoid
        # information leakage (it will be used only in interaction terms).
        for extra in ("time_to_close", "time_since_open_seconds", "time_since_last_trade",
                      "time_since_last_price_change"):
            if extra in df.columns and extra not in drop_cols:
                drop_cols.append(extra)

        working = df.drop(columns=drop_cols, errors="ignore")

        # Cast boolean columns to int.
        for col in _BOOL_COLS:
            if col in working.columns:
                working[col] = working[col].astype(int)

        # One-hot encode categorical columns.
        cat_cols_present = [c for c in _CATEGORICAL_COLS if c in working.columns]
        if cat_cols_present:
            working = pd.get_dummies(working, columns=cat_cols_present, dtype=float)

        # Cast all remaining columns to float64 (handles Decimal, int, bool).
        for col in working.columns:
            working[col] = working[col].apply(
                lambda v: float(v) if v is not None else np.nan
            )
        working = working.astype(np.float64)

        # Fill any remaining NaNs with 0 (simple imputation for missing optionals).
        working = working.fillna(0.0)

        X = working.values  # shape (n_samples, n_base_features)

        # Append interaction terms for the logistic model.
        if self.model_type == "logistic":
            int1 = (btc_dist_raw * time_to_close_raw).reshape(-1, 1)
            int2 = (order_imb_raw * time_to_close_raw).reshape(-1, 1)
            int3 = (btc_rv5m_raw * time_to_close_raw).reshape(-1, 1)
            X = np.hstack([X, int1, int2, int3])

        return X.astype(np.float64), y

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        tune_C: bool = True,
    ) -> dict[str, Any]:
        """Train and calibrate the model on *train_df*, then evaluate on *val_df*.

        Parameters
        ----------
        train_df:
            Panel DataFrame for the training fold (produced by :class:`PanelBuilder`).
        val_df:
            Panel DataFrame for the validation fold.
        tune_C:
            Whether to search over ``_C_GRID`` for the best regularisation
            strength via 3-fold cross-validation on *train_df*.  Only relevant
            for ``model_type="logistic"``.

        Returns
        -------
        dict with keys:

        - ``model``: the fitted (uncalibrated) sklearn estimator
        - ``calibrated_model``: the calibrated estimator (use this for predictions)
        - ``brier_score``: float
        - ``ece``: float
        - ``auc``: float
        - ``reliability``: list of :class:`CalibrationBin` dicts
        - ``fold_metrics``: dict with a subset of the above for convenience
        - ``model_version``: str

        Raises
        ------
        ValueError
            If *train_df* contains fewer than ``_MIN_TRAIN_ROWS`` labeled rows.
        NotImplementedError
            If ``model_type="gbt"`` (implemented in Task 14-04).
        """
        if self.model_type == "gbt":
            raise NotImplementedError("GBT model implemented in Task 14-04")

        # --- Build feature matrices ---
        X_train, y_train = self.build_feature_matrix(train_df)
        X_val, y_val = self.build_feature_matrix(val_df)

        # --- Minimum sample guard ---
        if len(X_train) < _MIN_TRAIN_ROWS:
            raise ValueError(
                f"Insufficient labeled training data: {len(X_train)} rows found, "
                f"but at least {_MIN_TRAIN_ROWS} are required "
                f"(24 h/day × 4 weeks = {_MIN_TRAIN_ROWS} hours)."
            )

        # --- Hyperparameter tuning ---
        best_C = 1.0
        if tune_C:
            best_score = -np.inf
            for C in _C_GRID:
                candidate = LogisticRegression(
                    C=C,
                    max_iter=1000,
                    random_state=self.random_state,
                )
                scores = cross_val_score(
                    candidate,
                    X_train,
                    y_train,
                    cv=3,
                    scoring="neg_brier_score",
                )
                mean_score = float(scores.mean())
                if mean_score > best_score:
                    best_score = mean_score
                    best_C = C

        # --- Fit base model ---
        lr = LogisticRegression(
            C=best_C,
            max_iter=1000,
            random_state=self.random_state,
        )
        lr.fit(X_train, y_train)

        # --- Platt scaling: fit calibration on the validation fold ---
        calibrated = CalibratedClassifierCV(
            estimator=lr,
            method="sigmoid",
            cv="prefit",
        )
        calibrated.fit(X_val, y_val)

        # --- Evaluate calibrated model on validation fold ---
        cal_report = self.evaluate(calibrated, X_val, y_val)

        fold_metrics = {
            "brier_score": float(cal_report.brier_score),
            "ece": float(cal_report.ece),
            "auc": float(cal_report.auc) if cal_report.auc is not None else None,
            "best_C": best_C,
            "n_train": len(X_train),
            "n_val": len(X_val),
        }

        return {
            "model": lr,
            "calibrated_model": calibrated,
            "brier_score": float(cal_report.brier_score),
            "ece": float(cal_report.ece),
            "auc": float(cal_report.auc) if cal_report.auc is not None else None,
            "reliability": [b.model_dump() for b in cal_report.reliability],
            "fold_metrics": fold_metrics,
            "model_version": self._model_version,
        }

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        calibrated_model: Any,
        X: np.ndarray,
        y: np.ndarray,
    ) -> CalibrationReport:
        """Compute Brier score, ECE (10 bins), AUC, and a reliability diagram.

        Parameters
        ----------
        calibrated_model:
            A fitted sklearn-compatible model that exposes ``predict_proba``.
        X:
            Feature matrix (n_samples, n_features).
        y:
            Ground-truth binary labels.

        Returns
        -------
        :class:`CalibrationReport`
            ``needs_recal`` is set to ``False``; the DriftMonitor sets this flag
            separately on a rolling 7-day window.
        """
        y_prob = calibrated_model.predict_proba(X)[:, 1]

        brier = float(brier_score_loss(y, y_prob))

        ece_val, bin_dicts = _compute_ece(y, y_prob)

        decomp_dict = _compute_brier_decomposition(y, y_prob)
        decomp_instance = BrierDecomposition(
            reliability=decomp_dict["reliability"],
            resolution=decomp_dict["resolution"],
            uncertainty=decomp_dict["uncertainty"],
        )

        # AUC is undefined if only one class is present.
        try:
            auc = float(roc_auc_score(y, y_prob))
        except ValueError:
            auc = None

        reliability = [
            CalibrationBin(
                bin_midpoint=b["bin_midpoint"],
                observed_freq=b["observed_freq"],
                predicted_freq=b["predicted_freq"],
            )
            for b in bin_dicts
        ]

        return CalibrationReport(
            generated_at=datetime.now(tz=timezone.utc),
            model_version=self._model_version,
            brier_score=round(brier, 8),
            ece=round(ece_val, 8),
            auc=round(auc, 8) if auc is not None else None,
            reliability=reliability,
            needs_recal=False,
            brier_decomposition=decomp_instance,
        )

    # ------------------------------------------------------------------
    # Walk-forward training
    # ------------------------------------------------------------------

    def walk_forward_train(
        self,
        full_df: pd.DataFrame,
        folds: list[WalkForwardFold],
    ) -> list[dict[str, Any]]:
        """Run :meth:`train` for each walk-forward fold.

        Parameters
        ----------
        full_df:
            Complete panel DataFrame (all folds combined).
        folds:
            Fold definitions produced by :meth:`PanelBuilder.build_walk_forward_folds`.

        Returns
        -------
        list of per-fold result dicts (same structure as :meth:`train` output),
        with an additional ``fold_index`` key.
        """
        from services.ml.probability_model.dataset import PanelBuilder

        builder = PanelBuilder()
        results: list[dict[str, Any]] = []

        for fold in folds:
            train_df, val_df = builder.split_by_fold(full_df, fold)
            result = self.train(train_df, val_df)
            result["fold_index"] = fold.fold_index
            results.append(result)

        return results
