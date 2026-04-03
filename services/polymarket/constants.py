"""
Constants for the Polymarket BTC hourly market-making service.

Includes API base URLs, fee parameters (with regime-change date), CTF contract
addresses (placeholders — update from https://docs.polymarket.com/resources/contract-addresses),
timing constants, and token/outcome identifiers.
"""

from datetime import date
from decimal import Decimal

# ---------------------------------------------------------------------------
# API base URLs
# ---------------------------------------------------------------------------

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
DATA_API_URL = "https://data-api.polymarket.com"
CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
BINANCE_API_URL = "https://api.binance.com"

# ---------------------------------------------------------------------------
# Fee parameters
# ---------------------------------------------------------------------------

# Pre-March 30, 2026 fee regime
FEE_RATE_PRE = Decimal("0.25")
FEE_EXPONENT_PRE = 2

# Post-March 30, 2026 fee regime (flat-rate model)
FEE_RATE_POST = Decimal("0.072")
FEE_EXPONENT_POST = 1

# Date on which the fee regime changes
FEE_REGIME_CHANGE_DATE = date(2026, 3, 30)

# Fraction of taker fees returned to makers as rebate
MAKER_REBATE_FRACTION = Decimal("0.20")

# ---------------------------------------------------------------------------
# CTF contract addresses (Polygon mainnet)
# PLACEHOLDER — replace with real values from:
# https://docs.polymarket.com/resources/contract-addresses
# ---------------------------------------------------------------------------

CTF_CONTRACT_ADDRESS = "0x0000000000000000000000000000000000000000"      # placeholder
USDC_CONTRACT_ADDRESS = "0x0000000000000000000000000000000000000000"     # placeholder
EXCHANGE_CONTRACT_ADDRESS = "0x0000000000000000000000000000000000000000"  # placeholder

# ---------------------------------------------------------------------------
# Polygon RPC endpoint
# ---------------------------------------------------------------------------

POLYGON_RPC_URL = "https://polygon-rpc.com"  # public RPC; override via config for reliability

# ---------------------------------------------------------------------------
# Timing constants (all values in seconds unless the name says otherwise)
# ---------------------------------------------------------------------------

# Platform cancels resting orders if no heartbeat is received within this window
HEARTBEAT_TIMEOUT_SECONDS = 10

DEFAULT_REQUOTE_INTERVAL = 10       # seconds between re-quote cycles
DEFAULT_WIND_DOWN_MINUTES = 5       # minutes before window close to stop quoting
SNAPSHOT_INTERVAL_SECONDS = 5      # orderbook / inventory snapshot cadence
PNL_SNAPSHOT_INTERVAL_SECONDS = 30  # session P&L snapshot cadence
BINANCE_POLL_INTERVAL_SECONDS = 5   # how often to poll Binance REST for BTC price

# ---------------------------------------------------------------------------
# Token / outcome identifiers
# ---------------------------------------------------------------------------

BTCUSDT_SYMBOL = "BTCUSDT"
YES_OUTCOME = "YES"
NO_OUTCOME = "NO"
