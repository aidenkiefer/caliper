"""
Strategy endpoints.

Provides CRUD operations for trading strategies.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from packages.common.api_schemas import (
    StrategyListResponse,
    StrategyListItem,
    StrategyListMeta,
    StrategyDetailResponse,
    StrategyDetailData,
    StrategyUpdateRequest,
    StrategyUpdateResponse,
    StrategyConfig,
    StrategyPerformance,
    StrategyStatus,
    StrategyMode,
)

router = APIRouter()

# Mock strategy data - TODO: Replace with database queries
MOCK_STRATEGIES = {
    "momentum_v1": {
        "strategy_id": "momentum_v1",
        "name": "Momentum Strategy V1",
        "description": "XGBoost-based momentum trading on S&P 500 stocks",
        "status": StrategyStatus.ACTIVE,
        "mode": StrategyMode.PAPER,
        "universe_size": 50,
        "max_positions": 10,
        "risk_per_trade_pct": "1.5",
        "created_at": datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 25, 8, 0, 0, tzinfo=timezone.utc),
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
    },
    "mean_reversion_v1": {
        "strategy_id": "mean_reversion_v1",
        "name": "Mean Reversion V1",
        "description": "Statistical arbitrage on correlated pairs",
        "status": StrategyStatus.INACTIVE,
        "mode": StrategyMode.BACKTEST,
        "universe_size": 20,
        "max_positions": 5,
        "risk_per_trade_pct": "1.0",
        "created_at": datetime(2026, 1, 10, 14, 30, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 20, 16, 45, 0, tzinfo=timezone.utc),
        "config": {
            "model_type": "linear_regression",
            "features": ["z_score", "spread", "correlation"],
            "signal_threshold": 2.0,
            "stop_loss_pct": "3.0",
            "take_profit_pct": "2.0",
        },
        "performance": {
            "total_pnl": "1234.56",
            "sharpe_ratio": "1.5",
            "max_drawdown": "-7.8",
            "win_rate": "0.55",
        },
    },
}


@router.get(
    "/strategies",
    response_model=StrategyListResponse,
    summary="List strategies",
    description="List all configured trading strategies.",
)
async def list_strategies(
    status: Optional[str] = Query(
        None,
        description="Filter by status: active, inactive, or all",
        pattern="^(active|inactive|all)$",
    ),
    mode: Optional[str] = Query(
        None,
        description="Filter by mode: BACKTEST, PAPER, or LIVE",
        pattern="^(BACKTEST|PAPER|LIVE)$",
    ),
) -> StrategyListResponse:
    """
    List all trading strategies.

    Args:
        status: Optional status filter (active, inactive, all)
        mode: Optional mode filter (BACKTEST, PAPER, LIVE)

    Returns:
        List of strategies with metadata
    """
    strategies = []

    for s in MOCK_STRATEGIES.values():
        # Apply status filter
        if status and status != "all":
            if s["status"].value != status:
                continue

        # Apply mode filter
        if mode and s["mode"].value != mode:
            continue

        strategies.append(
            StrategyListItem(
                strategy_id=s["strategy_id"],
                name=s["name"],
                description=s["description"],
                status=s["status"],
                mode=s["mode"],
                universe_size=s["universe_size"],
                max_positions=s["max_positions"],
                risk_per_trade_pct=s["risk_per_trade_pct"],
                created_at=s["created_at"],
                updated_at=s["updated_at"],
            )
        )

    active_count = sum(1 for s in strategies if s.status == StrategyStatus.ACTIVE)

    return StrategyListResponse(
        data=strategies,
        meta=StrategyListMeta(
            total_count=len(strategies),
            active_count=active_count,
        ),
    )


@router.get(
    "/strategies/{strategy_id}",
    response_model=StrategyDetailResponse,
    summary="Get strategy details",
    description="Get detailed information for a specific strategy.",
)
async def get_strategy(strategy_id: str) -> StrategyDetailResponse:
    """
    Get details for a specific strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Strategy details including config and performance

    Raises:
        HTTPException: 404 if strategy not found
    """
    if strategy_id not in MOCK_STRATEGIES:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    s = MOCK_STRATEGIES[strategy_id]

    return StrategyDetailResponse(
        data=StrategyDetailData(
            strategy_id=s["strategy_id"],
            name=s["name"],
            description=s["description"],
            status=s["status"],
            config=StrategyConfig(
                model_type=s["config"]["model_type"],
                features=s["config"]["features"],
                signal_threshold=s["config"]["signal_threshold"],
                stop_loss_pct=s["config"]["stop_loss_pct"],
                take_profit_pct=s["config"]["take_profit_pct"],
            ),
            performance=StrategyPerformance(
                total_pnl=s["performance"]["total_pnl"],
                sharpe_ratio=s["performance"]["sharpe_ratio"],
                max_drawdown=s["performance"]["max_drawdown"],
                win_rate=s["performance"]["win_rate"],
            ),
        )
    )


@router.patch(
    "/strategies/{strategy_id}",
    response_model=StrategyUpdateResponse,
    summary="Update strategy",
    description="Update strategy configuration (enable/disable, adjust risk parameters).",
)
async def update_strategy(
    strategy_id: str,
    request: StrategyUpdateRequest,
) -> StrategyUpdateResponse:
    """
    Update a strategy's configuration.

    Args:
        strategy_id: Strategy identifier
        request: Update request with new status/config

    Returns:
        Updated strategy details

    Raises:
        HTTPException: 404 if strategy not found
    """
    if strategy_id not in MOCK_STRATEGIES:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    s = MOCK_STRATEGIES[strategy_id]

    # Apply updates
    if request.status is not None:
        s["status"] = request.status

    if request.config is not None:
        for key, value in request.config.items():
            if key in s["config"]:
                s["config"][key] = value

    s["updated_at"] = datetime.now(timezone.utc)

    return StrategyUpdateResponse(
        message="Strategy updated successfully",
        data=StrategyDetailData(
            strategy_id=s["strategy_id"],
            name=s["name"],
            description=s["description"],
            status=s["status"],
            config=StrategyConfig(
                model_type=s["config"]["model_type"],
                features=s["config"]["features"],
                signal_threshold=s["config"]["signal_threshold"],
                stop_loss_pct=s["config"]["stop_loss_pct"],
                take_profit_pct=s["config"]["take_profit_pct"],
            ),
            performance=StrategyPerformance(
                total_pnl=s["performance"]["total_pnl"],
                sharpe_ratio=s["performance"]["sharpe_ratio"],
                max_drawdown=s["performance"]["max_drawdown"],
                win_rate=s["performance"]["win_rate"],
            ),
        ),
    )
