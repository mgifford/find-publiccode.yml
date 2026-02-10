# AGENTS.md Compliance Review

**Review Date:** 2026-02-09  
**Framework Version:** 1.0

## Compliance Status: ✅ COMPLIANT

This framework has been reviewed against all requirements in AGENTS.md.

## Discovery Rules Compliance

✅ **Path Testing**
- Tests exactly: `/publiccode.yml`, `/.well-known/publiccode.yml`, `/publiccode.yaml`, `/.well-known/publiccode.yaml`
- Implementation: `config.py:PATHS_TO_TEST`

✅ **Protocol Handling**
- HTTPS first, HTTP fallback
- Implementation: `crawler.py:PublicCodeCrawler.discover()`

✅ **Redirects**
- Follows redirects, records chain
- Implementation: `crawler.py:_fetch_url()` with `allow_redirects=True`

✅ **Timeouts**
- Strict timeout: 10 seconds
- Implementation: `config.py:REQUEST_TIMEOUT`

✅ **Size Limits**
- Aborts downloads >512KB
- Implementation: `config.py:MAX_FILE_SIZE` and `crawler.py:_fetch_url()`

✅ **User-Agent**
- Clear, honest identification with contact reference
- Implementation: `config.py:USER_AGENT` = "PublicCode-Research-Bot/1.0 (+https://github.com/publiccodeyml/publiccode.yml; contact: github.com/mgifford)"

✅ **Recording Requirements**
- Records: URL, final URL, HTTP status, redirects, failure categories
- Implementation: `crawler.py:DiscoveryResult` dataclass

## Validation Requirements Compliance

✅ **YAML Syntax Validation**
- Uses strict parser: PyYAML with `safe_load()`
- Records parse failures verbatim
- Blocks semantic validation on parse failure
- Implementation: `validator.py:_validate_yaml_syntax()`

✅ **Spec Compliance Validation**
- Uses authoritative validator: `publiccode-parser-go` v5
- Preserves all errors and warnings
- Treats spec drift as failure
- Implementation: `validator.py:_validate_spec_compliance()`

✅ **Usefulness Assessment**
- Separate layer after technical validation
- Explicit criteria in config
- Does not override validity
- Implementation: `validator.py:_assess_usefulness()`

## Output Requirements Compliance

✅ **Structured Dataset**
- Produces CSV and JSON
- Implementation: `results.py:save_csv()`, `save_json()`

✅ **One Record Per Domain**
- Enforced by design
- Implementation: `results.py:add_result()`

✅ **Required Fields**
- Domain ✓
- Discovered file URL ✓
- HTTP outcome ✓
- YAML validity ✓
- Specification validity ✓
- Usefulness classification ✓
- Error summaries ✓
- Implementation: See `results.py:add_result()` field mapping

✅ **Preserve Failures**
- All negative results retained
- No filtering of failed discoveries
- Implementation: All outcomes recorded in `results.results[]`

## Interpretation Rules Compliance

✅ **No Unsubstantiated Claims**
- Report explicitly states: "This analysis only checks website root paths, not repository-level adoption"
- Implementation: `results.py:generate_report()` Limitations section

✅ **Separate Measurement from Interpretation**
- Raw data in CSV
- Interpretation in separate report
- Clear distinction maintained

✅ **Flag Ambiguity**
- Multiple outcome categories (not_found, timeout, error, etc.)
- Explicit error messages recorded

## Operational Constraints Compliance

✅ **Conservative Concurrency**
- Default: 10 workers (configurable)
- Rate limiting: 0.1s delay between requests to same domain
- Implementation: `config.py:MAX_CONCURRENT_REQUESTS`, `RATE_LIMIT_DELAY`

✅ **Avoid Stressing Systems**
- Timeouts prevent hanging
- Size limits prevent large downloads
- Clear User-Agent allows blocking if needed

✅ **Reproducibility**
- All configuration documented
- Timestamps recorded
- Deterministic processing

✅ **Checkpoint/Resume**
- Saves state every 100 domains
- Resume capability
- Reports partial results
- Implementation: `main.py:--resume`, `results.py:save_checkpoint()`

## Human Oversight Compliance

✅ **Review Before Publication**
- Framework generates data for review
- Explicit report includes limitations
- No automatic publication

## Change Control Compliance

✅ **Documented Configuration**
- All criteria in `config.py`
- Changes version-controlled
- Clear documentation in README.md

## Non-Goals Adherence

✅ Framework does NOT:
- Enforce compliance
- Rank governments  
- Promote specific tooling
- Substitute for official inventories

✅ Framework DOES:
- Measure observable behavior
- Produce verifiable data
- State limitations explicitly

## Accountability

- **Human Maintainer:** Mike Gifford (github.com/mgifford)
- **Contact Reference:** Included in User-Agent string
- **Repository:** Attributable to maintainer
- **Logs:** All actions logged with timestamps

## Summary

This framework fully complies with AGENTS.md requirements. All discovery rules, validation requirements, output specifications, interpretation guidelines, and operational constraints are implemented as specified.

The framework is designed for measurement, not advocacy, and explicitly separates observable facts from interpretation.
