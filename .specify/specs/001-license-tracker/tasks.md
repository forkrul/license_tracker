# Tasks: License Tracker

**Input**: Design documents from `.specify/specs/001-license-tracker/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: Unit and integration tests included for core functionality.

**Organization**: Tasks grouped by user story for independent implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US6)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per plan.md layout
- [ ] T002 Initialize Python project with `pyproject.toml` (name: license-tracker, python>=3.11)
- [ ] T003 [P] Add core dependencies: typer, aiohttp, jinja2, tomli, license-expression
- [ ] T004 [P] Add dev dependencies: pytest, pytest-asyncio, pytest-cov, ruff, mypy
- [ ] T005 [P] Configure ruff for linting/formatting in `pyproject.toml`
- [ ] T006 [P] Configure mypy for type checking in `pyproject.toml`
- [ ] T007 Create `src/license_tracker/__init__.py` with version info
- [ ] T008 Create CLI entry point in `pyproject.toml` (`license-tracker` → `license_tracker.cli:app`)

**Checkpoint**: Project installable with `pip install -e .`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 Create data models in `src/license_tracker/models.py`:
  - PackageSpec (name, version, source)
  - LicenseLink (spdx_id, name, url, is_verified_file)
  - PackageMetadata (name, version, description, homepage, repository_url, licenses, is_root_project)
- [ ] T010 [P] Create Scanner base interface in `src/license_tracker/scanners/base.py`
- [ ] T011 [P] Create Resolver base interface in `src/license_tracker/resolvers/base.py`
- [ ] T012 [P] Create Reporter base interface in `src/license_tracker/reporters/base.py`
- [ ] T013 Create CLI skeleton with Typer in `src/license_tracker/cli.py` (gen, check commands as stubs)
- [ ] T014 [P] Create test fixtures in `tests/fixtures/` (sample poetry.lock, Pipfile.lock, requirements.txt)
- [ ] T015 Create `tests/conftest.py` with shared pytest fixtures

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 & 2 - Scanners (Priority: P1) 🎯 MVP

**Goal**: Parse lock files and extract dependency information without installation

**Independent Test**: Run `license-tracker gen --scan poetry.lock` and verify packages are listed

### Tests for Scanners ⚠️

> **Write tests FIRST, ensure they FAIL before implementation**

- [ ] T016 [P] [US1] Unit test for PoetryScanner in `tests/unit/test_scanners/test_poetry.py`
- [ ] T017 [P] [US2] Unit test for PipenvScanner in `tests/unit/test_scanners/test_pipenv.py`
- [ ] T018 [P] [US2] Unit test for RequirementsScanner in `tests/unit/test_scanners/test_requirements.py`

### Implementation for Scanners

- [ ] T019 [US1] Implement PoetryScanner in `src/license_tracker/scanners/poetry.py`
  - Parse [[package]] sections from TOML
  - Extract name and version
  - Return list of PackageSpec
- [ ] T020 [US2] Implement PipenvScanner in `src/license_tracker/scanners/pipenv.py`
  - Parse JSON structure
  - Handle default and develop sections
  - Strip `==` from versions
- [ ] T021 [US2] Implement RequirementsScanner in `src/license_tracker/scanners/requirements.py`
  - Parse version specifiers
  - Handle comments and blank lines
  - Skip git URLs (log warning)
- [ ] T022 [US1] Implement EnvironmentScanner in `src/license_tracker/scanners/environment.py`
  - Use importlib.metadata.distributions()
  - Extract installed packages
- [ ] T023 Create scanner factory in `src/license_tracker/scanners/__init__.py`
  - Auto-detect file type from extension
  - Return appropriate scanner instance

**Checkpoint**: Scanners extract packages from all lock file formats

---

## Phase 4: User Story 1 - Resolvers (Priority: P1) 🎯 MVP

**Goal**: Resolve license metadata via PyPI and GitHub APIs

**Independent Test**: Given a PackageSpec, return PackageMetadata with license URLs

### Tests for Resolvers ⚠️

- [ ] T024 [P] [US1] Unit test for PyPIResolver in `tests/unit/test_resolvers/test_pypi.py` (mock HTTP)
- [ ] T025 [P] [US1] Unit test for GitHubResolver in `tests/unit/test_resolvers/test_github.py` (mock HTTP)
- [ ] T026 [P] [US1] Unit test for SPDXResolver in `tests/unit/test_resolvers/test_spdx.py`

### Implementation for Resolvers

- [ ] T027 [US1] Implement PyPIResolver in `src/license_tracker/resolvers/pypi.py`
  - Async fetch from PyPI JSON API
  - Extract license, classifiers, project_urls
  - Map classifiers to SPDX using license-expression
- [ ] T028 [US1] Implement GitHubResolver in `src/license_tracker/resolvers/github.py`
  - Parse GitHub URL from project_urls
  - Fetch license via GitHub API
  - Handle rate limiting with retry
  - Accept token from env/parameter
- [ ] T029 [US1] Implement SPDXResolver in `src/license_tracker/resolvers/spdx.py`
  - Generate SPDX URL from license identifier
  - Mark as is_verified_file=False
- [ ] T030 [US1] Implement WaterfallResolver in `src/license_tracker/resolvers/__init__.py`
  - Orchestrate: Cache → Local → PyPI → GitHub → SPDX
  - Aggregate results into PackageMetadata
- [ ] T031 [US1] Implement cache layer in `src/license_tracker/cache.py`
  - SQLite storage in ~/.cache/license_tracker/
  - 30-day TTL
  - Async-compatible interface

**Checkpoint**: License resolution works for any valid PyPI package

---

## Phase 5: User Story 1 - Reporter (Priority: P1) 🎯 MVP

**Goal**: Generate hyperlinked Markdown attribution documentation

**Independent Test**: Given PackageMetadata list, output valid licenses.md

### Tests for Reporter ⚠️

- [ ] T032 [P] [US1] Unit test for MarkdownReporter in `tests/unit/test_reporters/test_markdown.py`

### Implementation for Reporter

- [ ] T033 [US1] Create default Jinja2 template in `src/license_tracker/templates/licenses.md.j2`
  - Header with project name
  - Table with Package, Version, License (linked), Source (linked)
  - Footer with generator attribution
- [ ] T034 [US1] Implement MarkdownReporter in `src/license_tracker/reporters/markdown.py`
  - Load template from package resources
  - Render with PackageMetadata list
  - Handle missing/empty fields gracefully

**Checkpoint**: User Story 1 complete - can generate licenses.md from lock file

---

## Phase 6: User Story 3 - Root Project (Priority: P2)

**Goal**: Include root project's license in output

**Independent Test**: Run with --include-root and verify root appears first

### Tests for Root Scanner ⚠️

- [ ] T035 [P] [US3] Unit test for root project scanning in `tests/unit/test_scanners/test_root.py`

### Implementation for Root Project

- [ ] T036 [US3] Implement root project scanner in `src/license_tracker/scanners/root.py`
  - Parse pyproject.toml for [project] metadata
  - Fallback to setup.cfg [metadata]
  - Extract name, version, license
- [ ] T037 [US3] Add `--include-root` flag to CLI gen command
- [ ] T038 [US3] Update template to show root project prominently

**Checkpoint**: Root project appears in attribution with is_root_project=True

---

## Phase 7: User Story 4 - Custom Templates (Priority: P2)

**Goal**: Support custom Jinja2 templates for output formatting

**Independent Test**: Provide custom.j2 and verify output matches template

### Implementation for Custom Templates

- [ ] T039 [US4] Add `--template` flag to CLI gen command
- [ ] T040 [US4] Update MarkdownReporter to load external template files
- [ ] T041 [US4] Create example templates in `examples/templates/`:
  - `html_table.j2` - HTML output
  - `rst_table.j2` - ReStructuredText
  - `csv.j2` - CSV export

**Checkpoint**: Custom templates work for various output formats

---

## Phase 8: User Story 5 - Compliance Check (Priority: P3)

**Goal**: Validate dependencies against license deny-list

**Independent Test**: Run check with forbidden GPL-3.0, verify exit code

### Tests for Compliance ⚠️

- [ ] T042 [P] [US5] Integration test for check command in `tests/integration/test_compliance.py`

### Implementation for Compliance

- [ ] T043 [US5] Implement `check` command in `src/license_tracker/cli.py`
  - Accept `--forbidden` comma-separated list
  - Accept `--allowed` as alternative (whitelist mode)
  - Scan and resolve licenses
  - Compare against policy
  - Exit 0 if compliant, 1 if violations
- [ ] T044 [US5] Add violation reporting format
  - List each violating package
  - Show detected license and why it's forbidden

**Checkpoint**: CI can gate deployments on license compliance

---

## Phase 9: User Story 6 - Download Licenses (Priority: P3)

**Goal**: Download and archive license text files locally

**Independent Test**: Run with --download and verify files in docs/licenses/

### Implementation for Download

- [ ] T045 [US6] Add `--download` flag to CLI gen command
- [ ] T046 [US6] Implement license file downloader in `src/license_tracker/downloader.py`
  - Fetch raw license text from resolved URLs
  - Save to docs/licenses/{package_name}-{version}.txt
  - Handle GitHub raw URLs
- [ ] T047 [US6] Update template to link to local files when downloaded

**Checkpoint**: License files archived locally for distribution

---

## Phase 10: CLI Integration & Polish

**Purpose**: Complete CLI implementation and cross-cutting concerns

- [ ] T048 Implement full `gen` command flow in `src/license_tracker/cli.py`
  - Wire together scanner → resolver → reporter
  - Add `--output` flag for file path
  - Add `--format` flag (md, json)
  - Progress indicator for large projects
- [ ] T049 Add `--github-token` flag and GITHUB_TOKEN env var support
- [ ] T050 [P] Add comprehensive error handling and logging
- [ ] T051 [P] Integration test for full gen workflow in `tests/integration/test_cli.py`
- [ ] T052 [P] Update README.md with usage examples
- [ ] T053 [P] Create CHANGELOG.md entry
- [ ] T054 Run full test suite and achieve >80% coverage
- [ ] T055 Validate against quickstart.md examples

**Checkpoint**: Tool ready for release

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **Scanners (Phase 3)**: Depends on Foundational - enables US1/US2
- **Resolvers (Phase 4)**: Depends on Foundational - enables US1
- **Reporter (Phase 5)**: Depends on Resolvers - completes US1 MVP
- **Root Project (Phase 6)**: Depends on Phase 5 - US3
- **Templates (Phase 7)**: Depends on Phase 5 - US4
- **Compliance (Phase 8)**: Depends on Phase 4 - US5
- **Download (Phase 9)**: Depends on Phase 5 - US6
- **Polish (Phase 10)**: Depends on all desired stories

### Within Each Phase

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before CLI integration
- Commit after each task or logical group

### Parallel Opportunities

Within phases marked [P]:
- All test tasks can run in parallel
- Model/interface tasks can run in parallel
- Independent scanner implementations can run in parallel
- Independent resolver implementations can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: Scanners (PoetryScanner only for MVP)
4. Complete Phase 4: Resolvers
5. Complete Phase 5: Reporter
6. **STOP and VALIDATE**: Test `license-tracker gen --scan poetry.lock`
7. Deploy/demo MVP

### Incremental Delivery

1. MVP (US1 core) → Test → Release v0.1.0
2. Add US2 (all scanners) → Test → Release v0.2.0
3. Add US3 (root project) → Test → Release v0.3.0
4. Add US4 (templates) + US5 (compliance) → Test → Release v0.4.0
5. Add US6 (download) + Polish → Test → Release v1.0.0

---

## Notes

- [P] tasks = different files, no dependencies within phase
- Tests use pytest-asyncio for async resolver tests
- Mock HTTP responses in tests (don't hit real APIs)
- Cache tests should use temp directory
- Keep scanner implementations simple - no premature optimization
