import logging
import sys
from pathlib import Path

from rich.console import Console


class ArgusLogger:
    """Centralized logging configuration for Argus CLI."""

    def __init__(self, name: str = "argus", console: Console | None = None):
        self.name = name
        self.console = console
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Configure and return logger instance."""
        logger = logging.getLogger(self.name)

        if logger.handlers:
            return logger

        logger.setLevel(logging.INFO)

        # Console handler with formatting
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)

        # File handler for detailed logs
        log_file = Path.home() / ".argus" / "logs" / "argus.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
        if self.console:
            self.console.print(f"[yellow]⚠[/yellow] {message}")

    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
        if self.console:
            self.console.print(f"[red]✗ Error:[/red] {message}")

    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)
        if self.console:
            self.console.print(f"[bold red]CRITICAL:[/bold red] {message}")

    def exception(self, message: str) -> None:
        """Log exception with traceback."""
        self.logger.exception(message)
        if self.console:
            self.console.print(f"[red]✗ Exception:[/red] {message}")


# Global logger instance
_logger: ArgusLogger | None = None


def get_logger(console: Console | None = None) -> ArgusLogger:
    """Get or create the global logger instance."""
    global _logger
    if _logger is None:
        _logger = ArgusLogger(console=console)
    return _logger
