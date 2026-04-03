"""
Unit tests for services/polymarket/wallet.py

All tests use mock Web3 providers — no real RPC calls are made.
"""

from __future__ import annotations

import warnings
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Test fixtures — standard Hardhat dev account (safe to commit)
# ---------------------------------------------------------------------------

TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
TEST_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

_CONDITION_ID = "0x" + "ab" * 32  # 32-byte hex condition ID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_w3() -> MagicMock:
    """Return a minimal mock Web3 instance that satisfies WalletManager's init."""
    w3 = MagicMock()
    # eth.get_transaction_count used during split/merge/redeem
    w3.eth.get_transaction_count.return_value = 0
    return w3


def _make_wallet(w3: MagicMock | None = None):
    """Construct a WalletManager with a mock Web3, suppressing placeholder warnings."""
    from services.polymarket.wallet import WalletManager

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return WalletManager(
            private_key=TEST_PRIVATE_KEY,
            wallet_address=TEST_ADDRESS,
            web3_provider=w3 if w3 is not None else _make_mock_w3(),
        )


def _make_contract_mock(return_value: int) -> MagicMock:
    """Create a mock contract whose balanceOf().call() returns ``return_value``."""
    contract = MagicMock()
    contract.functions.balanceOf.return_value.call.return_value = return_value
    return contract


# ---------------------------------------------------------------------------
# Test: get_usdc_balance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_usdc_balance_success():
    """balanceOf returns raw int → Decimal divided by 10^6."""
    w3 = _make_mock_w3()
    # Raw balance: 500_000_000 → 500 USDC
    w3.eth.contract.return_value = _make_contract_mock(500_000_000)

    wallet = _make_wallet(w3)
    balance = await wallet.get_usdc_balance()

    assert balance == Decimal("500")
    # Ensure the ERC-20 contract was called with the wallet address
    w3.eth.contract.assert_called_once()


@pytest.mark.asyncio
async def test_get_usdc_balance_zero():
    """Zero raw balance → Decimal('0')."""
    w3 = _make_mock_w3()
    w3.eth.contract.return_value = _make_contract_mock(0)

    wallet = _make_wallet(w3)
    balance = await wallet.get_usdc_balance()

    assert balance == Decimal("0")


# ---------------------------------------------------------------------------
# Test: get_token_balance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_token_balance_success():
    """ERC-1155 balanceOf returns raw int → Decimal divided by 10^6."""
    w3 = _make_mock_w3()
    # Raw: 250_000_000 → 250 shares
    w3.eth.contract.return_value = _make_contract_mock(250_000_000)

    wallet = _make_wallet(w3)
    balance = await wallet.get_token_balance("12345678")

    assert balance == Decimal("250")


@pytest.mark.asyncio
async def test_get_token_balance_fractional():
    """Raw balance of 1 → 0.000001 shares (smallest representable unit)."""
    w3 = _make_mock_w3()
    w3.eth.contract.return_value = _make_contract_mock(1)

    wallet = _make_wallet(w3)
    balance = await wallet.get_token_balance("99")

    assert balance == Decimal("1") / Decimal("1000000")


# ---------------------------------------------------------------------------
# Test: sign_order
# ---------------------------------------------------------------------------


def test_sign_order_returns_hex():
    """sign_order returns a non-empty hex string for a valid order dict."""
    wallet = _make_wallet()

    order_data = {
        "salt": 1,
        "maker": TEST_ADDRESS,
        "signer": TEST_ADDRESS,
        "taker": "0x0000000000000000000000000000000000000000",
        "tokenId": 12345,
        "makerAmount": 48_000_000,
        "takerAmount": 100_000_000,
        "expiration": 0,
        "nonce": 0,
        "feeRateBps": 0,
        "side": 0,
        "signatureType": 0,
    }

    sig = wallet.sign_order(order_data)

    assert isinstance(sig, str)
    assert len(sig) > 0
    # hex string — consists only of hex chars (may or may not include 0x prefix)
    clean = sig.lstrip("0x")
    assert all(c in "0123456789abcdefABCDEF" for c in clean)


def test_sign_order_deterministic_for_same_input():
    """Same order data and key → same signature (EIP-712 is deterministic)."""
    wallet = _make_wallet()

    order_data = {
        "salt": 42,
        "maker": TEST_ADDRESS,
        "signer": TEST_ADDRESS,
        "taker": "0x0000000000000000000000000000000000000000",
        "tokenId": 99,
        "makerAmount": 10_000_000,
        "takerAmount": 20_000_000,
        "expiration": 0,
        "nonce": 0,
        "feeRateBps": 0,
        "side": 1,
        "signatureType": 0,
    }

    sig1 = wallet.sign_order(order_data)
    sig2 = wallet.sign_order(order_data)
    assert sig1 == sig2


# ---------------------------------------------------------------------------
# Test: split_usdc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_split_usdc_calls_contract():
    """split_usdc calls splitPosition with correct args and returns tx_hash + amount."""
    w3 = _make_mock_w3()

    # Build a mock contract that captures the splitPosition call
    contract_mock = MagicMock()
    tx_mock = MagicMock()
    tx_mock.build_transaction.return_value = {"from": TEST_ADDRESS, "nonce": 0}
    contract_mock.functions.splitPosition.return_value = tx_mock

    # Fake signed tx and tx hash
    fake_raw = b"\xde\xad\xbe\xef"
    signed_tx_mock = MagicMock()
    signed_tx_mock.raw_transaction = fake_raw
    w3.eth.account.sign_transaction.return_value = signed_tx_mock
    w3.eth.send_raw_transaction.return_value = bytes.fromhex("cafebabe" * 8)

    w3.eth.contract.return_value = contract_mock

    wallet = _make_wallet(w3)
    result = await wallet.split_usdc(Decimal("100"), _CONDITION_ID)

    # Verify the return shape
    assert "tx_hash" in result
    assert result["amount_split"] == Decimal("100")

    # Verify splitPosition was called with the right arguments
    call_args = contract_mock.functions.splitPosition.call_args
    positional = call_args[0]

    # positional[3] = partition, positional[4] = amount
    assert positional[3] == [1, 2], "partition must be [1, 2]"
    assert positional[4] == 100_000_000, "amount must be scaled to 6 decimals"
    # parentCollectionId is zero bytes32
    assert positional[1] == b"\x00" * 32


@pytest.mark.asyncio
async def test_split_usdc_condition_id_without_prefix():
    """split_usdc handles condition_id without 0x prefix."""
    w3 = _make_mock_w3()

    contract_mock = MagicMock()
    tx_mock = MagicMock()
    tx_mock.build_transaction.return_value = {"from": TEST_ADDRESS, "nonce": 0}
    contract_mock.functions.splitPosition.return_value = tx_mock

    signed_tx_mock = MagicMock()
    signed_tx_mock.raw_transaction = b"\x00"
    w3.eth.account.sign_transaction.return_value = signed_tx_mock
    w3.eth.send_raw_transaction.return_value = b"\xab" * 32
    w3.eth.contract.return_value = contract_mock

    wallet = _make_wallet(w3)
    # condition_id without 0x prefix
    condition_no_prefix = "ab" * 32
    result = await wallet.split_usdc(Decimal("50"), condition_no_prefix)

    assert result["amount_split"] == Decimal("50")


# ---------------------------------------------------------------------------
# Test: merge_tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_merge_tokens_calls_contract():
    """merge_tokens calls mergePositions with correct args and returns tx_hash + amount."""
    w3 = _make_mock_w3()

    contract_mock = MagicMock()
    tx_mock = MagicMock()
    tx_mock.build_transaction.return_value = {"from": TEST_ADDRESS, "nonce": 0}
    contract_mock.functions.mergePositions.return_value = tx_mock

    signed_tx_mock = MagicMock()
    signed_tx_mock.raw_transaction = b"\x00"
    w3.eth.account.sign_transaction.return_value = signed_tx_mock
    w3.eth.send_raw_transaction.return_value = bytes.fromhex("deadbeef" * 8)

    w3.eth.contract.return_value = contract_mock

    wallet = _make_wallet(w3)
    result = await wallet.merge_tokens(Decimal("75"), _CONDITION_ID)

    assert "tx_hash" in result
    assert result["amount_merged"] == Decimal("75")

    call_args = contract_mock.functions.mergePositions.call_args
    positional = call_args[0]
    assert positional[3] == [1, 2], "partition must be [1, 2]"
    assert positional[4] == 75_000_000, "amount must be scaled to 6 decimals"
    assert positional[1] == b"\x00" * 32


# ---------------------------------------------------------------------------
# Test: redeem_tokens
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redeem_tokens_calls_contract():
    """redeem_tokens calls redeemPositions and returns tx_hash + token_id."""
    w3 = _make_mock_w3()

    contract_mock = MagicMock()
    tx_mock = MagicMock()
    tx_mock.build_transaction.return_value = {"from": TEST_ADDRESS, "nonce": 0}
    contract_mock.functions.redeemPositions.return_value = tx_mock

    signed_tx_mock = MagicMock()
    signed_tx_mock.raw_transaction = b"\x00"
    w3.eth.account.sign_transaction.return_value = signed_tx_mock
    w3.eth.send_raw_transaction.return_value = bytes.fromhex("aabbccdd" * 8)

    w3.eth.contract.return_value = contract_mock

    wallet = _make_wallet(w3)
    result = await wallet.redeem_tokens("99999", _CONDITION_ID)

    assert "tx_hash" in result
    assert result["token_id"] == "99999"
    # redeemPositions should have been called at least once
    contract_mock.functions.redeemPositions.assert_called()


@pytest.mark.asyncio
async def test_redeem_tokens_falls_back_to_second_index_set():
    """redeem_tokens falls back to index_sets=[1] when [2] raises an exception."""
    w3 = _make_mock_w3()

    call_count = {"n": 0}
    fake_tx = {"from": TEST_ADDRESS, "nonce": 0}

    def _build_tx_side_effect(**kwargs):
        return fake_tx

    def _redeem_side_effect(*args, **kwargs):
        """Return a mock that fails on first build_transaction call, succeeds on second."""
        tx_mock = MagicMock()
        call_count["n"] += 1
        if call_count["n"] == 1:
            tx_mock.build_transaction.side_effect = RuntimeError("cannot estimate gas")
        else:
            tx_mock.build_transaction.return_value = fake_tx
        return tx_mock

    contract_mock = MagicMock()
    contract_mock.functions.redeemPositions.side_effect = _redeem_side_effect

    signed_tx_mock = MagicMock()
    signed_tx_mock.raw_transaction = b"\x00"
    w3.eth.account.sign_transaction.return_value = signed_tx_mock
    w3.eth.send_raw_transaction.return_value = b"\x11" * 32

    w3.eth.contract.return_value = contract_mock

    wallet = _make_wallet(w3)
    result = await wallet.redeem_tokens("12345", _CONDITION_ID)

    assert result["token_id"] == "12345"
    assert "tx_hash" in result
    # Both index set attempts were made
    assert call_count["n"] == 2


@pytest.mark.asyncio
async def test_redeem_tokens_raises_when_all_attempts_fail():
    """redeem_tokens re-raises the last error when both index sets fail."""
    w3 = _make_mock_w3()

    contract_mock = MagicMock()
    tx_mock = MagicMock()
    tx_mock.build_transaction.side_effect = RuntimeError("always fails")
    contract_mock.functions.redeemPositions.return_value = tx_mock

    w3.eth.contract.return_value = contract_mock

    wallet = _make_wallet(w3)
    with pytest.raises(RuntimeError, match="always fails"):
        await wallet.redeem_tokens("000", _CONDITION_ID)


# ---------------------------------------------------------------------------
# Test: bytes32 padding for condition_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_split_usdc_pads_short_condition_id():
    """split_usdc accepts a condition_id shorter than 64 hex chars and left-pads it."""
    w3 = _make_mock_w3()

    contract_mock = MagicMock()
    tx_mock = MagicMock()
    tx_mock.build_transaction.return_value = {"from": TEST_ADDRESS, "nonce": 0}
    contract_mock.functions.splitPosition.return_value = tx_mock

    signed_tx_mock = MagicMock()
    signed_tx_mock.raw_transaction = b"\x00"
    w3.eth.account.sign_transaction.return_value = signed_tx_mock
    w3.eth.send_raw_transaction.return_value = b"\xab" * 32
    w3.eth.contract.return_value = contract_mock

    wallet = _make_wallet(w3)
    # Only 4 hex chars → 2 bytes; should be left-padded to 32 bytes without raising
    short_condition_id = "0xabcd"
    result = await wallet.split_usdc(Decimal("10"), short_condition_id)

    assert result["amount_split"] == Decimal("10")
    # Verify the condition bytes passed to splitPosition are exactly 32 bytes
    call_args = contract_mock.functions.splitPosition.call_args
    positional = call_args[0]
    assert len(positional[2]) == 32
    assert positional[2] == b"\x00" * 30 + b"\xab\xcd"


@pytest.mark.asyncio
async def test_split_usdc_rejects_too_long_condition_id():
    """split_usdc raises ValueError when condition_id decodes to more than 32 bytes."""
    w3 = _make_mock_w3()
    w3.eth.contract.return_value = MagicMock()

    wallet = _make_wallet(w3)
    # 33 bytes = 66 hex chars
    too_long = "0x" + "ab" * 33
    with pytest.raises(ValueError, match="bytes32 requires at most 32 bytes"):
        await wallet.split_usdc(Decimal("10"), too_long)


# ---------------------------------------------------------------------------
# Test: sign_order missing fields validation
# ---------------------------------------------------------------------------


def test_sign_order_raises_on_missing_fields():
    """sign_order raises ValueError when required EIP-712 fields are absent."""
    wallet = _make_wallet()

    incomplete_order = {
        "salt": 1,
        "maker": TEST_ADDRESS,
        # All other required fields are intentionally omitted
    }

    with pytest.raises(ValueError, match="missing required fields"):
        wallet.sign_order(incomplete_order)
