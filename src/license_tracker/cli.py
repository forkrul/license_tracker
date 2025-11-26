"""Command-line interface for license_tracker.

Provides the main entry point and subcommands for generating license
attribution documentation and checking compliance.
"""

import asyncio
import logging
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from license_tracker.cache import LicenseCache
from license_tracker.models import PackageMetadata, PackageSpec
from license_tracker.reporters import MarkdownReporter
from license_tracker.resolvers import WaterfallResolver
from license_tracker.scanners import get_scanner

app = typer.Typer(
    name="license-tracker",
    help="Automated open source license attribution and compliance tool.",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger("license_tracker")


def _setup_logging(verbose: bool) -> None:
    """Configure logging level based on verbosity flag."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.getLogger("license_tracker").setLevel(level)


async def _scan_and_resolve(
    scan: Path,
    github_token: Optional[str],
    verbose: bool,
    use_cache: bool = True,
) -> tuple[list[PackageSpec], dict[PackageSpec, Optional[PackageMetadata]]]:
    """Scan lock file and resolve license metadata for all packages.

    This is shared logic used by both the gen and check commands.

    Args:
        scan: Path to the lock file.
        github_token: Optional GitHub API token.
        verbose: Whether to print verbose output.
        use_cache: Whether to use the license cache.

    Returns:
        Tuple of (list of package specs, dict of resolved metadata).

    Raises:
        ValueError: If scanner cannot be determined for the file.
        Exception: If scanning fails.
    """
    # Scan for packages
    scanner = get_scanner(scan)
    if verbose:
        console.print(f"[dim]Using scanner: {scanner.source_name}[/dim]")

    packages = scanner.scan()

    if not packages:
        return packages, {}

    # Check cache first
    cache = LicenseCache() if use_cache else None
    cached_count = 0
    to_resolve = []
    cached_metadata: dict[PackageSpec, Optional[PackageMetadata]] = {}

    for spec in packages:
        if cache:
            cached = cache.get(spec.name, spec.version)
            if cached:
                cached_count += 1
                cached_metadata[spec] = PackageMetadata(
                    name=spec.name,
                    version=spec.version,
                    licenses=cached,
                )
                continue
        to_resolve.append(spec)

    if cached_count > 0 and verbose:
        console.print(f"[dim]Using {cached_count} cached entries[/dim]")

    # Resolve uncached packages
    resolved_metadata: dict[PackageSpec, Optional[PackageMetadata]] = {}
    if to_resolve:
        async with WaterfallResolver(github_token=github_token) as resolver:
            results = await resolver.resolve_batch(to_resolve)

        for spec, metadata in results.items():
            resolved_metadata[spec] = metadata
            # Cache the result
            if cache and metadata and metadata.licenses:
                cache.set(spec.name, spec.version, metadata.licenses)

    # Combine results
    all_metadata = {**cached_metadata, **resolved_metadata}

    return packages, all_metadata


async def _run_gen(
    scan: Path,
    output: Path,
    include_root: bool,
    template: Optional[Path],
    github_token: Optional[str],
    verbose: bool,
) -> int:
    """Async implementation of the gen command."""
    _setup_logging(verbose)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning and resolving licenses...", total=None)

        try:
            packages, all_metadata = await _scan_and_resolve(
                scan=scan,
                github_token=github_token,
                verbose=verbose,
                use_cache=True,
            )
        except ValueError as e:
            err_console.print(f"[red]Error:[/red] {e}")
            return 1
        except Exception as e:
            err_console.print(f"[red]Error scanning {scan}:[/red] {e}")
            return 1

        progress.update(task, completed=True)

    if not packages:
        console.print("[yellow]No packages found in lock file[/yellow]")
        return 0

    console.print(f"Found [bold]{len(packages)}[/bold] packages")

    # Count results
    resolved_count = sum(1 for m in all_metadata.values() if m and m.licenses)
    console.print(
        f"Resolved licenses for [bold]{resolved_count}[/bold]/{len(packages)} packages"
    )

    # Step 3: Generate report
    metadata_list = [m for m in all_metadata.values() if m]

    # Sort by package name for consistent output
    metadata_list.sort(key=lambda m: m.name.lower())

    # Handle root project
    root_project = None
    if include_root:
        # TODO: Implement root project scanning
        if verbose:
            console.print("[dim]Root project inclusion not yet implemented[/dim]")

    # Create reporter
    if template:
        reporter = MarkdownReporter(template_path=template)
    else:
        reporter = MarkdownReporter()

    # Write output
    try:
        reporter.write(metadata_list, output, root_project=root_project)
        console.print(f"[green]Generated:[/green] {output}")
    except Exception as e:
        err_console.print(f"[red]Error writing output:[/red] {e}")
        return 1

    return 0


@app.command()
def gen(
    scan: Annotated[
        Path,
        typer.Option(
            "--scan",
            "-s",
            help="Path to lock file (poetry.lock, Pipfile.lock, requirements.txt)",
            exists=True,
            readable=True,
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output file path",
        ),
    ] = Path("licenses.md"),
    include_root: Annotated[
        bool,
        typer.Option(
            "--include-root",
            help="Include root project license in output",
        ),
    ] = False,
    template: Annotated[
        Optional[Path],
        typer.Option(
            "--template",
            "-t",
            help="Custom Jinja2 template file",
            exists=True,
            readable=True,
        ),
    ] = None,
    download: Annotated[
        bool,
        typer.Option(
            "--download",
            help="Download license files locally",
        ),
    ] = False,
    github_token: Annotated[
        Optional[str],
        typer.Option(
            "--github-token",
            envvar="GITHUB_TOKEN",
            help="GitHub API token for higher rate limits",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output",
        ),
    ] = False,
) -> None:
    """Generate license attribution documentation.

    Scans a lock file, resolves license metadata, and generates a
    formatted attribution document.
    """
    if download:
        console.print("[yellow]Warning: --download not yet implemented[/yellow]")

    exit_code = asyncio.run(
        _run_gen(
            scan=scan,
            output=output,
            include_root=include_root,
            template=template,
            github_token=github_token,
            verbose=verbose,
        )
    )
    raise typer.Exit(code=exit_code)


@app.command()
def check(
    scan: Annotated[
        Path,
        typer.Option(
            "--scan",
            "-s",
            help="Path to lock file (poetry.lock, Pipfile.lock, requirements.txt)",
            exists=True,
            readable=True,
        ),
    ],
    forbidden: Annotated[
        Optional[str],
        typer.Option(
            "--forbidden",
            "-f",
            help="Comma-separated list of forbidden SPDX license IDs",
        ),
    ] = None,
    allowed: Annotated[
        Optional[str],
        typer.Option(
            "--allowed",
            "-a",
            help="Comma-separated list of allowed SPDX license IDs (whitelist mode)",
        ),
    ] = None,
    github_token: Annotated[
        Optional[str],
        typer.Option(
            "--github-token",
            envvar="GITHUB_TOKEN",
            help="GitHub API token for higher rate limits",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output",
        ),
    ] = False,
) -> None:
    """Check license compliance against allow/deny lists.

    Scans dependencies and validates their licenses against the
    specified policy.

    Exit codes:
        0 - All licenses compliant
        1 - Violations found or error occurred
    """
    _setup_logging(verbose)

    if not forbidden and not allowed:
        err_console.print(
            "[red]Error:[/red] Must specify either --forbidden or --allowed"
        )
        raise typer.Exit(code=1)

    if forbidden and allowed:
        err_console.print(
            "[red]Error:[/red] Cannot specify both --forbidden and --allowed"
        )
        raise typer.Exit(code=1)

    # Parse license lists
    forbidden_set = set(forbidden.split(",")) if forbidden else set()
    allowed_set = set(allowed.split(",")) if allowed else set()

    # Scan and resolve using shared logic
    async def run_check():
        return await _scan_and_resolve(
            scan=scan,
            github_token=github_token,
            verbose=verbose,
            use_cache=True,
        )

    try:
        packages, results = asyncio.run(run_check())
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    if not packages:
        console.print("[green]No packages to check[/green]")
        raise typer.Exit(code=0)

    console.print(f"Checking [bold]{len(packages)}[/bold] packages...")

    # Check compliance
    violations = []
    unknown = []

    for spec, metadata in results.items():
        if not metadata or not metadata.licenses:
            unknown.append(spec.name)
            continue

        for license_link in metadata.licenses:
            spdx_id = license_link.spdx_id

            if forbidden_set and spdx_id in forbidden_set:
                violations.append((spec.name, spec.version, spdx_id))
            elif allowed_set and spdx_id not in allowed_set:
                violations.append((spec.name, spec.version, spdx_id))

    # Report results
    if unknown:
        console.print(f"\n[yellow]Unknown licenses ({len(unknown)}):[/yellow]")
        for name in sorted(unknown):
            console.print(f"  - {name}")

    if violations:
        console.print(f"\n[red]Violations ({len(violations)}):[/red]")
        for name, version, spdx_id in sorted(violations):
            console.print(f"  - {name}=={version}: {spdx_id}")
        raise typer.Exit(code=1)
    else:
        console.print(f"\n[green]All {len(packages)} packages are compliant![/green]")
        raise typer.Exit(code=0)


@app.command()
def cache(
    action: Annotated[
        str,
        typer.Argument(help="Cache action: 'show' or 'clear'"),
    ],
    package: Annotated[
        Optional[str],
        typer.Argument(help="Specific package to clear (optional)"),
    ] = None,
) -> None:
    """Manage the license resolution cache.

    Actions:
        show  - Display cache location, entry count, and size
        clear - Clear all cached entries (or specific package)
    """
    cache_instance = LicenseCache()

    if action == "show":
        info = cache_instance.info()
        console.print(f"[bold]Cache Location:[/bold] {info['path']}")
        console.print(f"[bold]Entries:[/bold] {info['count']}")
        console.print(f"[bold]Size:[/bold] {info['size_bytes'] / 1024:.1f} KB")

    elif action == "clear":
        if package:
            cache_instance.clear(package=package)
            console.print(f"[green]Cleared cache for:[/green] {package}")
        else:
            cache_instance.clear()
            console.print("[green]Cache cleared[/green]")

    else:
        err_console.print(f"[red]Unknown action:[/red] {action}")
        err_console.print("Valid actions: show, clear")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
