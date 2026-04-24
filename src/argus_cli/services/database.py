import json
import os
import shutil
import tarfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import requests
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TransferSpeedColumn,
)

from ..core.exceptions import ConfigurationError, DatabaseError
from ..utils.logger import get_logger

logger = get_logger()

IP2PROXY_DB_CODE = "PX11LITEBIN"
IPINFO_EDITION_ID = "ipinfo_lite"
GREYNOISE_EDITION_ID = "greynoise_psychic"
GREYNOISE_REFRESH_HOURS = 168  # 7 days — 30-day rolling window changes slowly


class DatabaseManager:
    def __init__(self, config, console: Console):
        self.config = config
        self.console = console

    def load_state(self) -> dict:
        if not os.path.exists(self.config.state_file):
            return {}
        try:
            with open(self.config.state_file) as f:
                return json.load(f)
        except Exception:
            return {}

    def save_state(self, state: dict) -> None:
        with open(self.config.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def needs_download(self, edition_id: str, hours: int = 24) -> bool:
        state = self.load_state()
        last_download = state.get(edition_id)
        if not last_download:
            return True
        try:
            last_dt = datetime.fromisoformat(last_download)
            stale = datetime.now() - last_dt > timedelta(hours=hours)
        except Exception:
            return True
        else:
            if stale:
                logger.debug(f"{edition_id} is stale — download required")
            return stale

    def download_maxmind_database(self, license_key: str, edition_id: str, db_path: str) -> bool:
        if not self.needs_download(edition_id):
            return True

        logger.debug(f"Downloading MaxMind {edition_id}")
        url = f"https://download.maxmind.com/app/geoip_download?edition_id={edition_id}&license_key={license_key}&suffix=tar.gz"
        temp_file = str(self.config.data_dir / "temp_maxmind.tar.gz")

        try:
            self._download_file(url, temp_file, f"MaxMind {edition_id}")
            self._extract_maxmind_database(temp_file, db_path)
            self._update_state(edition_id)
        except Exception as e:
            self.console.print(f"[red]✗ Error:[/red] {e}", style="bold")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(db_path):
                self.console.print("[yellow]Continuing with existing database...[/yellow]")
                return True
            return False
        else:
            self.console.print(f"[green]✓[/green] MaxMind {edition_id} downloaded successfully")
            return True

    def download_ip2proxy_database(self, token: str, db_code: str, db_path: str) -> bool:
        if not self.needs_download(db_code):
            return True

        logger.debug(f"Downloading IP2Proxy {db_code}")
        url = f"https://www.ip2location.com/download/?token={token}&file={db_code}"
        temp_file = str(self.config.data_dir / "temp_ip2proxy.zip")

        try:
            self._download_file(url, temp_file, f"IP2Proxy {db_code}")
            self._extract_ip2proxy_database(temp_file, db_path)
            self._update_state(db_code)
        except Exception as e:
            self.console.print(f"[red]✗ Error:[/red] {e}", style="bold")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(db_path):
                self.console.print("[yellow]Continuing with existing database...[/yellow]")
                return True
            return False
        else:
            self.console.print(f"[green]✓[/green] IP2Proxy {db_code} database downloaded successfully")
            return True

    def download_ipinfo_database(self, token: str, db_path: str) -> bool:
        if not self.needs_download(IPINFO_EDITION_ID):
            return True

        logger.debug("Downloading IPinfo Lite database")
        url = f"https://ipinfo.io/data/ipinfo_lite.mmdb?token={token}"
        temp_file = str(self.config.data_dir / "temp_ipinfo.mmdb")

        try:
            self._download_file(url, temp_file, "IPinfo Lite")
            shutil.move(temp_file, db_path)
            self._update_state(IPINFO_EDITION_ID)
        except Exception as e:
            self.console.print(f"[red]✗ Error:[/red] {e}", style="bold")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(db_path):
                self.console.print("[yellow]Continuing with existing database...[/yellow]")
                return True
            return False
        else:
            self.console.print("[green]✓[/green] IPinfo Lite database downloaded successfully")
            return True

    def download_greynoise_database(self, api_key: str, db_path: str) -> bool:
        if not self.needs_download(GREYNOISE_EDITION_ID, hours=GREYNOISE_REFRESH_HOURS):
            return True

        logger.debug("Downloading GreyNoise Psychic database (30-day range, Model 2)")
        # Use yesterday as end_date — GreyNoise may not publish the current day's data yet
        end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")
        url = f"https://psychic.labs.greynoise.io/v1/psychic/generate/{start_date}/{end_date}/2"
        temp_file = str(self.config.data_dir / "temp_greynoise.bin")

        self.console.print("[dim]GreyNoise (30-day range) — first download may take a few minutes[/dim]")

        try:
            self._download_file(url, temp_file, "GreyNoise Psychic", headers={"key": api_key})
            shutil.move(temp_file, db_path)
            self._update_state(GREYNOISE_EDITION_ID)
        except Exception as e:
            self.console.print(f"[red]✗ Error:[/red] {e}", style="bold")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(db_path):
                self.console.print("[yellow]Continuing with existing database...[/yellow]")
                return True
            return False
        else:
            self.console.print("[green]✓[/green] GreyNoise Psychic database downloaded successfully")
            return True

    def _download_file(self, url: str, temp_file: str, description: str, headers: dict | None = None) -> None:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Downloading {description}", total=None)

            with requests.get(url, stream=True, timeout=120, headers=headers or {}) as r:
                if r.status_code in [401, 403]:
                    msg = f"{r.status_code} {r.reason}: Invalid or expired download token"
                    raise requests.exceptions.HTTPError(msg)
                if r.status_code >= 400:
                    body = r.text[:500] if r.text else "(no body)"
                    msg = f"{r.status_code} {r.reason} — {body}"
                    raise requests.exceptions.HTTPError(msg)
                r.raise_for_status()

                content_type = r.headers.get("content-type", "")
                if "text" in content_type.lower() or "html" in content_type.lower():
                    self.console.print(f"[dim]{r.text}[/dim]")
                    msg = f"Invalid token or download limit exceeded for {description}. Please check your account."
                    raise requests.exceptions.HTTPError(msg)

                total_size = int(r.headers.get("content-length", 0))
                progress.update(task, total=total_size)

                with open(temp_file, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))

    def _extract_maxmind_database(self, temp_file: str, db_path: str) -> None:
        extract_dir = str(self.config.data_dir)
        with tarfile.open(temp_file, "r:gz") as tar:
            mmdb_member = next((m for m in tar.getmembers() if m.name.endswith(".mmdb")), None)
            if not mmdb_member:
                msg = "Could not find .mmdb file in archive."
                raise ValueError(msg)

            tar.extract(mmdb_member, path=extract_dir)
            extracted_path = os.path.join(extract_dir, mmdb_member.name)
            shutil.move(extracted_path, db_path)

            extracted_dir_name = os.path.dirname(mmdb_member.name)
            if extracted_dir_name:
                full_extracted_dir = os.path.join(extract_dir, extracted_dir_name)
                if os.path.exists(full_extracted_dir):
                    shutil.rmtree(full_extracted_dir)

        os.remove(temp_file)

    def _extract_ip2proxy_database(self, temp_file: str, db_path: str) -> None:
        with zipfile.ZipFile(temp_file, "r") as zip_ref:
            bin_files = [f for f in zip_ref.namelist() if f.upper().endswith(".BIN")]
            if not bin_files:
                msg = "Could not find .BIN file in archive."
                raise ValueError(msg)

            bin_file = bin_files[0]
            with zip_ref.open(bin_file) as source, open(db_path, "wb") as target:
                target.write(source.read())

        os.remove(temp_file)

    def _update_state(self, edition_id: str) -> None:
        state = self.load_state()
        state[edition_id] = datetime.now().isoformat()
        self.save_state(state)

    def ensure_databases(self) -> None:
        maxmind_key = self.config.get_license_key("maxmind_license_key")
        if not maxmind_key and not (os.path.exists(self.config.db_city) and os.path.exists(self.config.db_asn)):
            self.display_missing_license_key_help()
            raise ConfigurationError("MaxMind license key not configured and no existing databases found")  # noqa: TRY003

        if maxmind_key:
            city_ok = self.download_maxmind_database(maxmind_key, "GeoLite2-City", self.config.db_city)
            asn_ok = self.download_maxmind_database(maxmind_key, "GeoLite2-ASN", self.config.db_asn)

            if (not city_ok and not os.path.exists(self.config.db_city)) or (
                not asn_ok and not os.path.exists(self.config.db_asn)
            ):
                raise DatabaseError("Required MaxMind databases are unavailable")  # noqa: TRY003

        self._ensure_optional_databases()

    def _ensure_optional_databases(self) -> None:
        ip2proxy_token = self.config.get_license_key("ip2proxy_token")
        if ip2proxy_token:
            self.download_ip2proxy_database(ip2proxy_token, IP2PROXY_DB_CODE, self.config.db_proxy)
        elif not os.path.exists(self.config.db_proxy):
            self.console.print(
                "[yellow]i[/yellow] IP2Proxy database not configured. Proxy detection will be unavailable."
            )

        ipinfo_token = self.config.get_license_key("ipinfo_token")
        if ipinfo_token:
            self.download_ipinfo_database(ipinfo_token, self.config.db_ipinfo)
        elif not os.path.exists(self.config.db_ipinfo):
            self.console.print(
                "[yellow]i[/yellow] IPinfo database not configured. Domain enrichment will be unavailable."
            )

        greynoise_key = self.config.get_license_key("greynoise_api_key")
        if greynoise_key:
            self.download_greynoise_database(greynoise_key, self.config.db_greynoise)
        elif not os.path.exists(self.config.db_greynoise):
            self.console.print("[yellow]i[/yellow] GreyNoise not configured. Threat intelligence will be unavailable.")

        org_dir = os.path.join(self.config.data_dir, "org")
        if not os.path.exists(org_dir) or not any(Path(org_dir).glob("*.db")):
            self.console.print(
                "[yellow]i[/yellow] Org databases not found. Org managed IP detection will be unavailable."
            )

    def display_missing_license_key_help(self) -> None:
        self.console.print("\n[red]✗ Missing license key[/red]")
        self.console.print("─" * 60, style="dim")
        self.console.print("Run setup to configure your MaxMind license key:")
        self.console.print("  [cyan]argus setup[/cyan]")
        self.console.print(
            "\nGet a free key at: [link=https://www.maxmind.com/en/geolite2/signup]https://www.maxmind.com/en/geolite2/signup[/link]"
        )
