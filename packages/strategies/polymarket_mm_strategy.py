"""
Polymarket fixed-spread market-making strategy.

Wraps the quoting logic from services/polymarket/quoting_engine.py into the
standard Strategy ABC. The SessionOrchestrator calls this strategy each
cycle instead of calling QuotingEngine directly.

Signal metadata keys:
    bid_price (str): computed bid price
    ask_price (str): computed ask price
    bid_size (str): computed bid size in shares
    ask_size (str): computed ask size in shares
    inventory_yes (str): current YES-share inventory at signal time
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from packages.common.schemas import Order, TradingMode
from packages.strategies.base import PortfolioState, Strategy

# Maximum book spread before quoting is suppressed
_MAX_QUOTED_SPREAD = Decimal("0.10")
_TICK = Decimal("0.01")


def _round_tick(price: Decimal) -> Decimal:
    return (price / _TICK).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * _TICK


class PolymarketMMStrategy(Strategy):
    """
    Fixed-spread symmetric market-making strategy for Polymarket binary markets.

    Config keys:
        market_id (str): Polymarket condition ID or readable name (for metadata)
        quote_spread (str/Decimal): full spread width in USDC, e.g. "0.02"
        quote_size (str/Decimal): shares per side, e.g. "50"
        inventory_cap (str/Decimal): max YES-shares before suppressing bid
    """

    market_type = MarketType.PREDICTION

    def __init__(self, strategy_id: str, config: Dict[str, Any]) -> None:
        super().__init__(strategy_id, config)
        self._market_id: str = config["market_id"]
        self._quote_spread = Decimal(str(config["quote_spread"]))
        self._quote_size = Decimal(str(config["quote_size"]))
        self._inventory_cap = Decimal(str(config["inventory_cap"]))
        self._last_ob_state: Optional[Any] = None
        self._inventory_yes: Decimal = Decimal("0")

    def initialize(self, mode: TradingMode) -> None:
        self.initialized = True
        self.mode = mode

    def on_market_data(self, bar: Any) -> None:
        """
        Accept an orderbook state snapshot.

        `bar` is any object with .midpoint (Optional[Decimal]) and
        .spread (Optional[Decimal]). In production this is DataFeedState.
        """
        self._last_ob_state = bar

    def update_inventory(self, inventory_yes: Decimal) -> None:
        """Called by session orchestrator after each fill to sync inventory."""
        self._inventory_yes = inventory_yes

    def generate_signals(self, portfolio: PortfolioState) -> List[UnifiedSignal]:
        """
        Compute fixed-spread quotes and emit one MARKET_MAKING signal.

        Returns empty list if:
        - No orderbook state received yet
        - Midpoint is None (stale feed)
        - Book spread wider than _MAX_QUOTED_SPREAD
        - Both bid_size and ask_size are 0 (inventory gate triggers both sides)
        """
        ob = self._last_ob_state
        if ob is None or ob.midpoint is None:
            return []

        if ob.spread is not None and ob.spread > _MAX_QUOTED_SPREAD:
            return []

        half = self._quote_spread / 2
        bid_price = _round_tick(ob.midpoint - half)
        ask_price = _round_tick(ob.midpoint + half)

        # Inventory gate: suppress bid if at cap, suppress ask if no inventory
        bid_size = Decimal("0") if self._inventory_yes >= self._inventory_cap else self._quote_size
        ask_size = Decimal("0") if self._inventory_yes <= 0 else self._quote_size

        if bid_size == Decimal("0") and ask_size == Decimal("0"):
            return []

        return [
            UnifiedSignal(
                asset_id=self._market_id,
                market_type=MarketType.PREDICTION,
                signal_type=SignalType.MARKET_MAKING,
                direction="none",
                confidence=Decimal("1.0"),
                horizon_seconds=self.config.get("horizon_seconds", 60),
                strategy_id=self.strategy_id,
                metadata={
                    "bid_price": str(bid_price),
                    "ask_price": str(ask_price),
                    "bid_size": str(bid_size),
                    "ask_size": str(ask_size),
                    "inventory_yes": str(self._inventory_yes),
                },
            )
        ]

    def risk_check(
        self, signals: List[UnifiedSignal], portfolio: PortfolioState
    ) -> List[Order]:
        """
        MM signals are passed to the executor directly via SessionOrchestrator.
        Strategy-level risk_check returns empty list; safety checks stay in SafetyLayer.
        """
        return []
