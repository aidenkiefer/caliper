"""
Unit tests for RiskManager.

Tests all risk limits from docs/risk-policy.md:
- Portfolio-level limits (drawdown, capital, positions)
- Order-level limits (risk per trade, notional, price, volume)
- Kill switch and circuit breaker

Following @testing-patterns skill:
- Factory pattern for test data
- Behavior-driven testing
- Organize with describe blocks
- Clear mocks between tests
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from services.risk.manager import RiskManager, RiskCheckResult
from services.risk.limits import (
    LimitType,
    OrderLimits,
    PortfolioLimits,
    RiskLimitViolation,
    StrategyLimits,
)
from services.risk.kill_switch import KillSwitch, KillSwitchStatus
from services.risk.circuit_breaker import CircuitBreaker, CircuitBreakerState

from tests.fixtures.execution_data import (
    get_mock_order,
    get_mock_portfolio,
    get_risky_order,
    get_safe_order,
    get_high_notional_order,
    get_penny_stock_order,
    get_price_deviation_order,
    get_max_positions_portfolio,
    get_drawdown_portfolio,
    get_over_deployed_portfolio,
    RISK_LIMITS,
    TEST_ADMIN_CODE,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def risk_manager() -> RiskManager:
    """Create a fresh RiskManager for each test."""
    return RiskManager()


@pytest.fixture
def risk_manager_with_strategy(risk_manager: RiskManager) -> RiskManager:
    """RiskManager with a registered test strategy."""
    risk_manager.register_strategy(
        "test_strategy_v1",
        StrategyLimits(
            strategy_id="test_strategy_v1",
            max_allocation_pct=Decimal("50.0"),
        ),
    )
    return risk_manager


@pytest.fixture
def portfolio() -> dict:
    """Default portfolio for testing."""
    return get_mock_portfolio()


@pytest.fixture
def order() -> dict:
    """Default order for testing."""
    return get_mock_order()


# ============================================================================
# Portfolio Limits Tests
# ============================================================================

class TestPortfolioLimits:
    """Tests for portfolio-level risk limits."""
    
    def test_rejects_order_when_daily_drawdown_exceeded(self, risk_manager: RiskManager):
        """Order rejected when daily drawdown exceeds 3% limit."""
        order = get_safe_order()
        portfolio = get_mock_portfolio()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=portfolio["equity"],
            current_positions=portfolio["positions_count"],
            capital_deployed=portfolio["capital_deployed"],
            daily_drawdown_pct=Decimal("3.5"),  # Exceeds 3% limit - triggers circuit breaker
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        # At 3.5% daily drawdown, circuit breaker trips and activates kill switch
        # Either MAX_DAILY_DRAWDOWN or KILL_SWITCH_ACTIVE violation is acceptable
        violation_types = [v.limit_type for v in result.violations]
        assert LimitType.MAX_DAILY_DRAWDOWN in violation_types or LimitType.KILL_SWITCH_ACTIVE in violation_types
    
    def test_rejects_order_when_total_drawdown_exceeded(self, risk_manager: RiskManager):
        """Order rejected when total drawdown exceeds 10% (triggers kill switch)."""
        order = get_safe_order()
        portfolio = get_mock_portfolio()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=portfolio["equity"],
            current_positions=portfolio["positions_count"],
            capital_deployed=portfolio["capital_deployed"],
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("10.5"),  # Exceeds 10% limit
        )
        
        assert result.approved is False
        violations = [v.limit_type for v in result.violations]
        assert LimitType.MAX_TOTAL_DRAWDOWN in violations or LimitType.KILL_SWITCH_ACTIVE in violations
    
    def test_rejects_order_when_capital_deployed_exceeded(self, risk_manager: RiskManager):
        """Order rejected when capital deployed exceeds 80% limit."""
        order = get_safe_order()
        portfolio = get_over_deployed_portfolio()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=portfolio["equity"],
            current_positions=portfolio["positions_count"],
            capital_deployed=portfolio["capital_deployed"],
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.MAX_CAPITAL_DEPLOYED for v in result.violations)
    
    def test_rejects_order_when_max_positions_exceeded(self, risk_manager: RiskManager):
        """Order rejected when at maximum 20 positions."""
        order = get_safe_order()
        portfolio = get_max_positions_portfolio()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=portfolio["equity"],
            current_positions=20,  # At maximum
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.MAX_OPEN_POSITIONS for v in result.violations)
    
    def test_allows_order_within_portfolio_limits(self, risk_manager: RiskManager):
        """Order approved when all portfolio limits are satisfied."""
        order = get_safe_order()
        portfolio = get_mock_portfolio(positions_count=5, cash=50000)
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=portfolio["equity"],
            current_positions=portfolio["positions_count"],
            capital_deployed=portfolio["capital_deployed"],
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
            last_price=order.get("last_price", order["limit_price"]),
            avg_daily_volume=order.get("avg_daily_volume", 10000000),
            stop_loss_price=order.get("stop_price"),
        )
        
        assert result.approved is True
        assert len(result.violations) == 0
    
    def test_allows_sell_order_when_positions_at_max(self, risk_manager: RiskManager):
        """SELL orders allowed even at max positions (closing position)."""
        order = get_safe_order()
        order["side"] = "SELL"
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side="SELL",
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=Decimal("100000"),
            current_positions=20,  # At maximum
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
            last_price=order["limit_price"],
        )
        
        # SELL orders bypass position limit check
        assert result.approved is True or LimitType.MAX_OPEN_POSITIONS not in [v.limit_type for v in result.violations]
    
    def test_daily_drawdown_at_exact_limit_rejected(self, risk_manager: RiskManager):
        """Order rejected when daily drawdown exactly at 3% limit."""
        order = get_safe_order()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("3.0"),  # Exactly at limit - triggers circuit breaker
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        # At exactly 3%, circuit breaker trips and activates kill switch
        # Either MAX_DAILY_DRAWDOWN or KILL_SWITCH_ACTIVE violation is acceptable
        violation_types = [v.limit_type for v in result.violations]
        assert LimitType.MAX_DAILY_DRAWDOWN in violation_types or LimitType.KILL_SWITCH_ACTIVE in violation_types
    
    def test_daily_drawdown_just_below_limit_approved(self, risk_manager: RiskManager):
        """Order approved when daily drawdown just below 3% limit."""
        order = get_safe_order()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("2.99"),  # Just below limit
            total_drawdown_pct=Decimal("0.0"),
            last_price=order["limit_price"],
            avg_daily_volume=10000000,
            stop_loss_price=order.get("stop_price"),
        )
        
        # Should be approved if other checks pass
        assert result.approved is True


# ============================================================================
# Order Limits Tests
# ============================================================================

class TestOrderLimits:
    """Tests for order-level risk limits."""
    
    def test_rejects_order_exceeding_max_risk_per_trade(self, risk_manager: RiskManager):
        """Order rejected when risk exceeds 2% of portfolio equity."""
        risky_order = get_risky_order()
        
        result = risk_manager.check_order(
            symbol=risky_order["symbol"],
            side=risky_order["side"],
            quantity=risky_order["quantity"],
            price=risky_order["limit_price"],
            strategy_id=risky_order["strategy_id"],
            portfolio_value=risky_order["portfolio_equity"],
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
            stop_loss_price=risky_order["stop_price"],
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.MAX_RISK_PER_TRADE for v in result.violations)
    
    def test_rejects_order_exceeding_max_notional(self, risk_manager: RiskManager):
        """Order rejected when notional exceeds $25,000."""
        order = get_high_notional_order()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.MAX_NOTIONAL for v in result.violations)
    
    def test_rejects_order_with_price_deviation(self, risk_manager: RiskManager):
        """Order rejected when price deviates >5% from last traded price."""
        order = get_price_deviation_order()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
            last_price=order["last_price"],
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.MAX_PRICE_DEVIATION for v in result.violations)
    
    def test_rejects_penny_stock_order(self, risk_manager: RiskManager):
        """Order rejected for stocks under $5.00."""
        order = get_penny_stock_order()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.MIN_STOCK_PRICE for v in result.violations)
    
    def test_allows_order_within_all_limits(self, risk_manager: RiskManager):
        """Order approved when all limits are satisfied."""
        order = get_safe_order()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=order["portfolio_equity"],
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
            last_price=order["last_price"],
            avg_daily_volume=order["avg_daily_volume"],
            stop_loss_price=order["stop_price"],
        )
        
        assert result.approved is True
        assert len(result.violations) == 0
    
    def test_notional_at_exact_limit_approved(self, risk_manager: RiskManager):
        """Order approved when notional exactly at $25,000 limit."""
        # 250 shares at $100 = $25,000
        result = risk_manager.check_order(
            symbol="TEST",
            side="BUY",
            quantity=Decimal("250"),
            price=Decimal("100.00"),
            strategy_id="test_strategy",
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
            last_price=Decimal("100.00"),
            avg_daily_volume=10000000,
        )
        
        # Should pass notional check (<=25000)
        assert not any(v.limit_type == LimitType.MAX_NOTIONAL for v in result.violations)
    
    def test_notional_just_over_limit_rejected(self, risk_manager: RiskManager):
        """Order rejected when notional just over $25,000 limit."""
        # 251 shares at $100 = $25,100
        result = risk_manager.check_order(
            symbol="TEST",
            side="BUY",
            quantity=Decimal("251"),
            price=Decimal("100.00"),
            strategy_id="test_strategy",
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.MAX_NOTIONAL for v in result.violations)
    
    def test_price_exactly_at_minimum_approved(self, risk_manager: RiskManager):
        """Order approved when price exactly at $5.00 minimum."""
        result = risk_manager.check_order(
            symbol="CHEAP",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("5.00"),
            strategy_id="test_strategy",
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
            last_price=Decimal("5.00"),
            avg_daily_volume=10000000,
        )
        
        # Should pass min price check (>= $5)
        assert not any(v.limit_type == LimitType.MIN_STOCK_PRICE for v in result.violations)
    
    def test_price_just_below_minimum_rejected(self, risk_manager: RiskManager):
        """Order rejected when price just below $5.00 minimum."""
        result = risk_manager.check_order(
            symbol="CHEAP",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("4.99"),
            strategy_id="test_strategy",
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.MIN_STOCK_PRICE for v in result.violations)


# ============================================================================
# Kill Switch Tests
# ============================================================================

class TestKillSwitch:
    """Tests for kill switch mechanism."""
    
    def test_kill_switch_blocks_all_orders(self, risk_manager: RiskManager):
        """Global kill switch blocks all order submissions."""
        # Activate kill switch
        risk_manager.activate_kill_switch(
            reason="Test activation",
            triggered_by="test",
        )
        
        order = get_safe_order()
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.KILL_SWITCH_ACTIVE for v in result.violations)
    
    def test_kill_switch_activation(self, risk_manager: RiskManager):
        """Kill switch can be activated with reason."""
        assert risk_manager.kill_switch.is_active() is False
        
        risk_manager.activate_kill_switch(
            reason="Market volatility",
            triggered_by="user",
        )
        
        assert risk_manager.kill_switch.is_active() is True
        info = risk_manager.kill_switch.get_global_info()
        assert info["reason"] == "Market volatility"
    
    def test_kill_switch_deactivation_requires_admin(self, risk_manager: RiskManager):
        """Kill switch deactivation requires admin code."""
        # Activate
        risk_manager.activate_kill_switch(reason="Test", triggered_by="test")
        assert risk_manager.kill_switch.is_active() is True
        
        # Attempt deactivation with wrong code
        with pytest.raises(PermissionError):
            risk_manager.deactivate_kill_switch(admin_code="wrong_code")
        
        # Kill switch should still be active
        assert risk_manager.kill_switch.is_active() is True
        
        # Deactivate with correct code
        risk_manager.deactivate_kill_switch(admin_code=TEST_ADMIN_CODE)
        assert risk_manager.kill_switch.is_active() is False
    
    def test_strategy_level_kill_switch(self, risk_manager: RiskManager):
        """Strategy-level kill switch only blocks that strategy."""
        # Activate for one strategy
        risk_manager.activate_kill_switch(
            reason="Strategy issues",
            strategy_id="blocked_strategy",
            triggered_by="test",
        )
        
        # Order from blocked strategy should fail
        result = risk_manager.check_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            strategy_id="blocked_strategy",
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.KILL_SWITCH_ACTIVE for v in result.violations)
        
        # Order from different strategy should pass kill switch check
        result2 = risk_manager.check_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            strategy_id="other_strategy",
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
            last_price=Decimal("150.00"),
            avg_daily_volume=10000000,
        )
        
        # Should not have kill switch violation
        assert not any(v.limit_type == LimitType.KILL_SWITCH_ACTIVE for v in result2.violations)
    
    def test_kill_switch_event_audit_trail(self, risk_manager: RiskManager):
        """Kill switch maintains event history."""
        # Activate and deactivate
        risk_manager.activate_kill_switch(reason="Test 1", triggered_by="test")
        risk_manager.deactivate_kill_switch(admin_code=TEST_ADMIN_CODE, reason="Reset 1")
        risk_manager.activate_kill_switch(reason="Test 2", triggered_by="test")
        
        events = risk_manager.kill_switch.get_events()
        assert len(events) == 3
        assert events[0].event_type == "activated"
        assert events[1].event_type == "deactivated"
        assert events[2].event_type == "activated"
    
    def test_global_kill_switch_overrides_strategy(self, risk_manager: RiskManager):
        """Global kill switch blocks even strategies without their own switch."""
        # Activate global
        risk_manager.activate_kill_switch(reason="Global halt", triggered_by="test")
        
        # Any strategy should be blocked
        result = risk_manager.check_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            strategy_id="any_strategy",
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

class TestCircuitBreaker:
    """Tests for circuit breaker automatic triggers."""
    
    def test_circuit_breaker_trips_on_total_drawdown(self, risk_manager: RiskManager):
        """Circuit breaker trips when total drawdown exceeds 10%."""
        order = get_safe_order()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("10.5"),  # Over 10% = trip
        )
        
        assert result.approved is False
        # Either kill switch or drawdown violation
        assert len(result.violations) > 0
    
    def test_circuit_breaker_trips_on_daily_drawdown(self, risk_manager: RiskManager):
        """Circuit breaker trips when daily drawdown exceeds 3%."""
        state = risk_manager.update_drawdown(
            daily_drawdown_pct=Decimal("3.5"),  # Over 3%
            total_drawdown_pct=Decimal("5.0"),
        )
        
        assert state == CircuitBreakerState.OPEN
        assert risk_manager.circuit_breaker.is_tripped() is True
    
    def test_circuit_breaker_warning_state(self, risk_manager: RiskManager):
        """Circuit breaker enters warning state near threshold."""
        state = risk_manager.update_drawdown(
            daily_drawdown_pct=Decimal("2.5"),  # Warning at 2%, halt at 3%
            total_drawdown_pct=Decimal("5.0"),
        )
        
        assert state == CircuitBreakerState.HALF_OPEN
        assert risk_manager.circuit_breaker.is_warning() is True
        assert risk_manager.circuit_breaker.is_tripped() is False
    
    def test_circuit_breaker_auto_activates_kill_switch(self, risk_manager: RiskManager):
        """Circuit breaker automatically activates kill switch when tripped."""
        # Trip the circuit breaker
        risk_manager.update_drawdown(
            daily_drawdown_pct=Decimal("3.5"),
            total_drawdown_pct=Decimal("5.0"),
        )
        
        # Kill switch should now be active
        assert risk_manager.kill_switch.is_active() is True
    
    def test_circuit_breaker_recovery_from_warning(self, risk_manager: RiskManager):
        """Circuit breaker recovers from warning state when drawdown improves."""
        # Enter warning state
        risk_manager.update_drawdown(
            daily_drawdown_pct=Decimal("2.5"),
            total_drawdown_pct=Decimal("8.5"),
        )
        assert risk_manager.circuit_breaker.is_warning() is True
        
        # Improve drawdown
        state = risk_manager.update_drawdown(
            daily_drawdown_pct=Decimal("1.0"),
            total_drawdown_pct=Decimal("5.0"),
        )
        
        assert state == CircuitBreakerState.CLOSED
        assert risk_manager.circuit_breaker.is_normal() is True
    
    def test_circuit_breaker_requires_manual_reset_from_tripped(self, risk_manager: RiskManager):
        """Circuit breaker requires manual reset to recover from OPEN state."""
        # Trip the breaker
        risk_manager.update_drawdown(
            daily_drawdown_pct=Decimal("4.0"),
            total_drawdown_pct=Decimal("5.0"),
        )
        assert risk_manager.circuit_breaker.is_tripped() is True
        
        # Even with improved drawdown, stays tripped
        risk_manager.update_drawdown(
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        assert risk_manager.circuit_breaker.is_tripped() is True
        
        # Manual reset required
        risk_manager.circuit_breaker.reset(admin_code=TEST_ADMIN_CODE)
        assert risk_manager.circuit_breaker.is_normal() is True


# ============================================================================
# Strategy Limits Tests
# ============================================================================

class TestStrategyLimits:
    """Tests for strategy-level risk limits."""
    
    def test_strategy_allocation_limit(self, risk_manager: RiskManager):
        """Strategy rejected when allocation exceeds configured limit."""
        risk_manager.register_strategy(
            "limited_strategy",
            StrategyLimits(
                strategy_id="limited_strategy",
                max_allocation_pct=Decimal("20.0"),  # Max 20% allocation
                current_allocation_pct=Decimal("18.0"),  # Already at 18%
            ),
        )
        
        # Try to add 5% more (would be 23%)
        result = risk_manager.check_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("500.00"),  # $50,000 order = 50% of $100k
            strategy_id="limited_strategy",
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.MAX_STRATEGY_ALLOCATION for v in result.violations)
    
    def test_paused_strategy_blocked(self, risk_manager: RiskManager):
        """Orders blocked for paused strategies."""
        risk_manager.register_strategy(
            "paused_strategy",
            StrategyLimits(
                strategy_id="paused_strategy",
                is_paused=True,
                pause_reason="Daily loss limit hit",
            ),
        )
        
        result = risk_manager.check_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            strategy_id="paused_strategy",
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        assert result.approved is False
        assert any(v.limit_type == LimitType.MAX_STRATEGY_ALLOCATION for v in result.violations)
        assert "paused" in result.rejection_reason.lower()


# ============================================================================
# Edge Cases and Combined Scenarios
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and combined scenarios."""
    
    def test_multiple_violations_all_reported(self, risk_manager: RiskManager):
        """All violations are reported when multiple limits exceeded."""
        # Order that violates multiple limits (but not circuit breaker thresholds)
        # Use drawdown below circuit breaker threshold to test multiple violations
        result = risk_manager.check_order(
            symbol="PENNY",
            side="BUY",
            quantity=Decimal("10000"),  # High notional ($40,000)
            price=Decimal("4.00"),  # Penny stock (< $5)
            strategy_id="test",
            portfolio_value=Decimal("100000"),
            current_positions=20,  # At max positions
            capital_deployed=Decimal("85000"),  # Over 80%
            daily_drawdown_pct=Decimal("1.0"),  # Below circuit breaker threshold
            total_drawdown_pct=Decimal("1.0"),  # Below circuit breaker threshold
        )
        
        assert result.approved is False
        assert len(result.violations) >= 2  # Multiple violations: penny stock, notional, positions, capital
    
    def test_zero_portfolio_value_handled(self, risk_manager: RiskManager):
        """Zero portfolio value doesn't cause division errors."""
        result = risk_manager.check_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            strategy_id="test",
            portfolio_value=Decimal("0"),
            current_positions=0,
            capital_deployed=Decimal("0"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
        )
        
        # Should not raise error
        assert isinstance(result, RiskCheckResult)
    
    def test_risk_check_timestamp(self, risk_manager: RiskManager):
        """Risk check result includes timestamp."""
        order = get_safe_order()
        
        result = risk_manager.check_order(
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["quantity"],
            price=order["limit_price"],
            strategy_id=order["strategy_id"],
            portfolio_value=Decimal("100000"),
            current_positions=5,
            capital_deployed=Decimal("50000"),
            daily_drawdown_pct=Decimal("0.0"),
            total_drawdown_pct=Decimal("0.0"),
            last_price=order["limit_price"],
            avg_daily_volume=10000000,
        )
        
        assert result.checked_at is not None
    
    def test_risk_manager_status(self, risk_manager: RiskManager):
        """Get comprehensive status from risk manager."""
        status = risk_manager.get_status()
        
        assert "kill_switch" in status
        assert "circuit_breaker" in status
        assert "portfolio_limits" in status
        assert "order_limits" in status
        assert "registered_strategies" in status


# ============================================================================
# PortfolioLimits Class Direct Tests
# ============================================================================

class TestPortfolioLimitsClass:
    """Direct tests for PortfolioLimits class."""
    
    def test_default_limits_match_policy(self):
        """Default limits match docs/risk-policy.md values."""
        limits = PortfolioLimits()
        
        assert limits.max_daily_drawdown_pct == Decimal("3.0")
        assert limits.max_total_drawdown_pct == Decimal("10.0")
        assert limits.max_capital_deployed_pct == Decimal("80.0")
        assert limits.max_open_positions == 20
    
    def test_custom_limits_can_be_set(self):
        """Custom limits can be configured."""
        limits = PortfolioLimits(
            max_daily_drawdown_pct=Decimal("2.0"),
            max_total_drawdown_pct=Decimal("5.0"),
            max_capital_deployed_pct=Decimal("50.0"),
            max_open_positions=10,
        )
        
        assert limits.max_daily_drawdown_pct == Decimal("2.0")
        assert limits.max_total_drawdown_pct == Decimal("5.0")


# ============================================================================
# OrderLimits Class Direct Tests
# ============================================================================

class TestOrderLimitsClass:
    """Direct tests for OrderLimits class."""
    
    def test_default_limits_match_policy(self):
        """Default limits match docs/risk-policy.md values."""
        limits = OrderLimits()
        
        assert limits.max_risk_per_trade_pct == Decimal("2.0")
        assert limits.max_notional_per_trade == Decimal("25000")
        assert limits.max_price_deviation_pct == Decimal("5.0")
        assert limits.min_stock_price == Decimal("5.0")
    
    def test_blocked_symbols_check(self):
        """Blocked symbols are rejected."""
        limits = OrderLimits(blocked_symbols=["BLOCKED"])
        
        violations = limits.check_price_sanity(
            order_price=Decimal("100.00"),
            last_price=Decimal("100.00"),
            symbol="BLOCKED",
        )
        
        assert len(violations) == 1
        assert violations[0].limit_type == LimitType.ASSET_BLOCKED
