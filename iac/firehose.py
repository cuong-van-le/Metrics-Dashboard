import logging
import time
from dataclasses import dataclass
from time import sleep

from botocore.exceptions import ClientError

from iac.base import Resource, ResourceResult
from iac.configs import FirehoseClient, FirehoseConfig
from iac.constants import ErrorCodes
from iac.retry import retry_on_iam_propagation
from iac.validation import ResourceValidator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FirehoseResult(ResourceResult):
    stream_name: str
    status: str


class FireHose(Resource[FirehoseResult]):
    def __init__(self, config: FirehoseConfig, firehose_client: FirehoseClient):
        super().__init__(
            config={
                "DELIVERY_STREAM_NAME": config.delivery_stream_name,
                "ROLE_ARN": config.role_arn,
                "BUCKET_ARN": config.bucket_arn,
                "LAMBDA_ARN": config.lambda_arn,
                "PREFIX": config.prefix,
                "BUFFERING_SIZE": config.buffering_size,
                "BUFFERING_TIME": config.buffering_time,
            },
            client=firehose_client,
        )
        self.firehose_config = config

    def _get_resource_name(self) -> str:
        return self.firehose_config.delivery_stream_name

    def _exists(self, stream_name: str) -> bool:
        try:
            self.client.describe_delivery_stream(DeliveryStreamName=stream_name)
            return True
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == ErrorCodes.RESOURCE_NOT_FOUND:
                return False
            raise

    def _handle_existing(self, stream_name: str) -> FirehoseResult:
        resp = self.client.describe_delivery_stream(DeliveryStreamName=stream_name)
        status = resp["DeliveryStreamDescription"]["DeliveryStreamStatus"]
        logger.info(f"Delivery stream exists: {stream_name} (status: {status})")

        if status == "ACTIVE":
            return FirehoseResult(stream_name=stream_name, status=status)

        self._wait_until_active(timeout_s=300)
        return FirehoseResult(stream_name=stream_name, status="ACTIVE")

    def _create(self, stream_name: str) -> FirehoseResult:
        if not ResourceValidator.validate_firehose_stream_name(stream_name):
            raise ValueError(
                f"Invalid Firehose stream name: {stream_name}. "
                "Stream names must be 1-64 characters and contain only letters, "
                "numbers, hyphens, and underscores."
            )

        logger.info(f"Delivery stream '{stream_name}' not found. Creating...")
        try:
            self._create_stream_with_retry(stream_name)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == ErrorCodes.RESOURCE_IN_USE:
                logger.info("Stream already exists (race condition).")
            else:
                raise
        self._wait_until_active(timeout_s=getattr(self, "_timeout_s", 300))
        return FirehoseResult(stream_name=stream_name, status="ACTIVE")

    @retry_on_iam_propagation()
    def _create_stream_with_retry(self, stream_name: str) -> None:
        if self.firehose_config.enable_dynamic_partitioning:
            s3_prefix = (
                "analytics/"
                "year=!{partitionKeyFromLambda:year}/"
                "month=!{partitionKeyFromLambda:month}/"
                "day=!{partitionKeyFromLambda:day}/"
                "hour=!{partitionKeyFromLambda:hour}/"
            )
        else:
            s3_prefix = self.firehose_config.prefix

        error_prefix = self.firehose_config.error_output_prefix
        if error_prefix is None and self.firehose_config.enable_dynamic_partitioning:
            error_prefix = (
                "errors/!{firehose:error-output-type}/"
                "year=!{timestamp:yyyy}/"
                "month=!{timestamp:MM}/"
                "day=!{timestamp:dd}/"
                "hour=!{timestamp:HH}/"
            )

        s3_config = {
            "RoleARN": self.firehose_config.role_arn,
            "BucketARN": self.firehose_config.bucket_arn,
            "Prefix": s3_prefix,
            "BufferingHints": {
                "SizeInMBs": self.firehose_config.buffering_size,
                "IntervalInSeconds": self.firehose_config.buffering_time,
            },
            "CompressionFormat": (
                "UNCOMPRESSED" if self.firehose_config.enable_parquet else "GZIP"
            ),
            "EncryptionConfiguration": {"NoEncryptionConfig": "NoEncryption"},
            "ProcessingConfiguration": {
                "Enabled": True,
                "Processors": [
                    {
                        "Type": "Lambda",
                        "Parameters": [
                            {
                                "ParameterName": "LambdaArn",
                                "ParameterValue": self.firehose_config.lambda_arn,
                            },
                            {
                                "ParameterName": "NumberOfRetries",
                                "ParameterValue": "3",
                            },
                            {
                                "ParameterName": "BufferSizeInMBs",
                                "ParameterValue": "3",
                            },
                            {
                                "ParameterName": "BufferIntervalInSeconds",
                                "ParameterValue": "120",
                            },
                        ],
                    }
                ],
            },
            "CloudWatchLoggingOptions": {
                "Enabled": True,
                "LogGroupName": f"/aws/kinesis_firehose/{stream_name}",
                "LogStreamName": "S3Delivery",
            },
        }

        if error_prefix:
            s3_config["ErrorOutputPrefix"] = error_prefix

        if self.firehose_config.enable_dynamic_partitioning:
            s3_config["DynamicPartitioningConfiguration"] = {
                "Enabled": True,
                "RetryOptions": {
                    "DurationInSeconds": 300,
                },
            }
            s3_config["CustomTimeZone"] = self.firehose_config.timezone

        if self.firehose_config.enable_parquet:
            if (
                not self.firehose_config.glue_database_name
                or not self.firehose_config.glue_table_name
            ):
                logger.warning(
                    "Parquet output enabled but Glue database/table not specified. "
                    "Parquet conversion will fail without a Glue schema."
                )
            else:
                s3_config["DataFormatConversionConfiguration"] = {
                    "Enabled": True,
                    "InputFormatConfiguration": {
                        "Deserializer": {"OpenXJsonSerDe": {}}
                    },
                    "OutputFormatConfiguration": {
                        "Serializer": {"ParquetSerDe": {"Compression": "SNAPPY"}}
                    },
                    "SchemaConfiguration": {
                        "DatabaseName": self.firehose_config.glue_database_name,
                        "TableName": self.firehose_config.glue_table_name,
                        "RoleARN": self.firehose_config.role_arn,
                    },
                }

        self.client.create_delivery_stream(
            DeliveryStreamName=stream_name,
            DeliveryStreamType="DirectPut",
            ExtendedS3DestinationConfiguration=s3_config,
        )
        logger.info("Delivery stream creation started...")

    def get_stream_status(self) -> str:
        resp = self.client.describe_delivery_stream(
            DeliveryStreamName=self.firehose_config.delivery_stream_name
        )
        return resp["DeliveryStreamDescription"]["DeliveryStreamStatus"]

    def _wait_until_active(self, timeout_s: int) -> None:
        start = time.time()
        while True:
            status = self.get_stream_status()
            if status == "ACTIVE":
                logger.info("Stream is ACTIVE.")
                return
            if status == "CREATING_FAILED":
                raise RuntimeError("Stream is CREATING_FAILED.")
            if time.time() - start > timeout_s:
                raise TimeoutError(
                    f"Timed out waiting for ACTIVE. Last status={status}"
                )
            sleep(5)

    def ensure_stream(self, timeout_s: int = 300) -> None:
        self._timeout_s = timeout_s
        try:
            result = self.ensure()
            if result.status != "ACTIVE":
                self._wait_until_active(timeout_s=timeout_s)
        finally:
            if hasattr(self, "_timeout_s"):
                delattr(self, "_timeout_s")
