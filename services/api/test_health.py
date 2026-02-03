"""
Unit tests for the health endpoint.

Tests the GET /v1/health endpoint for system health checks.
"""

import pytest
from fastapi.testclient import TestClient

from services.api.main import app


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /v1/health endpoint."""

    def test_health_returns_200(self, client):
        """Test that health endpoint returns 200 OK."""
        response = client.get("/v1/health")
        assert response.status_code == 200

    def test_health_response_has_status(self, client):
        """Test that health response includes overall status."""
        response = client.get("/v1/health")
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_response_has_services(self, client):
        """Test that health response includes service statuses."""
        response = client.get("/v1/health")
        data = response.json()

        assert "services" in data
        assert isinstance(data["services"], dict)

        # Check expected services are present
        expected_services = ["database", "data_feed", "broker_connection", "redis"]
        for service in expected_services:
            assert service in data["services"], f"Missing service: {service}"

    def test_health_response_has_timestamp(self, client):
        """Test that health response includes timestamp."""
        response = client.get("/v1/health")
        data = response.json()

        assert "timestamp" in data
        assert data["timestamp"] is not None

    def test_health_service_status_format(self, client):
        """Test that each service has a status field."""
        response = client.get("/v1/health")
        data = response.json()

        for service_name, service_data in data["services"].items():
            assert "status" in service_data, f"Service {service_name} missing status"
            assert service_data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_database_service_has_latency(self, client):
        """Test that database service includes latency metric."""
        response = client.get("/v1/health")
        data = response.json()

        db_service = data["services"]["database"]
        assert "latency_ms" in db_service
        assert isinstance(db_service["latency_ms"], int)

    def test_health_data_feed_has_staleness(self, client):
        """Test that data_feed service includes staleness metric."""
        response = client.get("/v1/health")
        data = response.json()

        feed_service = data["services"]["data_feed"]
        assert "staleness_seconds" in feed_service
        assert isinstance(feed_service["staleness_seconds"], int)

    def test_health_broker_has_mode(self, client):
        """Test that broker_connection includes mode."""
        response = client.get("/v1/health")
        data = response.json()

        broker_service = data["services"]["broker_connection"]
        assert "broker" in broker_service
        assert "mode" in broker_service
        assert broker_service["mode"] in ["PAPER", "LIVE"]

    def test_healthy_status_when_all_services_healthy(self, client):
        """Test overall status is healthy when all services are healthy."""
        response = client.get("/v1/health")
        data = response.json()

        # If all services are healthy, overall should be healthy
        all_healthy = all(s["status"] == "healthy" for s in data["services"].values())

        if all_healthy:
            assert data["status"] == "healthy"

    def test_health_response_matches_contract(self, client):
        """Test that health response matches api-contracts.md format."""
        response = client.get("/v1/health")
        data = response.json()

        # Validate top-level structure
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data

        # Validate service structure matches contract
        # Contract specifies: status, latency_ms, last_update, staleness_seconds, broker, mode
        db = data["services"]["database"]
        assert "status" in db

        feed = data["services"]["data_feed"]
        assert "status" in feed
        assert "last_update" in feed or "staleness_seconds" in feed

        broker = data["services"]["broker_connection"]
        assert "status" in broker
        assert "broker" in broker
        assert "mode" in broker
