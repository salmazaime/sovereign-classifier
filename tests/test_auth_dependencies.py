# tests/test_auth_dependencies.py
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.auth.dependencies import AuthenticatedUser, require_role


def test_require_role_allows_matching_role():
    checker = require_role("admin", "compliance_reviewer")
    user = AuthenticatedUser(user_id="u1", company_id="c1", roles=["compliance_reviewer"])
    result = checker(user=user)
    assert result is user


def test_require_role_rejects_missing_role():
    checker = require_role("admin")
    user = AuthenticatedUser(user_id="u1", company_id="c1", roles=["viewer"])
    with pytest.raises(HTTPException) as exc_info:
        checker(user=user)
    assert exc_info.value.status_code == 403
    