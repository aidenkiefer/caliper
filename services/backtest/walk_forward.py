"""
Walk-forward optimization engine.

Implements walk-forward analysis with optional parameter optimization:
1. Divide data into rolling/anchored windows
2. For each window: optimize parameters on in-sample, test on out-of-sample
3. Aggregate out-of-sample results for realistic performance estimate
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Callable, Type
from uuid import uuid4
import time

import numpy as np

from packages.common.schemas import PriceBar
from packages.strategies.base import Strategy

from .engine import BacktestEngine
from .models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    Trade,
    EquityPoint,
    WalkForwardConfig,
    WalkForwardResult,
    WalkForwardWindow,
    WalkForwardWindowResult,
    OptimizationResult,
    OptimizationObjective,
    WindowType,
    ParameterStability,
)


# Type alias for strategy factory function
StrategyFactory = Callable[[str, Dict[str, Any]], Strategy]


class WalkForwardEngine:
    """
    Walk-forward optimization engine.

    Performs walk-forward analysis by:
    1. Creating overlapping in-sample/out-of-sample windows
    2. Optionally optimizing parameters on each in-sample period
    3. Testing optimized parameters on out-of-sample period
    4. Aggregating all out-of-sample results for realistic performance

    Example:
        >>> engine = WalkForwardEngine()
        >>> wf_config = WalkForwardConfig(
        ...     in_sample_days=252,  # 1 year
        ...     out_of_sample_days=63,  # 3 months
        ...     step_days=63,
        ...     parameter_grid=ParameterGrid(parameters=[
        ...         ParameterRange(name='short_period', min_value=10, max_value=30, step=5),
        ...         ParameterRange(name='long_period', min_value=40, max_value=80, step=10),
        ...     ])
        ... )
        >>> result = engine.run(
        ...     strategy_factory=lambda id, cfg: SMACrossoverStrategy(id, cfg),
        ...     base_config={'position_size_pct': 0.1},
        ...     data=price_bars,
        ...     wf_config=wf_config,
        ...     backtest_config=BacktestConfig(initial_capital=Decimal('100000'))
        ... )
    """

    def __init__(self):
        """Initialize the walk-forward engine."""
        self.backtest_engine = BacktestEngine()

    def run(
        self,
        strategy_factory: StrategyFactory,
        base_config: Dict[str, Any],
        data: List[PriceBar],
        wf_config: WalkForwardConfig,
        backtest_config: BacktestConfig,
    ) -> WalkForwardResult:
        """
        Run walk-forward optimization.

        Args:
            strategy_factory: Function to create strategy instances
            base_config: Base strategy configuration (non-optimized params)
            data: Historical price bars (must be sorted by timestamp)
            wf_config: Walk-forward configuration
            backtest_config: Backtest configuration

        Returns:
            WalkForwardResult with per-window and aggregated results
        """
        if not data:
            raise ValueError("Data list cannot be empty")

        start_time = datetime.now(timezone.utc)
        windows = self._create_windows(data, wf_config)

        if not windows:
            raise ValueError("Not enough data for walk-forward analysis")

        window_results = []
        for window in windows:
            result = self._process_window(
                window=window,
                strategy_factory=strategy_factory,
                base_config=base_config,
                data=data,
                wf_config=wf_config,
                backtest_config=backtest_config,
            )
            if result:
                window_results.append(result)

        end_time = datetime.now(timezone.utc)

        return self._build_result(
            strategy_id=f"{strategy_factory.__name__}_wf",
            wf_config=wf_config,
            backtest_config=backtest_config,
            window_results=window_results,
            total_windows=len(windows),
            start_time=start_time,
            end_time=end_time,
        )

    def _create_windows(
        self, data: List[PriceBar], config: WalkForwardConfig
    ) -> List[WalkForwardWindow]:
        """Create walk-forward windows from data."""
        if not data:
            return []

        data_start = min(bar.timestamp for bar in data)
        data_end = max(bar.timestamp for bar in data)

        windows = []
        window_id = 0

        if config.window_type == WindowType.ANCHORED:
            current_in_sample_start = data_start
        else:
            current_in_sample_start = data_start

        while True:
            in_sample_end = current_in_sample_start + timedelta(days=config.in_sample_days)
            out_of_sample_start = in_sample_end
            out_of_sample_end = out_of_sample_start + timedelta(days=config.out_of_sample_days)

            if out_of_sample_end > data_end:
                break

            window = WalkForwardWindow(
                window_id=window_id,
                in_sample_start=current_in_sample_start,
                in_sample_end=in_sample_end,
                out_of_sample_start=out_of_sample_start,
                out_of_sample_end=out_of_sample_end,
            )
            windows.append(window)
            window_id += 1

            if config.window_type == WindowType.ANCHORED:
                current_in_sample_start = data_start
            else:
                current_in_sample_start += timedelta(days=config.step_days)

        return windows

    def _process_window(
        self,
        window: WalkForwardWindow,
        strategy_factory: StrategyFactory,
        base_config: Dict[str, Any],
        data: List[PriceBar],
        wf_config: WalkForwardConfig,
        backtest_config: BacktestConfig,
    ) -> Optional[WalkForwardWindowResult]:
        """Process a single walk-forward window."""
        in_sample_data = self._filter_data(data, window.in_sample_start, window.in_sample_end)
        out_of_sample_data = self._filter_data(
            data, window.out_of_sample_start, window.out_of_sample_end
        )

        if not in_sample_data or not out_of_sample_data:
            return None

        optimization_result = None
        best_params = base_config.copy()

        if wf_config.parameter_grid:
            optimization_result = self._optimize_parameters(
                window=window,
                strategy_factory=strategy_factory,
                base_config=base_config,
                data=in_sample_data,
                wf_config=wf_config,
                backtest_config=backtest_config,
            )
            if optimization_result:
                best_params = {**base_config, **optimization_result.best_params}

        in_sample_result = self._run_backtest(
            strategy_factory=strategy_factory,
            config=best_params,
            data=in_sample_data,
            backtest_config=backtest_config,
            strategy_id=f"window_{window.window_id}_in_sample",
        )

        out_of_sample_result = self._run_backtest(
            strategy_factory=strategy_factory,
            config=best_params,
            data=out_of_sample_data,
            backtest_config=backtest_config,
            strategy_id=f"window_{window.window_id}_out_of_sample",
        )

        if not in_sample_result or not out_of_sample_result:
            return None

        return WalkForwardWindowResult(
            window=window,
            optimization_result=optimization_result,
            in_sample_result=in_sample_result,
            out_of_sample_result=out_of_sample_result,
            params_used=best_params,
        )

    def _filter_data(self, data: List[PriceBar], start: datetime, end: datetime) -> List[PriceBar]:
        """Filter data to a date range."""
        return [bar for bar in data if start <= bar.timestamp <= end]

    def _optimize_parameters(
        self,
        window: WalkForwardWindow,
        strategy_factory: StrategyFactory,
        base_config: Dict[str, Any],
        data: List[PriceBar],
        wf_config: WalkForwardConfig,
        backtest_config: BacktestConfig,
    ) -> Optional[OptimizationResult]:
        """Optimize parameters on in-sample data."""
        if not wf_config.parameter_grid:
            return None

        start_time = time.time()
        combinations = wf_config.parameter_grid.get_combinations()

        all_results = []
        best_params = None
        best_value = None

        for params in combinations:
            merged_config = {**base_config, **params}

            result = self._run_backtest(
                strategy_factory=strategy_factory,
                config=merged_config,
                data=data,
                backtest_config=backtest_config,
                strategy_id=f"opt_window_{window.window_id}",
            )

            if not result:
                continue

            if result.metrics.total_trades < wf_config.min_trades_required:
                continue

            objective_value = self._get_objective_value(result.metrics, wf_config.objective)

            all_results.append(
                {
                    "params": params,
                    "objective_value": float(objective_value) if objective_value else None,
                    "total_return": float(result.metrics.total_return_pct),
                    "sharpe_ratio": float(result.metrics.sharpe_ratio)
                    if result.metrics.sharpe_ratio
                    else None,
                    "total_trades": result.metrics.total_trades,
                }
            )

            if objective_value is not None:
                if best_value is None or self._is_better(
                    objective_value, best_value, wf_config.objective
                ):
                    best_value = objective_value
                    best_params = params

        if best_params is None:
            return None

        optimization_time = time.time() - start_time

        return OptimizationResult(
            window_id=window.window_id,
            best_params=best_params,
            best_objective_value=Decimal(str(best_value)),
            all_results=all_results,
            optimization_time_seconds=optimization_time,
        )

    def _get_objective_value(
        self, metrics: PerformanceMetrics, objective: OptimizationObjective
    ) -> Optional[Decimal]:
        """Extract objective value from metrics."""
        if objective == OptimizationObjective.SHARPE_RATIO:
            return metrics.sharpe_ratio
        elif objective == OptimizationObjective.TOTAL_RETURN:
            return metrics.total_return
        elif objective == OptimizationObjective.PROFIT_FACTOR:
            return metrics.profit_factor
        elif objective == OptimizationObjective.WIN_RATE:
            return metrics.win_rate
        elif objective == OptimizationObjective.MAX_DRAWDOWN:
            return metrics.max_drawdown
        return None

    def _is_better(
        self, new_value: Decimal, old_value: Decimal, objective: OptimizationObjective
    ) -> bool:
        """Check if new value is better than old value."""
        if objective == OptimizationObjective.MAX_DRAWDOWN:
            return new_value > old_value
        return new_value > old_value

    def _run_backtest(
        self,
        strategy_factory: StrategyFactory,
        config: Dict[str, Any],
        data: List[PriceBar],
        backtest_config: BacktestConfig,
        strategy_id: str,
    ) -> Optional[BacktestResult]:
        """Run a single backtest."""
        try:
            strategy = strategy_factory(strategy_id, config)
            return self.backtest_engine.run(strategy, data, backtest_config)
        except Exception:
            return None

    def _build_result(
        self,
        strategy_id: str,
        wf_config: WalkForwardConfig,
        backtest_config: BacktestConfig,
        window_results: List[WalkForwardWindowResult],
        total_windows: int,
        start_time: datetime,
        end_time: datetime,
    ) -> WalkForwardResult:
        """Build the final walk-forward result."""
        aggregated_trades = self._aggregate_trades(window_results)
        aggregated_equity = self._aggregate_equity_curves(
            window_results, backtest_config.initial_capital
        )
        aggregated_metrics = self._calculate_aggregated_metrics(
            aggregated_trades,
            aggregated_equity,
            backtest_config.initial_capital,
        )
        parameter_stability = self._analyze_parameter_stability(window_results)

        return WalkForwardResult(
            strategy_id=strategy_id,
            config=wf_config,
            backtest_config=backtest_config,
            windows=window_results,
            aggregated_metrics=aggregated_metrics,
            aggregated_trades=aggregated_trades,
            aggregated_equity_curve=aggregated_equity,
            parameter_stability=parameter_stability,
            total_windows=total_windows,
            successful_windows=len(window_results),
            start_time=start_time,
            end_time=end_time,
        )

    def _aggregate_trades(self, window_results: List[WalkForwardWindowResult]) -> List[Trade]:
        """Aggregate all out-of-sample trades."""
        all_trades = []
        for result in window_results:
            all_trades.extend(result.out_of_sample_result.trades)
        return sorted(all_trades, key=lambda t: t.entry_time)

    def _aggregate_equity_curves(
        self, window_results: List[WalkForwardWindowResult], initial_capital: Decimal
    ) -> List[EquityPoint]:
        """Aggregate out-of-sample equity curves into continuous curve."""
        if not window_results:
            return []

        all_points = []
        cumulative_return = Decimal("1")

        for result in sorted(window_results, key=lambda r: r.window.out_of_sample_start):
            oos_curve = result.out_of_sample_result.equity_curve
            if not oos_curve:
                continue

            window_initial = oos_curve[0].equity if oos_curve else initial_capital

            for point in oos_curve:
                if window_initial > 0:
                    window_return = point.equity / window_initial
                    adjusted_equity = initial_capital * cumulative_return * window_return
                else:
                    adjusted_equity = point.equity

                all_points.append(
                    EquityPoint(
                        timestamp=point.timestamp,
                        equity=adjusted_equity,
                        cash=point.cash,
                        unrealized_pnl=point.unrealized_pnl,
                    )
                )

            if oos_curve and window_initial > 0:
                final_return = oos_curve[-1].equity / window_initial
                cumulative_return *= final_return

        return all_points

    def _calculate_aggregated_metrics(
        self, trades: List[Trade], equity_curve: List[EquityPoint], initial_capital: Decimal
    ) -> PerformanceMetrics:
        """Calculate aggregated performance metrics."""
        if not equity_curve:
            return self._empty_metrics()

        final_equity = equity_curve[-1].equity if equity_curve else initial_capital
        total_return = (final_equity - initial_capital) / initial_capital
        total_return_pct = total_return * Decimal("100")

        max_drawdown = self._calculate_max_drawdown(equity_curve, initial_capital)
        sharpe = self._calculate_sharpe_ratio(equity_curve)
        (
            win_rate,
            winning_trades,
            losing_trades,
            avg_win,
            avg_loss,
            profit_factor,
        ) = self._calculate_trade_stats(trades)

        return PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown / initial_capital * Decimal("100")
            if initial_capital
            else Decimal("0"),
            win_rate=win_rate,
            total_trades=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
        )

    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics."""
        return PerformanceMetrics(
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

    def _calculate_max_drawdown(
        self, equity_curve: List[EquityPoint], initial_capital: Decimal
    ) -> Decimal:
        """Calculate maximum drawdown."""
        if not equity_curve:
            return Decimal("0")

        peak = initial_capital
        max_dd = Decimal("0")

        for point in equity_curve:
            if point.equity > peak:
                peak = point.equity
            drawdown = point.equity - peak
            if drawdown < max_dd:
                max_dd = drawdown

        return max_dd

    def _calculate_sharpe_ratio(self, equity_curve: List[EquityPoint]) -> Optional[Decimal]:
        """Calculate annualized Sharpe ratio."""
        if len(equity_curve) < 2:
            return None

        returns = []
        for i in range(1, len(equity_curve)):
            prev_equity = equity_curve[i - 1].equity
            curr_equity = equity_curve[i].equity
            if prev_equity > 0:
                daily_return = (curr_equity - prev_equity) / prev_equity
                returns.append(float(daily_return))

        if not returns or len(returns) < 2:
            return None

        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)

        if std_return == 0:
            return None

        sharpe = Decimal(str(mean_return / std_return * np.sqrt(252)))
        return sharpe

    def _calculate_trade_stats(self, trades: List[Trade]) -> tuple:
        """Calculate trade statistics."""
        if not trades:
            return Decimal("0"), 0, 0, None, None, None

        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]

        win_rate = Decimal(len(winning_trades)) / Decimal(len(trades))

        avg_win = (
            Decimal(str(np.mean([float(t.pnl) for t in winning_trades])))
            if winning_trades
            else None
        )

        avg_loss = (
            Decimal(str(np.mean([float(t.pnl) for t in losing_trades]))) if losing_trades else None
        )

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

        return win_rate, len(winning_trades), len(losing_trades), avg_win, avg_loss, profit_factor

    def _analyze_parameter_stability(
        self, window_results: List[WalkForwardWindowResult]
    ) -> List[ParameterStability]:
        """Analyze parameter stability across windows."""
        if not window_results:
            return []

        first_params = window_results[0].params_used
        param_names = list(first_params.keys())
        stability_results = []

        for param_name in param_names:
            values = []
            for result in window_results:
                if param_name in result.params_used:
                    val = result.params_used[param_name]
                    if isinstance(val, (int, float, Decimal)):
                        values.append(float(val))

            if not values:
                continue

            mean_val = np.mean(values)
            std_val = np.std(values)

            if mean_val != 0:
                cv = std_val / abs(mean_val)
                stability_score = max(0, 1 - cv)
            else:
                stability_score = 1.0 if std_val == 0 else 0.0

            stability_results.append(
                ParameterStability(
                    parameter_name=param_name,
                    values_used=values,
                    mean_value=mean_val,
                    std_value=std_val,
                    stability_score=Decimal(str(min(1.0, max(0.0, stability_score)))),
                )
            )

        return stability_results
