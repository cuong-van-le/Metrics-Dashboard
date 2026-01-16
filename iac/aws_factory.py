import logging
from typing import Any

import boto3

logger = logging.getLogger(__name__)


class AWSClientFactory:
    def __init__(self, region: str, credentials: dict[str, Any] | None = None):
        self.region = region
        self.credentials = credentials or {}

    def _get_client_kwargs(self) -> dict[str, Any]:
        kwargs = {"region_name": self.region}
        kwargs.update(self.credentials)
        return kwargs

    def create_s3_client(self):
        return boto3.client("s3", **self._get_client_kwargs())

    def create_iam_client(self):
        return boto3.client("iam", **self._get_client_kwargs())

    def create_lambda_client(self):
        return boto3.client("lambda", **self._get_client_kwargs())

    def create_firehose_client(self):
        return boto3.client("firehose", **self._get_client_kwargs())
