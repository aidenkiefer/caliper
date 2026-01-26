"""
Unit tests for the positions endpoints.

Tests GET /v1/positions and GET /v1/positions/{id}.
"""

import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from tests.fixtures.api_data import get_mock_position


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


class TestListPositions:
    """Tests for GET /v1/positions endpoint."""
    
    def test_list_positions_returns_200(self, client):
        """Test that positions list returns 200 OK."""
        response = client.get("/v1/positions")
        assert response.status_code == 200
    
    def test_list_positions_returns_list(self, client):
        """Test that positions endpoint returns a list in data field."""
        response = client.get("/v1/positions")
        data = response.json()
        
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_list_positions_has_meta(self, client):
        """Test that response includes meta with pagination info."""
        response = client.get("/v1/positions")
        data = response.json()
        
        assert "meta" in data
        assert "total_count" in data["meta"]
        assert "page" in data["meta"]
        assert "per_page" in data["meta"]
        assert "total_unrealized_pnl" in data["meta"]
    
    def test_list_positions_item_structure(self, client):
        """Test that each position item has required fields per api-contracts.md."""
        response = client.get("/v1/positions")
        positions = response.json()["data"]
        
        if len(positions) > 0:
            position = positions[0]
            required_fields = [
                "position_id",
                "strategy_id",
                "symbol",
                "contract_type",
                "quantity",
                "average_entry_price",
                "current_price",
                "unrealized_pnl",
                "unrealized_pnl_pct",
                "market_value",
                "opened_at",
                "days_held",
            ]
            
            for field in required_fields:
                assert field in position, f"Missing field: {field}"
    
    def test_list_positions_filter_by_strategy(self, client):
        """Test filtering positions by strategy_id."""
        response = client.get("/v1/positions?strategy_id=momentum_v1")
        assert response.status_code == 200
        
        positions = response.json()["data"]
        for position in positions:
            assert position["strategy_id"] == "momentum_v1"
    
    def test_list_positions_filter_by_symbol(self, client):
        """Test filtering positions by symbol."""
        response = client.get("/v1/positions?symbol=AAPL")
        assert response.status_code == 200
        
        positions = response.json()["data"]
        for position in positions:
            assert position["symbol"] == "AAPL"
    
    def test_list_positions_filter_by_mode_paper(self, client):
        """Test filtering positions by PAPER mode."""
        response = client.get("/v1/positions?mode=PAPER")
        assert response.status_code == 200
    
    def test_list_positions_filter_by_mode_live(self, client):
        """Test filtering positions by LIVE mode."""
        response = client.get("/v1/positions?mode=LIVE")
        assert response.status_code == 200
    
    def test_list_positions_invalid_mode_rejected(self, client):
        """Test that invalid mode values are rejected."""
        response = client.get("/v1/positions?mode=INVALID")
        assert response.status_code == 400  # Custom handler returns 400
    
    def test_list_positions_pagination_default(self, client):
        """Test default pagination values."""
        response = client.get("/v1/positions")
        meta = response.json()["meta"]
        
        assert meta["page"] == 1
        assert meta["per_page"] == 20
    
    def test_list_positions_pagination_custom_page(self, client):
        """Test custom page parameter."""
        response = client.get("/v1/positions?page=2")
        assert response.status_code == 200
        
        meta = response.json()["meta"]
        assert meta["page"] == 2
    
    def test_list_positions_pagination_custom_per_page(self, client):
        """Test custom per_page parameter."""
        response = client.get("/v1/positions?per_page=10")
        assert response.status_code == 200
        
        meta = response.json()["meta"]
        assert meta["per_page"] == 10
    
    def test_list_positions_pagination_max_per_page(self, client):
        """Test that per_page is capped at 100."""
        response = client.get("/v1/positions?per_page=200")
        assert response.status_code == 400  # Custom handler returns 400
    
    def test_list_positions_pagination_min_page(self, client):
        """Test that page must be at least 1."""
        response = client.get("/v1/positions?page=0")
        assert response.status_code == 400  # Custom handler returns 400
    
    def test_list_positions_combined_filters(self, client):
        """Test combining multiple filters."""
        response = client.get(
            "/v1/positions?strategy_id=momentum_v1&symbol=AAPL"
        )
        assert response.status_code == 200
        
        positions = response.json()["data"]
        for position in positions:
            assert position["strategy_id"] == "momentum_v1"
            assert position["symbol"] == "AAPL"
    
    def test_list_positions_total_unrealized_pnl(self, client):
        """Test that total_unrealized_pnl is calculated correctly."""
        response = client.get("/v1/positions")
        data = response.json()
        
        positions = data["data"]
        meta = data["meta"]
        
        # Calculate expected total
        expected_total = sum(float(p["unrealized_pnl"]) for p in positions)
        actual_total = float(meta["total_unrealized_pnl"])
        
        # Allow small floating point difference
        assert abs(expected_total - actual_total) < 0.01
    
    def test_list_positions_quantity_is_string(self, client):
        """Test that quantity is returned as string (decimal precision)."""
        response = client.get("/v1/positions")
        positions = response.json()["data"]
        
        if len(positions) > 0:
            assert isinstance(positions[0]["quantity"], str)
    
    def test_list_positions_prices_are_strings(self, client):
        """Test that price values are returned as strings."""
        response = client.get("/v1/positions")
        positions = response.json()["data"]
        
        if len(positions) > 0:
            pos = positions[0]
            assert isinstance(pos["average_entry_price"], str)
            assert isinstance(pos["current_price"], str)
            assert isinstance(pos["market_value"], str)


class TestGetPosition:
    """Tests for GET /v1/positions/{position_id} endpoint."""
    
    def test_get_position_returns_200(self, client):
        """Test getting a known position returns 200."""
        response = client.get("/v1/positions/pos-001")
        assert response.status_code == 200
    
    def test_get_position_returns_data(self, client):
        """Test that position detail has data wrapper."""
        response = client.get("/v1/positions/pos-001")
        data = response.json()
        
        assert "data" in data
        assert isinstance(data["data"], dict)
    
    def test_get_position_detail_fields(self, client):
        """Test that position detail has all required fields per api-contracts.md."""
        response = client.get("/v1/positions/pos-001")
        position = response.json()["data"]
        
        required_fields = [
            "position_id",
            "strategy_id",
            "symbol",
            "quantity",
            "entry_orders",
            "unrealized_pnl",
            "risk_metrics",
        ]
        
        for field in required_fields:
            assert field in position, f"Missing field: {field}"
    
    def test_get_position_entry_orders_format(self, client):
        """Test that entry_orders has correct format."""
        response = client.get("/v1/positions/pos-001")
        entry_orders = response.json()["data"]["entry_orders"]
        
        assert isinstance(entry_orders, list)
        
        if len(entry_orders) > 0:
            order = entry_orders[0]
            required_fields = [
                "order_id",
                "filled_at",
                "quantity",
                "price",
            ]
            
            for field in required_fields:
                assert field in order, f"Missing order field: {field}"
    
    def test_get_position_risk_metrics_format(self, client):
        """Test that risk_metrics has correct format per api-contracts.md."""
        response = client.get("/v1/positions/pos-001")
        risk_metrics = response.json()["data"]["risk_metrics"]
        
        if risk_metrics:
            # These are optional per contract
            possible_fields = [
                "stop_loss_price",
                "take_profit_price",
                "max_loss",
                "max_profit",
            ]
            
            for field in possible_fields:
                if field in risk_metrics:
                    # Values can be None or strings
                    assert risk_metrics[field] is None or isinstance(risk_metrics[field], str)
    
    def test_get_position_not_found(self, client):
        """Test that unknown position returns 404."""
        response = client.get("/v1/positions/nonexistent-position")
        assert response.status_code == 404
    
    def test_get_position_404_has_detail(self, client):
        """Test that 404 response has detail message."""
        response = client.get("/v1/positions/nonexistent-position")
        data = response.json()
        
        assert "detail" in data
    
    def test_get_position_id_matches_request(self, client):
        """Test that returned position_id matches requested ID."""
        position_id = "pos-001"
        response = client.get(f"/v1/positions/{position_id}")
        data = response.json()["data"]
        
        assert data["position_id"] == position_id
    
    def test_get_position_has_symbol(self, client):
        """Test that position detail includes symbol."""
        response = client.get("/v1/positions/pos-001")
        data = response.json()["data"]
        
        assert "symbol" in data
        assert data["symbol"] is not None
    
    def test_get_position_has_unrealized_pnl(self, client):
        """Test that position detail includes unrealized P&L."""
        response = client.get("/v1/positions/pos-001")
        data = response.json()["data"]
        
        assert "unrealized_pnl" in data
        assert isinstance(data["unrealized_pnl"], str)


class TestPositionFactoryUsage:
    """Tests demonstrating factory function usage."""
    
    def test_factory_creates_valid_position(self):
        """Test that get_mock_position creates valid data."""
        position = get_mock_position()
        
        assert "position_id" in position
        assert "symbol" in position
        assert "quantity" in position
        assert "risk_metrics" in position
    
    def test_factory_accepts_overrides(self):
        """Test that factory accepts custom values."""
        position = get_mock_position({
            "symbol": "GOOGL",
            "quantity": "50.00",
        })
        
        assert position["symbol"] == "GOOGL"
        assert position["quantity"] == "50.00"
    
    def test_factory_generates_unique_ids(self):
        """Test that factory generates unique position IDs."""
        pos1 = get_mock_position()
        pos2 = get_mock_position()
        
        assert pos1["position_id"] != pos2["position_id"]
    
    def test_factory_risk_metrics_override(self):
        """Test that risk metrics can be overridden."""
        position = get_mock_position({
            "risk_metrics": {
                "stop_loss_price": "100.00",
                "max_loss": "-500.00",
            }
        })
        
        assert position["risk_metrics"]["stop_loss_price"] == "100.00"
        assert position["risk_metrics"]["max_loss"] == "-500.00"
        # Other fields should be preserved
        assert "take_profit_price" in position["risk_metrics"]
