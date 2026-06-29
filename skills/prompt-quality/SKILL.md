---
name: prompt-quality
description: >
  Checks whether a task prompt follows the anatomy-of-a-prompt guidelines (8 layers: Task, Context Files, Reference, Success Brief, Rules, Conversation, Plan, Alignment). Auto-invoked before responding to any new task. Outputs a quality report — confirmed or missing layers — then proceeds without blocking. Never invoke for follow-ups, continuations, or responses to clarifying questions.
---

# Prompt Quality

Analyze the incoming prompt against the anatomy-of-a-prompt guidelines and output a quality report as the very first content of your response.

## When to run

Run on every message that introduces a new task. Skip for:
- Short follow-ups ("yes", "do it", "go ahead", "ok", "sure", "looks good")
- Continuations that reference prior context without introducing a new goal
- Responses to clarifying questions you asked

## Step 1 — Classify the task

**Simple:** single-step action, quick question, rename, small bug fix, research lookup
**Complex:** multi-step implementation, feature creation, architecture decision, skill creation, multi-file refactor, full design task

Complexity signals: "implement", "build", "create", "design", "refactor across", "skill", "feature", "architecture", multi-file scope, multi-step scope.

## Step 2 — Check required layers

Simple tasks require layers 1, 3, 4, 5. Complex tasks require all 8.

| Layer | Name | Present when |
|-------|------|-------------|
| 1 | Task | States what to do AND why / what success looks like — "so that…", "in order to", "the goal is", or an explicit success criterion alongside the task |
| 2 | Context Files | Lists specific files to read first, each with a description — file paths, `[[filename]]` links, or backtick references with explanations |
| 3 | Reference | Provides an example of good output AND extracted rules — pasted content or "here is an example" followed by Always/Never patterns |
| 4 | Success Brief | Covers all four: output type/length, recipient reaction, what to avoid, and success definition ("success means…") |
| 5 | Rules | States explicit constraints OR asks Claude to flag violations before proceeding — "never", "always", "stop and tell me if", "my standards" |
| 6 | Conversation | Explicitly defers execution — "DO NOT start", "don't execute yet", "ask me questions first", "clarify before starting" |
| 7 | Plan | Asks Claude to prove understanding before producing output — "list the rules that matter", "which constraints apply", "before you write, list…" |
| 8 | Alignment | Requests an execution plan and alignment — "execution plan", "5 steps maximum", "only begin once we've aligned" |

## Step 3 — Output

Place this block as the very first output, before any other content:

All required layers present:
```
---
Prompt quality: All layers present
---
```

One or more required layers missing:
```
---
Prompt quality: Missing Layer X (Name), Layer Y (Name)
---
```

Then respond normally. Never block or delay execution based on this check.
