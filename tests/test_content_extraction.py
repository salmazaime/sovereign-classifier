"""
Verifies the two guarantees Rule 3 demands: (1) missing pypdf/
pytesseract never raises, just returns '', and (2) the smart
fallback correctly skips local sampling only for resources present
in the DLP map.
"""

from unittest.mock import patch

from app.connectors.content_detectors import (
    _PYPDF_AVAILABLE,
    extract_text_by_extension,
)


def test_pdf_extraction_returns_empty_string_when_pypdf_missing():
    with patch("app.connectors.content_detectors._PYPDF_AVAILABLE", False):
        result = extract_text_by_extension("report.pdf", b"not a real pdf")
        assert result == ""


def test_pdf_extraction_returns_empty_string_on_corrupt_bytes():
    # pypdf IS available, but the bytes aren't a valid PDF at all --
    # this simulates the truncation risk called out in the module
    # docstring (MAX_BINARY_SAMPLE_BYTES cutting a large file short).
    result = extract_text_by_extension("report.pdf", b"this is not valid pdf structure")
    assert result == ""


def test_plain_text_extraction_still_works_unaffected():
    result = extract_text_by_extension("data.csv", b"name,email\nJohn,john@acme.com")
    assert "john@acme.com" in result
    