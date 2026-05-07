# SecondPath

> Every AI workflow needs a second path.

SecondPath is a lightweight runtime layer for user-facing AI workflows.

It helps you separate:
- AI/model optimization logic (best path)
- product fallback logic (delivery under failure)

In one line:

`primary -> detect -> fallback_chain -> sinks`

## Install

```bash
pip3 install -e .
```

After PyPI release:

```bash
pip install secondpath
```

## Quick Start

```python
from secondpath import FallbackLayer, protect
from secondpath.detectors import EmptyResult, ExceptionType
from secondpath.sinks import StdoutSink


def primary(url: str, country: str) -> dict:
    if "timeout" in url:
        raise TimeoutError("crawl timed out")
    return {"headline": "", "image": None}


def text_only(url: str, country: str) -> dict:
    return {"headline": "Discover offers tailored to your market", "image": None}


plan = protect(
    primary=primary,
    detect=[
        EmptyResult("headline"),
        ExceptionType(TimeoutError, "timeout"),
    ],
    fallback_chain=[
        FallbackLayer.degraded_ai("text_only", text_only),
    ],
    sinks=[StdoutSink()],
)

result = plan.run(url="https://merchant.example", country="DE")
print(result.status, result.final_layer)
```

Possible statuses:
- `success`
- `degraded`
- `escalated`
- `failed`

## Examples

- `examples/website_creative.py`
  - canonical fallback-chain example (`success` / `degraded` / `escalated`)
- `examples/support_chatbot_queue.py`
  - chatbot + queue-backed human follow-up (`MessageQueueSink`)
- `examples/reuse_primary_output.py`
  - fallback reuses partial primary output through `context`
- `examples/react_agent_fallback.py`
  - primary execution unit can be a ReAct-style agent loop

Run any example:

```bash
python3 examples/website_creative.py
```

## Core Concepts

- `protect(...)`: wrap one execution unit
- `primary`: preferred execution strategy (can be complex internally)
- `detect`: decide whether primary result is acceptable
- `fallback_chain`: ordered acceptable alternatives
- `sinks`: incident routing (stdout/webhook/slack/sqlite/mq)

Handler contract:
- `plan.run(*args, **kwargs)` inputs are forwarded to primary and fallback handlers
- handlers may optionally accept `context=` to read runtime info (`primary_output`, `primary_error`, `failure_type`, `artifacts`)

## Error Handling Policy

- Execution/runtime failures may degrade through fallback layers
- Configuration mistakes fail fast (`ConfigurationError`)
- Detector crashes fail fast (`DetectorError`)
- Sink errors are best effort and do not block main execution

## Scope (v0.1-alpha)

In scope:
- sync runtime (`protect(...)`)
- sequential fallback chains
- core detectors/sinks
- examples + focused tests

Not in scope:
- workflow engine / graph runtime
- async-first orchestration
- full observability platform
- deep framework integrations

## Development

```bash
pip3 install -e .
python3 -m pytest
```

See also:
- `CONTRIBUTING.md`
- `ROADMAP.md`

## License

MIT
