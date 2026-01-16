from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from string import Template
from botocore.exceptions import ClientError

from iac.base import Resource, ResourceResult
from iac.configs import RoleConfig, IAMClient
from iac.constants import ErrorCodes
from iac.validation import ResourceValidator

logger = logging.getLogger(__name__)

BASE_PATH = Path(__file__).parent
TRUST_POLICY_PATH = BASE_PATH / "role_trust_policy.json"
PERMISSIONS_POLICY_PATH = BASE_PATH / "role_permissions_policy.json"


@dataclass(frozen=True)
class FirehoseRoleResult(ResourceResult):
    role_arn: str


class Role(Resource[FirehoseRoleResult]):
    def __init__(self, config: RoleConfig, iam_client: IAMClient):
        super().__init__(
            config={
                "ROLE_NAME": config.role_name,
                "BUCKET_ARN": config.bucket_arn,
                "LAMBDA_ARN": config.lambda_arn or "",
            },
            client=iam_client,
        )
        self.role_config = config

    def _get_resource_name(self) -> str:
        return self.role_config.role_name

    def _exists(self, role_name: str) -> bool:
        try:
            self.client.get_role(RoleName=role_name)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == ErrorCodes.NO_SUCH_ENTITY:
                return False
            raise

    def _handle_existing(self, role_name: str) -> FirehoseRoleResult:
        resp = self.client.get_role(RoleName=role_name)
        role_arn = resp["Role"]["Arn"]
        logger.info(f"IAM role exists: {role_arn}")
        self._attach_permissions_policy(role_name)
        return FirehoseRoleResult(role_arn=role_arn)

    def _create(self, role_name: str) -> FirehoseRoleResult:
        if not ResourceValidator.validate_role_name(role_name):
            raise ValueError(
                f"Invalid IAM role name: {role_name}. "
                "Role names must be 1-64 characters and contain only letters, numbers, "
                "and these characters: +, =, ., @, -, _"
            )

        role_arn = self._create_role(role_name)
        self._attach_permissions_policy(role_name)
        return FirehoseRoleResult(role_arn=role_arn)

    def _create_role(self, role_name: str) -> str:
        with open(TRUST_POLICY_PATH, encoding="utf-8") as f:
            trust_policy = json.load(f)

        resp = self.client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for Kinesis Data Firehose",
        )

        role_arn = resp["Role"]["Arn"]
        logger.info(f"IAM role created: {role_arn}")

        logger.info("Waiting for IAM role to propagate...")
        time.sleep(5)

        return role_arn

    def _attach_permissions_policy(self, role_name: str) -> None:
        with open(PERMISSIONS_POLICY_PATH, encoding="utf-8") as f:
            template = Template(f.read())

        policy_json = template.substitute(
            BUCKET_ARN=self.role_config.bucket_arn,
            LAMBDA_ARN=self.role_config.lambda_arn or "",
        )

        self.client.put_role_policy(
            RoleName=role_name,
            PolicyName="FirehoseDeliveryPolicy",
            PolicyDocument=policy_json,
        )

        logger.info("IAM permissions policy attached.")
