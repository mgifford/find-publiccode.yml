"""Validation module for publiccode.yml and other metadata files."""

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any

import yaml
import validators

import config

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a metadata file (publiccode.yml, codemeta.json, etc.)."""
    # File Format
    file_format: Optional[str] = None  # publiccode.yml, codemeta.json, code.json, contribute.json
    
    # Syntax Validation (YAML or JSON)
    yaml_valid: bool = False  # Note: also used for JSON validity
    yaml_error: Optional[str] = None  # Note: also used for JSON errors
    parsed_yaml: Optional[Dict] = None  # Note: also used for parsed JSON
    
    # Spec Compliance Validation
    spec_valid: bool = False
    spec_errors: List[str] = field(default_factory=list)
    spec_warnings: List[str] = field(default_factory=list)
    validator_output: Optional[str] = None
    validator_exit_code: Optional[int] = None
    
    # Usefulness Assessment
    useful: bool = False
    usefulness_score: int = 0  # 0-100
    usefulness_issues: List[str] = field(default_factory=list)
    
    # Metadata
    validation_timestamp: str = None
    
    def __post_init__(self):
        if self.validation_timestamp is None:
            self.validation_timestamp = datetime.utcnow().isoformat()


class PublicCodeValidator:
    """Validator for publiccode.yml files using multiple validation layers."""

    def __init__(self):
        """Initialize validator."""
        self.validator_available = self._check_validator()
        if not self.validator_available:
            logger.warning(
                f"publiccode-parser not found at {config.VALIDATOR_PATH}. "
                "Spec validation will be skipped. Install with: "
                "go install github.com/italia/publiccode-parser-go/v5/publiccode-parser@latest"
            )

    def _check_validator(self) -> bool:
        """Check if publiccode-parser is available."""
        if not os.path.exists(config.VALIDATOR_PATH):
            return False
        
        try:
            result = subprocess.run(
                [config.VALIDATOR_PATH, "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking validator: {e}")
            return False

    def validate(self, content: bytes, file_format: str = 'publiccode.yml', source_url: Optional[str] = None) -> ValidationResult:
        """
        Validate metadata file content through all validation layers.
        
        Args:
            content: Raw bytes of the metadata file
            file_format: File format (publiccode.yml, codemeta.json, code.json, contribute.json)
            
        Returns:
            ValidationResult with all validation outcomes
        """
        result = ValidationResult()
        result.file_format = file_format
        
        # Layer 1: Syntax Validation (YAML or JSON)
        if file_format == 'publiccode.yml':
            self._validate_yaml_syntax(content, result, source_url)
        else:  # JSON formats
            self._validate_json_syntax(content, result)
            
        if not result.yaml_valid:  # Note: yaml_valid used for all syntax validation
            return result  # Cannot proceed without valid syntax
        
        # Layer 2: Spec Compliance Validation
        if file_format == 'publiccode.yml' and self.validator_available:
            self._validate_spec_compliance(content, result)
        else:
            if file_format == 'publiccode.yml':
                result.spec_errors.append("Spec validator not available")
            else:
                result.spec_errors.append(f"No spec validator for {file_format}")
        
        # Layer 3: Usefulness Assessment
        self._assess_usefulness(result)
        
        return result

    def _validate_yaml_syntax(self, content: bytes, result: ValidationResult):
        """Validate YAML syntax."""
        try:
            # Decode content
            text = content.decode('utf-8')

            # Quick HTML/error heuristics using a small snippet
            snippet = text[:2048].lower()

            # If source URL suggests an error/document page, treat as HTML/error
            if source_url:
                url_lower = source_url.lower()
                if any(token in url_lower for token in ('errordocument', 'errordocument.php', '/error', '/err', '/inicio/errordocument', 'login', 'forbidden', 'unauthorized')):
                    result.yaml_error = f"Source URL indicates an error/landing page: {source_url}"
                    logger.debug("Source URL indicates an error/landing page")
                    return

            # Detect HTML structures in the text snippet
            if self._looks_like_html(snippet):
                result.yaml_error = "HTML content returned instead of YAML"
                logger.debug("Detected HTML content instead of YAML")
                return
            
            # Parse YAML
            parsed = yaml.safe_load(text)
            
            if not isinstance(parsed, dict):
                result.yaml_error = "Not a valid YAML dictionary"
                return
            
            result.yaml_valid = True
            result.parsed_yaml = parsed
            logger.debug("YAML syntax validation passed")
            
        except UnicodeDecodeError as e:
            result.yaml_error = "Encoding error"
            logger.warning(f"Unicode error: {e}")
            
        except yaml.YAMLError as e:
            # Truncate long error messages
            error_msg = str(e)
            if len(error_msg) > 100:
                result.yaml_error = "YAML syntax error"
            else:
                result.yaml_error = f"YAML error: {error_msg}"
            logger.warning(f"YAML error: {e}")
            
        except Exception as e:
            result.yaml_error = "Validation error"
            logger.error(f"Unexpected YAML validation error: {e}")

    def _validate_json_syntax(self, content: bytes, result: ValidationResult):
        """Validate JSON syntax."""
        try:
            # Decode content
            text = content.decode('utf-8')
            
            # Check if content is HTML (common mistake)
            text_lower = text.lower().strip()
            if text_lower.startswith('<!doctype html') or text_lower.startswith('<html') or '<head>' in text_lower[:500]:
                result.yaml_error = "HTML content returned instead of JSON"
                logger.debug("Detected HTML content instead of JSON")
                return
            
            # Parse JSON
            parsed = json.loads(text)
            
            if not isinstance(parsed, (dict, list)):
                result.yaml_error = "Not a valid JSON object or array"
                return
            
            result.yaml_valid = True  # Using yaml_valid for all syntax validation
            result.parsed_yaml = parsed  # Using parsed_yaml for all parsed content
            logger.debug("JSON syntax validation passed")
            
        except UnicodeDecodeError as e:
            result.yaml_error = "Encoding error"
            logger.warning(f"Unicode error: {e}")
            
        except json.JSONDecodeError as e:
            # Truncate long error messages
            error_msg = str(e)
            if len(error_msg) > 100:
                result.yaml_error = "JSON syntax error"
            else:
                result.yaml_error = f"JSON error: {error_msg}"
            logger.warning(f"JSON error: {e}")
            
        except Exception as e:
            result.yaml_error = "Validation error"
            logger.error(f"Unexpected JSON validation error: {e}")

    def _validate_spec_compliance(self, content: bytes, result: ValidationResult):
        """Validate against publiccode.yml specification using official parser."""
        try:
            # Write content to temporary file
            with tempfile.NamedTemporaryFile(
                mode='wb',
                suffix='.yml',
                delete=False
            ) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            try:
                # Run validator
                proc = subprocess.run(
                    [config.VALIDATOR_PATH, tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=config.VALIDATOR_TIMEOUT
                )
                
                result.validator_exit_code = proc.returncode
                result.validator_output = proc.stdout + proc.stderr
                
                # Exit code 0 means validation passed
                if proc.returncode == 0:
                    result.spec_valid = True
                    logger.debug("Spec validation passed")
                else:
                    result.spec_valid = False
                    # Parse errors and warnings from output
                    self._parse_validator_output(result.validator_output, result)
                    logger.debug(f"Spec validation failed: {len(result.spec_errors)} errors")
                    
            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                    
        except subprocess.TimeoutExpired:
            result.spec_errors.append("Validator timeout")
            logger.warning("Validator timeout")
            
        except Exception as e:
            result.spec_errors.append(f"Validator error: {str(e)}")
            logger.error(f"Spec validation error: {e}")

    def _parse_validator_output(self, output: str, result: ValidationResult):
        """Parse publiccode-parser output to extract errors and warnings."""
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if ': error:' in line.lower():
                result.spec_errors.append(line)
            elif ': warning:' in line.lower():
                result.spec_warnings.append(line)
            elif line:  # Other output
                result.spec_errors.append(line)

    def _assess_usefulness(self, result: ValidationResult):
        """Assess the practical usefulness of the publiccode.yml file."""
        if not result.yaml_valid or not result.parsed_yaml:
            return
        
        score = 0
        max_score = 100
        issues = []
        
        data = result.parsed_yaml
        
        # Check 1: Has meaningful description (20 points)
        if self._check_description(data):
            score += 20
        else:
            issues.append("Missing or insufficient description")
        
        # Check 2: Has valid license (20 points)
        if config.USEFULNESS_CHECKS.get("has_valid_license") and self._check_license(data):
            score += 20
        else:
            issues.append("Missing or invalid license information")
        
        # Check 3: Has maintenance information (15 points)
        if config.USEFULNESS_CHECKS.get("has_maintenance_info") and self._check_maintenance(data):
            score += 15
        else:
            issues.append("Missing maintenance information")
        
        # Check 4: Has contact information (15 points)
        if config.USEFULNESS_CHECKS.get("has_contact") and self._check_contact(data):
            score += 15
        else:
            issues.append("Missing contact information")
        
        # Check 5: Has required core fields (15 points)
        if self._check_core_fields(data):
            score += 15
        else:
            issues.append("Missing required core fields")
        
        # Check 6: Has development status (10 points)
        if self._check_development_status(data):
            score += 10
        else:
            issues.append("Missing or invalid development status")
        
        # Check 7: Has software type (5 points)
        if 'softwareType' in data:
            score += 5
        else:
            issues.append("Missing software type")
        
        result.usefulness_score = score
        result.usefulness_issues = issues
        
        # Consider "useful" if score >= 60 and spec is valid
        result.useful = (score >= 60 and result.spec_valid)
        
        logger.debug(f"Usefulness score: {score}/100")

    def _looks_like_html(self, snippet: str) -> bool:
        """Heuristic to detect HTML or error pages from a text snippet."""
        if not snippet:
            return False

        s = snippet.strip()
        if s.startswith('<!doctype') or s.startswith('<html'):
            return True

        # Presence of HTML tags early in the document
        if '<html' in s or '<head' in s or '<body' in s or '<!doctype' in s or '<script' in s:
            return True

        # CMS/error keywords that often indicate HTML landing pages
        keywords = ['404', 'not found', 'error', 'forbidden', 'unauthorized', 'login', 'index of', '<title>error', 'php']
        matches = sum(1 for kw in keywords if kw in s)
        if matches >= 2:
            return True

        # Many angle brackets -> likely HTML
        if s.count('<') > 5 and s.count('>') > 5:
            return True

        return False

    def _check_description(self, data: Dict) -> bool:
        """Check for meaningful description."""
        if 'description' not in data:
            return False
        
        desc = data['description']
        if not isinstance(desc, dict):
            return False
        
        # Check at least one language has substantial description
        min_length = config.USEFULNESS_CHECKS.get("description_min_length", 20)
        for lang, lang_data in desc.items():
            if isinstance(lang_data, dict):
                short_desc = lang_data.get('shortDescription', '')
                if len(short_desc) >= min_length:
                    return True
        
        return False

    def _check_license(self, data: Dict) -> bool:
        """Check for valid license information."""
        if 'legal' not in data:
            return False
        
        legal = data['legal']
        if not isinstance(legal, dict):
            return False
        
        return 'license' in legal and legal['license']

    def _check_maintenance(self, data: Dict) -> bool:
        """Check for maintenance information."""
        if 'maintenance' not in data:
            return False
        
        maint = data['maintenance']
        if not isinstance(maint, dict):
            return False
        
        return 'type' in maint or 'contacts' in maint

    def _check_contact(self, data: Dict) -> bool:
        """Check for contact information."""
        # Check maintenance contacts
        if 'maintenance' in data and isinstance(data['maintenance'], dict):
            maint = data['maintenance']
            if 'contacts' in maint and maint['contacts']:
                return True
        
        return False

    def _check_core_fields(self, data: Dict) -> bool:
        """Check for required core fields."""
        required = ['publiccodeYmlVersion', 'name', 'url']
        return all(field in data for field in required)

    def _check_development_status(self, data: Dict) -> bool:
        """Check for valid development status."""
        valid_statuses = ['concept', 'development', 'beta', 'stable', 'obsolete']
        status = data.get('developmentStatus', '')
        return status in valid_statuses
