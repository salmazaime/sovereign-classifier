# tests/test_interceptor_cli.py
"""
Verifies run_gate()'s ROUTING logic with a fully fake api_client --
no real HTTP, no real filesystem. This is the equivalent testing
philosophy to every repository test since Step 5: verify OUR logic
calls the dependency correctly and reacts correctly to its
responses, don't re-test the dependency itself.
"""

from unittest.mock import MagicMock

from app.connectors.base import DiscoveredResource
from app.connectors.region_lookup import RegionCountryTable
from app.interceptor.api_client import SovereigntyAPIError
from app.interceptor.cli import run_gate

REGION_TABLE = RegionCountryTable(
    aws={"eu-west-3": "France"},
    azure={"francecentral": "France"},
)


def _aws_resource(name="test-bucket", region="eu-west-3") -> DiscoveredResource:
    return DiscoveredResource(
        cloud_provider="aws", account_id="unknown", region=region,
        resource_id=f"terraform:aws_s3_bucket.{name}", resource_type="s3_bucket",
        name=name, granularity="dataset", is_publicly_accessible=True,
    )


def test_allowed_transfer_returns_exit_code_zero():
    resource = _aws_resource()
    mock_client = MagicMock()
    mock_client.ingest.return_value = "entity-123"
    mock_client.request_transfer.return_value = {
        "outcome": "ALLOW", "reason_code": "destination_on_adequacy_list", "policy_reference": "art_43_loi_09-08",
    }

    exit_code = run_gate([resource], mock_client, "Acme Corp", "banking", REGION_TABLE, "tester", "test-app")

    assert exit_code == 0


def test_deny_transfer_returns_exit_code_one():
    resource = _aws_resource()
    mock_client = MagicMock()
    mock_client.ingest.return_value = "entity-123"
    mock_client.request_transfer.return_value = {
        "outcome": "DENY", "reason_code": "no_sovereign_region_available", "policy_reference": "art_11_loi_05-20",
    }

    exit_code = run_gate([resource], mock_client, "Acme Corp", "banking", REGION_TABLE, "tester", "test-app")

    assert exit_code == 1


def test_review_transfer_also_blocks_per_this_steps_stricter_gate():
    """
    Unlike the earlier (unimplemented) Step 14 design, which polled
    on REVIEW, this version's explicit requirement is: DENY or
    REVIEW both fail the build immediately. This test locks in that
    deliberate difference.
    """
    resource = _aws_resource()
    mock_client = MagicMock()
    mock_client.ingest.return_value = "entity-123"
    mock_client.request_transfer.return_value = {
        "outcome": "REVIEW", "reason_code": "destination_not_on_adequacy_list", "policy_reference": "art_43_loi_09-08",
    }

    exit_code = run_gate([resource], mock_client, "Acme Corp", "banking", REGION_TABLE, "tester", "test-app")

    assert exit_code == 1


def test_ingestion_api_error_fails_closed():
    resource = _aws_resource()
    mock_client = MagicMock()
    mock_client.ingest.side_effect = SovereigntyAPIError("connection refused")

    exit_code = run_gate([resource], mock_client, "Acme Corp", "banking", REGION_TABLE, "tester", "test-app")

    assert exit_code == 1
    mock_client.request_transfer.assert_not_called()  # must not proceed to decision if ingestion never confirmed


def test_unresolvable_region_uses_unknown_and_still_gets_evaluated():
    resource = _aws_resource(region="ap-southeast-9")  # not in REGION_TABLE
    mock_client = MagicMock()
    mock_client.ingest.return_value = "entity-123"
    mock_client.request_transfer.return_value = {
        "outcome": "REVIEW", "reason_code": "destination_not_on_adequacy_list", "policy_reference": "art_43_loi_09-08",
    }

    exit_code = run_gate([resource], mock_client, "Acme Corp", "banking", REGION_TABLE, "tester", "test-app")

    assert exit_code == 1
    call_kwargs = mock_client.request_transfer.call_args[0][0]
    assert call_kwargs["destination_country"] == "UNKNOWN"


def test_non_cloud_resource_is_ingested_but_not_evaluated():
    """
    The synthetic repo-content bundle (cloud_provider='github') must
    be ingested for audit visibility but never sent to
    /transfer-request -- verifies the scope boundary from
    repo_scanner.py's docstring is actually enforced in code.
    """
    repo_resource = DiscoveredResource(
        cloud_provider="github", account_id="acme/repo", region="unknown",
        resource_id="git:acme/repo", resource_type="git_repository_content",
        name="acme/repo", granularity="dataset", is_publicly_accessible=False,
        content_findings=[{"category": "national_id", "field_or_location": "data.csv", "confidence": 0.6, "detector": "regex"}],
    )
    mock_client = MagicMock()
    mock_client.ingest.return_value = "entity-456"

    exit_code = run_gate([repo_resource], mock_client, "Acme Corp", "banking", REGION_TABLE, "tester", "test-app")

    assert exit_code == 0
    mock_client.ingest.assert_called_once()
    mock_client.request_transfer.assert_not_called()
    