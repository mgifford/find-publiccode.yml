# PublicCode.yml Discovery Framework - Usage Guide

## Overview

This framework provides a rigorous, reproducible method for discovering and validating `publiccode.yml` files across government domains. It follows strict measurement principles and produces auditable results.

## Quick Start

### 1. Setup

```bash
# Run the setup script
./setup.sh

# Activate the virtual environment
source venv/bin/activate
```

### 2. Test Run (Recommended First)

Test with a small sample before processing all domains:

```bash
python3 main.py --limit 10 --output test_results.csv --verbose
```

### 3. Full Analysis

Process all ~18,700 domains:

```bash
python3 main.py --input eu_gov_domains.csv --output results.csv
```

**Estimated time:** 4-6 hours (depends on network speed and server response times)

## Command-Line Options

### Basic Options

- `--input FILE` - Input CSV with `gov_domain` column (default: `eu_gov_domains.csv`)
- `--output FILE` - Output CSV file (default: `results.csv`)
- `--output-json FILE` - Optional JSON output with full details

### Execution Control

- `--limit N` - Process only first N domains (for testing)
- `--workers N` - Concurrent workers (default: 10)
- `--resume` - Resume from checkpoint file
- `--checkpoint-interval N` - Save checkpoint every N domains (default: 100)

### Logging

- `--verbose` - Enable debug logging
- `--log-file FILE` - Save logs to file

### Examples

```bash
# Small test run
python3 main.py --limit 5 --output test.csv

# Full run with JSON output
python3 main.py --output results.csv --output-json results.json

# Resume interrupted run
python3 main.py --output results.csv --resume

# Custom concurrency
python3 main.py --workers 20 --output results.csv

# Verbose logging to file
python3 main.py --verbose --log-file discovery.log --output results.csv
```

## Understanding Results

### CSV Output Columns

| Column | Description |
|--------|-------------|
| `domain` | Government domain tested |
| `file_url` | URL where file was found (if any) |
| `http_status` | HTTP response code (200, 404, etc.) |
| `http_outcome` | Outcome category: success, not_found, timeout, error, etc. |
| `final_url` | Final URL after redirects |
| `redirect_chain` | List of redirect URLs |
| `response_time_ms` | Response time in milliseconds |
| `yaml_valid` | Boolean - valid YAML syntax |
| `yaml_error` | YAML parse error message |
| `spec_valid` | Boolean - spec-compliant |
| `spec_errors` | Validation errors from publiccode-parser |
| `spec_warnings` | Validation warnings |
| `validator_exit_code` | Exit code from validator |
| `useful` | Boolean - high quality (>= 60% score) |
| `usefulness_score` | Quality score 0-100 |
| `usefulness_issues` | List of quality issues |
| `error_message` | Discovery error message |
| `discovery_timestamp` | ISO 8601 timestamp |
| `validation_timestamp` | ISO 8601 timestamp |

### Outcome Categories

**HTTP Outcomes:**
- `success` - File found and downloaded
- `not_found` - No file at any tested path
- `timeout` - Request timed out
- `error` - HTTP error (4xx, 5xx)
- `ssl_error` - SSL/TLS error
- `connection_error` - Connection failed
- `size_exceeded` - File too large (>512KB)
- `redirect` - Found after redirects

### Validation Layers

**Layer 1: YAML Syntax**
- Tests if file is valid YAML
- Tests if parsed structure is a dictionary

**Layer 2: Spec Compliance**
- Uses official `publiccode-parser-go` validator
- Checks conformance with publiccode.yml v0.5.0 standard
- Records all errors and warnings

**Layer 3: Usefulness Assessment**
- Checks for meaningful description (20 points)
- Validates license information (20 points)
- Checks maintenance info (15 points)
- Checks contact information (15 points)
- Validates required core fields (15 points)
- Checks development status (10 points)
- Checks software type (5 points)

**Total Score:** 100 points
**Useful Threshold:** >= 60 points AND spec-valid

## Analysis Report

The framework automatically generates `ANALYSIS_REPORT.md` with:
- Executive summary statistics
- Methodology description
- Key findings
- Discovery and quality rates
- Explicit limitations
- Reproducibility notes

## Resume Capability

The framework saves checkpoints every 100 domains (configurable). If interrupted:

```bash
python3 main.py --output results.csv --resume
```

Checkpoint file: `checkpoint.json`

## Optional: Install publiccode-parser

For full spec validation, install the official Go validator:

```bash
# Install Go (if not already installed)
brew install go  # macOS
# or download from https://go.dev/dl/

# Install publiccode-parser
go install github.com/italia/publiccode-parser-go/v5/publiccode-parser@latest

# Add to PATH (add to ~/.zshrc or ~/.bash_profile)
export PATH=$PATH:$HOME/go/bin

# Verify installation
publiccode-parser --version
```

Without the validator, the framework will still run but spec validation will be skipped.

## Performance Considerations

### Recommended Settings

For ~18,700 domains:
- **Workers:** 10 (default)
- **Expected time:** 4-6 hours
- **Network:** Required throughout
- **Storage:** ~10MB for results

### Adjusting Concurrency

**Lower concurrency (--workers 5):**
- More polite to servers
- Slower execution
- Recommended for very large datasets

**Higher concurrency (--workers 20):**
- Faster execution
- More network load
- May trigger rate limits on some servers

## Ethical Considerations

This framework is designed for research, not bulk harvesting:

- ✅ Clear User-Agent identifying the research purpose
- ✅ Respectful rate limiting
- ✅ Timeouts prevent hanging on slow servers
- ✅ Size limits prevent accidental large downloads
- ✅ Only tests specific documented paths
- ✅ No recursive crawling
- ✅ No credential harvesting

## Interpreting Results

### What Results Mean

✅ **File discovered and valid:** Domain publishes spec-compliant metadata
✅ **File discovered but invalid:** Domain attempts publiccode.yml but has errors
✅ **File not found:** No publiccode.yml at website root (does NOT mean no adoption)

### What Results DON'T Mean

❌ **Absence proves non-adoption** - Many projects have publiccode.yml in repositories, not on websites
❌ **Discovery rate = adoption rate** - This measures website publication, not overall usage
❌ **Quality score is objective** - Usefulness assessment uses configurable heuristics

## Configuration

Edit `config.py` to customize:

- Paths to test
- Timeout values
- Size limits
- Concurrency settings
- Usefulness criteria
- User-Agent string

## Troubleshooting

### "publiccode-parser not found"
The Go validator is optional. Install it for spec validation or continue without it.

### "Connection errors"
Normal - some domains may be offline or block automated requests.

### Slow execution
- Reduce `--workers`
- Check network connection
- Some domains have slow response times

### Out of memory
Unlikely with default settings. Reduce `--checkpoint-interval` if needed.

## Citation

When using this framework for research or publication, please cite:

- PublicCode.yml Standard: https://yml.publiccode.tools/
- Framework: [Your research details]

Include the full methodology and explicitly state limitations.

## Support

For issues or questions:
- Framework: Create an issue in your project repository
- PublicCode.yml specification: https://github.com/publiccodeyml/publiccode.yml
- Official validator: https://github.com/italia/publiccode-parser-go

## License

This framework is provided for research purposes. Respect the publiccode.yml standard's CC0-1.0 license.
