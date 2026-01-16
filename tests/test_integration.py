import pytest
from moto import mock_aws

from config.main import Config
from iac.aws_factory import AWSClientFactory
from iac.bucket import Bucket, BucketResult
from iac.configs import (
    BucketConfig,
    FirehoseConfig,
    LambdaConfig,
    RoleConfig,
)
from iac.firehose import FireHose, FirehoseResult
from iac.lambda_fn import LambdaProcessor, LambdaResult
from iac.orchestrator import InfrastructureOrchestrator
from iac.role import FirehoseRoleResult, Role


@pytest.fixture
def mock_aws_services():
    with mock_aws():
        yield


@pytest.fixture
def aws_clients(mock_aws_services, mock_env_vars):
    import json
    region = mock_env_vars["REGION_NAME"]
    factory = AWSClientFactory(region=region)
    iam = factory.create_iam_client()

    lambda_role_name = f"{mock_env_vars['LAMBDA_FUNCTION_NAME']}-execution-role"
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    
    try:
        iam.create_role(
            RoleName=lambda_role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Execution role for Lambda function",
        )
        iam.put_role_policy(
            RoleName=lambda_role_name,
            PolicyName="BasicExecutionPolicy",
            PolicyDocument=json.dumps({
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
            }),
        )
    except Exception:  # nosec B110
        pass

    return {
        "s3": factory.create_s3_client(),
        "lambda": factory.create_lambda_client(),
        "iam": iam,
        "firehose": factory.create_firehose_client(),
    }


@pytest.fixture
def test_config(mock_env_vars):
    return Config.from_env()


@pytest.mark.integration
class TestIntegrationInfrastructure:
    @pytest.mark.integration
    def test_full_infrastructure_creation(self, aws_clients, test_config, temp_dir):
        orchestrator = InfrastructureOrchestrator()

        bucket_config = BucketConfig.from_config(test_config, test_config.REGION_NAME)
        bucket_resource = Bucket(bucket_config, aws_clients["s3"])
        orchestrator.register("bucket", bucket_resource)
        
        lambda_config = LambdaConfig.from_config(test_config, role_arn=None)
        lambda_resource = LambdaProcessor(lambda_config, aws_clients["lambda"], iam_client=aws_clients["iam"])
        orchestrator.register("lambda", lambda_resource)
        
        def create_role(results):
            bucket_res = results["bucket"]
            lambda_res = results["lambda"]
            role_config = RoleConfig.from_config(
                test_config, bucket_res.bucket_arn, lambda_res.lambda_arn
            )
            return Role(role_config, aws_clients["iam"])

        orchestrator.register("role", depends_on=["bucket", "lambda"], factory=create_role)

        def create_firehose(results):
            firehose_config = FirehoseConfig.from_config(
                test_config,
                role_arn=results["role"].role_arn,
                bucket_arn=results["bucket"].bucket_arn,
                lambda_arn=results["lambda"].lambda_arn,
            )
            firehose_resource = FireHose(firehose_config, aws_clients["firehose"])
            firehose_resource._timeout_s = 5
            return firehose_resource

        orchestrator.register(
            "firehose", depends_on=["role", "bucket", "lambda"], factory=create_firehose
        )

        results = orchestrator.ensure_all()

        assert "bucket" in results
        assert "lambda" in results
        assert "role" in results
        assert "firehose" in results
        
        assert isinstance(results["bucket"], BucketResult)
        assert isinstance(results["lambda"], LambdaResult)
        assert isinstance(results["role"], FirehoseRoleResult)
        assert isinstance(results["firehose"], FirehoseResult)
        
        assert results["bucket"].bucket_arn == f"arn:aws:s3:::{test_config.BUCKET_NAME}"
        assert test_config.LAMBDA_FUNCTION_NAME in results["lambda"].lambda_arn
        assert test_config.ROLE_NAME in results["role"].role_arn
        assert results["firehose"].stream_name == test_config.DELIVERY_STREAM_NAME

    @pytest.mark.integration
    def test_idempotent_creation(self, aws_clients, test_config):
        bucket_config = BucketConfig.from_config(test_config, test_config.REGION_NAME)
        bucket_resource = Bucket(bucket_config, aws_clients["s3"])

        result1 = bucket_resource.ensure()
        result2 = bucket_resource.ensure()
        
        assert result1.bucket_arn == result2.bucket_arn

    @pytest.mark.integration
    def test_resource_dependencies(self, aws_clients, test_config):
        orchestrator = InfrastructureOrchestrator()

        bucket_config = BucketConfig.from_config(test_config, test_config.REGION_NAME)
        bucket_resource = Bucket(bucket_config, aws_clients["s3"])
        orchestrator.register("bucket", bucket_resource)
        
        lambda_config = LambdaConfig.from_config(test_config, role_arn=None)
        lambda_resource = LambdaProcessor(lambda_config, aws_clients["lambda"], iam_client=aws_clients["iam"])
        orchestrator.register("lambda", lambda_resource)
        
        def create_role(results):
            bucket_res = results["bucket"]
            lambda_res = results["lambda"]
            role_config = RoleConfig.from_config(
                test_config, bucket_res.bucket_arn, lambda_res.lambda_arn
            )
            return Role(role_config, aws_clients["iam"])

        orchestrator.register("role", depends_on=["bucket", "lambda"], factory=create_role)

        results = orchestrator.ensure_all()

        assert "bucket" in results
        assert "lambda" in results
        assert "role" in results
        
        assert results["role"].role_arn is not None
        assert test_config.BUCKET_NAME in results["bucket"].bucket_arn
        assert test_config.LAMBDA_FUNCTION_NAME in results["lambda"].lambda_arn

    @pytest.mark.integration
    def test_circular_dependency_detection(self):
        orchestrator = InfrastructureOrchestrator()

        class MockResource:
            def ensure(self):
                pass

        resource1 = MockResource()
        resource2 = MockResource()

        orchestrator.register("resource1", resource1)
        orchestrator.register("resource2", resource2)

        def factory1(results):
            return resource1

        def factory2(results):
            return resource2

        orchestrator.register("resource1", depends_on=["resource2"], factory=factory1)
        orchestrator.register("resource2", depends_on=["resource1"], factory=factory2)
        
        with pytest.raises(RuntimeError, match="Circular dependency"):
            orchestrator.ensure_all()
