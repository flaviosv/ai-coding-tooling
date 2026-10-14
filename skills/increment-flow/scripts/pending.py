#!/usr/bin/env python3
"""Validate an increment-flow pending.md and compute the next free numbers.

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
        "open": ["Open", "Researching", "Researched", "Planning", "Planned", "Implementing"],
        "closed": {"Done": "done", "Declined": "declined", "Rejected": "rejected"},
    },
    "pt-BR": {
        "header": ["#", "Item", "Estado", "Depende de", "Incremento", "Detalhe"],
        "open": ["Aberto", "Em Pesquisa", "Pesquisado", "Em Planejamento", "Planejado", "Desenvolvimento"],
        "closed": {"Feito": "feito", "Recusado": "recusado", "Rejeitado": "rejeitado"},
    },
}
DETAILS_MAX = 200
NONE = "—"
SECTION = re.compile(r"^## (\d+) — (.+?)(?: \(([^()]+)\))?\s*$")
INCREMENT_DIR = re.compile(r"^(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*$")


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    tables = []
    for i, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        row = cells(line)
        for lang, spec in LANGS.items():
            if row == spec["header"]:
                tables.append((i, lang))
    rows, sections = [], {}
    if len(tables) == 1:
        start, _ = tables[0]
        for n, line in enumerate(lines[start + 2:], start + 3):
            if not line.startswith("|"):
                break
            rows.append((n, cells(line)))
    for n, line in enumerate(lines, 1):
        m = SECTION.match(line)
        if m:
            sections.setdefault(int(m.group(1)), []).append((n, m.group(2), m.group(3)))
    return tables, rows, sections


def increments(root):
    found = {}
    for d in root.iterdir():
        m = INCREMENT_DIR.match(d.name)
        if d.is_dir() and m:
            found.setdefault(m.group(1), []).append(d.name)
    return found


def check(path):
    errors = []
    tables, rows, sections = parse(path)
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
    return errors


def next_numbers(path):
    _, rows, sections = parse(path)
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
