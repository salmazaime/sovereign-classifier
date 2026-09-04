# tests/test_terraform_parser.py
from pathlib import Path

from app.interceptor.iac.terraform_parser import parse_terraform_file


def test_s3_bucket_with_public_access_block_and_encryption(tmp_path: Path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
resource "aws_s3_bucket" "data" {
  bucket = "acme-payroll-exports"
  region = "eu-west-3"
  tags = {
    owner       = "hr-team"
    environment = "prod"
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}
""")
    resources = parse_terraform_file(tf_file)
    assert len(resources) == 1
    bucket = resources[0]
    assert bucket.name == "acme-payroll-exports"
    assert bucket.is_publicly_accessible is False  # all four flags true -> blocked
    assert bucket.encryption_enabled is True
    assert bucket.encryption_key_type == "AWS_KMS"
    assert bucket.tags["owner"] == "hr-team"


def test_s3_bucket_with_no_correlated_resources_fails_cautious(tmp_path: Path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
resource "aws_s3_bucket" "orphan" {
  bucket = "some-bucket"
  region = "eu-west-1"
}
""")
    resources = parse_terraform_file(tf_file)
    assert len(resources) == 1
    assert resources[0].is_publicly_accessible is True   # no correlated block -> assume public
    assert resources[0].encryption_enabled is False       # no correlated config -> assume unencrypted


def test_azurerm_storage_account_always_encrypted(tmp_path: Path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
resource "azurerm_storage_account" "acct" {
  name     = "acmestorageacct"
  location = "francecentral"
}
""")
    resources = parse_terraform_file(tf_file)
    assert len(resources) == 1
    assert resources[0].encryption_enabled is True  # platform default, not fail-cautious
    assert resources[0].encryption_key_type == "PLATFORM_MANAGED"


def test_malformed_hcl_returns_empty_list_not_exception(tmp_path: Path):
    tf_file = tmp_path / "broken.tf"
    tf_file.write_text("resource aws_s3_bucket { this is not valid HCL @@@")
    resources = parse_terraform_file(tf_file)
    assert resources == []


def test_irrelevant_resource_types_are_ignored(tmp_path: Path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
resource "aws_iam_role" "not_relevant" {
  name = "some-role"
}
""")
    resources = parse_terraform_file(tf_file)
    assert resources == []
    