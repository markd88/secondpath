"""Protection plan runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from inspect import Signature, signature
from typing import Any, Optional
from uuid import uuid4

from secondpath.errors import ConfigurationError, DetectorError
from secondpath.types import (
    Detector,
    ExecutionContext,
    FallbackKind,
    FallbackLayer,
    Incident,
    Handler,
    ProtectionResult,
    ProtectionStatus,
    Sink,
)


@dataclass
class ProtectionPlan:
    primary: Handler
    fallback_chain: list[FallbackLayer] = field(default_factory=list)
    detectors: list[Detector] = field(default_factory=list)
    sinks: list[Sink] = field(default_factory=list)
    name: str = "protected_execution"

    def __post_init__(self) -> None:
        if not callable(self.primary):
            raise ConfigurationError("primary must be callable")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ConfigurationError("plan name must be a non-empty string")
        for layer in self.fallback_chain:
            if not isinstance(layer.name, str) or not layer.name.strip():
                raise ConfigurationError("fallback layer names must be non-empty strings")
            if not callable(layer.handler):
                raise ConfigurationError(f"fallback layer '{layer.name}' must have a callable handler")
        for detector in self.detectors:
            if not hasattr(detector, "check") or not callable(detector.check):
                raise ConfigurationError("all detectors must define a callable check(...) method")
        for sink in self.sinks:
            if not hasattr(sink, "emit") or not callable(sink.emit):
                raise ConfigurationError("all sinks must define a callable emit(...) method")

    def run(self, *args: Any, **kwargs: Any) -> ProtectionResult:
        context = ExecutionContext(
            execution_id=self._new_id("exec"),
            plan_name=self.name,
            started_at=datetime.now(timezone.utc),
            metadata=self._metadata_from_args(kwargs),
        )
        self._validate_handler_call(
            self.primary,
            handler_name="primary",
            args=args,
            kwargs=kwargs,
            context=context,
        )

        primary_error: Exception | None = None
        primary_output: Any = None

        try:
            primary_output = self._invoke_handler(self.primary, args=args, kwargs=kwargs, context=context)
            context.primary_output = primary_output
        except Exception as error:  # noqa: BLE001
            context.primary_error = error
            primary_error = error

        failure_type = self._detect(output=primary_output, error=primary_error, context=context)
        if primary_error is not None:
            failure_type = failure_type or type(primary_error).__name__

        if primary_error is None and failure_type is None:
            return ProtectionResult(
                execution_id=context.execution_id,
                output=primary_output,
                status=ProtectionStatus.SUCCESS,
                used_fallback=False,
                final_layer="primary",
                summary="Primary path completed successfully.",
            )

        context.failure_type = failure_type

        for layer in self.fallback_chain:
            context.used_fallback = True
            context.current_layer = layer.name
            context.fallback_history.append(layer.name)
            self._validate_handler_call(
                layer.handler,
                handler_name=layer.name,
                args=args,
                kwargs=kwargs,
                context=context,
            )

            try:
                fallback_output = self._invoke_handler(layer.handler, args=args, kwargs=kwargs, context=context)
                status = (
                    ProtectionStatus.ESCALATED
                    if layer.kind is FallbackKind.HUMAN
                    else ProtectionStatus.DEGRADED
                )
                incident = self._build_incident(context, status)
                self._emit_incident(incident)
                return ProtectionResult(
                    execution_id=context.execution_id,
                    output=fallback_output,
                    status=status,
                    used_fallback=True,
                    final_layer=layer.name,
                    final_kind=layer.kind,
                    incident_id=incident.incident_id,
                    failure_type=failure_type,
                    summary=incident.summary,
                )
            except Exception:  # noqa: BLE001
                continue

        incident = self._build_incident(context, ProtectionStatus.FAILED)
        self._emit_incident(incident)
        return ProtectionResult(
            execution_id=context.execution_id,
            output=None,
            status=ProtectionStatus.FAILED,
            used_fallback=bool(self.fallback_chain),
            final_layer=context.current_layer,
            incident_id=incident.incident_id,
            failure_type=failure_type,
            summary=incident.summary,
        )

    def _detect(
        self,
        *,
        output: Any,
        error: Exception | None,
        context: ExecutionContext,
    ) -> Optional[str]:
        for detector in self.detectors:
            try:
                failure_type = detector.check(output=output, error=error, context=context)
            except Exception as exc:  # noqa: BLE001
                raise DetectorError(
                    f"Detector '{type(detector).__name__}' failed during execution: {exc}"
                ) from exc
            if failure_type is not None:
                return failure_type
        return None

    def _build_incident(
        self,
        context: ExecutionContext,
        status: ProtectionStatus,
    ) -> Incident:
        failure_type = context.failure_type or "unknown_failure"
        layer_text = context.current_layer
        if status is ProtectionStatus.DEGRADED:
            summary = f"Primary path failed; delivered fallback layer '{layer_text}'."
        elif status is ProtectionStatus.ESCALATED:
            summary = f"Primary path failed; escalated to human layer '{layer_text}'."
        else:
            summary = "Primary path failed and no fallback layer completed successfully."

        return Incident(
            incident_id=self._new_id("inc"),
            execution_id=context.execution_id,
            plan_name=context.plan_name,
            failure_type=failure_type,
            failed_stage=context.failed_stage,
            triggered_by=failure_type,
            fallback_attempted=list(context.fallback_history),
            final_status=status,
            summary=summary,
            metadata=dict(context.metadata),
        )

    def _emit_incident(self, incident: Incident) -> None:
        sink_errors = self._sink_errors(incident)
        if sink_errors:
            incident.metadata.setdefault("sink_errors", []).extend(sink_errors)

    def _sink_errors(self, incident: Incident) -> list[str]:
        errors: list[str] = []
        for sink in self.sinks:
            try:
                sink.emit(incident)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(sink).__name__}: {exc}")
        return errors

    @staticmethod
    def _validate_handler_call(
        handler: Handler,
        *,
        handler_name: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        context: ExecutionContext,
    ) -> None:
        sig = ProtectionPlan._get_handler_signature(handler)
        if sig is None:
            return

        call_kwargs = ProtectionPlan._build_handler_kwargs(handler, kwargs=kwargs, context=context)
        try:
            sig.bind_partial(*args, **call_kwargs)
        except TypeError as exc:
            raise ConfigurationError(
                f"Handler '{handler_name}' is not compatible with plan.run(...) arguments: {exc}"
            ) from exc

    @staticmethod
    def _invoke_handler(
        handler: Handler,
        *,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        call_kwargs = ProtectionPlan._build_handler_kwargs(handler, kwargs=kwargs, context=context)
        return handler(*args, **call_kwargs)

    @staticmethod
    def _build_handler_kwargs(
        handler: Handler,
        *,
        kwargs: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        call_kwargs = dict(kwargs)
        if ProtectionPlan._handler_accepts_context(handler):
            call_kwargs["context"] = context
        return call_kwargs

    @staticmethod
    def _handler_accepts_context(handler: Handler) -> bool:
        sig = ProtectionPlan._get_handler_signature(handler)
        if sig is None:
            return False
        if "context" in sig.parameters:
            return True
        return any(param.kind == param.VAR_KEYWORD for param in sig.parameters.values())

    @staticmethod
    def _get_handler_signature(handler: Handler) -> Optional[Signature]:
        try:
            return signature(handler)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _metadata_from_args(kwargs: dict[str, Any]) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        for key, value in kwargs.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                metadata[key] = value
        return metadata

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"
