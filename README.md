# SecondPath

> Every AI workflow needs a second path.

`secondpath` is a lightweight runtime layer for user-facing AI workflows.

It protects one execution unit with a fallback chain:

1. try the best AI path first
2. degrade to safer fallback layers when it fails or stops being trustworthy
3. emit an incident for review or human handling

At a higher level, SecondPath is about separating two concerns that usually get mixed together:

- optimize the model/application path for best-case quality
- protect the product path for acceptable delivery under failure

This is not a new workflow engine.

It is the layer that answers: what should my product do when the primary AI path does not hold?

## The Pattern

Most AI products already have this logic somewhere:

- skip the unstable step
- return a rule-based template
- send the case to a human

`secondpath` makes that path explicit.

```text
primary AI path
  -> degraded AI fallback
  -> rule-based fallback
  -> human escalation
```

You can think of it as multi-path execution for AI apps.

## Core Design Principle

SecondPath exists to keep two kinds of logic from collapsing into one:

- **model optimization logic**
  - prompts
  - model choice
  - extraction/generation quality
  - agent behavior inside the preferred path

- **product fallback logic**
  - safe templates
  - degraded responses
  - queue/human escalation
  - incident routing

In other words:

> let the AI path chase quality; let the second path guarantee delivery.

This is why SecondPath is designed as an outer protection layer instead of another workflow engine.

The canonical MVP story is:

- input: a merchant website URL
- primary path: crawl -> extract -> generate copy -> generate image
- fallback chain:
  - text-only AI fallback
  - country template fallback
  - human review escalation

## Quick Start

Current install options:

```bash
pip3 install -e .
```

After a PyPI release, the intended install path is:

```bash
pip install secondpath
```

```python
from secondpath import FallbackLayer, protect
from secondpath.detectors import EmptyResult, ExceptionType
from secondpath.sinks import StdoutSink


def generate_creative_from_url(url: str, country: str) -> dict:
    if "timeout" in url:
        raise TimeoutError("crawl timed out")
    return {"headline": "", "image": None}


def text_only_fallback(url: str, country: str) -> dict:
    return {"headline": "Discover offers tailored to your market", "image": None}


def human_review_fallback(url: str, country: str) -> dict:
    return {"status": "queued_for_review"}


plan = protect(
    primary=generate_creative_from_url,
    detect=[
        EmptyResult("headline"),
        ExceptionType(TimeoutError, "timeout"),
    ],
    fallback_chain=[
        FallbackLayer.degraded_ai("text_only", text_only_fallback),
        FallbackLayer.human("human_review", human_review_fallback),
    ],
    sinks=[StdoutSink()],
    name="creative_generation",
)

result = plan.run(url="https://merchant.example", country="DE")

print(result.status)
print(result.final_layer)
print(result.output)
```

Possible outcomes:

- `success`: primary path delivered
- `degraded`: a fallback layer delivered
- `escalated`: the chain reached a human layer
- `failed`: no layer completed successfully

Run the demo locally:

```bash
PYTHONPATH=src python3 examples/website_creative.py
```

It prints all three canonical outcomes:

- `success`
- `degraded`
- `escalated`

## Core Concepts

### `protect(...)`

Builds a `ProtectionPlan` around one AI execution unit.

That unit can be:

- website URL -> creative generation
- document -> extraction -> summary
- classify -> route -> template fallback

For v0.1-alpha, `primary` should be read as the preferred execution strategy, not necessarily a single model call.

That means `primary` can already contain internal orchestration such as:

- step 1, then step 2 if step 1 fails
- parallel sub-paths followed by a merge step

`secondpath` protects that outer execution unit.
It does not try to become the internal workflow engine for it.

### `fallback_chain`

An ordered chain of acceptable alternatives.

Typical chain:

1. best AI path
2. degraded AI path
3. rule-based fallback
4. human escalation

The key idea is not "retry until it works".

It is:

> lower quality in a controlled way so the product can still ship something acceptable.

This separation is intentional:

- the primary path focuses on model/application logic
- the fallback chain focuses on delivery and engineering logic

That keeps the best-path workflow clean, while making degradation explicit instead of scattering it across business code.

This also keeps the scope disciplined:

- internal branching inside `primary` is allowed
- `secondpath` handles the outer failure/degradation boundary
- non-linear orchestration is not a v0.1-alpha feature of `secondpath` itself

## Handler Contract

`plan.run(*args, **kwargs)` forwards the same inputs to:

- the `primary` handler
- each fallback handler in `fallback_chain`

So for v0.1-alpha, those handlers should accept a compatible call shape.

If a fallback needs a different signature, wrap it in a small adapter function.

Obvious handler-signature mismatches are treated as configuration errors, not runtime fallback failures.

Handlers may also opt into an extra keyword-only `context` argument.

That context gives access to runtime information such as:

- `primary_output`
- `primary_error`
- `failure_type`
- `artifacts`

This is the escape hatch for fallbacks that need to reuse partial results from the primary path.

## Defensive Behavior

`secondpath` tries to separate configuration mistakes from real workflow failures.

- invalid handler signatures fail fast as configuration errors
- invalid detector or sink interfaces fail fast during plan creation
- detector crashes are treated as detector errors, not normal workflow failures
- sink failures do not break the main execution path, but they are recorded in incident metadata

## Pipeline Error Policy

SecondPath does not treat every error the same way.

### These are normal execution failures and may trigger fallback

- primary runtime errors
- primary outputs that detectors mark as untrustworthy
- fallback layer runtime errors

### These fail the current execution fast

- configuration errors
- detector crashes
- obvious handler-signature mismatches
- SecondPath internal bugs

### These are best-effort side-path failures

- sink errors

Sink failures are recorded, but they do not block the main execution result.

### `Incident`

A structured record explaining:

- why the primary path failed
- which fallback layers were attempted
- what the final status was

This lets you route failed cases to:

- stdout/logging
- webhook receivers
- SQLite/Postgres
- Slack
- queue publishers via `MessageQueueSink`

## Why This Is Different

### Not a model gateway

Tools like Portkey help with provider/model failover.

`secondpath` sits one layer higher: it protects a user-facing execution, not just an API call.

### Not just output validation

Tools like Guardrails focus on validating or repairing a single model output.

`secondpath` answers a different question:

> if this execution is no longer worth continuing, what is the next acceptable path?

### Not a new orchestration framework

Frameworks like LangGraph and PydanticAI help you build and run AI systems.

`secondpath` is designed to wrap an existing workflow and give it a second path.

## Scope

This repo is intentionally narrow.

It is not:

- a new workflow engine
- an observability platform
- a model gateway
- an eval framework

It is:

- a protection layer for AI workflow execution
- a fallback-chain runner
- an incident emitter for human escalation paths

## v0.1-alpha Scope

The first public version is intentionally small.

### In scope

- `protect(...)` as the primary entry point
- `ProtectionPlan`, `FallbackLayer`, `ProtectionResult`, and `Incident`
- sequential `fallback_chain` execution
- simple built-in detectors:
  - `ExceptionType`
  - `EmptyResult`
  - `InvalidStructuredOutput`
- simple built-in sinks:
  - `StdoutSink`
  - `SqliteSink`
  - `WebhookSink` / `SlackSink`
- one strong canonical example:
  - website -> creative -> fallback chain
- minimal tests for the core runtime behavior

### Explicit non-goals for v0.1-alpha

- agent supervisor runtime
- async execution
- rich routing engine
- workflow builder / visual editor
- review inbox UI
- full observability platform
- provider gateway / model router
- deep framework integrations

### Product discipline

If a feature makes SecondPath look like a workflow engine, agent framework, or AI ops platform, it is probably out of scope for v0.1-alpha.

## Who This Is For

`secondpath` is most useful when all three are true:

1. the user sees the result directly
2. the primary AI path is better but not fully reliable
3. you already know some acceptable fallback exists

Typical examples:

- website -> ad copy / image generation
- document -> extraction -> structured result
- product input -> listing / catalog content
- internal AI workflow that must return something usable, not just error

The website-to-creative example is the reference MVP scenario for this repo.

Additional example patterns:

- `examples/support_chatbot_queue.py`
  - chatbot fallback to a canned safe reply
  - human follow-up modeled as a queue-backed sink
- `examples/reuse_primary_output.py`
  - fallback reuses partial primary output through `context`
  - teaches context-aware degradation instead of full recomputation
- `examples/react_agent_fallback.py`
  - the primary execution unit is a ReAct-style agent loop
  - teaches that `primary` can be any input/output execution unit
  - `secondpath` still only owns the outer fallback boundary

## Package Layout

```text
secondpath/
  src/secondpath/
    __init__.py
    plan.py
    protect.py
    types.py
    detectors/
    sinks/
  examples/
    react_agent_fallback.py
    reuse_primary_output.py
    support_chatbot_queue.py
    website_creative.py
```

## Development

Install locally:

```bash
pip3 install -e .
```

Run tests:

```bash
python3 -m pytest
```

Key docs:

- `CONTRIBUTING.md`
- `ROADMAP.md`

CI:

- GitHub Actions runs the test suite on supported Python versions

## Status

Early skeleton.

Current focus:

- sync `protect(...)`
- sequential fallback chains
- simple detectors
- simple sinks
- one sharp example
- one sharp open-source story

Current non-goals:

- full tracing platform
- visual review inbox
- multi-agent orchestration
- deep framework integrations in v0.1

Future extensions:

- async support
- richer detection objects
- non-linear routing
- agent supervisor adapters

## v0.1-alpha Publish Checklist

The repo is ready for a first public alpha when all of these are true:

- the project story is stable:
  - `Every AI workflow needs a second path.`
- the public API is stable enough for alpha:
  - `protect(primary, detect, fallback_chain, sinks, name=...)`
- the canonical demo works locally:
  - `examples/website_creative.py`
- the core runtime behavior is covered by focused tests
- editable install works:
  - `pip install -e .`
- the README explains:
  - what it is
  - what it is not
  - who it is for
  - how to run the demo

Current status:

- core API: done
- canonical demo: done
- focused tests: done
- editable install check: done
- naming: done (`SecondPath`)

That means this repo is in a reasonable `v0.1-alpha` state.

## License

MIT
