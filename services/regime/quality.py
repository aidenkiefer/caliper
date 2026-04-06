from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque, Optional, Sequence, Tuple

import numpy as np

from services.regime.schemas import RegimeLabel, RegimeQualityReport


def posterior_entropy(posterior: Sequence[float]) -> float:
    """Shannon entropy H(p) with natural log."""
    p = np.asarray(posterior, dtype=float)
    p = p / max(float(p.sum()), 1e-12)
    p = np.clip(p, 1e-12, 1.0)
    return float(-np.sum(p * np.log(p)))


def expected_duration_minutes(transmat: np.ndarray, step_minutes: float = 5.0) -> float:
    """
    Expected state duration in minutes based on diagonal of transition matrix.

    For a Markov chain, expected duration in steps for state i is 1/(1 - p_ii).
    """
    T = np.asarray(transmat, dtype=float)
    if T.ndim != 2 or T.shape[0] != T.shape[1]:
        return 0.0
    diags = np.clip(np.diag(T), 0.0, 0.999999)
    durations = 1.0 / (1.0 - diags)
    return float(np.mean(durations) * step_minutes)


def agreement_jaccard(primary_a: Sequence[RegimeLabel], primary_b: Sequence[RegimeLabel]) -> float:
    """
    Jaccard-style overlap between two primary-label sequences over the same window.

    Implemented as intersection/union over per-index agreement:
      intersection = count(a_i == b_i)
      union        = N
    """
    n = min(len(primary_a), len(primary_b))
    if n == 0:
        return 0.0
    matches = sum(1 for i in range(n) if primary_a[i] == primary_b[i])
    return float(matches) / float(n)


def switch_rate_per_hour(labels: Sequence[RegimeLabel], window_seconds: float) -> float:
    if len(labels) < 2 or window_seconds <= 0:
        return 0.0
    switches = 0
    prev = labels[0]
    for lab in labels[1:]:
        if lab != prev:
            switches += 1
            prev = lab
    hours = window_seconds / 3600.0
    return float(switches) / max(hours, 1e-9)


def quality_score(
    entropy: float,
    k: int,
    switch_rate: float,
    expected_duration_min: float,
    agreement: float,
) -> float:
    """
    Deterministic composite score in [0,1].
    """
    max_entropy = math.log(max(k, 2))
    ent_score = 1.0 - min(entropy / max_entropy, 1.0)

    # Switch rates above ~2/hour are considered noisy.
    sw_score = max(0.0, 1.0 - (switch_rate / 2.0))

    # Durations < 15m are suspicious; >= 60m is "good enough".
    if expected_duration_min <= 15.0:
        dur_score = 0.0
    elif expected_duration_min >= 60.0:
        dur_score = 1.0
    else:
        dur_score = (expected_duration_min - 15.0) / (60.0 - 15.0)

    ag_score = float(max(0.0, min(agreement, 1.0)))

    score = 0.4 * ent_score + 0.3 * ag_score + 0.2 * sw_score + 0.1 * dur_score
    return float(max(0.0, min(score, 1.0)))


@dataclass
class RegimeQualityWindow:
    """
    Rolling window tracker used by RegimeDetector to compute quality metrics.
    """

    window: timedelta = timedelta(hours=1)
    _hidden_posteriors: Deque[Tuple[datetime, np.ndarray]] = deque()
    _hmm_primary: Deque[Tuple[datetime, RegimeLabel]] = deque()
    _threshold_primary: Deque[Tuple[datetime, RegimeLabel]] = deque()

    def push_hidden(self, ts: datetime, posterior: np.ndarray) -> None:
        self._hidden_posteriors.append((ts, np.asarray(posterior, dtype=float)))
        self._trim(ts)

    def push_primary(self, ts: datetime, hmm_primary: RegimeLabel, threshold_primary: RegimeLabel) -> None:
        self._hmm_primary.append((ts, hmm_primary))
        self._threshold_primary.append((ts, threshold_primary))
        self._trim(ts)

    def _trim(self, now: datetime) -> None:
        cutoff = now - self.window
        while self._hidden_posteriors and self._hidden_posteriors[0][0] < cutoff:
            self._hidden_posteriors.popleft()
        while self._hmm_primary and self._hmm_primary[0][0] < cutoff:
            self._hmm_primary.popleft()
        while self._threshold_primary and self._threshold_primary[0][0] < cutoff:
            self._threshold_primary.popleft()

    def compute(
        self,
        *,
        computed_at: Optional[datetime] = None,
        transmat: Optional[np.ndarray] = None,
        step_minutes: float = 5.0,
    ) -> RegimeQualityReport:
        computed_at = computed_at or datetime.now(timezone.utc)
        self._trim(computed_at)

        if self._hidden_posteriors:
            last_p = self._hidden_posteriors[-1][1]
            ent = posterior_entropy(last_p)
            k = int(last_p.shape[0])
        else:
            ent = 0.0
            k = 4

        if self._hmm_primary:
            window_seconds = (self._hmm_primary[-1][0] - self._hmm_primary[0][0]).total_seconds()
        else:
            window_seconds = 0.0

        hmm_labels = [lab for _, lab in self._hmm_primary]
        thr_labels = [lab for _, lab in self._threshold_primary]

        sw_rate = switch_rate_per_hour(hmm_labels, window_seconds)
        agreement = agreement_jaccard(hmm_labels, thr_labels)
        dur = expected_duration_minutes(transmat, step_minutes=step_minutes) if transmat is not None else 0.0
        score = quality_score(entropy=ent, k=k, switch_rate=sw_rate, expected_duration_min=dur, agreement=agreement)

        return RegimeQualityReport(
            computed_at=computed_at,
            posterior_entropy=float(ent),
            switch_rate_per_hour=float(sw_rate),
            expected_duration_minutes=float(dur),
            agreement_with_threshold=float(agreement),
            quality_score=float(score),
        )

