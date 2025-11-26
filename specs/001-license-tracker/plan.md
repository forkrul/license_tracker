# Implementation Plan: License Tracker

**Branch**: `001-license-tracker` | **Date**: 2025-11-26 | **Spec**: `spec.md`
**Input**: Feature specification from `.specify/specs/001-license-tracker/spec.md`

## Summary

License Tracker is a Python CLI tool and library that automates open source license attribution documentation. It implements a hybrid static/dynamic scanning approach with multi-tiered metadata resolution (Local → PyPI → GitHub → SPDX) to generate hyperlinked `licenses.md` files. The architecture separates concerns into Scanners (dependency discovery), Resolvers (metadata enrichment), and Reporters (output generation).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), aiohttp (async HTTP), jinja2 (templating), tomli (TOML parsing), license-expression (SPDX normalization)
**Storage**: SQLite for local cache (`~/.cache/license_tracker/cache.sqlite`)
**Testing**: pytest with pytest-asyncio for async tests
**Target Platform**: Linux, macOS, Windows (cross-platform CLI)
**Project Type**: Single project (Python library + CLI)
**Performance Goals**: <30s for 100 dependencies with GitHub token, <5s for cached results
**Constraints**: Handle GitHub rate limits (60/hr unauthenticated, 5000/hr with token)
**Scale/Scope**: Support projects with 500+ dependencies

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Single project structure (no unnecessary splitting)
- [x] Minimal dependencies (only what's needed)
- [x] No over-engineering (simple pipeline architecture)
- [x] Clear separation of concerns (Scanner → Resolver → Reporter)

## Project Structure

### Documentation (this feature)

```text
.specify/specs/001-license-tracker/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Technology research
├── data-model.md        # Data model definitions
├── quickstart.md        # Getting started guide
├── contracts/           # API contracts
│   └── cli-spec.md      # CLI interface specification
└── tasks.md             # Implementation tasks
```

### Source Code (repository root)

```text
src/
├── license_tracker/
│   ├── __init__.py
│   ├── cli.py                 # Typer CLI entry point
│   ├── models.py              # Data models (PackageSpec, LicenseLink, PackageMetadata)
│   ├── scanners/
│   │   ├── __init__.py
│   │   ├── base.py            # Scanner interface
│   │   ├── poetry.py          # poetry.lock parser
│   │   ├── pipenv.py          # Pipfile.lock parser
│   │   ├── requirements.py    # requirements.txt parser
│   │   └── environment.py     # Installed packages scanner
│   ├── resolvers/
│   │   ├── __init__.py
│   │   ├── base.py            # Resolver interface
│   │   ├── pypi.py            # PyPI JSON API resolver
│   │   ├── github.py          # GitHub API resolver
│   │   └── spdx.py            # SPDX fallback resolver
│   ├── reporters/
│   │   ├── __init__.py
│   │   ├── base.py            # Reporter interface
│   │   └── markdown.py        # Markdown output generator
│   ├── cache.py               # SQLite caching layer
│   └── templates/
│       └── licenses.md.j2     # Default Jinja2 template

tests/
├── conftest.py
├── unit/
│   ├── test_models.py
│   ├── test_scanners/
│   │   ├── test_poetry.py
│   │   ├── test_pipenv.py
│   │   └── test_requirements.py
│   └── test_resolvers/
│       ├── test_pypi.py
│       └── test_github.py
├── integration/
│   └── test_cli.py
└── fixtures/
    ├── poetry.lock
    ├── Pipfile.lock
    └── requirements.txt
```

**Structure Decision**: Single project structure with clear module separation. Scanner/Resolver/Reporter pattern enables independent testing and extension.

## Implementation Phases

### Phase 0: Research

- Validate PyPI JSON API response format
- Document GitHub License API behavior
- Research license-expression library usage
- Identify edge cases in lock file formats

### Phase 1: Core Infrastructure

- Project setup with pyproject.toml
- Data models (PackageSpec, LicenseLink, PackageMetadata)
- Base interfaces for Scanners, Resolvers, Reporters
- CLI skeleton with Typer

### Phase 2: Scanners (User Stories 1, 2)

- Poetry lock file parser
- Pipfile.lock parser
- requirements.txt parser
- Environment scanner (importlib.metadata)
- Root project scanner (User Story 3)

### Phase 3: Resolvers (User Story 1)

- PyPI JSON API resolver
- GitHub License API resolver
- SPDX fallback resolver
- Waterfall resolution orchestration
- Local caching layer

### Phase 4: Reporters (User Stories 1, 4)

- Default Markdown reporter
- Jinja2 template engine integration
- Custom template support
- License file downloader (User Story 6)

### Phase 5: CLI & Integration (User Stories 2, 5)

- `gen` command implementation
- `check` command with deny-list
- GitHub token handling
- Pre-commit hook configuration

### Phase 6: Polish

- Error handling and logging
- Documentation
- Performance optimization
- Test coverage completion

## Complexity Tracking

> No constitution violations identified - structure is minimal and appropriate.

| Decision | Rationale |
|----------|-----------|
| Async HTTP | Required for performance with 100+ dependencies |
| SQLite cache | Simple, zero-config, portable |
| Jinja2 templates | Industry standard, user-familiar |
