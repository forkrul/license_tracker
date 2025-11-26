# License Tracker

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Automated open source license attribution and compliance tool for Python projects.**

License Tracker generates hyperlinked `licenses.md` attribution files by scanning your dependency lock files and resolving license metadata through PyPI and GitHub APIs. It bridges the gap between abstract package metadata and the concrete need for consumer-facing documentation with verified links.

## Features

- **Multiple Input Sources**: Scan `poetry.lock`, `Pipfile.lock`, `requirements.txt`, or installed environment
- **Smart License Resolution**: Multi-tiered lookup (Local → PyPI → GitHub → SPDX fallback)
- **Hyperlinked Output**: Every license links directly to the license text (GitHub file or SPDX page)
- **Root Project Inclusion**: Include your project's own license in the attribution
- **Custom Templates**: Use Jinja2 templates for custom output formats
- **Compliance Checking**: Validate against allow/deny license lists
- **CI/CD Ready**: Pre-commit hooks and GitHub Actions integration
- **Async Performance**: Handle 100+ dependencies efficiently with async HTTP

## Installation

```bash
pip install license-tracker
```

## Quick Start

```bash
# Generate licenses.md from poetry.lock
license-tracker gen --scan poetry.lock

# Include your project's license
license-tracker gen --scan poetry.lock --include-root

# Check compliance against forbidden licenses
license-tracker check --scan poetry.lock --forbidden "GPL-3.0,AGPL-3.0"
```

## Example Output

```markdown
# Open Source License Attribution

| Library | Version | License | Source |
|---------|---------|---------|--------|
| [requests](https://requests.readthedocs.io) | 2.31.0 | [Apache-2.0](https://github.com/psf/requests/blob/main/LICENSE) | [GitHub](https://github.com/psf/requests) |
| [click](https://palletsprojects.com/p/click/) | 8.1.7 | [BSD-3-Clause](https://github.com/pallets/click/blob/main/LICENSE.rst) | [GitHub](https://github.com/pallets/click) |
```

## GitHub Rate Limits

For projects with 60+ dependencies, provide a GitHub token:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
license-tracker gen --scan poetry.lock
```

## Documentation

- [Quickstart Guide](.specify/specs/001-license-tracker/quickstart.md)
- [CLI Reference](.specify/specs/001-license-tracker/contracts/cli-spec.md)
- [PRD & Architecture](.prd/001_seed_idea.md)

## Development

```bash
# Clone and install
git clone https://github.com/forkrul/license_tracker
cd license_tracker
pip install -e ".[dev,test]"

# Run tests
pytest

# Lint and format
ruff check src tests
ruff format src tests
```

## Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) first.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

*Generated with [Spec Kit](https://github.com/github/spec-kit) - Spec-Driven Development Toolkit*
