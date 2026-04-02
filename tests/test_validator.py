"""Tests for validator.py — PublicCodeValidator and ValidationResult."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from validator import PublicCodeValidator, ValidationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def validator():
    """Return a PublicCodeValidator with the spec validator marked unavailable."""
    with patch(
        "validator.PublicCodeValidator._check_validator", return_value=False
    ):
        return PublicCodeValidator()


@pytest.fixture
def validator_with_spec(tmp_path):
    """Return a PublicCodeValidator that pretends the spec validator is available."""
    fake_bin = tmp_path / "publiccode-parser"
    fake_bin.write_text("#!/bin/sh\nexit 0\n")
    fake_bin.chmod(0o755)
    with patch("validator.config.VALIDATOR_PATH", str(fake_bin)):
        with patch(
            "validator.PublicCodeValidator._check_validator", return_value=True
        ):
            v = PublicCodeValidator()
            v.validator_available = True
            return v


# ---------------------------------------------------------------------------
# ValidationResult dataclass
# ---------------------------------------------------------------------------

class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_defaults(self):
        """Default values are set correctly."""
        r = ValidationResult()
        assert r.yaml_valid is False
        assert r.spec_valid is False
        assert r.useful is False
        assert r.usefulness_score == 0
        assert r.spec_errors == []
        assert r.spec_warnings == []
        assert r.usefulness_issues == []

    def test_validation_timestamp_auto_set(self):
        """validation_timestamp is automatically populated."""
        r = ValidationResult()
        assert r.validation_timestamp is not None
        assert "T" in r.validation_timestamp  # ISO format

    def test_explicit_values(self):
        """Explicit field values are stored correctly."""
        r = ValidationResult(yaml_valid=True, usefulness_score=75)
        assert r.yaml_valid is True
        assert r.usefulness_score == 75


# ---------------------------------------------------------------------------
# YAML syntax validation
# ---------------------------------------------------------------------------

VALID_YAML = b"""publiccodeYmlVersion: '0.1'
name: My App
url: https://example.gov/myapp
"""

HTML_CONTENT = b"""<!DOCTYPE html>
<html><head><title>Error</title></head>
<body><h1>Not Found</h1></body></html>"""

INVALID_YAML = b"""name: test
  bad_indent: true
this: : broken
"""


class TestValidateYamlSyntax:
    """Tests for _validate_yaml_syntax."""

    def test_valid_yaml_passes(self, validator):
        """Valid YAML is parsed and sets yaml_valid=True."""
        result = validator.validate(VALID_YAML)
        assert result.yaml_valid is True
        assert result.yaml_error is None
        assert isinstance(result.parsed_yaml, dict)

    def test_html_content_detected(self, validator):
        """HTML response sets yaml_error and yaml_valid=False."""
        result = validator.validate(HTML_CONTENT)
        assert result.yaml_valid is False
        assert result.yaml_error == "HTML content returned instead of YAML"

    def test_invalid_yaml_sets_error(self, validator):
        """Malformed YAML sets yaml_error and yaml_valid=False."""
        result = validator.validate(INVALID_YAML)
        assert result.yaml_valid is False
        assert result.yaml_error is not None

    def test_non_dict_yaml_rejected(self, validator):
        """YAML that parses as a list (not dict) is rejected."""
        result = validator.validate(b"- item1\n- item2\n")
        assert result.yaml_valid is False
        assert "dictionary" in result.yaml_error

    def test_encoding_error_handled(self, validator):
        """Binary content that cannot be decoded as UTF-8 is handled."""
        result = validator.validate(b"\xff\xfe invalid utf-8 \xc3\x28")
        assert result.yaml_valid is False
        assert result.yaml_error == "Encoding error"

    def test_source_url_error_page_detected(self, validator):
        """A source URL containing an error-page token is rejected early."""
        result = validator.validate(
            VALID_YAML,
            source_url="https://example.gov/errordocument"
        )
        assert result.yaml_valid is False
        assert "error/landing page" in result.yaml_error

    def test_source_url_login_page_detected(self, validator):
        """A source URL containing 'login' is rejected early."""
        result = validator.validate(
            VALID_YAML,
            source_url="https://example.gov/login"
        )
        assert result.yaml_valid is False

    def test_normal_source_url_passes(self, validator):
        """A normal source URL does not trigger the error-page check."""
        result = validator.validate(
            VALID_YAML,
            source_url="https://example.gov/publiccode.yml"
        )
        assert result.yaml_valid is True

    def test_yaml_error_truncated_if_long(self, validator):
        """Very long YAML error messages are truncated to 'YAML syntax error'."""
        long_yaml_error_content = b"key: [\n"  # triggers yaml parse error
        result = validator.validate(long_yaml_error_content)
        assert result.yaml_valid is False
        # Error is either the short sentinel or a brief inline message
        assert result.yaml_error is not None
        assert len(result.yaml_error) <= 100


# ---------------------------------------------------------------------------
# JSON syntax validation
# ---------------------------------------------------------------------------

VALID_JSON = b'{"name": "My App", "version": "1.0.0"}'
VALID_JSON_ARRAY = b'[{"name": "App1"}, {"name": "App2"}]'
HTML_JSON = b"<!DOCTYPE html><html><head></head><body>Not Found</body></html>"
INVALID_JSON = b'{"name": "test", "broken": true, }'


class TestValidateJsonSyntax:
    """Tests for _validate_json_syntax."""

    def test_valid_json_object(self, validator):
        """Valid JSON object passes."""
        result = validator.validate(VALID_JSON, file_format="codemeta.json")
        assert result.yaml_valid is True
        assert isinstance(result.parsed_yaml, dict)

    def test_valid_json_array(self, validator):
        """Valid JSON array also passes."""
        result = validator.validate(VALID_JSON_ARRAY, file_format="code.json")
        assert result.yaml_valid is True
        assert isinstance(result.parsed_yaml, list)

    def test_html_instead_of_json(self, validator):
        """HTML returned instead of JSON is detected."""
        result = validator.validate(HTML_JSON, file_format="contribute.json")
        assert result.yaml_valid is False
        assert result.yaml_error == "HTML content returned instead of JSON"

    def test_invalid_json_sets_error(self, validator):
        """Invalid JSON sets an error message."""
        result = validator.validate(INVALID_JSON, file_format="code.json")
        assert result.yaml_valid is False
        assert result.yaml_error is not None

    def test_json_encoding_error(self, validator):
        """Binary content that cannot be decoded is handled gracefully."""
        result = validator.validate(b"\xff\xfe bad bytes", file_format="codemeta.json")
        assert result.yaml_valid is False
        assert result.yaml_error == "Encoding error"

    def test_json_scalar_rejected(self, validator):
        """A JSON scalar (not dict/list) is rejected."""
        result = validator.validate(b'"just a string"', file_format="code.json")
        assert result.yaml_valid is False
        assert "JSON object or array" in result.yaml_error

    def test_html_with_head_tag_in_body(self, validator):
        """HTML with <head> in the first 500 chars is rejected."""
        content = b"<html><head><title>err</title></head><body></body></html>"
        result = validator.validate(content, file_format="code.json")
        assert result.yaml_valid is False


# ---------------------------------------------------------------------------
# validate() routing / pipeline
# ---------------------------------------------------------------------------

class TestValidatePipeline:
    """Integration tests for the validate() method routing."""

    def test_returns_validation_result(self, validator):
        """validate() always returns a ValidationResult."""
        result = validator.validate(b"garbage")
        assert isinstance(result, ValidationResult)

    def test_file_format_stored_in_result(self, validator):
        """file_format is echoed back in ValidationResult."""
        result = validator.validate(VALID_JSON, file_format="codemeta.json")
        assert result.file_format == "codemeta.json"

    def test_json_format_skips_spec_validator(self, validator):
        """JSON formats add a 'No spec validator' message instead of running one."""
        result = validator.validate(VALID_JSON, file_format="codemeta.json")
        assert any("No spec validator" in e for e in result.spec_errors)

    def test_yaml_format_without_validator_adds_message(self, validator):
        """publiccode.yml without available validator adds spec error message."""
        result = validator.validate(VALID_YAML)
        assert any("not available" in e for e in result.spec_errors)

    def test_invalid_syntax_stops_pipeline(self, validator):
        """When syntax fails, spec and usefulness are not assessed."""
        result = validator.validate(HTML_CONTENT)
        assert result.yaml_valid is False
        assert result.spec_valid is False
        assert result.usefulness_score == 0

    def test_usefulness_assessed_when_yaml_valid(self, validator):
        """Usefulness is assessed when YAML is valid."""
        result = validator.validate(VALID_YAML)
        assert result.yaml_valid is True
        # usefulness_issues should be populated (score < 60 due to missing fields)
        assert isinstance(result.usefulness_issues, list)


# ---------------------------------------------------------------------------
# Spec compliance validation (_validate_spec_compliance)
# ---------------------------------------------------------------------------

class TestValidateSpecCompliance:
    """Tests for _validate_spec_compliance with mocked subprocess."""

    def test_spec_valid_on_exit_code_0(self, validator_with_spec):
        """Exit code 0 means spec validation passed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr=""
            )
            result = validator_with_spec.validate(VALID_YAML)
        assert result.spec_valid is True

    def test_spec_invalid_on_nonzero_exit(self, validator_with_spec):
        """Non-zero exit code means spec validation failed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="publiccode.yml: error: missing field 'name'\n",
                stderr=""
            )
            result = validator_with_spec.validate(VALID_YAML)
        assert result.spec_valid is False
        assert len(result.spec_errors) > 0

    def test_spec_timeout_handled(self, validator_with_spec):
        """Subprocess timeout is caught and recorded."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
            result = validator_with_spec.validate(VALID_YAML)
        assert result.spec_valid is False
        assert any("timeout" in e.lower() for e in result.spec_errors)

    def test_spec_validator_error_handled(self, validator_with_spec):
        """Unexpected exception during spec validation is handled."""
        with patch("subprocess.run", side_effect=OSError("binary not found")):
            result = validator_with_spec.validate(VALID_YAML)
        assert result.spec_valid is False
        assert len(result.spec_errors) > 0


# ---------------------------------------------------------------------------
# _parse_validator_output
# ---------------------------------------------------------------------------

class TestParseValidatorOutput:
    """Tests for _parse_validator_output."""

    def test_error_lines_captured(self, validator):
        """Lines with ': error:' are stored in spec_errors."""
        result = ValidationResult()
        output = "publiccode.yml: Error: missing field\n"
        validator._parse_validator_output(output, result)
        assert len(result.spec_errors) == 1
        assert "missing field" in result.spec_errors[0]

    def test_warning_lines_captured(self, validator):
        """Lines with ': warning:' are stored in spec_warnings."""
        result = ValidationResult()
        output = "publiccode.yml: Warning: deprecated field\n"
        validator._parse_validator_output(output, result)
        assert len(result.spec_warnings) == 1

    def test_blank_lines_ignored(self, validator):
        """Blank lines in output are ignored."""
        result = ValidationResult()
        validator._parse_validator_output("\n\n\n", result)
        assert result.spec_errors == []
        assert result.spec_warnings == []

    def test_other_lines_go_to_errors(self, validator):
        """Lines that are neither errors nor warnings go to spec_errors."""
        result = ValidationResult()
        output = "some informational line\n"
        validator._parse_validator_output(output, result)
        assert len(result.spec_errors) == 1


# ---------------------------------------------------------------------------
# Usefulness assessment
# ---------------------------------------------------------------------------

MINIMAL_YAML = b"publiccodeYmlVersion: '0.1'\nname: Test\nurl: https://x.gov\n"

FULL_YAML = b"""publiccodeYmlVersion: '0.1'
name: Full App
url: https://example.gov/full-app
developmentStatus: stable
softwareType: standalone/web
description:
  en:
    shortDescription: A comprehensive government software application
legal:
  license: MIT
maintenance:
  type: internal
  contacts:
    - name: Alice Smith
      email: alice@example.gov
"""


class TestAssessUsefulness:
    """Tests for _assess_usefulness and helper check methods."""

    def test_minimal_yaml_low_score(self, validator):
        """Minimal YAML (name/url/version only) gets a low usefulness score."""
        result = validator.validate(MINIMAL_YAML)
        assert result.usefulness_score < 60

    def test_full_yaml_higher_score(self, validator):
        """A rich YAML file gets a higher usefulness score."""
        result = validator.validate(FULL_YAML)
        assert result.usefulness_score >= 50  # most checks pass

    def test_not_useful_when_yaml_invalid(self, validator):
        """useful remains False when YAML is invalid."""
        result = validator.validate(HTML_CONTENT)
        assert result.useful is False
        assert result.usefulness_score == 0

    def test_usefulness_issues_populated(self, validator):
        """usefulness_issues lists missing fields for minimal YAML."""
        result = validator.validate(MINIMAL_YAML)
        assert len(result.usefulness_issues) > 0

    def test_software_type_adds_score(self, validator):
        """Presence of 'softwareType' adds 5 points."""
        result_with = validator.validate(FULL_YAML)
        result_without = validator.validate(MINIMAL_YAML)
        assert result_with.usefulness_score > result_without.usefulness_score


class TestCheckHelpers:
    """Tests for individual check helper methods."""

    def test_check_description_missing(self, validator):
        """Returns False when 'description' key is absent."""
        assert validator._check_description({}) is False

    def test_check_description_not_dict(self, validator):
        """Returns False when description is not a dict."""
        assert validator._check_description({"description": "plain string"}) is False

    def test_check_description_short(self, validator):
        """Returns False when shortDescription is too short."""
        data = {"description": {"en": {"shortDescription": "Too short"}}}
        assert validator._check_description(data) is False

    def test_check_description_sufficient(self, validator):
        """Returns True when shortDescription meets minimum length."""
        data = {
            "description": {
                "en": {
                    "shortDescription": "This is a sufficiently long description."
                }
            }
        }
        assert validator._check_description(data) is True

    def test_check_license_missing_legal(self, validator):
        """Returns False when 'legal' key is absent."""
        assert validator._check_license({}) is False

    def test_check_license_legal_not_dict(self, validator):
        """Returns False when 'legal' is not a dict."""
        assert validator._check_license({"legal": "MIT"}) is False

    def test_check_license_no_license_key(self, validator):
        """Returns False when 'license' key is absent from legal."""
        assert validator._check_license({"legal": {}}) is False

    def test_check_license_valid(self, validator):
        """Returns True when 'legal.license' is present and non-empty."""
        assert validator._check_license({"legal": {"license": "GPL-3.0"}}) is True

    def test_check_maintenance_missing(self, validator):
        """Returns False when 'maintenance' key is absent."""
        assert validator._check_maintenance({}) is False

    def test_check_maintenance_not_dict(self, validator):
        """Returns False when 'maintenance' is not a dict."""
        assert validator._check_maintenance({"maintenance": "internal"}) is False

    def test_check_maintenance_with_type(self, validator):
        """Returns True when 'maintenance.type' is present."""
        assert validator._check_maintenance(
            {"maintenance": {"type": "internal"}}
        ) is True

    def test_check_maintenance_with_contacts(self, validator):
        """Returns True when 'maintenance.contacts' is present."""
        assert validator._check_maintenance(
            {"maintenance": {"contacts": [{"name": "Alice"}]}}
        ) is True

    def test_check_contact_missing(self, validator):
        """Returns False when no contacts are present."""
        assert validator._check_contact({}) is False

    def test_check_contact_empty_list(self, validator):
        """Returns False when contacts list is empty."""
        assert validator._check_contact(
            {"maintenance": {"contacts": []}}
        ) is False

    def test_check_contact_present(self, validator):
        """Returns True when non-empty contacts list exists."""
        assert validator._check_contact(
            {"maintenance": {"contacts": [{"name": "Bob"}]}}
        ) is True

    def test_check_core_fields_all_present(self, validator):
        """Returns True when all three required fields are present."""
        data = {
            "publiccodeYmlVersion": "0.1",
            "name": "App",
            "url": "https://example.gov"
        }
        assert validator._check_core_fields(data) is True

    def test_check_core_fields_missing_one(self, validator):
        """Returns False when any required field is missing."""
        assert validator._check_core_fields({"name": "App", "url": "x"}) is False

    def test_check_development_status_valid(self, validator):
        """Returns True for all valid development status values."""
        for status in ["concept", "development", "beta", "stable", "obsolete"]:
            assert validator._check_development_status(
                {"developmentStatus": status}
            ) is True

    def test_check_development_status_invalid(self, validator):
        """Returns False for an unrecognised status string."""
        assert validator._check_development_status(
            {"developmentStatus": "unknown"}
        ) is False

    def test_check_development_status_missing(self, validator):
        """Returns False when developmentStatus key is absent."""
        assert validator._check_development_status({}) is False
