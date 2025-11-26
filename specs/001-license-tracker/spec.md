# Feature Specification: License Tracker

**Feature Branch**: `001-license-tracker`
**Created**: 2025-11-26
**Status**: Approved
**Input**: PRD from `.prd/001_seed_idea.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Attribution Documentation (Priority: P1) 🎯 MVP

As a developer, I want to run `license-tracker gen` to create a `licenses.md` file where every package name links to its homepage and every license name links to the specific license text URL, so I can comply with attribution requirements without manual research.

**Why this priority**: This is the core value proposition - generating compliant attribution documentation automatically is the primary use case.

**Independent Test**: Can be fully tested by running `license-tracker gen --scan poetry.lock` and verifying the generated `licenses.md` contains a properly formatted table with hyperlinked licenses and package homepages.

**Acceptance Scenarios**:

1. **Given** a Python project with a `poetry.lock` file, **When** I run `license-tracker gen`, **Then** a `licenses.md` file is created with a table containing Package Name, Version, License (hyperlinked), and Homepage columns.
2. **Given** a project with 10 dependencies, **When** I run `license-tracker gen`, **Then** all 10 packages appear in the output with resolved license URLs.
3. **Given** a package with a GitHub repository, **When** resolving its license, **Then** the license URL points directly to the LICENSE file in the repository (e.g., `github.com/owner/repo/blob/main/LICENSE`).
4. **Given** a package without a resolvable GitHub license, **When** resolving its license, **Then** the fallback URL points to the SPDX license page (e.g., `spdx.org/licenses/MIT.html`).

---

### User Story 2 - Static Lock File Scanning (Priority: P1)

As a DevOps engineer, I want to scan my `poetry.lock` file in a lightweight CI container (without installing dependencies) to verify license compliance before deployment.

**Why this priority**: CI/CD integration is critical for enterprise adoption - scanning without installation enables lightweight, fast pipelines.

**Independent Test**: Can be tested by providing a `poetry.lock` file to a fresh environment without installed packages and verifying the scan completes successfully.

**Acceptance Scenarios**:

1. **Given** a `poetry.lock` file, **When** I run `license-tracker scan --input poetry.lock`, **Then** all dependencies are parsed and their licenses resolved via PyPI API.
2. **Given** a `Pipfile.lock` file, **When** I run `license-tracker scan --input Pipfile.lock`, **Then** dependencies from both `default` and `develop` sections are parsed.
3. **Given** a `requirements.txt` file, **When** I run `license-tracker scan --input requirements.txt`, **Then** packages with version specifiers are correctly parsed.

---

### User Story 3 - Include Root Project License (Priority: P2)

As a project maintainer, I want the tool to include my project's license in the output report so that the generated file is a complete Bill of Materials for the software product.

**Why this priority**: Including the root project provides a complete, self-contained attribution artifact - important for compliance but not blocking core functionality.

**Independent Test**: Can be tested by running the tool in a project with a `pyproject.toml` containing license metadata and verifying the output includes the root project at the top.

**Acceptance Scenarios**:

1. **Given** a project with `pyproject.toml` containing license metadata, **When** I run `license-tracker gen --include-root`, **Then** the root project appears first in the output with `is_root_project=True`.
2. **Given** a project with `setup.cfg` containing license info, **When** I run `license-tracker gen --include-root`, **Then** the license is correctly extracted from the config file.

---

### User Story 4 - Custom Template Output (Priority: P2)

As a technical writer, I want to provide a custom Jinja2 template to format the output as an HTML table or a specific Markdown style to match my company's documentation guidelines.

**Why this priority**: Customization enables enterprise adoption with varied documentation standards.

**Independent Test**: Can be tested by providing a custom `.j2` template file and verifying the output matches the template format.

**Acceptance Scenarios**:

1. **Given** a custom Jinja2 template file, **When** I run `license-tracker gen --template my_template.j2`, **Then** the output is rendered using the custom template.
2. **Given** a template with HTML table markup, **When** generating output, **Then** a valid HTML file is produced.

---

### User Story 5 - License Compliance Check (Priority: P3)

As a DevOps engineer, I want to run a compliance check against a deny-list of licenses so that I can block deployments containing forbidden licenses.

**Why this priority**: Compliance gating is valuable but builds on core scanning functionality.

**Independent Test**: Can be tested by running check command with a forbidden license list and verifying correct exit codes.

**Acceptance Scenarios**:

1. **Given** a project with GPL-3.0 licensed dependencies, **When** I run `license-tracker check --forbidden "GPL-3.0"`, **Then** the command exits with non-zero status and lists the violations.
2. **Given** a project with only MIT/Apache-2.0 dependencies, **When** I run `license-tracker check --forbidden "GPL-3.0"`, **Then** the command exits with status 0.

---

### User Story 6 - Download License Files (Priority: P3)

As a legal compliance officer, I want to download actual license text files locally so that I can archive them with the software distribution.

**Why this priority**: Local archival is important for legal compliance but is an enhancement over URL-based attribution.

**Independent Test**: Can be tested by running with `--download` flag and verifying license files exist in the output directory.

**Acceptance Scenarios**:

1. **Given** I run `license-tracker gen --download`, **Then** license text files are downloaded to `docs/licenses/` directory.
2. **Given** downloaded license files, **When** generating the markdown report, **Then** links point to the local files instead of remote URLs.

---

### Edge Cases

- What happens when PyPI API is unreachable? → Graceful degradation with cached/local data
- What happens when GitHub rate limit is exceeded? → Exponential backoff + prompt for PAT
- How does system handle dual-licensed packages (MIT OR Apache-2.0)? → Parse with license-expression, list all licenses
- What happens with vendorized dependencies? → Support manual overrides via config file
- How to handle packages with no declared license? → Mark as "UNKNOWN" with warning

## Requirements *(mandatory)*

### Functional Requirements

#### Dependency Discovery (Scanners)

- **FR-1.1**: System MUST implement a Scanner interface for extracting direct dependency names and versions from multiple sources (transitive dependencies excluded; for poetry.lock, filter to keys in pyproject.toml [tool.poetry.dependencies])
- **FR-1.2**: System MUST support `poetry.lock` parsing (TOML) without requiring environment activation
- **FR-1.3**: System MUST support `Pipfile.lock` parsing (JSON) including default and develop sections
- **FR-1.4**: System MUST support `requirements.txt` parsing, handling version specifiers and git URLs
- **FR-1.5**: System MUST support "Environment Scan" mode using `importlib.metadata` for installed packages
- **FR-1.6**: System MUST optionally include root project metadata from `pyproject.toml` or `setup.cfg`

#### Metadata Resolution (Resolvers)

- **FR-2.1**: System MUST implement "Waterfall Resolution" strategy: Local → PyPI → GitHub → SPDX fallback
- **FR-2.2**: System MUST query PyPI JSON API (`pypi.org/pypi/<package>/json`) for license metadata
- **FR-2.3**: System MUST detect GitHub URLs and use GitHub REST API to resolve direct license file links
- **FR-2.4**: System MUST normalize license names to SPDX identifiers using `license-expression` library
- **FR-2.5**: System MUST generate SPDX fallback URLs when direct file links unavailable

#### Output Generation (Reporters)

- **FR-3.1**: System MUST generate Markdown output by default (`licenses.md`)
- **FR-3.2**: Output MUST contain table with: Package Name, Version, License (hyperlinked), Homepage/Source
- **FR-3.3**: System MUST support custom Jinja2 templates via `--template` flag
- **FR-3.4**: System MUST support `--download` option to download and locally store license files

#### CLI Interface

- **FR-4.1**: System MUST provide `gen` command for generating attribution documentation
- **FR-4.2**: System MUST provide `check` command for compliance validation against deny-lists
- **FR-4.3**: System MUST accept `--github-token` flag or read `GITHUB_TOKEN` environment variable
- **FR-4.4**: System MUST support `--output` flag to specify output file path
- **FR-4.5**: System MUST provide `cache` subcommand with `show` and `clear` operations for cache management

### Non-Functional Requirements

- **NFR-1**: Remote metadata fetching MUST be asynchronous (using `aiohttp`) for performance
- **NFR-2**: System MUST implement exponential backoff for GitHub API rate limiting
- **NFR-3**: System MUST implement local cache (`~/.cache/license_tracker/`) with 30-day TTL and `cache clear` command for manual invalidation
- **NFR-4**: System MUST distinguish between "verified" (GitHub) and "inferred" (SPDX) license links
- **NFR-5**: System MUST handle 100+ dependencies within 30 seconds (with valid GitHub token)
- **NFR-6**: System MUST provide structured logging with errors-only by default and `-v/--verbose` flag for debug output

### Key Entities

- **PackageSpec**: Name and version tuple representing a dependency (input to resolution)
- **LicenseLink**: SPDX ID, human-readable name, URL, and verification status
- **PackageMetadata**: Enriched package data including name, version, description, homepage, repository URL, licenses list, and root project flag

## Clarifications

### Session 2025-11-26

- Q: What logging verbosity should the CLI provide by default? → A: Structured logging with `-v/--verbose` flag for debug output (errors only by default)
- Q: How should cached license resolutions expire? → A: 30-day TTL with manual `cache clear` command
- Q: Should the tool resolve licenses for transitive dependencies or only direct dependencies? → A: Direct dependencies only (what's in lock file top-level)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can generate a compliant `licenses.md` file in under 60 seconds for projects with <50 dependencies
- **SC-002**: 95% of package licenses are successfully resolved to either direct file links or SPDX URLs
- **SC-003**: Static lock file scanning works without any package installation
- **SC-004**: CI pipeline integration reduces manual license documentation effort by 100%
- **SC-005**: Zero false negatives on forbidden license detection in compliance checks
