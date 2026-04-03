"""
Fee model for Polymarket binary market trading.

Computes taker fees, maker rebates, and net P&L under two fee regimes:

- Pre-March 30, 2026: flat 2% taker fee on contract value; no maker fee; no rebates.
- Post-March 30, 2026: curved taker fee f(p) = 0.02 × (1 - 2|p - 0.5|) × contract value;
  maker rebate r(p) = 0.01 × (1 - 2|p - 0.5|) × contract value.

The fee curve peaks at p=0.5 (maximum uncertainty) and approaches 0 at p=0 or p=1
(near-certain outcomes).  The curve factor is clamped to [0, 1].
"""

from datetime import date
from decimal import Decimal

from services.polymarket.constants import FEE_REGIME_CHANGE_DATE

# Fee rates
_TAKER_FEE_RATE = Decimal("0.02")
_MAKER_REBATE_RATE = Decimal("0.01")
_ZERO = Decimal("0")
_ONE = Decimal("1")
_TWO = Decimal("2")
_HALF = Decimal("0.5")


class FeeModel:
    """Compute trading fees and rebates for Polymarket binary markets.

    Parameters
    ----------
    as_of_date:
        The date to use when determining the fee regime.  Defaults to
        ``date.today()`` when not supplied; override for back-testing or
        unit tests.
    """

    def __init__(self, as_of_date: date | None = None) -> None:
        self._date: date = as_of_date or date.today()
        self._is_post_reform: bool = self._date >= FEE_REGIME_CHANGE_DATE

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def compute_fee(
        self,
        price: Decimal,
        size: Decimal,
        is_maker: bool,
        fees_enabled: bool,
    ) -> Decimal:
        """Return the fee charged for a single trade.

        Makers never pay fees in either regime.  If ``fees_enabled`` is
        ``False`` the method returns ``Decimal("0")`` regardless of other
        arguments.

        Parameters
        ----------
        price:
            Contract price in [0, 1].
        size:
            Number of contracts.
        is_maker:
            ``True`` when the order was resting (maker); ``False`` for a
            taker (aggressive) fill.
        fees_enabled:
            Whether fee deduction is active for this session.

        Returns
        -------
        Decimal
            Fee amount in USDC (same units as ``price × size``).
        """
        if not fees_enabled or is_maker:
            return _ZERO

        contract_value = price * size

        if self._is_post_reform:
            curve_factor = self._fee_curve_factor(price)
            return contract_value * _TAKER_FEE_RATE * curve_factor
        else:
            # Pre-reform: flat 2% taker fee
            return contract_value * _TAKER_FEE_RATE

    def compute_rebate(self, price: Decimal, size: Decimal) -> Decimal:
        """Return the estimated maker rebate for a fill.

        Pre-reform rebate is always zero.  Post-reform rebate uses the
        simplified per-fill formula r(p) = price × size × 0.01 ×
        (1 - 2|price - 0.5|).

        Parameters
        ----------
        price:
            Contract price in [0, 1].
        size:
            Number of contracts.

        Returns
        -------
        Decimal
            Estimated rebate amount in USDC.
        """
        if not self._is_post_reform:
            return _ZERO

        contract_value = price * size
        curve_factor = self._fee_curve_factor(price)
        return contract_value * _MAKER_REBATE_RATE * curve_factor

    def compute_net_pnl(
        self,
        gross_pnl: Decimal,
        fees_paid: Decimal,
        rebates_earned: Decimal,
    ) -> Decimal:
        """Return net P&L after fees and rebates.

        Parameters
        ----------
        gross_pnl:
            Gross profit or loss before fee attribution.
        fees_paid:
            Total fees paid (taker fees).
        rebates_earned:
            Total maker rebates received.

        Returns
        -------
        Decimal
            ``gross_pnl - fees_paid + rebates_earned``
        """
        return gross_pnl - fees_paid + rebates_earned

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fee_curve_factor(price: Decimal) -> Decimal:
        """Compute (1 - 2|price - 0.5|), clamped to [0, 1].

        The factor is 1.0 at p=0.5 and 0.0 at p=0 or p=1.
        """
        factor = _ONE - _TWO * abs(price - _HALF)
        if factor < _ZERO:
            return _ZERO
        if factor > _ONE:
            return _ONE
        return factor
