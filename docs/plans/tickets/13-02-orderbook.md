# Ticket 13-02: Order Book + Unit Tests

## Task

Implement `SimulatedOrderBook` (full limit order book with price-time priority) and `OrderMatcher` (Polymarket matching rules: taker sweeps, post-only maker insertion, partial fills). Include unit tests covering all AC-2 acceptance criteria.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/simulation/orderbook/book.py`
- Create: `services/simulation/orderbook/matching.py`
- Create: `tests/unit/simulation/__init__.py`
- Create: `tests/unit/simulation/test_orderbook.py`
- Modify: `services/simulation/orderbook/__init__.py` (exports)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ SimulatedOrderBook, § OrderMatcher)
- `services/simulation/schemas.py` (SimEvent, SimOrder, SimFill)

### Optional read-only references
- `tests/unit/features/test_feature_builder.py` (pytest fixture patterns)

## Done criteria

### `services/simulation/orderbook/book.py` — `SimulatedOrderBook`

- `__init__`: initializes `bids: SortedDict` (descending key = -price), `asks: SortedDict` (ascending key = price). Use `sortedcontainers.SortedDict`.
- `apply_snapshot(event: SimEvent)`: replaces full book state from a snapshot event payload `{"bids": [[price, size], ...], "asks": [[price, size], ...]}`. Clears existing state first. Prunes zero-volume levels.
- `apply_trade(event: SimEvent)`: removes matched volume from the appropriate side (payload has `side`, `price`, `size`). If remaining size at that level is zero, remove the level.
- `apply_cancel(event: SimEvent)`: removes a specific order by id. Payload has `side`, `price`, `order_id`, `size`.
- `place_limit(order: SimOrder)`: inserts at price level, respecting time priority (new orders go behind existing at same price). Stores `(order_id, size, timestamp)` tuple in a deque at that price level.
- `match_market(order: SimOrder) -> List[SimFill]`: sweeps opposite-side levels consuming volume. Returns one `SimFill` per price level consumed. Raises if order size is zero. Handles partial fill at last level.
- `best_bid() -> Optional[Decimal]`: returns highest bid price or None.
- `best_ask() -> Optional[Decimal]`: returns lowest ask price or None.
- `mid_price() -> Optional[Decimal]`: `(best_bid + best_ask) / 2` or None if either side empty.
- `spread() -> Optional[Decimal]`: `best_ask - best_bid` or None.

### `services/simulation/orderbook/matching.py` — `OrderMatcher`

- `match_taker(order: SimOrder, book: SimulatedOrderBook, submit_time: datetime) -> List[SimFill]`: calls `book.match_market(order)`. Records slippage vs mid at `submit_time`. Returns list of `SimFill` records with `maker_fill=False`.
- `match_maker(order: SimOrder, book: SimulatedOrderBook) -> Optional[SimFill]`: checks if order would cross (bid >= best_ask, or ask <= best_bid). If yes: **returns None** (post-only rejection, not a fill). If no: calls `book.place_limit(order)`, returns None (fill happens when opposite order arrives). The matcher does NOT generate a SimFill for maker orders placed successfully — fills happen via `apply_trade` events from the replay.
- `would_cross(order: SimOrder, book: SimulatedOrderBook) -> bool`: pure function, exposed for testing.

### `tests/unit/simulation/test_orderbook.py`

Minimum tests required (use descriptive names matching AC-2):

**Order book basics:**
- `test_apply_snapshot_populates_book`: after snapshot, best_bid and best_ask are correct
- `test_apply_trade_removes_volume`: trade event reduces size at price level
- `test_apply_trade_prunes_zero_level`: trade that exhausts a level removes the level
- `test_apply_cancel_removes_order`: cancel removes order from queue

**Taker matching:**
- `test_taker_single_level_full_fill`: taker order fills completely at one level
- `test_taker_multi_level_partial_fills`: taker sweeps across multiple levels, produces multiple SimFill records
- `test_taker_fill_sizes_sum_to_order_size`: sum of fill sizes equals original order size (AC-2)
- `test_taker_slippage_vs_mid`: slippage field is fill_price - mid_price at submit time

**Post-only maker:**
- `test_maker_post_only_rejection_would_cross`: maker order that would cross returns None from match_maker (AC-2)
- `test_maker_post_only_accepted_no_cross`: maker order that doesn't cross is placed without a fill
- `test_would_cross_bid_at_or_above_ask`: would_cross returns True when bid >= best_ask
- `test_would_cross_ask_at_or_below_bid`: would_cross returns True when ask <= best_bid

**Price-time priority:**
- `test_time_priority_at_same_price`: two maker orders at same price; first-in-time is first in queue

All tests use only synthetic in-memory data (no DB, no network). Use `Decimal` for prices and sizes.
