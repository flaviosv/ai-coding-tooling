---
name: cv-builder
description: Build a professional CV/resume from scratch or keep one updated. Runs a deep grilling interview that extracts a person's full experience catalog into a resumable experiences.md, then curates it into a recruiter-grade cv.md and a RenderCV cv.yaml rendered to PDF. Acts as a recruiter and coach; every claim is kept interview-defensible. Requires the grilling skill for the interview and RenderCV (via uvx) for rendering. Use when someone says "build my CV", "create my resume", "update my CV", "improve my resume", "CV from scratch", "work on my experience catalog", or wants a RenderCV/PDF CV. Do NOT use for cover letters, LinkedIn profile writing, or job-application tracking.
license: CC-BY-4.0
metadata:
  author: Flavio Studart
  version: 1.0.0
---

# CV Builder

Guide a person from a blank page (or an existing CV) to a recruiter-grade, interview-defensible CV — by first extracting their **full experience catalog** into a permanent, resumable `experiences.md`, then curating that catalog into a polished `cv.md` and a rendered `cv.yaml` PDF.

Act as a **recruiter, coach, and critical thinking partner** throughout: push for specifics, challenge weak or undefendable claims, and never let a bullet or skill onto the CV that the person could not defend in an interview.

## Core idea

The catalog is not the CV. `experiences.md` should hold **far more** than any single CV shows — every role, project, metric, and story the person can recall. The CV is a **curated distillation** of that catalog, targeted at a positioning. Extract exhaustively first; curate second.

## Working folder

All artifacts live under a `cv/` folder (create it on first run if missing). Never write CV artifacts outside it.

| File | Role |
|------|------|
| `cv/experiences.md` | The experience catalog **and full session memory** — `## Session State`, progress tracker, question bank, decisions log. The stop/resume hub for the whole workflow. |
| `cv/LEARNINGS.md` | Skill-improvement memory — records anything done differently from these instructions and any beneficial improvisation. Read at start, appended during the run. |
| `cv/cv.md` | The canonical, human-readable CV (recruiter review happens here). |
| `cv/cv.yaml` | The RenderCV input, authored from `cv.md`. |
| `cv/rendercv_output/` | Rendered PDF, PNGs, HTML, Markdown, Typst. |

## Dependencies

- **grilling skill** — the entire extraction and review runs one question at a time through it. If it is unavailable, tell the user and proceed with the same one-question-at-a-time discipline manually.
- **RenderCV** — used to render `cv.yaml`. Run `scripts/render.py` (uses an installed `rendercv`, else runs it ephemerally via `uvx --from "rendercv[full]"`).
- **Bundled guideline** — `references/cv-best-practices.md` is the sole CV-writing authority. Do not ask the user for an external knowledge base; load this file whenever writing or reviewing CV content.

## Memory

Two files under `cv/` make builds resumable and the skill self-improving. Read **both** at the start of every session or fresh context, before other work.

**Continuity — `cv/experiences.md`.** The single source of session state across all phases. Its top holds a `## Session State` block: current phase, positioning, page target, render/layout state, and the **next action**. On every session start or fresh context window, read the file fully to restore state and continue from the next action. After every meaningful step (answer captured, decision made, section written, layout tuned), update the Session State block, progress tracker, decisions log, and `Resume from:` markers. This is what survives weeks-later resumption and mid-session compaction.

**Learning — `cv/LEARNINGS.md`.** The skill-improvement log. Read it at Phase 1 and apply anything relevant. Append whenever the run **deviates from these instructions** or improvises beneficially — record: what the instructions said, what was done instead, and why it helped. Record only the reusable insight (a RenderCV quirk, a better question, a rule refinement, a validation gap), never a person's CV content. These entries are the raw material for improving this skill's instructions later.

## Mode detection

Check for `cv/experiences.md`:
- **Missing → Build from scratch.** Nothing is required. If the user offers a seed context (an existing CV `.md`/`.pdf`/`.yaml`, a LinkedIn profile or skills export, screenshots, or free-form notes), ingest it to pre-fill the tracker, then grill to fill gaps. With no seed, grill from zero.
- **Present → Keep updated.** Resume from the tracker and decisions log; apply the user's requested changes to `experiences.md` first, then propagate to `cv.md` and `cv.yaml`.

## Workflow

Move through the phases in order. Announce which phase you are in. The person can stop after any phase and resume later — `experiences.md` is the memory.

### Phase 1 — Setup

1. Create `cv/`; scaffold `cv/experiences.md` (from `assets/experiences-template.md`) and `cv/LEARNINGS.md` (from `assets/learnings-template.md`) if missing.
2. Read `cv/experiences.md` (restore the Session State) and `cv/LEARNINGS.md` (apply prior learnings). Load `references/cv-best-practices.md` and `references/question-bank.md`.
3. If a seed context was provided, extract everything you can into the catalog before grilling — then grill only the gaps.

### Phase 2 — Extraction (grilling)

Run the interview through the grilling skill, **one question at a time**, working roles oldest → newest (or newest-first if the person prefers). Use `references/question-bank.md` (Framing → Work/STAR → Scope → Deep tech-stack → Impact).

- **Extract as much as possible.** Depth over speed. Probe the tech stack hard — it is a first-class CV asset.
- **Honesty guards (non-negotiable):** record ownership precisely (built / co-built / contributed / team's); never invent metrics; mark estimates with `~` and log them under **To verify**; when a claimed skill or number looks undefendable, flag it and confirm before it survives.
- Write each answer straight into `cv/experiences.md` (STAR blocks, stack, scope, draft bullets). Update the progress tracker and the `Resume from:` marker after every answer so the session is always resumable.

### Phase 3 — Review

Once the target roles are mined, read the whole `experiences.md` end to end and, one item at a time:
- Fix inconsistencies and stale status markers.
- Pressure-test inflated or round-number claims.
- Run a **forgotten-wins sweep** (awards, promotions, extra projects, crises handled) and a **scale-number sweep** (users, throughput, revenue) — the person's memory is the bottleneck; prompt it hard.
- Record every resolution in the **Decisions log** so nothing gets re-litigated.

### Phase 4 — Build cv.md

1. **Positioning first** — decide the target (role, level, focus, what to de-emphasize). Everything downstream flows from this.
2. **Draft the top third first** (header + positioning line + summary + Stack & Skills), get reaction, then build the experience section tiered (full / condensed / earlier) by recency + relevance.
3. Apply every rule in `references/cv-best-practices.md` — impact formula, expertise-only skills (undefendable/used-not-expert tech → JD-mention only, never the skills list), no "firsts", client anonymization, naming currency, defensible metrics only.
4. **LinkedIn cross-check** (align listed skills with the person's LinkedIn) and a **recruiter review pass** before finalizing.
5. Write to `cv/cv.md` following `assets/cv-template.md`. Run `scripts/validate_cv.py cv/cv.md` and fix anything it flags.

### Phase 5 — Render cv.yaml

1. **Verify the current RenderCV schema before writing YAML** — query Context7 (`/rendercv/rendercv`), or fall back to web/`references/rendercv-schema.md`. RenderCV's schema versions; never assume it from memory.
2. Author `cv/cv.yaml` from the finalized `cv.md` (headline = positioning line; each experience's descriptor → the entry `summary`; skills → `OneLineEntry` label/details). Default `design:` = `theme: engineeringresumes` with `0.5in` page margins; change only if the person asks or to hit a page target.
3. Render with `scripts/render.py cv/cv.yaml`. Inspect the PNGs in `cv/rendercv_output/`.
4. **Tune layout to the page target** by editing the `design:` block (margins, `entries.allow_page_break`, spacing) and re-rendering — the agent owns this loop; do not script it. Run `validate_cv.py` again to confirm `cv.md` and `cv.yaml` still match.

## Guardrails

### Scope
- Only create or modify files under `cv/`. Never write CV artifacts elsewhere.
- Never fabricate content, metrics, employers, or dates. If it did not come from the person, it does not go in.

### Before starting
- Confirm the grilling skill is available; if not, keep the one-question-at-a-time discipline manually.
- Detect mode from `cv/experiences.md` presence before doing anything else.

### On collision
- `experiences.md` exists → **resume and merge**; never overwrite the catalog.
- `cv.md` / `cv.yaml` exist → **update in place**, preserving prior decisions from the log.

### When to stop and ask
- A metric or claim cannot be verified → ask; do not invent or round up.
- A skill would not survive an interview deep-dive → flag it and let the person decide (keep / cut / JD-mention).
- The target positioning is unclear → resolve it before writing any CV content.

### Output validation
- `cv.md` must pass `scripts/validate_cv.py` (required sections present and ordered, entries complete, no placeholder text, `cv.md`↔`cv.yaml` consistency).
- RenderCV validates the YAML schema on render — treat a render error as a blocker, fix and re-render.

### Privacy
- CV data is personal. Do not distribute it. Anonymize third-party/agency clients to their market or industry per the best-practices rules.

## Examples

### Build from scratch, no seed
User: "Help me build my CV from scratch."
1. Create `cv/`, scaffold `experiences.md`. 2. Grill role by role through the Question Bank, writing the catalog as you go. 3. Review sweeps. 4. Decide positioning, curate `cv.md`. 5. Author + render `cv.yaml`.
Result: `cv/rendercv_output/…_CV.pdf` plus a deep, reusable `experiences.md`.

### Keep an existing CV updated
User: "I changed jobs — update my CV."
1. Detect existing `cv/experiences.md`, resume from it. 2. Grill only the new role into the catalog. 3. Propagate to `cv.md` (re-tier if needed), re-run LinkedIn cross-check + recruiter pass. 4. Re-author the affected `cv.yaml` entries, re-render.
Result: updated PDF, catalog and decisions log intact.

### Seed from an existing resume
User: "Here's my old resume — make it better." (attaches file)
1. Ingest the file into the tracker. 2. Grill to deepen thin roles and surface missing metrics/wins. 3. Reposition + curate. 4. Render.
Result: a stronger, defensible CV built on the extracted catalog.

## Troubleshooting

### RenderCV error: "install with rendercv[full]"
`render.py` already runs `uvx --from "rendercv[full]"`. If a local `rendercv` is installed without extras, reinstall with `rendercv[full]` or let `render.py` use the uvx path.

### CV renders to too many pages
Tune the `design:` block: reduce page margins, enable `entries.allow_page_break` to fill mid-page gaps, tighten spacing — then trim content (drop weakest bullets, condense older roles) only after design tuning is exhausted.

### validate_cv.py reports drift between cv.md and cv.yaml
The two got out of sync. Reconcile toward the finalized `cv.md`, re-author the affected `cv.yaml` entries, re-run the validator.
