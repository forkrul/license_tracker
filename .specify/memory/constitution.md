# License Tracker Constitution

## Core Principles

### I. Attribution-First Design
The primary goal is generating human-readable attribution documentation, not forensic auditing. Every design decision prioritizes developer experience and end-user accessibility over exhaustive legal analysis.

### II. Static Analysis Preferred
Scanning MUST work without installing dependencies. Lock file parsing and API lookups are preferred over environment inspection. This enables lightweight CI/CD integration.

### III. Direct Dependencies Only
By default, only direct dependencies are tracked (not transitive). This keeps attribution documents manageable and reflects what the project explicitly chose to include.

### IV. Graceful Degradation
When external APIs fail (rate limits, network issues), the system MUST fall back gracefully:
- Cache → Local metadata → PyPI → GitHub → SPDX generic URLs
- Never fail completely; always produce some output with warnings.

### V. Test-First Development
TDD is mandatory for all scanner, resolver, and reporter implementations:
- Write failing tests first
- Implement to pass tests
- Mock external HTTP calls in tests

### VI. Minimal Dependencies
Core functionality uses only essential libraries:
- typer (CLI)
- aiohttp (async HTTP)
- jinja2 (templating)
- tomli (TOML parsing)
- license-expression (SPDX normalization)

No additional frameworks without explicit justification.

## Quality Gates

- All PRs must include tests for new functionality
- Coverage target: >80%
- All public functions must have type hints
- Ruff linting must pass with zero errors

## Governance

This constitution defines non-negotiable principles for license_tracker development. Amendments require documented justification and explicit approval.

**Version**: 1.0.0 | **Ratified**: 2025-11-26 | **Last Amended**: 2025-11-26
