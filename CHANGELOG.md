# Changelog

All notable changes to this project will be documented in this file.

This project follows the [Common Changelog](https://common-changelog.org/) specification.

## [Unreleased]

## [0.1.0] - 2025-11-27

Initial release of license_tracker - an automated open source license attribution and compliance tool.

### Added

- **Scanners** for parsing Python dependency files:
  - `PoetryScanner` - parses `poetry.lock` TOML files
  - `PipenvScanner` - parses `Pipfile.lock` JSON files
  - `RequirementsScanner` - parses `requirements.txt` with version specifiers
  - Scanner factory `get_scanner()` for automatic format detection

- **Resolvers** for fetching license metadata:
  - `PyPIResolver` - fetches from PyPI JSON API with SPDX normalization
  - `GitHubResolver` - fetches verified LICENSE file URLs via GitHub API
  - `SPDXResolver` - fallback resolver for SPDX license page URLs
  - `WaterfallResolver` - orchestrates resolvers in priority order (PyPI → GitHub → SPDX)
  - `HttpResolver` - shared base class for HTTP session management

- **Cache layer** with SQLite backend:
  - 30-day TTL for license resolution results
  - Automatic purging of expired entries on initialization
  - Commands for viewing and clearing cache

- **Reporters** for output generation:
  - `MarkdownReporter` with Jinja2 templating
  - Support for custom templates
  - XSS protection via Jinja2 autoescaping

- **CLI commands**:
  - `gen` - generate license attribution documentation
  - `check` - validate licenses against allow/deny lists
  - `cache` - manage the resolution cache (show/clear)

- **Data models**:
  - `PackageSpec` - package name and version
  - `LicenseLink` - SPDX ID, name, URL, verification status
  - `PackageMetadata` - complete package information with licenses

- **Test suite** with 150 tests covering:
  - All scanners, resolvers, and reporters
  - CLI integration tests
  - Security-focused tests for XSS prevention

### Security

- Enabled Jinja2 autoescaping to prevent XSS vulnerabilities
- Added `SECURITY_AUDIT.md` documenting security review findings
- No hardcoded secrets or credentials in codebase

### Documentation

- Comprehensive README with quick start guide
- CLI specification in `specs/001-license-tracker/contracts/cli-spec.md`
- Data model documentation in `specs/001-license-tracker/data-model.md`
- Security audit report in `SECURITY_AUDIT.md`

[Unreleased]: https://github.com/forkrul/license_tracker/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/forkrul/license_tracker/releases/tag/v0.1.0
