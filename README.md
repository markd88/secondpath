<p align="center">
  <img src=".github/assets/secondpath-banner.svg" alt="SecondPath banner" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/markd88/secondpath/actions/workflows/ci.yml">
    <img src="https://github.com/markd88/secondpath/actions/workflows/ci.yml/badge.svg" alt="CI" />
  </a>
  <img src="https://img.shields.io/github/v/release/markd88/secondpath" alt="release" />
  <img src="https://img.shields.io/badge/python-3.9%2B-3776AB" alt="python" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license" />
</p>

# SecondPath

> Separate AI optimization from product fallback.

SecondPath is a design principle for user-facing AI systems.

Most teams optimize the best AI path and leave fallback scattered across product
code. SecondPath argues these should be designed separately:

- AI path: optimize quality, latency, and cost
- Product path: guarantee delivery when the AI path fails, degrades, times out,
  or returns something unusable

Model success is not the same as product success. The best path should not be
the only path.

This repository contains a lightweight Python reference implementation of that
pattern:

`primary -> detect -> fallback_chain -> sinks`

## Why This Exists

Most teams optimize the AI path but leave fallback scattered across product
code. SecondPath makes fallback explicit, so delivery does not collapse when
the model path fails.

## Reference Implementation

Requirements:

- Python `>=3.9`

Install:

```bash
pip3 install -e .
```

After PyPI release:

```bash
pip install secondpath
```

Quick start:

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

## Reference Implementation Scope (v0.1-alpha)

In scope:
- sync runtime (`protect(...)`)
- sequential fallback chains
- core detectors/sinks
- examples (including sink-backed human-review queue pattern)
- focused runtime/configuration/sink tests

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
