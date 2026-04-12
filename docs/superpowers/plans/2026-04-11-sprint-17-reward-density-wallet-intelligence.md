# Sprint 17: Reward Density + Wallet Intelligence + Signal Aggregation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reward density scoring, wallet intelligence, composite signal aggregation, and model lifecycle management to Caliper v2.7.

**Architecture:** Four new service directories (`services/reward_density/`, `services/wallet_intelligence/`, `services/signal_aggregation/`, and `services/fleet/lifecycle.py`) expose pure Python components. They integrate with the Sprint 16 ranker (adds `w_D` term), the Sprint 16 strategies (replace raw `M(t)` threshold), and the FastAPI layer (new routers). One new Alembic migration (`014`) adds five tables.

**Tech Stack:** Python 3.11+, Pydantic v2, FastAPI, SQLAlchemy (text queries), web3.py (Polygon RPC for OrderFilled events), scikit-learn (KMeans), numpy (z-scoring), httpx (async HTTP for leaderboard + optional Graph API).

---

## File Map

### New files — create

```
services/reward_density/__init__.py
services/reward_density/schemas.py
services/reward_density/onchain/__init__.py
services/reward_density/onchain/polygon_client.py
services/reward_density/competition.py
services/reward_density/incentives.py
services/reward_density/risk_scorer.py
services/reward_density/analyzer.py

services/wallet_intelligence/__init__.py
services/wallet_intelligence/schemas.py
services/wallet_intelligence/profiler.py
services/wallet_intelligence/ranker.py
services/wallet_intelligence/clustering.py
services/wallet_intelligence/signals.py

services/signal_aggregation/__init__.py
services/signal_aggregation/schemas.py
services/signal_aggregation/weighter.py
services/signal_aggregation/aggregator.py

services/fleet/lifecycle.py

services/data/alembic/versions/014_create_sprint17_tables.py

services/api/routers/reward_density.py
services/api/routers/wallet_intelligence.py
services/api/routers/signal_aggregation.py
services/api/routers/lifecycle.py

tests/unit/reward_density/__init__.py
tests/unit/reward_density/test_competition.py
tests/unit/reward_density/test_incentives.py
tests/unit/reward_density/test_analyzer.py
tests/unit/wallet_intelligence/__init__.py
tests/unit/wallet_intelligence/test_clustering.py
tests/unit/wallet_intelligence/test_signals.py
tests/unit/signal_aggregation/__init__.py
tests/unit/signal_aggregation/test_aggregator.py
tests/unit/fleet/__init__.py
tests/unit/fleet/test_lifecycle.py
tests/integration/__init__.py  (may already exist)
tests/integration/test_sprint17_pipeline.py
```

### Modified files

```
services/ranking/score.py           — add reward_density param, 5th weight term
services/ranking/schemas.py         — add reward_density_score field to MarketScore
services/ranking/ranker.py          — accept optional reward_density_scorer, pass score
packages/strategies/poly_directional_v1.py  — accept AggregatedSignal, replace M(t) check
packages/strategies/poly_hybrid_v1.py       — accept AggregatedSignal for directional lean
services/api/main.py                — include four new routers
```

---

## Task 1: Reward Density Schemas

**Files:**
- Create: `services/reward_density/__init__.py`
- Create: `services/reward_density/schemas.py`

- [ ] **Step 1: Write the test**

```python
# tests/unit/reward_density/__init__.py  (empty)

# tests/unit/reward_density/test_incentives.py
# (will grow — start with schema smoke test here)
from decimal import Decimal
from datetime import datetime, timezone

from services.reward_density.schemas import (
    RewardDensityScore,
    CompetitionMetric,
    IncentiveEstimate,
)


def test_reward_density_score_fields() -> None:
    score = RewardDensityScore(
        market_id="mkt1",
        scored_at=datetime.now(timezone.utc),
        expected_incentives_usd=Decimal("5.00"),
        maker_rebate_estimate=Decimal("3.00"),
        liquidity_reward_estimate=Decimal("2.00"),
        competition=Decimal("4.0"),
        risk_score=Decimal("1.5"),
        reward_density_score=Decimal("2.22"),
        alpha=Decimal("1.0"),
        beta=Decimal("0.5"),
        confidence="high",
    )
    assert score.market_id == "mkt1"
    assert score.confidence == "high"


def test_competition_metric_is_estimate_flag() -> None:
    m = CompetitionMetric(
        market_id="mkt1",
        computed_at=datetime.now(timezone.utc),
        lookback_days=7,
        hhi=Decimal("1.0"),
        n_eff=Decimal("1.0"),
        top_maker_address=None,
        top_maker_share=None,
        data_source="onchain",
        is_estimate=False,
    )
    assert m.hhi == Decimal("1.0")
    assert m.n_eff == Decimal("1.0")
```

- [ ] **Step 2: Run test to verify it fails**

```
poetry run pytest tests/unit/reward_density/test_incentives.py -v
```
Expected: ImportError — module does not exist yet.

- [ ] **Step 3: Create schemas**

```python
# services/reward_density/__init__.py
```

```python
# services/reward_density/schemas.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel


class IncentiveEstimate(BaseModel):
    market_id: str
    estimated_at: datetime
    fee_pool_usd: Decimal
    maker_rebate_pool_usd: Decimal
    liquidity_reward_pool_usd: Decimal
    expected_maker_share: Decimal
    expected_lr_share: Decimal
    expected_total_usd: Decimal


class CompetitionMetric(BaseModel):
    market_id: str
    computed_at: datetime
    lookback_days: int
    hhi: Decimal
    n_eff: Decimal
    top_maker_address: Optional[str] = None
    top_maker_share: Optional[Decimal] = None
    data_source: Literal["onchain", "rewards_api_proxy"]
    is_estimate: bool


class RewardDensityScore(BaseModel):
    market_id: str
    scored_at: datetime
    expected_incentives_usd: Decimal
    maker_rebate_estimate: Decimal
    liquidity_reward_estimate: Decimal
    competition: Decimal        # N_eff
    risk_score: Decimal
    reward_density_score: Decimal
    alpha: Decimal
    beta: Decimal
    confidence: Literal["high", "medium", "low"]
```

- [ ] **Step 4: Run test to verify it passes**

```
poetry run pytest tests/unit/reward_density/test_incentives.py -v
```
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add services/reward_density/__init__.py services/reward_density/schemas.py \
        tests/unit/reward_density/__init__.py tests/unit/reward_density/test_incentives.py
git commit -m "feat(17-1): reward density schemas"
```

---

## Task 2: Polygon On-Chain Client

**Files:**
- Create: `services/reward_density/onchain/__init__.py`
- Create: `services/reward_density/onchain/polygon_client.py`

The client fetches `OrderFilled` events from Polygon using web3.py (JSON-RPC). The CTF Exchange contract address is `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E`. Events are decoded from the ABI.

- [ ] **Step 1: Write the test**

```python
# tests/unit/reward_density/test_competition.py
from decimal import Decimal
from unittest.mock import MagicMock, patch

from services.reward_density.onchain.polygon_client import PolygonClient, OrderFilledEvent


def test_order_filled_event_model() -> None:
    evt = OrderFilledEvent(
        maker="0xabc",
        taker="0xdef",
        maker_asset_id="0x" + "00" * 32,
        taker_asset_id="0x" + "01" * 32,
        maker_amount_filled=1_000_000,
        taker_amount_filled=500_000,
        fee=100,
        block_number=12345,
        tx_hash="0x" + "aa" * 32,
    )
    assert evt.maker == "0xabc"
    assert evt.fee == 100


def test_polygon_client_init_no_rpc() -> None:
    """Client initialises without connecting when no RPC URL is set."""
    client = PolygonClient(rpc_url=None)
    assert client.rpc_url is None
```

- [ ] **Step 2: Run test to verify it fails**

```
poetry run pytest tests/unit/reward_density/test_competition.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement polygon_client.py**

```python
# services/reward_density/onchain/__init__.py
```

```python
# services/reward_density/onchain/polygon_client.py
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

# web3 is an optional dependency — import guarded so the module loads without it
try:
    from web3 import Web3
    from web3.types import LogReceipt
    _HAS_WEB3 = True
except ImportError:
    _HAS_WEB3 = False

CTF_EXCHANGE_ADDRESS = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"

# OrderFilled(address,address,uint256,uint256,uint256,uint256,uint256)
ORDER_FILLED_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bde8f33ef4b0ad58e74519"

# Minimal ABI for the OrderFilled event
_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "name": "maker", "type": "address"},
            {"indexed": False, "name": "taker", "type": "address"},
            {"indexed": False, "name": "makerAssetId", "type": "uint256"},
            {"indexed": False, "name": "takerAssetId", "type": "uint256"},
            {"indexed": False, "name": "makerAmountFilled", "type": "uint256"},
            {"indexed": False, "name": "takerAmountFilled", "type": "uint256"},
            {"indexed": False, "name": "fee", "type": "uint256"},
        ],
        "name": "OrderFilled",
        "type": "event",
    }
]


@dataclass
class OrderFilledEvent:
    maker: str
    taker: str
    maker_asset_id: str
    taker_asset_id: str
    maker_amount_filled: int
    taker_amount_filled: int
    fee: int
    block_number: int
    tx_hash: str


class PolygonClient:
    """Fetches OrderFilled events from Polygon CTF Exchange."""

    def __init__(self, rpc_url: Optional[str] = None) -> None:
        self.rpc_url = rpc_url or os.getenv("POLYGON_RPC_URL")
        self._w3: Optional[object] = None
        self._contract: Optional[object] = None

        if self.rpc_url and _HAS_WEB3:
            self._w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self._contract = self._w3.eth.contract(  # type: ignore[union-attr]
                address=Web3.to_checksum_address(CTF_EXCHANGE_ADDRESS),
                abi=_ABI,
            )

    def _blocks_for_days(self, days: int) -> tuple[int, int]:
        """Approximate block range for the last N days (Polygon ~2s blocks)."""
        if self._w3 is None:
            return 0, 0
        latest = self._w3.eth.block_number  # type: ignore[union-attr]
        blocks_per_day = 43_200  # 86400s / 2s
        from_block = max(0, latest - days * blocks_per_day)
        return from_block, latest

    def fetch_order_filled_events(
        self,
        maker_asset_id: str,
        lookback_days: int = 7,
    ) -> List[OrderFilledEvent]:
        """Return OrderFilled events for a given makerAssetId token."""
        if self._contract is None or self._w3 is None:
            return []

        from_block, to_block = self._blocks_for_days(lookback_days)
        try:
            raw_events = self._contract.events.OrderFilled.get_logs(  # type: ignore[union-attr]
                fromBlock=from_block,
                toBlock=to_block,
            )
        except Exception:
            return []

        results: List[OrderFilledEvent] = []
        asset_id_int = int(maker_asset_id, 16) if maker_asset_id.startswith("0x") else int(maker_asset_id)
        for evt in raw_events:
            args = evt["args"]
            if args["makerAssetId"] != asset_id_int:
                continue
            results.append(
                OrderFilledEvent(
                    maker=args["maker"],
                    taker=args["taker"],
                    maker_asset_id=str(args["makerAssetId"]),
                    taker_asset_id=str(args["takerAssetId"]),
                    maker_amount_filled=args["makerAmountFilled"],
                    taker_amount_filled=args["takerAmountFilled"],
                    fee=args["fee"],
                    block_number=evt["blockNumber"],
                    tx_hash=evt["transactionHash"].hex(),
                )
            )
        return results
```

- [ ] **Step 4: Run test to verify it passes**

```
poetry run pytest tests/unit/reward_density/test_competition.py::test_order_filled_event_model \
                  tests/unit/reward_density/test_competition.py::test_polygon_client_init_no_rpc -v
```
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add services/reward_density/onchain/ tests/unit/reward_density/test_competition.py
git commit -m "feat(17-2): polygon on-chain client (OrderFilled)"
```

---

## Task 3: HHI Competition Estimator

**Files:**
- Create: `services/reward_density/competition.py`
- Modify: `tests/unit/reward_density/test_competition.py`

- [ ] **Step 1: Write the tests**

Append to `tests/unit/reward_density/test_competition.py`:

```python
from services.reward_density.competition import CompetitionEstimator
from services.reward_density.onchain.polygon_client import OrderFilledEvent


def _make_event(maker: str, fee: int) -> OrderFilledEvent:
    return OrderFilledEvent(
        maker=maker,
        taker="0x0",
        maker_asset_id="123",
        taker_asset_id="456",
        maker_amount_filled=1000,
        taker_amount_filled=900,
        fee=fee,
        block_number=1,
        tx_hash="0x00",
    )


def test_hhi_single_maker() -> None:
    events = [_make_event("0xA", 100), _make_event("0xA", 200)]
    estimator = CompetitionEstimator()
    metric = estimator.compute("mkt1", events)
    assert metric.hhi == pytest.approx(1.0, abs=1e-9)
    assert metric.n_eff == pytest.approx(1.0, abs=1e-9)
    assert metric.top_maker_address == "0xA"
    assert float(metric.top_maker_share) == pytest.approx(1.0, abs=1e-9)


def test_hhi_equal_distribution() -> None:
    events = [_make_event(f"0x{i:X}", 100) for i in range(4)]
    estimator = CompetitionEstimator()
    metric = estimator.compute("mkt1", events)
    # 4 equal makers → HHI = 4 * (0.25)^2 = 0.25, N_eff = 4
    assert float(metric.hhi) == pytest.approx(0.25, abs=1e-9)
    assert float(metric.n_eff) == pytest.approx(4.0, abs=1e-9)


def test_hhi_no_events_fallback() -> None:
    estimator = CompetitionEstimator()
    metric = estimator.compute("mkt1", [])
    assert metric.is_estimate is True
    assert metric.data_source == "rewards_api_proxy"
```

Add `import pytest` at the top of the test file.

- [ ] **Step 2: Run test to verify it fails**

```
poetry run pytest tests/unit/reward_density/test_competition.py -v
```
Expected: ImportError for `CompetitionEstimator`.

- [ ] **Step 3: Implement competition.py**

```python
# services/reward_density/competition.py
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from services.reward_density.onchain.polygon_client import OrderFilledEvent
from services.reward_density.schemas import CompetitionMetric


class CompetitionEstimator:
    """Compute maker HHI from on-chain OrderFilled events."""

    def __init__(self, lookback_days: int = 7) -> None:
        self.lookback_days = lookback_days

    def compute(
        self,
        market_id: str,
        events: List[OrderFilledEvent],
        *,
        fallback_n_eff: Optional[Decimal] = None,
    ) -> CompetitionMetric:
        now = datetime.now(timezone.utc)

        if not events:
            n_eff = fallback_n_eff or Decimal("5")
            return CompetitionMetric(
                market_id=market_id,
                computed_at=now,
                lookback_days=self.lookback_days,
                hhi=Decimal("1") / n_eff,
                n_eff=n_eff,
                top_maker_address=None,
                top_maker_share=None,
                data_source="rewards_api_proxy",
                is_estimate=True,
            )

        fee_by_maker: Dict[str, int] = defaultdict(int)
        for evt in events:
            fee_by_maker[evt.maker] += evt.fee

        total_fee = sum(fee_by_maker.values())
        if total_fee == 0:
            n_eff = fallback_n_eff or Decimal(str(len(fee_by_maker)))
            return CompetitionMetric(
                market_id=market_id,
                computed_at=now,
                lookback_days=self.lookback_days,
                hhi=Decimal("1") / n_eff,
                n_eff=n_eff,
                top_maker_address=None,
                top_maker_share=None,
                data_source="onchain",
                is_estimate=True,
            )

        shares: Dict[str, Decimal] = {
            maker: Decimal(str(fee)) / Decimal(str(total_fee))
            for maker, fee in fee_by_maker.items()
        }
        hhi = sum(w * w for w in shares.values())
        n_eff = Decimal("1") / hhi

        top_maker = max(shares, key=lambda k: shares[k])
        return CompetitionMetric(
            market_id=market_id,
            computed_at=now,
            lookback_days=self.lookback_days,
            hhi=hhi,
            n_eff=n_eff,
            top_maker_address=top_maker,
            top_maker_share=shares[top_maker],
            data_source="onchain",
            is_estimate=False,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```
poetry run pytest tests/unit/reward_density/test_competition.py -v
```
Expected: PASS (5 tests including schema tests from Task 1).

- [ ] **Step 5: Commit**

```bash
git add services/reward_density/competition.py tests/unit/reward_density/test_competition.py
git commit -m "feat(17-3): HHI competition estimator"
```

---

## Task 4: Incentive Estimator

**Files:**
- Create: `services/reward_density/incentives.py`
- Modify: `tests/unit/reward_density/test_incentives.py`

- [ ] **Step 1: Write the tests**

Append to `tests/unit/reward_density/test_incentives.py`:

```python
import pytest
from decimal import Decimal

from services.reward_density.incentives import IncentiveEstimator, effective_fee_rate


def test_effective_fee_rate_formula() -> None:
    # effective_fee_rate = price * 0.072 * (price * (1 - price))^1
    price = Decimal("0.5")
    expected = price * Decimal("0.072") * (price * (Decimal("1") - price))
    result = effective_fee_rate(price)
    assert result == pytest.approx(float(expected), rel=1e-6)


def test_fee_rate_at_extreme_price() -> None:
    # At price=0.01, fee rate should be very low
    result = effective_fee_rate(Decimal("0.01"))
    assert result > 0


def test_rebate_pool_is_20pct_of_fee_pool() -> None:
    estimator = IncentiveEstimator()
    # volume = $1000, price = 0.5
    volume = Decimal("1000")
    price = Decimal("0.5")
    fee_pool = estimator.compute_fee_pool(volume, price)
    rebate = estimator.compute_maker_rebate_pool(fee_pool)
    assert rebate == pytest.approx(float(fee_pool) * 0.20, rel=1e-6)


def test_rebate_pool_within_1pct() -> None:
    """AC-1: rebate_pool_i = 0.20 * fee_pool_i within 1%."""
    estimator = IncentiveEstimator()
    # Known values: volume=$10000, price=0.6
    volume = Decimal("10000")
    price = Decimal("0.6")
    fee_pool = estimator.compute_fee_pool(volume, price)
    rebate = estimator.compute_maker_rebate_pool(fee_pool)
    direct = Decimal("0.20") * fee_pool
    assert abs(float(rebate) - float(direct)) / float(direct) < 0.01


def test_estimate_total_no_lr() -> None:
    """When market is not reward-eligible, LR contribution is 0."""
    estimator = IncentiveEstimator()
    result = estimator.estimate(
        market_id="mkt1",
        volume_7d_avg=Decimal("5000"),
        avg_price=Decimal("0.5"),
        n_eff=Decimal("5"),
        historical_fill_rate=Decimal("0.1"),
        lr_pool_per_day=Decimal("0"),
        lr_max_spread=None,
        lr_min_size=None,
        our_spread=Decimal("0.02"),
        our_size=Decimal("50"),
    )
    assert float(result.liquidity_reward_pool_usd) == 0.0
    assert float(result.expected_total_usd) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```
poetry run pytest tests/unit/reward_density/test_incentives.py -v
```
Expected: ImportError for `IncentiveEstimator`.

- [ ] **Step 3: Implement incentives.py**

```python
# services/reward_density/incentives.py
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from services.reward_density.schemas import IncentiveEstimate


def effective_fee_rate(price: Decimal) -> Decimal:
    """Post-March-30 crypto fee formula: price * 0.072 * (price*(1-price))^1."""
    return price * Decimal("0.072") * (price * (Decimal("1") - price))


class IncentiveEstimator:
    """Estimates maker rebates and liquidity rewards for a candidate market."""

    def compute_fee_pool(self, volume_7d_avg: Decimal, avg_price: Decimal) -> Decimal:
        rate = effective_fee_rate(avg_price)
        return volume_7d_avg * rate

    def compute_maker_rebate_pool(self, fee_pool: Decimal) -> Decimal:
        return Decimal("0.20") * fee_pool

    def _expected_maker_share(
        self,
        n_eff: Decimal,
        historical_fill_rate: Optional[Decimal],
    ) -> Decimal:
        """Initial estimate: 1/N_eff; refined by historical fill rate if available."""
        base = Decimal("1") / max(n_eff, Decimal("1"))
        if historical_fill_rate is not None and historical_fill_rate > Decimal("0"):
            # Blend: 50% base, 50% historical
            return (base + historical_fill_rate) / Decimal("2")
        return base

    def _expected_lr_share(
        self,
        n_eff: Decimal,
        lr_max_spread: Optional[Decimal],
        lr_min_size: Optional[Decimal],
        our_spread: Decimal,
        our_size: Decimal,
    ) -> Decimal:
        """1/N_eff if our quotes qualify, else 0."""
        if lr_max_spread is None or lr_min_size is None:
            return Decimal("0")
        if our_spread > lr_max_spread:
            return Decimal("0")
        if our_size < lr_min_size:
            return Decimal("0")
        return Decimal("1") / max(n_eff, Decimal("1"))

    def estimate(
        self,
        market_id: str,
        volume_7d_avg: Decimal,
        avg_price: Decimal,
        n_eff: Decimal,
        historical_fill_rate: Optional[Decimal],
        lr_pool_per_day: Decimal,
        lr_max_spread: Optional[Decimal],
        lr_min_size: Optional[Decimal],
        our_spread: Decimal,
        our_size: Decimal,
        *,
        lookback_days: int = 7,
    ) -> IncentiveEstimate:
        fee_pool = self.compute_fee_pool(volume_7d_avg, avg_price)
        rebate_pool = self.compute_maker_rebate_pool(fee_pool)
        maker_share = self._expected_maker_share(n_eff, historical_fill_rate)

        lr_pool_total = lr_pool_per_day * Decimal(str(lookback_days))
        lr_share = self._expected_lr_share(n_eff, lr_max_spread, lr_min_size, our_spread, our_size)

        expected_rebate = rebate_pool * maker_share
        expected_lr = lr_pool_total * lr_share
        total = expected_rebate + expected_lr

        return IncentiveEstimate(
            market_id=market_id,
            estimated_at=datetime.now(timezone.utc),
            fee_pool_usd=fee_pool,
            maker_rebate_pool_usd=rebate_pool,
            liquidity_reward_pool_usd=lr_pool_total,
            expected_maker_share=maker_share,
            expected_lr_share=lr_share,
            expected_total_usd=total,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```
poetry run pytest tests/unit/reward_density/test_incentives.py -v
```
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add services/reward_density/incentives.py tests/unit/reward_density/test_incentives.py
git commit -m "feat(17-4): incentive estimator with post-March-30 fee formula"
```

---

## Task 5: Risk Scorer

**Files:**
- Create: `services/reward_density/risk_scorer.py`
- Modify: `tests/unit/reward_density/test_analyzer.py`

- [ ] **Step 1: Write the test**

```python
# tests/unit/reward_density/test_analyzer.py
import pytest
from decimal import Decimal

from services.reward_density.risk_scorer import RiskScorer


def test_risk_scorer_zscore_single_market() -> None:
    """Single-market z-score = 0 (no cross-section)."""
    scorer = RiskScorer(lambda_toxicity=Decimal("0.5"))
    scores = scorer.compute_cross_sectional(
        [{"market_id": "mkt1", "btc_rv": Decimal("0.02"), "toxicity": Decimal("0.3")}]
    )
    assert len(scores) == 1
    assert "mkt1" in scores


def test_risk_scorer_relative_ordering() -> None:
    """Higher vol + higher toxicity should yield higher risk score."""
    scorer = RiskScorer(lambda_toxicity=Decimal("0.5"))
    items = [
        {"market_id": "low", "btc_rv": Decimal("0.01"), "toxicity": Decimal("0.05")},
        {"market_id": "high", "btc_rv": Decimal("0.10"), "toxicity": Decimal("0.80")},
    ]
    scores = scorer.compute_cross_sectional(items)
    assert float(scores["high"]) > float(scores["low"])
```

- [ ] **Step 2: Run test to verify it fails**

```
poetry run pytest tests/unit/reward_density/test_analyzer.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement risk_scorer.py**

```python
# services/reward_density/risk_scorer.py
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List


class RiskScorer:
    """Computes cross-sectional risk scores using z-scored vol + toxicity."""

    def __init__(self, lambda_toxicity: Decimal = Decimal("0.5")) -> None:
        self.lambda_toxicity = lambda_toxicity

    @staticmethod
    def _zscore(values: List[Decimal]) -> List[Decimal]:
        if len(values) <= 1:
            return [Decimal("0")] * len(values)
        mean = sum(values) / Decimal(str(len(values)))
        variance = sum((v - mean) ** 2 for v in values) / Decimal(str(len(values)))
        std = variance.sqrt() if variance > Decimal("0") else Decimal("1")
        return [(v - mean) / std for v in values]

    def compute_cross_sectional(
        self,
        items: List[Dict],
    ) -> Dict[str, Decimal]:
        """
        items: list of dicts with keys 'market_id', 'btc_rv', 'toxicity'.
        Returns {market_id: risk_score}.
        """
        if not items:
            return {}

        vols = [item["btc_rv"] for item in items]
        toxicities = [item["toxicity"] for item in items]

        z_vol = self._zscore(vols)
        z_tox = self._zscore(toxicities)

        result: Dict[str, Decimal] = {}
        for item, zv, zt in zip(items, z_vol, z_tox):
            score = zv + self.lambda_toxicity * zt
            result[item["market_id"]] = score
        return result
```

- [ ] **Step 4: Run test to verify it passes**

```
poetry run pytest tests/unit/reward_density/test_analyzer.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/reward_density/risk_scorer.py tests/unit/reward_density/test_analyzer.py
git commit -m "feat(17-5): risk scorer (cross-sectional z-score)"
```

---

## Task 6: Reward Density Analyzer + Sprint 16 Ranker Integration

**Files:**
- Create: `services/reward_density/analyzer.py`
- Modify: `services/ranking/score.py`
- Modify: `services/ranking/schemas.py`
- Modify: `services/ranking/ranker.py`
- Modify: `tests/unit/reward_density/test_analyzer.py`
- Modify: `tests/unit/ranking/test_ranking_score.py`

- [ ] **Step 1: Write analyzer tests**

Append to `tests/unit/reward_density/test_analyzer.py`:

```python
from datetime import datetime, timezone
from services.reward_density.analyzer import RewardDensityAnalyzer
from services.reward_density.schemas import CompetitionMetric, IncentiveEstimate


def _make_competition(n_eff: float, is_estimate: bool = False) -> CompetitionMetric:
    return CompetitionMetric(
        market_id="mkt1",
        computed_at=datetime.now(timezone.utc),
        lookback_days=7,
        hhi=Decimal(str(round(1 / n_eff, 6))),
        n_eff=Decimal(str(n_eff)),
        top_maker_address=None,
        top_maker_share=None,
        data_source="onchain" if not is_estimate else "rewards_api_proxy",
        is_estimate=is_estimate,
    )


def _make_incentive(total: float, rebate: float, lr: float) -> IncentiveEstimate:
    return IncentiveEstimate(
        market_id="mkt1",
        estimated_at=datetime.now(timezone.utc),
        fee_pool_usd=Decimal(str(total * 5)),
        maker_rebate_pool_usd=Decimal(str(rebate * 5)),
        liquidity_reward_pool_usd=Decimal(str(lr * 5)),
        expected_maker_share=Decimal("0.2"),
        expected_lr_share=Decimal("0.1"),
        expected_total_usd=Decimal(str(total)),
    )


def test_analyzer_score_higher_for_better_market() -> None:
    """High volume + low competition → higher score than low vol + high comp (same risk)."""
    analyzer = RewardDensityAnalyzer()
    good = analyzer.score(
        market_id="good",
        incentive=_make_incentive(10.0, 6.0, 4.0),
        competition=_make_competition(n_eff=10.0),
        risk_score=Decimal("0.5"),
    )
    bad = analyzer.score(
        market_id="bad",
        incentive=_make_incentive(2.0, 1.5, 0.5),
        competition=_make_competition(n_eff=1.0),
        risk_score=Decimal("0.5"),
    )
    assert float(good.reward_density_score) > float(bad.reward_density_score)


def test_analyzer_zero_score_no_incentives() -> None:
    """Score = 0 when expected incentives = 0 (AC-3)."""
    analyzer = RewardDensityAnalyzer()
    score = analyzer.score(
        market_id="empty",
        incentive=_make_incentive(0.0, 0.0, 0.0),
        competition=_make_competition(n_eff=5.0),
        risk_score=Decimal("0.5"),
    )
    assert float(score.reward_density_score) == 0.0
```

Write ranker integration tests in `tests/unit/ranking/test_ranking_score.py`:

Append:
```python
def test_composite_score_includes_reward_density() -> None:
    from services.ranking.score import RankingWeights, composite_score
    weights = RankingWeights()  # uses defaults including w_density
    score_with = composite_score(
        ev_adj=Decimal("0.25"),
        sigma=Decimal("2"),
        feasibility=0.5,
        confidence=0.8,
        reward_density=1.0,
        weights=weights,
    )
    score_without = composite_score(
        ev_adj=Decimal("0.25"),
        sigma=Decimal("2"),
        feasibility=0.5,
        confidence=0.8,
        reward_density=0.0,
        weights=weights,
    )
    assert score_with > score_without
```

- [ ] **Step 2: Run tests to verify they fail**

```
poetry run pytest tests/unit/reward_density/test_analyzer.py tests/unit/ranking/test_ranking_score.py -v
```
Expected: Import/assertion errors.

- [ ] **Step 3: Implement analyzer.py**

```python
# services/reward_density/analyzer.py
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from services.reward_density.schemas import CompetitionMetric, IncentiveEstimate, RewardDensityScore


class RewardDensityAnalyzer:
    """Computes the composite reward density score for a candidate market."""

    def __init__(
        self,
        alpha: Decimal = Decimal("1.0"),
        beta: Decimal = Decimal("0.5"),
    ) -> None:
        self.alpha = alpha
        self.beta = beta

    def score(
        self,
        market_id: str,
        incentive: IncentiveEstimate,
        competition: CompetitionMetric,
        risk_score: Decimal,
    ) -> RewardDensityScore:
        incentives = incentive.expected_total_usd
        n_eff = competition.n_eff

        if incentives <= Decimal("0"):
            density = Decimal("0")
        else:
            # Score = E[Incentives] / (Competition^alpha * Risk^beta)
            # Risk must be positive; clip to 1e-6
            safe_risk = max(risk_score, Decimal("0.000001"))
            # n_eff as competition proxy
            denom = (n_eff ** self.alpha) * (safe_risk ** self.beta)
            density = incentives / denom if denom > Decimal("0") else Decimal("0")

        confidence: str
        if not competition.is_estimate:
            confidence = "high"
        elif competition.is_estimate and float(n_eff) > 1:
            confidence = "medium"
        else:
            confidence = "low"

        return RewardDensityScore(
            market_id=market_id,
            scored_at=datetime.now(timezone.utc),
            expected_incentives_usd=incentives,
            maker_rebate_estimate=incentive.expected_maker_share * incentive.maker_rebate_pool_usd,
            liquidity_reward_estimate=incentive.expected_lr_share * incentive.liquidity_reward_pool_usd,
            competition=n_eff,
            risk_score=risk_score,
            reward_density_score=density,
            alpha=self.alpha,
            beta=self.beta,
            confidence=confidence,  # type: ignore[arg-type]
        )
```

- [ ] **Step 4: Update score.py to add 5th weight term**

Replace the content of `services/ranking/score.py`:

```python
# services/ranking/score.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RankingWeights:
    """Composite score weights. Sprint 17 adds w_density (w_D = 0.15)."""

    ev: float = 0.34
    risk: float = 0.255
    liquidity: float = 0.17
    confidence: float = 0.085
    density: float = 0.15


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def composite_score(
    *,
    ev_adj: Decimal | float,
    sigma: Decimal | float,
    feasibility: float,
    confidence: float,
    reward_density: float = 0.0,
    weights: RankingWeights | None = None,
) -> float:
    """Compute the cross-sectional ranking score (Sprint 17: adds density term)."""

    weight = weights or RankingWeights()
    ev = float(ev_adj)
    if ev < 0.0:
        return 0.0

    sigma_value = max(float(sigma), 1e-9)
    feasibility_value = _clamp(float(feasibility))
    confidence_value = _clamp(float(confidence))
    density_value = max(float(reward_density), 0.0)

    return (
        weight.ev * ev
        + weight.risk * (ev / sigma_value)
        + weight.liquidity * feasibility_value
        + weight.confidence * confidence_value
        + weight.density * density_value
    )
```

- [ ] **Step 5: Update schemas.py — add reward_density_score to MarketScore**

In `services/ranking/schemas.py`, add to the `MarketScore` class (after `exclusion_reason`):

```python
    reward_density_score: float = 0.0
```

- [ ] **Step 6: Update ranker.py — pass reward_density_score to composite_score**

In `services/ranking/ranker.py`, modify `score_candidate`:

```python
    def score_candidate(
        self,
        candidate: CandidateMarket,
        reward_density: float = 0.0,
    ) -> MarketScore:
        edge = self._edge_estimator.estimate(candidate)
        feasibility = self._feasibility_scorer.score(candidate)
        sigma = float(candidate.sigma)
        confidence = float(candidate.confidence)
        score = composite_score(
            ev_adj=edge.ev_adj,
            sigma=sigma,
            feasibility=feasibility.feasibility_score,
            confidence=confidence,
            reward_density=reward_density,
            weights=self._weights,
        )
        excluded = feasibility.exclude or edge.ev_adj < 0
        exclusion_reason = feasibility.exclusion_reason
        if edge.ev_adj < 0:
            exclusion_reason = "negative_ev"
        return MarketScore(
            candidate=candidate,
            edge=edge,
            feasibility=feasibility,
            sigma=sigma,
            confidence=confidence,
            score=score,
            reward_density_score=reward_density,
            selected=False,
            excluded=excluded,
            exclusion_reason=exclusion_reason,
        )
```

- [ ] **Step 7: Run all ranking + analyzer tests**

```
poetry run pytest tests/unit/reward_density/ tests/unit/ranking/ -v
```
Expected: All PASS.

- [ ] **Step 8: Commit**

```bash
git add services/reward_density/analyzer.py \
        services/ranking/score.py services/ranking/schemas.py services/ranking/ranker.py \
        tests/unit/reward_density/test_analyzer.py tests/unit/ranking/test_ranking_score.py
git commit -m "feat(17-6): reward density analyzer + ranker integration (5th weight term)"
```

---

## Task 7: Wallet Intelligence Schemas

**Files:**
- Create: `services/wallet_intelligence/__init__.py`
- Create: `services/wallet_intelligence/schemas.py`
- Create: `tests/unit/wallet_intelligence/__init__.py`

- [ ] **Step 1: Write test**

```python
# tests/unit/wallet_intelligence/__init__.py  (empty)

# tests/unit/wallet_intelligence/test_clustering.py
from datetime import datetime, timezone
from decimal import Decimal

from services.wallet_intelligence.schemas import WalletProfile, WalletSignal


def test_wallet_profile_fields() -> None:
    p = WalletProfile(
        wallet_address="0xABC",
        profiled_at=datetime.now(timezone.utc),
        total_volume_usd=Decimal("50000"),
        total_pnl_usd=Decimal("1000"),
        win_rate=Decimal("0.55"),
        avg_position_size=Decimal("200"),
        preferred_markets=["cond1", "cond2"],
        role="maker",
        activity_hours=[9, 10, 11],
        last_active_at=datetime.now(timezone.utc),
    )
    assert p.role == "maker"
    assert len(p.preferred_markets) == 2


def test_wallet_signal_consensus_range() -> None:
    sig = WalletSignal(
        market_id="mkt1",
        computed_at=datetime.now(timezone.utc),
        net_smart_money_position=Decimal("500"),
        smart_money_consensus=Decimal("0.4"),
        smart_money_activity_zscore=Decimal("1.8"),
        top_wallet_direction="long",
        signal_confidence=Decimal("0.75"),
        wallet_count=5,
    )
    assert sig.smart_money_consensus == Decimal("0.4")
    assert sig.top_wallet_direction == "long"
```

- [ ] **Step 2: Run test to verify it fails**

```
poetry run pytest tests/unit/wallet_intelligence/test_clustering.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create schemas**

```python
# services/wallet_intelligence/__init__.py
```

```python
# services/wallet_intelligence/schemas.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel


class WalletProfile(BaseModel):
    wallet_address: str
    profiled_at: datetime
    total_volume_usd: Decimal
    total_pnl_usd: Decimal
    win_rate: Decimal
    avg_position_size: Decimal
    preferred_markets: List[str]
    role: Literal["maker", "taker", "mixed"]
    activity_hours: List[int]
    last_active_at: datetime
    cluster_id: Optional[int] = None


class WalletCluster(BaseModel):
    cluster_id: int
    label: Literal["informed_directionals", "efficient_makers", "noise_traders", "opportunists"]
    wallet_count: int
    avg_maker_fraction: Decimal
    avg_win_rate: Decimal


class WalletSignal(BaseModel):
    market_id: str
    computed_at: datetime
    net_smart_money_position: Decimal
    smart_money_consensus: Decimal       # -1 to +1
    smart_money_activity_zscore: Decimal
    top_wallet_direction: Optional[Literal["long", "short", "flat"]] = None
    signal_confidence: Decimal
    wallet_count: int
```

- [ ] **Step 4: Run test to verify it passes**

```
poetry run pytest tests/unit/wallet_intelligence/test_clustering.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/wallet_intelligence/__init__.py services/wallet_intelligence/schemas.py \
        tests/unit/wallet_intelligence/__init__.py tests/unit/wallet_intelligence/test_clustering.py
git commit -m "feat(17-7): wallet intelligence schemas"
```

---

## Task 8: Wallet Profiler + Ranker

**Files:**
- Create: `services/wallet_intelligence/profiler.py`
- Create: `services/wallet_intelligence/ranker.py`
- Modify: `tests/unit/wallet_intelligence/test_clustering.py`

- [ ] **Step 1: Write tests**

Append to `tests/unit/wallet_intelligence/test_clustering.py`:

```python
from services.wallet_intelligence.profiler import WalletProfiler
from services.wallet_intelligence.ranker import WalletRanker
from services.reward_density.onchain.polygon_client import OrderFilledEvent


def _make_fill_event(maker: str, maker_amount: int, fee: int) -> OrderFilledEvent:
    return OrderFilledEvent(
        maker=maker,
        taker="0x0",
        maker_asset_id="111",
        taker_asset_id="222",
        maker_amount_filled=maker_amount,
        taker_amount_filled=maker_amount - 10,
        fee=fee,
        block_number=100,
        tx_hash="0x" + "bb" * 32,
    )


def test_profiler_role_maker() -> None:
    """AC-4: role='maker' when maker_fraction > 0.70."""
    profiler = WalletProfiler()
    fills = [_make_fill_event("0xA", 1000, 10) for _ in range(8)]  # 8 maker fills
    # 2 taker fills (swap maker/taker)
    taker_fills = [
        OrderFilledEvent(
            maker="0xB",
            taker="0xA",
            maker_asset_id="111",
            taker_asset_id="222",
            maker_amount_filled=500,
            taker_amount_filled=490,
            fee=5,
            block_number=101,
            tx_hash="0x" + "cc" * 32,
        )
        for _ in range(2)
    ]
    profile = profiler.build_from_events(
        wallet_address="0xA",
        maker_fills=fills,
        taker_fills=taker_fills,
        pnl_usd=Decimal("200"),
        total_volume_usd=Decimal("10000"),
    )
    assert profile.role == "maker"


def test_ranker_top_wallets() -> None:
    from datetime import datetime, timedelta, timezone

    ranker = WalletRanker()
    # Build fake weekly PnL series
    base = Decimal("100")
    daily_pnls = [base + Decimal(str(i * 10)) for i in range(7)]
    score = ranker.compute_wallet_score(daily_pnls_7d=daily_pnls, active_days_7d=7)
    assert score > Decimal("0")
```

- [ ] **Step 2: Run test to verify it fails**

```
poetry run pytest tests/unit/wallet_intelligence/test_clustering.py -v
```
Expected: ImportError for profiler/ranker.

- [ ] **Step 3: Implement profiler.py**

```python
# services/wallet_intelligence/profiler.py
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from services.reward_density.onchain.polygon_client import OrderFilledEvent
from services.wallet_intelligence.schemas import WalletProfile


class WalletProfiler:
    """Builds WalletProfile from on-chain maker/taker fills."""

    def build_from_events(
        self,
        wallet_address: str,
        maker_fills: List[OrderFilledEvent],
        taker_fills: List[OrderFilledEvent],
        *,
        pnl_usd: Decimal,
        total_volume_usd: Decimal,
    ) -> WalletProfile:
        total_fills = len(maker_fills) + len(taker_fills)
        maker_fraction = (
            Decimal(str(len(maker_fills))) / Decimal(str(total_fills))
            if total_fills > 0
            else Decimal("0")
        )

        if maker_fraction > Decimal("0.70"):
            role = "maker"
        elif maker_fraction < Decimal("0.30"):
            role = "taker"
        else:
            role = "mixed"

        all_fills = maker_fills + taker_fills
        win_count = sum(1 for f in maker_fills if f.taker_amount_filled >= f.maker_amount_filled)
        win_rate = (
            Decimal(str(win_count)) / Decimal(str(len(maker_fills)))
            if len(maker_fills) > 0
            else Decimal("0")
        )

        all_amounts = [f.maker_amount_filled for f in all_fills]
        avg_size = (
            Decimal(str(sum(all_amounts) // len(all_amounts)))
            if all_amounts
            else Decimal("0")
        )

        condition_ids = list({str(f.maker_asset_id) for f in all_fills})[:5]

        now = datetime.now(timezone.utc)
        return WalletProfile(
            wallet_address=wallet_address,
            profiled_at=now,
            total_volume_usd=total_volume_usd,
            total_pnl_usd=pnl_usd,
            win_rate=win_rate,
            avg_position_size=avg_size,
            preferred_markets=condition_ids,
            role=role,  # type: ignore[arg-type]
            activity_hours=[],
            last_active_at=now,
        )
```

- [ ] **Step 4: Implement ranker.py**

```python
# services/wallet_intelligence/ranker.py
from __future__ import annotations

from decimal import Decimal
from typing import List


class WalletRanker:
    """Ranks wallets by risk-adjusted PnL consistency."""

    def compute_wallet_score(
        self,
        daily_pnls_7d: List[Decimal],
        active_days_7d: int,
    ) -> Decimal:
        """WalletScore = PnL_7d / max(StdDev, ε) * sqrt(active_days)."""
        if not daily_pnls_7d:
            return Decimal("0")

        pnl_7d = sum(daily_pnls_7d)
        n = Decimal(str(len(daily_pnls_7d)))
        mean = pnl_7d / n
        variance = sum((p - mean) ** 2 for p in daily_pnls_7d) / n
        std = variance.sqrt() if variance > Decimal("0") else Decimal("0.0001")
        eps = Decimal("0.0001")
        active = Decimal(str(max(active_days_7d, 1)))

        return (pnl_7d / max(std, eps)) * active.sqrt()
```

- [ ] **Step 5: Run tests to verify they pass**

```
poetry run pytest tests/unit/wallet_intelligence/test_clustering.py -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add services/wallet_intelligence/profiler.py services/wallet_intelligence/ranker.py \
        tests/unit/wallet_intelligence/test_clustering.py
git commit -m "feat(17-8): wallet profiler and ranker"
```

---

## Task 9: Wallet Clustering

**Files:**
- Create: `services/wallet_intelligence/clustering.py`
- Modify: `tests/unit/wallet_intelligence/test_clustering.py`

- [ ] **Step 1: Write tests**

Append to `tests/unit/wallet_intelligence/test_clustering.py`:

```python
from services.wallet_intelligence.clustering import WalletClusterer


def test_clustering_stable_with_same_seed() -> None:
    """AC-5: same seed → identical cluster assignments."""
    import numpy as np

    clusterer = WalletClusterer(n_clusters=4, random_state=42)
    # 12 synthetic wallets with 5 features each
    np.random.seed(99)
    feature_matrix = np.random.rand(12, 5).tolist()
    wallet_ids = [f"0x{i:02X}" for i in range(12)]

    assignments_1 = clusterer.fit_predict(feature_matrix, wallet_ids)
    assignments_2 = clusterer.fit_predict(feature_matrix, wallet_ids)
    assert assignments_1 == assignments_2


def test_clustering_produces_four_clusters() -> None:
    import numpy as np

    clusterer = WalletClusterer(n_clusters=4, random_state=42)
    np.random.seed(0)
    # 20 wallets with 5 features
    features = np.random.rand(20, 5).tolist()
    wallet_ids = [f"0x{i:02X}" for i in range(20)]
    assignments = clusterer.fit_predict(features, wallet_ids)
    cluster_ids = set(assignments.values())
    assert len(cluster_ids) == 4
```

- [ ] **Step 2: Run test to verify it fails**

```
poetry run pytest tests/unit/wallet_intelligence/test_clustering.py::test_clustering_stable_with_same_seed -v
```
Expected: ImportError.

- [ ] **Step 3: Implement clustering.py**

```python
# services/wallet_intelligence/clustering.py
from __future__ import annotations

from typing import Dict, List, Literal

from sklearn.cluster import KMeans


CLUSTER_LABELS: Dict[int, str] = {
    0: "informed_directionals",
    1: "efficient_makers",
    2: "noise_traders",
    3: "opportunists",
}


class WalletClusterer:
    """K-Means clustering on wallet feature vectors (k=4)."""

    def __init__(self, n_clusters: int = 4, random_state: int = 42) -> None:
        self.n_clusters = n_clusters
        self.random_state = random_state
        self._kmeans: KMeans | None = None

    def fit_predict(
        self,
        feature_matrix: List[List[float]],
        wallet_ids: List[str],
    ) -> Dict[str, int]:
        """Fit KMeans and return {wallet_id: cluster_id}."""
        km = KMeans(n_clusters=self.n_clusters, random_state=self.random_state, n_init=10)
        labels = km.fit_predict(feature_matrix)
        self._kmeans = km
        return {wid: int(label) for wid, label in zip(wallet_ids, labels)}

    def cluster_label(self, cluster_id: int) -> str:
        return CLUSTER_LABELS.get(cluster_id, "noise_traders")
```

- [ ] **Step 4: Run tests to verify they pass**

```
poetry run pytest tests/unit/wallet_intelligence/test_clustering.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/wallet_intelligence/clustering.py tests/unit/wallet_intelligence/test_clustering.py
git commit -m "feat(17-9): wallet clustering (KMeans k=4)"
```

---

## Task 10: Wallet Signal Extractor

**Files:**
- Create: `services/wallet_intelligence/signals.py`
- Modify: `tests/unit/wallet_intelligence/test_clustering.py` (or a new file)

Actually create a new file to keep it focused:

- Create: `tests/unit/wallet_intelligence/test_signals.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/wallet_intelligence/test_signals.py
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from services.wallet_intelligence.signals import WalletSignalExtractor
from services.reward_density.onchain.polygon_client import OrderFilledEvent


SMART_MONEY = {"0xA", "0xB", "0xC"}


def _fill(maker: str, amount: int, maker_side: bool = True) -> OrderFilledEvent:
    return OrderFilledEvent(
        maker=maker if maker_side else "0xOther",
        taker="0xOther" if maker_side else maker,
        maker_asset_id="YES_TOKEN",
        taker_asset_id="NO_TOKEN",
        maker_amount_filled=amount,
        taker_amount_filled=amount - 5,
        fee=1,
        block_number=1,
        tx_hash="0x" + "aa" * 32,
    )


def test_signal_consensus_bullish_when_net_long() -> None:
    """AC-6: consensus > 0.3 when smart money predominantly net long."""
    extractor = WalletSignalExtractor(smart_money_addresses=SMART_MONEY)
    fills = [_fill("0xA", 1000), _fill("0xB", 800), _fill("0xC", 600)]
    sig = extractor.compute(
        market_id="mkt1",
        recent_fills=fills,
        asset_id_yes="YES_TOKEN",
    )
    assert float(sig.smart_money_consensus) > 0.3


def test_signal_confidence_low_when_few_wallets() -> None:
    """AC-6: signal_confidence is low when fewer than 3 wallets contribute."""
    extractor = WalletSignalExtractor(smart_money_addresses=SMART_MONEY)
    fills = [_fill("0xA", 100)]  # only 1 wallet
    sig = extractor.compute(
        market_id="mkt1",
        recent_fills=fills,
        asset_id_yes="YES_TOKEN",
    )
    assert float(sig.signal_confidence) < 0.5
    assert sig.wallet_count == 1


def test_signal_zero_no_fills() -> None:
    extractor = WalletSignalExtractor(smart_money_addresses=SMART_MONEY)
    sig = extractor.compute(
        market_id="mkt1",
        recent_fills=[],
        asset_id_yes="YES_TOKEN",
    )
    assert float(sig.smart_money_consensus) == 0.0
    assert sig.wallet_count == 0
```

- [ ] **Step 2: Run test to verify it fails**

```
poetry run pytest tests/unit/wallet_intelligence/test_signals.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement signals.py**

```python
# services/wallet_intelligence/signals.py
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Set

from services.reward_density.onchain.polygon_client import OrderFilledEvent
from services.wallet_intelligence.schemas import WalletSignal


class WalletSignalExtractor:
    """Extracts smart-money consensus signals from recent OrderFilled events."""

    def __init__(self, smart_money_addresses: Set[str]) -> None:
        self.smart_money_addresses = {addr.lower() for addr in smart_money_addresses}

    def compute(
        self,
        market_id: str,
        recent_fills: List[OrderFilledEvent],
        asset_id_yes: str,
    ) -> WalletSignal:
        now = datetime.now(timezone.utc)

        # Filter to smart money
        sm_fills = [
            f for f in recent_fills
            if f.maker.lower() in self.smart_money_addresses
            or f.taker.lower() in self.smart_money_addresses
        ]

        if not sm_fills:
            return WalletSignal(
                market_id=market_id,
                computed_at=now,
                net_smart_money_position=Decimal("0"),
                smart_money_consensus=Decimal("0"),
                smart_money_activity_zscore=Decimal("0"),
                top_wallet_direction=None,
                signal_confidence=Decimal("0"),
                wallet_count=0,
            )

        # Net position: positive = net YES (bullish)
        net_by_wallet: dict[str, int] = defaultdict(int)
        for f in sm_fills:
            maker_lower = f.maker.lower()
            taker_lower = f.taker.lower()
            if maker_lower in self.smart_money_addresses:
                # maker providing YES liquidity = long YES if makerAssetId is YES
                sign = 1 if str(f.maker_asset_id) == asset_id_yes else -1
                net_by_wallet[maker_lower] += sign * f.maker_amount_filled
            if taker_lower in self.smart_money_addresses:
                sign = -1 if str(f.taker_asset_id) == asset_id_yes else 1
                net_by_wallet[taker_lower] += sign * f.taker_amount_filled

        wallet_count = len(net_by_wallet)
        net_total = sum(net_by_wallet.values())

        # Normalize to [-1, +1]
        max_abs = max(abs(v) for v in net_by_wallet.values()) if net_by_wallet else 1
        consensus = Decimal(str(net_total)) / Decimal(str(max_abs)) if max_abs > 0 else Decimal("0")
        consensus = max(Decimal("-1"), min(Decimal("1"), consensus))

        # Confidence: scales with wallet count (low < 3, high >= 5)
        if wallet_count == 0:
            confidence = Decimal("0")
        elif wallet_count < 3:
            confidence = Decimal("0.3")
        elif wallet_count < 5:
            confidence = Decimal("0.6")
        else:
            confidence = Decimal("0.9")

        direction = None
        if consensus > Decimal("0.1"):
            direction = "long"
        elif consensus < Decimal("-0.1"):
            direction = "short"
        else:
            direction = "flat"

        return WalletSignal(
            market_id=market_id,
            computed_at=now,
            net_smart_money_position=Decimal(str(net_total)),
            smart_money_consensus=consensus,
            smart_money_activity_zscore=Decimal("0"),  # rolling baseline not tracked yet
            top_wallet_direction=direction,  # type: ignore[arg-type]
            signal_confidence=confidence,
            wallet_count=wallet_count,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```
poetry run pytest tests/unit/wallet_intelligence/test_signals.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/wallet_intelligence/signals.py tests/unit/wallet_intelligence/test_signals.py
git commit -m "feat(17-10): wallet signal extractor (smart-money consensus)"
```

---

## Task 11: Signal Aggregation Schemas + Aggregator

**Files:**
- Create: `services/signal_aggregation/__init__.py`
- Create: `services/signal_aggregation/schemas.py`
- Create: `services/signal_aggregation/weighter.py`
- Create: `services/signal_aggregation/aggregator.py`
- Create: `tests/unit/signal_aggregation/__init__.py`
- Create: `tests/unit/signal_aggregation/test_aggregator.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/signal_aggregation/__init__.py  (empty)

# tests/unit/signal_aggregation/test_aggregator.py
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from services.signal_aggregation.aggregator import SignalAggregator
from services.signal_aggregation.schemas import AggregatedSignal
from services.signal_aggregation.weighter import SignalWeighter


def test_final_signal_zero_when_all_components_zero() -> None:
    """AC-7: FinalSignal = 0 when all components are 0."""
    agg = SignalAggregator()
    result = agg.aggregate(
        market_id="mkt1",
        model_signal=Decimal("0"),
        wallet_signal=Decimal("0"),
        microstructure_signal=Decimal("0"),
        history=[
            {"model": Decimal("0"), "wallet": Decimal("0"), "micro": Decimal("0")}
        ] * 5,
    )
    assert float(result.final_signal) == pytest.approx(0.0, abs=1e-9)


def test_aggregator_applies_zscoring() -> None:
    """AC-7: z-scoring normalises components before weighting."""
    # History with clear mean/std
    history = [
        {"model": Decimal(str(i)), "wallet": Decimal("0"), "micro": Decimal("0")}
        for i in range(-5, 6)
    ]
    agg = SignalAggregator()
    result = agg.aggregate(
        market_id="mkt1",
        model_signal=Decimal("5"),
        wallet_signal=Decimal("0"),
        microstructure_signal=Decimal("0"),
        history=history,
    )
    # z-scored model signal should be (5 - mean) / std where mean≈0, std≈√10
    model_mean = sum(range(-5, 6)) / 11  # = 0
    model_std = (sum(i**2 for i in range(-5, 6)) / 11) ** 0.5
    expected_z_model = (5 - model_mean) / model_std
    weights = {"model": 0.50, "wallet": 0.30, "micro": 0.20}
    expected_final = expected_z_model * weights["model"]
    assert float(result.model_component) == pytest.approx(expected_z_model, rel=0.05)


def test_weight_learning_increases_better_predictor() -> None:
    """AC-7: weight learning increases w1 when ModelSignal has higher predictive power."""
    weighter = SignalWeighter(
        initial_weights={"model": Decimal("0.50"), "wallet": Decimal("0.30"), "micro": Decimal("0.20")}
    )
    # Simulate: model perfectly predicted 5-min moves, wallet/micro did not
    correlation_scores = {"model": Decimal("0.8"), "wallet": Decimal("0.1"), "micro": Decimal("0.1")}
    new_weights = weighter.update(correlation_scores)
    assert new_weights["model"] > Decimal("0.50")
    assert new_weights["model"] <= Decimal("0.70")  # bounded


def test_aggregated_signal_threshold_met() -> None:
    agg = SignalAggregator(threshold=Decimal("0.3"))
    result = agg.aggregate(
        market_id="mkt1",
        model_signal=Decimal("10"),
        wallet_signal=Decimal("10"),
        microstructure_signal=Decimal("10"),
        history=[{"model": Decimal("0"), "wallet": Decimal("0"), "micro": Decimal("0")}] * 5,
    )
    assert result.threshold_met is True
```

- [ ] **Step 2: Run tests to verify they fail**

```
poetry run pytest tests/unit/signal_aggregation/test_aggregator.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement schemas.py**

```python
# services/signal_aggregation/__init__.py
```

```python
# services/signal_aggregation/schemas.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, Literal

from pydantic import BaseModel


class AggregatedSignal(BaseModel):
    market_id: str
    aggregated_at: datetime
    final_signal: Decimal         # -1 to +1; positive = bullish
    model_component: Decimal      # z-scored
    wallet_component: Decimal     # z-scored
    microstructure_component: Decimal  # z-scored
    weights: Dict[str, Decimal]
    threshold_met: bool
    signal_strength: Literal["strong", "moderate", "weak", "none"]
```

- [ ] **Step 4: Implement weighter.py**

```python
# services/signal_aggregation/weighter.py
from __future__ import annotations

from decimal import Decimal
from typing import Dict

WEIGHT_MIN = Decimal("0.10")
WEIGHT_MAX = Decimal("0.70")
MAX_WEEKLY_CHANGE = Decimal("0.05")


class SignalWeighter:
    """Updates composite signal weights based on recent predictive power."""

    def __init__(
        self,
        initial_weights: Dict[str, Decimal] | None = None,
    ) -> None:
        self.weights: Dict[str, Decimal] = initial_weights or {
            "model": Decimal("0.50"),
            "wallet": Decimal("0.30"),
            "micro": Decimal("0.20"),
        }

    def update(self, correlation_scores: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """
        Shift weights toward components with higher recent correlation.
        Bounded per component, max weekly change = 0.05.
        """
        total_corr = sum(correlation_scores.values())
        if total_corr <= Decimal("0"):
            return dict(self.weights)

        new_weights: Dict[str, Decimal] = {}
        for key in self.weights:
            target_share = correlation_scores.get(key, Decimal("0")) / total_corr
            current = self.weights[key]
            delta = (target_share - current).copy_sign(target_share - current)
            # Cap weekly change
            capped_delta = min(abs(delta), MAX_WEEKLY_CHANGE)
            if target_share > current:
                new_w = current + capped_delta
            else:
                new_w = current - capped_delta
            new_weights[key] = max(WEIGHT_MIN, min(WEIGHT_MAX, new_w))

        # Re-normalize to sum to 1.0
        total = sum(new_weights.values())
        self.weights = {k: v / total for k, v in new_weights.items()}
        return dict(self.weights)
```

- [ ] **Step 5: Implement aggregator.py**

```python
# services/signal_aggregation/aggregator.py
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Literal

from services.signal_aggregation.schemas import AggregatedSignal
from services.signal_aggregation.weighter import SignalWeighter


def _zscore_value(value: Decimal, history: List[Decimal]) -> Decimal:
    """Z-score a single value against a list of historical values."""
    if len(history) < 2:
        return Decimal("0")
    n = Decimal(str(len(history)))
    mean = sum(history) / n
    variance = sum((h - mean) ** 2 for h in history) / n
    std = variance.sqrt() if variance > Decimal("0") else Decimal("1")
    return (value - mean) / std


class SignalAggregator:
    """Combines model, wallet, and microstructure signals into a composite."""

    def __init__(
        self,
        weighter: SignalWeighter | None = None,
        threshold: Decimal = Decimal("0.3"),
    ) -> None:
        self._weighter = weighter or SignalWeighter()
        self.threshold = threshold

    def aggregate(
        self,
        market_id: str,
        model_signal: Decimal,
        wallet_signal: Decimal,
        microstructure_signal: Decimal,
        history: List[Dict[str, Decimal]],
    ) -> AggregatedSignal:
        """
        history: list of dicts with keys 'model', 'wallet', 'micro'
                 (rolling window of past values for z-scoring).
        """
        model_hist = [h["model"] for h in history]
        wallet_hist = [h["wallet"] for h in history]
        micro_hist = [h["micro"] for h in history]

        z_model = _zscore_value(model_signal, model_hist)
        z_wallet = _zscore_value(wallet_signal, wallet_hist)
        z_micro = _zscore_value(microstructure_signal, micro_hist)

        w = self._weighter.weights
        w1 = w.get("model", Decimal("0.50"))
        w2 = w.get("wallet", Decimal("0.30"))
        w3 = w.get("micro", Decimal("0.20"))

        final = w1 * z_model + w2 * z_wallet + w3 * z_micro
        final = max(Decimal("-1"), min(Decimal("1"), final))

        abs_final = abs(float(final))
        if abs_final >= 0.7:
            strength: Literal["strong", "moderate", "weak", "none"] = "strong"
        elif abs_final >= 0.4:
            strength = "moderate"
        elif abs_final >= float(self.threshold):
            strength = "weak"
        else:
            strength = "none"

        return AggregatedSignal(
            market_id=market_id,
            aggregated_at=datetime.now(timezone.utc),
            final_signal=final,
            model_component=z_model,
            wallet_component=z_wallet,
            microstructure_component=z_micro,
            weights={"model": w1, "wallet": w2, "micro": w3},
            threshold_met=abs(float(final)) >= float(self.threshold),
            signal_strength=strength,
        )
```

- [ ] **Step 6: Run tests to verify they pass**

```
poetry run pytest tests/unit/signal_aggregation/test_aggregator.py -v
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add services/signal_aggregation/ tests/unit/signal_aggregation/
git commit -m "feat(17-11): signal aggregation layer (z-score, weight learning)"
```

---

## Task 12: Model Lifecycle Manager

**Files:**
- Create: `services/fleet/lifecycle.py`
- Create: `tests/unit/fleet/__init__.py`
- Create: `tests/unit/fleet/test_lifecycle.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/fleet/__init__.py  (empty)

# tests/unit/fleet/test_lifecycle.py
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from services.fleet.lifecycle import (
    LifecycleAction,
    LifecycleManager,
    LifecycleRule,
    StrategyEvaluationSnapshot,
)


def _make_snapshot(
    strategy_id: str,
    sharpe_7d: float,
    drawdown_7d: float,
    active_days: int = 30,
    win_rate: float = 0.60,
    max_drawdown: float = 0.10,
    is_live: bool = False,
    paused_days: int = 0,
) -> StrategyEvaluationSnapshot:
    return StrategyEvaluationSnapshot(
        strategy_id=strategy_id,
        sharpe_7d=Decimal(str(sharpe_7d)),
        drawdown_7d=Decimal(str(drawdown_7d)),
        active_paper_days=active_days,
        win_rate=Decimal(str(win_rate)),
        max_drawdown=Decimal(str(max_drawdown)),
        is_live=is_live,
        paused_days=paused_days,
    )


def test_pause_rule_triggers_on_low_sharpe() -> None:
    """AC-8: PAUSE auto-triggers when Sharpe < -0.5."""
    manager = LifecycleManager()
    snapshot = _make_snapshot("strat1", sharpe_7d=-0.8, drawdown_7d=0.10)
    events = manager.evaluate([snapshot])
    pause_events = [e for e in events if e.action == LifecycleAction.PAUSE and e.strategy_id == "strat1"]
    assert len(pause_events) == 1
    assert pause_events[0].requires_human_approval is False


def test_pause_rule_triggers_on_high_drawdown() -> None:
    """AC-8: PAUSE auto-triggers when 7d drawdown > 0.20."""
    manager = LifecycleManager()
    snapshot = _make_snapshot("strat1", sharpe_7d=0.5, drawdown_7d=0.25)
    events = manager.evaluate([snapshot])
    pause_events = [e for e in events if e.action == LifecycleAction.PAUSE and e.strategy_id == "strat1"]
    assert len(pause_events) == 1


def test_promote_rule_creates_pending_not_auto() -> None:
    """AC-8: PROMOTE creates pending notification, does NOT auto-execute."""
    manager = LifecycleManager()
    snapshot = _make_snapshot(
        "strat2",
        sharpe_7d=1.2,
        drawdown_7d=0.05,
        active_days=35,
        win_rate=0.60,
        max_drawdown=0.10,
    )
    events = manager.evaluate([snapshot])
    promote_events = [e for e in events if e.action == LifecycleAction.PROMOTE]
    assert len(promote_events) == 1
    assert promote_events[0].requires_human_approval is True
    assert promote_events[0].auto_executed is False


def test_demote_rule_triggers_on_live_drawdown() -> None:
    """AC-8: DEMOTE auto-triggers when live strategy drawdown > 0.15."""
    manager = LifecycleManager()
    snapshot = _make_snapshot("live_strat", sharpe_7d=0.8, drawdown_7d=0.18, is_live=True)
    events = manager.evaluate([snapshot])
    demote_events = [e for e in events if e.action == LifecycleAction.DEMOTE]
    assert len(demote_events) == 1
    assert demote_events[0].requires_human_approval is False


def test_no_action_for_healthy_strategy() -> None:
    manager = LifecycleManager()
    snapshot = _make_snapshot("healthy", sharpe_7d=1.5, drawdown_7d=0.05)
    events = manager.evaluate([snapshot])
    assert events == []
```

- [ ] **Step 2: Run tests to verify they fail**

```
poetry run pytest tests/unit/fleet/test_lifecycle.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement lifecycle.py**

```python
# services/fleet/lifecycle.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class LifecycleAction(str, Enum):
    PROMOTE = "promote"
    PAUSE = "pause"
    RETIRE = "retire"
    CLONE = "clone"
    DEMOTE = "demote"


@dataclass
class StrategyEvaluationSnapshot:
    strategy_id: str
    sharpe_7d: Decimal
    drawdown_7d: Decimal
    active_paper_days: int
    win_rate: Decimal
    max_drawdown: Decimal
    is_live: bool = False
    paused_days: int = 0


@dataclass
class LifecycleEvent:
    strategy_id: str
    action: LifecycleAction
    rule_id: str
    triggered_at: datetime
    requires_human_approval: bool
    auto_executed: bool
    notes: str = ""


class LifecycleManager:
    """Evaluates lifecycle rules and produces LifecycleEvents."""

    def evaluate(
        self,
        snapshots: List[StrategyEvaluationSnapshot],
    ) -> List[LifecycleEvent]:
        now = datetime.now(timezone.utc)
        events: List[LifecycleEvent] = []

        for snap in snapshots:
            # DEMOTE: live strategy with 7d drawdown > 0.15 (auto)
            if snap.is_live and snap.drawdown_7d > Decimal("0.15"):
                events.append(
                    LifecycleEvent(
                        strategy_id=snap.strategy_id,
                        action=LifecycleAction.DEMOTE,
                        rule_id="demote_live_drawdown",
                        triggered_at=now,
                        requires_human_approval=False,
                        auto_executed=True,
                        notes=f"Live drawdown {snap.drawdown_7d} > 0.15",
                    )
                )
                continue  # demoted strategies skip other rules

            # PAUSE: 7d Sharpe < -0.5 OR 7d drawdown > 0.20 (auto)
            if snap.sharpe_7d < Decimal("-0.5") or snap.drawdown_7d > Decimal("0.20"):
                events.append(
                    LifecycleEvent(
                        strategy_id=snap.strategy_id,
                        action=LifecycleAction.PAUSE,
                        rule_id="pause_underperformer",
                        triggered_at=now,
                        requires_human_approval=False,
                        auto_executed=True,
                        notes=f"Sharpe={snap.sharpe_7d}, Drawdown={snap.drawdown_7d}",
                    )
                )
                continue

            # RETIRE: paused > 14 days with no improvement (human approval)
            if snap.paused_days > 14:
                events.append(
                    LifecycleEvent(
                        strategy_id=snap.strategy_id,
                        action=LifecycleAction.RETIRE,
                        rule_id="retire_zombie",
                        triggered_at=now,
                        requires_human_approval=True,
                        auto_executed=False,
                        notes=f"Paused for {snap.paused_days} days",
                    )
                )
                continue

            # PROMOTE: Sharpe > 1.0, win_rate > 0.55, max_drawdown < 0.15, ≥ 28 days paper
            if (
                snap.sharpe_7d > Decimal("1.0")
                and snap.win_rate > Decimal("0.55")
                and snap.max_drawdown < Decimal("0.15")
                and snap.active_paper_days >= 28
            ):
                events.append(
                    LifecycleEvent(
                        strategy_id=snap.strategy_id,
                        action=LifecycleAction.PROMOTE,
                        rule_id="promote_candidate",
                        triggered_at=now,
                        requires_human_approval=True,
                        auto_executed=False,
                        notes="Meets all promotion criteria",
                    )
                )

        return events
```

- [ ] **Step 4: Run tests to verify they pass**

```
poetry run pytest tests/unit/fleet/test_lifecycle.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/fleet/lifecycle.py tests/unit/fleet/__init__.py tests/unit/fleet/test_lifecycle.py
git commit -m "feat(17-12): model lifecycle manager (PAUSE/PROMOTE/DEMOTE/RETIRE rules)"
```

---

## Task 13: Database Migration 014

**Files:**
- Create: `services/data/alembic/versions/014_create_sprint17_tables.py`

- [ ] **Step 1: No test needed** — migration correctness is verified by Alembic running against the actual DB.

- [ ] **Step 2: Create migration**

```python
# services/data/alembic/versions/014_create_sprint17_tables.py
"""Sprint 17 tables: reward density, wallet profiles/signals, aggregated signals, lifecycle events.

Revision ID: 014
Revises: 013
Create Date: 2026-04-11
"""

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reward density scores (hypertable)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pm.reward_density_scores (
            score_id    UUID DEFAULT gen_random_uuid() NOT NULL,
            market_id   TEXT NOT NULL,
            scored_at   TIMESTAMPTZ NOT NULL,
            score       JSONB NOT NULL,
            PRIMARY KEY (score_id, scored_at)
        );
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'pm.reward_density_scores', 'scored_at',
            if_not_exists => TRUE
        );
        """
    )

    # Wallet profiles (regular table — point-in-time snapshots)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pm.wallet_profiles (
            wallet_address  TEXT NOT NULL,
            profiled_at     TIMESTAMPTZ NOT NULL,
            profile         JSONB NOT NULL,
            cluster_id      INTEGER,
            PRIMARY KEY (wallet_address, profiled_at)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_pm_wallet_profiles_profiled_at
            ON pm.wallet_profiles(profiled_at DESC);
        """
    )

    # Wallet signals (hypertable)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pm.wallet_signals (
            signal_id   UUID DEFAULT gen_random_uuid() NOT NULL,
            market_id   TEXT NOT NULL,
            computed_at TIMESTAMPTZ NOT NULL,
            signal      JSONB NOT NULL,
            PRIMARY KEY (signal_id, computed_at)
        );
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'pm.wallet_signals', 'computed_at',
            if_not_exists => TRUE
        );
        """
    )

    # Aggregated signals (hypertable)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pm.aggregated_signals (
            signal_id       UUID DEFAULT gen_random_uuid() NOT NULL,
            market_id       TEXT NOT NULL,
            aggregated_at   TIMESTAMPTZ NOT NULL,
            signal          JSONB NOT NULL,
            PRIMARY KEY (signal_id, aggregated_at)
        );
        """
    )
    op.execute(
        """
        SELECT create_hypertable(
            'pm.aggregated_signals', 'aggregated_at',
            if_not_exists => TRUE
        );
        """
    )

    # Lifecycle events (regular table — audit log)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pm.lifecycle_events (
            event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            strategy_id     TEXT NOT NULL,
            event_type      TEXT NOT NULL,
            triggered_at    TIMESTAMPTZ NOT NULL,
            rule_id         TEXT NOT NULL,
            approved        BOOLEAN,
            approved_at     TIMESTAMPTZ,
            notes           TEXT
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_pm_lifecycle_events_strategy_time
            ON pm.lifecycle_events(strategy_id, triggered_at DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_pm_lifecycle_events_type_time
            ON pm.lifecycle_events(event_type, triggered_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pm.lifecycle_events;")
    op.execute("DROP TABLE IF EXISTS pm.aggregated_signals;")
    op.execute("DROP TABLE IF EXISTS pm.wallet_signals;")
    op.execute("DROP TABLE IF EXISTS pm.wallet_profiles;")
    op.execute("DROP TABLE IF EXISTS pm.reward_density_scores;")
```

- [ ] **Step 3: Commit**

```bash
git add services/data/alembic/versions/014_create_sprint17_tables.py
git commit -m "feat(17-13): migration 014 — sprint 17 tables"
```

---

## Task 14: API Routers

**Files:**
- Create: `services/api/routers/reward_density.py`
- Create: `services/api/routers/wallet_intelligence.py`
- Create: `services/api/routers/signal_aggregation.py`
- Create: `services/api/routers/lifecycle.py`
- Modify: `services/api/main.py`
- Modify: `services/api/routers/__init__.py`

- [ ] **Step 1: Create reward_density router**

```python
# services/api/routers/reward_density.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db

router = APIRouter()


class RewardDensityScoreRow(BaseModel):
    market_id: str
    scored_at: str
    reward_density_score: float
    expected_incentives_usd: float
    competition: float
    risk_score: float
    confidence: str


@router.get(
    "/reward-density/scores",
    response_model=List[RewardDensityScoreRow],
    summary="Get latest reward density scores",
)
async def get_reward_density_scores(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[RewardDensityScoreRow]:
    try:
        rows = db.execute(
            text(
                """
                SELECT DISTINCT ON (market_id) market_id, scored_at, score
                FROM pm.reward_density_scores
                ORDER BY market_id, scored_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Reward density scores unavailable") from exc

    out: List[RewardDensityScoreRow] = []
    for r in rows:
        s: Dict[str, Any] = r["score"] or {}
        out.append(
            RewardDensityScoreRow(
                market_id=str(r["market_id"]),
                scored_at=str(r["scored_at"]),
                reward_density_score=float(s.get("reward_density_score", 0)),
                expected_incentives_usd=float(s.get("expected_incentives_usd", 0)),
                competition=float(s.get("competition", 1)),
                risk_score=float(s.get("risk_score", 0)),
                confidence=str(s.get("confidence", "low")),
            )
        )
    return out
```

- [ ] **Step 2: Create wallet_intelligence router**

```python
# services/api/routers/wallet_intelligence.py
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db

router = APIRouter()


class WalletSignalRow(BaseModel):
    market_id: str
    computed_at: str
    smart_money_consensus: float
    smart_money_activity_zscore: float
    signal_confidence: float
    wallet_count: int
    top_wallet_direction: str | None


@router.get(
    "/wallet-intelligence/signals",
    response_model=List[WalletSignalRow],
    summary="Get latest wallet intelligence signals",
)
async def get_wallet_signals(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[WalletSignalRow]:
    try:
        rows = db.execute(
            text(
                """
                SELECT DISTINCT ON (market_id) market_id, computed_at, signal
                FROM pm.wallet_signals
                ORDER BY market_id, computed_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Wallet signals unavailable") from exc

    out: List[WalletSignalRow] = []
    for r in rows:
        s: Dict[str, Any] = r["signal"] or {}
        out.append(
            WalletSignalRow(
                market_id=str(r["market_id"]),
                computed_at=str(r["computed_at"]),
                smart_money_consensus=float(s.get("smart_money_consensus", 0)),
                smart_money_activity_zscore=float(s.get("smart_money_activity_zscore", 0)),
                signal_confidence=float(s.get("signal_confidence", 0)),
                wallet_count=int(s.get("wallet_count", 0)),
                top_wallet_direction=s.get("top_wallet_direction"),
            )
        )
    return out
```

- [ ] **Step 3: Create signal_aggregation router**

```python
# services/api/routers/signal_aggregation.py
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db

router = APIRouter()


class AggregatedSignalRow(BaseModel):
    market_id: str
    aggregated_at: str
    final_signal: float
    model_component: float
    wallet_component: float
    microstructure_component: float
    threshold_met: bool
    signal_strength: str


@router.get(
    "/signal-aggregation/signals",
    response_model=List[AggregatedSignalRow],
    summary="Get latest aggregated signals",
)
async def get_aggregated_signals(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[AggregatedSignalRow]:
    try:
        rows = db.execute(
            text(
                """
                SELECT DISTINCT ON (market_id) market_id, aggregated_at, signal
                FROM pm.aggregated_signals
                ORDER BY market_id, aggregated_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Aggregated signals unavailable") from exc

    out: List[AggregatedSignalRow] = []
    for r in rows:
        s: Dict[str, Any] = r["signal"] or {}
        out.append(
            AggregatedSignalRow(
                market_id=str(r["market_id"]),
                aggregated_at=str(r["aggregated_at"]),
                final_signal=float(s.get("final_signal", 0)),
                model_component=float(s.get("model_component", 0)),
                wallet_component=float(s.get("wallet_component", 0)),
                microstructure_component=float(s.get("microstructure_component", 0)),
                threshold_met=bool(s.get("threshold_met", False)),
                signal_strength=str(s.get("signal_strength", "none")),
            )
        )
    return out
```

- [ ] **Step 4: Create lifecycle router**

```python
# services/api/routers/lifecycle.py
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db

router = APIRouter()


class LifecycleEventRow(BaseModel):
    event_id: str
    strategy_id: str
    event_type: str
    triggered_at: str
    rule_id: str
    approved: Optional[bool]
    notes: Optional[str]


@router.get(
    "/lifecycle/events",
    response_model=List[LifecycleEventRow],
    summary="Get lifecycle events",
)
async def get_lifecycle_events(
    strategy_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[LifecycleEventRow]:
    where = "WHERE strategy_id = :strategy_id" if strategy_id else ""
    params: dict = {"limit": limit}
    if strategy_id:
        params["strategy_id"] = strategy_id

    try:
        rows = db.execute(
            text(
                f"""
                SELECT event_id, strategy_id, event_type, triggered_at, rule_id, approved, notes
                FROM pm.lifecycle_events
                {where}
                ORDER BY triggered_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Lifecycle events unavailable") from exc

    return [
        LifecycleEventRow(
            event_id=str(r["event_id"]),
            strategy_id=str(r["strategy_id"]),
            event_type=str(r["event_type"]),
            triggered_at=str(r["triggered_at"]),
            rule_id=str(r["rule_id"]),
            approved=r.get("approved"),
            notes=str(r["notes"]) if r.get("notes") else None,
        )
        for r in rows
    ]
```

- [ ] **Step 5: Wire routers into main.py**

In `services/api/main.py`, add these four imports to the existing import block (after `fleet`):

```python
from .routers import (
    ...
    reward_density,
    wallet_intelligence,
    signal_aggregation,
    lifecycle,
)
```

Then add four `include_router` calls after the fleet router:

```python
app.include_router(
    reward_density.router,
    prefix=API_V1_PREFIX,
    tags=["reward-density"],
)

app.include_router(
    wallet_intelligence.router,
    prefix=API_V1_PREFIX,
    tags=["wallet-intelligence"],
)

app.include_router(
    signal_aggregation.router,
    prefix=API_V1_PREFIX,
    tags=["signal-aggregation"],
)

app.include_router(
    lifecycle.router,
    prefix=API_V1_PREFIX,
    tags=["lifecycle"],
)
```

- [ ] **Step 6: Commit**

```bash
git add services/api/routers/reward_density.py \
        services/api/routers/wallet_intelligence.py \
        services/api/routers/signal_aggregation.py \
        services/api/routers/lifecycle.py \
        services/api/main.py
git commit -m "feat(17-14): api routers for reward density, wallet intelligence, signal aggregation, lifecycle"
```

---

## Task 15: Strategy Integration — AggregatedSignal Replaces M(t)

**Files:**
- Modify: `packages/strategies/poly_directional_v1.py`
- Modify: `packages/strategies/poly_hybrid_v1.py`

The spec (AC-9) requires `AggregatedSignal` to replace the raw `M(t)` threshold in Strategy 2 (directional) and be used for the directional lean in Strategy 3 (hybrid).

- [ ] **Step 1: Write tests**

```python
# Add to tests/unit/strategies/test_poly_directional_v1.py — check that
# AggregatedSignal threshold_met=False suppresses signal even with large mispricing.
# Note: locate the test file and append:
```

Open `tests/unit/strategies/test_poly_directional_v1.py` and append:

```python
from services.signal_aggregation.schemas import AggregatedSignal
from decimal import Decimal
from datetime import datetime, timezone


def _make_agg_signal(threshold_met: bool, final: float = 0.5) -> AggregatedSignal:
    return AggregatedSignal(
        market_id="mkt1",
        aggregated_at=datetime.now(timezone.utc),
        final_signal=Decimal(str(final)),
        model_component=Decimal("0.5"),
        wallet_component=Decimal("0.3"),
        microstructure_component=Decimal("0.2"),
        weights={"model": Decimal("0.5"), "wallet": Decimal("0.3"), "micro": Decimal("0.2")},
        threshold_met=threshold_met,
        signal_strength="moderate" if threshold_met else "none",
    )


def test_directional_suppressed_when_agg_signal_not_met(directional_v1_with_prediction) -> None:
    """Strategy 2 suppresses signals when AggregatedSignal threshold not met."""
    strategy = directional_v1_with_prediction
    # Inject suppressing aggregated signal
    strategy.on_aggregated_signal(_make_agg_signal(threshold_met=False))
    portfolio = PortfolioState(cash=Decimal("10000"), positions={})
    signals = strategy.generate_signals(portfolio)
    assert signals == []
```

- [ ] **Step 2: Check the existing test fixtures**

Read `tests/unit/strategies/_sprint16_fixtures.py` to understand fixture shapes before editing strategies.

- [ ] **Step 3: Add `on_aggregated_signal` to `PolyDirectionalStrategyV1`**

In `packages/strategies/poly_directional_v1.py`:

Add the import at the top:
```python
from services.signal_aggregation.schemas import AggregatedSignal
```

In `__init__`, add:
```python
        self._aggregated_signal: Optional[AggregatedSignal] = None
```

Add method after `on_regime_state`:
```python
    def on_aggregated_signal(self, signal: AggregatedSignal) -> None:
        self._aggregated_signal = signal
```

In `initialize`, add:
```python
        self._aggregated_signal = None
```

In `generate_signals`, replace the `mispricing <= threshold` check so it reads:

```python
        mispricing, threshold = get_prediction_edge(prediction)
        if mispricing is None or threshold is None or abs(mispricing) <= threshold:
            return []

        # If an aggregated signal is present and its threshold is not met, suppress
        if self._aggregated_signal is not None and not self._aggregated_signal.threshold_met:
            return []
```

- [ ] **Step 4: Add `on_aggregated_signal` to `PolyHybridStrategyV1`**

In `packages/strategies/poly_hybrid_v1.py`, add the same import and method as above. In the hybrid strategy's `generate_signals`, use `self._aggregated_signal.final_signal` (when present and `threshold_met`) to skew the directional lean rather than suppressing entirely.

Read the full `generate_signals` method in `poly_hybrid_v1.py` first, then add after the existing regime/prediction checks:

```python
    def on_aggregated_signal(self, signal: "AggregatedSignal") -> None:
        self._aggregated_signal = signal
```

And in `__init__`:
```python
        self._aggregated_signal: Optional["AggregatedSignal"] = None
```

And in `initialize`:
```python
        self._aggregated_signal = None
```

- [ ] **Step 5: Run strategy tests**

```
poetry run pytest tests/unit/strategies/test_poly_directional_v1.py \
                  tests/unit/strategies/test_poly_hybrid_v1.py -v
```
Expected: All existing tests PASS plus the new suppression test.

- [ ] **Step 6: Commit**

```bash
git add packages/strategies/poly_directional_v1.py \
        packages/strategies/poly_hybrid_v1.py \
        tests/unit/strategies/test_poly_directional_v1.py
git commit -m "feat(17-15): strategies accept AggregatedSignal (replaces raw M(t) check)"
```

---

## Task 16: Integration Test — Full Pipeline

**Files:**
- Create: `tests/integration/test_sprint17_pipeline.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_sprint17_pipeline.py
"""
Integration test: FeatureSnapshot → WalletSignal → AggregatedSignal.
Tests AC-10: full signal aggregation pipeline from synthetic data.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from services.wallet_intelligence.signals import WalletSignalExtractor
from services.signal_aggregation.aggregator import SignalAggregator
from services.reward_density.competition import CompetitionEstimator
from services.reward_density.incentives import IncentiveEstimator
from services.reward_density.risk_scorer import RiskScorer
from services.reward_density.analyzer import RewardDensityAnalyzer
from services.reward_density.onchain.polygon_client import OrderFilledEvent


def _fill(maker: str, fee: int) -> OrderFilledEvent:
    return OrderFilledEvent(
        maker=maker,
        taker="0x0",
        maker_asset_id="TOKEN_YES",
        taker_asset_id="TOKEN_NO",
        maker_amount_filled=1000,
        taker_amount_filled=990,
        fee=fee,
        block_number=1,
        tx_hash="0x" + "ff" * 32,
    )


def test_full_reward_density_pipeline() -> None:
    """End-to-end: on-chain events → competition → incentives → density score."""
    events = [
        _fill("0xMaker1", 200),
        _fill("0xMaker1", 300),
        _fill("0xMaker2", 100),
    ]

    competition = CompetitionEstimator().compute("mkt1", events)
    assert float(competition.n_eff) == pytest.approx(1 / float(competition.hhi), rel=1e-6)

    incentive = IncentiveEstimator().estimate(
        market_id="mkt1",
        volume_7d_avg=Decimal("5000"),
        avg_price=Decimal("0.55"),
        n_eff=competition.n_eff,
        historical_fill_rate=None,
        lr_pool_per_day=Decimal("10"),
        lr_max_spread=Decimal("0.05"),
        lr_min_size=Decimal("20"),
        our_spread=Decimal("0.02"),
        our_size=Decimal("50"),
    )
    assert float(incentive.expected_total_usd) > 0

    risk_scores = RiskScorer().compute_cross_sectional(
        [{"market_id": "mkt1", "btc_rv": Decimal("0.015"), "toxicity": Decimal("0.2")}]
    )

    density = RewardDensityAnalyzer().score(
        market_id="mkt1",
        incentive=incentive,
        competition=competition,
        risk_score=risk_scores["mkt1"],
    )
    assert float(density.reward_density_score) >= 0


def test_full_signal_aggregation_pipeline() -> None:
    """End-to-end: WalletSignal + synthetic model/micro signals → AggregatedSignal."""
    smart_money = {"0xSmart1", "0xSmart2"}
    extractor = WalletSignalExtractor(smart_money_addresses=smart_money)

    fills = [
        OrderFilledEvent(
            maker="0xSmart1",
            taker="0xOther",
            maker_asset_id="YES_TOKEN",
            taker_asset_id="NO_TOKEN",
            maker_amount_filled=1000,
            taker_amount_filled=990,
            fee=2,
            block_number=1,
            tx_hash="0x" + "aa" * 32,
        ),
        OrderFilledEvent(
            maker="0xSmart2",
            taker="0xOther",
            maker_asset_id="YES_TOKEN",
            taker_asset_id="NO_TOKEN",
            maker_amount_filled=800,
            taker_amount_filled=795,
            fee=1,
            block_number=2,
            tx_hash="0x" + "bb" * 32,
        ),
    ]

    wallet_sig = extractor.compute("mkt1", fills, asset_id_yes="YES_TOKEN")
    assert wallet_sig.wallet_count == 2

    # Build history for z-scoring (5 past ticks)
    history = [
        {"model": Decimal("0"), "wallet": Decimal("0"), "micro": Decimal("0")}
    ] * 10

    agg = SignalAggregator()
    result = agg.aggregate(
        market_id="mkt1",
        model_signal=Decimal("0.4"),
        wallet_signal=wallet_sig.smart_money_consensus,
        microstructure_signal=Decimal("0.1"),
        history=history,
    )
    assert result.market_id == "mkt1"
    assert isinstance(result.threshold_met, bool)
    assert result.signal_strength in ("strong", "moderate", "weak", "none")
```

- [ ] **Step 2: Run integration test**

```
poetry run pytest tests/integration/test_sprint17_pipeline.py -v
```
Expected: PASS.

- [ ] **Step 3: Run all sprint 17 tests**

```
poetry run pytest tests/unit/reward_density/ tests/unit/wallet_intelligence/ \
                  tests/unit/signal_aggregation/ tests/unit/fleet/ \
                  tests/integration/test_sprint17_pipeline.py -v
```
Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_sprint17_pipeline.py
git commit -m "feat(17-16): integration test for sprint 17 end-to-end pipeline"
```

---

## Self-Review Against Spec

**AC-1** (rebate = 0.20 * fee_pool within 1%): Covered in `test_rebate_pool_within_1pct`.

**AC-2** (HHI single maker = 1.0, equal → N_eff = n): Covered in `test_hhi_single_maker` and `test_hhi_equal_distribution`.

**AC-3** (score higher for better market; zero when no incentives): Covered in `test_analyzer_score_higher_for_better_market` and `test_analyzer_zero_score_no_incentives`.

**AC-4** (WalletProfile role='maker' when fraction > 0.70): Covered in `test_profiler_role_maker`.

**AC-5** (KMeans stable with same seed, 4 clusters): Covered in `test_clustering_stable_with_same_seed` and `test_clustering_produces_four_clusters`.

**AC-6** (consensus > 0.3 when net long; confidence low < 3 wallets): Covered in `test_signal_consensus_bullish_when_net_long` and `test_signal_confidence_low_when_few_wallets`.

**AC-7** (FinalSignal=0 when all zero; z-scoring; weight learning): Covered in signal aggregation tests.

**AC-8** (PAUSE/PROMOTE/DEMOTE rules): Covered in lifecycle tests.

**AC-9** (RewardDensityScore in RankingScore; AggregatedSignal in Strategy 2): Covered in Task 6 and Task 15.

**AC-10** (unit tests for HHI, incentive, aggregator, lifecycle; integration test): All covered.

**Gap check:**
- Polygon client uses web3.py guarded import — if web3 not installed, client degrades gracefully (returns empty list). ✓
- Reward density `confidence` field: "high" for real on-chain data, "medium"/"low" for estimates. ✓
- Weight bounds `[0.10, 0.70]`, max weekly change 0.05. ✓
- PROMOTE always requires human approval. ✓
- Auto-PAUSE and auto-DEMOTE do NOT require human approval. ✓
- Migration is 014, revises 013. ✓

**Type consistency check:**
- `CompetitionMetric.n_eff: Decimal` used as `competition.n_eff` in `analyzer.py`. ✓
- `IncentiveEstimate.expected_total_usd: Decimal` used in `analyzer.score()`. ✓
- `AggregatedSignal` imported in strategies from `services.signal_aggregation.schemas`. ✓
- `composite_score` gains `reward_density: float = 0.0` param — existing callers continue to work (default). ✓
- `MarketScore.reward_density_score: float = 0.0` — backward compatible. ✓

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-11-sprint-17-reward-density-wallet-intelligence.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
