"""
Report generation for backtest results.

Generates both JSON (machine-readable) and HTML (human-readable) reports.
"""

from typing import Dict, Any
import json
from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .models import BacktestResult


class ReportGenerator:
    """Generate reports from backtest results."""
    
    def generate_json(self, result: BacktestResult) -> Dict[str, Any]:
        """
        Generate JSON report (machine-readable).
        
        Args:
            result: Backtest result to generate report from
            
        Returns:
            Dictionary with all backtest data
        """
        return {
            'backtest_id': str(result.backtest_id),
            'strategy_id': result.strategy_id,
            'start_time': result.start_time.isoformat(),
            'end_time': result.end_time.isoformat(),
            'config': {
                'initial_capital': str(result.config.initial_capital),
                'commission_per_trade': str(result.config.commission_per_trade),
                'slippage_bps': str(result.config.slippage_bps),
            },
            'metrics': {
                'total_return': str(result.metrics.total_return),
                'total_return_pct': str(result.metrics.total_return_pct),
                'sharpe_ratio': str(result.metrics.sharpe_ratio) if result.metrics.sharpe_ratio else None,
                'max_drawdown': str(result.metrics.max_drawdown),
                'max_drawdown_pct': str(result.metrics.max_drawdown_pct),
                'win_rate': str(result.metrics.win_rate),
                'total_trades': result.metrics.total_trades,
                'winning_trades': result.metrics.winning_trades,
                'losing_trades': result.metrics.losing_trades,
                'avg_win': str(result.metrics.avg_win) if result.metrics.avg_win else None,
                'avg_loss': str(result.metrics.avg_loss) if result.metrics.avg_loss else None,
                'profit_factor': str(result.metrics.profit_factor) if result.metrics.profit_factor else None,
            },
            'trades': [
                {
                    'trade_id': str(trade.trade_id),
                    'symbol': trade.symbol,
                    'entry_time': trade.entry_time.isoformat(),
                    'exit_time': trade.exit_time.isoformat(),
                    'entry_price': str(trade.entry_price),
                    'exit_price': str(trade.exit_price),
                    'quantity': str(trade.quantity),
                    'commission': str(trade.commission),
                    'pnl': str(trade.pnl),
                    'return_pct': str(trade.return_pct),
                }
                for trade in result.trades
            ],
            'equity_curve': [
                {
                    'timestamp': point.timestamp.isoformat(),
                    'equity': str(point.equity),
                    'cash': str(point.cash),
                    'unrealized_pnl': str(point.unrealized_pnl),
                }
                for point in result.equity_curve
            ],
            'metadata': result.metadata,
        }
    
    def generate_html(self, result: BacktestResult) -> str:
        """
        Generate HTML report (human-readable with charts).
        
        Args:
            result: Backtest result to generate report from
            
        Returns:
            HTML string with embedded charts
        """
        equity_chart = self._create_equity_chart(result)
        trades_table = self._create_trades_table(result)
        metrics_summary = self._create_metrics_summary(result)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Backtest Report - {result.strategy_id}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .section {{
            background-color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .metric-card {{
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }}
        .metric-label {{
            font-size: 12px;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .positive {{
            color: #27ae60;
        }}
        .negative {{
            color: #e74c3c;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #34495e;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Backtest Report</h1>
        <p><strong>Strategy:</strong> {result.strategy_id}</p>
        <p><strong>Period:</strong> {result.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} to {result.end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    
    <div class="section">
        <h2>Performance Metrics</h2>
        {metrics_summary}
    </div>
    
    <div class="section">
        <h2>Equity Curve</h2>
        <div id="equity-chart"></div>
    </div>
    
    <div class="section">
        <h2>Trades ({len(result.trades)} total)</h2>
        {trades_table}
    </div>
    
    <script>
        {equity_chart}
    </script>
</body>
</html>
"""
        return html
    
    def _create_equity_chart(self, result: BacktestResult) -> str:
        """Create Plotly equity curve chart."""
        timestamps = [point.timestamp for point in result.equity_curve]
        equity_values = [float(point.equity) for point in result.equity_curve]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=equity_values,
            mode='lines',
            name='Equity',
            line=dict(color='#3498db', width=2)
        ))
        
        fig.update_layout(
            title='Equity Curve',
            xaxis_title='Date',
            yaxis_title='Equity ($)',
            hovermode='x unified',
            height=400,
        )
        
        return f"Plotly.newPlot('equity-chart', {fig.to_json()});"
    
    def _create_trades_table(self, result: BacktestResult) -> str:
        """Create HTML table of trades."""
        if not result.trades:
            return "<p>No trades executed during this backtest.</p>"
        
        rows = []
        for trade in result.trades:
            pnl_class = "positive" if trade.pnl > 0 else "negative"
            rows.append(f"""
                <tr>
                    <td>{trade.symbol}</td>
                    <td>{trade.entry_time.strftime('%Y-%m-%d %H:%M')}</td>
                    <td>{trade.exit_time.strftime('%Y-%m-%d %H:%M')}</td>
                    <td>${float(trade.entry_price):.2f}</td>
                    <td>${float(trade.exit_price):.2f}</td>
                    <td>{float(trade.quantity):.2f}</td>
                    <td class="{pnl_class}">${float(trade.pnl):.2f}</td>
                    <td class="{pnl_class}">{float(trade.return_pct):.2f}%</td>
                </tr>
            """)
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Entry Time</th>
                    <th>Exit Time</th>
                    <th>Entry Price</th>
                    <th>Exit Price</th>
                    <th>Quantity</th>
                    <th>P&L</th>
                    <th>Return %</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _create_metrics_summary(self, result: BacktestResult) -> str:
        """Create HTML summary of performance metrics."""
        metrics = result.metrics
        
        def format_metric(label: str, value: Any, is_percent: bool = False, is_positive: bool = False) -> str:
            """Format a single metric card."""
            if value is None:
                value_str = "N/A"
            elif is_percent:
                value_str = f"{float(value):.2f}%"
            else:
                value_str = f"{float(value):.2f}"
            
            value_class = ""
            if is_positive and value is not None:
                value_class = "positive" if float(value) > 0 else "negative"
            
            return f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value {value_class}">{value_str}</div>
                </div>
            """
        
        return f"""
        <div class="metrics-grid">
            {format_metric('Total Return', metrics.total_return_pct, is_percent=True, is_positive=True)}
            {format_metric('Sharpe Ratio', metrics.sharpe_ratio, is_positive=True)}
            {format_metric('Max Drawdown', metrics.max_drawdown_pct, is_percent=True)}
            {format_metric('Win Rate', metrics.win_rate * 100, is_percent=True, is_positive=True)}
            {format_metric('Total Trades', metrics.total_trades)}
            {format_metric('Winning Trades', metrics.winning_trades)}
            {format_metric('Losing Trades', metrics.losing_trades)}
            {format_metric('Avg Win', metrics.avg_win, is_positive=True)}
            {format_metric('Avg Loss', metrics.avg_loss)}
            {format_metric('Profit Factor', metrics.profit_factor, is_positive=True)}
        </div>
        """
