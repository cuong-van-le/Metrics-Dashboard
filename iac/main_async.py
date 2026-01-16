from __future__ import annotations

import asyncio
from pathlib import Path

from config.env_updater import EnvUpdater
from config.logging_config import get_logger
from config.main import Config, State

from iac.aws_factory import AWSClientFactory
from iac.bucket import Bucket
from iac.configs import (
    BucketConfig,
    FirehoseConfig,
    LambdaConfig,
    RoleConfig,
)
from iac.firehose import FireHose
from iac.lambda_fn import LambdaProcessor
from iac.role import Role

logger = get_logger(__name__)


async def ensure_infra_async(
    update_env: bool = False, env_path: Path = Path(".env")
) -> dict:
    cfg = Config.from_env()
    region = cfg.REGION_NAME

    factory = AWSClientFactory(region=region)
    s3 = factory.create_s3_client()
    iam = factory.create_iam_client()
    lam = factory.create_lambda_client()
    firehose = factory.create_firehose_client()

    bucket_config = BucketConfig.from_config(cfg, region)
    lambda_config = LambdaConfig.from_config(cfg, role_arn=None)

    bucket_resource = Bucket(bucket_config, s3)
    lambda_resource = LambdaProcessor(lambda_config, lam, iam_client=iam)

    bucket_task = asyncio.create_task(asyncio.to_thread(bucket_resource.ensure))
    lambda_task = asyncio.create_task(asyncio.to_thread(lambda_resource.ensure))

    bucket_res, lambda_res = await asyncio.gather(bucket_task, lambda_task)

    role_config = RoleConfig.from_config(
        cfg, bucket_res.bucket_arn, lambda_res.lambda_arn
    )
    role_resource = Role(role_config, iam)
    role_res = await asyncio.to_thread(role_resource.ensure)

    new_state = State(
        ROLE_ARN=role_res.role_arn,
        BUCKET_ARN=bucket_res.bucket_arn,
        LAMBDA_ARN=lambda_res.lambda_arn,
    )
    new_state.save()

    if update_env:
        updater = EnvUpdater(env_path=env_path)
        updater.update(
            role_arn=new_state.ROLE_ARN,
            bucket_arn=new_state.BUCKET_ARN,
            lambda_arn=new_state.LAMBDA_ARN,
        )

    firehose_config = FirehoseConfig.from_config(
        cfg,
        role_arn=new_state.ROLE_ARN,
        bucket_arn=new_state.BUCKET_ARN,
        lambda_arn=new_state.LAMBDA_ARN,
    )
    firehose_resource = FireHose(firehose_config, firehose)
    await asyncio.to_thread(firehose_resource.ensure_stream)

    logger.info("Infrastructure setup complete")
    return {
        "region": region,
        "delivery_stream_name": cfg.DELIVERY_STREAM_NAME,
        "role_arn": new_state.ROLE_ARN,
        "bucket_arn": new_state.BUCKET_ARN,
        "lambda_arn": new_state.LAMBDA_ARN,
    }
