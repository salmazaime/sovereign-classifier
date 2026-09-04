"""
Focused on the one thing that actually matters to get right here:
resolve_authorization_request's rowcount-based race detection.
"""

from unittest.mock import MagicMock
from uuid import uuid4

from app.db.repository import PostgresRepository


def _mock_pool_with_rowcount(rowcount: int):
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = rowcount

    mock_pool.connection.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    return mock_pool, mock_cursor


def test_resolve_returns_true_when_row_was_updated():
    mock_pool, _ = _mock_pool_with_rowcount(rowcount=1)
    repo = PostgresRepository(mock_pool)

    result = repo.resolve_authorization_request(
        authorization_request_id=uuid4(),
        reviewer_user_id=uuid4(),
        approve=True,
    )

    assert result is True


def test_resolve_returns_false_when_already_resolved_or_expired():
    """
    rowcount == 0 simulates the exact race scenario: the WHERE clause
    (status = 'PENDING' AND expires_at > now()) matched nothing
    because another request got there first, or time ran out.
    """
    mock_pool, _ = _mock_pool_with_rowcount(rowcount=0)
    repo = PostgresRepository(mock_pool)

    result = repo.resolve_authorization_request(
        authorization_request_id=uuid4(),
        reviewer_user_id=uuid4(),
        approve=True,
    )

    assert result is False
    