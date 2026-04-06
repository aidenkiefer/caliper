# Unified Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the Equities and Polymarket execution paths under a single signal → portfolio → execution → risk pipeline so that any strategy (directional, market-making, ML-hybrid) can be added without touching service internals.

**Architecture:** Introduce a `MarketType`-aware `Signal` schema and universal `Strategy` ABC; add a `services/portfolio/` allocator that sits between signals and execution; refactor `services/execution/` around a broker-agnostic `ExecutionAdapter`; extract Polymarket quoting logic into `packages/strategies/`; and upgrade `services/risk/` to a `GlobalRiskManager` that handles both equity and prediction-market constraints.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, Poetry monorepo. No new external dependencies.

---

## Scope and file map

This refactor touches 6 subsystems in strict dependency order. Each task is independently testable and non-breaking within its own boundary. Downstream tasks import the interfaces defined by upstream tasks — follow the order.

| Task | Subsystem | Creates | Modifies |
|------|-----------|---------|----------|
| 1 | Shared schemas | `packages/common/market_schemas.py` | — |
| 2 | Strategy interface | — | `packages/strategies/base.py` |
| 3 | Portfolio allocator | `services/portfolio/__init__.py`, `services/portfolio/allocator.py`, `services/portfolio/sizing.py` | — |
| 4 | Execution adapters | `services/execution/adapter.py`, `services/execution/adapters/alpaca_adapter.py`, `services/execution/adapters/polymarket_adapter.py` | `services/execution/broker/base.py` |
| 5 | Polymarket strategy | `packages/strategies/polymarket_mm_strategy.py` | `services/polymarket/session.py` |
| 6 | Global risk manager | `services/risk/global_risk_manager.py` | `services/risk/limits.py` |

**Preserve (do not touch):**
- `services/ml/` — drift, gating, explainability, baselines, HITL
- `packages/common/schemas.py`, `polymarket_schemas.py`, `ml_schemas.py` — existing contracts
- `services/data/` — migrations and DB schema
- `services/polymarket/adapters/` — CLOB/Gamma/Binance clients stay as-is
- `docs/` structure

---

## Task 1 — Market-aware Signal and MarketType schemas

**Purpose:** Add the shared types (`MarketType`, `SignalType`, unified `Signal`) that every later task depends on. Lives in a new module to avoid breaking any existing import of `packages/common/schemas.py`.

**Files:**
- Create: `packages/common/market_schemas.py`
- Create: `tests/unit/common/test_market_schemas.py`

---

- [ ] **Step 1.1 — Write the failing tests**

```python
# tests/unit/common/test_market_schemas.py
from decimal import Decimal
import pytest
from packages.common.market_schemas import (
    MarketType,
    SignalType,
    UnifiedSignal,
)


def test_market_type_values():
    assert MarketType.EQUITY == "EQUITY"
    assert MarketType.PREDICTION == "PREDICTION"
    assert MarketType.CRYPTO == "CRYPTO"


def test_signal_type_values():
    assert SignalType.DIRECTIONAL == "DIRECTIONAL"
    assert SignalType.MARKET_MAKING == "MARKET_MAKING"
    assert SignalType.HYBRID == "HYBRID"


def test_unified_signal_directional():
    s = UnifiedSignal(
        asset_id="AAPL",
        market_type=MarketType.EQUITY,
        signal_type=SignalType.DIRECTIONAL,
        direction="long",
        confidence=Decimal("0.75"),
        horizon_seconds=3600,
        strategy_id="sma_v1",
    )
    assert s.asset_id == "AAPL"
    assert s.confidence == Decimal("0.75")
    assert s.metadata == {}


def test_unified_signal_market_making():
    s = UnifiedSignal(
        asset_id="BTC-UP-2026-04-04T15",
        market_type=MarketType.PREDICTION,
        signal_type=SignalType.MARKET_MAKING,
        direction="none",
        confidence=Decimal("1.0"),
        horizon_seconds=3600,
        strategy_id="polymarket_mm_v1",
        metadata={"quote_spread": "0.02", "inventory_yes": "50"},
    )
    assert s.signal_type == SignalType.MARKET_MAKING
    assert s.metadata["quote_spread"] == "0.02"


def test_unified_signal_confidence_validation():
    with pytest.raises(Exception):
        UnifiedSignal(
            asset_id="AAPL",
            market_type=MarketType.EQUITY,
            signal_type=SignalType.DIRECTIONAL,
            direction="long",
            confidence=Decimal("1.5"),  # out of range
            horizon_seconds=3600,
            strategy_id="sma_v1",
        )


def test_unified_signal_direction_validation():
    with pytest.raises(Exception):
        UnifiedSignal(
            asset_id="AAPL",
            market_type=MarketType.EQUITY,
            signal_type=SignalType.DIRECTIONAL,
            direction="sideways",  # invalid
            confidence=Decimal("0.6"),
            horizon_seconds=3600,
            strategy_id="sma_v1",
        )
```

- [ ] **Step 1.2 — Run tests to confirm they fail**

```bash
cd /path/to/quant
poetry run pytest tests/unit/common/test_market_schemas.py -v
# Expected: ImportError — packages.common.market_schemas does not exist
```

- [ ] **Step 1.3 — Implement `packages/common/market_schemas.py`**

```python
"""
Market-type-aware signal schemas shared across all strategies.

These extend (not replace) the existing packages/common/schemas.py.
Import from here when building new strategies or the portfolio allocator.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class MarketType(str, Enum):
    """Supported market surfaces."""

    EQUITY = "EQUITY"
    PREDICTION = "PREDICTION"
    CRYPTO = "CRYPTO"


class SignalType(str, Enum):
    """Classification of what a signal instructs execution to do."""

    DIRECTIONAL = "DIRECTIONAL"    # take / exit a position
    MARKET_MAKING = "MARKET_MAKING"  # post two-sided quotes
    HYBRID = "HYBRID"              # directional + quote skew combined


class UnifiedSignal(BaseModel):
    """
    Universal signal emitted by any strategy, for any market.

    The portfolio allocator and risk layer consume this; downstream
    execution adapters translate it into market-specific orders.
    """

    signal_id: UUID = Field(default_factory=uuid4)
    strategy_id: str = Field(..., description="ID of the emitting strategy")

    # What and where
    asset_id: str = Field(
        ...,
        description="Symbol (equities) or market condition ID (prediction)",
    )
    market_type: MarketType = Field(..., description="Market surface")
    signal_type: SignalType = Field(..., description="Execution intent")

    # Direction: 'long', 'short', or 'none' (for pure MM signals)
    direction: Literal["long", "short", "none"] = Field(
        ..., description="Directional intent"
    )

    # Confidence 0–1 (used by confidence gating)
    confidence: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Model/rule confidence 0–1",
    )

    # How long is this signal valid?
    horizon_seconds: int = Field(
        ..., gt=0, description="Expected signal validity in seconds"
    )

    # Strategy-specific extras (spread params, model outputs, etc.)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy-specific payload (not interpreted by allocator)",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 1.4 — Run tests to confirm they pass**

```bash
poetry run pytest tests/unit/common/test_market_schemas.py -v
# Expected: 5 passed
```

- [ ] **Step 1.5 — Commit**

```bash
git add packages/common/market_schemas.py tests/unit/common/test_market_schemas.py
git commit -m "feat: add MarketType, SignalType, UnifiedSignal to packages/common/market_schemas"
```

---

## Task 2 — Refactor Strategy base to emit UnifiedSignal

**Purpose:** Make `Strategy` ABC emit `UnifiedSignal` instead of the equity-only `Signal`. Existing strategies (`SMAcrossover`, `MLDirectionStrategyV1`) must continue to work — update them to wrap their current output.

**Current issue:** `generate_signals()` returns `List[Signal]` (equity-only; `Signal.side` is `BUY/SELL/ABSTAIN`). `risk_check()` is also on the strategy, causing strategies to bypass the global risk layer.

**Design decision:** Keep `risk_check()` on strategies for now as a *strategy-level* guard (position sizing, strategy-specific rules). The new `GlobalRiskManager` (Task 6) adds a second, portfolio-level layer that all trades pass through. This avoids a big-bang rewrite.

**Files:**
- Modify: `packages/strategies/base.py`
- Modify: `packages/strategies/sma_crossover.py` (adapt `generate_signals`)
- Modify: `packages/strategies/ml_direction_v1.py` (adapt `generate_signals`)
- Create: `tests/unit/strategies/test_base_unified_signal.py`

---

- [ ] **Step 2.1 — Write the failing tests**

```python
# tests/unit/strategies/test_base_unified_signal.py
from decimal import Decimal
import pytest
from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from packages.common.schemas import TradingMode, PriceBar
from packages.strategies.base import Strategy, PortfolioState
from datetime import datetime, timezone


class MinimalStrategy(Strategy):
    """Concrete strategy for testing the base class contract."""

    def initialize(self, mode: TradingMode) -> None:
        self.initialized = True
        self.mode = mode

    def on_market_data(self, bar: PriceBar) -> None:
        pass

    def generate_signals(self, portfolio: PortfolioState):
        return [
            UnifiedSignal(
                asset_id="AAPL",
                market_type=MarketType.EQUITY,
                signal_type=SignalType.DIRECTIONAL,
                direction="long",
                confidence=Decimal("0.8"),
                horizon_seconds=3600,
                strategy_id=self.strategy_id,
            )
        ]

    def risk_check(self, signals, portfolio):
        return []


def test_strategy_generate_signals_returns_unified_signal():
    s = MinimalStrategy("test_strategy", {})
    s.initialize(TradingMode.PAPER)
    bar = PriceBar(
        symbol="AAPL",
        timestamp=datetime.now(timezone.utc),
        open=Decimal("150"),
        high=Decimal("152"),
        low=Decimal("149"),
        close=Decimal("151"),
        volume=1000,
    )
    s.on_market_data(bar)
    portfolio = PortfolioState(
        equity=Decimal("100000"),
        cash=Decimal("100000"),
        positions=[],
    )
    signals = s.generate_signals(portfolio)
    assert len(signals) == 1
    assert isinstance(signals[0], UnifiedSignal)
    assert signals[0].strategy_id == "test_strategy"
    assert signals[0].market_type == MarketType.EQUITY


def test_strategy_market_type_declared():
    s = MinimalStrategy("test_strategy", {})
    # market_type is declared by subclass; MinimalStrategy should define it
    # This test will fail until the base class mandates market_type
    assert hasattr(s, "market_type")
```

- [ ] **Step 2.2 — Run to confirm failure**

```bash
poetry run pytest tests/unit/strategies/test_base_unified_signal.py -v
# Expected: FAIL — generate_signals returns old Signal type; no market_type attr
```

- [ ] **Step 2.3 — Update `packages/strategies/base.py`**

Replace the `Signal` class and update the `Strategy` ABC. Keep `PortfolioState` and `on_fill`/`daily_close` unchanged — only the signal interface changes.

```python
"""
Base strategy interface and abstract classes.

All trading strategies must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from packages.common.schemas import Order, Position, TradingMode
from packages.common.market_schemas import MarketType, UnifiedSignal


class PortfolioState:
    """Current portfolio state passed to strategies each cycle."""

    def __init__(
        self,
        equity: Decimal,
        cash: Decimal,
        positions: List[Position],
        unrealized_pnl: Decimal = Decimal(0),
    ):
        self.equity = equity
        self.cash = cash
        self.positions = positions
        self.unrealized_pnl = unrealized_pnl


class Strategy(ABC):
    """
    Abstract base class for all trading strategies (equity, prediction, hybrid).

    generate_signals() now returns List[UnifiedSignal] so the portfolio
    allocator and global risk manager can process any strategy uniformly.
    """

    # Subclasses MUST declare the market surface they operate on.
    market_type: MarketType

    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.config = config
        self.initialized = False
        self.mode: Optional[TradingMode] = None

    @abstractmethod
    def initialize(self, mode: TradingMode) -> None:
        """Called once before the strategy starts processing data."""
        pass

    @abstractmethod
    def on_market_data(self, bar) -> None:
        """
        Process incoming market data.

        `bar` type is intentionally untyped here so strategies can accept
        PriceBar (equity) or OrderbookState (prediction) depending on
        their market_type.
        """
        pass

    @abstractmethod
    def generate_signals(self, portfolio: PortfolioState) -> List[UnifiedSignal]:
        """
        Generate UnifiedSignal objects for the portfolio allocator.

        Every signal must carry strategy_id, market_type, signal_type,
        direction, confidence, and horizon_seconds.
        """
        pass

    @abstractmethod
    def risk_check(
        self, signals: List[UnifiedSignal], portfolio: PortfolioState
    ) -> List[Order]:
        """
        Strategy-level guard: filter/size signals into Orders.

        The GlobalRiskManager (services/risk/global_risk_manager.py) applies
        a second, portfolio-wide check after this method. This layer handles
        strategy-specific constraints only.
        """
        pass

    def on_fill(self, fill: Order) -> None:
        """Handle order fill notification. Override as needed."""
        pass

    def daily_close(self) -> None:
        """End-of-day hook. Override as needed."""
        pass

    def get_state(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "market_type": str(self.market_type) if hasattr(self, "market_type") else None,
            "initialized": self.initialized,
            "mode": str(self.mode) if self.mode else None,
        }
```

- [ ] **Step 2.4 — Update `packages/strategies/sma_crossover.py`**

Add `market_type = MarketType.EQUITY` class attribute and change `generate_signals` to return `UnifiedSignal`. Only the return type and the wrapping change — SMA logic is untouched.

Find the section in `sma_crossover.py` that builds `Signal(...)` objects and replace with:

```python
from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
# Add at top of file; remove old Signal import from base

# Inside the class:
market_type = MarketType.EQUITY

def generate_signals(self, portfolio: PortfolioState) -> list:
    signals = []
    # ... existing SMA crossover logic that currently creates Signal(...) ...
    # Replace each Signal(..., side="BUY", ...) with:
    if golden_cross:
        signals.append(UnifiedSignal(
            asset_id=self.symbol,
            market_type=MarketType.EQUITY,
            signal_type=SignalType.DIRECTIONAL,
            direction="long",
            confidence=self._compute_strength(),
            horizon_seconds=86400,
            strategy_id=self.strategy_id,
        ))
    elif death_cross:
        signals.append(UnifiedSignal(
            asset_id=self.symbol,
            market_type=MarketType.EQUITY,
            signal_type=SignalType.DIRECTIONAL,
            direction="short",
            confidence=self._compute_strength(),
            horizon_seconds=86400,
            strategy_id=self.strategy_id,
        ))
    return signals
```

> **Note:** Read the full `sma_crossover.py` before editing; the crossover detection logic and `_compute_strength` (or equivalent) are already there — only the return object changes.

- [ ] **Step 2.5 — Update `packages/strategies/ml_direction_v1.py`**

Same pattern: add `market_type = MarketType.EQUITY` and change `generate_signals` to return `UnifiedSignal`. The ML inference call and confidence gating logic stay the same; only the final signal wrapping changes.

```python
from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal

market_type = MarketType.EQUITY

# In generate_signals():
# Replace: return [Signal(symbol=..., side="BUY", strength=confidence)]
# With:
return [UnifiedSignal(
    asset_id=self.symbol,
    market_type=MarketType.EQUITY,
    signal_type=SignalType.DIRECTIONAL,
    direction="long" if prediction == "BUY" else ("short" if prediction == "SELL" else "none"),
    confidence=Decimal(str(confidence)),
    horizon_seconds=self.config.get("horizon_seconds", 3600),
    strategy_id=self.strategy_id,
)]
```

- [ ] **Step 2.6 — Run all strategy tests to confirm nothing regressed**

```bash
poetry run pytest tests/unit/strategies/ -v
# Expected: all tests pass (may need minor fixture updates for UnifiedSignal fields)
```

- [ ] **Step 2.7 — Commit**

```bash
git add packages/strategies/base.py packages/strategies/sma_crossover.py \
        packages/strategies/ml_direction_v1.py \
        tests/unit/strategies/test_base_unified_signal.py
git commit -m "feat: refactor Strategy ABC to emit UnifiedSignal; add market_type class attr"
```

---

## Task 3 — Portfolio allocator service

**Purpose:** Create `services/portfolio/` with an `Allocator` that sits between strategy signals and execution. It converts `List[UnifiedSignal]` into sized position targets, enforcing per-market capital budgets.

**Files:**
- Create: `services/portfolio/__init__.py`
- Create: `services/portfolio/allocator.py`
- Create: `services/portfolio/sizing.py`
- Create: `tests/unit/portfolio/test_allocator.py`
- Create: `tests/unit/portfolio/test_sizing.py`

---

- [ ] **Step 3.1 — Write failing tests for position sizing helpers**

```python
# tests/unit/portfolio/test_sizing.py
from decimal import Decimal
import pytest
from services.portfolio.sizing import (
    fixed_fraction_size,
    kelly_size,
    clamp,
)


def test_fixed_fraction_size_basic():
    # 2% of $100,000 portfolio at price $150 → $2000 / $150 = 13.33 → floor 13
    qty = fixed_fraction_size(
        portfolio_equity=Decimal("100000"),
        fraction=Decimal("0.02"),
        price=Decimal("150"),
    )
    assert qty == Decimal("13")


def test_fixed_fraction_size_zero_price():
    with pytest.raises(ValueError, match="price must be positive"):
        fixed_fraction_size(Decimal("100000"), Decimal("0.02"), Decimal("0"))


def test_clamp_within_bounds():
    assert clamp(Decimal("5"), Decimal("1"), Decimal("10")) == Decimal("5")


def test_clamp_below_min():
    assert clamp(Decimal("0"), Decimal("1"), Decimal("10")) == Decimal("1")


def test_clamp_above_max():
    assert clamp(Decimal("15"), Decimal("1"), Decimal("10")) == Decimal("10")


def test_kelly_size_positive_edge():
    # Kelly: f = (p*(b+1) - 1) / b  where b = win_loss_ratio
    # p=0.6, b=1 → f=(0.6*2 - 1)/1 = 0.2
    size = kelly_size(
        win_probability=Decimal("0.6"),
        win_loss_ratio=Decimal("1.0"),
        portfolio_equity=Decimal("100000"),
        price=Decimal("100"),
        max_fraction=Decimal("0.2"),
    )
    assert size == Decimal("200")  # 0.2 * 100000 / 100


def test_kelly_size_negative_edge_returns_zero():
    # p=0.3, b=1 → f=negative → return 0
    size = kelly_size(
        win_probability=Decimal("0.3"),
        win_loss_ratio=Decimal("1.0"),
        portfolio_equity=Decimal("100000"),
        price=Decimal("100"),
        max_fraction=Decimal("0.2"),
    )
    assert size == Decimal("0")
```

- [ ] **Step 3.2 — Write failing tests for the allocator**

```python
# tests/unit/portfolio/test_allocator.py
from decimal import Decimal
import pytest
from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from services.portfolio.allocator import Allocator, AllocationResult, CapitalBudget


def _make_signal(asset_id, direction, market_type=MarketType.EQUITY, confidence=Decimal("0.8")):
    return UnifiedSignal(
        asset_id=asset_id,
        market_type=market_type,
        signal_type=SignalType.DIRECTIONAL,
        direction=direction,
        confidence=confidence,
        horizon_seconds=3600,
        strategy_id="test",
    )


def test_allocator_basic_long():
    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={MarketType.EQUITY: Decimal("0.80")},
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    signals = [_make_signal("AAPL", "long")]
    results = allocator.allocate(signals, current_price_map={"AAPL": Decimal("150")})
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, AllocationResult)
    assert r.asset_id == "AAPL"
    assert r.direction == "long"
    assert r.target_quantity > 0


def test_allocator_respects_market_budget():
    # PREDICTION budget = 2%; signal for large size should be capped
    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={
            MarketType.EQUITY: Decimal("0.80"),
            MarketType.PREDICTION: Decimal("0.02"),
        },
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    signals = [_make_signal("BTC-UP", "long", MarketType.PREDICTION)]
    results = allocator.allocate(signals, current_price_map={"BTC-UP": Decimal("0.60")})
    # Max notional = 2% of 100000 = $2000; qty <= $2000 / $0.60 = 3333
    assert results[0].target_quantity <= Decimal("3334")


def test_allocator_skips_none_direction():
    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={MarketType.PREDICTION: Decimal("0.02")},
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    signals = [_make_signal("BTC-UP", "none", MarketType.PREDICTION)]
    results = allocator.allocate(signals, current_price_map={"BTC-UP": Decimal("0.60")})
    # "none" direction = market-making intent; allocator passes through with qty=0
    assert results[0].target_quantity == Decimal("0")
    assert results[0].pass_through is True


def test_allocator_no_budget_for_market_rejects():
    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={MarketType.EQUITY: Decimal("0.80")},
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    signals = [_make_signal("BTC-UP", "long", MarketType.PREDICTION)]
    results = allocator.allocate(signals, current_price_map={"BTC-UP": Decimal("0.60")})
    assert len(results) == 0
```

- [ ] **Step 3.3 — Run to confirm failures**

```bash
poetry run pytest tests/unit/portfolio/ -v
# Expected: ImportError — services.portfolio does not exist
```

- [ ] **Step 3.4 — Create `services/portfolio/__init__.py`**

```python
"""Portfolio allocation layer — sits between strategy signals and execution."""
```

- [ ] **Step 3.5 — Create `services/portfolio/sizing.py`**

```python
"""
Position sizing helpers.

All functions take Decimal inputs and return Decimal quantities.
"""

from decimal import Decimal, ROUND_DOWN


def clamp(value: Decimal, min_val: Decimal, max_val: Decimal) -> Decimal:
    """Clamp value to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def fixed_fraction_size(
    portfolio_equity: Decimal,
    fraction: Decimal,
    price: Decimal,
) -> Decimal:
    """
    Size a position as a fixed fraction of portfolio equity.

    Returns shares (floored to whole number). Raises ValueError if price <= 0.
    """
    if price <= Decimal("0"):
        raise ValueError("price must be positive")
    notional = portfolio_equity * fraction
    return (notional / price).to_integral_value(rounding=ROUND_DOWN)


def kelly_size(
    win_probability: Decimal,
    win_loss_ratio: Decimal,
    portfolio_equity: Decimal,
    price: Decimal,
    max_fraction: Decimal = Decimal("0.25"),
) -> Decimal:
    """
    Kelly criterion sizing, capped at max_fraction.

    kelly_f = (p * (b + 1) - 1) / b  where b = win_loss_ratio.
    Returns 0 if kelly_f <= 0 (negative or zero edge).
    """
    if win_loss_ratio <= Decimal("0"):
        return Decimal("0")
    kelly_f = (win_probability * (win_loss_ratio + 1) - 1) / win_loss_ratio
    if kelly_f <= Decimal("0"):
        return Decimal("0")
    fraction = clamp(kelly_f, Decimal("0"), max_fraction)
    return fixed_fraction_size(portfolio_equity, fraction, price)
```

- [ ] **Step 3.6 — Create `services/portfolio/allocator.py`**

```python
"""
Portfolio allocator.

Converts List[UnifiedSignal] into List[AllocationResult], enforcing
per-market capital budgets and per-position size caps.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List

from packages.common.market_schemas import MarketType, UnifiedSignal
from services.portfolio.sizing import fixed_fraction_size


@dataclass
class CapitalBudget:
    """
    Defines how total equity is distributed across market surfaces.

    market_budgets: fraction of total_equity each MarketType may use.
        e.g. {MarketType.EQUITY: Decimal("0.80"), MarketType.PREDICTION: Decimal("0.02")}
    max_single_position_pct: maximum fraction of total equity in any one position.
    """
    total_equity: Decimal
    market_budgets: Dict[MarketType, Decimal]
    max_single_position_pct: Decimal = Decimal("0.05")


@dataclass
class AllocationResult:
    """Sized allocation for a single signal."""
    asset_id: str
    strategy_id: str
    market_type: MarketType
    direction: str           # 'long', 'short', or 'none'
    target_quantity: Decimal
    signal: UnifiedSignal
    pass_through: bool = False  # True for MM signals that skip directional sizing


class Allocator:
    """
    Allocates capital across signals respecting per-market budgets.

    Usage::

        budget = CapitalBudget(
            total_equity=Decimal("100000"),
            market_budgets={MarketType.EQUITY: Decimal("0.80")},
        )
        allocator = Allocator(budget)
        results = allocator.allocate(signals, price_map)
    """

    def __init__(self, budget: CapitalBudget) -> None:
        self._budget = budget

    def allocate(
        self,
        signals: List[UnifiedSignal],
        current_price_map: Dict[str, Decimal],
    ) -> List[AllocationResult]:
        """
        Size each signal against the capital budget.

        Signals for markets not in market_budgets are silently dropped.
        Signals with direction='none' (market-making) are passed through
        with target_quantity=0 and pass_through=True for the executor to handle.

        Parameters
        ----------
        signals:
            UnifiedSignal list from one or more strategies.
        current_price_map:
            Map of asset_id → current price (for position sizing).

        Returns
        -------
        List[AllocationResult]
        """
        results: List[AllocationResult] = []

        for signal in signals:
            if signal.market_type not in self._budget.market_budgets:
                continue

            # Market-making signals: pass through without sizing
            if signal.direction == "none":
                results.append(AllocationResult(
                    asset_id=signal.asset_id,
                    strategy_id=signal.strategy_id,
                    market_type=signal.market_type,
                    direction="none",
                    target_quantity=Decimal("0"),
                    signal=signal,
                    pass_through=True,
                ))
                continue

            price = current_price_map.get(signal.asset_id)
            if price is None or price <= Decimal("0"):
                continue

            market_budget_pct = self._budget.market_budgets[signal.market_type]
            market_notional = self._budget.total_equity * market_budget_pct

            # Cap to single-position limit
            max_notional = self._budget.total_equity * self._budget.max_single_position_pct
            effective_notional = min(market_notional, max_notional)

            # Confidence-scale the fraction
            fraction = (effective_notional / self._budget.total_equity) * signal.confidence
            quantity = fixed_fraction_size(self._budget.total_equity, fraction, price)

            if quantity <= Decimal("0"):
                continue

            results.append(AllocationResult(
                asset_id=signal.asset_id,
                strategy_id=signal.strategy_id,
                market_type=signal.market_type,
                direction=signal.direction,
                target_quantity=quantity,
                signal=signal,
            ))

        return results
```

- [ ] **Step 3.7 — Run tests to confirm they pass**

```bash
poetry run pytest tests/unit/portfolio/ -v
# Expected: all tests pass
```

- [ ] **Step 3.8 — Commit**

```bash
git add services/portfolio/ tests/unit/portfolio/
git commit -m "feat: add portfolio allocator and sizing helpers (services/portfolio/)"
```

---

## Task 4 — Unified ExecutionAdapter with market-specific implementations

**Purpose:** Add `get_orderbook()` to the broker interface and create a single `ExecutionAdapter` ABC that both `AlpacaAdapter` and `PolymarketAdapter` implement. This removes duplicated order-placement code.

**Files:**
- Modify: `services/execution/broker/base.py` (add `get_orderbook`, `OrderbookLevel`, `OrderbookSnapshot`)
- Create: `services/execution/adapter.py` (new `ExecutionAdapter` ABC)
- Create: `services/execution/adapters/__init__.py`
- Create: `services/execution/adapters/alpaca_adapter.py`
- Create: `services/execution/adapters/polymarket_adapter.py`
- Create: `tests/unit/execution/test_execution_adapter.py`

---

- [ ] **Step 4.1 — Write failing tests**

```python
# tests/unit/execution/test_execution_adapter.py
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest
from services.execution.adapter import ExecutionAdapter
from services.execution.broker.base import OrderbookSnapshot, OrderbookLevel


def test_orderbook_snapshot_shape():
    snap = OrderbookSnapshot(
        asset_id="AAPL",
        bids=[OrderbookLevel(price=Decimal("149.50"), size=Decimal("100"))],
        asks=[OrderbookLevel(price=Decimal("150.00"), size=Decimal("50"))],
    )
    assert snap.best_bid == Decimal("149.50")
    assert snap.best_ask == Decimal("150.00")
    assert snap.midpoint == Decimal("149.75")
    assert snap.spread == Decimal("0.50")


def test_orderbook_snapshot_empty_side():
    snap = OrderbookSnapshot(asset_id="AAPL", bids=[], asks=[])
    assert snap.best_bid is None
    assert snap.best_ask is None
    assert snap.midpoint is None


class ConcreteAdapter(ExecutionAdapter):
    """Minimal concrete implementation for ABC testing."""

    async def place_order(self, order): return MagicMock()
    async def cancel_order(self, order_id): return True
    async def get_positions(self): return []
    async def get_account(self): return MagicMock()
    async def get_order_status(self, order_id): return MagicMock()
    async def get_orders(self, status=None, limit=100): return []
    async def get_orderbook(self, asset_id): return OrderbookSnapshot(asset_id=asset_id, bids=[], asks=[])
    def is_connected(self): return True
    def is_paper(self): return True


@pytest.mark.asyncio
async def test_concrete_adapter_implements_interface():
    adapter = ConcreteAdapter()
    snap = await adapter.get_orderbook("AAPL")
    assert snap.asset_id == "AAPL"
```

- [ ] **Step 4.2 — Run to confirm failures**

```bash
poetry run pytest tests/unit/execution/test_execution_adapter.py -v
# Expected: ImportError — services.execution.adapter does not exist
```

- [ ] **Step 4.3 — Add `OrderbookLevel` and `OrderbookSnapshot` to `services/execution/broker/base.py`**

Append to the existing `base.py` file after the `PositionNotFoundError` class:

```python
from typing import Optional


class OrderbookLevel(BaseModel):
    """Single price level in an order book."""
    price: Decimal = Field(..., description="Price at this level")
    size: Decimal = Field(..., description="Total size available at this level")


class OrderbookSnapshot(BaseModel):
    """Top-of-book snapshot for a single asset."""

    asset_id: str = Field(..., description="Symbol or market ID")
    bids: List[OrderbookLevel] = Field(default_factory=list)
    asks: List[OrderbookLevel] = Field(default_factory=list)

    @property
    def best_bid(self) -> Optional[Decimal]:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[Decimal]:
        return self.asks[0].price if self.asks else None

    @property
    def midpoint(self) -> Optional[Decimal]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    @property
    def spread(self) -> Optional[Decimal]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid
```

- [ ] **Step 4.4 — Create `services/execution/adapter.py`**

```python
"""
Market-agnostic ExecutionAdapter ABC.

Both AlpacaAdapter and PolymarketAdapter implement this interface so the
portfolio layer and risk manager can dispatch orders without knowing the
underlying venue.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from services.execution.broker.base import (
    Account,
    Order,
    OrderResult,
    OrderbookSnapshot,
    Position,
)


class ExecutionAdapter(ABC):
    """
    Unified execution interface for any market.

    Implementations:
    - services/execution/adapters/alpaca_adapter.py  (equities)
    - services/execution/adapters/polymarket_adapter.py  (prediction markets)
    """

    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult:
        """Place an order on the venue."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order. Returns True on success."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Return all open positions."""
        pass

    @abstractmethod
    async def get_account(self) -> Account:
        """Return account balance and status."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResult:
        """Poll status for a specific order."""
        pass

    @abstractmethod
    async def get_orders(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[OrderResult]:
        """Return recent orders, optionally filtered by status."""
        pass

    @abstractmethod
    async def get_orderbook(self, asset_id: str) -> OrderbookSnapshot:
        """
        Return a top-of-book snapshot.

        For equity venues this returns bid/ask from the quote feed.
        For Polymarket CLOB this returns the YES-token order book.
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """True if the adapter has an active venue connection."""
        pass

    @abstractmethod
    def is_paper(self) -> bool:
        """True if orders go to a paper/sandbox environment."""
        pass
```

- [ ] **Step 4.5 — Create `services/execution/adapters/__init__.py`**

```python
"""Market-specific ExecutionAdapter implementations."""
```

- [ ] **Step 4.6 — Create `services/execution/adapters/alpaca_adapter.py`**

This is a thin wrapper that delegates to the existing `AlpacaClient`:

```python
"""
AlpacaAdapter — wraps the existing AlpacaClient under ExecutionAdapter.

The existing AlpacaClient in services/execution/broker/alpaca.py is kept
intact; this adapter just re-exposes it through the unified interface and
adds get_orderbook() via the Alpaca quotes endpoint.
"""

from decimal import Decimal
from typing import List, Optional

from services.execution.adapter import ExecutionAdapter
from services.execution.broker.alpaca import AlpacaClient
from services.execution.broker.base import (
    Account,
    Order,
    OrderResult,
    OrderbookLevel,
    OrderbookSnapshot,
    Position,
)


class AlpacaAdapter(ExecutionAdapter):
    """ExecutionAdapter backed by the Alpaca paper/live API."""

    def __init__(self, client: AlpacaClient) -> None:
        self._client = client

    async def place_order(self, order: Order) -> OrderResult:
        return await self._client.place_order(order)

    async def cancel_order(self, order_id: str) -> bool:
        return await self._client.cancel_order(order_id)

    async def get_positions(self) -> List[Position]:
        return await self._client.get_positions()

    async def get_account(self) -> Account:
        return await self._client.get_account()

    async def get_order_status(self, order_id: str) -> OrderResult:
        return await self._client.get_order_status(order_id)

    async def get_orders(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[OrderResult]:
        return await self._client.get_orders(status=status, limit=limit)

    async def get_orderbook(self, asset_id: str) -> OrderbookSnapshot:
        """
        Fetch top-of-book from Alpaca's latest quote endpoint.

        Uses alpaca-py SDK: TradingClient.get_latest_quote(symbol).
        Returns an OrderbookSnapshot with one bid and one ask level.
        """
        try:
            quote = await self._client.get_latest_quote(asset_id)
            bids = [OrderbookLevel(price=Decimal(str(quote.bid_price)), size=Decimal(str(quote.bid_size)))]
            asks = [OrderbookLevel(price=Decimal(str(quote.ask_price)), size=Decimal(str(quote.ask_size)))]
        except Exception:
            bids, asks = [], []
        return OrderbookSnapshot(asset_id=asset_id, bids=bids, asks=asks)

    def is_connected(self) -> bool:
        return self._client.is_connected()

    def is_paper(self) -> bool:
        return self._client.is_paper()
```

- [ ] **Step 4.7 — Create `services/execution/adapters/polymarket_adapter.py`**

```python
"""
PolymarketAdapter — wraps existing Polymarket CLOB client under ExecutionAdapter.

Translates the unified Order schema into CLOB API calls and returns
OrderResult objects so the global risk layer can track all trades uniformly.
Order placement is still post-only (enforced in executor.py).
"""

from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from services.execution.adapter import ExecutionAdapter
from services.execution.broker.base import (
    Account,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderbookLevel,
    OrderbookSnapshot,
    Position,
    TimeInForce,
)
from services.polymarket.adapters.clob_client import CLOBClient
from services.polymarket.data_feed import DataFeed


class PolymarketAdapter(ExecutionAdapter):
    """
    ExecutionAdapter for Polymarket CLOB.

    Note: Polymarket uses prediction-share sizes (not dollar quantities).
    The `order.quantity` field represents share count; `limit_price` is
    the USDC price per share (0.01–0.99 range).
    """

    def __init__(self, clob_client: CLOBClient, data_feed: DataFeed) -> None:
        self._clob = clob_client
        self._feed = data_feed
        self._connected: bool = True

    async def place_order(self, order: Order) -> OrderResult:
        """
        Submit a post-only limit order to the Polymarket CLOB.

        Translates the unified Order schema to CLOB API format.
        Raises BrokerError on CLOB rejection.
        """
        side = "BUY" if order.side == OrderSide.BUY else "SELL"
        resp = await self._clob.place_limit_order(
            token_id=order.symbol,
            side=side,
            price=float(order.limit_price),
            size=float(order.quantity),
            client_order_id=order.client_order_id,
        )
        return OrderResult(
            broker_order_id=resp.get("orderID", str(uuid4())),
            client_order_id=order.client_order_id,
            status=OrderStatus.SUBMITTED,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            time_in_force=TimeInForce.GTC,
        )

    async def cancel_order(self, order_id: str) -> bool:
        result = await self._clob.cancel_order(order_id)
        return bool(result)

    async def get_positions(self) -> List[Position]:
        """
        Returns empty list — Polymarket positions are tracked via pm.* DB,
        not pulled from CLOB in real-time. Use recorder.py for inventory.
        """
        return []

    async def get_account(self) -> Account:
        """Returns minimal account stub; balance is from WalletManager."""
        return Account(
            account_id="polymarket",
            cash=Decimal("0"),
            portfolio_value=Decimal("0"),
            buying_power=Decimal("0"),
            equity=Decimal("0"),
            status="active",
        )

    async def get_order_status(self, order_id: str) -> OrderResult:
        resp = await self._clob.get_order(order_id)
        status_map = {
            "LIVE": OrderStatus.SUBMITTED,
            "MATCHED": OrderStatus.FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
        }
        return OrderResult(
            broker_order_id=resp["id"],
            client_order_id=resp.get("clientId", order_id),
            status=status_map.get(resp.get("status", ""), OrderStatus.SUBMITTED),
            symbol=resp.get("asset_id", ""),
            side=OrderSide.BUY if resp.get("side") == "BUY" else OrderSide.SELL,
            quantity=Decimal(str(resp.get("original_size", 0))),
            time_in_force=TimeInForce.GTC,
        )

    async def get_orders(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[OrderResult]:
        return []

    async def get_orderbook(self, asset_id: str) -> OrderbookSnapshot:
        """Pull live order book state from the data feed."""
        state = self._feed.get_current_state()
        bids, asks = [], []
        if state.midpoint and state.spread:
            half = state.spread / 2
            bids = [OrderbookLevel(price=state.midpoint - half, size=Decimal("100"))]
            asks = [OrderbookLevel(price=state.midpoint + half, size=Decimal("100"))]
        return OrderbookSnapshot(asset_id=asset_id, bids=bids, asks=asks)

    def is_connected(self) -> bool:
        return self._connected

    def is_paper(self) -> bool:
        return False
```

- [ ] **Step 4.8 — Run all execution tests**

```bash
poetry run pytest tests/unit/execution/ -v
# Expected: existing tests pass; new adapter tests pass
```

- [ ] **Step 4.9 — Commit**

```bash
git add services/execution/broker/base.py \
        services/execution/adapter.py \
        services/execution/adapters/ \
        tests/unit/execution/test_execution_adapter.py
git commit -m "feat: add ExecutionAdapter ABC with Alpaca and Polymarket implementations; add OrderbookSnapshot"
```

---

## Task 5 — Extract Polymarket market-making logic into a Strategy

**Purpose:** Move quoting strategy logic from `services/polymarket/session.py` + `quoting_engine.py` into `packages/strategies/polymarket_mm_strategy.py`. The service layer keeps CLOB clients and the wallet; strategy is pure signal generation.

**What moves:** The `QuotingEngine.compute_quotes()` decision logic → `PolymarketMMStrategy.generate_signals()`. The `SessionOrchestrator` is refactored to use the strategy instead of calling the quoting engine directly.

**Files:**
- Create: `packages/strategies/polymarket_mm_strategy.py`
- Modify: `services/polymarket/session.py` (call strategy instead of quoting engine directly)
- Create: `tests/unit/strategies/test_polymarket_mm_strategy.py`

---

- [ ] **Step 5.1 — Write failing tests**

```python
# tests/unit/strategies/test_polymarket_mm_strategy.py
from decimal import Decimal
import pytest
from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from packages.common.schemas import TradingMode
from packages.strategies.polymarket_mm_strategy import PolymarketMMStrategy


def _make_orderbook_state(midpoint, spread):
    """Minimal stub matching QuotingEngine's interface expectation."""
    class State:
        pass
    s = State()
    s.midpoint = Decimal(str(midpoint)) if midpoint else None
    s.spread = Decimal(str(spread)) if spread else None
    return s


def test_mm_strategy_market_type():
    config = {
        "market_id": "BTC-UP-2026-04-04T15",
        "quote_spread": "0.02",
        "quote_size": "50",
        "inventory_cap": "200",
    }
    s = PolymarketMMStrategy("pm_mm_test", config)
    assert s.market_type == MarketType.PREDICTION


def test_mm_strategy_generates_mm_signal():
    config = {
        "market_id": "BTC-UP-2026-04-04T15",
        "quote_spread": "0.02",
        "quote_size": "50",
        "inventory_cap": "200",
    }
    s = PolymarketMMStrategy("pm_mm_test", config)
    s.initialize(TradingMode.LIVE)

    ob_state = _make_orderbook_state(midpoint="0.55", spread="0.02")
    s.on_market_data(ob_state)

    from packages.strategies.base import PortfolioState
    portfolio = PortfolioState(equity=Decimal("1000"), cash=Decimal("1000"), positions=[])
    signals = s.generate_signals(portfolio)

    assert len(signals) == 1
    sig = signals[0]
    assert isinstance(sig, UnifiedSignal)
    assert sig.signal_type == SignalType.MARKET_MAKING
    assert sig.direction == "none"
    assert sig.market_type == MarketType.PREDICTION
    assert "bid_price" in sig.metadata
    assert "ask_price" in sig.metadata


def test_mm_strategy_suppresses_when_stale():
    config = {
        "market_id": "BTC-UP-2026-04-04T15",
        "quote_spread": "0.02",
        "quote_size": "50",
        "inventory_cap": "200",
    }
    s = PolymarketMMStrategy("pm_mm_test", config)
    s.initialize(TradingMode.LIVE)
    # No market data → stale midpoint
    from packages.strategies.base import PortfolioState
    portfolio = PortfolioState(equity=Decimal("1000"), cash=Decimal("1000"), positions=[])
    signals = s.generate_signals(portfolio)
    assert signals == []
```

- [ ] **Step 5.2 — Run to confirm failures**

```bash
poetry run pytest tests/unit/strategies/test_polymarket_mm_strategy.py -v
# Expected: ImportError — packages.strategies.polymarket_mm_strategy does not exist
```

- [ ] **Step 5.3 — Create `packages/strategies/polymarket_mm_strategy.py`**

```python
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
        self._last_ob_state: Optional[Any] = None  # OrderbookState from data feed
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
        """
        ob = self._last_ob_state
        if ob is None or ob.midpoint is None:
            return []

        if ob.spread is not None and ob.spread > _MAX_QUOTED_SPREAD:
            return []

        half = self._quote_spread / 2
        raw_bid = ob.midpoint - half
        raw_ask = ob.midpoint + half

        bid_price = _round_tick(raw_bid)
        ask_price = _round_tick(raw_ask)

        # Inventory gate: suppress bid if already at cap
        bid_size = Decimal("0") if self._inventory_yes >= self._inventory_cap else self._quote_size
        # Suppress ask if no inventory to sell
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
        Strategy-level risk check for MM signals.

        MM signals are passed to the executor directly (via SessionOrchestrator),
        not converted to Orders here. Return empty list; the GlobalRiskManager
        handles session-level loss limits via the safety layer integration.
        """
        return []
```

- [ ] **Step 5.4 — Refactor `services/polymarket/session.py` to use the strategy**

Open `services/polymarket/session.py`. Find the main quoting loop (the `while True` cycle inside `run_session` or `_run_quoting_loop`). Replace the direct call to `self._quoting_engine.compute_quotes(...)` with a strategy call:

```python
# Before (in session.py):
quote_decision = self._quoting_engine.compute_quotes(
    orderbook_state, inventory_yes, config
)

# After:
from packages.common.schemas import TradingMode
from packages.strategies.base import PortfolioState
from decimal import Decimal

# Strategy is passed in or created in __init__; update inventory each cycle
self._strategy.update_inventory(inventory_yes)
ob_state = self._data_feed.get_current_state()
self._strategy.on_market_data(ob_state)

portfolio = PortfolioState(
    equity=Decimal(str(wallet_balance)),
    cash=Decimal(str(wallet_balance)),
    positions=[],
)
signals = self._strategy.generate_signals(portfolio)

# MM signal metadata carries bid/ask/size — extract for executor
if not signals:
    continue  # suppressed; heartbeat still runs

sig = signals[0]
bid_price = Decimal(sig.metadata["bid_price"])
ask_price = Decimal(sig.metadata["ask_price"])
bid_size = Decimal(sig.metadata["bid_size"])
ask_size = Decimal(sig.metadata["ask_size"])
```

Also add `strategy: PolymarketMMStrategy` to `SessionOrchestrator.__init__` and update `cli.py` to instantiate it before passing to the orchestrator.

> **Note:** Read `session.py` carefully to find the exact quoting loop location. The replacement above is a find-and-replace pattern — match the surrounding context.

- [ ] **Step 5.5 — Run strategy and integration tests**

```bash
poetry run pytest tests/unit/strategies/ tests/integration/polymarket/ -v
# Expected: all pass; integration tests may need strategy instantiation in fixtures
```

- [ ] **Step 5.6 — Commit**

```bash
git add packages/strategies/polymarket_mm_strategy.py \
        services/polymarket/session.py \
        tests/unit/strategies/test_polymarket_mm_strategy.py
git commit -m "feat: extract Polymarket quoting logic into PolymarketMMStrategy; wire session orchestrator"
```

---

## Task 6 — Global risk manager

**Purpose:** Create `services/risk/global_risk_manager.py` that wraps the existing `RiskManager` for equities and adds a Polymarket-aware extension, so all trades across both surfaces pass through one choke point.

**Files:**
- Create: `services/risk/global_risk_manager.py`
- Modify: `services/risk/limits.py` (add `MarketType`-aware limit types)
- Create: `tests/unit/risk/test_global_risk_manager.py`

---

- [ ] **Step 6.1 — Write failing tests**

```python
# tests/unit/risk/test_global_risk_manager.py
from decimal import Decimal
import pytest
from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from services.portfolio.allocator import AllocationResult
from services.risk.global_risk_manager import GlobalRiskManager, GlobalRiskConfig


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
    allocation = _make_allocation("BTC-UP", "none", MarketType.PREDICTION, Decimal("0"))
    allocation.signal = UnifiedSignal(
        asset_id="BTC-UP",
        market_type=MarketType.PREDICTION,
        signal_type=SignalType.MARKET_MAKING,
        direction="none",
        confidence=Decimal("1"),
        horizon_seconds=3600,
        strategy_id="test",
    )
    result = grm.check(
        allocation,
        current_drawdown_pct=Decimal("1"),
        polymarket_session_pnl=Decimal("-60"),
    )
    assert result.approved is False
    assert "session loss" in result.rejection_reason.lower()
```

- [ ] **Step 6.2 — Run to confirm failures**

```bash
poetry run pytest tests/unit/risk/test_global_risk_manager.py -v
# Expected: ImportError — services.risk.global_risk_manager does not exist
```

- [ ] **Step 6.3 — Create `services/risk/global_risk_manager.py`**

```python
"""
GlobalRiskManager — unified pre-trade risk check across all market surfaces.

Sits between the portfolio allocator and the execution adapters. Every
AllocationResult must pass through here before an order is placed.

Check order:
1. Kill switch (blocks all markets)
2. Portfolio drawdown (blocks all markets)
3. Market-specific extensions:
   - Equity: delegates to existing RiskManager
   - Prediction: checks session loss limit
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from packages.common.market_schemas import MarketType
from services.portfolio.allocator import AllocationResult


@dataclass
class GlobalRiskConfig:
    """Runtime risk parameters for the global manager."""
    total_equity: Decimal
    max_drawdown_pct: Decimal
    kill_switch_active: bool = False
    max_polymarket_session_loss_usdc: Decimal = Decimal("100")


@dataclass
class GlobalRiskResult:
    """Result of a global risk check."""
    approved: bool
    rejection_reason: Optional[str] = None

    @classmethod
    def approve(cls) -> "GlobalRiskResult":
        return cls(approved=True)

    @classmethod
    def reject(cls, reason: str) -> "GlobalRiskResult":
        return cls(approved=False, rejection_reason=reason)


class GlobalRiskManager:
    """
    Single choke point for all pre-trade risk checks.

    Usage::

        config = GlobalRiskConfig(
            total_equity=Decimal("100000"),
            max_drawdown_pct=Decimal("10"),
        )
        grm = GlobalRiskManager(config)

        result = grm.check(
            allocation,
            current_drawdown_pct=portfolio_drawdown,
            polymarket_session_pnl=session_realized_pnl,
        )
        if not result.approved:
            logger.warning("Trade blocked: %s", result.rejection_reason)
            return
    """

    def __init__(self, config: GlobalRiskConfig) -> None:
        self._config = config

    def check(
        self,
        allocation: AllocationResult,
        current_drawdown_pct: Decimal = Decimal("0"),
        polymarket_session_pnl: Optional[Decimal] = None,
    ) -> GlobalRiskResult:
        """
        Run all applicable risk checks for an allocation.

        Parameters
        ----------
        allocation:
            Sized allocation from the portfolio allocator.
        current_drawdown_pct:
            Portfolio drawdown from high-water mark (as a positive %).
        polymarket_session_pnl:
            Realized PnL for the current Polymarket session (negative = loss).
            Required only when allocation.market_type == PREDICTION.

        Returns
        -------
        GlobalRiskResult with approved=True or a rejection reason.
        """

        # --- Layer 1: Kill switch (universal) ---
        if self._config.kill_switch_active:
            return GlobalRiskResult.reject("Kill switch is active — all trading halted")

        # --- Layer 2: Portfolio drawdown (universal) ---
        if current_drawdown_pct >= self._config.max_drawdown_pct:
            return GlobalRiskResult.reject(
                f"Portfolio drawdown {current_drawdown_pct}% >= limit {self._config.max_drawdown_pct}%"
            )

        # --- Layer 3: Market-specific ---
        if allocation.market_type == MarketType.PREDICTION:
            return self._check_prediction(allocation, polymarket_session_pnl)

        if allocation.market_type == MarketType.EQUITY:
            return self._check_equity(allocation)

        return GlobalRiskResult.approve()

    def _check_prediction(
        self,
        allocation: AllocationResult,
        session_pnl: Optional[Decimal],
    ) -> GlobalRiskResult:
        """Polymarket-specific: session loss limit."""
        if session_pnl is not None:
            loss_limit = -abs(self._config.max_polymarket_session_loss_usdc)
            if session_pnl < loss_limit:
                return GlobalRiskResult.reject(
                    f"Polymarket session loss {session_pnl} USDC exceeds limit {loss_limit} USDC"
                )
        return GlobalRiskResult.approve()

    def _check_equity(self, allocation: AllocationResult) -> GlobalRiskResult:
        """
        Equity-specific checks.

        The existing per-order RiskManager checks (strategy limits, notional
        caps, penny stock filter) are still applied by the execution engine.
        This layer adds portfolio-global guards only.
        """
        # Future: add equity-specific cross-strategy exposure checks here
        return GlobalRiskResult.approve()
```

- [ ] **Step 6.4 — Run all risk tests**

```bash
poetry run pytest tests/unit/risk/ -v
# Expected: all tests pass (existing RiskManager tests + new GlobalRiskManager tests)
```

- [ ] **Step 6.5 — Commit**

```bash
git add services/risk/global_risk_manager.py \
        tests/unit/risk/test_global_risk_manager.py
git commit -m "feat: add GlobalRiskManager with equity and prediction market extensions"
```

---

## Task 7 — Integration smoke test: full pipeline

**Purpose:** One end-to-end test proving the six subsystems connect correctly: signal → allocator → global risk → execution adapter.

**Files:**
- Create: `tests/integration/test_unified_pipeline.py`

---

- [ ] **Step 7.1 — Write the integration test**

```python
# tests/integration/test_unified_pipeline.py
"""
End-to-end smoke test: strategy → allocator → global risk → adapter stub.

Uses in-memory stubs — no network or DB required.
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest

from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from packages.common.schemas import TradingMode
from packages.strategies.sma_crossover import SMACrossoverStrategy
from services.portfolio.allocator import Allocator, CapitalBudget
from services.risk.global_risk_manager import GlobalRiskConfig, GlobalRiskManager
from services.execution.adapter import ExecutionAdapter
from services.execution.broker.base import (
    Account, Order, OrderResult, OrderSide, OrderStatus,
    OrderbookSnapshot, Position, TimeInForce,
)


class StubAdapter(ExecutionAdapter):
    def __init__(self):
        self.placed = []

    async def place_order(self, order):
        self.placed.append(order)
        return OrderResult(
            broker_order_id="stub-001",
            client_order_id=order.client_order_id,
            status=OrderStatus.SUBMITTED,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            time_in_force=TimeInForce.DAY,
        )

    async def cancel_order(self, order_id): return True
    async def get_positions(self): return []
    async def get_account(self):
        return Account(account_id="stub", cash=Decimal("100000"),
                      portfolio_value=Decimal("100000"), buying_power=Decimal("100000"),
                      equity=Decimal("100000"), status="active")
    async def get_order_status(self, order_id): return MagicMock()
    async def get_orders(self, status=None, limit=100): return []
    async def get_orderbook(self, asset_id):
        return OrderbookSnapshot(asset_id=asset_id, bids=[], asks=[])
    def is_connected(self): return True
    def is_paper(self): return True


@pytest.mark.asyncio
async def test_unified_pipeline_equity_signal_to_adapter():
    """
    One directional signal travels through all 4 new layers
    and reaches the execution adapter.
    """
    # 1. Strategy emits a UnifiedSignal (we inject it directly here)
    signal = UnifiedSignal(
        asset_id="AAPL",
        market_type=MarketType.EQUITY,
        signal_type=SignalType.DIRECTIONAL,
        direction="long",
        confidence=Decimal("0.85"),
        horizon_seconds=3600,
        strategy_id="test_sma",
    )

    # 2. Allocator sizes it
    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={MarketType.EQUITY: Decimal("0.80")},
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    allocations = allocator.allocate([signal], current_price_map={"AAPL": Decimal("150")})
    assert len(allocations) == 1
    allocation = allocations[0]
    assert allocation.target_quantity > 0

    # 3. Global risk approves
    grm_config = GlobalRiskConfig(
        total_equity=Decimal("100000"),
        max_drawdown_pct=Decimal("10"),
    )
    grm = GlobalRiskManager(grm_config)
    risk_result = grm.check(allocation, current_drawdown_pct=Decimal("1"))
    assert risk_result.approved

    # 4. Adapter receives the order
    adapter = StubAdapter()
    from uuid import uuid4
    order = Order(
        client_order_id=str(uuid4()),
        symbol=allocation.asset_id,
        side=OrderSide.BUY,
        quantity=allocation.target_quantity,
        order_type="MARKET",
        time_in_force=TimeInForce.DAY,
    )
    result = await adapter.place_order(order)
    assert result.status == OrderStatus.SUBMITTED
    assert len(adapter.placed) == 1
```

- [ ] **Step 7.2 — Run the integration test**

```bash
poetry run pytest tests/integration/test_unified_pipeline.py -v
# Expected: PASS
```

- [ ] **Step 7.3 — Run the full test suite to confirm nothing regressed**

```bash
poetry run pytest tests/ -v --tb=short
# Expected: all pre-existing tests pass; new tests pass
```

- [ ] **Step 7.4 — Final commit**

```bash
git add tests/integration/test_unified_pipeline.py
git commit -m "test: add end-to-end unified pipeline integration smoke test"
```

---

## Self-review against `readjustment.md` acceptance criteria

| Criterion | Task(s) that satisfy it |
|-----------|------------------------|
| All strategies use same interface | Task 2 (`UnifiedSignal`, `Strategy` ABC), Tasks 5 |
| Portfolio allocator sits between signal and execution | Task 3 |
| Execution uses adapter pattern (no duplicated logic) | Task 4 |
| Risk is enforced globally across all trades | Task 6 |
| Polymarket strategies exist in `packages/strategies` | Task 5 |
| New strategy can be added without modifying services | Tasks 1–3 (all new strategies just implement `Strategy` and declare `market_type`) |

---

## What is NOT changed (preserving existing work)

- `services/ml/` — unchanged
- `packages/common/schemas.py`, `polymarket_schemas.py`, `ml_schemas.py` — unchanged
- `services/data/` and all Alembic migrations — unchanged
- `services/polymarket/adapters/` (CLOB/Gamma/Binance clients) — unchanged
- `services/polymarket/recorder.py`, `wallet.py`, `safety.py` — unchanged (safety is still called from session.py alongside GlobalRiskManager)
- `docs/` — unchanged

---

## PROGRESS.md update

After completing all tasks, add a row to `docs/plans/PROGRESS.md`:

```
| **v2.1.0** | **Architecture refactor: unified pipeline** | In progress | — | 0 | `docs/plans/2026-04-04-unified-architecture-refactor.md` | Tasks 1–7 |
```
