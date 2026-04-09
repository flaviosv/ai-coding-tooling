---
name: unsupported-tech-stack-alert
description: Standardized alert to display when no matching tech-specific reference files are found for the detected stack.
type: template
---

If no matching reference file exists for the detected stack in either location, STOP immediately before proceeding with any coding task. Output the following alert and wait for the user's response:

---
🚨🔴 **UNSUPPORTED TECH STACK — ACTION REQUIRED** 🔴🚨

> ❌ No tech-specific reference files were found for the detected stack: **[detected stack]**
> Neither the parent skill's `reference/` directory nor this extension's `reference/` directory contains matching guidelines.
>
> **Choose how to proceed:**
> 1. 🛠️ **Add support** — run the `tech-reference-add` skill to generate guidelines for this stack, then retry.
> 2. ⚠️ **Proceed without stack-specific rules** — base behavioral guidelines only will apply. Tech-specific naming, idioms, and patterns will NOT be enforced.
>
> _Reply with **1** or **2** to continue._
---

Do not apply any coding guidelines or make any code changes until the user replies. If they choose option 2, proceed using only the parent skill's behavioral guidelines and note at the top of your response that no stack-specific rules are in effect.
