"""Tests for OrgImporter service."""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from argus_cli.core.exceptions import FileOperationError, ValidationError
from argus_cli.services.org_import import OrgImporter


@pytest.fixture
def org_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "org"


@pytest.fixture
def importer(org_dir):
    return OrgImporter(str(org_dir))


@pytest.fixture
def csv_file(tmp_path):
    f = tmp_path / "test.csv"
    f.write_text("ip,org_id,platform\n8.8.8.8,GOOGLE,gcp\n1.1.1.1,CLOUDFLARE,cloudflare\n")
    return f


@pytest.fixture
def json_file(tmp_path):
    f = tmp_path / "test.json"
    data = [
        {"ip": "8.8.8.8", "org_id": "GOOGLE", "platform": "gcp"},
        {"ip": "1.1.1.1", "org_id": "CLOUDFLARE", "platform": "cloudflare"},
    ]
    f.write_text(json.dumps(data))
    return f


class TestOrgImporterCSV:
    def test_import_csv_success(self, importer, csv_file, org_dir):
        result = importer.import_file(csv_file, "test_org")
        assert result.imported == 2
        assert result.skipped == 0
        assert (org_dir / "test_org.db").exists()

    def test_import_csv_creates_valid_sqlite(self, importer, csv_file, org_dir):
        importer.import_file(csv_file, "test_org")

        conn = sqlite3.connect(str(org_dir / "test_org.db"))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT ip, org_id, platform FROM data ORDER BY ip").fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0]["ip"] == "1.1.1.1"
        assert rows[0]["org_id"] == "CLOUDFLARE"
        assert rows[1]["ip"] == "8.8.8.8"
        assert rows[1]["platform"] == "gcp"

    def test_import_csv_missing_columns(self, importer, tmp_path):
        f = tmp_path / "bad.csv"
        f.write_text("ip,name\n8.8.8.8,test\n")

        with pytest.raises(ValidationError, match="missing required columns"):
            importer.import_file(f, "bad")

    def test_import_csv_empty(self, importer, tmp_path):
        f = tmp_path / "empty.csv"
        f.write_text("")

        with pytest.raises(ValidationError, match="CSV file is empty"):
            importer.import_file(f, "empty")

    def test_import_csv_skips_invalid_ips(self, importer, tmp_path):
        f = tmp_path / "mixed.csv"
        f.write_text(
            "ip,org_id,platform\n"
            "8.8.8.8,GOOGLE,gcp\n"
            "not_an_ip,BAD,aws\n"
            "999.999.999.999,BAD,azure\n"
            "1.1.1.1,CF,cloudflare\n"
        )
        result = importer.import_file(f, "mixed")
        assert result.imported == 2
        assert result.skipped == 2
        assert "not_an_ip" in result.skipped_ips
        assert "999.999.999.999" in result.skipped_ips

    def test_import_csv_extra_columns_ignored(self, importer, tmp_path):
        f = tmp_path / "extra.csv"
        f.write_text("ip,org_id,platform,notes,owner\n8.8.8.8,GOOGLE,gcp,dns,infra\n")
        result = importer.import_file(f, "extra")
        assert result.imported == 1


class TestOrgImporterJSON:
    def test_import_json_success(self, importer, json_file, org_dir):
        result = importer.import_file(json_file, "test_org")
        assert result.imported == 2
        assert result.skipped == 0
        assert (org_dir / "test_org.db").exists()

    def test_import_json_missing_keys(self, importer, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps([{"ip": "8.8.8.8", "name": "test"}]))

        with pytest.raises(ValidationError, match="missing required keys"):
            importer.import_file(f, "bad")

    def test_import_json_not_array(self, importer, tmp_path):
        f = tmp_path / "obj.json"
        f.write_text(json.dumps({"ip": "8.8.8.8"}))

        with pytest.raises(ValidationError, match="must be an array"):
            importer.import_file(f, "obj")

    def test_import_json_empty_array(self, importer, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]")

        with pytest.raises(ValidationError, match="array is empty"):
            importer.import_file(f, "empty")

    def test_import_json_invalid_json(self, importer, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{not valid json")

        with pytest.raises(FileOperationError, match="Invalid JSON"):
            importer.import_file(f, "bad")

    def test_import_json_skips_invalid_ips(self, importer, tmp_path):
        f = tmp_path / "mixed.json"
        data = [
            {"ip": "8.8.8.8", "org_id": "GOOGLE", "platform": "gcp"},
            {"ip": "invalid", "org_id": "BAD", "platform": "aws"},
        ]
        f.write_text(json.dumps(data))

        result = importer.import_file(f, "mixed")
        assert result.imported == 1
        assert result.skipped == 1


class TestOrgImporterOverwrite:
    def test_import_refuses_overwrite_by_default(self, importer, csv_file, org_dir):
        importer.import_file(csv_file, "test_org")

        with pytest.raises(FileOperationError, match="already exists"):
            importer.import_file(csv_file, "test_org")

    def test_import_force_overwrites(self, importer, csv_file, org_dir):
        importer.import_file(csv_file, "test_org")
        result = importer.import_file(csv_file, "test_org", force=True)
        assert result.imported == 2


class TestOrgImporterUnsupportedFormat:
    def test_import_unsupported_extension(self, importer, tmp_path):
        f = tmp_path / "data.xml"
        f.write_text("<data/>")

        with pytest.raises(ValidationError, match="Unsupported file format"):
            importer.import_file(f, "data")
