from app.observability.context import get_company_id, get_request_id, set_company_id, set_request_id


def test_defaults_are_placeholder_dash():
    assert get_request_id() == "-"
    assert get_company_id() == "-"


def test_set_and_get_roundtrip():
    set_request_id("abc-123")
    set_company_id("company-xyz")
    assert get_request_id() == "abc-123"
    assert get_company_id() == "company-xyz"
    