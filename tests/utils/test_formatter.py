import csv
import json
import os
import tempfile
from unittest.mock import MagicMock

from argus_cli.services.lookup import DataSourceCapabilities
from argus_cli.utils.formatter import ResultFormatter


class TestResultFormatter:
    def test_format_json(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        results = [
            {"ip": "1.1.1.1", "domain": "one.one", "city": "Austin", "country": "US", "asn": 13335, "org": "Cloudflare"}
        ]
        json_output = formatter.format_json(results)
        parsed = json.loads(json_output)
        assert len(parsed) == 1
        assert parsed[0]["ip"] == "1.1.1.1"

    def test_format_json_empty(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        json_output = formatter.format_json([])
        parsed = json.loads(json_output)
        assert parsed == []

    def test_format_csv(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        results = [
            {
                "ip": "1.1.1.1",
                "domain": "one.one",
                "city": "Austin",
                "country": "US",
                "asn": 13335,
                "asn_org": "Cloudflare",
                "error": None,
            },
            {
                "ip": "8.8.8.8",
                "domain": "dns.google",
                "city": "Unknown",
                "country": "US",
                "asn": 15169,
                "asn_org": "Google",
                "error": None,
            },
        ]
        csv_output = formatter.format_csv(results)
        lines = csv_output.strip().split("\r\n")
        assert len(lines) == 3  # header + 2 rows
        assert '"ip"' in lines[0]
        assert '"domain"' in lines[0]
        assert '"isp"' in lines[0]
        assert '"usage_type"' in lines[0]
        assert '"postal"' in lines[0]
        assert '"1.1.1.1"' in lines[1]
        assert '"one.one"' in lines[1]

    def test_format_csv_empty(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        csv_output = formatter.format_csv([])
        assert csv_output == ""

    def test_write_to_file_json(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        results = [
            {
                "ip": "1.1.1.1",
                "domain": "one.one",
                "city": "Austin",
                "country": "US",
                "asn": 13335,
                "asn_org": "Cloudflare",
                "error": None,
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            formatter.write_to_file(results, temp_path, "json")

            with open(temp_path) as f:
                content = json.load(f)

            assert len(content) == 1
            assert content[0]["ip"] == "1.1.1.1"
            console.print.assert_called()
        finally:
            os.unlink(temp_path)

    def test_write_to_file_csv(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        results = [
            {
                "ip": "1.1.1.1",
                "domain": "one.one",
                "city": "Austin",
                "country": "US",
                "asn": 13335,
                "asn_org": "Cloudflare",
                "error": None,
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = f.name

        try:
            formatter.write_to_file(results, temp_path, "csv")

            with open(temp_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["ip"] == "1.1.1.1"
            console.print.assert_called()
        finally:
            os.unlink(temp_path)

    def test_write_to_file_auto_naming_json(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        results = [
            {
                "ip": "1.1.1.1",
                "domain": "one.one",
                "city": "Austin",
                "country": "US",
                "asn": 13335,
                "asn_org": "Cloudflare",
                "error": None,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                formatter.write_to_file(results, "", "json")

                call_args = console.print.call_args_list
                assert any("argus_results_" in str(call) and ".json" in str(call) for call in call_args)

                # Verify file was created in temp directory
                json_files = [f for f in os.listdir(tmpdir) if f.startswith("argus_results_") and f.endswith(".json")]
                assert len(json_files) == 1
            finally:
                os.chdir(original_dir)

    def test_write_to_file_auto_naming_csv(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        results = [
            {
                "ip": "1.1.1.1",
                "domain": "one.one",
                "city": "Austin",
                "country": "US",
                "asn": 13335,
                "asn_org": "Cloudflare",
                "error": None,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                formatter.write_to_file(results, "", "csv")

                call_args = console.print.call_args_list
                assert any("argus_results_" in str(call) and ".csv" in str(call) for call in call_args)

                # Verify file was created in temp directory
                csv_files = [f for f in os.listdir(tmpdir) if f.startswith("argus_results_") and f.endswith(".csv")]
                assert len(csv_files) == 1
            finally:
                os.chdir(original_dir)

    def test_format_table(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        results = [
            {
                "ip": "1.1.1.1",
                "domain": "one.one",
                "city": "Austin",
                "country": "US",
                "asn": 13335,
                "asn_org": "Cloudflare",
                "error": None,
            }
        ]

        table = formatter.format_table(results)

        assert table is not None

    def test_format_table_empty(self):
        console = MagicMock()
        formatter = ResultFormatter(console)

        table = formatter.format_table([])

        assert table is not None

    def test_format_table_hides_org_column(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        caps = DataSourceCapabilities(has_proxy=True, has_org=False)
        results = [
            {"ip": "1.1.1.1", "city": "Austin", "country": "US", "asn": 13335, "asn_org": "Cloudflare", "error": None},
            {"ip": "8.8.8.8", "city": "MV", "country": "US", "asn": 15169, "asn_org": "Google", "error": None},
        ]
        table = formatter.format_table(results, caps)
        column_headers = [col.header for col in table.columns]
        assert "Org Info" not in column_headers
        assert "Proxy" in column_headers
        assert len(table.columns) == 4

    def test_format_table_hides_proxy_column(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        caps = DataSourceCapabilities(has_proxy=False, has_org=True)
        results = [
            {
                "ip": "1.1.1.1",
                "city": "Austin",
                "country": "US",
                "asn": 13335,
                "asn_org": "Cloudflare",
                "org_managed": False,
                "org_id": None,
                "platform": None,
                "error": None,
            },
            {
                "ip": "8.8.8.8",
                "city": "MV",
                "country": "US",
                "asn": 15169,
                "asn_org": "Google",
                "org_managed": True,
                "org_id": "GOOG",
                "platform": "gcp",
                "error": None,
            },
        ]
        table = formatter.format_table(results, caps)
        column_headers = [col.header for col in table.columns]
        assert "Proxy" not in column_headers
        assert "Org Info" in column_headers
        assert len(table.columns) == 4

    def test_format_table_hides_both_optional_columns(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        caps = DataSourceCapabilities(has_proxy=False, has_org=False)
        results = [
            {"ip": "1.1.1.1", "city": "Austin", "country": "US", "asn": 13335, "asn_org": "Cloudflare", "error": None},
            {"ip": "8.8.8.8", "city": "MV", "country": "US", "asn": 15169, "asn_org": "Google", "error": None},
        ]
        table = formatter.format_table(results, caps)
        column_headers = [col.header for col in table.columns]
        assert "Org Info" not in column_headers
        assert "Proxy" not in column_headers
        assert len(table.columns) == 3

    def test_format_table_error_row_with_hidden_columns(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        caps = DataSourceCapabilities(has_proxy=False, has_org=False)
        results = [
            {"ip": "1.2.3.4", "error": "IP not found in database"},
            {"ip": "1.1.1.1", "city": "Austin", "country": "US", "asn": 13335, "asn_org": "Cloudflare", "error": None},
        ]
        table = formatter.format_table(results, caps)
        assert len(table.columns) == 3
        assert table.row_count == 2

    def test_format_table_no_capabilities_shows_all(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        results = [
            {"ip": "1.1.1.1", "city": "Austin", "country": "US", "asn": 13335, "asn_org": "Cloudflare", "error": None},
            {"ip": "8.8.8.8", "city": "MV", "country": "US", "asn": 15169, "asn_org": "Google", "error": None},
        ]
        table = formatter.format_table(results)
        assert len(table.columns) == 6

    def test_format_csv_excludes_org_fields(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        caps = DataSourceCapabilities(has_proxy=True, has_org=False)
        results = [{"ip": "1.1.1.1", "error": None}]
        csv_output = formatter.format_csv(results, caps)
        header = csv_output.split("\r\n")[0]
        assert "org_managed" not in header
        assert "org_id" not in header
        assert "platform" not in header
        assert "proxy_type" in header

    def test_format_csv_excludes_proxy_fields(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        caps = DataSourceCapabilities(has_proxy=False, has_org=True)
        results = [{"ip": "1.1.1.1", "error": None}]
        csv_output = formatter.format_csv(results, caps)
        header = csv_output.split("\r\n")[0]
        assert "proxy_type" not in header
        assert "isp" not in header
        assert "usage_type" not in header
        assert "domain" not in header
        assert "org_managed" in header

    def test_format_csv_no_capabilities_shows_all(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        results = [{"ip": "1.1.1.1", "error": None}]
        csv_output = formatter.format_csv(results)
        header = csv_output.split("\r\n")[0]
        assert "org_managed" in header
        assert "proxy_type" in header
        assert "domain" in header
        assert "isp" in header

    def test_format_table_shows_domain_column_with_ipinfo(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        caps = DataSourceCapabilities(has_proxy=False, has_org=False, has_ipinfo=True)
        results = [
            {"ip": "1.1.1.1", "domain": "cloudflare.com", "city": "Austin", "country": "US", "asn": 13335, "asn_org": "Cloudflare", "error": None},
            {"ip": "8.8.8.8", "domain": "google.com", "city": "MV", "country": "US", "asn": 15169, "asn_org": "Google", "error": None},
        ]
        table = formatter.format_table(results, caps)
        column_headers = [col.header for col in table.columns]
        assert "Domain" in column_headers
        assert len(table.columns) == 4  # IP + Domain + Network + Location

    def test_format_table_hides_domain_column_without_ipinfo(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        caps = DataSourceCapabilities(has_proxy=False, has_org=False, has_ipinfo=False)
        results = [
            {"ip": "1.1.1.1", "city": "Austin", "country": "US", "asn": 13335, "asn_org": "Cloudflare", "error": None},
            {"ip": "8.8.8.8", "city": "MV", "country": "US", "asn": 15169, "asn_org": "Google", "error": None},
        ]
        table = formatter.format_table(results, caps)
        column_headers = [col.header for col in table.columns]
        assert "Domain" not in column_headers
        assert len(table.columns) == 3  # IP + Network + Location

    def test_format_csv_shows_domain_with_ipinfo_only(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        caps = DataSourceCapabilities(has_proxy=False, has_org=False, has_ipinfo=True)
        results = [{"ip": "1.1.1.1", "domain": "cloudflare.com", "error": None}]
        csv_output = formatter.format_csv(results, caps)
        header = csv_output.split("\r\n")[0]
        assert "domain" in header
        assert "proxy_type" not in header

    def test_format_csv_hides_domain_without_proxy_or_ipinfo(self):
        console = MagicMock()
        formatter = ResultFormatter(console)
        caps = DataSourceCapabilities(has_proxy=False, has_org=False, has_ipinfo=False)
        results = [{"ip": "1.1.1.1", "error": None}]
        csv_output = formatter.format_csv(results, caps)
        header = csv_output.split("\r\n")[0]
        assert "domain" not in header
