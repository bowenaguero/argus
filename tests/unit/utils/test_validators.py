"""Tests for utility modules."""

from pathlib import Path

import pytest

from argus_cli.utils.validators import ParameterValidator, ValidationError


class TestParameterValidator:
    """Test cases for ParameterValidator class."""

    def test_validate_ip_valid_ipv4(self):
        """Test validation of valid IPv4 addresses."""
        valid_ips = ["8.8.8.8", "1.1.1.1", "192.168.1.1", "255.255.255.255"]

        for ip in valid_ips:
            result = ParameterValidator.validate_ip(ip)
            assert result == ip

    def test_validate_ip_valid_cidr(self):
        """Test validation of valid CIDR notation."""
        valid_cidrs = ["192.168.1.0/24", "10.0.0.0/8", "172.16.0.0/12"]

        for cidr in valid_cidrs:
            result = ParameterValidator.validate_ip(cidr)
            assert result == cidr

    def test_validate_ip_invalid_format(self):
        """Test validation of invalid IP formats."""
        invalid_ips = ["invalid", "999.999.999.999", "192.168.1", "192.168.1.1.1"]

        for ip in invalid_ips:
            with pytest.raises(ValidationError, match="Invalid IP address"):
                ParameterValidator.validate_ip(ip)

    def test_validate_ip_invalid_cidr_prefix(self):
        """Test validation of invalid CIDR prefixes."""
        invalid_cidrs = ["192.168.1.0/33", "10.0.0.0/-1", "172.16.0.0/abc"]

        for cidr in invalid_cidrs:
            with pytest.raises(ValidationError, match="Invalid CIDR prefix"):
                ParameterValidator.validate_ip(cidr)

    def test_validate_ip_empty(self):
        """Test validation of empty IP."""
        with pytest.raises(ValidationError, match="IP address cannot be empty"):
            ParameterValidator.validate_ip("")

    def test_validate_file_path_exists(self):
        """Test validation of existing file."""
        with pytest.raises(ValidationError, match="File does not exist"):
            ParameterValidator.validate_file_path(Path("/nonexistent/file.txt"))

    def test_validate_asn_numbers_valid(self):
        """Test validation of valid ASN numbers."""
        valid_asns = [0, 1, 13335, 15169, 4294967295]

        result = ParameterValidator.validate_asn_numbers(valid_asns)
        assert result == valid_asns

    def test_validate_asn_numbers_invalid(self):
        """Test validation of invalid ASN numbers."""
        invalid_asns = [-1, 4294967296]

        for asn in invalid_asns:
            with pytest.raises(ValidationError, match="Invalid ASN number"):
                ParameterValidator.validate_asn_numbers([asn])

    def test_validate_country_names_valid(self):
        """Test validation of valid country names."""
        valid_countries = ["Germany", "United States", "china", "Brazil"]

        result = ParameterValidator.validate_country_names(valid_countries)
        assert result == ["GERMANY", "UNITED STATES", "CHINA", "BRAZIL"]

    def test_validate_country_names_invalid(self):
        """Test validation of invalid country names."""
        invalid_countries = ["", "123", "US-1"]

        for country in invalid_countries:
            with pytest.raises(ValidationError, match="Invalid country name"):
                ParameterValidator.validate_country_names([country])

    def test_validate_sort_by_valid(self):
        """Test validation of valid sort fields."""
        valid_fields = ["ip", "domain", "city", "country", "asn", "asn_org"]

        for field in valid_fields:
            result = ParameterValidator.validate_sort_by(field)
            assert result == field

    def test_validate_sort_by_invalid(self):
        """Test validation of invalid sort fields."""
        invalid_fields = ["invalid_field", "unknown", "random"]

        for field in invalid_fields:
            with pytest.raises(ValidationError, match="Invalid sort field"):
                ParameterValidator.validate_sort_by(field)

    def test_validate_output_path_valid(self):
        """Test validation of valid output paths."""
        # Should not raise for valid paths
        result = ParameterValidator.validate_output_path("")
        assert result == ""

        result = ParameterValidator.validate_output_path("/tmp/output.json")  # noqa: S108
        assert result == "/tmp/output.json"  # noqa: S108

    def test_validate_output_path_writable(self):
        """Test validation of writable output directory."""
        # This test would need to mock file system operations
        # For now, we just ensure it doesn't crash
        result = ParameterValidator.validate_output_path("/tmp/test_output.json")  # noqa: S108
        assert result == "/tmp/test_output.json"  # noqa: S108
