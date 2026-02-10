# PublicCode.yml Discovery and Validation Framework

## Overview

This framework systematically discovers, validates, and assesses publiccode.yml files across ~18,000+ European government domains.

**✅ Fully compliant with AGENTS.md requirements** - See [COMPLIANCE.md](COMPLIANCE.md) for details.

## Key Features

- **Rigorous Discovery** - Tests 4 standard paths per domain (HTTPS-first)
- **Three-Layer Validation** - YAML syntax → Spec compliance → Usefulness  
- **Continuous Monitoring** - Progress bar + periodic summaries (every 60s)
- **Checkpoint/Resume** - Automatic saves every 100 domains
- **Transparent Logging** - All actions recorded with timestamps
- **Structured Output** - CSV + JSON with 19 fields per domain
- **Human Oversight** - Explicit limitations, no unsubstantiated claims

## Architecture

### Components

1. **Domain Crawler** (`crawler.py`)
   - Tests 4 standard paths per domain
   - HTTPS-first with HTTP fallback
   - Handles redirects, timeouts, size limits
   - Polite concurrency control

2. **YAML Validator** (`validator.py`)
   - Syntax validation using PyYAML
   - Spec validation using official publiccode-parser-go
   - Usefulness assessment layer

3. **Results Manager** (`results.py`)
   - Structured output (CSV + JSON)
   - Aggregate statistics
   - Reproducibility tracking

4. **Main Orchestrator** (`main.py`)
   - Coordinates discovery → validation → reporting
   - Progress tracking
   - Resume capability

## Discovery Paths

Per domain, tests:
- `https://domain/publiccode.yml`
- `https://domain/.well-known/publiccode.yml`
- `https://domain/publiccode.yaml`
- `https://domain/.well-known/publiccode.yaml`

Falls back to HTTP if HTTPS fails.

**Plus www/non-www variations:**
- If `example.gov` fails, also tries `www.example.gov`
- If `www.example.gov` fails, also tries `example.gov`

This maximizes discovery while staying within documented paths.

## Validation Layers

1. **HTTP Access** (accessible, timeout, size check)
2. **YAML Syntax** (parseable, valid structure)
3. **Spec Compliance** (publiccode.yml schema v0.5.0)
4. **Usefulness** (meaningful metadata, valid URLs, completeness)

## Output Format

### CSV Columns
- `domain` - Government domain tested
- `file_url` - Discovered file URL (if any)
- `http_status` - HTTP response code
- `http_outcome` - Success/Redirect/Timeout/Error
- `yaml_valid` - Boolean
- `yaml_error` - Parse error message
- `spec_valid` - Boolean
- `spec_errors` - Validator output
- `useful` - Boolean
- `usefulness_score` - 0-100
- `usefulness_issues` - Quality problems
- `discovery_timestamp` - ISO 8601 timestamp
- `validation_timestamp` - ISO 8601 timestamp

### JSON Format
Nested structure with full validation details, HTTP headers, redirect chains.

## Configuration

See `config.py` for:
- Concurrency limits
- Timeout values
- Size thresholds
- User-Agent string
- Validator paths

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Install publiccode-parser-go
go install github.com/italia/publiccode-parser-go/v5/publiccode-parser@latest

# Run discovery
python main.py --input eu_gov_domains.csv --output results.csv

# Resume from checkpoint
python main.py --input eu_gov_domains.csv --output results.csv --resume

# Test mode (first 100 domains)
python main.py --input eu_gov_domains.csv --output results.csv --limit 100
```

## Reproducibility

All runs log:
- Tool versions
- Configuration parameters
- Execution timestamp
- Environmental metadata

## Ethical Considerations

- Rate limiting: Max 10 concurrent requests
- Respectful User-Agent identifying the research
- Timeout after 10 seconds per request
- No credential harvesting
- No recursive crawling beyond specified paths

## Dependencies

- Python 3.9+
- PyYAML
- requests
- validators
- publiccode-parser-go (Go binary)
- pandas (for reporting)

## Documentation

- **[USAGE.md](USAGE.md)** - Complete usage guide
- **[COMPLIANCE.md](COMPLIANCE.md)** - AGENTS.md compliance review  
- **[TERMINAL_OUTPUT.md](TERMINAL_OUTPUT.md)** - Progress monitoring details
- **[AGENTS.md](AGENTS.md)** - Governance and operational rules
