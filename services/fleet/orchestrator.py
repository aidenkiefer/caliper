from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional

from packages.common.market_schemas import SignalType, UnifiedSignal
from packages.common.schemas import TradingMode
from packages.strategies.base import PortfolioState, Strategy
from services.fleet.paper_store import PaperTradeStore
from services.fleet.schemas import FleetStatus, PaperTrade, SignalLogEntry, StrategyLifecycle, StrategyStatus
from services.portfolio.allocator import Allocator

logger = logging.getLogger(__name__)


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _clone_signal(signal: UnifiedSignal, *, confidence: Decimal, metadata: Dict[str, Any]) -> UnifiedSignal:
    return UnifiedSignal.model_validate({**signal.model_dump(), "confidence": confidence, "metadata": metadata})


class FleetOrchestrator:
    """Paper-mode fleet loop that never submits live CLOB orders."""

    def __init__(
        self,
        *,
        strategies: Mapping[str, Strategy],
        allocator: Allocator,
        paper_store: Optional[PaperTradeStore] = None,
        execution_adapter: Optional[Any] = None,
        paper_mode: bool = True,
        risk_manager: Optional[Any] = None,
        mode: TradingMode = TradingMode.PAPER,
    ) -> None:
        self._strategies = dict(strategies)
        self._allocator = allocator
        self._paper_store = paper_store
        self._execution_adapter = execution_adapter
        self._paper_mode = paper_mode
        self._risk_manager = risk_manager
        self._mode = mode
        self._paper_trades: List[PaperTrade] = []
        self._signal_log: List[SignalLogEntry] = []
        self._latest_status = FleetStatus(captured_at=datetime.now(timezone.utc), mode=mode, paper_mode=paper_mode)

    @property
    def latest_status(self) -> FleetStatus:
        return self._latest_status

    @property
    def paper_trades(self) -> List[PaperTrade]:
        return list(self._paper_trades)

    @property
    def signal_log(self) -> List[SignalLogEntry]:
        return list(self._signal_log)

    async def _call_hook(self, strategy: Strategy, hook_name: str, *args: Any) -> None:
        hook = getattr(strategy, hook_name, None)
        if hook is None or not callable(hook):
            return
        result = hook(*args)
        if inspect.isawaitable(result):
            await result

    def _allocation_weights(self, allocation_decision: Any) -> Mapping[str, Decimal]:
        if allocation_decision is None:
            return {}
        if isinstance(allocation_decision, Mapping):
            return allocation_decision
        weights = getattr(allocation_decision, "weights", None)
        return weights if isinstance(weights, Mapping) else {}

    def _strategy_weight(self, allocation_weights: Mapping[str, Decimal], strategy_id: str) -> Decimal:
        return _decimal(allocation_weights.get(strategy_id, Decimal("1")))

    def _regime_label(self, regime_state: Any) -> Optional[str]:
        if regime_state is None:
            return None
        return str(getattr(regime_state, "primary_regime", regime_state))

    def _market_feed(self, strategy: Strategy, market_data: Mapping[str, Any]) -> Any:
        if strategy.strategy_id in market_data:
            return market_data[strategy.strategy_id]
        market_id = strategy.config.get("market_id")
        if market_id in market_data:
            return market_data[market_id]
        return None

    def _build_trades(
        self,
        signal: UnifiedSignal,
        *,
        regime: Optional[str],
        allocation_weight: Decimal,
        current_price_map: Mapping[str, Decimal],
        quantity_override: Optional[Decimal] = None,
    ) -> List[PaperTrade]:
        now = datetime.now(timezone.utc)
        metadata = dict(signal.metadata)
        trades: List[PaperTrade] = []

        def add_trade(side: str, price: Decimal, quantity: Decimal) -> None:
            if price <= 0 or quantity <= 0:
                return
            trades.append(
                PaperTrade(
                    executed_at=now,
                    strategy_id=signal.strategy_id,
                    market_id=signal.asset_id,
                    signal_type=signal.signal_type,
                    direction=signal.direction,
                    side=side,  # type: ignore[arg-type]
                    price=price,
                    quantity=quantity,
                    notional=price * quantity,
                    confidence=signal.confidence,
                    status="paper_filled",
                    regime=regime,
                    allocation_weight=allocation_weight,
                    metadata=metadata,
                )
            )

        if signal.signal_type == SignalType.MARKET_MAKING or signal.direction == "none":
            add_trade("BUY", _decimal(metadata.get("bid_price")), _decimal(metadata.get("bid_size")))
            add_trade("SELL", _decimal(metadata.get("ask_price")), _decimal(metadata.get("ask_size")))
            return trades

        price = _decimal(metadata.get("order_price"), default="0")
        if price <= 0:
            price = _decimal(current_price_map.get(signal.asset_id))
        quantity = quantity_override if quantity_override is not None else _decimal(metadata.get("order_quantity"), default="0")
        side = "BUY" if signal.direction == "long" else "SELL"
        add_trade(side, price, quantity)
        return trades

    async def process_cycle(
        self,
        *,
        market_data: Mapping[str, Any],
        portfolio: PortfolioState,
        current_price_map: Mapping[str, Decimal],
        allocation_decision: Any = None,
        regime_state: Any = None,
        prediction_record: Any = None,
    ) -> FleetStatus:
        allocation_weights = self._allocation_weights(allocation_decision)
        regime_label = self._regime_label(regime_state)
        strategy_statuses: List[StrategyStatus] = []
        cycle_signals: List[SignalLogEntry] = []
        weighted_signals: List[UnifiedSignal] = []
        paper_trades: List[PaperTrade] = []
        active_markets: List[str] = []

        for strategy_id, strategy in self._strategies.items():
            if not strategy.initialized:
                strategy.initialize(self._mode)
            if regime_state is not None:
                await self._call_hook(strategy, "update_regime_state", regime_state)
            if prediction_record is not None:
                await self._call_hook(strategy, "update_prediction_record", prediction_record)

            feed = self._market_feed(strategy, market_data)
            if feed is not None:
                strategy.on_market_data(feed)

            signals = strategy.generate_signals(portfolio)
            weight = self._strategy_weight(allocation_weights, strategy_id)
            for signal in signals:
                weighted = _clone_signal(
                    signal,
                    confidence=signal.confidence * weight,
                    metadata={**signal.metadata, "allocation_weight": str(weight)},
                )
                weighted_signals.append(weighted)
                cycle_signals.append(
                    SignalLogEntry(
                        recorded_at=datetime.now(timezone.utc),
                        strategy_id=weighted.strategy_id,
                        market_id=weighted.asset_id,
                        signal_type=weighted.signal_type,
                        direction=weighted.direction,
                        confidence=weighted.confidence,
                        action_taken="executed" if weighted.direction != "none" else "abstained",
                        fill_price=_decimal(
                            weighted.metadata.get("bid_price")
                            or weighted.metadata.get("ask_price")
                            or current_price_map.get(weighted.asset_id)
                        ),
                        quantity=_decimal(
                            weighted.metadata.get("bid_size")
                            or weighted.metadata.get("ask_size")
                            or weighted.metadata.get("order_quantity")
                        ),
                        regime=regime_label,
                        metadata=dict(weighted.metadata),
                    )
                )
                if weighted.asset_id not in active_markets:
                    active_markets.append(weighted.asset_id)

            strategy_statuses.append(
                StrategyStatus(
                    strategy_id=strategy_id,
                    market_type=strategy.market_type,
                    status=StrategyLifecycle.ACTIVE if signals else StrategyLifecycle.ABSTAIN,
                    current_allocation_weight=weight,
                    active_market_id=signals[0].asset_id if signals else None,
                    last_signal_at=datetime.now(timezone.utc) if signals else None,
                    last_action="signal" if signals else "abstain",
                    metadata=dict(strategy.get_state()),
                )
            )

        allocated = self._allocator.allocate(weighted_signals, dict(current_price_map))
        for result in allocated:
            if self._risk_manager is not None:
                approved = True
                if hasattr(self._risk_manager, "pre_trade_check"):
                    decision = self._risk_manager.pre_trade_check(result, portfolio)
                    if inspect.isawaitable(decision):
                        decision = await decision
                    approved = bool(decision)
                elif callable(self._risk_manager):
                    decision = self._risk_manager(result, portfolio)
                    if inspect.isawaitable(decision):
                        decision = await decision
                    approved = bool(decision)
                if not approved:
                    continue

            paper_trades.extend(
                self._build_trades(
                    result.signal,
                    regime=regime_label,
                    allocation_weight=self._strategy_weight(allocation_weights, result.strategy_id),
                    current_price_map=current_price_map,
                    quantity_override=result.target_quantity,
                )
            )

        if self._paper_store is not None:
            for trade in paper_trades:
                await self._paper_store.write_fill(trade)

        if self._paper_mode and self._execution_adapter is not None:
            logger.debug("Paper mode active; execution adapter is intentionally unused.")

        self._paper_trades.extend(paper_trades)
        self._signal_log.extend(cycle_signals)
        self._latest_status = FleetStatus(
            captured_at=datetime.now(timezone.utc),
            mode=self._mode,
            paper_mode=self._paper_mode,
            strategies=strategy_statuses,
            active_markets=active_markets,
            signal_log=cycle_signals[-50:],
            metadata={"cycle_signals": len(cycle_signals), "paper_trades": len(paper_trades)},
        )
        return self._latest_status

    async def run(
        self,
        event_queue: "asyncio.Queue[Mapping[str, Any] | None]",
        output_queue: Optional["asyncio.Queue[FleetStatus]"] = None,
    ) -> None:
        while True:
            event = await event_queue.get()
            if event is None:
                event_queue.task_done()
                break
            status = await self.process_cycle(
                market_data=event.get("market_data", {}),
                portfolio=event["portfolio"],
                current_price_map=event.get("current_price_map", {}),
                allocation_decision=event.get("allocation_decision"),
                regime_state=event.get("regime_state"),
                prediction_record=event.get("prediction_record"),
            )
            if output_queue is not None:
                await output_queue.put(status)
            event_queue.task_done()
