from decimal import Decimal

from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from services.portfolio.allocator import AllocationResult
from services.risk.global_risk_manager import GlobalRiskConfig, GlobalRiskManager


def _make_allocation(asset_id, direction, market_type, quantity):
    signal = UnifiedSignal(
        asset_id=asset_id,
        market_type=market_type,
        signal_type=SignalType.DIRECTIONAL,
        direction=direction,
        confidence=Decimal("0.8"),
        horizon_seconds=3600,
        strategy_id="test",
    )
    return AllocationResult(
        asset_id=asset_id,
        strategy_id="test",
        market_type=market_type,
        direction=direction,
        target_quantity=quantity,
        signal=signal,
    )


def _make_mm_allocation(asset_id):
    """Market-making allocation (direction='none', pass_through=True)."""
    signal = UnifiedSignal(
        asset_id=asset_id,
        market_type=MarketType.PREDICTION,
        signal_type=SignalType.MARKET_MAKING,
        direction="none",
        confidence=Decimal("1.0"),
        horizon_seconds=3600,
        strategy_id="test",
    )
    return AllocationResult(
        asset_id=asset_id,
        strategy_id="test",
        market_type=MarketType.PREDICTION,
        direction="none",
        target_quantity=Decimal("0"),
        signal=signal,
        pass_through=True,
    )


def test_global_risk_approves_normal_equity_trade():
    config = GlobalRiskConfig(
        total_equity=Decimal("100000"),
        max_drawdown_pct=Decimal("10"),
        kill_switch_active=False,
        max_polymarket_session_loss_usdc=Decimal("100"),
    )
    grm = GlobalRiskManager(config)
    allocation = _make_allocation("AAPL", "long", MarketType.EQUITY, Decimal("10"))
    result = grm.check(allocation, current_drawdown_pct=Decimal("2"))
    assert result.approved is True


def test_global_risk_rejects_when_kill_switch_active():
    config = GlobalRiskConfig(
        total_equity=Decimal("100000"),
        max_drawdown_pct=Decimal("10"),
        kill_switch_active=True,
        max_polymarket_session_loss_usdc=Decimal("100"),
    )
    grm = GlobalRiskManager(config)
    allocation = _make_allocation("AAPL", "long", MarketType.EQUITY, Decimal("10"))
    result = grm.check(allocation, current_drawdown_pct=Decimal("2"))
    assert result.approved is False
    assert "kill switch" in result.rejection_reason.lower()


def test_global_risk_rejects_when_drawdown_exceeded():
    config = GlobalRiskConfig(
        total_equity=Decimal("100000"),
        max_drawdown_pct=Decimal("10"),
        kill_switch_active=False,
        max_polymarket_session_loss_usdc=Decimal("100"),
    )
    grm = GlobalRiskManager(config)
    allocation = _make_allocation("AAPL", "long", MarketType.EQUITY, Decimal("10"))
    result = grm.check(allocation, current_drawdown_pct=Decimal("11"))
    assert result.approved is False
    assert "drawdown" in result.rejection_reason.lower()


def test_global_risk_rejects_polymarket_over_session_loss():
    config = GlobalRiskConfig(
        total_equity=Decimal("100000"),
        max_drawdown_pct=Decimal("10"),
        kill_switch_active=False,
        max_polymarket_session_loss_usdc=Decimal("50"),
    )
    grm = GlobalRiskManager(config)
    allocation = _make_mm_allocation("BTC-UP")
    result = grm.check(
        allocation,
        current_drawdown_pct=Decimal("1"),
        polymarket_session_pnl=Decimal("-60"),
    )
    assert result.approved is False
    assert "session loss" in result.rejection_reason.lower()


def test_global_risk_approves_polymarket_within_session_loss():
    config = GlobalRiskConfig(
        total_equity=Decimal("100000"),
        max_drawdown_pct=Decimal("10"),
        kill_switch_active=False,
        max_polymarket_session_loss_usdc=Decimal("100"),
    )
    grm = GlobalRiskManager(config)
    allocation = _make_mm_allocation("BTC-UP")
    result = grm.check(
        allocation,
        current_drawdown_pct=Decimal("1"),
        polymarket_session_pnl=Decimal("-40"),
    )
    assert result.approved is True


def test_global_risk_kill_switch_blocks_polymarket_too():
    config = GlobalRiskConfig(
        total_equity=Decimal("100000"),
        max_drawdown_pct=Decimal("10"),
        kill_switch_active=True,
        max_polymarket_session_loss_usdc=Decimal("100"),
    )
    grm = GlobalRiskManager(config)
    allocation = _make_mm_allocation("BTC-UP")
    result = grm.check(allocation, current_drawdown_pct=Decimal("1"))
    assert result.approved is False
    assert "kill switch" in result.rejection_reason.lower()
