"""Example: fallback reuses partial output from the primary path.

This example teaches the `context` pattern:

1. the primary path produces a partial useful result
2. a detector marks the overall result as not good enough
3. the fallback reuses the partial output instead of recomputing everything
"""

from __future__ import annotations

from secondpath import FallbackLayer, protect
from secondpath.detectors import EmptyResult
from secondpath.sinks import StdoutSink


def extract_and_generate_listing(product_url: str) -> dict:
    return {
        "title": "Wireless Noise-Canceling Headphones",
        "bullets": [],
        "description": "Immersive sound with all-day comfort.",
    }


def reuse_partial_listing(product_url: str, *, context=None) -> dict:
    del product_url
    primary_output = getattr(context, "primary_output", {}) or {}
    title = primary_output.get("title", "Featured Product")
    description = primary_output.get("description", "Explore product details and highlights.")

    return {
        "title": title,
        "bullets": [
            "High-quality sound",
            "Comfortable all-day fit",
            "Fast shipping available",
        ],
        "description": description,
    }


plan = protect(
    primary=extract_and_generate_listing,
    detect=[EmptyResult("bullets")],
    fallback_chain=[
        FallbackLayer.rule_based(
            "reuse_partial_listing",
            reuse_partial_listing,
            description="Reuse partial primary output and fill missing fields.",
        )
    ],
    sinks=[StdoutSink()],
    name="listing_generation",
)


if __name__ == "__main__":
    result = plan.run(product_url="https://shop.example/products/headphones")
    print(f"status={result.status.value}")
    print(f"final_layer={result.final_layer}")
    print(f"summary={result.summary}")
    print(f"output={result.output}")
