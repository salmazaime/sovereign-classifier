from app.observability.metrics import INGESTION_TOTAL, POLICY_DECISIONS_TOTAL


def test_policy_decisions_counter_increments_per_outcome():
    before = POLICY_DECISIONS_TOTAL.labels(outcome="ALLOW")._value.get()
    POLICY_DECISIONS_TOTAL.labels(outcome="ALLOW").inc()
    after = POLICY_DECISIONS_TOTAL.labels(outcome="ALLOW")._value.get()
    assert after == before + 1


def test_ingestion_total_has_independent_label_counters():
    INGESTION_TOTAL.labels(result="success").inc()
    INGESTION_TOTAL.labels(result="failure").inc()
    success_count = INGESTION_TOTAL.labels(result="success")._value.get()
    failure_count = INGESTION_TOTAL.labels(result="failure")._value.get()
    assert success_count >= 1
    assert failure_count >= 1
    