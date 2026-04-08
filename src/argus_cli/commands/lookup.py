import time
from pathlib import Path

import typer
from rich.console import Console

from ..core.config import Config
from ..services.database import DatabaseManager
from ..services.lookup import GeoIPLookup
from ..utils.filters import ResultFilter
from ..utils.formatter import ResultFormatter
from ..utils.parser import FileParser


class LookupCommand:
    def __init__(self, console: Console):
        self.console = console
        self.config = Config()
        self.db_manager = DatabaseManager(self.config, self.console)
        self.lookup_service = GeoIPLookup(
            self.config.db_city, self.config.db_asn, self.config.db_proxy, self.config.db_org_dir
        )
        self.file_parser = FileParser()
        self.formatter = ResultFormatter(self.console)

    def execute(
        self,
        ip: str | None,
        file: Path | None,
        output: str | None,
        output_format: str,
        exclude_country: list[str] | None,
        exclude_city: list[str] | None,
        exclude_asn: list[int] | None,
        exclude_org: list[str] | None,
        exclude_org_managed: bool,
        exclude_not_org_managed: bool,
        exclude_platform: list[str] | None,
        exclude_org_id: list[str] | None,
        sort_by: str,
    ) -> list[dict] | None:
        if not ip and not file:
            self.console.print("[yellow]No IP or file provided. Use --help for usage information.[/yellow]")
            raise typer.Exit(0)

        if output == "-":
            output = ""

        start_time = time.time()

        self.db_manager.ensure_databases()

        ips = self._collect_ips(ip, file)
        if not ips:
            return None

        try:
            results = self.lookup_service.lookup_ips(ips)
        except Exception as e:
            self.console.print(f"[red]✗ Error:[/red] {e}", style="bold")
            raise typer.Exit(1) from e

        filtered_results = self._filter_results(
            results,
            exclude_country,
            exclude_city,
            exclude_asn,
            exclude_org,
            exclude_org_managed,
            exclude_not_org_managed,
            exclude_platform,
            exclude_org_id,
        )

        sorted_results = self._sort_results(filtered_results, sort_by)

        self.console.print(self.formatter.format_table(sorted_results))

        if output is not None:
            self.formatter.write_to_file(sorted_results, output, output_format)

        elapsed_time = time.time() - start_time
        self.console.print(f"\n[dim]Processed {len(ips)} IP(s) in {elapsed_time:.2f}s[/dim]")

        return sorted_results

    def _collect_ips(self, ip: str | None, file: Path | None) -> list[str]:
        ips = []
        if ip:
            if "/" in ip:
                try:
                    expanded = self.file_parser.expand_cidr(ip)
                    ips.extend(expanded)
                    self.console.print(f"[green]✓[/green] Expanded CIDR block {ip} into {len(expanded)} IP(s)")
                except ValueError as e:
                    self.console.print(f"[red]✗ Error:[/red] {e}")
                    raise typer.Exit(1) from e
            else:
                ips.append(ip)
        if file:
            try:
                with self.console.status(f"[bold blue]Reading file {file}...", spinner="dots"):
                    content = self.file_parser.read_file_content(str(file))
                    extracted = self.file_parser.extract_ips(content)
                if extracted:
                    ips.extend(extracted)
                    self.console.print(f"[green]✓[/green] Extracted {len(extracted)} unique public IP(s) from file")
                else:
                    self.console.print("[yellow]⚠[/yellow] Warning: No public IPs found in file")
            except FileNotFoundError as e:
                self.console.print(f"[red]✗ Error:[/red] File '[cyan]{file}[/cyan]' not found")
                raise typer.Exit(1) from e
        return ips

    def _filter_results(
        self,
        results: list[dict],
        exclude_country: list[str] | None,
        exclude_city: list[str] | None,
        exclude_asn: list[int] | None,
        exclude_org: list[str] | None,
        exclude_org_managed: bool,
        exclude_not_org_managed: bool,
        exclude_platform: list[str] | None,
        exclude_org_id: list[str] | None,
    ) -> list[dict]:
        result_filter = ResultFilter(
            exclude_countries=exclude_country,
            exclude_cities=exclude_city,
            exclude_asns=exclude_asn,
            exclude_orgs=exclude_org,
            exclude_org_managed=exclude_org_managed,
            exclude_not_org_managed=exclude_not_org_managed,
            exclude_platforms=exclude_platform,
            exclude_org_ids=exclude_org_id,
        )
        filtered_results = result_filter.filter_results(results)

        if len(filtered_results) < len(results):
            self.console.print(f"[yellow][i][/i][/yellow] Filtered out {len(results) - len(filtered_results)} IP(s)")

        return filtered_results

    def _sort_results(self, results: list[dict], sort_by: str) -> list[dict]:
        def sort_key(x):
            val = x.get(sort_by)
            if val is None:
                return (True, 0)  # None values go to the end
            return (False, val)

        return sorted(results, key=sort_key)
