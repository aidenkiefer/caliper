# 5. Backtest Engine Design

date: 2026-01-26
updated: 2026-01-26
status: accepted

## Context

Sprint 3 required implementing a backtesting engine to simulate trading strategies on historical data. The architecture document (`docs/architecture.md`) suggested using either **Backtrader** or **vectorbt** as the backtesting library.

We needed to decide:
1. Which library to use (Backtrader vs vectorbt vs custom)
2. How to integrate with our existing Strategy interface
3. How to generate reports

**Requirements:**
- Execute strategies implementing `packages/strategies/base.py` interface
- Calculate P&L with realistic commission and slippage
- Generate performance metrics (Sharpe, drawdown, win rate, etc.)
- Produce JSON and HTML reports
- Support configuration via Pydantic models

## Decision

We chose to implement a **Custom Lightweight Backtest Engine** instead of using Backtrader or vectorbt.

**Implementation:**
- `services/backtest/engine.py` - Core `BacktestEngine` class
- `services/backtest/walk_forward.py` - `WalkForwardEngine` class (added Sprint 3)
- `services/backtest/models.py` - Pydantic models for config and results
- `services/backtest/report.py` - `ReportGenerator` with JSON and HTML output

## Rationale

### Why Not Backtrader?

1. **Interface Mismatch**: Backtrader has its own `Strategy` base class with different method signatures (`__init__`, `next`, `notify_order`). Integrating with our existing `Strategy` interface would require an adapter layer.

2. **Complexity**: Backtrader is designed for advanced features (multiple data feeds, complex order types, cerebro orchestration) that we don't need for v1.

3. **Learning Curve**: Team would need to learn Backtrader's paradigms (lines, indicators, data feeds) which are different from our existing patterns.

4. **Dependency Weight**: Backtrader brings significant dependencies and complexity.

### Why Not vectorbt?

1. **Vectorized Paradigm**: vectorbt is optimized for vectorized backtesting (NumPy arrays), not event-driven strategies. Our Strategy interface is event-driven (`on_market_data`, `generate_signals`).

2. **Different Signal Model**: vectorbt expects signals as arrays, not incremental signal generation.

3. **Overkill for v1**: vectorbt's strength is rapid parameter optimization and Monte Carlo simulation - features not needed yet.

### Why Custom Implementation?

1. **Direct Integration**: Works directly with our `Strategy` interface - no adapters needed.

2. **Simplicity**: ~500 lines of code, easy to understand and debug.

3. **Control**: Full control over fill simulation, slippage model, P&L calculation.

4. **Pydantic Native**: Uses Pydantic for all models, consistent with rest of codebase.

5. **Iterative Enhancement**: Can add features (multi-symbol, limit orders, walk-forward) incrementally without fighting library constraints.

6. **Testability**: Simple class structure is easy to unit test.

## Consequences

### Positive

- **Seamless Integration**: Strategy interface works without modification
- **Maintainability**: Small codebase, easy to understand and modify
- **Type Safety**: Full Pydantic/typing support throughout
- **Performance**: Sufficient for daily bars on single symbols (our current use case)
- **Report Quality**: Plotly-based HTML reports with interactive charts

### Negative

- **Feature Gap**: Missing some advanced features available in mature libraries:
  - Multi-asset portfolio backtesting
  - Limit/stop order simulation
  - ~~Walk-forward optimization~~ ✅ **Implemented** (see Update below)
  - Monte Carlo simulation
  - Advanced slippage models

- **Maintenance Burden**: We own all the code, including edge cases and bugs

- **Reinventing Wheel**: Some code duplicates functionality available in libraries

### Neutral

- **Performance**: Adequate for current use case, but may need optimization for minute-level data or large universes

## Alternatives Considered

### 1. Backtrader with Adapter
- **Approach**: Create adapter to wrap our Strategy in Backtrader's interface
- **Rejected Because**: Adds complexity, Backtrader's paradigm doesn't align well

### 2. vectorbt for Signal-Based Testing
- **Approach**: Convert strategies to produce signal arrays for vectorbt
- **Rejected Because**: Would require rewriting strategy interface, loses event-driven benefits

### 3. zipline (Quantopian's engine)
- **Approach**: Use zipline's event-driven backtester
- **Rejected Because**: Complex setup, designed for Quantopian's ecosystem, maintenance concerns since Quantopian shutdown

### 4. Hybrid Approach (Custom now, Library later)
- **Approach**: Start custom, migrate to library when needed
- **Selected**: This is effectively our approach - custom v1, can migrate if requirements grow

## Future Considerations

When these requirements emerge, consider migrating to a library:

1. **Multi-symbol portfolios** with position sizing across assets
2. **Sub-daily backtesting** requiring high performance
3. ~~**Walk-forward optimization** with parameter sweeps~~ ✅ **Implemented**
4. **Monte Carlo simulation** for robustness testing
5. **Advanced order types** (limit, stop, bracket orders)

At that point, **vectorbt** would be the likely choice for vectorized operations, or a custom enhancement of the current engine.

## Update: Walk-Forward Optimization Added (2026-01-26)

Walk-forward optimization was implemented as part of Sprint 3, validating the "iterative enhancement" approach.

**New Components:**
- `services/backtest/walk_forward.py` - `WalkForwardEngine` class (~600 lines)
- Additional models in `services/backtest/models.py`:
  - `WalkForwardConfig`, `WalkForwardResult`
  - `ParameterGrid`, `ParameterRange`
  - `OptimizationObjective`, `WindowType`
  - `ParameterStability` for stability analysis

**Features:**
- Rolling and anchored window types
- Grid search parameter optimization
- Multiple optimization objectives (Sharpe, returns, profit factor, win rate, drawdown)
- Parameter stability analysis across windows
- Aggregated out-of-sample metrics

**This validates the custom implementation approach** - walk-forward was added incrementally without requiring migration to a library. The custom engine's simple structure made this enhancement straightforward.

## Related Decisions

- ADR-0001: Monorepo Organization (services structure)
- ADR-0003: FastAPI Backend (Pydantic model patterns)
- `packages/strategies/base.py`: Strategy interface design
