#!/usr/bin/env python3
"""Link an increment folder to an Azure DevOps Task under a User Story and keep the Task's state in step.

Usage:
  wit.py ado                                   exit 0 when a git remote is Azure DevOps, 1 otherwise
  wit.py item   --type <type> --title <text> --description <text> [--parent <id|url>] [--project <name>]
  wit.py create <increment-dir> --us <id|url> --title <text> --description <text>
  wit.py none   <increment-dir>
  wit.py state  <increment-dir> New|Active|Resolved

`item` creates any work item (Feature, User Story, ...) under an optional parent and prints one JSON
line with its id, url, type, state and project. `create` checks the User Story exists, creates a Task (Activity "30 - Desenvolvimento", Original Estimate 8), makes the Story its parent and writes
<increment-dir>/wit.md. `none` writes wit.md with "none" (no User Story, do not ask again).
`state` moves the Task; it exits 0 doing nothing when wit.md says none, and exits 3 when there is no
wit.md yet (the caller has not asked the user). Needs `az` with the azure-devops extension, logged in.
"""
import argparse
import html
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import date
from pathlib import Path

WIT_FILE = "wit.md"
NONE = "none"
STATES = ["New", "Active", "Resolved"]
NOT_ASKED = 3
TASK_FIELDS = ["Microsoft.VSTS.Common.Activity=30 - Desenvolvimento", "Microsoft.VSTS.Scheduling.OriginalEstimate=8"]
ORG_FROM_URL = re.compile(r"^(https://dev\.azure\.com/[^/]+|https://[^/.]+\.visualstudio\.com)", re.I)
ID_FROM_REF = re.compile(r"(?:_workitems/edit/|#|^)(\d+)/?$")
ROW = re.compile(r"^\| (.+?) \| (.*?) \|$")
FLOW_LEAK = re.compile(r"\bIC[ -]?\d+\b|\bincrement[o]?s?[ -]?\d{3}\b|\.md\b|docs/research", re.I)
ADO_HOSTS = re.compile(r"^(ssh\.)?dev\.azure\.com$|^vs-ssh\.visualstudio\.com$|\.visualstudio\.com$", re.I)
SCP_HOST = re.compile(r"^(?:[^@/]+@)?([^:/]+):")
LINK = re.compile(r"^\[#(\d+)\]\((.+)\)$")


def fail(message, code=1):
    print(message, file=sys.stderr)
    sys.exit(code)


def az(*args, org=None):
    cmd = ["az", "boards", *args, "--output", "json", "--only-show-errors"]
    if org:
        cmd += ["--org", org]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail(f"az failed to run: {exc}")
    if proc.returncode != 0:
        fail(f"az {' '.join(args[:2])} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def parse_ref(ref):
    match = ID_FROM_REF.search(ref.strip())
    if not match:
        fail(f"cannot read a work item id from '{ref}'")
    org = ORG_FROM_URL.match(ref.strip())
    return match.group(1), (org.group(1) + "/" if org else None)


def web_url(item):
    return item["_links"]["html"]["href"]


def read_wit(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match and match.group(1) not in ("Field", "---"):
            rows[match.group(1)] = match.group(2)
    return rows


def write_wit(inc_dir, rows):
    number = inc_dir.name.split("-")[0]
    lines = [f"# Azure DevOps — increment {number}", "", "| Field | Value |", "|---|---|"]
    lines += [f"| {key} | {value} |" for key, value in rows.items()]
    (inc_dir / WIT_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")


def link(item):
    return f"[#{item['id']}]({web_url(item)})"


def cmd_none(inc_dir):
    write_wit(inc_dir, {"User Story": NONE, "Task": NONE})
    print(f"{inc_dir.name}: no User Story, wit.md says none")


def make_item(item_type, title, description, parent, project, org, fields=()):
    for text in (title, description):
        leak = FLOW_LEAK.search(text)
        if leak:
            fail(f"'{leak.group(0)}' refers to the increment flow; Azure DevOps text must describe the card itself")
    parent_id = None
    if parent:
        parent_id, parent_org = parse_ref(parent)
        org = org or parent_org
        project = project or az("work-item", "show", "--id", parent_id, org=org)["fields"]["System.TeamProject"]
    if not project:
        fail("--project is required when the item has no parent")
    item = az(
        "work-item", "create", "--type", item_type, "--project", project,
        "--title", title, "--description", html.escape(description).replace("\n", "<br>"),
        *(["--fields", *fields] if fields else []),
        org=org,
    )
    if parent_id:
        try:
            az("work-item", "relation", "add", "--id", str(item["id"]), "--relation-type", "parent",
               "--target-id", parent_id, org=org)
        except SystemExit:
            print(f"{item_type} #{item['id']} was created but not linked to #{parent_id}; delete or link it by hand",
                  file=sys.stderr)
            raise
    return item, project, org


def cmd_item(item_type, title, description, parent, project):
    item, project, _ = make_item(item_type, title, description, parent, project, None)
    print(json.dumps({"id": item["id"], "url": web_url(item), "type": item_type,
                      "state": item["fields"]["System.State"], "project": project}))


def cmd_create(inc_dir, ref, title, description):
    existing = inc_dir / WIT_FILE
    if existing.exists() and read_wit(existing).get("Task") != NONE:
        fail(f"{existing} already has a Task; use `state` to move it")
    us_id, org = parse_ref(ref)
    story = az("work-item", "show", "--id", us_id, org=org)
    task, project, org = make_item("Task", title, description, ref, None, org, TASK_FIELDS)
    state = task["fields"]["System.State"]
    write_wit(inc_dir, {
        "Organization": org or "default",
        "Project": project,
        "User Story": link(story),
        "Task": link(task),
        "State": state,
        "Updated": date.today().isoformat(),
    })
    print(f"{inc_dir.name}: Task #{task['id']} under {story['fields']['System.WorkItemType']} #{us_id}, state {state}")


def remote_host(url):
    if "://" in url:
        return urllib.parse.urlsplit(url).hostname or ""
    match = SCP_HOST.match(url)
    return match.group(1) if match else ""


def resolve_alias(host):
    try:
        proc = subprocess.run(["ssh", "-G", host], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return host
    for line in proc.stdout.splitlines():
        key, _, value = line.partition(" ")
        if key == "hostname" and value.strip():
            return value.strip()
    return host


def cmd_ado():
    try:
        out = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        sys.exit(1)
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            host = remote_host(parts[1])
            if host and (ADO_HOSTS.search(host) or ADO_HOSTS.search(resolve_alias(host))):
                print("ado")
                return
    sys.exit(1)


def cmd_state(inc_dir, state):
    path = inc_dir / WIT_FILE
    if not path.exists():
        fail(f"{path} not found: the user has not been asked about a User Story yet", NOT_ASKED)
    rows = read_wit(path)
    task = LINK.match(rows.get("Task", ""))
    if rows.get("Task") == NONE or not task:
        print(f"{inc_dir.name}: no Task, nothing to move")
        return
    if rows.get("State") == state:
        print(f"{inc_dir.name}: Task #{task.group(1)} already {state}")
        return
    org = rows.get("Organization")
    az("work-item", "update", "--id", task.group(1), "--state", state,
       org=None if org == "default" else org)
    rows["State"] = state
    rows["Updated"] = date.today().isoformat()
    write_wit(inc_dir, rows)
    print(f"{inc_dir.name}: Task #{task.group(1)} -> {state}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ado")
    item = sub.add_parser("item")
    item.add_argument("--type", required=True)
    item.add_argument("--title", required=True)
    item.add_argument("--description", required=True)
    item.add_argument("--parent")
    item.add_argument("--project")
    create = sub.add_parser("create")
    create.add_argument("inc_dir", type=Path)
    create.add_argument("--us", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--description", required=True)
    sub.add_parser("none").add_argument("inc_dir", type=Path)
    state = sub.add_parser("state")
    state.add_argument("inc_dir", type=Path)
    state.add_argument("state", choices=STATES)
    args = parser.parse_args()
    if args.command == "ado":
        return cmd_ado()
    if args.command == "item":
        return cmd_item(args.type, args.title, args.description, args.parent, args.project)
    if not args.inc_dir.is_dir():
        fail(f"{args.inc_dir} is not an increment folder")
    if args.command == "create":
        cmd_create(args.inc_dir, args.us, args.title, args.description)
    elif args.command == "none":
        cmd_none(args.inc_dir)
    else:
        cmd_state(args.inc_dir, args.state)


if __name__ == "__main__":
    main()
