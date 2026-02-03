"""
Risk Manager - Main pre-trade risk check orchestrator.

Coordinates all risk checks before order submission.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .limits import (
    LimitType,
    OrderLimits,
    PortfolioLimits,
    RiskLimitViolation,
    StrategyLimits,
)
from .kill_switch import KillSwitch, KillSwitchStatus
from .circuit_breaker import CircuitBreaker, CircuitBreakerState


class RiskCheckResult(BaseModel):
    """Result of pre-trade risk check."""

    approved: bool = Field(..., description="Whether order is approved")
    violations: List[RiskLimitViolation] = Field(
        default_factory=list,
        description="List of limit violations",
    )
    warnings: List[RiskLimitViolation] = Field(
        default_factory=list,
        description="List of warnings (non-blocking)",
    )
    rejection_reason: Optional[str] = Field(
        None,
        description="Primary reason for rejection if not approved",
    )
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of risk check",
    )

    def add_violation(self, violation: RiskLimitViolation) -> None:
        """Add a violation to the result."""
        if violation.severity == "error":
            self.violations.append(violation)
            self.approved = False
            if self.rejection_reason is None:
                self.rejection_reason = violation.message
        else:
            self.warnings.append(violation)


class RiskManager:
    """
    Pre-trade risk check orchestrator.

    Performs all risk checks before order submission:
    1. Kill switch check
    2. Portfolio-level limits
    3. Strategy-level limits
    4. Order-level limits

    Usage:
        manager = RiskManager()
        result = manager.check_order(
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.00,
            strategy_id="momentum_v1",
            portfolio_value=100000,
            current_positions=5,
            capital_deployed=40000,
        )

        if result.approved:
            # Proceed with order
        else:
            print(f"Rejected: {result.rejection_reason}")
    """

    def __init__(
        self,
        portfolio_limits: Optional[PortfolioLimits] = None,
        order_limits: Optional[OrderLimits] = None,
        kill_switch: Optional[KillSwitch] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        """
        Initialize Risk Manager.

        Args:
            portfolio_limits: Portfolio-level limits (uses defaults if None)
            order_limits: Order-level limits (uses defaults if None)
            kill_switch: Kill switch instance (creates new if None)
            circuit_breaker: Circuit breaker instance (creates new if None)
        """
        self._portfolio_limits = portfolio_limits or PortfolioLimits()
        self._order_limits = order_limits or OrderLimits()
        self._kill_switch = kill_switch or KillSwitch()
        self._circuit_breaker = circuit_breaker or CircuitBreaker(self._kill_switch)

        # Strategy-level limits (can be configured per strategy)
        self._strategy_limits: Dict[str, StrategyLimits] = {}

    @property
    def kill_switch(self) -> KillSwitch:
        """Get kill switch instance."""
        return self._kill_switch

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get circuit breaker instance."""
        return self._circuit_breaker

    def register_strategy(
        self,
        strategy_id: str,
        limits: Optional[StrategyLimits] = None,
    ) -> None:
        """
        Register a strategy with optional custom limits.

        Args:
            strategy_id: Strategy identifier
            limits: Custom limits for this strategy
        """
        if limits is None:
            limits = StrategyLimits(strategy_id=strategy_id)
        self._strategy_limits[strategy_id] = limits

    def get_strategy_limits(self, strategy_id: str) -> StrategyLimits:
        """Get limits for a strategy (creates default if not registered)."""
        if strategy_id not in self._strategy_limits:
            self.register_strategy(strategy_id)
        return self._strategy_limits[strategy_id]

    def check_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        strategy_id: str,
        portfolio_value: Decimal,
        current_positions: int,
        capital_deployed: Decimal,
        daily_drawdown_pct: Decimal = Decimal("0.0"),
        total_drawdown_pct: Decimal = Decimal("0.0"),
        last_price: Optional[Decimal] = None,
        avg_daily_volume: Optional[int] = None,
        stop_loss_price: Optional[Decimal] = None,
    ) -> RiskCheckResult:
        """
        Perform comprehensive pre-trade risk check.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            price: Order price
            strategy_id: Strategy placing the order
            portfolio_value: Current portfolio value
            current_positions: Number of open positions
            capital_deployed: Currently deployed capital
            daily_drawdown_pct: Current daily drawdown %
            total_drawdown_pct: Current total drawdown %
            last_price: Last traded price (for price sanity check)
            avg_daily_volume: 20-day average volume (for volume check)
            stop_loss_price: Stop loss price (for risk calculation)

        Returns:
            RiskCheckResult with approval status and any violations
        """
        result = RiskCheckResult(approved=True)

        # 1. Kill switch check (highest priority)
        violations = self._check_kill_switch(strategy_id)
        for v in violations:
            result.add_violation(v)

        if not result.approved:
            return result

        # 2. Update circuit breaker and check state
        self._circuit_breaker.update_drawdown(daily_drawdown_pct, total_drawdown_pct)
        if self._circuit_breaker.is_tripped():
            result.add_violation(
                RiskLimitViolation(
                    limit_type=LimitType.KILL_SWITCH_ACTIVE,
                    limit_value="tripped",
                    actual_value="circuit_breaker",
                    message="Circuit breaker tripped - trading halted",
                    severity="error",
                )
            )
            return result

        # 3. Portfolio-level checks
        violations = self._check_portfolio_limits(
            daily_drawdown_pct=daily_drawdown_pct,
            total_drawdown_pct=total_drawdown_pct,
            capital_deployed_pct=(capital_deployed / portfolio_value * 100)
            if portfolio_value > 0
            else Decimal("0"),
            current_positions=current_positions,
            is_opening_order=(side == "BUY"),
        )
        for v in violations:
            result.add_violation(v)

        # 4. Strategy-level checks
        strategy_limits = self.get_strategy_limits(strategy_id)
        violations = self._check_strategy_limits(
            strategy_limits=strategy_limits,
            order_notional=quantity * price,
            portfolio_value=portfolio_value,
        )
        for v in violations:
            result.add_violation(v)

        # 5. Order-level checks
        order_notional = quantity * price

        # Calculate risk amount
        if stop_loss_price and side == "BUY":
            risk_per_share = price - stop_loss_price
            risk_amount = quantity * risk_per_share
        elif stop_loss_price and side == "SELL":
            risk_per_share = stop_loss_price - price
            risk_amount = quantity * risk_per_share
        else:
            # Default: assume 10% risk if no stop loss
            risk_amount = order_notional * Decimal("0.10")

        violations = self._check_order_limits(
            symbol=symbol,
            order_notional=order_notional,
            risk_amount=risk_amount,
            portfolio_equity=portfolio_value,
            order_price=price,
            last_price=last_price or price,
            order_quantity=int(quantity),
            avg_daily_volume=avg_daily_volume or 1000000,
        )
        for v in violations:
            result.add_violation(v)

        return result

    def _check_kill_switch(self, strategy_id: str) -> List[RiskLimitViolation]:
        """Check if kill switch is active."""
        violations = []

        # Check global kill switch
        if self._kill_switch.is_active():
            global_info = self._kill_switch.get_global_info()
            violations.append(
                RiskLimitViolation(
                    limit_type=LimitType.KILL_SWITCH_ACTIVE,
                    limit_value="active",
                    actual_value="global",
                    message=f"Global kill switch active: {global_info.get('reason', 'Unknown')}",
                    severity="error",
                )
            )
            return violations

        # Check strategy-specific kill switch
        if self._kill_switch.is_active(strategy_id):
            strategy_info = self._kill_switch.get_strategy_info(strategy_id)
            violations.append(
                RiskLimitViolation(
                    limit_type=LimitType.KILL_SWITCH_ACTIVE,
                    limit_value="active",
                    actual_value=f"strategy:{strategy_id}",
                    message=f"Strategy kill switch active: {strategy_info.get('reason', 'Unknown')}",
                    severity="error",
                )
            )

        return violations

    def _check_portfolio_limits(
        self,
        daily_drawdown_pct: Decimal,
        total_drawdown_pct: Decimal,
        capital_deployed_pct: Decimal,
        current_positions: int,
        is_opening_order: bool,
    ) -> List[RiskLimitViolation]:
        """Check portfolio-level limits."""
        violations = []

        # Drawdown checks
        violations.extend(
            self._portfolio_limits.check_drawdown(
                daily_drawdown_pct=daily_drawdown_pct,
                total_drawdown_pct=total_drawdown_pct,
            )
        )

        # Only check capital/position limits for opening orders
        if is_opening_order:
            violations.extend(self._portfolio_limits.check_capital(capital_deployed_pct))
            violations.extend(self._portfolio_limits.check_positions(current_positions))

        return violations

    def _check_strategy_limits(
        self,
        strategy_limits: StrategyLimits,
        order_notional: Decimal,
        portfolio_value: Decimal,
    ) -> List[RiskLimitViolation]:
        """Check strategy-level limits."""
        violations = []

        # Check if strategy is paused
        if strategy_limits.is_paused:
            violations.append(
                RiskLimitViolation(
                    limit_type=LimitType.MAX_STRATEGY_ALLOCATION,
                    limit_value="paused",
                    actual_value=strategy_limits.strategy_id,
                    message=f"Strategy paused: {strategy_limits.pause_reason}",
                    severity="error",
                )
            )
            return violations

        # Calculate new allocation
        if portfolio_value > 0:
            current_allocation = strategy_limits.current_allocation_pct
            order_allocation = (order_notional / portfolio_value) * 100
            new_allocation = current_allocation + order_allocation

            violations.extend(strategy_limits.check_allocation(new_allocation))

        return violations

    def _check_order_limits(
        self,
        symbol: str,
        order_notional: Decimal,
        risk_amount: Decimal,
        portfolio_equity: Decimal,
        order_price: Decimal,
        last_price: Decimal,
        order_quantity: int,
        avg_daily_volume: int,
    ) -> List[RiskLimitViolation]:
        """Check order-level limits."""
        violations = []

        # Position sizing checks
        violations.extend(
            self._order_limits.check_position_sizing(
                order_notional=order_notional,
                risk_amount=risk_amount,
                portfolio_equity=portfolio_equity,
            )
        )

        # Price sanity checks
        violations.extend(
            self._order_limits.check_price_sanity(
                order_price=order_price,
                last_price=last_price,
                symbol=symbol,
            )
        )

        # Volume checks
        violations.extend(
            self._order_limits.check_volume(
                order_quantity=order_quantity,
                avg_daily_volume=avg_daily_volume,
            )
        )

        return violations

    def update_drawdown(
        self,
        daily_drawdown_pct: Decimal,
        total_drawdown_pct: Decimal,
    ) -> CircuitBreakerState:
        """
        Update drawdown and check circuit breaker.

        Args:
            daily_drawdown_pct: Current daily drawdown %
            total_drawdown_pct: Current total drawdown %

        Returns:
            Current circuit breaker state
        """
        return self._circuit_breaker.update_drawdown(
            daily_drawdown_pct=daily_drawdown_pct,
            total_drawdown_pct=total_drawdown_pct,
        )

    def activate_kill_switch(
        self,
        reason: str,
        strategy_id: Optional[str] = None,
        triggered_by: str = "user",
    ) -> None:
        """
        Manually activate kill switch.

        Args:
            reason: Reason for activation
            strategy_id: If provided, activate for specific strategy only
            triggered_by: Who/what triggered activation
        """
        if strategy_id:
            self._kill_switch.activate_strategy(
                strategy_id=strategy_id,
                reason=reason,
                triggered_by=triggered_by,
            )
        else:
            self._kill_switch.activate_global(
                reason=reason,
                triggered_by=triggered_by,
            )

    def deactivate_kill_switch(
        self,
        admin_code: str,
        strategy_id: Optional[str] = None,
        reason: str = "Manual deactivation",
    ) -> None:
        """
        Deactivate kill switch.

        Args:
            admin_code: Admin code for authorization
            strategy_id: If provided, deactivate for specific strategy only
            reason: Reason for deactivation
        """
        if strategy_id:
            self._kill_switch.deactivate_strategy(
                strategy_id=strategy_id,
                admin_code=admin_code,
                reason=reason,
            )
        else:
            self._kill_switch.deactivate_global(
                admin_code=admin_code,
                reason=reason,
            )

    def get_status(self) -> Dict:
        """Get comprehensive risk manager status."""
        return {
            "kill_switch": self._kill_switch.get_summary(),
            "circuit_breaker": self._circuit_breaker.get_status(),
            "portfolio_limits": {
                "max_daily_drawdown_pct": str(self._portfolio_limits.max_daily_drawdown_pct),
                "max_total_drawdown_pct": str(self._portfolio_limits.max_total_drawdown_pct),
                "max_capital_deployed_pct": str(self._portfolio_limits.max_capital_deployed_pct),
                "max_open_positions": self._portfolio_limits.max_open_positions,
            },
            "order_limits": {
                "max_risk_per_trade_pct": str(self._order_limits.max_risk_per_trade_pct),
                "max_notional_per_trade": str(self._order_limits.max_notional_per_trade),
                "max_price_deviation_pct": str(self._order_limits.max_price_deviation_pct),
                "min_stock_price": str(self._order_limits.min_stock_price),
            },
            "registered_strategies": list(self._strategy_limits.keys()),
        }
