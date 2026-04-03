"""CLI entrypoint for the Polymarket BTC hourly market-making service.

Usage::

    polymarket-session [--dry-run] [--target-hour N]
    python -m polymarket [--dry-run] [--target-hour N]
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path
from typing import Optional

import httpx
import asyncpg
import typer

from services.polymarket.config import PolymarketConfig
from services.polymarket.adapters.gamma_client import GammaClient
from services.polymarket.adapters.clob_client import CLOBClient
from services.polymarket.adapters.binance_client import BinanceClient
from services.polymarket.wallet import WalletManager
from services.polymarket.market_discovery import MarketDiscovery
from services.polymarket.data_feed import DataFeed
from services.polymarket.quoting_engine import QuotingEngine
from services.polymarket.executor import Executor
from services.polymarket.safety import SafetyLayer
from services.polymarket.recorder import Recorder
from services.polymarket.session import SessionOrchestrator

app = typer.Typer(add_completion=False)

logger = logging.getLogger(__name__)


def setup_logging(log_id: str) -> None:
    """Configure root logger to write to stdout and a session log file."""
    Path("logs").mkdir(exist_ok=True)
    log_file = f"logs/polymarket_{log_id}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file),
        ],
    )
    logger.info("Logging to %s", log_file)


@app.command()
def _command(
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip actual order placement"),
    target_hour: Optional[int] = typer.Option(
        None, "--target-hour", help="Override target_hour_local in config"
    ),
) -> None:
    """Run one Polymarket BTC hourly market-making session."""
    session_log_id = uuid.uuid4().hex
    setup_logging(session_log_id)

    if dry_run:
        logger.info("DRY RUN MODE enabled — order placement will be skipped")

    # Load configuration from environment variables.
    config = PolymarketConfig()

    # Apply CLI overrides.
    if target_hour is not None:
        config = config.model_copy(update={"target_hour_local": target_hour})
        logger.info("Overriding target_hour_local → %d", target_hour)

    try:
        asyncio.run(_run(config, dry_run=dry_run))
    except Exception:
        logger.exception("Fatal error — exiting with code 1")
        sys.exit(1)


async def _run(config: PolymarketConfig, *, dry_run: bool) -> None:
    """Build all dependencies and run the session orchestrator."""
    # Resolve database URL — handle both plain str and SecretStr.
    try:
        db_url = config.database_url.get_secret_value()
    except AttributeError:
        db_url = str(config.database_url)

    async with httpx.AsyncClient() as http_client:
        db_pool = await asyncpg.create_pool(db_url)
        try:
            gamma_client = GammaClient(http_client=http_client)
            clob_client = CLOBClient(http_client=http_client, config=config)
            binance_client = BinanceClient(http_client=http_client)
            wallet_manager = WalletManager(config=config)
            market_discovery = MarketDiscovery(gamma_client=gamma_client)
            data_feed = DataFeed(
                clob_client=clob_client,
                binance_client=binance_client,
            )
            quoting_engine = QuotingEngine()
            executor = Executor(clob_client=clob_client, config=config)
            safety_layer = SafetyLayer(config=config)
            recorder = Recorder(db_pool=db_pool)

            if dry_run:
                async def _dry_run_place_quotes(quote, token_id, quote_version=None):
                    logger.info("DRY RUN: would place quotes %s for token_id=%s", quote, token_id)
                    return {}

                executor.place_quotes = _dry_run_place_quotes

            orchestrator = SessionOrchestrator(
                market_discovery=market_discovery,
                data_feed=data_feed,
                quoting_engine=quoting_engine,
                executor=executor,
                safety_layer=safety_layer,
                recorder=recorder,
                wallet_manager=wallet_manager,
            )

            await orchestrator.run_session(config)
        finally:
            await db_pool.close()


def main() -> None:
    """Callable entry point for the ``polymarket-session`` script."""
    app()


if __name__ == "__main__":
    main()
