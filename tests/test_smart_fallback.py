"""
Verifies the per-resource smart fallback: a bucket present in the
DLP map uses ONLY those findings (local sampling skipped entirely);
a bucket absent from the map still gets local sampling.
"""

import boto3
from moto import mock_aws

from app.connectors.aws.client import AWSClientFactory
from app.connectors.aws.s3_connector import discover_s3_buckets


@mock_aws
def test_bucket_with_macie_findings_skips_local_sampling():
    s3 = boto3.client("s3", region_name="eu-west-3")
    s3.create_bucket(Bucket="macie-covered-bucket", CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
    # Deliberately put a detectable email in the object -- if local
    # sampling ran, we'd see it as a SECOND, duplicate finding.
    s3.put_object(Bucket="macie-covered-bucket", Key="sample.csv", Body=b"email: test@acme.com")

    macie_map = {
        "macie-covered-bucket": [
            {"category": "national_id", "field_or_location": "sample.csv", "confidence": 0.97, "detector": "aws_macie"}
        ]
    }

    factory = AWSClientFactory(region="eu-west-3")
    resources = discover_s3_buckets(factory, dlp_findings_by_resource=macie_map)

    assert len(resources) == 1
    findings = resources[0].content_findings
    # Exactly the ONE Macie-provided finding -- proves local regex
    # sampling did NOT also run for this bucket.
    assert len(findings) == 1
    assert findings[0]["detector"] == "aws_macie"


@mock_aws
def test_bucket_without_macie_findings_falls_back_to_local_sampling():
    s3 = boto3.client("s3", region_name="eu-west-3")
    s3.create_bucket(Bucket="uncovered-bucket", CreateBucketConfiguration={"LocationConstraint": "eu-west-3"})
    s3.put_object(Bucket="uncovered-bucket", Key="sample.csv", Body=b"email: test@acme.com")

    factory = AWSClientFactory(region="eu-west-3")
    # No DLP map at all -- default {} -- every bucket must fall back.
    resources = discover_s3_buckets(factory)

    assert len(resources) == 1
    findings = resources[0].content_findings
    assert any(f["detector"] == "regex" for f in findings)
    