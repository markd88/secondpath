"""Public factory for building protection plans."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from secondpath.plan import ProtectionPlan
from secondpath.types import Detector, FallbackKind, FallbackLayer, Handler, Sink


def protect(
    primary: Handler,
    *,
    detect: Optional[Sequence[Detector]] = None,
    fallback_chain: Optional[Sequence[object]] = None,
    sinks: Optional[Sequence[Sink]] = None,
    name: str = "protected_execution",
) -> ProtectionPlan:
    return ProtectionPlan(
        primary=primary,
        fallback_chain=[_coerce_layer(item, index) for index, item in enumerate(fallback_chain or [])],
        detectors=list(detect or []),
        sinks=list(sinks or []),
        name=name,
    )


def _coerce_layer(item: object, index: int) -> FallbackLayer:
    if isinstance(item, FallbackLayer):
        return item
    if callable(item):
        name = getattr(item, "__name__", f"fallback_{index}")
        return FallbackLayer(name=name, kind=FallbackKind.RULE_BASED, handler=item)
    raise TypeError(f"Unsupported fallback layer: {item!r}")
