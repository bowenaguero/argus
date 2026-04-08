"""Tests for OrgCommand class."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from argus_cli.commands.org import OrgCommand


@pytest.fixture
def org_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "org"


@pytest.fixture
def org_command(mock_console, org_dir):
    cmd = OrgCommand(mock_console)
    cmd.config = MagicMock()
    cmd.config.db_org_dir = str(org_dir)
    return cmd


def _create_org_db(org_dir: Path, name: str, rows: list[tuple]) -> Path:
    """Helper to create a real SQLite org database."""
    org_dir.mkdir(parents=True, exist_ok=True)
    db_path = org_dir / f"{name}.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE data (ip TEXT PRIMARY KEY, org_id TEXT NOT NULL, platform TEXT NOT NULL)")
    conn.executemany("INSERT INTO data (ip, org_id, platform) VALUES (?, ?, ?)", rows)
    conn.commit()
    conn.close()
    return db_path


class TestOrgCommandImport:
    def test_import_csv(self, org_command, org_dir, tmp_path):
        csv_file = tmp_path / "ips.csv"
        csv_file.write_text("ip,org_id,platform\n8.8.8.8,GOOGLE,gcp\n1.1.1.1,CF,cloudflare\n")

        org_command.import_db(csv_file, name=None, force=False)

        assert (org_dir / "ips.db").exists()
        org_command.console.print.assert_called()
        call_str = str(org_command.console.print.call_args_list)
        assert "2 IPs" in call_str

    def test_import_with_custom_name(self, org_command, org_dir, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("ip,org_id,platform\n8.8.8.8,GOOGLE,gcp\n")

        org_command.import_db(csv_file, name="my_custom_db", force=False)

        assert (org_dir / "my_custom_db.db").exists()

    def test_import_uses_filename_as_default_name(self, org_command, org_dir, tmp_path):
        csv_file = tmp_path / "cloud_ips.csv"
        csv_file.write_text("ip,org_id,platform\n8.8.8.8,GOOGLE,gcp\n")

        org_command.import_db(csv_file, name=None, force=False)

        assert (org_dir / "cloud_ips.db").exists()

    def test_import_shows_skipped_count(self, org_command, org_dir, tmp_path):
        csv_file = tmp_path / "mixed.csv"
        csv_file.write_text("ip,org_id,platform\n8.8.8.8,GOOGLE,gcp\ninvalid,BAD,aws\n")

        org_command.import_db(csv_file, name=None, force=False)

        call_str = str(org_command.console.print.call_args_list)
        assert "Skipped 1" in call_str


class TestOrgCommandList:
    def test_list_empty(self, org_command):
        org_command.list_dbs()

        call_str = str(org_command.console.print.call_args_list)
        assert "No org databases found" in call_str

    def test_list_with_databases(self, org_command, org_dir):
        _create_org_db(org_dir, "cloud", [("8.8.8.8", "GOOGLE", "gcp")])
        _create_org_db(
            org_dir,
            "office",
            [
                ("10.0.0.1", "ACME", "on-prem"),
                ("10.0.0.2", "ACME", "on-prem"),
            ],
        )

        org_command.list_dbs()

        org_command.console.print.assert_called()

    def test_list_no_org_dir(self, org_command):
        org_command.list_dbs()

        call_str = str(org_command.console.print.call_args_list)
        assert "No org databases found" in call_str


class TestOrgCommandRemove:
    def test_remove_nonexistent(self, org_command, org_dir):
        org_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(typer.Exit):
            org_command.remove_db("nonexistent", force=True)

    def test_remove_with_force(self, org_command, org_dir):
        db_path = _create_org_db(org_dir, "test_db", [("8.8.8.8", "GOOGLE", "gcp")])
        assert db_path.exists()

        org_command.remove_db("test_db", force=True)

        assert not db_path.exists()
        call_str = str(org_command.console.print.call_args_list)
        assert "Removed" in call_str

    def test_remove_with_confirmation(self, org_command, org_dir):
        db_path = _create_org_db(org_dir, "test_db", [("8.8.8.8", "GOOGLE", "gcp")])

        with patch("argus_cli.commands.org.typer.confirm", return_value=True):
            org_command.remove_db("test_db", force=False)

        assert not db_path.exists()

    def test_remove_cancelled(self, org_command, org_dir):
        db_path = _create_org_db(org_dir, "test_db", [("8.8.8.8", "GOOGLE", "gcp")])

        with patch("argus_cli.commands.org.typer.confirm", return_value=False), pytest.raises(typer.Exit):
            org_command.remove_db("test_db", force=False)

        assert db_path.exists()


class TestOrgCommandHelpers:
    def test_format_size_bytes(self):
        assert OrgCommand._format_size(500) == "500 B"

    def test_format_size_kb(self):
        assert OrgCommand._format_size(2048) == "2 KB"

    def test_format_size_mb(self):
        assert OrgCommand._format_size(2 * 1024 * 1024) == "2.0 MB"

    def test_get_row_count(self, org_dir):
        db_path = _create_org_db(
            org_dir,
            "test",
            [
                ("8.8.8.8", "GOOGLE", "gcp"),
                ("1.1.1.1", "CF", "cloudflare"),
            ],
        )
        assert OrgCommand._get_row_count(db_path) == 2

    def test_get_row_count_bad_file(self, tmp_path):
        bad_file = tmp_path / "bad.db"
        bad_file.write_text("not a database")
        assert OrgCommand._get_row_count(bad_file) == -1
