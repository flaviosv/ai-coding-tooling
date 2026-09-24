#!/usr/bin/env python3
"""The Azure DevOps review checkpoint page for the `code-review` skill.

    review_page.py render  <findings.json> <pr.diff> <out.html>
    review_page.py collect <findings.json> <db_dir> <out post.json>

`render` fills `assets/review-page.template.html` with the findings and, for each,
the diff lines around it. The page stores the user's choices in the artifact's
database, never the findings themselves:

    decisions/f<N>  {"state": "keep" | "drop", "body": "<edited text>"}   N = index in findings.json
    added/<id>      {"path": "...", "line": 12, "body": "..."}

`collect` reads those documents from the directory an ArtifactData `list` with
`out_dir` wrote (<db_dir>/decisions/*.json, <db_dir>/added/*.json) and writes
post.json: every finding not dropped, with its edited body when there is one,
followed by every added finding. A finding with no decision document is kept
unchanged. post.json keeps each finding's id, severity, and title, so the same
file feeds `ado_review.py post` and a fix worker that fixes without posting.

findings.json is post.json's shape, plus `id`, `severity`, and `title` on every
comment and `pr_url` / `pr_title` at the top level.
"""

import argparse
import glob
import json
import os
import sys

from github_review import HUNK_HEADER_RE, fatal, parse_unified_diff, read_json_file
from ado_review import validate_post_config

TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "assets", "review-page.template.html")
DATA_SLOT = "/*__REVIEW_DATA__*/null"
TITLE_SLOT = "__PAGE_TITLE__"
CONTEXT_LINES = 3


def hunk_rows(patch):
    """[[(kind, new_line or None, text)]] — one list per hunk, `kind` one of + - space."""
    hunks, new = [], None
    for raw in (patch or "").splitlines():
        header = HUNK_HEADER_RE.match(raw)
        if header:
            new = int(header.group(2))
            hunks.append([])
            continue
        if new is None or raw.startswith("\\"):
            continue
        kind, text = (raw[:1] or " "), raw[1:]
        if kind == "-":
            hunks[-1].append(("-", None, text))
        else:
            hunks[-1].append((kind if kind == "+" else " ", new, text))
            new += 1
    return hunks


def snippet(patch, line, anchor):
    if line is not None:
        for rows in hunk_rows(patch):
            for index, (_, number, _) in enumerate(rows):
                if number == line:
                    window = rows[max(0, index - CONTEXT_LINES): index + CONTEXT_LINES + 1]
                    return [{"k": k, "n": n, "t": t} for k, n, t in window]
    if anchor:
        return [{"k": " ", "n": line, "t": anchor}]
    return []


def render(findings, diff_text):
    patches = parse_unified_diff(diff_text)
    comments = []
    for index, comment in enumerate(findings["comments"]):
        path = comment["path"].lstrip("/")
        comments.append({
            "key": f"f{index}",
            "id": comment.get("id") or f"#{index + 1}",
            "severity": comment.get("severity") or "",
            "title": comment.get("title") or "",
            "path": path,
            "line": comment.get("line"),
            "body": comment["body"],
            "snippet": snippet(patches.get(path), comment.get("line"), comment.get("anchor")),
        })
    data = {
        "pr": findings["pr"],
        "prUrl": findings.get("pr_url") or "",
        "prTitle": findings.get("pr_title") or "",
        "repo": f"{findings['org']}/{findings['project']}/{findings['repo']}",
        "files": sorted(patches),
        "findings": comments,
    }
    with open(TEMPLATE, encoding="utf-8") as handle:
        page = handle.read()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return page.replace(TITLE_SLOT, f"{findings['repo']} PR {findings['pr']} findings").replace(DATA_SLOT, payload)


def read_docs(db_dir, collection):
    """{doc_id: body} from ArtifactData's out_dir files, oldest-first by file name."""
    docs = {}
    for path in sorted(glob.glob(os.path.join(db_dir, collection, "*.json"))):
        with open(path, encoding="utf-8") as handle:
            doc = json.load(handle)
        if isinstance(doc.get("data"), dict) and ("version" in doc or "id" in doc):
            doc = doc["data"]
        docs[os.path.splitext(os.path.basename(path))[0]] = doc
    return docs


def collect(findings, db_dir):
    decisions = read_docs(db_dir, "decisions")
    added = read_docs(db_dir, "added")
    kept, dropped, edited = [], [], []
    for index, comment in enumerate(findings["comments"]):
        decision = decisions.get(f"f{index}") or {}
        if decision.get("state") == "drop":
            dropped.append(comment.get("id"))
            continue
        out = dict(comment)
        out["path"] = comment["path"].lstrip("/")
        body = decision.get("body")
        if isinstance(body, str) and body.strip() and body != comment["body"]:
            out["body"] = body
            edited.append(comment.get("id"))
        kept.append(out)

    new = []
    for doc in added.values():
        path, line, body = (doc.get("path") or "").lstrip("/"), doc.get("line"), doc.get("body") or ""
        if path and isinstance(line, int) and line > 0 and body.strip():
            new.append({"id": f"U{len(new) + 1}", "severity": "", "title": "Added at checkpoint",
                        "path": path, "line": line, "body": body})

    post = {key: findings[key] for key in ("org", "project", "repo", "pr")}
    post["comments"] = kept + new
    summary = {
        "kept": len(kept),
        "dropped": dropped,
        "edited": edited,
        "added": len(new),
        "remaining": len(kept) + len(new),
    }
    return post, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render and collect the ADO review checkpoint page.")
    sub = parser.add_subparsers(dest="command", required=True)
    render_cmd = sub.add_parser("render")
    render_cmd.add_argument("findings")
    render_cmd.add_argument("diff")
    render_cmd.add_argument("out")
    collect_cmd = sub.add_parser("collect")
    collect_cmd.add_argument("findings")
    collect_cmd.add_argument("db_dir")
    collect_cmd.add_argument("out")
    args = parser.parse_args(argv)

    findings, error = read_json_file(args.findings)
    if error:
        return fatal(error)
    error = validate_post_config(findings)
    if error:
        return fatal(f"findings.json: {error}")

    if args.command == "render":
        try:
            with open(args.diff, encoding="utf-8") as handle:
                diff_text = handle.read()
        except OSError as exc:
            return fatal(f"cannot read diff: {exc}")
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(render(findings, diff_text))
        print(json.dumps({"page": os.path.abspath(args.out), "findings": len(findings["comments"])}))
        return 0

    if not os.path.isdir(args.db_dir):
        return fatal(f"no database export at {args.db_dir}")
    try:
        post, summary = collect(findings, args.db_dir)
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        return fatal(f"cannot read database export: {exc}")
    if post["comments"]:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(post, handle, indent=2, ensure_ascii=False)
        summary["post_json_path"] = os.path.abspath(args.out)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
