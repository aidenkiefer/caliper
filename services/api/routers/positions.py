"""
Positions endpoints.

Provides endpoints for viewing open positions.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from packages.common.api_schemas import (
    PositionListResponse,
    PositionItem,
    PositionListMeta,
    PositionDetailResponse,
    PositionDetailData,
    EntryOrder,
    PositionRiskMetrics,
)

router = APIRouter()

# Mock position data - TODO: Replace with database queries
MOCK_POSITIONS = {
    "pos-001": {
        "position_id": "pos-001",
        "strategy_id": "momentum_v1",
        "symbol": "AAPL",
        "contract_type": "STOCK",
        "quantity": "100.00",
        "average_entry_price": "150.25",
        "current_price": "155.80",
        "unrealized_pnl": "555.00",
        "unrealized_pnl_pct": "3.69",
        "market_value": "15580.00",
        "opened_at": datetime(2026, 1, 20, 14, 30, 0, tzinfo=timezone.utc),
        "days_held": 6,
        "entry_orders": [
            {
                "order_id": "ord-001",
                "filled_at": datetime(2026, 1, 20, 14, 30, 0, tzinfo=timezone.utc),
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
    },
    "pos-002": {
        "position_id": "pos-002",
        "strategy_id": "momentum_v1",
        "symbol": "MSFT",
        "contract_type": "STOCK",
        "quantity": "50.00",
        "average_entry_price": "380.00",
        "current_price": "385.50",
        "unrealized_pnl": "275.00",
        "unrealized_pnl_pct": "1.45",
        "market_value": "19275.00",
        "opened_at": datetime(2026, 1, 22, 10, 15, 0, tzinfo=timezone.utc),
        "days_held": 4,
        "entry_orders": [
            {
                "order_id": "ord-002",
                "filled_at": datetime(2026, 1, 22, 10, 15, 0, tzinfo=timezone.utc),
                "quantity": "50.00",
                "price": "380.00",
            },
        ],
        "risk_metrics": {
            "stop_loss_price": "372.40",
            "take_profit_price": "399.00",
            "max_loss": "-380.00",
            "max_profit": "950.00",
        },
    },
    "pos-003": {
        "position_id": "pos-003",
        "strategy_id": "mean_reversion_v1",
        "symbol": "GOOGL",
        "contract_type": "STOCK",
        "quantity": "25.00",
        "average_entry_price": "142.50",
        "current_price": "140.25",
        "unrealized_pnl": "-56.25",
        "unrealized_pnl_pct": "-1.58",
        "market_value": "3506.25",
        "opened_at": datetime(2026, 1, 23, 9, 45, 0, tzinfo=timezone.utc),
        "days_held": 3,
        "entry_orders": [
            {
                "order_id": "ord-003",
                "filled_at": datetime(2026, 1, 23, 9, 45, 0, tzinfo=timezone.utc),
                "quantity": "25.00",
                "price": "142.50",
            },
        ],
        "risk_metrics": {
            "stop_loss_price": "138.23",
            "take_profit_price": "145.35",
            "max_loss": "-106.75",
            "max_profit": "71.25",
        },
    },
}


@router.get(
    "/positions",
    response_model=PositionListResponse,
    summary="List positions",
    description="List current open positions across all strategies.",
)
async def list_positions(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    mode: Optional[str] = Query(
        None,
        description="Filter by mode: PAPER or LIVE",
        pattern="^(PAPER|LIVE)$",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PositionListResponse:
    """
    List all open positions.
    
    Args:
        strategy_id: Optional filter by strategy
        symbol: Optional filter by symbol
        mode: Optional filter by mode (PAPER or LIVE)
        page: Page number (1-based)
        per_page: Items per page (max 100)
    
    Returns:
        Paginated list of positions
    """
    positions = []
    total_unrealized_pnl = 0.0
    
    for p in MOCK_POSITIONS.values():
        # Apply filters
        if strategy_id and p["strategy_id"] != strategy_id:
            continue
        if symbol and p["symbol"] != symbol:
            continue
        # mode filter would require mode field in position data
        
        positions.append(
            PositionItem(
                position_id=p["position_id"],
                strategy_id=p["strategy_id"],
                symbol=p["symbol"],
                contract_type=p["contract_type"],
                quantity=p["quantity"],
                average_entry_price=p["average_entry_price"],
                current_price=p["current_price"],
                unrealized_pnl=p["unrealized_pnl"],
                unrealized_pnl_pct=p["unrealized_pnl_pct"],
                market_value=p["market_value"],
                opened_at=p["opened_at"],
                days_held=p["days_held"],
            )
        )
        total_unrealized_pnl += float(p["unrealized_pnl"])
    
    # Simple pagination
    total = len(positions)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_positions = positions[start:end]
    
    return PositionListResponse(
        data=paginated_positions,
        meta=PositionListMeta(
            total_count=total,
            page=page,
            per_page=per_page,
            total_unrealized_pnl=f"{total_unrealized_pnl:.2f}",
        ),
    )


@router.get(
    "/positions/{position_id}",
    response_model=PositionDetailResponse,
    summary="Get position details",
    description="Get detailed information for a specific position.",
)
async def get_position(position_id: str) -> PositionDetailResponse:
    """
    Get details for a specific position.
    
    Args:
        position_id: Position identifier
    
    Returns:
        Position details including entry orders and risk metrics
    
    Raises:
        HTTPException: 404 if position not found
    """
    if position_id not in MOCK_POSITIONS:
        raise HTTPException(status_code=404, detail=f"Position '{position_id}' not found")
    
    p = MOCK_POSITIONS[position_id]
    
    entry_orders = [
        EntryOrder(
            order_id=o["order_id"],
            filled_at=o["filled_at"],
            quantity=o["quantity"],
            price=o["price"],
        )
        for o in p["entry_orders"]
    ]
    
    risk_metrics = PositionRiskMetrics(
        stop_loss_price=p["risk_metrics"]["stop_loss_price"],
        take_profit_price=p["risk_metrics"]["take_profit_price"],
        max_loss=p["risk_metrics"]["max_loss"],
        max_profit=p["risk_metrics"]["max_profit"],
    )
    
    return PositionDetailResponse(
        data=PositionDetailData(
            position_id=p["position_id"],
            strategy_id=p["strategy_id"],
            symbol=p["symbol"],
            quantity=p["quantity"],
            entry_orders=entry_orders,
            unrealized_pnl=p["unrealized_pnl"],
            risk_metrics=risk_metrics,
        )
    )
