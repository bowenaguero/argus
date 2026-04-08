import os
import re
from pathlib import Path

from ..core.exceptions import ValidationError


class ParameterValidator:
    """Validates command-line parameters."""

    @staticmethod
    def validate_ip(ip: str) -> str:
        """Validate IP address format."""
        if not ip:
            raise ValidationError("IP address cannot be empty")  # noqa: TRY003

        # Check for CIDR notation
        if "/" in ip:
            ip_part, cidr_part = ip.split("/", 1)
            if not ParameterValidator._is_valid_ip(ip_part):
                raise ValidationError(f"Invalid IP address in CIDR: {ip_part}")  # noqa: TRY003
            if not cidr_part.isdigit() or not (0 <= int(cidr_part) <= 32):
                raise ValidationError(f"Invalid CIDR prefix: {cidr_part}")  # noqa: TRY003
            return ip

        if not ParameterValidator._is_valid_ip(ip):
            raise ValidationError(f"Invalid IP address: {ip}")  # noqa: TRY003

        return ip

    @staticmethod
    def validate_file_path(file_path: Path) -> Path:
        """Validate file path exists and is readable."""
        if not file_path.exists():
            raise ValidationError(f"File does not exist: {file_path}")  # noqa: TRY003

        if not file_path.is_file():
            raise ValidationError(f"Path is not a file: {file_path}")  # noqa: TRY003

        if not os.access(file_path, mode=os.R_OK):
            raise ValidationError(f"File is not readable: {file_path}")  # noqa: TRY003

        return file_path

    @staticmethod
    def validate_output_path(output_path: str) -> str:
        """Validate output path."""
        if not output_path:
            return output_path

        # Check if directory exists and is writable
        output_dir = os.path.dirname(output_path) if output_path != "-" else "."
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                raise ValidationError(f"Cannot create output directory: {e}") from e  # noqa: TRY003

        if output_dir and not os.access(output_dir, mode=os.W_OK):
            raise ValidationError(f"Output directory is not writable: {output_dir}")  # noqa: TRY003

        return output_path

    @staticmethod
    def validate_sort_by(sort_by: str) -> str:
        """Validate sort field."""
        valid_fields = {"ip", "domain", "city", "country", "asn", "asn_org"}
        if sort_by not in valid_fields:
            raise ValidationError(f"Invalid sort field: {sort_by}. Valid options: {', '.join(sorted(valid_fields))}")  # noqa: TRY003
        return sort_by

    @staticmethod
    def validate_asn_numbers(asn_list: list[int]) -> list[int]:
        """Validate ASN numbers."""
        for asn in asn_list:
            if not (0 <= asn <= 4294967295):
                raise ValidationError(f"Invalid ASN number: {asn}. Must be between 0 and 4294967295")  # noqa: TRY003
        return asn_list

    @staticmethod
    def validate_country_names(country_list: list[str]) -> list[str]:
        """Validate country names are non-empty alphabetic strings."""
        for country in country_list:
            if not country or not country.replace(" ", "").isalpha():
                raise ValidationError(f"Invalid country name: {country}")  # noqa: TRY003
        return [country.upper() for country in country_list]

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """Check if IP address is valid."""
        # IPv4 regex
        ipv4_pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        return bool(re.match(ipv4_pattern, ip))
