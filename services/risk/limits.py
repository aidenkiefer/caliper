"""
Risk limit definitions for portfolio, strategy, and order levels.

Implements limits from docs/risk-policy.md.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LimitType(str, Enum):
    """Type of risk limit."""
    # Portfolio-level
    MAX_DAILY_DRAWDOWN = "max_daily_drawdown"
    MAX_TOTAL_DRAWDOWN = "max_total_drawdown"
    MAX_CAPITAL_DEPLOYED = "max_capital_deployed"
    MAX_OPEN_POSITIONS = "max_open_positions"
    
    # Strategy-level
    MAX_STRATEGY_ALLOCATION = "max_strategy_allocation"
    MAX_STRATEGY_DRAWDOWN = "max_strategy_drawdown"
    STRATEGY_DAILY_LOSS = "strategy_daily_loss"
    
    # Order-level
    MAX_RISK_PER_TRADE = "max_risk_per_trade"
    MAX_NOTIONAL = "max_notional"
    MAX_PRICE_DEVIATION = "max_price_deviation"
    MIN_STOCK_PRICE = "min_stock_price"
    MAX_ORDER_QUANTITY = "max_order_quantity"
    
    # Other
    KILL_SWITCH_ACTIVE = "kill_switch_active"
    ASSET_BLOCKED = "asset_blocked"


class RiskLimitViolation(BaseModel):
    """Record of a risk limit violation."""
    limit_type: LimitType = Field(..., description="Type of limit violated")
    limit_value: str = Field(..., description="Configured limit value")
    actual_value: str = Field(..., description="Actual value that violated limit")
    message: str = Field(..., description="Human-readable violation message")
    severity: str = Field("error", description="Severity: warning, error")


class PortfolioLimits(BaseModel):
    """
    Portfolio-level risk limits (system-wide).
    
    From docs/risk-policy.md:
    - Max Daily Drawdown: 3% → Halt new entries
    - Max Total Drawdown: 10% → Kill switch
    - Max Capital Deployed: 80%
    - Max Open Positions: 20
    """
    # Drawdown limits
    max_daily_drawdown_pct: Decimal = Field(
        Decimal("3.0"),
        description="Max daily drawdown % before halting entries",
    )
    max_total_drawdown_pct: Decimal = Field(
        Decimal("10.0"),
        description="Max total drawdown % from high water mark (triggers kill switch)",
    )
    
    # Capital limits
    max_capital_deployed_pct: Decimal = Field(
        Decimal("80.0"),
        description="Max % of capital that can be deployed",
    )
    
    # Position limits
    max_open_positions: int = Field(
        20,
        description="Maximum number of open positions across all strategies",
    )
    
    # Margin (if enabled)
    max_margin_usage: Decimal = Field(
        Decimal("1.5"),
        description="Maximum margin multiplier (1.5x = 50% margin)",
    )
    
    def check_drawdown(
        self,
        daily_drawdown_pct: Decimal,
        total_drawdown_pct: Decimal,
    ) -> List[RiskLimitViolation]:
        """Check drawdown limits."""
        violations = []
        
        if daily_drawdown_pct >= self.max_daily_drawdown_pct:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.MAX_DAILY_DRAWDOWN,
                limit_value=f"{self.max_daily_drawdown_pct}%",
                actual_value=f"{daily_drawdown_pct}%",
                message=f"Daily drawdown of {daily_drawdown_pct}% exceeds limit of {self.max_daily_drawdown_pct}%",
                severity="error",
            ))
        
        if total_drawdown_pct >= self.max_total_drawdown_pct:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.MAX_TOTAL_DRAWDOWN,
                limit_value=f"{self.max_total_drawdown_pct}%",
                actual_value=f"{total_drawdown_pct}%",
                message=f"Total drawdown of {total_drawdown_pct}% exceeds kill switch threshold of {self.max_total_drawdown_pct}%",
                severity="error",
            ))
        
        return violations
    
    def check_capital(
        self,
        capital_deployed_pct: Decimal,
    ) -> List[RiskLimitViolation]:
        """Check capital deployment limits."""
        violations = []
        
        if capital_deployed_pct >= self.max_capital_deployed_pct:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.MAX_CAPITAL_DEPLOYED,
                limit_value=f"{self.max_capital_deployed_pct}%",
                actual_value=f"{capital_deployed_pct}%",
                message=f"Capital deployed of {capital_deployed_pct}% exceeds limit of {self.max_capital_deployed_pct}%",
                severity="error",
            ))
        
        return violations
    
    def check_positions(
        self,
        current_positions: int,
    ) -> List[RiskLimitViolation]:
        """Check position count limits."""
        violations = []
        
        if current_positions >= self.max_open_positions:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.MAX_OPEN_POSITIONS,
                limit_value=str(self.max_open_positions),
                actual_value=str(current_positions),
                message=f"Open positions ({current_positions}) at or exceeds limit of {self.max_open_positions}",
                severity="error",
            ))
        
        return violations


class StrategyLimits(BaseModel):
    """
    Strategy-level risk limits.
    
    From docs/risk-policy.md:
    - Max Allocation: 0-100% of portfolio
    - Max Drawdown: 5-10% of strategy allocation
    - Daily Loss Limit: 1-2% of strategy allocation
    """
    strategy_id: str = Field(..., description="Strategy identifier")
    
    # Allocation limits
    max_allocation_pct: Decimal = Field(
        Decimal("100.0"),
        description="Max % of portfolio this strategy can control",
    )
    current_allocation_pct: Decimal = Field(
        Decimal("0.0"),
        description="Current allocation %",
    )
    
    # Drawdown limits
    max_drawdown_pct: Decimal = Field(
        Decimal("10.0"),
        description="Max drawdown % before pausing strategy",
    )
    
    # Daily loss limit
    daily_loss_limit_pct: Decimal = Field(
        Decimal("2.0"),
        description="Max daily loss % before pausing for session",
    )
    
    # Status
    is_paused: bool = Field(False, description="Whether strategy is paused")
    pause_reason: Optional[str] = Field(None, description="Reason for pause")
    
    def check_allocation(
        self,
        new_allocation_pct: Decimal,
    ) -> List[RiskLimitViolation]:
        """Check if new allocation would exceed limit."""
        violations = []
        
        if new_allocation_pct > self.max_allocation_pct:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.MAX_STRATEGY_ALLOCATION,
                limit_value=f"{self.max_allocation_pct}%",
                actual_value=f"{new_allocation_pct}%",
                message=f"Strategy allocation of {new_allocation_pct}% would exceed limit of {self.max_allocation_pct}%",
                severity="error",
            ))
        
        return violations
    
    def check_drawdown(
        self,
        current_drawdown_pct: Decimal,
    ) -> List[RiskLimitViolation]:
        """Check strategy drawdown."""
        violations = []
        
        if current_drawdown_pct >= self.max_drawdown_pct:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.MAX_STRATEGY_DRAWDOWN,
                limit_value=f"{self.max_drawdown_pct}%",
                actual_value=f"{current_drawdown_pct}%",
                message=f"Strategy drawdown of {current_drawdown_pct}% exceeds limit of {self.max_drawdown_pct}%",
                severity="error",
            ))
        
        return violations
    
    def check_daily_loss(
        self,
        daily_loss_pct: Decimal,
    ) -> List[RiskLimitViolation]:
        """Check daily loss limit."""
        violations = []
        
        if daily_loss_pct >= self.daily_loss_limit_pct:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.STRATEGY_DAILY_LOSS,
                limit_value=f"{self.daily_loss_limit_pct}%",
                actual_value=f"{daily_loss_pct}%",
                message=f"Strategy daily loss of {daily_loss_pct}% exceeds limit of {self.daily_loss_limit_pct}%",
                severity="error",
            ))
        
        return violations


class OrderLimits(BaseModel):
    """
    Order-level risk limits (pre-trade checks).
    
    From docs/risk-policy.md:
    - Max Risk Per Trade: 2% of equity
    - Max Notional: $25,000
    - Price Deviation: >5% rejected
    - Min Stock Price: $5.00
    """
    # Position sizing
    max_risk_per_trade_pct: Decimal = Field(
        Decimal("2.0"),
        description="Max risk per trade as % of portfolio equity",
    )
    max_notional_per_trade: Decimal = Field(
        Decimal("25000"),
        description="Max notional value per trade",
    )
    
    # Price sanity checks
    max_price_deviation_pct: Decimal = Field(
        Decimal("5.0"),
        description="Max deviation from last traded price",
    )
    min_stock_price: Decimal = Field(
        Decimal("5.0"),
        description="Minimum stock price (penny stock filter)",
    )
    
    # Volume checks
    max_quantity_pct_of_adv: Decimal = Field(
        Decimal("10.0"),
        description="Max order quantity as % of average daily volume",
    )
    min_avg_volume: int = Field(
        500000,
        description="Minimum 20-day average volume",
    )
    
    # Asset restrictions
    blocked_symbols: List[str] = Field(
        default_factory=list,
        description="Symbols that cannot be traded",
    )
    
    def check_position_sizing(
        self,
        order_notional: Decimal,
        risk_amount: Decimal,
        portfolio_equity: Decimal,
    ) -> List[RiskLimitViolation]:
        """Check position sizing limits."""
        violations = []
        
        # Check notional cap
        if order_notional > self.max_notional_per_trade:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.MAX_NOTIONAL,
                limit_value=f"${self.max_notional_per_trade:,.2f}",
                actual_value=f"${order_notional:,.2f}",
                message=f"Order notional of ${order_notional:,.2f} exceeds limit of ${self.max_notional_per_trade:,.2f}",
                severity="error",
            ))
        
        # Check risk per trade
        if portfolio_equity > 0:
            risk_pct = (risk_amount / portfolio_equity) * 100
            if risk_pct > self.max_risk_per_trade_pct:
                violations.append(RiskLimitViolation(
                    limit_type=LimitType.MAX_RISK_PER_TRADE,
                    limit_value=f"{self.max_risk_per_trade_pct}%",
                    actual_value=f"{risk_pct:.2f}%",
                    message=f"Trade risk of {risk_pct:.2f}% exceeds limit of {self.max_risk_per_trade_pct}%",
                    severity="error",
                ))
        
        return violations
    
    def check_price_sanity(
        self,
        order_price: Decimal,
        last_price: Decimal,
        symbol: str,
    ) -> List[RiskLimitViolation]:
        """Check price sanity (fat finger protection)."""
        violations = []
        
        # Check minimum price
        if order_price < self.min_stock_price:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.MIN_STOCK_PRICE,
                limit_value=f"${self.min_stock_price}",
                actual_value=f"${order_price}",
                message=f"Stock price ${order_price} below minimum of ${self.min_stock_price}",
                severity="error",
            ))
        
        # Check price deviation
        if last_price > 0:
            deviation_pct = abs((order_price - last_price) / last_price) * 100
            if deviation_pct > self.max_price_deviation_pct:
                violations.append(RiskLimitViolation(
                    limit_type=LimitType.MAX_PRICE_DEVIATION,
                    limit_value=f"{self.max_price_deviation_pct}%",
                    actual_value=f"{deviation_pct:.2f}%",
                    message=f"Order price ${order_price} deviates {deviation_pct:.2f}% from last price ${last_price}",
                    severity="error",
                ))
        
        # Check blocked symbols
        if symbol in self.blocked_symbols:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.ASSET_BLOCKED,
                limit_value="blocked",
                actual_value=symbol,
                message=f"Symbol {symbol} is on the blocked list",
                severity="error",
            ))
        
        return violations
    
    def check_volume(
        self,
        order_quantity: int,
        avg_daily_volume: int,
    ) -> List[RiskLimitViolation]:
        """Check volume-based limits."""
        violations = []
        
        # Check minimum ADV
        if avg_daily_volume < self.min_avg_volume:
            violations.append(RiskLimitViolation(
                limit_type=LimitType.MAX_ORDER_QUANTITY,
                limit_value=f"{self.min_avg_volume:,}",
                actual_value=f"{avg_daily_volume:,}",
                message=f"Average volume {avg_daily_volume:,} below minimum of {self.min_avg_volume:,}",
                severity="warning",
            ))
        
        # Check order size vs ADV
        if avg_daily_volume > 0:
            quantity_pct = (order_quantity / avg_daily_volume) * 100
            if quantity_pct > self.max_quantity_pct_of_adv:
                violations.append(RiskLimitViolation(
                    limit_type=LimitType.MAX_ORDER_QUANTITY,
                    limit_value=f"{self.max_quantity_pct_of_adv}% of ADV",
                    actual_value=f"{quantity_pct:.2f}% of ADV",
                    message=f"Order quantity is {quantity_pct:.2f}% of ADV, exceeds limit of {self.max_quantity_pct_of_adv}%",
                    severity="error",
                ))
        
        return violations
