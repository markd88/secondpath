from __future__ import annotations

from secondpath import FallbackLayer, ProtectionStatus, protect
from secondpath.detectors import EmptyResult, ExceptionType


def test_primary_success_returns_success() -> None:
    def primary(url: str) -> dict:
        return {"headline": f"hello {url}", "image": "img.png"}

    plan = protect(primary=primary)

    result = plan.run(url="https://merchant.example")

    assert result.status is ProtectionStatus.SUCCESS
    assert result.final_layer == "primary"
    assert result.used_fallback is False
    assert result.output["headline"] == "hello https://merchant.example"


def test_empty_result_triggers_degraded_fallback() -> None:
    def primary(url: str, country: str) -> dict:
        return {"headline": "", "image": None}

    def text_only(url: str, country: str, *, context=None) -> dict:
        assert context is not None
        assert isinstance(context.primary_output, dict)
        return {"headline": "template headline", "image": None}

    plan = protect(
        primary=primary,
        detect=[EmptyResult("headline")],
        fallback_chain=[FallbackLayer.degraded_ai("text_only", text_only)],
        name="creative_generation",
    )

    result = plan.run(url="https://merchant.example", country="DE")

    assert result.status is ProtectionStatus.DEGRADED
    assert result.final_layer == "text_only"
    assert result.final_kind is not None
    assert result.failure_type == "empty_result"
    assert result.output == {"headline": "template headline", "image": None}


def test_human_layer_returns_escalated() -> None:
    def primary(url: str, country: str) -> dict:
        raise TimeoutError("crawl timed out")

    def auto_fallback(url: str, country: str) -> dict:
        raise ValueError("automatic fallback failed")

    def human_review(url: str, country: str, *, context=None) -> dict:
        assert context is not None
        return {
            "status": "queued_for_review",
            "failure_type": context.failure_type,
        }

    plan = protect(
        primary=primary,
        detect=[ExceptionType(TimeoutError, "timeout")],
        fallback_chain=[
            FallbackLayer.degraded_ai("auto", auto_fallback),
            FallbackLayer.human("human_review", human_review),
        ],
    )

    result = plan.run(url="https://merchant.example", country="DE")

    assert result.status is ProtectionStatus.ESCALATED
    assert result.final_layer == "human_review"
    assert result.failure_type == "timeout"
    assert result.output["status"] == "queued_for_review"
