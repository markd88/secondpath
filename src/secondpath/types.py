"""Core types for SecondPath."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Protocol


class FallbackKind(str, Enum):
    DEGRADED_AI = "degraded_ai"
    RULE_BASED = "rule_based"
    HUMAN = "human"


class ProtectionStatus(str, Enum):
    SUCCESS = "success"
    DEGRADED = "degraded"
    ESCALATED = "escalated"
    FAILED = "failed"


Handler = Callable[..., Any]


@dataclass
class FallbackLayer:
    name: str
    kind: FallbackKind
    handler: Handler
    description: str = ""

    @classmethod
    def degraded_ai(cls, name: str, handler: Handler, description: str = "") -> "FallbackLayer":
        return cls(name=name, kind=FallbackKind.DEGRADED_AI, handler=handler, description=description)

    @classmethod
    def rule_based(cls, name: str, handler: Handler, description: str = "") -> "FallbackLayer":
        return cls(name=name, kind=FallbackKind.RULE_BASED, handler=handler, description=description)

    @classmethod
    def human(cls, name: str, handler: Handler, description: str = "") -> "FallbackLayer":
        return cls(name=name, kind=FallbackKind.HUMAN, handler=handler, description=description)


@dataclass
class ExecutionContext:
    execution_id: str
    plan_name: str
    started_at: datetime
    current_layer: str = "primary"
    failed_stage: Optional[str] = None
    failure_type: Optional[str] = None
    used_fallback: bool = False
    fallback_history: list[str] = field(default_factory=list)
    primary_output: Any = None
    primary_error: Optional[Exception] = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Incident:
    incident_id: str
    execution_id: str
    plan_name: str
    failure_type: str
    failed_stage: Optional[str]
    triggered_by: str
    fallback_attempted: list[str]
    final_status: ProtectionStatus
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProtectionResult:
    execution_id: str
    output: Any
    status: ProtectionStatus
    used_fallback: bool
    final_layer: str
    final_kind: Optional[FallbackKind] = None
    incident_id: Optional[str] = None
    failure_type: Optional[str] = None
    summary: str = ""


class Detector(Protocol):
    def check(
        self,
        *,
        output: Any,
        error: Exception | None,
        context: ExecutionContext,
    ) -> Optional[str]:
        ...


class Sink(Protocol):
    def emit(self, incident: Incident) -> None:
        ...
