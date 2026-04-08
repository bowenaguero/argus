import os
import sqlite3
from contextlib import suppress
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..core.config import Config
from ..services.org_import import OrgImporter


class OrgCommand:
    def __init__(self, console: Console):
        self.console = console
        self.config = Config()

    def import_db(self, file: Path, name: str | None, force: bool) -> None:
        db_name = name or file.stem

        self.console.print(f"[bold cyan]Importing org database from {file.name}...[/bold cyan]")

        importer = OrgImporter(self.config.db_org_dir)
        result = importer.import_file(file, db_name, force=force)

        if result.skipped > 0:
            self.console.print(f"[yellow]Skipped {result.skipped} invalid IP(s)[/yellow]")

        self.console.print(f"[green]✓[/green] Created org database: [cyan]{db_name}[/cyan] ({result.imported:,} IPs)")

    def list_dbs(self) -> None:
        org_dir = Path(self.config.db_org_dir)
        if not org_dir.exists():
            self.console.print("[yellow]No org databases found.[/yellow]")
            self.console.print("[dim]Import one with: argus org import <file>[/dim]")
            return

        db_files = sorted(org_dir.glob("*.db"))
        if not db_files:
            self.console.print("[yellow]No org databases found.[/yellow]")
            self.console.print("[dim]Import one with: argus org import <file>[/dim]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("IPs", justify="right")
        table.add_column("Size", justify="right")

        for db_file in db_files:
            row_count = self._get_row_count(db_file)
            size = self._format_size(db_file.stat().st_size)
            table.add_row(db_file.stem, f"{row_count:,}" if row_count >= 0 else "error", size)

        self.console.print(f"\n[bold]Org Databases ({len(db_files)} found):[/bold]")
        self.console.print(table)

    def remove_db(self, name: str, force: bool) -> None:
        db_path = Path(self.config.db_org_dir) / f"{name}.db"

        if not db_path.exists():
            self.console.print(f"[red]✗ Error:[/red] Org database '{name}' not found")
            raise typer.Exit(1)

        if not force:
            confirm = typer.confirm(f"Remove org database '{name}'?", default=False)
            if not confirm:
                self.console.print("[yellow]Cancelled[/yellow]")
                raise typer.Exit(0)

        os.remove(db_path)
        self.console.print(f"[green]✓[/green] Removed {name}.db")

    @staticmethod
    def _get_row_count(db_path: Path) -> int:
        with suppress(Exception):
            conn = sqlite3.connect(str(db_path))
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM data")
                return cursor.fetchone()[0]
            finally:
                conn.close()
        return -1

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.0f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
