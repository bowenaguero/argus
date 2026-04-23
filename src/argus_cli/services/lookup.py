import os
from dataclasses import dataclass

import geoip2.database
import geoip2.errors
import IP2Proxy
import maxminddb
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from ..utils.logger import get_logger
from .org_lookup import OrgLookup

logger = get_logger()


@dataclass
class DataSourceCapabilities:
    has_proxy: bool
    has_org: bool
    has_ipinfo: bool = False


class GeoIPLookup:
    def __init__(self, city_db_path: str, asn_db_path: str, proxy_db_path: str, org_db_dir: str, ipinfo_db_path: str = ""):
        self.city_db_path = city_db_path
        self.asn_db_path = asn_db_path
        self.proxy_db_path = proxy_db_path
        self.org_db_dir = org_db_dir
        self.ipinfo_db_path = ipinfo_db_path
        self.has_proxy_db = os.path.exists(proxy_db_path)
        self.has_ipinfo_db = bool(ipinfo_db_path) and os.path.exists(ipinfo_db_path)
        self.org_lookup = OrgLookup(org_db_dir)

    def lookup_ip(self, city_reader, asn_reader, proxy_db, ipinfo_reader, ip: str) -> dict:
        logger.debug(f"Looking up IP: {ip}")
        try:
            city_resp = city_reader.city(ip)
            asn_resp = asn_reader.asn(ip)
        except geoip2.errors.AddressNotFoundError:
            return {"ip": ip, "error": "IP not found in database"}
        except ValueError:
            return {"ip": ip, "error": "Invalid IP format"}
        except Exception as e:
            return {"ip": ip, "error": str(e)}

        result = {
            "ip": ip,
            "domain": None,
            "city": city_resp.city.name if city_resp.city.name else None,
            "region": (
                city_resp.subdivisions.most_specific.name if city_resp.subdivisions.most_specific.name else None
            ),
            "country": city_resp.country.name if city_resp.country.name else None,
            "iso_code": (city_resp.country.iso_code if city_resp.country.iso_code else None),
            "postal": city_resp.postal.code if city_resp.postal.code else None,
            "asn": (asn_resp.autonomous_system_number if asn_resp.autonomous_system_number else None),
            "asn_org": (asn_resp.autonomous_system_organization if asn_resp.autonomous_system_organization else None),
            "org_managed": False,
            "org_id": None,
            "platform": None,
            "error": None,
        }

        if proxy_db and self.has_proxy_db:
            self._enrich_proxy(result, proxy_db, ip)

        if ipinfo_reader and self.has_ipinfo_db:
            self._enrich_ipinfo(result, ipinfo_reader, ip)

        if self.org_lookup.has_org_dbs:
            org_result = self.org_lookup.lookup_ip(ip)
            if org_result:
                result["org_managed"] = org_result["org_managed"]
                result["org_id"] = org_result["org_id"]
                result["platform"] = org_result["platform"]

        return result

    def _enrich_proxy(self, result: dict, proxy_db, ip: str) -> None:
        proxy_record = proxy_db.get_all(ip)
        if proxy_record and proxy_record["country_short"] != "-":
            result["proxy_type"] = proxy_record["proxy_type"] if proxy_record["proxy_type"] != "-" else None
            result["isp"] = proxy_record["isp"] if proxy_record["isp"] != "-" else None
            result["usage_type"] = proxy_record["usage_type"] if proxy_record["usage_type"] != "-" else None

    def _enrich_ipinfo(self, result: dict, ipinfo_reader, ip: str) -> None:
        try:
            ipinfo_record = ipinfo_reader.get(ip)
            if ipinfo_record and ipinfo_record.get("as_domain"):
                result["domain"] = ipinfo_record["as_domain"]
        except Exception:
            logger.debug(f"IPinfo lookup failed for {ip}")

    def lookup_ips(self, ips: list[str]) -> tuple[list[dict], DataSourceCapabilities]:
        logger.debug(f"Starting batch lookup for {len(ips)} IP(s)")
        results = []

        show_progress = len(ips) > 1

        self.org_lookup.load_databases()

        proxy_db = None
        if self.has_proxy_db:
            proxy_db = IP2Proxy.IP2Proxy()
            proxy_db.open(self.proxy_db_path)

        ipinfo_reader = None
        if self.has_ipinfo_db:
            ipinfo_reader = maxminddb.open_database(self.ipinfo_db_path)

        capabilities = DataSourceCapabilities(
            has_proxy=self.has_proxy_db,
            has_org=self.org_lookup.has_org_dbs,
            has_ipinfo=self.has_ipinfo_db,
        )

        try:
            with (
                geoip2.database.Reader(self.city_db_path) as city_reader,
                geoip2.database.Reader(self.asn_db_path) as asn_reader,
            ):
                if show_progress:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[bold blue]Looking up IPs..."),
                        BarColumn(),
                        TaskProgressColumn(),
                        TextColumn("[cyan]{task.fields[current_ip]}"),
                        transient=True,
                    ) as progress:
                        task = progress.add_task("lookup", total=len(ips), current_ip="")
                        for ip in ips:
                            progress.update(task, current_ip=ip)
                            result = self.lookup_ip(city_reader, asn_reader, proxy_db, ipinfo_reader, ip)
                            results.append(result)
                            progress.advance(task)
                else:
                    for ip in ips:
                        result = self.lookup_ip(city_reader, asn_reader, proxy_db, ipinfo_reader, ip)
                        results.append(result)
        finally:
            if proxy_db:
                proxy_db.close()
            if ipinfo_reader:
                ipinfo_reader.close()
            self.org_lookup.close()

        return results, capabilities
