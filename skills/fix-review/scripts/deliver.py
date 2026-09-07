#!/usr/bin/env python3
"""Deterministic GitHub review-thread delivery for the `fix-review` skill.

Takes an already-decided set of `{thread_id: {body, resolve}}` and delivers it:

    fetch baseline -> reply (batched) -> verify -> resolve (batched) -> verify

Every number this script reports comes from re-fetching GitHub's own state, never
from what it sent. It exits non-zero when any intended outcome is unconfirmed, so
a caller cannot mistake "sent" for "landed" — the failure mode this script exists
to make impossible (see skills/fix-review/STATE.md AD-001, AD-006).

Usage:
    python3 deliver.py <delivery.json> [--dry-run] [--batch-size N]

Input JSON:
    {
      "owner": "octocat",
      "repo": "hello-world",
      "pr": 42,
      "threads": {
        "PRRT_kwDOxxx": {"body": "reply text", "resolve": true},
        "PRRT_kwDOyyy": {"body": "reply text", "resolve": false}
      },
      "skipped": {
        "PRRT_kwDOzzz": "routed to @alice — awaiting her answer",
        "PRRT_kwDOwww": "unclear which of two approaches was meant"
      }
    }

`threads` and `skipped` together must account for every in-scope thread on the PR
(published, not already resolved). Any in-scope thread in neither list is reported
as `unaccounted` and exits non-zero — this is the coverage check, and it is the
reason a run cannot quietly drop threads from its own report.

Output JSON goes to stdout; human-readable progress goes to stderr.

Exit codes:
    0  every in-scope thread accounted for, every intended reply and resolve
       confirmed present on GitHub
    1  partial — an intended outcome is unconfirmed, or a thread went unaccounted
    2  fatal — bad input, or GitHub unreachable
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

DEFAULT_BATCH_SIZE = 10
REPLY_BATCH_PACE_S = 5.0
RESOLVE_BATCH_PACE_S = 1.0
ABUSE_WAIT_S = 180
MAX_ABUSE_WAITS = 2
GH_TIMEOUT_S = 120
THREAD_PAGE_SIZE = 100
COMMENT_PAGE_SIZE = 100

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


def resolve_login():
    data = run_gh(["gh", "api", "user"])
    login = data.get("login")
    if not login:
        raise GhError("could not resolve authenticated login from `gh api user`")
    return login


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


def chunks(items, size):
    for start in range(0, len(items), size):
        yield items[start : start + size]


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("delivery_file", help="path to the delivery JSON")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be sent without writing to GitHub",
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()

    try:
        with open(args.delivery_file, encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"fatal": f"cannot read delivery file: {exc}"}), flush=True)
        return 2

    for key in ("owner", "repo", "pr", "threads"):
        if key not in config:
            print(json.dumps({"fatal": f"delivery file missing '{key}'"}), flush=True)
            return 2
    if not isinstance(config["threads"], dict) or not config["threads"]:
        print(json.dumps({"fatal": "'threads' must be a non-empty object"}), flush=True)
        return 2
    for tid, spec in config["threads"].items():
        if not isinstance(spec, dict) or "body" not in spec:
            print(
                json.dumps({"fatal": f"thread {tid} needs a 'body'"}), flush=True
            )
            return 2
    skipped = config.get("skipped")
    if skipped is not None:
        if not isinstance(skipped, dict):
            print(
                json.dumps({"fatal": "'skipped' must be an object of id -> reason"}),
                flush=True,
            )
            return 2
        for tid, reason in skipped.items():
            if not isinstance(reason, str) or not reason.strip():
                print(
                    json.dumps(
                        {"fatal": f"skipped thread {tid} needs a non-empty reason"}
                    ),
                    flush=True,
                )
                return 2
        overlap = sorted(set(skipped) & set(config["threads"]))
        if overlap:
            print(
                json.dumps(
                    {"fatal": f"threads listed as both replied and skipped: {overlap}"}
                ),
                flush=True,
            )
            return 2

    try:
        result, code = deliver(config, args.batch_size, args.dry_run)
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
