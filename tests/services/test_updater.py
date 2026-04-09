import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from argus_cli.core.config import Config
from argus_cli.services.updater import UpdateChecker


@pytest.fixture
def checker(tmp_path):
    config = MagicMock(spec=Config)
    config.state_file = str(tmp_path / "state.json")
    return UpdateChecker(config, MagicMock(spec=Console))


class TestIsNewer:
    def test_newer_patch(self):
        assert UpdateChecker._is_newer("0.0.5", "0.0.4") is True

    def test_newer_minor(self):
        assert UpdateChecker._is_newer("0.1.0", "0.0.9") is True

    def test_newer_major(self):
        assert UpdateChecker._is_newer("1.0.0", "0.9.9") is True

    def test_same_version(self):
        assert UpdateChecker._is_newer("0.0.4", "0.0.4") is False

    def test_older_version(self):
        assert UpdateChecker._is_newer("0.0.3", "0.0.4") is False

    def test_invalid_version_strings(self):
        assert UpdateChecker._is_newer("not-a-version", "0.0.4") is False


class TestGetLatestVersion:
    def test_returns_cached_version_within_24h(self, checker):
        recent = (datetime.now() - timedelta(hours=1)).isoformat()
        state = {"update_check": {"last_checked": recent, "latest_version": "1.2.3"}}
        with open(checker.config.state_file, "w") as f:
            json.dump(state, f)

        with patch.object(checker, "_fetch_and_cache") as mock_fetch:
            result = checker._get_latest_version()

        assert result == "1.2.3"
        mock_fetch.assert_not_called()

    def test_fetches_when_cache_is_stale(self, checker):
        old = (datetime.now() - timedelta(hours=25)).isoformat()
        state = {"update_check": {"last_checked": old, "latest_version": "0.0.1"}}
        with open(checker.config.state_file, "w") as f:
            json.dump(state, f)

        with patch.object(checker, "_fetch_and_cache", return_value="0.0.5") as mock_fetch:
            result = checker._get_latest_version()

        assert result == "0.0.5"
        mock_fetch.assert_called_once()

    def test_fetches_when_no_state_file(self, checker):
        with patch.object(checker, "_fetch_and_cache", return_value="0.0.5") as mock_fetch:
            result = checker._get_latest_version()

        assert result == "0.0.5"
        mock_fetch.assert_called_once()

    def test_fetches_when_timestamp_is_invalid(self, checker):
        state = {"update_check": {"last_checked": "not-a-date", "latest_version": "0.0.1"}}
        with open(checker.config.state_file, "w") as f:
            json.dump(state, f)

        with patch.object(checker, "_fetch_and_cache", return_value="0.0.5") as mock_fetch:
            result = checker._get_latest_version()

        assert result == "0.0.5"
        mock_fetch.assert_called_once()


class TestFetchAndCache:
    def test_strips_v_prefix_and_caches(self, checker):
        mock_response = MagicMock()
        mock_response.json.return_value = {"tag_name": "v0.0.5"}

        with patch("argus_cli.services.updater.requests.get", return_value=mock_response):
            result = checker._fetch_and_cache()

        assert result == "0.0.5"

        with open(checker.config.state_file) as f:
            state = json.load(f)

        assert state["update_check"]["latest_version"] == "0.0.5"
        assert "last_checked" in state["update_check"]

    def test_handles_missing_tag_name(self, checker):
        mock_response = MagicMock()
        mock_response.json.return_value = {}

        with patch("argus_cli.services.updater.requests.get", return_value=mock_response):
            result = checker._fetch_and_cache()

        assert result == ""

    def test_overwrites_existing_cache(self, checker):
        old = (datetime.now() - timedelta(hours=25)).isoformat()
        state = {"update_check": {"last_checked": old, "latest_version": "0.0.1"}}
        with open(checker.config.state_file, "w") as f:
            json.dump(state, f)

        mock_response = MagicMock()
        mock_response.json.return_value = {"tag_name": "v0.0.5"}

        with patch("argus_cli.services.updater.requests.get", return_value=mock_response):
            result = checker._fetch_and_cache()

        assert result == "0.0.5"


class TestNotifyIfUpdateAvailable:
    def test_prints_notice_when_update_available(self, checker):
        with patch.object(checker, "_get_latest_version", return_value="99.0.0"):
            checker.notify_if_update_available()

        checker.console.print.assert_called_once()
        printed = checker.console.print.call_args[0][0]
        assert "99.0.0" in printed
        assert "uv tool upgrade argus" in printed

    def test_no_notice_when_already_up_to_date(self, checker):
        with (
            patch("argus_cli.services.updater.__version__", "0.0.4"),
            patch.object(checker, "_get_latest_version", return_value="0.0.4"),
        ):
            checker.notify_if_update_available()

        checker.console.print.assert_not_called()

    def test_no_notice_when_on_newer_version(self, checker):
        with (
            patch("argus_cli.services.updater.__version__", "0.0.5"),
            patch.object(checker, "_get_latest_version", return_value="0.0.4"),
        ):
            checker.notify_if_update_available()

        checker.console.print.assert_not_called()

    def test_silently_ignores_network_error(self, checker):
        with patch.object(checker, "_get_latest_version", side_effect=Exception("network failure")):
            checker.notify_if_update_available()  # should not raise

        checker.console.print.assert_not_called()

    def test_silently_ignores_none_version(self, checker):
        with patch.object(checker, "_get_latest_version", return_value=None):
            checker.notify_if_update_available()  # should not raise

        checker.console.print.assert_not_called()
