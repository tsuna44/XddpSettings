import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import xddp_review_brief as mod  # noqa: E402

import tempfile  # noqa: E402


class ReviewBriefTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name) / "CR-2026-999"
        self.root.mkdir()
        self.baseline_path = self.root / ".phase-baseline-4a.json"
        self.brief_path = self.root / ".review-brief.md"

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, argv):
        parser = mod.build_parser()
        args = parser.parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _write(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    # --- baseline ---

    def test_baseline_scans_files_and_excludes_control_files(self):
        self._write("a.md", "hello\nworld\n")
        (self.root / ".gate-snapshot.json").write_text("{}", encoding="utf-8")
        result = self._run([
            "baseline", "--root", str(self.root), "--step", "4a", "--out", str(self.baseline_path),
        ])
        self.assertTrue(result["ok"])
        self.assertEqual(result["file_count"], 1)
        data = json.loads(self.baseline_path.read_text(encoding="utf-8"))
        self.assertIn("a.md", data["files"])
        self.assertNotIn(".gate-snapshot.json", data["files"])
        self.assertEqual(data["step"], "4a")

    def test_baseline_is_idempotent_on_rerun(self):
        self._write("a.md", "hello\n")
        self._run(["baseline", "--root", str(self.root), "--step", "4a", "--out", str(self.baseline_path)])
        self._write("a.md", "hello\nworld\n")
        result = self._run(["baseline", "--root", str(self.root), "--step", "4a", "--out", str(self.baseline_path)])
        self.assertTrue(result["ok"])
        data = json.loads(self.baseline_path.read_text(encoding="utf-8"))
        self.assertEqual(data["files"]["a.md"]["lines"], 2)

    # --- marker extraction: each of the 6 marker types ---

    def test_marker_review_critical_unresolved_note(self):
        self._write("03_change-requirements/review/03_req-review.md", "本文\n⚠️ 未解決の重大指摘あり\n")
        out_path = self.root / ".review-brief.md"
        result = self._run([
            "generate", "--root", str(self.root), "--step", "3", "--out", str(out_path),
        ])
        types = {t["marker_type"] for t in result["top"]}
        self.assertIn("未解決レビュー指摘", types)

    def test_marker_review_critical_red_row(self):
        self._write("03_change-requirements/review/03_req-review.md", "| 1 | 🔴 重大 | 場所 | 内容 |\n")
        out_path = self.root / ".review-brief.md"
        result = self._run(["generate", "--root", str(self.root), "--step", "3", "--out", str(out_path)])
        types = {t["marker_type"] for t in result["top"]}
        self.assertIn("未解決レビュー指摘", types)

    def test_marker_grep_uncovered_pattern(self):
        content = (
            "## grep未対応パターン（手動確認必要）\n"
            "| パターン種別 | 根拠 | 確認状況 |\n"
            "|---|---|---|\n"
            "| （例）リフレクション | ダミー | ⬜ 未確認 |\n"
            "| リフレクション | getattr 使用箇所あり | ⬜ 未確認 |\n"
            "\n"
            "## Wave 0\n"
            "| 見出し | ダミー |\n"
        )
        self._write("04_specout/repoA/discovery-log.md", content)
        out_path = self.root / ".review-brief.md"
        result = self._run(["generate", "--root", str(self.root), "--step", "4a", "--out", str(out_path)])
        types = {t["marker_type"] for t in result["top"]}
        self.assertIn("grep未対応パターン", types)
        self.assertEqual(result["counts"]["grep未対応パターン"], 1)

    def test_marker_needs_confirmation(self):
        self._write("04_specout/repoA/SPO-CR-2026-999.md", "この振る舞いは未確認（要確認）\n")
        out_path = self.root / ".review-brief.md"
        result = self._run(["generate", "--root", str(self.root), "--step", "4a", "--out", str(out_path)])
        types = {t["marker_type"] for t in result["top"]}
        self.assertIn("要確認注記", types)

    def test_marker_module_level(self):
        self._write("04_specout/repoA/SPO-CR-2026-999.md", "確信度: MODULE-LEVEL\n")
        out_path = self.root / ".review-brief.md"
        result = self._run(["generate", "--root", str(self.root), "--step", "4a", "--out", str(out_path)])
        types = {t["marker_type"] for t in result["top"]}
        self.assertIn("確信度MODULE-LEVEL", types)

    def test_marker_medium_confidence(self):
        self._write("04_specout/repoA/SPO-CR-2026-999.md", "確信度: MEDIUM\n")
        out_path = self.root / ".review-brief.md"
        result = self._run(["generate", "--root", str(self.root), "--step", "4a", "--out", str(out_path)])
        types = {t["marker_type"] for t in result["top"]}
        self.assertIn("確信度MEDIUM", types)

    def test_marker_estimated(self):
        self._write("04_specout/repoA/SPO-CR-2026-999.md", "この関連は推定に基づく（推定）\n")
        out_path = self.root / ".review-brief.md"
        result = self._run(["generate", "--root", str(self.root), "--step", "4a", "--out", str(out_path)])
        types = {t["marker_type"] for t in result["top"]}
        self.assertIn("推定注記", types)

    # --- ranking by weight ---

    def test_top_sorted_by_weight_descending(self):
        self._write("a.md", "確信度: MEDIUM\n")
        self._write("03_change-requirements/review/b-review.md", "🔴 重大\n")
        out_path = self.root / ".review-brief.md"
        result = self._run(["generate", "--root", str(self.root), "--step", "3", "--out", str(out_path)])
        weights = [t["weight"] for t in result["top"]]
        self.assertEqual(weights, sorted(weights, reverse=True))
        self.assertEqual(result["top"][0]["marker_type"], "未解決レビュー指摘")

    def test_top_n_limits_results(self):
        content = "\n".join(f"（要確認） line {i}" for i in range(5))
        self._write("a.md", content)
        out_path = self.root / ".review-brief.md"
        result = self._run([
            "generate", "--root", str(self.root), "--step", "3", "--out", str(out_path), "--top-n", "2",
        ])
        self.assertEqual(len(result["top"]), 2)

    # --- diff summary ---

    def test_diff_detects_added_changed_deleted(self):
        self._write("a.md", "line1\nline2\n")
        self._write("b.md", "keep\n")
        self._run(["baseline", "--root", str(self.root), "--step", "3", "--out", str(self.baseline_path)])
        self._write("a.md", "line1\nline2\nline3\n")
        (self.root / "b.md").unlink()
        self._write("c.md", "new file\n")
        out_path = self.root / ".review-brief.md"
        result = self._run([
            "generate", "--root", str(self.root), "--step", "3",
            "--baseline", str(self.baseline_path), "--out", str(out_path),
        ])
        brief_text = out_path.read_text(encoding="utf-8")
        self.assertIn("c.md", brief_text)
        self.assertIn("a.md", brief_text)
        self.assertIn("b.md", brief_text)
        self.assertNotIn("ベースライン未取得のため差分省略", brief_text)

    def test_diff_omitted_without_baseline(self):
        self._write("a.md", "hello\n")
        out_path = self.root / ".review-brief.md"
        self._run(["generate", "--root", str(self.root), "--step", "3", "--out", str(out_path)])
        brief_text = out_path.read_text(encoding="utf-8")
        self.assertIn("ベースライン未取得のため差分省略", brief_text)

    def test_missing_baseline_file_falls_back_gracefully(self):
        self._write("a.md", "hello\n")
        out_path = self.root / ".review-brief.md"
        result = self._run([
            "generate", "--root", str(self.root), "--step", "3",
            "--baseline", str(self.root / "nope.json"), "--out", str(out_path),
        ])
        self.assertTrue(result["ok"])
        brief_text = out_path.read_text(encoding="utf-8")
        self.assertIn("ベースライン未取得のため差分省略", brief_text)

    # --- zero markers / zero files: normal completion ---

    def test_zero_files_completes_normally(self):
        out_path = self.root / ".review-brief.md"
        result = self._run(["generate", "--root", str(self.root), "--step", "3", "--out", str(out_path)])
        self.assertTrue(result["ok"])
        self.assertEqual(result["top"], [])
        brief_text = out_path.read_text(encoding="utf-8")
        self.assertIn("特筆すべき不確実箇所は検出されませんでした", brief_text)

    def test_zero_markers_completes_normally(self):
        self._write("a.md", "普通の本文です\n")
        out_path = self.root / ".review-brief.md"
        result = self._run(["generate", "--root", str(self.root), "--step", "3", "--out", str(out_path)])
        self.assertTrue(result["ok"])
        self.assertEqual(result["top"], [])

    # --- work/ intermediate files and metrics files are excluded ---

    def _generate(self, step="4a", baseline=False):
        argv = ["generate", "--root", str(self.root), "--step", step, "--out", str(self.brief_path)]
        if baseline:
            argv += ["--baseline", str(self.baseline_path)]
        result = self._run(argv)
        return result, self.brief_path.read_text(encoding="utf-8")

    def _section(self, brief_text, head):
        start = brief_text.index(head)
        end = brief_text.find("\n## ", start + 1)
        return brief_text[start:] if end < 0 else brief_text[start:end]

    def _take_baseline(self):
        self._run(["baseline", "--root", str(self.root), "--step", "4a", "--out", str(self.baseline_path)])

    def test_work_dir_files_excluded_from_ranking_and_top(self):
        self._write("04_specout/repoA/work/wave-0-hits.json", "{}\n")
        self._write("04_specout/repoA/work/discovery-log-review-scope.md", "確信度: MEDIUM\n")
        self._write("04_specout/repoA/SPO-X.md", "本文\n")
        result, brief_text = self._generate()
        sec1 = self._section(brief_text, "## ①")
        sec3 = self._section(brief_text, "## ③")
        for rel in ("04_specout/repoA/work/wave-0-hits.json",
                    "04_specout/repoA/work/discovery-log-review-scope.md"):
            self.assertNotIn(rel, sec1)
            self.assertNotIn(rel, sec3)
            self.assertNotIn(rel, [t["file"] for t in result["top"]])
        self.assertIn("04_specout/repoA/SPO-X.md", sec3)

    def test_cross_work_dir_excluded(self):
        self._write("04_specout/cross/work/cross-propagation-log.json", "{}\n")
        _, brief_text = self._generate()
        self.assertNotIn("cross-propagation-log.json", self._section(brief_text, "## ③"))

    def _setup_work_changes(self):
        self._write("04_specout/repoA/work/keep.json", "a\n")
        self._write("04_specout/repoA/work/gone.json", "a\n")
        self._take_baseline()
        self._write("04_specout/repoA/work/keep.json", "b\n")
        (self.root / "04_specout/repoA/work/gone.json").unlink()
        self._write("04_specout/repoA/work/new1.json", "a\n")
        self._write("04_specout/repoA/work/new2.json", "a\n")

    def test_work_dir_counted_in_diff_summary(self):
        self._setup_work_changes()
        _, brief_text = self._generate(baseline=True)
        sec2 = self._section(brief_text, "## ②")
        self.assertIn("- 中間ファイル（work/ 配下。レビュー対象外）: 追加 2件・変更 1件・削除 1件", sec2)
        self.assertNotIn("04_specout/repoA/work/", sec2)

    def test_work_dir_not_mixed_into_regular_diff_counts(self):
        self._setup_work_changes()
        self._write("04_specout/repoA/SPO-X.md", "本文\n")
        _, brief_text = self._generate(baseline=True)
        sec2 = self._section(brief_text, "## ②")
        self.assertIn("- 追加: 1件", sec2)
        self.assertIn("- 変更: 0件", sec2)
        self.assertIn("- 削除: 0件", sec2)

    def test_work_dir_line_omitted_when_no_work_changes(self):
        self._write("04_specout/repoA/work/keep.json", "a\n")
        self._take_baseline()
        self._write("04_specout/repoA/SPO-X.md", "本文\n")
        _, brief_text = self._generate(baseline=True)
        self.assertNotIn("中間ファイル", self._section(brief_text, "## ②"))

    def test_work_dir_count_without_baseline(self):
        for i in range(3):
            self._write(f"04_specout/repoA/work/f{i}.json", "{}\n")
        _, brief_text = self._generate()
        self.assertIn(
            "（ベースライン未取得のため差分省略）\n- 中間ファイル（work/ 配下。レビュー対象外）: 3件",
            brief_text,
        )

    def test_repo_named_work_not_excluded(self):
        self._write("04_specout/work/SPO-X.md", "本文\n")
        self._write("04_specout/work/work/bfs-state.json", "{}\n")
        _, brief_text = self._generate()
        sec3 = self._section(brief_text, "## ③")
        self.assertIn("04_specout/work/SPO-X.md", sec3)
        self.assertNotIn("04_specout/work/work/bfs-state.json", sec3)

    def test_metrics_files_excluded_as_control(self):
        self._write(".phase-metrics-4a.json", "{}\n")
        self._write("metrics.jsonl", "{}\n")
        self._write("a.md", "hello\n")
        self._take_baseline()
        data = json.loads(self.baseline_path.read_text(encoding="utf-8"))
        self.assertNotIn(".phase-metrics-4a.json", data["files"])
        self.assertNotIn("metrics.jsonl", data["files"])
        self._write("metrics.jsonl", "{}\n{}\n")
        self._write(".phase-metrics-4a.json", "{\"x\": 1}\n")
        _, brief_text = self._generate(baseline=True)
        self.assertNotIn("metrics", self._section(brief_text, "## ②"))
        self.assertNotIn("metrics", self._section(brief_text, "## ③"))
        nested = self._write("04_specout/repoA/metrics.jsonl", "{}\n")
        self.assertFalse(mod._is_control_file(nested, self.root))

    def test_control_files_in_old_baseline_not_listed_as_deleted(self):
        self._write("a.md", "hello\n")
        self.baseline_path.write_text(json.dumps({
            "root": str(self.root), "step": "4a",
            "files": {"a.md": {"sha256": "x", "lines": 1}, "metrics.jsonl": {"sha256": "y", "lines": 3}},
        }), encoding="utf-8")
        _, brief_text = self._generate(baseline=True)
        sec2 = self._section(brief_text, "## ②")
        self.assertIn("- 削除: 0件", sec2)
        self.assertNotIn("metrics.jsonl", sec2)

    def test_est_total_min_excludes_work(self):
        self._write("04_specout/repoA/SPO-X.md", "本文\n")
        before, _ = self._generate()
        self._write("04_specout/repoA/work/bfs-state.json", "{}\n" * 400)
        after, _ = self._generate()
        self.assertEqual(before["est_total_min"], after["est_total_min"])

    def test_missing_root_errors(self):
        parser = mod.build_parser()
        args = parser.parse_args([
            "generate", "--root", str(self.root / "nope"), "--step", "3", "--out", str(self.root / "out.md"),
        ])
        with self.assertRaises(SystemExit):
            args.func(args)


if __name__ == "__main__":
    unittest.main()
