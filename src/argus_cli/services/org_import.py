import csv
import ipaddress
import json
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from ..core.exceptions import FileOperationError, ValidationError

REQUIRED_COLUMNS = {"ip", "org_id", "platform"}


@dataclass
class ImportResult:
    imported: int = 0
    skipped: int = 0
    skipped_ips: list[str] = field(default_factory=list)
    db_path: str = ""


class OrgImporter:
    def __init__(self, org_db_dir: str):
        self.org_db_dir = Path(org_db_dir)

    def import_file(self, file_path: Path, db_name: str, force: bool = False) -> ImportResult:
        db_path = self.org_db_dir / f"{db_name}.db"

        if db_path.exists() and not force:
            raise FileOperationError(  # noqa: TRY003
                f"Org database '{db_name}' already exists. Use --force to overwrite.",
            )

        rows = self._parse_file(file_path)
        result = self._validate_rows(rows)

        self.org_db_dir.mkdir(parents=True, exist_ok=True)
        self._write_sqlite(db_path, result.valid_rows)

        return ImportResult(
            imported=len(result.valid_rows),
            skipped=len(result.skipped_ips),
            skipped_ips=result.skipped_ips,
            db_path=str(db_path),
        )

    def _parse_file(self, file_path: Path) -> list[dict]:
        ext = file_path.suffix.lower()
        if ext == ".csv":
            return self._parse_csv(file_path)
        elif ext == ".json":
            return self._parse_json(file_path)
        else:
            raise ValidationError(f"Unsupported file format: {ext}. Use .csv or .json")  # noqa: TRY003

    def _parse_csv(self, file_path: Path) -> list[dict]:
        try:
            f = open(file_path, encoding="utf-8", newline="")  # noqa: SIM115
        except Exception as e:
            raise FileOperationError(f"Error reading CSV file: {e}") from e  # noqa: TRY003

        try:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ValidationError("CSV file is empty")  # noqa: TRY003

            missing = REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing:
                raise ValidationError(  # noqa: TRY003
                    f"CSV missing required columns: {', '.join(sorted(missing))}. Required: ip, org_id, platform",
                )

            return list(reader)
        finally:
            f.close()

    def _parse_json(self, file_path: Path) -> list[dict]:
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise FileOperationError(f"Invalid JSON: {e}") from e  # noqa: TRY003
        except Exception as e:
            raise FileOperationError(f"Error reading JSON file: {e}") from e  # noqa: TRY003

        if not isinstance(data, list):
            raise ValidationError("JSON must be an array of objects")  # noqa: TRY003

        if not data:
            raise ValidationError("JSON array is empty")  # noqa: TRY003

        first = data[0]
        if not isinstance(first, dict):
            raise ValidationError("JSON array must contain objects with ip, org_id, platform keys")  # noqa: TRY003

        missing = REQUIRED_COLUMNS - set(first.keys())
        if missing:
            raise ValidationError(  # noqa: TRY003
                f"JSON objects missing required keys: {', '.join(sorted(missing))}. Required: ip, org_id, platform",
            )

        return data

    def _validate_rows(self, rows: list[dict]) -> "_ValidationResult":
        valid_rows = []
        skipped_ips = []

        for row in rows:
            ip_str = str(row.get("ip", "")).strip()
            org_id = str(row.get("org_id", "")).strip()
            platform = str(row.get("platform", "")).strip()

            if not ip_str or not org_id or not platform:
                skipped_ips.append(ip_str or "(empty)")
                continue

            try:
                ipaddress.ip_address(ip_str)
            except ValueError:
                skipped_ips.append(ip_str)
                continue

            valid_rows.append({"ip": ip_str, "org_id": org_id, "platform": platform})

        if not valid_rows:
            raise ValidationError("No valid rows found after validation")  # noqa: TRY003

        return _ValidationResult(valid_rows=valid_rows, skipped_ips=skipped_ips)

    def _write_sqlite(self, db_path: Path, rows: list[dict]) -> None:
        if db_path.exists():
            os.remove(db_path)

        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE data (  ip TEXT PRIMARY KEY,  org_id TEXT NOT NULL,  platform TEXT NOT NULL)")
            conn.executemany(
                "INSERT OR IGNORE INTO data (ip, org_id, platform) VALUES (?, ?, ?)",
                [(r["ip"], r["org_id"], r["platform"]) for r in rows],
            )
            conn.commit()
        except Exception as e:
            if db_path.exists():
                os.remove(db_path)
            raise FileOperationError(f"Error creating database: {e}") from e  # noqa: TRY003
        finally:
            conn.close()


@dataclass
class _ValidationResult:
    valid_rows: list[dict]
    skipped_ips: list[str]
