"""Tests for command classes."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from argus_cli.commands.lookup import LookupCommand
from argus_cli.commands.setup import SetupCommand


class TestSetupCommand:
    """Test cases for SetupCommand class."""

    @pytest.fixture
    def setup_command(self, mock_console):
        return SetupCommand(mock_console)

    @pytest.fixture
    def mock_config(self, sample_config_data):
        config_instance = MagicMock()
        config_instance.config_file = "/tmp/test_keys.json"  # noqa: S108
        config_instance.data_dir = MagicMock()
        return config_instance

    @pytest.fixture
    def setup_command_with_mock_config(self, mock_console, mock_config):
        with patch("argus_cli.commands.setup.Config") as mock_config_class:
            mock_config_class.return_value = mock_config
            return SetupCommand(mock_console)

    def test_init(self, mock_console):
        """Test SetupCommand initialization."""
        setup_cmd = SetupCommand(mock_console)
        assert setup_cmd.console == mock_console
        assert setup_cmd.config is not None

    @patch("argus_cli.commands.setup.typer.prompt")
    @patch("argus_cli.commands.setup.os.path.exists")
    @patch("argus_cli.commands.setup.open")
    def test_execute_success(self, mock_open, mock_exists, mock_prompt, setup_command_with_mock_config, mock_config):
        """Test successful setup execution."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '{"maxmind_license_key": ""}'
        mock_prompt.side_effect = [1, "test_license_key"]

        with patch("argus_cli.commands.setup.typer.Exit") as mock_exit_class:
            mock_exit_class.side_effect = lambda code=0: SystemExit(code)
            setup_command_with_mock_config.execute()

        mock_config.data_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_prompt.assert_called()

    @patch("argus_cli.commands.setup.typer.prompt")
    def test_execute_cancel(self, mock_prompt, setup_command_with_mock_config):
        """Test setup cancellation."""
        mock_prompt.return_value = 0

        with patch("argus_cli.commands.setup.typer.Exit") as mock_exit_class:
            mock_exit_class.side_effect = lambda code=0: SystemExit(code)
            with pytest.raises(SystemExit) as exc_info:
                setup_command_with_mock_config.execute()
            assert exc_info.value.code == 0

    @patch("argus_cli.commands.setup.typer.prompt")
    def test_execute_empty_key(self, mock_prompt, setup_command_with_mock_config, mock_config):
        """Test setup with empty license key."""
        mock_prompt.side_effect = [1, ""]

        with patch("argus_cli.commands.setup.typer.Exit") as mock_exit_class:
            mock_exit_class.side_effect = lambda code=0: SystemExit(code)
            with pytest.raises(SystemExit) as exc_info:
                setup_command_with_mock_config.execute()
            assert exc_info.value.code == 1


class TestLookupCommand:
    """Test cases for LookupCommand class."""

    @pytest.fixture
    def lookup_command(self, mock_console):
        return LookupCommand(mock_console)

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.db_city = "/tmp/city.mmdb"  # noqa: S108
        config.db_asn = "/tmp/asn.mmdb"  # noqa: S108
        config.db_proxy = "/tmp/proxy.bin"  # noqa: S108
        config.db_org_dir = "/tmp/org"  # noqa: S108
        return config

    def test_init(self, mock_console):
        """Test LookupCommand initialization."""
        lookup_cmd = LookupCommand(mock_console)
        assert lookup_cmd.console == mock_console
        assert lookup_cmd.config is not None

    def test_execute_with_validation_success(self, lookup_command):
        """Test successful lookup execution."""
        with patch.object(lookup_command, "db_manager") as mock_db:
            mock_db.ensure_databases = MagicMock()

            with patch.object(lookup_command, "_collect_ips") as mock_collect:
                mock_collect.return_value = ["8.8.8.8"]

                with patch.object(lookup_command, "lookup_service") as mock_service:
                    mock_service.lookup_ips.return_value = [{"ip": "8.8.8.8", "country": "US", "error": None}]

                    with patch.object(lookup_command, "_filter_results") as mock_filter:
                        mock_filter.return_value = [{"ip": "8.8.8.8", "country": "US", "error": None}]

                        with patch.object(lookup_command, "_sort_results") as mock_sort:
                            mock_sort.return_value = [{"ip": "8.8.8.8", "country": "US", "error": None}]

                            with patch("argus_cli.commands.lookup.typer.Exit") as mock_exit_class:
                                mock_exit_class.side_effect = lambda code=0: SystemExit(code)

                                with patch.object(lookup_command, "formatter") as mock_formatter:
                                    mock_formatter.format_table.return_value = MagicMock()
                                    result = lookup_command.execute(
                                        ip="8.8.8.8",
                                        file=Path("/tmp/test.txt"),  # noqa: S108
                                        output=None,
                                        output_format="json",
                                        exclude_country=None,
                                        exclude_city=None,
                                        exclude_asn=None,
                                        exclude_org=None,
                                        exclude_org_managed=False,
                                        exclude_not_org_managed=False,
                                        exclude_platform=None,
                                        exclude_org_id=None,
                                        sort_by="asn_org",
                                    )

                                    assert result is not None
                                    assert len(result) == 1
                                    assert result[0]["ip"] == "8.8.8.8"

    def test_collect_ips_single_ip(self, lookup_command):
        """Test collecting a single IP address."""
        with patch.object(lookup_command, "file_parser") as mock_parser:
            mock_parser.expand_cidr.side_effect = ValueError("Not CIDR")

            ips = lookup_command._collect_ips("8.8.8.8", None)

            assert ips == ["8.8.8.8"]

    def test_collect_ips_cidr(self, lookup_command):
        """Test expanding CIDR block to individual IPs."""
        cidr = "192.168.1.0/30"
        expanded_ips = ["192.168.1.1", "192.168.1.2"]

        with patch.object(lookup_command, "file_parser") as mock_parser:
            mock_parser.expand_cidr.return_value = expanded_ips

            ips = lookup_command._collect_ips(cidr, None)

            assert ips == expanded_ips
            mock_parser.expand_cidr.assert_called_once_with(cidr)

    def test_collect_ips_from_file(self, lookup_command):
        """Test collecting IPs from file."""
        extracted_ips = ["8.8.8.8", "1.1.1.1"]
        file_path = Path("/tmp/test.txt")  # noqa: S108

        with patch.object(lookup_command, "file_parser") as mock_parser:
            mock_parser.read_file_content.return_value = "8.8.8.8 1.1.1.1"
            mock_parser.extract_ips.return_value = extracted_ips

            ips = lookup_command._collect_ips(None, file_path)

            assert ips == extracted_ips
            mock_parser.read_file_content.assert_called_once_with(str(file_path))
            mock_parser.extract_ips.assert_called_once_with("8.8.8.8 1.1.1.1")

    def test_filter_results(self, lookup_command):
        """Test result filtering."""
        sample_results = [
            {"ip": "8.8.8.8", "country": "US", "asn": 15169, "org_managed": False},
            {"ip": "1.1.1.1", "country": "AU", "asn": 13335, "org_managed": True},
        ]

        # Mock the ResultFilter class
        with patch("argus_cli.commands.lookup.ResultFilter") as mock_filter_class:
            mock_filter_instance = MagicMock()
            mock_filter_instance.filter_results.return_value = [sample_results[1]]
            mock_filter_class.return_value = mock_filter_instance

            filtered = lookup_command._filter_results(
                sample_results,
                exclude_country=["US"],
                exclude_city=None,
                exclude_asn=None,
                exclude_org=None,
                exclude_org_managed=False,
                exclude_not_org_managed=False,
                exclude_platform=None,
                exclude_org_id=None,
            )

            assert len(filtered) == 1
            assert filtered[0]["country"] == "AU"

    def test_sort_results(self, lookup_command):
        """Test result sorting."""
        sample_results = [
            {"ip": "8.8.8.8", "asn_org": "Google LLC"},
            {"ip": "1.1.1.1", "asn_org": "Amazon.com"},
        ]

        sorted_results = lookup_command._sort_results(sample_results, "asn_org")

        assert len(sorted_results) == 2
        assert sorted_results[0]["asn_org"] == "Amazon.com"
        assert sorted_results[1]["asn_org"] == "Google LLC"

    def test_sort_results_by_asn(self, lookup_command):
        """Test result sorting by ASN number."""
        sample_results = [
            {"ip": "8.8.8.8", "asn": 15169},
            {"ip": "1.1.1.1", "asn": 13335},
            {"ip": "9.9.9.9", "asn": None},
        ]

        sorted_results = lookup_command._sort_results(sample_results, "asn")

        assert len(sorted_results) == 3
        assert sorted_results[0]["asn"] == 13335
        assert sorted_results[1]["asn"] == 15169
        assert sorted_results[2]["asn"] is None
