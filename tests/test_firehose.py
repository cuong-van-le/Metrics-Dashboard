import pytest
from botocore.exceptions import ClientError
from unittest.mock import patch

from iac.firehose import FireHose
from iac.configs import FirehoseConfig


class TestFireHose:
    """Test FireHose class."""

    @pytest.mark.unit
    def test_stream_exists_active(self, mock_firehose_client):
        """Test detection of existing active stream."""
        mock_firehose_client.describe_delivery_stream.side_effect = None
        mock_firehose_client.describe_delivery_stream.return_value = {
            "DeliveryStreamDescription": {"DeliveryStreamStatus": "ACTIVE"}
        }

        config = FirehoseConfig(
            delivery_stream_name="test-stream",
            role_arn="arn:aws:iam::123456789012:role/test",
            bucket_arn="arn:aws:s3:::test",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:test",
            prefix="data/",
            buffering_size=5,
            buffering_time=300,
        )
        firehose = FireHose(config, mock_firehose_client)

        firehose.ensure_stream()

        mock_firehose_client.create_delivery_stream.assert_not_called()

    @pytest.mark.unit
    def test_stream_creation(self, mock_firehose_client):
        """Test stream creation when it doesn't exist."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ClientError(
                    {"Error": {"Code": "ResourceNotFoundException"}},
                    "DescribeDeliveryStream",
                )
            return {"DeliveryStreamDescription": {"DeliveryStreamStatus": "ACTIVE"}}

        mock_firehose_client.describe_delivery_stream.side_effect = side_effect
        mock_firehose_client.create_delivery_stream.return_value = {}

        config = FirehoseConfig(
            delivery_stream_name="test-stream",
            role_arn="arn:aws:iam::123456789012:role/test",
            bucket_arn="arn:aws:s3:::test",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:test",
            prefix="data/",
            buffering_size=5,
            buffering_time=300,
        )
        firehose = FireHose(config, mock_firehose_client)

        with patch("time.sleep"):
            firehose.ensure_stream()

        mock_firehose_client.create_delivery_stream.assert_called_once()

    @pytest.mark.unit
    def test_stream_role_propagation_retry(self, mock_firehose_client):
        """Test retry logic for IAM role propagation."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ClientError(
                    {"Error": {"Code": "ResourceNotFoundException"}},
                    "DescribeDeliveryStream",
                )
            return {"DeliveryStreamDescription": {"DeliveryStreamStatus": "ACTIVE"}}

        mock_firehose_client.describe_delivery_stream.side_effect = side_effect

        mock_firehose_client.create_delivery_stream.side_effect = [
            ClientError(
                {
                    "Error": {
                        "Code": "InvalidArgumentException",
                        "Message": "unable to assume role",
                    }
                },
                "CreateDeliveryStream",
            ),
            {},
        ]

        config = FirehoseConfig(
            delivery_stream_name="test-stream",
            role_arn="arn:aws:iam::123456789012:role/test",
            bucket_arn="arn:aws:s3:::test",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:test",
            prefix="data/",
            buffering_size=5,
            buffering_time=300,
        )
        firehose = FireHose(config, mock_firehose_client)

        with patch("time.sleep"):
            firehose.ensure_stream()

        assert mock_firehose_client.create_delivery_stream.call_count == 2

    @pytest.mark.unit
    def test_stream_creating_failed(self, mock_firehose_client):
        """Test handling of CREATING_FAILED status."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ClientError(
                    {"Error": {"Code": "ResourceNotFoundException"}},
                    "DescribeDeliveryStream",
                )
            return {
                "DeliveryStreamDescription": {"DeliveryStreamStatus": "CREATING_FAILED"}
            }

        mock_firehose_client.describe_delivery_stream.side_effect = side_effect
        mock_firehose_client.create_delivery_stream.return_value = {}

        config = FirehoseConfig(
            delivery_stream_name="test-stream",
            role_arn="arn:aws:iam::123456789012:role/test",
            bucket_arn="arn:aws:s3:::test",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:test",
            prefix="data/",
            buffering_size=5,
            buffering_time=300,
        )
        firehose = FireHose(config, mock_firehose_client)

        with pytest.raises(RuntimeError, match="CREATING_FAILED"):
            firehose.ensure_stream()
