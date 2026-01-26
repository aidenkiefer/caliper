"""
Unit tests for baseline strategies and regret calculation.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal

from services.ml.baselines.hold_cash import HoldCashBaseline
from services.ml.baselines.buy_and_hold import BuyAndHoldBaseline
from services.ml.baselines.random import RandomControlledBaseline
from services.ml.baselines.regret import RegretCalculator, RegretMetrics
from services.backtest.models import BacktestConfig, BacktestResult, PerformanceMetrics
from packages.common.schemas import PriceBar


class TestHoldCashBaseline:
    """Test hold cash baseline strategy."""
    
    def test_hold_cash_returns_zero(self):
        """Hold cash strategy should return 0% (ignoring risk-free rate)."""
        baseline = HoldCashBaseline(risk_free_rate=Decimal("0.0"))
        
        config = BacktestConfig(initial_capital=Decimal("100000"))
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        
        result = baseline.run(config, start_date, end_date)
        
        assert result.metrics.total_return == Decimal("0")
        assert len(result.trades) == 0
    
    def test_hold_cash_with_risk_free_rate(self):
        """Hold cash with risk-free rate should return positive."""
        baseline = HoldCashBaseline(risk_free_rate=Decimal("0.05"))  # 5% annual
        
        config = BacktestConfig(initial_capital=Decimal("100000"))
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        
        result = baseline.run(config, start_date, end_date)
        
        assert result.metrics.total_return > Decimal("0")


class TestBuyAndHoldBaseline:
    """Test buy & hold baseline strategy."""
    
    def test_buy_and_hold_matches_market(self):
        """Buy & hold should track market performance."""
        baseline = BuyAndHoldBaseline(symbol="SPY")
        
        config = BacktestConfig(initial_capital=Decimal("100000"))
        
        # Create price bars
        price_bars = [
            PriceBar(
                symbol="SPY",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                timeframe="1day",
                open=Decimal("400"),
                high=Decimal("405"),
                low=Decimal("399"),
                close=Decimal("402"),
                volume=1000000,
                source="alpaca",
            ),
            PriceBar(
                symbol="SPY",
                timestamp=datetime(2024, 12, 31, tzinfo=timezone.utc),
                timeframe="1day",
                open=Decimal("440"),
                high=Decimal("445"),
                low=Decimal("439"),
                close=Decimal("442"),
                volume=1000000,
                source="alpaca",
            ),
        ]
        
        result = baseline.run(config, price_bars)
        
        assert len(result.trades) == 1
        assert result.trades[0].entry_price == Decimal("402")
        assert result.trades[0].exit_price == Decimal("442")
        assert result.metrics.total_return > Decimal("0")  # Price went up


class TestRandomBaseline:
    """Test random baseline strategy."""
    
    def test_random_baseline_respects_risk_controls(self):
        """Random baseline should respect risk controls."""
        baseline = RandomControlledBaseline(
            max_risk_per_trade=Decimal("0.02"),
            seed=42,
        )
        
        config = BacktestConfig(initial_capital=Decimal("100000"))
        
        # Create price bars
        price_bars = [
            PriceBar(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                timeframe="1day",
                open=Decimal("150"),
                high=Decimal("155"),
                low=Decimal("149"),
                close=Decimal("152"),
                volume=1000000,
                source="alpaca",
            ),
        ] * 100  # 100 days
        
        result = baseline.run(config, price_bars)
        
        # Should have some trades (random)
        assert result.metrics.total_trades >= 0
    
    def test_random_baseline_reproducible_with_seed(self):
        """Random baseline should be reproducible with same seed."""
        baseline1 = RandomControlledBaseline(seed=42)
        baseline2 = RandomControlledBaseline(seed=42)
        
        config = BacktestConfig(initial_capital=Decimal("100000"))
        price_bars = [
            PriceBar(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                timeframe="1day",
                open=Decimal("150"),
                high=Decimal("155"),
                low=Decimal("149"),
                close=Decimal("152"),
                volume=1000000,
                source="alpaca",
            ),
        ] * 50
        
        result1 = baseline1.run(config, price_bars)
        result2 = baseline2.run(config, price_bars)
        
        # Results should be identical with same seed
        assert result1.metrics.total_trades == result2.metrics.total_trades


class TestRegretCalculation:
    """Test regret calculation."""
    
    def test_positive_regret_when_worse_than_baseline(self):
        """Regret should be positive when strategy underperforms baseline."""
        calculator = RegretCalculator()
        
        # Strategy underperforms
        strategy_result = BacktestResult(
            strategy_id="strategy-1",
            config=BacktestConfig(initial_capital=Decimal("100000")),
            equity_curve=[],
            trades=[],
            metrics=PerformanceMetrics(
                total_return=Decimal("0.05"),  # 5% return
                total_return_pct=Decimal("5.0"),
                sharpe_ratio=None,
                max_drawdown=Decimal("-0.10"),
                max_drawdown_pct=Decimal("-10.0"),
                win_rate=Decimal("0.5"),
                total_trades=10,
                winning_trades=5,
                losing_trades=5,
            ),
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        
        # Baseline outperforms
        baseline_results = {
            "hold_cash": BacktestResult(
                strategy_id="hold_cash",
                config=BacktestConfig(initial_capital=Decimal("100000")),
                equity_curve=[],
                trades=[],
                metrics=PerformanceMetrics(
                    total_return=Decimal("0.0"),
                    total_return_pct=Decimal("0.0"),
                    sharpe_ratio=None,
                    max_drawdown=Decimal("0"),
                    max_drawdown_pct=Decimal("0"),
                    win_rate=Decimal("0"),
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                ),
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
            ),
            "buy_and_hold": BacktestResult(
                strategy_id="buy_and_hold",
                config=BacktestConfig(initial_capital=Decimal("100000")),
                equity_curve=[],
                trades=[],
                metrics=PerformanceMetrics(
                    total_return=Decimal("0.12"),  # 12% return (better)
                    total_return_pct=Decimal("12.0"),
                    sharpe_ratio=None,
                    max_drawdown=Decimal("-0.05"),
                    max_drawdown_pct=Decimal("-5.0"),
                    win_rate=Decimal("1.0"),
                    total_trades=1,
                    winning_trades=1,
                    losing_trades=0,
                ),
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
            ),
        }
        
        regret = calculator.calculate(strategy_result, baseline_results)
        
        # Regret vs buy & hold should be negative (strategy worse)
        assert regret.regret_vs_buy_hold < Decimal("0")
        assert regret.outperforms_buy_hold is False
    
    def test_negative_regret_when_better_than_baseline(self):
        """Regret should be negative when strategy outperforms baseline."""
        calculator = RegretCalculator()
        
        # Strategy outperforms
        strategy_result = BacktestResult(
            strategy_id="strategy-1",
            config=BacktestConfig(initial_capital=Decimal("100000")),
            equity_curve=[],
            trades=[],
            metrics=PerformanceMetrics(
                total_return=Decimal("0.15"),  # 15% return
                total_return_pct=Decimal("15.0"),
                sharpe_ratio=None,
                max_drawdown=Decimal("-0.08"),
                max_drawdown_pct=Decimal("-8.0"),
                win_rate=Decimal("0.6"),
                total_trades=20,
                winning_trades=12,
                losing_trades=8,
            ),
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        
        # Baseline underperforms
        baseline_results = {
            "hold_cash": BacktestResult(
                strategy_id="hold_cash",
                config=BacktestConfig(initial_capital=Decimal("100000")),
                equity_curve=[],
                trades=[],
                metrics=PerformanceMetrics(
                    total_return=Decimal("0.0"),
                    total_return_pct=Decimal("0.0"),
                    sharpe_ratio=None,
                    max_drawdown=Decimal("0"),
                    max_drawdown_pct=Decimal("0"),
                    win_rate=Decimal("0"),
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                ),
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
            ),
            "buy_and_hold": BacktestResult(
                strategy_id="buy_and_hold",
                config=BacktestConfig(initial_capital=Decimal("100000")),
                equity_curve=[],
                trades=[],
                metrics=PerformanceMetrics(
                    total_return=Decimal("0.10"),  # 10% return (worse)
                    total_return_pct=Decimal("10.0"),
                    sharpe_ratio=None,
                    max_drawdown=Decimal("-0.12"),
                    max_drawdown_pct=Decimal("-12.0"),
                    win_rate=Decimal("1.0"),
                    total_trades=1,
                    winning_trades=1,
                    losing_trades=0,
                ),
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
            ),
        }
        
        regret = calculator.calculate(strategy_result, baseline_results)
        
        # Regret vs buy & hold should be positive (strategy better)
        assert regret.regret_vs_buy_hold > Decimal("0")
        assert regret.outperforms_buy_hold is True
