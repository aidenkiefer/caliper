"""
Portfolio allocator.

Converts List[UnifiedSignal] into List[AllocationResult], enforcing
per-market capital budgets and per-position size caps.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List

from packages.common.market_schemas import MarketType, UnifiedSignal

from services.portfolio.sizing import fixed_fraction_size


@dataclass
class CapitalBudget:
    """
    Defines how total equity is distributed across market surfaces.

    market_budgets: fraction of total_equity each MarketType may use.
        e.g. {MarketType.EQUITY: Decimal("0.80"), MarketType.PREDICTION: Decimal("0.02")}
    max_single_position_pct: maximum fraction of total equity in any one position.
    """

    total_equity: Decimal
    market_budgets: Dict[MarketType, Decimal]
    max_single_position_pct: Decimal = Decimal("0.05")


@dataclass
class AllocationResult:
    """Sized allocation for a single signal."""

    asset_id: str
    strategy_id: str
    market_type: MarketType
    direction: str  # 'long', 'short', or 'none'
    target_quantity: Decimal
    signal: UnifiedSignal
    pass_through: bool = False  # True for MM signals that skip directional sizing


class Allocator:
    """
    Allocates capital across signals respecting per-market budgets.

    Usage::

        budget = CapitalBudget(
            total_equity=Decimal("100000"),
            market_budgets={MarketType.EQUITY: Decimal("0.80")},
        )
        allocator = Allocator(budget)
        results = allocator.allocate(signals, price_map)
    """

    def __init__(self, budget: CapitalBudget) -> None:
        self._budget = budget

    def allocate(
        self,
        signals: List[UnifiedSignal],
        current_price_map: Dict[str, Decimal],
    ) -> List[AllocationResult]:
        """
        Size each signal against the capital budget.

        Signals for markets not in market_budgets are silently dropped.
        Signals with direction='none' (market-making) are passed through
        with target_quantity=0 and pass_through=True for the executor to handle.

        Parameters
        ----------
        signals:
            UnifiedSignal list from one or more strategies.
        current_price_map:
            Map of asset_id → current price (for position sizing).

        Returns
        -------
        List[AllocationResult]

        Notes
        -----
        Per-market notional is tracked across all signals in this call so the
        aggregate allocation for a market type does not exceed its budget.
        """
        results: List[AllocationResult] = []
        # Track how much notional has been allocated per market type this cycle
        allocated_notional: Dict[MarketType, Decimal] = {
            mt: Decimal("0") for mt in self._budget.market_budgets
        }

        for signal in signals:
            if signal.market_type not in self._budget.market_budgets:
                continue

            # Market-making signals: pass through without sizing
            if signal.direction == "none":
                results.append(
                    AllocationResult(
                        asset_id=signal.asset_id,
                        strategy_id=signal.strategy_id,
                        market_type=signal.market_type,
                        direction="none",
                        target_quantity=Decimal("0"),
                        signal=signal,
                        pass_through=True,
                    )
                )
                continue

            price = current_price_map.get(signal.asset_id)
            if price is None or price <= Decimal("0"):
                continue

            market_budget_pct = self._budget.market_budgets[signal.market_type]
            total_market_budget = self._budget.total_equity * market_budget_pct

            # Remaining budget for this market type
            remaining_market_budget = total_market_budget - allocated_notional[signal.market_type]
            if remaining_market_budget <= Decimal("0"):
                continue

            # Cap to single-position limit and remaining market budget
            max_single_notional = self._budget.total_equity * self._budget.max_single_position_pct
            effective_notional = min(remaining_market_budget, max_single_notional)

            # Confidence-scale the fraction
            fraction = (effective_notional / self._budget.total_equity) * signal.confidence
            quantity = fixed_fraction_size(self._budget.total_equity, fraction, price)

            if quantity <= Decimal("0"):
                continue

            actual_notional = quantity * price
            allocated_notional[signal.market_type] += actual_notional

            results.append(
                AllocationResult(
                    asset_id=signal.asset_id,
                    strategy_id=signal.strategy_id,
                    market_type=signal.market_type,
                    direction=signal.direction,
                    target_quantity=quantity,
                    signal=signal,
                )
            )

        return results
