# AGENTS.md

## Purpose

This repository is operated with the assistance of agentic large language models.  
Agents are used **only** to support discovery, validation, analysis, and reporting related to `publiccode.yml` files published by government entities.

Agents do not make policy decisions.  
Agents do not publish findings without human review.

---

## Scope of Agent Authority

Agents are permitted to:

- Discover candidate `publiccode.yml` files on government web domains
- Validate discovered files for:
  - YAML syntax correctness
  - Conformance with the publiccode.yml specification
  - Basic metadata quality and usefulness
- Produce structured, machine-readable reports
- Summarize findings and failure modes

Agents are **not** permitted to:

- Modify or submit `publiccode.yml` files on behalf of third parties
- Make claims about adoption without explicit population definitions
- Infer repository practices from website-level absence
- Execute destructive actions
- Publish or disseminate results without review

---

## Definitions

- **Discovery**  
  The process of attempting to retrieve `publiccode.yml` files from predefined URL paths on known domains.

- **Validation**  
  The process of verifying that a retrieved file:
  1. Parses as valid YAML
  2. Conforms to the publiccode.yml specification
  3. Contains minimally useful metadata

- **Usefulness**  
  A qualitative assessment applied *after* technical validation, based on explicit criteria defined in this repository.

---

## Discovery Rules

Agents must only attempt retrieval from the following paths:

- `/publiccode.yml`
- `/.well-known/publiccode.yml`
- `/publiccode.yaml`
- `/.well-known/publiccode.yaml`

Rules:

- Attempt HTTPS first
- Fall back to HTTP only if HTTPS fails
- Follow redirects
- Apply strict timeouts
- Abort downloads exceeding a defined size threshold
- Use a clear and honest User-Agent string

Agents must record:

- Requested URL
- Final resolved URL
- HTTP status
- Redirect behavior
- Failure category (404, 403, timeout, TLS error, etc.)

---

## Validation Requirements

### YAML Syntax Validation

- Agents must parse files using a strict YAML parser
- Parse failures must be recorded verbatim
- Semantic validation must not proceed if parsing fails

### publiccode.yml Specification Validation

- Agents must use an authoritative validator
- Validators must match the published specification
- Validation errors must be preserved
- Spec drift must be treated as a failure, not ignored

### Usefulness Assessment

Usefulness is a separate classification layer and must not override technical validity.

Agents must apply explicit criteria, including:

- Non-trivial descriptions
- Reachable URLs
- Recognizable licenses
- Plausible dates and maintenance declarations

Usefulness categories must be clearly distinguished from validity categories.

---

## Output Requirements

Agents must produce:

- A structured dataset (CSV or JSON)
- One record per domain
- Clear, normalized fields

At minimum, outputs must include:

- Domain
- Discovered file URL (if any)
- HTTP outcome
- YAML validity
- Specification validity
- Usefulness classification
- Notes or error summaries

Agents must not discard failed or negative results.

---

## Interpretation Rules

Agents must not:

- Claim “adoption rates” without a defined population
- Treat missing files as non-compliance
- Conflate website-level absence with repository-level practices

Agents must:

- Explicitly state assumptions
- Separate measurement from interpretation
- Flag ambiguity and uncertainty

---

## Operational Constraints

Agents must:

- Use conservative concurrency
- Avoid stressing external systems
- Prefer reproducibility over speed
- Log and report failures rather than retrying indefinitely

If execution constraints prevent full completion, agents must:

- Report partial results
- Describe limitations
- Avoid speculative conclusions

---

## Human Oversight

All agent-generated outputs require human review before:

- Publication
- External sharing
- Policy or strategic use

Agents are advisory tools, not decision-makers.

---

## Change Control

Changes to:

- Discovery paths
- Validation rules
- Usefulness criteria
- Output formats

must be documented and reviewed before execution.

Silent changes are prohibited.

---

## Non-Goals

This repository does **not** aim to:

- Enforce compliance
- Rank governments
- Promote specific tooling
- Substitute for official inventories

It exists to **measure observable behavior**, not to judge intent.

---

## Contact and Accountability

Agent runs must be attributable to a human maintainer.  
All automated requests must include a contact reference.