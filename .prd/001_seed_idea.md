# Automated Open Source Attribution and Compliance Architecture: A Comprehensive Product Requirements Document and Landscape Analysis for license_tracker

## 1. Executive Summary

In the contemporary software engineering landscape, the management of open source software (OSS) supply chains has evolved from a peripheral legal concern to a central pillar of DevSecOps and software architecture. As organizations increasingly rely on third-party libraries to accelerate development, the obligation to provide accurate, accessible, and legally compliant attribution—specifically in the form of licenses.md or NOTICE files—has become a critical operational requirement. The user query necessitates the creation of a Product Requirements Document (PRD) for a new Python library, license_tracker, designed to automate the tracking of open source dependencies, link to their specific licenses, and generate attribution artifacts. Crucially, the request highlights a specific functional gap in the current ecosystem: the ability to generate human-readable documentation that not only lists licenses but provides direct, verified hyperlinks to the license text, and the ability to include the root project's own license in this aggregation.

This report serves a dual purpose. First, it conducts an exhaustive landscape analysis of existing tools—such as pip-licenses, scancode-toolkit, and pip-audit—to identify architectural precedents and functional deficits. The analysis reveals that while the ecosystem is rich in forensic scanners and security auditing tools, there is a distinct lack of lightweight, developer-centric libraries capable of bridging the gap between abstract package metadata and the concrete need for hyperlinked consumer-facing documentation. Second, leveraging these insights, the report delivers a definitive PRD and technical specification for license_tracker.

The proposed system architecture addresses the friction between static analysis (parsing poetry.lock or Pipfile.lock without installation) and dynamic environment inspection. By utilizing a multi-layered resolution strategy—enriching local metadata with data from the PyPI JSON API and the GitHub REST API—license_tracker aims to produce high-fidelity attribution artifacts. This tool will serve not merely as a compliance checker, but as a documentation generator, transforming the legal requirement of attribution into a seamless, automated component of the continuous integration (CI) pipeline.

## 2. The Context of Software Supply Chain Compliance

To define the requirements for license_tracker, one must first understand the complexity of the domain it inhabits. The Python ecosystem, managed primarily through the Python Package Index (PyPI), presents unique challenges regarding metadata standardization, which directly impacts the ability to automate license tracking.

### 2.1 The Evolution of Python Packaging Metadata

Historically, Python packaging metadata has been fragmented. The reliance on setup.py, an executable Python script, meant that metadata was often dynamic and could not be determined without executing code—a security risk and an operational bottleneck. While newer standards like PEP 621 and the move to pyproject.toml have introduced declarative metadata, millions of legacy packages still rely on unstructured classifiers or free-text License fields.

The introduction of PEP 639, which specifies how to declare project licenses using SPDX expressions (e.g., MIT OR Apache-2.0) and legally required license files, marks a significant shift. However, adoption is gradual. A robust license tracker must therefore operate in a hybrid environment, parsing both the structured future (SPDX expressions in pyproject.toml) and the unstructured past (ambiguous classifiers in setup.cfg).

### 2.2 The "Attribution vs. Audit" Distinction

A critical distinction often missed in tool design is the difference between an Audit and Attribution.

* **Audit Tools** (e.g., scancode-toolkit) are designed for legal teams. They are forensic, exhaustive, and prioritize detecting every snippet of copied code, often resulting in massive reports that are unintelligible to the average user.
* **Attribution Tools** (the goal of license_tracker) are designed for end-users. They must generate a concise, readable Bill of Materials (BoM) that fulfills the legal requirement of "including a copy of the license" often by linking to it or summarizing it in a licenses.md file.

The user request specifically targets the latter: a tool to generate a licenses.md file with links. This requirement fundamentally alters the technical architecture, prioritizing metadata resolution and URL validation over forensic source code scanning.

## 3. Landscape Analysis of Existing Open Source Libraries

Before specifying license_tracker, a deep-dive analysis of existing solutions is required to validate the need for a new tool and to identify reusable components. The market is currently bifurcated between lightweight metadata parsers and heavyweight forensic scanners.

### 3.1 Metadata-Based Trackers

These tools inspect the installed environment or lock files to report what is declared.

#### 3.1.1 pip-licenses

pip-licenses is the most direct incumbent. It is a command-line tool that scans the site-packages directory of the active Python environment to list installed packages and their declared licenses.

* **Mechanism**: It relies on pkg_resources (setuptools) or importlib.metadata to read the METADATA or PKG-INFO files generated during installation.
* **Gap Analysis - The Linking Problem**: A primary limitation relative to the user's request is its handling of license text. pip-licenses can output the path to a local license file on the disk using the --with-license-file option, but it does not inherently resolve remote URLs for these licenses to create a hyperlinked Markdown table. It focuses on dumping the text found on disk, which bloats the output, rather than creating a sleek, link-based attribution file.
* **Gap Analysis - Static Analysis**: It requires packages to be installed. It cannot scan a poetry.lock file in a clean CI environment to generate a report; the environment must be hydrated first, which is resource-intensive.

#### 3.1.2 pip-audit

While primarily a security tool for vulnerability scanning, pip-audit offers a superior architectural model for dependency resolution.

* **Mechanism**: It supports parsing requirements.txt and communicating with the PyPI JSON API to fetch metadata (vulnerabilities) without installing the packages.
* **Relevance**: license_tracker should emulate pip-audit's ability to act on abstract dependency lists (static analysis) rather than requiring a full environment install. However, pip-audit focuses on CVEs, not licenses, and its output formats (CycloneDX SBOM) are not designed for human attribution.

#### 3.1.3 license-expression

Maintained by the AboutCode organization, this library does not scan packages but provides the logic to parse, normalize, and compare license strings (e.g., handling complex boolean expressions like GPL-2.0-or-later WITH Classpath-exception-2.0).

* **Integration**: It is an essential component for license_tracker to normalize the messy strings found in PyPI metadata into standard SPDX identifiers that can be reliably linked to URLs.

### 3.2 Forensic and Source Code Scanners

#### 3.2.1 scancode-toolkit

The industry standard for forensic identification, scancode-toolkit scans source code and binaries for copyright headers and license texts using a database of over 2,100 license variations.

* **Pros**: Unmatched accuracy. It finds licenses that packaging metadata misses (e.g., a file-level license in a sub-module).
* **Cons**: It is "heavy." Scanning a site-packages directory with scancode is slow and resource-intensive (I/O heavy). For a developer tool intended to run quickly in a pre-commit hook or CI step to generate licenses.md, scancode-toolkit is often excessive. It is an audit tool, not a documentation generator.

#### 3.2.2 LicenseFinder

A multi-language tool that integrates into CI to approve/reject dependencies based on policy.

* **Cons**: Its primary output is a pass/fail decision or a CSV report. It lacks the specific "Markdown with links" generation capability requested and is Ruby-centric in its origin, though it supports Python.

### 3.3 Comparative Summary Table

| Feature | pip-licenses | scancode-toolkit | pip-audit | license_tracker (Target) |
|---|---|---|---|---|
| Analysis Mode | Dynamic (Must be installed) | Static (Source Scan) | Static (API Lookup) | Hybrid (Static + Dynamic) |
| Input Sources | site-packages | File System | requirements.txt | poetry.lock, Pipfile, Env |
| License Links | Local path only | N/A (Embedded text) | N/A | Remote (GitHub/SPDX) & Local |
| Output Focus | Text Dump / CSV | Legal Audit Data | Security SBOM | Human-Readable Attribution |
| Metadata Source | Local PKG-INFO | File Content | PyPI Advisory DB | PyPI API + GitHub API |

The analysis confirms a clear market gap: A tool that combines the static parsing capabilities of pip-audit with the license focus of pip-licenses, upgraded with a "Smart Linking" engine to generate developer-friendly Markdown documentation.

## 4. Product Requirements Document (PRD): license_tracker

**Project Name**: license_tracker
**Version**: 1.0.0
**Status**: Specification
**Target Persona**: Senior Python Developers, OSPOs, and DevOps Engineers.

### 4.1 Product Vision

license_tracker is a Python library and Command Line Interface (CLI) tool designed to automate the generation of open source compliance documentation. It tracks dependencies across modern package managers (Pip, Poetry, Pipenv), resolves their license metadata through a multi-tiered lookup strategy (Local -> PyPI -> GitHub), and generates a standardized, hyperlinked licenses.md file. It ensures that the project containing the tracker is also included in the report, providing a complete, self-contained attribution artifact.

### 4.2 User Stories

* **US-1 (The Documentation Generator)**: As a developer, I want to run license-tracker gen to create a licenses.md file where every package name links to its homepage and every license name links to the specific license text URL, so I can comply with attribution requirements without manual research.
* **US-2 (The CI Gatekeeper)**: As a DevOps engineer, I want to scan my poetry.lock file in a lightweight CI container (without installing dependencies) to verify license compliance before deployment.
* **US-3 (The Self-Reflective Audit)**: As a project maintainer, I want the tool to include my project's license in the output report so that the generated file is a complete Bill of Materials for the software product.
* **US-4 (The Customizer)**: As a technical writer, I want to provide a custom Jinja2 template to format the output as an HTML table or a specific Markdown style to match my company's documentation guidelines.

### 4.3 Functional Requirements (FR)

#### 4.3.1 Dependency Discovery (The Scanners)

* **FR-1.1**: The system shall implement a Scanner interface capable of extracting dependency names and versions from multiple sources.
* **FR-1.2**: The system shall support poetry.lock parsing (TOML) to extract dependencies and their versions without requiring the environment to be active.
* **FR-1.3**: The system shall support Pipfile.lock parsing (JSON) to extract the dependency graph.
* **FR-1.4**: The system shall support requirements.txt parsing, handling version specifiers and git URLs.
* **FR-1.5**: The system shall support an "Environment Scan" mode using importlib.metadata to detect currently installed packages.
* **FR-1.6**: The system shall optionally include the root project (the project executing the tool) in the dependency list, reading its metadata from pyproject.toml or setup.cfg.

#### 4.3.2 Metadata Resolution (The Resolvers)

* **FR-2.1**: The system shall implement a "Waterfall Resolution" strategy. It must attempt to resolve license metadata from local sources first, then fall back to remote APIs.
* **FR-2.2**: The system shall query the PyPI JSON API (pypi.org/pypi/<package>/json) to retrieve declared license classifiers and project URLs.
* **FR-2.3**: The system shall detect GitHub repository URLs in package metadata and use the GitHub REST API (/repos/{owner}/{repo}/license) to retrieve the direct HTML link to the license file (e.g., blob/main/LICENSE).
* **FR-2.4**: The system shall map legacy license names (e.g., "BSD", "Apache 2.0") to valid SPDX identifiers using the license-expression library.
* **FR-2.5**: If a direct file link cannot be resolved, the system shall generate a fallback link to the corresponding OSI or SPDX license definition page.

#### 4.3.3 Output Generation (The Reporters)

* **FR-3.1**: The system shall generate a Markdown file by default (licenses.md).
* **FR-3.2**: The Markdown output shall contain a table with columns: Package Name, Version, License (Hyperlinked), and Homepage/Source.
* **FR-3.3**: The system shall support custom templates using the Jinja2 engine, allowing users to supply a .j2 file to override the default output format.
* **FR-3.4**: The system shall support an option --download to download the raw license text files to a local directory (docs/licenses/) and link to these local files in the Markdown report.

### 4.4 Non-Functional Requirements (NFR)

* **NFR-1 (Performance)**: Remote metadata fetching must be asynchronous (using aiohttp or similar) to handle projects with hundreds of dependencies efficiently.
* **NFR-2 (Rate Limiting)**: The system must handle HTTP 429 errors from the GitHub API gracefully, utilizing exponential backoff or prompting the user for a Personal Access Token (PAT).
* **NFR-3 (Accuracy)**: The system must clearly distinguish between "verified" license links (from GitHub API) and "inferred" license links (SPDX generic pages).

## 5. Technical Specification and Architecture

This section details the internal architecture required to build license_tracker, focusing on the unique challenge of linking and the hybrid analysis model.

### 5.1 System Architecture Diagram (Textual Description)

The architecture follows a pipeline pattern:

**Input Source -> Scanner -> Intermediate Representation (Package List) -> Resolver Engine -> Enriched Data -> Reporter -> Output Artifact.**

* **Scanner Layer**: Abstract classes for PoetryScanner, PipenvScanner, RequirementsScanner, and EnvironmentScanner. Each accepts a file path and returns a list of PackageSpec objects (name, version).
* **Resolver Layer**: A composite engine containing PyPIResolver and GitHubResolver. It accepts PackageSpec and returns PackageMetadata (includes license URLs, authors, descriptions).
* **Reporter Layer**: Accepts a list of PackageMetadata and a Jinja2 template to render the final string.

### 5.2 Data Models

To normalize data across different sources (static vs. dynamic), we define a robust schema.

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class LicenseLink:
    """Represents a specific license attached to a package."""
    spdx_id: str          # e.g., "MIT", "Apache-2.0"
    name: str             # e.g., "MIT License" (Human readable)
    url: str              # The resolved URL (GitHub blob or SPDX definition)
    is_verified_file: bool # True if URL points to a specific file in the source repo

@dataclass
class PackageMetadata:
    """Enriched metadata for a dependency."""
    name: str
    version: str
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository_url: Optional[str] = None
    licenses: List[LicenseLink] = field(default_factory=list)
    is_root_project: bool = False # Flag for the project including the tracker
```

### 5.3 The "Waterfall" Resolution Algorithm

The core innovation of license_tracker is its ability to generate high-quality links. The resolution logic proceeds as follows:

**Step 1: Local Extraction (If available).**
* If running in EnvironmentScanner mode, check dist-info/METADATA for Project-URL and License headers. Note: PEP 639 is improving this, but legacy packages are messy.

**Step 2: Remote PyPI Enrichment.**
* If static scanning or local data is sparse, query `https://pypi.org/pypi/{name}/{version}/json`.
* Extract info.license and info.classifiers.
* Use license-expression to parse boolean logic (e.g., MIT OR Apache-2.0).

**Step 3: Repository Heuristic (The Linking Engine).**
* Extract the Source Code URL from PyPI metadata.
* If the URL matches github.com/{owner}/{repo}, normalize it.
* API Call: GET `https://api.github.com/repos/{owner}/{repo}/license`.
* Response Processing: The API returns the html_url to the license file. Crucially, to ensure immutability, the tool should attempt to rewrite this URL to use the specific commit hash or tag matching the installed version (e.g., blob/v1.0.0/LICENSE) rather than blob/main/LICENSE.
* Fallback: If the API call fails (404 or rate limit), fall back to step 4.

**Step 4: SPDX Fallback.**
* If the specific license file cannot be found, map the license classifier (e.g., License :: OSI Approved :: MIT License) to the SPDX ID MIT.
* Generate a generic URL: `https://spdx.org/licenses/MIT.html`.

### 5.4 Handling "The Project That Includes This Project"

The request requires the tool to document the project it is embedded within. This is often overlooked by tools like pip-licenses which only scan dependencies.

* **Implementation**: The Scanner must implement a scan_root() method.
* **Mechanism**: It parses the pyproject.toml, setup.cfg, or setup.py in the current working directory.
* **Logic**: It treats the current project as a PackageMetadata object with is_root_project=True. In the final report, this entry is typically placed at the top or in a separate "Project License" section via the Jinja2 template.

### 5.5 Jinja2 Templating Strategy

To satisfy the licenses.md generation requirement, the tool will use Jinja2. The default template will look like this:

```jinja2
# Open Source License Attribution

This project, {{ root.name }} ({{ root.license.name }}), utilizes the following open source libraries:

| Library | Version | License | Source |
|---|---|---|---|
{% for pkg in dependencies %}
| {{ pkg.name }} | {{ pkg.version }} | [{% for lic in pkg.licenses %}{{ lic.name }}{% if not loop.last %}, {% endif %}{% endfor %}]({{ pkg.licenses[0].url }}) | [Link]({{ pkg.homepage }}) |
{% endfor %}

---
*Generated by license_tracker*
```

This approach allows infinite customization. A user could provide a template that generates an HTML accordion, a CSV, or a ReStructuredText file.

## 6. Implementation Guide and Edge Case Handling

Writing a robust library requires handling the messy reality of the Python ecosystem.

### 6.1 Parsing poetry.lock and Pipfile.lock

* **Poetry**: The poetry.lock file is a TOML file. The parser must iterate over the [[package]] array. Crucially, poetry.lock often contains the name and version but NOT the license. This validates the design decision to strictly separate Scanning (finding names) from Resolution (finding licenses via API). You cannot generate a license report from poetry.lock alone; you must hit PyPI.
* **Pipenv**: Pipfile.lock is a JSON file. Dependencies are nested under default and develop. The scanner must flatten this structure and resolve valid versions.

### 6.2 The GitHub Rate Limit Problem

The GitHub API has a rate limit of 60 requests per hour for unauthenticated users. A medium-sized Django project can easily have 100+ dependencies (including transitives).

* **Solution**: license_tracker must accept a --github-token CLI flag or read GITHUB_TOKEN from the environment. With a token, the limit rises to 5,000 requests per hour.
* **Optimization**: Implement a local cache (e.g., ~/.cache/license_tracker/github_cache.sqlite). License URLs for specific package versions are immutable. Once resolved, they should never be fetched again.

### 6.3 Dual Licensing and Complex Expressions

Packages often have complex licensing (e.g., (MIT OR Apache-2.0)).

* **Handling**: The license-expression library parses this into a Python object. The PackageMetadata class supports a list of licenses. The Jinja2 template iterates through this list, creating comma-separated links: [MIT](url), [Apache 2.0](url). This ensures legal precision over simplification.

### 6.4 Vendorized Dependencies

A limitation of pip-licenses and pip-audit is the inability to see "vendorized" code (libraries copied directly into the source tree, common in pip and setuptools).

* **Policy**: license_tracker is a metadata tool, not a source scanner. It will not detect vendorized code by default.
* **Mitigation**: The tool should support a manual "overrides" or "additions" configuration file (e.g., license_tracker.toml) where users can manually list vendorized packages to include them in the report.

## 7. Operational Workflows and Integration

How does this tool fit into a professional development lifecycle?

### 7.1 Integration with Pre-Commit Hooks

To ensure licenses.md is always up to date, license_tracker should provide a pre-commit hook configuration.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/user/license_tracker
    rev: v1.0.0
    hooks:
      - id: license-tracker
        args: ["--output", "licenses.md", "--scan", "poetry.lock"]
```

This ensures that whenever a developer modifies dependencies (changing the lock file), the attribution file is regenerated automatically before the commit is accepted.

### 7.2 CI/CD Pipeline Integration

In a CI environment (e.g., GitHub Actions), the tool can function as a gatekeeper.

```yaml
# .github/workflows/compliance.yml
steps:
  - uses: actions/checkout@v3
  - name: Check Licenses
    run: |
      pip install license_tracker
      license-tracker check --forbidden "GPL-3.0, AGPL-3.0" --scan poetry.lock
```

The check command (distinct from generate) scans the resolved licenses against a deny-list and exits with a non-zero status code if a violation is found, blocking the deployment.

## 8. Conclusion

The landscape of open source compliance tools is populated by distinct categories of software: forensic scanners like scancode-toolkit which are powerful but heavy; security tools like pip-audit which are modern but focused on vulnerabilities; and metadata listers like pip-licenses which are useful but lack the connectivity to generate consumer-ready documentation with verified links.

The proposed license_tracker library fills a critical void. By treating license attribution as a documentation generation problem rather than purely a legal audit problem, it prioritizes developer experience and end-user accessibility. Its architecture—defined by the separation of static scanning from dynamic API-based resolution—allows it to function effectively in modern, containerized, and CI-driven workflows where installing full environments is undesirable. Furthermore, by strictly adhering to the user's requirement to link directly to license texts and include the root project's own metadata, license_tracker ensures a level of transparency and compliance rigor that manual processes simply cannot match.

This specification provides the blueprint for a tool that not only tracks compliance but automates trust in the software supply chain.
