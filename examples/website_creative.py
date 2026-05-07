"""Canonical website-to-creative demo for SecondPath.

This example shows three outcomes:

1. success: the primary AI path works
2. degraded: the workflow falls back to a safer automatic layer
3. escalated: the workflow reaches the human layer
"""

from __future__ import annotations

from secondpath import FallbackLayer, protect
from secondpath.detectors import EmptyResult, ExceptionType
from secondpath.sinks import StdoutSink


COUNTRY_TEMPLATES = {
    "DE": "Entdecke Produkte, die zu deinem Markt passen.",
    "US": "Discover offers tailored to your market.",
}


def generate_creative_from_url(url: str, country: str) -> dict:
    if "timeout" in url:
        raise TimeoutError("crawl timed out")
    if "empty" in url:
        return {"headline": "", "image": None}
    if "blocked" in url:
        raise ValueError("merchant page blocked or unsupported")
    return {
        "headline": f"Smart creative for {url} in {country}",
        "image": "generated-image.png",
    }


def text_only_fallback(url: str, country: str, *, context=None) -> dict:
    if "blocked" in url:
        raise ValueError("text-only fallback also cannot safely continue")
    del country
    headline = None
    if context is not None and isinstance(context.primary_output, dict):
        headline = context.primary_output.get("headline")
    return {
        "headline": headline or "Discover products built for everyday needs.",
        "image": None,
    }


def country_template_fallback(url: str, country: str) -> dict:
    if "blocked" in url:
        raise ValueError("template fallback disabled for blocked merchant")
    return {
        "headline": COUNTRY_TEMPLATES.get(country, "Explore relevant offers for your market."),
        "image": None,
    }


def human_review_fallback(url: str, country: str, *, context=None) -> dict:
    return {
        "status": "queued_for_review",
        "url": url,
        "country": country,
        "failure_type": getattr(context, "failure_type", None),
    }


plan = protect(
    primary=generate_creative_from_url,
    detect=[
        EmptyResult("headline"),
        ExceptionType(TimeoutError, "timeout"),
    ],
    fallback_chain=[
        FallbackLayer.degraded_ai(
            name="text_only",
            handler=text_only_fallback,
            description="Skip image generation and return text only.",
        ),
        FallbackLayer.rule_based(
            name="country_template",
            handler=country_template_fallback,
            description="Return a PM-approved country template.",
        ),
        FallbackLayer.human(
            name="human_review",
            handler=human_review_fallback,
            description="Queue the case for human review.",
        ),
    ],
    sinks=[StdoutSink()],
    name="website_creative",
)


if __name__ == "__main__":
    scenarios = [
        ("success", "https://merchant.example"),
        ("degraded", "https://empty.example"),
        ("escalated", "https://blocked.example"),
    ]

    for label, url in scenarios:
        result = plan.run(url=url, country="DE")
        print(f"[{label}] {url}")
        print(f"  status={result.status.value}")
        print(f"  final_layer={result.final_layer}")
        print(f"  summary={result.summary}")
        print(f"  output={result.output}")
