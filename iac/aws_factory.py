import boto3
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AWSClientFactory:
    def __init__(self, region: str, credentials: Optional[Dict[str, Any]] = None):
        self.region = region
        self.credentials = credentials or {}

    def _get_client_kwargs(self) -> Dict[str, Any]:
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
