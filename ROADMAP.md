# Roadmap

## v0.1-alpha

Goal:

- prove the `second path` pattern for user-facing AI workflows

Includes:

- `protect(...)`
- sequential `fallback_chain`
- basic detectors
- basic sinks
- canonical website-to-creative example
- focused runtime/configuration/sink tests

## Next Likely Steps

1. Add one more example
- human review represented as a sink-backed queue instead of a fallback layer

2. Improve incident ergonomics
- richer summaries
- clearer sink failure reporting

3. Improve developer ergonomics
- clearer docs
- optional helper adapters for fallback handlers

## Explicitly Deferred

- workflow graph runtime
- agent supervisor/event adapter layer
- async-first execution model
- hosted control plane or review UI
