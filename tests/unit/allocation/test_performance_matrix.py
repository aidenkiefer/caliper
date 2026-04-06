from __future__ import annotations

import math

import numpy as np

from services.allocation.performance_matrix import discounted_mean, ledoit_wolf_covariance


def test_discounted_mean_half_life_7_days() -> None:
    # Two returns: "now" (0 hours ago) and 7 days ago (168 hours ago).
    r = np.array([1.0, 0.0], dtype=float)
    hours_ago = np.array([0.0, 168.0], dtype=float)
    m = discounted_mean(r, hours_ago=hours_ago)
    # With half-life, weight(old)=0.5 weight(now); mean = 1 / (1 + 0.5) = 2/3.
    assert abs(m - (2.0 / 3.0)) < 1e-6


def test_ledoitwolf_covariance_is_psdish() -> None:
    rng = np.random.default_rng(7)
    X = rng.normal(size=(500, 4))
    cov = ledoit_wolf_covariance(X)
    eig = np.linalg.eigvalsh(cov)
    assert eig.min() > -1e-8

