class MergetypError(Exception):
    """Base class for expected application errors

    Args:
        message: Human-readable error message
    """

    exit_code = 1

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class InputFileNotFoundError(MergetypError):
    """Raised when template or data file does not exist"""

    exit_code = 2


class TypstNotFoundError(MergetypError):
    """Raised when Typst CLI is not available on PATH"""


class DataValidationError(MergetypError):
    """Raised when input data cannot be loaded or validated"""


class FilenamePatternError(MergetypError):
    """Raised when output filename pattern is invalid"""


class OutputCollisionError(MergetypError):
    """Raised when output file names collide"""


class OutputWriteError(MergetypError):
    """Raised when PDF output cannot be written"""


class TypstCompileError(MergetypError):
    """Raised when Typst returns a non-zero exit code"""


class TypstTimeoutError(MergetypError):
    """Raised when Typst compilation exceeds timeout"""
