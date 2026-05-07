# Roadmap

## v0.1-alpha

Goal:

- prove the `second path` pattern for user-facing AI workflows

Includes:

- `protect(...)` ✅
- sequential `fallback_chain` ✅
- basic detectors ✅
- basic sinks ✅
- canonical website-to-creative example ✅
- focused runtime/configuration/sink tests ✅
- human-review queue example (`support_chatbot_queue.py`) ✅

## Next Likely Steps

1. Improve incident ergonomics
- richer summaries
- clearer sink failure reporting

2. Improve developer ergonomics
- clearer docs
- optional helper adapters for fallback handlers

3. Launch readiness
- package/release workflow for PyPI
- release notes + versioning policy
- benchmark-style example showing degraded-but-delivered outcomes

## Explicitly Deferred

- workflow graph runtime
- agent supervisor/event adapter layer
- async-first execution model
- hosted control plane or review UI
