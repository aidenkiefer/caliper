from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import numpy as np

from services.regime.schemas import RegimeLabel


_G_T_FEATURES: List[str] = [
    # Volatility
    "btc_rv_1m",
    "btc_rv_5m",
    "btc_rv_15m",
    # Liquidity
    "spread_bps",
    "book_depth_bid_5tick",
    "book_depth_ask_5tick",
    # Trend
    "btc_momentum_5m",
    "btc_sign_persistence_5m",
    "btc_distance_to_open",
    # Toxicity
    "vpin_proxy",
    "trade_flow_imbalance_5m",
    "last_5min_volume_share",
    # Funding
    "btc_funding_rate",
    "btc_basis_proxy",
]


@dataclass
class HMMArtifact:
    """In-memory model artifact for HMM regime inference."""

    model: object
    state_to_regime: Dict[int, RegimeLabel]
    feature_names: List[str]


class HMMRegimeClassifier:
    """
    Gaussian HMM wrapper (hmmlearn) for regime probabilities.

    The model produces posteriors over K hidden states (default K=4). A separate
    mapping collapses hidden state probabilities into semantic regime labels.
    """

    def __init__(self, artifact: HMMArtifact):
        self._artifact = artifact

    @property
    def n_states(self) -> int:
        return int(getattr(self._artifact.model, "n_components"))

    @property
    def feature_names(self) -> List[str]:
        return list(self._artifact.feature_names)

    @staticmethod
    def default_feature_names() -> List[str]:
        return list(_G_T_FEATURES)

    def encode_rows(self, rows: Iterable[object]) -> np.ndarray:
        data: List[List[float]] = []
        for row in rows:
            data.append([float(getattr(row, k)) for k in self._artifact.feature_names])
        return np.asarray(data, dtype=float)

    def encode_snapshot(self, snapshot: object) -> np.ndarray:
        return np.asarray([float(getattr(snapshot, k)) for k in self._artifact.feature_names], dtype=float)

    def predict_hidden_posterior(self, x: np.ndarray) -> np.ndarray:
        """
        Return posterior probabilities over hidden states for one or more rows.

        Parameters
        ----------
        x:
            Shape (n_features,) or (n_samples, n_features)
        """
        X = x.reshape(1, -1) if x.ndim == 1 else x
        proba = self._artifact.model.predict_proba(X)
        return np.asarray(proba, dtype=float)

    def hidden_to_regime_probabilities(self, hidden_posterior: Sequence[float]) -> Dict[RegimeLabel, float]:
        totals: Dict[RegimeLabel, float] = {"R1": 0.0, "R2": 0.0, "R3": 0.0, "R4": 0.0, "R5": 0.0}
        for state_idx, p in enumerate(hidden_posterior):
            regime = self._artifact.state_to_regime.get(int(state_idx), "R2")
            totals[regime] += float(p)

        # Normalize only across {R1,R2,R3} (R4/R5 handled by threshold classifier).
        s = totals["R1"] + totals["R2"] + totals["R3"]
        if s <= 0:
            return totals
        totals["R1"] /= s
        totals["R2"] /= s
        totals["R3"] /= s
        return totals

    def predict(self, snapshot: object) -> Dict[str, object]:
        """
        Predict on one snapshot.

        Returns a dict with:
          - hidden_posterior: np.ndarray shape (K,)
          - regime_probabilities: Dict[RegimeLabel, float] over R1..R3 (normalized) + R4/R5=0
        """
        x = self.encode_snapshot(snapshot)
        hidden = self.predict_hidden_posterior(x)[0]
        regime_probs = self.hidden_to_regime_probabilities(hidden)
        return {"hidden_posterior": hidden, "regime_probabilities": regime_probs}

