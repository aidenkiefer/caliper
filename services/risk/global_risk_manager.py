"""
GlobalRiskManager — unified pre-trade risk check across all market surfaces.

Sits between the portfolio allocator and the execution adapters. Every
AllocationResult must pass through here before an order is placed.

Check order:
1. Kill switch (blocks all markets)
2. Portfolio drawdown (blocks all markets)
3. Market-specific extensions:
   - Equity: delegates further checks to existing per-strategy RiskManager
   - Prediction: checks session loss limit
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from packages.common.market_schemas import MarketType
from services.portfolio.allocator import AllocationResult


@dataclass
class GlobalRiskConfig:
    """Runtime risk parameters for the global manager."""

    total_equity: Decimal
    max_drawdown_pct: Decimal
    kill_switch_active: bool = False
    max_polymarket_session_loss_usdc: Decimal = Decimal("100")


@dataclass
class GlobalRiskResult:
    """Result of a global risk check."""

    approved: bool
    rejection_reason: Optional[str] = None

    @classmethod
    def approve(cls) -> "GlobalRiskResult":
        return cls(approved=True)

    @classmethod
    def reject(cls, reason: str) -> "GlobalRiskResult":
        return cls(approved=False, rejection_reason=reason)


class GlobalRiskManager:
    """
    Single choke point for all pre-trade risk checks.

    Usage::

        config = GlobalRiskConfig(
            total_equity=Decimal("100000"),
            max_drawdown_pct=Decimal("10"),
        )
        grm = GlobalRiskManager(config)

        result = grm.check(
            allocation,
            current_drawdown_pct=portfolio_drawdown,
            polymarket_session_pnl=session_realized_pnl,
        )
        if not result.approved:
            logger.warning("Trade blocked: %s", result.rejection_reason)
            return
    """

    def __init__(self, config: GlobalRiskConfig) -> None:
        self._config = config

    def check(
        self,
        allocation: AllocationResult,
        current_drawdown_pct: Decimal = Decimal("0"),
        polymarket_session_pnl: Optional[Decimal] = None,
    ) -> GlobalRiskResult:
        """
        Run all applicable risk checks for an allocation.

        Parameters
        ----------
        allocation:
            Sized allocation from the portfolio allocator.
        current_drawdown_pct:
            Portfolio drawdown from high-water mark (as a positive %).
        polymarket_session_pnl:
            Realized PnL for the current Polymarket session (negative = loss).
            Required only when allocation.market_type == PREDICTION.

        Returns
        -------
        GlobalRiskResult with approved=True or a rejection reason.
        """

        # --- Layer 1: Kill switch (universal) ---
        if self._config.kill_switch_active:
            return GlobalRiskResult.reject(
                "Kill switch is active — all trading halted"
            )

        # --- Layer 2: Portfolio drawdown (universal) ---
        if current_drawdown_pct >= self._config.max_drawdown_pct:
            return GlobalRiskResult.reject(
                f"Portfolio drawdown {current_drawdown_pct}% >= limit {self._config.max_drawdown_pct}%"
            )

        # --- Layer 3: Market-specific ---
        if allocation.market_type == MarketType.PREDICTION:
            return self._check_prediction(polymarket_session_pnl)

        if allocation.market_type == MarketType.EQUITY:
            return self._check_equity(allocation)

        return GlobalRiskResult.approve()

    def _check_prediction(
        self,
        session_pnl: Optional[Decimal],
    ) -> GlobalRiskResult:
        """Polymarket-specific: session loss limit."""
        if session_pnl is not None:
            loss_limit = -abs(self._config.max_polymarket_session_loss_usdc)
            if session_pnl < loss_limit:
                return GlobalRiskResult.reject(
                    f"Polymarket session loss {session_pnl} USDC exceeds session loss limit {loss_limit} USDC"
                )
        return GlobalRiskResult.approve()

    def _check_equity(self, allocation: AllocationResult) -> GlobalRiskResult:
        """
        Equity-specific checks.

        The existing per-order RiskManager checks (strategy limits, notional
        caps, penny stock filter) are still applied by the execution engine.
        This layer adds portfolio-global guards only.
        """
        # Future: add cross-strategy exposure checks here
        return GlobalRiskResult.approve()
