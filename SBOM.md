# SBOM (Software Bill of Materials)

This document tracks software used by this repository to support legal and
security risk management through version and license visibility.

## Inventory

| Component | Type | Version / Constraint | Source | License (to verify) | Notes |
| --- | --- | --- | --- | --- | --- |
| Python | Runtime | `>=3.9` | `pyproject.toml` | Python Software Foundation License | Required runtime |
| uv | Package / env manager | tool (`uv`) | `setup.sh`, local tooling | MIT | Used for dependency sync and command execution |
| requests | Python dependency | `>=2.31.0` | `pyproject.toml` | Apache-2.0 | HTTP client |
| PyYAML | Python dependency | `>=6.0` | `pyproject.toml` | MIT | YAML parsing |
| validators | Python dependency | `>=0.22.0` | `pyproject.toml` | MIT | URL and value validation |
| pandas | Python dependency | `>=2.2.0` | `pyproject.toml` | BSD-3-Clause | Reporting/data handling |
| tqdm | Python dependency | `>=4.66.0` | `pyproject.toml` | MPL-2.0 / MIT | Progress display |
| flake8 | Dev dependency | `>=7.0.0` | `pyproject.toml` | MIT | Linting |
| pytest | Dev dependency | `>=8.0.0` | `pyproject.toml` | MIT | Testing |
| Go | Runtime for validator | required in setup | `setup.sh` | BSD-3-Clause | Required for publiccode parser |
| publiccode-parser-go | External validator | `v5` (`@latest` in setup) | `setup.sh` | AGPL-3.0 (upstream) | Specification validation |

## Version Control and Update Tracking

- Python dependencies are declared in `pyproject.toml` and locked in
  `uv.lock`.
- Dependency updates should be done with `uv` and reflected in both files.
- Tooling/runtime updates (Python, Go, `publiccode-parser-go`) should be logged
  in pull requests with rationale and impact.
- Security-sensitive updates should include a short risk note in PR
  descriptions.

## License Tracking Process

- Confirm license metadata for each dependency at upgrade time.
- Record any license changes in this file in the same PR as the version change.
- Flag copyleft or license-incompatible additions for human review before merge.
- Keep this file aligned with `pyproject.toml`, `uv.lock`, and `setup.sh`.

## Review Cadence

- Review and refresh this SBOM during dependency update PRs.
- Perform a full SBOM review at least quarterly.
