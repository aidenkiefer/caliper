from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np

from services.regime.quality import (
    RegimeQualityWindow,
    expected_duration_minutes,
    posterior_entropy,
)


def test_entropy_uniform_is_log_k() -> None:
    k = 4
    p = np.ones(k) / k
    h = posterior_entropy(p)
    assert abs(h - math.log(k)) < 1e-6


def test_expected_duration_minutes_from_transition_diagonal() -> None:
    # Diagonal 0.5 => expected duration 1/(1-0.5) = 2 steps.
    T = np.eye(4) * 0.5 + (np.ones((4, 4)) - np.eye(4)) * (0.5 / 3.0)
    d = expected_duration_minutes(T, step_minutes=5.0)
    assert abs(d - 10.0) < 1e-6


def test_quality_window_tracks_switch_rate_and_agreement() -> None:
    w = RegimeQualityWindow(window=timedelta(hours=1))
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # 6 samples over 30 minutes -> 0.5h, 2 switches => 4/hour.
    labels = ["R1", "R1", "R2", "R2", "R1", "R1"]
    for i, lab in enumerate(labels):
        ts = t0 + timedelta(minutes=5 * i)
        w.push_hidden(ts, np.array([1.0, 0.0, 0.0, 0.0]))
        w.push_primary(ts, lab, lab)

    report = w.compute(transmat=np.eye(4))
    assert report.agreement_with_threshold == 1.0
    assert report.switch_rate_per_hour > 0.0

