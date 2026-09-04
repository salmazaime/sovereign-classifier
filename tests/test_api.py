"""
API-level tests using FastAPI's TestClient, with the pipeline
function itself mocked — we're testing that routes call the pipeline
correctly and map its outcomes to the right HTTP status codes, NOT
re-testing the pipeline or the databases again.
"""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(autouse=True)
def setup_app_state():
    """Automatically mock app.state repos for all API tests."""
    app.state.postgres_repo = MagicMock()
    app.state.graph_repo = MagicMock()
    yield
    
client = TestClient(app)

VALID_PAYLOAD = {
    "company_name": "Acme Corp",
    "company_sector": "banking",
    "entity_type": "DATA_ASSET",
    "entity_name": "customer_export.csv",
    "plugin_used": "aws_s3_plugin",
    "phase": "INITIAL_DISCOVERY",
    "payload": {
        "asset": {"granularity": "dataset", "resource_type": "s3_object", "content_findings": []},
        "classification": {
            "sensitivity_category": ["ordinary_pii"],
            "residency_lock": "none",
            "aggregate_sensitivity": "medium",
        },
    },
    "overall_confidence": 0.9,
}


def test_ingest_missing_fields_returns_422():
    response = client.post("/ingest", json={"company_name": "Acme Corp"})
    assert response.status_code == 422


@patch("app.api.routes.ingest_discovery_finding")
def test_ingest_success_returns_201(mock_ingest):
    fake_id = uuid4()
    mock_ingest.return_value = fake_id

    app.state.postgres_repo = MagicMock()
    app.state.graph_repo = MagicMock()

    response = client.post("/ingest", json=VALID_PAYLOAD)

    assert response.status_code == 201
    assert response.json()["entity_id"] == str(fake_id)
    assert response.json()["status"] == "ingested"


@patch("app.api.routes.ingest_discovery_finding")
def test_ingest_graph_failure_returns_207(mock_ingest):
    from app.ingestion.pipeline import GraphProjectionError

    fake_id = uuid4()
    mock_ingest.side_effect = GraphProjectionError(fake_id, Exception("neo4j down"))

    app.state.postgres_repo = MagicMock()
    app.state.graph_repo = MagicMock()

    response = client.post("/ingest", json=VALID_PAYLOAD)

    assert response.status_code == 207
    assert response.json()["detail"]["entity_id"] == str(fake_id)
    