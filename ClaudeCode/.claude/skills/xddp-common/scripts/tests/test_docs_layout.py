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
    def test_non_constraint_knowledge_dirs(self):
        dirs = layout.NON_CONSTRAINT_KNOWLEDGE_DIRS
        self.assertTrue(set(layout.SHARED_KNOWLEDGE_DIRS) <= set(dirs))
        self.assertIn("_cochange", dirs)
        self.assertEqual(len(dirs), len(set(dirs)))
        self.assertEqual(layout.CONSTRAINTS_FILE, "constraints.md")

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


STEP11_TEMPLATES = Path(__file__).resolve().parents[3] / "xddp-11-specs" / "templates"
# 工程11 のテンプレート → それが作るファイルの名前の例
TEMPLATE_FILE_NAMES = {
    "11_cross-interface-schema-template.md": "schema.md",
    "11_cross-interface-spec-template.md": "spec.md",
    "11_cross-sequence-template.md": "alert-flow-seq.md",
    "11_module-sequence-template.md": "main-seq.md",
    "11_module-spec-template.md": "spec.md",
    "11_module-state-machine-template.md": "state-machine.md",
    "11_module-structure-template.md": "structure.md",
    "11_overview-architecture-template.md": "architecture.md",
    "11_overview-crud-template.md": "crud.md",
    "11_overview-data-model-template.md": "data-model.md",
    "11_overview-deployment-template.md": "deployment.md",
    "11_overview-dfd-template.md": "dfd.md",
    "11_overview-sequence-template.md": "startup-seq.md",
    "11_system-use-case-description-template.md": "description.md",
    "11_system-use-case-sequence-template.md": "normal-seq.md",
}


class InsightsTestCase(unittest.TestCase):
    def test_find_sections_any_level(self):
        text = "# t\n\n##　9．　気づき・提案メモ　\n\nA\n\n### 小\n\nB\n\n## 10. 次\n\nC\n"
        bodies = layout.find_insight_sections(text)
        self.assertEqual(len(bodies), 1)
        self.assertIn("B", bodies[0])
        self.assertNotIn("C", bodies[0])

    def test_items(self):
        body = ["> 案内", "<!-- コメント", "| 1 | x | y | z |", "-->", "", "| # | 種別 | 内容 | 対応方針 |",
                "|---|---|---|---|", "| 1 | 改善案 | 本物 | 次回CR |", "| 2 | — | なし | — |",
                "| 3 | 修正点 | {内容} | 今回対応 |", "", "なし。", "表の外の本文", "---"]
        items = layout.insight_items(body)
        self.assertEqual([i["key"] for i in items], ["改善案|本物|次回CR", "表の外の本文"])
        self.assertEqual(layout.render_insight_items(items),
                         ["| # | 種別 | 内容 | 対応方針 |", "|---|---|---|---|", "| 1 | 改善案 | 本物 | 次回CR |",
                          "", "表の外の本文"])

    def test_none_words_only(self):
        for line in ("なし", "（なし）", "(なし)", "特になし", "特になし。"):
            self.assertEqual(layout.insight_items([line]), [], line)

    def test_has_insights(self):
        self.assertTrue(layout.has_insights({"has_insights": "true"}))
        self.assertFalse(layout.has_insights({"has_insights": "false"}))
        self.assertIsNone(layout.has_insights({}))

    def test_expected_has_insights(self):
        for name, expected in (("spec.md", True), ("schema.md", False), ("crud.md", False), ("dfd.md", False),
                               ("x/main-seq.md", False), ("architecture.md", True)):
            self.assertEqual(layout.expected_has_insights(name), expected, name)

    def test_latest_to_docs_path(self):
        self.assertEqual(layout.latest_to_docs_path("/d", "latest-specs/svc/mod/spec.md"),
                         Path("/d/svc/specs/mod/spec.md"))

    def test_step11_templates_match_rule(self):
        """工程11 の全テンプレートで has_insights と節の有無・ファイル名の期待値が一致する。"""
        names = sorted(p.name for p in STEP11_TEMPLATES.glob("11_*.md"))
        self.assertEqual(names, sorted(TEMPLATE_FILE_NAMES))
        for name in names:
            text = (STEP11_TEMPLATES / name).read_text(encoding="utf-8")
            value = layout.has_insights(layout.parse_frontmatter(text))
            with self.subTest(name):
                self.assertIsNotNone(value)
                self.assertEqual(value, bool(layout.find_insight_sections(text)))
                self.assertEqual(value, layout.expected_has_insights(TEMPLATE_FILE_NAMES[name]))


class SpecDirTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _spec(self, root, name, module_dir):
        p = root / name / "spec.md"
        p.parent.mkdir(parents=True)
        p.write_text(f'---\nmodule-dir: "{module_dir}"\n---\n', encoding="utf-8")

    def test_module_spec_dir_name(self):
        self.assertEqual(layout.module_spec_dir_name("AuthService"), "auth-service")
        self.assertEqual(layout.module_spec_dir_name("src/auth"), "src-auth")
        self.assertEqual(layout.module_spec_dir_name("sensor_reader"), "sensor-reader")
        self.assertEqual(layout.module_spec_dir_name("HTTPServer"), "http-server")
        self.assertEqual(layout.module_spec_dir_name("system"), "mod-system")

    def test_norm_module_dir(self):
        self.assertEqual(layout.norm_module_dir("./src/auth/"), "src/auth")
        self.assertEqual(layout.norm_module_dir("."), ".")
        self.assertEqual(layout.norm_module_dir("./"), ".")
        self.assertEqual(layout.norm_module_dir(""), "")
        self.assertEqual(layout.norm_module_dir("{src/モジュール名/ 等}"), "")

    def test_resolve_spec_dir_priority_and_duplicates(self):
        latest, docs = self.root / "latest", self.root / "docs"
        self._spec(docs, "authentication", "src/auth")
        self.assertEqual(layout.resolve_spec_dir("auth", "src/auth/", [latest, docs]), ("authentication", []))
        self._spec(latest, "auth-b", "src/auth")
        self._spec(latest, "auth-a", "src/auth")
        name, dups = layout.resolve_spec_dir("auth", "src/auth", [latest, docs])
        self.assertEqual(name, "auth-a")
        self.assertEqual(dups, [str(latest / "auth-b"), str(docs / "authentication")])
        self.assertEqual(layout.resolve_spec_dir("Auth", "", [latest, docs]), ("auth", []))
        self._spec(latest, "top", ".")
        self.assertEqual(layout.resolve_spec_dir("root", ".", [latest, docs]), ("top", []))

    def test_seq_file_stem(self):
        import unicodedata
        self.assertEqual(layout.seq_file_stem("4.5.1 メイン処理", 1), "メイン処理")
        self.assertEqual(layout.seq_file_stem("Main Flow_A", 1), "main-flow-a")
        self.assertEqual(layout.seq_file_stem("（）！", 3), "seq-3")
        self.assertEqual(layout.seq_file_stem(unicodedata.normalize("NFD", "ガード処理"), 1), "ガード処理")
        self.assertEqual(layout.cross_seq_stem("3.1 repositoryレベルのシーケンス図（例: repository）", 1), "repository")


class Step11RecordTestCase(unittest.TestCase):
    def test_write_and_read_lists(self):
        text = "# p\n\n## 工程11 更新仕様書ファイル一覧\n\n<!-- x -->\n\n---\n\n## 次に実行すべきコマンド\n\nx\n"
        out = layout.write_step11_lists(text, ["latest-specs/a/b.md"], [])
        self.assertEqual(layout.read_step11_list(out, layout.STEP11_UPDATED_HEADING), ["latest-specs/a/b.md"])
        self.assertEqual(layout.read_step11_list(out, layout.STEP11_DELETED_HEADING), [])
        self.assertIsNone(layout.read_step11_list("# p\n", layout.STEP11_DELETED_HEADING))
        self.assertEqual(layout.write_step11_lists(out, ["latest-specs/a/b.md"], []), out)

    def test_progress_template_headings_match_constants(self):
        tpl = (Path(__file__).resolve().parents[3] / "xddp-01-init" / "templates" / "00_progress-management-template.md")
        heads = [ln.strip() for ln in tpl.read_text(encoding="utf-8").split("\n") if ln.startswith("## ")]
        for h in (layout.STEP11_UPDATED_HEADING, layout.STEP11_DELETED_HEADING, layout.NEXT_COMMAND_HEADING):
            self.assertIn(h, heads)
        self.assertLess(heads.index(layout.STEP11_UPDATED_HEADING), heads.index(layout.STEP11_DELETED_HEADING))

    def test_cr_in_progress(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertFalse(layout.cr_in_progress(root, "CR-1"))      # progress.md が無い
            for cr, extra in (("CR-1", ""), ("CR-2", "\n## CR クローズ\n"), ("CR-3", "\n## CR 中止\n")):
                (root / cr).mkdir()
                (root / cr / "progress.md").write_text("# p\n" + extra, encoding="utf-8")
            self.assertTrue(layout.cr_in_progress(root, "CR-1"))
            self.assertFalse(layout.cr_in_progress(root, "CR-2"))
            self.assertFalse(layout.cr_in_progress(root, "CR-3"))
            self.assertEqual(layout.in_progress_crs(root), ["CR-1"])
            self.assertEqual(layout.in_progress_crs(root, exclude="CR-1"), [])


if __name__ == "__main__":
    unittest.main()
