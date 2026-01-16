"""Tests for S3 bucket creation and management."""

import pytest
from botocore.exceptions import ClientError

from iac.bucket import Bucket, BucketResult
from iac.configs import BucketConfig


class TestBucket:
    """Test Bucket class."""

    @pytest.mark.unit
    def test_bucket_exists(self, mock_s3_client):
        mock_s3_client.head_bucket.side_effect = None
        mock_s3_client.head_bucket.return_value = {}

        config = BucketConfig(bucket_name="test-bucket", region="us-east-1")
        bucket = Bucket(config, mock_s3_client)
        result = bucket.ensure()

        assert isinstance(result, BucketResult)
        assert result.bucket_arn == "arn:aws:s3:::test-bucket"
        mock_s3_client.create_bucket.assert_not_called()

    @pytest.mark.unit
    def test_bucket_creation(self, mock_s3_client):
        mock_s3_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadBucket"
        )
        mock_s3_client.create_bucket.return_value = {}
        mock_s3_client.put_public_access_block.return_value = {}

        config = BucketConfig(bucket_name="test-bucket", region="us-east-1")
        bucket = Bucket(config, mock_s3_client)
        result = bucket.ensure()

        assert isinstance(result, BucketResult)
        mock_s3_client.create_bucket.assert_called_once()
        mock_s3_client.put_public_access_block.assert_called_once()

    @pytest.mark.unit
    def test_bucket_already_exists_error(self, mock_s3_client):
        """Test handling of BucketAlreadyExists error."""
        mock_s3_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadBucket"
        )
        mock_s3_client.create_bucket.side_effect = ClientError(
            {"Error": {"Code": "BucketAlreadyExists"}}, "CreateBucket"
        )

        config = BucketConfig(bucket_name="test-bucket", region="us-east-1")
        bucket = Bucket(config, mock_s3_client)
        result = bucket.ensure()

        assert isinstance(result, BucketResult)

    @pytest.mark.unit
    def test_bucket_region_us_east_1(self, mock_s3_client):
        """Test bucket creation in us-east-1 (no LocationConstraint)."""
        mock_s3_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadBucket"
        )

        config = BucketConfig(bucket_name="test-bucket", region="us-east-1")
        bucket = Bucket(config, mock_s3_client)
        bucket.ensure()

        call_args = mock_s3_client.create_bucket.call_args
        assert "CreateBucketConfiguration" not in call_args.kwargs

    @pytest.mark.unit
    def test_bucket_region_other(self, mock_s3_client):
        """Test bucket creation in other regions (with LocationConstraint)."""
        mock_s3_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadBucket"
        )

        config = BucketConfig(bucket_name="test-bucket", region="eu-central-1")
        bucket = Bucket(config, mock_s3_client)
        bucket.ensure()

        # Check that LocationConstraint is in params
        call_args = mock_s3_client.create_bucket.call_args
        assert "CreateBucketConfiguration" in call_args.kwargs
        assert (
            call_args.kwargs["CreateBucketConfiguration"]["LocationConstraint"]
            == "eu-central-1"
        )

    @pytest.mark.unit
    def test_bucket_missing_region(self, mock_s3_client):
        """Test error when region is missing."""
        mock_s3_client.meta.region_name = None

        config = BucketConfig(bucket_name="test-bucket", region="")
        bucket = Bucket(config, mock_s3_client)

        with pytest.raises(RuntimeError, match="S3 region is missing"):
            bucket.ensure()
