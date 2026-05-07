# Contributing

Thanks for taking a look at `secondpath`.

## Project Shape

`secondpath` is intentionally narrow.

It is a runtime protection layer for existing AI workflows.

It is not:

- a workflow engine
- an agent framework
- an AI gateway
- a full observability platform

When contributing, prefer changes that keep the project sharp and small.

## Development Setup

```bash
pip3 install -e .
python3 -m pytest
```

Run the canonical demo:

```bash
python3 examples/website_creative.py
```

## Contribution Guidelines

Please optimize for:

1. small, composable changes
2. clear runtime behavior
3. preserving the `protect(...)` mental model
4. keeping configuration errors separate from workflow failures

## MVP Boundaries

Changes that are usually welcome:

- improving `protect(...)`
- better fallback-chain ergonomics
- better incident/sink behavior
- more realistic examples
- tests and docs improvements

Changes that should be discussed before implementation:

- async runtime support
- agent supervisor/runtime adapters
- non-linear routing engine
- workflow graph abstractions
- UI/review inbox features

## Before Opening a PR

Please make sure:

- tests pass locally
- examples still run
- the README still matches actual behavior
- the change does not turn `secondpath` into a framework
