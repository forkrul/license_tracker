Architecture
============

License Tracker uses a modular architecture with three main components:
Scanners, Resolvers, and Reporters.

System Overview
---------------

.. mermaid::

   flowchart TB
       subgraph Input["Input Sources"]
           PL[poetry.lock]
           PF[Pipfile.lock]
           RT[requirements.txt]
       end

       subgraph Scanners["Scanners"]
           PS[PoetryScanner]
           PIS[PipenvScanner]
           RS[RequirementsScanner]
       end

       subgraph Resolution["License Resolution"]
           WR[WaterfallResolver]
           PyPI[PyPIResolver]
           GH[GitHubResolver]
           SPDX[SPDXResolver]
           Cache[(SQLite Cache)]
       end

       subgraph Output["Output"]
           MR[MarkdownReporter]
           MD[licenses.md]
       end

       PL --> PS
       PF --> PIS
       RT --> RS

       PS --> WR
       PIS --> WR
       RS --> WR

       WR --> Cache
       Cache -.->|miss| PyPI
       PyPI --> GH
       GH --> SPDX

       WR --> MR
       MR --> MD

Scanners
--------

Scanners parse dependency lock files and extract package specifications.

.. mermaid::

   classDiagram
       class BaseScanner {
           <<abstract>>
           +source_name: str
           +scan() list~PackageSpec~
       }
       class PoetryScanner {
           +source_name = "poetry.lock"
           +scan() list~PackageSpec~
       }
       class PipenvScanner {
           +source_name = "Pipfile.lock"
           +scan() list~PackageSpec~
       }
       class RequirementsScanner {
           +source_name = "requirements.txt"
           +scan() list~PackageSpec~
       }

       BaseScanner <|-- PoetryScanner
       BaseScanner <|-- PipenvScanner
       BaseScanner <|-- RequirementsScanner

Resolvers
---------

Resolvers fetch license metadata from external sources.

**Resolution Order (Waterfall Strategy):**

1. **Cache**: Check SQLite cache for previously resolved licenses
2. **PyPI**: Fetch metadata from PyPI JSON API, normalize to SPDX
3. **GitHub**: If repository URL exists, fetch verified LICENSE file link
4. **SPDX**: Fallback to generic SPDX license page URL

.. mermaid::

   sequenceDiagram
       participant CLI
       participant WR as WaterfallResolver
       participant Cache
       participant PyPI as PyPIResolver
       participant GH as GitHubResolver

       CLI->>WR: resolve(PackageSpec)
       WR->>Cache: get(name, version)

       alt Cache Hit
           Cache-->>WR: LicenseLink[]
       else Cache Miss
           WR->>PyPI: resolve(spec)
           PyPI-->>WR: PackageMetadata

           alt Has Repository URL
               WR->>GH: enrich(spec, metadata)
               GH-->>WR: Enriched Metadata
           end

           WR->>Cache: set(name, version, licenses)
       end

       WR-->>CLI: PackageMetadata

Reporters
---------

Reporters generate output files from resolved package metadata.

Currently supported:

- **MarkdownReporter**: Generates Markdown with Jinja2 templates

Data Models
-----------

.. mermaid::

   classDiagram
       class PackageSpec {
           +name: str
           +version: str
       }

       class LicenseLink {
           +spdx_id: str
           +name: str
           +url: str
           +is_verified_file: bool
       }

       class PackageMetadata {
           +name: str
           +version: str
           +description: str
           +homepage: str
           +repository_url: str
           +author: str
           +licenses: list~LicenseLink~
           +is_root_project: bool
       }

       PackageMetadata --> "*" LicenseLink
