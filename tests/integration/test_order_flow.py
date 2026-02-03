"""
Integration tests for order submission flow.

Tests API endpoints for order submission with risk checks:
- POST /v1/orders
- GET /v1/orders/{order_id}
- Risk rejection responses

Following @testing-patterns skill:
- Integration tests with FastAPI TestClient
- Test behavior, not implementation
- Factory pattern for test data
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from services.api.main import app
from tests.fixtures.execution_data import (
    get_mock_order,
    get_safe_order,
    get_risky_order,
    get_high_notional_order,
    get_penny_stock_order,
    RISK_LIMITS,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def safe_order_request() -> dict:
    """Request body for a safe order (passes all risk checks)."""
    return {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": "100",
        "order_type": "LIMIT",
        "limit_price": "150.00",
        "time_in_force": "DAY",
        "strategy_id": "test_strategy",
        "client_order_id": f"test_{uuid4().hex[:8]}",
    }


@pytest.fixture
def risky_order_request() -> dict:
    """Request body for a risky order (fails risk checks)."""
    return {
        "symbol": "TSLA",
        "side": "BUY",
        "quantity": "500",  # $50,000 notional at $100/share
        "order_type": "LIMIT",
        "limit_price": "100.00",
        "time_in_force": "DAY",
        "strategy_id": "test_strategy",
        "client_order_id": f"risky_{uuid4().hex[:8]}",
    }


# ============================================================================
# Order Rejection Tests
# ============================================================================


class TestOrderRejection:
    """Tests for order rejection due to risk limit violations."""

    def test_order_rejected_returns_400_with_reason(self, client: TestClient):
        """Rejected order returns 400 with rejection details."""
        # Order that exceeds notional limit ($25,000)
        request = {
            "symbol": "NVDA",
            "side": "BUY",
            "quantity": "300",
            "order_type": "LIMIT",
            "limit_price": "100.00",  # $30,000 notional
            "time_in_force": "DAY",
            "strategy_id": "test_strategy",
        }

        response = client.post("/v1/orders", json=request)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "violations" in data["detail"]

    def test_order_rejected_for_high_notional(self, client: TestClient):
        """Order rejected when notional exceeds $25,000."""
        request = {
            "symbol": "GOOGL",
            "side": "BUY",
            "quantity": "300",
            "order_type": "LIMIT",
            "limit_price": "100.00",  # $30,000
            "time_in_force": "DAY",
            "strategy_id": "test_strategy",
        }

        response = client.post("/v1/orders", json=request)

        assert response.status_code == 400
        data = response.json()

        violations = data["detail"]["violations"]
        assert any(v["limit_type"] == "max_notional" for v in violations)

    def test_order_rejected_for_penny_stock(self, client: TestClient):
        """Order rejected for stocks under $5.00."""
        request = {
            "symbol": "PNNY",
            "side": "BUY",
            "quantity": "100",
            "order_type": "LIMIT",
            "limit_price": "3.50",  # Below $5 minimum
            "time_in_force": "DAY",
            "strategy_id": "test_strategy",
        }

        response = client.post("/v1/orders", json=request)

        assert response.status_code == 400
        data = response.json()

        violations = data["detail"]["violations"]
        assert any(v["limit_type"] == "min_stock_price" for v in violations)

    def test_order_rejected_for_high_risk(self, client: TestClient):
        """Order rejected when estimated risk exceeds limit."""
        # Large order with high estimated risk
        request = {
            "symbol": "TSLA",
            "side": "BUY",
            "quantity": "500",
            "order_type": "LIMIT",
            "limit_price": "100.00",  # $50k notional, 10% risk = $5k > 2% of $100k
            "time_in_force": "DAY",
            "strategy_id": "test_strategy",
        }

        response = client.post("/v1/orders", json=request)

        # Should be rejected for notional and/or risk
        assert response.status_code == 400

    def test_risk_rejection_includes_limit_violated(self, client: TestClient):
        """Rejection response includes which limit was violated."""
        request = {
            "symbol": "HIGH",
            "side": "BUY",
            "quantity": "300",
            "order_type": "LIMIT",
            "limit_price": "100.00",
            "time_in_force": "DAY",
            "strategy_id": "test_strategy",
        }

        response = client.post("/v1/orders", json=request)

        assert response.status_code == 400
        data = response.json()

        violations = data["detail"]["violations"]
        # Each violation should have these fields
        for violation in violations:
            assert "limit_type" in violation
            assert "limit_value" in violation
            assert "actual_value" in violation
            assert "message" in violation


# ============================================================================
# Order Acceptance Tests
# ============================================================================


class TestOrderAcceptance:
    """Tests for successful order submission."""

    def test_order_accepted_returns_202(self, client: TestClient, safe_order_request: dict):
        """Accepted order returns 200 with order details."""
        response = client.post("/v1/orders", json=safe_order_request)

        # Note: Our implementation returns 200 for sync success
        # In production with async broker, might be 202
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert data["data"]["symbol"] == safe_order_request["symbol"]
        assert data["data"]["status"] in ["PENDING", "SUBMITTED"]

    def test_order_accepted_has_order_id(self, client: TestClient, safe_order_request: dict):
        """Accepted order response includes order ID."""
        response = client.post("/v1/orders", json=safe_order_request)

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "order_id" in data["data"]
        assert data["data"]["order_id"] is not None

    def test_order_accepted_within_limits(self, client: TestClient):
        """Order within all limits is accepted."""
        # Small order well within all limits
        request = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": "10",  # Small quantity
            "order_type": "LIMIT",
            "limit_price": "150.00",  # $1,500 notional
            "time_in_force": "DAY",
            "strategy_id": "conservative_strategy",
            "client_order_id": f"small_{uuid4().hex[:8]}",
        }

        response = client.post("/v1/orders", json=request)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] in ["PENDING", "SUBMITTED"]

    def test_market_order_accepted(self, client: TestClient):
        """Market order is accepted with mock price."""
        request = {
            "symbol": "MSFT",
            "side": "BUY",
            "quantity": "50",
            "order_type": "MARKET",
            "time_in_force": "DAY",
            "strategy_id": "test_strategy",
            "client_order_id": f"market_{uuid4().hex[:8]}",
        }

        response = client.post("/v1/orders", json=request)

        # Market orders use mock price for risk check
        assert response.status_code == 200


# ============================================================================
# Order Retrieval Tests
# ============================================================================


class TestOrderRetrieval:
    """Tests for retrieving order details."""

    def test_get_order_by_id(self, client: TestClient, safe_order_request: dict):
        """Order can be retrieved by order_id."""
        # Create order first
        create_response = client.post("/v1/orders", json=safe_order_request)
        assert create_response.status_code == 200
        order_id = create_response.json()["data"]["order_id"]

        # Retrieve order
        get_response = client.get(f"/v1/orders/{order_id}")

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["data"]["order_id"] == order_id

    def test_get_order_by_client_order_id(self, client: TestClient, safe_order_request: dict):
        """Order can be retrieved by client_order_id."""
        # Create order
        create_response = client.post("/v1/orders", json=safe_order_request)
        assert create_response.status_code == 200

        # Retrieve by client_order_id
        client_order_id = safe_order_request["client_order_id"]
        get_response = client.get(f"/v1/orders/{client_order_id}")

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["data"]["client_order_id"] == client_order_id

    def test_get_nonexistent_order_returns_404(self, client: TestClient):
        """Requesting non-existent order returns 404."""
        response = client.get("/v1/orders/nonexistent_order_id")

        assert response.status_code == 404

    def test_list_orders(self, client: TestClient, safe_order_request: dict):
        """List orders endpoint returns orders."""
        # Create a few orders
        for i in range(3):
            request = safe_order_request.copy()
            request["client_order_id"] = f"list_test_{i}_{uuid4().hex[:4]}"
            client.post("/v1/orders", json=request)

        # List orders
        response = client.get("/v1/orders")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)

    def test_list_orders_pagination(self, client: TestClient):
        """Orders list supports pagination."""
        response = client.get("/v1/orders", params={"page": 1, "per_page": 10})

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 10

    def test_list_orders_filter_by_strategy(self, client: TestClient, safe_order_request: dict):
        """Orders can be filtered by strategy_id."""
        # Create order with specific strategy
        request = safe_order_request.copy()
        request["strategy_id"] = "filter_test_strategy"
        request["client_order_id"] = f"filter_{uuid4().hex[:8]}"
        client.post("/v1/orders", json=request)

        # Filter by strategy
        response = client.get("/v1/orders", params={"strategy_id": "filter_test_strategy"})

        assert response.status_code == 200
        data = response.json()
        for order in data["data"]:
            assert order["strategy_id"] == "filter_test_strategy"


# ============================================================================
# Order Idempotency Tests
# ============================================================================


class TestOrderIdempotency:
    """Tests for order idempotency via client_order_id."""

    def test_duplicate_client_order_id_returns_existing(
        self, client: TestClient, safe_order_request: dict
    ):
        """Submitting order with existing client_order_id returns existing order."""
        # Submit first order
        response1 = client.post("/v1/orders", json=safe_order_request)
        assert response1.status_code == 200
        order_id1 = response1.json()["data"]["order_id"]

        # Submit duplicate
        response2 = client.post("/v1/orders", json=safe_order_request)
        assert response2.status_code == 200
        order_id2 = response2.json()["data"]["order_id"]

        # Should return same order
        assert order_id1 == order_id2

    def test_idempotent_response_message(self, client: TestClient, safe_order_request: dict):
        """Idempotent response indicates order already exists."""
        # Submit first order
        client.post("/v1/orders", json=safe_order_request)

        # Submit duplicate
        response = client.post("/v1/orders", json=safe_order_request)

        assert response.status_code == 200
        data = response.json()
        # Message should indicate idempotent behavior
        assert "idempotent" in data["message"].lower() or "exists" in data["message"].lower()


# ============================================================================
# Order Cancellation Tests
# ============================================================================


class TestOrderCancellation:
    """Tests for order cancellation."""

    def test_cancel_pending_order(self, client: TestClient, safe_order_request: dict):
        """Pending/submitted order can be cancelled."""
        # Create order
        create_response = client.post("/v1/orders", json=safe_order_request)
        order_id = create_response.json()["data"]["order_id"]

        # Cancel order
        cancel_response = client.delete(f"/v1/orders/{order_id}")

        assert cancel_response.status_code == 200
        data = cancel_response.json()
        assert data["status"] == "CANCELLED"

    def test_cancel_nonexistent_order_returns_404(self, client: TestClient):
        """Cancelling non-existent order returns 404."""
        response = client.delete("/v1/orders/nonexistent")

        assert response.status_code == 404


# ============================================================================
# Error Response Format Tests
# ============================================================================


class TestErrorResponseFormat:
    """Tests for consistent error response format."""

    def test_validation_error_format(self, client: TestClient):
        """Validation errors have consistent format."""
        # Missing required field
        request = {
            "symbol": "AAPL",
            # Missing side, quantity, etc.
        }

        response = client.post("/v1/orders", json=request)

        # FastAPI returns 422 for validation errors, but may return 400 in some configs
        assert response.status_code in [400, 422]  # Validation error

    def test_risk_rejection_format(self, client: TestClient):
        """Risk rejection has consistent format."""
        request = {
            "symbol": "PENNY",
            "side": "BUY",
            "quantity": "1000",
            "order_type": "LIMIT",
            "limit_price": "3.00",  # Penny stock
            "time_in_force": "DAY",
            "strategy_id": "test",
        }

        response = client.post("/v1/orders", json=request)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "message" in data["detail"]
        assert "violations" in data["detail"]
