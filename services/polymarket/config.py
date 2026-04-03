"""
Configuration for the Polymarket BTC hourly market-making service.

All settings are loaded from environment variables with the POLYMARKET_ prefix,
or from a .env file. Sensitive values (private key) use SecretStr so they are
not exposed in logs or repr output.
"""

from decimal import Decimal

from pydantic import SecretStr
from pydantic_settings import BaseSettings

from services.polymarket.constants import (
    GAMMA_API_URL, CLOB_API_URL, DATA_API_URL, CLOB_WS_URL, BINANCE_API_URL
)


class PolymarketConfig(BaseSettings):
    # Wallet
    private_key: SecretStr  # Polygon wallet private key
    wallet_address: str  # Public address

    # Target window — specified in local time, converted to UTC at runtime
    # using zoneinfo. This handles DST transitions automatically.
    target_hour_local: int = 9  # 9 AM in target_timezone
    target_timezone: str = "America/New_York"  # IANA timezone name
    pre_session_minutes: int = 5
    wind_down_minutes: int = 5

    # Quoting parameters
    quote_spread: Decimal = Decimal("0.02")  # 2 cents each side of mid
    quote_size: Decimal = Decimal("50")  # 50 shares per side
    inventory_cap: Decimal = Decimal("200")  # Max YES shares held
    requote_interval_seconds: int = 10

    # Safety
    max_session_loss_usdc: Decimal = Decimal("20")
    heartbeat_interval_seconds: int = 5
    cancel_all_on_error: bool = True

    # Recording
    snapshot_interval_seconds: int = 5

    # Database
    database_url: str

    # API URLs (defaults to production)
    gamma_api_url: str = GAMMA_API_URL
    clob_api_url: str = CLOB_API_URL
    data_api_url: str = DATA_API_URL
    clob_ws_url: str = CLOB_WS_URL
    binance_api_url: str = BINANCE_API_URL

    # Binance staleness threshold
    binance_stale_seconds: int = 30

    model_config = {
        "env_prefix": "POLYMARKET_",
        "env_file": ".env",
    }
