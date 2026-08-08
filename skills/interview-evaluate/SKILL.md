---
name: interview-evaluate
description: Evaluate a completed job-interview transcript against your CV, scoring each answer's relevance, accuracy, depth calibration, STAR structure (behavioral questions), CV alignment, and technical rigor (technical questions), then writes a dated Markdown report to interviews/. Requires a cv.* file (.md, .pdf, .docx primary; other formats need explicit approval) in the working folder, and reads the transcript from a file path you provide — never accepts transcript text pasted into the prompt. Use when the user says "evaluate my interview", "review my interview performance", "how did I do in this interview", "grade my interview answers", or invokes /interview-evaluate. Do NOT use for building or updating a CV (use cv-builder) or for general interview prep/question banks.
license: CC-BY-4.0
metadata:
  author: Flavio Studart
  version: "1.0.0"
---

# Interview Evaluate

Score how well a candidate performed in a completed job interview by reading the transcript and the candidate's CV from disk, then producing a per-question rubric evaluation and a prioritized set of takeaways for the next interview.

Act as an interview coach and technical bar-raiser: be honest about weak answers, specific about why, and concrete about what a stronger answer would have included.

## Working folder

Runs from the current working directory, which must already contain a `cv.*` file.

| File | Role |
|------|------|
| `cv.*` (existing, required) | Candidate's CV — source of truth for CV-alignment scoring |
| transcript file (user-provided path) | Full interview transcript, read once from disk |
| `interviews/<date>_<description>.md` | The generated evaluation report |

## Dependencies

- `pandoc` — used to extract plain text from `.docx` files (CV or transcript). If missing, ask the user to export the file to `.md`/`.txt`/`.pdf` instead.
- `references/star-method.md` — the STAR rubric authority. Load it whenever scoring a behavioral/experience answer. Do not ask the user for an external STAR reference — this file is the sole source.

## Before Starting

1. Look for `cv.*` in the current folder (case-insensitive). Accept `.md`, `.pdf`, `.docx` without asking. Any other extension → ask for explicit approval before reading it.
2. If no `cv.*` file is found at all: stop, tell the user this skill requires a CV in the working folder, and mention the `cv-builder` skill can create one. Do not proceed.
3. Ask the user for the path to the interview transcript file. Never accept transcript text pasted directly into the prompt — if the user pastes text instead of a path, ask them to save it to a file first and give the path. This is a hard rule with no exceptions (avoids burning context on a long transcript before it's clear the file is even the right one).

## Workflow

### Step 1 — Read the source files

Read `cv.*` and the transcript file, converting non-native formats:
- `.md` / `.txt` — read directly.
- `.pdf` — read directly (the Read tool renders PDF content).
- `.docx` — extract text first: `pandoc <file> -t plain`.

### Step 2 — Reconstruct question/answer pairs

Transcripts vary in shape (speaker-labeled, timestamped, diarized, or plain dialogue). Parse the transcript into an ordered list of interviewer-question → candidate-answer pairs, using judgment to:
- Merge an interrupted or multi-turn answer into one candidate turn.
- Split a single interviewer turn that bundles multiple distinct questions.
- Skip pure logistics/small talk (scheduling, introductions) — note it was skipped, don't score it.

If the transcript is too ambiguous to reconstruct clear pairs (e.g. no speaker labels at all), stop and ask the user for a cleaner transcript or clarification rather than guessing at attribution.

### Step 3 — Classify each question

Tag each question as one of:
- **Behavioral/experience** — STAR structure applies.
- **Technical** — technical rigor applies.
- **Other** — light-touch note only, skip the full rubric.

A question can be both behavioral and technical (e.g. "tell me about a time you debugged a production incident") — apply both dimensions when that happens.

### Step 4 — Score each question against the rubric

Rate every applicable dimension as **Strong / Adequate / Weak**, each with a one- or two-sentence concrete justification tied to what was actually said — never a bare label.

| Dimension | Applies to | What it measures |
|---|---|---|
| Relevance | All | Did the answer address what was actually asked, or drift/deflect? |
| Accuracy | All | Are the claims about past work, facts, or numbers internally consistent and plausible — any contradiction or overstatement? |
| Depth calibration | All | Deep enough to be clear and convincing, without padding that adds no further value — flag both under-explained and over-explained answers. |
| STAR structure | Behavioral | Load `references/star-method.md`. Which of Situation/Task/Action/Result are present, blended, or missing? Is the Result quantified? |
| CV alignment | All | Does the answer match what the CV claims for that experience? Should it have been more detailed (CV undersells it) or less (candidate over-elaborated beyond what the CV or role justifies)? |
| Technical rigor | Technical | Independent of general Accuracy: is the technical reasoning itself correct, precise, and at the right level for the question (not just "did they lie" but "did they get the concept/mechanism right")? |

### Step 5 — Aggregate and write the report

1. Identify recurring strengths and recurring weaknesses across all scored questions (patterns, not just a re-listing).
2. Write 3-5 concrete, prioritized recommendations for the next interview — each tied to a specific observed gap, not generic advice.
3. Ask the user for the report's date (default: today) and a short description (e.g. company or role) for the filename.
4. Check whether `interviews/<date>_<description>.md` already exists. If it does, tell the user and ask whether to overwrite it or use a different date/description — never overwrite silently.
5. Write the report using this structure:

```markdown
# Interview Evaluation — <description> (<date>)

## Overview
- Transcript: <path>
- CV reference: <cv file>
- Questions evaluated: <N> (<M> skipped as small talk/logistics)

## Per-Question Evaluation

### Q<n> — <Behavioral | Technical | Behavioral+Technical | Other>
**Question:** <question, summarized if long>
**Answer summary:** <1-3 sentence summary of what the candidate actually said>

| Dimension | Rating | Notes |
|---|---|---|
| Relevance | Strong/Adequate/Weak | ... |
| Accuracy | Strong/Adequate/Weak | ... |
| Depth calibration | Strong/Adequate/Weak | ... |
| STAR structure | Strong/Adequate/Weak | ... (omit row if not behavioral) |
| CV alignment | Strong/Adequate/Weak | ... |
| Technical rigor | Strong/Adequate/Weak | ... (omit row if not technical) |

<repeat per question>

## Overall Summary
- Recurring strengths: ...
- Recurring weaknesses: ...

## Key Takeaways for Next Interview
1. ...
2. ...
3. ...
```

## Guardrails

### Scope
- Only read `cv.*` and the transcript file the user points to; only write to `interviews/<date>_<description>.md`. Never modify the CV or transcript files.
- Never fabricate what the candidate said or what the CV contains — every claim in the report must trace to the transcript or the CV.

### Before Starting
- `cv.*` must exist in the working folder — see Before Starting above. Missing → stop and explain.
- Always require a transcript file path — never accept pasted transcript text as a substitute.
- A CV or transcript file extension outside `.md`/`.pdf`/`.docx` → ask for explicit approval before reading it.

### On Collision
- `interviews/<date>_<description>.md` already exists → ask before overwriting; offer to overwrite or pick a new date/description.

### When to Stop and Ask
- Transcript speaker turns are too ambiguous to reconstruct clear question/answer pairs → ask for a cleaner transcript rather than guessing at attribution.
- `pandoc` is unavailable and a `.docx` file needs conversion → ask the user to export to `.md`/`.txt`/`.pdf`.

### Output Validation
- The report must include Overview, one evaluation block per scored question, Overall Summary, and Key Takeaways.
- Every question in the transcript is accounted for — either scored or explicitly noted as skipped (small talk/logistics), never silently dropped.

## Examples

### Standard run
User: "Evaluate my interview, I just finished the onsite with Acme."
1. Find `cv.md` in the folder — present, proceed.
2. Ask for the transcript file path; user provides `acme-onsite.txt`.
3. Read both files, reconstruct 8 Q/A pairs, classify (5 behavioral, 2 technical, 1 other).
4. Score each against the rubric, loading `references/star-method.md` for the 5 behavioral answers.
5. Ask for date/description → `2026-07-20_acme-staff-swe`.
6. Write `interviews/2026-07-20_acme-staff-swe.md`.
Result: a full per-question report plus 3-5 prioritized takeaways.

### Missing CV
User: "Evaluate my interview" (no `cv.*` in the folder).
1. Precondition check fails.
Result: stop, explain that a `cv.*` file is required in the working folder, and suggest running `cv-builder` first.

### Pasted transcript instead of a file
User: "Evaluate my interview, here's the transcript: [pastes 2000 words]."
1. Refuse to consume the pasted text.
Result: ask the user to save it to a file and provide the path instead.

## Troubleshooting

### Transcript has no speaker labels
Ask the user whether they can re-export with speaker diarization, or manually mark which lines are the interviewer vs. the candidate — do not guess attribution on an unlabeled transcript.

### `.docx` file and no `pandoc` installed
Ask the user to install `pandoc` or export the file as `.md`, `.txt`, or `.pdf` instead.

### CV and transcript disagree on a claim
This is exactly what CV-alignment scoring is for — note the discrepancy in that dimension's justification rather than silently picking one source as ground truth.
