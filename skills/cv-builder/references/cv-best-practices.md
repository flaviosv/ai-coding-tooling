# CV Best Practices

The sole CV-writing authority for this skill. Load it whenever writing or reviewing CV content. Distilled from modern ATS/recruiter guidance and hardened by real build sessions. Rules are ordered by leverage.

---

## How modern ATS and recruiters actually read

Modern ATS use NLP to judge the **context** of experience, not just keyword presence. A recruiter then scans the top third in seconds, top-down, weighting the most recent roles most. So: keywords need context, the top third must land the positioning fast, and recent work gets the space.

- A missing keyword lowers a score; it rarely auto-rejects. Do not keyword-stuff — modern systems detect the artificial pattern.
- Every keyword earns context: not "management" but "technical leadership of a 5-dev team". Not a bare "AWS" but "ran the AWS estate (EC2, RDS), cut costs ~10%".

## The catalog vs. the CV

Extract exhaustively into `experiences.md` (the catalog); the CV is a **curated distillation** of it targeted at one positioning. Never dump the catalog onto the CV.

## Positioning first

Before writing any CV content, decide the target: role, level, focus, and what to de-emphasize. Everything — summary, ordering, emphasis, which skills lead — flows from this. For a career pivot, lead with the *destination* discipline and use the deepest history as proof, not the headline.

## The header

- **Positioning line** under the name: `Title · Specialization · Focus`. Not a generic job title.
- Contacts: location, email, LinkedIn, GitHub. Prefer a **LinkedIn link over a phone number**.
- Clarify remote/authorization where ambiguous (e.g. "Remote (US company)" for someone based elsewhere; note dual citizenship if it aids work authorization).

## The summary (formula)

`[role/specialization] with [X years] in [domain]. [impact metric 1] and [impact metric 2] in [context].` Add one **forward-looking "seeking" line** for a pivot — it tells a recruiter why this history is applying for this target, closing the gap before they wonder.

```text
// Good
Senior Software Engineer focused on backend and AI engineering, with ~20 years in system
design and software architecture. Sustained 12k concurrent users and cut an LLM chatbot's
tokens 67% / latency 50%. Seeking a collaborative, high-challenge role with a modern stack.

// Bad
Dedicated, proactive software professional passionate about technology and teamwork,
seeking challenging opportunities to grow.
```

## Impact bullets (formula)

`impact verb + metric + method`. Lead with a strong verb (Architected, Designed, Reduced, Migrated, Built, Led, Automated). Attach a number and the method.

```text
// Good
Cut mobile API response times ~40% by introducing a BFF gateway and direct-read endpoints.

// Bad
Was responsible for improving the performance of the mobile API.
```

- Keep bullets skimmable (roughly one to two lines). Split or trim any that run long.
- Separate concerns: do not mix a leadership claim and a feature achievement in one bullet.

## Stack & Skills — expertise-only

The skills list is a "grill me on any of these" list. **List only what the person would survive a deep-dive on.** Categorize (Languages, Frameworks, Architecture, AI, Cloud, Databases, …); technical items only; alphabetize within each category.

- **Used-but-not-expert** technology → **JD-mention only**: it appears in the relevant experience bullet (proving exposure) but not the skills list.
- Stale tech (years since last use) → cut unless still defendable.
- A specific soft-skills line is allowed for senior/leadership profiles (technical leadership, mentoring, stakeholder communication) — never generic filler ("hardworking, proactive").
- **Cross-check with LinkedIn:** every listed skill should be defendable and consistent with the person's public profile.

## Tiered experience

Weight by recency + relevance:
- **Full detail** (3–5 bullets): the strongest recent roles.
- **Condensed** (1–2 high-signal bullets): older or lower-relevance roles.
- **Earlier** (one compact line each): the oldest roles, to show career span without spending space.

Tenure matters less than what a role proves — a 5-month role with a strong, owned deliverable can stay full-detail.

## Hard rules (learned the hard way)

- **No "firsts" on the CV.** "First Go project", "first architect role" undersell to a recruiter whose only impression is the document. Save firsts for interviews; frame everything as owned competence.
- **Anonymize third-party clients.** For agency/consultancy work, replace a confidential client's name with its **market/industry** (e.g. "a homeschooling retailer", "a US utility"). Keep integration platforms and non-confidential named tech.
- **Naming currency.** Use the current product/brand name (e.g. the current name of a rebranded platform), keeping legacy names only where historically accurate.
- **Defensible metrics only.** Never fabricate. Mark estimates `~`. Drop or clearly qualify unmeasured numbers — an unmeasured "30% faster" collapses under "how did you measure that?".
- **Attribution honesty.** Claim only what the person built or owned. "Contributed to" and "worked on" are honest and still valuable; do not upgrade them to "architected".

## STAR (for interviews and bullet sourcing)

Every achievement is a Situation → Task → Action → Result. The **Result** (with a metric) is what makes a bullet land and what an interviewer probes. Keep a story bank in the catalog; the CV bullet is the compressed Result-forward version.

## Final passes before done

1. **Recruiter review** — read the whole CV as a 30-second top-down scan. Is the positioning unmistakable? Any weak, redundant, or undefendable line? Any bullet a recruiter's eye bounces off?
2. **LinkedIn cross-check** — CV skills align with LinkedIn; nothing listed that can't be defended.
3. **Length** — target the agreed page count; tune design before cutting content, then cut weakest-first.
