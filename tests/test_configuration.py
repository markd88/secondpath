from __future__ import annotations

import pytest

from secondpath import protect
from secondpath.errors import ConfigurationError, DetectorError


def test_empty_plan_name_raises_configuration_error() -> None:
    def primary(url: str) -> dict:
        return {"headline": url}

    with pytest.raises(ConfigurationError):
        protect(primary=primary, name="")


def test_fallback_signature_mismatch_raises_configuration_error() -> None:
    def primary(url: str, country: str) -> dict:
        raise TimeoutError("boom")

    def invalid_fallback(merchant_id: str) -> dict:
        return {"headline": merchant_id}

    plan = protect(primary=primary, fallback_chain=[invalid_fallback])

    with pytest.raises(ConfigurationError):
        plan.run(url="https://merchant.example", country="DE")


def test_invalid_detector_interface_raises_configuration_error() -> None:
    def primary(url: str) -> dict:
        return {"headline": url}

    with pytest.raises(ConfigurationError):
        protect(primary=primary, detect=[object()])


def test_detector_crash_raises_detector_error() -> None:
    class BrokenDetector:
        def check(self, *, output, error, context):
            raise RuntimeError("detector broke")

    def primary(url: str) -> dict:
        return {"headline": url}

    plan = protect(primary=primary, detect=[BrokenDetector()])

    with pytest.raises(DetectorError):
        plan.run(url="https://merchant.example")


def test_detector_crash_does_not_fallback() -> None:
    class BrokenDetector:
        def check(self, *, output, error, context):
            raise RuntimeError("detector broke")

    def primary(url: str) -> dict:
        return {"headline": url}

    def fallback(url: str) -> dict:
        return {"headline": "fallback"}

    plan = protect(
        primary=primary,
        detect=[BrokenDetector()],
        fallback_chain=[fallback],
    )

    with pytest.raises(DetectorError):
        plan.run(url="https://merchant.example")
