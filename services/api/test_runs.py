"""
Unit tests for the runs endpoints.

Tests GET /v1/runs, GET /v1/runs/{id}, and POST /v1/runs.
"""

import pytest
from fastapi.testclient import TestClient

from services.api.main import app
from tests.fixtures.api_data import get_mock_backtest_run


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


class TestListRuns:
    """Tests for GET /v1/runs endpoint."""

    def test_list_runs_returns_200(self, client):
        """Test that runs list returns 200 OK."""
        response = client.get("/v1/runs")
        assert response.status_code == 200

    def test_list_runs_returns_list(self, client):
        """Test that runs endpoint returns a list in data field."""
        response = client.get("/v1/runs")
        data = response.json()

        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_runs_has_meta(self, client):
        """Test that response includes meta with pagination info."""
        response = client.get("/v1/runs")
        data = response.json()

        assert "meta" in data
        assert "total_count" in data["meta"]
        assert "page" in data["meta"]
        assert "per_page" in data["meta"]

    def test_list_runs_item_structure(self, client):
        """Test that each run item has required fields."""
        response = client.get("/v1/runs")
        runs = response.json()["data"]

        if len(runs) > 0:
            run = runs[0]
            required_fields = [
                "run_id",
                "strategy_id",
                "run_type",
                "start_date",
                "end_date",
                "status",
                "created_at",
            ]

            for field in required_fields:
                assert field in run, f"Missing field: {field}"

    def test_list_runs_filter_by_strategy(self, client):
        """Test filtering runs by strategy_id."""
        response = client.get("/v1/runs?strategy_id=momentum_v1")
        assert response.status_code == 200

        runs = response.json()["data"]
        for run in runs:
            assert run["strategy_id"] == "momentum_v1"

    def test_list_runs_filter_by_type_backtest(self, client):
        """Test filtering runs by BACKTEST type."""
        response = client.get("/v1/runs?run_type=BACKTEST")
        assert response.status_code == 200

        runs = response.json()["data"]
        for run in runs:
            assert run["run_type"] == "BACKTEST"

    def test_list_runs_filter_by_type_paper(self, client):
        """Test filtering runs by PAPER type."""
        response = client.get("/v1/runs?run_type=PAPER")
        assert response.status_code == 200

        runs = response.json()["data"]
        for run in runs:
            assert run["run_type"] == "PAPER"

    def test_list_runs_filter_by_type_live(self, client):
        """Test filtering runs by LIVE type."""
        response = client.get("/v1/runs?run_type=LIVE")
        assert response.status_code == 200

    def test_list_runs_filter_by_status_running(self, client):
        """Test filtering runs by RUNNING status."""
        response = client.get("/v1/runs?status=RUNNING")
        assert response.status_code == 200

        runs = response.json()["data"]
        for run in runs:
            assert run["status"] == "RUNNING"

    def test_list_runs_filter_by_status_completed(self, client):
        """Test filtering runs by COMPLETED status."""
        response = client.get("/v1/runs?status=COMPLETED")
        assert response.status_code == 200

        runs = response.json()["data"]
        for run in runs:
            assert run["status"] == "COMPLETED"

    def test_list_runs_filter_by_status_failed(self, client):
        """Test filtering runs by FAILED status."""
        response = client.get("/v1/runs?status=FAILED")
        assert response.status_code == 200

    def test_list_runs_invalid_type_rejected(self, client):
        """Test that invalid run_type values are rejected."""
        response = client.get("/v1/runs?run_type=INVALID")
        assert response.status_code == 400  # Custom handler returns 400

    def test_list_runs_invalid_status_rejected(self, client):
        """Test that invalid status values are rejected."""
        response = client.get("/v1/runs?status=INVALID")
        assert response.status_code == 400  # Custom handler returns 400

    def test_list_runs_pagination_default(self, client):
        """Test default pagination values."""
        response = client.get("/v1/runs")
        meta = response.json()["meta"]

        assert meta["page"] == 1
        assert meta["per_page"] == 20

    def test_list_runs_pagination_custom_page(self, client):
        """Test custom page parameter."""
        response = client.get("/v1/runs?page=2")
        assert response.status_code == 200

        meta = response.json()["meta"]
        assert meta["page"] == 2

    def test_list_runs_pagination_custom_per_page(self, client):
        """Test custom per_page parameter."""
        response = client.get("/v1/runs?per_page=10")
        assert response.status_code == 200

        meta = response.json()["meta"]
        assert meta["per_page"] == 10

    def test_list_runs_pagination_max_per_page(self, client):
        """Test that per_page is capped at 100."""
        response = client.get("/v1/runs?per_page=200")
        # Should reject values over 100
        assert response.status_code == 400  # Custom handler returns 400

    def test_list_runs_pagination_min_page(self, client):
        """Test that page must be at least 1."""
        response = client.get("/v1/runs?page=0")
        assert response.status_code == 400  # Custom handler returns 400

    def test_list_runs_combined_filters(self, client):
        """Test combining multiple filters."""
        response = client.get("/v1/runs?strategy_id=momentum_v1&run_type=BACKTEST&status=COMPLETED")
        assert response.status_code == 200

        runs = response.json()["data"]
        for run in runs:
            assert run["strategy_id"] == "momentum_v1"
            assert run["run_type"] == "BACKTEST"
            assert run["status"] == "COMPLETED"


class TestGetRun:
    """Tests for GET /v1/runs/{run_id} endpoint."""

    def test_get_run_returns_200(self, client):
        """Test getting a known run returns 200."""
        response = client.get("/v1/runs/run-001")
        assert response.status_code == 200

    def test_get_run_returns_data(self, client):
        """Test that run detail has data wrapper."""
        response = client.get("/v1/runs/run-001")
        data = response.json()

        assert "data" in data
        assert isinstance(data["data"], dict)

    def test_get_run_detail_fields(self, client):
        """Test that run detail has all required fields."""
        response = client.get("/v1/runs/run-001")
        run = response.json()["data"]

        required_fields = [
            "run_id",
            "strategy_id",
            "metrics",
            "equity_curve",
            "trades",
        ]

        for field in required_fields:
            assert field in run, f"Missing field: {field}"

    def test_get_run_metrics_fields(self, client):
        """Test that run metrics has expected fields per api-contracts.md."""
        response = client.get("/v1/runs/run-001")
        metrics = response.json()["data"]["metrics"]

        required_metrics = [
            "total_return",
            "max_drawdown",
            "win_rate",
            "total_trades",
        ]

        for field in required_metrics:
            assert field in metrics, f"Missing metrics field: {field}"

    def test_get_run_optional_metrics(self, client):
        """Test that optional metrics fields are present if applicable."""
        response = client.get("/v1/runs/run-001")
        metrics = response.json()["data"]["metrics"]

        # These are optional per contract but may be present
        optional_fields = [
            "cagr",
            "sharpe_ratio",
            "sortino_ratio",
            "profit_factor",
            "avg_trade_duration_hours",
        ]

        # Just verify structure, not values
        for field in optional_fields:
            if field in metrics:
                # Value can be None or a string
                assert metrics[field] is None or isinstance(metrics[field], str)

    def test_get_run_equity_curve_format(self, client):
        """Test that equity curve has correct format."""
        response = client.get("/v1/runs/run-001")
        equity_curve = response.json()["data"]["equity_curve"]

        assert isinstance(equity_curve, list)

        for point in equity_curve:
            assert "date" in point
            assert "value" in point

    def test_get_run_trades_format(self, client):
        """Test that trades have correct format."""
        response = client.get("/v1/runs/run-001")
        trades = response.json()["data"]["trades"]

        assert isinstance(trades, list)

        if len(trades) > 0:
            trade = trades[0]
            required_trade_fields = [
                "trade_id",
                "symbol",
                "entry_time",
                "exit_time",
                "entry_price",
                "exit_price",
                "quantity",
                "pnl",
                "return_pct",
            ]

            for field in required_trade_fields:
                assert field in trade, f"Missing trade field: {field}"

    def test_get_run_not_found(self, client):
        """Test that unknown run returns 404."""
        response = client.get("/v1/runs/nonexistent-run")
        assert response.status_code == 404

    def test_get_run_404_has_detail(self, client):
        """Test that 404 response has detail message."""
        response = client.get("/v1/runs/nonexistent-run")
        data = response.json()

        assert "detail" in data

    def test_get_run_id_matches_request(self, client):
        """Test that returned run_id matches requested ID."""
        run_id = "run-001"
        response = client.get(f"/v1/runs/{run_id}")
        data = response.json()["data"]

        assert data["run_id"] == run_id


class TestCreateRun:
    """Tests for POST /v1/runs endpoint."""

    def test_create_run_returns_202(self, client):
        """Test that creating a run returns 202 Accepted."""
        response = client.post(
            "/v1/runs",
            json={
                "strategy_id": "momentum_v1",
                "start_date": "2024-01-01",
                "end_date": "2025-12-31",
                "initial_capital": "100000.00",
            },
        )
        assert response.status_code == 202

    def test_create_run_has_message(self, client):
        """Test that create response has message."""
        response = client.post(
            "/v1/runs",
            json={
                "strategy_id": "momentum_v1",
                "start_date": "2024-01-01",
                "end_date": "2025-12-31",
                "initial_capital": "100000.00",
            },
        )
        data = response.json()

        assert "message" in data
        # Per api-contracts.md, message is "Backtest started"
        assert "backtest" in data["message"].lower() or "started" in data["message"].lower()

    def test_create_run_has_data(self, client):
        """Test that create response includes run data."""
        response = client.post(
            "/v1/runs",
            json={
                "strategy_id": "momentum_v1",
                "start_date": "2024-01-01",
                "end_date": "2025-12-31",
                "initial_capital": "100000.00",
            },
        )
        data = response.json()

        assert "data" in data
        assert "run_id" in data["data"]
        assert "status" in data["data"]

    def test_create_run_status_is_running(self, client):
        """Test that new run has RUNNING status."""
        response = client.post(
            "/v1/runs",
            json={
                "strategy_id": "momentum_v1",
                "start_date": "2024-01-01",
                "end_date": "2025-12-31",
                "initial_capital": "100000.00",
            },
        )
        data = response.json()["data"]

        assert data["status"] == "RUNNING"

    def test_create_run_has_estimated_completion(self, client):
        """Test that response includes estimated completion time."""
        response = client.post(
            "/v1/runs",
            json={
                "strategy_id": "momentum_v1",
                "start_date": "2024-01-01",
                "end_date": "2025-12-31",
                "initial_capital": "100000.00",
            },
        )
        data = response.json()["data"]

        assert "estimated_completion" in data

    def test_create_run_generates_unique_id(self, client):
        """Test that each created run gets a unique ID."""
        response1 = client.post(
            "/v1/runs",
            json={
                "strategy_id": "momentum_v1",
                "start_date": "2024-01-01",
                "end_date": "2025-12-31",
                "initial_capital": "100000.00",
            },
        )

        response2 = client.post(
            "/v1/runs",
            json={
                "strategy_id": "momentum_v1",
                "start_date": "2024-01-01",
                "end_date": "2025-12-31",
                "initial_capital": "100000.00",
            },
        )

        run_id_1 = response1.json()["data"]["run_id"]
        run_id_2 = response2.json()["data"]["run_id"]

        assert run_id_1 != run_id_2

    def test_create_run_missing_strategy_id(self, client):
        """Test that missing strategy_id is rejected."""
        response = client.post(
            "/v1/runs",
            json={
                "start_date": "2024-01-01",
                "end_date": "2025-12-31",
                "initial_capital": "100000.00",
            },
        )
        assert response.status_code == 400  # Custom handler returns 400

    def test_create_run_missing_start_date(self, client):
        """Test that missing start_date is rejected."""
        response = client.post(
            "/v1/runs",
            json={
                "strategy_id": "momentum_v1",
                "end_date": "2025-12-31",
                "initial_capital": "100000.00",
            },
        )
        assert response.status_code == 400  # Custom handler returns 400

    def test_create_run_missing_end_date(self, client):
        """Test that missing end_date is rejected."""
        response = client.post(
            "/v1/runs",
            json={
                "strategy_id": "momentum_v1",
                "start_date": "2024-01-01",
                "initial_capital": "100000.00",
            },
        )
        assert response.status_code == 400  # Custom handler returns 400

    def test_create_run_missing_initial_capital(self, client):
        """Test that missing initial_capital is rejected."""
        response = client.post(
            "/v1/runs",
            json={
                "strategy_id": "momentum_v1",
                "start_date": "2024-01-01",
                "end_date": "2025-12-31",
            },
        )
        assert response.status_code == 400  # Custom handler returns 400


class TestRunFactoryUsage:
    """Tests demonstrating factory function usage."""

    def test_factory_creates_valid_run(self):
        """Test that get_mock_backtest_run creates valid data."""
        run = get_mock_backtest_run()

        assert "run_id" in run
        assert "strategy_id" in run
        assert "status" in run
        assert "metrics" in run

    def test_factory_accepts_overrides(self):
        """Test that factory accepts custom values."""
        from packages.common.api_schemas import RunStatus

        run = get_mock_backtest_run(
            {
                "strategy_id": "custom_strategy",
                "status": RunStatus.FAILED,
            }
        )

        assert run["strategy_id"] == "custom_strategy"
        assert run["status"] == RunStatus.FAILED

    def test_factory_generates_unique_ids(self):
        """Test that factory generates unique run IDs."""
        run1 = get_mock_backtest_run()
        run2 = get_mock_backtest_run()

        assert run1["run_id"] != run2["run_id"]
