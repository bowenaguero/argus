"""Shared test fixtures and utilities for Argus CLI tests."""

import contextlib
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from rich.console import Console


@pytest.fixture
def mock_console():
    """Create a mock console for testing."""
    return MagicMock(spec=Console)


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "maxmind_license_key": "test_maxmind_key_12345",
        "ip2proxy_token": "test_ip2proxy_token_67890",
        "ipinfo_token": "test_ipinfo_token_24680",
    }


@pytest.fixture
def sample_lookup_results():
    """Sample IP lookup results for testing."""
    return [
        {
            "ip": "8.8.8.8",
            "domain": "dns.google",
            "city": "Mountain View",
            "region": "California",
            "country": "United States",
            "iso_code": "US",
            "postal": "94035",
            "asn": 15169,
            "asn_org": "Google LLC",
            "org_managed": False,
            "org_id": None,
            "platform": None,
            "proxy_type": None,
            "isp": None,
            "domain_name": None,
            "usage_type": None,
            "error": None,
        },
        {
            "ip": "1.1.1.1",
            "domain": "one.one.one.one",
            "city": "Unknown",
            "region": None,
            "country": "Australia",
            "iso_code": "AU",
            "postal": None,
            "asn": 13335,
            "asn_org": "Cloudflare Inc.",
            "org_managed": True,
            "org_id": "CLOUDFLARE",
            "platform": "cloudflare",
            "proxy_type": None,
            "isp": None,
            "domain_name": None,
            "usage_type": None,
            "error": None,
        },
        {
            "ip": "192.168.1.1",
            "domain": None,
            "city": None,
            "region": None,
            "country": None,
            "iso_code": None,
            "postal": None,
            "asn": None,
            "asn_org": None,
            "org_managed": False,
            "org_id": None,
            "platform": None,
            "proxy_type": None,
            "isp": None,
            "domain_name": None,
            "usage_type": None,
            "error": "Private IP address",
        },
    ]


@pytest.fixture
def sample_ip_text():
    """Sample text containing IP addresses."""
    return """
    Sample log file with IP addresses:
    2024-01-01 12:00:00 - Connection from 8.8.8.8
    2024-01-01 12:01:00 - Connection from 1.1.1.1
    2024-01-01 12:02:00 - Private IP: 192.168.1.1
    2024-01-01 12:03:00 - Invalid IP: 999.999.999.999
    2024-01-01 12:04:00 - CIDR: 10.0.0.0/24
    2024-01-01 12:05:00 - Another IP: 208.67.222.222
    """


@pytest.fixture
def sample_cidr_blocks():
    """Sample CIDR blocks for testing."""
    return ["192.168.1.0/24", "10.0.0.0/8", "172.16.0.0/12"]


@pytest.fixture
def mock_geoip_responses():
    """Mock GeoIP database responses."""

    class MockCityResponse:
        def __init__(self):
            self.city = MagicMock()
            self.city.name = "Mountain View"
            self.subdivisions = MagicMock()
            self.subdivisions.most_specific = MagicMock()
            self.subdivisions.most_specific.name = "California"
            self.country = MagicMock()
            self.country.name = "United States"
            self.country.iso_code = "US"
            self.postal = MagicMock()
            self.postal.code = "94035"

    class MockASNResponse:
        def __init__(self):
            self.autonomous_system_number = 15169
            self.autonomous_system_organization = "Google LLC"

    return {
        "city": MockCityResponse(),
        "asn": MockASNResponse(),
    }


@pytest.fixture
def mock_proxy_response():
    """Mock IP2Proxy database response."""
    return {
        "proxy_type": "DCH",
        "country_short": "US",
        "isp": "Google LLC",
        "domain": "google.com",
        "usage_type": "DCH",
    }


@pytest.fixture
def mock_database_files():
    """Mock database file paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        return {
            "city_db": str(Path(tmpdir) / "GeoLite2-City.mmdb"),
            "asn_db": str(Path(tmpdir) / "GeoLite2-ASN.mmdb"),
            "proxy_db": str(Path(tmpdir) / "IP2PROXY-IP-PROXYTYPE-COUNTRY-REGION-CITY-ISP-DOMAIN-USAGETYPE-ASN.BIN"),
            "config_file": str(Path(tmpdir) / "keys.json"),
            "state_file": str(Path(tmpdir) / "state.json"),
        }


class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_lookup_result(
        ip: str = "8.8.8.8",
        country: str = "United States",
        asn: int = 15169,
        asn_org: str = "Google LLC",
        org_managed: bool = False,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Create a lookup result dictionary."""
        return {
            "ip": ip,
            "domain": None,
            "city": "Mountain View",
            "region": "California",
            "country": country,
            "iso_code": "US",
            "postal": "94035",
            "asn": asn,
            "asn_org": asn_org,
            "org_managed": org_managed,
            "org_id": None,
            "platform": None,
            "proxy_type": None,
            "isp": None,
            "domain_name": None,
            "usage_type": None,
            "error": error,
        }

    @staticmethod
    def create_config_data(
        maxmind_key: str = "test_key",
        ip2proxy_token: str = "test_token",  # noqa: S107
        ipinfo_token: str = "test_ipinfo_token",  # noqa: S107
    ) -> dict[str, str]:
        """Create configuration data."""
        return {
            "maxmind_license_key": maxmind_key,
            "ip2proxy_token": ip2proxy_token,
            "ipinfo_token": ipinfo_token,
        }


class MockHelpers:
    """Helper methods for creating mocks."""

    @staticmethod
    def create_mock_console() -> MagicMock:
        """Create a mock console."""
        return MagicMock(spec=Console)

    @staticmethod
    def create_temp_file(content: str, suffix: str = ".txt") -> str:
        """Create a temporary file with given content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            f.write(content)
            return f.name

    @staticmethod
    def cleanup_temp_file(file_path: str) -> None:
        """Clean up a temporary file."""
        with contextlib.suppress(OSError):
            os.unlink(file_path)


def assert_lookup_results_equal(result1: dict[str, Any], result2: dict[str, Any]) -> None:
    """Assert that two lookup result dictionaries are equal, ignoring minor differences."""
    # Compare only important fields
    important_fields = ["ip", "country", "city", "asn", "asn_org", "org_managed", "error"]
    for field in important_fields:
        assert result1.get(field) == result2.get(field), (
            f"Field {field} differs: {result1.get(field)} != {result2.get(field)}"
        )
