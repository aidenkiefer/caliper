from __future__ import annotations

from datetime import timedelta

import numpy as np
import pytest

from services.regime.trainer import HMMTrainer, HMMTrainerConfig


def test_hmm_trains_and_posteriors_sum_to_one() -> None:
    pytest.importorskip("hmmlearn")

    rng = np.random.default_rng(7)
    # Synthetic "30 day" sample (approx 30*24*12 5-min intervals) but keep it small for unit test.
    n = 2000
    d = 14
    X = rng.normal(size=(n, d))

    trainer = HMMTrainer(config=HMMTrainerConfig(n_states=4, random_seed=7), feature_names=[f"f{i}" for i in range(d)])
    artifact = trainer.fit(X)

    probs = artifact.model.predict_proba(X[:50])
    assert probs.shape == (50, 4)
    sums = probs.sum(axis=1)
    assert np.allclose(sums, 1.0, atol=1e-6)


def test_hmm_kmeans_init_is_deterministic() -> None:
    pytest.importorskip("hmmlearn")

    rng = np.random.default_rng(123)
    X = rng.normal(size=(500, 10))

    trainer1 = HMMTrainer(config=HMMTrainerConfig(n_states=4, random_seed=7), feature_names=[f"f{i}" for i in range(10)])
    trainer2 = HMMTrainer(config=HMMTrainerConfig(n_states=4, random_seed=7), feature_names=[f"f{i}" for i in range(10)])

    a1 = trainer1.fit(X)
    a2 = trainer2.fit(X)

    # Means should be identical given identical KMeans initialization + same random seed.
    assert np.allclose(a1.model.means_, a2.model.means_)

