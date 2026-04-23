from unittest.mock import MagicMock, patch

from rich.console import Console

from argus_cli.core.config import Config
from argus_cli.services.database import DatabaseManager


class TestNeedsDownload:
    @patch("argus_cli.services.database.DatabaseManager.load_state")
    def test_needs_download_no_state(self, mock_load_state):
        mock_load_state.return_value = {}
        config = Config()
        db_manager = DatabaseManager(config, Console())
        assert db_manager.needs_download("GeoLite2-City") is True

    @patch("argus_cli.services.database.DatabaseManager.load_state")
    def test_needs_download_old_data(self, mock_load_state):
        from datetime import datetime, timedelta

        old_time = (datetime.now() - timedelta(hours=48)).isoformat()
        mock_load_state.return_value = {"GeoLite2-City": old_time}
        config = Config()
        db_manager = DatabaseManager(config, Console())
        assert db_manager.needs_download("GeoLite2-City") is True

    @patch("argus_cli.services.database.DatabaseManager.load_state")
    def test_no_download_needed_recent(self, mock_load_state):
        from datetime import datetime, timedelta

        recent_time = (datetime.now() - timedelta(hours=12)).isoformat()
        mock_load_state.return_value = {"GeoLite2-City": recent_time}
        config = Config()
        db_manager = DatabaseManager(config, Console())
        assert db_manager.needs_download("GeoLite2-City") is False

    @patch("argus_cli.services.database.DatabaseManager.load_state")
    def test_needs_download_invalid_format(self, mock_load_state):
        mock_load_state.return_value = {"GeoLite2-City": "invalid-date"}
        config = Config()
        db_manager = DatabaseManager(config, Console())
        assert db_manager.needs_download("GeoLite2-City") is True


class TestDownloadIpinfoDatabase:
    @patch("argus_cli.services.database.shutil.move")
    @patch("argus_cli.services.database.DatabaseManager._update_state")
    @patch("argus_cli.services.database.DatabaseManager._download_file")
    @patch("argus_cli.services.database.DatabaseManager.needs_download")
    def test_download_ipinfo_database_success(self, mock_needs, mock_dl, mock_state, mock_move):
        mock_needs.return_value = True
        config = Config()
        console = MagicMock(spec=Console)
        db_manager = DatabaseManager(config, console)

        result = db_manager.download_ipinfo_database("test_token", "/tmp/ipinfo_lite.mmdb")

        assert result is True
        mock_dl.assert_called_once()
        mock_move.assert_called_once()
        mock_state.assert_called_once_with("ipinfo_lite")

    @patch("argus_cli.services.database.DatabaseManager.needs_download")
    def test_download_ipinfo_database_skips_when_fresh(self, mock_needs):
        mock_needs.return_value = False
        config = Config()
        console = MagicMock(spec=Console)
        db_manager = DatabaseManager(config, console)

        result = db_manager.download_ipinfo_database("test_token", "/tmp/ipinfo_lite.mmdb")

        assert result is True
