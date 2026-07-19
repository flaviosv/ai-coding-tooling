# RenderCV Schema (snapshot)

A starting reference for authoring `cv.yaml`. RenderCV's schema versions — **always verify the current shape live before writing YAML**: query Context7 (`/rendercv/rendercv`) or fetch the docs (docs.rendercv.com). Treat anything here that conflicts with live docs as outdated.

---

## Top-level keys

```yaml
cv:        # content: name, contacts, sections
design:    # theme + visual styling
locale:    # language, month names (optional)
settings:  # behavior, output paths (optional)
```

## cv block

```yaml
cv:
  name: Full Name
  headline: "Title · Specialization · Focus"   # the positioning line
  location: "City, Country (Remote)"
  email: name@example.com
  # phone: optional (prefer LinkedIn)
  social_networks:
    - network: LinkedIn      # LinkedIn, GitHub, GitLab, X, StackOverflow, ...
      username: handle
    - network: GitHub
      username: handle
  sections:
    Section Title:           # key = rendered section heading
      - <entries>
```

## Entry types (auto-detected by fields; one type per section)

- **ExperienceEntry** — needs `company`, `position`; supports `location`, `start_date`, `end_date` (or `"present"`), `summary`, `highlights` (list). Use `summary` for the one-line company descriptor; `highlights` for the bullets.
- **EducationEntry** — needs `institution`, `area`; supports `degree`, `location`, dates, `highlights`.
- **OneLineEntry** — needs `label`, `details`. Use for **Stack & Skills** (label = category, details = comma list), Certifications, Languages.
- **BulletEntry** — needs `bullet`. Use for a compact "Earlier Experience" section.
- **TextEntry** — a plain string. Use for the **Summary** paragraph.
- Others: PublicationEntry, NormalEntry, NumberedEntry, ReversedNumberedEntry.

Dates: `YYYY-MM` or `YYYY`; end date may be `present`. Highlights and text support Markdown (`**bold**`, `*italic*`, `[links](url)`).

## Mapping cv.md → cv.yaml

| cv.md element | cv.yaml |
|---|---|
| Positioning line | `cv.headline` |
| Contact line | `cv.location`, `cv.email`, `cv.social_networks` |
| `## Summary` paragraph | `Summary:` → TextEntry (plain string) |
| `## Stack & Skills` `**Category:** items` | `Stack & Skills:` → OneLineEntry (`label`/`details`) |
| `### Company — Title` + `*descriptor*` + bullets | ExperienceEntry (`company`, `position`, `location`, dates, `summary`, `highlights`) |
| `## Earlier Experience` one-liners | `Earlier Experience:` → BulletEntry list |
| Education / Certifications / Languages | EducationEntry / OneLineEntry |

## design block (defaults for this skill)

```yaml
design:
  theme: engineeringresumes    # clean, ATS-friendly, compact
  page:
    top_margin: 0.5in
    bottom_margin: 0.5in
    left_margin: 0.5in
    right_margin: 0.5in
```

Available themes: classic, engineeringresumes, engineeringclassic, sb2nov, moderncv.

## Layout tuning (agent-driven, for the page target)

- `design.entries.allow_page_break: true` — lets a single entry flow across a page break, filling the blank space the "keep-together" default leaves at page bottoms. Trade-off: an entry can split mid-page.
- `design.page.*_margin` — smaller margins reclaim vertical space and widen the text column (fewer line wraps).
- `design.typography.line_spacing`, `design.sections.space_between_regular_entries`, `design.section_titles.space_above/space_below` — fine spacing control.
- Render, inspect the PNGs, adjust, re-render. Tune design before cutting content; then cut weakest-first.

## Markdown quirks to avoid

- Bold immediately followed by punctuation (`**word**;`) can drop the punctuation — put a space or rephrase.
- Inside double-quoted YAML, escape internal double quotes (`\"`); apostrophes are safe.
