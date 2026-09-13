import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

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

    def test_anchor_found_nowhere_with_line_is_unpostable(self):
        plan = gr.plan_post([self.comment(line=11, anchor="nope")], self.files, self.contents, [])
        self.assertEqual(plan["to_post"], [])
        self.assertEqual(plan["unpostable"], [{"path": "a.py", "line": 11, "reason": "anchor text not found at PR head"}])


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

    def test_new_comments_by_login(self):
        base = {"comments": [("c1", "rev")]}
        now = {"comments": [("c1", "rev"), ("c2", "me"), ("c3", "other")]}
        self.assertEqual(gr.new_comments_by("me", base, now), ["c2"])


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


if __name__ == "__main__":
    unittest.main()
