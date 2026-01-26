"""
Pydantic schemas for API request/response models.

These schemas define the contract between the FastAPI backend and clients.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Common Response Envelope
# ============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information for a specific field."""
    field: str = Field(..., description="Field that caused the error")
    message: str = Field(..., description="Error message")


class ErrorResponse(BaseModel):
    """Standard error response format."""
    code: str = Field(..., description="Error code (e.g., VALIDATION_ERROR)")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Field-level errors")


class APIError(BaseModel):
    """Top-level error wrapper."""
    error: ErrorResponse
    request_id: Optional[str] = Field(None, description="Request ID for debugging")


# ============================================================================
# Metrics Schemas
# ============================================================================

class EquityCurvePoint(BaseModel):
    """Single point on the equity curve."""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    value: str = Field(..., description="Equity value as string")


class MetricsSummaryData(BaseModel):
    """Aggregated metrics data."""
    total_pnl: str = Field(..., description="Total P&L")
    total_pnl_percent: str = Field(..., description="Total P&L percentage")
    sharpe_ratio: str = Field(..., description="Sharpe ratio")
    max_drawdown: str = Field(..., description="Maximum drawdown percentage")
    win_rate: str = Field(..., description="Win rate (0.0 to 1.0)")
    total_trades: int = Field(..., description="Total number of trades")
    active_positions: int = Field(..., description="Number of active positions")
    capital_deployed: str = Field(..., description="Capital deployed")
    available_capital: str = Field(..., description="Available capital")
    equity_curve: List[EquityCurvePoint] = Field(default_factory=list, description="Equity curve")


class MetricsMeta(BaseModel):
    """Metadata for metrics response."""
    period: str = Field(..., description="Time period filter")
    updated_at: datetime = Field(..., description="Last update timestamp")


class MetricsSummaryResponse(BaseModel):
    """Response for GET /v1/metrics/summary."""
    data: MetricsSummaryData
    meta: MetricsMeta


# ============================================================================
# Strategy Schemas
# ============================================================================

class StrategyStatus(str, Enum):
    """Strategy status."""
    ACTIVE = "active"
    INACTIVE = "inactive"


class StrategyMode(str, Enum):
    """Strategy trading mode."""
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"


class StrategyConfig(BaseModel):
    """Strategy configuration details."""
    model_type: Optional[str] = Field(None, description="ML model type")
    features: Optional[List[str]] = Field(None, description="Feature list")
    signal_threshold: Optional[float] = Field(None, description="Signal threshold")
    stop_loss_pct: Optional[str] = Field(None, description="Stop loss percentage")
    take_profit_pct: Optional[str] = Field(None, description="Take profit percentage")
    risk_per_trade_pct: Optional[str] = Field(None, description="Risk per trade percentage")


class StrategyPerformance(BaseModel):
    """Strategy performance summary."""
    total_pnl: str = Field(..., description="Total P&L")
    sharpe_ratio: str = Field(..., description="Sharpe ratio")
    max_drawdown: str = Field(..., description="Maximum drawdown")
    win_rate: str = Field(..., description="Win rate")


class StrategyListItem(BaseModel):
    """Strategy item in list response."""
    strategy_id: str = Field(..., description="Strategy identifier")
    name: str = Field(..., description="Strategy name")
    description: Optional[str] = Field(None, description="Strategy description")
    status: StrategyStatus = Field(..., description="Active or inactive")
    mode: StrategyMode = Field(..., description="Trading mode")
    universe_size: Optional[int] = Field(None, description="Number of symbols in universe")
    max_positions: Optional[int] = Field(None, description="Maximum positions")
    risk_per_trade_pct: Optional[str] = Field(None, description="Risk per trade")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class StrategyListMeta(BaseModel):
    """Metadata for strategy list response."""
    total_count: int = Field(..., description="Total number of strategies")
    active_count: int = Field(..., description="Number of active strategies")


class StrategyListResponse(BaseModel):
    """Response for GET /v1/strategies."""
    data: List[StrategyListItem]
    meta: StrategyListMeta


class StrategyDetailData(BaseModel):
    """Detailed strategy data."""
    strategy_id: str = Field(..., description="Strategy identifier")
    name: str = Field(..., description="Strategy name")
    description: Optional[str] = Field(None, description="Strategy description")
    status: StrategyStatus = Field(..., description="Active or inactive")
    config: Optional[StrategyConfig] = Field(None, description="Configuration")
    performance: Optional[StrategyPerformance] = Field(None, description="Performance metrics")


class StrategyDetailResponse(BaseModel):
    """Response for GET /v1/strategies/{strategy_id}."""
    data: StrategyDetailData


class StrategyUpdateRequest(BaseModel):
    """Request for PATCH /v1/strategies/{strategy_id}."""
    status: Optional[StrategyStatus] = Field(None, description="New status")
    config: Optional[Dict[str, Any]] = Field(None, description="Config updates")


class StrategyUpdateResponse(BaseModel):
    """Response for PATCH /v1/strategies/{strategy_id}."""
    message: str = Field(..., description="Success message")
    data: StrategyDetailData


# ============================================================================
# Position Schemas
# ============================================================================

class PositionItem(BaseModel):
    """Position item in list response."""
    position_id: str = Field(..., description="Position identifier")
    strategy_id: str = Field(..., description="Strategy identifier")
    symbol: str = Field(..., description="Symbol")
    contract_type: str = Field(..., description="STOCK or OPTION")
    quantity: str = Field(..., description="Position quantity")
    average_entry_price: str = Field(..., description="Average entry price")
    current_price: str = Field(..., description="Current market price")
    unrealized_pnl: str = Field(..., description="Unrealized P&L")
    unrealized_pnl_pct: str = Field(..., description="Unrealized P&L percentage")
    market_value: str = Field(..., description="Current market value")
    opened_at: datetime = Field(..., description="When position was opened")
    days_held: int = Field(..., description="Days position has been held")


class PositionListMeta(BaseModel):
    """Metadata for position list response."""
    total_count: int = Field(..., description="Total positions")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    total_unrealized_pnl: str = Field(..., description="Total unrealized P&L")


class PositionListResponse(BaseModel):
    """Response for GET /v1/positions."""
    data: List[PositionItem]
    meta: PositionListMeta


class EntryOrder(BaseModel):
    """Entry order for a position."""
    order_id: str = Field(..., description="Order identifier")
    filled_at: datetime = Field(..., description="Fill timestamp")
    quantity: str = Field(..., description="Filled quantity")
    price: str = Field(..., description="Fill price")


class PositionRiskMetrics(BaseModel):
    """Risk metrics for a position."""
    stop_loss_price: Optional[str] = Field(None, description="Stop loss price")
    take_profit_price: Optional[str] = Field(None, description="Take profit price")
    max_loss: Optional[str] = Field(None, description="Maximum loss")
    max_profit: Optional[str] = Field(None, description="Maximum profit")


class PositionDetailData(BaseModel):
    """Detailed position data."""
    position_id: str = Field(..., description="Position identifier")
    strategy_id: str = Field(..., description="Strategy identifier")
    symbol: str = Field(..., description="Symbol")
    quantity: str = Field(..., description="Position quantity")
    entry_orders: List[EntryOrder] = Field(default_factory=list, description="Entry orders")
    unrealized_pnl: str = Field(..., description="Unrealized P&L")
    risk_metrics: Optional[PositionRiskMetrics] = Field(None, description="Risk metrics")


class PositionDetailResponse(BaseModel):
    """Response for GET /v1/positions/{position_id}."""
    data: PositionDetailData


# ============================================================================
# Run Schemas
# ============================================================================

class RunType(str, Enum):
    """Run type."""
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"


class RunStatus(str, Enum):
    """Run status."""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RunListItem(BaseModel):
    """Run item in list response."""
    run_id: str = Field(..., description="Run identifier")
    strategy_id: str = Field(..., description="Strategy identifier")
    run_type: RunType = Field(..., description="Run type")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    total_return: Optional[str] = Field(None, description="Total return percentage")
    sharpe_ratio: Optional[str] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[str] = Field(None, description="Maximum drawdown")
    total_trades: Optional[int] = Field(None, description="Total trades")
    status: RunStatus = Field(..., description="Run status")
    report_url: Optional[str] = Field(None, description="Report URL")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class RunListMeta(BaseModel):
    """Metadata for run list response."""
    total_count: int = Field(..., description="Total runs")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")


class RunListResponse(BaseModel):
    """Response for GET /v1/runs."""
    data: List[RunListItem]
    meta: RunListMeta


class RunMetrics(BaseModel):
    """Detailed run metrics."""
    total_return: str = Field(..., description="Total return percentage")
    cagr: Optional[str] = Field(None, description="CAGR")
    sharpe_ratio: Optional[str] = Field(None, description="Sharpe ratio")
    sortino_ratio: Optional[str] = Field(None, description="Sortino ratio")
    max_drawdown: str = Field(..., description="Maximum drawdown")
    win_rate: str = Field(..., description="Win rate")
    profit_factor: Optional[str] = Field(None, description="Profit factor")
    total_trades: int = Field(..., description="Total trades")
    avg_trade_duration_hours: Optional[str] = Field(None, description="Average trade duration")


class RunTrade(BaseModel):
    """Trade in a run."""
    trade_id: str = Field(..., description="Trade identifier")
    symbol: str = Field(..., description="Symbol")
    entry_time: datetime = Field(..., description="Entry timestamp")
    exit_time: datetime = Field(..., description="Exit timestamp")
    entry_price: str = Field(..., description="Entry price")
    exit_price: str = Field(..., description="Exit price")
    quantity: str = Field(..., description="Quantity")
    pnl: str = Field(..., description="P&L")
    return_pct: str = Field(..., description="Return percentage")


class RunDetailData(BaseModel):
    """Detailed run data."""
    run_id: str = Field(..., description="Run identifier")
    strategy_id: str = Field(..., description="Strategy identifier")
    metrics: RunMetrics = Field(..., description="Performance metrics")
    equity_curve: List[EquityCurvePoint] = Field(default_factory=list, description="Equity curve")
    trades: List[RunTrade] = Field(default_factory=list, description="Trade history")


class RunDetailResponse(BaseModel):
    """Response for GET /v1/runs/{run_id}."""
    data: RunDetailData


class RunCreateRequest(BaseModel):
    """Request for POST /v1/runs."""
    strategy_id: str = Field(..., description="Strategy to backtest")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    initial_capital: str = Field(..., description="Initial capital")


class RunCreateData(BaseModel):
    """Data for run creation response."""
    run_id: str = Field(..., description="New run identifier")
    status: RunStatus = Field(..., description="Run status")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion")


class RunCreateResponse(BaseModel):
    """Response for POST /v1/runs."""
    message: str = Field(..., description="Success message")
    data: RunCreateData


# ============================================================================
# Health Schemas
# ============================================================================

class ServiceHealth(BaseModel):
    """Health status of a single service."""
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    latency_ms: Optional[int] = Field(None, description="Latency in milliseconds")
    last_update: Optional[datetime] = Field(None, description="Last update timestamp")
    staleness_seconds: Optional[int] = Field(None, description="Data staleness")
    broker: Optional[str] = Field(None, description="Broker name")
    mode: Optional[str] = Field(None, description="Trading mode")


class HealthResponse(BaseModel):
    """Response for GET /v1/health."""
    status: str = Field(..., description="Overall status: healthy, degraded, unhealthy")
    services: Dict[str, ServiceHealth] = Field(..., description="Per-service health")
    timestamp: datetime = Field(..., description="Health check timestamp")
