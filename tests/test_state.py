"""Tests for state management."""

import json
import pytest
from config.main import State
from pathlib import Path


class TestState:
    """Test State class."""

    def test_state_loads_from_file(self, valid_state_file):
        """Test loading state from valid JSON file."""
        state = State.load(path=valid_state_file)
        assert state.ROLE_ARN == "arn:aws:iam::123456789012:role/test-role"
        assert state.BUCKET_ARN == "arn:aws:s3:::test-bucket"
        assert (
            state.LAMBDA_ARN
            == "arn:aws:lambda:us-east-1:123456789012:function:test-lambda"
        )

    def test_state_loads_empty_if_missing(self, tmp_path):
        """Test that missing state file returns empty state."""
        missing_path = tmp_path / "missing.json"
        state = State.load(path=missing_path)
        assert state.ROLE_ARN is None
        assert state.BUCKET_ARN is None
        assert state.LAMBDA_ARN is None

    def test_state_loads_empty_if_corrupted(self, corrupted_state_file):
        """Test that corrupted state file raises error."""
        with pytest.raises(json.JSONDecodeError):
            State.load(path=corrupted_state_file)

    def test_state_saves_to_file(self, tmp_path):
        """Test saving state to file."""
        state_path = tmp_path / "state.json"
        state = State(
            ROLE_ARN="arn:aws:iam::123456789012:role/test",
            BUCKET_ARN="arn:aws:s3:::test",
            LAMBDA_ARN="arn:aws:lambda:us-east-1:123456789012:function:test",
        )
        state.save(path=state_path)

        assert state_path.exists()
        loaded = json.loads(state_path.read_text())
        assert loaded["ROLE_ARN"] == "arn:aws:iam::123456789012:role/test"
        assert loaded["BUCKET_ARN"] == "arn:aws:s3:::test"
        assert (
            loaded["LAMBDA_ARN"]
            == "arn:aws:lambda:us-east-1:123456789012:function:test"
        )
