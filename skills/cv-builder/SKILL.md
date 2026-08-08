---
name: cv-builder
description: Build a professional CV/resume from scratch, keep one updated, or tailor an existing CV to a specific job posting (writes a job-specific variant, never touches the base cv.md/cv.yaml), targeting a 2-page PDF (3 pages max). Runs a deep grilling interview that extracts a person's full experience catalog into a resumable experiences.md, then curates it into a recruiter-grade cv.md and a RenderCV cv.yaml rendered to PDF, and — by default — a paste-ready linkedin.md, all sourced from the same experiences.md catalog. Acts as a recruiter and coach; every claim is kept interview-defensible. Requires the grilling skill and RenderCV (via uvx). Use when someone says "build my CV", "create my resume", "update my CV", "improve my resume", "update my LinkedIn", "tailor my CV for this job", "match my resume to this job description", "customize my CV for [company]", or wants a RenderCV/PDF CV. Do NOT use for cover letters or job-application tracking.
license: CC-BY-4.0
metadata:
  author: Flavio Studart
  version: "1.2.0"
---

# CV Builder

Guide a person from a blank page (or an existing CV) to a recruiter-grade, interview-defensible CV — by first extracting their **full experience catalog** into a permanent, resumable `experiences.md`, then curating that catalog into a polished `cv.md`, a rendered `cv.yaml` PDF (2 pages target, 3 max), and — by default — a paste-ready `linkedin.md`.

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
| `cv/linkedin.md` | The LinkedIn-ready profile text — Headline, About (Summary + Skills), Experience. Plain text only (`-` bullets allowed, no other markdown), within LinkedIn's field character limits. |
| `cv/job-specific/<date>_<role>_<company>.md` | The tailoring dossier for one job application — JD summary, keyword match/gap table, positioning decision, grilling Q&A log. Never the CV itself. |
| `cv/job-specific/<date>_<role>_<company>/` | That application's tailored `cv.md` + `cv.yaml` + `rendercv_output/` — a self-contained variant, one subfolder per job so renders never collide. |

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
- **Present → Keep updated.** Resume from the tracker and decisions log; apply the user's requested changes to `experiences.md` first, then propagate to the target file(s).
- **Request references a job description/posting → Job-Tailoring Mode.** Requires `cv/experiences.md` **and** `cv/cv.md` to already exist — this mode riffs on an already-curated CV, it does not build one. If either is missing, say so and offer to run the normal build flow (Phases 1–5) first.

## Scope (target)

Default: build/update **both** `cv.md`/`cv.yaml` and `linkedin.md`. If the person scopes the request ("just update my CV", "just refresh LinkedIn"), build/update only that target. Record the active scope in the `Target` field of `experiences.md`'s Session State so a resumed session continues with the same scope.

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

### Phase 4 — Build cv.md (skip if scope is linkedin-only)

1. **Positioning first** — decide the target (role, level, focus, what to de-emphasize). Everything downstream flows from this, including `linkedin.md` if in scope. Also set the **page target** now: default **2 pages, 3 pages max**, unless the person requests otherwise — curate with this budget in mind from the start rather than drafting as if space is unlimited.
2. **Draft the top third first** (header + positioning line + summary + Stack & Skills), get reaction, then build the experience section tiered (full / condensed / earlier) by recency + relevance.
3. Apply every rule in `references/cv-best-practices.md` — impact formula, expertise-only skills (undefendable/used-not-expert tech → JD-mention only, never the skills list), no "firsts", client anonymization, naming currency, defensible metrics only.
4. **Recruiter review pass** before finalizing.
5. Write to `cv/cv.md` following `assets/cv-template.md`. Run `scripts/validate_cv.py cv/cv.md` and fix anything it flags.

### Phase 5 — Render cv.yaml (skip if scope is linkedin-only)

1. **Verify the current RenderCV schema before writing YAML** — query Context7 (`/rendercv/rendercv`), or fall back to web/`references/rendercv-schema.md`. RenderCV's schema versions; never assume it from memory.
2. Author `cv/cv.yaml` from the finalized `cv.md` (headline = positioning line; each experience's descriptor → the entry `summary`; skills → `OneLineEntry` label/details). Default `design:` = `theme: engineeringresumes` with `0.5in` page margins; change only if the person asks or to hit a page target.
3. Render with `scripts/render.py cv/cv.yaml`. Inspect the PNGs in `cv/rendercv_output/`.
4. **Tune layout to the page target** by editing the `design:` block (margins, `entries.allow_page_break`, spacing) and re-rendering — the agent owns this loop; do not script it. Run `validate_cv.py` again to confirm `cv.md` and `cv.yaml` still match.
5. **Page ceiling:** 2 pages is the target, 3 is the hard-ish ceiling. If design tuning is exhausted and it still exceeds 3 pages, do not finalize silently — flag it clearly, list which weakest bullets/sections you'd cut, and get the person's explicit call before accepting 4+ pages.

### Phase 6 — Build linkedin.md (skip if scope is cv-only)

1. Reuse the positioning decided in Phase 4. If scope is linkedin-only and no `cv.md` exists yet, decide positioning here first using the same "Positioning first" rule.
2. Both sections source from `cv/experiences.md`, not from the compressed `cv.md` bullets — there is no page limit here, so pull in richer detail and secondary wins that didn't survive the CV's budget. Stay curated: more room is not license to dump the raw catalog.
3. **About** = Summary (can run fuller than the CV's tight formula, but still fact-based) + Skills (same expertise-only, categorized list as the CV). Combined ≤2,600 characters.
4. **Headline** = the positioning line, ≤220 characters.
5. **Experience** = each relevant role gets a short context paragraph (mandate/scope) plus impact bullets — more freedom than the CV's 3-5 bullet cap, but stay skimmable, not verbose. Each entry's description ≤2,000 characters.
6. Write to `cv/linkedin.md` following `assets/linkedin-template.md`. **Plain text only** — no `#`, `**`, `__`, links, tables, or `---` rules; `-` bullets are the only markdown-like syntax LinkedIn will render usefully.
7. Run `scripts/validate_cv.py cv/linkedin.md` (auto-detected by filename) and fix anything it flags — disallowed markdown or a field over LinkedIn's character limit.

## Job-Tailoring Mode

A separate, self-contained mode — not a phase of the build/update workflow above. It never runs as a continuation of Phase 6; **Mode detection** routes into it directly, and only when `cv/experiences.md` and `cv/cv.md` already exist from a prior build. It produces a **job-specific variant** and never edits the base `cv.md`/`cv.yaml`/`linkedin.md` — treat them as read-only sources throughout.

1. **Ingest the JD.** Accept pasted text, a local file path, or a URL (fetch it). Save the JD text (or link) into the dossier as you go.
2. **Load context read-only:** the full `cv/experiences.md` catalog and the current `cv/cv.md`. The catalog is the real source — it holds material that didn't survive the base CV's page budget but may still fit this JD better.
3. **Match/gap analysis.** Extract the JD's required skills, responsibilities, and seniority signals. For each, mark: already on `cv.md` / in the catalog but cut from `cv.md` / not in the catalog at all (a real gap). Do not keyword-stuff — every match still needs bullet-level context per `references/cv-best-practices.md`.
4. **Grill only the ambiguous calls** — through the grilling skill, one question at a time, using `references/question-bank.md` § F. Skip anything the match/gap analysis already resolves confidently.
5. **Decide job-specific positioning** — may differ from the base CV's positioning line/summary. Still governed by every rule in `references/cv-best-practices.md`: expertise-only skills, no "firsts", defensible metrics, attribution honesty. A JD requirement with **zero** support in `experiences.md` is a gap — flag it in the dossier, never invent it.
6. **Re-tier bullets from the catalog**, not from `cv.md`'s already-compressed set — pull in higher-relevance bullets for this JD even if they lost out in the base CV's positioning.
7. Write the dossier to `cv/job-specific/<date>_<role-slug>_<company-slug>.md` following `assets/job-tailoring-template.md` (JD summary/link, match/gap table, positioning decision, grilling Q&A log, what changed vs. base `cv.md`).
8. Author `cv/job-specific/<date>_<role-slug>_<company-slug>/cv.md` (same structure as `assets/cv-template.md`) and, verifying the current RenderCV schema first (Context7 `/rendercv/rendercv`, else `references/rendercv-schema.md`), `cv.yaml`.
9. Render with `scripts/render.py cv/job-specific/<date>_<role-slug>_<company-slug>/cv.yaml`. **Each job gets its own subfolder** — `render.py` always writes to `rendercv_output/` next to its input yaml, so flat files across jobs would overwrite each other's PDFs.
10. Tune to the same page target used in the build workflow (2 default, 3 hard-ish ceiling), then run `scripts/validate_cv.py cv/job-specific/<date>_<role-slug>_<company-slug>/cv.md` and fix anything flagged.

## Guardrails

### Scope
- Only create or modify files under `cv/`. Never write CV artifacts elsewhere.
- Never fabricate content, metrics, employers, or dates. If it did not come from the person, it does not go in.
- Job-Tailoring Mode never modifies `cv/cv.md`, `cv/cv.yaml`, or `cv/linkedin.md` — it only reads them and writes under `cv/job-specific/`.

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
- `cv.md` still exceeds the 3-page ceiling after design tuning is exhausted → stop, propose specific cuts, and get explicit confirmation before accepting it.
- Job-Tailoring Mode is requested but `cv/experiences.md` or `cv/cv.md` is missing → stop and offer the normal build flow first; there is nothing to tailor.
- A JD requirement has no support anywhere in `experiences.md` → flag it as a gap in the dossier; ask whether the person has relevant undocumented experience before treating it as absent.

### Output validation
- `cv.md` must pass `scripts/validate_cv.py` (required sections present and ordered, entries complete, no placeholder text, `cv.md`↔`cv.yaml` consistency).
- `linkedin.md` must pass `scripts/validate_cv.py` in LinkedIn mode (no disallowed markdown beyond `-` bullets; Headline/About/each Experience entry within LinkedIn's character limits).
- RenderCV validates the YAML schema on render — treat a render error as a blocker, fix and re-render.

### Privacy
- CV data is personal. Do not distribute it. Anonymize third-party/agency clients to their market or industry per the best-practices rules.

## Examples

### Build from scratch, no seed
User: "Help me build my CV from scratch."
1. Create `cv/`, scaffold `experiences.md`. 2. Grill role by role through the Question Bank, writing the catalog as you go. 3. Review sweeps. 4. Decide positioning + page target, curate `cv.md`. 5. Author + render `cv.yaml`. 6. Build `linkedin.md` from the same catalog (default scope: both).
Result: `cv/rendercv_output/…_CV.pdf` (≤3 pages), `cv/linkedin.md`, plus a deep, reusable `experiences.md`.

### Keep an existing CV updated
User: "I changed jobs — update my CV."
1. Detect existing `cv/experiences.md`, resume from it. 2. Grill only the new role into the catalog. 3. Propagate to `cv.md` (re-tier if needed) and `linkedin.md`, re-run the recruiter pass. 4. Re-author the affected `cv.yaml` entries, re-render. 5. Update the Experience section of `linkedin.md`.
Result: updated PDF and `linkedin.md`, catalog and decisions log intact.

### LinkedIn only
User: "Just refresh my LinkedIn About section, don't touch the CV."
1. Detect existing `cv/experiences.md`, resume from it. 2. Set scope = linkedin in Session State. 3. Rebuild the About section (Summary + Skills, ≤2,600 chars) from the catalog, leaving `cv.md`/`cv.yaml` untouched. 4. Validate with `scripts/validate_cv.py cv/linkedin.md`.
Result: updated `cv/linkedin.md` only.

### Seed from an existing resume
User: "Here's my old resume — make it better." (attaches file)
1. Ingest the file into the tracker. 2. Grill to deepen thin roles and surface missing metrics/wins. 3. Reposition + curate. 4. Render `cv.yaml`. 5. Build `linkedin.md`.
Result: a stronger, defensible CV and LinkedIn profile built on the extracted catalog.

### Tailor for a specific job
User: "Tailor my CV for this job posting at Acme." (pastes JD)
1. Detect `cv/experiences.md` and `cv/cv.md` both exist → Job-Tailoring Mode. 2. Match/gap the JD against the full catalog, not just `cv.md`. 3. Grill the ambiguous mappings only. 4. Decide job-specific positioning, re-tier bullets from the catalog. 5. Write the dossier + tailored `cv.md`/`cv.yaml` under `cv/job-specific/2026-07-20_senior-backend-engineer_acme/`, render, validate.
Result: a job-specific PDF variant and its dossier, base `cv.md`/`cv.yaml` untouched.

## Troubleshooting

### RenderCV error: "install with rendercv[full]"
`render.py` already runs `uvx --from "rendercv[full]"`. If a local `rendercv` is installed without extras, reinstall with `rendercv[full]` or let `render.py` use the uvx path.

### CV renders to too many pages
Tune the `design:` block: reduce page margins, enable `entries.allow_page_break` to fill mid-page gaps, tighten spacing — then trim content (drop weakest bullets, condense older roles) only after design tuning is exhausted. Past 3 pages, stop and get explicit confirmation before finalizing (see the page ceiling rule in Phase 5).

### validate_cv.py reports drift between cv.md and cv.yaml
The two got out of sync. Reconcile toward the finalized `cv.md`, re-author the affected `cv.yaml` entries, re-run the validator.

### validate_cv.py flags linkedin.md for disallowed markdown
LinkedIn renders `#`, `**`, `__`, links, tables, and `---` rules as literal characters. Rewrite the flagged line in plain text; `-` bullets are the only allowed markdown-like syntax.

### validate_cv.py flags a linkedin.md field over the character limit
Headline (220), About (2,600, Summary + Skills combined), or an Experience entry (2,000) is too long. Trim to the strongest content first — do not silently truncate; if cutting loses something important, ask the person which to keep.

### Job-tailoring surfaces a JD requirement with no catalog support
Do not fabricate it. Flag it in the dossier's match/gap table, ask the person if it's undocumented experience worth grilling into `experiences.md`, or leave it as an honest gap — a CV that overclaims does not survive an interview.
