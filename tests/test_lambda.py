"""Tests for Lambda function creation and management."""

import pytest
from botocore.exceptions import ClientError
from unittest.mock import patch

from iac.lambda_fn import LambdaProcessor, LambdaResult
from iac.lambda_fn import _package_lambda_code


class TestLambdaPackaging:
    """Test Lambda code packaging."""

    @pytest.mark.unit
    def test_package_lambda_code(self, transform_dir):
        """Test packaging lambda code from directory."""
        zip_bytes = _package_lambda_code(transform_dir)

        assert zip_bytes is not None
        assert len(zip_bytes) > 0
        # Verify it's a valid zip
        import zipfile
        import io

        zip_file = zipfile.ZipFile(io.BytesIO(zip_bytes))
        assert "app.py" in zip_file.namelist()

    @pytest.mark.unit
    def test_package_empty_directory(self, empty_transform_dir):
        """Test packaging empty directory raises error."""
        # Empty directory should still create a zip, but it will be empty
        zip_bytes = _package_lambda_code(empty_transform_dir)
        assert zip_bytes is not None


class TestLambdaProcessor:
    """Test LambdaProcessor class."""

    @pytest.mark.unit
    def test_lambda_exists(self, mock_lambda_client, transform_dir):
        """Test detection of existing lambda."""
        # Mock lambda exists - clear side_effect first
        mock_lambda_client.get_function.side_effect = None
        mock_lambda_client.get_function.return_value = {
            "Configuration": {
                "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test"
            }
        }
        mock_lambda_client.update_function_code.return_value = {}

        from iac.configs import LambdaConfig

        config = LambdaConfig(
            function_name="test-lambda",
            runtime="python3.12",
            handler="app.handler",
            timeout=60,
            memory_mb=256,
        )
        processor = LambdaProcessor(config, mock_lambda_client)

        with patch("iac.lambda_fn.Path", return_value=transform_dir):
            result = processor.ensure()

        assert isinstance(result, LambdaResult)
        mock_lambda_client.update_function_code.assert_called_once()

    @pytest.mark.unit
    def test_lambda_creation(self, mock_lambda_client, mock_iam_client, transform_dir):
        """Test lambda creation when it doesn't exist."""
        # Mock lambda doesn't exist
        mock_lambda_client.get_function.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "GetFunction"
        )

        # Mock role creation
        mock_iam_client.get_role.side_effect = ClientError(
            {"Error": {"Code": "NoSuchEntity"}}, "GetRole"
        )
        mock_iam_client.create_role.return_value = {
            "Role": {"Arn": "arn:aws:iam::123456789012:role/test-execution-role"}
        }
        mock_iam_client.attach_role_policy.return_value = {}

        # Mock lambda creation
        mock_lambda_client.create_function.return_value = {
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test"
        }

        from iac.configs import LambdaConfig

        config = LambdaConfig(
            function_name="test-lambda",
            runtime="python3.12",
            handler="app.handler",
            timeout=60,
            memory_mb=256,
        )
        processor = LambdaProcessor(config, mock_lambda_client, iam_client=mock_iam_client)

        with patch("iac.lambda_fn.Path", return_value=transform_dir), patch(
            "time.sleep"
        ):  # Skip sleep in tests
            result = processor.ensure()

        assert isinstance(result, LambdaResult)
        mock_lambda_client.create_function.assert_called_once()

    @pytest.mark.unit
    def test_lambda_empty_transform_directory(
        self, mock_lambda_client, mock_iam_client, empty_transform_dir
    ):
        """Test error when transform directory is empty."""
        mock_lambda_client.get_function.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "GetFunction"
        )
        
        # Mock role creation so we can get to the zip_bytes check
        mock_iam_client.get_role.side_effect = ClientError(
            {"Error": {"Code": "NoSuchEntity"}}, "GetRole"
        )
        mock_iam_client.create_role.return_value = {
            "Role": {"Arn": "arn:aws:iam::123456789012:role/test-execution-role"}
        }
        mock_iam_client.attach_role_policy.return_value = {}

        from iac.configs import LambdaConfig

        config = LambdaConfig(
            function_name="test-lambda",
            runtime="python3.12",
            handler="app.handler",
            timeout=60,
            memory_mb=256,
        )
        processor = LambdaProcessor(config, mock_lambda_client, iam_client=mock_iam_client)

        with patch("iac.lambda_fn.Path", return_value=empty_transform_dir), patch("time.sleep"):
            with pytest.raises(ValueError, match="transform directory is empty"):
                processor.ensure()

    @pytest.mark.unit
    def test_lambda_missing_transform_directory(self, mock_lambda_client, mock_iam_client, tmp_path):
        """Test error when transform directory doesn't exist."""
        mock_lambda_client.get_function.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "GetFunction"
        )
        
        # Mock role creation so we can get to the zip_bytes check
        mock_iam_client.get_role.side_effect = ClientError(
            {"Error": {"Code": "NoSuchEntity"}}, "GetRole"
        )
        mock_iam_client.create_role.return_value = {
            "Role": {"Arn": "arn:aws:iam::123456789012:role/test-execution-role"}
        }
        mock_iam_client.attach_role_policy.return_value = {}

        from iac.configs import LambdaConfig

        config = LambdaConfig(
            function_name="test-lambda",
            runtime="python3.12",
            handler="app.handler",
            timeout=60,
            memory_mb=256,
        )
        processor = LambdaProcessor(config, mock_lambda_client, iam_client=mock_iam_client)

        missing_dir = tmp_path / "nonexistent"
        with patch("iac.lambda_fn.Path", return_value=missing_dir), patch("time.sleep"):
            with pytest.raises(ValueError, match="transform directory is empty"):
                processor.ensure()

    @pytest.mark.unit
    def test_lambda_role_propagation_retry(
        self, mock_lambda_client, mock_iam_client, transform_dir
    ):
        """Test retry logic for IAM role propagation."""
        mock_lambda_client.get_function.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "GetFunction"
        )

        # Mock role creation
        mock_iam_client.get_role.side_effect = ClientError(
            {"Error": {"Code": "NoSuchEntity"}}, "GetRole"
        )
        mock_iam_client.create_role.return_value = {
            "Role": {"Arn": "arn:aws:iam::123456789012:role/test-execution-role"}
        }

        # First call fails with role not ready, second succeeds
        mock_lambda_client.create_function.side_effect = [
            ClientError(
                {
                    "Error": {
                        "Code": "InvalidParameterValueException",
                        "Message": "cannot be assumed",
                    }
                },
                "CreateFunction",
            ),
            {"FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test"},
        ]

        from iac.configs import LambdaConfig

        config = LambdaConfig(
            function_name="test-lambda",
            runtime="python3.12",
            handler="app.handler",
            timeout=60,
            memory_mb=256,
        )
        processor = LambdaProcessor(config, mock_lambda_client, iam_client=mock_iam_client)

        with patch("iac.lambda_fn.Path", return_value=transform_dir), patch(
            "time.sleep"
        ):  # Skip sleep in tests
            result = processor.ensure()

        assert isinstance(result, LambdaResult)
        assert mock_lambda_client.create_function.call_count == 2  # Retried once
