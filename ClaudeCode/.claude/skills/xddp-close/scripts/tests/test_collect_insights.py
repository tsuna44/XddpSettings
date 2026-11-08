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


    def test_summary_counts_match_input(self):
        self._write_ana(FILLED_TABLE)  # +1 scanned, +1 with_section, +1 entry
        self._write_crs_placeholder()  # +1 scanned, +1 with_section, +0 entry
        # svc-a に対する SPO/DSN(4種)/CODING/VERIFY/TSP（計8）・CHD インデックス（1）・progress.md（1）が
        # いずれも未作成のため、想定ファイル10件が「存在しなかった」として計上される。
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], ["svc-a"], False)
        self.assertEqual(result["scanned"], 2)
        self.assertEqual(result["with_section"], 2)
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["missing"], 10)

    def test_render_output_contains_summary(self):
        self._write_ana(FILLED_TABLE)
        self._write_crs_placeholder()
        result = mod.collect(self.cr_path, self.xddp_dir, self.cr, [], [], False)
        rendered = "\n".join(mod.render_output(self.cr, result))
        self.assertIn("## 収集サマリ", rendered)
        self.assertIn("抽出エントリ数: 1", rendered)
        self.assertIn(f"# 気づき・提案メモ集約（{self.cr}）", rendered)


def _spec(cr: str, body: str, has_insights: str = "true") -> str:
    return (f"---\nversion: \"1.0.0\"\nlast-updated-cr: \"{cr}\"\nhas_insights: {has_insights}\n---\n\n"
            f"# 仕様\n\n## 8. 気づき・提案メモ\n\n{body}\n---\n\n## 9. 変更履歴\n")


def _table(*rows) -> str:
    return EMPTY_TABLE + "".join(f"| {i + 1} | 改善案 | {r} | 次回CR |\n" for i, r in enumerate(rows))


class LatestSpecsAndTargetsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.cr = "CR-TEST"
        self.xddp = self.root / "xddp"
        self.cr_path = self.xddp / self.cr
        self.docs = self.root / "baseline_docs"
        self.cr_path.mkdir(parents=True)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _w(self, path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _progress(self, listed=None, insights=PLACEHOLDER_ROW_TABLE):
        text = "# 進捗\n\n"
        if listed is not None:
            text += "## 工程11 更新仕様書ファイル一覧\n\n<!-- コメント -->\n\n"
            text += "".join(f"- {p}\n" for p in listed) + "\n---\n\n"
        text += f"## 気づき・提案メモ\n\n{insights}\n---\n\n## 次に実行すべきコマンド\n"
        self._w(self.cr_path / "progress.md", text)

    def _collect(self, **kw):
        return mod.collect(self.cr_path, self.xddp, self.cr, ["svc-a"], ["svc-a"], kw.pop("has_cross", False),
                           docs=self.docs, **kw)

    def _sources(self, result):
        return [p for p, _ in result["entries"]]

    def test_cross_tsp_and_progress_collected(self):
        self._progress(insights=_table("進捗の気づき"))
        self._w(self.cr_path / "09_test-spec" / "cross" / f"TSP-{self.cr}-cross.md", _ana_text(_table("cross TSP")))
        r = self._collect(has_cross=True)
        self.assertEqual(self._sources(r), [f"09_test-spec/cross/TSP-{self.cr}-cross.md", "progress.md"])

    def test_latest_union_has_insights_and_docs_exclusion(self):
        listed = "latest-specs/svc-a/mod_a/spec.md"
        self._progress(listed=[listed, "latest-specs/svc-a/mod_a/structure.md"])
        self._w(self.xddp / listed, _spec(self.cr, _table("前からある", "今回足した")))
        self._w(self.xddp / "latest-specs/svc-a/mod_a/structure.md", _spec(self.cr, _table("節あり"), "false"))
        self._w(self.xddp / "latest-specs/svc-a/mod_b/spec.md", _spec(self.cr, _table("一覧に無い")))
        self._w(self.xddp / "latest-specs/svc-a/mod_c/spec.md", _spec("CR-OLD", _table("前の CR")))
        self._w(self.docs / "svc-a/specs/mod_a/spec.md", _spec("CR-OLD", _table("前からある")))
        r = self._collect()
        bodies = dict(r["entries"])
        self.assertEqual(self._sources(r), [listed, "latest-specs/svc-a/mod_b/spec.md"])
        self.assertIn("今回足した", bodies[listed])
        self.assertNotIn("前からある", bodies[listed])
        self.assertEqual(r["latest"]["excluded"], 1)
        self.assertEqual(r["latest"]["not_listed"], ["latest-specs/svc-a/mod_b/spec.md"])
        rendered = "\n".join(mod.render_output(self.cr, r))
        self.assertIn("工程11 の一覧に無いファイル", rendered)
        self.assertIn("`{DOCS}` に既にある 1 件を除外", rendered)

    def test_latest_not_scanned_without_list_or_cr(self):
        self._progress(listed=None)
        self._w(self.xddp / "latest-specs/svc-a/mod_c/spec.md", _spec("CR-OLD", _table("前の CR")))
        r = self._collect()
        self.assertTrue(r["latest"]["skipped"])
        self.assertIn("latest-specs: 走査しなかった", "\n".join(mod.render_output(self.cr, r)))

    def test_rerun_after_promotion_carries_previous(self):
        listed = "latest-specs/svc-a/mod_a/spec.md"
        self._progress(listed=[listed])
        self._w(self.xddp / listed, _spec(self.cr, _table("前からある", "今回足した")))
        self._w(self.docs / "svc-a/specs/mod_a/spec.md", _spec("CR-OLD", _table("前からある")))
        out = self.cr_path / "pending-items" / f"INSIGHTS-{self.cr}.md"
        first = self._collect(previous_output=out)
        mod._write_lines(out, mod.render_output(self.cr, first))
        # 前回の close が C2 まで進み、{DOCS} に今の CR の版が昇格した状態
        self._w(self.docs / "svc-a/specs/mod_a/spec.md", (self.xddp / listed).read_text(encoding="utf-8"))
        second = self._collect(previous_output=out)
        self.assertEqual(dict(second["entries"])[listed], dict(first["entries"])[listed])
        self.assertEqual(second["latest"]["carried"], [listed])

    def test_rerun_after_promotion_without_previous(self):
        listed = "latest-specs/svc-a/mod_a/spec.md"
        self._progress(listed=[listed])
        self._w(self.xddp / listed, _spec(self.cr, _table("今回足した")))
        self._w(self.docs / "svc-a/specs/mod_a/spec.md", _spec(self.cr, _table("今回足した")))
        r = self._collect(previous_output=self.cr_path / "pending-items" / "none.md")
        self.assertEqual(r["latest"]["no_previous"], [listed])
        self.assertIn("前回の収集結果が無い 1 ファイル", "\n".join(mod.render_output(self.cr, r)))

    def test_none_comments_and_guidance_not_collected(self):
        variants = {
            "なし": "なし\n",
            "特になし。": "特になし。\n",
            "comment": "<!-- 書き手: AI。\n複数行 -->\n",
            "guidance": GUIDANCE,
            "none-row": EMPTY_TABLE + "| 1 | — | なし | — |\n",
        }
        for name, body in variants.items():
            with self.subTest(name):
                self._w(self.cr_path / "02_analysis" / f"ANA-{self.cr}.md", _ana_text(body))
                r = self._collect()
                self.assertEqual(r["entries"], [])

    def test_body_excludes_uncounted_lines(self):
        body = GUIDANCE + "<!-- 案内 -->\n" + EMPTY_TABLE + "| 1 | — | なし | — |\n| 2 | 懸念 | 本物 | 保留 |\n"
        self._w(self.cr_path / "02_analysis" / f"ANA-{self.cr}.md", _ana_text(body))
        r = self._collect()
        text = r["entries"][0][1]
        self.assertIn("| 2 | 懸念 | 本物 | 保留 |", text)
        self.assertIn("| # | 種別 | 内容 | 対応方針 |", text)
        self.assertNotIn("なし", text)
        self.assertNotIn("案内", text)
        self.assertNotIn(">", text)

    def test_every_artifact_section_collected(self):
        """CR の fixture（ANA・CRS・SPO・TSP〔repo・cross〕・CODING・VERIFY〔repo・cross〕・TRS・progress.md・
        latest-specs）の各成果物の節が集まる。"""
        c = self.cr
        files = [f"02_analysis/ANA-{c}.md", f"03_change-requirements/CRS-{c}.md", f"04_specout/svc-a/SPO-{c}.md",
                 f"07_coding/CODING-{c}-svc-a.md", f"08_code-review/VERIFY-{c}-svc-a.md",
                 f"08_code-review/VERIFY-{c}-cross.md", f"09_test-spec/svc-a/TSP-{c}.md",
                 f"09_test-spec/cross/TSP-{c}-cross.md", f"10_test-results/svc-a/TRS-{c}-001.md"]
        for f in files:
            self._w(self.cr_path / f, _ana_text(_table(f"気づき {f}")))
        listed = "latest-specs/svc-a/mod_a/spec.md"
        self._progress(listed=[listed], insights=_table("progress の気づき"))
        self._w(self.xddp / listed, _spec(c, _table("latest の気づき")))
        r = self._collect(has_cross=True)
        self.assertEqual(sorted(self._sources(r)), sorted(files + ["progress.md", listed]))


class Step11RecordReaderTestCase(unittest.TestCase):
    """spec_changes.py record が書いた progress.md の更新一覧を、close の読む側（collect_insights）が読める。"""

    def test_reads_list_written_by_record(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "xddp-11-specs" / "scripts"))
        import spec_changes
        with tempfile.TemporaryDirectory() as d:
            xddp = Path(d) / "xddp"
            (xddp / "CR-1").mkdir(parents=True)
            progress = xddp / "CR-1" / "progress.md"
            progress.write_text("# p\n\n## 次に実行すべきコマンド\n\nx\n", encoding="utf-8")
            spec_changes.snapshot(xddp, "CR-1")
            target = xddp / "latest-specs" / "svc" / "m" / "spec.md"
            target.parent.mkdir(parents=True)
            target.write_text("x", encoding="utf-8")
            spec_changes.record(xddp, "CR-1")
            self.assertEqual(mod.step11_listed_files(progress), ["latest-specs/svc/m/spec.md"])


class CliErrorHandlingTestCase(unittest.TestCase):
    def test_missing_cr_path_exits_1(self):
        parser = mod.build_parser()
        args = parser.parse_args([
            "collect", "--cr", "CR-TEST", "--cr-path", "/no/such/dir",
            "--xddp-dir", "/no/such/xddp", "--docs", "/no/such/docs", "--repos-keys", "", "--affected-repos", "",
            "--output-file", "/tmp/does-not-matter.md",
        ])
        with self.assertRaises(SystemExit) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
