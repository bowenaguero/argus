import json
import os
from datetime import datetime, timedelta

import requests
from rich.console import Console

from .. import __version__
from ..core.config import Config

GITHUB_RELEASES_URL = "https://api.github.com/repos/bowenaguero/argus/releases/latest"
STATE_KEY = "update_check"
CHECK_INTERVAL_HOURS = 24


class UpdateChecker:
    def __init__(self, config: Config, console: Console):
        self.config = config
        self.console = console

    def notify_if_update_available(self) -> None:
        """Check for a newer release and print a notice if one exists. Always silent on failure."""
        try:
            latest = self._get_latest_version()
            if latest and self._is_newer(latest, __version__):
                self.console.print(
                    f"\n[dim]A new version of argus is available: [bold]{latest}[/bold] "
                    f"(current: {__version__}). Run [cyan]uv tool upgrade argus[/cyan] to update.[/dim]"
                )
        except Exception:  # noqa: S110
            pass

    def _get_latest_version(self) -> str | None:
        """Return the latest version string, using a 24hr cache."""
        state = self._load_state()
        entry = state.get(STATE_KEY, {})
        last_checked = entry.get("last_checked")

        if last_checked:
            try:
                last_dt = datetime.fromisoformat(last_checked)
                if datetime.now() - last_dt < timedelta(hours=CHECK_INTERVAL_HOURS):
                    return entry.get("latest_version")
            except Exception:  # noqa: S110
                pass

        return self._fetch_and_cache()

    def _fetch_and_cache(self) -> str | None:
        """Hit the GitHub Releases API and cache the result."""
        response = requests.get(
            GITHUB_RELEASES_URL,
            headers={"Accept": "application/vnd.github+json"},
            timeout=5,
        )
        response.raise_for_status()
        tag = response.json().get("tag_name", "")
        latest = tag.lstrip("v")

        state = self._load_state()
        state[STATE_KEY] = {
            "last_checked": datetime.now().isoformat(),
            "latest_version": latest,
        }
        self._save_state(state)
        return latest

    @staticmethod
    def _is_newer(latest: str, current: str) -> bool:
        """Compare version strings without external dependencies."""
        try:
            return tuple(int(x) for x in latest.split(".")) > tuple(int(x) for x in current.split("."))
        except Exception:
            return False

    def _load_state(self) -> dict:
        """Reuse the same state.json used by DatabaseManager."""
        try:
            if os.path.exists(self.config.state_file):
                with open(self.config.state_file) as f:
                    return json.load(f)
        except Exception:  # noqa: S110
            pass
        return {}

    def _save_state(self, state: dict) -> None:
        with open(self.config.state_file, "w") as f:
            json.dump(state, f, indent=2)
