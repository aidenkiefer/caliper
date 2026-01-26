"""
Backtesting service for quantitative trading strategies.

This service provides:
- BacktestEngine: Execute strategies on historical data
- WalkForwardEngine: Walk-forward optimization with parameter optimization
- ReportGenerator: Generate JSON and HTML reports
- Performance metrics calculation (Sharpe, drawdown, win rate)
"""

from .engine import BacktestEngine
from .models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    Trade,
    EquityPoint,
    # Walk-forward models
    WalkForwardConfig,
    WalkForwardResult,
    WalkForwardWindow,
    WalkForwardWindowResult,
    ParameterGrid,
    ParameterRange,
    OptimizationObjective,
    WindowType,
    OptimizationResult,
    ParameterStability,
)
from .report import ReportGenerator
from .walk_forward import WalkForwardEngine

__all__ = [
    # Core backtest
    'BacktestEngine',
    'BacktestConfig',
    'BacktestResult',
    'PerformanceMetrics',
    'Trade',
    'EquityPoint',
    'ReportGenerator',
    # Walk-forward optimization
    'WalkForwardEngine',
    'WalkForwardConfig',
    'WalkForwardResult',
    'WalkForwardWindow',
    'WalkForwardWindowResult',
    'ParameterGrid',
    'ParameterRange',
    'OptimizationObjective',
    'WindowType',
    'OptimizationResult',
    'ParameterStability',
]
