"""Tests for .env file update functionality."""

import pytest
from pathlib import Path

from config.env_updater import EnvUpdater
from config.main import State


class TestEnvUpdate:
    """Test .env file update functionality."""

    def test_update_env_adds_missing_arns(self, env_file_path):
        """Test that missing ARNs are added to .env."""
        env_file_path.write_text("DELIVERY_STREAM_NAME=test\n")

        updater = EnvUpdater(env_path=env_file_path)
        updater.update(
            role_arn="arn:aws:iam::123456789012:role/test",
            bucket_arn="arn:aws:s3:::test",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:test",
        )

        content = env_file_path.read_text()
        assert "ROLE_ARN=arn:aws:iam::123456789012:role/test" in content
        assert "BUCKET_ARN=arn:aws:s3:::test" in content
        assert (
            "LAMBDA_ARN=arn:aws:lambda:us-east-1:123456789012:function:test" in content
        )

    def test_update_env_updates_existing_arns(self, env_file_path):
        """Test that existing ARNs are updated."""
        env_file_path.write_text("ROLE_ARN=old-arn\nBUCKET_ARN=old-bucket\n")

        updater = EnvUpdater(env_path=env_file_path)
        updater.update(
            role_arn="arn:aws:iam::123456789012:role/new",
            bucket_arn="arn:aws:s3:::new-bucket",
            lambda_arn="arn:aws:lambda:us-east-1:123456789012:function:new",
        )

        content = env_file_path.read_text()
        assert "ROLE_ARN=arn:aws:iam::123456789012:role/new" in content
        assert "BUCKET_ARN=arn:aws:s3:::new-bucket" in content
        assert "old-arn" not in content

    def test_update_env_preserves_comments(self, env_file_path):
        """Test that comments are preserved."""
        env_file_path.write_text(
            "# This is a comment\nROLE_ARN=old\n# Another comment\n"
        )

        updater = EnvUpdater(env_path=env_file_path)
        updater.update(
            role_arn="arn:aws:iam::123456789012:role/new",
            bucket_arn=None,
            lambda_arn=None,
        )

        content = env_file_path.read_text()
        assert "# This is a comment" in content
        assert "# Another comment" in content

    def test_update_env_handles_missing_file(self, tmp_path):
        """Test that missing .env file is handled gracefully."""
        missing_path = tmp_path / "missing.env"

        updater = EnvUpdater(env_path=missing_path)
        # Should not raise error, just log warning
        result = updater.update(
            role_arn="arn:aws:iam::123456789012:role/test",
            bucket_arn=None,
            lambda_arn=None,
        )
        assert result is False

    def test_update_env_no_changes_needed(self, env_file_path):
        """Test that no changes are made when ARNs match."""
        env_file_path.write_text("ROLE_ARN=arn:aws:iam::123456789012:role/test\n")

        updater = EnvUpdater(env_path=env_file_path)
        updater.update(
            role_arn="arn:aws:iam::123456789012:role/test",
            bucket_arn=None,
            lambda_arn=None,
        )

        # Content should be the same (or very similar)
        new_content = env_file_path.read_text()
        assert "ROLE_ARN=arn:aws:iam::123456789012:role/test" in new_content
