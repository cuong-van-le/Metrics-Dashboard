"""Tests for configuration loading and validation."""

import pytest
from config.main import Config


class TestConfig:
    """Test Config class."""

    @pytest.mark.unit
    def test_config_loads_from_env(self, mock_env_vars):
        """Test that Config loads all required variables."""
        config = Config.from_env()
        assert config.DELIVERY_STREAM_NAME == "test-stream"
        assert config.PREFIX == "data/"
        assert config.BUFFERING_SIZE == 5
        assert config.BUFFERING_TIME == 300
        assert config.REGION_NAME == "us-east-1"
        assert config.ROLE_NAME == "test-role"
        assert config.BUCKET_NAME == "test-bucket"
        assert config.LAMBDA_FUNCTION_NAME == "test-lambda"
        assert config.LAMBDA_RUNTIME == "python3.12"
        assert config.LAMBDA_HANDLER == "app.handler"
        assert config.LAMBDA_TIMEOUT == 60
        assert config.LAMBDA_MEMORY_MB == 256

    @pytest.mark.unit
    def test_config_missing_required_var(self, mock_env_vars_missing):
        """Test that missing required env var raises error."""
        with pytest.raises(RuntimeError, match="Missing required environment variable"):
            Config.from_env()

    @pytest.mark.unit
    def test_config_invalid_integer(self, mock_env_vars_invalid_int):
        """Test that invalid integer values raise error."""
        with pytest.raises(RuntimeError, match="must be an integer"):
            Config.from_env()

    @pytest.mark.unit
    def test_config_empty_string(self, monkeypatch, mock_env_vars):
        """Test that empty string values raise error."""
        monkeypatch.setenv("DELIVERY_STREAM_NAME", "")
        with pytest.raises(RuntimeError, match="Missing required environment variable"):
            Config.from_env()
