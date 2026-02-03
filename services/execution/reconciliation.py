"""
Position tracking and reconciliation.

Maintains local position state and reconciles with broker state.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .broker.base import BrokerClient, Position as BrokerPosition


class TrackedPosition(BaseModel):
    """
    Position tracked by the execution engine.

    Includes local tracking state and strategy attribution.
    """

    position_id: UUID = Field(default_factory=uuid4, description="Internal position ID")
    symbol: str = Field(..., description="Trading symbol")
    strategy_id: str = Field(..., description="Strategy that owns this position")

    # Position details
    quantity: Decimal = Field(Decimal(0), description="Current quantity")
    average_entry_price: Decimal = Field(Decimal(0), description="Average entry price")
    cost_basis: Decimal = Field(Decimal(0), description="Total cost basis")

    # Market data (updated from broker)
    current_price: Optional[Decimal] = Field(None, description="Current market price")
    market_value: Optional[Decimal] = Field(None, description="Current market value")
    unrealized_pnl: Optional[Decimal] = Field(None, description="Unrealized P&L")
    realized_pnl: Decimal = Field(Decimal(0), description="Realized P&L from closed portions")

    # Timestamps
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = Field(None, description="When position was fully closed")

    def is_open(self) -> bool:
        """Check if position is still open."""
        return self.quantity != 0

    def is_long(self) -> bool:
        """Check if position is long."""
        return self.quantity > 0

    def is_short(self) -> bool:
        """Check if position is short."""
        return self.quantity < 0

    def update_market_data(
        self,
        current_price: Decimal,
    ) -> None:
        """Update position with current market price."""
        self.current_price = current_price
        self.market_value = abs(self.quantity) * current_price
        self.unrealized_pnl = (current_price - self.average_entry_price) * self.quantity
        self.updated_at = datetime.now(timezone.utc)


class PositionDiscrepancy(BaseModel):
    """Discrepancy between local and broker position state."""

    symbol: str
    local_quantity: Decimal
    broker_quantity: Decimal
    local_avg_price: Decimal
    broker_avg_price: Decimal
    discrepancy_type: str  # "quantity_mismatch", "price_mismatch", "missing_local", "missing_broker"
    severity: str  # "warning", "error"
    message: str


class ReconciliationResult(BaseModel):
    """Result of position reconciliation."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    has_discrepancies: bool = Field(False)
    discrepancies: List[PositionDiscrepancy] = Field(default_factory=list)
    local_positions: int = Field(0)
    broker_positions: int = Field(0)
    matched_positions: int = Field(0)

    def add_discrepancy(
        self,
        symbol: str,
        local_quantity: Decimal,
        broker_quantity: Decimal,
        local_avg_price: Decimal,
        broker_avg_price: Decimal,
        discrepancy_type: str,
        severity: str,
        message: str,
    ) -> None:
        """Add a discrepancy to the result."""
        self.discrepancies.append(
            PositionDiscrepancy(
                symbol=symbol,
                local_quantity=local_quantity,
                broker_quantity=broker_quantity,
                local_avg_price=local_avg_price,
                broker_avg_price=broker_avg_price,
                discrepancy_type=discrepancy_type,
                severity=severity,
                message=message,
            )
        )
        self.has_discrepancies = True


class PositionTracker:
    """
    Tracks positions across strategies and reconciles with broker.

    Features:
    - Multi-strategy position tracking
    - Fill processing to update positions
    - Broker reconciliation
    - P&L tracking
    """

    def __init__(self):
        """Initialize position tracker."""
        # Positions indexed by position_id
        self._positions: Dict[UUID, TrackedPosition] = {}

        # Index by symbol for quick lookup
        self._symbol_index: Dict[str, Set[UUID]] = {}

        # Index by strategy
        self._strategy_index: Dict[str, Set[UUID]] = {}

        # Aggregate position by symbol (across all strategies)
        self._aggregate_by_symbol: Dict[str, Decimal] = {}

    def open_position(
        self,
        symbol: str,
        strategy_id: str,
        quantity: Decimal,
        entry_price: Decimal,
    ) -> TrackedPosition:
        """
        Open a new position or add to existing.

        Args:
            symbol: Trading symbol
            strategy_id: Strategy identifier
            quantity: Position quantity (positive for long, negative for short)
            entry_price: Entry price

        Returns:
            TrackedPosition
        """
        # Check if strategy already has position in this symbol
        existing = self.get_position(symbol, strategy_id)

        if existing:
            # Update existing position
            return self.update_position(
                existing.position_id,
                quantity_delta=quantity,
                price=entry_price,
            )

        # Create new position
        cost = abs(quantity) * entry_price
        position = TrackedPosition(
            symbol=symbol,
            strategy_id=strategy_id,
            quantity=quantity,
            average_entry_price=entry_price,
            cost_basis=cost,
        )

        # Store and index
        self._positions[position.position_id] = position

        # Symbol index
        if symbol not in self._symbol_index:
            self._symbol_index[symbol] = set()
        self._symbol_index[symbol].add(position.position_id)

        # Strategy index
        if strategy_id not in self._strategy_index:
            self._strategy_index[strategy_id] = set()
        self._strategy_index[strategy_id].add(position.position_id)

        # Update aggregate
        self._aggregate_by_symbol[symbol] = (
            self._aggregate_by_symbol.get(symbol, Decimal(0)) + quantity
        )

        return position

    def update_position(
        self,
        position_id: UUID,
        quantity_delta: Decimal,
        price: Decimal,
    ) -> TrackedPosition:
        """
        Update an existing position (add or reduce).

        Args:
            position_id: Position ID
            quantity_delta: Quantity change (positive to add, negative to reduce)
            price: Transaction price

        Returns:
            Updated TrackedPosition
        """
        position = self._positions.get(position_id)
        if not position:
            raise ValueError(f"Position not found: {position_id}")

        old_quantity = position.quantity
        new_quantity = old_quantity + quantity_delta

        # Check if we're adding or reducing
        if (old_quantity > 0 and quantity_delta > 0) or (old_quantity < 0 and quantity_delta < 0):
            # Adding to position - calculate new average
            old_value = abs(old_quantity) * position.average_entry_price
            new_value = abs(quantity_delta) * price
            total_value = old_value + new_value
            total_quantity = abs(old_quantity) + abs(quantity_delta)

            position.average_entry_price = (
                total_value / total_quantity if total_quantity > 0 else Decimal(0)
            )
            position.cost_basis = total_value
        else:
            # Reducing position - realize P&L
            closing_quantity = min(abs(quantity_delta), abs(old_quantity))
            pnl_per_share = price - position.average_entry_price

            if old_quantity > 0:  # Long position
                realized = closing_quantity * pnl_per_share
            else:  # Short position
                realized = closing_quantity * (-pnl_per_share)

            position.realized_pnl += realized

        # Update quantity
        position.quantity = new_quantity
        position.updated_at = datetime.now(timezone.utc)

        # Update aggregate
        self._aggregate_by_symbol[position.symbol] = (
            self._aggregate_by_symbol.get(position.symbol, Decimal(0)) + quantity_delta
        )

        # Check if position is closed
        if new_quantity == 0:
            position.closed_at = datetime.now(timezone.utc)

        return position

    def close_position(
        self,
        position_id: UUID,
        exit_price: Decimal,
    ) -> TrackedPosition:
        """
        Fully close a position.

        Args:
            position_id: Position ID
            exit_price: Exit price

        Returns:
            Closed TrackedPosition
        """
        position = self._positions.get(position_id)
        if not position:
            raise ValueError(f"Position not found: {position_id}")

        # Close by reducing by full quantity
        return self.update_position(
            position_id,
            quantity_delta=-position.quantity,
            price=exit_price,
        )

    def get_position(
        self,
        symbol: str,
        strategy_id: str,
    ) -> Optional[TrackedPosition]:
        """Get position for a symbol and strategy."""
        if strategy_id not in self._strategy_index:
            return None

        for pos_id in self._strategy_index[strategy_id]:
            position = self._positions.get(pos_id)
            if position and position.symbol == symbol and position.is_open():
                return position

        return None

    def get_positions_by_strategy(
        self,
        strategy_id: str,
        include_closed: bool = False,
    ) -> List[TrackedPosition]:
        """Get all positions for a strategy."""
        if strategy_id not in self._strategy_index:
            return []

        positions = [self._positions[pos_id] for pos_id in self._strategy_index[strategy_id]]

        if not include_closed:
            positions = [p for p in positions if p.is_open()]

        return positions

    def get_positions_by_symbol(
        self,
        symbol: str,
        include_closed: bool = False,
    ) -> List[TrackedPosition]:
        """Get all positions in a symbol."""
        if symbol not in self._symbol_index:
            return []

        positions = [self._positions[pos_id] for pos_id in self._symbol_index[symbol]]

        if not include_closed:
            positions = [p for p in positions if p.is_open()]

        return positions

    def get_all_open_positions(self) -> List[TrackedPosition]:
        """Get all open positions."""
        return [p for p in self._positions.values() if p.is_open()]

    def get_aggregate_position(self, symbol: str) -> Decimal:
        """Get aggregate position across all strategies for a symbol."""
        return self._aggregate_by_symbol.get(symbol, Decimal(0))

    def update_market_prices(
        self,
        prices: Dict[str, Decimal],
    ) -> None:
        """
        Update all positions with current market prices.

        Args:
            prices: Dict mapping symbol to current price
        """
        for position in self._positions.values():
            if position.is_open() and position.symbol in prices:
                position.update_market_data(prices[position.symbol])

    def update_from_broker(
        self,
        broker_positions: List[BrokerPosition],
    ) -> None:
        """
        Update positions with broker data.

        Args:
            broker_positions: List of positions from broker
        """
        for bp in broker_positions:
            if bp.current_price:
                # Update all positions in this symbol with current price
                for position in self.get_positions_by_symbol(bp.symbol):
                    position.update_market_data(bp.current_price)

    async def reconcile(
        self,
        broker_client: BrokerClient,
    ) -> ReconciliationResult:
        """
        Reconcile local positions with broker state.

        Args:
            broker_client: Broker client to fetch positions from

        Returns:
            ReconciliationResult with any discrepancies
        """
        result = ReconciliationResult()

        # Get broker positions
        broker_positions = await broker_client.get_positions()
        broker_by_symbol: Dict[str, BrokerPosition] = {bp.symbol: bp for bp in broker_positions}

        result.broker_positions = len(broker_positions)

        # Get local aggregate positions
        local_symbols = set(self._aggregate_by_symbol.keys())
        result.local_positions = sum(1 for q in self._aggregate_by_symbol.values() if q != 0)

        broker_symbols = set(broker_by_symbol.keys())
        all_symbols = local_symbols | broker_symbols

        for symbol in all_symbols:
            local_qty = self._aggregate_by_symbol.get(symbol, Decimal(0))
            broker_pos = broker_by_symbol.get(symbol)
            broker_qty = broker_pos.quantity if broker_pos else Decimal(0)

            # Skip if both are zero
            if local_qty == 0 and broker_qty == 0:
                continue

            # Get average prices (use 0 if missing)
            local_avg_price = Decimal(0)
            if local_qty != 0:
                # Calculate weighted average from all positions in this symbol
                positions = self.get_positions_by_symbol(symbol)
                if positions:
                    total_value = sum(abs(p.quantity) * p.average_entry_price for p in positions)
                    total_qty = sum(abs(p.quantity) for p in positions)
                    local_avg_price = total_value / total_qty if total_qty > 0 else Decimal(0)

            broker_avg_price = broker_pos.average_entry_price if broker_pos else Decimal(0)

            # Check for discrepancies
            if symbol not in broker_symbols:
                result.add_discrepancy(
                    symbol=symbol,
                    local_quantity=local_qty,
                    broker_quantity=Decimal(0),
                    local_avg_price=local_avg_price,
                    broker_avg_price=Decimal(0),
                    discrepancy_type="missing_broker",
                    severity="error",
                    message=f"Position in {symbol} exists locally but not at broker",
                )
            elif symbol not in local_symbols or local_qty == 0:
                result.add_discrepancy(
                    symbol=symbol,
                    local_quantity=Decimal(0),
                    broker_quantity=broker_qty,
                    local_avg_price=Decimal(0),
                    broker_avg_price=broker_avg_price,
                    discrepancy_type="missing_local",
                    severity="warning",
                    message=f"Position in {symbol} exists at broker but not tracked locally",
                )
            elif local_qty != broker_qty:
                result.add_discrepancy(
                    symbol=symbol,
                    local_quantity=local_qty,
                    broker_quantity=broker_qty,
                    local_avg_price=local_avg_price,
                    broker_avg_price=broker_avg_price,
                    discrepancy_type="quantity_mismatch",
                    severity="error",
                    message=f"Quantity mismatch for {symbol}: local={local_qty}, broker={broker_qty}",
                )
            else:
                result.matched_positions += 1

        return result

    def get_total_exposure(self) -> Dict[str, Decimal]:
        """
        Get total exposure by symbol.

        Returns:
            Dict mapping symbol to total market value
        """
        exposure = {}
        for position in self.get_all_open_positions():
            if position.market_value:
                exposure[position.symbol] = (
                    exposure.get(position.symbol, Decimal(0)) + position.market_value
                )
        return exposure

    def get_total_unrealized_pnl(self) -> Decimal:
        """Get total unrealized P&L across all positions."""
        total = Decimal(0)
        for position in self.get_all_open_positions():
            if position.unrealized_pnl:
                total += position.unrealized_pnl
        return total

    def get_total_realized_pnl(self) -> Decimal:
        """Get total realized P&L across all positions."""
        return sum(p.realized_pnl for p in self._positions.values())
