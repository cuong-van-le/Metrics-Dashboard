from __future__ import annotations

import io
import json
import logging
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from botocore.exceptions import ClientError

from iac.base import Resource, ResourceResult
from iac.configs import LambdaConfig, LambdaClient, IAMClient
from iac.constants import ErrorCodes
from iac.retry import retry_on_iam_propagation

LAMBDA_TRUST_POLICY_PATH = Path(__file__).parent / "lambda_trust_policy.json"
from iac.validation import ResourceValidator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LambdaResult(ResourceResult):
    lambda_arn: str


def _package_lambda_code(transform_dir: Path) -> bytes:
    """
    Package Lambda code with dependencies.
    Installs dependencies from requirements.txt if it exists.
    """
    zip_buffer = io.BytesIO()
    requirements_file = transform_dir / "requirements.txt"

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in transform_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                if file_path.name == "requirements.txt":
                    continue
                arcname = file_path.relative_to(transform_dir)
                zip_file.write(file_path, arcname)

        if requirements_file.exists():
            logger.info(f"Found requirements.txt, installing dependencies...")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                try:
                    subprocess.run(
                        [
                            "pip",
                            "install",
                            "-r",
                            str(requirements_file),
                            "-t",
                            str(temp_path),
                            "--quiet",
                            "--no-cache-dir",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    logger.info("Dependencies installed successfully")

                    for file_path in temp_path.rglob("*"):
                        if file_path.is_file():
                            if (
                                "__pycache__" in str(file_path)
                                or file_path.suffix == ".pyc"
                            ):
                                continue
                            arcname = file_path.relative_to(temp_path)
                            zip_file.write(file_path, arcname)
                except subprocess.CalledProcessError as e:
                    logger.warning(
                        f"Failed to install dependencies: {e.stderr}. "
                        "Continuing without dependencies - Lambda may fail at runtime."
                    )

    zip_buffer.seek(0)
    return zip_buffer.read()


class LambdaProcessor(Resource[LambdaResult]):
    def __init__(
        self,
        config: LambdaConfig,
        lambda_client: LambdaClient,
        iam_client: IAMClient | None = None,
    ):
        super().__init__(
            config={
                "LAMBDA_FUNCTION_NAME": config.function_name,
                "LAMBDA_RUNTIME": config.runtime,
                "LAMBDA_HANDLER": config.handler,
                "LAMBDA_TIMEOUT": config.timeout,
                "LAMBDA_MEMORY_MB": config.memory_mb,
                "LAMBDA_ROLE_ARN": config.role_arn,
                "LAMBDA_ZIP_BYTES": config.zip_bytes,
            },
            client=lambda_client,
        )
        self.lambda_config = config
        self.iam_client = iam_client

    def _get_resource_name(self) -> str:
        return self.lambda_config.function_name

    def _exists(self, fn_name: str) -> bool:
        try:
            self.client.get_function(FunctionName=fn_name)
            return True
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == ErrorCodes.RESOURCE_NOT_FOUND:
                return False
            raise

    def _handle_existing(self, fn_name: str) -> LambdaResult:
        resp = self.client.get_function(FunctionName=fn_name)
        arn = resp["Configuration"]["FunctionArn"]
        logger.info(f"Lambda exists: {arn}")

        zip_bytes = self.lambda_config.zip_bytes
        if not zip_bytes:
            transform_dir = Path("transform")
            if transform_dir.exists() and any(transform_dir.iterdir()):
                logger.debug(
                    "Packaging lambda code from transform directory for update..."
                )
                zip_bytes = _package_lambda_code(transform_dir)

        if zip_bytes:
            self.client.update_function_code(
                FunctionName=fn_name,
                ZipFile=zip_bytes,
                Publish=True,
            )
            logger.info("Lambda code updated.")
        return LambdaResult(lambda_arn=arn)

    def _create(self, fn_name: str) -> LambdaResult:
        if not ResourceValidator.validate_lambda_name(fn_name):
            raise ValueError(
                f"Invalid Lambda function name: {fn_name}. "
                "Function names must be 1-64 characters and contain only letters, "
                "numbers, hyphens, and underscores."
            )

        lambda_role_arn = self.lambda_config.role_arn
        if not lambda_role_arn:
            lambda_role_arn = self._ensure_lambda_execution_role()
            if not lambda_role_arn:
                raise ValueError(
                    "Lambda function not found and LAMBDA_ROLE_ARN not provided. "
                    "Cannot create lambda without execution role."
                )

        zip_bytes = self.lambda_config.zip_bytes
        if not zip_bytes:
            transform_dir = Path("transform")
            if transform_dir.exists() and any(transform_dir.iterdir()):
                logger.info("Packaging lambda code from transform directory...")
                zip_bytes = _package_lambda_code(transform_dir)
            else:
                raise ValueError(
                    "Lambda function not found and zip_bytes not provided. "
                    "Also, transform directory is empty or doesn't exist."
                )

        return self._create_function_with_retry(fn_name, lambda_role_arn, zip_bytes)

    @retry_on_iam_propagation()
    def _create_function_with_retry(
        self, fn_name: str, lambda_role_arn: str, zip_bytes: bytes
    ) -> LambdaResult:
        resp = self.client.create_function(
            FunctionName=fn_name,
            Runtime=self.lambda_config.runtime,
            Role=lambda_role_arn,
            Handler=self.lambda_config.handler,
            Code={"ZipFile": zip_bytes},
            Timeout=self.lambda_config.timeout,
            MemorySize=self.lambda_config.memory_mb,
            Publish=True,
            Description="Firehose transform processor",
        )
        arn = resp["FunctionArn"]
        logger.info(f"Lambda created: {arn}")
        return LambdaResult(lambda_arn=arn)

    def _ensure_lambda_execution_role(self) -> str | None:
        if not self.iam_client:
            return None

        role_name = f"{self.lambda_config.function_name}-execution-role"

        with open(LAMBDA_TRUST_POLICY_PATH, encoding="utf-8") as f:
            trust_policy = json.load(f)

        try:
            resp = self.iam_client.get_role(RoleName=role_name)
            role_arn = resp["Role"]["Arn"]
            logger.info(f"Lambda execution role exists: {role_arn}")
            self.iam_client.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=json.dumps(trust_policy),
            )
            logger.info("Updated Lambda execution role trust policy.")
            return role_arn
        except ClientError as e:
            if e.response["Error"]["Code"] != ErrorCodes.NO_SUCH_ENTITY:
                raise

        try:
            resp = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Execution role for Lambda function",
            )
            role_arn = resp["Role"]["Arn"]
            logger.info(f"Lambda execution role created: {role_arn}")

            try:
                self.iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                )
                logger.info("Attached basic lambda execution policy.")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code in (ErrorCodes.NO_SUCH_ENTITY, "NoSuchEntity"):
                    policy_doc = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents",
                                ],
                                "Resource": "*",
                            }
                        ],
                    }
                    self.iam_client.put_role_policy(
                        RoleName=role_name,
                        PolicyName="LambdaBasicExecutionPolicy",
                        PolicyDocument=json.dumps(policy_doc),
                    )
                    logger.info("Attached custom lambda execution policy (fallback).")
                else:
                    raise

            logger.info("Waiting for IAM role to propagate...")
            time.sleep(5)

            return role_arn
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == ErrorCodes.ENTITY_ALREADY_EXISTS:
                resp = self.iam_client.get_role(RoleName=role_name)
                role_arn = resp["Role"]["Arn"]
                logger.info(f"Lambda execution role already exists: {role_arn}")
                return role_arn
            logger.warning(f"Could not create lambda execution role: {e}")
            return None
