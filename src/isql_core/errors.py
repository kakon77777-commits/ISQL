class ISQLError(Exception):
    """Base ISQL error."""


class ISQLValidationError(ISQLError):
    """Raised when canonical ISQL input is invalid."""


class ISQLExecutionError(ISQLError):
    """Raised when a valid code cannot be executed in the current registry."""


class ISQLNotFoundError(ISQLError):
    """Raised when a referenced stored object cannot be found."""
