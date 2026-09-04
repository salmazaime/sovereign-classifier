# tests/test_auth_security.py
"""
Pure tests -- no FastAPI, no database, no network. Same testability
payoff as every pure function in this project since Step 9.
"""

from datetime import timedelta

import pytest

from app.auth.security import (
    TokenValidationError, create_access_token, decode_access_token,
    hash_password, verify_password,
)

SECRET = "test-secret-key-not-for-production"


def test_password_hash_and_verify_roundtrip():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_never_raises_on_malformed_hash():
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_token_roundtrip():
    token = create_access_token("user-1", "company-1", ["admin"], SECRET)
    payload = decode_access_token(token, SECRET)
    assert payload["sub"] == "user-1"
    assert payload["company_id"] == "company-1"
    assert payload["roles"] == ["admin"]


def test_expired_token_raises_token_validation_error():
    token = create_access_token(
        "user-1", "company-1", [], SECRET, expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(TokenValidationError, match="expired"):
        decode_access_token(token, SECRET)


def test_token_signed_with_wrong_secret_is_rejected():
    token = create_access_token("user-1", "company-1", [], SECRET)
    with pytest.raises(TokenValidationError):
        decode_access_token(token, "a-completely-different-secret")
        