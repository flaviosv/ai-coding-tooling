import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ado_review as ar

ME = "me-id"
OTHER = "other-id"


def comment(cid, author, body, ctype="text"):
    return {"id": cid, "author": {"id": author, "displayName": author}, "content": body, "commentType": ctype}


def thread(tid, comments, status="active", path=None, line=None):
    t = {"id": tid, "status": status, "comments": comments, "isDeleted": False}
    if path:
        t["threadContext"] = {"filePath": "/" + path, "rightFileStart": {"line": line, "offset": 1}}
    return t


class FakeAdo:
    """The subset of `Ado` the subcommands call, backed by in-memory threads."""

    org, project, repo = "fabrikam", "Fiber", "web"

    def __init__(self, threads=None, changes=None, files=None, drop_posts=0, fail_replies=()):
        self._threads = threads or []
        self._changes = changes or {}
        self._files = files or {}
        self.drop_posts = drop_posts
        self.fail_replies = set(fail_replies)
        self.created = []
        self.statuses = []
        self._next_id = 100

    def pr_web_url(self, pr):
        return f"https://dev.azure.com/fabrikam/Fiber/_git/web/pullrequest/{pr}"

    def identity(self):
        return {"id": ME, "name": "Me"}

    def pull_request(self, pr):
        return {"lastMergeSourceCommit": {"commitId": "abc"}}

    def latest_iteration(self, pr):
        return 3

    def changes(self, pr, iteration):
        return self._changes

    def file_lines(self, path, commit):
        return self._files.get(path)

    def threads(self, pr):
        return json.loads(json.dumps(self._threads))

    def create_thread(self, pr, body):
        self.created.append(body)
        if self.drop_posts:
            self.drop_posts -= 1
            raise ar.AdoError("HTTP 500", 500, "boom")
        self._next_id += 1
        ctx = body["threadContext"]
        self._threads.append(thread(
            self._next_id, [comment(1, ME, body["comments"][0]["content"])],
            path=ctx["filePath"].lstrip("/"), line=ctx["rightFileStart"]["line"],
        ))

    def reply(self, pr, tid, parent, content):
        if str(tid) in self.fail_replies:
            raise ar.AdoError("HTTP 500", 500, "boom")
        for t in self._threads:
            if str(t["id"]) == str(tid):
                t["comments"].append(comment(len(t["comments"]) + 1, ME, content))

    def set_status(self, pr, tid, status):
        self.statuses.append((str(tid), status))
        for t in self._threads:
            if str(t["id"]) == str(tid):
                t["status"] = status


CHANGES = {"src/a.py": {"tracking_id": 7, "change_type": "edit"},
           "src/gone.py": {"tracking_id": 8, "change_type": "delete"}}
FILES = {"src/a.py": ["def f():", "    x = 1", "    return x"]}


class PlanPostTest(unittest.TestCase):
    def plan(self, comments, existing=()):
        return ar.plan_post(comments, CHANGES, FILES, list(existing))

    def test_posts_with_tracking_id_and_line_width(self):
        plan = self.plan([{"path": "src/a.py", "line": 2, "body": "b", "anchor": "x = 1"}])
        self.assertEqual(plan["to_post"], [{"path": "src/a.py", "line": 2, "body": "b",
                                            "tracking_id": 7, "end_offset": 10}])

    def test_leading_slash_is_accepted(self):
        plan = self.plan([{"path": "/src/a.py", "line": 3, "body": "b"}])
        self.assertEqual(plan["to_post"][0]["path"], "src/a.py")

    def test_unchanged_file_is_unpostable(self):
        plan = self.plan([{"path": "src/b.py", "line": 1, "body": "b"}])
        self.assertEqual(plan["unpostable"][0]["reason"], "file not changed by this PR")

    def test_deleted_file_is_unpostable(self):
        plan = self.plan([{"path": "src/gone.py", "line": 1, "body": "b"}])
        self.assertEqual(plan["unpostable"][0]["reason"], "file deleted by this PR")

    def test_anchor_corrects_line(self):
        plan = self.plan([{"path": "src/a.py", "line": 1, "body": "b", "anchor": "return x"}])
        self.assertEqual(plan["anchor_corrected"], [{"path": "src/a.py", "from_line": 1, "line": 3}])

    def test_anchor_nowhere_posts_unverified(self):
        plan = self.plan([{"path": "src/a.py", "line": 2, "body": "b", "anchor": "nope"}])
        self.assertEqual(plan["anchor_unverified"], [{"path": "src/a.py", "line": 2}])
        self.assertEqual(len(plan["to_post"]), 1)

    def test_existing_thread_is_not_reposted(self):
        plan = self.plan([{"path": "src/a.py", "line": 2, "body": "b"}], [("src/a.py", 2, "b")])
        self.assertEqual(plan["already_present"], [{"path": "src/a.py", "line": 2}])
        self.assertEqual(plan["to_post"], [])

    def test_duplicate_input_posts_once(self):
        c = {"path": "src/a.py", "line": 2, "body": "b"}
        plan = self.plan([c, dict(c)])
        self.assertEqual(len(plan["to_post"]), 1)
        self.assertEqual(len(plan["input_duplicates"]), 1)


class PostTest(unittest.TestCase):
    CONFIG = {"org": "fabrikam", "project": "Fiber", "repo": "web", "pr": 42,
              "comments": [{"path": "src/a.py", "line": 2, "body": "**[Q1]** fix", "anchor": "x = 1"}]}

    def setUp(self):
        patcher = mock.patch.object(ar.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_posts_and_confirms(self):
        fake = FakeAdo(changes=CHANGES, files=FILES)
        result, code = ar.post(fake, self.CONFIG, dry_run=False)
        self.assertEqual((code, result["posted_confirmed"], result["missing"]), (0, 1, []))
        payload = fake.created[0]
        self.assertEqual(payload["threadContext"]["filePath"], "/src/a.py")
        self.assertEqual(payload["pullRequestThreadContext"]["changeTrackingId"], 7)
        self.assertEqual(payload["pullRequestThreadContext"]["iterationContext"]["secondComparingIteration"], 3)

    def test_failed_request_is_retried_once(self):
        fake = FakeAdo(changes=CHANGES, files=FILES, drop_posts=1)
        result, code = ar.post(fake, self.CONFIG, dry_run=False)
        self.assertEqual((code, result["posted_confirmed"], len(fake.created)), (0, 1, 2))

    def test_still_missing_after_retry_is_partial(self):
        fake = FakeAdo(changes=CHANGES, files=FILES, drop_posts=2)
        result, code = ar.post(fake, self.CONFIG, dry_run=False)
        self.assertEqual((code, len(result["missing"])), (1, 1))

    def test_rerun_skips_what_is_already_posted(self):
        fake = FakeAdo(changes=CHANGES, files=FILES)
        ar.post(fake, self.CONFIG, dry_run=False)
        result, code = ar.post(fake, self.CONFIG, dry_run=False)
        self.assertEqual((code, len(fake.created), len(result["already_present"])), (0, 1, 1))

    def test_dry_run_writes_nothing(self):
        fake = FakeAdo(changes=CHANGES, files=FILES)
        result, code = ar.post(fake, self.CONFIG, dry_run=True)
        self.assertEqual((code, result["would_post"], fake.created), (0, 1, []))


class DeliverTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(ar.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def threads(self):
        return [
            thread(17, [comment(1, OTHER, "finding one")], path="src/a.py", line=2),
            thread(18, [comment(1, OTHER, "finding two")], status="pending"),
            thread(19, [comment(1, OTHER, "done already")], status="fixed"),
            thread(20, [comment(1, "system", "vote changed", ctype="system")]),
        ]

    def config(self, threads, skipped=None):
        return {"org": "fabrikam", "project": "Fiber", "repo": "web", "pr": 42,
                "threads": threads, "skipped": skipped or {}}

    def test_replies_resolves_and_confirms(self):
        fake = FakeAdo(threads=self.threads())
        cfg = self.config({"17": {"body": "fixed it", "resolve": "fixed"},
                           "18": {"body": "rejected", "resolve": "wontFix"}})
        result, code = ar.deliver(fake, cfg, dry_run=False)
        self.assertEqual(code, 0)
        self.assertEqual((result["in_scope"], result["replied_confirmed"], result["resolved_confirmed"]), (2, 2, 2))
        self.assertIn(ar.REPLY_MARKER, fake._threads[0]["comments"][-1]["content"])

    def test_system_and_resolved_threads_are_out_of_scope(self):
        fake = FakeAdo(threads=self.threads())
        result, code = ar.deliver(fake, self.config({"17": {"body": "x"}}), dry_run=True)
        self.assertEqual((code, result["unaccounted"]), (1, ["18"]))

    def test_rerun_does_not_reply_twice(self):
        fake = FakeAdo(threads=self.threads())
        cfg = self.config({"17": {"body": "fixed it", "resolve": "fixed"}}, {"18": "routed to a person"})
        ar.deliver(fake, cfg, dry_run=False)
        result, code = ar.deliver(fake, cfg, dry_run=False)
        self.assertEqual(code, 0)
        self.assertEqual(len(fake._threads[0]["comments"]), 2)

    def test_unconfirmed_reply_is_not_resolved(self):
        fake = FakeAdo(threads=self.threads(), fail_replies={"17"})
        cfg = self.config({"17": {"body": "x", "resolve": "fixed"}}, {"18": "routed"})
        result, code = ar.deliver(fake, cfg, dry_run=False)
        self.assertEqual((code, result["reply_missing"], fake.statuses), (1, ["17"], []))

    def test_unknown_thread_is_reported(self):
        fake = FakeAdo(threads=self.threads())
        cfg = self.config({"99": {"body": "x"}}, {"17": "a", "18": "b"})
        result, code = ar.deliver(fake, cfg, dry_run=False)
        self.assertEqual((code, result["unknown_threads"]), (1, ["99"]))


class ValidationTest(unittest.TestCase):
    def test_bad_resolve_status(self):
        cfg = {"org": "o", "project": "p", "repo": "r", "pr": 1, "threads": {"1": {"body": "x", "resolve": True}}}
        self.assertIn("resolve", ar.validate_delivery_config(cfg))

    def test_post_needs_line_or_anchor(self):
        cfg = {"org": "o", "project": "p", "repo": "r", "pr": 1, "comments": [{"path": "a", "body": "b"}]}
        self.assertIn("anchor", ar.validate_post_config(cfg))


class CandidatesTest(unittest.TestCase):
    def fake(self, prs, threads_by_pr):
        fake = FakeAdo()
        fake.active_prs_for_reviewer = lambda reviewer: prs
        fake.threads = lambda pr: threads_by_pr.get(pr, [])
        return fake

    def pr(self, number, vote):
        return {"pullRequestId": number, "title": f"PR {number}", "reviewers": [{"id": ME, "vote": vote}]}

    def test_fix_sweep_keeps_waiting_and_rejected_votes(self):
        fake = self.fake([self.pr(1, -5), self.pr(2, -10), self.pr(3, 10), self.pr(4, 0)], {})
        result, _ = ar.candidates(fake, "fix")
        self.assertEqual([c["pr"] for c in result["candidates"]], [1, 2])

    def test_review_sweep_skips_prs_already_commented_on(self):
        mine = [thread(5, [comment(1, ME, "earlier finding")], path="a", line=1)]
        fake = self.fake([self.pr(1, 0), self.pr(2, 0), self.pr(3, 5)], {2: mine})
        result, _ = ar.candidates(fake, "review")
        self.assertEqual([c["pr"] for c in result["candidates"]], [1])


class AuthTest(unittest.TestCase):
    def test_falls_back_to_pat(self):
        with mock.patch.object(ar.subprocess, "run", side_effect=OSError), \
                mock.patch.dict(os.environ, {ar.PAT_ENV: "secret"}):
            self.assertTrue(ar.auth_header().startswith("Basic "))

    def test_no_credentials_is_an_error(self):
        env = {k: v for k, v in os.environ.items() if k != ar.PAT_ENV}
        with mock.patch.object(ar.subprocess, "run", side_effect=OSError), \
                mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ar.AdoError):
                ar.auth_header()


class RequestTest(unittest.TestCase):
    def response(self, status, body):
        resp = mock.MagicMock(status=status)
        resp.read.return_value = body.encode()
        resp.__enter__.return_value = resp
        return resp

    def throttled(self):
        return ar.urllib.error.HTTPError("u", 429, "Too Many", {"Retry-After": "7"}, io.BytesIO(b""))

    def test_throttle_waits_retry_after_then_succeeds(self):
        ado = ar.Ado("o", "p", "r", auth="Bearer t")
        with mock.patch.object(ar.urllib.request, "urlopen",
                               side_effect=[self.throttled(), self.response(200, '{"ok": 1}')]), \
                mock.patch.object(ar.time, "sleep") as sleep:
            self.assertEqual(ado.request("GET", "https://x"), {"ok": 1})
        sleep.assert_called_once_with(7)

    def test_sign_in_page_is_a_credential_error(self):
        ado = ar.Ado("o", "p", "r", auth="Basic x")
        with mock.patch.object(ar.urllib.request, "urlopen", return_value=self.response(203, "<html>")):
            with self.assertRaises(ar.AdoError) as ctx:
                ado.request("GET", "https://x")
        self.assertIn("credentials", str(ctx.exception))


class MainTest(unittest.TestCase):
    def test_invalid_input_is_fatal(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"org": "o"}, handle)
        self.addCleanup(os.remove, handle.name)
        out = io.StringIO()
        with redirect_stdout(out):
            code = ar.main(["post", handle.name])
        self.assertEqual(code, 2)
        self.assertIn("fatal", json.loads(out.getvalue()))


if __name__ == "__main__":
    unittest.main()
