"""Custom exceptions for Argus CLI."""


class ArgusError(Exception):
    """Base exception for all Argus CLI errors."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ConfigurationError(ArgusError):
    """Raised when there's a configuration problem."""

    pass


class DatabaseError(ArgusError):
    """Raised when database operations fail."""

    pass


class IpLookupError(ArgusError):
    """Raised when IP lookup operations fail."""

    pass


class ValidationError(ArgusError):
    """Raised when parameter validation fails."""

    pass


class FileOperationError(ArgusError):
    """Raised when file operations fail."""

    pass


class NetworkError(ArgusError):
    """Raised when network operations fail."""

    pass


class AuthenticationError(ArgusError):
    """Raised when authentication/authorization fails."""

    pass


class CLIExitError(ArgusError):
    """Custom CLI exit exception."""

    pass
