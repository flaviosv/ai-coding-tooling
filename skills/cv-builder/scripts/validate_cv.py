#!/usr/bin/env python3
"""Validate the structure of cv.md and its consistency with cv.yaml.

Checks (stdlib only, no PyYAML):
  - Required sections present and in order.
  - Header has a name (H1), a positioning line, and a contact line.
  - Each Experience entry (### heading) has at least one bullet.
  - No leftover placeholder text.
  - Company set in cv.md matches the company set in cv.yaml (if cv.yaml exists).

Usage: python3 validate_cv.py [path/to/cv.md]   (default: cv/cv.md, else ./cv.md)
Exit code 0 = pass, 1 = problems found.
"""
import re
import sys
from pathlib import Path

REQUIRED_ORDER = ["Summary", "Stack & Skills", "Experience", "Education"]
OPTIONAL = ["Earlier Experience", "Certifications", "Languages"]
PLACEHOLDERS = ["TODO", "_(pending)_", "_(pending", "PLACEHOLDER", "[ ]", "TBD", "FIXME", "XXX"]


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


def main() -> int:
    md_path = resolve_input(sys.argv)
    if not md_path.exists():
        print(f"error: cv.md not found: {md_path}", file=sys.stderr)
        return 1
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


if __name__ == "__main__":
    raise SystemExit(main())
