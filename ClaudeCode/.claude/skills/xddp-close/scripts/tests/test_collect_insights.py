import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import collect_insights as mod  # noqa: E402

GUIDANCE = (
    "> 作成・レビュー中に気づいた修正すべき内容・改善案・懸念事項を自由に記録する。\n"
    "> 現在のCRスコープ外の内容も記載可。次のCR起票・バックログの入力として活用する。\n"
)

EMPTY_TABLE = "| # | 種別 | 内容 | 対応方針 |\n|---|------|------|----------|\n"

PLACEHOLDER_ROW_TABLE = (
    EMPTY_TABLE
    + "| 1 | 修正点／改善案／懸念／質問 | {内容} | 今回対応／次回CR／保留／却下 |\n"
)

FILLED_TABLE = (
    EMPTY_TABLE
    + "| 1 | 改善案 | 許容範囲を設定可能にする案 | 次回CR |\n"
)


def _ana_text(body: str, heading: str = "## 7. 気づき・提案メモ") -> str:
    return (
        "# 要求分析メモ\n\n"
        "## 6. 分析結果\n\n本文\n\n"
        f"{heading}\n\n{body}\n"
        "---\n\n## 8. 変更履歴\n"
    )


class EnumerateAndSectionTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.cr = "CR-TEST"
        self.cr_path = self.root / "xddp" / self.cr
        self.xddp_dir = self.root / "xddp"
        (self.cr_path / "02_analysis").mkdir(parents=True)
        (self.cr_path / "03_change-requirements").mkdir(parents=True)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_ana(self, body: str, heading: str = "## 7. 気づき・提案メモ") -> Path:
        p = self.cr_path / "02_analysis" / f"ANA-{self.cr}.md"
        p.write_text(_ana_text(body, heading), encoding="utf-8")
        return p

    def _write_crs_placeholder(self) -> None:
        p = self.cr_path / "03_change-requirements" / f"CRS-{self.cr}.md"
        p.write_text(_ana_text("（なし）", heading="## 6. 気づき・提案メモ"), encoding="utf-8")

    def test_heading_level_h2_and_h3_both_detected(self):
        self._write_ana(FILLED_TABLE, heading="## 7. 気づき・提案メモ")
        self._write_crs_placeholder()
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], [], False)
        self.assertEqual(result["with_section"], 2)
        self.assertEqual(len(result["entries"]), 1)

        # H3 variant in a fresh fixture
        self.tmpdir.cleanup()
        self.setUp()
        self._write_ana(FILLED_TABLE, heading="### 気づき・提案メモ")
        self._write_crs_placeholder()
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], [], False)
        self.assertEqual(result["with_section"], 2)
        self.assertEqual(len(result["entries"]), 1)

    def test_heading_whitespace_and_fullwidth_space_normalized(self):
        heading = "##　7．　気づき・提案メモ　"
        self._write_ana(FILLED_TABLE, heading=heading)
        self._write_crs_placeholder()
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], [], False)
        self.assertEqual(result["with_section"], 2)
        self.assertEqual(len(result["entries"]), 1)

    def test_file_without_heading_skipped_normally(self):
        p = self.cr_path / "02_analysis" / f"ANA-{self.cr}.md"
        p.write_text("# 要求分析メモ\n\n本文のみ、見出しなし。\n", encoding="utf-8")
        self._write_crs_placeholder()
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], [], False)
        self.assertEqual(result["scanned"], 2)
        self.assertEqual(result["with_section"], 1)
        self.assertEqual(len(result["entries"]), 0)

    def test_placeholder_variants_not_entries(self):
        for body in ("（なし）", EMPTY_TABLE, PLACEHOLDER_ROW_TABLE):
            self.tmpdir.cleanup()
            self.setUp()
            self._write_ana(body)
            self._write_crs_placeholder()
            result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], [], False)
            self.assertEqual(len(result["entries"]), 0, msg=f"body={body!r}")
            self.assertEqual(result["with_section"], 2)

    def test_real_entry_extracted_with_body(self):
        self._write_ana(FILLED_TABLE)
        self._write_crs_placeholder()
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], [], False)
        self.assertEqual(len(result["entries"]), 1)
        source_path, body = result["entries"][0]
        self.assertEqual(source_path, str(Path("02_analysis") / f"ANA-{self.cr}.md"))
        self.assertIn("許容範囲を設定可能にする案", body)

    def test_has_cross_toggle_includes_cross_files(self):
        self._write_ana(PLACEHOLDER_ROW_TABLE)
        self._write_crs_placeholder()
        (self.cr_path / "04_specout" / "cross").mkdir(parents=True)
        cross_spo = self.cr_path / "04_specout" / "cross" / f"SPO-{self.cr}-cross.md"
        cross_spo.write_text(_ana_text(FILLED_TABLE, heading="## 9. 気づき・提案メモ"), encoding="utf-8")

        result_without = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], [], False)
        self.assertEqual(len(result_without["entries"]), 0)

        result_with = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], [], True)
        self.assertEqual(len(result_with["entries"]), 1)

    def test_chd_multiple_batches_all_scanned(self):
        self._write_ana(PLACEHOLDER_ROW_TABLE)
        self._write_crs_placeholder()
        design_dir = self.cr_path / "06_design" / "svc-a"
        design_dir.mkdir(parents=True)
        (design_dir / f"CHD-{self.cr}.md").write_text(
            "# 変更設計書 インデックス\n\n"
            "## 2. UR別ファイル一覧\n\n"
            "| UR ID | UR名 | バッチ | SP数 | ファイル | 該当変更 |\n"
            "|---|---|---|---|---|---|\n"
            f"| {self.cr}-UR-001 | UR1 | - | 1 | "
            f"[CHD-{self.cr}-UR-001.md](./CHD-{self.cr}-UR-001.md) | あり |\n"
            f"| {self.cr}-UR-002 | UR2 | - | 1 | "
            f"[CHD-{self.cr}-UR-002.md](./CHD-{self.cr}-UR-002.md) | あり |\n",
            encoding="utf-8",
        )
        (design_dir / f"CHD-{self.cr}-UR-001.md").write_text(
            _ana_text(FILLED_TABLE, heading="## 8. 気づき・提案メモ"), encoding="utf-8"
        )
        (design_dir / f"CHD-{self.cr}-UR-002.md").write_text(
            _ana_text("（なし）", heading="## 8. 気づき・提案メモ"), encoding="utf-8"
        )
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], ["svc-a"], False)
        self.assertEqual(len(result["entries"]), 1)
        self.assertIn(str(Path("06_design") / "svc-a" / f"CHD-{self.cr}-UR-001.md"),
                       [p for p, _ in result["entries"]])

    def test_latest_specs_old_structure_duplicate_no_crash(self):
        self._write_ana(PLACEHOLDER_ROW_TABLE)
        self._write_crs_placeholder()
        specs_dir = self.xddp_dir / "latest-specs" / "svc-a" / "mod_a"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text(
            _ana_text(FILLED_TABLE, heading="## 8. 気づき・提案メモ"), encoding="utf-8"
        )
        old_style = self.xddp_dir / "latest-specs" / "svc-a"
        (old_style / "auth-spec.md").write_text(
            _ana_text(FILLED_TABLE, heading="## 8. 気づき・提案メモ"), encoding="utf-8"
        )
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, ["svc-a"], [], False)
        self.assertEqual(len(result["entries"]), 2)

    def test_exclude_filter_skips_non_insight_latest_specs_files(self):
        self._write_ana(PLACEHOLDER_ROW_TABLE)
        self._write_crs_placeholder()
        specs_dir = self.xddp_dir / "latest-specs" / "svc-a" / "mod_a"
        specs_dir.mkdir(parents=True)
        for name in ("schema.md", "crud.md", "dfd.md", "mod_a-seq.md"):
            (specs_dir / name).write_text(
                _ana_text(FILLED_TABLE, heading="## 8. 気づき・提案メモ"), encoding="utf-8"
            )
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, ["svc-a"], [], False)
        self.assertEqual(result["scanned"], 2)
        self.assertEqual(len(result["entries"]), 0)

    def test_summary_counts_match_input(self):
        self._write_ana(FILLED_TABLE)  # +1 scanned, +1 with_section, +1 entry
        self._write_crs_placeholder()  # +1 scanned, +1 with_section, +0 entry
        # svc-a に対する SPO/DSN(4種)/CODING/VERIFY/TSP（計8）と CHD インデックス（1）が
        # いずれも未作成のため、想定ファイル9件が「存在しなかった」として計上される。
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], ["svc-a"], False)
        self.assertEqual(result["scanned"], 2)
        self.assertEqual(result["with_section"], 2)
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["missing"], 9)

    def test_render_output_contains_summary(self):
        self._write_ana(FILLED_TABLE)
        self._write_crs_placeholder()
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], [], False)
        rendered = "\n".join(mod.render_output(self.cr, result))
        self.assertIn("## 収集サマリ", rendered)
        self.assertIn("抽出エントリ数: 1", rendered)
        self.assertIn(f"# 気づき・提案メモ集約（{self.cr}）", rendered)


class CliErrorHandlingTestCase(unittest.TestCase):
    def test_missing_cr_path_exits_1(self):
        parser = mod.build_parser()
        args = parser.parse_args([
            "collect", "--cr", "CR-TEST", "--cr-path", "/no/such/dir",
            "--xddp-dir", "/no/such/xddp", "--repos-keys", "", "--affected-repos", "",
            "--output-file", "/tmp/does-not-matter.md",
        ])
        with self.assertRaises(SystemExit) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
