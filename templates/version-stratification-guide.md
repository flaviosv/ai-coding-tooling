---
name: version-stratification-guide
description: Guide for organizing reference file content by technology version with version-specific sections.
type: template
---

## Version Stratification

Reference files MUST be organized by version when the technology has multiple versions with meaningful differences. The version range spans from the oldest still-supported version to the latest stable.

Use this structure:

```
# <Technology> Reference — <SkillName>

<!-- General section covers conventions that apply across ALL still-supported versions -->
## General <Technology> Patterns

[Universal conventions: naming, file organization, core idioms — things that apply regardless of version]

---

## <Technology> <BaseVersion>  (e.g. PHP 8.1)

[Patterns and features present since the base supported version. This is the floor — everything a
project on this version can use.]

---

## <Technology> <BaseVersion+1>  (e.g. PHP 8.2)

[Only what is NEW in this version compared to the previous section. Do NOT repeat earlier content.]

---

## <Technology> <Latest>  (e.g. PHP 8.4)

[Only what is NEW in the latest version. Do NOT repeat earlier content.]
```

**Rules:**

- Start with a **General** section for universal conventions that span all supported versions.
- The **base version section** covers everything available as of the oldest still-supported version (the floor for new projects).
- Each subsequent version section documents **only what is new** in that version — no repetition.
- Add a section per minor (or major) version only if it introduced changes **relevant to the skill's domain**. Skip versions with no meaningful new content for that domain.
- Note version requirements inline where useful (e.g. `# PHP 8.3+`), but the section header already implies the version floor.
- If the technology has no meaningful version-level differences for this skill's domain, omit version sections and use a flat structure.
