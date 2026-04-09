import logging
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

import argus_cli.utils.logger as logger_module
from argus_cli.utils.logger import ArgusLogger


@pytest.fixture(autouse=True)
def reset_logger_singleton():
    """Reset the global logger singleton before and after each test."""
    original = logger_module._logger
    logger_module._logger = None
    yield
    logger_module._logger = original


class TestSetVerbose:
    def test_lowers_console_handler_to_debug(self):
        al = ArgusLogger(console=Console())
        al.set_verbose()

        assert al._verbose is True
        assert al.logger.level == logging.DEBUG

        stream_handlers = [
            h
            for h in al.logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        assert len(stream_handlers) == 1
        assert stream_handlers[0].level == logging.DEBUG

    def test_file_handler_level_unchanged(self):
        al = ArgusLogger(console=Console())
        al.set_verbose()

        file_handlers = [h for h in al.logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
        assert file_handlers[0].level == logging.DEBUG  # was already DEBUG

    def test_verbose_false_by_default(self):
        al = ArgusLogger(console=Console())
        assert al._verbose is False


def _raise_value_error():
    raise ValueError


class TestExceptionVerbose:
    def test_prints_traceback_when_verbose(self):
        mock_console = MagicMock(spec=Console)
        al = ArgusLogger(console=mock_console)
        al.set_verbose()

        try:
            _raise_value_error()
        except ValueError:
            al.exception("something went wrong")

        mock_console.print_exception.assert_called_once()

    def test_no_traceback_when_not_verbose(self):
        mock_console = MagicMock(spec=Console)
        al = ArgusLogger(console=mock_console)

        try:
            _raise_value_error()
        except ValueError:
            al.exception("something went wrong")

        mock_console.print_exception.assert_not_called()


class TestVerboseCLIFlag:
    def test_verbose_flag_calls_set_verbose(self):
        from typer.testing import CliRunner

        from argus_cli.argus import app

        runner = CliRunner()
        with (
            patch("argus_cli.argus.logger") as mock_logger,
            patch("argus_cli.argus.UpdateChecker"),
        ):
            runner.invoke(app, ["--verbose", "lookup", "--help"])

        mock_logger.set_verbose.assert_called_once()

    def test_no_verbose_flag_does_not_call_set_verbose(self):
        from typer.testing import CliRunner

        from argus_cli.argus import app

        runner = CliRunner()
        with (
            patch("argus_cli.argus.logger") as mock_logger,
            patch("argus_cli.argus.UpdateChecker"),
        ):
            runner.invoke(app, ["lookup", "--help"])

        mock_logger.set_verbose.assert_not_called()
