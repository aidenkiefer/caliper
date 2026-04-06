from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from services.regime.classifiers.hmm import HMMArtifact, HMMRegimeClassifier
from services.regime.schemas import RegimeLabel


@dataclass(frozen=True)
class HMMTrainerConfig:
    n_states: int = 4
    random_seed: int = 7


class HMMTrainer:
    """Minimal in-memory trainer scaffold (Sprint 15)."""

    def __init__(
        self,
        config: Optional[HMMTrainerConfig] = None,
        feature_names: Optional[List[str]] = None,
    ) -> None:
        self._config = config or HMMTrainerConfig()
        self._feature_names = feature_names or HMMRegimeClassifier.default_feature_names()

    def fit(self, X: np.ndarray) -> HMMArtifact:
        """
        Fit a GaussianHMM using KMeans initialization (deterministic).

        X is expected to be (n_samples, n_features) and already standardized if desired.
        """
        from hmmlearn.hmm import GaussianHMM
        from sklearn.cluster import KMeans

        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError("X must be 2D (n_samples, n_features)")

        kmeans = KMeans(n_clusters=self._config.n_states, n_init=10, random_state=self._config.random_seed)
        labels = kmeans.fit_predict(X)
        means = kmeans.cluster_centers_

        # Empirical covars per cluster; fall back to global covariance on degenerate clusters.
        n_features = X.shape[1]
        global_covar = np.cov(X.T) + 1e-6 * np.eye(n_features)
        covars = np.zeros((self._config.n_states, n_features, n_features), dtype=float)
        for k in range(self._config.n_states):
            rows = X[labels == k]
            if rows.shape[0] < 2:
                covars[k] = global_covar
            else:
                covars[k] = np.cov(rows.T) + 1e-6 * np.eye(n_features)

        model = GaussianHMM(
            n_components=self._config.n_states,
            covariance_type="full",
            n_iter=200,
            random_state=self._config.random_seed,
        )

        model.startprob_ = np.full(self._config.n_states, 1.0 / self._config.n_states)

        # Slight persistence bias for stability.
        trans = np.full((self._config.n_states, self._config.n_states), 1.0 / self._config.n_states)
        np.fill_diagonal(trans, 0.70)
        trans = trans / trans.sum(axis=1, keepdims=True)
        model.transmat_ = trans

        model.means_ = means
        model.covars_ = covars

        model.fit(X)

        mapping = self._map_states_to_regimes(model.means_, self._feature_names)
        return HMMArtifact(model=model, state_to_regime=mapping, feature_names=list(self._feature_names))

    @staticmethod
    def _map_states_to_regimes(means: np.ndarray, feature_names: List[str]) -> Dict[int, RegimeLabel]:
        """
        Heuristic mapping of hidden states → {R1,R2,R3}.

        This is intentionally simple and deterministic.
        """
        idx = {name: i for i, name in enumerate(feature_names)}
        mapping: Dict[int, RegimeLabel] = {}
        for k in range(means.shape[0]):
            vpin = float(means[k, idx.get("vpin_proxy", 0)])
            rv_5m = float(means[k, idx.get("btc_rv_5m", 0)])
            sign_persist = float(means[k, idx.get("btc_sign_persistence_5m", 0)])
            momentum = float(means[k, idx.get("btc_momentum_5m", 0)])

            if vpin >= 0.65:
                mapping[k] = "R3"
                continue

            if rv_5m >= 0.002 and sign_persist < 0.6 and abs(momentum) < 0.001:
                mapping[k] = "R2"
                continue

            mapping[k] = "R1"
        return mapping

