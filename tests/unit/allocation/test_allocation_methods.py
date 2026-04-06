from __future__ import annotations

from decimal import Decimal

import numpy as np

from services.allocation.methods.hrp import hrp_weights
from services.allocation.methods.kelly import bounded_kelly_weights
from services.allocation.methods.risk_parity import risk_parity_weights


def test_risk_parity_inverse_sigma() -> None:
    sig = {"a": Decimal("2"), "b": Decimal("1")}
    w = risk_parity_weights(sig)
    assert w["b"] > w["a"]
    assert (w["a"] + w["b"]) <= Decimal("1")


def test_hrp_deterministic_on_identical_input() -> None:
    cov = np.array([[1.0, 0.9, 0.1], [0.9, 1.0, 0.2], [0.1, 0.2, 1.0]])
    strategies = ["s1", "s2", "s3"]
    w1 = hrp_weights(cov.tolist(), strategies)
    w2 = hrp_weights(cov.tolist(), strategies)
    assert w1 == w2


def test_bounded_kelly_respects_caps() -> None:
    cov = [[1.0, 0.0], [0.0, 1.0]]
    w = bounded_kelly_weights([1.0, 1.0], cov, ["a", "b"], max_weight=0.40, total_weight_cap=1.0)
    assert float(w["a"]) <= 0.40 + 1e-9
    assert float(w["b"]) <= 0.40 + 1e-9
    assert float(w["a"] + w["b"]) <= 1.0 + 1e-9

