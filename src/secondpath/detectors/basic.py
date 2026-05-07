"""Simple built-in detectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from secondpath.types import ExecutionContext


@dataclass
class EmptyResult:
    field: str

    def check(
        self,
        *,
        output: Any,
        error: Exception | None,
        context: ExecutionContext,
    ) -> Optional[str]:
        if error is not None or not isinstance(output, dict):
            return None
        value = output.get(self.field)
        if value in (None, "", [], {}):
            context.failed_stage = context.failed_stage or "output_validation"
            return "empty_result"
        return None


@dataclass
class InvalidStructuredOutput:
    def check(
        self,
        *,
        output: Any,
        error: Exception | None,
        context: ExecutionContext,
    ) -> Optional[str]:
        if error is not None:
            return None
        if not isinstance(output, dict):
            context.failed_stage = context.failed_stage or "output_validation"
            return "invalid_structured_output"
        return None


@dataclass
class ExceptionType:
    error_type: type[Exception]
    failure_name: str

    def check(
        self,
        *,
        output: Any,
        error: Exception | None,
        context: ExecutionContext,
    ) -> Optional[str]:
        del output, context
        if error is not None and isinstance(error, self.error_type):
            return self.failure_name
        return None
