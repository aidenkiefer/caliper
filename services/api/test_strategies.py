"""
Unit tests for the strategies endpoints.

Tests GET /v1/strategies, GET /v1/strategies/{id}, and PATCH /v1/strategies/{id}.
"""

import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from tests.fixtures.api_data import get_mock_strategy


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


class TestListStrategies:
    """Tests for GET /v1/strategies endpoint."""
    
    def test_list_strategies_returns_200(self, client):
        """Test that strategies list returns 200 OK."""
        response = client.get("/v1/strategies")
        assert response.status_code == 200
    
    def test_list_strategies_returns_list(self, client):
        """Test that strategies endpoint returns a list in data field."""
        response = client.get("/v1/strategies")
        data = response.json()
        
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_list_strategies_has_meta(self, client):
        """Test that response includes meta with counts."""
        response = client.get("/v1/strategies")
        data = response.json()
        
        assert "meta" in data
        assert "total_count" in data["meta"]
        assert "active_count" in data["meta"]
    
    def test_list_strategies_item_structure(self, client):
        """Test that each strategy item has required fields."""
        response = client.get("/v1/strategies")
        strategies = response.json()["data"]
        
        if len(strategies) > 0:
            strategy = strategies[0]
            required_fields = [
                "strategy_id",
                "name",
                "status",
                "mode",
                "created_at",
                "updated_at",
            ]
            
            for field in required_fields:
                assert field in strategy, f"Missing field: {field}"
    
    def test_list_strategies_filter_by_status_active(self, client):
        """Test filtering strategies by active status."""
        response = client.get("/v1/strategies?status=active")
        assert response.status_code == 200
        
        strategies = response.json()["data"]
        for strategy in strategies:
            assert strategy["status"] == "active"
    
    def test_list_strategies_filter_by_status_inactive(self, client):
        """Test filtering strategies by inactive status."""
        response = client.get("/v1/strategies?status=inactive")
        assert response.status_code == 200
        
        strategies = response.json()["data"]
        for strategy in strategies:
            assert strategy["status"] == "inactive"
    
    def test_list_strategies_filter_by_status_all(self, client):
        """Test filtering with status=all returns all strategies."""
        response = client.get("/v1/strategies?status=all")
        assert response.status_code == 200
    
    def test_list_strategies_filter_by_mode_backtest(self, client):
        """Test filtering strategies by BACKTEST mode."""
        response = client.get("/v1/strategies?mode=BACKTEST")
        assert response.status_code == 200
        
        strategies = response.json()["data"]
        for strategy in strategies:
            assert strategy["mode"] == "BACKTEST"
    
    def test_list_strategies_filter_by_mode_paper(self, client):
        """Test filtering strategies by PAPER mode."""
        response = client.get("/v1/strategies?mode=PAPER")
        assert response.status_code == 200
        
        strategies = response.json()["data"]
        for strategy in strategies:
            assert strategy["mode"] == "PAPER"
    
    def test_list_strategies_filter_by_mode_live(self, client):
        """Test filtering strategies by LIVE mode."""
        response = client.get("/v1/strategies?mode=LIVE")
        assert response.status_code == 200
    
    def test_list_strategies_invalid_status_rejected(self, client):
        """Test that invalid status values are rejected."""
        response = client.get("/v1/strategies?status=invalid")
        assert response.status_code == 400  # Custom handler returns 400
    
    def test_list_strategies_invalid_mode_rejected(self, client):
        """Test that invalid mode values are rejected."""
        response = client.get("/v1/strategies?mode=INVALID")
        assert response.status_code == 400  # Custom handler returns 400
    
    def test_list_strategies_meta_counts_match(self, client):
        """Test that meta counts match actual data."""
        response = client.get("/v1/strategies")
        data = response.json()
        
        strategies = data["data"]
        meta = data["meta"]
        
        assert meta["total_count"] == len(strategies)
        
        active_count = sum(1 for s in strategies if s["status"] == "active")
        assert meta["active_count"] == active_count


class TestGetStrategy:
    """Tests for GET /v1/strategies/{strategy_id} endpoint."""
    
    def test_get_strategy_returns_200(self, client):
        """Test getting a known strategy returns 200."""
        response = client.get("/v1/strategies/momentum_v1")
        assert response.status_code == 200
    
    def test_get_strategy_returns_data(self, client):
        """Test that strategy detail has data wrapper."""
        response = client.get("/v1/strategies/momentum_v1")
        data = response.json()
        
        assert "data" in data
        assert isinstance(data["data"], dict)
    
    def test_get_strategy_detail_fields(self, client):
        """Test that strategy detail has all required fields."""
        response = client.get("/v1/strategies/momentum_v1")
        strategy = response.json()["data"]
        
        required_fields = [
            "strategy_id",
            "name",
            "status",
            "config",
            "performance",
        ]
        
        for field in required_fields:
            assert field in strategy, f"Missing field: {field}"
    
    def test_get_strategy_config_fields(self, client):
        """Test that strategy config has expected fields."""
        response = client.get("/v1/strategies/momentum_v1")
        config = response.json()["data"]["config"]
        
        # Config can have optional fields per api-contracts.md
        assert isinstance(config, dict)
        
        # Check for typical config fields if present
        if config:
            possible_fields = [
                "model_type",
                "features",
                "signal_threshold",
                "stop_loss_pct",
                "take_profit_pct",
            ]
            # At least some config should be present
            assert any(f in config for f in possible_fields)
    
    def test_get_strategy_performance_fields(self, client):
        """Test that strategy performance has expected fields."""
        response = client.get("/v1/strategies/momentum_v1")
        performance = response.json()["data"]["performance"]
        
        if performance:
            expected_fields = [
                "total_pnl",
                "sharpe_ratio",
                "max_drawdown",
                "win_rate",
            ]
            
            for field in expected_fields:
                assert field in performance, f"Missing performance field: {field}"
    
    def test_get_strategy_not_found(self, client):
        """Test that unknown strategy returns 404."""
        response = client.get("/v1/strategies/nonexistent_strategy")
        assert response.status_code == 404
    
    def test_get_strategy_404_has_detail(self, client):
        """Test that 404 response has detail message."""
        response = client.get("/v1/strategies/nonexistent_strategy")
        data = response.json()
        
        assert "detail" in data
    
    def test_get_strategy_id_matches_request(self, client):
        """Test that returned strategy_id matches requested ID."""
        strategy_id = "momentum_v1"
        response = client.get(f"/v1/strategies/{strategy_id}")
        data = response.json()["data"]
        
        assert data["strategy_id"] == strategy_id


class TestUpdateStrategy:
    """Tests for PATCH /v1/strategies/{strategy_id} endpoint."""
    
    def test_update_strategy_returns_200(self, client):
        """Test updating a strategy returns 200."""
        response = client.patch(
            "/v1/strategies/momentum_v1",
            json={"status": "inactive"}
        )
        assert response.status_code == 200
    
    def test_update_strategy_has_message(self, client):
        """Test that update response has success message."""
        response = client.patch(
            "/v1/strategies/momentum_v1",
            json={"status": "active"}
        )
        data = response.json()
        
        assert "message" in data
        assert "success" in data["message"].lower()
    
    def test_update_strategy_has_data(self, client):
        """Test that update response includes updated strategy data."""
        response = client.patch(
            "/v1/strategies/momentum_v1",
            json={"status": "active"}
        )
        data = response.json()
        
        assert "data" in data
        assert "strategy_id" in data["data"]
    
    def test_update_strategy_status_change(self, client):
        """Test that status update is reflected in response."""
        # Set to inactive
        response = client.patch(
            "/v1/strategies/momentum_v1",
            json={"status": "inactive"}
        )
        data = response.json()["data"]
        assert data["status"] == "inactive"
        
        # Set back to active
        response = client.patch(
            "/v1/strategies/momentum_v1",
            json={"status": "active"}
        )
        data = response.json()["data"]
        assert data["status"] == "active"
    
    def test_update_strategy_config(self, client):
        """Test that config update is reflected in response."""
        response = client.patch(
            "/v1/strategies/momentum_v1",
            json={"config": {"signal_threshold": 0.75}}
        )
        assert response.status_code == 200
        
        # Verify the update took effect
        data = response.json()["data"]
        assert data["config"]["signal_threshold"] == 0.75
    
    def test_update_strategy_not_found(self, client):
        """Test that updating unknown strategy returns 404."""
        response = client.patch(
            "/v1/strategies/nonexistent_strategy",
            json={"status": "inactive"}
        )
        assert response.status_code == 404
    
    def test_update_strategy_empty_body(self, client):
        """Test update with empty body succeeds (no-op)."""
        response = client.patch(
            "/v1/strategies/momentum_v1",
            json={}
        )
        assert response.status_code == 200
    
    def test_update_strategy_preserves_unchanged_fields(self, client):
        """Test that unchanged fields are preserved after update."""
        # Get original strategy
        original = client.get("/v1/strategies/momentum_v1").json()["data"]
        original_name = original["name"]
        
        # Update only status
        response = client.patch(
            "/v1/strategies/momentum_v1",
            json={"status": "active"}
        )
        updated = response.json()["data"]
        
        # Name should be unchanged
        assert updated["name"] == original_name


class TestStrategyFactoryUsage:
    """Tests demonstrating factory function usage."""
    
    def test_factory_creates_valid_strategy(self):
        """Test that get_mock_strategy creates valid data."""
        strategy = get_mock_strategy()
        
        assert "strategy_id" in strategy
        assert "name" in strategy
        assert "status" in strategy
        assert "config" in strategy
    
    def test_factory_accepts_overrides(self):
        """Test that factory accepts custom values."""
        strategy = get_mock_strategy({
            "name": "Custom Strategy",
            "status": "inactive",
        })
        
        assert strategy["name"] == "Custom Strategy"
    
    def test_factory_generates_unique_ids(self):
        """Test that factory generates unique strategy IDs."""
        strategy1 = get_mock_strategy()
        strategy2 = get_mock_strategy()
        
        assert strategy1["strategy_id"] != strategy2["strategy_id"]
