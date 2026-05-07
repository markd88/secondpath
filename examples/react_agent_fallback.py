"""Example: the primary execution unit can be an agent loop.

This example demonstrates a key boundary in SecondPath:

- the `primary` execution unit can be anything with inputs and outputs
- internally it can be a ReAct-style loop, custom orchestration, or other logic
- SecondPath still only focuses on the outer fallback boundary
"""

from __future__ import annotations

from secondpath import FallbackLayer, protect
from secondpath.detectors import EmptyResult, ExceptionType
from secondpath.sinks import StdoutSink


def run_react_agent(task: str) -> dict:
    """A tiny fake ReAct-style agent loop.

    This is intentionally simple and dependency-free. The point is to show
    that SecondPath wraps the whole execution unit, not just one model call.
    """

    scratchpad = []

    scratchpad.append("Thought: I should search docs first.")
    scratchpad.append("Action: search_docs('refund policy')")

    if "loop" in task.lower():
        raise RuntimeError("agent got stuck retrying the same tool")

    if "unclear" in task.lower():
        return {
            "answer": "",
            "trace": scratchpad,
        }

    scratchpad.append("Observation: Found support article.")
    scratchpad.append("Thought: I can now answer the user.")

    return {
        "answer": f"AI agent answer for task: {task}",
        "trace": scratchpad,
    }


def safe_rule_based_reply(task: str, *, context=None) -> dict:
    return {
        "answer": "Thanks for your question. Our support team is reviewing it and will follow up shortly.",
        "trace": getattr(context, "primary_output", None),
        "fallback_reason": getattr(context, "failure_type", None),
        "task": task,
    }


plan = protect(
    primary=run_react_agent,
    detect=[
        EmptyResult("answer"),
        ExceptionType(RuntimeError, "agent_runtime_error"),
    ],
    fallback_chain=[
        FallbackLayer.rule_based(
            "safe_rule_based_reply",
            safe_rule_based_reply,
            description="Return a safe non-agent response when the agent is not trustworthy.",
        )
    ],
    sinks=[StdoutSink()],
    name="react_agent_wrapper",
)


if __name__ == "__main__":
    scenarios = [
        ("success", "How do I reset my password?"),
        ("degraded-empty", "This request is unclear"),
        ("degraded-loop", "Please loop forever on refund policy"),
    ]

    for label, task in scenarios:
        result = plan.run(task=task)
        print(f"[{label}] {task}")
        print(f"  status={result.status.value}")
        print(f"  final_layer={result.final_layer}")
        print(f"  summary={result.summary}")
        print(f"  output={result.output}")
