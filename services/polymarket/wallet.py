"""
Wallet management for Polymarket Polygon operations.

Handles:
- USDC.e (ERC-20) and conditional token (ERC-1155) balance queries
- EIP-712 order signing (same domain/types as CLOBClient)
- Token split/merge via the Conditional Token Framework (CTF) contract
- Token redemption after market resolution

Known limitations (V1):
- Web3.py contract calls are synchronous and will block the event loop.
  Wrap in a thread executor if strict async behaviour is required.
- CTF and USDC contract addresses in constants.py are placeholder zero addresses;
  update them with real Polygon mainnet values before using in production.
"""

from __future__ import annotations

import logging
import warnings
from decimal import Decimal
from typing import Any, Optional

from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

from services.polymarket.constants import (
    CTF_CONTRACT_ADDRESS,
    POLYGON_RPC_URL,
    USDC_CONTRACT_ADDRESS,
    EXCHANGE_CONTRACT_ADDRESS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Decimal constants
# ---------------------------------------------------------------------------

_USDC_DECIMALS = 6
_TOKEN_DECIMALS = 6
_ZERO_BYTES32 = b"\x00" * 32

# ---------------------------------------------------------------------------
# Minimal ABIs — only the functions this module needs
# ---------------------------------------------------------------------------

_ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    }
]

_ERC1155_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "account", "type": "address"},
            {"name": "id", "type": "uint256"},
        ],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    }
]

_CTF_ABI = [
    {
        "name": "splitPosition",
        "type": "function",
        "inputs": [
            {"name": "collateralToken", "type": "address"},
            {"name": "parentCollectionId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"},
            {"name": "partition", "type": "uint256[]"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [],
    },
    {
        "name": "mergePositions",
        "type": "function",
        "inputs": [
            {"name": "collateralToken", "type": "address"},
            {"name": "parentCollectionId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"},
            {"name": "partition", "type": "uint256[]"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [],
    },
    {
        "name": "redeemPositions",
        "type": "function",
        "inputs": [
            {"name": "collateralToken", "type": "address"},
            {"name": "parentCollectionId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"},
            {"name": "indexSets", "type": "uint256[]"},
        ],
        "outputs": [],
    },
]

# ---------------------------------------------------------------------------
# EIP-712 domain and type definitions (duplicated from clob_client for V1 isolation)
# ---------------------------------------------------------------------------

_REQUIRED_ORDER_FIELDS = {
    "salt", "maker", "signer", "taker", "tokenId",
    "makerAmount", "takerAmount", "expiration", "nonce",
    "feeRateBps", "side", "signatureType",
}

_ORDER_EIP712_TYPES = {
    "Order": [
        {"name": "salt", "type": "uint256"},
        {"name": "maker", "type": "address"},
        {"name": "signer", "type": "address"},
        {"name": "taker", "type": "address"},
        {"name": "tokenId", "type": "uint256"},
        {"name": "makerAmount", "type": "uint256"},
        {"name": "takerAmount", "type": "uint256"},
        {"name": "expiration", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
        {"name": "feeRateBps", "type": "uint256"},
        {"name": "side", "type": "uint8"},
        {"name": "signatureType", "type": "uint8"},
    ]
}

_DOMAIN = {
    "name": "Polymarket CTF Exchange",
    "version": "1",
    "chainId": 137,
    "verifyingContract": EXCHANGE_CONTRACT_ADDRESS,
}


# ---------------------------------------------------------------------------
# WalletManager
# ---------------------------------------------------------------------------


class WalletManager:
    """Manages Polygon wallet operations for the Polymarket service.

    Parameters
    ----------
    private_key:
        Hex-encoded Ethereum private key (with or without ``0x`` prefix).
        Never logged; stored internally as ``_private_key``.
    wallet_address:
        Checksum Ethereum address corresponding to ``private_key``.
    web3_provider:
        Optional pre-constructed :class:`web3.Web3` instance.  When *None*
        (default) a new instance is created using ``POLYGON_RPC_URL``.
        Pass an explicit instance for testing (dependency injection).
    rpc_url:
        Polygon RPC endpoint URL.  Ignored when ``web3_provider`` is supplied.
        Defaults to :data:`~services.polymarket.constants.POLYGON_RPC_URL`.
    """

    def __init__(
        self,
        private_key: str,
        wallet_address: str,
        web3_provider: Optional[Any] = None,
        rpc_url: str = POLYGON_RPC_URL,
    ) -> None:
        self._private_key = private_key
        self._wallet_address = wallet_address

        # Validate the private key once at construction time; the Account object
        # is not stored — only the raw key is kept to minimise surface area.
        Account.from_key(private_key)

        if web3_provider is not None:
            self._w3 = web3_provider
        else:
            self._w3 = Web3(Web3.HTTPProvider(rpc_url))

        # Warn if placeholder contract addresses are still in use
        _ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
        if any(addr == _ZERO_ADDRESS for addr in [
            CTF_CONTRACT_ADDRESS, USDC_CONTRACT_ADDRESS, EXCHANGE_CONTRACT_ADDRESS
        ]):
            warnings.warn(
                "One or more contract addresses are placeholders (zero address). "
                "EIP-712 signatures and CTF contract calls will be invalid against production. "
                "Update constants.py with real values from https://docs.polymarket.com/resources/contract-addresses",
                UserWarning,
                stacklevel=2,
            )

    # ------------------------------------------------------------------
    # Balance queries
    # ------------------------------------------------------------------

    async def get_usdc_balance(self) -> Decimal:
        """Return the USDC.e ERC-20 balance for the managed wallet.

        Returns
        -------
        Decimal
            Human-readable USDC balance (raw / 10^6).
        """
        contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(USDC_CONTRACT_ADDRESS),
            abi=_ERC20_ABI,
        )
        raw: int = contract.functions.balanceOf(
            Web3.to_checksum_address(self._wallet_address)
        ).call()
        return Decimal(raw) / Decimal(10 ** _USDC_DECIMALS)

    async def get_token_balance(self, token_id: str) -> Decimal:
        """Return the ERC-1155 conditional token balance for the managed wallet.

        Parameters
        ----------
        token_id:
            String representation of the ERC-1155 token ID (uint256).

        Returns
        -------
        Decimal
            Human-readable token balance (raw / 10^6).
        """
        contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(CTF_CONTRACT_ADDRESS),
            abi=_ERC1155_ABI,
        )
        raw: int = contract.functions.balanceOf(
            Web3.to_checksum_address(self._wallet_address),
            int(token_id),
        ).call()
        return Decimal(raw) / Decimal(10 ** _TOKEN_DECIMALS)

    # ------------------------------------------------------------------
    # EIP-712 signing
    # ------------------------------------------------------------------

    def sign_order(self, order_data: dict) -> str:
        """Sign ``order_data`` with EIP-712 and return the hex signature string.

        The signing domain and type definitions match those used by
        :class:`~services.polymarket.adapters.clob_client.CLOBClient`.

        Parameters
        ----------
        order_data:
            Dict conforming to the ``Order`` EIP-712 type (salt, maker, signer,
            taker, tokenId, makerAmount, takerAmount, expiration, nonce,
            feeRateBps, side, signatureType).

        Returns
        -------
        str
            Hex-encoded signature string (e.g. ``"0xabcd..."``)
        """
        missing = _REQUIRED_ORDER_FIELDS - set(order_data.keys())
        if missing:
            raise ValueError(f"sign_order: missing required fields: {sorted(missing)}")
        structured_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                **_ORDER_EIP712_TYPES,
            },
            "domain": _DOMAIN,
            "primaryType": "Order",
            "message": order_data,
        }
        encoded = encode_typed_data(full_message=structured_data)
        signed = Account.sign_message(encoded, private_key=self._private_key)
        return signed.signature.hex()

    # ------------------------------------------------------------------
    # Token split / merge / redeem
    # ------------------------------------------------------------------

    async def split_usdc(self, amount: Decimal, condition_id: str) -> dict:
        """Split USDC into YES+NO conditional token pairs via the CTF contract.

        Calls ``splitPosition`` on the CTF contract with:

        - ``collateralToken`` = USDC_CONTRACT_ADDRESS
        - ``parentCollectionId`` = bytes32(0)
        - ``conditionId`` = bytes32 from hex ``condition_id``
        - ``partition`` = [1, 2] (index 0 → NO, index 1 → YES)
        - ``amount`` = ``amount`` * 10^6 (raw integer)

        Parameters
        ----------
        amount:
            Human-readable USDC amount to split (e.g. ``Decimal("100")``).
        condition_id:
            Hex condition ID string (with or without ``0x`` prefix).

        Returns
        -------
        dict
            ``{"tx_hash": "0x...", "amount_split": amount}``
        """
        raw_amount = int(amount * Decimal(10 ** _USDC_DECIMALS))
        raw = bytes.fromhex(condition_id.lstrip("0x"))
        if len(raw) > 32:
            raise ValueError(
                f"condition_id decodes to {len(raw)} bytes; bytes32 requires at most 32 bytes."
            )
        condition_bytes = raw.rjust(32, b"\x00")

        contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(CTF_CONTRACT_ADDRESS),
            abi=_CTF_ABI,
        )
        tx = contract.functions.splitPosition(
            Web3.to_checksum_address(USDC_CONTRACT_ADDRESS),
            _ZERO_BYTES32,
            condition_bytes,
            [1, 2],
            raw_amount,
        ).build_transaction(
            {
                "from": Web3.to_checksum_address(self._wallet_address),
                "nonce": self._w3.eth.get_transaction_count(
                    Web3.to_checksum_address(self._wallet_address)
                ),
            }
        )
        signed_tx = self._w3.eth.account.sign_transaction(tx, private_key=self._private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        logger.info(
            "splitPosition tx submitted: condition=%s amount=%s tx_hash=%s",
            condition_id,
            amount,
            tx_hash.hex(),
        )
        return {"tx_hash": tx_hash.hex(), "amount_split": amount}

    async def merge_tokens(self, amount: Decimal, condition_id: str) -> dict:
        """Merge YES+NO conditional token pairs back to USDC via the CTF contract.

        Calls ``mergePositions`` with the same parameters as :meth:`split_usdc`
        (partition ``[1, 2]``, parentCollectionId = bytes32(0)).

        Parameters
        ----------
        amount:
            Human-readable share amount to merge (e.g. ``Decimal("100")``).
        condition_id:
            Hex condition ID string (with or without ``0x`` prefix).

        Returns
        -------
        dict
            ``{"tx_hash": "0x...", "amount_merged": amount}``
        """
        raw_amount = int(amount * Decimal(10 ** _TOKEN_DECIMALS))
        raw = bytes.fromhex(condition_id.lstrip("0x"))
        if len(raw) > 32:
            raise ValueError(
                f"condition_id decodes to {len(raw)} bytes; bytes32 requires at most 32 bytes."
            )
        condition_bytes = raw.rjust(32, b"\x00")

        contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(CTF_CONTRACT_ADDRESS),
            abi=_CTF_ABI,
        )
        tx = contract.functions.mergePositions(
            Web3.to_checksum_address(USDC_CONTRACT_ADDRESS),
            _ZERO_BYTES32,
            condition_bytes,
            [1, 2],
            raw_amount,
        ).build_transaction(
            {
                "from": Web3.to_checksum_address(self._wallet_address),
                "nonce": self._w3.eth.get_transaction_count(
                    Web3.to_checksum_address(self._wallet_address)
                ),
            }
        )
        signed_tx = self._w3.eth.account.sign_transaction(tx, private_key=self._private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        logger.info(
            "mergePositions tx submitted: condition=%s amount=%s tx_hash=%s",
            condition_id,
            amount,
            tx_hash.hex(),
        )
        return {"tx_hash": tx_hash.hex(), "amount_merged": amount}

    async def redeem_tokens(self, token_id: str, condition_id: str) -> dict:
        """Redeem winning tokens after market resolution via the CTF contract.

        Calls ``redeemPositions`` and attempts both index sets (YES=2, NO=1).
        The first successful transaction is returned.

        Parameters
        ----------
        token_id:
            ERC-1155 token ID string (used for logging and the return value).
        condition_id:
            Hex condition ID string (with or without ``0x`` prefix).

        Returns
        -------
        dict
            ``{"tx_hash": "0x...", "token_id": token_id}``

        Raises
        ------
        Exception
            Re-raises the last error if both index-set attempts fail.
        """
        raw = bytes.fromhex(condition_id.lstrip("0x"))
        if len(raw) > 32:
            raise ValueError(
                f"condition_id decodes to {len(raw)} bytes; bytes32 requires at most 32 bytes."
            )
        condition_bytes = raw.rjust(32, b"\x00")
        contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(CTF_CONTRACT_ADDRESS),
            abi=_CTF_ABI,
        )

        nonce = self._w3.eth.get_transaction_count(
            Web3.to_checksum_address(self._wallet_address)
        )
        last_error: Optional[Exception] = None
        for attempt, index_sets in enumerate(([2], [1])):
            try:
                tx = contract.functions.redeemPositions(
                    Web3.to_checksum_address(USDC_CONTRACT_ADDRESS),
                    _ZERO_BYTES32,
                    condition_bytes,
                    index_sets,
                ).build_transaction(
                    {
                        "from": Web3.to_checksum_address(self._wallet_address),
                        "nonce": nonce + attempt,
                    }
                )
                signed_tx = self._w3.eth.account.sign_transaction(
                    tx, private_key=self._private_key
                )
                tx_hash = self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                logger.info(
                    "redeemPositions tx submitted: token=%s index_sets=%s tx_hash=%s",
                    token_id,
                    index_sets,
                    tx_hash.hex(),
                )
                return {"tx_hash": tx_hash.hex(), "token_id": token_id}
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "redeemPositions failed with index_sets=%s: %s", index_sets, exc
                )
                last_error = exc

        raise last_error  # type: ignore[misc]
