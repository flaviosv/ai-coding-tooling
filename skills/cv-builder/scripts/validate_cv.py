#!/usr/bin/env python3
"""Validate cv.md (structure + cv.yaml consistency) or linkedin.md (plain-text + LinkedIn field limits).

Mode is chosen by the input filename: "linkedin.md" -> LinkedIn validation, anything else -> CV validation.

Usage: python3 validate_cv.py [path/to/cv.md|path/to/linkedin.md]   (default: cv/cv.md, else ./cv.md)
Exit code 0 = pass, 1 = problems found.
"""
import re
import sys
from pathlib import Path

REQUIRED_ORDER = ["Summary", "Stack & Skills", "Experience", "Education"]
OPTIONAL = ["Earlier Experience", "Certifications", "Languages"]
PLACEHOLDERS = ["TODO", "_(pending)_", "_(pending", "PLACEHOLDER", "[ ]", "TBD", "FIXME", "XXX"]

LINKEDIN_LIMITS = {"Headline": 220, "About": 2600, "Experience entry": 2000}
DISALLOWED_MARKDOWN = [
    (r"^#{1,6}\s", "heading (#)"),
    (r"\*\*[^*]+\*\*", "bold (**)"),
    (r"__[^_]+__", "bold (__)"),
    (r"\[[^\]]+\]\([^)]+\)", "link ([text](url))"),
    (r"^```", "code fence"),
    (r"^\|.*\|\s*$", "table row"),
    (r"^>\s", "blockquote"),
    (r"^(---|===)\s*$", "horizontal rule"),
]


def resolve_input(argv) -> Path:
    if len(argv) > 1:
        return Path(argv[1])
    for candidate in (Path("cv/cv.md"), Path("cv.md")):
        if candidate.exists():
            return candidate
    return Path("cv/cv.md")


def section_titles(md: str):
    return [m.group(1).strip() for m in re.finditer(r"^##\s+(.+?)\s*$", md, re.M)]


def companies_from_md(md: str):
    names = set()
    in_experience = False
    for line in md.splitlines():
        h2 = re.match(r"^##\s+(.+?)\s*$", line)
        if h2:
            in_experience = h2.group(1).strip().lower() == "experience"
            continue
        if in_experience:
            h3 = re.match(r"^###\s+(.+?)\s*$", line)
            if h3:
                heading = h3.group(1).strip()
                if heading.lower().startswith("earlier experience"):
                    continue
                # "### Company — Title"  ->  "Company"
                names.add(re.split(r"\s+[—–-]\s+", heading)[0].strip())
    return names


def companies_from_yaml(text: str):
    return {m.group(1).strip().strip('"\'') for m in re.finditer(r"^\s*-?\s*company:\s*(.+?)\s*$", text, re.M)}


def validate_cv(md_path: Path) -> int:
    md = md_path.read_text(encoding="utf-8")
    lines = [l for l in md.splitlines()]
    errors, warnings = [], []

    # Header
    if not re.search(r"^#\s+\S", md, re.M):
        errors.append("missing H1 name (`# Name`).")
    head = [l for l in lines[:8] if l.strip()]
    if not any(l.strip().startswith("**") for l in head):
        warnings.append("no bold positioning line found near the top.")
    if not any("@" in l for l in head):
        warnings.append("no contact line with an email found near the top.")

    # Sections present + ordered
    titles = section_titles(md)
    for req in REQUIRED_ORDER:
        if req not in titles:
            errors.append(f"missing required section: ## {req}")
    present_required = [t for t in titles if t in REQUIRED_ORDER]
    if present_required != [t for t in REQUIRED_ORDER if t in titles]:
        errors.append(f"required sections out of order: {present_required} (expected {REQUIRED_ORDER}).")

    # Experience entries each have a bullet
    blocks = re.split(r"^###\s+", md, flags=re.M)
    for block in blocks[1:]:
        heading = block.splitlines()[0].strip()
        body = "\n".join(block.splitlines()[1:])
        # only enforce within roles that look like experience entries (have a date-ish line)
        if re.search(r"\b(19|20)\d{2}\b", body) and not re.search(r"^\s*[-*]\s+\S", body, re.M):
            warnings.append(f"entry '{heading}' has no bullet points.")

    # Placeholders
    for ph in PLACEHOLDERS:
        if ph in md:
            errors.append(f"leftover placeholder text found: '{ph}'")

    # Consistency with cv.yaml
    yaml_path = md_path.parent / "cv.yaml"
    if yaml_path.exists():
        md_co = companies_from_md(md)
        yaml_co = companies_from_yaml(yaml_path.read_text(encoding="utf-8"))
        only_md = md_co - yaml_co
        only_yaml = yaml_co - md_co
        if only_md:
            warnings.append(f"companies in cv.md but not cv.yaml: {sorted(only_md)}")
        if only_yaml:
            warnings.append(f"companies in cv.yaml but not cv.md: {sorted(only_yaml)}")
    else:
        warnings.append("cv.yaml not found — skipped cv.md<->cv.yaml consistency check.")

    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"FAIL: {e}")
    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"\nOK — cv.md valid ({len(warnings)} warning(s)).")
    return 0


def validate_linkedin(md_path: Path) -> int:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors, warnings = [], []

    for pattern, label in DISALLOWED_MARKDOWN:
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line):
                errors.append(f"line {i}: disallowed markdown — {label}: {line.strip()[:60]!r}")

    def find_line(label):
        for i, line in enumerate(lines):
            if line.strip() == label:
                return i
        return None

    about_i = find_line("ABOUT")
    experience_i = find_line("EXPERIENCE")
    education_i = find_line("EDUCATION")
    if about_i is None:
        errors.append("missing ABOUT section marker.")
    if experience_i is None:
        errors.append("missing EXPERIENCE section marker.")

    # Headline = first non-empty line after the name (line 1)
    non_empty = [l for l in lines if l.strip()]
    if len(non_empty) >= 2:
        headline = non_empty[1]
        if len(headline) > LINKEDIN_LIMITS["Headline"]:
            errors.append(f"Headline is {len(headline)} chars, over the {LINKEDIN_LIMITS['Headline']} limit.")
    else:
        warnings.append("could not find a Headline line (name + headline near the top).")

    if about_i is not None and experience_i is not None:
        about_text = "\n".join(lines[about_i + 1:experience_i]).strip()
        if len(about_text) > LINKEDIN_LIMITS["About"]:
            errors.append(f"About section is {len(about_text)} chars, over the {LINKEDIN_LIMITS['About']} limit.")

    if experience_i is not None:
        end_i = education_i if education_i is not None else len(lines)
        # entry headers look like "Company — Title" (em dash), never a bullet line
        header_re = re.compile(r"^\S.* — .+\S$")
        headers = [
            i for i in range(experience_i + 1, end_i)
            if lines[i].strip() and not lines[i].strip().startswith("-") and header_re.match(lines[i])
        ]
        if not headers:
            warnings.append("no Experience entries found under the EXPERIENCE marker.")
        for idx, h in enumerate(headers):
            entry_end = headers[idx + 1] if idx + 1 < len(headers) else end_i
            body = lines[h + 1:entry_end]
            # skip the location/dates line right after the header, count the rest as the description
            first_nonblank = next((k for k, l in enumerate(body) if l.strip()), None)
            desc = "\n".join(body[first_nonblank + 1:]).strip() if first_nonblank is not None else ""
            if len(desc) > LINKEDIN_LIMITS["Experience entry"]:
                errors.append(
                    f"Experience entry '{lines[h].strip()[:60]}' description is {len(desc)} chars, "
                    f"over the {LINKEDIN_LIMITS['Experience entry']} limit."
                )

    for ph in PLACEHOLDERS:
        if ph in text:
            errors.append(f"leftover placeholder text found: '{ph}'")

    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"FAIL: {e}")
    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"\nOK — linkedin.md valid ({len(warnings)} warning(s)).")
    return 0


def main() -> int:
    md_path = resolve_input(sys.argv)
    if not md_path.exists():
        print(f"error: file not found: {md_path}", file=sys.stderr)
        return 1
    if md_path.name == "linkedin.md":
        return validate_linkedin(md_path)
    return validate_cv(md_path)


if __name__ == "__main__":
    raise SystemExit(main())
