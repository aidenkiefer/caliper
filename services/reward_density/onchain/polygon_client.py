# services/reward_density/onchain/polygon_client.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

# web3 is an optional dependency — import guarded so the module loads without it
try:
    from web3 import Web3
    _HAS_WEB3 = True
except ImportError:
    _HAS_WEB3 = False

CTF_EXCHANGE_ADDRESS = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"

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
