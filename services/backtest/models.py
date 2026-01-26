"""
Pydantic models for backtesting configuration and results.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class BacktestConfig(BaseModel):
    """Configuration for a backtest run."""
    
    initial_capital: Decimal = Field(
        ...,
        gt=0,
        description="Starting capital for the backtest"
    )
    commission_per_trade: Decimal = Field(
        Decimal('1.00'),
        ge=0,
        description="Commission per trade (default: $1.00)"
    )
    slippage_bps: Decimal = Field(
        Decimal('10'),
        ge=0,
        le=1000,
        description="Slippage in basis points (default: 10 bps = 0.1%)"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Start date for backtest (if None, uses first bar)"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="End date for backtest (if None, uses last bar)"
    )
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def timestamps_must_be_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure timestamps are timezone-aware (UTC)."""
        if v is not None and v.tzinfo is None:
            raise ValueError('timestamp must be timezone-aware (UTC)')
        return v
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class EquityPoint(BaseModel):
    """Single point on the equity curve."""
    
    timestamp: datetime = Field(..., description="Timestamp for this equity point")
    equity: Decimal = Field(..., ge=0, description="Total portfolio equity")
    cash: Decimal = Field(..., ge=0, description="Cash balance")
    unrealized_pnl: Decimal = Field(..., description="Unrealized P&L")
    
    @field_validator('timestamp')
    @classmethod
    def timestamp_must_be_utc(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware (UTC)."""
        if v.tzinfo is None:
            raise ValueError('timestamp must be timezone-aware (UTC)')
        return v
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class Trade(BaseModel):
    """A completed trade (entry + exit)."""
    
    trade_id: UUID = Field(default_factory=uuid4, description="Unique trade identifier")
    symbol: str = Field(..., max_length=20, description="Trading symbol")
    entry_time: datetime = Field(..., description="Entry timestamp")
    exit_time: datetime = Field(..., description="Exit timestamp")
    entry_price: Decimal = Field(..., gt=0, description="Entry price")
    exit_price: Decimal = Field(..., gt=0, description="Exit price")
    quantity: Decimal = Field(..., gt=0, description="Quantity traded")
    commission: Decimal = Field(..., ge=0, description="Total commission paid")
    pnl: Decimal = Field(..., description="Profit/loss for this trade")
    return_pct: Decimal = Field(..., description="Return percentage")
    
    @field_validator('entry_time', 'exit_time')
    @classmethod
    def timestamps_must_be_utc(cls, v: datetime) -> datetime:
        """Ensure timestamps are timezone-aware (UTC)."""
        if v.tzinfo is None:
            raise ValueError('timestamp must be timezone-aware (UTC)')
        return v
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }


class PerformanceMetrics(BaseModel):
    """Performance metrics calculated from backtest results."""
    
    total_return: Decimal = Field(..., description="Total return (as decimal, e.g., 0.15 = 15%)")
    total_return_pct: Decimal = Field(..., description="Total return as percentage")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Annualized Sharpe ratio")
    max_drawdown: Decimal = Field(..., le=0, description="Maximum drawdown (negative value)")
    max_drawdown_pct: Decimal = Field(..., le=0, description="Maximum drawdown as percentage")
    win_rate: Decimal = Field(..., ge=0, le=1, description="Win rate (0.0 to 1.0)")
    total_trades: int = Field(..., ge=0, description="Total number of trades")
    winning_trades: int = Field(..., ge=0, description="Number of winning trades")
    losing_trades: int = Field(..., ge=0, description="Number of losing trades")
    avg_win: Optional[Decimal] = Field(None, description="Average winning trade P&L")
    avg_loss: Optional[Decimal] = Field(None, description="Average losing trade P&L")
    profit_factor: Optional[Decimal] = Field(None, ge=0, description="Profit factor (gross profit / gross loss)")
    
    class Config:
        json_encoders = {
            Decimal: str,
        }


class BacktestResult(BaseModel):
    """Complete backtest result."""
    
    backtest_id: UUID = Field(default_factory=uuid4, description="Unique backtest identifier")
    strategy_id: str = Field(..., description="Strategy that was backtested")
    config: BacktestConfig = Field(..., description="Configuration used")
    equity_curve: List[EquityPoint] = Field(..., description="Equity curve over time")
    trades: List[Trade] = Field(default_factory=list, description="All completed trades")
    metrics: PerformanceMetrics = Field(..., description="Performance metrics")
    start_time: datetime = Field(..., description="Backtest start time")
    end_time: datetime = Field(..., description="Backtest end time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('start_time', 'end_time')
    @classmethod
    def timestamps_must_be_utc(cls, v: datetime) -> datetime:
        """Ensure timestamps are timezone-aware (UTC)."""
        if v.tzinfo is None:
            raise ValueError('timestamp must be timezone-aware (UTC)')
        return v
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }


# ============================================================================
# Walk-Forward Optimization Models
# ============================================================================

class OptimizationObjective(str, Enum):
    """Objective function for parameter optimization."""
    SHARPE_RATIO = "sharpe_ratio"
    TOTAL_RETURN = "total_return"
    PROFIT_FACTOR = "profit_factor"
    WIN_RATE = "win_rate"
    MAX_DRAWDOWN = "max_drawdown"  # Minimize (will negate)


class WindowType(str, Enum):
    """Type of walk-forward window."""
    ROLLING = "rolling"  # Fixed-size window that moves forward
    ANCHORED = "anchored"  # Start fixed, end moves forward (expanding)


class ParameterRange(BaseModel):
    """Range of values for a single parameter to optimize."""
    
    name: str = Field(..., description="Parameter name (e.g., 'short_period')")
    min_value: float = Field(..., description="Minimum value")
    max_value: float = Field(..., description="Maximum value")
    step: float = Field(..., gt=0, description="Step size between values")
    param_type: str = Field("float", description="Parameter type: 'int' or 'float'")
    
    def get_values(self) -> List[Union[int, float]]:
        """Generate all values in the range."""
        values = []
        current = self.min_value
        while current <= self.max_value:
            if self.param_type == "int":
                values.append(int(current))
            else:
                values.append(current)
            current += self.step
        return values


class ParameterGrid(BaseModel):
    """Grid of parameters to optimize over."""
    
    parameters: List[ParameterRange] = Field(
        ...,
        min_length=1,
        description="List of parameter ranges to optimize"
    )
    
    def get_combinations(self) -> List[Dict[str, Any]]:
        """Generate all parameter combinations."""
        from itertools import product
        
        param_names = [p.name for p in self.parameters]
        param_values = [p.get_values() for p in self.parameters]
        
        combinations = []
        for values in product(*param_values):
            combinations.append(dict(zip(param_names, values)))
        
        return combinations
    
    def combination_count(self) -> int:
        """Return total number of combinations."""
        count = 1
        for param in self.parameters:
            count *= len(param.get_values())
        return count


class WalkForwardConfig(BaseModel):
    """Configuration for walk-forward optimization."""
    
    in_sample_days: int = Field(
        ...,
        gt=0,
        description="Number of days for in-sample (training) period"
    )
    out_of_sample_days: int = Field(
        ...,
        gt=0,
        description="Number of days for out-of-sample (test) period"
    )
    step_days: int = Field(
        ...,
        gt=0,
        description="Number of days to step forward each iteration"
    )
    window_type: WindowType = Field(
        WindowType.ROLLING,
        description="Rolling or anchored window type"
    )
    min_trades_required: int = Field(
        5,
        ge=0,
        description="Minimum trades required in in-sample for valid optimization"
    )
    objective: OptimizationObjective = Field(
        OptimizationObjective.SHARPE_RATIO,
        description="Optimization objective function"
    )
    parameter_grid: Optional[ParameterGrid] = Field(
        None,
        description="Parameter grid for optimization (None = no optimization)"
    )
    
    @model_validator(mode='after')
    def validate_step_size(self) -> 'WalkForwardConfig':
        """Ensure step size is reasonable."""
        if self.step_days > self.out_of_sample_days:
            raise ValueError('step_days should be <= out_of_sample_days to avoid gaps')
        return self


class WalkForwardWindow(BaseModel):
    """A single walk-forward window."""
    
    window_id: int = Field(..., description="Window sequence number (0-based)")
    in_sample_start: datetime = Field(..., description="In-sample period start")
    in_sample_end: datetime = Field(..., description="In-sample period end")
    out_of_sample_start: datetime = Field(..., description="Out-of-sample period start")
    out_of_sample_end: datetime = Field(..., description="Out-of-sample period end")
    
    @field_validator('in_sample_start', 'in_sample_end', 'out_of_sample_start', 'out_of_sample_end')
    @classmethod
    def timestamps_must_be_utc(cls, v: datetime) -> datetime:
        """Ensure timestamps are timezone-aware (UTC)."""
        if v.tzinfo is None:
            raise ValueError('timestamp must be timezone-aware (UTC)')
        return v


class OptimizationResult(BaseModel):
    """Result of parameter optimization for a single window."""
    
    window_id: int = Field(..., description="Window this optimization was for")
    best_params: Dict[str, Any] = Field(..., description="Best parameters found")
    best_objective_value: Decimal = Field(..., description="Best objective value achieved")
    all_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All parameter combinations tested with results"
    )
    optimization_time_seconds: float = Field(..., ge=0, description="Time taken for optimization")


class WalkForwardWindowResult(BaseModel):
    """Result for a single walk-forward window."""
    
    window: WalkForwardWindow = Field(..., description="Window configuration")
    optimization_result: Optional[OptimizationResult] = Field(
        None,
        description="Optimization result (None if no optimization)"
    )
    in_sample_result: BacktestResult = Field(..., description="In-sample backtest result")
    out_of_sample_result: BacktestResult = Field(..., description="Out-of-sample backtest result")
    params_used: Dict[str, Any] = Field(..., description="Parameters used for this window")


class ParameterStability(BaseModel):
    """Analysis of parameter stability across windows."""
    
    parameter_name: str = Field(..., description="Name of the parameter")
    values_used: List[Any] = Field(..., description="Values used in each window")
    mean_value: float = Field(..., description="Mean value across windows")
    std_value: float = Field(..., description="Standard deviation across windows")
    stability_score: Decimal = Field(
        ...,
        ge=0,
        le=1,
        description="Stability score (1.0 = perfectly stable)"
    )


class WalkForwardResult(BaseModel):
    """Complete walk-forward optimization result."""
    
    walk_forward_id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    strategy_id: str = Field(..., description="Strategy that was optimized")
    config: WalkForwardConfig = Field(..., description="Walk-forward configuration")
    backtest_config: BacktestConfig = Field(..., description="Backtest configuration used")
    windows: List[WalkForwardWindowResult] = Field(..., description="Results per window")
    
    # Aggregated out-of-sample metrics
    aggregated_metrics: PerformanceMetrics = Field(
        ...,
        description="Combined out-of-sample performance"
    )
    aggregated_trades: List[Trade] = Field(
        default_factory=list,
        description="All out-of-sample trades combined"
    )
    aggregated_equity_curve: List[EquityPoint] = Field(
        default_factory=list,
        description="Combined out-of-sample equity curve"
    )
    
    # Parameter stability analysis
    parameter_stability: List[ParameterStability] = Field(
        default_factory=list,
        description="Parameter stability analysis"
    )
    
    # Timing
    total_windows: int = Field(..., ge=0, description="Total number of windows")
    successful_windows: int = Field(..., ge=0, description="Windows with valid results")
    start_time: datetime = Field(..., description="Walk-forward start time")
    end_time: datetime = Field(..., description="Walk-forward end time")
    
    @field_validator('start_time', 'end_time')
    @classmethod
    def timestamps_must_be_utc(cls, v: datetime) -> datetime:
        """Ensure timestamps are timezone-aware (UTC)."""
        if v.tzinfo is None:
            raise ValueError('timestamp must be timezone-aware (UTC)')
        return v
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
