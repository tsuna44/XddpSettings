import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import merge_classification as mod  # noqa: E402


class MergeClassificationTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write(self, name: str, obj) -> Path:
        p = self.root / name
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p

    def _hit(self, line_id: str, file_: str = "src/a.py") -> dict:
        return {"line_id": line_id, "command_id": "W0-C1", "symbol": "foo",
                "scope_file": None, "file": file_, "line_no": 1, "matched_text": "foo()"}

    def _class(self, line_id: str, value: str = "propagation-direct") -> dict:
        return {"line_id": line_id, "classification": value, "next_symbols": []}

    # -- 結合の基本形 -----------------------------------------------------

    def test_merge_combines_two_chunks_in_hits_order(self):
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R2"), self._hit("W0-R1")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        hc1 = self._write("wave-0-hits-chunk-1.json", {"chunk_id": "W0-K1", "hits": [self._hit("W0-R2")]})
        c0 = self._write("wave-0-chunk-0-class.json",
                          {"chunk_id": "W0-K0", "classification": [self._class("W0-R1")]})
        c1 = self._write("wave-0-chunk-1-class.json",
                          {"chunk_id": "W0-K1", "classification": [self._class("W0-R2")]})
        out = self.root / "wave-0-class.json"
        unsupported_out = self.root / "wave-0-unsupported.json"
        result = mod.merge(hits, [hc0, hc1], [c0, c1], out, unsupported_out)
        self.assertTrue(result["ok"])
        ordered = json.loads(out.read_text(encoding="utf-8"))
        # --hits の出現順（R2, R1）に整列される
        self.assertEqual([c["line_id"] for c in ordered], ["W0-R2", "W0-R1"])
        self.assertEqual(json.loads(unsupported_out.read_text(encoding="utf-8")), [])

    def test_merge_single_chunk_no_split(self):
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        c0 = self._write("wave-0-chunk-0-class.json",
                          {"chunk_id": "W0-K0", "classification": [self._class("W0-R1")]})
        out = self.root / "wave-0-class.json"
        result = mod.merge(hits, [hc0], [c0], out, self.root / "u.json")
        self.assertEqual(result["chunk_count"], 1)
        ordered = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual([c["line_id"] for c in ordered], ["W0-R1"])

    def test_merge_empty_chunk_is_valid(self):
        """空チャンク（hits 0件）は line_id 集合が空同士で一致し、正常に扱われる。"""
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        hc1 = self._write("wave-0-hits-chunk-1.json", {"chunk_id": "W0-K1", "hits": []})
        c0 = self._write("wave-0-chunk-0-class.json",
                          {"chunk_id": "W0-K0", "classification": [self._class("W0-R1")]})
        c1 = self._write("wave-0-chunk-1-class.json", {"chunk_id": "W0-K1", "classification": []})
        out = self.root / "wave-0-class.json"
        result = mod.merge(hits, [hc0, hc1], [c0, c1], out, self.root / "u.json")
        self.assertEqual(result["chunk_count"], 2)
        ordered = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual([c["line_id"] for c in ordered], ["W0-R1"])

    # -- 処理2: hits 全体との照合（欠落・重複） ---------------------------

    def test_merge_detects_missing_line_id(self):
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1"), self._hit("W0-R2")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        c0 = self._write("wave-0-chunk-0-class.json",
                          {"chunk_id": "W0-K0", "classification": [self._class("W0-R1")]})
        out = self.root / "wave-0-class.json"
        buf = io.StringIO()
        with redirect_stderr(buf), self.assertRaises(SystemExit) as cm:
            mod.merge(hits, [hc0], [c0], out, self.root / "u.json")
        self.assertNotEqual(cm.exception.code, 0)
        self.assertIn("W0-R2", buf.getvalue())
        self.assertFalse(out.exists())

    def test_merge_detects_duplicate_line_id_across_chunks(self):
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1")]})
        # 2チャンクとも W0-R1 を含む（本来チャンク分割で起き得ないが、混入時の検出を確認）
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        hc1 = self._write("wave-0-hits-chunk-1.json", {"chunk_id": "W0-K1", "hits": [self._hit("W0-R1")]})
        c0 = self._write("wave-0-chunk-0-class.json",
                          {"chunk_id": "W0-K0", "classification": [self._class("W0-R1")]})
        c1 = self._write("wave-0-chunk-1-class.json",
                          {"chunk_id": "W0-K1", "classification": [self._class("W0-R1")]})
        buf = io.StringIO()
        with redirect_stderr(buf), self.assertRaises(SystemExit):
            mod.merge(hits, [hc0, hc1], [c0, c1], self.root / "out.json", self.root / "u.json")
        self.assertIn("重複", buf.getvalue())

    # -- 処理3: 未知の classification 値 -----------------------------------

    def test_merge_detects_unknown_classification_value(self):
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        c0 = self._write("wave-0-chunk-0-class.json",
                          {"chunk_id": "W0-K0", "classification": [self._class("W0-R1", value="not-a-real-value")]})
        buf = io.StringIO()
        with redirect_stderr(buf), self.assertRaises(SystemExit):
            mod.merge(hits, [hc0], [c0], self.root / "out.json", self.root / "u.json")
        self.assertIn("not-a-real-value", buf.getvalue())

    # -- 処理6: チャンク単位の line_id 集合照合（stale チャンク） -----------

    def test_merge_detects_stale_chunk_with_unknown_line_id(self):
        """classifier 出力の line_id が対応するヒットチャンクの集合と一致しない（旧ランの混入）。"""
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        # 旧ランの stale な classification（W0-R1 ではなく別の line_id を含む）
        c0 = self._write("wave-0-chunk-0-class.json",
                          {"chunk_id": "W0-K0", "classification": [self._class("W0-R99")]})
        buf = io.StringIO()
        with redirect_stderr(buf), self.assertRaises(SystemExit) as cm:
            mod.merge(hits, [hc0], [c0], self.root / "out.json", self.root / "u.json")
        self.assertNotEqual(cm.exception.code, 0)
        self.assertIn("再投入対象チャンク", buf.getvalue())
        self.assertIn("W0-K0", buf.getvalue())

    # -- 処理8: 欠落チャンク（classifier が OUT_FILE を書かなかった） -------

    def test_merge_missing_chunk_file_reports_chunk_id_and_path_not_traceback(self):
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        missing_path = self.root / "wave-0-chunk-0-class.json"  # 意図的に書き出さない
        buf = io.StringIO()
        with redirect_stderr(buf), self.assertRaises(SystemExit) as cm:
            mod.merge(hits, [hc0], [missing_path], self.root / "out.json", self.root / "u.json")
        self.assertNotEqual(cm.exception.code, 0)
        self.assertIn("欠落チャンク", buf.getvalue())
        self.assertIn("W0-K0", buf.getvalue())
        self.assertIn(str(missing_path), buf.getvalue())

    def test_merge_mismatched_hits_chunks_and_chunks_count_is_explicit_error(self):
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        c0 = self._write("wave-0-chunk-0-class.json",
                          {"chunk_id": "W0-K0", "classification": [self._class("W0-R1")]})
        buf = io.StringIO()
        with redirect_stderr(buf), self.assertRaises(SystemExit):
            mod.merge(hits, [hc0, hc0], [c0], self.root / "out.json", self.root / "u.json")

    # -- §6 確認項目: --hits-chunks / --chunks の取り違え -------------------

    def test_merge_swapped_hits_chunks_and_chunks_reads_zero_classification(self):
        """--chunks にヒットチャンクを渡すと classification が1件も読まれず、
        チャンク単位の line_id 照合（処理6）が不一致として検出する
        （フラグ名一致のため refcheck では検出不能な取り違えを、値の中身で捕捉する）。"""
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        buf = io.StringIO()
        # --hits-chunks と --chunks を取り違え、両方に同じ「ヒットチャンク」ファイルを渡す
        # （--chunks 側はヒットチャンク形式のため "classification" キーを持たず、0件と読める）
        with redirect_stderr(buf), self.assertRaises(SystemExit):
            mod.merge(hits, [hc0], [hc0], self.root / "out.json", self.root / "u.json")
        self.assertIn("再投入対象チャンク", buf.getvalue())
        self.assertIn("missing_line_ids=['W0-R1']", buf.getvalue())

    # -- 処理4: grep未対応パターンのマージ（重複集約） ----------------------

    def test_merge_deduplicates_unsupported_patterns_by_pattern_and_location(self):
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1"), self._hit("W0-R2")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        hc1 = self._write("wave-0-hits-chunk-1.json", {"chunk_id": "W0-K1", "hits": [self._hit("W0-R2")]})
        c0 = self._write("wave-0-chunk-0-class.json", {
            "chunk_id": "W0-K0", "classification": [self._class("W0-R1")],
            "unsupported_patterns": [{"pattern": "eval", "location": "src/a.py:1", "note": "x"}],
        })
        c1 = self._write("wave-0-chunk-1-class.json", {
            "chunk_id": "W0-K1", "classification": [self._class("W0-R2")],
            "unsupported_patterns": [{"pattern": "eval", "location": "src/a.py:1", "note": "x"}],
        })
        unsupported_out = self.root / "u.json"
        mod.merge(hits, [hc0, hc1], [c0, c1], self.root / "out.json", unsupported_out)
        merged = json.loads(unsupported_out.read_text(encoding="utf-8"))
        self.assertEqual(len(merged), 1)

    # -- 処理7: chunk_mtimes / min_chunk_mtime -----------------------------

    def test_merge_outputs_chunk_mtimes_and_min(self):
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        c0 = self._write("wave-0-chunk-0-class.json",
                          {"chunk_id": "W0-K0", "classification": [self._class("W0-R1")]})
        result = mod.merge(hits, [hc0], [c0], self.root / "out.json", self.root / "u.json")
        self.assertEqual(len(result["chunk_mtimes"]), 1)
        self.assertEqual(result["chunk_mtimes"][0]["chunk_id"], "W0-K0")
        self.assertEqual(result["min_chunk_mtime"], result["chunk_mtimes"][0]["mtime"])

    def test_collect_chunk_mtimes_skips_unreadable_entries_without_error(self):
        """mtime が取得できないチャンクがあってもエラーにしない（計測専用・correctness に関与しない）。"""
        chunk_mtimes, min_chunk_mtime = mod._collect_chunk_mtimes(
            [("W0-K0", self.root / "does-not-exist.json")]
        )
        self.assertEqual(chunk_mtimes, [])
        self.assertIsNone(min_chunk_mtime)

    def test_collect_chunk_mtimes_sorts_ascending_and_reports_min(self):
        a = self._write("a.json", {})
        b = self._write("b.json", {})
        import os
        os.utime(a, (1000.0, 1000.0))
        os.utime(b, (2000.0, 2000.0))
        chunk_mtimes, min_chunk_mtime = mod._collect_chunk_mtimes([("W0-K1", b), ("W0-K0", a)])
        self.assertEqual([e["chunk_id"] for e in chunk_mtimes], ["W0-K0", "W0-K1"])
        self.assertEqual(min_chunk_mtime, 1000.0)

    # -- CLI --------------------------------------------------------------

    def test_cli_main_writes_output_and_prints_ok_json(self):
        hits = self._write("wave-0-hits.json", {"wave": 0, "hits": [self._hit("W0-R1")]})
        hc0 = self._write("wave-0-hits-chunk-0.json", {"chunk_id": "W0-K0", "hits": [self._hit("W0-R1")]})
        c0 = self._write("wave-0-chunk-0-class.json",
                          {"chunk_id": "W0-K0", "classification": [self._class("W0-R1")]})
        out = self.root / "out.json"
        unsupported_out = self.root / "u.json"
        argv = ["--hits", str(hits), "--hits-chunks", str(hc0), "--chunks", str(c0),
                "--out", str(out), "--unsupported-out", str(unsupported_out)]
        parser = mod.build_parser()
        args = parser.parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = mod.merge(Path(args.hits), args.hits_chunks, args.chunks,
                                Path(args.out), Path(args.unsupported_out))
            print(json.dumps(result, ensure_ascii=False))
        printed = json.loads(buf.getvalue().strip())
        self.assertTrue(printed["ok"])
        self.assertTrue(out.exists())
        self.assertTrue(unsupported_out.exists())


if __name__ == "__main__":
    unittest.main()
