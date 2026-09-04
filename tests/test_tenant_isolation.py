# tests/test_tenant_isolation.py
"""
Verifies the cross-tenant fix itself: a valid API key for company A
must be refused when acting on company B's data. Uses FastAPI's
TestClient with dependency_overrides -- the standard way to swap in
fake auth for route-level tests without real tokens or a real DB.
"""

from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_postgres_repo
from app.auth.dependencies import require_api_key
from app.main import app

client = TestClient(app)

COMPANY_A = str(uuid4())
COMPANY_B = str(uuid4())


def test_transfer_request_rejects_entity_from_different_company():
    mock_repo = MagicMock()
    mock_entity = MagicMock()
    mock_entity.company_id = COMPANY_B  # entity belongs to B
    mock_repo.get_entity.return_value = mock_entity

    app.dependency_overrides[require_api_key] = lambda: COMPANY_A  # caller authenticated as A
    app.dependency_overrides[get_postgres_repo] = lambda: mock_repo

    try:
        response = client.post("/transfer-request", json={
            "entity_id": str(uuid4()), "operation": "test",
            "destination_cloud": "aws", "destination_service": "s3",
            "destination_region": "eu-west-3", "destination_country": "France",
        })
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
        