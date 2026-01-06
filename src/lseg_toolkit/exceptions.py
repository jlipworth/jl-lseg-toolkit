"""
Custom exceptions for LSEG toolkit.

Exception hierarchy:
    LsegError (base)
    ├── SessionError - Session management failures
    ├── DataRetrievalError - API call failures
    ├── DataValidationError - Invalid/unexpected data
    └── ConfigurationError - Invalid configuration
"""


class LsegError(Exception):
    """Base exception for all LSEG toolkit errors."""


class SessionError(LsegError):
    """Failed to establish or maintain LSEG session.

    Raised when:
    - LSEG Workspace Desktop is not running
    - Authentication fails
    - Session unexpectedly closes
    """


class DataRetrievalError(LsegError):
    """Failed to retrieve data from LSEG API.

    Raised when:
    - API call returns None or fails
    - Network timeout occurs
    - Invalid index/ticker specified
    """


class DataValidationError(LsegError):
    """Data retrieved but failed validation or processing.

    Raised when:
    - Expected columns missing from response
    - Data type conversion fails
    - Required fields are empty
    """


class ConfigurationError(LsegError):
    """Invalid configuration parameters.

    Raised when:
    - Invalid date format
    - Invalid index code
    - Conflicting parameters
    """


# =============================================================================
# Timeseries Module Exceptions
# =============================================================================


class InstrumentNotFoundError(LsegError):
    """Instrument not found or invalid.

    Raised when:
    - RIC not found in LSEG
    - Symbol cannot be mapped to RIC
    - Instrument data unavailable
    """


class StorageError(LsegError):
    """Database or storage operation failed.

    Raised when:
    - SQLite connection fails
    - Schema creation fails
    - Read/write operations fail
    - Parquet export fails
    """


class RollCalculationError(LsegError):
    """Continuous contract roll calculation failed.

    Raised when:
    - Insufficient contract data for roll detection
    - Missing prices at roll date
    - Invalid roll configuration
    """
