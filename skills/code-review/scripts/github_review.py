#!/usr/bin/env python3
"""Deterministic GitHub writes for the `code-review` skill.

Three subcommands, one set of mechanics:

    post     <post.json>      pending review: validate anchors -> dedup -> batched threads -> reconcile
    submit   <owner> <repo> <pr>   submit this identity's pending review as COMMENT -> confirm state
    deliver  <delivery.json>  thread replies and resolves -> confirm each by re-fetch

Every number this script reports comes from re-fetching GitHub's own state, never
from what it sent. It exits non-zero when any intended outcome is unconfirmed, so a
caller cannot mistake "sent" for "landed" — the failure mode this script exists to
make impossible (see skills/code-review/STATE.md FR-AD-001, FR-AD-006, FR-AD-007).

post.json:
    {
      "owner": "octocat", "repo": "hello-world", "pr": 42,
      "comments": [
        {"path": "src/a.py", "line": 18, "side": "RIGHT",
         "body": "**[Security — S1, High]** ...", "anchor": "exact text of line 18"}
      ]
    }

    `side` defaults to RIGHT. `line` may be null only for RIGHT with an `anchor`.
    Anchors are checked against the file at the PR head commit: a line whose anchor
    text sits elsewhere is corrected, and an anchor found nowhere makes the comment
    unpostable. A comment outside every diff hunk is re-anchored to the nearest
    in-hunk line of its file, and one on a file the PR never touched is unpostable.

delivery.json:
    {
      "owner": "octocat", "repo": "hello-world", "pr": 42,
      "threads": {"PRRT_kwDOxxx": {"body": "reply text", "resolve": true}},
      "skipped": {"PRRT_kwDOzzz": "routed to @alice — awaiting her answer"}
    }

    `threads` and `skipped` together must account for every in-scope thread on the
    PR (published, not already resolved). Any in-scope thread in neither list is
    reported as `unaccounted` and exits non-zero.

Output JSON goes to stdout; human-readable progress goes to stderr.

Exit codes:
    0  every intended outcome confirmed on GitHub
    1  partial — an intended outcome is unconfirmed, or a thread went unaccounted
    2  fatal — bad input, or GitHub unreachable
"""

import argparse
import base64
import json
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone

DEFAULT_BATCH_SIZE = 10
POST_BATCH_PACE_S = 1.0
REPLY_BATCH_PACE_S = 5.0
RESOLVE_BATCH_PACE_S = 1.0
ABUSE_WAIT_S = 180
MAX_ABUSE_WAITS = 2
GH_TIMEOUT_S = 120
THREAD_PAGE_SIZE = 100
COMMENT_PAGE_SIZE = 100
SIDES = ("LEFT", "RIGHT")
HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


# ---------------------------------------------------------------------------
# Shared mechanics
# ---------------------------------------------------------------------------


class GhError(RuntimeError):
    """A `gh` invocation that did not return usable JSON."""

    def __init__(self, message, stdout="", stderr=""):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr

    def looks_like_abuse_block(self):
        blob = (self.stdout + self.stderr).lower()
        return "abuse" in blob or "secondary rate limit" in blob


def log(message):
    print(message, file=sys.stderr, flush=True)


def run_gh(args):
    """Invoke gh with an argument array — never a shell string.

    Passing argv directly is what keeps this script usable inside a
    worktree-isolated session: there is no shell to quote for, no command
    substitution, and no heredoc for a command-shape guard to refuse.
    """
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=GH_TIMEOUT_S
        )
    except subprocess.TimeoutExpired as exc:
        raise GhError(f"gh timed out after {GH_TIMEOUT_S}s") from exc
    except FileNotFoundError as exc:
        raise GhError("gh not found on PATH") from exc

    if proc.returncode != 0 and not proc.stdout.strip():
        raise GhError(
            f"gh exited {proc.returncode}", stdout=proc.stdout, stderr=proc.stderr
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise GhError(
            "gh returned unparseable output", stdout=proc.stdout, stderr=proc.stderr
        ) from exc


def gh_graphql(query, str_vars=None, int_vars=None):
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in (str_vars or {}).items():
        args += ["-f", f"{key}={value}"]
    for key, value in (int_vars or {}).items():
        # -F for Int variables. A ":Int" type annotation here is rejected by gh;
        # it infers the type itself.
        args += ["-F", f"{key}={value}"]
    return run_gh(args)


def graphql_data(payload, what):
    if payload.get("errors") and not payload.get("data"):
        raise GhError(f"{what} returned errors: {payload['errors']}")
    data = payload.get("data") or {}
    if "repository" in data and data["repository"] is None:
        raise GhError(f"{what}: repository not found or not accessible")
    return data


def resolve_login():
    data = run_gh(["gh", "api", "user"])
    login = data.get("login")
    if not login:
        raise GhError("could not resolve authenticated login from `gh api user`")
    return login


def chunks(items, size):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def wait_for_abuse_block(abuse_waits):
    if abuse_waits >= MAX_ABUSE_WAITS:
        return abuse_waits
    abuse_waits += 1
    log(f"abuse block detected — waiting {ABUSE_WAIT_S}s (wait {abuse_waits})")
    time.sleep(ABUSE_WAIT_S)
    return abuse_waits


def record_send_error(errors, phase, exc, items, mark_request=False):
    abuse = exc.looks_like_abuse_block()
    entry = {
        "phase": phase,
        "items": items,
        "error": str(exc),
        "raw": (exc.stderr or exc.stdout)[:500],
        "abuse_block": abuse,
    }
    if mark_request:
        entry["request_failed"] = True
    errors.append(entry)
    return abuse


def record_alias_errors(errors, phase, payload, items):
    for err in payload.get("errors") or []:
        path = err.get("path") or []
        alias = path[0] if path else None
        item = None
        if isinstance(alias, str) and alias[1:].isdigit():
            index = int(alias[1:])
            if index < len(items):
                item = items[index]
        errors.append(
            {
                "phase": phase,
                "items": [item] if item is not None else items,
                "error": err.get("message", "unknown GraphQL error"),
                "raw": json.dumps(err)[:500],
                "abuse_block": False,
            }
        )


def fatal(message):
    print(json.dumps({"fatal": message}), flush=True)
    return 2


def read_json_file(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"cannot read input file: {exc}"


def require_keys(config, keys):
    for key in keys:
        if key not in config:
            return f"input file missing '{key}'"
    return None


# ---------------------------------------------------------------------------
# post
# ---------------------------------------------------------------------------

PENDING_REVIEW_QUERY = """
query($owner: String!, $repo: String!, $pr: Int!, $me: String!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      id
      url
      headRefOid
      reviews(first: 1, states: PENDING, author: $me) {
        nodes { id author { login } }
      }
    }
  }
}
"""

REVIEW_COMMENTS_QUERY = """
query($id: ID!, $after: String) {
  node(id: $id) {
    ... on PullRequestReview {
      state
      comments(first: %d, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes { path line body }
      }
    }
  }
}
""" % COMMENT_PAGE_SIZE

CREATE_REVIEW_MUTATION = """
mutation($prId: ID!) {
  addPullRequestReview(input: { pullRequestId: $prId }) { pullRequestReview { id } }
}
"""


def validate_post_config(config):
    missing = require_keys(config, ("owner", "repo", "pr", "comments"))
    if missing:
        return missing
    comments = config["comments"]
    if not isinstance(comments, list) or not comments:
        return "'comments' must be a non-empty array"
    for index, comment in enumerate(comments):
        if not isinstance(comment, dict):
            return f"comment {index} must be an object"
        if not isinstance(comment.get("path"), str) or not comment["path"]:
            return f"comment {index} needs a 'path'"
        if not isinstance(comment.get("body"), str) or not comment["body"].strip():
            return f"comment {index} needs a non-empty 'body'"
        line = comment.get("line")
        if line is not None and (not isinstance(line, int) or line < 1):
            return f"comment {index} 'line' must be a positive integer or null"
        side = comment.get("side", "RIGHT")
        if side not in SIDES:
            return f"comment {index} 'side' must be LEFT or RIGHT"
        if line is None and side == "LEFT":
            return f"comment {index} on side LEFT needs a 'line'"
        if line is None and not (comment.get("anchor") or "").strip():
            return f"comment {index} has no 'line' and no 'anchor' to resolve it"
    return None


def parse_hunk_lines(patch):
    """Return {"RIGHT": set, "LEFT": set} of line numbers a review thread may anchor to."""
    lines = {"RIGHT": set(), "LEFT": set()}
    old = new = None
    for raw in (patch or "").splitlines():
        header = HUNK_HEADER_RE.match(raw)
        if header:
            old, new = int(header.group(1)), int(header.group(2))
            continue
        if new is None or raw.startswith("\\"):
            continue
        if raw.startswith("+"):
            lines["RIGHT"].add(new)
            new += 1
        elif raw.startswith("-"):
            lines["LEFT"].add(old)
            old += 1
        else:
            lines["RIGHT"].add(new)
            lines["LEFT"].add(old)
            new += 1
            old += 1
    return lines


def nearest_line(target, candidates):
    if not candidates:
        return None
    return min(candidates, key=lambda n: (abs(n - target), n))


def resolve_anchor(line, anchor, file_lines):
    """Return (line, status) where status is ok | corrected | mismatch | not_found | unchecked."""
    anchor = (anchor or "").strip()
    if not anchor or file_lines is None:
        return line, "unchecked"
    if line is not None and 1 <= line <= len(file_lines):
        if file_lines[line - 1].strip() == anchor:
            return line, "ok"
    matches = [i + 1 for i, text in enumerate(file_lines) if text.strip() == anchor]
    if matches:
        best = nearest_line(line, matches) if line is not None else matches[0]
        return best, "corrected"
    if line is None:
        return None, "not_found"
    return line, "mismatch"


def reanchor_body(path, line, body):
    return (
        f"This concerns `{path}:{line}`, outside this PR's diff — anchored here for "
        f"visibility.\n\n{body}"
    )


def plan_post(comments, files, contents, existing):
    """Decide exactly what to post. Pure: no GitHub calls.

    files:    {path: patch or None} for every file the PR changed
    contents: {path: [lines] or None} at the PR head commit
    existing: [(path, line, body)] already on this identity's pending review
    """
    plan = {
        "to_post": [],
        "already_present": [],
        "input_duplicates": [],
        "reanchored": [],
        "anchor_corrected": [],
        "unpostable": [],
    }
    existing_keys = {(p, l, b) for p, l, b in existing}
    seen = set()

    for comment in comments:
        path = comment["path"]
        side = comment.get("side", "RIGHT")
        body = comment["body"]
        line = comment.get("line")

        if path not in files:
            plan["unpostable"].append(
                {"path": path, "line": line, "reason": "file not changed by this PR"}
            )
            continue

        if side == "RIGHT":
            resolved, status = resolve_anchor(line, comment.get("anchor"), contents.get(path))
            if status == "corrected":
                plan["anchor_corrected"].append(
                    {"path": path, "from_line": line, "line": resolved}
                )
            elif status in ("mismatch", "not_found"):
                plan["unpostable"].append(
                    {"path": path, "line": line, "reason": "anchor text not found at PR head"}
                )
                continue
            elif status == "unchecked" and line is None:
                plan["unpostable"].append(
                    {"path": path, "line": None, "reason": "no line and file content unavailable"}
                )
                continue
            line = resolved

        patch = files[path]
        if patch is None:
            plan["unpostable"].append(
                {"path": path, "line": line, "reason": "no diff hunk data (binary or too large)"}
            )
            continue

        allowed = parse_hunk_lines(patch)[side]
        if line not in allowed:
            target = nearest_line(line, allowed)
            if target is None:
                plan["unpostable"].append(
                    {"path": path, "line": line, "reason": f"no {side} diff lines in this file"}
                )
                continue
            plan["reanchored"].append({"path": path, "from_line": line, "line": target})
            body = reanchor_body(path, line, body)
            line = target

        key = (path, line, body)
        if key in seen:
            plan["input_duplicates"].append({"path": path, "line": line})
            continue
        seen.add(key)
        if key in existing_keys:
            plan["already_present"].append({"path": path, "line": line})
            continue
        plan["to_post"].append({"path": path, "line": line, "side": side, "body": body})

    return plan


def build_thread_mutation(count):
    params = ", ".join(
        f"$path{i}: String!, $line{i}: Int!, $side{i}: DiffSide!, $body{i}: String!"
        for i in range(count)
    )
    aliases = "\n    ".join(
        f"c{i}: addPullRequestReviewThread(input: {{ pullRequestReviewId: $reviewId, "
        f"path: $path{i}, line: $line{i}, side: $side{i}, body: $body{i} }}) "
        f"{{ thread {{ id }} }}"
        for i in range(count)
    )
    return f"mutation($reviewId: ID!, {params}) {{\n    {aliases}\n}}"


def count_by_path_body(comments):
    counts = {}
    for path, _, body in comments:
        counts[(path, body)] = counts.get((path, body), 0) + 1
    return counts


def reconcile_post(intended, before, after):
    """Compare what should exist against a fresh fetch.

    intended: [{"path", "body", ...}] this run tried to add
    before:   [(path, line, body)] on the review before this run
    after:    [(path, line, body)] on the review now
    """
    before_counts = count_by_path_body(before)
    after_counts = count_by_path_body(after)
    wanted = {}
    for item in intended:
        key = (item["path"], item["body"])
        wanted[key] = wanted.get(key, 0) + 1

    confirmed, missing, duplicates = 0, [], []
    for key, need in wanted.items():
        added = after_counts.get(key, 0) - before_counts.get(key, 0)
        confirmed += min(added, need)
        if added < need:
            missing.extend([{"path": key[0], "body": key[1]}] * (need - added))
        elif added > need:
            duplicates.append({"path": key[0], "body_prefix": key[1][:80], "extra": added - need})
    return confirmed, missing, duplicates


def fetch_pr_and_pending_review(owner, repo, pr, login):
    data = graphql_data(
        gh_graphql(
            PENDING_REVIEW_QUERY,
            str_vars={"owner": owner, "repo": repo, "me": login},
            int_vars={"pr": pr},
        ),
        "pull request fetch",
    )
    pull = data["repository"]["pullRequest"]
    if pull is None:
        raise GhError(f"PR #{pr} not found in {owner}/{repo}")
    review_id = None
    for node in pull["reviews"]["nodes"]:
        if ((node.get("author") or {}).get("login") or "") == login:
            review_id = node["id"]
    return pull, review_id


def fetch_review(review_id):
    """Return (state, [(path, line, body)]) for a review, paging every comment."""
    comments, cursor, state = [], None, None
    while True:
        str_vars = {"id": review_id}
        if cursor:
            str_vars["after"] = cursor
        node = graphql_data(gh_graphql(REVIEW_COMMENTS_QUERY, str_vars=str_vars), "review fetch")["node"]
        if node is None:
            return None, []
        state = node.get("state")
        page = node["comments"]
        comments.extend((c["path"], c.get("line"), c["body"]) for c in page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            return state, comments
        cursor = page["pageInfo"]["endCursor"]


def fetch_pr_files(owner, repo, pr):
    pages = run_gh(
        ["gh", "api", f"repos/{owner}/{repo}/pulls/{pr}/files", "--paginate", "--slurp"]
    )
    files = {}
    for page in pages:
        for entry in page:
            files[entry["filename"]] = entry.get("patch")
    return files


def fetch_file_lines(owner, repo, path, ref):
    try:
        quoted = urllib.parse.quote(path)
        data = run_gh(["gh", "api", f"repos/{owner}/{repo}/contents/{quoted}?ref={ref}"])
    except GhError:
        return None
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        return None
    try:
        return base64.b64decode(data.get("content", "")).decode("utf-8").splitlines()
    except (ValueError, UnicodeDecodeError):
        return None


def send_thread_batch(review_id, batch, errors):
    str_vars = {"reviewId": review_id}
    int_vars = {}
    for i, item in enumerate(batch):
        str_vars[f"path{i}"] = item["path"]
        str_vars[f"side{i}"] = item["side"]
        str_vars[f"body{i}"] = item["body"]
        int_vars[f"line{i}"] = item["line"]
    items = [f"{item['path']}:{item['line']}" for item in batch]
    try:
        payload = gh_graphql(build_thread_mutation(len(batch)), str_vars, int_vars)
    except GhError as exc:
        return record_send_error(errors, "post", exc, items, mark_request=True)
    record_alias_errors(errors, "post", payload, items)
    return False


def post_batches(review_id, items, batch_size, errors):
    abuse_waits = 0
    for index, batch in enumerate(chunks(items, batch_size)):
        if index:
            time.sleep(POST_BATCH_PACE_S)
        if send_thread_batch(review_id, batch, errors):
            abuse_waits = wait_for_abuse_block(abuse_waits)


def post(config, batch_size, dry_run):
    owner, repo, pr = config["owner"], config["repo"], int(config["pr"])
    login = resolve_login()
    log(f"authenticated as {login}")

    pull, review_id = fetch_pr_and_pending_review(owner, repo, pr, login)
    before = fetch_review(review_id)[1] if review_id else []
    files = fetch_pr_files(owner, repo, pr)

    contents = {}
    for comment in config["comments"]:
        path = comment["path"]
        if comment.get("side", "RIGHT") == "RIGHT" and path in files and path not in contents:
            contents[path] = fetch_file_lines(owner, repo, path, pull["headRefOid"])

    plan = plan_post(config["comments"], files, contents, before)
    log(
        f"plan: {len(plan['to_post'])} to post, {len(plan['already_present'])} already present, "
        f"{len(plan['reanchored'])} re-anchored, {len(plan['unpostable'])} unpostable"
    )

    summary = {
        "pr": pr,
        "repo": f"{owner}/{repo}",
        "identity": login,
        "pr_url": pull.get("url"),
        "intended": len(config["comments"]),
        "carried_over": len(before),
        "already_present": plan["already_present"],
        "input_duplicates": plan["input_duplicates"],
        "reanchored": plan["reanchored"],
        "anchor_corrected": plan["anchor_corrected"],
        "unpostable": plan["unpostable"],
    }

    if dry_run:
        summary.update({"dry_run": True, "would_post": len(plan["to_post"]),
                        "existing_pending_review": review_id})
        return summary, 0

    errors = []
    if plan["to_post"] and not review_id:
        try:
            created = graphql_data(
                gh_graphql(CREATE_REVIEW_MUTATION, str_vars={"prId": pull["id"]}),
                "review creation",
            )
            review_id = created["addPullRequestReview"]["pullRequestReview"]["id"]
        except (GhError, KeyError, TypeError) as exc:
            _, review_id = fetch_pr_and_pending_review(owner, repo, pr, login)
            if not review_id:
                raise GhError(f"could not create a pending review: {exc}") from exc

    if plan["to_post"]:
        log(f"posting {len(plan['to_post'])} threads to review {review_id}")
        post_batches(review_id, plan["to_post"], batch_size, errors)

        after = fetch_review(review_id)[1]
        _, missing, _ = reconcile_post(plan["to_post"], before, after)
        if missing:
            failed_requests = {item for err in errors if err.get("request_failed") for item in err["items"]}
            retry_keys = {(m["path"], m["body"]) for m in missing}
            retry = [
                i for i in plan["to_post"]
                if (i["path"], i["body"]) in retry_keys and f"{i['path']}:{i['line']}" in failed_requests
            ]
            if retry:
                log(f"re-fetch shows {len(missing)} missing — retrying the {len(retry)} from failed requests once")
                post_batches(review_id, retry, batch_size, errors)

    state, final = fetch_review(review_id) if review_id else (None, [])
    confirmed, missing, duplicates = reconcile_post(plan["to_post"], before, final)
    missing = [{"path": m["path"], "body_prefix": m["body"][:80]} for m in missing]

    summary.update(
        {
            "dry_run": False,
            "review_id": review_id,
            "review_state": state,
            "posted_confirmed": confirmed,
            "missing": missing,
            "duplicates_found": duplicates,
            "total_on_review": len(final),
            "errors": errors,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return summary, (0 if not missing and not duplicates else 1)


# ---------------------------------------------------------------------------
# submit
# ---------------------------------------------------------------------------

SUBMIT_MUTATION = """
mutation($reviewId: ID!) {
  submitPullRequestReview(input: { pullRequestReviewId: $reviewId, event: COMMENT }) {
    pullRequestReview { id state }
  }
}
"""


def submit(owner, repo, pr, dry_run):
    login = resolve_login()
    pull, review_id = fetch_pr_and_pending_review(owner, repo, pr, login)
    result = {"pr": pr, "repo": f"{owner}/{repo}", "identity": login, "pr_url": pull.get("url")}

    if not review_id:
        result.update({"submitted": False, "reason": "no pending review for this identity"})
        return result, 0
    if not fetch_review(review_id)[1]:
        result.update({"submitted": False, "review_id": review_id,
                       "reason": "pending review has no comments — left pending"})
        return result, 0
    if dry_run:
        result.update({"dry_run": True, "would_submit": review_id})
        return result, 0

    error = None
    try:
        payload = gh_graphql(SUBMIT_MUTATION, str_vars={"reviewId": review_id})
        if payload.get("errors"):
            error = {"error": "submit returned GraphQL errors", "raw": json.dumps(payload["errors"])[:500]}
    except GhError as exc:
        error = {"error": str(exc), "raw": (exc.stderr or exc.stdout)[:500]}

    state, comments = fetch_review(review_id)
    confirmed = state is not None and state != "PENDING"
    result.update(
        {
            "review_id": review_id,
            "submitted": confirmed,
            "state": state,
            "comments": len(comments),
            "error": error,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return result, (0 if confirmed else 1)


# ---------------------------------------------------------------------------
# deliver
# ---------------------------------------------------------------------------

FETCH_QUERY = """
query($owner: String!, $repo: String!, $pr: Int!, $after: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: %d, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          comments(first: %d) {
            nodes { id author { login } pullRequestReview { state } }
          }
        }
      }
    }
  }
}
""" % (THREAD_PAGE_SIZE, COMMENT_PAGE_SIZE)


def fetch_threads(owner, repo, pr):
    """Return {thread_id: {"resolved", "pending", "comments": [(id, author), ...]}}.

    `pending` marks a thread whose every comment belongs to an unsubmitted review —
    not this skill's to act on, and excluded from the coverage reconciliation so it
    cannot show up as an unaccounted thread.
    """
    threads = {}
    cursor = None
    truncated = False
    while True:
        str_vars = {"owner": owner, "repo": repo}
        if cursor:
            str_vars["after"] = cursor
        payload = gh_graphql(FETCH_QUERY, str_vars=str_vars, int_vars={"pr": pr})

        if "errors" in payload and payload["errors"]:
            raise GhError(f"thread fetch returned errors: {payload['errors']}")

        node = payload["data"]["repository"]["pullRequest"]["reviewThreads"]
        for thread in node["nodes"]:
            comments = thread.get("comments", {}).get("nodes", []) or []
            states = [
                ((c.get("pullRequestReview") or {}).get("state") or "")
                for c in comments
            ]
            threads[thread["id"]] = {
                "resolved": bool(thread.get("isResolved")),
                "pending": bool(states) and all(s == "PENDING" for s in states),
                "comments": [
                    (c["id"], ((c.get("author") or {}).get("login") or ""))
                    for c in comments
                ],
            }
            if len(comments) >= COMMENT_PAGE_SIZE:
                truncated = True

        page = node["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]

    return threads, truncated


def in_scope_threads(threads):
    """Thread ids this skill is responsible for: published and not already resolved."""
    return {
        tid
        for tid, entry in threads.items()
        if not entry["resolved"] and not entry["pending"]
    }


def build_reply_mutation(count):
    params = ", ".join(f"$thread{i}: ID!, $body{i}: String!" for i in range(count))
    aliases = "\n    ".join(
        f"r{i}: addPullRequestReviewThreadReply("
        f"input: {{ pullRequestReviewThreadId: $thread{i}, body: $body{i} }}"
        f") {{ comment {{ id }} }}"
        for i in range(count)
    )
    return f"mutation({params}) {{\n    {aliases}\n}}"


def build_resolve_mutation(count):
    params = ", ".join(f"$thread{i}: ID!" for i in range(count))
    aliases = "\n    ".join(
        f"r{i}: resolveReviewThread(input: {{ threadId: $thread{i} }}) "
        f"{{ thread {{ isResolved }} }}"
        for i in range(count)
    )
    return f"mutation({params}) {{\n    {aliases}\n}}"


def send_batch(kind, batch, errors):
    """Send one aliased batch. Records errors; never raises on a send failure.

    A failed-looking send is NOT treated as "nothing landed" — GitHub may have
    committed every mutation before the response was lost. The caller's next
    verification fetch is what decides what actually happened.
    """
    if kind == "reply":
        query = build_reply_mutation(len(batch))
        str_vars = {}
        for i, (thread_id, spec) in enumerate(batch):
            str_vars[f"thread{i}"] = thread_id
            str_vars[f"body{i}"] = spec["body"]
    else:
        query = build_resolve_mutation(len(batch))
        str_vars = {f"thread{i}": tid for i, (tid, _) in enumerate(batch)}

    try:
        payload = gh_graphql(query, str_vars=str_vars)
    except GhError as exc:
        abuse = exc.looks_like_abuse_block()
        errors.append(
            {
                "phase": kind,
                "threads": [tid for tid, _ in batch],
                "error": str(exc),
                "raw": (exc.stderr or exc.stdout)[:500],
                "abuse_block": abuse,
            }
        )
        return abuse

    for err in payload.get("errors") or []:
        path = err.get("path") or []
        alias = path[0] if path else None
        thread_id = None
        if isinstance(alias, str) and alias.startswith("r"):
            try:
                thread_id = batch[int(alias[1:])][0]
            except (ValueError, IndexError):
                thread_id = None
        errors.append(
            {
                "phase": kind,
                "threads": [thread_id] if thread_id else [tid for tid, _ in batch],
                "error": err.get("message", "unknown GraphQL error"),
                "raw": json.dumps(err)[:500],
                "abuse_block": False,
            }
        )
    return False


def new_comments_by(login, baseline_entry, current_entry):
    seen = {cid for cid, _ in (baseline_entry or {}).get("comments", [])}
    return [
        cid
        for cid, author in current_entry.get("comments", [])
        if cid not in seen and author == login
    ]


def validate_delivery_config(config):
    missing = require_keys(config, ("owner", "repo", "pr", "threads"))
    if missing:
        return missing
    if not isinstance(config["threads"], dict) or not config["threads"]:
        return "'threads' must be a non-empty object"
    for tid, spec in config["threads"].items():
        if not isinstance(spec, dict) or "body" not in spec:
            return f"thread {tid} needs a 'body'"
    skipped = config.get("skipped")
    if skipped is not None:
        if not isinstance(skipped, dict):
            return "'skipped' must be an object of id -> reason"
        for tid, reason in skipped.items():
            if not isinstance(reason, str) or not reason.strip():
                return f"skipped thread {tid} needs a non-empty reason"
        overlap = sorted(set(skipped) & set(config["threads"]))
        if overlap:
            return f"threads listed as both replied and skipped: {overlap}"
    return None


def deliver(config, batch_size, dry_run):
    owner = config["owner"]
    repo = config["repo"]
    pr = int(config["pr"])
    wanted = config["threads"]
    skipped = config.get("skipped") or {}

    login = resolve_login()
    log(f"authenticated as {login}")

    baseline, truncated = fetch_threads(owner, repo, pr)
    scope = in_scope_threads(baseline)
    log(f"baseline: {len(baseline)} threads fetched, {len(scope)} in scope")

    # Coverage reconciliation: every in-scope thread must be either replied to or
    # explicitly skipped with a reason. A thread in neither set is one this run
    # dropped without saying so — the failure that let 32 of 43 threads vanish from
    # a real run's report.
    unaccounted = sorted(scope - set(wanted) - set(skipped))
    if unaccounted:
        log(f"UNACCOUNTED: {len(unaccounted)} in-scope threads in neither list")

    unknown = [tid for tid in wanted if tid not in baseline]
    targets = [(tid, spec) for tid, spec in wanted.items() if tid in baseline]

    # A thread that already carries a reply from us is not re-replied to. This is
    # what makes a re-run after a partial failure safe rather than duplicating.
    already_replied = []
    to_reply = []
    for tid, spec in targets:
        if any(author == login for _, author in baseline[tid]["comments"][1:]):
            already_replied.append(tid)
        else:
            to_reply.append((tid, spec))

    if dry_run:
        return {
            "dry_run": True,
            "in_scope": len(scope),
            "would_reply": [tid for tid, _ in to_reply],
            "would_resolve": [
                tid for tid, spec in targets if spec.get("resolve")
            ],
            "already_replied": already_replied,
            "skipped_with_reason": skipped,
            "unaccounted": unaccounted,
            "unknown_threads": unknown,
        }, (1 if (unaccounted or unknown) else 0)

    errors = []
    abuse_waits = 0

    log(f"replying to {len(to_reply)} threads ({len(already_replied)} already had a reply)")
    for index, batch in enumerate(chunks(to_reply, batch_size)):
        if index:
            time.sleep(REPLY_BATCH_PACE_S)
        hit_abuse = send_batch("reply", batch, errors)
        if hit_abuse and abuse_waits < MAX_ABUSE_WAITS:
            abuse_waits += 1
            log(f"abuse block detected — waiting {ABUSE_WAIT_S}s (wait {abuse_waits})")
            time.sleep(ABUSE_WAIT_S)

    after_reply, _ = fetch_threads(owner, repo, pr)

    replied_confirmed, reply_missing, duplicates = [], [], []
    for tid, _ in targets:
        if tid in already_replied:
            replied_confirmed.append(tid)
            continue
        added = new_comments_by(login, baseline.get(tid), after_reply.get(tid, {}))
        if len(added) == 1:
            replied_confirmed.append(tid)
        elif len(added) == 0:
            reply_missing.append(tid)
        else:
            duplicates.append({"thread": tid, "comment_ids": added})

    log(
        f"verified: {len(replied_confirmed)} replied, "
        f"{len(reply_missing)} missing, {len(duplicates)} duplicated"
    )

    # Only threads whose reply is confirmed present are eligible to resolve — a
    # thread whose reply never landed stays open.
    to_resolve = [
        (tid, spec)
        for tid, spec in targets
        if spec.get("resolve")
        and tid in replied_confirmed
        and not after_reply.get(tid, {}).get("resolved")
    ]
    log(f"resolving {len(to_resolve)} threads")
    for index, batch in enumerate(chunks(to_resolve, batch_size)):
        if index:
            time.sleep(RESOLVE_BATCH_PACE_S)
        send_batch("resolve", batch, errors)

    final, _ = fetch_threads(owner, repo, pr)

    intended_resolve = [tid for tid, spec in targets if spec.get("resolve")]
    resolved_confirmed = [
        tid for tid in intended_resolve if final.get(tid, {}).get("resolved")
    ]
    resolve_not_confirmed = [
        tid for tid in intended_resolve if not final.get(tid, {}).get("resolved")
    ]

    result = {
        "dry_run": False,
        "pr": pr,
        "repo": f"{owner}/{repo}",
        "identity": login,
        "in_scope": len(scope),
        "attempted": len(wanted),
        "replied_confirmed": len(replied_confirmed),
        "resolved_confirmed": len(resolved_confirmed),
        "intended_resolve": len(intended_resolve),
        "skipped_with_reason": skipped,
        "unaccounted": unaccounted,
        "reply_missing": reply_missing,
        "resolve_not_confirmed": resolve_not_confirmed,
        "duplicates_found": duplicates,
        "unknown_threads": unknown,
        "thread_page_truncated": truncated,
        "errors": errors,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }

    clean = (
        not reply_missing
        and not resolve_not_confirmed
        and not duplicates
        and not unknown
        and not unaccounted
    )
    return result, (0 if clean else 1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        description="Deterministic GitHub writes for the code-review skill."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    post_cmd = sub.add_parser("post", help="add findings to this identity's pending review")
    post_cmd.add_argument("input_file", help="path to post.json")
    post_cmd.add_argument("--dry-run", action="store_true", help="plan only, write nothing")
    post_cmd.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)

    submit_cmd = sub.add_parser("submit", help="submit this identity's pending review as COMMENT")
    submit_cmd.add_argument("owner")
    submit_cmd.add_argument("repo")
    submit_cmd.add_argument("pr", type=int)
    submit_cmd.add_argument("--dry-run", action="store_true", help="report only, write nothing")

    deliver_cmd = sub.add_parser("deliver", help="reply to and resolve review threads")
    deliver_cmd.add_argument("input_file", help="path to delivery.json")
    deliver_cmd.add_argument("--dry-run", action="store_true", help="plan only, write nothing")
    deliver_cmd.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if getattr(args, "batch_size", DEFAULT_BATCH_SIZE) < 1:
        return fatal("--batch-size must be at least 1")

    if args.command == "submit":
        runner = lambda: submit(args.owner, args.repo, args.pr, args.dry_run)
    else:
        config, error = read_json_file(args.input_file)
        if error:
            return fatal(error)
        validator = validate_post_config if args.command == "post" else validate_delivery_config
        error = validator(config)
        if error:
            return fatal(error)
        action = post if args.command == "post" else deliver
        runner = lambda: action(config, args.batch_size, args.dry_run)

    try:
        result, code = runner()
    except GhError as exc:
        print(
            json.dumps(
                {
                    "fatal": str(exc),
                    "raw": (exc.stderr or exc.stdout)[:1000],
                    "hint": "nothing was confirmed — report this run blocked",
                }
            ),
            flush=True,
        )
        return 2

    print(json.dumps(result, indent=2), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
