import sqlite3
from contextlib import suppress
from pathlib import Path


class OrgLookup:
    def __init__(self, org_db_dir: str):
        self.org_db_dir = Path(org_db_dir)
        self.connections: list[dict] = []
        self.has_org_dbs = False
        self._loaded = False

    def load_databases(self) -> bool:
        if self._loaded:
            return self.has_org_dbs

        self._loaded = True

        if not self.org_db_dir.exists():
            return False

        db_files = list(self.org_db_dir.glob("*.db"))
        if not db_files:
            return False

        loaded_count = 0

        for db_file in db_files:
            try:
                conn = sqlite3.connect(str(db_file), check_same_thread=False)
                conn.row_factory = sqlite3.Row
                self.connections.append({
                    "name": db_file.stem,
                    "conn": conn,
                })
                loaded_count += 1
            except Exception:
                continue

        self.has_org_dbs = loaded_count > 0
        return self.has_org_dbs

    def lookup_ip(self, ip: str) -> dict | None:
        if not self.connections:
            return None

        for db in self.connections:
            result = self._lookup_in_database(ip, db["conn"])
            if result:
                return result

        return None

    def _lookup_in_database(self, ip: str, conn: sqlite3.Connection) -> dict | None:
        with suppress(Exception):
            cursor = conn.execute("SELECT org_id, platform FROM data WHERE ip = ? LIMIT 1", (ip,))
            row = cursor.fetchone()

            if row:
                return {
                    "org_managed": True,
                    "org_id": row["org_id"],
                    "platform": row["platform"],
                }

        return None

    def close(self):
        for db in self.connections:
            with suppress(Exception):
                db["conn"].close()
        self.connections = []
        self.has_org_dbs = False
        self._loaded = False

    def __del__(self):
        self.close()
