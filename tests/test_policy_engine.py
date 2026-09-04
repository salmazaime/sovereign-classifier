"""
Unit tests for the pure decision engine. No mocks needed at all —
this is the payoff of keeping decide_transfer() free of I/O: we
construct plain objects and assert on plain outputs.
"""

from app.policy.engine import DecisionInput, DecisionOutcome, decide_transfer
from app.policy.lookup_tables import AdequacyTable, QualifiedProviderTable
from app.schemas import ResidencyLock

ADEQUACY = AdequacyTable(adequate_countries=frozenset({"France"}))
QUALIFIED = QualifiedProviderTable(qualified_pairs=frozenset({("atlas_cloud", "morocco-central")}))


def test_non_locked_asset_to_adequate_country_is_allowed():
    result = decide_transfer(
        DecisionInput(ResidencyLock.NONE, False, "azure", "francecentral", "France"),
        ADEQUACY, QUALIFIED,
    )
    assert result.outcome == DecisionOutcome.ALLOW
    assert result.reason_code == "destination_on_adequacy_list"


def test_non_locked_asset_to_non_adequate_country_is_review():
    result = decide_transfer(
        DecisionInput(ResidencyLock.NONE, False, "aws", "us-east-1", "United States"),
        ADEQUACY, QUALIFIED,
    )
    assert result.outcome == DecisionOutcome.REVIEW


def test_residency_locked_asset_to_aws_is_denied_regardless_of_country():
    """
    The critical test: even a 'good' country (France, on the
    adequacy list) must NOT override a residency lock. This proves
    Gate 1 is a hard override, not a weighted signal, exactly as
    designed.
    """
    result = decide_transfer(
        DecisionInput(
            ResidencyLock.SENSITIVE_HOSTING_REQUIRED, False, "aws", "eu-west-3", "France"
        ),
        ADEQUACY, QUALIFIED,
    )
    assert result.outcome == DecisionOutcome.DENY
    assert result.reason_code == "no_sovereign_region_available"
    assert result.policy_reference == "art_11_loi_05-20"


def test_oiv_company_requiring_qualified_provider_denied_on_aws():
    result = decide_transfer(
        DecisionInput(ResidencyLock.NONE, True, "aws", "eu-west-3", "France"),
        ADEQUACY, QUALIFIED,
    )
    assert result.outcome == DecisionOutcome.DENY
    assert result.policy_reference == "decree_2.24.921"


def test_residency_locked_asset_to_qualified_provider_is_allowed():
    result = decide_transfer(
        DecisionInput(
            ResidencyLock.OIV_HOSTING_REQUIRED, False, "atlas_cloud", "morocco-central", "Morocco"
        ),
        ADEQUACY, QUALIFIED,
    )
    assert result.outcome == DecisionOutcome.ALLOW
    assert result.reason_code == "qualified_sovereign_provider"
    