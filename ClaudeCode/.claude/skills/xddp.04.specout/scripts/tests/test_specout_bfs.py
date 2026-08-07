import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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
        data = self._load_state()
        # vendor はマップ未掲載（近傍外）→ simple モードでは既定 LOW として退避される（捨てない）
        self.assertIn("step3", data["low_priority_frontier"])

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
        data = self._load_state()
        self.assertIn("noise", data["low_priority_frontier"])


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
        self.assertEqual(cmds[0].pattern_repr, r"\b(alpha)\b")
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
        self.assertEqual(cmds[0].pattern_repr, r"\b(validate)\b")
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
        self.assertEqual(cmds[0].pattern_repr, r"\balpha\b|\bbeta\b")
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


if __name__ == "__main__":
    unittest.main()
