#!/usr/bin/env python3
"""Report the facts architecture-evaluate needs before choosing and running a mode, as JSON.

Usage:
    context_scan.py [--root PATH] [--base REF]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BASELINE_DIR = "docs/codebase"
CANONICAL = [
    "ARCHITECTURE.md",
    "CONCERNS.md",
    "CONVENTIONS.md",
    "INTEGRATIONS.md",
    "PIPELINE.md",
    "PROJECT.md",
    "STACK.md",
    "STRUCTURE.md",
    "TESTING.md",
]
SKIP_DIRS = {
    ".git", ".next", ".nuxt", ".terraform", ".tox", ".venv", "__pycache__",
    "build", "coverage", "dist", "node_modules", "target", "vendor", "venv",
}
PIPELINE_FILES = [
    ".drone.yml",
    ".gitlab-ci.yml",
    ".travis.yml",
    "Jenkinsfile",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
]
PIPELINE_DIRS = [".buildkite", ".circleci", ".github/workflows"]


def scan_baseline(root):
    base = root / BASELINE_DIR
    present = [name for name in CANONICAL if (base / name).is_file()]
    extra = sorted(
        str(p.relative_to(root))
        for p in base.rglob("*.md")
        if p.is_file() and p.relative_to(base).as_posix() not in CANONICAL
    ) if base.is_dir() else []
    return {
        "dir": BASELINE_DIR,
        "exists": bool(present),
        "present": present,
        "missing": [name for name in CANONICAL if name not in present],
        "extra": extra,
    }


def scan_misplaced(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel = current.relative_to(root).as_posix()
        if rel == BASELINE_DIR:
            dirnames[:] = []
            continue
        # A nested directory holding its own .git is a separate checkout (e.g. a worktree), not this project.
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and not (current / d / ".git").exists()
        )
        found.extend(
            str((current / name).relative_to(root)) for name in sorted(filenames) if name in CANONICAL
        )
    return found


def scan_pipeline(root):
    paths = [name for name in PIPELINE_FILES if (root / name).is_file()]
    for name in PIPELINE_DIRS:
        folder = root / name
        if folder.is_dir():
            paths.extend(sorted(str(p.relative_to(root)) for p in folder.rglob("*") if p.is_file()))
    return {"exists": bool(paths), "paths": paths}


def git_lines(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return [line for line in result.stdout.splitlines() if line]


def scan_changes(root, base):
    try:
        if base:
            changed = git_lines(root, "diff", "--name-only", f"{base}...HEAD")
            added = git_lines(root, "diff", "--name-only", "--diff-filter=A", f"{base}...HEAD")
        else:
            untracked = git_lines(root, "ls-files", "--others", "--exclude-standard")
            changed = git_lines(root, "diff", "--name-only", "HEAD") + untracked
            added = git_lines(root, "diff", "--name-only", "--diff-filter=A", "HEAD") + untracked
    except (RuntimeError, FileNotFoundError) as error:
        return {"source": base or "working-tree", "error": str(error)}
    return {
        "source": f"{base}...HEAD" if base else "working-tree",
        "changed": sorted(set(changed)),
        "added": sorted(set(added)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--base", help="base ref; report changes in <base>...HEAD instead of the working tree")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.exit(f"not a directory: {root}")

    pipeline = scan_pipeline(root)
    deliverables = [
        f"{BASELINE_DIR}/{name}" for name in CANONICAL if name != "PIPELINE.md" or pipeline["exists"]
    ]
    report = {
        "root": str(root),
        "baseline": scan_baseline(root),
        "misplaced": scan_misplaced(root),
        "pipeline": pipeline,
        "deliverables": deliverables,
        "changes": scan_changes(root, args.base),
    }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
