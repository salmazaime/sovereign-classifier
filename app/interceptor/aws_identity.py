"""
Resolves the AWS account ID the CURRENT PIPELINE RUN is authenticated
as, via a single STS call -- separate from Terraform parsing (which
stays credential-free and testable, per Step 14's original design).

This is a real, meaningful signal: if GitHub Actions has AWS
credentials configured (via aws-actions/configure-aws-credentials or
equivalent, typically needed for the actual `terraform apply` step
that runs after this gate), we can attribute declared infrastructure
to the account this specific pipeline run will actually deploy into.

Never raises. If no credentials are configured (a very normal case --
many repos push IaC changes reviewed by humans before a separate,
credentialed deploy step), this returns None and the caller falls
back to "unknown", exactly as before.
"""

import logging

logger = logging.getLogger(__name__)


def resolve_current_aws_account_id() -> str | None:
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        logger.info("boto3 not installed -- cannot resolve AWS account id.")
        return None

    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        account_id = identity["Account"]
        logger.info("Resolved AWS account id for this pipeline run: %s", account_id)
        return account_id
    except NoCredentialsError:
        logger.info("No AWS credentials configured in this environment -- account id will show as 'unknown'.")
        return None
    except ClientError as exc:
        logger.warning("Could not resolve AWS account id via STS: %s", exc)
        return None
        