#!/usr/bin/env python3
"""Validate an increment-flow pending.md (increments table, items table, and the progress.md beside it) and compute the next free numbers.

Usage:
  pending.py check <pending.md>   exit 0 when consistent, 1 with one line per violation
  pending.py next  <pending.md>   prints "item=<N> increment=<NNN>"
"""
import re
import sys
from pathlib import Path

LANGS = {
    "en-US": {
        "header": ["#", "Item", "Status", "Depends on", "Increment", "Details"],
        "inc_header": ["Increment Number", "Title", "Status"],
        "inc_statuses": ["Open", "In Progress", "Done"],
        "open": ["Open", "Researching", "Researched", "Planning", "Planned", "Implementing"],
        "closed": {"Done": "done", "Declined": "declined", "Rejected": "rejected"},
        "progress_heading": "Increment",
        "progress_types": ["decision", "done", "change", "customization", "addition"],
    },
    "pt-BR": {
        "header": ["#", "Item", "Estado", "Depende de", "Incremento", "Detalhe"],
        "inc_header": ["Número do Incremento", "Título", "Estado"],
        "inc_statuses": ["Aberto", "Em Andamento", "Feito"],
        "open": ["Aberto", "Em Pesquisa", "Pesquisado", "Em Planejamento", "Planejado", "Desenvolvimento"],
        "closed": {"Feito": "feito", "Recusado": "recusado", "Rejeitado": "rejeitado"},
        "progress_heading": "Incremento",
        "progress_types": ["decisão", "feito", "mudança", "customização", "adição"],
    },
}
DETAILS_MAX = 200
ENTRY_MAX = 200
PROGRESS_FILE = "progress.md"
NONE = "—"
SECTION = re.compile(r"^## (\d+) — (.+?)(?: \(([^()]+)\))?\s*$")
INCREMENT_DIR = re.compile(r"^(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*$")
PROGRESS_SECTION = re.compile(r"^## (\S+) (\d{3}) — (.+?)\s*$")
PROGRESS_ENTRY = re.compile(r"^- (\d{4}-\d{2}-\d{2}) · (\S+) · (.+)$")


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read_rows(lines, start):
    rows = []
    for n, line in enumerate(lines[start + 2:], start + 3):
        if not line.startswith("|"):
            break
        rows.append((n, cells(line)))
    return rows


def parse(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    tables, inc_tables = [], []
    for i, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        row = cells(line)
        for lang, spec in LANGS.items():
            if row == spec["header"]:
                tables.append((i, lang))
            elif row == spec["inc_header"]:
                inc_tables.append((i, lang))
    rows = read_rows(lines, tables[0][0]) if len(tables) == 1 else []
    inc_rows = read_rows(lines, inc_tables[0][0]) if len(inc_tables) == 1 else []
    sections = {}
    for n, line in enumerate(lines, 1):
        m = SECTION.match(line)
        if m:
            sections.setdefault(int(m.group(1)), []).append((n, m.group(2), m.group(3)))
    return tables, rows, sections, inc_tables, inc_rows


def increments(root):
    found = {}
    for d in root.iterdir():
        m = INCREMENT_DIR.match(d.name)
        if d.is_dir() and m:
            found.setdefault(m.group(1), []).append(d.name)
    return found


def check_progress(path, lang, incs):
    spec = LANGS[lang]
    errors = []
    seen = []
    current = None
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("## "):
            m = PROGRESS_SECTION.match(line)
            if not m or m.group(1) != spec["progress_heading"]:
                errors.append(f"{PROGRESS_FILE} line {n}: section must be '## {spec['progress_heading']} NNN — <slug>'")
                current = None
                continue
            code, slug = m.group(2), m.group(3)
            current = code
            if code in seen:
                errors.append(f"{PROGRESS_FILE} line {n}: more than one section for increment {code}")
            elif seen and code < seen[-1]:
                errors.append(f"{PROGRESS_FILE} line {n}: sections must be in ascending increment order")
            seen.append(code)
            if code not in incs:
                errors.append(f"{PROGRESS_FILE} line {n}: increment {code} has no folder '{code}-<slug>/' next to pending.md")
            elif f"{code}-{slug}" not in incs[code]:
                errors.append(f"{PROGRESS_FILE} line {n}: slug '{slug}' differs from folder '{incs[code][0]}'")
        elif current and line.strip():
            m = PROGRESS_ENTRY.match(line)
            if not m:
                errors.append(f"{PROGRESS_FILE} line {n}: entry must be '- YYYY-MM-DD · <type> · <text>'")
            elif m.group(2) not in spec["progress_types"]:
                errors.append(f"{PROGRESS_FILE} line {n}: type '{m.group(2)}' is not one of: {', '.join(spec['progress_types'])}")
            elif len(m.group(3)) > ENTRY_MAX:
                errors.append(f"{PROGRESS_FILE} line {n}: text has {len(m.group(3))} characters, max {ENTRY_MAX}; shorten it or point to the file")
    return errors


def check_increments(inc_tables, inc_rows, lang, incs, rows):
    spec = LANGS[lang]
    if not inc_tables:
        return [f"no increments table; add '| {' | '.join(spec['inc_header'])} |' above the items table, one row per increment folder"]
    if len(inc_tables) != 1:
        return [f"expected exactly one increments table, found {len(inc_tables)}"]
    if inc_tables[0][1] != lang:
        return [f"increments table is in {inc_tables[0][1]} but the items table is in {lang}"]
    open_status, *working = spec["open"]
    closed = list(spec["closed"])
    statuses = spec["inc_statuses"]
    errors = []
    seen = []
    for line, row in inc_rows:
        where = f"line {line}"
        if len(row) != 3:
            errors.append(f"{where}: expected 3 cells in the increments table, found {len(row)}")
            continue
        code, title, status = row
        if not re.fullmatch(r"\d{3}", code):
            errors.append(f"{where}: Increment Number must be 3 digits, found '{code}'")
            continue
        where = f"line {line} (increment {code})"
        if code in seen:
            errors.append(f"{where}: duplicate increment number")
        elif seen and code < seen[-1]:
            errors.append(f"{where}: increments must be in ascending order")
        seen.append(code)
        if code not in incs:
            errors.append(f"{where}: no folder '{code}-<slug>/' next to pending.md")
        if not title:
            errors.append(f"{where}: Title is empty")
        if status not in statuses:
            errors.append(f"{where}: Status '{status}' is not one of: {', '.join(statuses)}")
            continue
        items = [r for _, r in rows if len(r) == 6 and r[4] == code]
        if status == statuses[0]:
            for r in items:
                if r[2] in working:
                    errors.append(f"{where}: is {status} but item #{r[0]} is {r[2]}; set the increment to {statuses[1]}")
        elif status == statuses[2]:
            for r in items:
                if r[2] not in closed:
                    errors.append(f"{where}: is {status} but item #{r[0]} is {r[2]}; close the item or move it to another increment")
    for code in sorted(incs):
        if code not in seen:
            errors.append(f"increment {code} has a folder but no row in the increments table")
    return errors


def check(path):
    errors = []
    tables, rows, sections, inc_tables, inc_rows = parse(path)
    if len(tables) != 1:
        return [f"expected exactly one item table, found {len(tables)}"]
    lang = tables[0][1]
    spec = LANGS[lang]
    suffix_of = spec["closed"]
    statuses = spec["open"] + list(suffix_of)
    incs = increments(path.parent)
    for code, names in incs.items():
        if len(names) > 1:
            errors.append(f"increment {code} has more than one folder: {', '.join(sorted(names))}")
    errors += check_increments(inc_tables, inc_rows, lang, incs, rows)

    numbers = []
    for line, row in rows:
        where = f"line {line}"
        if len(row) != 6:
            errors.append(f"{where}: expected 6 cells, found {len(row)}")
            continue
        num, item, status, depends, inc, details = row
        if not re.fullmatch(r"[1-9]\d*", num):
            errors.append(f"{where}: '#' must be a positive integer, found '{num}'")
            continue
        n = int(num)
        where = f"line {line} (#{n})"
        if n in numbers:
            errors.append(f"{where}: duplicate item number")
        if numbers and n < numbers[-1]:
            errors.append(f"{where}: rows must be in ascending '#' order")
        numbers.append(n)
        if not item:
            errors.append(f"{where}: Item is empty")
        if status not in statuses:
            errors.append(f"{where}: Status '{status}' is not one of: {', '.join(statuses)}")
        if depends != NONE:
            deps = [d.strip() for d in depends.split(",")]
            if not all(re.fullmatch(r"[1-9]\d*", d) for d in deps):
                errors.append(f"{where}: Depends on must be item numbers ('3' or '3, 5') or '{NONE}', found '{depends}'")
        if inc != NONE:
            if not re.fullmatch(r"\d{3}", inc):
                errors.append(f"{where}: Increment must be a 3-digit number or '{NONE}', found '{inc}'")
            elif inc not in incs:
                errors.append(f"{where}: Increment {inc} has no folder '{inc}-<slug>/' next to pending.md")
        if not details:
            errors.append(f"{where}: Details is empty")
        elif len(details) > DETAILS_MAX:
            errors.append(f"{where}: Details has {len(details)} characters, max {DETAILS_MAX}; move the rest to the section")

        found = sections.get(n)
        if not found:
            errors.append(f"{where}: no section '## {n} — {item}'")
            continue
        if len(found) > 1:
            errors.append(f"{where}: {len(found)} sections numbered {n}")
        _, title, suffix = found[0]
        if title != item:
            errors.append(f"{where}: Item '{item}' differs from section title '{title}'")
        expected = suffix_of.get(status)
        if suffix != expected:
            want = f"'({expected})'" if expected else "no status suffix"
            errors.append(f"{where}: section title must have {want} for status '{status}'")

    for line, row in rows:
        if len(row) == 6 and row[3] != NONE and re.fullmatch(r"[1-9]\d*", row[0]):
            for d in (x.strip() for x in row[3].split(",")):
                if d.isdigit() and int(d) not in numbers:
                    errors.append(f"line {line} (#{row[0]}): depends on item {d}, which is not in the table")
                if d == row[0]:
                    errors.append(f"line {line} (#{row[0]}): depends on itself")

    for n, found in sections.items():
        if n not in numbers:
            errors.append(f"line {found[0][0]}: section {n} has no row in the table")

    progress = path.parent / PROGRESS_FILE
    if progress.is_file():
        errors += check_progress(progress, lang, incs)
    return errors


def next_numbers(path):
    _, rows, sections, _, _ = parse(path)
    used = {int(r[0]) for _, r in rows if r and r[0].isdigit()} | set(sections)
    incs = increments(path.parent)
    item = max(used, default=0) + 1
    inc = max((int(c) for c in incs), default=0) + 1
    return item, f"{inc:03d}"


def main(argv):
    if len(argv) != 3 or argv[1] not in ("check", "next"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    path = Path(argv[2])
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2
    if argv[1] == "next":
        item, inc = next_numbers(path)
        print(f"item={item} increment={inc}")
        return 0
    errors = check(path)
    for e in errors:
        print(e)
    if not errors:
        print("ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
