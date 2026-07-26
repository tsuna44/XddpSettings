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

    def test_missing_root_errors(self):
        parser = mod.build_parser()
        args = parser.parse_args([
            "generate", "--root", str(self.root / "nope"), "--step", "3", "--out", str(self.root / "out.md"),
        ])
        with self.assertRaises(SystemExit):
            args.func(args)


if __name__ == "__main__":
    unittest.main()
