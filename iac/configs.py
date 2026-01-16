from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from config.main import Config

if TYPE_CHECKING:
    try:
        from mypy_boto3_s3 import S3Client as _S3Client
        from mypy_boto3_lambda import LambdaClient as _LambdaClient
        from mypy_boto3_iam import IAMClient as _IAMClient
        from mypy_boto3_firehose import FirehoseClient as _FirehoseClient

        S3Client = _S3Client
        LambdaClient = _LambdaClient
        IAMClient = _IAMClient
        FirehoseClient = _FirehoseClient
    except ImportError:
        S3Client = Any
        LambdaClient = Any
        IAMClient = Any
        FirehoseClient = Any
else:
    S3Client = Any
    LambdaClient = Any
    IAMClient = Any
    FirehoseClient = Any


@dataclass(frozen=True)
class BucketConfig:
    bucket_name: str
    region: str

    @classmethod
    def from_config(cls, cfg: Config, region: str) -> "BucketConfig":
        return cls(bucket_name=cfg.BUCKET_NAME, region=region)


@dataclass(frozen=True)
class LambdaConfig:
    function_name: str
    runtime: str
    handler: str
    timeout: int
    memory_mb: int
    role_arn: Optional[str] = None
    zip_bytes: Optional[bytes] = None

    @classmethod
    def from_config(
        cls,
        cfg: Config,
        role_arn: Optional[str] = None,
        zip_bytes: Optional[bytes] = None,
    ) -> "LambdaConfig":
        return cls(
            function_name=cfg.LAMBDA_FUNCTION_NAME,
            runtime=cfg.LAMBDA_RUNTIME,
            handler=cfg.LAMBDA_HANDLER,
            timeout=cfg.LAMBDA_TIMEOUT,
            memory_mb=cfg.LAMBDA_MEMORY_MB,
            role_arn=role_arn,
            zip_bytes=zip_bytes,
        )


@dataclass(frozen=True)
class RoleConfig:
    role_name: str
    bucket_arn: str
    lambda_arn: Optional[str] = None

    @classmethod
    def from_config(
        cls, cfg: Config, bucket_arn: str, lambda_arn: Optional[str] = None
    ) -> "RoleConfig":
        return cls(
            role_name=cfg.ROLE_NAME,
            bucket_arn=bucket_arn,
            lambda_arn=lambda_arn,
        )


@dataclass(frozen=True)
class FirehoseConfig:
    delivery_stream_name: str
    role_arn: str
    bucket_arn: str
    lambda_arn: str
    prefix: str
    buffering_size: int
    buffering_time: int
    enable_dynamic_partitioning: bool = True
    error_output_prefix: Optional[str] = None
    timezone: str = "Europe/Bucharest"
    enable_parquet: bool = True
    glue_database_name: Optional[str] = None
    glue_table_name: Optional[str] = None

    @classmethod
    def from_config(
        cls, cfg: Config, role_arn: str, bucket_arn: str, lambda_arn: str
    ) -> "FirehoseConfig":
        return cls(
            delivery_stream_name=cfg.DELIVERY_STREAM_NAME,
            role_arn=role_arn,
            bucket_arn=bucket_arn,
            lambda_arn=lambda_arn,
            prefix=cfg.PREFIX,
            buffering_size=cfg.BUFFERING_SIZE,
            buffering_time=cfg.BUFFERING_TIME,
            enable_dynamic_partitioning=getattr(cfg, "ENABLE_DYNAMIC_PARTITIONING", True),
            error_output_prefix=getattr(cfg, "ERROR_OUTPUT_PREFIX", None),
            timezone=getattr(cfg, "TIMEZONE", "Europe/Bucharest"),
            enable_parquet=getattr(cfg, "ENABLE_PARQUET", True),
            glue_database_name=cfg.GLUE_DATABASE_NAME,
            glue_table_name=cfg.GLUE_TABLE_NAME,
        )
