import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import github_review as gr

PATCH = """@@ -10,4 +10,5 @@ def handler():
     keep_a
-    removed_b
+    added_b
+    added_c
     keep_d
@@ -40,2 +41,2 @@ def other():
-    old_x
+    new_x
     keep_y"""


class ParseHunkLinesTest(unittest.TestCase):
    def test_right_and_left_lines(self):
        lines = gr.parse_hunk_lines(PATCH)
        self.assertEqual(lines["RIGHT"], {10, 11, 12, 13, 41, 42})
        self.assertEqual(lines["LEFT"], {10, 11, 12, 40, 41})

    def test_no_newline_marker_is_ignored(self):
        lines = gr.parse_hunk_lines("@@ -1 +1 @@\n-a\n+b\n\\ No newline at end of file")
        self.assertEqual(lines["RIGHT"], {1})
        self.assertEqual(lines["LEFT"], {1})

    def test_empty_patch(self):
        self.assertEqual(gr.parse_hunk_lines(None), {"RIGHT": set(), "LEFT": set()})


class NearestLineTest(unittest.TestCase):
    def test_prefers_closest_then_lower(self):
        self.assertEqual(gr.nearest_line(20, {10, 30}), 10)
        self.assertEqual(gr.nearest_line(39, {13, 41}), 41)

    def test_empty(self):
        self.assertIsNone(gr.nearest_line(5, set()))


class ResolveAnchorTest(unittest.TestCase):
    FILE = ["def f():", "    x = 1", "    return x", "    x = 1"]

    def test_ok(self):
        self.assertEqual(gr.resolve_anchor(2, "x = 1", self.FILE), (2, "ok"))

    def test_corrected_to_nearest_occurrence(self):
        self.assertEqual(gr.resolve_anchor(3, "x = 1", self.FILE), (2, "corrected"))

    def test_null_line_resolved_by_anchor(self):
        self.assertEqual(gr.resolve_anchor(None, "return x", self.FILE), (3, "corrected"))

    def test_mismatch_keeps_line(self):
        self.assertEqual(gr.resolve_anchor(1, "missing", self.FILE), (1, "mismatch"))

    def test_not_found_without_line(self):
        self.assertEqual(gr.resolve_anchor(None, "missing", self.FILE), (None, "not_found"))

    def test_unchecked_without_content(self):
        self.assertEqual(gr.resolve_anchor(4, "x = 1", None), (4, "unchecked"))

    def test_whitespace_runs_are_ignored(self):
        self.assertEqual(gr.resolve_anchor(2, "x   =  1", self.FILE), (2, "ok"))

    def test_leading_diff_marker_is_ignored(self):
        self.assertEqual(gr.resolve_anchor(3, "+    return x", self.FILE), (3, "ok"))

    def test_partial_anchor_matches_its_own_line(self):
        self.assertEqual(gr.resolve_anchor(3, "return", self.FILE), (3, "ok"))

    def test_partial_anchor_elsewhere_needs_a_unique_match(self):
        self.assertEqual(gr.resolve_anchor(1, "return", self.FILE), (3, "corrected"))
        self.assertEqual(gr.resolve_anchor(3, "x =", self.FILE), (3, "mismatch"))
        self.assertEqual(gr.resolve_anchor(1, "= 1", ["pass", "a = 1", "b = 1"]), (1, "mismatch"))

    def test_marker_kept_when_the_line_really_starts_with_it(self):
        self.assertEqual(gr.resolve_anchor(2, "- item", ["# list", "- item"]), (2, "ok"))


class PlanPostTest(unittest.TestCase):
    def setUp(self):
        self.files = {"a.py": PATCH, "bin.png": None}
        self.contents = {"a.py": [f"line{i}" for i in range(1, 60)]}

    def comment(self, **kw):
        base = {"path": "a.py", "line": 11, "body": "finding", "anchor": "line11"}
        base.update(kw)
        return base

    def test_in_hunk_posts_as_is(self):
        plan = gr.plan_post([self.comment()], self.files, self.contents, [])
        self.assertEqual(plan["to_post"], [{"path": "a.py", "line": 11, "side": "RIGHT", "body": "finding"}])

    def test_outside_hunk_is_reanchored_with_note(self):
        plan = gr.plan_post([self.comment(line=25, anchor="line25")], self.files, self.contents, [])
        self.assertEqual(plan["reanchored"], [{"path": "a.py", "from_line": 25, "line": 13}])
        self.assertTrue(plan["to_post"][0]["body"].startswith("This concerns `a.py:25`"))
        self.assertEqual(plan["to_post"][0]["line"], 13)

    def test_untouched_file_is_unpostable(self):
        plan = gr.plan_post([self.comment(path="other.py")], self.files, self.contents, [])
        self.assertEqual(plan["to_post"], [])
        self.assertEqual(plan["unpostable"][0]["reason"], "file not changed by this PR")

    def test_file_without_patch_is_unpostable(self):
        plan = gr.plan_post([self.comment(path="bin.png", anchor="")], self.files, self.contents, [])
        self.assertIn("no diff hunk data", plan["unpostable"][0]["reason"])

    def test_anchor_correction_applies_before_hunk_check(self):
        plan = gr.plan_post([self.comment(line=30, anchor="line12")], self.files, self.contents, [])
        self.assertEqual(plan["anchor_corrected"], [{"path": "a.py", "from_line": 30, "line": 12}])
        self.assertEqual(plan["to_post"][0]["line"], 12)

    def test_anchor_not_found_without_line_is_unpostable(self):
        plan = gr.plan_post([self.comment(line=None, anchor="nope")], self.files, self.contents, [])
        self.assertEqual(plan["unpostable"][0]["reason"], "anchor text not found at PR head")

    def test_existing_comment_is_not_reposted(self):
        plan = gr.plan_post([self.comment()], self.files, self.contents, [("a.py", 11, "finding")])
        self.assertEqual(plan["to_post"], [])
        self.assertEqual(plan["already_present"], [{"path": "a.py", "line": 11}])

    def test_duplicate_input_posts_once(self):
        plan = gr.plan_post([self.comment(), self.comment()], self.files, self.contents, [])
        self.assertEqual(len(plan["to_post"]), 1)
        self.assertEqual(len(plan["input_duplicates"]), 1)

    def test_left_side_skips_anchor_check(self):
        plan = gr.plan_post([self.comment(side="LEFT", line=40, anchor="whatever")], self.files, self.contents, [])
        self.assertEqual(plan["to_post"][0]["side"], "LEFT")
        self.assertEqual(plan["unpostable"], [])

    def test_anchor_found_nowhere_with_line_posts_unverified(self):
        plan = gr.plan_post([self.comment(line=11, anchor="nope")], self.files, self.contents, [])
        self.assertEqual(plan["to_post"], [{"path": "a.py", "line": 11, "side": "RIGHT", "body": "finding"}])
        self.assertEqual(plan["anchor_unverified"], [{"path": "a.py", "line": 11}])
        self.assertEqual(plan["unpostable"], [])

    def test_empty_patch_is_unpostable(self):
        plan = gr.plan_post([self.comment()], {"a.py": ""}, self.contents, [])
        self.assertIn("no diff hunk data", plan["unpostable"][0]["reason"])


class ReconcilePostTest(unittest.TestCase):
    def test_confirmed_missing_and_duplicates(self):
        intended = [{"path": "a.py", "body": "one"}, {"path": "a.py", "body": "two"}, {"path": "b.py", "body": "three"}]
        before = [("a.py", 1, "old")]
        after = [("a.py", 1, "old"), ("a.py", 2, "one"), ("b.py", 3, "three"), ("b.py", 3, "three")]
        confirmed, missing, duplicates = gr.reconcile_post(intended, before, after)
        self.assertEqual(confirmed, 2)
        self.assertEqual(missing, [{"path": "a.py", "body": "two"}])
        self.assertEqual(duplicates, [{"path": "b.py", "body_prefix": "three", "extra": 1}])

    def test_preexisting_identical_comment_is_not_counted_as_new(self):
        intended = [{"path": "a.py", "body": "same"}]
        before = [("a.py", 1, "same")]
        after = [("a.py", 1, "same")]
        confirmed, missing, _ = gr.reconcile_post(intended, before, after)
        self.assertEqual((confirmed, len(missing)), (0, 1))


class MutationBuilderTest(unittest.TestCase):
    def test_thread_mutation_has_one_alias_per_item(self):
        query = gr.build_thread_mutation(3)
        self.assertEqual(query.count("addPullRequestReviewThread("), 3)
        self.assertIn("$reviewId: ID!", query)
        self.assertIn("$line2: Int!", query)
        self.assertIn("$side2: DiffSide!", query)

    def test_reply_and_resolve_mutations(self):
        self.assertEqual(gr.build_reply_mutation(2).count("addPullRequestReviewThreadReply("), 2)
        self.assertEqual(gr.build_resolve_mutation(4).count("resolveReviewThread("), 4)


class DeliverHelpersTest(unittest.TestCase):
    def test_in_scope_excludes_resolved_and_pending(self):
        threads = {
            "t1": {"resolved": False, "pending": False, "comments": []},
            "t2": {"resolved": True, "pending": False, "comments": []},
            "t3": {"resolved": False, "pending": True, "comments": []},
        }
        self.assertEqual(gr.in_scope_threads(threads), {"t1"})

    def test_new_comments_by_login_count_only_delivered_replies(self):
        marker = gr.REPLY_MARKER
        base = {"comments": [("c1", "rev", "finding")]}
        now = {"comments": [("c1", "rev", "finding"), ("c2", "me", f"done\n\n{marker}"),
                            ("c3", "other", f"x {marker}"), ("c4", "me", "yes, fix this")]}
        self.assertEqual(gr.new_comments_by("me", base, now), ["c2"])

    def test_marked_body_adds_the_marker_once(self):
        once = gr.marked_body("Fixed.\n")
        self.assertEqual(once, f"Fixed.\n\n{gr.REPLY_MARKER}")
        self.assertEqual(gr.marked_body(once), once)

    def test_own_plain_comment_is_not_a_delivered_reply(self):
        entry = {"comments": [("c1", "me", "**[Security — S1, High]** ..."), ("c2", "me", "yes, fix this")]}
        self.assertFalse(gr.has_delivered_reply("me", entry))
        entry["comments"].append(("c3", "me", gr.marked_body("Fixed.")))
        self.assertTrue(gr.has_delivered_reply("me", entry))

    def test_first_comment_never_counts_as_a_reply(self):
        entry = {"comments": [("c1", "me", gr.marked_body("finding"))]}
        self.assertFalse(gr.has_delivered_reply("me", entry))


class UnifiedDiffTest(unittest.TestCase):
    DIFF = "\n".join([
        "diff --git a/a.py b/a.py",
        "index 1..2 100644",
        "--- a/a.py",
        "+++ b/a.py",
        "@@ -1,2 +1,3 @@",
        " keep",
        "+++ b/looks-like-a-header",
        "+new",
        "diff --git a/gone.py b/gone.py",
        "--- a/gone.py",
        "+++ /dev/null",
        "@@ -1 +0,0 @@",
        "-old",
        "diff --git a/img.png b/img.png",
        "Binary files a/img.png and b/img.png differ",
    ])

    def test_patches_by_path(self):
        patches = gr.parse_unified_diff(self.DIFF)
        self.assertEqual(patches, {"a.py": "@@ -1,2 +1,3 @@\n keep\n+++ b/looks-like-a-header\n+new"})
        self.assertEqual(gr.parse_hunk_lines(patches["a.py"])["RIGHT"], {1, 2, 3})

    def test_fill_missing_patches_only_for_commented_files(self):
        files = {"a.py": None, "img.png": None, "c.py": "@@ -1 +1 @@\n+c"}
        with mock.patch.object(gr, "run_gh_text", return_value=self.DIFF) as run:
            filled = gr.fill_missing_patches("o", "r", 7, files, ["a.py", "img.png", "c.py"])
        run.assert_called_once_with(["gh", "pr", "diff", "7", "--repo", "o/r"])
        self.assertTrue(filled["a.py"].startswith("@@ -1,2 +1,3 @@"))
        self.assertIsNone(filled["img.png"])

    def test_fill_missing_patches_skips_the_diff_when_nothing_is_missing(self):
        with mock.patch.object(gr, "run_gh_text") as run:
            gr.fill_missing_patches("o", "r", 7, {"c.py": "@@ -1 +1 @@\n+c"}, ["c.py"])
        run.assert_not_called()

    def test_fill_missing_patches_survives_a_diff_failure(self):
        with mock.patch.object(gr, "run_gh_text", side_effect=gr.GhError("too large")):
            self.assertEqual(gr.fill_missing_patches("o", "r", 7, {"a.py": None}, ["a.py"]), {"a.py": None})


def completed(returncode, stdout, stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class RunGhTest(unittest.TestCase):
    def run_with(self, proc):
        with mock.patch.object(gr.subprocess, "run", return_value=proc):
            return gr.run_gh(["gh", "api", "x"])

    def test_success(self):
        self.assertEqual(self.run_with(completed(0, '{"login": "me"}')), {"login": "me"})

    def test_http_error_body_on_stdout_raises(self):
        with self.assertRaises(gr.GhError) as ctx:
            self.run_with(completed(1, '{"message":"Not Found","status":"404"}', "gh: Not Found (HTTP 404)"))
        self.assertIn("Not Found", ctx.exception.stdout)

    def test_graphql_partial_data_is_returned(self):
        payload = '{"data":{"r0":null,"r1":{"comment":{"id":"c"}}},"errors":[{"path":["r0"],"message":"bad"}]}'
        self.assertEqual(self.run_with(completed(1, payload))["data"]["r1"]["comment"]["id"], "c")

    def test_rate_limit_is_an_abuse_block(self):
        body = '{"message":"You have exceeded a secondary rate limit and have been temporarily blocked"}'
        with self.assertRaises(gr.GhError) as ctx:
            self.run_with(completed(1, body, "gh: HTTP 403"))
        self.assertTrue(ctx.exception.looks_like_abuse_block())

    def test_graphql_errors_without_data_raise(self):
        with self.assertRaises(gr.GhError):
            self.run_with(completed(1, '{"data":null,"errors":[{"type":"RATE_LIMITED","message":"API rate limit exceeded"}]}'))

    def test_unparseable_output_raises(self):
        with self.assertRaises(gr.GhError):
            self.run_with(completed(1, "", "gh: connection refused"))


class LoginTest(unittest.TestCase):
    def tearDown(self):
        gr.GH_ENV = None

    def test_resolve_login_rejects_another_identity(self):
        with mock.patch.object(gr, "run_gh", return_value={"login": "other"}):
            with self.assertRaises(gr.GhError):
                gr.resolve_login("me")
            self.assertEqual(gr.resolve_login(), "other")

    def test_use_login_sets_the_token_for_later_calls(self):
        with mock.patch.object(gr, "run_gh_text", return_value="tok123\n") as run:
            gr.use_login("me")
        run.assert_called_once_with(["gh", "auth", "token", "--user", "me"])
        self.assertEqual(gr.GH_ENV["GH_TOKEN"], "tok123")

    def test_use_login_without_a_token_fails(self):
        with mock.patch.object(gr, "run_gh_text", side_effect=gr.GhError("no account")):
            with self.assertRaises(gr.GhError):
                gr.use_login("ghost")


class SubmitTest(unittest.TestCase):
    PULL = {"url": "https://github.com/o/r/pull/1"}

    def test_empty_pending_review_is_left_in_place(self):
        with mock.patch.object(gr, "resolve_login", return_value="me"), \
             mock.patch.object(gr, "fetch_pr_and_pending_review", return_value=(self.PULL, "PRR_1")), \
             mock.patch.object(gr, "fetch_review", return_value=("PENDING", [])), \
             mock.patch.object(gr, "review_body", return_value=""), \
             mock.patch.object(gr, "gh_graphql") as graphql:
            result, code = gr.submit("o", "r", 1, False)
        self.assertEqual(code, 0)
        self.assertEqual((result["submitted"], result["empty_review"]), (False, True))
        graphql.assert_not_called()

    def test_no_pending_review_is_exit_0(self):
        with mock.patch.object(gr, "resolve_login", return_value="me"), \
             mock.patch.object(gr, "fetch_pr_and_pending_review", return_value=(self.PULL, None)):
            result, code = gr.submit("o", "r", 1, False)
        self.assertEqual((code, result["submitted"]), (0, False))


class ValidationTest(unittest.TestCase):
    def test_post_config(self):
        ok = {"owner": "o", "repo": "r", "pr": 1, "comments": [{"path": "a", "line": 1, "body": "b"}]}
        self.assertIsNone(gr.validate_post_config(ok))
        self.assertIn("'comments'", gr.validate_post_config({**ok, "comments": []}))
        bad_line = {**ok, "comments": [{"path": "a", "line": None, "body": "b"}]}
        self.assertIn("no 'line' and no 'anchor'", gr.validate_post_config(bad_line))
        bad_side = {**ok, "comments": [{"path": "a", "line": 1, "body": "b", "side": "UP"}]}
        self.assertIn("'side'", gr.validate_post_config(bad_side))
        left_null = {**ok, "comments": [{"path": "a", "line": None, "body": "b", "side": "LEFT", "anchor": "x"}]}
        self.assertIn("side LEFT needs a 'line'", gr.validate_post_config(left_null))

    def test_graphql_data_rejects_missing_repository(self):
        with self.assertRaises(gr.GhError):
            gr.graphql_data({"data": {"repository": None}}, "fetch")

    def test_delivery_config(self):
        ok = {"owner": "o", "repo": "r", "pr": 1, "threads": {"t": {"body": "x"}}}
        self.assertIsNone(gr.validate_delivery_config(ok))
        self.assertIn("both replied and skipped", gr.validate_delivery_config({**ok, "skipped": {"t": "why"}}))
        self.assertIn("non-empty reason", gr.validate_delivery_config({**ok, "skipped": {"u": " "}}))
        self.assertIsNone(gr.validate_delivery_config({**ok, "threads": {}, "skipped": {"t": "routed to @alice"}}))
        self.assertIn("cannot both be empty", gr.validate_delivery_config({**ok, "threads": {}}))

    def test_main_rejects_bad_input_with_exit_2(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"owner": "o"}, handle)
        try:
            out = io.StringIO()
            with redirect_stdout(out):
                code = gr.main(["post", handle.name])
            self.assertEqual(code, 2)
            self.assertIn("missing 'repo'", out.getvalue())
        finally:
            os.unlink(handle.name)

    def test_main_turns_an_unexpected_response_shape_into_exit_2(self):
        out = io.StringIO()
        with mock.patch.object(gr, "submit", side_effect=KeyError("data")), redirect_stdout(out):
            code = gr.main(["submit", "o", "r", "1"])
        self.assertEqual(code, 2)
        self.assertIn("unexpected GitHub response shape", out.getvalue())


if __name__ == "__main__":
    unittest.main()
