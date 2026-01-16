from __future__ import annotations

import logging
from dataclasses import dataclass
from botocore.exceptions import ClientError

from iac.base import Resource, ResourceResult
from iac.configs import BucketConfig, S3Client
from iac.constants import AWSConstants, ErrorCodes
from iac.validation import ResourceValidator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BucketResult(ResourceResult):
    bucket_arn: str


class Bucket(Resource[BucketResult]):
    def __init__(self, config: BucketConfig, s3_client: S3Client):
        super().__init__(
            config={
                "BUCKET_NAME": config.bucket_name,
                "REGION": config.region,
            },
            client=s3_client,
        )
        self.bucket_config = config

    def _get_resource_name(self) -> str:
        return self.bucket_config.bucket_name

    def _exists(self, bucket_name: str) -> bool:
        try:
            self.client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError:
            return False

    def _handle_existing(self, bucket_name: str) -> BucketResult:
        arn = f"arn:aws:s3:::{bucket_name}"
        logger.info(f"S3 bucket exists: {bucket_name}")
        return BucketResult(bucket_arn=arn)

    def _create(self, bucket_name: str) -> BucketResult:
        """Create the bucket."""
        if not ResourceValidator.validate_bucket_name(bucket_name):
            raise ValueError(
                f"Invalid bucket name: {bucket_name}. "
                "Bucket names must be 3-63 characters, contain only lowercase letters, "
                "numbers, dots, and hyphens, and cannot start/end with dot or hyphen."
            )

        region = self.bucket_config.region or self.client.meta.region_name
        if not region:
            raise RuntimeError(
                "S3 region is missing (REGION not provided and client has no region)."
            )

        params = {"Bucket": bucket_name}

        if region != AWSConstants.US_EAST_1:
            params["CreateBucketConfiguration"] = {"LocationConstraint": region}

        logger.debug(f"Creating bucket with params: {params}")

        try:
            self.client.create_bucket(**params)
            logger.info(f"S3 bucket created: {bucket_name}")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in (
                ErrorCodes.BUCKET_ALREADY_OWNED,
                ErrorCodes.BUCKET_ALREADY_EXISTS,
            ):
                logger.info(f"S3 bucket already exists/owned: {bucket_name}")
            else:
                raise

        self._block_public_access(bucket_name)

        arn = f"arn:aws:s3:::{bucket_name}"
        return BucketResult(bucket_arn=arn)

    def _block_public_access(self, bucket_name: str) -> None:
        try:
            self.client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                },
            )
            logger.info("S3 public access blocked.")
        except ClientError as e:
            logger.warning(f"Could not set public access block: {e}")
