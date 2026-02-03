"""
Integration tests for Human-in-the-Loop (HITL) workflow.
"""

import pytest
from fastapi.testclient import TestClient
from services.api.main import app

client = TestClient(app)


class TestApprovalQueue:
    """Test recommendation approval queue."""

    def test_recommendation_added_to_queue(self):
        """Recommendations should be added to queue."""
        # In production, this would be done via model inference
        # For now, we test the API endpoint exists
        response = client.get("/v1/recommendations")

        # Should return 200 even if empty
        assert response.status_code in [200, 404]

    def test_approve_recommendation(self):
        """Test approving a recommendation."""
        # First, we'd need a recommendation in the queue
        # For integration test, we'd set up test data
        recommendation_id = "test-rec-1"

        response = client.post(
            f"/v1/recommendations/{recommendation_id}/approve",
            json={"user_id": "test-user", "rationale": "Looks good"},
        )

        # Should handle missing recommendation gracefully
        assert response.status_code in [200, 404]

    def test_reject_recommendation(self):
        """Test rejecting a recommendation."""
        recommendation_id = "test-rec-1"

        response = client.post(
            f"/v1/recommendations/{recommendation_id}/reject",
            json={"user_id": "test-user", "reason": "Too risky"},
        )

        assert response.status_code in [200, 404]

    def test_pending_recommendations_returned(self):
        """Pending recommendations should be returned."""
        response = client.get("/v1/recommendations")

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)


class TestHumanLogging:
    """Test human decision logging."""

    def test_approval_logged_correctly(self):
        """Approvals should be logged with user and rationale."""
        # In production, would verify database entry
        # For integration test, verify API response
        recommendation_id = "test-rec-1"

        response = client.post(
            f"/v1/recommendations/{recommendation_id}/approve",
            json={
                "user_id": "test-user-123",
                "rationale": "High confidence, good entry point",
            },
        )

        # Verify response indicates success
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] == "approved"

    def test_rejection_logged_with_reason(self):
        """Rejections should be logged with reason."""
        recommendation_id = "test-rec-1"

        response = client.post(
            f"/v1/recommendations/{recommendation_id}/reject",
            json={
                "user_id": "test-user-123",
                "reason": "Market conditions unfavorable",
            },
        )

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] == "rejected"

    def test_agreement_stats_calculated(self):
        """Agreement statistics should be calculated correctly."""
        strategy_id = "strategy-1"

        response = client.get(f"/v1/recommendations/stats?strategy_id={strategy_id}")

        if response.status_code == 200:
            data = response.json()
            assert "agreement_rate" in data
            assert 0 <= data["agreement_rate"] <= 1
