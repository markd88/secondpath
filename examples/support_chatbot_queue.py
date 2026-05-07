"""Chatbot example where human review is modeled as a sink-backed queue.

This example shows a different pattern from `website_creative.py`:

1. the workflow degrades to a safe canned response
2. the incident is also pushed to a queue for human follow-up

In this case, human handling is not the fallback layer itself.
It is the system behind the sink.
"""

from __future__ import annotations

from secondpath import FallbackLayer, protect
from secondpath.detectors import EmptyResult, ExceptionType
from secondpath.sinks import MessageQueueSink, StdoutSink


def generate_support_reply(message: str, customer_tier: str) -> dict:
    if "billing" in message.lower():
        raise TimeoutError("billing knowledge lookup timed out")
    if "refund" in message.lower():
        return {"reply": "", "handoff": False}
    return {
        "reply": f"Here is an AI-generated answer for {customer_tier} customer: {message}",
        "handoff": False,
    }


def canned_safe_reply(message: str, customer_tier: str, *, context=None) -> dict:
    del message, customer_tier
    return {
        "reply": "Thanks for reaching out. Our team is reviewing your request and will follow up shortly.",
        "handoff": True,
        "failure_type": getattr(context, "failure_type", None),
    }


def publish_to_memory_queue(payload: dict) -> None:
    print("[mq.publish]", payload)


plan = protect(
    primary=generate_support_reply,
    detect=[
        EmptyResult("reply"),
        ExceptionType(TimeoutError, "timeout"),
    ],
    fallback_chain=[
        FallbackLayer.rule_based(
            "canned_safe_reply",
            canned_safe_reply,
            description="Return a safe canned response to the user.",
        )
    ],
    sinks=[
        StdoutSink(),
        MessageQueueSink(publisher=publish_to_memory_queue, topic="support.review"),
    ],
    name="support_chatbot",
)


if __name__ == "__main__":
    scenarios = [
        ("success", "Where can I find your pricing page?"),
        ("degraded+queued", "I need a refund on my order"),
        ("timeout+queued", "Billing issue with my invoice"),
    ]

    for label, message in scenarios:
        result = plan.run(message=message, customer_tier="enterprise")
        print(f"[{label}] {message}")
        print(f"  status={result.status.value}")
        print(f"  final_layer={result.final_layer}")
        print(f"  summary={result.summary}")
        print(f"  output={result.output}")
