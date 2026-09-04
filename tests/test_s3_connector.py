# tests/test_s3_connector.py
import boto3
from moto import mock_aws

from app.connectors.aws.client import AWSClientFactory
from app.connectors.aws.s3_connector import discover_s3_buckets


@mock_aws
def test_discover_s3_buckets_finds_bucket_and_flags_public_access():
    s3 = boto3.client("s3", region_name="eu-west-3")
    s3.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": "eu-west-3"},
    )
    s3.put_object(Bucket="test-bucket", Key="sample.csv", Body=b"email: test@acme.com")

    factory = AWSClientFactory(region="eu-west-3")
    resources = discover_s3_buckets(factory)

    assert len(resources) == 1
    bucket = resources[0]
    assert bucket.name == "test-bucket"
    assert bucket.resource_type == "s3_bucket"
    # No public access block configured -> our fail-cautious default is True
    assert bucket.is_publicly_accessible is True
    assert any(f["category"] == "ordinary_pii" for f in bucket.content_findings)


@mock_aws
def test_discover_s3_buckets_handles_zero_buckets_gracefully():
    factory = AWSClientFactory(region="eu-west-3")
    resources = discover_s3_buckets(factory)
    assert resources == []

    