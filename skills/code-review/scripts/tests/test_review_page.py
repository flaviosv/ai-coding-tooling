import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import review_page as rp

DIFF = """diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1,6 +1,7 @@
 def f():
     a = 1
-    b = 2
+    b = 3
+    c = </script>
     d = 4
     e = 5
     g = 6
"""

FINDINGS = {
    "org": "fabrikam", "project": "Fiber", "repo": "web", "pr": 42,
    "pr_url": "https://dev.azure.com/fabrikam/Fiber/_git/web/pullrequest/42", "pr_title": "Retry backoff",
    "comments": [
        {"id": "Q1", "severity": "High", "title": "Wrong constant", "path": "src/a.py", "line": 3,
         "anchor": "b = 3", "body": "**[Quality — Q1, High]** b should stay 2"},
        {"id": "S1", "severity": "Low", "title": "Unsafe", "path": "src/a.py", "line": 4,
         "anchor": "c = </script>", "body": "**[Security — S1, Low]** closing tag"},
    ],
}


class SnippetTest(unittest.TestCase):
    PATCH = rp.parse_unified_diff(DIFF)["src/a.py"]

    def test_window_around_the_line_with_removed_lines(self):
        rows = rp.snippet(self.PATCH, 3, "b = 3")
        self.assertEqual([r["n"] for r in rows], [1, 2, None, 3, 4, 5, 6])
        self.assertEqual(rows[3], {"k": "+", "n": 3, "t": "    b = 3"})

    def test_line_outside_hunks_falls_back_to_anchor(self):
        self.assertEqual(rp.snippet(self.PATCH, 90, "x"), [{"k": " ", "n": 90, "t": "x"}])

    def test_nothing_known(self):
        self.assertEqual(rp.snippet(None, None, None), [])


class RenderTest(unittest.TestCase):
    def test_embeds_data_and_escapes_script_close(self):
        page = rp.render(FINDINGS, DIFF)
        self.assertIn("<title>web PR 42 findings</title>", page)
        self.assertNotIn(rp.DATA_SLOT, page)
        self.assertNotIn("c = </script>", page)
        data = json.loads(page.split("const DATA = ", 1)[1].split(";\n", 1)[0].replace("<\\/", "</"))
        self.assertEqual([f["key"] for f in data["findings"]], ["f0", "f1"])
        self.assertEqual(data["files"], ["src/a.py"])


class CollectTest(unittest.TestCase):
    def export(self, decisions=None, added=None, wrapped=False):
        root = tempfile.mkdtemp()
        for collection, docs in (("decisions", decisions or {}), ("added", added or {})):
            os.makedirs(os.path.join(root, collection))
            for doc_id, body in docs.items():
                doc = {"id": doc_id, "version": 1, "data": body} if wrapped else body
                with open(os.path.join(root, collection, doc_id + ".json"), "w") as handle:
                    json.dump(doc, handle)
        return root

    def test_no_decisions_keeps_everything(self):
        post, summary = rp.collect(FINDINGS, self.export())
        self.assertEqual([c["id"] for c in post["comments"]], ["Q1", "S1"])
        self.assertEqual(summary["remaining"], 2)

    def test_drop_edit_and_add(self):
        db = self.export(
            decisions={"f0": {"state": "drop"}, "f1": {"state": "keep", "body": "reworded"}},
            added={"zz": {"path": "src/a.py", "line": 6, "body": "**[Added]** missing test"}},
        )
        post, summary = rp.collect(FINDINGS, db)
        self.assertEqual([(c["id"], c["body"]) for c in post["comments"]],
                         [("S1", "reworded"), ("U1", "**[Added]** missing test")])
        self.assertEqual((summary["dropped"], summary["edited"], summary["added"]), (["Q1"], ["S1"], 1))

    def test_wrapped_export_shape_is_unwrapped(self):
        post, _ = rp.collect(FINDINGS, self.export(decisions={"f0": {"state": "drop"}}, wrapped=True))
        self.assertEqual([c["id"] for c in post["comments"]], ["S1"])

    def test_incomplete_added_finding_is_ignored(self):
        post, summary = rp.collect(FINDINGS, self.export(added={"a": {"path": "src/a.py", "body": "no line"}}))
        self.assertEqual(summary["added"], 0)

    def test_all_dropped_writes_no_post_file(self):
        db = self.export(decisions={"f0": {"state": "drop"}, "f1": {"state": "drop"}})
        with tempfile.TemporaryDirectory() as tmp:
            findings = os.path.join(tmp, "findings.json")
            with open(findings, "w") as handle:
                json.dump(FINDINGS, handle)
            out = io.StringIO()
            with redirect_stdout(out):
                code = rp.main(["collect", findings, db, os.path.join(tmp, "post.json")])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())["remaining"], 0)
            self.assertFalse(os.path.exists(os.path.join(tmp, "post.json")))


if __name__ == "__main__":
    unittest.main()
