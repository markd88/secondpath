"""SecondPath public API."""

from secondpath.errors import ConfigurationError, DetectorError, SecondPathError
from secondpath.plan import ProtectionPlan
from secondpath.protect import protect
from secondpath.types import (
    Detector,
    ExecutionContext,
    FallbackKind,
    FallbackLayer,
    Incident,
    ProtectionResult,
    ProtectionStatus,
    Sink,
)

__version__ = "0.1.0a1"

__all__ = [
    "ConfigurationError",
    "Detector",
    "DetectorError",
    "ExecutionContext",
    "FallbackKind",
    "FallbackLayer",
    "Incident",
    "ProtectionPlan",
    "ProtectionResult",
    "ProtectionStatus",
    "SecondPathError",
    "Sink",
    "protect",
]
