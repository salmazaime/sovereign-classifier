"""
Unit tests for GraphRepository, using a mocked driver so these run
in CI without needing a live Neo4j instance. What we're testing is
NOT "does Neo4j work" (that's the database's job) — we're testing
that our code calls the driver correctly.
"""

from unittest.mock import MagicMock

from app.graph.repository import GraphRepository


def test_upsert_asset_calls_execute_write() -> None:
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    repo = GraphRepository(mock_driver)
    repo.upsert_asset(
        entity_id="abc-123", name="test.csv", resource_type="s3_object"
    )

    mock_session.execute_write.assert_called_once()
    args = mock_session.execute_write.call_args[0]
    assert args[1] == "abc-123"
    assert args[2] == "test.csv"
    assert args[3] == "s3_object"


def test_link_depends_on_calls_execute_write() -> None:
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    repo = GraphRepository(mock_driver)
    repo.link_depends_on("from-id", "to-id", confidence=0.8)

    mock_session.execute_write.assert_called_once()
    args = mock_session.execute_write.call_args[0]
    assert args[1] == "from-id"
    assert args[2] == "to-id"
    assert args[3] == 0.8
    