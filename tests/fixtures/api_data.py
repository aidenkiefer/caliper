"""
API test data factories.

Factory functions for generating mock API data with sensible defaults
and optional overrides for testing.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from packages.common.api_schemas import (
    StrategyStatus,
    StrategyMode,
    RunType,
    RunStatus,
)


def get_mock_strategy(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a mock strategy with sensible defaults.
    
    Args:
        overrides: Optional dict of fields to override
    
    Returns:
        Mock strategy data dict
    
    Example:
        >>> strategy = get_mock_strategy({"status": StrategyStatus.INACTIVE})
        >>> assert strategy["status"] == StrategyStatus.INACTIVE
    """
    now = datetime.now(timezone.utc)
    
    default = {
        "strategy_id": f"test_strategy_{uuid4().hex[:8]}",
        "name": "Test Strategy",
        "description": "A test trading strategy",
        "status": StrategyStatus.ACTIVE,
        "mode": StrategyMode.PAPER,
        "universe_size": 50,
        "max_positions": 10,
        "risk_per_trade_pct": "1.5",
        "created_at": now - timedelta(days=30),
        "updated_at": now,
        "config": {
            "model_type": "xgboost",
            "features": ["rsi_14", "macd", "volume_sma_20"],
            "signal_threshold": 0.6,
            "stop_loss_pct": "2.0",
            "take_profit_pct": "5.0",
        },
        "performance": {
            "total_pnl": "2345.67",
            "sharpe_ratio": "2.1",
            "max_drawdown": "-5.2",
            "win_rate": "0.62",
        },
    }
    
    if overrides:
        # Handle nested config updates
        if "config" in overrides and isinstance(overrides["config"], dict):
            default["config"] = {**default["config"], **overrides["config"]}
            overrides = {k: v for k, v in overrides.items() if k != "config"}
        
        if "performance" in overrides and isinstance(overrides["performance"], dict):
            default["performance"] = {**default["performance"], **overrides["performance"]}
            overrides = {k: v for k, v in overrides.items() if k != "performance"}
        
        default.update(overrides)
    
    return default


def get_mock_backtest_run(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a mock backtest run with sensible defaults.
    
    Args:
        overrides: Optional dict of fields to override
    
    Returns:
        Mock run data dict
    
    Example:
        >>> run = get_mock_backtest_run({"status": RunStatus.FAILED})
        >>> assert run["status"] == RunStatus.FAILED
    """
    now = datetime.now(timezone.utc)
    
    default = {
        "run_id": f"run-{uuid4().hex[:8]}",
        "strategy_id": "momentum_v1",
        "run_type": RunType.BACKTEST,
        "start_date": "2024-01-01",
        "end_date": "2025-12-31",
        "total_return": "18.45",
        "sharpe_ratio": "2.15",
        "max_drawdown": "-9.23",
        "total_trades": 87,
        "status": RunStatus.COMPLETED,
        "report_url": "https://storage.example.com/reports/test-run.html",
        "created_at": now - timedelta(hours=1),
        "completed_at": now - timedelta(minutes=45),
        "metrics": {
            "total_return": "18.45",
            "cagr": "17.82",
            "sharpe_ratio": "2.15",
            "sortino_ratio": "2.87",
            "max_drawdown": "-9.23",
            "win_rate": "0.61",
            "profit_factor": "2.34",
            "total_trades": 87,
            "avg_trade_duration_hours": "72.50",
        },
        "trades": [
            {
                "trade_id": f"trade-{uuid4().hex[:8]}",
                "symbol": "AAPL",
                "entry_time": now - timedelta(days=30),
                "exit_time": now - timedelta(days=27),
                "entry_price": "172.50",
                "exit_price": "178.25",
                "quantity": "100",
                "pnl": "575.00",
                "return_pct": "3.33",
            },
        ],
        "equity_curve": [
            {"date": "2024-01-01", "value": "100000.00"},
            {"date": "2024-06-01", "value": "108500.00"},
            {"date": "2025-01-01", "value": "112000.00"},
            {"date": "2025-12-31", "value": "118450.00"},
        ],
    }
    
    if overrides:
        # Handle nested updates
        if "metrics" in overrides and isinstance(overrides["metrics"], dict):
            default["metrics"] = {**default["metrics"], **overrides["metrics"]}
            overrides = {k: v for k, v in overrides.items() if k != "metrics"}
        
        default.update(overrides)
    
    return default


def get_mock_metrics(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create mock metrics summary with sensible defaults.
    
    Args:
        overrides: Optional dict of fields to override
    
    Returns:
        Mock metrics data dict
    
    Example:
        >>> metrics = get_mock_metrics({"total_pnl": "50000.00"})
        >>> assert metrics["total_pnl"] == "50000.00"
    """
    now = datetime.now(timezone.utc)
    
    default = {
        "total_pnl": "12345.67",
        "total_pnl_percent": "15.23",
        "sharpe_ratio": "1.85",
        "max_drawdown": "-8.45",
        "win_rate": "0.58",
        "total_trades": 142,
        "active_positions": 8,
        "capital_deployed": "45000.00",
        "available_capital": "55000.00",
        "equity_curve": [
            {"date": "2026-01-01", "value": "100000.00"},
            {"date": "2026-01-02", "value": "101234.56"},
            {"date": "2026-01-03", "value": "100890.12"},
            {"date": "2026-01-04", "value": "102345.67"},
            {"date": "2026-01-05", "value": "103456.78"},
        ],
        "period": "1m",
        "updated_at": now,
    }
    
    if overrides:
        default.update(overrides)
    
    return default


def get_mock_position(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a mock position with sensible defaults.
    
    Args:
        overrides: Optional dict of fields to override
    
    Returns:
        Mock position data dict
    
    Example:
        >>> pos = get_mock_position({"symbol": "GOOGL", "quantity": "50.00"})
        >>> assert pos["symbol"] == "GOOGL"
    """
    now = datetime.now(timezone.utc)
    
    default = {
        "position_id": f"pos-{uuid4().hex[:8]}",
        "strategy_id": "momentum_v1",
        "symbol": "AAPL",
        "contract_type": "STOCK",
        "quantity": "100.00",
        "average_entry_price": "150.25",
        "current_price": "155.80",
        "unrealized_pnl": "555.00",
        "unrealized_pnl_pct": "3.69",
        "market_value": "15580.00",
        "opened_at": now - timedelta(days=6),
        "days_held": 6,
        "entry_orders": [
            {
                "order_id": f"ord-{uuid4().hex[:8]}",
                "filled_at": now - timedelta(days=6),
                "quantity": "100.00",
                "price": "150.25",
            },
        ],
        "risk_metrics": {
            "stop_loss_price": "147.25",
            "take_profit_price": "157.76",
            "max_loss": "-300.00",
            "max_profit": "751.00",
        },
    }
    
    if overrides:
        # Handle nested updates
        if "risk_metrics" in overrides and isinstance(overrides["risk_metrics"], dict):
            default["risk_metrics"] = {**default["risk_metrics"], **overrides["risk_metrics"]}
            overrides = {k: v for k, v in overrides.items() if k != "risk_metrics"}
        
        default.update(overrides)
    
    return default


def get_mock_equity_curve(
    days: int = 30,
    start_value: float = 100000.0,
    volatility: float = 0.02,
) -> List[Dict[str, str]]:
    """
    Generate a mock equity curve.
    
    Args:
        days: Number of days to generate
        start_value: Starting equity value
        volatility: Daily volatility (as decimal)
    
    Returns:
        List of equity curve points
    """
    import random
    
    curve = []
    value = start_value
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        curve.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": f"{value:.2f}",
        })
        # Random walk with slight upward drift
        change = value * volatility * (random.random() - 0.45)
        value += change
    
    return curve


def get_mock_health_response(
    overall_status: str = "healthy",
    service_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Create a mock health response.
    
    Args:
        overall_status: Overall health status
        service_overrides: Optional service-specific overrides
    
    Returns:
        Mock health response dict
    """
    now = datetime.now(timezone.utc)
    
    services = {
        "database": {
            "status": "healthy",
            "latency_ms": 12,
        },
        "data_feed": {
            "status": "healthy",
            "last_update": now,
            "staleness_seconds": 10,
        },
        "broker_connection": {
            "status": "healthy",
            "broker": "alpaca",
            "mode": "PAPER",
        },
        "redis": {
            "status": "healthy",
        },
    }
    
    if service_overrides:
        for service, overrides in service_overrides.items():
            if service in services:
                services[service].update(overrides)
            else:
                services[service] = overrides
    
    return {
        "status": overall_status,
        "services": services,
        "timestamp": now,
    }
