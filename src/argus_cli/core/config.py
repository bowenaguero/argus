import json
import os
from pathlib import Path

from platformdirs import user_data_dir


class Config:
    def __init__(self):
        self.data_dir = self._get_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_city = str(self.data_dir / "GeoLite2-City.mmdb")
        self.db_asn = str(self.data_dir / "GeoLite2-ASN.mmdb")
        self.db_proxy = str(self.data_dir / "IP2PROXY-IP-PROXYTYPE-COUNTRY-REGION-CITY-ISP-DOMAIN-USAGETYPE-ASN.BIN")
        self.db_org_dir = str(self.data_dir / "org")
        self.state_file = str(self.data_dir / "state.json")
        self.config_file = str(self.data_dir / "keys.json")

    def _get_data_dir(self) -> Path:
        return Path(user_data_dir("argus", appauthor=False))

    def get_license_key(self, license_key_name: str) -> str | None:
        if not os.path.exists(self.config_file):
            return None

        try:
            with open(self.config_file, encoding="utf-8") as f:
                config = json.load(f)
                return config.get(license_key_name)
        except Exception:
            return None
