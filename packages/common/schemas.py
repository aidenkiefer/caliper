"""
Shared Pydantic schemas for the trading platform.

These schemas are the single source of truth for data contracts.
All services must use these exact schemas to ensure consistency.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Enums
# ============================================================================

class OptionRight(str, Enum):
    """Option contract type (call or put)."""
    CALL = "CALL"
    PUT = "PUT"


class ContractType(str, Enum):
    """Type of financial contract."""
    STOCK = "STOCK"
    OPTION = "OPTION"


class OrderSide(str, Enum):
    """Order side (buy or sell)."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    """Time in force for orders."""
    DAY = "DAY"  # Day order
    GTC = "GTC"  # Good-til-cancelled
    IOC = "IOC"  # Immediate-or-cancel
    FOK = "FOK"  # Fill-or-kill


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class TradingMode(str, Enum):
    """Trading mode."""
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"


# ============================================================================
# Market Data Schemas
# ============================================================================

class PriceBar(BaseModel):
    """
    OHLCV price bar for a given symbol and timeframe.
    
    Represents a candlestick bar with open, high, low, close, and volume.
    """
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol (e.g., AAPL)")
    exchange: Optional[str] = Field(None, max_length=10, description="Exchange code (e.g., NASDAQ)")
    timestamp: datetime = Field(..., description="Bar start time in UTC (timezone-aware)")
    timeframe: str = Field(..., pattern=r"^\d+(min|hour|day)$", description="Timeframe (e.g., 1min, 1day)")
    open: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="Highest price")
    low: Decimal = Field(..., gt=0, description="Lowest price")
    close: Decimal = Field(..., gt=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")
    vwap: Optional[Decimal] = Field(None, description="Volume-weighted average price")
    trade_count: Optional[int] = Field(None, ge=0, description="Number of trades in bar")
    source: str = Field(..., description="Data provider (e.g., alpaca, polygon, iex)")

    @field_validator('timestamp')
    @classmethod
    def timestamp_must_be_utc(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware (UTC)."""
        if v.tzinfo is None:
            raise ValueError('timestamp must be timezone-aware (UTC)')
        return v

    @model_validator(mode='after')
    def validate_ohlc(self) -> 'PriceBar':
        """Validate that high >= all prices and low <= all prices."""
        if self.high < self.open or self.high < self.close or self.high < self.low:
            raise ValueError('high must be >= open, close, and low')
        if self.low > self.open or self.low > self.close:
            raise ValueError('low must be <= open and close')
        return self

    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class OptionsQuote(BaseModel):
    """
    Options contract quote snapshot.
    
    Represents a snapshot of an options contract with pricing and Greeks.
    """
    underlying: str = Field(..., min_length=1, max_length=20, description="Underlying symbol (e.g., AAPL)")
    expiration: date = Field(..., description="Expiration date (YYYY-MM-DD)")
    strike: Decimal = Field(..., gt=0, description="Strike price")
    right: OptionRight = Field(..., description="Call or Put")
    timestamp: datetime = Field(..., description="Quote timestamp in UTC")
    bid: Optional[Decimal] = Field(None, ge=0, description="Bid price")
    ask: Optional[Decimal] = Field(None, ge=0, description="Ask price")
    mid: Optional[Decimal] = Field(None, ge=0, description="Midpoint price (bid + ask) / 2")
    last: Optional[Decimal] = Field(None, ge=0, description="Last trade price")
    volume: int = Field(0, ge=0, description="Daily volume")
    open_interest: int = Field(0, ge=0, description="Open interest")
    implied_volatility: Optional[Decimal] = Field(
        None, ge=0, le=10, description="Implied volatility as decimal (e.g., 0.25 = 25%)"
    )
    delta: Optional[Decimal] = Field(None, ge=-1, le=1, description="Delta Greek")
    gamma: Optional[Decimal] = Field(None, ge=0, description="Gamma Greek")
    theta: Optional[Decimal] = Field(None, description="Theta Greek")
    vega: Optional[Decimal] = Field(None, ge=0, description="Vega Greek")
    source: str = Field(..., description="Data provider")

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
            date: lambda v: v.isoformat(),
        }


# ============================================================================
# Execution Schemas
# ============================================================================

class Order(BaseModel):
    """
    Order sent to the broker (paper or live).
    
    Represents a trading order with all relevant metadata.
    """
    order_id: UUID = Field(..., description="Unique order identifier")
    strategy_id: str = Field(..., max_length=100, description="Strategy that generated this order")
    symbol: str = Field(..., max_length=20, description="Trading symbol")
    contract_type: ContractType = Field(..., description="Stock or Option")
    side: OrderSide = Field(..., description="Buy or Sell")
    quantity: Decimal = Field(..., gt=0, description="Order quantity (supports fractional shares)")
    order_type: OrderType = Field(..., description="Market, Limit, Stop, or Stop Limit")
    limit_price: Optional[Decimal] = Field(None, gt=0, description="Limit price (required for LIMIT orders)")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="Stop price (required for STOP orders)")
    time_in_force: TimeInForce = Field(TimeInForce.DAY, description="Time in force")
    status: OrderStatus = Field(OrderStatus.PENDING, description="Current order status")
    broker_order_id: Optional[str] = Field(None, max_length=100, description="Broker's order ID")
    submitted_at: Optional[datetime] = Field(None, description="When order was submitted to broker")
    filled_at: Optional[datetime] = Field(None, description="When order was filled")
    cancelled_at: Optional[datetime] = Field(None, description="When order was cancelled")
    filled_quantity: Decimal = Field(Decimal(0), ge=0, description="Quantity filled so far")
    average_fill_price: Optional[Decimal] = Field(None, gt=0, description="Average fill price")
    fees: Decimal = Field(Decimal(0), ge=0, description="Total fees for this order")
    reject_reason: Optional[str] = Field(None, description="Reason for rejection if status is REJECTED")
    mode: TradingMode = Field(..., description="Backtest, Paper, or Live")
    created_at: datetime = Field(..., description="When order was created")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_validator('submitted_at', 'filled_at', 'cancelled_at', 'created_at', 'updated_at')
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
            UUID: str,
        }


class Position(BaseModel):
    """
    Current holding (stock or option).
    
    Represents an open position with entry price and current P&L.
    """
    position_id: UUID = Field(..., description="Unique position identifier")
    strategy_id: str = Field(..., max_length=100, description="Strategy that owns this position")
    symbol: str = Field(..., max_length=20, description="Trading symbol")
    contract_type: ContractType = Field(..., description="Stock or Option")
    quantity: Decimal = Field(..., description="Position quantity (positive = long, negative = short)")
    average_entry_price: Decimal = Field(..., gt=0, description="Average entry price")
    current_price: Optional[Decimal] = Field(None, gt=0, description="Latest market price")
    unrealized_pnl: Optional[Decimal] = Field(None, description="Unrealized profit/loss")
    realized_pnl: Decimal = Field(Decimal(0), description="Locked-in P&L from closed portions")
    cost_basis: Optional[Decimal] = Field(None, description="Total cost including fees")
    market_value: Optional[Decimal] = Field(None, description="Current market value (quantity * current_price)")
    mode: TradingMode = Field(..., description="Paper or Live")
    opened_at: datetime = Field(..., description="When position was opened")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @model_validator(mode='after')
    def compute_unrealized_pnl(self) -> 'Position':
        """Compute unrealized P&L if current_price is available."""
        if self.current_price is not None:
            self.unrealized_pnl = (self.current_price - self.average_entry_price) * self.quantity
            self.market_value = self.current_price * abs(self.quantity)
        return self

    @field_validator('opened_at', 'updated_at')
    @classmethod
    def timestamp_must_be_utc(cls, v: datetime) -> datetime:
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
