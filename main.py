"""Main entry point for the application."""

import argparse

from config.logging_config import setup_logging, get_logger
from config.main import Config, State
from iac.main import ensure_infra
from iac.aws_factory import AWSClientFactory
from pipeline.delivery import Ingestion

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Roxxane - Data ingestion pipeline")
    parser.add_argument(
        "--update-env",
        action="store_true",
        help="Update .env file with ARNs after infrastructure setup",
    )
    parser.add_argument(
        "--no-env-update",
        action="store_true",
        help="Do not update .env file even if --update-env is set elsewhere",
    )
    args = parser.parse_args()

    update_env_flag = args.update_env and not args.no_env_update
    ensure_infra(update_env=update_env_flag)

    cfg = Config.from_env()
    st = State.load()

    factory = AWSClientFactory(region=cfg.REGION_NAME)
    client = factory.create_firehose_client()

    runtime_config = {
        "DELIVERY_STREAM_NAME": cfg.DELIVERY_STREAM_NAME,
        "PREFIX": cfg.PREFIX,
        "BUFFERING_SIZE": cfg.BUFFERING_SIZE,
        "BUFFERING_TIME": cfg.BUFFERING_TIME,
        "REGION_NAME": cfg.REGION_NAME,
        "ROLE_ARN": st.ROLE_ARN,
        "BUCKET_ARN": st.BUCKET_ARN,
        "LAMBDA_ARN": st.LAMBDA_ARN,
    }
    logger.info(f"Runtime configuration: {runtime_config}")
    ingester = Ingestion(cfg,client)
    ingester.listen()


if __name__ == "__main__":
    main()
