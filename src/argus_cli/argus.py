from pathlib import Path
from typing import Annotated

import click
import typer
from rich.console import Console

from . import __version__
from .commands.lookup import LookupCommand
from .commands.org import OrgCommand
from .commands.setup import SetupCommand
from .core.config import Config
from .core.exceptions import ArgusError
from .services.updater import UpdateChecker
from .utils.logger import get_logger
from .utils.validators import ParameterValidator

console = Console()
logger = get_logger(console)

app = typer.Typer(
    help="IP lookup and enrichment",
    add_completion=False,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"argus {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version and exit"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output for debugging"),
    ] = False,
) -> None:
    if verbose:
        logger.set_verbose()
    UpdateChecker(Config(), console).notify_if_update_available()


@app.command(help="Initial setup for Argus CLI (run this first)")
def setup():
    """Configure API keys for Argus CLI."""
    try:
        setup_cmd = SetupCommand(console)
        setup_cmd.execute()
    except ArgusError as e:
        logger.exception("Error during setup")
        raise typer.Exit(1) from e
    except Exception as e:
        logger.exception("Unexpected error during setup")
        raise typer.Exit(1) from e


@app.command(help="Lookup an IP address")
def lookup(
    ip: Annotated[str | None, typer.Argument(help="IP address to lookup")] = None,
    file: Annotated[Path | None, typer.Option("-f", "--file", help="Extract IPs from file")] = None,
    output_format: Annotated[
        str,
        typer.Option(
            "-fmt",
            "--format",
            click_type=click.Choice(["json", "csv"]),
            help="Output file format",
        ),
    ] = "json",
    exclude_country: Annotated[
        list[str] | None,
        typer.Option(
            "-xc",
            "--exclude-country",
            help="Exclude IPs from country (e.g., Germany, China)",
        ),
    ] = None,
    exclude_city: Annotated[
        list[str] | None,
        typer.Option("-xct", "--exclude-city", help="Exclude IPs from city (case-insensitive)"),
    ] = None,
    exclude_asn: Annotated[
        list[int] | None,
        typer.Option("-xa", "--exclude-asn", help="Exclude IPs from ASN (e.g., 15169)"),
    ] = None,
    exclude_org: Annotated[
        list[str] | None,
        typer.Option(
            "-xo",
            "--exclude-org",
            help="Exclude IPs from organizations containing text (case-insensitive)",
        ),
    ] = None,
    exclude_org_managed: Annotated[
        bool,
        typer.Option(
            "--exclude-org-managed",
            help="Exclude IPs where org_managed is True",
        ),
    ] = False,
    exclude_not_org_managed: Annotated[
        bool,
        typer.Option(
            "--exclude-not-org-managed",
            help="Exclude IPs where org_managed is False",
        ),
    ] = False,
    exclude_platform: Annotated[
        list[str] | None,
        typer.Option(
            "-xp",
            "--exclude-platform",
            help="Exclude IPs by platform (e.g., aws, azure)",
        ),
    ] = None,
    exclude_org_id: Annotated[
        list[str] | None,
        typer.Option(
            "-xoi",
            "--exclude-org-id",
            help="Exclude IPs by org ID",
        ),
    ] = None,
    sort_by: Annotated[
        str,
        typer.Option(
            "--sort-by",
            click_type=click.Choice(["ip", "domain", "city", "country", "asn", "asn_org"]),
            help="Sort results by field (default: asn_org)",
        ),
    ] = "asn_org",
    output: Annotated[
        str | None,
        typer.Option(
            "-o",
            "--output",
            help="Write results to file. Use '-o -' for auto-naming (argus_results_TIMESTAMP.json)",
        ),
    ] = None,
):
    """Perform IP lookup with optional filtering and output options."""
    try:
        # Validate parameters
        if ip:
            ParameterValidator.validate_ip(ip)

        if file:
            ParameterValidator.validate_file_path(file)

        ParameterValidator.validate_output_path(output or "")
        ParameterValidator.validate_sort_by(sort_by)

        if exclude_asn:
            ParameterValidator.validate_asn_numbers(exclude_asn)

        if exclude_country:
            ParameterValidator.validate_country_names(exclude_country)

        # Execute lookup
        lookup_cmd = LookupCommand(console)
        lookup_cmd.execute(
            ip=ip,
            file=file,
            output=output,
            output_format=output_format,
            exclude_country=exclude_country,
            exclude_city=exclude_city,
            exclude_asn=exclude_asn,
            exclude_org=exclude_org,
            exclude_org_managed=exclude_org_managed,
            exclude_not_org_managed=exclude_not_org_managed,
            exclude_platform=exclude_platform,
            exclude_org_id=exclude_org_id,
            sort_by=sort_by,
        )

    except ArgusError:
        logger.exception("Error during lookup")
        raise typer.Exit(code=1) from None
    except Exception:
        logger.exception("Unexpected error during lookup")
        raise typer.Exit(code=1) from None


org_app = typer.Typer(help="Manage org IP databases", no_args_is_help=True)
app.add_typer(org_app, name="org")


@org_app.command(name="import", help="Import IPs from CSV or JSON into an org database")
def org_import(
    file: Annotated[Path, typer.Argument(help="CSV or JSON file to import")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Database name (default: filename)")] = None,
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing database")] = False,
):
    """Import org IPs from a CSV or JSON file."""
    try:
        ParameterValidator.validate_file_path(file)
        org_cmd = OrgCommand(console)
        org_cmd.import_db(file, name, force)
    except ArgusError:
        logger.exception("Error during org import")
        raise typer.Exit(code=1) from None
    except Exception:
        logger.exception("Unexpected error during org import")
        raise typer.Exit(code=1) from None


@org_app.command(name="list", help="List org databases")
def org_list():
    """Show all org databases with row counts."""
    try:
        org_cmd = OrgCommand(console)
        org_cmd.list_dbs()
    except Exception:
        logger.exception("Unexpected error listing org databases")
        raise typer.Exit(code=1) from None


@org_app.command(name="export", help="Export an org database to CSV")
def org_export(
    name: Annotated[str, typer.Argument(help="Name of the org database to export")],
    output: Annotated[
        Path | None, typer.Option("-o", "--output", help="Output file path (default: <name>.csv)")
    ] = None,
):
    """Export an org database to a CSV file."""
    try:
        org_cmd = OrgCommand(console)
        org_cmd.export_db(name, output)
    except ArgusError:
        logger.exception("Error exporting org database")
        raise typer.Exit(code=1) from None
    except Exception:
        logger.exception("Unexpected error exporting org database")
        raise typer.Exit(code=1) from None


@org_app.command(name="remove", help="Remove an org database")
def org_remove(
    name: Annotated[str, typer.Argument(help="Name of the org database to remove")],
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation prompt")] = False,
):
    """Remove an org database."""
    try:
        org_cmd = OrgCommand(console)
        org_cmd.remove_db(name, force)
    except ArgusError:
        logger.exception("Error removing org database")
        raise typer.Exit(code=1) from None
    except Exception:
        logger.exception("Unexpected error removing org database")
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
