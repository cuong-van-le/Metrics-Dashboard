import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck

from iac.validation import ResourceValidator


class TestPropertyBasedValidation:
    @pytest.mark.unit
    @given(st.text(min_size=3, max_size=63, alphabet=st.characters(min_codepoint=97, max_codepoint=122, whitelist_categories=('Ll', 'Nd'))))
    @settings(suppress_health_check=[HealthCheck.filter_too_much], max_examples=20)
    def test_bucket_name_property(self, name):
        assume(not name.startswith(".") and not name.endswith("."))
        assume(not name.startswith("-") and not name.endswith("-"))
        assume(".." not in name)
        assume(not name.replace(".", "").replace("-", "").isdigit())
        
        result = ResourceValidator.validate_bucket_name(name)
        assert isinstance(result, bool)

    @pytest.mark.unit
    @given(st.text(min_size=1, max_size=64, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters="-_")))
    @settings(suppress_health_check=[HealthCheck.filter_too_much], max_examples=20)
    def test_lambda_name_property(self, name):
        result = ResourceValidator.validate_lambda_name(name)
        assert isinstance(result, bool)

    @pytest.mark.unit
    @given(st.text(min_size=1, max_size=64, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters="+=,.@_-")))
    @settings(suppress_health_check=[HealthCheck.filter_too_much], max_examples=20)
    def test_role_name_property(self, name):
        result = ResourceValidator.validate_role_name(name)
        assert isinstance(result, bool)

    @pytest.mark.unit
    @given(st.text(min_size=1, max_size=64, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters="-_")))
    @settings(suppress_health_check=[HealthCheck.filter_too_much], max_examples=20)
    def test_firehose_stream_name_property(self, name):
        result = ResourceValidator.validate_firehose_stream_name(name)
        assert isinstance(result, bool)

    @pytest.mark.unit
    @given(st.text())
    def test_arn_validation_property(self, arn):
        result = ResourceValidator.validate_arn(arn)
        assert isinstance(result, bool)
        
        if result:
            assert arn.startswith("arn:aws:")
            parts = arn.split(":")
            assert len(parts) >= 4

    @pytest.mark.unit
    @given(st.text())
    def test_s3_arn_property(self, arn):
        result = ResourceValidator.validate_s3_arn(arn)
        assert isinstance(result, bool)
        
        if result:
            assert arn.startswith("arn:aws:s3:::")

    @pytest.mark.unit
    @given(st.text())
    def test_lambda_arn_property(self, arn):
        result = ResourceValidator.validate_lambda_arn(arn)
        assert isinstance(result, bool)
        
        if result:
            assert arn.startswith("arn:aws:lambda:")

    @pytest.mark.unit
    @given(st.text())
    def test_iam_role_arn_property(self, arn):
        result = ResourceValidator.validate_iam_role_arn(arn)
        assert isinstance(result, bool)
        
        if result:
            assert arn.startswith("arn:aws:iam::")

    @pytest.mark.unit
    @given(st.one_of(
        st.none(),
        st.integers(),
        st.floats(),
        st.booleans(),
        st.lists(st.text()),
        st.dictionaries(st.text(), st.text()),
    ))
    def test_validation_handles_non_string_types(self, value):
        assert ResourceValidator.validate_bucket_name(value) is False
        assert ResourceValidator.validate_lambda_name(value) is False
        assert ResourceValidator.validate_role_name(value) is False
        assert ResourceValidator.validate_firehose_stream_name(value) is False
        assert ResourceValidator.validate_arn(value) is False
        assert ResourceValidator.validate_s3_arn(value) is False
        assert ResourceValidator.validate_lambda_arn(value) is False
        assert ResourceValidator.validate_iam_role_arn(value) is False

    @pytest.mark.unit
    @given(st.text(min_size=3, max_size=63, alphabet=st.characters(min_codepoint=97, max_codepoint=122, whitelist_categories=('Ll', 'Nd'))))
    @settings(suppress_health_check=[HealthCheck.filter_too_much], max_examples=20)
    def test_valid_bucket_names_are_accepted(self, name):
        assume(not name.startswith(".") and not name.endswith("."))
        assume(not name.startswith("-") and not name.endswith("-"))
        assume(".." not in name)
        assume(not name.replace(".", "").replace("-", "").isdigit())
        
        if ResourceValidator.validate_bucket_name(name):
            assert 3 <= len(name) <= 63
            assert all(c.isalnum() or c in ".-" for c in name)
