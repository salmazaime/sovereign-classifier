# tests/test_log_formatter.py
import json
import logging

from app.observability.context import set_request_id
from app.observability.log_formatter import JSONLogFormatter


def test_json_formatter_includes_request_id():
    set_request_id("test-request-id")
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello world", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["message"] == "hello world"
    assert parsed["request_id"] == "test-request-id"
    assert parsed["level"] == "INFO"


def test_json_formatter_output_is_valid_json_even_with_special_characters():
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg='message with "quotes" and \n newlines', args=(), exc_info=None,
    )
    output = formatter.format(record)
    json.loads(output)  # raises if not valid JSON -- the actual assertion
    