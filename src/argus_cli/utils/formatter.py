from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..core.exceptions import FileOperationError

if TYPE_CHECKING:
    from ..services.lookup import DataSourceCapabilities


class ResultFormatter:
    def __init__(self, console: Console):
        self.console = console

    def format_json(self, results: list[dict]) -> str:
        return json.dumps(results, indent=2)

    def format_table(self, results: list[dict], capabilities: DataSourceCapabilities | None = None) -> Table | Panel:
        return (
            self._format_panel(results[0]) if len(results) == 1 else self._format_grouped_table(results, capabilities)
        )

    def _format_panel(self, result: dict) -> Panel:
        if result.get("error"):
            content = Text(f"ERROR: {result['error']}", style="bold red")
            return Panel(content, title=f"[cyan]{result['ip']}[/cyan]", border_style="red")

        lines = self.create_panel_lines(result)
        content = Text("\n").join(lines) if lines else Text("No additional information available", style="dim")
        border_style = "bright_green" if result.get("org_managed") else "cyan"
        return Panel(content, title=f"[cyan]{result['ip']}[/cyan]", border_style=border_style)

    def create_panel_lines(self, result: dict) -> list[Text]:
        lines = []

        if result.get("org_managed"):
            org_text = f"✓ {result.get('org_id', 'Unknown')}"
            if result.get("platform"):
                org_text += f" ({result['platform']})"
            lines.append(Text("Org Managed: ", style="bright_green") + Text(org_text, style="bright_cyan"))

        location_parts = [p for p in [result.get("city"), result.get("country")] if p]
        if location_parts:
            lines.append(Text("Location: ", style="yellow") + Text(", ".join(location_parts)))

        asn_parts = []
        if result.get("asn"):
            asn_parts.append(f"AS{result['asn']}")
        if result.get("asn_org"):
            asn_parts.append(f"({result['asn_org']})")
        if asn_parts:
            lines.append(Text("ASN: ", style="magenta") + Text(" ".join(asn_parts)))

        if result.get("domain"):
            lines.append(Text("Domain: ", style="bright_cyan") + Text(result["domain"]))

        proxy_parts = [
            p
            for p in [result.get("proxy_type"), f"({result.get('usage_type')})" if result.get("usage_type") else None]
            if p
        ]
        if proxy_parts:
            lines.append(Text("Proxy: ", style="red") + Text(" ".join(proxy_parts)))

        return lines

    def _format_grouped_table(self, results: list[dict], capabilities: DataSourceCapabilities | None = None) -> Table:
        show_org = capabilities is None or capabilities.has_org
        show_proxy = capabilities is None or capabilities.has_proxy

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("IP", style="cyan", no_wrap=True)
        if show_org:
            table.add_column("Org Info", style="bright_green")
        if show_proxy:
            table.add_column("Proxy", style="red")
        table.add_column("Network", style="bright_cyan")
        table.add_column("Location", style="yellow")

        for r in results:
            if r.get("error"):
                row = [r["ip"]]
                if show_org:
                    row.append("")
                if show_proxy:
                    row.append("")
                row.append(f"[red]ERROR: {r['error']}[/red]")
                row.append("")
                table.add_row(*row)
            else:
                row = [r["ip"]]
                if show_org:
                    row.append(self._format_org_cell(r))
                if show_proxy:
                    row.append(self._format_proxy_cell(r))
                row.append(self._format_network_cell(r))
                row.append(self._format_location_cell(r))
                table.add_row(*row)

        return table

    def _format_org_cell(self, result: dict) -> str:
        if not result.get("org_managed"):
            return "-"

        parts = ["✓"]
        if result.get("org_id"):
            parts.append(result["org_id"])
        if result.get("platform"):
            parts.append(f"({result['platform']})")
        return " ".join(parts)

    def _format_proxy_cell(self, result: dict) -> str:
        parts = []
        if result.get("proxy_type"):
            parts.append(result["proxy_type"])
        if result.get("usage_type"):
            parts.append(f"({result['usage_type']})")
        return " ".join(parts) if parts else "-"

    def _format_network_cell(self, result: dict) -> str:
        parts = []
        if result.get("domain"):
            parts.append(result["domain"])
        if result.get("asn"):
            asn_str = f"AS{result['asn']}"
            if result.get("asn_org"):
                asn_str += f" ({result['asn_org']})"
            parts.append(asn_str)
        return "\n".join(parts) if parts else "-"

    def _format_location_cell(self, result: dict) -> str:
        location_parts = [p for p in [result.get("city"), result.get("country")] if p]
        return ", ".join(location_parts) if location_parts else "-"

    def format_csv(self, results: list[dict], capabilities: DataSourceCapabilities | None = None) -> str:
        if not results:
            return ""

        show_org = capabilities is None or capabilities.has_org
        show_proxy = capabilities is None or capabilities.has_proxy

        fieldnames = ["ip"]
        if show_org:
            fieldnames.extend(["org_managed", "org_id", "platform"])
        if show_proxy:
            fieldnames.append("proxy_type")
        show_domain = capabilities is None or capabilities.has_ipinfo
        if show_domain:
            fieldnames.append("domain")
        fieldnames.extend(["city", "region", "country", "iso_code", "postal"])
        if show_proxy:
            fieldnames.extend(["isp", "usage_type"])
        fieldnames.extend(["asn", "asn_org", "error"])

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow(fieldnames)

        for result in results:
            row = [str(result.get(field, "") or "") for field in fieldnames]
            writer.writerow(row)

        return output.getvalue().rstrip("\r\n")

    def write_to_file(
        self,
        results: list[dict],
        output_file: str | None,
        file_format: str = "json",
        capabilities: DataSourceCapabilities | None = None,
    ) -> None:
        file_path: str
        if output_file == "":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = "json" if file_format == "json" else "csv"
            file_path = f"argus_results_{timestamp}.{extension}"
        else:
            file_path = output_file if output_file is not None else "argus_results.json"

        try:
            if file_format == "csv":
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.format_csv(results, capabilities))
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)

            self.console.print(f"[green]✓[/green] Results written to [cyan]{file_path}[/cyan]")
        except Exception as e:
            raise FileOperationError(f"Error writing to file: {e}") from e  # noqa: TRY003
