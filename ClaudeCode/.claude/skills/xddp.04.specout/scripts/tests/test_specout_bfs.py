import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import specout_bfs as mod  # noqa: E402


def _fake_run(stdout_seq=None, default_stdout="", record=None):
    """subprocess.run のモック生成。呼び出しごとに stdout_seq を順に返し、尽きたら default_stdout。
    record を渡すと各呼び出しの argv を追記する。"""
    seq = list(stdout_seq or [])

    def _run(cmd, capture_output=True, text=True):
        if record is not None:
            record.append(cmd)
        out = seq.pop(0) if seq else default_stdout
        return SimpleNamespace(stdout=out, returncode=0, stderr="")

    return _run


class SpecoutBfsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.state_path = self.root / "bfs-state.json"
        self.log_path = self.root / "discovery-log.md"

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, argv):
        parser = mod.build_parser()
        args = parser.parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _init(self, symbols="processPayment", **kw):
        argv = [
            "init", "--path", str(self.state_path), "--repo-path", str(self.repo),
            "--discovery-log", str(self.log_path), "--symbols", symbols,
            "--today", "2026-07-19", "--cr", "CR-2026-999", "--repo", "device-svc",
        ]
        for k, v in kw.items():
            argv += [f"--{k.replace('_', '-')}", str(v)]
        return self._run(argv)

    def _write_file(self, rel_path: str, content: str):
        p = self.repo / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _load_state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    # -- init ---------------------------------------------------------

    def test_init_creates_state_and_log_header(self):
        result = self._init()
        self.assertTrue(result["ok"])
        self.assertEqual(result["current_wave"], 0)
        self.assertEqual(result["frontier_count"], 1)
        self.assertTrue(self.log_path.exists())
        text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("CR-2026-999", text)
        self.assertIn("processPayment", text)

    def test_init_rejects_invalid_frontier_format(self):
        with self.assertRaises(SystemExit):
            self._init(symbols="bad[symbol")

    # -- search ---------------------------------------------------------

    def test_search_finds_high_symbol_hits(self):
        self._write_file("src/billing/handler.py", "def handlePaymentRequest():\n    processPayment(order, amount)\n")
        self._init(symbols="processPayment")
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "wave-0-hits.json")])
        self.assertTrue(result["ok"])
        self.assertEqual(result["hit_count"], 1)
        hits = json.loads((self.root / "wave-0-hits.json").read_text(encoding="utf-8"))
        self.assertEqual(hits["hits"][0]["symbol"], "processPayment")
        self.assertEqual(hits["hits"][0]["file"], "src/billing/handler.py")
        data = self._load_state()
        self.assertFalse(data["wave_write_complete"])

    def test_search_medium_scope_limits_to_file(self):
        self._write_file("src/a.py", "def f():\n    return validate(x)\n")
        self._write_file("src/b.py", "def g():\n    return validate(y)\n")
        self._init(symbols="")
        data = self._load_state()
        data["frontier"] = [f"validate[MEDIUM:{self.repo / 'src/a.py'}]"]
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "wave-0-hits.json")])
        self.assertEqual(result["hit_count"], 1)
        hits = json.loads((self.root / "wave-0-hits.json").read_text(encoding="utf-8"))
        self.assertEqual(hits["hits"][0]["file"], "src/a.py")

    def test_search_medium_scope_resolves_relative_path(self):
        self._write_file("src/a.py", "def f():\n    return validate(x)\n")
        self._write_file("src/b.py", "def g():\n    return validate(y)\n")
        self._init(symbols="")
        data = self._load_state()
        data["frontier"] = ["validate[MEDIUM:src/a.py]"]
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "wave-0-hits.json")])
        self.assertEqual(result["hit_count"], 1)
        hits = json.loads((self.root / "wave-0-hits.json").read_text(encoding="utf-8"))
        self.assertEqual(hits["hits"][0]["file"], "src/a.py")

    def test_search_errors_when_complete(self):
        self._init()
        data = self._load_state()
        data["state"] = "complete"
        mod._write_state(self.state_path, data)
        with self.assertRaises(SystemExit):
            self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "x.json")])

    def test_search_pauses_at_wave_limit(self):
        self._init(max_wave=1)
        data = self._load_state()
        data["current_wave"] = 2
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "x.json")])
        self.assertTrue(result["paused"])
        self.assertEqual(result["state"], "paused-at-limit")
        self.assertEqual(result["limit_reached_count"], 1)
        text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("探索上限到達", text)

    def test_search_second_wave_limit_hit_escalates(self):
        self._init(max_wave=1)
        data = self._load_state()
        data["current_wave"] = 2
        data["limit_reached_count"] = 1
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "x.json")])
        self.assertEqual(result["state"], "paused-at-limit-2nd")

    # -- PLAN-20260804 Phase 0/1a/1b: metrics / dedup / 保守的フィルタ -----

    def test_is_pure_line_comment_extension_aware(self):
        # C/C++ の #define/#include/#ifdef は「#」で始まっても前処理指令＝真の参照 → 除外しない（.c）
        self.assertFalse(mod._is_pure_line_comment("#define PROCESS_X 1", "PROCESS_X", ".c"))
        self.assertFalse(mod._is_pure_line_comment("#include <PROCESS_X.h>", "PROCESS_X", ".h"))
        self.assertFalse(mod._is_pure_line_comment("#ifdef PROCESS_X", "PROCESS_X", ".c"))
        # C/C++ の // 行コメントは除外対象
        self.assertTrue(mod._is_pure_line_comment("// calls PROCESS_X here", "PROCESS_X", ".c"))
        # Python の # 行コメントは除外対象、コード行は除外しない
        self.assertTrue(mod._is_pure_line_comment("# process_x mention", "process_x", ".py"))
        self.assertFalse(mod._is_pure_line_comment("process_x(1)  # trailing", "process_x", ".py"))
        # 未登録・曖昧拡張子（.m 等）は常に除外しない（安全側）
        self.assertFalse(mod._is_pure_line_comment("% process_x", "process_x", ".m"))
        self.assertFalse(mod._is_pure_line_comment("# process_x", "process_x", ".unknownext"))

    def test_search_conservative_filter_skips_line_comment(self):
        # .py 内: 行コメント行は除外、コード行は残る（filter_removed=1）
        self._write_file("src/a.py", "# processPayment placeholder\nprocessPayment(x)\n")
        self._init(symbols="processPayment")  # 既定 hit_filter=conservative
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "wave-0-hits.json")])
        self.assertEqual(result["hit_count"], 1)
        self.assertEqual(result["filter_removed"], 1)
        self.assertEqual(result["raw_hits"], 2)
        hits = json.loads((self.root / "wave-0-hits.json").read_text(encoding="utf-8"))
        self.assertTrue(all("#" not in h["matched_text"].lstrip()[:1] for h in hits["hits"]))
        # 除外行は filtered_out に監査記録される
        self.assertEqual(len(hits["filtered_out"]), 1)
        self.assertEqual(hits["filtered_out"][0]["reason"], "line-comment")

    def test_search_c_preprocessor_not_filtered(self):
        # .c 内: #define / 参照はいずれも除外されない（漏れゼロ）
        self._write_file("src/x.c", "#define PROCESS_X 1\nint use(){ return PROCESS_X; }\n")
        self._init(symbols="PROCESS_X")
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "wave-0-hits.json")])
        self.assertEqual(result["filter_removed"], 0)
        self.assertEqual(result["hit_count"], 2)

    def test_search_hit_filter_off_keeps_comments(self):
        self._write_file("src/a.py", "# processPayment placeholder\nprocessPayment(x)\n")
        self._init(symbols="processPayment", hit_filter="off")
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "wave-0-hits.json")])
        self.assertEqual(result["hit_count"], 2)
        self.assertEqual(result["filter_removed"], 0)

    def test_search_dedup_skips_classified_location(self):
        self._write_file("src/a.py", "validate(x)\n")
        self._init(symbols="validate")
        data = self._load_state()
        # 過去波で同一スコープ種別（HIGH）で分類済みのロケーションを事前登録
        data["classified_locations"] = ["validate\x00src/a.py\x001\x00HIGH"]
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "wave-0-hits.json")])
        self.assertEqual(result["hit_count"], 0)
        self.assertEqual(result["dedup_removed"], 1)

    def test_search_dedup_key_includes_scope_class(self):
        # HIGH 済みでも MEDIUM スコープの初出は落とさない（ケースA入力保持・scope_class をキーに含む）
        self._write_file("src/a.py", "validate(x)\n")
        self._init(symbols="")
        data = self._load_state()
        data["frontier"] = ["validate[MEDIUM:src/a.py]"]
        data["classified_locations"] = ["validate\x00src/a.py\x001\x00HIGH"]  # HIGH のみ登録済み
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "wave-0-hits.json")])
        # MEDIUM:src/a.py は scope_class が異なるため dedup されない
        self.assertEqual(result["hit_count"], 1)
        self.assertEqual(result["dedup_removed"], 0)

    def test_init_accepts_hit_filter(self):
        self._init(hit_filter="off")
        self.assertEqual(self._load_state()["hit_filter"], "off")

    # -- commit-wave: basic propagation --------------------------------

    def _hits_payload(self, wave, commands, hits, frontier_medium_scopes=None, searched_frontier=None,
                      metrics=None, filtered_out=None):
        payload = {
            "wave": wave, "commands": commands, "hits": hits,
            "frontier_medium_scopes": frontier_medium_scopes or {},
            "searched_frontier": searched_frontier or [],
        }
        if metrics is not None:
            payload["metrics"] = metrics
        if filtered_out is not None:
            payload["filtered_out"] = filtered_out
        return payload

    def test_commit_wave_writes_metrics_and_classified_locations(self):
        self._init(symbols="processPayment")
        hits = self._hits_payload(
            0,
            [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": r"\bprocessPayment\b", "scope": "全域",
              "hit_count": 3, "dedup_removed": 1, "filter_removed": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "processPayment", "scope_file": None,
              "file": "src/billing/handler.py", "line_no": 12, "matched_text": "processPayment(order)"}],
            searched_frontier=["processPayment"],
            metrics={"wave": 0, "search_ms": 5, "raw_hits": 3, "dedup_removed": 1, "filter_removed": 1},
            filtered_out=[{"file": "src/x.py", "line_no": 2, "symbol": "processPayment", "reason": "line-comment"}],
        )
        hits_path = self.root / "wave-0-hits.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [{"line_id": "W0-R1", "classification": "propagation-direct",
                            "next_symbols": [], "enclosing_function": "h", "is_external_api": False}]
        class_path = self.root / "wave-0-class.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        result = self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                             "--classification", str(class_path), "--today", "2026-07-19"])
        self.assertEqual(result["dedup_removed"], 1)
        self.assertEqual(result["filter_removed"], 1)
        # metrics.jsonl が hits と同ディレクトリに1行出力される
        metrics_path = self.root / "metrics.jsonl"
        self.assertTrue(metrics_path.exists())
        m = json.loads(metrics_path.read_text(encoding="utf-8").strip().splitlines()[0])
        self.assertEqual(m["wave"], 0)
        self.assertEqual(m["classified"], 1)
        self.assertEqual(m["dedup_removed"], 1)
        self.assertEqual(m["filter_removed"], 1)
        # classified_locations に scope_class 込みキーが登録される
        data = self._load_state()
        self.assertIn("processPayment\x00src/billing/handler.py\x0012\x00HIGH", data["classified_locations"])
        # 除外行が discovery-log の監査セクションに記録される
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## フィルタ除外一覧", log_text)
        self.assertIn("### 件数一致検証", log_text)
        self.assertIn("| W0-C1 | 3 | 1 | 1 | 0 | 1 | ✅（dedup 1/filter 1/noise-collapse 0 除外） |", log_text)

    def test_commit_wave_basic_propagation_and_confirmed_files(self):
        self._init(symbols="processPayment")
        hits = self._hits_payload(
            0,
            [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": r"\bprocessPayment\b", "scope": "全域", "hit_count": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "processPayment", "scope_file": None,
              "file": "src/billing/handler.py", "line_no": 12, "matched_text": "processPayment(order, amount)"}],
            searched_frontier=["processPayment"],
        )
        hits_path = self.root / "wave-0-hits.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [{"line_id": "W0-R1", "classification": "propagation-direct",
                            "next_symbols": ["handlePaymentRequest"], "enclosing_function": "handlePaymentRequest",
                            "is_external_api": False}]
        class_path = self.root / "wave-0-class.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")

        result = self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                             "--classification", str(class_path), "--today", "2026-07-19"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["next_frontier_count"], 1)
        data = self._load_state()
        self.assertIn("handlePaymentRequest", data["frontier"])
        self.assertIn("processPayment", data["visited"])
        self.assertEqual(data["confirmed_files"]["src/billing/handler.py"]["confidence"], "HIGH")
        self.assertTrue(data["wave_write_complete"])
        self.assertEqual(data["last_completed_wave"], 0)
        self.assertEqual(data["current_wave"], 1)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## Wave 0", log_text)
        self.assertIn("W0-R1", log_text)
        self.assertIn("handlePaymentRequest", log_text)
        self.assertIn("| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | ", log_text)

    def test_commit_wave_false_positive_not_propagated(self):
        self._init(symbols="err")
        hits = self._hits_payload(
            0,
            [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": r"\berr\b", "scope": "全域", "hit_count": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "err", "scope_file": None,
              "file": "src/x.py", "line_no": 3, "matched_text": "# err is a comment mention"}],
            searched_frontier=["err"],
        )
        hits_path = self.root / "h.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [{"line_id": "W0-R1", "classification": "false-positive", "next_symbols": []}]
        class_path = self.root / "c.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        result = self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                             "--classification", str(class_path), "--today", "2026-07-19"])
        self.assertEqual(result["next_frontier_count"], 0)
        data = self._load_state()
        self.assertEqual(data["state"], "complete")

    def test_commit_wave_rejects_missing_classification(self):
        self._init(symbols="foo")
        hits = self._hits_payload(
            0, [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": "foo", "scope": "全域", "hit_count": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "foo", "scope_file": None,
              "file": "a.py", "line_no": 1, "matched_text": "foo()"}],
            searched_frontier=["foo"],
        )
        hits_path = self.root / "h.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        class_path = self.root / "c.json"
        class_path.write_text(json.dumps([]), encoding="utf-8")
        with self.assertRaises(SystemExit):
            self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                       "--classification", str(class_path), "--today", "2026-07-19"])

    def test_commit_wave_rejects_unknown_classification_value(self):
        self._init(symbols="foo")
        hits = self._hits_payload(
            0, [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": "foo", "scope": "全域", "hit_count": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "foo", "scope_file": None,
              "file": "a.py", "line_no": 1, "matched_text": "foo()"}],
            searched_frontier=["foo"],
        )
        hits_path = self.root / "h.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        class_path = self.root / "c.json"
        class_path.write_text(json.dumps([{"line_id": "W0-R1", "classification": "bogus"}]), encoding="utf-8")
        with self.assertRaises(SystemExit):
            self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                       "--classification", str(class_path), "--today", "2026-07-19"])

    # -- HIGH/MEDIUM crossing -------------------------------------------

    def test_high_medium_crossing_blocks_medium_reentry(self):
        self._init(symbols="a")
        data = self._load_state()
        data["visited"] = ["convert"]
        mod._write_state(self.state_path, data)
        hits = self._hits_payload(
            0, [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": "a", "scope": "全域", "hit_count": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "a", "scope_file": None,
              "file": "a.py", "line_no": 1, "matched_text": "a()"}],
            searched_frontier=["a"],
        )
        hits_path = self.root / "h.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [{"line_id": "W0-R1", "classification": "propagation-argument",
                            "next_symbols": ["convert[MEDIUM:b.py]"]}]
        class_path = self.root / "c.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        result = self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                             "--classification", str(class_path), "--today", "2026-07-19"])
        self.assertEqual(result["next_frontier_count"], 0)

    # -- Case A/B/C same-name MEDIUM multi-scope -------------------------

    def test_case_a_promotes_to_high_and_discards_other_scope(self):
        self._init(symbols="")
        data = self._load_state()
        data["frontier"] = ["param[MEDIUM:fileA.py]", "param[MEDIUM:fileB.py]"]
        mod._write_state(self.state_path, data)
        hits = self._hits_payload(
            0,
            [
                {"command_id": "W0-C1", "kind": "MEDIUM", "pattern": "param", "scope": "fileA.py", "hit_count": 1},
                {"command_id": "W0-C2", "kind": "MEDIUM", "pattern": "param", "scope": "fileB.py", "hit_count": 1},
            ],
            [
                {"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "param", "scope_file": "fileA.py",
                 "file": "fileA.py", "line_no": 5, "matched_text": "return param"},
                {"line_id": "W0-R2", "command_id": "W0-C2", "symbol": "param", "scope_file": "fileB.py",
                 "file": "fileB.py", "line_no": 8, "matched_text": "x = param"},
            ],
            frontier_medium_scopes={"param": ["fileA.py", "fileB.py"]},
            searched_frontier=["param[MEDIUM:fileA.py]", "param[MEDIUM:fileB.py]"],
        )
        hits_path = self.root / "h.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [
            {"line_id": "W0-R1", "classification": "propagation-return", "next_symbols": [], "is_external_api": True},
            {"line_id": "W0-R2", "classification": "propagation-direct", "next_symbols": ["x"], "is_external_api": False},
        ]
        class_path = self.root / "c.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        result = self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                             "--classification", str(class_path), "--today", "2026-07-19"])
        self.assertIn("param", result["case_a_promoted"])
        data = self._load_state()
        self.assertIn("param", data["frontier"])
        self.assertNotIn("x", data["frontier"])  # fileB (非トリガースコープ) の結果は廃棄される
        self.assertNotIn("param[MEDIUM:fileA.py]", data["frontier"])
        self.assertNotIn("param[MEDIUM:fileB.py]", data["frontier"])
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("同名 MEDIUM シンボル・異スコープ重複ログ", log_text)
        self.assertIn("A（HIGH昇格）", log_text)
        self.assertIn("➖ 廃棄（ケースA", log_text)
        self.assertIn("`param[MEDIUM:fileA.py]`", log_text)
        self.assertIn("`param[MEDIUM:fileB.py]`", log_text)

    def test_case_b_no_hits_logged(self):
        self._init(symbols="")
        data = self._load_state()
        data["frontier"] = ["value[MEDIUM:h.py]", "value[MEDIUM:p.py]"]
        mod._write_state(self.state_path, data)
        hits = self._hits_payload(
            0,
            [
                {"command_id": "W0-C1", "kind": "MEDIUM", "pattern": "value", "scope": "h.py", "hit_count": 0},
                {"command_id": "W0-C2", "kind": "MEDIUM", "pattern": "value", "scope": "p.py", "hit_count": 0},
            ],
            [],
            frontier_medium_scopes={"value": ["h.py", "p.py"]},
            searched_frontier=["value[MEDIUM:h.py]", "value[MEDIUM:p.py]"],
        )
        hits_path = self.root / "h.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        class_path = self.root / "c.json"
        class_path.write_text(json.dumps([]), encoding="utf-8")
        self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                   "--classification", str(class_path), "--today", "2026-07-19"])
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("B（ヒットなし）", log_text)

    def test_case_c_internal_only_keeps_visited_no_propagation_marker(self):
        self._init(symbols="")
        data = self._load_state()
        data["frontier"] = ["ctx[MEDIUM:a.go]", "ctx[MEDIUM:b.go]"]
        mod._write_state(self.state_path, data)
        hits = self._hits_payload(
            0,
            [
                {"command_id": "W0-C1", "kind": "MEDIUM", "pattern": "ctx", "scope": "a.go", "hit_count": 1},
                {"command_id": "W0-C2", "kind": "MEDIUM", "pattern": "ctx", "scope": "b.go", "hit_count": 1},
            ],
            [
                {"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "ctx", "scope_file": "a.go",
                 "file": "a.go", "line_no": 1, "matched_text": "ctx.Value()"},
                {"line_id": "W0-R2", "command_id": "W0-C2", "symbol": "ctx", "scope_file": "b.go",
                 "file": "b.go", "line_no": 2, "matched_text": "ctx.Done()"},
            ],
            frontier_medium_scopes={"ctx": ["a.go", "b.go"]},
            searched_frontier=["ctx[MEDIUM:a.go]", "ctx[MEDIUM:b.go]"],
        )
        hits_path = self.root / "h.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [
            {"line_id": "W0-R1", "classification": "propagation-direct", "next_symbols": [], "is_external_api": False},
            {"line_id": "W0-R2", "classification": "propagation-direct", "next_symbols": [], "is_external_api": False},
        ]
        class_path = self.root / "c.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                   "--classification", str(class_path), "--today", "2026-07-19"])
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("C（スコープ内参照のみ）", log_text)
        self.assertIn("`ctx[MEDIUM:a.go]`", log_text)
        data = self._load_state()
        self.assertIn("ctx[MEDIUM:a.go]", data["visited"])
        self.assertIn("ctx[MEDIUM:b.go]", data["visited"])

    # -- high noise ------------------------------------------------------

    def test_high_noise_symbol_stops_propagation(self):
        self._init(symbols="log", max_files_per_module=2)
        commands = [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": "log", "scope": "全域", "hit_count": 3}]
        hits = self._hits_payload(
            0, commands,
            [
                {"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "log", "scope_file": None,
                 "file": "f1.py", "line_no": 1, "matched_text": "log(a)"},
                {"line_id": "W0-R2", "command_id": "W0-C1", "symbol": "log", "scope_file": None,
                 "file": "f2.py", "line_no": 1, "matched_text": "log(b)"},
                {"line_id": "W0-R3", "command_id": "W0-C1", "symbol": "log", "scope_file": None,
                 "file": "f3.py", "line_no": 1, "matched_text": "log(c)"},
            ],
            searched_frontier=["log"],
        )
        hits_path = self.root / "h.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [
            {"line_id": "W0-R1", "classification": "propagation-argument", "next_symbols": ["a"]},
            {"line_id": "W0-R2", "classification": "propagation-argument", "next_symbols": ["b"]},
            {"line_id": "W0-R3", "classification": "propagation-argument", "next_symbols": ["c"]},
        ]
        class_path = self.root / "c.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        result = self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                             "--classification", str(class_path), "--today", "2026-07-19"])
        self.assertIn("log", result["high_noise_symbols"])
        self.assertEqual(result["next_frontier_count"], 0)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("高ノイズシンボル", log_text)
        self.assertIn("| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | ", log_text)

    # -- PLAN-20260806 Phase 2A: 前倒し縮退（noise-collapse） --------------

    def test_search_pre_noisy_collapses_to_representative_subset(self):
        for name in ("a", "b", "c", "d", "e"):
            self._write_file(f"m/{name}.py", "log(x)\n")
        self._init(symbols="log", max_files_per_module=3)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h.json")])
        self.assertEqual(result["hit_count"], 3)
        self.assertEqual(result["noise_collapse_removed"], 2)
        self.assertEqual(result["pre_noisy"], ["log"])
        hits = json.loads((self.root / "h.json").read_text(encoding="utf-8"))
        self.assertEqual(hits["pre_noisy"], ["log"])
        self.assertEqual(hits["module_files"]["log"], ["m/a.py", "m/b.py", "m/c.py", "m/d.py", "m/e.py"])
        # 代表サブセットはファイルパス昇順で先頭 max_files_per_module 件・各ファイル最大1行
        self.assertEqual(sorted(h["file"] for h in hits["hits"]), ["m/a.py", "m/b.py", "m/c.py"])
        noise_collapsed = [fo for fo in hits["filtered_out"] if fo["reason"] == "noise-collapse"]
        self.assertEqual(sorted(fo["file"] for fo in noise_collapsed), ["m/d.py", "m/e.py"])

    def test_search_below_threshold_not_pre_noisy(self):
        for name in ("a", "b"):
            self._write_file(f"m/{name}.py", "log(x)\n")
        self._init(symbols="log", max_files_per_module=3)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h.json")])
        self.assertEqual(result["hit_count"], 2)
        self.assertEqual(result["noise_collapse_removed"], 0)
        self.assertEqual(result["pre_noisy"], [])

    def test_2a_confirmed_files_and_frontier_equivalent_to_pre_collapse(self):
        """等価性 fixture（PLAN §3.1 不変条件）: 前倒し縮退（新方式）と、縮退なしで全ヒットを
        そのまま commit-wave に渡した場合（現行相当のシミュレーション）とで、confirmed_files・
        next_frontier が完全一致することを検証する。"""
        files = [f"m/{name}.py" for name in ("a", "b", "c", "d", "e")]
        for f in files:
            self._write_file(f, "log(x)\n")

        # 新方式: 実際に cmd_search（前倒し縮退あり）→ commit-wave を実行
        self._init(symbols="log", max_files_per_module=3)
        search_result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "new-h.json")])
        hits_new = json.loads((self.root / "new-h.json").read_text(encoding="utf-8"))
        classification_new = [
            {"line_id": h["line_id"], "classification": "propagation-argument", "next_symbols": ["helper"]}
            for h in hits_new["hits"]
        ]
        class_path_new = self.root / "new-c.json"
        class_path_new.write_text(json.dumps(classification_new), encoding="utf-8")
        self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(self.root / "new-h.json"),
                   "--classification", str(class_path_new), "--today", "2026-07-19"])
        data_new = self._load_state()

        # 旧方式シミュレーション: 縮退せず全5ヒットをそのまま commit-wave に渡す（pre_noisy/module_files 無し）
        old_state_path = self.root / "old-bfs-state.json"
        old_log_path = self.root / "old-discovery-log.md"
        argv = [
            "init", "--path", str(old_state_path), "--repo-path", str(self.repo),
            "--discovery-log", str(old_log_path), "--symbols", "log",
            "--today", "2026-07-19", "--cr", "CR-2026-999", "--repo", "device-svc",
            "--max-files-per-module", "3",
        ]
        parser = mod.build_parser()
        args = parser.parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        old_hits = [
            {"line_id": f"W0-R{i+1}", "command_id": "W0-C1", "symbol": "log", "scope_file": None,
             "file": f, "line_no": 1, "matched_text": "log(x)"}
            for i, f in enumerate(files)
        ]
        old_payload = self._hits_payload(
            0, [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": "log", "scope": "全域", "hit_count": 5}],
            old_hits, searched_frontier=["log"],
        )
        old_hits_path = self.root / "old-h.json"
        old_hits_path.write_text(json.dumps(old_payload), encoding="utf-8")
        classification_old = [
            {"line_id": h["line_id"], "classification": "propagation-argument", "next_symbols": ["helper"]}
            for h in old_hits
        ]
        old_class_path = self.root / "old-c.json"
        old_class_path.write_text(json.dumps(classification_old), encoding="utf-8")
        args = parser.parse_args(["commit-wave", "--path", str(old_state_path), "--hits", str(old_hits_path),
                                   "--classification", str(old_class_path), "--today", "2026-07-19"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        data_old = json.loads(old_state_path.read_text(encoding="utf-8"))

        self.assertEqual(data_new["confirmed_files"], data_old["confirmed_files"])
        self.assertEqual(sorted(data_new["frontier"]), sorted(data_old["frontier"]))
        self.assertEqual(data_new["state"], data_old["state"])
        self.assertEqual(set(files), set(data_new["confirmed_files"].keys()))

    # -- PLAN-20260806 Phase 2B: catalog 不在時の簡易近傍優先 ---------------

    def test_2b_simple_neighbor_priority_computed_without_catalog(self):
        self._write_file("near/core.py", "def x(): pass\n")
        self._init(symbols="entryFunc")  # module_catalog 未指定
        hits = self._hits_payload(
            0, [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": "entryFunc", "scope": "全域", "hit_count": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "entryFunc", "scope_file": None,
              "file": "near/core.py", "line_no": 1, "matched_text": "entryFunc()"}],
            searched_frontier=["entryFunc"],
        )
        hits_path = self.root / "h.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [{"line_id": "W0-R1", "classification": "propagation-direct", "next_symbols": ["step2"]}]
        class_path = self.root / "c.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                   "--classification", str(class_path), "--today", "2026-07-19"])
        data = self._load_state()
        self.assertTrue(data["module_priority_computed"])
        self.assertEqual(data["module_priority_mode"], "simple")
        self.assertEqual(data["module_priority_map"].get("near"), "HIGH")
        self.assertEqual(data["symbol_module"]["step2"], "near")
        self.assertNotIn("vendor", data["module_priority_map"])

    def test_2b_search_defers_unlisted_module_as_low_and_keeps_it(self):
        self._write_file("near/again.py", "def noise(): pass\n")
        self._init(symbols="")
        data = self._load_state()
        data["frontier"] = ["nearAgain", "step3"]
        data["module_priority_computed"] = True
        data["module_priority_mode"] = "simple"
        data["module_priority_map"] = {"near": "HIGH", "_root": "HIGH"}
        data["symbol_module"] = {"nearAgain": "near", "step3": "vendor"}
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h.json")])
        self.assertTrue(result["ok"])
        # vendor はマップ未掲載（近傍外）→ simple モードでは既定 LOW として退避される（捨てない）。
        # PLAN-20260806 Phase 3 Stage 1 §4.5(g): 退避結果は search が state へ書き戻さず hits の
        # deferred_low に載る（state への反映は commit-wave が行う）ため、検査対象を hits へ移す。
        hits = json.loads((self.root / "h.json").read_text(encoding="utf-8"))
        self.assertIn("step3", hits["deferred_low"])
        self.assertEqual(self._load_state()["low_priority_frontier"], [])

    def test_2b_catalog_mode_unaffected_when_catalog_present(self):
        """既存の catalog 経路は不変（未知ディレクトリの既定は HIGH のまま）。"""
        catalog_text = (
            "## 2. モジュール一覧\n\n"
            "### payment/ — 決済処理\n\n"
            "- **ディレクトリ：** `payment`\n"
            "- **依存先モジュール：** （なし）\n"
            "- **被依存元モジュール：** （なし）\n\n"
            "## 3. シンボル索引\n\n"
            "| シンボル名 | モジュールディレクトリ |\n"
            "|---|---|\n"
        )
        catalog_path = self.root / "module-catalog.md"
        catalog_path.write_text(catalog_text, encoding="utf-8")
        self._init(symbols="")
        data = self._load_state()
        data["frontier"] = ["unknownSym"]
        data["module_priority_computed"] = True
        data["module_priority_mode"] = "catalog"
        data["module_priority_map"] = {"payment": "HIGH"}
        data["symbol_module"] = {"unknownSym": "unlisted_dir"}
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h.json")])
        self.assertTrue(result["ok"])
        data = self._load_state()
        self.assertNotIn("unknownSym", data["low_priority_frontier"])

    # -- prune / merge-frontier / re-discover / import -------------------

    def test_prune_removes_symbol_and_logs(self):
        self._init(symbols="a,b")
        result = self._run(["prune", "--path", str(self.state_path), "--remove", "b", "--reason", "スコープ外"])
        self.assertEqual(result["frontier_count"], 1)
        self.assertIn("Frontier剪定ログ", self.log_path.read_text(encoding="utf-8"))

    def test_prune_requires_reason(self):
        self._init(symbols="a")
        with self.assertRaises(SystemExit):
            self._run(["prune", "--path", str(self.state_path), "--remove", "a", "--reason", ""])

    def test_merge_frontier_dedups(self):
        self._init(symbols="a")
        result = self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "a,c"])
        self.assertEqual(result["added"], ["c"])

    def test_re_discover_requires_complete_state(self):
        self._init(symbols="a")
        with self.assertRaises(SystemExit):
            self._run(["re-discover", "--path", str(self.state_path), "--symbols", "z", "--today", "2026-07-19"])

    def test_re_discover_from_complete(self):
        self._init(symbols="a")
        data = self._load_state()
        data["state"] = "complete"
        data["last_completed_wave"] = 3
        mod._write_state(self.state_path, data)
        result = self._run(["re-discover", "--path", str(self.state_path), "--symbols", "z", "--today", "2026-07-19"])
        self.assertEqual(result["state"], "in-progress")
        self.assertEqual(result["resume_wave"], 4)

    def test_import_from_checkpoint_md(self):
        self._init(symbols="a")
        md_path = self.root / "bfs-state.md"
        new_state_path = self.root / "imported.json"
        result = self._run([
            "import", "--path", str(new_state_path), "--from", str(md_path),
            "--repo-path", str(self.repo), "--discovery-log", str(self.log_path),
        ])
        self.assertTrue(result["ok"])
        self.assertIn("warnings", result)
        self.assertTrue(any("import 警告" in w or "復元" in w for w in result["warnings"]))
        data = json.loads(new_state_path.read_text(encoding="utf-8"))
        self.assertIn("a", data["frontier"])
        # checkpoint.md からは復元できない帳簿が初期化されていることを確認
        self.assertEqual(data["confirmed_files"], {})
        self.assertEqual(data["symbol_origin_map"], {})
        self.assertEqual(data["classified_locations"], [])
        self.assertEqual(data["module_priority_map"], {})
        # discovery-log.md にも警告が記録されていること
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("import 警告", log_text)

    def test_import_from_checkpoint_md_without_discovery_log(self):
        # --discovery-log 省略時も warnings が返り、例外が発生しない
        self._init(symbols="a")
        md_path = self.root / "bfs-state.md"
        new_state_path = self.root / "imported.json"
        result = self._run([
            "import", "--path", str(new_state_path), "--from", str(md_path),
            "--repo-path", str(self.repo),
        ])
        self.assertTrue(result["ok"])
        self.assertIn("warnings", result)
        self.assertTrue(any("import 警告" in w or "復元" in w for w in result["warnings"]))
        self.assertEqual(result["imported_from"], str(md_path))
        data = json.loads(new_state_path.read_text(encoding="utf-8"))
        self.assertIn("a", data["frontier"])

    # -- finish / record-module -------------------------------------------

    def test_finish_out_of_scope_requires_reason(self):
        self._init(symbols="a")
        with self.assertRaises(SystemExit):
            self._run(["finish", "--path", str(self.state_path), "--mode", "out-of-scope", "--today", "2026-07-19"])

    def test_finish_out_of_scope_marks_complete(self):
        self._init(symbols="a")
        result = self._run(["finish", "--path", str(self.state_path), "--mode", "out-of-scope",
                             "--reason", "マイクロサービス境界を越えないため影響なし", "--today", "2026-07-19"])
        self.assertEqual(result["state"], "complete")
        data = self._load_state()
        self.assertEqual(data["frontier"], [])

    def test_finish_complete_records_module_level_files(self):
        self._write_file("payment/core.py", "def process(): pass\n")
        self._write_file("payment/util.py", "def helper(): pass\n")
        self._init(symbols="")
        data = self._load_state()
        data["frontier"] = ["someFunc"]
        data["symbol_module"] = {"someFunc": "payment"}
        mod._write_state(self.state_path, data)
        result = self._run(["finish", "--path", str(self.state_path), "--mode", "complete", "--today", "2026-07-19"])
        self.assertEqual(result["state"], "complete")
        self.assertIn("payment", result["modules"])
        data = self._load_state()
        self.assertEqual(data["confirmed_files"]["payment/core.py"]["confidence"], "MODULE-LEVEL")

    def test_record_module_direct_call(self):
        self._write_file("notify/sender.py", "def send(): pass\n")
        self._init(symbols="")
        result = self._run(["record-module", "--path", str(self.state_path), "--module", "notify", "--today", "2026-07-19"])
        self.assertEqual(result["file_count"], 1)
        data = self._load_state()
        self.assertEqual(data["confirmed_files"]["notify/sender.py"]["confidence"], "MODULE-LEVEL")

    # -- module priority ---------------------------------------------------

    def test_module_priority_computed_after_wave_zero(self):
        catalog_text = (
            "## 2. モジュール一覧\n\n"
            "### payment/ — 決済処理\n\n"
            "- **ディレクトリ：** `payment`\n"
            "- **主要シンボル：** `processPayment`\n"
            "- **依存先モジュール：** `ledger`\n"
            "- **被依存元モジュール：** （なし）\n\n"
            "### ledger/ — 台帳\n\n"
            "- **ディレクトリ：** `ledger`\n"
            "- **依存先モジュール：** （なし）\n"
            "- **被依存元モジュール：** `payment`\n\n"
            "### unrelated/ — 無関係モジュール\n\n"
            "- **ディレクトリ：** `unrelated`\n"
            "- **依存先モジュール：** （なし）\n"
            "- **被依存元モジュール：** （なし）\n\n"
            "## 3. シンボル索引\n\n"
            "| シンボル名 | モジュールディレクトリ |\n"
            "|---|---|\n"
            "| `processPayment` | `payment` |\n"
        )
        catalog_path = self.root / "module-catalog.md"
        catalog_path.write_text(catalog_text, encoding="utf-8")
        self._init(symbols="processPayment", module_catalog=str(catalog_path))
        hits = self._hits_payload(
            0, [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": "processPayment", "scope": "全域", "hit_count": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "processPayment", "scope_file": None,
              "file": "payment/core.py", "line_no": 1, "matched_text": "processPayment(x)"}],
            searched_frontier=["processPayment"],
        )
        hits_path = self.root / "h.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [{"line_id": "W0-R1", "classification": "propagation-direct", "next_symbols": ["settle"]}]
        class_path = self.root / "c.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                   "--classification", str(class_path), "--today", "2026-07-19"])
        data = self._load_state()
        self.assertTrue(data["module_priority_computed"])
        self.assertEqual(data["module_priority_map"]["payment"], "HIGH")
        self.assertEqual(data["module_priority_map"]["ledger"], "HIGH")
        self.assertEqual(data["module_priority_map"]["unrelated"], "LOW")

    def test_search_defers_low_priority_module(self):
        self._write_file("unrelated/thing.py", "def noise(): pass\n")
        self._init(symbols="")
        data = self._load_state()
        data["frontier"] = ["noise", "core"]
        data["module_priority_computed"] = True
        data["module_priority_map"] = {"unrelated": "LOW", "payment": "HIGH"}
        data["symbol_module"] = {"noise": "unrelated", "core": "payment"}
        mod._write_state(self.state_path, data)
        self._write_file("payment/core.py", "def core(): pass\n")
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h.json")])
        self.assertTrue(result["ok"])
        # PLAN-20260806 Phase 3 Stage 1 §4.5(g): 退避結果は hits の deferred_low に載る
        # （state への反映は commit-wave）。LOW 退避が起きること自体の保証は維持する。
        hits = json.loads((self.root / "h.json").read_text(encoding="utf-8"))
        self.assertIn("noise", hits["deferred_low"])
        self.assertEqual(self._load_state()["low_priority_frontier"], [])

    # -- PLAN-20260806 Phase 3 Stage 1 -------------------------------------
    # §4.5(g) cmd_search の非破壊化 / §4.5(c)(d) 分類区間の計測とライフサイクル。

    def _stage1_wave_files(self, wave=0, next_symbols=None, deferred_low=None, symbol="foo"):
        """1ヒットだけの hits / classification を作る（計測・fail-loud テスト用の最小入力）。"""
        hits = self._hits_payload(
            wave,
            [{"command_id": f"W{wave}-C1", "kind": "HIGH複合", "pattern": symbol, "scope": "全域", "hit_count": 1}],
            [{"line_id": f"W{wave}-R1", "command_id": f"W{wave}-C1", "symbol": symbol, "scope_file": None,
              "file": "src/a.py", "line_no": 1, "matched_text": f"{symbol}()"}],
            searched_frontier=[symbol],
        )
        if deferred_low is not None:
            hits["deferred_low"] = deferred_low
        hits_path = self.root / f"wave-{wave}-hits.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [{"line_id": f"W{wave}-R1", "classification": "propagation-direct",
                            "next_symbols": next_symbols or [], "is_external_api": False}]
        class_path = self.root / f"wave-{wave}-class.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        return hits_path, class_path

    def _stage1_commit(self, hits_path, class_path, extra=None):
        return self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                          "--classification", str(class_path), "--today", "2026-07-19"] + (extra or []))

    def _stage1_metrics(self):
        text = (self.root / "metrics.jsonl").read_text(encoding="utf-8").strip()
        return [json.loads(line) for line in text.splitlines()]

    def _stage1_set_state(self, **kw):
        data = self._load_state()
        data.update(kw)
        mod._write_state(self.state_path, data)
        return data

    def _stage1_seed_timer(self, at=1000.0, wave=0):
        return self._stage1_set_state(classify_started_at=at, classify_started_wave=wave)

    # (g) 再 search の冪等性 -------------------------------------------------

    def test_stage1_search_does_not_mutate_frontier_state(self):
        """同一 state に対する2回連続 search で low_priority_frontier が変化せず、
        searched_frontier・line_id・hits が完全一致する（繰り越し LOW の累積 (ii) の回帰検査）。"""
        self._write_file("unrelated/thing.py", "def noise(): pass\n")
        self._write_file("payment/core.py", "def core(): pass\n")
        self._init(symbols="")
        before = self._stage1_set_state(
            frontier=["noise", "core"], low_priority_frontier=["carried"],
            module_priority_computed=True, module_priority_map={"unrelated": "LOW", "payment": "HIGH"},
            symbol_module={"noise": "unrelated", "core": "payment"},
        )
        self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h1.json")])
        after_first = self._load_state()
        self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h2.json")])
        after_second = self._load_state()

        h1 = json.loads((self.root / "h1.json").read_text(encoding="utf-8"))
        h2 = json.loads((self.root / "h2.json").read_text(encoding="utf-8"))
        self.assertEqual(h1["searched_frontier"], ["core"])
        self.assertEqual(h1["searched_frontier"], h2["searched_frontier"])
        self.assertEqual([h["line_id"] for h in h1["hits"]], [h["line_id"] for h in h2["hits"]])
        self.assertEqual(h1["hits"], h2["hits"])
        # 繰り越し分に当波の退避分が1回だけ足される（再実行で累積しない）
        self.assertEqual(h1["deferred_low"], ["carried", "noise"])
        self.assertEqual(h1["deferred_low"], h2["deferred_low"])
        for key in ("frontier", "low_priority_frontier"):
            self.assertEqual(after_first[key], before[key])
            self.assertEqual(after_second[key], before[key])

    def test_stage1_search_idempotent_when_low_frontier_swaps_in(self):
        """`this_wave` が空になり `this_wave, low = low, []` の入れ替えが起きる波でも、
        commit-wave に到達するまで繰り越し LOW が state から失われない（取りこぼし (i) の回帰検査）。"""
        self._write_file("unrelated/thing.py", "def noise(): pass\n")
        self._init(symbols="")
        before = self._stage1_set_state(
            frontier=["noise"], low_priority_frontier=["carried"],
            module_priority_computed=True, module_priority_map={"unrelated": "LOW"},
            symbol_module={"noise": "unrelated"},
        )
        self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h1.json")])
        after_first = self._load_state()
        self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h2.json")])
        after_second = self._load_state()

        h1 = json.loads((self.root / "h1.json").read_text(encoding="utf-8"))
        h2 = json.loads((self.root / "h2.json").read_text(encoding="utf-8"))
        self.assertEqual(h1["searched_frontier"], ["carried", "noise"])
        self.assertEqual(h1["searched_frontier"], h2["searched_frontier"])
        self.assertEqual([h["line_id"] for h in h1["hits"]], [h["line_id"] for h in h2["hits"]])
        self.assertEqual(h1["deferred_low"], [])
        self.assertEqual(h2["deferred_low"], [])
        # 入れ替え後も state 側の繰り越し LOW は保持される（消えない）
        self.assertEqual(after_first["low_priority_frontier"], before["low_priority_frontier"])
        self.assertEqual(after_second["low_priority_frontier"], before["low_priority_frontier"])

    def test_stage1_commit_wave_applies_deferred_low(self):
        """deferred_low が low_priority_frontier へ反映され、complete 判定・discovery-log の
        frontier 行のいずれもが反映**後**の値で行われる（§4.5(g) 適用位置）。"""
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files(deferred_low=["lowSym"])
        self._stage1_commit(hits_path, class_path)
        data = self._load_state()
        self.assertEqual(data["low_priority_frontier"], ["lowSym"])
        # (A) complete 判定: next_frontier は空だが LOW が残るため complete にならない
        self.assertEqual(data["state"], "in-progress")
        # (B) discovery-log の frontier 行: 「探索終了」と書かれない
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertNotIn("→ 空。新規発見なし。探索終了。", log_text)
        self.assertIn("(MODULE_PRIORITY_LOW 分へ移行)", log_text)

    def test_stage1_commit_wave_log_says_complete_when_low_swapped_in(self):
        """入れ替えが起きた波（deferred_low が空）では、繰り越し LOW が state に残っていても
        discovery-log は「探索終了」と書き、complete と整合する（§4.5(g) 適用位置 (ii)）。"""
        self._init(symbols="foo")
        self._stage1_set_state(low_priority_frontier=["carried"])
        hits_path, class_path = self._stage1_wave_files(deferred_low=[])
        self._stage1_commit(hits_path, class_path)
        data = self._load_state()
        self.assertEqual(data["low_priority_frontier"], [])
        self.assertEqual(data["state"], "complete")
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("→ 空。新規発見なし。探索終了。", log_text)
        self.assertNotIn("(MODULE_PRIORITY_LOW 分へ移行)", log_text)

    def test_stage1_commit_wave_keeps_low_frontier_when_deferred_low_absent(self):
        """deferred_low キーが無い hits（旧形式）では既存値を変更しない（安全側の既定）。"""
        self._init(symbols="foo")
        self._stage1_set_state(low_priority_frontier=["carried"])
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_commit(hits_path, class_path)
        self.assertEqual(self._load_state()["low_priority_frontier"], ["carried"])

    # (c)(d) 分類区間の計測 --------------------------------------------------

    def test_stage1_classify_wall_ms_recorded_and_timer_consumed(self):
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_seed_timer(at=1000.0, wave=0)
        with patch.object(mod.time, "time", return_value=1002.5):
            self._stage1_commit(hits_path, class_path)
        m = self._stage1_metrics()[0]
        self.assertEqual(m["classify_wall_ms"], 2500)
        self.assertFalse(m["classify_wall_ms_suspect"])
        self.assertFalse(m["classify_wall_ms_reused"])
        # ゲート判定に使う既存キー（post-dedup/filter の実分類行数）が併記されている
        self.assertEqual(m["classified"], 1)
        # 消費後破棄（次波の search が再度書く）
        data = self._load_state()
        self.assertNotIn("classify_started_at", data)
        self.assertNotIn("classify_started_wave", data)

    def test_stage1_classify_wall_ms_suspect_true_over_threshold(self):
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_seed_timer(at=1000.0, wave=0)
        over = 1000.0 + (mod.CLASSIFY_WALL_MS_SUSPECT_THRESHOLD_MS / 1000.0) + 1
        with patch.object(mod.time, "time", return_value=over):
            self._stage1_commit(hits_path, class_path)
        m = self._stage1_metrics()[0]
        self.assertGreater(m["classify_wall_ms"], mod.CLASSIFY_WALL_MS_SUSPECT_THRESHOLD_MS)
        self.assertTrue(m["classify_wall_ms_suspect"])

    def test_stage1_classify_wall_ms_null_when_timer_missing(self):
        """2キー欠損時は null フォールバックし、commit-wave は落ちない。
        suspect は false ではなく null（値なしと閾値内を集計側で区別するため）。"""
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_commit(hits_path, class_path)
        m = self._stage1_metrics()[0]
        self.assertIsNone(m["classify_wall_ms"])
        self.assertIsNone(m["classify_wall_ms_suspect"])
        self.assertIsNone(m["classify_wall_ms_reused"])

    def test_stage1_classify_wall_ms_null_on_started_wave_mismatch(self):
        """α＝開始時刻の波不一致（classify_started_wave != wave）。β（hits の波不一致）とは別物であり、
        β は exit 非0 で metrics 行そのものが出ないため α の検証にはならない。"""
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files(wave=0)
        self._stage1_seed_timer(at=1000.0, wave=5)  # state を直接書き換えて α を再現する
        self._stage1_commit(hits_path, class_path)
        m = self._stage1_metrics()[0]
        self.assertIsNone(m["classify_wall_ms"])
        self.assertIsNone(m["classify_wall_ms_reused"])
        self.assertIsNone(m["classify_wall_ms_suspect"])
        data = self._load_state()
        self.assertNotIn("classify_started_at", data)

    def test_stage1_classify_wall_ms_reused_when_classification_predates_search(self):
        """再利用波の判定（過小計測の防止）: classification の mtime < classify_started_at なら
        reused=true / classify_wall_ms=null（§4.9 の集計から除外できる）。"""
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        started_at = mod.time.time()
        os.utime(class_path, (started_at - 100, started_at - 100))
        self._stage1_seed_timer(at=started_at, wave=0)
        self._stage1_commit(hits_path, class_path)
        m = self._stage1_metrics()[0]
        self.assertTrue(m["classify_wall_ms_reused"])
        self.assertIsNone(m["classify_wall_ms"])
        self.assertIsNone(m["classify_wall_ms_suspect"])

    def test_stage1_classify_wall_ms_reused_null_when_mtime_unavailable(self):
        """mtime が取得できない場合は reused=null とし、classify_wall_ms は通常どおり算出する
        （計測専用であり correctness に関与しないため commit-wave を失敗させない）。"""
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_seed_timer(at=1000.0, wave=0)
        with patch.object(mod, "_file_mtime", return_value=None), \
             patch.object(mod.time, "time", return_value=1001.0):
            self._stage1_commit(hits_path, class_path)
        m = self._stage1_metrics()[0]
        self.assertIsNone(m["classify_wall_ms_reused"])
        self.assertEqual(m["classify_wall_ms"], 1000)

    def test_stage1_chunk_metrics_default_to_one(self):
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_commit(hits_path, class_path)
        m = self._stage1_metrics()[0]
        self.assertEqual((m["chunk_count"], m["batch_count"], m["parallelism"]), (1, 1, 1))

    def test_stage1_chunk_metrics_record_passed_values(self):
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_commit(hits_path, class_path,
                            extra=["--chunk-count", "5", "--batch-count", "2", "--parallelism", "4"])
        m = self._stage1_metrics()[0]
        self.assertEqual((m["chunk_count"], m["batch_count"], m["parallelism"]), (5, 2, 4))

    # (c) ライフサイクル: 削除する経路／削除しない経路 -----------------------

    def test_stage1_wave_limit_pause_drops_classify_timer(self):
        """波数上限の早期 return では2キーを書かず、既存の2キーを削除する。"""
        self._init(max_wave=1)
        self._stage1_set_state(current_wave=2, classify_started_at=1000.0, classify_started_wave=1)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "x.json")])
        self.assertTrue(result["paused"])
        data = self._load_state()
        self.assertNotIn("classify_started_at", data)
        self.assertNotIn("classify_started_wave", data)

    def test_stage1_finish_drops_classify_timer(self):
        self._init(symbols="a")
        self._stage1_seed_timer()
        self._run(["finish", "--path", str(self.state_path), "--mode", "out-of-scope",
                   "--reason", "スコープ外", "--today", "2026-07-19"])
        self.assertNotIn("classify_started_at", self._load_state())

    def test_stage1_re_discover_drops_classify_timer(self):
        self._init(symbols="a")
        self._stage1_set_state(state="complete", last_completed_wave=3,
                                classify_started_at=1000.0, classify_started_wave=3)
        self._run(["re-discover", "--path", str(self.state_path), "--symbols", "z", "--today", "2026-07-19"])
        self.assertNotIn("classify_started_at", self._load_state())

    def test_stage1_prune_drops_classify_timer(self):
        self._init(symbols="a,b")
        self._stage1_seed_timer()
        self._run(["prune", "--path", str(self.state_path), "--remove", "b", "--reason", "スコープ外"])
        self.assertNotIn("classify_started_at", self._load_state())

    def test_stage1_set_state_drops_classify_timer(self):
        self._init(symbols="a")
        self._stage1_seed_timer()
        self._run(["set-state", "--path", str(self.state_path), "--state", "in-progress"])
        self.assertNotIn("classify_started_at", self._load_state())

    def test_stage1_merge_frontier_and_record_module_keep_classify_timer(self):
        """いずれも波を進めないため、その波の分類区間は継続中とみなして2キーを保持する。"""
        self._write_file("notify/sender.py", "def send(): pass\n")
        self._init(symbols="a")
        self._stage1_seed_timer()
        self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "c"])
        data = self._load_state()
        self.assertEqual(data["classify_started_at"], 1000.0)
        self.assertEqual(data["classify_started_wave"], 0)
        self._run(["record-module", "--path", str(self.state_path), "--module", "notify", "--today", "2026-07-19"])
        data = self._load_state()
        self.assertEqual(data["classify_started_at"], 1000.0)
        self.assertEqual(data["classify_started_wave"], 0)

    def test_stage1_import_does_not_restore_classify_timer(self):
        """import は _default_state() から再構築するため2キーは復元されない（仕様として固定）。"""
        self._init(symbols="a")
        self._stage1_seed_timer()
        new_state_path = self.root / "imported.json"
        self._run(["import", "--path", str(new_state_path), "--from", str(self.root / "bfs-state.md"),
                   "--repo-path", str(self.repo), "--discovery-log", str(self.log_path)])
        data = json.loads(new_state_path.read_text(encoding="utf-8"))
        self.assertNotIn("classify_started_at", data)
        self.assertNotIn("classify_started_wave", data)

    # (g) コミット妥当性の fail-loud（条件1〜3）------------------------------

    def test_stage1_commit_wave_rejects_wave_mismatch(self):
        """条件1（β＝hits の波不一致）。検証は _truncate_wave_section より前で行われるため、
        切り捨て対象の `## Wave 2` セクションが残存する。"""
        self._init(symbols="foo")
        before = self._stage1_set_state(current_wave=5, wave_write_complete=False,
                                         frontier=["f"], low_priority_frontier=["keepme"])
        mod._append_to_file(self.log_path, "\n## Wave 2\n\n書きかけ\n\n## Wave 3\n\n確定済み\n")
        hits_path, class_path = self._stage1_wave_files(wave=2, next_symbols=["revived"],
                                                        deferred_low=["stale"])
        with self.assertRaises(SystemExit):
            self._stage1_commit(hits_path, class_path)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## Wave 2", log_text)
        self.assertIn("## Wave 3", log_text)
        after = self._load_state()
        self.assertEqual(after["low_priority_frontier"], before["low_priority_frontier"])
        self.assertEqual(after["frontier"], before["frontier"])
        self.assertEqual(after["current_wave"], 5)
        self.assertFalse((self.root / "metrics.jsonl").exists())

    def test_stage1_commit_wave_rejects_recommit_after_finish(self):
        """条件2（state == complete）が単独で成立する state。当該波の search 後に finish した場合、
        cmd_finish は wave_write_complete / last_completed_wave / current_wave を触らないため
        条件1・3 はいずれも不成立であり、条件2 を落とすとこの経路が素通りする。"""
        self._init(symbols="foo")
        before = self._stage1_set_state(current_wave=1, last_completed_wave=0, wave_write_complete=False,
                                         state="complete", frontier=[], low_priority_frontier=[])
        # 書きかけ Wave セクションの後ろに継続パス C の監査記録がある状態を作る
        mod._append_to_file(self.log_path, "\n## Wave 1\n\n書きかけ\n")
        mod._append_to_file(self.log_path, "\n---\n## 継続パス C（残存フロンティアをスコープ外として承認）\n- 根拠: 境界外\n")
        # 伝播を生む classification（条件2 が無いと frontier が復活する入力）
        hits_path, class_path = self._stage1_wave_files(wave=1, next_symbols=["revived"], deferred_low=["stale"])
        with self.assertRaises(SystemExit):
            self._stage1_commit(hits_path, class_path)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## 継続パス C", log_text)   # 切り捨てが起きていない
        self.assertIn("## Wave 1", log_text)
        after = self._load_state()
        self.assertEqual(after["frontier"], before["frontier"])            # frontier が復活しない
        self.assertEqual(after["low_priority_frontier"], before["low_priority_frontier"])
        self.assertEqual(after["state"], "complete")

    def test_stage1_commit_wave_rejects_recommit_of_completed_wave(self):
        """条件3（wave <= last_completed_wave）が単独で成立する state。
        set-state 相当で in-progress へ戻しているため条件2 は不成立、波は一致するため条件1 も不成立。
        （wave_write_complete = False の版は test_commit_wave_rejects_recommit_of_completed_wave が担う。
        PLAN-20260808 で条件3 から wave_write_complete の連言を外したため両値で成立する。）"""
        self._init(symbols="foo")
        self._stage1_set_state(current_wave=0, last_completed_wave=0, wave_write_complete=True,
                                state="in-progress")
        hits_path, class_path = self._stage1_wave_files(wave=0)
        with self.assertRaises(SystemExit):
            self._stage1_commit(hits_path, class_path)
        self.assertNotIn("## Wave 0", self.log_path.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "metrics.jsonl").exists())

    def test_stage1_final_wave_recommit_does_not_duplicate_records(self):
        """最終波（BFS を完了させた波）は current_wave が進まないため条件1 では捕捉できない。
        条件2・3 のいずれかが効いていれば discovery-log・metrics.jsonl の二重追記は起きない
        （挙動テストであり、個々の条件の検査は上記2件が担う）。"""
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_commit(hits_path, class_path)
        self.assertEqual(self._load_state()["state"], "complete")
        with self.assertRaises(SystemExit):
            self._stage1_commit(hits_path, class_path)
        self.assertEqual(len(self._stage1_metrics()), 1)
        self.assertEqual(self.log_path.read_text(encoding="utf-8").count("## Wave 0"), 1)

    # -- PLAN-20260808 不具合1（Markdown セルのエスケープ）-------------------

    @staticmethod
    def _cells(line: str) -> list:
        """discovery-log のテーブル行をセルへ分割する（specout_verify_counts._split_row と同一規約）。"""
        return re.split(r"(?<!\\)\|", line.strip())[1:-1]

    def _table_rows(self, text: str):
        """(ヘッダ列数, データ行の列数, 行内容) を全テーブル・全データ行について yield する。

        注記 blockquote（`> ` 始まり）は `\\|` を含むためテーブル行として数えない。
        """
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            is_sep = (i + 1 < len(lines)
                      and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1])
                      and "-" in lines[i + 1])
            if line.startswith("|") and is_sep:
                header_cols = len(self._cells(line))
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    yield header_cols, len(self._cells(lines[j])), lines[j]
                    j += 1
                i = j
                continue
            i += 1

    def test_md_cell_escapes_pipe_and_newline(self):
        self.assertEqual(mod._md_cell("a |= b"), r"a \|= b")
        self.assertEqual(mod._md_cell(r"\b(A|B|C)\b"), r"\b(A\|B\|C)\b")
        self.assertEqual(mod._md_cell("x\ny\rz"), "x y z")
        self.assertEqual(mod._md_cell(None), "")
        self.assertEqual(mod._md_cell(12), "12")

    def test_commit_wave_escapes_pipe_in_match_content(self):
        """マッチ内容にソースコードの生 `|` が入っても、ヒット行テーブルの列数が壊れない。"""
        self._init(symbols="expire_flags")
        hits = self._hits_payload(
            0,
            [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": r"\bexpire_flags\b", "scope": "全域",
              "hit_count": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "expire_flags", "scope_file": None,
              "file": "src/db.c", "line_no": 295,
              "matched_text": "    expire_flags |= EXPIRE_FORCE_DELETE_EXPIRED;"}],
            searched_frontier=["expire_flags"],
        )
        hits_path = self.root / "wave-0-hits.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        class_path = self.root / "wave-0-class.json"
        class_path.write_text(json.dumps([{"line_id": "W0-R1", "classification": "propagation-direct",
                                            "next_symbols": [], "is_external_api": False}]), encoding="utf-8")
        self._stage1_commit(hits_path, class_path)
        text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(r"expire_flags \|= EXPIRE_FORCE_DELETE_EXPIRED;", text)
        for header_cols, row_cols, line in self._table_rows(text):
            self.assertEqual(row_cols, header_cols, f"列数不一致: {line}")

    def test_commit_wave_escapes_pipe_in_command_pattern(self):
        """HIGH 複合パターン `\\b(A|B|C)\\b` を含む実行コマンド一覧の行が5セルに収まる。"""
        self._init(symbols="alpha")
        hits = self._hits_payload(
            0,
            [{"command_id": "W0-C1", "kind": "HIGH複合", "pattern": r"\b(alpha|beta|gamma)\b",
              "scope": "全域", "hit_count": 0}],
            [],
            searched_frontier=["alpha"],
        )
        hits_path = self.root / "wave-0-hits.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        class_path = self.root / "wave-0-class.json"
        class_path.write_text(json.dumps([]), encoding="utf-8")
        self._stage1_commit(hits_path, class_path)
        text = self.log_path.read_text(encoding="utf-8")
        cmd_line = next(l for l in text.split("\n") if l.startswith("| W0-C1 |"))
        self.assertEqual(len(self._cells(cmd_line)), 5)
        self.assertIn(r"\b(alpha\|beta\|gamma)\b", cmd_line)

    def _all_tables_commit(self):
        """§3.1 の7テーブルすべてが出力される commit-wave を1回実行する（各セルに生 `|` を含む）。"""
        self._init(symbols="foo", max_files_per_module=1)
        commands = [
            # 高ノイズ判定用（2ファイル > max_files_per_module=1）
            {"command_id": "W0-C1", "kind": "HIGH複合", "pattern": r"\b(noisy|other)\b", "scope": "全域",
             "hit_count": 2},
            # ケースB（同名 MEDIUM・異スコープ・ヒットなし）用
            {"command_id": "W0-C2", "kind": "MEDIUM", "pattern": "param", "scope": "src/a|x.py",
             "hit_count": 0},
            {"command_id": "W0-C3", "kind": "MEDIUM", "pattern": "param", "scope": "src/b.py",
             "hit_count": 0},
        ]
        hits = self._hits_payload(
            0, commands,
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "noisy", "scope_file": None,
              "file": "src/x.c", "line_no": 1, "matched_text": "noisy |= FLAG_A;"},
             {"line_id": "W0-R2", "command_id": "W0-C1", "symbol": "noisy", "scope_file": None,
              "file": "src/y.c", "line_no": 2, "matched_text": "noisy |= FLAG_B;"}],
            frontier_medium_scopes={"param": ["src/a|x.py", "src/b.py"]},
            searched_frontier=["noisy", "param[MEDIUM:src/a|x.py]", "param[MEDIUM:src/b.py]"],
            filtered_out=[{"file": "src/z|1.c", "line_no": 9, "symbol": "noisy|alias",
                            "reason": "line-comment"}],
        )
        hits_path = self.root / "wave-0-hits.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [
            {"line_id": "W0-R1", "classification": "propagation-direct", "next_symbols": [],
             "is_external_api": False},
            {"line_id": "W0-R2", "classification": "propagation-direct", "next_symbols": [],
             "is_external_api": False},
        ]
        class_path = self.root / "wave-0-class.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        self._stage1_commit(hits_path, class_path)
        return self.log_path.read_text(encoding="utf-8")

    def test_commit_wave_all_tables_have_consistent_column_counts(self):
        """§3.1 の7テーブルすべてについて、全データ行の列数がヘッダと一致する。"""
        text = self._all_tables_commit()
        # 7テーブルすべてが出力されていること（検査対象の網羅を保証する）
        for heading in ("### 実行コマンド一覧", "### 件数一致検証",
                        "## 高ノイズシンボル（上限超過のため波及停止）",
                        "## 同名 MEDIUM シンボル・異スコープ重複ログ（発生時のみ記録）",
                        "## フィルタ除外一覧（Wave 0・監査用）",
                        "## 確定した波及ファイル一覧（Documentation チェックリスト）"):
            self.assertIn(heading, text)
        self.assertIn("| 行ID | コマンドID |", text)  # ヒット行テーブル
        checked = 0
        for header_cols, row_cols, line in self._table_rows(text):
            self.assertEqual(row_cols, header_cols, f"列数不一致: {line}")
            checked += 1
        self.assertGreater(checked, 0)

    def test_cell_notation_notes_are_followed_by_blank_line(self):
        """注記 blockquote の直後は必ず空行（GFM の lazy continuation でテーブルが壊れないこと）。"""
        text = self._all_tables_commit()
        lines = text.split("\n")
        note_lines = [i for i, l in enumerate(lines) if l.startswith("> ")]
        self.assertGreaterEqual(len(note_lines), 3)  # 配置2（4行）＋配置3（1行）＋配置5（4行）
        for i in note_lines:
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if nxt.startswith("> "):
                continue  # blockquote の継続行
            self.assertEqual(nxt.strip(), "", f"注記の直後が空行ではない: {lines[i]!r} → {nxt!r}")

    def test_parse_module_catalog_unescapes_pipe(self):
        """(F) シンボル索引セルの `\\|` が区切りと誤認されず、値のエスケープが戻る。"""
        catalog = (
            "## 3. シンボル索引\n"
            "| シンボル名 | モジュールディレクトリ |\n"
            "|---|---|\n"
            r"| `a\|b` | src/mod |" "\n"
        )
        _, _, _, symbol_to_module = mod._parse_module_catalog(catalog)
        self.assertEqual(symbol_to_module.get("a|b"), "src/mod")

    # -- PLAN-20260808 不具合2（完了済み波の再突入ガード）--------------------

    def _run_expect_err(self, argv) -> str:
        """コマンドが exit 非0 で停止することを確認し、stderr の内容を返す。"""
        buf = io.StringIO()
        parser = mod.build_parser()
        args = parser.parse_args(argv)
        with redirect_stderr(buf), self.assertRaises(SystemExit) as cm:
            args.func(args)
        self.assertNotEqual(cm.exception.code, 0)
        return buf.getvalue()

    def test_search_rejects_wave_at_or_below_last_completed(self):
        """一次防御（§3.25）: commit-wave 済みの波へ set-state で戻した後の search が分類前に止まる。"""
        self._write_file("src/a.py", "def foo(): pass\n")
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_commit(hits_path, class_path)
        data = self._load_state()
        self.assertEqual(data["current_wave"], data["last_completed_wave"])
        self._run(["set-state", "--path", str(self.state_path), "--state", "in-progress"])
        self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "bar"])
        err = self._run_expect_err(["search", "--path", str(self.state_path),
                                     "--hits-out", str(self.root / "h.json")])
        self.assertIn("last_completed_wave", err)
        self.assertFalse((self.root / "h.json").exists())

    def test_search_allows_normal_and_crash_resume_waves(self):
        """非回帰（§3.25）: Wave 0 初回・通常の次波・クラッシュ再開のいずれも search が成功する。"""
        self._write_file("src/a.py", "def foo(): pass\n")
        self._init(symbols="foo")
        # (1) Wave 0 初回（last_completed_wave = -1）
        self.assertEqual(self._load_state()["last_completed_wave"], -1)
        self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h0.json")])
        # (2) クラッシュ再開（同じ波を再 search）
        self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h0b.json")])
        # (3) 通常の次波（current_wave = last_completed_wave + 1）
        self._stage1_set_state(current_wave=1, last_completed_wave=0, wave_write_complete=True,
                                state="in-progress", frontier=["foo"])
        self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h1.json")])
        for name in ("h0.json", "h0b.json", "h1.json"):
            self.assertTrue((self.root / name).exists())

    def test_search_allows_prune_resume_from_paused_at_limit(self):
        """非回帰（§3.25）: 継続パス A（paused-at-limit → prune → search）がガードに掛からない。"""
        self._write_file("src/a.py", "def foo(): pass\n")
        self._init(symbols="foo")
        self._stage1_set_state(current_wave=2, last_completed_wave=1, wave_write_complete=True,
                                state="paused-at-limit", frontier=["foo", "drop"])
        self._run(["prune", "--path", str(self.state_path), "--remove", "drop", "--reason", "高ノイズ"])
        self.assertEqual(self._load_state()["state"], "in-progress")
        self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h.json")])
        self.assertTrue((self.root / "h.json").exists())

    def test_commit_wave_rejects_recommit_of_completed_wave(self):
        """二次防御（§3.2・条件3）: wave_write_complete=False でも完了済みの波は再コミットできず、
        確定済みの `## Wave N` セクションが切り捨てられない。"""
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_commit(hits_path, class_path)
        before = self.log_path.read_text(encoding="utf-8")
        wave_lines_before = before.split("## Wave 0", 1)[1]
        # search が wave_write_complete を False にした状態を直接組む
        # （search 自体は §3.25 のガードで止まるため経由できない）
        self._stage1_set_state(current_wave=0, last_completed_wave=0, wave_write_complete=False,
                                state="in-progress")
        self._run_expect_err(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                               "--classification", str(class_path), "--today", "2026-07-19"])
        after = self.log_path.read_text(encoding="utf-8")
        self.assertEqual(after.count("## Wave 0"), 1)
        self.assertEqual(after.split("## Wave 0", 1)[1], wave_lines_before)
        self.assertEqual(len(self._stage1_metrics()), 1)

    def test_commit_wave_allows_recommit_after_crash_before_commit(self):
        """非回帰: wave == current_wave > last_completed_wave（search 済み・commit 未完）は成功する。"""
        self._write_file("src/a.py", "def foo(): pass\n")
        self._init(symbols="foo")
        self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h.json")])
        self.assertFalse(self._load_state()["wave_write_complete"])
        hits_path, class_path = self._stage1_wave_files()
        result = self._stage1_commit(hits_path, class_path)
        self.assertTrue(result["ok"])

    def test_commit_wave_allows_first_wave_zero_commit(self):
        """非回帰: last_completed_wave = -1 の初回 Wave 0 コミットが成功する。"""
        self._init(symbols="foo")
        self.assertEqual(self._load_state()["last_completed_wave"], -1)
        hits_path, class_path = self._stage1_wave_files()
        result = self._stage1_commit(hits_path, class_path)
        self.assertTrue(result["ok"])
        self.assertEqual(self._load_state()["last_completed_wave"], 0)

    def test_commit_wave_complete_message_recommends_re_discover_only(self):
        """条件2 のメッセージが set-state を再開手段として推奨せず re-discover に一本化されている。"""
        self._init(symbols="foo")
        self._stage1_set_state(current_wave=1, last_completed_wave=0, wave_write_complete=False,
                                state="complete", frontier=[])
        hits_path, class_path = self._stage1_wave_files(wave=1)
        err = self._run_expect_err(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                                     "--classification", str(class_path), "--today", "2026-07-19"])
        self.assertIn("re-discover", err)
        self.assertNotIn("set-state", err)

    def test_guard_messages_embed_real_state_path(self):
        """条件3・search ガードの停止メッセージに実 --path が入り、プレースホルダが残らない。"""
        self._write_file("src/a.py", "def foo(): pass\n")
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_commit(hits_path, class_path)
        self._stage1_set_state(current_wave=0, last_completed_wave=0, wave_write_complete=False,
                                state="in-progress", frontier=["foo"])
        commit_err = self._run_expect_err(
            ["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
             "--classification", str(class_path), "--today", "2026-07-19"])
        search_err = self._run_expect_err(
            ["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h.json")])
        for err in (commit_err, search_err):
            self.assertIn(str(self.state_path), err)
            self.assertNotIn("{PATH}", err)
            self.assertIn("set-state", err)      # complete へ戻す手順
            self.assertIn("re-discover", err)

    # -- PLAN-20260806 Phase 3 Stage 2 -------------------------------------
    # (a) known_symbols 配布 / (b) チャンク分割 / (e) --unsupported-patterns / (f) status --brief
    # / §4.5(d)〔S2〕 --chunk-mtime-min。

    def test_search_hits_out_and_hits_dir_mutually_exclusive(self):
        self._init(symbols="foo")
        with self.assertRaises(SystemExit):
            self._run(["search", "--path", str(self.state_path)])
        with self.assertRaises(SystemExit):
            self._run(["search", "--path", str(self.state_path),
                       "--hits-out", str(self.root / "a.json"),
                       "--hits-dir", str(self.root)])

    def test_search_hits_dir_builds_wave_hits_path(self):
        self._write_file("src/a.py", "def foo(): pass\n")
        self._init(symbols="foo")
        out_dir = self.root / "out"
        result = self._run(["search", "--path", str(self.state_path), "--hits-dir", str(out_dir)])
        expected = out_dir / "wave-0-hits.json"
        self.assertEqual(result["hits_file"], str(expected))
        self.assertTrue(expected.exists())

    def test_search_known_symbols_normalizes_medium_scope(self):
        """§4.1: visited/searched_frontier の MEDIUM エントリは素名へ正規化して複製配布される。"""
        self._write_file("src/a.py", "def f():\n    return validate(x)\n")
        self._init(symbols="")
        self._stage1_set_state(
            visited=["processed", "helper[MEDIUM:src/old.py]"],
            frontier=["validate[MEDIUM:src/a.py]"],
        )
        result = self._run(["search", "--path", str(self.state_path),
                            "--hits-out", str(self.root / "h.json")])
        self.assertTrue(result["ok"])
        hits = json.loads((self.root / "h.json").read_text(encoding="utf-8"))
        ks = hits["known_symbols"]
        self.assertEqual(ks["visited"], ["helper", "processed"])
        self.assertEqual(ks["searched_frontier"], ["validate"])
        self.assertEqual(ks["current_wave"], ["validate"])

    def test_split_hits_into_chunks_no_split_below_threshold(self):
        hits = [{"line_id": "W0-R1", "file": "a.py"}]
        self.assertEqual(mod._split_hits_into_chunks(hits, chunk_size=0), [hits])
        self.assertEqual(mod._split_hits_into_chunks(hits, chunk_size=40), [hits])
        self.assertEqual(mod._split_hits_into_chunks([], chunk_size=40), [[]])

    def test_split_hits_into_chunks_groups_by_file_with_no_loss(self):
        hits = [
            {"line_id": "W0-R1", "file": "a.py"},
            {"line_id": "W0-R2", "file": "a.py"},
            {"line_id": "W0-R3", "file": "b.py"},
            {"line_id": "W0-R4", "file": "b.py"},
            {"line_id": "W0-R5", "file": "b.py"},
            {"line_id": "W0-R6", "file": "c.py"},
        ]
        chunks = mod._split_hits_into_chunks(hits, chunk_size=2)
        all_ids = [h["line_id"] for chunk in chunks for h in chunk]
        # 全 line_id がちょうど1チャンクに属する（欠落・重複ゼロ）
        self.assertEqual(sorted(all_ids), sorted(h["line_id"] for h in hits))
        self.assertEqual(len(all_ids), len(hits))
        # 同一ファイルのヒットは同一チャンクに入る（1ファイルが chunk_size を超える b.py は単独チャンク化）
        by_file = {}
        for chunk in chunks:
            for h in chunk:
                by_file.setdefault(h["file"], set()).add(id(chunk))
        for chunk_ids in by_file.values():
            self.assertEqual(len(chunk_ids), 1)
        b_chunk = next(c for c in chunks if any(h["file"] == "b.py" for h in c))
        self.assertEqual(len(b_chunk), 3)

    def test_search_chunks_single_when_chunk_size_zero(self):
        self._write_file("src/a.py", "def foo(): pass\nfoo()\n")
        self._init(symbols="foo")
        result = self._run(["search", "--path", str(self.state_path),
                            "--hits-out", str(self.root / "wave-0-hits.json")])
        self.assertEqual(result["chunk_count"], 1)
        self.assertEqual(len(result["chunks"]), 1)
        chunk_path = Path(result["chunks"][0])
        self.assertTrue(chunk_path.exists())
        chunk = json.loads(chunk_path.read_text(encoding="utf-8"))
        self.assertEqual(chunk["chunk_id"], "W0-K0")
        self.assertEqual(len(chunk["hits"]), result["hit_count"])
        self.assertIn("known_symbols", chunk)
        self.assertIn("commands", chunk)

    def test_search_chunk_contains_only_referenced_commands_subset(self):
        self._write_file("a.py", "foo()\n")
        self._write_file("b.py", "foo()\n")
        self._init(symbols="foo")
        result = self._run(["search", "--path", str(self.state_path),
                            "--hits-out", str(self.root / "wave-0-hits.json"),
                            "--chunk-size", "1"])
        self.assertGreaterEqual(result["chunk_count"], 2)
        for chunk_path in result["chunks"]:
            chunk = json.loads(Path(chunk_path).read_text(encoding="utf-8"))
            cmd_ids_in_chunk = {c["command_id"] for c in chunk["commands"]}
            hit_cmd_ids = {h["command_id"] for h in chunk["hits"]}
            self.assertEqual(cmd_ids_in_chunk, hit_cmd_ids)

    def test_search_removes_stale_chunk_files_on_rerun(self):
        self._write_file("a.py", "foo()\n")
        self._write_file("b.py", "foo()\n")
        self._init(symbols="foo")
        out_dir = self.root / "out"
        self._run(["search", "--path", str(self.state_path), "--hits-dir", str(out_dir), "--chunk-size", "1"])
        first = sorted(out_dir.glob("wave-0-hits-chunk-*.json"))
        self.assertEqual(len(first), 2)
        self._run(["search", "--path", str(self.state_path), "--hits-dir", str(out_dir), "--chunk-size", "0"])
        second = sorted(out_dir.glob("wave-0-hits-chunk-*.json"))
        self.assertEqual(len(second), 1)

    def test_status_brief_returns_minimal_keys(self):
        self._init(symbols="foo")
        self._stage1_set_state(frontier=["a", "b"], low_priority_frontier=["c"])
        result = self._run(["status", "--path", str(self.state_path), "--brief"])
        self.assertEqual(set(result.keys()),
                          {"ok", "state", "current_wave", "wave_write_complete", "remaining_frontier_count",
                           "confirmed_file_count"})
        self.assertEqual(result["remaining_frontier_count"], 3)
        self.assertEqual(result["confirmed_file_count"], 0)

    def test_status_brief_counts_low_priority_only_remainder(self):
        """§4.5(f): frontier が空でも low_priority_frontier が残る repo を 0 と誤判定しない。"""
        self._init(symbols="foo")
        self._stage1_set_state(frontier=[], low_priority_frontier=["only-low"])
        result = self._run(["status", "--path", str(self.state_path), "--brief"])
        self.assertEqual(result["remaining_frontier_count"], 1)

    def test_status_without_brief_returns_full_state(self):
        self._init(symbols="foo")
        result = self._run(["status", "--path", str(self.state_path)])
        self.assertIn("visited", result)
        self.assertIn("confirmed_files", result)

    def test_commit_wave_unsupported_patterns_inserted_in_header_section(self):
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        unsupported = [{"pattern": "リフレクション", "location": "src/a.py:42", "note": "動的呼び出し"}]
        up_path = self.root / "wave-0-unsupported.json"
        up_path.write_text(json.dumps(unsupported), encoding="utf-8")
        self._stage1_commit(hits_path, class_path, extra=["--unsupported-patterns", str(up_path)])
        log_text = self.log_path.read_text(encoding="utf-8")
        header_part, wave_part = log_text.split("## Wave 0", 1)
        self.assertIn("リフレクション", header_part)
        self.assertIn("src/a.py:42（動的呼び出し）", header_part)
        self.assertIn("⬜ 未確認", header_part)
        self.assertNotIn("リフレクション", wave_part)

    def test_commit_wave_unsupported_patterns_absent_is_noop(self):
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        header_before = self.log_path.read_text(encoding="utf-8").split("## Wave 0", 1)[0]
        self._stage1_commit(hits_path, class_path)
        header_after = self.log_path.read_text(encoding="utf-8").split("## Wave 0", 1)[0]
        self.assertEqual(header_before, header_after)

    def test_append_unsupported_patterns_dedups_by_pattern_and_location(self):
        self._init(symbols="foo")
        entries = [{"pattern": "eval", "location": "src/x.py:1", "note": "a"}]
        mod._append_unsupported_patterns(self.log_path, entries)
        mod._append_unsupported_patterns(self.log_path, entries)
        text = self.log_path.read_text(encoding="utf-8")
        self.assertEqual(text.count("| eval |"), 1)

    def test_append_unsupported_patterns_noop_when_heading_absent(self):
        self.log_path.write_text("# no header here\n", encoding="utf-8")
        mod._append_unsupported_patterns(self.log_path, [{"pattern": "x", "location": "y:1"}])
        self.assertEqual(self.log_path.read_text(encoding="utf-8"), "# no header here\n")

    def test_truncate_wave_section_preserves_unsupported_patterns_section(self):
        self._init(symbols="foo")
        mod._append_unsupported_patterns(self.log_path, [{"pattern": "eval", "location": "src/x.py:1"}])
        self.log_path.write_text(
            self.log_path.read_text(encoding="utf-8") + "\n## Wave 0\nsome content\n", encoding="utf-8")
        mod._truncate_wave_section(self.log_path, 0)
        text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("| eval |", text)
        self.assertNotIn("some content", text)

    def test_commit_wave_chunk_mtime_min_overrides_file_mtime_for_reuse(self):
        """§4.5(d)「判定方法〔S2〕」: --chunk-mtime-min が指定されればファイル mtime より優先される。"""
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_seed_timer(at=1000.0, wave=0)
        os.utime(class_path, (2000.0, 2000.0))  # ファイル mtime 単体なら reused=False になるはずの構成
        result = self._stage1_commit(hits_path, class_path, extra=["--chunk-mtime-min", "500"])
        self.assertTrue(result["ok"])
        m = self._stage1_metrics()[-1]
        self.assertTrue(m["classify_wall_ms_reused"])
        self.assertIsNone(m["classify_wall_ms"])

    def test_commit_wave_chunk_mtime_min_absent_falls_back_to_file_mtime(self):
        self._init(symbols="foo")
        hits_path, class_path = self._stage1_wave_files()
        self._stage1_seed_timer(at=1000.0, wave=0)
        os.utime(class_path, (2000.0, 2000.0))
        result = self._stage1_commit(hits_path, class_path)
        self.assertTrue(result["ok"])
        m = self._stage1_metrics()[-1]
        self.assertFalse(m["classify_wall_ms_reused"])
        self.assertIsNotNone(m["classify_wall_ms"])

    # -- scope_summary --------------------------------------------------

    def test_init_scope_summary_file_populates_state(self):
        summary_path = self.root / "_scope-summary.md"
        summary_path.write_text(
            "対象システム: device-svc\n対象UR: UR-001 決済APIの追加\n", encoding="utf-8")
        self._init(scope_summary_file=str(summary_path))
        data = self._load_state()
        self.assertEqual(data["scope_summary"], "対象システム: device-svc\n対象UR: UR-001 決済APIの追加")

    def test_init_without_scope_summary_file_defaults_empty(self):
        result = self._init()
        self.assertTrue(result["ok"])
        data = self._load_state()
        self.assertEqual(data["scope_summary"], "")
        self.assertNotIn("warnings", result)

    def test_init_scope_summary_file_missing_path_fails_soft_with_warning(self):
        missing_path = self.root / "_does-not-exist.md"
        result = self._init(scope_summary_file=str(missing_path))
        self.assertTrue(result["ok"])
        data = self._load_state()
        self.assertEqual(data["scope_summary"], "")
        self.assertIn("warnings", result)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("scope_summary が空です", log_text)

    def test_search_scope_summary_distributed_to_hits_and_chunks(self):
        summary_path = self.root / "_scope-summary.md"
        summary_path.write_text("要約テキスト", encoding="utf-8")
        self._write_file("src/a.py", "def foo(): pass\nfoo()\n")
        self._init(symbols="foo", scope_summary_file=str(summary_path))
        result = self._run(["search", "--path", str(self.state_path),
                            "--hits-out", str(self.root / "wave-0-hits.json")])
        hits = json.loads((self.root / "wave-0-hits.json").read_text(encoding="utf-8"))
        self.assertEqual(hits["scope_summary"], "要約テキスト")
        chunk_path = Path(result["chunks"][0])
        chunk = json.loads(chunk_path.read_text(encoding="utf-8"))
        self.assertEqual(chunk["scope_summary"], "要約テキスト")

    def test_import_warns_about_scope_summary_loss(self):
        summary_path = self.root / "_scope-summary.md"
        summary_path.write_text("要約テキスト", encoding="utf-8")
        self._init(scope_summary_file=str(summary_path))
        result = self._run(["import", "--path", str(self.state_path)])
        self.assertIn("scope_summary", " ".join(result["warnings"]))
        data = self._load_state()
        self.assertEqual(data["scope_summary"], "")


class BackendTestCase(unittest.TestCase):
    """Backend 抽象の単体テスト（subprocess は全てモック＝0トークン・grep/rg バイナリ非依存）。"""

    # -- GrepBackend ---------------------------------------------------

    def test_grep_backend_high_splits_into_batches_with_candidates(self):
        """HIGH は _batch_symbols のバッチごとに SearchCommand を返し、candidates はそのバッチ。"""
        record = []
        with patch.object(mod, "_batch_symbols", return_value=[["alpha"], ["beta"]]), \
             patch.object(mod.subprocess, "run",
                          _fake_run(stdout_seq=["f.py:1:alpha beta", ""], record=record)):
            backend = mod.GrepBackend([], [], "/repo")
            cmds = backend.search(["alpha", "beta"], None)
        self.assertEqual(len(cmds), 2)
        self.assertEqual(cmds[0].candidates, ["alpha"])
        self.assertEqual(cmds[1].candidates, ["beta"])
        self.assertEqual(cmds[0].pattern_repr, r"\balpha\b")
        self.assertEqual(cmds[0].rows, [("f.py", 1, "alpha beta")])
        # grep 経路のコマンド（grep -rn -E）で実行されている
        self.assertEqual(record[0][0], "grep")

    def test_grep_backend_medium_single_command(self):
        record = []
        with patch.object(mod.subprocess, "run",
                          _fake_run(stdout_seq=["src/a.py:5:validate(x)"], record=record)):
            backend = mod.GrepBackend([], [], "/repo")
            cmds = backend.search(["validate"], "src/a.py")
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].pattern_repr, r"\bvalidate\b")
        self.assertEqual(cmds[0].candidates, ["validate"])
        # MEDIUM（scope 指定）では除外オプションを付けず、scope を対象パスに解決する
        cmd = record[0]
        self.assertIn("src/a.py", cmd[-1])
        self.assertNotIn("--exclude-dir=tests", cmd)

    def test_grep_backend_uses_grep_exclude_opts(self):
        record = []
        with patch.object(mod.subprocess, "run", _fake_run(record=record)):
            backend = mod.GrepBackend(["tests/"], [".py"], "/repo")
            backend.search(["x"], None)
        cmd = record[0]
        self.assertIn("--exclude-dir=tests", cmd)
        self.assertIn("--include=*.py", cmd)

    # -- RgBackend -----------------------------------------------------

    def test_rg_backend_high_single_command(self):
        record = []
        with patch.object(mod.subprocess, "run",
                          _fake_run(stdout_seq=["f.py:2:alpha()"], record=record)):
            backend = mod.RgBackend([], [], "/repo")
            cmds = backend.search(["alpha", "beta"], None)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].pattern_repr, r"\b(alpha|beta)\b")
        self.assertEqual(cmds[0].candidates, ["alpha", "beta"])
        self.assertEqual(record[0][0], "rg")

    def test_rg_backend_medium_uses_grep_style_pattern_repr(self):
        """MEDIUM の pattern_repr は現行同様 grep 形式の複合パターン（rg 経路でも同一表現を記録）。"""
        with patch.object(mod.subprocess, "run", _fake_run(default_stdout="")):
            backend = mod.RgBackend([], [], "/repo")
            cmds = backend.search(["validate", "check"], "src/a.py")
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].pattern_repr, r"\b(validate|check)\b")

    def test_rg_backend_uses_rg_exclude_opts(self):
        record = []
        with patch.object(mod.subprocess, "run", _fake_run(record=record)):
            backend = mod.RgBackend(["tests/"], [".py"], "/repo")
            backend.search(["x"], None)
        cmd = record[0]
        self.assertIn("!tests", cmd)
        self.assertIn("*.py", cmd)

    # -- resolve_backend ----------------------------------------------

    def _state(self, backend="auto"):
        d = mod._default_state()
        d["repo_path"] = "/repo"
        d["backend"] = backend
        return d

    def test_resolve_backend_auto_prefers_rg_when_available(self):
        with patch.object(mod.shutil, "which", return_value="/usr/bin/rg"):
            backend, name, warn = mod.resolve_backend(self._state("auto"))
        self.assertIsInstance(backend, mod.RgBackend)
        self.assertEqual(name, "rg")
        self.assertIsNone(warn)

    def test_resolve_backend_auto_falls_to_grep_when_no_rg(self):
        with patch.object(mod.shutil, "which", return_value=None):
            backend, name, warn = mod.resolve_backend(self._state("auto"))
        self.assertIsInstance(backend, mod.GrepBackend)
        self.assertEqual(name, "grep")
        self.assertIsNone(warn)

    def test_resolve_backend_explicit_grep(self):
        with patch.object(mod.shutil, "which", return_value="/usr/bin/rg"):
            backend, name, warn = mod.resolve_backend(self._state("grep"))
        self.assertIsInstance(backend, mod.GrepBackend)
        self.assertIsNone(warn)

    def test_resolve_backend_explicit_rg_missing_binary_falls_back_with_warning(self):
        with patch.object(mod.shutil, "which", return_value=None):
            backend, name, warn = mod.resolve_backend(self._state("rg"))
        self.assertIsInstance(backend, mod.GrepBackend)
        self.assertEqual(name, "grep")
        self.assertIsNotNone(warn)

    def test_resolve_backend_static_backend_falls_back_with_warning(self):
        with patch.object(mod.shutil, "which", return_value=None):
            backend, name, warn = mod.resolve_backend(self._state("ctags"))
        self.assertIsInstance(backend, mod.GrepBackend)
        self.assertEqual(name, "grep")
        self.assertIn("ctags", warn)

    def test_resolve_backend_unknown_value_falls_back_with_warning(self):
        with patch.object(mod.shutil, "which", return_value=None):
            backend, name, warn = mod.resolve_backend(self._state("bogus"))
        self.assertIsInstance(backend, mod.GrepBackend)
        self.assertEqual(name, "grep")
        self.assertIn("bogus", warn)

    def test_resolve_backend_missing_field_defaults_auto(self):
        """backend フィールド欠落の旧状態を読んでも既定 auto で解決（前方互換）。"""
        d = mod._default_state()
        d["repo_path"] = "/repo"
        del d["backend"]
        with patch.object(mod.shutil, "which", return_value=None):
            backend, name, warn = mod.resolve_backend(d)
        self.assertEqual(name, "grep")
        self.assertIsNone(warn)


class SearchBackendIntegrationTestCase(unittest.TestCase):
    """cmd_search 経由の Backend 配線検証（実 grep/rg のみ使用・0トークン）。"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.state_path = self.root / "bfs-state.json"
        self.log_path = self.root / "discovery-log.md"

    def tearDown(self):
        self.tmpdir.cleanup()

    def _init(self, symbols="processPayment", **kw):
        argv = [
            "init", "--path", str(self.state_path), "--repo-path", str(self.repo),
            "--discovery-log", str(self.log_path), "--symbols", symbols,
            "--today", "2026-07-19", "--cr", "CR-2026-999", "--repo", "device-svc",
        ]
        for k, v in kw.items():
            argv += [f"--{k.replace('_', '-')}", str(v)]
        parser = mod.build_parser()
        args = parser.parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _search(self):
        parser = mod.build_parser()
        args = parser.parse_args(["search", "--path", str(self.state_path),
                                  "--hits-out", str(self.root / "hits.json")])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _load_state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _set_backend(self, name):
        data = self._load_state()
        data["backend"] = name
        mod._write_state(self.state_path, data)

    def _hits_tuples(self):
        hits = json.loads((self.root / "hits.json").read_text(encoding="utf-8"))["hits"]
        return {(h["file"], h["line_no"], h["matched_text"], h["symbol"]) for h in hits}

    def test_init_records_backend_field(self):
        self._init(backend="grep")
        self.assertEqual(self._load_state()["backend"], "grep")

    def test_init_defaults_backend_auto(self):
        self._init()
        self.assertEqual(self._load_state()["backend"], "auto")

    def test_grep_and_rg_cross_equivalent(self):
        """grep 経路と rg 経路が (file,line_no,matched_text,symbol) の集合として一致する。"""
        import shutil as _sh
        if not _sh.which("rg"):
            self.skipTest("rg（ripgrep）が無いため横断等価テストをスキップ")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "a.py").write_text(
            "def h():\n    processPayment(order, amount)\n    processPayment(x)\n", encoding="utf-8")
        (self.repo / "src" / "b.py").write_text("x = processPayment\n", encoding="utf-8")

        self._init(symbols="processPayment", backend="grep")
        self._search()
        grep_hits = self._hits_tuples()

        # 同じ状態で rg 経路を実行し直す
        self.state_path.unlink()
        self.log_path.unlink()
        self._init(symbols="processPayment", backend="rg")
        self._search()
        rg_hits = self._hits_tuples()

        self.assertEqual(grep_hits, rg_hits)
        self.assertTrue(grep_hits)  # 空集合の偶然一致を避ける

    def test_grep_and_rg_cross_equivalent_mocked(self):
        """実 rg バイナリ非依存版: grep/rg の生ヒットを同一にモックし、集合一致を検証する。"""
        rows = "src/a.py:2:processPayment(order)\nsrc/a.py:3:processPayment(x)\nsrc/b.py:1:x = processPayment\n"

        self._init(symbols="processPayment", backend="grep")
        with patch.object(mod.shutil, "which", return_value=None), \
             patch.object(mod.subprocess, "run", _fake_run(default_stdout=rows)):
            self._search()
        grep_hits = self._hits_tuples()

        self.state_path.unlink()
        self.log_path.unlink()
        self._init(symbols="processPayment", backend="rg")
        with patch.object(mod.shutil, "which", return_value="/usr/bin/rg"), \
             patch.object(mod.subprocess, "run", _fake_run(default_stdout=rows)):
            self._search()
        rg_hits = self._hits_tuples()

        self.assertEqual(grep_hits, rg_hits)
        self.assertEqual(len(grep_hits), 3)

    def test_unknown_backend_logs_warning_and_effective_grep(self):
        (self.repo / "a.py").write_text("processPayment()\n", encoding="utf-8")
        self._init(symbols="processPayment", backend="bogus")
        self._search()
        data = self._load_state()
        self.assertEqual(data["backend_effective"], "grep")
        self.assertTrue(data["backend_fallback_logged"])
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("バックエンド警告", log_text)

    def test_missing_backend_field_search_defaults_auto(self):
        (self.repo / "a.py").write_text("processPayment()\n", encoding="utf-8")
        self._init(symbols="processPayment")
        data = self._load_state()
        del data["backend"]
        mod._write_state(self.state_path, data)
        result = self._search()
        self.assertTrue(result["ok"])
        self.assertIn(self._load_state()["backend_effective"], ("rg", "grep"))

    # -- word boundary helpers ------------------------------------------

    def test_word_boundary_omits_leading_boundary_for_nonword_prefix(self):
        # $state: `$` は非単語文字なので先頭の \b を省略
        self.assertEqual(mod._word_boundary("$state"), r"\$state\b")

    def test_word_boundary_omits_trailing_boundary_for_nonword_suffix(self):
        # operator+: `+` は非単語文字なので末尾の \b を省略
        self.assertEqual(mod._word_boundary("operator+"), r"\boperator\+")

    def test_word_boundary_keeps_both_boundaries_for_plain_word(self):
        self.assertEqual(mod._word_boundary("validate"), r"\bvalidate\b")

    def test_word_boundary_matches_dollar_prefixed_symbol(self):
        # `$state` の先頭は非単語文字なので先頭の \b を省略する。これにより
        # 行頭・空白直後の `$state` も無音 0 ヒットせず検出できる。
        # 副作用として `my$state` 内の部分列にもマッチするが、specout は
        # 「偽陰性ゼロ（見逃しを許さない）」を優先する設計である。
        pattern = mod._word_boundary("$state")
        self.assertRegex("x = $state", pattern)
        self.assertRegex("$state = 1", pattern)

    def test_grep_compound_resolves_boundaries_per_symbol(self):
        pattern = mod._grep_compound(["foo", "$state"])
        self.assertEqual(pattern, r"(\bfoo\b|\$state\b)")
        self.assertRegex("call foo()", pattern)
        self.assertRegex("x = $state", pattern)

    def test_grep_compound_repr_empty_list(self):
        self.assertEqual(mod._grep_compound_repr([]), "()")

    def test_grep_compound_repr_single_symbol_omits_group(self):
        self.assertEqual(mod._grep_compound_repr(["alpha"]), r"\balpha\b")

    def test_grep_compound_repr_word_symbols_use_legacy_form(self):
        self.assertEqual(mod._grep_compound_repr(["alpha", "beta"]), r"\b(alpha|beta)\b")

    def test_grep_compound_repr_nonword_prefix_uses_individual_boundaries(self):
        self.assertEqual(mod._grep_compound_repr(["alpha", "$state"]), r"(\balpha\b|\$state\b)")

    def test_grep_compound_repr_nonword_suffix_uses_individual_boundaries(self):
        self.assertEqual(mod._grep_compound_repr(["alpha", "operator+"]), r"(\balpha\b|\boperator\+)")

    def test_grep_compound_execution_pattern_unchanged(self):
        # 実行用パターンはキャプチャグループ (A|B|C) のまま
        self.assertEqual(mod._grep_compound(["alpha", "beta"]), r"(\balpha\b|\bbeta\b)")


if __name__ == "__main__":
    unittest.main()
