"""
Test fixtures for execution and risk management.

Factory functions following @testing-patterns skill:
- get_mock_x(overrides?: Partial<X>) pattern
- Sensible defaults with override capability
- Keeps tests DRY and maintainable
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4


def get_mock_order(
    symbol: str = "AAPL",
    quantity: int = 10,
    side: str = "BUY",
    risk_percent: float = 1.0,
    **overrides: Any
) -> dict:
    """
    Factory function for mock order data.
    
    Args:
        symbol: Trading symbol
        quantity: Order quantity
        side: BUY or SELL
        risk_percent: Risk as % of portfolio (used for stop loss calculation)
        **overrides: Additional fields to override
        
    Returns:
        Dict representing an order for testing
        
    Example:
        >>> order = get_mock_order(symbol="MSFT", quantity=50)
        >>> assert order["symbol"] == "MSFT"
    """
    # Default price for AAPL-like stock
    price = Decimal("150.00")
    
    # Calculate stop loss based on risk_percent
    # Assuming $100k portfolio, risk_percent of price determines stop loss distance
    risk_per_share = price * Decimal(str(risk_percent)) / Decimal("100")
    stop_loss = price - risk_per_share if side == "BUY" else price + risk_per_share
    
    defaults = {
        "client_order_id": f"test_{uuid4().hex[:8]}",
        "symbol": symbol,
        "side": side,
        "quantity": Decimal(str(quantity)),
        "order_type": "LIMIT",
        "limit_price": price,
        "stop_price": stop_loss,
        "time_in_force": "DAY",
        "strategy_id": "test_strategy_v1",
        "created_at": datetime.now(timezone.utc),
    }
    
    defaults.update(overrides)
    return defaults


def get_mock_portfolio(
    equity: float = 100000,
    cash: float = 50000,
    positions_count: int = 5,
    drawdown_percent: float = 0.0,
    **overrides: Any
) -> dict:
    """
    Factory function for mock portfolio data.
    
    Args:
        equity: Total portfolio equity
        cash: Available cash
        positions_count: Number of open positions
        drawdown_percent: Current drawdown as positive percentage
        **overrides: Additional fields to override
        
    Returns:
        Dict representing portfolio state for testing
        
    Example:
        >>> portfolio = get_mock_portfolio(equity=50000, drawdown_percent=5.0)
        >>> assert portfolio["equity"] == Decimal("50000")
    """
    equity_decimal = Decimal(str(equity))
    cash_decimal = Decimal(str(cash))
    capital_deployed = equity_decimal - cash_decimal
    
    defaults = {
        "equity": equity_decimal,
        "cash": cash_decimal,
        "buying_power": cash_decimal * Decimal("2"),  # 2x margin
        "portfolio_value": equity_decimal,
        "capital_deployed": capital_deployed,
        "capital_deployed_pct": (capital_deployed / equity_decimal * 100) if equity > 0 else Decimal("0"),
        "positions_count": positions_count,
        "daily_drawdown_pct": Decimal(str(drawdown_percent)),
        "total_drawdown_pct": Decimal(str(drawdown_percent)),
        "high_water_mark": equity_decimal * (Decimal("1") + Decimal(str(drawdown_percent)) / Decimal("100")),
    }
    
    defaults.update(overrides)
    return defaults


def get_risky_order() -> dict:
    """
    Get an order that exceeds risk limits (>2% risk).
    
    This order should fail risk checks:
    - Risk per trade: 5% (limit is 2%)
    
    Returns:
        Dict representing a risky order that should be rejected
    """
    # Price $100, stop loss $95 = $5 risk per share (5%)
    # With 100 shares, total risk = $500 = 5% of $10,000 portfolio
    # For $100k portfolio this would be 0.5%, so we need bigger size
    # 
    # To get 5% risk of $100k = $5,000 risk
    # At $5 risk per share, need 1000 shares
    return {
        "client_order_id": f"risky_order_{uuid4().hex[:8]}",
        "symbol": "TSLA",
        "side": "BUY",
        "quantity": Decimal("1000"),
        "order_type": "LIMIT",
        "limit_price": Decimal("100.00"),
        "stop_price": Decimal("95.00"),  # $5 risk per share = $5000 total
        "time_in_force": "DAY",
        "strategy_id": "aggressive_strategy",
        "risk_amount": Decimal("5000"),  # 5% of $100k portfolio
        "portfolio_equity": Decimal("100000"),
    }


def get_safe_order() -> dict:
    """
    Get an order that passes all risk checks.
    
    This order should pass all limits:
    - Risk per trade: ~1% (limit is 2%)
    - Notional: $15,000 (limit is $25,000)
    - Price: $150 (above $5 minimum)
    - No price deviation
    
    Returns:
        Dict representing a safe order that should be approved
    """
    return {
        "client_order_id": f"safe_order_{uuid4().hex[:8]}",
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": Decimal("100"),
        "order_type": "LIMIT",
        "limit_price": Decimal("150.00"),
        "stop_price": Decimal("147.00"),  # $3 risk per share = $300 = 0.3% risk
        "time_in_force": "DAY",
        "strategy_id": "conservative_strategy",
        "risk_amount": Decimal("300"),  # 0.3% of $100k portfolio
        "portfolio_equity": Decimal("100000"),
        "last_price": Decimal("150.00"),  # No price deviation
        "avg_daily_volume": 50000000,  # Highly liquid
    }


def get_high_notional_order() -> dict:
    """
    Get an order that exceeds max notional limit ($25,000).
    
    Returns:
        Dict with notional > $25,000
    """
    return {
        "client_order_id": f"high_notional_{uuid4().hex[:8]}",
        "symbol": "GOOGL",
        "side": "BUY",
        "quantity": Decimal("200"),
        "order_type": "LIMIT",
        "limit_price": Decimal("150.00"),  # $30,000 notional
        "stop_price": Decimal("148.00"),
        "time_in_force": "DAY",
        "strategy_id": "test_strategy",
    }


def get_penny_stock_order() -> dict:
    """
    Get an order for a penny stock (price < $5).
    
    Returns:
        Dict with price below minimum
    """
    return {
        "client_order_id": f"penny_stock_{uuid4().hex[:8]}",
        "symbol": "PNNY",
        "side": "BUY",
        "quantity": Decimal("1000"),
        "order_type": "LIMIT",
        "limit_price": Decimal("3.50"),  # Below $5 minimum
        "stop_price": Decimal("3.00"),
        "time_in_force": "DAY",
        "strategy_id": "test_strategy",
    }


def get_price_deviation_order() -> dict:
    """
    Get an order with high price deviation from last price (>5%).
    
    Returns:
        Dict with order price far from market price
    """
    return {
        "client_order_id": f"deviation_{uuid4().hex[:8]}",
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": Decimal("100"),
        "order_type": "LIMIT",
        "limit_price": Decimal("170.00"),  # ~13% above last price
        "stop_price": Decimal("165.00"),
        "time_in_force": "DAY",
        "strategy_id": "test_strategy",
        "last_price": Decimal("150.00"),  # Market price
    }


def get_max_positions_portfolio() -> dict:
    """
    Get portfolio at maximum positions (20).
    
    Returns:
        Dict representing portfolio at position limit
    """
    return get_mock_portfolio(
        equity=100000,
        cash=20000,  # 80% deployed
        positions_count=20,  # At maximum
        drawdown_percent=1.0,
    )


def get_drawdown_portfolio(daily_pct: float = 0.0, total_pct: float = 0.0) -> dict:
    """
    Get portfolio with specific drawdown levels.
    
    Args:
        daily_pct: Daily drawdown percentage
        total_pct: Total drawdown from high water mark
        
    Returns:
        Dict representing portfolio in drawdown
    """
    return get_mock_portfolio(
        equity=100000 * (1 - total_pct / 100),
        cash=50000,
        positions_count=5,
        drawdown_percent=0.0,
        daily_drawdown_pct=Decimal(str(daily_pct)),
        total_drawdown_pct=Decimal(str(total_pct)),
    )


def get_over_deployed_portfolio() -> dict:
    """
    Get portfolio with >80% capital deployed.
    
    Returns:
        Dict representing over-deployed portfolio
    """
    return get_mock_portfolio(
        equity=100000,
        cash=15000,  # Only 15% cash = 85% deployed
        positions_count=10,
        drawdown_percent=0.0,
    )


# Risk limit constants from docs/risk-policy.md
RISK_LIMITS = {
    "max_daily_drawdown_pct": Decimal("3.0"),
    "max_total_drawdown_pct": Decimal("10.0"),
    "max_capital_deployed_pct": Decimal("80.0"),
    "max_open_positions": 20,
    "max_risk_per_trade_pct": Decimal("2.0"),
    "max_notional_per_trade": Decimal("25000"),
    "max_price_deviation_pct": Decimal("5.0"),
    "min_stock_price": Decimal("5.0"),
}


# Valid admin code for testing kill switch deactivation
TEST_ADMIN_CODE = "EMERGENCY_OVERRIDE_2026"
