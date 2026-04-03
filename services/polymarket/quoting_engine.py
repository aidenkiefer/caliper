"""
V1 fixed-spread symmetric quoting engine for Polymarket binary market making.

Computes bid and ask prices from a midpoint using a symmetric spread offset,
rounds to the configured tick size, and gates quoting based on inventory
position and market conditions (stale data, wide spread).
"""

from decimal import Decimal, ROUND_HALF_UP

from services.polymarket.config import PolymarketConfig
from services.polymarket.schemas import QuoteDecision

# Maximum spread permitted before quoting is suppressed.
MAX_QUOTED_SPREAD = Decimal("0.10")


def round_to_tick(price: Decimal, tick_size: Decimal = Decimal("0.01")) -> Decimal:
    """Round price to nearest tick size.

    Parameters
    ----------
    price:
        The raw price to round.
    tick_size:
        Minimum price increment (default 0.01).

    Returns
    -------
    Decimal
        Price rounded to the nearest multiple of ``tick_size``.
    """
    return (price / tick_size).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick_size


class QuotingEngine:
    """V1 fixed-spread symmetric quoting engine.

    Produces bid/ask prices and sizes for a Polymarket binary YES token given
    an orderbook state snapshot and the current YES inventory.  All quoting
    decisions respect the configured spread, tick size, and inventory cap.
    """

    def compute_quotes(
        self,
        orderbook_state,
        inventory_yes: Decimal,
        config: PolymarketConfig,
        tick_size: Decimal = Decimal("0.01"),
    ) -> QuoteDecision:
        """Compute bid and ask quotes for the YES token.

        Parameters
        ----------
        orderbook_state:
            Any object with ``midpoint`` (``Optional[Decimal]``) and
            ``spread`` (``Optional[Decimal]``) attributes.  In production
            this will be a ``DataFeedState`` returned by
            ``DataFeed.get_current_state()``.
        inventory_yes:
            Current YES-share inventory (net long position in shares).
        config:
            Service configuration supplying ``quote_spread``, ``quote_size``,
            and ``inventory_cap``.
        tick_size:
            Minimum price increment used for rounding.  Defaults to
            ``Decimal("0.01")`` (1 cent).

        Returns
        -------
        QuoteDecision
            Populated quote decision.  When a side is suppressed the
            corresponding price is ``None`` and size is ``Decimal("0")``.
        """
        midpoint: Decimal | None = orderbook_state.midpoint
        spread: Decimal | None = orderbook_state.spread

        # --- Gate: no midpoint (stale / empty book) ---
        if midpoint is None:
            return QuoteDecision(
                bid_price=None,
                ask_price=None,
                bid_size=Decimal("0"),
                ask_size=Decimal("0"),
                should_quote_bid=False,
                should_quote_ask=False,
                midpoint=None,
                reason="no midpoint",
            )

        # --- Gate: wide market ---
        if spread is not None and spread > MAX_QUOTED_SPREAD:
            return QuoteDecision(
                bid_price=None,
                ask_price=None,
                bid_size=Decimal("0"),
                ask_size=Decimal("0"),
                should_quote_bid=False,
                should_quote_ask=False,
                midpoint=midpoint,
                reason="wide spread",
            )

        # --- Compute raw bid/ask from symmetric spread offset ---
        spread_offset = config.quote_spread / Decimal("2")
        bid_price = round_to_tick(midpoint - spread_offset, tick_size)
        ask_price = round_to_tick(midpoint + spread_offset, tick_size)

        should_quote_bid = True
        should_quote_ask = True
        reason = None

        # --- Gate: inventory cap reached — suppress bid (buying more YES) ---
        if inventory_yes >= config.inventory_cap:
            should_quote_bid = False
            reason = "inventory cap reached"

        # --- Gate: no YES inventory — suppress ask (cannot sell what we don't have) ---
        if inventory_yes <= Decimal("0"):
            should_quote_ask = False
            # Only set reason if not already set (bid suppression takes priority in messaging)
            if reason is None:
                reason = "no YES inventory for asks"

        return QuoteDecision(
            bid_price=bid_price if should_quote_bid else None,
            ask_price=ask_price if should_quote_ask else None,
            bid_size=config.quote_size if should_quote_bid else Decimal("0"),
            ask_size=config.quote_size if should_quote_ask else Decimal("0"),
            should_quote_bid=should_quote_bid,
            should_quote_ask=should_quote_ask,
            midpoint=midpoint,
            reason=reason,
        )
