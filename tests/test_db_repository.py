"""
Unit tests for PostgresRepository using a mocked pool — same
philosophy as the graph repository tests: we're verifying our SQL
gets called with the right parameters, not re-testing Postgres itself.
"""

from unittest.mock import MagicMock

from app.db.repository import PostgresRepository


def _mock_pool_returning(row: dict):
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_pool.connection.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = row

    return mock_pool, mock_cursor


def test_upsert_company_returns_id_and_commits():
    fake_id = "a1b2c3d4-0000-0000-0000-000000000000"
    mock_pool, mock_cursor = _mock_pool_returning({"id": fake_id})

    repo = PostgresRepository(mock_pool)
    result = repo.upsert_company(name="Acme Corp", sector="banking")

    assert result == fake_id
    mock_cursor.execute.assert_called_once()
    sql_text, params = mock_cursor.execute.call_args[0]
    assert "ON CONFLICT (name) DO UPDATE" in sql_text
    assert params == ("Acme Corp", "banking")


def test_upsert_entity_uses_natural_key_conflict_target():
    fake_id = "e1e1e1e1-0000-0000-0000-000000000000"
    mock_pool, mock_cursor = _mock_pool_returning({"id": fake_id})

    repo = PostgresRepository(mock_pool)
    result = repo.upsert_entity(
        company_id="c1c1c1c1-0000-0000-0000-000000000000",
        entity_type="DATA_ASSET",
        name="payroll_2026_07.csv",
    )

    assert result == fake_id
    sql_text, _ = mock_cursor.execute.call_args[0]
    assert "ON CONFLICT (company_id, entity_type, name) DO UPDATE" in sql_text
    