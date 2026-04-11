# services/wallet_intelligence/clustering.py
from __future__ import annotations

from typing import Dict, List

from sklearn.cluster import KMeans


CLUSTER_LABELS: Dict[int, str] = {
    0: "informed_directionals",
    1: "efficient_makers",
    2: "noise_traders",
    3: "opportunists",
}


class WalletClusterer:
    """K-Means clustering on wallet feature vectors (k=4)."""

    def __init__(self, n_clusters: int = 4, random_state: int = 42) -> None:
        self.n_clusters = n_clusters
        self.random_state = random_state
        self._kmeans: KMeans | None = None

    def fit_predict(
        self,
        feature_matrix: List[List[float]],
        wallet_ids: List[str],
    ) -> Dict[str, int]:
        """Fit KMeans and return {wallet_id: cluster_id}."""
        km = KMeans(n_clusters=self.n_clusters, random_state=self.random_state, n_init=10)
        labels = km.fit_predict(feature_matrix)
        self._kmeans = km
        return {wid: int(label) for wid, label in zip(wallet_ids, labels)}

    def cluster_label(self, cluster_id: int) -> str:
        return CLUSTER_LABELS.get(cluster_id, "noise_traders")
