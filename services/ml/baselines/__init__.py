"""
Baseline Strategies & Regret Metrics

Reference strategies for comparison:
- Hold Cash
- Buy & Hold
- Random (risk-controlled)
"""

from .hold_cash import HoldCashBaseline
from .buy_and_hold import BuyAndHoldBaseline
from .random import RandomControlledBaseline
from .regret import RegretCalculator, RegretMetrics

__all__ = [
    "HoldCashBaseline",
    "BuyAndHoldBaseline",
    "RandomControlledBaseline",
    "RegretCalculator",
    "RegretMetrics",
]
