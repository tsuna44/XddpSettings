import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import artifact_lint as mod  # noqa: E402

MODULE_SPEC_OK = """---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
module: "sensor-reader"
repo: "device-svc"
has_insights: false
---

# spec
"""

MODULE_SPEC_MISSING_MODULE = """---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
repo: "device-svc"
has_insights: false
---

# spec
"""

OVERVIEW_OK = """---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
repo: "device-svc"
has_insights: false
---

# overview
"""

USE_CASE_DESCRIPTION_MISSING_RELATED = """---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: ai-inferred
has_insights: false
---

# description
"""

NO_FRONTMATTER = "# no frontmatter\n\nsome content\n"

MERMAID_OK = """# doc

```mermaid
sequenceDiagram
  A->>B: hello
```
"""

MERMAID_MISSING_KEYWORD = """# doc

```mermaid
A --> B
```
"""

MERMAID_EMPTY = """# doc

```mermaid
```
"""

MERMAID_UNBALANCED = """# doc

```mermaid
graph TD
  A[Start --> B[End]
```
"""

MERMAID_BROKEN_ARROW = """# doc

```mermaid
graph TD
  A -> B
```
"""

TABLE_MISMATCH = """# doc

| a | b | c |
|---|---|---|
| 1 | 2 |
"""

TABLE_OK = """# doc

| a | b | c |
|---|---|---|
| 1 | 2 | 3 |
"""


class ArtifactLintTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name) / "latest-specs"
        self.root.mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, path: Path, doc_type: str = "SPEC"):
        parser = mod.build_parser()
        args = parser.parse_args(["--file", str(path), "--doc-type", doc_type])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def test_module_spec_ok_no_missing_keys(self):
        p = self.root / "device-svc" / "sensor-reader" / "spec.md"
        p.parent.mkdir(parents=True)
        p.write_text(MODULE_SPEC_OK, encoding="utf-8")
        result = self._run(p)
        self.assertTrue(result["frontmatter"]["applicable"])
        self.assertEqual(result["frontmatter"]["missing_keys"], [])

    def test_module_spec_missing_module_key_detected(self):
        p = self.root / "device-svc" / "sensor-reader" / "spec.md"
        p.parent.mkdir(parents=True)
        p.write_text(MODULE_SPEC_MISSING_MODULE, encoding="utf-8")
        result = self._run(p)
        self.assertIn("module", result["frontmatter"]["missing_keys"])
        self.assertNotIn("repo", result["frontmatter"]["missing_keys"])

    def test_overview_does_not_require_module(self):
        p = self.root / "device-svc" / "overview" / "architecture.md"
        p.parent.mkdir(parents=True)
        p.write_text(OVERVIEW_OK, encoding="utf-8")
        result = self._run(p)
        self.assertEqual(result["frontmatter"]["missing_keys"], [])
        self.assertNotIn("module", result["frontmatter"]["required_keys"])

    def test_use_case_description_requires_related_modules(self):
        p = self.root / "system" / "use-cases" / "foo" / "description.md"
        p.parent.mkdir(parents=True)
        p.write_text(USE_CASE_DESCRIPTION_MISSING_RELATED, encoding="utf-8")
        result = self._run(p)
        self.assertIn("related-modules", result["frontmatter"]["missing_keys"])

    def test_non_spec_doc_type_skips_frontmatter(self):
        p = self.root / "device-svc" / "sensor-reader" / "spec.md"
        p.parent.mkdir(parents=True)
        p.write_text(MODULE_SPEC_MISSING_MODULE, encoding="utf-8")
        result = self._run(p, doc_type="CHD")
        self.assertFalse(result["frontmatter"]["applicable"])

    def test_no_frontmatter_file_skips_check(self):
        p = self.root / "plan.md"
        p.write_text(NO_FRONTMATTER, encoding="utf-8")
        result = self._run(p)
        self.assertFalse(result["frontmatter"]["applicable"])

    def test_mermaid_ok_no_issues(self):
        p = self.root / "doc.md"
        p.write_text(MERMAID_OK, encoding="utf-8")
        result = self._run(p, doc_type="SPEC")
        self.assertEqual(result["mermaid"][0]["issues"], [])

    def test_mermaid_missing_keyword_detected(self):
        p = self.root / "doc.md"
        p.write_text(MERMAID_MISSING_KEYWORD, encoding="utf-8")
        result = self._run(p)
        self.assertTrue(any("図種別キーワード" in i for i in result["mermaid"][0]["issues"]))

    def test_mermaid_empty_block_detected(self):
        p = self.root / "doc.md"
        p.write_text(MERMAID_EMPTY, encoding="utf-8")
        result = self._run(p)
        self.assertTrue(any("空です" in i for i in result["mermaid"][0]["issues"]))

    def test_mermaid_unbalanced_brackets_detected(self):
        p = self.root / "doc.md"
        p.write_text(MERMAID_UNBALANCED, encoding="utf-8")
        result = self._run(p)
        self.assertTrue(any("角括弧" in i for i in result["mermaid"][0]["issues"]))

    def test_mermaid_broken_arrow_detected(self):
        p = self.root / "doc.md"
        p.write_text(MERMAID_BROKEN_ARROW, encoding="utf-8")
        result = self._run(p)
        self.assertTrue(any("エッジ記法" in i for i in result["mermaid"][0]["issues"]))

    def test_table_column_mismatch_detected(self):
        p = self.root / "doc.md"
        p.write_text(TABLE_MISMATCH, encoding="utf-8")
        result = self._run(p)
        self.assertEqual(len(result["tables"]), 1)
        self.assertIn("列数", result["tables"][0]["issue"])

    def test_table_ok_no_issues(self):
        p = self.root / "doc.md"
        p.write_text(TABLE_OK, encoding="utf-8")
        result = self._run(p)
        self.assertEqual(result["tables"], [])

    def test_files_mode_returns_array(self):
        p1 = self.root / "a.md"
        p1.write_text(TABLE_OK, encoding="utf-8")
        p2 = self.root / "b.md"
        p2.write_text(TABLE_MISMATCH, encoding="utf-8")
        parser = mod.build_parser()
        args = parser.parse_args(["--files", f"{p1},{p2}", "--doc-type", "SPEC"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        result = json.loads(buf.getvalue())
        self.assertEqual(len(result["results"]), 2)

    def test_missing_file_errors(self):
        parser = mod.build_parser()
        args = parser.parse_args(["--file", str(self.root / "nope.md"), "--doc-type", "SPEC"])
        with self.assertRaises(SystemExit):
            args.func(args)


if __name__ == "__main__":
    unittest.main()
