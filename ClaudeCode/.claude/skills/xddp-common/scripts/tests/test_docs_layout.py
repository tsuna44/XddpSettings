import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import docs_layout as layout  # noqa: E402


def fm(body: str) -> dict:
    return layout.parse_frontmatter("---\n" + body + "\n---\n# t\n")


class FrontmatterTestCase(unittest.TestCase):
    def test_scalar_unquoted(self):
        self.assertEqual(fm('version: "1.0.0"\nlast-updated-cr: CR-1'),
                         {"version": "1.0.0", "last-updated-cr": "CR-1"})

    def test_empty_inline_list(self):
        self.assertEqual(fm("related-modules: []")["related-modules"], [])

    def test_inline_list(self):
        self.assertEqual(fm("related-modules: [a, b]")["related-modules"], ["a", "b"])

    def test_inline_list_quoted(self):
        self.assertEqual(fm('related-modules: ["a", \'b\']')["related-modules"], ["a", "b"])

    def test_block_list(self):
        self.assertEqual(fm("related-modules:\n  - a\n  - b")["related-modules"], ["a", "b"])

    def test_block_list_quoted(self):
        self.assertEqual(fm('related-modules:\n  - "a"\n  - \'b\'')["related-modules"], ["a", "b"])

    def test_no_frontmatter(self):
        self.assertEqual(layout.parse_frontmatter("# no fm\n"), {})


class UsecaseTestCase(unittest.TestCase):
    TEMPLATE = (
        "---\n"
        'version: "1.0.0"\n'
        'last-updated-cr: "CR-2026-001"\n'
        "related-modules:\n"
        '  - "{module1}"\n'
        '  - "{module2}"\n'
        "---\n\n"
        "# ユースケース記述 — x\n\n"
        "## 2. 目的・ゴール\n\n"
        "ラベルで絞り込む。\n二行目。\n\n---\n"
    )

    def test_purpose_first_line_of_first_paragraph(self):
        self.assertEqual(layout.usecase_purpose(self.TEMPLATE), "ラベルで絞り込む。")

    def test_purpose_missing(self):
        self.assertEqual(layout.usecase_purpose("# x\n\n## 3. アクター\n\nA\n"), "")

    def test_related_modules_template_form(self):
        self.assertEqual(layout.usecase_related_modules(layout.parse_frontmatter(self.TEMPLATE)),
                         ["{module1}", "{module2}"])

    def test_related_modules_absent_or_empty(self):
        self.assertEqual(layout.usecase_related_modules({}), [])
        self.assertEqual(layout.usecase_related_modules({"related-modules": []}), [])
        self.assertEqual(layout.usecase_related_modules({"related-modules": ""}), [])


class BreakingTestCase(unittest.TestCase):
    def test_true(self):
        self.assertTrue(layout.is_breaking(fm("breaking: true")))

    def test_false(self):
        self.assertFalse(layout.is_breaking(fm("breaking: false")))

    def test_quoted_true(self):
        self.assertTrue(layout.is_breaking(fm('breaking: "true"')))

    def test_absent(self):
        self.assertFalse(layout.is_breaking(fm("version: 1")))
        self.assertIsNone(layout.breaking_value(fm("version: 1")))

    def test_vocabulary(self):
        self.assertEqual(layout.BREAKING_VALUES, ("true", "false"))


class LayoutTestCase(unittest.TestCase):
    def test_paths(self):
        docs, latest = Path("/d"), Path("/l")
        self.assertEqual(layout.docs_specs_root(docs, "repo-a"), Path("/d/repo-a/specs"))
        self.assertEqual(layout.latest_specs_root(latest, "repo-a"), Path("/l/repo-a"))
        self.assertEqual(layout.docs_usecases_dir(docs), Path("/d/system/specs/use-cases"))
        self.assertEqual(layout.latest_usecases_dir(latest), Path("/l/system/use-cases"))
        self.assertEqual(layout.docs_interfaces_dir(docs), Path("/d/cross/specs/interfaces"))
        self.assertEqual(layout.latest_interfaces_dir(latest), Path("/l/cross/interfaces"))
        self.assertEqual(layout.code_knowledge_dir(docs, "cross"),
                         Path("/d/cross/knowledge/code-knowledge"))

    def test_module_names_excludes_overview_and_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ("overview", "b", "a"):
                (root / d).mkdir()
            (root / "README.md").write_text("x", encoding="utf-8")
            self.assertEqual(layout.module_names(root), ["a", "b"])
            self.assertEqual(layout.module_names(root / "missing"), [])


if __name__ == "__main__":
    unittest.main()
