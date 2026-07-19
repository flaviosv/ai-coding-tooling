#!/usr/bin/env python3
"""Render a RenderCV cv.yaml to PDF/PNG/HTML/Markdown/Typst.

Uses an installed `rendercv` if present, otherwise runs it ephemerally via
`uvx --from "rendercv[full]"` (no permanent install), then `pipx` as a last resort.
Output lands in `rendercv_output/` next to the input file. Reports the page count
so the agent knows if it is over the target.

Usage: python3 render.py [path/to/cv.yaml]   (default: cv/cv.yaml, else ./cv.yaml)
"""
import shutil
import subprocess
import sys
from pathlib import Path


def resolve_input(argv) -> Path:
    if len(argv) > 1:
        return Path(argv[1])
    for candidate in (Path("cv/cv.yaml"), Path("cv.yaml")):
        if candidate.exists():
            return candidate
    return Path("cv/cv.yaml")


def build_command(yaml_name: str):
    if shutil.which("rendercv"):
        return ["rendercv", "render", yaml_name]
    if shutil.which("uvx") or shutil.which("uv"):
        return ["uvx", "--from", "rendercv[full]", "rendercv", "render", yaml_name]
    if shutil.which("pipx"):
        return ["pipx", "run", "--spec", "rendercv[full]", "rendercv", "render", yaml_name]
    return None


def main() -> int:
    yaml_path = resolve_input(sys.argv)
    if not yaml_path.exists():
        print(f"error: input not found: {yaml_path}", file=sys.stderr)
        return 2

    workdir = yaml_path.parent if yaml_path.parent != Path("") else Path(".")
    cmd = build_command(yaml_path.name)
    if cmd is None:
        print("error: no renderer available. Install rendercv, or install uv/pipx.", file=sys.stderr)
        return 3

    print(f"rendering {yaml_path} with: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=workdir)
    if result.returncode != 0:
        print("error: render failed (see output above).", file=sys.stderr)
        return result.returncode

    out_dir = workdir / "rendercv_output"
    pngs = sorted(out_dir.glob("*_[0-9]*.png")) if out_dir.exists() else []
    pdf = next(iter(out_dir.glob("*.pdf")), None) if out_dir.exists() else None
    print(f"\noutput: {out_dir}")
    if pdf:
        print(f"pdf:    {pdf}")
    print(f"pages:  {len(pngs)}")
    if len(pngs) > 2:
        print("note: over 2 pages — inspect the PNGs and tune the design: block if a shorter CV is wanted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
