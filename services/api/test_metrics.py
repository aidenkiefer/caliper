"""
Unit tests for the metrics endpoint.

Tests the GET /v1/metrics/summary endpoint for aggregated metrics.
"""

import pytest
from fastapi.testclient import TestClient

from services.api.main import app


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


class TestMetricsSummaryEndpoint:
    """Tests for GET /v1/metrics/summary endpoint."""
    
    def test_metrics_summary_returns_200(self, client):
        """Test that metrics summary endpoint returns 200 OK."""
        response = client.get("/v1/metrics/summary")
        assert response.status_code == 200
    
    def test_metrics_summary_has_data(self, client):
        """Test that metrics summary includes data object."""
        response = client.get("/v1/metrics/summary")
        data = response.json()
        
        assert "data" in data
        assert isinstance(data["data"], dict)
    
    def test_metrics_summary_has_meta(self, client):
        """Test that metrics summary includes meta object."""
        response = client.get("/v1/metrics/summary")
        data = response.json()
        
        assert "meta" in data
        assert isinstance(data["meta"], dict)
    
    def test_metrics_summary_data_fields(self, client):
        """Test that metrics data contains required fields per api-contracts.md."""
        response = client.get("/v1/metrics/summary")
        data = response.json()["data"]
        
        required_fields = [
            "total_pnl",
            "total_pnl_percent",
            "sharpe_ratio",
            "max_drawdown",
            "win_rate",
            "total_trades",
            "active_positions",
            "capital_deployed",
            "available_capital",
            "equity_curve",
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_metrics_summary_meta_fields(self, client):
        """Test that meta contains required fields."""
        response = client.get("/v1/metrics/summary")
        meta = response.json()["meta"]
        
        assert "period" in meta
        assert "updated_at" in meta
    
    def test_metrics_summary_equity_curve_format(self, client):
        """Test equity curve has correct format."""
        response = client.get("/v1/metrics/summary")
        equity_curve = response.json()["data"]["equity_curve"]
        
        assert isinstance(equity_curve, list)
        assert len(equity_curve) > 0
        
        # Check each point has date and value
        for point in equity_curve:
            assert "date" in point
            assert "value" in point
    
    def test_metrics_summary_default_period(self, client):
        """Test default period is 1m when not specified."""
        response = client.get("/v1/metrics/summary")
        meta = response.json()["meta"]
        
        assert meta["period"] == "1m"
    
    def test_metrics_summary_with_period_1d(self, client):
        """Test metrics with period=1d parameter."""
        response = client.get("/v1/metrics/summary?period=1d")
        assert response.status_code == 200
        
        meta = response.json()["meta"]
        assert meta["period"] == "1d"
    
    def test_metrics_summary_with_period_1w(self, client):
        """Test metrics with period=1w parameter."""
        response = client.get("/v1/metrics/summary?period=1w")
        assert response.status_code == 200
        
        meta = response.json()["meta"]
        assert meta["period"] == "1w"
    
    def test_metrics_summary_with_period_3m(self, client):
        """Test metrics with period=3m parameter."""
        response = client.get("/v1/metrics/summary?period=3m")
        assert response.status_code == 200
        
        meta = response.json()["meta"]
        assert meta["period"] == "3m"
    
    def test_metrics_summary_with_period_1y(self, client):
        """Test metrics with period=1y parameter."""
        response = client.get("/v1/metrics/summary?period=1y")
        assert response.status_code == 200
        
        meta = response.json()["meta"]
        assert meta["period"] == "1y"
    
    def test_metrics_summary_with_period_all(self, client):
        """Test metrics with period=all parameter."""
        response = client.get("/v1/metrics/summary?period=all")
        assert response.status_code == 200
        
        meta = response.json()["meta"]
        assert meta["period"] == "all"
    
    def test_metrics_summary_invalid_period_rejected(self, client):
        """Test that invalid period values are rejected."""
        response = client.get("/v1/metrics/summary?period=invalid")
        assert response.status_code == 400  # Custom handler returns 400
    
    def test_metrics_summary_with_mode_paper(self, client):
        """Test metrics with mode=PAPER filter."""
        response = client.get("/v1/metrics/summary?mode=PAPER")
        assert response.status_code == 200
    
    def test_metrics_summary_with_mode_live(self, client):
        """Test metrics with mode=LIVE filter."""
        response = client.get("/v1/metrics/summary?mode=LIVE")
        assert response.status_code == 200
    
    def test_metrics_summary_invalid_mode_rejected(self, client):
        """Test that invalid mode values are rejected."""
        response = client.get("/v1/metrics/summary?mode=INVALID")
        assert response.status_code == 400  # Custom handler returns 400
    
    def test_metrics_summary_combined_params(self, client):
        """Test metrics with both period and mode parameters."""
        response = client.get("/v1/metrics/summary?period=1w&mode=PAPER")
        assert response.status_code == 200
        
        meta = response.json()["meta"]
        assert meta["period"] == "1w"
    
    def test_metrics_pnl_is_string(self, client):
        """Test that P&L values are returned as strings (decimal precision)."""
        response = client.get("/v1/metrics/summary")
        data = response.json()["data"]
        
        # Per api-contracts.md, monetary values are strings
        assert isinstance(data["total_pnl"], str)
        assert isinstance(data["capital_deployed"], str)
        assert isinstance(data["available_capital"], str)
    
    def test_metrics_trades_is_integer(self, client):
        """Test that trade counts are integers."""
        response = client.get("/v1/metrics/summary")
        data = response.json()["data"]
        
        assert isinstance(data["total_trades"], int)
        assert isinstance(data["active_positions"], int)
