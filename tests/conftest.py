import json
import shutil
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def temp_dir(tmp_path):
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture
def mock_env_vars(monkeypatch):
    env_vars = {
        "DELIVERY_STREAM_NAME": "test-stream",
        "PREFIX": "data/",
        "BUFFERING_SIZE": "5",
        "BUFFERING_TIME": "300",
        "REGION_NAME": "us-east-1",
        "ROLE_NAME": "test-role",
        "BUCKET_NAME": "test-bucket",
        "LAMBDA_FUNCTION_NAME": "test-lambda",
        "LAMBDA_RUNTIME": "python3.12",
        "LAMBDA_HANDLER": "app.handler",
        "LAMBDA_TIMEOUT": "60",
        "LAMBDA_MEMORY_MB": "256",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_env_vars_missing(monkeypatch):
    env_vars = {
        "DELIVERY_STREAM_NAME": "test-stream",
        "PREFIX": "data/",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    for key in ["BUFFERING_SIZE", "BUFFERING_TIME", "REGION_NAME"]:
        monkeypatch.delenv(key, raising=False)
    return env_vars


@pytest.fixture
def mock_env_vars_invalid_int(monkeypatch):
    env_vars = {
        "DELIVERY_STREAM_NAME": "test-stream",
        "PREFIX": "data/",
        "BUFFERING_SIZE": "not-a-number",
        "BUFFERING_TIME": "300",
        "REGION_NAME": "us-east-1",
        "ROLE_NAME": "test-role",
        "BUCKET_NAME": "test-bucket",
        "LAMBDA_FUNCTION_NAME": "test-lambda",
        "LAMBDA_RUNTIME": "python3.12",
        "LAMBDA_HANDLER": "app.handler",
        "LAMBDA_TIMEOUT": "abc",
        "LAMBDA_MEMORY_MB": "256",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    client = MagicMock()
    client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
    )
    return client


@pytest.fixture
def mock_lambda_client():
    """Mock Lambda client."""
    client = MagicMock()
    client.get_function.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "Not Found"}},
        "GetFunction",
    )
    return client


@pytest.fixture
def mock_iam_client():
    """Mock IAM client."""
    client = MagicMock()
    client.get_role.side_effect = ClientError(
        {"Error": {"Code": "NoSuchEntity", "Message": "Not Found"}}, "GetRole"
    )
    return client


@pytest.fixture
def mock_firehose_client():
    """Mock Firehose client."""
    client = MagicMock()
    client.describe_delivery_stream.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "Not Found"}},
        "DescribeDeliveryStream",
    )
    return client


@pytest.fixture
def state_file_path(tmp_path):
    """Create a temporary state.json file path."""
    state_path = tmp_path / "state.json"
    return state_path


@pytest.fixture
def empty_state_file(state_file_path):
    """Create an empty state.json file."""
    state_file_path.write_text("{}")
    return state_file_path


@pytest.fixture
def valid_state_file(state_file_path):
    """Create a valid state.json file."""
    state = {
        "ROLE_ARN": "arn:aws:iam::123456789012:role/test-role",
        "BUCKET_ARN": "arn:aws:s3:::test-bucket",
        "LAMBDA_ARN": "arn:aws:lambda:us-east-1:123456789012:function:test-lambda",
    }
    state_file_path.write_text(json.dumps(state))
    return state_file_path


@pytest.fixture
def corrupted_state_file(state_file_path):
    """Create a corrupted state.json file."""
    state_file_path.write_text("{ invalid json }")
    return state_file_path


@pytest.fixture
def transform_dir(tmp_path):
    """Create a transform directory with test files."""
    transform_path = tmp_path / "transform"
    transform_path.mkdir()

    (transform_path / "app.py").write_text(
        'def handler(event, context):\n    return {"statusCode": 200}\n'
    )

    return transform_path


@pytest.fixture
def empty_transform_dir(tmp_path):
    """Create an empty transform directory."""
    transform_path = tmp_path / "transform"
    transform_path.mkdir()
    return transform_path


@pytest.fixture
def env_file_path(tmp_path):
    """Create a temporary .env file path."""
    env_path = tmp_path / ".env"
    return env_path


@pytest.fixture
def valid_env_file(env_file_path):
    """Create a valid .env file."""
    env_content = """DELIVERY_STREAM_NAME=test-stream
PREFIX=data/
BUFFERING_SIZE=5
BUFFERING_TIME=300
REGION_NAME=us-east-1
ROLE_NAME=test-role
BUCKET_NAME=test-bucket
LAMBDA_FUNCTION_NAME=test-lambda
LAMBDA_RUNTIME=python3.12
LAMBDA_HANDLER=app.handler
LAMBDA_TIMEOUT=60
LAMBDA_MEMORY_MB=256
"""
    env_file_path.write_text(env_content)
    return env_file_path


@pytest.fixture
def malformed_env_file(env_file_path):
    """Create a malformed .env file."""
    env_file_path.write_text("INVALID LINE WITHOUT EQUALS\nKEY=value")
    return env_file_path
