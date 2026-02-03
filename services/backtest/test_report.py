"""
Unit tests for report generation.

Following @testing-patterns skill:
- Test behavior, not implementation
- Use descriptive test names
- Create factory functions for test data
- Keep tests focused (one behavior per test)
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List
from uuid import uuid4

from services.backtest.report import ReportGenerator
from services.backtest.models import (
    BacktestResult,
    BacktestConfig,
    Trade,
    EquityPoint,
    PerformanceMetrics,
)

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tests.fixtures.backtest_data import (
    get_mock_trade,
    get_mock_backtest_config,
    get_mock_equity_point,
    get_mock_performance_metrics,
)


# =============================================================================
# Factory Functions for Tests
# =============================================================================


def get_mock_backtest_result(
    num_trades: int = 3,
    num_equity_points: int = 10,
) -> BacktestResult:
    """
    Factory function for BacktestResult test data.

    Args:
        num_trades: Number of trades to include
        num_equity_points: Number of equity points to include

    Returns:
        BacktestResult with mock data
    """
    base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Generate trades
    trades = []
    for i in range(num_trades):
        entry_time = base_time + timedelta(days=i * 5)
        exit_time = entry_time + timedelta(days=3)
        pnl = Decimal("100") if i % 2 == 0 else Decimal("-50")

        trades.append(
            Trade(
                trade_id=uuid4(),
                symbol="AAPL",
                entry_time=entry_time,
                exit_time=exit_time,
                entry_price=Decimal("150.00"),
                exit_price=Decimal("155.00") if pnl > 0 else Decimal("145.00"),
                quantity=Decimal("10"),
                commission=Decimal("2.00"),
                pnl=pnl,
                return_pct=Decimal("3.33") if pnl > 0 else Decimal("-3.33"),
            )
        )

    # Generate equity curve
    equity_curve = []
    equity = Decimal("100000")
    for i in range(num_equity_points):
        equity += Decimal(str(i * 100 - 50))  # Slight upward trend
        equity_curve.append(
            EquityPoint(
                timestamp=base_time + timedelta(days=i),
                equity=equity,
                cash=equity * Decimal("0.8"),
                unrealized_pnl=equity * Decimal("0.01"),
            )
        )

    return BacktestResult(
        backtest_id=uuid4(),
        strategy_id="test-strategy",
        config=get_mock_backtest_config(),
        equity_curve=equity_curve,
        trades=trades,
        metrics=get_mock_performance_metrics(),
        start_time=base_time,
        end_time=base_time + timedelta(days=num_equity_points),
        metadata={"test": True},
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def report_generator() -> ReportGenerator:
    """Create a ReportGenerator instance."""
    return ReportGenerator()


@pytest.fixture
def sample_result() -> BacktestResult:
    """Create a sample backtest result."""
    return get_mock_backtest_result()


@pytest.fixture
def empty_result() -> BacktestResult:
    """Create a backtest result with no trades."""
    return get_mock_backtest_result(num_trades=0, num_equity_points=5)


# =============================================================================
# Tests: JSON Report Generation
# =============================================================================


class TestJsonReportGeneration:
    """Tests for JSON report generation."""

    def test_generates_valid_json(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """Generated JSON should be valid and serializable."""
        report = report_generator.generate_json(sample_result)

        # Should be a dictionary
        assert isinstance(report, dict)

        # Should be JSON serializable
        json_str = json.dumps(report)
        assert json_str is not None

        # Should be able to parse back
        parsed = json.loads(json_str)
        assert parsed == report

    def test_json_contains_backtest_id(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """JSON report should contain backtest_id."""
        report = report_generator.generate_json(sample_result)

        assert "backtest_id" in report
        assert report["backtest_id"] == str(sample_result.backtest_id)

    def test_json_contains_strategy_id(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """JSON report should contain strategy_id."""
        report = report_generator.generate_json(sample_result)

        assert "strategy_id" in report
        assert report["strategy_id"] == sample_result.strategy_id

    def test_json_contains_timestamps(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """JSON report should contain start_time and end_time."""
        report = report_generator.generate_json(sample_result)

        assert "start_time" in report
        assert "end_time" in report

        # Should be ISO format strings
        assert isinstance(report["start_time"], str)
        assert isinstance(report["end_time"], str)

    def test_json_contains_config(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """JSON report should contain configuration."""
        report = report_generator.generate_json(sample_result)

        assert "config" in report
        config = report["config"]

        assert "initial_capital" in config
        assert "commission_per_trade" in config
        assert "slippage_bps" in config

    def test_json_contains_metrics(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """JSON report should contain all performance metrics."""
        report = report_generator.generate_json(sample_result)

        assert "metrics" in report
        metrics = report["metrics"]

        # Required metrics fields
        required_fields = [
            "total_return",
            "total_return_pct",
            "sharpe_ratio",
            "max_drawdown",
            "max_drawdown_pct",
            "win_rate",
            "total_trades",
            "winning_trades",
            "losing_trades",
        ]

        for field in required_fields:
            assert field in metrics, f"Missing metric: {field}"

    def test_json_contains_trades(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """JSON report should contain all trades."""
        report = report_generator.generate_json(sample_result)

        assert "trades" in report
        trades = report["trades"]

        assert len(trades) == len(sample_result.trades)

        # Check trade structure
        for trade in trades:
            assert "trade_id" in trade
            assert "symbol" in trade
            assert "entry_time" in trade
            assert "exit_time" in trade
            assert "entry_price" in trade
            assert "exit_price" in trade
            assert "quantity" in trade
            assert "pnl" in trade
            assert "return_pct" in trade

    def test_json_contains_equity_curve(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """JSON report should contain equity curve."""
        report = report_generator.generate_json(sample_result)

        assert "equity_curve" in report
        equity_curve = report["equity_curve"]

        assert len(equity_curve) == len(sample_result.equity_curve)

        # Check equity point structure
        for point in equity_curve:
            assert "timestamp" in point
            assert "equity" in point
            assert "cash" in point
            assert "unrealized_pnl" in point

    def test_json_handles_empty_trades(
        self, report_generator: ReportGenerator, empty_result: BacktestResult
    ):
        """JSON report should handle backtest with no trades."""
        report = report_generator.generate_json(empty_result)

        assert "trades" in report
        assert report["trades"] == []

    def test_json_contains_metadata(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """JSON report should contain metadata."""
        report = report_generator.generate_json(sample_result)

        assert "metadata" in report
        assert report["metadata"] == sample_result.metadata


# =============================================================================
# Tests: HTML Report Generation
# =============================================================================


class TestHtmlReportGeneration:
    """Tests for HTML report generation."""

    def test_generates_valid_html(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """Generated HTML should be a valid string."""
        html = report_generator.generate_html(sample_result)

        assert isinstance(html, str)
        assert len(html) > 0

    def test_html_contains_doctype(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """HTML should start with DOCTYPE declaration."""
        html = report_generator.generate_html(sample_result)

        assert "<!DOCTYPE html>" in html

    def test_html_contains_strategy_id(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """HTML should display strategy ID."""
        html = report_generator.generate_html(sample_result)

        assert sample_result.strategy_id in html

    def test_html_contains_metrics_section(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """HTML should contain performance metrics section."""
        html = report_generator.generate_html(sample_result)

        assert "Performance Metrics" in html
        assert "Total Return" in html
        assert "Sharpe Ratio" in html or "sharpe" in html.lower()
        assert "Max Drawdown" in html or "drawdown" in html.lower()
        assert "Win Rate" in html

    def test_html_contains_equity_chart_section(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """HTML should contain equity chart section."""
        html = report_generator.generate_html(sample_result)

        assert "Equity Curve" in html or "equity-chart" in html

    def test_html_contains_trades_section(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """HTML should contain trades table section."""
        html = report_generator.generate_html(sample_result)

        assert "Trades" in html
        assert "Symbol" in html
        assert "Entry" in html
        assert "Exit" in html
        assert "P&L" in html or "pnl" in html.lower()

    def test_html_includes_plotly(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """HTML should include Plotly for charts."""
        html = report_generator.generate_html(sample_result)

        assert "plotly" in html.lower()

    def test_html_handles_empty_trades(
        self, report_generator: ReportGenerator, empty_result: BacktestResult
    ):
        """HTML should handle backtest with no trades gracefully."""
        html = report_generator.generate_html(empty_result)

        # Should still generate valid HTML
        assert "<!DOCTYPE html>" in html
        assert "No trades" in html or "no trades" in html.lower() or "0 total" in html

    def test_html_contains_styling(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """HTML should contain CSS styling."""
        html = report_generator.generate_html(sample_result)

        assert "<style>" in html
        assert "</style>" in html

    def test_html_displays_dates(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """HTML should display backtest dates."""
        html = report_generator.generate_html(sample_result)

        # Should contain year from the backtest
        assert "2024" in html  # From our mock data


# =============================================================================
# Tests: Report Structure Validation
# =============================================================================


class TestReportStructure:
    """Tests for report structure completeness."""

    def test_json_report_all_required_fields_present(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """JSON report should have all required top-level fields."""
        report = report_generator.generate_json(sample_result)

        required_fields = [
            "backtest_id",
            "strategy_id",
            "start_time",
            "end_time",
            "config",
            "metrics",
            "trades",
            "equity_curve",
            "metadata",
        ]

        for field in required_fields:
            assert field in report, f"Missing required field: {field}"

    def test_metrics_structure_complete(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """Metrics should have all required fields."""
        report = report_generator.generate_json(sample_result)
        metrics = report["metrics"]

        required_metric_fields = [
            "total_return",
            "total_return_pct",
            "sharpe_ratio",
            "max_drawdown",
            "max_drawdown_pct",
            "win_rate",
            "total_trades",
            "winning_trades",
            "losing_trades",
            "avg_win",
            "avg_loss",
            "profit_factor",
        ]

        for field in required_metric_fields:
            assert field in metrics, f"Missing metric field: {field}"

    def test_trade_structure_complete(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """Each trade should have all required fields."""
        report = report_generator.generate_json(sample_result)

        required_trade_fields = [
            "trade_id",
            "symbol",
            "entry_time",
            "exit_time",
            "entry_price",
            "exit_price",
            "quantity",
            "commission",
            "pnl",
            "return_pct",
        ]

        for trade in report["trades"]:
            for field in required_trade_fields:
                assert field in trade, f"Missing trade field: {field}"

    def test_equity_point_structure_complete(
        self, report_generator: ReportGenerator, sample_result: BacktestResult
    ):
        """Each equity point should have all required fields."""
        report = report_generator.generate_json(sample_result)

        required_equity_fields = [
            "timestamp",
            "equity",
            "cash",
            "unrealized_pnl",
        ]

        for point in report["equity_curve"]:
            for field in required_equity_fields:
                assert field in point, f"Missing equity point field: {field}"


# =============================================================================
# Tests: Edge Cases
# =============================================================================


class TestReportEdgeCases:
    """Tests for edge cases in report generation."""

    def test_handles_null_optional_metrics(self, report_generator: ReportGenerator):
        """Report should handle None values in optional metrics."""
        result = get_mock_backtest_result(num_trades=0, num_equity_points=5)
        # Modify metrics to have None values
        result.metrics = PerformanceMetrics(
            total_return=Decimal("0"),
            total_return_pct=Decimal("0"),
            sharpe_ratio=None,
            max_drawdown=Decimal("0"),
            max_drawdown_pct=Decimal("0"),
            win_rate=Decimal("0"),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_win=None,
            avg_loss=None,
            profit_factor=None,
        )

        report = report_generator.generate_json(result)
        html = report_generator.generate_html(result)

        # Should complete without error
        assert "sharpe_ratio" in report["metrics"]
        assert report["metrics"]["sharpe_ratio"] is None

        # HTML should handle None gracefully
        assert "N/A" in html or "None" not in html.replace("Assign", "")

    def test_handles_large_numbers(self, report_generator: ReportGenerator):
        """Report should handle large monetary values."""
        result = get_mock_backtest_result(num_trades=1, num_equity_points=2)
        result.equity_curve[0].equity = Decimal("1000000000")  # $1 billion

        report = report_generator.generate_json(result)
        html = report_generator.generate_html(result)

        assert report is not None
        assert html is not None

    def test_handles_negative_returns(self, report_generator: ReportGenerator):
        """Report should handle negative returns correctly."""
        result = get_mock_backtest_result(num_trades=1, num_equity_points=2)
        result.metrics = PerformanceMetrics(
            total_return=Decimal("-0.25"),
            total_return_pct=Decimal("-25.00"),
            sharpe_ratio=Decimal("-1.5"),
            max_drawdown=Decimal("-50000"),
            max_drawdown_pct=Decimal("-50.00"),
            win_rate=Decimal("0"),
            total_trades=5,
            winning_trades=0,
            losing_trades=5,
            avg_win=None,
            avg_loss=Decimal("-1000"),
            profit_factor=Decimal("0"),
        )

        report = report_generator.generate_json(result)
        html = report_generator.generate_html(result)

        assert "-25" in report["metrics"]["total_return_pct"]
        assert "negative" in html.lower() or "-" in html
