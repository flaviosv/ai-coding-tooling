#!/usr/bin/env python3
"""Deterministic Azure DevOps reads and writes for the `code-review` skill.

Azure DevOps Services only (dev.azure.com), REST api-version 7.1.

    pr          <org> <project> <repo> <pr>     PR metadata and changed files
    threads     <org> <project> <repo> <pr>     in-scope comment threads, every comment in order
    candidates  <org> <project> <repo> <sweep>  active PRs for a batch sweep (review | fix)
    post        <post.json>                     one thread per finding -> reconcile by re-fetch
    deliver     <delivery.json>                 replies and status changes -> confirm each by re-fetch

Azure DevOps has no pending review: a thread is public the moment it is created.
So `post` is the publish step, and nothing here submits or votes.

Every count this script reports comes from re-fetching Azure DevOps' own state,
never from what it sent, exactly as github_review.py does for GitHub; anchor
resolution and post reconciliation are shared with it.

post.json:
    {"org": "fabrikam", "project": "Fiber", "repo": "web", "pr": 42,
     "comments": [{"path": "src/a.py", "line": 18, "body": "**[Security — S1, High]** ...",
                   "anchor": "exact text of line 18"}]}

    `line` may be null when `anchor` is set. Paths are repo-relative. A comment on a
    file the PR did not change, or on a deleted file, is unpostable. Azure DevOps
    accepts a thread on any line of a changed file, so nothing is re-anchored.

delivery.json:
    {"org": "fabrikam", "project": "Fiber", "repo": "web", "pr": 42,
     "threads": {"17": {"body": "reply text", "resolve": "fixed"}},
     "skipped": {"18": "routed to Alice — awaiting her answer"}}

    `resolve` is a thread status (fixed | wontFix | closed | byDesign) or false to
    leave the thread active. `threads` and `skipped` together must account for every
    in-scope thread (text threads whose status is active or pending).

Auth: an Entra token from `az account get-access-token` (after `az login`), else a
PAT in AZURE_DEVOPS_EXT_PAT. Tokens are never printed.

Output JSON goes to stdout; progress goes to stderr.

Exit codes:
    0  every intended outcome confirmed
    1  partial — an intended outcome is unconfirmed, or a thread went unaccounted
    2  fatal — bad input, no credentials, or Azure DevOps unreachable
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from github_review import (
    fatal,
    read_json_file,
    reconcile_post,
    require_keys,
    resolve_anchor,
)

API_VERSION = "7.1"
CONNECTION_DATA_API_VERSION = "7.1-preview"
ADO_RESOURCE_ID = "499b84ac-1321-427f-aa17-267ca6975798"
PAT_ENV = "AZURE_DEVOPS_EXT_PAT"
HTTP_TIMEOUT_S = 60
MAX_THROTTLE_WAITS = 2
MAX_THROTTLE_WAIT_S = 300
POST_PACE_S = 1.0
REPLY_PACE_S = 1.0
RESOLVE_PACE_S = 0.5
PR_PAGE_SIZE = 100
CHANGES_PAGE_SIZE = 2000
REPLY_MARKER = "<!-- code-review:deliver -->"
RESOLVE_STATUSES = ("fixed", "wontFix", "closed", "byDesign")
OPEN_STATUSES = ("active", "pending")
CHANGES_REQUESTED_VOTES = (-5, -10)


class AdoError(RuntimeError):
    def __init__(self, message, status=None, body=""):
        super().__init__(message)
        self.status = status
        self.body = body


def log(message):
    print(message, file=sys.stderr, flush=True)


def quote(segment):
    return urllib.parse.quote(str(segment), safe="")


def auth_header():
    try:
        proc = subprocess.run(
            ["az", "account", "get-access-token", "--resource", ADO_RESOURCE_ID,
             "--query", "accessToken", "-o", "tsv"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return f"Bearer {proc.stdout.strip()}"
    except (OSError, subprocess.TimeoutExpired):
        pass
    pat = os.environ.get(PAT_ENV, "").strip()
    if pat:
        return "Basic " + base64.b64encode(f":{pat}".encode()).decode()
    raise AdoError(f"no Azure DevOps credentials — run `az login`, or set {PAT_ENV}")


class Ado:
    """One PR's repository, reached with one credential for the whole run."""

    def __init__(self, org, project, repo, auth=None):
        self.org, self.project, self.repo = org, project, repo
        self.auth = auth or auth_header()
        self.throttle_waits = 0
        self.repo_base = (
            f"https://dev.azure.com/{quote(org)}/{quote(project)}"
            f"/_apis/git/repositories/{quote(repo)}"
        )

    def pr_web_url(self, pr):
        return (
            f"https://dev.azure.com/{quote(self.org)}/{quote(self.project)}"
            f"/_git/{quote(self.repo)}/pullrequest/{pr}"
        )

    def request(self, method, url, body=None, params=None, api_version=API_VERSION):
        query = dict(params or {})
        query["api-version"] = api_version
        full = f"{url}?{urllib.parse.urlencode(query)}"
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": self.auth, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        while True:
            req = urllib.request.Request(full, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
                    status, raw = resp.status, resp.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", "replace")
                if exc.code in (429, 503) and self.throttle_waits < MAX_THROTTLE_WAITS:
                    self.wait_for_throttle(exc.headers.get("Retry-After"))
                    continue
                raise AdoError(f"{method} {url} -> HTTP {exc.code}", exc.code, raw[:500]) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                raise AdoError(f"{method} {url} failed: {exc}") from exc
            try:
                return json.loads(raw) if raw else {}
            except json.JSONDecodeError as exc:
                # A rejected credential comes back as 203 with an HTML sign-in page.
                raise AdoError(
                    f"{method} {url} -> HTTP {status} with a non-JSON body — check credentials",
                    status, raw[:200],
                ) from exc

    def wait_for_throttle(self, retry_after):
        self.throttle_waits += 1
        try:
            wait = min(max(int(retry_after), 1), MAX_THROTTLE_WAIT_S)
        except (TypeError, ValueError):
            wait = 60
        log(f"throttled — waiting {wait}s (wait {self.throttle_waits})")
        time.sleep(wait)

    def identity(self):
        data = self.request(
            "GET", f"https://dev.azure.com/{quote(self.org)}/_apis/connectionData",
            api_version=CONNECTION_DATA_API_VERSION,
        )
        user = data.get("authenticatedUser") or {}
        if not user.get("id"):
            raise AdoError("could not resolve the authenticated identity")
        return {"id": user["id"], "name": user.get("providerDisplayName") or ""}

    def pull_request(self, pr):
        return self.request("GET", f"{self.repo_base}/pullRequests/{pr}")

    def latest_iteration(self, pr):
        iterations = self.request("GET", f"{self.repo_base}/pullRequests/{pr}/iterations").get("value") or []
        if not iterations:
            raise AdoError(f"PR {pr} has no iterations")
        return max(it["id"] for it in iterations)

    def changes(self, pr, iteration):
        """Return {repo-relative path: {"tracking_id", "change_type"}} against the merge base."""
        result, skip = {}, 0
        while True:
            page = self.request(
                "GET", f"{self.repo_base}/pullRequests/{pr}/iterations/{iteration}/changes",
                params={"$top": CHANGES_PAGE_SIZE, "$skip": skip},
            )
            for entry in page.get("changeEntries") or []:
                path = ((entry.get("item") or {}).get("path") or "").lstrip("/")
                if path:
                    result[path] = {
                        "tracking_id": entry.get("changeTrackingId"),
                        "change_type": entry.get("changeType") or "",
                    }
            skip = page.get("nextSkip") or 0
            if not skip:
                return result

    def file_lines(self, path, commit):
        try:
            item = self.request(
                "GET", f"{self.repo_base}/items",
                params={
                    "path": "/" + path,
                    "versionDescriptor.version": commit,
                    "versionDescriptor.versionType": "commit",
                    "includeContent": "true",
                },
            )
        except AdoError:
            return None
        if (item.get("contentMetadata") or {}).get("isBinary"):
            return None
        content = item.get("content")
        return content.splitlines() if isinstance(content, str) else None

    def threads(self, pr):
        return self.request("GET", f"{self.repo_base}/pullRequests/{pr}/threads").get("value") or []

    def create_thread(self, pr, body):
        return self.request("POST", f"{self.repo_base}/pullRequests/{pr}/threads", body=body)

    def reply(self, pr, thread_id, parent_id, content):
        return self.request(
            "POST", f"{self.repo_base}/pullRequests/{pr}/threads/{thread_id}/comments",
            body={"content": content, "parentCommentId": parent_id, "commentType": 1},
        )

    def set_status(self, pr, thread_id, status):
        return self.request(
            "PATCH", f"{self.repo_base}/pullRequests/{pr}/threads/{thread_id}",
            body={"status": status},
        )

    def repository_id(self):
        return self.request("GET", self.repo_base)["id"]

    def active_prs_for_reviewer(self, reviewer_id):
        base = f"https://dev.azure.com/{quote(self.org)}/{quote(self.project)}/_apis/git/pullrequests"
        repo_id = self.repository_id()
        prs, skip = [], 0
        while True:
            page = self.request("GET", base, params={
                "searchCriteria.reviewerId": reviewer_id,
                "searchCriteria.repositoryId": repo_id,
                "searchCriteria.status": "active",
                "$top": PR_PAGE_SIZE,
                "$skip": skip,
            }).get("value") or []
            prs.extend(page)
            if len(page) < PR_PAGE_SIZE:
                return prs
            skip += PR_PAGE_SIZE


# ---------------------------------------------------------------------------
# Thread shape
# ---------------------------------------------------------------------------


def text_comments(thread):
    return [c for c in thread.get("comments") or [] if not c.get("isDeleted")]


def is_text_thread(thread):
    comments = text_comments(thread)
    return (
        not thread.get("isDeleted")
        and bool(comments)
        and (comments[0].get("commentType") or "text") == "text"
    )


def thread_path(thread):
    return ((thread.get("threadContext") or {}).get("filePath") or "").lstrip("/")


def thread_line(thread):
    start = (thread.get("threadContext") or {}).get("rightFileStart") or {}
    return start.get("line")


def summarize_thread(thread):
    return {
        "id": thread["id"],
        "status": thread.get("status"),
        "path": thread_path(thread) or None,
        "line": thread_line(thread),
        "comments": [
            {
                "id": c.get("id"),
                "author_id": (c.get("author") or {}).get("id"),
                "author": (c.get("author") or {}).get("displayName") or "",
                "body": c.get("content") or "",
            }
            for c in text_comments(thread)
        ],
    }


def in_scope(threads):
    """Text threads that still ask for something: active or pending, not deleted."""
    return {
        str(t["id"]): t
        for t in threads
        if is_text_thread(t) and t.get("status") in OPEN_STATUSES
    }


def my_thread_keys(threads, me):
    """[(path, line, body)] for every thread this identity opened."""
    keys = []
    for thread in threads:
        comments = text_comments(thread)
        if is_text_thread(thread) and (comments[0].get("author") or {}).get("id") == me:
            keys.append((thread_path(thread), thread_line(thread), comments[0].get("content") or ""))
    return keys


# ---------------------------------------------------------------------------
# pr / threads / candidates
# ---------------------------------------------------------------------------


def pr_info(ado, pr):
    data = ado.pull_request(pr)
    iteration = ado.latest_iteration(pr)
    changes = ado.changes(pr, iteration)
    return {
        "pr": pr,
        "pr_url": ado.pr_web_url(pr),
        "title": data.get("title") or "",
        "description": data.get("description") or "",
        "status": data.get("status"),
        "is_draft": bool(data.get("isDraft")),
        "source_ref": data.get("sourceRefName"),
        "source_branch": (data.get("sourceRefName") or "").removeprefix("refs/heads/"),
        "target_ref": data.get("targetRefName"),
        "target_branch": (data.get("targetRefName") or "").removeprefix("refs/heads/"),
        "source_commit": (data.get("lastMergeSourceCommit") or {}).get("commitId"),
        "target_commit": (data.get("lastMergeTargetCommit") or {}).get("commitId"),
        "iteration": iteration,
        "files": [{"path": p, "change_type": c["change_type"]} for p, c in sorted(changes.items())],
    }, 0


def threads_info(ado, pr):
    me = ado.identity()
    scope = in_scope(ado.threads(pr))
    return {
        "pr": pr,
        "pr_url": ado.pr_web_url(pr),
        "identity": me,
        "in_scope": len(scope),
        "threads": [summarize_thread(t) for t in scope.values()],
    }, 0


def candidates(ado, sweep):
    me = ado.identity()
    result = []
    for pr in ado.active_prs_for_reviewer(me["id"]):
        mine = next((r for r in pr.get("reviewers") or [] if r.get("id") == me["id"]), None)
        vote = (mine or {}).get("vote", 0)
        number = pr["pullRequestId"]
        if sweep == "fix":
            if vote not in CHANGES_REQUESTED_VOTES:
                continue
        elif vote != 0 or my_thread_keys(ado.threads(number), me["id"]):
            continue
        result.append({"pr": number, "title": pr.get("title") or "", "url": ado.pr_web_url(number), "vote": vote})
    return {"sweep": sweep, "identity": me, "candidates": result}, 0


# ---------------------------------------------------------------------------
# post
# ---------------------------------------------------------------------------


def validate_post_config(config):
    missing = require_keys(config, ("org", "project", "repo", "pr", "comments"))
    if missing:
        return missing
    comments = config["comments"]
    if not isinstance(comments, list) or not comments:
        return "'comments' must be a non-empty array"
    for index, comment in enumerate(comments):
        if not isinstance(comment, dict):
            return f"comment {index} must be an object"
        if not isinstance(comment.get("path"), str) or not comment["path"].strip("/"):
            return f"comment {index} needs a 'path'"
        if not isinstance(comment.get("body"), str) or not comment["body"].strip():
            return f"comment {index} needs a non-empty 'body'"
        line = comment.get("line")
        if line is not None and (not isinstance(line, int) or line < 1):
            return f"comment {index} 'line' must be a positive integer or null"
        if line is None and not (comment.get("anchor") or "").strip():
            return f"comment {index} has no 'line' and no 'anchor' to resolve it"
    return None


def plan_post(comments, changes, contents, existing):
    """Decide exactly what to post. Pure: no Azure DevOps calls.

    changes:  {path: {"tracking_id", "change_type"}} for every file the PR changed
    contents: {path: [lines] or None} at the PR source commit
    existing: [(path, line, body)] threads this identity already opened on the PR
    """
    plan = {
        "to_post": [],
        "already_present": [],
        "input_duplicates": [],
        "anchor_corrected": [],
        "anchor_unverified": [],
        "unpostable": [],
    }
    existing_keys = set(existing)
    seen = set()

    for comment in comments:
        path = comment["path"].lstrip("/")
        body = comment["body"]
        line = comment.get("line")
        change = changes.get(path)

        if change is None:
            plan["unpostable"].append({"path": path, "line": line, "reason": "file not changed by this PR"})
            continue
        if "delete" in change["change_type"]:
            plan["unpostable"].append({"path": path, "line": line, "reason": "file deleted by this PR"})
            continue

        file_lines = contents.get(path)
        resolved, status = resolve_anchor(line, comment.get("anchor"), file_lines)
        if status == "corrected":
            plan["anchor_corrected"].append({"path": path, "from_line": line, "line": resolved})
        elif status == "mismatch":
            plan["anchor_unverified"].append({"path": path, "line": line})
        elif status == "not_found":
            plan["unpostable"].append({"path": path, "line": None, "reason": "anchor text not found at PR head"})
            continue
        elif status == "unchecked" and line is None:
            plan["unpostable"].append({"path": path, "line": None, "reason": "no line and file content unavailable"})
            continue
        line = resolved

        key = (path, line, body)
        if key in seen:
            plan["input_duplicates"].append({"path": path, "line": line})
            continue
        seen.add(key)
        if key in existing_keys:
            plan["already_present"].append({"path": path, "line": line})
            continue
        width = len(file_lines[line - 1]) if file_lines and line <= len(file_lines) else 0
        plan["to_post"].append({
            "path": path, "line": line, "body": body,
            "tracking_id": change["tracking_id"], "end_offset": width + 1,
        })

    return plan


def thread_payload(item, iteration):
    return {
        "comments": [{"parentCommentId": 0, "content": item["body"], "commentType": 1}],
        "status": "active",
        "threadContext": {
            "filePath": "/" + item["path"],
            "rightFileStart": {"line": item["line"], "offset": 1},
            "rightFileEnd": {"line": item["line"], "offset": item["end_offset"]},
        },
        "pullRequestThreadContext": {
            "changeTrackingId": item["tracking_id"],
            "iterationContext": {"firstComparingIteration": 1, "secondComparingIteration": iteration},
        },
    }


def send_threads(ado, pr, items, iteration, errors):
    """Create each thread; return the `path:line` of every request that failed."""
    failed = set()
    for index, item in enumerate(items):
        if index:
            time.sleep(POST_PACE_S)
        try:
            ado.create_thread(pr, thread_payload(item, iteration))
        except AdoError as exc:
            where = f"{item['path']}:{item['line']}"
            failed.add(where)
            errors.append({"phase": "post", "items": [where], "error": str(exc), "raw": exc.body, "request_failed": True})
    return failed


def post(ado, config, dry_run):
    pr = int(config["pr"])
    me = ado.identity()
    log(f"authenticated as {me['name'] or me['id']}")

    data = ado.pull_request(pr)
    commit = (data.get("lastMergeSourceCommit") or {}).get("commitId")
    iteration = ado.latest_iteration(pr)
    changes = ado.changes(pr, iteration)
    before = my_thread_keys(ado.threads(pr), me["id"])

    contents = {}
    for comment in config["comments"]:
        path = comment["path"].lstrip("/")
        if path in changes and path not in contents:
            contents[path] = ado.file_lines(path, commit) if commit else None

    plan = plan_post(config["comments"], changes, contents, before)
    log(f"plan: {len(plan['to_post'])} to post, {len(plan['already_present'])} already present, "
        f"{len(plan['unpostable'])} unpostable")

    summary = {
        "pr": pr,
        "repo": f"{ado.org}/{ado.project}/{ado.repo}",
        "identity": me["name"] or me["id"],
        "pr_url": ado.pr_web_url(pr),
        "intended": len(config["comments"]),
        "already_present": plan["already_present"],
        "input_duplicates": plan["input_duplicates"],
        "anchor_corrected": plan["anchor_corrected"],
        "anchor_unverified": plan["anchor_unverified"],
        "unpostable": plan["unpostable"],
    }
    if dry_run:
        summary.update({"dry_run": True, "would_post": len(plan["to_post"])})
        return summary, 0

    errors = []
    if plan["to_post"]:
        log(f"posting {len(plan['to_post'])} threads")
        failed = send_threads(ado, pr, plan["to_post"], iteration, errors)
        _, missing, _ = reconcile_post(plan["to_post"], before, my_thread_keys(ado.threads(pr), me["id"]))
        if missing and failed:
            retry_keys = {(m["path"], m["body"]) for m in missing}
            retry = [i for i in plan["to_post"]
                     if (i["path"], i["body"]) in retry_keys and f"{i['path']}:{i['line']}" in failed]
            if retry:
                log(f"re-fetch shows {len(missing)} missing — retrying the {len(retry)} from failed requests once")
                send_threads(ado, pr, retry, iteration, errors)

    final = my_thread_keys(ado.threads(pr), me["id"])
    confirmed, missing, duplicates = reconcile_post(plan["to_post"], before, final)
    summary.update({
        "dry_run": False,
        "posted_confirmed": confirmed,
        "missing": [{"path": m["path"], "body_prefix": m["body"][:80]} for m in missing],
        "duplicates_found": duplicates,
        "errors": errors,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    })
    return summary, (0 if not missing and not duplicates else 1)


# ---------------------------------------------------------------------------
# deliver
# ---------------------------------------------------------------------------


def validate_delivery_config(config):
    missing = require_keys(config, ("org", "project", "repo", "pr", "threads"))
    if missing:
        return missing
    if not isinstance(config["threads"], dict):
        return "'threads' must be an object"
    if not config["threads"] and not config.get("skipped"):
        return "'threads' and 'skipped' cannot both be empty"
    for tid, spec in config["threads"].items():
        if not isinstance(spec, dict) or not isinstance(spec.get("body"), str) or not spec["body"].strip():
            return f"thread {tid} needs a non-empty 'body'"
        resolve = spec.get("resolve", False)
        if resolve is not False and resolve not in RESOLVE_STATUSES:
            return f"thread {tid} 'resolve' must be false or one of {list(RESOLVE_STATUSES)}"
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


def marked_body(body):
    return body if REPLY_MARKER in body else f"{body.rstrip()}\n\n{REPLY_MARKER}"


def delivered_replies(thread, me):
    """Ids of marked replies from this identity — never the thread's opening comment."""
    return [
        c.get("id")
        for c in text_comments(thread)[1:]
        if (c.get("author") or {}).get("id") == me and REPLY_MARKER in (c.get("content") or "")
    ]


def deliver(ado, config, dry_run):
    pr = int(config["pr"])
    wanted = {str(k): v for k, v in config["threads"].items()}
    skipped = {str(k): v for k, v in (config.get("skipped") or {}).items()}

    me = ado.identity()
    log(f"authenticated as {me['name'] or me['id']}")

    baseline = {str(t["id"]): t for t in ado.threads(pr)}
    scope = in_scope(baseline.values())
    unaccounted = sorted(set(scope) - set(wanted) - set(skipped), key=int)
    unknown = [tid for tid in wanted if tid not in baseline]
    targets = [(tid, spec) for tid, spec in wanted.items() if tid in baseline]

    already_replied = [tid for tid, _ in targets if delivered_replies(baseline[tid], me["id"])]
    to_reply = [(tid, spec) for tid, spec in targets if tid not in already_replied]

    if dry_run:
        return {
            "dry_run": True,
            "in_scope": len(scope),
            "would_reply": [tid for tid, _ in to_reply],
            "would_resolve": {tid: spec["resolve"] for tid, spec in targets if spec.get("resolve")},
            "already_replied": already_replied,
            "skipped_with_reason": skipped,
            "unaccounted": unaccounted,
            "unknown_threads": unknown,
        }, (1 if (unaccounted or unknown) else 0)

    errors = []
    log(f"replying to {len(to_reply)} threads ({len(already_replied)} already had a reply)")
    for index, (tid, spec) in enumerate(to_reply):
        if index:
            time.sleep(REPLY_PACE_S)
        parent = text_comments(baseline[tid])[0].get("id")
        try:
            ado.reply(pr, tid, parent, marked_body(spec["body"]))
        except AdoError as exc:
            errors.append({"phase": "reply", "threads": [tid], "error": str(exc), "raw": exc.body})

    after_reply = {str(t["id"]): t for t in ado.threads(pr)}
    replied_confirmed, reply_missing, duplicates = [], [], []
    for tid, _ in targets:
        if tid in already_replied:
            replied_confirmed.append(tid)
            continue
        earlier = set(delivered_replies(baseline[tid], me["id"]))
        added = [cid for cid in delivered_replies(after_reply.get(tid, {}), me["id"]) if cid not in earlier]
        if len(added) == 1:
            replied_confirmed.append(tid)
        elif not added:
            reply_missing.append(tid)
        else:
            duplicates.append({"thread": tid, "comment_ids": added})

    to_resolve = [
        (tid, spec["resolve"]) for tid, spec in targets
        if spec.get("resolve") and tid in replied_confirmed
        and after_reply.get(tid, {}).get("status") != spec["resolve"]
    ]
    log(f"setting status on {len(to_resolve)} threads")
    for index, (tid, status) in enumerate(to_resolve):
        if index:
            time.sleep(RESOLVE_PACE_S)
        try:
            ado.set_status(pr, tid, status)
        except AdoError as exc:
            errors.append({"phase": "resolve", "threads": [tid], "error": str(exc), "raw": exc.body})

    final = {str(t["id"]): t for t in ado.threads(pr)}
    intended_resolve = {tid: spec["resolve"] for tid, spec in targets if spec.get("resolve")}
    resolved_confirmed = [tid for tid, status in intended_resolve.items() if final.get(tid, {}).get("status") == status]
    resolve_not_confirmed = [tid for tid in intended_resolve if tid not in resolved_confirmed]

    result = {
        "dry_run": False,
        "pr": pr,
        "repo": f"{ado.org}/{ado.project}/{ado.repo}",
        "identity": me["name"] or me["id"],
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
        "errors": errors,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    clean = not (reply_missing or resolve_not_confirmed or duplicates or unknown or unaccounted)
    return result, (0 if clean else 1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(description="Deterministic Azure DevOps reads and writes for code-review.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("pr", "PR metadata and changed files"), ("threads", "in-scope comment threads")):
        cmd = sub.add_parser(name, help=help_text)
        for arg in ("org", "project", "repo"):
            cmd.add_argument(arg)
        cmd.add_argument("pr", type=int)
    cand = sub.add_parser("candidates", help="active PRs for a batch sweep")
    for arg in ("org", "project", "repo"):
        cand.add_argument(arg)
    cand.add_argument("sweep", choices=("review", "fix"))
    for name, help_text in (("post", "one thread per finding"), ("deliver", "reply to and resolve threads")):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("input_file")
        cmd.add_argument("--dry-run", action="store_true", help="plan only, write nothing")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.command in ("post", "deliver"):
        config, error = read_json_file(args.input_file)
        if error:
            return fatal(error)
        validator = validate_post_config if args.command == "post" else validate_delivery_config
        error = validator(config)
        if error:
            return fatal(error)
        coords = (config["org"], config["project"], config["repo"])
    else:
        coords = (args.org, args.project, args.repo)

    try:
        ado = Ado(*coords)
        if args.command == "pr":
            result, code = pr_info(ado, args.pr)
        elif args.command == "threads":
            result, code = threads_info(ado, args.pr)
        elif args.command == "candidates":
            result, code = candidates(ado, args.sweep)
        elif args.command == "post":
            result, code = post(ado, config, args.dry_run)
        else:
            result, code = deliver(ado, config, args.dry_run)
    except AdoError as exc:
        print(json.dumps({"fatal": str(exc), "status": exc.status, "raw": exc.body[:1000],
                          "hint": "nothing was confirmed — report this run blocked"}), flush=True)
        return 2
    except (KeyError, TypeError, IndexError, ValueError) as exc:
        print(json.dumps({"fatal": f"unexpected Azure DevOps response shape: {exc!r}",
                          "hint": "nothing was confirmed — report this run blocked"}), flush=True)
        return 2

    print(json.dumps(result, indent=2), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
