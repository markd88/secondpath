"""Project-specific exceptions."""


class SecondPathError(Exception):
    """Base exception for SecondPath."""


class ConfigurationError(SecondPathError):
    """Raised when a protection plan is configured incorrectly."""


class DetectorError(SecondPathError):
    """Raised when a detector fails during execution."""
