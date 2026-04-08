import ipaddress
import re
from pathlib import Path

import openpyxl
import pypdf

from ..core.exceptions import FileOperationError


class FileParser:
    @staticmethod
    def expand_cidr(cidr: str) -> list[str]:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as e:
            msg = f"Invalid CIDR block: {cidr}"
            raise ValueError(msg) from e

        if network.num_addresses > 1024:
            msg = f"CIDR block {cidr} too large (max 1024 IPs)"
            raise ValueError(msg)

        return [str(ip) for ip in network.hosts() if ipaddress.ip_address(ip).is_global]

    @staticmethod
    def extract_ips(text: str) -> list[str]:
        ips = set()
        for match in re.finditer(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", text):
            try:
                ip_obj = ipaddress.ip_address(match.group())
                if ip_obj.is_global:
                    ips.add(match.group())
            except ValueError:
                continue
        return sorted(ips)

    @staticmethod
    def read_pdf(filepath: str) -> str:
        try:
            with open(filepath, "rb") as f:
                reader = pypdf.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            raise FileOperationError(f"Error reading PDF: {e}") from e  # noqa: TRY003
        else:
            return text

    @staticmethod
    def read_excel(filepath: str) -> str:
        try:
            wb = openpyxl.load_workbook(filepath, data_only=True)
            text = ""
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    for cell in row:
                        if cell:
                            text += str(cell) + " "
                    text += "\n"
        except Exception as e:
            raise FileOperationError(f"Error reading Excel file: {e}") from e  # noqa: TRY003
        else:
            return text

    @classmethod
    def read_file_content(cls, filepath: str) -> str:
        ext = Path(filepath).suffix.lower()

        if ext == ".pdf":
            return cls.read_pdf(filepath)
        elif ext in [".xlsx", ".xls"]:
            return cls.read_excel(filepath)
        else:
            try:
                with open(filepath, encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                raise FileOperationError(f"Error reading file: {e}") from e  # noqa: TRY003
