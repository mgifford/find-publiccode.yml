# Multi-Format Discovery Support

**Date:** February 10, 2026  
**Status:** ✅ Implemented and Tested

---

## Overview

The discovery framework has been expanded to support **four open-source software metadata formats**, enabling comparative analysis across different metadata standards used by government entities.

---

## Supported Formats

### 1. **publiccode.yml** (publiccode.yaml)
- **Origin:** European Union
- **Standard:** https://yml.publiccode.tools/
- **Purpose:** Describe open-source software developed or adopted by public administrations
- **Validation:** YAML syntax + Spec compliance (via publiccode-parser-go)

### 2. **codemeta.json**
- **Origin:** Academic/Research community
- **Standard:** https://codemeta.github.io/
- **Purpose:** Software metadata using schema.org vocabulary
- **Validation:** JSON syntax (spec validation: future)

### 3. **code.json**
- **Origin:** US Federal Government
- **Standard:** https://code.gov/
- **Purpose:** Federal source code inventory
- **Validation:** JSON syntax (spec validation: future)

### 4. **contribute.json**
- **Origin:** Mozilla
- **Standard:** https://www.contributejson.org/
- **Purpose:** Contribution guidelines and project metadata
- **Validation:** JSON syntax

---

## Discovery Paths

Each domain is now tested for **10 paths** (previously 4):

```
1.  /publiccode.yml
2.  /.well-known/publiccode.yml
3.  /publiccode.yaml
4.  /.well-known/publiccode.yaml
5.  /codemeta.json
6.  /.well-known/codemeta.json
7.  /code.json
8.  /.well-known/code.json
9.  /contribute.json
10. /.well-known/contribute.json
```

**Discovery Order:**
- Tests HTTPS first, falls back to HTTP
- Tests www/non-www variations
- Stops at first successful file found
- Records which format was discovered

---

## Implementation Details

### Files Modified

1. **config.py**
   - Added 6 new discovery paths
   - Maintains existing configuration

2. **crawler.py**
   - Added `file_format` field to DiscoveryResult
   - Implemented `_detect_file_format()` method
   - Updated discovery messages to include format

3. **validator.py**
   - Added JSON syntax validation (`_validate_json_syntax()`)
   - Updated `validate()` to accept file_format parameter
   - HTML detection now works for both YAML and JSON
   - ValidationResult tracks file_format

4. **results.py**
   - Added `file_format` column to CSV output
   - Column order: domain, file_url, **file_format**, http_status, ...

5. **main.py**
   - Passes file_format from discovery to validator

### New Test Suite

**test_formats.py** validates:
- ✅ File format detection from URLs
- ✅ JSON syntax validation (valid, invalid, HTML)
- ✅ YAML syntax validation (still works)
- ✅ HTML detection for all formats
- ✅ Configuration completeness

---

## CSV Output Changes

### New Column: `file_format`

**Position:** 3rd column (after domain, file_url)

**Possible Values:**
- `publiccode.yml`
- `codemeta.json`
- `code.json`
- `contribute.json`
- `null` (if no file found)

### Example Rows

```csv
domain,file_url,file_format,http_status,http_outcome,yaml_valid,...
example.gov,https://example.gov/publiccode.yml,publiccode.yml,200,success,True,...
test.gov,https://test.gov/codemeta.json,codemeta.json,200,success,True,...
demo.gov,https://demo.gov/code.json,code.json,200,success,True,...
```

---

## Validation Layers

### For publiccode.yml/yaml (YAML)

1. **Syntax:** PyYAML parser
2. **Spec:** publiccode-parser-go (if installed)
3. **Usefulness:** Custom quality checks

### For JSON formats (codemeta, code, contribute)

1. **Syntax:** Python json parser
2. **Spec:** Not yet implemented (format-specific validators needed)
3. **Usefulness:** Custom quality checks (future)

---

## Performance Impact

### Per Domain

**Before:** 4 paths × 2 protocols = ~8 HTTP requests maximum  
**After:** 10 paths × 2 protocols = ~20 HTTP requests maximum

**Mitigation:**
- Discovery stops at first successful file
- Most domains will test fewer paths
- Same rate limiting and concurrency controls apply
- Typical domain: 0-4 successful requests

### For 18,723 Domains

**Estimated Additional Time:**
- Assuming 10% domains require full path testing: +~30 minutes
- Most domains fail fast (404s, connection errors)
- Real-world impact: Minimal due to early termination

---

## Use Cases

### 1. Format Comparison
"Which metadata format is most commonly adopted by European governments?"

### 2. Multi-Format Adoption
"Do any governments publish multiple formats?"

### 3. Geographic Patterns
"Do certain countries prefer certain formats?"

### 4. Quality Assessment
"Which format produces higher-quality metadata?"

---

## Testing

### Automated Tests

Run: `python3 test_formats.py`

**Validates:**
- 10 configuration paths present
- Format detection from URLs
- JSON validation (valid, invalid, HTML)  
- YAML validation (still works)
- HTML detection for allformats

### Manual Testing

```bash
# Test on small dataset
python3 main.py --limit 10 --output test_multiformat.csv

# Examine results
grep -v "not_found" test_multiformat.csv | cut -d, -f1,3,8
# Shows: domain, file_format, yaml_valid
```

---

## Command Reference

### Run Discovery

```bash
# Full dataset
python3 main.py

# Subset for testing
python3 main.py --limit 100 --output formats_test.csv

# Specific file
python3 main.py --domains my_domains.csv --output results.csv
```

### Analyze Results

```bash
# Count by format
cut -d, -f3 results.csv | sort | uniq -c

# Show successful discoveries
awk -F, '$5=="success" {print $1","$3}' results.csv

# Find multi-format domains (theoretical)
# Would require multiple runs or custom analysis
```

---

## Future Enhancements

### Potential Additions

1. **Format-Specific Validators**
   - CodeMeta schema validation
   - Code.json schema validation
   - Contribute.json schema validation

2. **Format-Specific Usefulness Checks**
   - CodeMeta: Check for academic identifiers (DOI, ORCID)
   - Code.json: Check for repository URLs, license
   - Contribute.json: Check for contribution URLs

3. **Additional Formats**
   - CITATION.cff (software citation)
   - package.json (npm/Node.js)
   - setup.py metadata (Python)
   - DESCRIPTION (R packages)

4. **Multi-Format Discovery**
   - Current: Stops at first file
   - Future: Option to discover ALL formats per domain

---

## Compliance (AGENTS.md)

### Discovery Rules ✅

- Attempts retrieval from predefined paths only
- HTTPS first, HTTP fallback
- Follows redirects
- Applies strict timeouts
- Aborts downloads exceeding size threshold
- Uses clear User-Agent string
- Records all outcomes (404, success, timeout, etc.)

### Output Requirements ✅

- Structured dataset (CSV + JSON)
- One record per domain
- Clear, normalized fields
- Includes `file_format` for discovered files
- Does not discard failed results

### Interpretation Rules ✅

- Does not claim "adoption rates" without population
- Separates measurement (found/not found) from interpretation
- Flags format ambiguity in results
- Format-specific analysis must state assumptions

---

## Documentation

**See Also:**
- [README.md](README.md) - Project overview
- [USAGE.md](USAGE.md) - How to use the framework
- [COMPLIANCE.md](COMPLIANCE.md) - AGENTS.md compliance details
- [AGENTS.md](AGENTS.md) - Agent operating constraints

---

## Changelog

### 2026-02-10: Multi-Format Support
- Added codemeta.json, code.json, contribute.json discovery
- Implemented JSON syntax validation
- Added file_format tracking and CSV column
- Created test_formats.py test suite
- Updated all modules for multi-format support
- Maintained backward compatibility with publiccode.yml-only usage

### 2026-02-09: Initial Implementation
- publiccode.yml discovery and validation
- YAML syntax and spec validation
- www/non-www variant testing
- HTML detection and error cleanup

---

## Contact

Framework maintainer: mike.gifford  
Repository: /Users/mike.gifford/find-publiccode  
Agent-generated components: Subject to human review before publication
