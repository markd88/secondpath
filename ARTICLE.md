# Your AI Model Worked. Your Product Still Failed.

*Why user-facing AI systems need an explicit fallback path*

---

It's Black Friday. Your e-commerce platform generates AI-powered ads for 50,000 merchants — headlines, images, the works. A merchant uploads a product page. Your model reads it, understands what they are selling, and writes a headline that converts. In staging, everything looks great: sharp copy, strong images, low latency. You ship it with confidence.

Then one merchant's product page times out. The crawler can't reach it — maybe the server is overloaded, maybe the DNS hiccupped. Either way, the model receives almost nothing: no product description, no specs, no context.

Here is the part that is easy to miss: the model still returns a result. It does not throw an exception. It does not log a warning. It just returns whatever it can with the input it got — in this case, an empty headline in a perfectly valid JSON payload.

No error. No alert. The user sees a blank ad slot.

High-traffic day. Real money on the line. An empty box where the creative should be.

The model did exactly what you asked it to do. It took input, processed it, and produced output. The product still failed.

**Model success is not the same as product success.**

Most teams spend their energy on the AI path and leave fallback scattered across product code. The result is a system that looks good in demos and frays in production.

---

## The code you probably have

Most AI products start with something like this:

```python
def generate_creative(product_page, locale):
    try:
        return model.generate(product_page, locale)
    except Exception:
        return None
```

This is not a fallback strategy. It is a `try/except` shaped hole.

Four things are missing:

**No detection.** The model can return `{"headline": ""}` without raising an exception. Your `except` block never runs, and the user still gets a blank.

**No ordering.** Once you add a second fallback, the sequence lives in ad hoc `if` statements spread across the codebase.

**No observability.** You cannot answer basic questions like: how often did the primary path fail, which layer recovered it, and what type of failure triggered the chain?

**No distinction between user-facing recovery and side effects.** Returning a safer reply to the user is one responsibility. Logging, queueing, or paging a human is another.

The fix is not more exception handling. The fix is to design the fallback path on purpose.

---

## The SecondPath pattern

```
┌──────────┐     ┌──────────┐     ┌──────────────────┐     ┌──────────┐
│ primary  │────▶│  detect  │────▶│  fallback_chain   │────▶│  sinks   │
│ (AI call)│     │ (check)  │     │ (degraded → rule  │     │ (log,    │
│          │     │          │     │  → human)         │     │  queue)  │
└──────────┘     └──────────┘     └──────────────────┘     └──────────┘
```

The best path should not be the only path. Here is how each stage works.

### Primary: what you already have

The primary is the AI call you are already running — a chat completion, an agent loop, a retrieval-augmented generator, any of it. SecondPath does not change the primary. It wraps it and handles what happens when the primary returns something that is not shippable.

### Detect: what counts as "failure"

The detect stage decides whether the primary result is good enough to ship. Timeouts are easy to notice. The harder failures are silent:

- an empty field in an otherwise valid payload
- structured output with the wrong shape
- an answer that passes parsing but does not meet a business threshold

Detection is a product decision, not a model decision. The question is not "did the model throw?" It is "is this output good enough to ship?" In the reference implementation, detectors are explicit and declarative:

```python
detect = [
    EmptyResult("headline"),
    InvalidStructuredOutput(),
    ExceptionType(TimeoutError, "timeout"),
]
```

If your product needs score thresholds, policy checks, or domain-specific validation, add a custom detector for that rule.

### Fallback chain: ordered degradation

If the detect stage flags the primary result as not shippable, the fallback chain takes over. Each layer is lower-fidelity than the one before, but still returns something the user can see. The chain stops at the first layer that produces a usable result. A chain can have two layers or ten — the structure is the same.

### Sinks: side effects, not user responses

Fallback layers return something to the user. Sinks do something else: log the incident, push it to a queue, send an alert, persist it for later review. This distinction matters. If you build human review as a fallback layer, the user waits for a human response. If you build it as a sink, the user gets an immediate degraded response and a human follows up later. The product decision is: what does the user see right now, and what happens in the background?

### The outcome is always traceable

Because each layer is named and ordered, every run produces a clear result: the primary path succeeded, a specific fallback layer handled it, or nothing worked. You always know which path was taken and why — no more silent fallbacks buried in `if` statements.

### Two paths, two owners

Once you lay out the architecture this way, something else becomes clear. You actually have two independent optimization paths:

- **AI path**: the primary. Optimize quality, latency, and cost.
- **Product path**: detect, fallback chain, sinks. Guarantee a usable outcome when the AI path is empty, malformed, late, or otherwise not shippable.

That separation also works at the team level. The model team owns the primary path: prompts, fine-tuning, latency budgets. The product team owns the fallback chain: which rule-based template ships when the model is empty, which canned reply is safe enough, what the escalation flow looks like. Right now both responsibilities live in the same `try/except` block. Splitting them explicitly means each team can iterate on their own path without stepping on the other.

The underlying idea is not new. Reliability engineering has always used degraded modes, backups, and escalation paths. The useful move in user-facing AI is to make those paths explicit in application code instead of leaving them buried in exception handlers and one-off patches.

---

## Three common patterns

The same structure shows up in different products. The logic is always the same: detect whether the primary result is usable, step down through fallback layers, and send incidents to sinks when needed.

### 1. Content generation

```
AI creates the full version
  -> detect: is the result usable?
  -> fallback 1: simpler version (text only, no image)
  -> fallback 2: basic default version (pre-written approved copy)
  -> fallback 3: human review
  -> sinks: log, queue, alert
```

This could be an ad, a product description, an image, a summary, or an email draft. The goal is not to preserve every feature of the original result. The goal is to keep delivering something usable.

### 2. Customer support

```
AI answers the user
  -> detect: is the reply safe and complete?
  -> fallback: safe canned reply
  -> sinks: log the incident, notify support team
```

Here, the human follow-up is not the fallback layer itself. The fallback is the safe reply the user gets immediately. The support notification is a sink. If you build human review as a fallback layer, the user waits 20 minutes for a response. If you build it as a sink, the user gets an immediate acknowledgment and a follow-up later.

### 3. Multi-step assistant

```
AI completes a task using several steps
  -> detect: is it making progress?
  -> fallback 1: simpler workflow
  -> fallback 2: basic answer without tools
  -> sinks: log the failure, alert operators
```

These systems often fail quietly. They may keep running without making progress, or produce output that looks valid but is not actually useful. That is why explicit detection matters: the model did not throw an exception, but the result is still not shippable.

---

## What this looks like in code

The pattern is the point. In the reference implementation, the core API looks like this:

```python
from secondpath import FallbackLayer, protect
from secondpath.detectors import EmptyResult, ExceptionType

plan = protect(
    primary=generate_creative,
    detect=[
        EmptyResult("headline"),
        ExceptionType(TimeoutError, "timeout"),
    ],
    fallback_chain=[
        FallbackLayer.degraded_ai("text_only", text_only),
        FallbackLayer.rule_based("country_template", country_template),
        FallbackLayer.human("human_review", human_review),
    ],
    name="website_creative",
)

result = plan.run(url="https://merchant.example", country="DE")
# result.status: success | degraded | escalated | failed
```

Each fallback layer is lower-fidelity than the primary path, but still returns something the user can see. The detection step is declarative: you decide what counts as "not shippable" and the chain handles the rest.

For the chatbot pattern, where human handling happens asynchronously behind a queue instead of as a fallback layer, add sinks:

```python
from secondpath.sinks import StdoutSink, MessageQueueSink

plan = protect(
    primary=generate_support_reply,
    detect=[EmptyResult("reply"), ExceptionType(TimeoutError, "timeout")],
    fallback_chain=[
        FallbackLayer.rule_based("canned_safe_reply", canned_safe_reply),
    ],
    sinks=[StdoutSink(), MessageQueueSink(publisher=publish, topic="support.review")],
)
```

The user gets an immediate safe reply. The incident is also pushed to a queue for human follow-up. Fallback layers and sinks are separate by design.

If you want the runnable examples, they are in the repository: [github.com/markd88/secondpath](https://github.com/markd88/secondpath)

---

## When this pattern applies

SecondPath is a good fit when:

- your system is user-facing and "no answer" is a bad product outcome
- a degraded response is still better than nothing
- different failure modes need different handling
- you want to observe how often the AI path degrades in practice

It is a poor fit when:

- the workflow is batch-only and nobody is waiting for an immediate answer
- there is no acceptable degraded output
- a workflow engine already owns retries, state, escalation, and recovery end to end

---

## Why this matters now

Fallback is not a temporary patch. It is part of the product. Models hallucinate, time out, return empty results, and produce output that passes parsing but fails business logic. That is not a bug you eliminate once. It is a property you design around. And even when the model works well, there is a ceiling: the best model output still needs rule-based templates for edge cases, canned replies for safety, and human review for judgment calls.

Yet most teams plan to remove fallback later. "We'll clean this up once the model gets better." In practice, the fallback chain is a permanent product path that needs its own development and iteration — just like the AI path. The safe reply that ships when the model times out is not a workaround. It is a product feature that your PM should own, test, and improve over time.

The practical implication: if you are not investing in your rule-based fallbacks the same way you invest in prompts and fine-tuning, you are not fully shipping your product. You are shipping the best case and hoping the rest works out.

You do not need a big platform to fix that. You need a declared second path:

- define what failure means for the product
- order the fallback chain explicitly
- separate synchronous fallback layers from asynchronous sinks

SecondPath is an open-source reference implementation of that idea: [github.com/markd88/secondpath](https://github.com/markd88/secondpath)

Even if you never use the library, the design question is still the right one:

**What should the user receive when the AI path is not shippable?**

If that answer lives in scattered `try/except` blocks, you do not have a product path yet.
