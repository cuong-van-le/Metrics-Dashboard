"""Tests for resource validation utilities."""

from iac.validation import ResourceValidator


class TestResourceValidator:
    """Test ResourceValidator class."""

    def test_validate_bucket_name_valid(self):
        """Test valid bucket names."""
        assert ResourceValidator.validate_bucket_name("my-bucket") is True  # nosec B101
        assert ResourceValidator.validate_bucket_name("my.bucket") is True  # noqa: B101
        assert ResourceValidator.validate_bucket_name("bucket123") is True  # noqa: B101
        assert ResourceValidator.validate_bucket_name("a" * 63) is True  # noqa: B101
        assert ResourceValidator.validate_bucket_name("abc") is True  # noqa: B101

    def test_validate_bucket_name_invalid(self):
        """Test invalid bucket names."""
        assert ResourceValidator.validate_bucket_name("") is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name("ab") is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name("a" * 64) is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name("MyBucket") is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name(".bucket") is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name("bucket.") is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name("-bucket") is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name("bucket-") is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name("bucket..name") is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name("192.168.1.1") is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name("bucket_name") is False  # noqa: B101
        assert ResourceValidator.validate_bucket_name(None) is False  # noqa: B101

    def test_validate_lambda_name_valid(self):
        """Test valid Lambda function names."""
        assert ResourceValidator.validate_lambda_name("my-function") is True  # noqa: B101
        assert ResourceValidator.validate_lambda_name("my_function") is True  # noqa: B101
        assert ResourceValidator.validate_lambda_name("MyFunction") is True  # noqa: B101
        assert ResourceValidator.validate_lambda_name("function123") is True  # noqa: B101
        assert ResourceValidator.validate_lambda_name("a" * 64) is True  # noqa: B101
        assert ResourceValidator.validate_lambda_name("a") is True  # noqa: B101

    def test_validate_lambda_name_invalid(self):
        """Test invalid Lambda function names."""
        assert ResourceValidator.validate_lambda_name("") is False  # noqa: B101
        assert ResourceValidator.validate_lambda_name("a" * 65) is False  # noqa: B101
        assert ResourceValidator.validate_lambda_name("my.function") is False  # noqa: B101
        assert ResourceValidator.validate_lambda_name(None) is False  # noqa: B101

    def test_validate_role_name_valid(self):
        """Test valid IAM role names."""
        assert ResourceValidator.validate_role_name("my-role") is True  # noqa: B101
        assert ResourceValidator.validate_role_name("my_role") is True  # noqa: B101
        assert ResourceValidator.validate_role_name("MyRole") is True  # noqa: B101
        assert ResourceValidator.validate_role_name("role+test") is True  # noqa: B101
        assert ResourceValidator.validate_role_name("role=test") is True  # noqa: B101
        assert ResourceValidator.validate_role_name("role.test") is True  # noqa: B101
        assert ResourceValidator.validate_role_name("role@test") is True  # noqa: B101
        assert ResourceValidator.validate_role_name("a" * 64) is True  # noqa: B101
        assert ResourceValidator.validate_role_name("a") is True  # noqa: B101

    def test_validate_role_name_invalid(self):
        """Test invalid IAM role names."""
        assert ResourceValidator.validate_role_name("") is False  # noqa: B101
        assert ResourceValidator.validate_role_name("a" * 65) is False  # noqa: B101
        assert ResourceValidator.validate_role_name("role#test") is False  # noqa: B101
        assert ResourceValidator.validate_role_name(None) is False  # noqa: B101

    def test_validate_firehose_stream_name_valid(self):
        """Test valid Firehose stream names."""
        assert ResourceValidator.validate_firehose_stream_name("my-stream") is True  # noqa: B101
        assert ResourceValidator.validate_firehose_stream_name("my_stream") is True  # noqa: B101
        assert ResourceValidator.validate_firehose_stream_name("MyStream") is True  # noqa: B101
        assert ResourceValidator.validate_firehose_stream_name("stream123") is True  # noqa: B101
        assert ResourceValidator.validate_firehose_stream_name("a" * 64) is True  # noqa: B101
        assert ResourceValidator.validate_firehose_stream_name("a") is True  # noqa: B101

    def test_validate_firehose_stream_name_invalid(self):
        """Test invalid Firehose stream names."""
        assert ResourceValidator.validate_firehose_stream_name("") is False  # noqa: B101
        assert ResourceValidator.validate_firehose_stream_name("a" * 65) is False  # noqa: B101
        assert ResourceValidator.validate_firehose_stream_name("my.stream") is False  # noqa: B101
        assert ResourceValidator.validate_firehose_stream_name(None) is False  # noqa: B101

    def test_validate_arn_valid(self):
        """Test valid ARN formats."""
        assert (  # noqa: B101
            ResourceValidator.validate_arn(
                "arn:aws:s3:::my-bucket"
            )
            is True
        )
        assert (  # noqa: B101
            ResourceValidator.validate_arn(
                "arn:aws:lambda:us-east-1:123456789012:function:my-function"
            )
            is True
        )
        assert (  # noqa: B101
            ResourceValidator.validate_arn(
                "arn:aws:iam::123456789012:role/my-role"
            )
            is True
        )

    def test_validate_arn_invalid(self):
        """Test invalid ARN formats."""
        assert ResourceValidator.validate_arn("not-an-arn") is False  # noqa: B101
        assert ResourceValidator.validate_arn("arn:aws:s3:::") is False  # noqa: B101
        assert ResourceValidator.validate_arn("arn:aws:s3") is False  # noqa: B101
        assert ResourceValidator.validate_arn(None) is False  # noqa: B101

    def test_validate_s3_arn_valid(self):
        """Test valid S3 ARN formats."""
        assert ResourceValidator.validate_s3_arn("arn:aws:s3:::my-bucket") is True  # noqa: B101
        assert ResourceValidator.validate_s3_arn("arn:aws:s3:::my.bucket") is True  # noqa: B101

    def test_validate_s3_arn_invalid(self):
        """Test invalid S3 ARN formats."""
        assert ResourceValidator.validate_s3_arn("arn:aws:lambda:us-east-1:123456789012:function:test") is False  # noqa: B101
        assert ResourceValidator.validate_s3_arn("not-an-arn") is False  # noqa: B101
        assert ResourceValidator.validate_s3_arn(None) is False  # noqa: B101

    def test_validate_lambda_arn_valid(self):
        """Test valid Lambda ARN formats."""
        assert (  # noqa: B101
            ResourceValidator.validate_lambda_arn(
                "arn:aws:lambda:us-east-1:123456789012:function:my-function"
            )
            is True
        )

    def test_validate_lambda_arn_invalid(self):
        """Test invalid Lambda ARN formats."""
        assert ResourceValidator.validate_lambda_arn("arn:aws:s3:::my-bucket") is False  # noqa: B101
        assert ResourceValidator.validate_lambda_arn("not-an-arn") is False  # noqa: B101
        assert ResourceValidator.validate_lambda_arn(None) is False  # noqa: B101

    def test_validate_iam_role_arn_valid(self):
        """Test valid IAM role ARN formats."""
        assert (  # noqa: B101
            ResourceValidator.validate_iam_role_arn(
                "arn:aws:iam::123456789012:role/my-role"
            )
            is True
        )

    def test_validate_iam_role_arn_invalid(self):
        """Test invalid IAM role ARN formats."""
        assert ResourceValidator.validate_iam_role_arn("arn:aws:s3:::my-bucket") is False  # noqa: B101
        assert ResourceValidator.validate_iam_role_arn("not-an-arn") is False  # noqa: B101
        assert ResourceValidator.validate_iam_role_arn(None) is False  # noqa: B101
