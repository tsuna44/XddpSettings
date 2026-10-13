import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import specout_bfs as mod  # noqa: E402
import specout_slice as slice_mod  # noqa: E402
import specout_verify_counts as verify_mod  # noqa: E402

ENGINE_EXTS = slice_mod.ENGINE_EXTS


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

    def test_search_warns_on_unparsed_hit_lines(self):
        """grep/rg が _HIT_LINE_RE にマッチしない行を返した場合、discovery-log.md に警告が
        記録され、かつ hit_count・raw_hits には計上されないことを検証する。"""
        self._write_file("src/a.py", "def f():\n    return validate(x)\n")
        self._init(symbols="validate", backend="grep")
        with patch.object(mod.subprocess, "run",
                          _fake_run(stdout_seq=["not-a-valid-hit-line-format"])):
            result = self._run(["search", "--path", str(self.state_path),
                                "--hits-out", str(self.root / "wave-0-hits.json")])
        self.assertEqual(result["hit_count"], 0)
        self.assertEqual(result["raw_hits"], 0)
        text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("パース不能なヒット行", text)

    def test_search_no_warning_when_all_hit_lines_parse(self):
        """正常系（全行がパース可能）では警告が記録されないことを確認する回帰用の対比テスト。"""
        self._write_file("src/a.py", "def f():\n    return validate(x)\n")
        self._init(symbols="validate")
        self._run(["search", "--path", str(self.state_path),
                  "--hits-out", str(self.root / "wave-0-hits.json")])
        text = self.log_path.read_text(encoding="utf-8")
        self.assertNotIn("パース不能なヒット行", text)

    def test_search_errors_when_complete(self):
        self._init()
        data = self._load_state()
        data["state"] = "complete"
        mod._write_state(self.state_path, data)
        with self.assertRaises(SystemExit):
            self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "x.json")])

    def test_search_auto_completes_at_wave_limit(self):
        """上限 N なら起点から N 波（第0〜N-1波）を調べ、第N波の search で打ち切り記録を残して complete にする。"""
        self._init(max_wave=1)
        data = self._load_state()
        data["current_wave"] = 1
        data["last_completed_wave"] = 0
        data["frontier"] = ["a", "b"]
        data["low_priority_frontier"] = ["c"]
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "x.json")])
        self.assertTrue(result["complete"])
        self.assertTrue(result["truncated"])
        self.assertEqual(result["truncated_count"], 3)
        self.assertEqual(result["wave"], 1)
        data = self._load_state()
        self.assertEqual(data["state"], "complete")
        self.assertEqual(data["frontier"], [])
        self.assertEqual(data["low_priority_frontier"], [])
        self.assertEqual([(t["symbol"], t["reason"], t["from"], t["hits"]) for t in data["truncated"]],
                         [("a", "wave-limit", "frontier", None), ("b", "wave-limit", "frontier", None),
                          ("c", "wave-limit", "low", None)])
        text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## 打ち切り記録", text)
        self.assertIn("| Wave 1 | wave-limit | `a` | - |", text)
        self.assertNotIn("探索上限到達", text)
        self.assertFalse((self.root / "x.json").exists())

    def test_search_below_wave_limit_searches(self):
        """境界: 起点から N-1 波目（current_wave - wave_origin = N-1）はまだ検索する。"""
        self._write_file("a.py", "a()\n")
        self._init(symbols="a", max_wave=2)
        data = self._load_state()
        data["current_wave"] = 1
        data["last_completed_wave"] = 0
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "x.json")])
        self.assertNotIn("complete", result)
        self.assertEqual(result["wave"], 1)

    def test_wave_limit_counts_from_wave_origin(self):
        self._write_file("a.py", "a()\n")
        self._init(symbols="a", max_wave=2)
        data = self._load_state()
        data["current_wave"] = 5
        data["last_completed_wave"] = 4
        data["wave_origin"] = 4
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "x.json")])
        self.assertEqual(result["wave"], 5)
        data = self._load_state()
        data["current_wave"] = 6
        data["last_completed_wave"] = 5
        data["wave_write_complete"] = True
        mod._write_state(self.state_path, data)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "y.json")])
        self.assertTrue(result["complete"])

    def test_set_state_rejects_removed_paused_states(self):
        self._init(symbols="a")
        for st in ("paused-at-limit", "paused-at-limit-2nd"):
            with self.assertRaises(SystemExit):
                self._run(["set-state", "--path", str(self.state_path), "--state", st])

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
            [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": r"\bprocessPayment\b", "scope": "全域",
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
        # metrics.jsonl が state（bfs-state.json）と同ディレクトリに1行出力される
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
        self.assertIn("| W0-C1 | 3 | 1 | 1 | 0 | 1 | ✅ excluded(dedup=1,filter=1,noise-collapse=0) |", log_text)

    def test_commit_wave_writes_metrics_next_to_state_not_hits(self):
        """hits が state と別ディレクトリ（work/waves/）でも metrics.jsonl は state 側に出力される。"""
        self._init(symbols="processPayment")
        hits = self._hits_payload(
            0,
            [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": r"\bprocessPayment\b", "scope": "全域", "hit_count": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "processPayment", "scope_file": None,
              "file": "src/billing/handler.py", "line_no": 12, "matched_text": "processPayment(order)"}],
            searched_frontier=["processPayment"],
            metrics={"wave": 0, "search_ms": 5, "raw_hits": 1},
        )
        waves_dir = self.root / "waves"
        waves_dir.mkdir()
        hits_path = waves_dir / "wave-0-hits.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [{"line_id": "W0-R1", "classification": "propagation-direct",
                            "next_symbols": [], "enclosing_function": "h", "is_external_api": False}]
        class_path = waves_dir / "wave-0-class.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                   "--classification", str(class_path), "--today", "2026-07-19"])
        self.assertEqual(self.state_path.parent, self.root)
        self.assertTrue((self.root / "metrics.jsonl").exists())
        self.assertFalse((waves_dir / "metrics.jsonl").exists())

    def test_commit_wave_basic_propagation_and_confirmed_files(self):
        self._init(symbols="processPayment")
        hits = self._hits_payload(
            0,
            [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": r"\bprocessPayment\b", "scope": "全域", "hit_count": 1}],
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
            [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": r"\berr\b", "scope": "全域", "hit_count": 1}],
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
            0, [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": "foo", "scope": "全域", "hit_count": 1}],
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
            0, [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": "foo", "scope": "全域", "hit_count": 1}],
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
            0, [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": "a", "scope": "全域", "hit_count": 1}],
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
        self.assertIn("| case-a | promote-high; discard=`fileB.py` |", log_text)
        self.assertIn("➖ discarded(case-a)", log_text)
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
        self.assertIn("| case-b | manual-check |", log_text)

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
        self.assertIn("| case-c | keep-visited |", log_text)
        self.assertIn("`ctx[MEDIUM:a.go]`", log_text)
        data = self._load_state()
        self.assertIn("ctx[MEDIUM:a.go]", data["visited"])
        self.assertIn("ctx[MEDIUM:b.go]", data["visited"])

    # -- high noise ------------------------------------------------------

    def test_high_noise_symbol_stops_propagation(self):
        self._init(symbols="log", max_files_per_module=2)
        commands = [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": "log", "scope": "全域", "hit_count": 3}]
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

    def test_search_pre_noisy_representative_is_min_line_number_per_file(self):
        """BUG-004: 代表行はファイル内の最小行番号であることを固定する
        （複数マッチを持つファイルでの回帰）。"""
        self._write_file("m/a.py", "noop()\nnoop()\nlog(x)\nnoop()\nlog(y)\n")  # a.py は3行目・5行目にマッチ
        for name in ("b", "c", "d"):
            self._write_file(f"m/{name}.py", "log(x)\n")
        self._init(symbols="log", max_files_per_module=2)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "h.json")])
        self.assertEqual(result["pre_noisy"], ["log"])
        hits = json.loads((self.root / "h.json").read_text(encoding="utf-8"))
        # 代表サブセット（ファイルパス昇順で先頭2件）に m/a.py が含まれ、その代表行は
        # 5行目ではなく最小行番号の3行目であることを固定する
        a_hit = next(h for h in hits["hits"] if h["file"] == "m/a.py")
        self.assertEqual(a_hit["line_no"], 3)

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
            0, [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": "log", "scope": "全域", "hit_count": 5}],
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
            0, [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": "entryFunc", "scope": "全域", "hit_count": 1}],
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

    # -- merge-frontier / re-discover / import ----------------------------

    def test_merge_frontier_dedups(self):
        self._init(symbols="a")
        result = self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "a,c"])
        self.assertEqual(result["added"], ["c"])

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
            0, [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": "processPayment", "scope": "全域", "hit_count": 1}],
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
            [{"command_id": f"W{wave}-C1", "kind": "HIGH-compound", "pattern": symbol, "scope": "全域", "hit_count": 1}],
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

    def test_stage1_wave_limit_complete_drops_classify_timer(self):
        """波数上限の自動完了では2キーを書かず、既存の2キーを削除する。"""
        self._init(max_wave=1)
        self._stage1_set_state(current_wave=2, last_completed_wave=1, classify_started_at=1000.0,
                               classify_started_wave=1)
        result = self._run(["search", "--path", str(self.state_path), "--hits-out", str(self.root / "x.json")])
        self.assertTrue(result["complete"])
        data = self._load_state()
        self.assertNotIn("classify_started_at", data)
        self.assertNotIn("classify_started_wave", data)

    def test_stage1_set_state_drops_classify_timer(self):
        self._init(symbols="a")
        self._stage1_seed_timer()
        self._run(["set-state", "--path", str(self.state_path), "--state", "in-progress"])
        self.assertNotIn("classify_started_at", self._load_state())

    def test_stage1_merge_frontier_keeps_classify_timer(self):
        """波を進めないため、その波の分類区間は継続中とみなして2キーを保持する。"""
        self._init(symbols="a")
        self._stage1_seed_timer()
        self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "c"])
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

    def test_stage1_commit_wave_rejects_recommit_after_set_state_complete(self):
        """条件2（state == complete）が単独で成立する state。当該波の search 後に set-state complete した場合、
        wave_write_complete / last_completed_wave / current_wave は進まないため
        条件1・3 はいずれも不成立であり、条件2 を落とすとこの経路が素通りする。"""
        self._init(symbols="foo")
        self._stage1_set_state(current_wave=1, last_completed_wave=0, wave_write_complete=False,
                               state="in-progress", frontier=["foo"], low_priority_frontier=[])
        # 書きかけ Wave セクションの後ろに監査記録がある状態を作る
        mod._append_to_file(self.log_path, "\n## Wave 1\n\n書きかけ\n")
        mod._append_to_file(self.log_path, "\n---\n## 完了時の監査記録\n- 根拠: 境界外\n")
        self._run(["set-state", "--path", str(self.state_path), "--state", "complete"])
        before = self._load_state()
        # 伝播を生む classification（条件2 が無いと frontier が復活する入力）
        hits_path, class_path = self._stage1_wave_files(wave=1, next_symbols=["revived"], deferred_low=["stale"])
        with self.assertRaises(SystemExit):
            self._stage1_commit(hits_path, class_path)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## 完了時の監査記録", log_text)   # 切り捨てが起きていない
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
            [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": r"\bexpire_flags\b", "scope": "全域",
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
            [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": r"\b(alpha|beta|gamma)\b",
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
            {"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": r"\b(noisy|other)\b", "scope": "全域",
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

    def test_commit_wave_complete_message_recommends_new_run(self):
        """条件2 のメッセージが set-state を再開手段として推奨せず、新しい調査を案内する。"""
        self._init(symbols="foo")
        self._stage1_set_state(current_wave=1, last_completed_wave=0, wave_write_complete=False,
                                state="complete", frontier=[])
        hits_path, class_path = self._stage1_wave_files(wave=1)
        err = self._run_expect_err(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                                     "--classification", str(class_path), "--today", "2026-07-19"])
        self.assertIn("/xddp-investigate", err)
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
            self.assertIn("set-state", err)      # 完了済みの波へ戻さない
            self.assertIn("run-remove", err)

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
        first = sorted(p.name for p in out_dir.glob("wave-0-hits-chunk-*.json"))
        self.assertEqual(first, ["wave-0-hits-chunk-0.json", "wave-0-hits-chunk-1.json", "wave-0-hits-chunk-S.json"])
        self._run(["search", "--path", str(self.state_path), "--hits-dir", str(out_dir), "--chunk-size", "0"])
        second = sorted(p.name for p in out_dir.glob("wave-0-hits-chunk-*.json"))
        self.assertEqual(second, ["wave-0-hits-chunk-0.json", "wave-0-hits-chunk-S.json"])

    def test_status_brief_returns_minimal_keys(self):
        self._init(symbols="foo")
        self._stage1_set_state(frontier=["a", "b"], low_priority_frontier=["c"])
        result = self._run(["status", "--path", str(self.state_path), "--brief"])
        self.assertEqual(set(result.keys()),
                          {"ok", "state", "current_wave", "wave_write_complete", "remaining_frontier_count",
                           "confirmed_file_count", "max_wave_depth", "truncated_wave_limit_count",
                           "slice_engine", "seed_direct_file_count", "seed_budget_truncated_count",
                           "name_only_file_count"})
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

    def test_module_dir_for_file_independent_of_cwd(self):
        """Change S-0: リポジトリ相対パス入力時、cwd（実行時の作業ディレクトリ）に依存せず
        先頭ディレクトリを返す（xddp コマンドの通常運用は cwd=WORKSPACE_ROOT・repo_path はそのサブ
        ディレクトリであり、両者が一致しない）。"""
        repo_path = str(self.repo)
        original_cwd = os.getcwd()
        try:
            os.chdir(str(self.root))  # repo_path とは異なるディレクトリ（WORKSPACE_ROOT 相当）
            self.assertEqual(mod._module_dir_for_file(repo_path, "src/billing/handler.py"), "src")
            self.assertEqual(mod._module_dir_for_file(repo_path, "root.py"), "_root")
        finally:
            os.chdir(original_cwd)

    def test_module_dir_for_file_absolute_path_still_resolves_via_repo_path(self):
        """絶対パス入力時は従来どおり repo_path からの relpath 変換を行う（既存動作の保存）。"""
        repo_path = str(self.repo)
        abs_file = str(self.repo / "src" / "billing" / "handler.py")
        self.assertEqual(mod._module_dir_for_file(repo_path, abs_file), "src")

    def test_status_without_brief_includes_confirmed_modules(self):
        """Change S: confirmed_files に記録されたファイルの第1階層ディレクトリ名が
        confirmed_modules として status（--brief なし）に含まれる。"""
        self._init(symbols="processPayment")
        hits = self._hits_payload(
            0,
            [{"command_id": "W0-C1", "kind": "HIGH-compound", "pattern": r"\bprocessPayment\b",
              "scope": "全域", "hit_count": 1}],
            [{"line_id": "W0-R1", "command_id": "W0-C1", "symbol": "processPayment", "scope_file": None,
              "file": "src/billing/handler.py", "line_no": 12, "matched_text": "processPayment(order, amount)"}],
            searched_frontier=["processPayment"],
        )
        hits_path = self.root / "wave-0-hits.json"
        hits_path.write_text(json.dumps(hits), encoding="utf-8")
        classification = [{"line_id": "W0-R1", "classification": "propagation-direct",
                            "next_symbols": [], "enclosing_function": "handlePaymentRequest",
                            "is_external_api": False}]
        class_path = self.root / "wave-0-class.json"
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hits_path),
                    "--classification", str(class_path), "--today", "2026-07-19"])
        result = self._run(["status", "--path", str(self.state_path)])
        self.assertEqual(result["confirmed_modules"], ["src"])

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

    def test_resolve_backend_auto_is_index_delegating_to_rg(self):
        with patch.object(mod.shutil, "which", return_value="/usr/bin/rg"):
            backend, name, warn = mod.resolve_backend(self._state("auto"))
        self.assertIsInstance(backend, mod.IndexBackend)
        self.assertIsInstance(backend.delegate, mod.RgBackend)
        self.assertEqual(name, "index")
        self.assertIsNone(warn)

    def test_resolve_backend_auto_is_index_delegating_to_grep_when_no_rg(self):
        with patch.object(mod.shutil, "which", return_value=None):
            backend, name, warn = mod.resolve_backend(self._state("auto"))
        self.assertIsInstance(backend, mod.IndexBackend)
        self.assertIsInstance(backend.delegate, mod.GrepBackend)
        self.assertEqual(name, "index")
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
        self.assertEqual(name, "index")
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
        self.assertEqual(self._load_state()["backend_effective"], "index")

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


# -- funcmap-counts（PLAN-20260913-funcmap-count-script） --------------------

FUNCMAP_WAVE0_HEADER = (
    "| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | "
    "含む関数/クラス（ファイル読み込みで確認） | 伝播種別 | 確信度 | Wave 1 追加シンボル | 派生元 |"
)
FUNCMAP_WAVE0_SEP = "|---|---|---|---|---|---|---|---|---|---|---|"


def _funcmap_row(line_id: str, cmd_id: str, symbol: str, file_: str, origin: str, line_no: int = 1,
                 label: str = "直接参照") -> str:
    return (
        f"| {line_id} | {cmd_id} | `{symbol}` | {file_} | {line_no} | `{symbol}()` | "
        f"`fn` | {label} | HIGH | — | {origin} |"
    )


def _funcmap_wave0_block(rows_text: str) -> str:
    return (
        "## Wave 0\n\n"
        "### 実行コマンド一覧\n"
        "| コマンドID | 種別 | パターン/対象シンボル | 対象スコープ | ヒット行数（生） |\n"
        "|---|---|---|---|---|\n"
        "| C1 | HIGH-compound | `foo` | 全域 | 1 |\n\n"
        + FUNCMAP_WAVE0_HEADER + "\n" + FUNCMAP_WAVE0_SEP + "\n"
        + rows_text
        + "\n"
    )


class FuncmapCountsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.log_path = self.root / "discovery-log.md"
        self.out_path = self.root / "SPO-CR-TEST-funcmap-counts.md"

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, log_text: str):
        self.log_path.write_text(log_text, encoding="utf-8")
        parser = mod.build_parser()
        args = parser.parse_args([
            "funcmap-counts", "--discovery-log", str(self.log_path), "--out", str(self.out_path),
        ])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        result = json.loads(buf.getvalue())
        return result, self.out_path.read_text(encoding="utf-8")

    def _run_fail(self, log_text: str):
        self.log_path.write_text(log_text, encoding="utf-8")
        parser = mod.build_parser()
        args = parser.parse_args([
            "funcmap-counts", "--discovery-log", str(self.log_path), "--out", str(self.out_path),
        ])
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                args.func(args)

    def test_single_symbol_counts_unique_files(self):
        rows = (
            _funcmap_row("L1", "C1", "foo", "src/a.py", "seed(foo)") + "\n"
            + _funcmap_row("L2", "C1", "foo", "src/b.py", "seed(foo)") + "\n"
        )
        result, out_text = self._run(_funcmap_wave0_block(rows))
        self.assertTrue(result["ok"])
        self.assertEqual(result["symbols"], 1)
        self.assertEqual(result["n_rows"], 2)
        self.assertEqual(result["skipped_rows"], 0)
        self.assertIn("| `foo` | 2 | `src/a.py`, `src/b.py` |", out_text)

    def test_missing_wave0_heading_fails_loud(self):
        self._run_fail("# Discovery Log\n\n## 探索設定\n- 開始日時: 2026-09-13\n")

    def test_false_positive_rows_are_not_counted(self):
        rows = (
            _funcmap_row("L1", "C1", "foo", "src/a.py", "seed(foo)") + "\n"
            + _funcmap_row("L2", "C1", "foo", "src/comment.py", "seed(foo)", label="false-positive") + "\n"
        )
        result, out_text = self._run(_funcmap_wave0_block(rows))
        self.assertEqual((result["symbols"], result["skipped_rows"], result["false_positive_rows"]), (1, 0, 1))
        self.assertIn("| `foo` | 1 | `src/a.py` |", out_text)
        self.assertIn("- false-positive で除いた行数: 1", out_text)

    def test_seed_with_only_false_positive_rows_gets_zero_row(self):
        rows = (
            _funcmap_row("L1", "C1", "foo", "src/a.py", "seed(foo)") + "\n"
            + _funcmap_row("L2", "C1", "bar", "src/comment.py", "seed(bar)", label="false-positive") + "\n"
        )
        result, out_text = self._run(_funcmap_wave0_block(rows))
        self.assertTrue(result["ok"])
        self.assertIn("| `bar` | 0 | （なし） |", out_text)
        # 第0波がすべて false-positive でも全行スキップの検査で失敗しない
        only_fp = _funcmap_row("L1", "C1", "bar", "src/comment.py", "seed(bar)", label="false-positive") + "\n"
        result, out_text = self._run(_funcmap_wave0_block(only_fp))
        self.assertEqual(result["symbols"], 1)
        self.assertIn("| `bar` | 0 | （なし） |", out_text)

    def test_header_without_label_column_fails_loud(self):
        header = FUNCMAP_WAVE0_HEADER.replace(" 伝播種別 |", " 種別 |")
        self.assertNotEqual(header, FUNCMAP_WAVE0_HEADER)
        log_text = ("## Wave 0\n\n" + header + "\n" + FUNCMAP_WAVE0_SEP + "\n"
                    + _funcmap_row("L1", "C1", "foo", "src/a.py", "seed(foo)") + "\n")
        self._run_fail(log_text)

    def test_header_mismatch_fails_loud(self):
        log_text = "## Wave 0\n\n| A | B |\n|---|---|\n| x | y |\n"
        self._run_fail(log_text)

    def test_no_data_rows_fails_loud(self):
        log_text = "## Wave 0\n\n" + FUNCMAP_WAVE0_HEADER + "\n" + FUNCMAP_WAVE0_SEP + "\n"
        self._run_fail(log_text)

    def test_duplicate_hits_same_file_counted_once(self):
        rows = (
            _funcmap_row("L1", "C1", "foo", "src/a.py", "seed(foo)", line_no=10) + "\n"
            + _funcmap_row("L2", "C1", "foo", "src/a.py", "seed(foo)", line_no=20) + "\n"
        )
        result, out_text = self._run(_funcmap_wave0_block(rows))
        self.assertEqual(result["symbols"], 1)
        self.assertIn("| `foo` | 1 | `src/a.py` |", out_text)

    def test_noise_collapsed_log_equivalent_to_full_log(self):
        """前倒し縮退（noise-collapse）済みログでも、同一ファイル内の複数ヒットは1件に集約
        されるだけで直接呼び出し元数（ユニークファイル数）自体は変化しない
        （4.の「リスク」記載の等価性を固定する回帰テスト）。"""
        full_rows = (
            _funcmap_row("L1", "C1", "foo", "src/a.py", "seed(foo)", line_no=10) + "\n"
            + _funcmap_row("L2", "C1", "foo", "src/a.py", "seed(foo)", line_no=20) + "\n"
            + _funcmap_row("L3", "C1", "foo", "src/b.py", "seed(foo)", line_no=5) + "\n"
        )
        full_result, _ = self._run(_funcmap_wave0_block(full_rows))

        self.tearDown()
        self.setUp()
        collapsed_rows = (
            _funcmap_row("L1", "C1", "foo", "src/a.py", "seed(foo)", line_no=10) + "\n"
            + _funcmap_row("L2", "C1", "foo", "src/b.py", "seed(foo)", line_no=5) + "\n"
        )
        collapsed_result, _ = self._run(_funcmap_wave0_block(collapsed_rows))

        self.assertEqual(full_result["symbols"], collapsed_result["symbols"])

    def test_unformatted_derivation_line_is_skipped_and_counted(self):
        rows = (
            _funcmap_row("L1", "C1", "foo", "src/a.py", "seed(foo)") + "\n"
            + _funcmap_row("L2", "C1", "bar", "src/c.py", "不明な派生元テキスト") + "\n"
        )
        result, out_text = self._run(_funcmap_wave0_block(rows))
        self.assertEqual(result["skipped_rows"], 1)
        self.assertIn("## スキップされた行（書式不一致）", out_text)
        self.assertIn("| `L2` | `不明な派生元テキスト` |", out_text)

    def test_all_rows_unformatted_fails_loud(self):
        rows = _funcmap_row("L1", "C1", "foo", "src/a.py", "不明な派生元テキスト") + "\n"
        self._run_fail(_funcmap_wave0_block(rows))

    def test_failure_removes_stale_output_file(self):
        rows = _funcmap_row("L1", "C1", "foo", "src/a.py", "seed(foo)") + "\n"
        self._run(_funcmap_wave0_block(rows))
        self.assertTrue(self.out_path.exists())

        self._run_fail("# Discovery Log\n\n## 探索設定\n- 開始日時: 2026-09-13\n")
        self.assertFalse(self.out_path.exists())


# ---------------------------------------------------------------------------
# 未ヒット投入シンボル検出・投入シンボルの由来（Wave 0 シード結線）
# ---------------------------------------------------------------------------

class _SeedTestBase(unittest.TestCase):
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
        args = mod.build_parser().parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _init(self, symbols, entry_point_symbols=None):
        argv = [
            "init", "--path", str(self.state_path), "--repo-path", str(self.repo),
            "--discovery-log", str(self.log_path), "--symbols", symbols,
            "--today", "2026-09-26", "--cr", "CR-2026-999", "--repo", "svc",
        ]
        if entry_point_symbols is not None:
            argv += ["--entry-point-symbols", entry_point_symbols]
        return self._run(argv)

    def _search(self, wave=0):
        return self._run(["search", "--path", str(self.state_path),
                          "--hits-out", str(self.root / f"wave-{wave}-hits.json")])

    def _write_file(self, rel_path, content):
        p = self.repo / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _patch_state(self, **kw):
        data = self._state()
        data.update(kw)
        mod._write_state(self.state_path, data)

    def _log(self):
        return self.log_path.read_text(encoding="utf-8")

    def _origin_ep_cell(self):
        for line in self._log().split("\n"):
            cells = mod._split_row(line)
            if cells and cells[0] == mod.ORIGIN_ROW_ENTRY_POINTS:
                return cells[1]
        return None


class ZeroHitDetectionTest(_SeedTestBase):
    """cmd_search の未ヒット投入シンボル検出。"""

    def test_wave0_raw_zero_hit(self):
        self._write_file("src/a.py", "def f():\n    foo()\n")
        self._init("foo,typoSym")
        result = self._search()
        self.assertEqual(result["zero_hit_symbols"], ["typoSym"])
        self.assertEqual(result["zero_after_filter_symbols"], [])
        self.assertEqual(result["wave0_seed_count"], 2)
        self.assertIn("## 未ヒット投入シンボル（Wave 0）", self._log())
        self.assertIn("| `typoSym` | CRS等 | 生ヒット0件 |", self._log())

    def test_wave0_all_filtered_goes_to_after_filter(self):
        self._write_file("src/a.py", "def f():\n    foo()\n# commented barSym\n")
        self._init("foo,barSym")
        result = self._search()
        self.assertEqual(result["zero_hit_symbols"], [])
        self.assertEqual(result["zero_after_filter_symbols"], ["barSym"])
        self.assertIn("フィルタ後0件", self._log())

    def test_wave1_propagated_symbols_excluded(self):
        self._write_file("src/a.py", "def f():\n    foo()\n")
        self._init("foo")
        self._patch_state(current_wave=1, last_completed_wave=0, frontier=["propagatedMissing"])
        result = self._search(1)
        self.assertEqual(result["zero_hit_symbols"], [])
        self.assertEqual(result["zero_after_filter_symbols"], [])
        self.assertEqual(result["wave0_seed_count"], 0)
        self.assertNotIn("## 未ヒット投入シンボル（Wave 1）", self._log())

    def test_wave1_entry_point_symbol_detected(self):
        self._write_file("src/a.py", "def f():\n    foo()\n")
        self._init("foo")
        self._patch_state(current_wave=1, last_completed_wave=0,
                          frontier=["propagatedMissing", "humanTypo"], entry_point_symbols=["humanTypo"])
        result = self._search(1)
        self.assertEqual(result["zero_hit_symbols"], ["humanTypo"])
        self.assertIn("| `humanTypo` | ENTRY_POINTS | 生ヒット0件 |", self._log())

    def test_medium_entries_excluded(self):
        self._write_file("src/a.py", "def f():\n    foo()\n")
        self._init("foo")
        self._patch_state(frontier=["foo", "nothere[MEDIUM:src/a.py]"])
        result = self._search()
        self.assertEqual(result["zero_hit_symbols"], [])
        self.assertEqual(result["zero_after_filter_symbols"], [])

    def test_entry_point_origin_column(self):
        self._write_file("src/a.py", "def f():\n    foo()\n")
        self._init("foo,epMissing,crsMissing", entry_point_symbols="epMissing")
        result = self._search()
        self.assertEqual(result["zero_hit_symbols"], ["crsMissing", "epMissing"])
        log = self._log()
        self.assertIn("| `epMissing` | ENTRY_POINTS |", log)
        self.assertIn("| `crsMissing` | CRS等 |", log)
        self.assertNotIn("MEDIUM", log[log.index("## 未ヒット投入シンボル"):log.index(mod.GREP_UNSUPPORTED_HEADING)])

    def test_sections_per_wave_coexist(self):
        self._write_file("src/a.py", "def f():\n    foo()\n")
        self._init("foo,w0Missing")
        self._search()
        self._patch_state(current_wave=1, last_completed_wave=0,
                          frontier=["w1Missing"], entry_point_symbols=["w1Missing"])
        self._search(1)
        log = self._log()
        self.assertIn("## 未ヒット投入シンボル（Wave 0）", log)
        self.assertIn("## 未ヒット投入シンボル（Wave 1）", log)
        self.assertIn("`w0Missing`", log)
        self.assertIn("`w1Missing`", log)


class UpsertSectionTest(_SeedTestBase):
    """_upsert_section の冪等性・挿入位置・境界規則。"""

    def test_research_is_idempotent(self):
        self._write_file("src/a.py", "def f():\n    foo()\n")
        self._init("foo,typoSym")
        self._search()
        self._search()
        self.assertEqual(self._log().count("## 未ヒット投入シンボル（Wave 0）"), 1)

    def test_resolved_zero_hit_removes_section(self):
        self._write_file("src/a.py", "def f():\n    foo()\n")
        self._init("foo,laterSym")
        self._search()
        self.assertIn("## 未ヒット投入シンボル（Wave 0）", self._log())
        self._write_file("src/b.py", "laterSym()\n")
        result = self._search()
        self.assertEqual(result["zero_hit_symbols"], [])
        self.assertNotIn("## 未ヒット投入シンボル（Wave 0）", self._log())
        self.assertIn(mod.GREP_UNSUPPORTED_HEADING, self._log())

    def test_inserted_before_grep_unsupported_heading(self):
        self._write_file("src/a.py", "def f():\n    foo()\n")
        self._init("foo,typoSym")
        self._search()
        log = self._log()
        zi = log.index("## 未ヒット投入シンボル（Wave 0）")
        self.assertLess(log.index(mod.ORIGIN_HEADING), zi)
        self.assertLess(zi, log.index(mod.GREP_UNSUPPORTED_HEADING))

    def test_eof_warnings_survive_research(self):
        self._write_file("src/a.py", "def f():\n    foo()\n")
        self._init("foo,typoSym")
        self._search()
        mod._append_to_file(self.log_path, "\n> ⚠️ バックエンド警告: test\n")
        mod._append_to_file(self.log_path, "\n> ⚠️ パース不能なヒット行が 1 件検出されました\n")
        self._search()
        log = self._log()
        self.assertIn("> ⚠️ バックエンド警告: test", log)
        self.assertIn("> ⚠️ パース不能なヒット行が 1 件検出されました", log)

    def test_boundary_stops_at_next_heading_and_dash(self):
        text = ("# L\n\n## 未ヒット投入シンボル（Wave 0）\n\nold\n\n## next\nkeep1\n---\nkeep2\n"
                + mod.GREP_UNSUPPORTED_HEADING + "\n")
        self.log_path.write_text(text, encoding="utf-8")
        mod._upsert_section(str(self.log_path), mod._zero_hit_heading(0), "new\n")
        log = self._log()
        self.assertIn("## 未ヒット投入シンボル（Wave 0）\n\nnew\n\n## next\nkeep1\n---\nkeep2", log)
        self.assertNotIn("old", log)
        text2 = "# L\n\n## 未ヒット投入シンボル（Wave 0）\n\nold\n---\nkeep\n"
        self.log_path.write_text(text2, encoding="utf-8")
        mod._upsert_section(str(self.log_path), mod._zero_hit_heading(0), "new\n")
        self.assertIn("new\n\n---\nkeep", self._log())

    def test_legacy_log_without_grep_heading_is_noop(self):
        text = "# Legacy\n\n## 探索設定\n- x\n"
        self.log_path.write_text(text, encoding="utf-8")
        mod._upsert_section(str(self.log_path), mod._zero_hit_heading(0), "body\n")
        self.assertEqual(self._log(), text)

    def test_empty_or_missing_path_is_noop(self):
        mod._upsert_section("", mod._zero_hit_heading(0), "body\n")
        mod._upsert_section(str(self.root / "nope.md"), mod._zero_hit_heading(0), "body\n")
        self.assertFalse((self.root / "nope.md").exists())


class EntryPointSymbolsStateTest(_SeedTestBase):
    """--entry-point-symbols の state セマンティクス（init / merge-frontier / re-discover）。"""

    def _complete(self):
        self._patch_state(state="complete", last_completed_wave=0, current_wave=0)

    def test_default_state_has_key(self):
        self.assertEqual(mod._default_state()["entry_point_symbols"], [])

    def test_init_saves_value(self):
        self._init("foo,bar", entry_point_symbols="bar")
        self.assertEqual(self._state()["entry_point_symbols"], ["bar"])

    def test_init_unspecified_is_backward_compatible(self):
        self._init("processPayment")
        data = self._state()
        self.assertEqual(data["entry_point_symbols"], [])
        expected = mod._default_state()
        self.assertEqual(set(data.keys()), set(expected.keys()))
        md = (self.root / "bfs-state.md").read_text(encoding="utf-8")
        self.assertIn("**投入シンボル（ENTRY_POINTS）：** ", md)
        log = self._log()
        self.assertNotIn("（CRS SP項目より）", log)
        self.assertIn("- 初期シンボル（Wave 0）:\n  - `processPayment`\n", log)
        self.assertIn(mod.ORIGIN_HEADING, log)

    def test_merge_frontier_unspecified_keeps(self):
        self._init("foo", entry_point_symbols="a")
        self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "b"])
        self.assertEqual(self._state()["entry_point_symbols"], ["a"])

    def test_checkpoint_roundtrip_via_import(self):
        self._init("foo", entry_point_symbols="a,b")
        md = (self.root / "bfs-state.md").read_text(encoding="utf-8")
        self.assertIn("**投入シンボル（ENTRY_POINTS）：** a,b", md)
        self.state_path.unlink()
        self._run(["import", "--path", str(self.state_path), "--from", str(self.root / "bfs-state.md")])
        self.assertEqual(self._state()["entry_point_symbols"], ["a", "b"])

    def test_import_legacy_checkpoint_without_label(self):
        legacy = self.root / "legacy.md"
        legacy.write_text("# BFS Checkpoint\n\n**状態：** in-progress\n**現在 Wave 番号：** 0\n", encoding="utf-8")
        self._run(["import", "--path", str(self.state_path), "--from", str(legacy)])
        self.assertEqual(self._state()["entry_point_symbols"], [])


class OriginEntryPointsTest(_SeedTestBase):
    """_update_origin_entry_points の行単位更新と cmd_init による骨組み出力。"""

    def _rows(self):
        rows = {}
        log = self._log()
        sec = log[log.index(mod.ORIGIN_HEADING):log.index(mod.GREP_UNSUPPORTED_HEADING)]
        for line in sec.split("\n"):
            cells = mod._split_row(line)
            if len(cells) == 3 and cells[0] not in ("由来", "---"):
                rows[cells[0]] = cells
        return rows

    def _set_ep_cell(self, cell):
        log = self._log()
        new = []
        for line in log.split("\n"):
            cells = mod._split_row(line)
            if cells and cells[0] == mod.ORIGIN_ROW_ENTRY_POINTS:
                line = f"| {mod.ORIGIN_ROW_ENTRY_POINTS} | {cell} | 備考X |"
            new.append(line)
        self.log_path.write_text("\n".join(new), encoding="utf-8")

    def test_init_skeleton_position_and_cells(self):
        self._init("foo", entry_point_symbols="a,b")
        log = self._log()
        self.assertLess(log.index(mod.ORIGIN_HEADING), log.index(mod.GREP_UNSUPPORTED_HEADING))
        rows = self._rows()
        self.assertEqual(rows[mod.ORIGIN_ROW_ENTRY_POINTS][1], "`a`, `b`")
        for name in mod.ORIGIN_OTHER_ROWS:
            self.assertEqual(rows[name][1], mod.ORIGIN_NONE_CELL)
            self.assertEqual(rows[name][2], "—")

    def test_init_unspecified_uses_empty_cell(self):
        self._init("foo")
        self.assertEqual(self._origin_ep_cell(), mod.ORIGIN_EMPTY_CELL)

class HeadingCollisionTest(unittest.TestCase):
    """新設見出し2種が Wave 見出し検出に誤検出されないこと（回帰）。"""

    def test_headings_not_detected_as_wave(self):
        for heading in (mod._zero_hit_heading(0), mod._zero_hit_heading(12), mod.ORIGIN_HEADING,
                        mod._noisy_seed_heading(0), mod._noisy_seed_heading(12)):
            with self.subTest(heading=heading):
                text = f"# L\n\n{heading}\n\nbody\n"
                self.assertEqual(mod.WAVE_HEADING_RE.findall(text), [])
                self.assertEqual(mod._wave0_block_span(text), (None, None))
                self.assertNotIn("## Wave 0", text)
                self.assertFalse(heading.startswith("## Wave "))

    def test_truncate_wave_section_ignores_new_headings(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "log.md"
            text = (f"# L\n\n{mod._zero_hit_heading(0)}\n\nbody\n\n{mod.ORIGIN_HEADING}\n\nx\n\n"
                    f"{mod._noisy_seed_heading(0)}\n\ny\n")
            p.write_text(text, encoding="utf-8")
            mod._truncate_wave_section(p, 0)
            self.assertEqual(p.read_text(encoding="utf-8"), text)


class NoisySeedDetectionTest(_SeedTestBase):
    """cmd_search のヒット過多の投入シンボル検出。"""

    def _spread(self, sym, n):
        for i in range(n):
            self._write_file(f"{sym}_m{i}/f{i}.py", f"{sym}()\n")

    def _init_small_limit(self, symbols, entry_point_symbols=None, limit=2):
        self._init(symbols, entry_point_symbols)
        self._patch_state(max_files_per_module=limit)

    def _section(self, wave=0):
        log = self._log()
        h = mod._noisy_seed_heading(wave)
        if h not in log:
            return None
        start = log.index(h)
        end = log.find("\n## ", start + len(h))
        return log[start:end if end != -1 else len(log)]

    def test_wave0_noisy_seed_detected_with_full_file_count(self):
        self._spread("route", 5)
        self._write_file("a/x.py", "rareSym()\n")
        self._init_small_limit("route,rareSym")
        result = self._search()
        self.assertEqual(result["noisy_seed_symbols"], [{"symbol": "route", "file_count": 5}])
        self.assertFalse(result["all_seeds_noisy"])
        sec = self._section()
        self.assertIsNotNone(sec)
        self.assertIn("| `route` | CRS等 | 5 |", sec)
        self.assertNotIn("全件がヒット過多", sec)

    def test_under_limit_not_detected(self):
        self._spread("route", 2)
        self._init_small_limit("route")
        result = self._search()
        self.assertEqual(result["noisy_seed_symbols"], [])
        self.assertIsNone(self._section())

    def test_all_seeds_noisy(self):
        self._spread("route", 3)
        self._spread("install", 3)
        self._init_small_limit("route,install")
        result = self._search()
        self.assertTrue(result["all_seeds_noisy"])
        self.assertIn("全件がヒット過多", self._section())

    def test_wave1_propagated_noisy_symbol_excluded(self):
        self._write_file("a/x.py", "foo()\n")
        self._init_small_limit("foo")
        self._search()
        self._spread("propagated", 4)
        self._patch_state(current_wave=1, last_completed_wave=0, frontier=["propagated"], entry_point_symbols=[])
        result = self._search(1)
        self.assertEqual(result["noisy_seed_symbols"], [])
        self.assertFalse(result["all_seeds_noisy"])
        self.assertIsNone(self._section(1))

    def test_wave1_entry_point_noisy_symbol_detected(self):
        self._write_file("a/x.py", "foo()\n")
        self._init_small_limit("foo")
        self._search()
        self._spread("order", 4)
        self._patch_state(current_wave=1, last_completed_wave=0, frontier=["order"], entry_point_symbols=["order"])
        result = self._search(1)
        self.assertEqual(result["noisy_seed_symbols"], [{"symbol": "order", "file_count": 4}])
        self.assertTrue(result["all_seeds_noisy"])
        self.assertIn("| `order` | ENTRY_POINTS | 4 |", self._section(1))

    def test_medium_entry_excluded(self):
        self._spread("param", 4)
        self._init_small_limit("anchorSym")
        self._write_file("a/x.py", "anchorSym()\n")
        self._patch_state(frontier=["anchorSym", "param[MEDIUM:param_m0/f0.py]"])
        result = self._search()
        self.assertEqual(result["noisy_seed_symbols"], [])

    def test_keys_present_when_no_detection_target(self):
        self._write_file("a/x.py", "foo()\n")
        self._init_small_limit("foo")
        self._search()
        self._patch_state(current_wave=1, last_completed_wave=0, frontier=["foo"], entry_point_symbols=[])
        result = self._search(1)
        self.assertIn("noisy_seed_symbols", result)
        self.assertEqual(result["noisy_seed_symbols"], [])
        self.assertIs(result["all_seeds_noisy"], False)

    def test_research_is_idempotent(self):
        self._spread("route", 3)
        self._write_file("a/x.py", "rareSym()\n")
        self._init_small_limit("route,rareSym")
        self._search()
        self._search()
        self.assertEqual(self._log().count(mod._noisy_seed_heading(0)), 1)

    def test_sections_per_wave_coexist(self):
        self._spread("route", 3)
        self._write_file("a/x.py", "rareSym()\n")
        self._init_small_limit("route,rareSym")
        self._search()
        self._spread("order", 3)
        self._patch_state(current_wave=1, last_completed_wave=0, frontier=["order"], entry_point_symbols=["order"])
        self._search(1)
        log = self._log()
        self.assertIn(mod._noisy_seed_heading(0), log)
        self.assertIn(mod._noisy_seed_heading(1), log)

    def test_resolved_noisy_removes_section(self):
        self._spread("route", 3)
        self._write_file("a/x.py", "rareSym()\n")
        self._init_small_limit("route,rareSym")
        self._search()
        self.assertIsNotNone(self._section())
        self._patch_state(max_files_per_module=10)
        result = self._search()
        self.assertEqual(result["noisy_seed_symbols"], [])
        self.assertIsNone(self._section())
        self.assertIn(mod.GREP_UNSUPPORTED_HEADING, self._log())

    def test_section_has_no_medium_word(self):
        self._spread("route", 3)
        self._init_small_limit("route")
        self._search()
        self.assertNotIn("MEDIUM", self._section())


class EmptySeedExitTest(_SeedTestBase):
    """シード0件の search は EXIT_EMPTY_SEED、1波以上コミット後の frontier 空は従来どおり 1。"""

    def _search_exit_code(self):
        args = mod.build_parser().parse_args(["search", "--path", str(self.state_path),
                                               "--hits-out", str(self.root / "h.json")])
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                args.func(args)
        return cm.exception.code

    def test_empty_seed_exits_4(self):
        self._init("")
        self.assertEqual(self._search_exit_code(), mod.EXIT_EMPTY_SEED)
        self.assertEqual(mod.EXIT_EMPTY_SEED, 4)

    def test_empty_frontier_after_commit_exits_1(self):
        self._init("")
        self._patch_state(current_wave=1, last_completed_wave=0)
        self.assertEqual(self._search_exit_code(), 1)


class OriginCodeDerivedRowTest(_SeedTestBase):
    """由来テーブルの骨組みが9行（ENTRY_POINTS 行 → ORIGIN_OTHER_ROWS の順）であること。"""

    EXPECTED_ROWS = [
        "ENTRY_POINTS（人が明示指定）", "CRS SP項目", "下調べ（Step A-Prelim）", "母体コードから補完", "継承展開",
        "確認時に人が追加", "確認時に人が除外", "解決できなかった ENTRY_POINT", "シンボル不明",
    ]

    def _origin_names(self, text):
        sec = text[text.index(mod.ORIGIN_HEADING):]
        sec = sec[:sec.index("\n## ", 1)]
        names = []
        for line in sec.split("\n"):
            cells = mod._split_row(line)
            if cells and len(cells) >= 3 and cells[0] not in ("由来", "---"):
                names.append(cells[0])
        return names

    def test_code_derived_row_after_entry_points(self):
        self._init("foo")
        self.assertEqual(self._origin_names(self._log()), self.EXPECTED_ROWS)
        self.assertEqual([mod.ORIGIN_ROW_ENTRY_POINTS] + list(mod.ORIGIN_OTHER_ROWS), self.EXPECTED_ROWS)

    def test_template_rows_match_skeleton(self):
        """テンプレートの由来テーブルが `_origin_section_skeleton` の行構成・空セル表記と一致すること。"""
        template = (Path(__file__).resolve().parents[2] / "templates"
                    / "04_specout-discovery-log-template.md").read_text(encoding="utf-8")
        self.assertEqual(self._origin_names(template), self.EXPECTED_ROWS)
        skeleton_rows = [line for line in mod._origin_section_skeleton([]).split("\n") if line.startswith("| ")]
        for row in skeleton_rows:
            self.assertIn(row, template)

    def test_template_legend_matches_generated_legend(self):
        """テンプレートの「## 凡例」が init の書く凡例と一致し、旧形式（日本語）の値が残っていないこと。"""
        template = (Path(__file__).resolve().parents[2] / "templates"
                    / "04_specout-discovery-log-template.md").read_text(encoding="utf-8")
        self.assertIn(mod.LEGEND_HEADING + "\n\n" + mod.LEGEND_BODY, template)
        for old in ("HIGH複合", "初期シンボル:", "件数不一致", "制御フロー＋データフロー", "一時停止"):
            self.assertNotIn(old, template)


class FuncmapOriginTest(unittest.TestCase):
    """_FUNCMAP_ORIGIN_RE は seed(X) だけを受理し、seed-global(X) と旧形式（日本語）は受理しない。"""

    def test_accepts_seed_only(self):
        self.assertEqual(mod._FUNCMAP_ORIGIN_RE.match("seed(foo)").group(1), "foo")
        self.assertIsNone(mod._FUNCMAP_ORIGIN_RE.match("seed-global(server.dirty)"))
        self.assertIsNone(mod._FUNCMAP_ORIGIN_RE.match("Wave0（初期シンボル: foo）"))
        self.assertIsNone(mod._FUNCMAP_ORIGIN_RE.match("CRS（初期シンボル: foo）"))



# ---------------------------------------------------------------------------
# 下調べ・シード確認・追加下調べ（seed-preview / init --seed-candidates / doc-targets / prelim-metrics）
# ---------------------------------------------------------------------------

class _PrelimTestBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.out = self.root / "out"
        self.work = self.out / "work"
        self.work.mkdir(parents=True)
        self.state_path = self.work / "bfs-state.json"
        self.log_path = self.out / "discovery-log.md"
        self.cand_path = self.work / "seed-candidates.md"
        self.ledger_path = self.work / "documented-files.md"
        self.memo_path = self.work / "observation-memo.md"
        self.assign_path = self.work / "module-assignments.json"

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, argv):
        args = mod.build_parser().parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _run_fail(self, argv):
        """(終了コード, stderr) を返す。"""
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                args = mod.build_parser().parse_args(argv)
                args.func(args)
        return cm.exception.code, err.getvalue()

    def _write_file(self, rel_path, content):
        p = self.repo / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _write_candidates(self, rows, unresolved=(), unknown=()):
        """rows: (採否, シンボル, 由来, 根拠, ヒット, 警告, 除外理由) のタプル列。"""
        lines = ["# シード候補 — CR-2026-999 / svc", "",
                 "> 「ヒット」「警告」列は `specout_bfs.py seed-preview` が書き換える。", "",
                 "## 候補", "| 採否 | シンボル | 由来 | 根拠 | ヒット（ファイル数） | 警告 | 除外理由 |",
                 "|---|---|---|---|---|---|---|"]
        lines += ["| " + " | ".join(r) + " |" for r in rows]
        lines += ["", "## 解決できなかった ENTRY_POINT", "| 指定値 | 理由 |", "|---|---|"]
        lines += ["| " + " | ".join(r) + " |" for r in unresolved]
        lines += ["", "## 識別子を特定できなかった振る舞い", "| 振る舞い（CRS） | 調べた範囲 |", "|---|---|"]
        lines += ["| " + " | ".join(r) + " |" for r in unknown]
        self.cand_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_ledger(self, rows):
        """rows: (ファイルパス, モジュール, モジュールディレクトリ, 工程) のタプル列。"""
        lines = ["# 文書化済みファイル台帳 — CR-2026-999 / svc", "",
                 "> 下調べと追加下調べが追記する。", "",
                 "| ファイルパス | モジュール | モジュールディレクトリ | 工程 | 関係する振る舞い（CRS） |",
                 "|---|---|---|---|---|"]
        lines += [f"| {f} | {m} | {d} | {ph} | 振る舞い |" for f, m, d, ph in rows]
        self.ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_memo(self, side_effect_files=(), testability_files=()):
        lines = ["## 外部副作用", "| 識別子（関数/メソッド） | ファイルパス | 副作用種別 | 対象 | 備考 |", "|---|---|---|---|---|"]
        lines += [f"| fn | {f} | ファイルI/O | x | - |" for f in side_effect_files]
        lines += ["", "## テスト可能性", "| ファイルパス | テスト可能性 | 備考 |", "|---|---|---|"]
        lines += [f"| {f} | 高 | - |" for f in testability_files]
        lines += ["", "## 非機能特性",
                  "| ファイル/識別子 | ファイルパス | 特性種別 | 観察内容 | アーキテクトへの示唆 | 影響度 |",
                  "|---|---|---|---|---|---|",
                  "", "## 入力源", "| ファイルパス | 入力種別 | 識別子（ハンドラ/購読関数等） | 外部エンティティ（想定） | 備考 |",
                  "|---|---|---|---|---|",
                  "", "## 制約照合", "| MODULE | ファイルパス | 既存制約 [CK-NNN] | 新観察内容 | 矛盾・不整合の有無 |",
                  "|---|---|---|---|---|", ""]
        self.memo_path.write_text("\n".join(lines), encoding="utf-8")

    def _write_state(self, confirmed, cr="CR-2026-999"):
        data = mod._default_state()
        data.update({"repo_path": str(self.repo), "discovery_log": str(self.log_path), "cr": cr,
                     "repo": "svc", "state": "complete",
                     "confirmed_files": {f: {"wave": 0, "confidence": c} for f, c in confirmed.items()}})
        data["confirmed_file_count"] = len(data["confirmed_files"])
        mod._write_state(self.state_path, data)

    def _candidate_rows(self):
        text = self.cand_path.read_text(encoding="utf-8")
        sec = text[text.index("## 候補"):text.index("## 解決できなかった ENTRY_POINT")]
        rows = {}
        for line in sec.split("\n"):
            cells = mod._split_row(line)
            if len(cells) == 7 and cells[0] in ("☑", "☐"):
                rows[cells[1].strip("`")] = cells
        return rows


class WriteSeedCandidatesTest(_PrelimTestBase):
    TEMPLATE = Path(mod.__file__).resolve().parent.parent / "templates" / "04_specout-seed-candidates-template.md"

    def _input(self, **kw):
        data = {"entry_points": [], "crs": [], "prelim": [], "code_derived": [], "inherit": [],
                "unresolved_entry_points": [], "unknown_behaviors": [], "unsupported_patterns": []}
        data.update(kw)
        self.inp = self.work / "seed-input.json"
        self.inp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return self.inp

    def _argv(self, *extra):
        return ["write-seed-candidates", "--input", str(self.inp), "--out", str(self.cand_path),
                "--unsupported-out", str(self.unsup_path),
                "--template", str(self.TEMPLATE), "--cr", "CR-2026-999", "--repo", "svc", *extra]

    @property
    def unsup_path(self):
        return self.work / "seed-unsupported.json"

    def _append_argv(self):
        return ["write-seed-candidates", "--input", str(self.inp), "--out", str(self.cand_path),
                "--unsupported-out", str(self.unsup_path), "--append"]

    def _unsupported(self):
        return json.loads(self.unsup_path.read_text(encoding="utf-8"))

    def _create(self, **kw):
        self._input(**kw)
        return self._run(self._argv())

    def test_create_all_adopted_and_priority_folding(self):
        out = self._create(entry_points=["a"], crs=["a", "b", "c"],
                           prelim=[{"symbol": "b", "evidence": "x.c:1 根拠"}, {"symbol": "d", "evidence": "y.c:2 根拠"}],
                           code_derived=[{"symbol": "e", "evidence": "z.c:3"}], inherit=["e", "f"])
        seeds = mod._parse_seed_candidates(self.cand_path)
        self.assertTrue(all(c["adopted"] for c in seeds["candidates"]))
        rows = {c["symbol"]: c for c in seeds["candidates"]}
        self.assertEqual([c["symbol"] for c in seeds["candidates"]], ["a", "b", "c", "d", "e", "f"])
        self.assertEqual(rows["a"]["origin"], mod.SEED_ORIGIN_ENTRY_POINTS)
        self.assertEqual((rows["b"]["origin"], rows["b"]["basis"]), (mod.SEED_ORIGIN_CRS, "—"))
        self.assertEqual((rows["d"]["origin"], rows["d"]["basis"]), (mod.SEED_ORIGIN_PRELIM, "y.c:2 根拠"))
        self.assertEqual((rows["e"]["origin"], rows["e"]["basis"]), (mod.SEED_ORIGIN_CODE, "z.c:3"))
        self.assertEqual(rows["f"]["origin"], mod.SEED_ORIGIN_INHERIT)
        self.assertEqual(out["candidate_count"], 6)
        self.assertEqual(out["by_origin"][mod.SEED_ORIGIN_CRS], 2)

    def test_pipe_escape_roundtrip_and_downstream_readers(self):
        self._create(prelim=[{"symbol": "a", "evidence": "x | y"}],
                     unknown_behaviors=[{"behavior": "A|B", "scope": "dir"}],
                     unresolved_entry_points=[{"value": "no.c", "reason": "ファイル不在"}])
        seeds = mod._parse_seed_candidates(self.cand_path)
        self.assertEqual(seeds["candidates"][0]["basis"], "x | y")
        self.assertEqual(seeds["unknown_behaviors"][0]["behavior"], "A|B")
        self.assertEqual(seeds["unresolved_entry_points"][0]["value"], "no.c")
        self._write_file("a.c", "int a(void){return 0;}\n")
        self._run(["seed-preview", "--seed-candidates", str(self.cand_path), "--repo-path", str(self.repo)])
        self._run(["init", "--path", str(self.state_path), "--repo-path", str(self.repo),
                   "--discovery-log", str(self.log_path), "--seed-candidates", str(self.cand_path),
                   "--today", "2026-10-04", "--cr", "CR-2026-999", "--repo", "svc"])

    def test_empty_input_succeeds(self):
        out = self._create()
        self.assertEqual((out["candidate_count"], out["unresolved_count"], out["unknown_count"]), (0, 0, 0))

    def test_fail_loud_on_bad_input(self):
        for kw in ({"entry_points": ["a b"]}, {"crs": [""]}, {"entry_points": ["f[MEDIUM:p q.c]"]},
                   {"prelim": [{"symbol": "a"}]}):
            self._input(**kw)
            code, err = self._run_fail(self._argv())
            self.assertEqual(code, 1)
            self.assertIn(str(self.inp), err)
            self.assertFalse(self.cand_path.exists())
        self._input()
        data = json.loads(self.inp.read_text(encoding="utf-8"))
        del data["crs"]
        self.inp.write_text(json.dumps(data), encoding="utf-8")
        code, err = self._run_fail(self._argv())
        self.assertEqual(code, 1)
        self.assertIn(str(self.inp), err)

    def test_fail_on_template_mismatch_leaves_no_file(self):
        tpl = self.root / "bad-template.md"
        tpl.write_text("# x\n\n## 候補\n| 違う |\n|---|\n", encoding="utf-8")
        self._input(crs=["a"])
        argv = self._argv()
        argv[argv.index("--template") + 1] = str(tpl)
        code, err = self._run_fail(argv)
        self.assertEqual(code, 1)
        self.assertIn(str(tpl), err)
        self.assertFalse(self.cand_path.exists())
        self.assertFalse(list(self.work.glob("*.tmp")))

    def test_overwrite_guard(self):
        stale = self.root / "prelim-index.md"
        stale.write_text("x", encoding="utf-8")
        self._create(crs=["a"])
        before = self.cand_path.read_text(encoding="utf-8")
        self._input(crs=["z"])
        code, err = self._run_fail(self._argv())
        self.assertEqual(code, 1)
        code, err = self._run_fail(self._argv("--stale-ref", str(stale)))
        self.assertEqual(code, 1)
        self.assertIn(str(self.cand_path), err)
        os.utime(stale, (time.time() + 100, time.time() + 100))
        self._run(self._argv("--stale-ref", str(stale)))
        self.assertNotEqual(self.cand_path.read_text(encoding="utf-8"), before)
        self.assertEqual(mod._parse_seed_candidates(self.cand_path)["candidates"][0]["symbol"], "z")

    def test_failed_overwrite_keeps_existing_file(self):
        stale = self.root / "prelim-index.md"
        stale.write_text("x", encoding="utf-8")
        os.utime(stale, (time.time() + 100, time.time() + 100))
        self._create(crs=["a"])
        before = self.cand_path.read_text(encoding="utf-8")
        self._input(crs=["a b"])
        code, _ = self._run_fail(self._argv("--stale-ref", str(stale)))
        self.assertEqual(code, 1)
        self.assertEqual(self.cand_path.read_text(encoding="utf-8"), before)
        self.assertFalse(list(self.work.glob("*.tmp")))

    def test_append_keeps_existing_rows(self):
        self._write_candidates(
            [("☑", "keep", "CRS SP項目", "—", "3", "", ""),
             ("☐", "dropped", "ENTRY_POINTS", "人が外した \\| 根拠", "", "", "不要なため"),
             ("☑", "human", "人が追加", "手書き", "", "", "")],
            unresolved=[("old.c", "ファイル不在")])
        before = self.cand_path.read_text(encoding="utf-8").split("\n")
        self._input(entry_points=["dropped", "keep", "newep"], inherit=["newinh", "newep"], crs=["ignored"],
                    prelim=[{"symbol": "ignored2", "evidence": "x"}],
                    unresolved_entry_points=[{"value": "old.c", "reason": "別理由"}, {"value": "new.c", "reason": "ファイル不在"}])
        out = self._run(self._append_argv())
        after = self.cand_path.read_text(encoding="utf-8").split("\n")
        for line in before:
            self.assertIn(line, after)
        self.assertEqual(after[:9], before[:9])
        seeds = mod._parse_seed_candidates(self.cand_path)
        added = [c for c in seeds["candidates"] if c["symbol"] in ("newep", "newinh")]
        self.assertEqual([(c["symbol"], c["origin"], c["adopted"], c["basis"]) for c in added],
                         [("newep", "ENTRY_POINTS", True, "—"), ("newinh", "継承展開", True, "—")])
        self.assertNotIn("ignored", [c["symbol"] for c in seeds["candidates"]])
        self.assertNotIn("ignored2", [c["symbol"] for c in seeds["candidates"]])
        self.assertEqual(out["excluded_entry_points"], [{"symbol": "dropped", "reason": "不要なため"}])
        self.assertEqual(out["appended_count"], 2)
        self.assertEqual([u["value"] for u in seeds["unresolved_entry_points"]], ["old.c", "new.c"])
        self.assertEqual(seeds["unresolved_entry_points"][0]["reason"], "ファイル不在")

    def test_unsupported_written_and_read_by_init(self):
        out = self._create(crs=["a"], unsupported_patterns=[
            {"pattern": "Go インタフェース暗黙実装", "location": "Reader", "note": "実装クラスの手動確認が必要"},
            {"pattern": "モジュール再エクスポート", "location": "src/index.ts"}])
        self.assertEqual(self._unsupported(), [
            {"pattern": "Go インタフェース暗黙実装", "location": "Reader", "note": "実装クラスの手動確認が必要"},
            {"pattern": "モジュール再エクスポート", "location": "src/index.ts"}])
        self.assertEqual((out["unsupported_count"], out["unsupported_appended_count"], out["unsupported_skipped_count"]),
                         (2, 2, 0))
        self._write_file("a.c", "int a(void){return 0;}\n")
        self._run(["init", "--path", str(self.state_path), "--repo-path", str(self.repo),
                   "--discovery-log", str(self.log_path), "--seed-candidates", str(self.cand_path),
                   "--unsupported-patterns", str(self.unsup_path),
                   "--today", "2026-10-04", "--cr", "CR-2026-999", "--repo", "svc"])
        log = self.log_path.read_text(encoding="utf-8")
        self.assertIn("| Go インタフェース暗黙実装 | Reader（実装クラスの手動確認が必要） | ⬜ 未確認 |", log)
        self.assertIn("| モジュール再エクスポート | src/index.ts | ⬜ 未確認 |", log)

    def test_unsupported_normalization(self):
        out = self._create(unsupported_patterns=[
            {"pattern": " 設定・DI ", "location": " 設定（config A の注入） "},
            {"pattern": "設定・DI", "location": "設定（config B の注入）", "note": "config A の注入"},
            {"pattern": "設定・DI", "location": "設定", "note": "config AB"},
            {"pattern": "リフレクション", "location": "SP-1（getattr）", "note": "動的呼び出し"},
            {"pattern": "エイリアス定義", "location": "SR-1"},
            {"pattern": "エイリアス定義", "location": "SR-1", "note": "typedef"},
            {"pattern": "マクロ", "location": "（先頭が括弧）"},
            {"pattern": "", "location": "x"},
            {"pattern": "x", "location": "  "},
            {"pattern": "y", "location": "z", "note": None}])
        self.assertEqual(self._unsupported(), [
            {"pattern": "設定・DI", "location": "設定", "note": "config A の注入; config B の注入; config AB"},
            {"pattern": "リフレクション", "location": "SP-1", "note": "getattr; 動的呼び出し"},
            {"pattern": "エイリアス定義", "location": "SR-1", "note": "typedef"},
            {"pattern": "y", "location": "z"}])
        self.assertEqual((out["unsupported_count"], out["unsupported_appended_count"], out["unsupported_skipped_count"]),
                         (4, 4, 3))

    def test_unsupported_empty_writes_empty_array(self):
        out = self._create(crs=["a"])
        self.assertEqual(self._unsupported(), [])
        self.assertEqual((out["unsupported_count"], out["unsupported_appended_count"], out["unsupported_skipped_count"]),
                         (0, 0, 0))
        self._write_file("a.c", "int a(void){return 0;}\n")
        self._run(["init", "--path", str(self.state_path), "--repo-path", str(self.repo),
                   "--discovery-log", str(self.log_path), "--seed-candidates", str(self.cand_path),
                   "--unsupported-patterns", str(self.unsup_path),
                   "--today", "2026-10-04", "--cr", "CR-2026-999", "--repo", "svc"])
        log = self.log_path.read_text(encoding="utf-8")
        sec = log[log.index(mod.GREP_UNSUPPORTED_HEADING):]
        self.assertNotIn("⬜ 未確認", sec.split("\n## ")[0])

    def test_unsupported_fail_loud_on_bad_input(self):
        bad = ("not-a-list", [{"pattern": 1, "location": "x"}], [{"pattern": "p"}], ["s"],
               [{"pattern": "p", "location": "x", "note": 3}])
        for value in bad:
            self._input(unsupported_patterns=value)
            code, err = self._run_fail(self._argv())
            self.assertEqual(code, 1)
            self.assertIn(str(self.inp), err)
            self.assertFalse(self.cand_path.exists())
            self.assertFalse(self.unsup_path.exists())
            self.assertFalse(list(self.work.glob("*.tmp")))
        self._input()
        data = json.loads(self.inp.read_text(encoding="utf-8"))
        del data["unsupported_patterns"]
        self.inp.write_text(json.dumps(data), encoding="utf-8")
        code, err = self._run_fail(self._argv())
        self.assertEqual(code, 1)
        self.assertIn(str(self.inp), err)
        self.assertFalse(self.unsup_path.exists())

    def test_unsupported_untouched_when_candidates_fail(self):
        tpl = self.root / "bad-template.md"
        tpl.write_text("# x\n\n## 候補\n| 違う |\n|---|\n", encoding="utf-8")
        self._input(crs=["a"], unsupported_patterns=[{"pattern": "p", "location": "x"}])
        argv = self._argv()
        argv[argv.index("--template") + 1] = str(tpl)
        code, _ = self._run_fail(argv)
        self.assertEqual(code, 1)
        self.assertFalse(self.unsup_path.exists())
        self.assertFalse(list(self.work.glob("*.tmp")))
        # 上書きガードで止まるとき、既存の seed-unsupported.json は変わらない
        self._create(crs=["a"], unsupported_patterns=[{"pattern": "p", "location": "x"}])
        before = self.unsup_path.read_text(encoding="utf-8")
        self._input(crs=["b"], unsupported_patterns=[{"pattern": "q", "location": "y"}])
        code, _ = self._run_fail(self._argv())
        self.assertEqual(code, 1)
        self.assertEqual(self.unsup_path.read_text(encoding="utf-8"), before)
        self.assertFalse(list(self.work.glob("*.tmp")))

    def test_unsupported_append(self):
        self._write_candidates([("☑", "keep", "CRS SP項目", "—", "", "", "")])
        existing = [{"pattern": "設定・DI", "location": "設定", "note": "既存の注記"},
                    {"pattern": "モジュール再エクスポート", "location": "a.ts"}]
        self.unsup_path.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
        self._input(unsupported_patterns=[
            {"pattern": "設定・DI", "location": "設定（新しい注記）"},
            {"pattern": "モジュール再エクスポート", "location": "b.ts"},
            {"pattern": "モジュール再エクスポート", "location": "a.ts"},
            {"pattern": "", "location": "x"}])
        out = self._run(self._append_argv())
        self.assertEqual(self._unsupported(), existing + [{"pattern": "モジュール再エクスポート", "location": "b.ts"}])
        self.assertEqual((out["unsupported_count"], out["unsupported_appended_count"], out["unsupported_skipped_count"]),
                         (3, 1, 1))

    def test_unsupported_append_creates_missing_file(self):
        self._write_candidates([("☑", "keep", "CRS SP項目", "—", "", "", "")])
        self._input(unsupported_patterns=[{"pattern": "p", "location": "x"}])
        out = self._run(self._append_argv())
        self.assertEqual(self._unsupported(), [{"pattern": "p", "location": "x"}])
        self.assertEqual((out["unsupported_count"], out["unsupported_appended_count"]), (1, 1))

    def test_unsupported_append_fails_on_broken_existing_file(self):
        self._write_candidates([("☑", "keep", "CRS SP項目", "—", "", "", "")])
        cand_before = self.cand_path.read_text(encoding="utf-8")
        self.unsup_path.write_text("{broken", encoding="utf-8")
        self._input(entry_points=["newep"], unsupported_patterns=[{"pattern": "p", "location": "x"}])
        code, err = self._run_fail(self._append_argv())
        self.assertEqual(code, 1)
        self.assertIn(str(self.unsup_path), err)
        self.assertEqual(self.cand_path.read_text(encoding="utf-8"), cand_before)
        self.assertEqual(self.unsup_path.read_text(encoding="utf-8"), "{broken")
        self.assertFalse(list(self.work.glob("*.tmp")))


class ClassSeedTest(_PrelimTestBase):
    def _setup_repo(self):
        self._write_file("a.cpp", "void A::write() { write(1); }\nvoid B::write() { write(2); }\n")
        self._write_file("w.h", "void write(int);\n")
        self._write_file("b.c", "int write(int x) { return x; }\n")

    def test_candidates_accept_class_and_init(self):
        self._setup_repo()
        self._write_candidates([("☑", "`write[CLASS:A]`", "下調べ", "x", "", "", "")])
        result = self._run(["seed-preview", "--seed-candidates", str(self.cand_path), "--repo-path", str(self.repo),
                            "--backend", "grep", "--max-files-per-module", "10", "--wave-hit-budget", "100"])
        self.assertEqual(result["adopted_total_hits"], 3)               # C++ のファイル（a.cpp 2行・w.h 1行）だけ
        text = self.cand_path.read_text(encoding="utf-8")
        self.assertIn("| ☑ | `write[CLASS:A]` | 下調べ | x | 2 |", text)
        self.assertIn("クラスで絞る前の件数", text)
        r = self._run(["seed-preview", "--seed-candidates", str(self.cand_path), "--repo-path", str(self.repo),
                       "--backend", "grep", "--slice-h-as", "c"])
        self.assertEqual(r["adopted_total_hits"], 2)                     # .h を C とみなせば数えない
        seeds = mod._parse_seed_candidates(self.cand_path)
        self.assertEqual(mod._seed_adopted_symbols(seeds), ["write[CLASS:A]"])

    def test_class_rows_get_warnings(self):
        self._setup_repo()
        self._write_candidates([("☑", "`nothere[CLASS:A]`", "下調べ", "x", "", "", ""),
                                ("☑", "`write[CLASS:B]`", "下調べ", "x", "", "", "")])
        result = self._run(["seed-preview", "--seed-candidates", str(self.cand_path), "--repo-path", str(self.repo),
                            "--backend", "grep", "--max-files-per-module", "1"])
        self.assertEqual(result["zero_hit"], ["nothere[CLASS:A]"])
        self.assertEqual(result["noisy"], [{"symbol": "write[CLASS:B]", "file_count": 2}])

    def test_seed_input_rejects_class_form(self):
        p = self.work / "seed-input.json"
        p.write_text(json.dumps({"entry_points": [], "crs": ["write[CLASS:A]"],
                                 "inherit": [], "prelim": [], "code_derived": [], "unresolved_entry_points": [],
                                 "unknown_behaviors": [], "unsupported_patterns": []}),
                     encoding="utf-8")
        code, err = self._run_fail(["write-seed-candidates", "--input", str(p), "--out", str(self.cand_path),
                                    "--unsupported-out", str(self.work / "u.json")])
        self.assertEqual(code, 1)
        self.assertIn("CLASS 形式", err)
        self.assertIn(str(p), err)

    def test_resolve_h_as_matches_init(self):
        self._setup_repo()
        self.assertEqual(mod.resolve_h_as("auto", str(self.repo), []), "cpp")
        self.assertEqual(mod.resolve_h_as("c", str(self.repo), []), "c")


class SeedPreviewTest(_PrelimTestBase):

    def _preview(self, extra=(), max_files=2):
        return self._run(["seed-preview", "--seed-candidates", str(self.cand_path), "--repo-path", str(self.repo),
                          "--backend", "grep", "--max-files-per-module", str(max_files)] + list(extra))

    def _preview_fail(self, extra=()):
        return self._run_fail(["seed-preview", "--seed-candidates", str(self.cand_path),
                               "--repo-path", str(self.repo), "--backend", "grep"] + list(extra))

    def _setup_repo(self):
        self._write_file("src/a.c", "foo();\n")
        self._write_file("src/b.c", "foo();\n")
        self._write_file("src/c.py", "# baz is only in a comment\n")
        for i in range(3):
            self._write_file(f"lib/n{i}.c", "route();\n")

    def test_counts_and_warnings(self):
        self._setup_repo()
        self._write_candidates([
            ("☑", "`foo`", "CRS SP項目", "SP-001", "", "", ""),
            ("☑", "`bar`", "下調べ", "x", "", "", ""),
            ("☑", "`baz`", "下調べ", "x", "", "", ""),
            ("☑", "`route`", "CRS SP項目", "x", "", "", ""),
            ("☐", "`qux`", "下調べ", "x", "5", "ヒット過多", "一般語"),
        ])
        result = self._preview()
        self.assertEqual(result["adopted_count"], 4)
        self.assertEqual(result["zero_hit"], ["bar"])
        self.assertEqual(result["zero_after_filter"], ["baz"])
        self.assertEqual(result["noisy"], [{"symbol": "route", "file_count": 3}])
        self.assertFalse(result["all_adopted_noisy"])
        self.assertNotIn("prelim_file_count", result)
        rows = self._candidate_rows()
        self.assertEqual(rows["foo"][4:6], ["2", ""])
        self.assertEqual(rows["bar"][4:6], ["0", "未ヒット"])
        self.assertEqual(rows["baz"][4:6], ["0", "フィルタ後0件"])
        self.assertEqual(rows["route"][4:6], ["3", "ヒット過多"])
        # 除外行は両列を空にし、他の列は保持する
        self.assertEqual(rows["qux"], ["☐", "`qux`", "下調べ", "x", "", "", "一般語"])
        self.assertFalse(self.state_path.exists())

    def test_root_field_counts_arrow_lines_like_search(self):
        self._write_file("src/a.c", "x = server.dirty;\ny = server -> dirty;\n")
        self._write_file("src/b.c", "z = server->dirty;\n")
        self._write_candidates([("☑", "`server.dirty`", "CRS SP項目", "SP-001", "", "", "")])
        result = self._preview()
        self.assertEqual(result["zero_hit"], [])
        self.assertEqual(self._candidate_rows()["server.dirty"][4:6], ["2", ""])

    def test_noisy_boundary_equals_limit_is_not_noisy(self):
        self._setup_repo()
        self._write_candidates([("☑", "foo", "CRS SP項目", "", "", "", "")])
        result = self._preview(max_files=2)
        self.assertEqual(result["noisy"], [])

    def test_all_adopted_noisy(self):
        self._setup_repo()
        self._write_candidates([("☑", "route", "CRS SP項目", "", "", "", ""),
                                ("☐", "foo", "CRS SP項目", "", "", "", "")])
        result = self._preview()
        self.assertTrue(result["all_adopted_noisy"])

    def test_no_adopted_is_not_all_noisy(self):
        self._setup_repo()
        self._write_candidates([("☐", "route", "CRS SP項目", "", "", "", "")])
        result = self._preview()
        self.assertEqual(result["adopted_count"], 0)
        self.assertFalse(result["all_adopted_noisy"])

    def test_preserves_escaped_pipe_and_other_sections(self):
        self._setup_repo()
        self._write_candidates([("☑", "foo", "CRS SP項目", r"a \| b", "", "", "")],
                               unresolved=[("`badEP`", "見つからない")])
        before = self.cand_path.read_text(encoding="utf-8")
        self._preview()
        after = self.cand_path.read_text(encoding="utf-8")
        self.assertIn(r"| ☑ | foo | CRS SP項目 | a \| b | 2 |  |  |", after)
        self.assertEqual(before.split("## 解決できなかった ENTRY_POINT")[1],
                         after.split("## 解決できなかった ENTRY_POINT")[1])

    def test_ledger_counts_only_prelim_rows(self):
        self._setup_repo()
        self._write_candidates([("☑", "foo", "CRS SP項目", "", "", "", "")])
        self._write_ledger([("src/auth/a.c", "auth", "src/auth", "下調べ"),
                            ("src/auth/b.c", "auth", "src/auth", "下調べ"),
                            ("src/net/n.c", "net", "src/net", "下調べ"),
                            ("src/db/d.c", "db", "src/db", "追加下調べ")])
        result = self._preview(["--ledger", str(self.ledger_path)])
        self.assertEqual(result["prelim_module_count"], 2)
        self.assertEqual(result["prelim_file_count"], 3)

    def test_ledger_absent_counts_zero(self):
        self._setup_repo()
        self._write_candidates([("☑", "foo", "CRS SP項目", "", "", "", "")])
        result = self._preview(["--ledger", str(self.ledger_path)])
        self.assertEqual((result["prelim_module_count"], result["prelim_file_count"]), (0, 0))

    def test_ledger_pair_conflict_exit_1_without_rewriting_candidates(self):
        self._setup_repo()
        self._write_candidates([("☑", "foo", "CRS SP項目", "", "", "", "")])
        before = self.cand_path.read_text(encoding="utf-8")
        for rows in ([("src/a/x.c", "auth", "src/a", "下調べ"), ("src/b/y.c", "auth", "src/b", "下調べ")],
                     [("src/a/x.c", "auth", "src/a", "下調べ"), ("src/a/y.c", "auth2", "src/a", "下調べ")]):
            with self.subTest(rows=rows):
                self._write_ledger(rows)
                code, err = self._preview_fail(["--ledger", str(self.ledger_path)])
                self.assertEqual(code, 1)
                self.assertIn(str(self.ledger_path), err)
                self.assertNotIn(str(self.cand_path), err)
                self.assertEqual(self.cand_path.read_text(encoding="utf-8"), before)

    def test_ledger_row_consistency_exit_1(self):
        self._setup_repo()
        self._write_candidates([("☑", "foo", "CRS SP項目", "", "", "", "")])
        cases = {
            "not_under": [("src/b/x.c", "auth", "src/a", "下調べ")],
            "longest_mismatch": [("src/a/sub/s.c", "auth", "src/a", "下調べ"),
                                 ("src/a/sub/t.c", "authsub", "src/a/sub", "下調べ")],
        }
        for name, rows in cases.items():
            with self.subTest(case=name):
                self._write_ledger(rows)
                code, err = self._preview_fail(["--ledger", str(self.ledger_path)])
                self.assertEqual(code, 1)
                self.assertIn(str(self.ledger_path), err)

    def test_ledger_root_dot_row_with_nested_file_exit_1(self):
        self._setup_repo()
        self._write_candidates([("☑", "foo", "CRS SP項目", "", "", "", "")])
        self._write_ledger([("main.c", "root", ".", "下調べ"), ("src/x.c", "root", ".", "下調べ")])
        code, err = self._preview_fail(["--ledger", str(self.ledger_path)])
        self.assertEqual(code, 1)
        self.assertIn(str(self.ledger_path), err)

    def test_candidates_format_errors_exit_1_with_candidates_path(self):
        self._setup_repo()
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ")])
        good = [("☑", "foo", "CRS SP項目", "", "", "", "")]
        cases = {
            "bad_mark": lambda: self._write_candidates([("x", "foo", "CRS SP項目", "", "", "", "")]),
            "column_count": lambda: self._write_candidates([("☑", "foo", "CRS SP項目", "", "", "")]),
            "missing_heading": lambda: self.cand_path.write_text(
                self.cand_path.read_text(encoding="utf-8").replace("## 候補\n", ""), encoding="utf-8"),
            "missing_sub_heading": lambda: self.cand_path.write_text(
                self.cand_path.read_text(encoding="utf-8").replace("## 識別子を特定できなかった振る舞い\n", ""),
                encoding="utf-8"),
            "unknown_origin": lambda: self._write_candidates([("☑", "foo", "CRS", "", "", "", "")]),
        }
        for name, prepare in cases.items():
            with self.subTest(case=name):
                self._write_candidates(good)
                prepare()
                code, err = self._preview_fail(["--ledger", str(self.ledger_path)])
                self.assertEqual(code, 1)
                self.assertIn(str(self.cand_path), err)
                self.assertNotIn(str(self.ledger_path), err)

    def test_ledger_format_errors_exit_1_with_ledger_path(self):
        self._setup_repo()
        self._write_candidates([("☑", "foo", "CRS SP項目", "", "", "", "")])
        cases = {
            "column_count": "| ファイルパス | モジュール | モジュールディレクトリ | 工程 | 関係する振る舞い（CRS） |\n"
                            "|---|---|---|---|---|\n| src/a/x.c | auth | src/a | 下調べ |\n",
            "missing_header": "# 文書化済みファイル台帳\n\n| a | b |\n|---|---|\n",
            "bad_phase": "| ファイルパス | モジュール | モジュールディレクトリ | 工程 | 関係する振る舞い（CRS） |\n"
                         "|---|---|---|---|---|\n| src/a/x.c | auth | src/a | 調査 | x |\n",
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                self.ledger_path.write_text(text, encoding="utf-8")
                code, err = self._preview_fail(["--ledger", str(self.ledger_path)])
                self.assertEqual(code, 1)
                self.assertIn(str(self.ledger_path), err)
                self.assertNotIn(str(self.cand_path), err)

    def test_missing_candidates_file_fails_loud(self):
        code, err = self._preview_fail()
        self.assertEqual(code, 1)
        self.assertIn(str(self.cand_path), err)


class InitSeedCandidatesTest(_PrelimTestBase):

    def _init_argv(self, extra=()):
        return ["init", "--path", str(self.state_path), "--repo-path", str(self.repo),
                "--discovery-log", str(self.log_path), "--today", "2026-10-01", "--cr", "CR-2026-999",
                "--repo", "svc"] + list(extra)

    def _origin_rows(self):
        log = self.log_path.read_text(encoding="utf-8")
        sec = log[log.index(mod.ORIGIN_HEADING):log.index(mod.GREP_UNSUPPORTED_HEADING)]
        rows = {}
        for line in sec.split("\n"):
            cells = mod._split_row(line)
            if len(cells) == 3 and cells[0] not in ("由来", "---"):
                rows[cells[0]] = cells[1:]
        return rows

    def _full_candidates(self):
        self._write_candidates(
            [("☑", "`ep1`", "ENTRY_POINTS", "", "", "", ""),
             ("☑", "`crs1`", "CRS SP項目", "SP-001", "", "", ""),
             ("☑", "`pre1`", "下調べ", "auth.c で定義", "", "", ""),
             ("☑", "`code1`", "母体コードから補完", "呼び出し元", "", "", ""),
             ("☑", "`inh1`", "継承展開", "", "", "", ""),
             ("☑", "`add1`", "人が追加", "人の指定", "", "", ""),
             ("☐", "`rej1`", "下調べ", "x", "", "", "一般語"),
             ("☐", "`ep2`", "ENTRY_POINTS", "", "", "", "対象外")],
            unresolved=[("`badEP`", "見つからない")],
            unknown=[("ログ出力の抑止", "src/")])

    def test_initial_symbols_entry_points_and_origin_rows(self):
        self._full_candidates()
        result = self._run(self._init_argv(["--seed-candidates", str(self.cand_path)]))
        self.assertEqual(result["frontier_count"], 6)
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(data["frontier"], ["ep1", "crs1", "pre1", "code1", "inh1", "add1"])
        self.assertEqual(data["entry_point_symbols"], ["ep1", "add1"])
        log = self.log_path.read_text(encoding="utf-8")
        self.assertIn("- 初期シンボル（Wave 0）:\n  - `ep1`\n  - `crs1`\n", log)
        self.assertNotIn("`rej1`\n", log.split(mod.ORIGIN_HEADING)[0])
        rows = self._origin_rows()
        self.assertEqual(list(rows), [mod.ORIGIN_ROW_ENTRY_POINTS] + list(mod.ORIGIN_OTHER_ROWS))
        self.assertEqual(rows["ENTRY_POINTS（人が明示指定）"], ["`ep1`", "—"])
        self.assertEqual(rows["CRS SP項目"], ["`crs1`", "—"])
        self.assertEqual(rows["下調べ（Step A-Prelim）"], ["`pre1`", "`pre1`: auth.c で定義"])
        self.assertEqual(rows["母体コードから補完"], ["`code1`", "`code1`: 呼び出し元"])
        self.assertEqual(rows["継承展開"], ["`inh1`", "—"])
        self.assertEqual(rows["確認時に人が追加"], ["`add1`", "`add1`: 人の指定"])
        self.assertEqual(rows["確認時に人が除外"], ["`rej1`, `ep2`", "`rej1`: 一般語; `ep2`: 対象外"])
        self.assertEqual(rows["解決できなかった ENTRY_POINT"], ["`badEP`", "`badEP`: 見つからない"])
        self.assertEqual(rows["シンボル不明"], ["（特定できず）", "ログ出力の抑止（要確認）"])

    def test_empty_rows_use_empty_cells(self):
        self._write_candidates([("☑", "crs1", "CRS SP項目", "", "", "", "")])
        self._run(self._init_argv(["--seed-candidates", str(self.cand_path)]))
        rows = self._origin_rows()
        self.assertEqual(rows[mod.ORIGIN_ROW_ENTRY_POINTS], [mod.ORIGIN_EMPTY_CELL, "—"])
        for name in mod.ORIGIN_OTHER_ROWS:
            if name != mod.ORIGIN_ROW_CRS:
                self.assertEqual(rows[name], [mod.ORIGIN_NONE_CELL, "—"], name)
        self.assertEqual(json.loads(self.state_path.read_text(encoding="utf-8"))["entry_point_symbols"], [])

    def test_exclusive_with_symbols_and_entry_point_symbols(self):
        self._full_candidates()
        for extra in (["--symbols", "a"], ["--symbols", ""], ["--entry-point-symbols", "a"]):
            with self.subTest(extra=extra):
                code, _err = self._run_fail(self._init_argv(["--seed-candidates", str(self.cand_path)] + extra))
                self.assertEqual(code, 2)
                self.assertFalse(self.state_path.exists())
                self.assertFalse(self.log_path.exists())

    def test_zero_adopted_exit_1(self):
        self._write_candidates([("☐", "a", "CRS SP項目", "", "", "", "理由")])
        code, err = self._run_fail(self._init_argv(["--seed-candidates", str(self.cand_path)]))
        self.assertEqual(code, 1)
        self.assertFalse(self.state_path.exists())
        self.assertFalse(self.log_path.exists())

    def test_existing_discovery_log_exit_1(self):
        self._full_candidates()
        self.log_path.write_text("# 残骸\n", encoding="utf-8")
        code, _err = self._run_fail(self._init_argv(["--seed-candidates", str(self.cand_path)]))
        self.assertEqual(code, 1)
        self.assertFalse(self.state_path.exists())
        self.assertEqual(self.log_path.read_text(encoding="utf-8"), "# 残骸\n")

    def test_candidates_format_error_exit_1_without_state(self):
        self._write_candidates([("?", "a", "CRS SP項目", "", "", "", "")])
        code, err = self._run_fail(self._init_argv(["--seed-candidates", str(self.cand_path)]))
        self.assertEqual(code, 1)
        self.assertIn(str(self.cand_path), err)
        self.assertFalse(self.state_path.exists())

    def test_unsupported_patterns_recorded(self):
        self._full_candidates()
        up = self.work / "seed-unsupported.json"
        up.write_text(json.dumps([{"pattern": "re-export", "location": "src/index.ts:3", "note": "export *"}]),
                      encoding="utf-8")
        self._run(self._init_argv(["--seed-candidates", str(self.cand_path), "--unsupported-patterns", str(up)]))
        log = self.log_path.read_text(encoding="utf-8")
        sec = log[log.index(mod.GREP_UNSUPPORTED_HEADING):]
        self.assertIn("| re-export | src/index.ts:3（export *） | ⬜ 未確認 |", sec)

    def test_unsupported_patterns_absent_or_empty_is_noop(self):
        for content in (None, "[]"):
            with self.subTest(content=content):
                for p in (self.state_path, self.state_path.with_suffix(".md"), self.log_path):
                    if p.exists():
                        p.unlink()
                up = self.work / "seed-unsupported.json"
                if up.exists():
                    up.unlink()
                if content is not None:
                    up.write_text(content, encoding="utf-8")
                self._run(self._init_argv(["--symbols", "a", "--unsupported-patterns", str(up)]))
                log = self.log_path.read_text(encoding="utf-8")
                self.assertTrue(log.rstrip("\n").endswith("|---|---|---|"))

    def test_symbols_mode_still_works_without_seed_candidates(self):
        self._run(self._init_argv(["--symbols", "a,b", "--entry-point-symbols", "b"]))
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(data["frontier"], ["a", "b"])
        self.assertEqual(self._origin_rows()[mod.ORIGIN_ROW_ENTRY_POINTS][0], "`b`")

    def test_symbols_omitted_means_empty(self):
        self._run(self._init_argv())
        self.assertEqual(json.loads(self.state_path.read_text(encoding="utf-8"))["frontier"], [])


class DocTargetsTest(_PrelimTestBase):

    def _doc(self, ledger=True, memo=False, assignments=False):
        argv = ["doc-targets", "--path", str(self.state_path)]
        if ledger:
            argv += ["--ledger", str(self.ledger_path)]
        if memo:
            argv += ["--memo", str(self.memo_path)]
        if assignments:
            argv += ["--module-assignments", str(self.assign_path)]
        return argv

    def _write_assign(self, pairs):
        self.assign_path.write_text(json.dumps([{"module": m, "module_dir": d} for m, d in pairs]), encoding="utf-8")

    def _targets(self, result):
        return {t["file"]: (t["module"], t["module_dir"]) for t in result["doc_targets"]}

    def test_three_sets_and_derived_fields(self):
        self._write_state({"src/a/x.c": "HIGH", "src/a/y.c": "MEDIUM", "src/b/z.c": "HIGH",
                           "lib/m.c": "HIGH", "top.c": "HIGH"})
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ"),
                            ("old/gone.c", "old", "old", "追加下調べ"),
                            ("lib/m.c", "lib", "lib", "下調べ")])
        result = self._run(self._doc())
        self.assertEqual(result["doc_targets"], [
            {"file": "src/a/y.c", "confidence": "MEDIUM", "module": "auth", "module_dir": "src/a"},
            {"file": "src/b/z.c", "confidence": "HIGH", "module": "", "module_dir": ""},
            {"file": "top.c", "confidence": "HIGH", "module": "", "module_dir": ""},
        ])
        # 確定した台帳のファイルは documented_confirmed に入り、doc_targets・unconfirmed には入らない
        self.assertEqual(result["documented_confirmed"], ["lib/m.c", "src/a/x.c"])
        self.assertEqual(result["unconfirmed_documented"], ["old/gone.c"])
        self.assertEqual(result["unassigned"], ["src/b/z.c", "top.c"])
        self.assertEqual(result["doc_target_modules"], ["_root", "src"])
        self.assertEqual(result["module_file_counts"], {"auth": 2, "lib": 1, "old": 1})
        self.assertEqual(result["current_layout"], "none")
        self.assertEqual(result["memo_pruned"], 0)

    def test_directory_boundary(self):
        self._write_state({"src/ab/x.c": "HIGH", "src/a/y.c": "HIGH"})
        self._write_ledger([("src/a/k.c", "a", "src/a", "下調べ")])
        targets = self._targets(self._run(self._doc()))
        self.assertEqual(targets["src/ab/x.c"], ("", ""))
        self.assertEqual(targets["src/a/y.c"], ("a", "src/a"))

    def test_module_assignments_applied(self):
        self._write_state({"src/b/z.c": "HIGH", "src/b/w.c": "MEDIUM"})
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ")])
        self._write_assign([("billing", "src/b")])
        result = self._run(self._doc(assignments=True))
        self.assertEqual(self._targets(result)["src/b/z.c"], ("billing", "src/b"))
        self.assertEqual(result["unassigned"], [])
        self.assertEqual(result["module_file_counts"], {"auth": 1, "billing": 2})

    def test_multiple_functional_dirs_under_src(self):
        self._write_state({"src/auth/a.c": "HIGH", "src/net/n.c": "HIGH", "src/auth/sub/s.c": "HIGH",
                           "src/auth/deep/d.c": "MEDIUM"})
        self._write_ledger([("src/auth/k.c", "auth", "src/auth", "下調べ"),
                            ("src/net/k.c", "net", "src/net", "下調べ"),
                            ("src/auth/sub/k.c", "authsub", "src/auth/sub", "下調べ")])
        targets = self._targets(self._run(self._doc()))
        self.assertEqual(targets["src/auth/a.c"], ("auth", "src/auth"))
        self.assertEqual(targets["src/net/n.c"], ("net", "src/net"))
        self.assertEqual(targets["src/auth/sub/s.c"], ("authsub", "src/auth/sub"))
        self.assertEqual(targets["src/auth/deep/d.c"], ("auth", "src/auth"))

    def test_single_child_java_layout(self):
        base = "src/main/java/com/example"
        self._write_state({f"{base}/auth/A.java": "HIGH", f"{base}/billing/B.java": "HIGH"})
        self._write_ledger([(f"{base}/auth/K.java", "auth", f"{base}/auth", "下調べ")])
        result = self._run(self._doc())
        self.assertEqual(self._targets(result)[f"{base}/auth/A.java"], ("auth", f"{base}/auth"))
        self.assertEqual(result["unassigned"], [f"{base}/billing/B.java"])
        self.assertEqual(result["doc_target_modules"], ["src"])

    def test_ledger_pair_conflicts_exit_1(self):
        self._write_state({"src/a/x.c": "HIGH"})
        for rows in ([("src/a/x.c", "auth", "src/a", "下調べ"), ("src/b/y.c", "auth", "src/b", "下調べ")],
                     [("src/a/x.c", "auth", "src/a", "下調べ"), ("src/a/y.c", "auth2", "src/a", "下調べ")]):
            with self.subTest(rows=rows):
                self._write_ledger(rows)
                code, err = self._run_fail(self._doc())
                self.assertEqual(code, 1)
                self.assertIn(str(self.ledger_path), err)

    def test_ledger_row_not_under_dir_or_longest_mismatch_exit_1(self):
        self._write_state({"src/a/x.c": "HIGH"})
        for rows in ([("src/b/x.c", "auth", "src/a", "下調べ")],
                     [("src/a/sub/s.c", "auth", "src/a", "下調べ"),
                      ("src/a/sub/t.c", "authsub", "src/a/sub", "追加下調べ")]):
            with self.subTest(rows=rows):
                self._write_ledger(rows)
                code, err = self._run_fail(self._doc())
                self.assertEqual(code, 1)
                self.assertIn(str(self.ledger_path), err)

    def test_module_assignments_invalid_exit_5(self):
        self._write_state({"src/c/x.c": "HIGH"})
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ")])
        cases = {
            "json_syntax": "{not json",
            "not_list": json.dumps({"module": "c", "module_dir": "src/c"}),
            "missing_key": json.dumps([{"module": "c"}]),
            "bad_chars": json.dumps([{"module": "c d", "module_dir": "src/c"}]),
            "same_as_ledger_dir": json.dumps([{"module": "c", "module_dir": "src/a"}]),
            "pair_name_conflict": json.dumps([{"module": "c", "module_dir": "src/c"},
                                              {"module": "c", "module_dir": "src/d"}]),
            "pair_dir_conflict": json.dumps([{"module": "c", "module_dir": "src/c"},
                                             {"module": "d", "module_dir": "src/c"}]),
            "ledger_name_conflict": json.dumps([{"module": "auth", "module_dir": "src/c"}]),
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                self.assign_path.write_text(text, encoding="utf-8")
                code, err = self._run_fail(self._doc(assignments=True))
                self.assertEqual(code, mod.EXIT_ASSIGNMENTS_INVALID)
                self.assertEqual(code, 5)
                self.assertIn(str(self.assign_path), err)

    def test_ledger_violation_takes_precedence_over_assignments(self):
        self._write_state({"src/c/x.c": "HIGH"})
        self._write_ledger([("src/b/x.c", "auth", "src/a", "下調べ")])
        self.assign_path.write_text("{not json", encoding="utf-8")
        code, err = self._run_fail(self._doc(assignments=True))
        self.assertEqual(code, 1)
        self.assertIn(str(self.ledger_path), err)

    def test_exit_1_and_5_do_not_rewrite_memo(self):
        self._write_state({"src/a/x.c": "HIGH"})
        self._write_memo(side_effect_files=["orphan.c", "src/m/*"])
        before = self.memo_path.read_text(encoding="utf-8")
        self._write_ledger([("src/b/x.c", "auth", "src/a", "下調べ")])
        self.assertEqual(self._run_fail(self._doc(memo=True))[0], 1)
        self.assertEqual(self.memo_path.read_text(encoding="utf-8"), before)
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ")])
        self._write_assign([("bad name", "src/c")])
        self.assertEqual(self._run_fail(self._doc(memo=True, assignments=True))[0], 5)
        self.assertEqual(self.memo_path.read_text(encoding="utf-8"), before)

    def test_memo_format_error_exit_1_with_memo_path(self):
        self._write_state({"src/a/x.c": "HIGH"})
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ")])
        cases = {
            "missing_section": lambda t: t.replace("## 入力源\n", ""),
            "missing_file_column": lambda t: t.replace("| ファイルパス | テスト可能性 | 備考 |", "| パス | テスト可能性 | 備考 |"),
            "column_count": lambda t: t.replace("| fn | src/a/x.c | ファイルI/O | x | - |", "| fn | src/a/x.c | ファイルI/O |"),
        }
        for name, fn in cases.items():
            with self.subTest(case=name):
                self._write_memo(side_effect_files=["src/a/x.c"])
                self.memo_path.write_text(fn(self.memo_path.read_text(encoding="utf-8")), encoding="utf-8")
                code, err = self._run_fail(self._doc(memo=True))
                self.assertEqual(code, 1)
                self.assertIn(str(self.memo_path), err)
                self.assertNotIn(str(self.ledger_path), err)

    def test_unused_pair_under_later_ledger_dir_is_allowed(self):
        # 台帳 outer（src/a）の配下でも、配下に台帳の行が無い割り当て inner（src/a/b）は帰属を書き換えないので通る
        self._write_state({"src/a/b/x.c": "HIGH"})
        self._write_assign([("outer", "src/a"), ("inner", "src/a/b")])
        self._write_ledger([("src/a/k.c", "outer", "src/a", "追加下調べ")])
        targets = self._targets(self._run(self._doc(assignments=True)))
        self.assertEqual(targets["src/a/b/x.c"], ("inner", "src/a/b"))

    def test_assignment_rewriting_ledger_row_exit_5(self):
        self._write_state({"src/a/x.c": "HIGH"})
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ"), ("src/a/c/y.c", "auth", "src/a", "下調べ")])
        self._write_assign([("c", "src/a/c")])
        code, err = self._run_fail(self._doc(assignments=True))
        self.assertEqual(code, 5)
        self.assertIn("src/a/c/y.c", err)
        self.assertIn("帰属を書き換えます", err)

    def test_nested_assignment_without_ledger_rows_is_allowed(self):
        # doc-limit で台帳に行が無い入れ子のモジュール（zebra/dpdk）
        self._write_state({"zebra/dpdk/d.c": "HIGH"})
        self._write_ledger([("zebra/a.c", "zebra", "zebra", "追加下調べ")])
        self._write_assign([("zebra-dpdk", "zebra/dpdk")])
        targets = self._targets(self._run(self._doc(assignments=True)))
        self.assertEqual(targets["zebra/dpdk/d.c"], ("zebra-dpdk", "zebra/dpdk"))

    def test_nested_assignment_with_ledger_rows_exit_5(self):
        self._write_state({"zebra/b.c": "HIGH"})
        self._write_ledger([("zebra/a.c", "zebra", "zebra", "追加下調べ"),
                            ("zebra/dpdk/x.c", "zebra", "zebra", "追加下調べ")])
        self._write_assign([("zebra-dpdk", "zebra/dpdk")])
        code, err = self._run_fail(self._doc(assignments=True))
        self.assertEqual(code, 5)
        self.assertIn("zebra/dpdk/x.c", err)

    def test_ancestor_assignment_is_allowed(self):
        self._write_state({"lib/b.c": "HIGH"})
        self._write_ledger([("lib/foo/a.c", "foo", "lib/foo", "追加下調べ")])
        self._write_assign([("lib", "lib")])
        targets = self._targets(self._run(self._doc(assignments=True)))
        self.assertEqual(targets["lib/b.c"], ("lib", "lib"))

    def test_assignment_exactly_matching_ledger_is_exempt_and_used(self):
        self._write_state({"src/b/z.c": "HIGH", "src/c/w.c": "HIGH"})
        self._write_ledger([("src/b/old.c", "billing", "src/b", "追加下調べ")])
        self._write_assign([("billing", "src/b"), ("core", "src/c")])
        result = self._run(self._doc(assignments=True))
        targets = self._targets(result)
        self.assertEqual(targets["src/b/z.c"], ("billing", "src/b"))
        self.assertEqual(targets["src/c/w.c"], ("core", "src/c"))
        # 2回目（台帳に core も書かれた後の再実行）でも exit 5 にならない
        self._write_ledger([("src/b/old.c", "billing", "src/b", "追加下調べ"),
                            ("src/c/w.c", "core", "src/c", "追加下調べ")])
        result = self._run(self._doc(assignments=True))
        self.assertEqual(result["module_file_counts"], {"billing": 2, "core": 1})

    def test_module_file_counts_no_double_count(self):
        self._write_state({"src/a/x.c": "HIGH", "src/a/y.c": "HIGH"})
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ")])
        self.assertEqual(self._run(self._doc())["module_file_counts"], {"auth": 2})

    def test_current_layout_values(self):
        self._write_state({"src/a/x.c": "HIGH"}, cr="CR-2026-999")
        self.assertEqual(self._run(self._doc())["current_layout"], "none")
        (self.out / "SPO-CR-2026-999.md").write_text("# SPO\n", encoding="utf-8")
        self.assertEqual(self._run(self._doc())["current_layout"], "integrated")
        (self.out / "modules").mkdir()
        self.assertEqual(self._run(self._doc())["current_layout"], "split")

    def test_memo_prunes_orphan_and_glob_rows(self):
        self._write_state({"src/a/x.c": "HIGH"})
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ")])
        self._write_memo(side_effect_files=["src/a/x.c", "orphan.c", "src/m/*", "./*"],
                         testability_files=["`src/a/x.c`", "other/y.c"])
        result = self._run(self._doc(memo=True))
        self.assertEqual(result["memo_pruned"], 4)
        text = self.memo_path.read_text(encoding="utf-8")
        self.assertIn("| fn | src/a/x.c | ファイルI/O | x | - |", text)
        self.assertIn("| `src/a/x.c` | 高 | - |", text)
        for gone in ("orphan.c", "src/m/*", "./*", "other/y.c"):
            self.assertNotIn(gone, text)
        for heading in mod.OBS_MEMO_SECTIONS:
            self.assertEqual(text.count(heading + "\n"), 1)
        # 冪等: 再実行では何も除去しない
        self.assertEqual(self._run(self._doc(memo=True))["memo_pruned"], 0)

    def test_ledger_and_memo_absent(self):
        self._write_state({"src/a/x.c": "HIGH"})
        result = self._run(self._doc(memo=True))
        self.assertEqual([t["file"] for t in result["doc_targets"]], ["src/a/x.c"])
        self.assertEqual(result["documented_confirmed"], [])
        self.assertEqual(result["unconfirmed_documented"], [])
        self.assertEqual(result["unassigned"], ["src/a/x.c"])
        self.assertEqual(result["module_file_counts"], {})
        self.assertEqual(result["memo_pruned"], 0)
        self.assertFalse(self.memo_path.exists())

    def test_missing_state_fails_loud(self):
        code, _err = self._run_fail(self._doc())
        self.assertEqual(code, 1)

    # -- リポジトリ直下のファイルからなるモジュール（モジュールディレクトリ "."）--

    def test_root_dot_module_matches_only_top_level_files(self):
        self._write_state({"util.c": "HIGH", "src/x.c": "HIGH"})
        self._write_ledger([("main.c", "root", ".", "下調べ")])
        result = self._run(self._doc())
        targets = self._targets(result)
        self.assertEqual(targets["util.c"], ("root", "."))
        self.assertEqual(targets["src/x.c"], ("", ""))
        self.assertEqual(result["unassigned"], ["src/x.c"])
        self.assertEqual(result["module_file_counts"], {"root": 2})

    def test_root_dot_module_dir_normalized(self):
        self._write_state({"util.c": "HIGH"})
        for cell in ("./", "`.`", ""):
            with self.subTest(cell=cell):
                self._write_ledger([("main.c", "root", cell, "下調べ")])
                self.assertEqual(self._targets(self._run(self._doc()))["util.c"], ("root", "."))

    def test_root_dot_ledger_row_with_nested_file_exit_1(self):
        self._write_state({"util.c": "HIGH"})
        self._write_ledger([("src/x.c", "root", ".", "下調べ")])
        code, err = self._run_fail(self._doc())
        self.assertEqual(code, 1)
        self.assertIn(str(self.ledger_path), err)

    def test_root_dot_is_not_parent_of_other_dirs_in_assignments(self):
        # 台帳に "." があっても、サブディレクトリの組は「台帳のモジュールディレクトリの下」にならない
        self._write_state({"src/b/z.c": "HIGH", "top.c": "HIGH"})
        self._write_ledger([("main.c", "root", ".", "下調べ")])
        self._write_assign([("billing", "src/b")])
        result = self._run(self._doc(assignments=True))
        self.assertEqual(self._targets(result)["src/b/z.c"], ("billing", "src/b"))
        self.assertEqual(self._targets(result)["top.c"], ("root", "."))
        # 逆に、台帳にサブディレクトリがあっても "." の組（"./"・空文字列も "." と同じ）は追加できる
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ")])
        for d in (".", "./", ""):
            with self.subTest(module_dir=d):
                self._write_assign([("top", d)])
                result = self._run(self._doc(assignments=True))
                self.assertEqual(self._targets(result)["top.c"], ("top", "."))
                self.assertEqual(self._targets(result)["src/b/z.c"], ("", ""))
        # 台帳の "." と同じディレクトリの別名の組は exit 5
        self._write_ledger([("main.c", "root", ".", "下調べ")])
        self._write_assign([("top", "./")])
        self.assertEqual(self._run_fail(self._doc(assignments=True))[0], 5)


    # -- 追加下調べの対象（--only seed-direct）--

    def _seed_state(self, files, hits=None, resolved=()):
        """files: シードの直接参照（すべて確定ファイル）。hits: {ファイル: シードのヒット行数}。resolved: 同一性 resolved のファイル。"""
        self._write_state({f: "HIGH" for f in files})
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        for f in files:
            data["confirmed_files"][f]["identity"] = "resolved" if f in resolved else "name-only"
        data["seed_direct_files"] = sorted(files)
        data["seed_direct_hits"] = dict(hits or {})
        mod._write_state(self.state_path, data)

    def _seed_doc(self, max_files, reviewed=False):
        argv = self._doc() + ["--only", "seed-direct", "--max-files", str(max_files)]
        if reviewed:
            argv += ["--gap-reviewed", str(self.work / "prelim-gap-reviewed.md")]
        return argv

    def _write_reviewed(self, rows):
        lines = ["# 追加下調べの判断の記録", "", "| ファイルパス | 判断 | 理由 |", "|---|---|---|"]
        lines += [f"| {f} | {j} | {r} |" for f, j, r in rows]
        (self.work / "prelim-gap-reviewed.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_seed_direct_targets_exclude_ledger_and_reviewed(self):
        self._seed_state(["src/a/x.c", "src/a/y.c", "src/a/z.c"])
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ")])
        self._write_reviewed([("src/a/z.c", "関係なし", "名前が同じだけ")])
        result = self._run(self._seed_doc(20, reviewed=True))
        self.assertEqual([t["file"] for t in result["doc_targets"]], ["src/a/y.c"])
        self.assertEqual(result["over_limit_files"], [])
        # 判断の記録を渡さなければ z.c も対象
        self.assertEqual([t["file"] for t in self._run(self._seed_doc(20))["doc_targets"]], ["src/a/y.c", "src/a/z.c"])

    def test_seed_direct_order_and_over_limit(self):
        # resolved を先 → シードのヒット行数の多い順 → パスの順に採り、残りを over_limit_files に返す
        self._seed_state(["src/a/p.c", "src/a/q.c", "src/a/r.c", "src/a/s.c"],
                         hits={"src/a/p.c": 1, "src/a/q.c": 5, "src/a/r.c": 9, "src/a/s.c": 5}, resolved=("src/a/p.c",))
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ")])
        result = self._run(self._seed_doc(2))
        self.assertEqual(sorted(t["file"] for t in result["doc_targets"]), ["src/a/p.c", "src/a/r.c"])
        self.assertEqual(result["over_limit_files"], ["src/a/q.c", "src/a/s.c"])

    def test_seed_direct_limit_is_cumulative(self):
        self._seed_state(["src/a/p.c", "src/a/q.c", "src/a/r.c", "src/a/s.c"])
        # 台帳の `追加下調べ` の行（1）と判断の記録の行（1）の分だけ今回採れる件数が減る（下調べの行は数えない）
        self._write_ledger([("src/a/p.c", "auth", "src/a", "追加下調べ"), ("src/a/x.c", "auth", "src/a", "下調べ")])
        self._write_reviewed([("src/a/q.c", "関係なし", "x")])
        result = self._run(self._seed_doc(3, reviewed=True))
        self.assertEqual([t["file"] for t in result["doc_targets"]], ["src/a/r.c"])
        self.assertEqual(result["over_limit_files"], ["src/a/s.c"])
        # 残りが 0 なら doc_targets は空
        result = self._run(self._seed_doc(2, reviewed=True))
        self.assertEqual(result["doc_targets"], [])
        self.assertEqual(result["over_limit_files"], ["src/a/r.c", "src/a/s.c"])

    def test_seed_direct_requires_max_files(self):
        self._seed_state(["src/a/p.c"])
        self.assertEqual(self._run_fail(self._doc() + ["--only", "seed-direct"])[0], 2)
        self.assertEqual(self._run_fail(self._doc() + ["--max-files", "3"])[0], 2)

    def test_ledger_rejects_old_final_phase(self):
        self._write_state({"src/a/x.c": "HIGH"})
        self._write_ledger([("src/a/x.c", "auth", "src/a", "資料の確定")])
        code, err = self._run_fail(self._doc())
        self.assertEqual(code, 1)
        self.assertIn("`下調べ` / `追加下調べ`", err)

    def test_gap_reviewed_format_errors_exit_1(self):
        self._seed_state(["src/a/p.c"])
        gap = self.work / "prelim-gap-reviewed.md"
        for rows, text in (([("src/a/p.c", "関係あり", "x")], None), (None, "| ファイル | 判断 |\n|---|---|\n"),
                           (None, "| ファイルパス | 判断 | 理由 |\n|---|---|---|\n| a.c | 関係なし |\n")):
            with self.subTest(rows=rows, text=text):
                if rows:
                    self._write_reviewed(rows)
                else:
                    gap.write_text(text, encoding="utf-8")
                code, err = self._run_fail(self._seed_doc(5, reviewed=True))
                self.assertEqual(code, 1)
                self.assertIn(str(gap), err)


class PrelimMetricsTest(_PrelimTestBase):

    def _metrics(self, ledger=True, gate="true"):
        argv = ["prelim-metrics", "--path", str(self.state_path), "--seed-candidates", str(self.cand_path),
                "--seed-gate", gate]
        if ledger:
            argv += ["--ledger", str(self.ledger_path)]
        return argv

    def _events(self):
        p = self.work / "metrics.jsonl"
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

    def _setup(self):
        self._write_candidates([
            ("☑", "p1", "下調べ", "", "2", "", ""),
            ("☑", "p2", "下調べ", "", "0", "未ヒット", ""),
            ("☐", "p3", "下調べ", "", "", "", "一般語"),
            ("☑", "c1", "CRS SP項目", "", "0", "フィルタ後0件", ""),
            ("☑", "h1", "人が追加", "", "30", "ヒット過多", ""),
            ("☐", "e1", "ENTRY_POINTS", "", "", "", "対象外"),
        ])
        self._write_ledger([("src/a/x.c", "auth", "src/a", "下調べ"),
                            ("src/a/y.c", "auth", "src/a", "下調べ"),
                            ("lib/m.c", "lib", "lib", "下調べ"),
                            ("gone/g.c", "gone", "gone", "下調べ"),
                            ("src/b/z.c", "b", "src/b", "追加下調べ")])
        self._write_state({"src/a/x.c": "HIGH", "src/b/z.c": "MEDIUM", "src/c/n.c": "HIGH",
                           "lib/m.c": "HIGH"})

    def test_fields(self):
        self._setup()
        result = self._run(self._metrics(gate="false"))
        events = self._events()
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["event"], "prelim_summary")
        self.assertIn("timestamp", ev)
        self.assertIs(ev["seed_gate"], False)
        self.assertEqual(ev["prelim_file_count"], 4)
        self.assertEqual(ev["prelim_seed_count"], 3)
        self.assertEqual(ev["prelim_seed_adopted_count"], 2)
        self.assertEqual(ev["human_added_count"], 1)
        self.assertEqual(ev["human_removed_count"], 2)
        self.assertEqual(ev["adopted_zero_hit_count"], 2)
        self.assertEqual(ev["adopted_noisy_count"], 1)
        # 確定ファイル全体（HIGH＋MEDIUM）
        self.assertEqual(ev["confirmed_file_count"], 4)
        # 確定 HIGH/MEDIUM − 台帳の工程 下調べ（src/b/z.c は 追加下調べ なので差し引かない）
        self.assertEqual(ev["bfs_only_file_count"], 2)
        self.assertLessEqual(ev["bfs_only_file_count"], ev["confirmed_file_count"])
        # 台帳の工程 下調べ − 確定全体（確定した lib/m.c は引かれる）
        self.assertEqual(ev["prelim_only_file_count"], 2)
        for key, value in ev.items():
            self.assertEqual(result[key], value)
        self.assertTrue(result["ok"])

    def test_ledger_omitted(self):
        self._setup()
        ev = self._run(self._metrics(ledger=False))
        self.assertEqual(ev["prelim_file_count"], 0)
        self.assertEqual(ev["prelim_only_file_count"], 0)
        self.assertEqual(ev["bfs_only_file_count"], ev["confirmed_file_count"])
        self.assertIs(ev["seed_gate"], True)

    def test_second_run_skipped(self):
        self._setup()
        (self.work / "metrics.jsonl").write_text(json.dumps({"wave": 0}) + "\nnot json\n", encoding="utf-8")
        self._run(self._metrics())
        result = self._run(self._metrics())
        self.assertEqual(result["skipped"], "already_recorded")
        self.assertEqual(sum(1 for e in self._events_lenient() if e.get("event") == "prelim_summary"), 1)

    def _events_lenient(self):
        out = []
        for line in (self.work / "metrics.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
        return out

    def test_fail_loud_on_format_errors(self):
        self._setup()
        self.cand_path.write_text("# 候補なし\n", encoding="utf-8")
        code, err = self._run_fail(self._metrics())
        self.assertEqual(code, 1)
        self.assertIn(str(self.cand_path), err)
        self._setup()
        self.ledger_path.write_text("| a | b |\n|---|---|\n", encoding="utf-8")
        code, err = self._run_fail(self._metrics())
        self.assertEqual(code, 1)
        self.assertIn(str(self.ledger_path), err)
        self.assertFalse((self.work / "metrics.jsonl").exists())


class _SlicerBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.work = self.root / "work"
        self.waves = self.work / "waves"
        self.waves.mkdir(parents=True)
        self.state_path = self.work / "bfs-state.json"
        self.log_path = self.root / "discovery-log.md"

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, argv, module=mod):
        args = module.build_parser().parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _run_fail(self, argv, module=mod):
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                args = module.build_parser().parse_args(argv)
                args.func(args)
        return cm.exception.code, err.getvalue()

    def _write(self, rel, content):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _set(self, **kw):
        data = self._state()
        data.update(kw)
        mod._write_state(self.state_path, data)

    def _init(self, symbols, engine="rule", engine_exts=None, ignore="", warning=None, extra=(), **kw):
        probe = self.work / "slice-probe.json"
        probe.write_text(json.dumps({"ok": True, "engine": "slice" if engine == "slice" else "unavailable",
                                     "engine_exts": ENGINE_EXTS if engine_exts is None else engine_exts,
                                     "warning": warning}), encoding="utf-8")
        ign = self.work / "slice-ignore-calls.txt"
        ign.write_text(ignore + "\n", encoding="utf-8")
        argv = ["init", "--path", str(self.state_path), "--repo-path", str(self.repo),
                "--discovery-log", str(self.log_path), "--symbols", symbols, "--today", "2026-10-04",
                "--cr", "CR-2026-970", "--repo", "svc", "--slice-engine", engine, "--probe-file", str(probe),
                "--slice-ignore-calls-file", str(ign), "--exclude", kw.pop("exclude", "")] + list(extra)
        for k, v in kw.items():
            argv += [f"--{k.replace('_', '-')}", str(v)]
        return self._run(argv)

    def _search(self):
        return self._run(["search", "--path", str(self.state_path), "--hits-dir", str(self.waves),
                          "--chunk-size", "40"])

    def _classify_and_commit(self, out, override=None, llm=None):
        """スライス用チャンクを規則判定で判定し（override: {line_id: エントリの上書き}）、LLM 用チャンクは llm
        （{line_id: エントリ}。無ければ propagation-direct・次の波なし）で埋めて merge → commit-wave する。"""
        n = out["wave"]
        s_out = self.waves / f"wave-{n}-chunk-S-class.json"
        self._run(["classify", "--path", str(self.state_path), "--hits", out["slice_chunk"], "--out", str(s_out)],
                  module=slice_mod)
        if override:
            payload = json.loads(s_out.read_text(encoding="utf-8"))
            payload["classification"] = [dict(e, **override.get(e["line_id"], {})) for e in payload["classification"]]
            s_out.write_text(json.dumps(payload), encoding="utf-8")
        class_chunks = [str(s_out)]
        for k, chunk in enumerate(out["chunks"]):
            ch = json.loads(Path(chunk).read_text(encoding="utf-8"))
            entries = [(llm or {}).get(h["line_id"], {"line_id": h["line_id"], "classification": "propagation-direct",
                                                       "next_symbols": [], "enclosing_function": "",
                                                       "is_external_api": False, "note": "stub"})
                       for h in ch["hits"]]
            p = self.waves / f"wave-{n}-chunk-{k}-class.json"
            p.write_text(json.dumps({"chunk_id": ch["chunk_id"], "classification": entries,
                                     "unsupported_patterns": []}), encoding="utf-8")
            class_chunks.append(str(p))
        merged = self.waves / f"wave-{n}-class.json"
        unsup = self.waves / f"wave-{n}-unsupported.json"
        import merge_classification as merge_mod
        with redirect_stdout(io.StringIO()):
            merge_mod.merge(Path(out["hits_file"]), [out["slice_chunk"]] + out["chunks"], class_chunks, merged, unsup)
        return self._run(["commit-wave", "--path", str(self.state_path), "--hits", out["hits_file"],
                          "--classification", str(merged), "--unsupported-patterns", str(unsup),
                          "--chunk-count", str(len(out["chunks"])), "--batch-count", "0", "--today", "2026-10-04"])

    def _verify(self):
        args = verify_mod.build_parser().parse_args(["--log", str(self.log_path), "--wave", "all", "--strict"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _log(self):
        return self.log_path.read_text(encoding="utf-8")


class InitEngineSettingsTest(_SlicerBase):
    def test_init_saves_engine_settings_and_writes_header(self):
        self._write("a.c", "int f(void) { return seed_x; }\n")
        result = self._init("seed_x", engine="slice", max_wave=3, wave_hit_budget=500, llm_hit_budget=20)
        data = self._state()
        self.assertEqual((data["max_wave_depth"], data["wave_origin"], data["wave_hit_budget"],
                          data["llm_hit_budget"], data["slice_engine"], data["engine_exts"], data["slice_h_as"]),
                         (3, 0, 500, 20, "slice", ENGINE_EXTS, "c"))
        self.assertEqual(data["seed_summary_pending"], ["seed_x"])
        self.assertEqual(result["seed_summary_pending_count"], 1)
        log = self._log()
        self.assertIn("- 検索ツール: index（識別子索引。索引で引けないシンボルは", log)
        self.assertIn("- 最大波数: 3（探索の起点の波から数えて 3 波。上限到達時は打ち切り記録を残して自動完了）", log)
        self.assertIn("- 判定先: slice（スライス判定・tree-sitter）: .c,.cc,", log)
        self.assertIn("## 凡例", log)
        self.assertIn("| 打ち切り記録「理由」 | `hit-budget` |", log)
        self.assertLess(log.index("## 凡例"), log.index("## 投入シンボルの由来"))

    def test_rule_engine_does_not_mark_pending(self):
        self._write("a.c", "int f(void) { return seed_x; }\n")
        self._init("seed_x", engine="rule")
        self.assertEqual(self._state()["seed_summary_pending"], [])

    def test_h_as_auto_detects_cpp_sources(self):
        self._write("a.h", "int x;\n")
        self._init("x")
        self.assertEqual(self._state()["slice_h_as"], "c")
        self.tearDown()
        self.setUp()
        self._write("a.h", "int x;\n")
        self._write("b.cpp", "int y;\n")
        self._init("x")
        self.assertEqual(self._state()["slice_h_as"], "cpp")

    def test_probe_warning_and_ignore_calls_with_quotes_survive(self):
        self._write("a.c", "int x;\n")
        warning = "tree-sitter を import できません（ModuleNotFoundError: No module named 'tree_sitter'）"
        self._init("x", warning=warning, ignore=r"log_\w+|\"quoted\"|it's", extra=["--use-probe-warning"])
        self.assertEqual(self._state()["slice_ignore_calls"], r"log_\w+|\"quoted\"|it's")
        self.assertIn(f"> ⚠️ スライス判定エンジン警告: {warning}（規則判定で実行）", self._log())

    def test_ignore_calls_file_reading_rules(self):
        self._write("a.c", "int x;\n")
        p = self.root / "ign.txt"
        p.write_bytes(b" a|b \r\n")
        self.assertEqual(mod._read_ignore_calls(p), " a|b ")
        p.write_bytes(b"a|b\n\n")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            mod._read_ignore_calls(p)

    def test_invalid_ignore_regex_exits_1(self):
        self._write("a.c", "int x;\n")
        code, err = self._run_fail(["init", "--path", str(self.state_path), "--repo-path", str(self.repo),
                                    "--discovery-log", str(self.log_path), "--symbols", "x", "--today", "t",
                                    "--cr", "c", "--repo", "r", "--slice-ignore-calls-file",
                                    str(self._ign("log_(\n"))])
        self.assertEqual(code, 1)
        self.assertIn("正規表現が不正", err)
        self.assertFalse(self.state_path.exists())

    def _ign(self, text):
        p = self.root / "ign2.txt"
        p.write_text(text, encoding="utf-8")
        return p

    def test_unmatched_exclude_pattern_is_warned(self):
        self._write("src/a.c", "int x;\n")
        self._write("lib/legacy/b.c", "int x;\n")
        self._init("x", exclude="lib/legacy/,nosuch/,*.pb.c")
        log = self._log()
        self.assertIn("> ⚠️ 除外パターン警告: nosuch/ に一致するファイルがありません", log)
        self.assertIn("> ⚠️ 除外パターン警告: *.pb.c に一致するファイルがありません", log)
        self.assertNotIn("除外パターン警告: lib/legacy/", log)


class ExclusionPatternTest(_SlicerBase):
    PATTERNS = ["lib/legacy/", "tests/", "*.pb.c", "gen/*.c"]

    def _layout(self):
        for rel in ("src/a.c", "lib/legacy/x.c", "src/legacy/y.c", "src/tests/t.c", "tests/u.c",
                    "proto/m.pb.c", "gen/g.c", "gen/sub/h.c", "lib/legacy2/z.c"):
            self._write(rel, "int target_sym;\n")

    def test_is_excluded_three_forms(self):
        ex = lambda p: mod._is_excluded(p, self.PATTERNS)  # noqa: E731
        self.assertTrue(ex("lib/legacy/x.c"))
        self.assertFalse(ex("src/legacy/y.c"))      # パスで書いたエントリはルートからだけ
        self.assertFalse(ex("lib/legacy2/z.c"))     # ディレクトリ境界
        self.assertTrue(ex("src/tests/t.c"))        # 名前だけのエントリはどの階層でも
        self.assertTrue(ex("tests/u.c"))
        self.assertTrue(ex("proto/m.pb.c"))         # / を含まない glob はファイル名
        self.assertTrue(ex("gen/g.c"))              # / を含む glob はルートからのパス
        self.assertTrue(ex("gen/sub/h.c"))          # fnmatch の * は / にも一致する
        self.assertFalse(ex("src/a.c"))

    def _files_for(self, backend):
        self._layout()
        self._init("target_sym", exclude=",".join(self.PATTERNS), backend=backend)
        out = self._search()
        hits = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))["hits"]
        return sorted({h["file"] for h in hits})

    def test_index_and_grep_exclude_the_same_files(self):
        expected = ["lib/legacy2/z.c", "src/a.c", "src/legacy/y.c"]
        self.assertEqual(self._files_for("auto"), expected)
        self.tearDown()
        self.setUp()
        self.assertEqual(self._files_for("grep"), expected)

    @unittest.skipUnless(mod.shutil.which("rg"), "rg が無い")
    def test_rg_excludes_the_same_files(self):
        self.assertEqual(self._files_for("rg"), ["lib/legacy2/z.c", "src/a.c", "src/legacy/y.c"])


class IndexBackendTest(_SlicerBase):
    def test_root_field_symbol_matches_dot_and_arrow(self):
        self._write("a.c", "void f(void) {\n  server.dirty++;\n  server->dirty = 1;\n  server.dirtyx = 2;\n}\n")
        self._init("server.dirty")
        out = self._search()
        hits = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))["hits"]
        self.assertEqual([(h["line_no"], h["symbol"]) for h in hits], [(2, "server.dirty"), (3, "server.dirty")])

    def test_matching_symbol_handles_non_word_edges(self):
        self.assertEqual(mod._matching_symbol("echo $var", ["Foo::bar", "$var"]), "$var")
        self.assertEqual(mod._matching_symbol("x = server->dirty;", ["server", "server.dirty"]), "server")
        self.assertEqual(mod._matching_symbol("x = server->dirty;", ["server.dirty", "server"]), "server.dirty")

    def test_non_identifier_symbols_are_delegated(self):
        self._write("a.cpp", "void g() { Foo::bar(); }\n")
        self._write("s.sh", "echo $var\n")
        self._write("conf/x.txt", "include conf/x.txt\n")
        self._init("Foo::bar,$var,conf/x.txt,plain")
        out = self._search()
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        self.assertEqual(sorted(h["symbol"] for h in payload["hits"]), ["$var", "Foo::bar", "conf/x.txt"])
        self.assertEqual(len(payload["commands"]), 2)   # 索引で引くシンボル1件＋委譲1件（grep は50件ずつ）
        self.assertEqual(payload["commands"][0]["pattern"], r"\bplain\b")
        self.assertEqual(out["zero_hit_symbols"], ["plain"])

    ROOT_FIELD_SRC = (
        "a = server.dirty;\n"
        "b = server -> dirty ;\n"
        "c = xserver.dirty;\n"
        "d = server.dirtyx;\n"
        "e = s.server.dirty;\n"
        "f = server .\tdirty;\n"
        "g = foo;\n"
    )

    def _hit_lines(self, symbols, backend, medium=False):
        self._write("a.c", self.ROOT_FIELD_SRC)
        self._init(symbols, backend=backend)
        if medium:
            self._set(frontier=[f"{symbols}[MEDIUM:a.c]"])
        out = self._search()
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        self.assertEqual(payload["budget_truncated"], [])
        self.assertEqual(self._state().get("truncated") or [], [])
        return sorted((h["symbol"], h["line_no"]) for h in payload["hits"])

    def _backends(self):
        names = ["grep", "index"]
        if mod.shutil.which("rg"):
            names.append("rg")
        return names

    def test_root_field_pattern_for_grep_and_rg(self):
        self.assertEqual(mod._grep_symbol_pattern("server.dirty"),
                         r"\bserver[[:space:]]*(\.|->)[[:space:]]*dirty\b")
        for sym in ("plain", "$var", "Foo::bar"):
            self.assertEqual(mod._grep_symbol_pattern(sym), mod._word_boundary(sym))

    def test_root_field_is_searched_equally_by_all_backends(self):
        expected = [("server.dirty", n) for n in (1, 2, 5, 6)]
        for backend in self._backends():
            for medium in (False, True):
                with self.subTest(backend=backend, medium=medium):
                    self.tearDown()
                    self.setUp()
                    self.assertEqual(self._hit_lines("server.dirty", backend, medium), expected)

    def test_root_field_mixed_with_identifier_in_one_compound_pattern(self):
        for backend in self._backends():
            with self.subTest(backend=backend):
                self.tearDown()
                self.setUp()
                got = self._hit_lines("server.dirty,foo", backend)
                self.assertEqual([h for h in got if h[0] == "server.dirty"],
                                 [("server.dirty", n) for n in (1, 2, 5, 6)])
                self.assertEqual([h for h in got if h[0] == "foo"], [("foo", 7)])

    def test_root_field_pattern_matches_same_lines_as_python_regex(self):
        import subprocess
        lines = self.ROOT_FIELD_SRC.splitlines()
        py = mod._symbol_regex("server.dirty")
        want = [i for i, ln in enumerate(lines, 1) if py.search(ln)]
        self._write("a.c", self.ROOT_FIELD_SRC)
        out = subprocess.run(["grep", "-n", "-E", mod._grep_symbol_pattern("server.dirty"), str(self.repo / "a.c")],
                             capture_output=True, text=True).stdout
        self.assertEqual([int(r.split(":", 1)[0]) for r in out.splitlines()], want)

    def test_root_field_attribution_with_its_root_in_the_same_command(self):
        for backend in self._backends():
            with self.subTest(backend=backend):
                self.tearDown()
                self.setUp()
                got = self._hit_lines("server.dirty,server", backend)
                # `server->dirty` の行は既存の帰属規則（_matching_symbol）どおりに帰属する
                for sym, n in got:
                    line = self.ROOT_FIELD_SRC.splitlines()[n - 1]
                    self.assertEqual(sym, mod._matching_symbol(line, ["server.dirty", "server"]))

    def test_compound_repr_shows_root_field_as_pattern(self):
        rep = mod._grep_compound_repr(["server.dirty", "foo"])
        self.assertIn(r"\bserver[[:space:]]*(\.|->)[[:space:]]*dirty\b", rep)
        self.assertNotEqual(rep, r"\b(server\.dirty|foo)\b")
        self.assertEqual(mod._grep_compound_repr(["alpha", "beta"]), r"\b(alpha|beta)\b")
        self.assertEqual(mod._grep_compound_repr(["server.dirty"]), mod._grep_symbol_pattern("server.dirty"))


class RoutingAndChunksTest(_SlicerBase):
    def test_hits_are_routed_to_slice_and_llm_chunks(self):
        self._write("a.c", "int f(void) { return sym; }\n")
        self._write("b.js", "function g() { return sym; }\n")
        self._init("sym")
        out = self._search()
        self.assertTrue(out["slice_chunk"].endswith("wave-0-hits-chunk-S.json"))
        self.assertEqual(len(out["chunks"]), 1)
        self.assertEqual((out["slice_hit_count"], out["llm_hit_count"], out["chunk_count"]), (1, 1, 1))
        s = json.loads(Path(out["slice_chunk"]).read_text(encoding="utf-8"))
        self.assertEqual((s["chunk_id"], [h["file"] for h in s["hits"]]), ("W0-KS", ["a.c"]))
        self.assertIn("frontier_summaries", s)
        k = json.loads(Path(out["chunks"][0]).read_text(encoding="utf-8"))
        self.assertEqual((k["chunk_id"], [h["file"] for h in k["hits"]]), ("W0-K0", ["b.js"]))
        commit = self._classify_and_commit(out)
        self.assertEqual(commit["state"], "in-progress")
        self.assertEqual(self._state()["frontier"], ["f"])
        log = self._log()
        self.assertIn("| rule(enclosing) | HIGH | name-only | `f` | seed(sym) |", log)
        self.assertIn("| propagation-direct | HIGH | name-only | — | seed(sym) |", log)
        m = json.loads((self.work / "metrics.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertEqual((m["rule_hits"], m["slice_hits"], m["llm_hits"]), (1, 0, 1))
        self.assertIsNotNone(m["slice_classify_ms"])

    def test_zero_hit_wave_still_writes_slice_chunk_and_commits(self):
        self._write("a.c", "int f(void) { return 0; }\n")
        self._init("nothing_here")
        out = self._search()
        self.assertEqual((out["hit_count"], out["chunks"]), (0, []))
        self.assertTrue(Path(out["slice_chunk"]).is_file())
        commit = self._classify_and_commit(out)
        self.assertEqual(commit["state"], "complete")
        self.assertEqual(self._verify()["mismatch_waves"], [])

    def test_noisy_seed_detected_for_slice_routed_hits(self):
        """C / C++ / Python のヒット（縮退しない）でも、多数のファイルにヒットした投入シンボルは報告される。"""
        for i in range(4):
            self._write(f"m{i}.c", "int f(void) { return common; }\n")
        self._init("common", max_files_per_module=2)
        out = self._search()
        self.assertEqual(out["noisy_seed_symbols"], [{"symbol": "common", "file_count": 4}])
        self.assertTrue(out["all_seeds_noisy"])
        self.assertEqual((out["pre_noisy"], out["noise_collapse_removed"], out["hit_count"]), ([], 0, 4))
        self.assertIn("## ヒット過多の投入シンボル（Wave 0）", self._log())

    def test_funcmap_reads_new_log(self):
        self._write("a.c", "int f(void) { return sym; }\nint g(void) { return f(); }\n")
        self._init("sym")
        self._classify_and_commit(self._search())
        self._classify_and_commit(self._search())
        r = self._run(["funcmap-counts", "--discovery-log", str(self.log_path), "--out", str(self.root / "fm.md")])
        self.assertEqual((r["symbols"], r["skipped_rows"]), (1, 0))

    def test_frontier_summaries_contain_function_symbols_with_summaries(self):
        self._write("a.c", "int f(void) { return g(); }\n")
        self._init("g,VAL")
        summ = {"returns": True, "out": [], "globals": [], "side": False, "closure": []}
        self._set(symbol_summaries={"g": summ, "VAL": summ}, symbol_kinds={"VAL": "value"})
        out = self._search()
        s = json.loads(Path(out["slice_chunk"]).read_text(encoding="utf-8"))
        self.assertEqual(s["frontier_summaries"], {"g": summ})
        hits = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))["hits"]
        self.assertEqual(hits[0]["loc_scope_class"], "HIGH#returns=1;side=0;out=")


class BudgetTest(_SlicerBase):
    def test_hit_budget_prefers_functions_then_fewest_hits(self):
        self._write("a.c", "".join(f"int a{i}(void) {{ return fA; }}\n" for i in range(2))
                    + "".join(f"int b{i}(void) {{ return fB; }}\n" for i in range(5))
                    + "int c0(void) { return vC; }\nint c1(void) { return vC; }\n")
        self._init("fA,fB,vC", wave_hit_budget=4)
        self._set(symbol_kinds={"vC": "value"})
        out = self._search()
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        self.assertEqual(payload["budget_truncated"],
                         [{"wave": 0, "reason": "hit-budget", "symbol": "fB", "hits": 5}])
        self.assertEqual(sorted({h["symbol"] for h in payload["hits"]}), ["fA", "vC"])
        self.assertEqual(out["hit_budget_removed"], 5)
        self.assertEqual(out["budget_truncated_seed_symbols"], [{"symbol": "fB", "hits": 5}])
        self.assertFalse(out["all_seeds_budget_truncated"])
        self.assertNotIn("fB", out["zero_hit_symbols"] + out["zero_after_filter_symbols"])
        self.assertIn("## 予算で打ち切った投入シンボル（Wave 0）", self._log())
        self._classify_and_commit(out)
        log = self._log()
        self.assertIn("| W0-C1 | 9 | 0 | 5 | 0 | 4 | ✅ excluded(dedup=0,filter=5,noise-collapse=0) |", log)
        self.assertIn("| Wave 0 | hit-budget | `fB` | 5 |", log)
        self.assertEqual(self._verify()["mismatch_waves"], [])
        # commit-wave と specout_verify_counts.py は同じ判定の文字列を書く（書き直しても表が変わらない）
        self.assertEqual(self._log(), log)
        brief = self._run(["status", "--path", str(self.state_path), "--brief"])
        self.assertEqual(brief["seed_budget_truncated_count"], 1)
        self.assertNotIn("fB", self._state()["frontier"])
        self.assertIn("fB", self._state()["visited"])

    def test_rule_engine_also_prefers_function_symbols(self):
        self._write("a.c", "int a(void) { return big_fn; }\nint b(void) { return big_fn; }\n"
                    "int c(void) { return small_val; }\n")
        self._init("big_fn,small_val", wave_hit_budget=2)
        self._set(symbol_kinds={"small_val": "value"})
        out = self._search()
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        self.assertEqual([t["symbol"] for t in payload["budget_truncated"]], ["small_val"])

    def test_llm_budget_removes_only_llm_hits(self):
        self._write("a.c", "int f(void) { return sym; }\n")
        self._write("x.js", "sym();\nsym();\n")
        self._write("y.js", "other();\n")
        self._init("sym,other", llm_hit_budget=1)
        out = self._search()
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        self.assertEqual(payload["budget_truncated"],
                         [{"wave": 0, "reason": "llm-budget", "symbol": "sym", "hits": 2}])
        self.assertEqual(sorted((h["file"], h["symbol"]) for h in payload["hits"]),
                         [("a.c", "sym"), ("y.js", "other")])
        self.assertEqual(out["llm_budget_removed"], 2)
        self._classify_and_commit(out)
        self.assertEqual(self._verify()["mismatch_waves"], [])
        self.assertIn("| Wave 0 | llm-budget | `sym` | 2 |", self._log())


class WaveOriginAndExtendTest(_SlicerBase):
    def _complete_at_limit(self):
        self._write("a.c", "int f(void) { return x; }\n")
        self._init("x", max_wave=1)
        self._set(current_wave=1, last_completed_wave=0, frontier=["a", "b"], low_priority_frontier=["c"])
        return self._search()

    def test_extend_restores_wave_limit_entries(self):
        self._complete_at_limit()
        self._set(truncated=self._state()["truncated"] + [{"wave": 0, "reason": "hit-budget", "symbol": "big",
                                                             "hits": 99}])
        result = self._run(["extend", "--path", str(self.state_path), "--max-wave", "3", "--today", "2026-10-05"])
        self.assertEqual((result["extended"], result["restored_count"], result["state"]), (True, 3, "in-progress"))
        data = self._state()
        self.assertEqual((data["frontier"], data["low_priority_frontier"], data["max_wave_depth"]),
                         (["a", "b"], ["c"], 3))
        self.assertEqual([t["reason"] for t in data["truncated"]], ["hit-budget"])   # 予算の打ち切りは戻さない
        self.assertTrue(data["wave_write_complete"])
        log = self._log()
        self.assertIn("## 探索の延長（上限 1 → 3）", log)
        self.assertNotIn("| Wave 1 | wave-limit |", log)
        again = self._run(["extend", "--path", str(self.state_path), "--max-wave", "3", "--today", "2026-10-05"])
        self.assertFalse(again["extended"])
        out = self._search()
        self.assertEqual(out["wave"], 1)

    def test_extend_in_progress_and_complete_without_wave_limit(self):
        self._write("a.c", "int f(void) { return x; }\n")
        self._init("x", max_wave=2)
        r = self._run(["extend", "--path", str(self.state_path), "--max-wave", "5", "--today", "t"])
        self.assertEqual((r["extended"], r["state"], self._state()["max_wave_depth"]), (True, "in-progress", 5))
        self._set(state="complete", frontier=[])
        r = self._run(["extend", "--path", str(self.state_path), "--max-wave", "7", "--today", "t"])
        self.assertEqual((r["restored_count"], r["state"]), (0, "complete"))
        r = self._run(["extend", "--path", str(self.state_path), "--max-wave", "4", "--today", "t"])
        self.assertFalse(r["extended"])
        self.assertEqual(self._state()["max_wave_depth"], 7)

    def test_status_brief_reports_wave_limit_truncation(self):
        self._complete_at_limit()
        brief = self._run(["status", "--path", str(self.state_path), "--brief"])
        self.assertEqual((brief["state"], brief["max_wave_depth"], brief["truncated_wave_limit_count"]),
                         ("complete", 1, 3))

class SeedSummaryPendingTest(_SlicerBase):
    def test_search_exits_6_until_summaries_are_merged(self):
        self._write("a.c", "int seed_fn(int a) { g = a; return a; }\nint g;\nint use(void) { return seed_fn(1); }\n")
        self._init("seed_fn,VALUE_ONLY", engine="slice")
        code, err = self._run_fail(["search", "--path", str(self.state_path), "--hits-dir", str(self.waves)])
        self.assertEqual(code, mod.EXIT_SEED_SUMMARY_PENDING)
        self.assertIn("シード要約の取り込みが済んでいません（2 件）", err)
        self.assertTrue(self._state()["wave_write_complete"])
        summaries = self.work / "seed-summaries.json"
        summaries.write_text(json.dumps({"targets": ["seed_fn", "VALUE_ONLY"], "globals": ["g"],
                                         "summaries": {"seed_fn": {"returns": True, "out": [], "globals": ["g"],
                                                                   "side": False, "closure": []}}}),
                             encoding="utf-8")
        r = self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "g", "--as-seed-globals",
                       "--summaries-file", str(summaries)])
        self.assertEqual((r["summaries_merged"], r["seed_summary_pending_count"]), (1, 0))
        data = self._state()
        self.assertEqual((data["seed_globals"], data["symbol_kinds"]["g"]), (["g"], "variable"))
        self.assertEqual(data["symbol_summaries"]["seed_fn"]["globals"], ["g"])
        out = self._search()
        self.assertEqual(out["wave0_seed_count"], 2)          # シードのグローバルを数えない
        self.assertEqual(out["zero_hit_symbols"], ["VALUE_ONLY"])
        self._set(slice_engine="rule")   # 判定は規則判定で代用する（tree-sitter の無い環境でも実行するため）
        self._classify_and_commit(out)
        log = self._log()
        self.assertIn("| seed-global(g) |", log)
        self.assertIn("| seed(seed_fn) |", log)
        # funcmap-counts は seed-global(X) を数えず、スキップ一覧にも出さない
        counts = self.root / "funcmap.md"
        r = self._run(["funcmap-counts", "--discovery-log", str(self.log_path), "--out", str(counts)])
        self.assertEqual(r["skipped_rows"], 0)
        self.assertNotIn("`g`", counts.read_text(encoding="utf-8"))

    def test_summaries_file_without_definitions_clears_pending(self):
        self._write("a.c", "int x;\n")
        self._init("MACRO_ONLY", engine="slice")
        summaries = self.work / "s.json"
        summaries.write_text(json.dumps({"targets": ["MACRO_ONLY"], "summaries": {}, "globals": []}),
                             encoding="utf-8")
        self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "", "--summaries-file",
                   str(summaries)])
        self.assertEqual(self._state()["seed_summary_pending"], [])
        self.assertEqual(self._search()["wave"], 0)

class PreprocessRecordTest(_SlicerBase):
    MACROS = ("#define X_API\n#define NS_BEGIN namespace n {\n#define NS_END }\n"
              "#define NUM 1\n")

    def test_init_records_neutralized_macros(self):
        self._write("a.h", self.MACROS)
        self._write("b.cpp", "NS_BEGIN\nX_API int f() { return seed_x; }\nNS_END\n")
        self._init("seed_x", engine="slice")
        pre = self._state()["preprocess"]
        self.assertEqual(pre, {"neutralized_macros": 3, "namespace": 2, "decorator": 1, "empty_pair": 0})
        self.assertIn("- 置き換えたマクロ: 3 件（名前空間 2・宣言を飾る 1・空にした組 0）", self._log())
        # specout_slice.py は同じ関数で同じ表を作る
        r = slice_mod.Repo(str(self.repo), h_as="cpp")
        import specout_macros as macros
        self.assertEqual(macros.table_counts(r.neutral()), pre)

    def test_rule_engine_and_switch(self):
        self._write("a.h", self.MACROS)
        self._init("seed_x", engine="rule")
        self.assertNotIn("preprocess", self._state())
        self.assertIn("- 置き換えたマクロ: —（規則判定では置き換えない）", self._log())
        self.tearDown()
        self.setUp()
        self._write("a.h", self.MACROS)
        self._init("seed_x", engine="slice")
        self._run(["switch-engine", "--path", str(self.state_path), "--to", "rule", "--today", "2026-10-11"])
        self.assertNotIn("preprocess", self._state())
        log = self._log()
        self.assertIn("- 置き換えたマクロ: —（規則判定では置き換えない）", log)
        self.assertNotIn("- 置き換えたマクロ: 3 件", log)


class ClassEntryTest(_SlicerBase):
    """エントリ表記 `symbol[CLASS:ClassName]`（C++ のメソッド・メンバー変数）。"""

    def _setup(self):
        self._write("a.cpp", "void A::f() { run(); }\nvoid B::f() { run(); other(); }\nint z = run() + other();\n"
                             "// run in a comment\n")
        self._write("x.h", "int run();\n")
        self._write("b.c", "int run(void) { return 0; }\n")
        self._write("c.py", "def run():\n    pass\n")

    def test_entry_helpers(self):
        self.assertEqual(mod._parse_entry("run[CLASS:A]"), ("run", "A"))
        self.assertEqual(mod._entry_scope_kind("run[CLASS:A]"), mod.SCOPE_CLASS)
        self.assertEqual(mod._format_entry("run", "A", mod.SCOPE_CLASS), "run[CLASS:A]")
        self.assertEqual(mod._frontier_tag("run[CLASS:A]"), "CLASS:A")
        self.assertEqual(mod._confidence_label(mod.LV.KIND_CLASS), "HIGH")
        self.assertEqual([mod.summary_key(e) for e in ("f[CLASS:X]", "f[FILE:a.c]", "f", "f[MEDIUM:a.c]")],
                         ["f[CLASS:X]", "f", "f", "f"])
        mod._validate_frontier_format(["run[CLASS:A]"])
        with redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit):
            mod._validate_frontier_format(["run[CLASS:a/b.cpp]"])
        self.assertIn("CLASS形式", err.getvalue())

    def _search_class(self, frontier, backend="grep", **state):
        self._setup()
        self._init("seed_x", engine="rule", backend=backend)
        self._set(frontier=frontier, **state)
        return self._search()

    def test_search_class_entries_cpp_only_and_duplicated(self):
        backends = ["grep", "index"] + (["rg"] if shutil.which("rg") else [])
        for backend in backends:
            with self.subTest(backend=backend):
                self.tearDown()
                self.setUp()
                out = self._search_class(["run[CLASS:A]", "run[CLASS:B]", "other[CLASS:A]"], backend=backend)
                payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
                cmds = {c["command_id"]: c for c in payload["commands"]}
                self.assertEqual({(c["kind"], c["scope"]) for c in cmds.values()},
                                 {("CLASS", "CLASS:A"), ("CLASS", "CLASS:B")})
                # run は a.cpp の4行（コメント行を含む）と x.h（.h は C++ のソースがあるため cpp）の1行・b.c と c.py は数えない
                counts = sorted((c["scope"], c["pattern"], c["hit_count"]) for c in cmds.values())
                self.assertEqual([n for *_x, n in counts], [2, 5, 5])
                self.assertEqual(payload["metrics"]["raw_hits"], sum(c["hit_count"] for c in cmds.values()))
                self.assertEqual(len({h["line_id"] for h in payload["hits"]}), len(payload["hits"]))
                self.assertFalse(any(h["file"] in ("b.c", "c.py") for h in payload["hits"]))
                self.assertTrue(all(h["scope_file"] is None for h in payload["hits"]))
                self.assertEqual({h["loc_scope_class"] for h in payload["hits"] if h["entry"] == "run[CLASS:B]"},
                                 {"CLASS:B"})
                self._classify_and_commit(out)
                self.assertEqual(self._verify()["mismatch_waves"], [])
                log = self._log()
                self.assertIn("| CLASS | `", log)
                self.assertIn("| CLASS:A |", log)
                self.assertEqual(self._state()["confirmed_files"]["a.cpp"]["confidence"], "HIGH")

    def test_filter_and_dedup_recorded_per_entry(self):
        out = self._search_class(["run[CLASS:A]", "run[CLASS:B]"])
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        self.assertEqual(sorted(f["entry"] for f in payload["filtered_out"]), ["run[CLASS:A]", "run[CLASS:B]"])
        self._classify_and_commit(out)
        self.assertEqual(self._verify()["mismatch_waves"], [])
        self.assertIn("`run[CLASS:A]` | 行コメント", self._log())

    def test_budget_is_per_entry(self):
        out = self._search_class(["run[CLASS:A]", "run[CLASS:B]", "other[CLASS:A]"], wave_hit_budget=6,
                                 symbol_kinds={"other[CLASS:A]": "variable"})
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        cut = [t["symbol"] for t in payload["budget_truncated"]]
        self.assertEqual(len(cut), 1)
        self.assertTrue(cut[0].startswith("run[CLASS:"))   # 関数（run の2エントリ）→ 値（other）の順に採る
        self.assertIn("other[CLASS:A]", {h["entry"] for h in payload["hits"]})
        self._classify_and_commit(out)
        self.assertEqual(self._verify()["mismatch_waves"], [])
        self.assertIn(f"`{cut[0]}`", self._log().split(mod.TRUNCATION_HEADING)[1])

    def test_seed_detection_for_class_and_file_seeds(self):
        self._setup()
        self._init("nohit[CLASS:A],nohit2[FILE:a.cpp],run[CLASS:A]", engine="rule", wave_hit_budget=1)
        out = self._search()
        self.assertEqual(out["zero_hit_symbols"], ["nohit2[FILE:a.cpp]", "nohit[CLASS:A]"])
        self.assertEqual(out["budget_truncated_seed_symbols"], [{"symbol": "run[CLASS:A]", "hits": 4}])

    def test_seed_global_class_entry_does_not_hide_same_base(self):
        self._setup()
        self._init("seed_x", engine="rule")
        self._set(frontier=["run[CLASS:A]", "run[CLASS:B]"], seed_globals=["run[CLASS:B]"])
        out = self._search()
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        self.assertEqual(payload["seed_symbols"], ["run[CLASS:A]"])
        self.assertEqual(out["wave0_seed_count"], 1)
        chunk = json.loads(Path(out["slice_chunk"]).read_text(encoding="utf-8"))
        self.assertEqual(chunk["seed_keys"], ["run[CLASS:A]"])

    def test_seed_entries_match_class_and_file_entries(self):
        # 修飾なしで入れた人のシンボルは今どおり素名で照合する
        self.assertEqual(mod._seed_entries(["run[CLASS:B]"], 1, set(), {"run"}), {"run[CLASS:B]"})
        self.assertEqual(mod._seed_entries(["run[CLASS:B]"], 1, set(), {"run[CLASS:A]"}), set())
        self.assertEqual(mod._seed_entries(["x"], 1, set(), {"x[FILE:p]"}), set())
        self.assertEqual(mod._seed_entries(["x"], 0, {"x[FILE:p]"}, set()), {"x"})

    def test_kinds_and_revisit_use_summary_key(self):
        self._setup()
        self._init("zzz", engine="rule")
        summ = {"returns": True, "out": [], "globals": [], "side": False, "closure": []}
        self._set(visited=["f[CLASS:X]", "f[CLASS:Y]"], symbol_summaries={"f[CLASS:X]": summ, "f[CLASS:Y]": summ},
                  symbol_kinds={"f[CLASS:X]": "function", "f[CLASS:Y]": "function"})
        out = self._search()
        grown = dict(summ, globals=["g"])
        info = {"engine": "slice", "status": "sliced", "escapes": [["return", "f", 1]]}
        self._classify_and_commit(out, override={"W0-R1": {
            "slice": info, "next_symbols": ["f[CLASS:X]"], "next_symbol_kinds": {"f[CLASS:X]": "function"},
            "next_symbol_summaries": {"f[CLASS:X]": grown}}} if out["hit_count"] else None)
        data = self._state()
        if out["hit_count"]:
            self.assertIn("f[CLASS:X]", data["frontier"])
            self.assertNotIn("f[CLASS:Y]", data["frontier"])
            self.assertEqual(data["symbol_summaries"]["f[CLASS:X]"]["globals"], ["g"])

    def test_merge_frontier_seed_globals_and_pending(self):
        self._setup()
        self._init("seed_x", engine="slice")
        self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "m[CLASS:B]", "--as-seed-globals"])
        self.assertEqual(self._state()["symbol_kinds"]["m[CLASS:B]"], "variable")
        data = self._state()
        mod._mark_seed_summary_pending(data, ["f[CLASS:X]", "g[MEDIUM:a.c]"])
        self.assertIn("f[CLASS:X]", data["seed_summary_pending"])
        self.assertIn("g", data["seed_summary_pending"])

    def test_rule_engine_class_entries_are_name_only(self):
        out = self._search_class(["run[CLASS:A]"])
        self._classify_and_commit(out)
        self.assertEqual(self._state()["confirmed_files"]["a.cpp"]["identity"], "name-only")


class SwitchEngineTest(_SlicerBase):
    def test_switch_to_rule(self):
        self._write("a.c", "int x;\n")
        self._init("x", engine="slice")
        r = self._run(["switch-engine", "--path", str(self.state_path), "--to", "rule", "--today", "2026-10-05"])
        self.assertEqual((r["switched"], r["wave"]), (True, 0))
        data = self._state()
        self.assertEqual((data["slice_engine"], data["seed_summary_pending"]), ("rule", []))
        log = self._log()
        self.assertIn("## 判定エンジンの切り替え（Wave 0 から rule）", log)
        self.assertIn("- 判定先: rule（規則判定・標準ライブラリ）", log)
        self.assertEqual(self._search()["wave"], 0)      # exit 6 が解消する
        again = self._run(["switch-engine", "--path", str(self.state_path), "--to", "rule", "--today", "t"])
        self.assertFalse(again["switched"])
        code, _err = self._run_fail(["switch-engine", "--path", str(self.state_path), "--to", "slice",
                                     "--today", "t"])
        self.assertEqual(code, 1)


class RevisitAndSeedDirectTest(_SlicerBase):
    SUMM = {"returns": True, "out": [], "globals": [], "side": False, "closure": []}

    def _setup_wave0(self):
        self._write("a.c", "int f(void) { return s; }\n")
        self._write("b.c", "void g(void) { f(); }\n")
        self._init("s", engine="rule")
        out = self._search()
        info = {"engine": "slice", "status": "sliced", "escapes": [["return", "f", 1]]}
        self._classify_and_commit(out, override={"W0-R1": {"slice": info, "next_symbol_summaries": {"f": self.SUMM}}})
        self.assertEqual(self._state()["frontier"], ["f"])
        self.assertEqual(self._state()["symbol_kinds"]["f"], "function")

    def test_summary_growth_revisits_and_rejudges_callers(self):
        self._setup_wave0()
        out = self._search()   # wave 1: f
        hits = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))["hits"]
        by_file = {h["file"]: h["line_id"] for h in hits}
        self.assertEqual({h["loc_scope_class"] for h in hits}, {"HIGH#returns=1;side=0;out="})
        grown = dict(self.SUMM, side=True)
        info = {"engine": "slice", "status": "sliced", "escapes": [["unknown", "x", 1]]}
        commit = self._classify_and_commit(out, override={
            by_file["a.c"]: {"slice": info, "next_symbols": ["f"], "enclosing_function": "f",
                             "next_symbol_summaries": {"f": grown}},
            by_file["b.c"]: {"slice": info, "next_symbols": ["g"], "enclosing_function": "g",
                             "next_symbol_summaries": {"g": self.SUMM}}})
        self.assertEqual(commit["revisit_count"], 1)
        data = self._state()
        self.assertEqual(sorted(data["frontier"]), ["f", "g"])
        self.assertTrue(data["symbol_summaries"]["f"]["side"])
        self.assertIn("## 要約の拡大による再訪（Wave 1）", self._log())
        self.assertIn("| `f` | side |", self._log())
        out2 = self._search()   # wave 2: 鍵が変わるため b.c の呼び出し元の行は dedup されない
        hits2 = json.loads(Path(out2["hits_file"]).read_text(encoding="utf-8"))["hits"]
        self.assertIn(("b.c", "f"), {(h["file"], h["symbol"]) for h in hits2})
        self.assertEqual(out2["dedup_removed"], 0)
        self._classify_and_commit(out2)
        self.assertEqual(self._verify()["mismatch_waves"], [])

    def test_no_growth_does_not_revisit(self):
        self._setup_wave0()
        out = self._search()
        hits = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))["hits"]
        a_id = next(h["line_id"] for h in hits if h["file"] == "a.c")
        info = {"engine": "slice", "status": "sliced", "escapes": [["return", "f", 1]]}
        commit = self._classify_and_commit(out, override={
            a_id: {"slice": info, "next_symbols": ["f"], "enclosing_function": "f",
                   "next_symbol_summaries": {"f": self.SUMM}}})
        self.assertEqual(commit["revisit_count"], 0)
        self.assertNotIn("f", self._state()["frontier"])

    def test_seed_direct_files_exclude_fp_discard_and_seed_globals(self):
        self._write("a.c", "// s only in a comment\nint q;\n")
        self._write("b.c", "int f(void) { return s; }\n")
        self._write("c.js", "s();\n")
        self._write("d.c", "int h(void) { return gl; }\n")
        self._init("s", engine="rule")
        self._set(frontier=["s", "gl"], seed_globals=["gl"], symbol_kinds={"gl": "value"})
        out = self._search()
        hits = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))["hits"]
        c_id = next(h["line_id"] for h in hits if h["file"] == "c.js")
        llm = {c_id: {"line_id": c_id, "classification": "out-of-scope-discard", "next_symbols": [],
                      "enclosing_function": "", "is_external_api": False, "note": "x"}}
        self._classify_and_commit(out, llm=llm)
        self.assertEqual(self._state()["seed_direct_files"], ["b.c"])
        # ヒット行数もシードのエントリの伝播する判定だけを数える（a.c の偽陽性・c.js の discard・d.c のシードのグローバルは数えない）
        self.assertEqual(self._state()["seed_direct_hits"], {"b.c": 1})
        brief = self._run(["status", "--path", str(self.state_path), "--brief"])
        self.assertEqual(brief["seed_direct_file_count"], 1)
        self.assertNotIn("seed_direct_hits", brief)

class ImportRestoreTest(_SlicerBase):
    def test_import_restores_condition_keys(self):
        self._write("a.c", "int x;\n")
        self._init("x", engine="slice", max_wave=3, wave_hit_budget=50, llm_hit_budget=5, ignore="log_\\w+ ")
        self._set(wave_origin=2, seed_globals=["gl"], truncated=[{"wave": 1, "reason": "hit-budget",
                                                                  "symbol": "big", "hits": 9}])
        md = self.work / "bfs-state.md"
        r = self._run(["import", "--path", str(self.state_path), "--from", str(md)])
        data = self._state()
        self.assertEqual((data["max_wave_depth"], data["wave_origin"], data["wave_hit_budget"],
                          data["llm_hit_budget"], data["slice_engine"], data["engine_exts"], data["slice_h_as"],
                          data["seed_globals"], data["seed_summary_pending"], data["slice_ignore_calls"]),
                         (3, 2, 50, 5, "slice", ENGINE_EXTS, "c", ["gl"], ["x"], "log_\\w+ "))
        self.assertEqual(data["truncated"], [])
        self.assertEqual(data["seed_direct_hits"], {})
        self.assertIn("truncated, symbol_summaries, symbol_kinds", " ".join(r["warnings"]))
        self.assertIn("seed_direct_files, seed_direct_hits", " ".join(r["warnings"]))

    def test_import_warns_when_ignore_file_missing(self):
        self._write("a.c", "int x;\n")
        self._init("x")
        (self.work / "slice-ignore-calls.txt").unlink()
        r = self._run(["import", "--path", str(self.state_path), "--from", str(self.work / "bfs-state.md")])
        self.assertTrue(any("slice-ignore-calls.txt" in w for w in r["warnings"]))


class SeedPreviewBudgetTest(_PrelimTestBase):
    def _preview(self, budget, engine="rule"):
        return self._run(["seed-preview", "--seed-candidates", str(self.cand_path), "--repo-path", str(self.repo),
                          "--backend", "grep", "--max-files-per-module", "2", "--wave-hit-budget", str(budget),
                          "--slice-engine", engine])

    def _setup(self):
        for i in range(4):
            self._write_file(f"m{i}.c", "wide();\n")
        self._write_file("one.c", "deep();\n" * 6)
        self._write_file("two.c", "calm();\n")
        self._write_candidates([("☑", "wide", "CRS SP項目", "-", "", "", ""),
                                ("☑", "deep", "CRS SP項目", "-", "", "", ""),
                                ("☑", "calm", "CRS SP項目", "-", "", "", "")])

    def test_over_budget_is_independent_of_noisy(self):
        self._setup()
        r = self._preview(3)
        rows = self._candidate_rows()
        self.assertEqual(rows["wide"][5], "予算超過・ヒット過多")
        self.assertEqual(rows["deep"][5], "予算超過")
        self.assertEqual(rows["calm"][5], "")
        self.assertEqual([n["symbol"] for n in r["noisy"]], ["wide"])
        self.assertEqual(r["over_budget"], [{"symbol": "wide", "hits": 4}, {"symbol": "deep", "hits": 6}])
        self.assertFalse(r["all_adopted_noisy"])
        self.assertFalse(r["all_adopted_noisy_or_over_budget"])
        self.assertEqual((r["adopted_total_hits"], r["over_budget_total"]), (11, True))

    def test_all_noisy_or_over_budget(self):
        self._setup()
        text = self.cand_path.read_text(encoding="utf-8").replace("| ☑ | calm |", "| ☐ | calm |")
        self.cand_path.write_text(text, encoding="utf-8")
        r = self._preview(3)
        self.assertTrue(r["all_adopted_noisy_or_over_budget"])

    def test_total_note_is_replaced_not_duplicated(self):
        self._setup()
        self._preview(3, engine="slice")
        self._preview(3, engine="slice")
        text = self.cand_path.read_text(encoding="utf-8")
        self.assertEqual(text.count("採用シンボルの合計ヒット数"), 1)
        self.assertIn("> ⚠️ 採用シンボルの合計ヒット数: 11（1波の予算 3 を超えています）", text)
        self.assertIn("シードが書くグローバルは試算に含まれない", text)
        self.assertIn("を超えています）。", text)
        self.assertLess(text.index("採用シンボルの合計ヒット数"), text.index("| 採否 |"))
        self._preview(100)
        text = self.cand_path.read_text(encoding="utf-8")
        self.assertEqual(text.count("採用シンボルの合計ヒット数"), 1)
        self.assertIn("> 採用シンボルの合計ヒット数: 11（1波の予算 100 以内）\n\n| 採否 |", text)
        self._preview(0)
        self.assertNotIn("採用シンボルの合計ヒット数", self.cand_path.read_text(encoding="utf-8"))
        rows = self._candidate_rows()
        self.assertEqual(set(rows), {"wide", "deep", "calm"})

    def test_prelim_metrics_counts_warning_words(self):
        self._setup()
        self._preview(3)
        self._write_state({})
        r = self._run(["prelim-metrics", "--path", str(self.state_path), "--seed-candidates", str(self.cand_path),
                       "--seed-gate", "true"])
        self.assertEqual((r["adopted_noisy_count"], r["adopted_over_budget_count"], r["adopted_total_hits"]),
                         (1, 2, 11))


# -- SPO の仕上げ: doc-targets --auto-assign / ripple-summary / verify-sweep / assemble-spo ---------------

DOC_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "doc"
TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
SUMMARY_TPL = TEMPLATES / "04_specout-summary-template.md"
MODULE_TPL = TEMPLATES / "04_specout-module-template.md"

DRAFT_AUTH = """## 2.A. auth

- ディレクトリ: src/auth
- 既存仕様書: なし

### 2.A.1 処理フロー

ログイン判定の流れ。

### 2.A.2 主要な処理・ロジック

| 識別子 | ファイルパス | 行番号 | 役割 |
|--------|------------|--------|------|
| session_start | src/auth/session.c | 1 | セッション開始 |

### 2.A.7 既存仕様の文書化

#### 2.A.7.1 ログイン

仕様の本文。

### 2.A.8 モジュール内ダイアグラム

#### 2.A.8.5 モジュール内シーケンス図

```mermaid
sequenceDiagram
    A->>B: x
```
"""


class _DocBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.repo = self.root / "repo"
        shutil.copytree(DOC_FIXTURE / "repo", self.repo)
        self.out = self.root / "out"
        self.work = self.out / "work"
        self.work.mkdir(parents=True)
        # 工程4a の初回の調査（ripple/initial/）を採用した状態
        self.run_dir = self.out / "ripple" / "initial"
        self.run_work = self.run_dir / "work"
        self.run_work.mkdir(parents=True)
        self.log_path = self.run_dir / "discovery-log.md"
        shutil.copy(DOC_FIXTURE / "discovery-log.md", self.log_path)
        shutil.copytree(DOC_FIXTURE / "waves", self.run_work / "waves")
        shutil.copy(DOC_FIXTURE / "documented-files.md", self.work / "documented-files.md")
        shutil.copy(DOC_FIXTURE / "module-assignments.json", self.work / "module-assignments.json")
        self.state_path = self.run_work / "bfs-state.json"
        self.runs_json = self.out / "ripple" / "runs.json"
        self.runs_json.write_text(json.dumps({"cr": "CR-2026-970", "repo": "svc", "runs": [
            {"run": "initial", "origin": "specout", "created": "2026-10-04T10:00:00", "approach": None, "reason": None,
             "seeds": [], "entry_identity": "resolved", "adopted": True, "adopted_by": "specout",
             "adopted_on": "2026-10-04"}]}), encoding="utf-8")
        text = (DOC_FIXTURE / "state.json").read_text(encoding="utf-8")
        self.state_path.write_text(text.replace("__REPO__", str(self.repo)).replace("__LOG__", str(self.log_path)),
                                   encoding="utf-8")
        self.ledger = self.work / "documented-files.md"
        self.assign = self.work / "module-assignments.json"
        self.gap = self.work / "prelim-gap-reviewed.md"
        self.summary_md = self.out / "ripple-summary.md"
        self.summary_json = self.work / "ripple-summary.json"
        self.crs = self.root / "CRS-CR-2026-970.md"
        self.crs.write_text("# CRS\n\nSP-001: ログイン判定を変える\n", encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, argv):
        args = mod.build_parser().parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _run_exit(self, argv):
        """(終了コード, stdout の JSON または None, stderr)。"""
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                args = mod.build_parser().parse_args(argv)
                args.func(args)
            except SystemExit as e:
                code = e.code
        text = out.getvalue().strip()
        return code, (json.loads(text) if text else None), err.getvalue()

    def _state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _set_state(self, **kw):
        data = self._state()
        data.update(kw)
        mod._write_state(self.state_path, data)

    def _auto_assign(self):
        return self._run(["doc-targets", "--path", str(self.state_path), "--ledger", str(self.ledger),
                          "--module-assignments", str(self.assign), "--auto-assign"])

    def _ripple_argv(self, max_files=20, extra=()):
        return ["ripple-summary", "--path", str(self.state_path), "--discovery-log", str(self.log_path),
                "--ledger", str(self.ledger), "--module-assignments", str(self.assign), "--gap-reviewed", str(self.gap),
                "--max-files", str(max_files), "--out", str(self.summary_md), "--json", str(self.summary_json), *extra]

    def _merged_ripple_argv(self, max_files=20, extra=()):
        return ["ripple-summary", "--repo-dir", str(self.out), "--repo-path", str(self.repo),
                "--ledger", str(self.ledger), "--module-assignments", str(self.assign), "--gap-reviewed", str(self.gap),
                "--max-files", str(max_files), "--out", str(self.summary_md), "--json", str(self.summary_json), *extra]

    def _make_summary(self, merged=False, **kw):
        self._auto_assign()
        return self._run(self._merged_ripple_argv(**kw) if merged else self._ripple_argv(**kw))

    def _common_argv(self, max_files, level="standard"):
        return ["--repo-dir", str(self.out), "--repo-path", str(self.repo), "--repo", "svc",
                "--output-dir", str(self.out), "--summary-template", str(SUMMARY_TPL),
                "--module-template", str(MODULE_TPL), "--max-files-per-module", str(max_files),
                "--detail-level", level, "--cr", "CR-2026-970", "--today", "2026-10-04"]

    def _layout_argv(self, max_files=10, cap=20):
        return ["assemble-spo", *self._common_argv(max_files),
                "--layout-only", "--only", "seed-direct", "--max-files", str(cap)]

    def _assemble_argv(self, max_files=10, level="standard", entry_points="", extra=()):
        return ["assemble-spo", *self._common_argv(max_files, level),
                "--crs-file", str(self.crs), "--entry-points", entry_points, *extra]

    def _add_run(self, name, seeds=(), origin="human", state_updates=None, approach=None):
        """初回の調査の写しを、別の調査（未採用）として加える。state_updates で state を書き換える。"""
        rdir = self.out / "ripple" / name
        shutil.copytree(self.run_dir, rdir)
        state = rdir / "work" / "bfs-state.json"
        data = json.loads(state.read_text(encoding="utf-8"))
        data["discovery_log"] = str(rdir / "discovery-log.md")
        data.update(state_updates or {})
        state.write_text(json.dumps(data), encoding="utf-8")
        reg = json.loads(self.runs_json.read_text(encoding="utf-8"))
        reg["runs"].append({"run": name, "origin": origin, "created": "2026-10-05T10:00:00", "approach": approach,
                            "reason": None, "seeds": list(seeds), "entry_identity": "resolved", "adopted": False,
                            "adopted_by": None, "adopted_on": None})
        self.runs_json.write_text(json.dumps(reg), encoding="utf-8")
        return rdir

    def _assemble_without_adopted(self, extra=()):
        self._unadopt_all()
        self._run(self._merged_ripple_argv())
        return self._run(self._assemble_argv(extra=extra))

    def _unadopt_all(self):
        reg = json.loads(self.runs_json.read_text(encoding="utf-8"))
        for r in reg["runs"]:
            r.update({"adopted": False, "adopted_by": None, "adopted_on": None})
        self.runs_json.write_text(json.dumps(reg), encoding="utf-8")

    def _sweep_argv(self):
        return ["verify-sweep", "--path", str(self.state_path), "--discovery-log", str(self.log_path)]

    def _write_ledger(self, rows):
        """rows: (ファイルパス, モジュール, モジュールディレクトリ, 工程) のタプル列。"""
        lines = ["# 文書化済みファイル台帳 — CR-2026-970 / svc", "",
                 "| ファイルパス | モジュール | モジュールディレクトリ | 工程 | 関係する振る舞い（CRS） |", "|---|---|---|---|---|"]
        lines += [f"| {f} | {m} | {d} | {ph} | 振る舞い {f} |" for f, m, d, ph in rows]
        self.ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_reviewed(self, rows):
        lines = ["# 追加下調べの判断の記録", "", "| ファイルパス | 判断 | 理由 |", "|---|---|---|"]
        lines += [f"| {f} | 関係なし | {r} |" for f, r in rows]
        self.gap.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _spo(self):
        return (self.out / "SPO-CR-2026-970.md").read_text(encoding="utf-8")

    def _write_prelim_spo(self, modules=()):
        """下調べが書いた形の SPO（版 0.1・冒頭の表示・統合パスの §2.A…）。modules: [(名前, 本文)]。"""
        text = SUMMARY_TPL.read_text(encoding="utf-8").replace("{CR番号}", "CR-2026-970").replace("{YYYY-MM-DD}", "2026-10-03")
        text = text.replace("**作成者：** AI（xddp-specout-document-agent）", "**作成者：** AI（xddp-specout-prelim-agent）")
        text = text.replace("**版数：** 1.0", "**版数：** 0.1\n\n> ⚠️ 波紋調査前の資料です。§4〜§7・§9〜§10 は未記入です。")
        text = text.replace("| 1.0 | 2026-10-03 | AI（xddp-specout-document-agent） | 初版作成 |",
                            "| 0.1 | 2026-10-03 | AI（xddp-specout-prelim-agent） | 下調べ（波紋調査前） |")
        blocks = "".join(f"## 2.{mod._letter_name(k)}. {name}\n\n{body}\n\n---\n\n" for k, (name, body) in enumerate(modules))
        text = text.replace("## 3. モジュール間シーケンス図", blocks + "## 3. モジュール間シーケンス図", 1)
        (self.out / "SPO-CR-2026-970.md").write_text(text, encoding="utf-8")

    def _write_module_doc(self, name, mdir, version="0.1"):
        text = MODULE_TPL.read_text(encoding="utf-8").replace("{CR番号}", "CR-2026-970").replace("{モジュール名}", name)
        text = text.replace("{モジュールパス}", mdir).replace("{YYYY-MM-DD}", "2026-10-03")
        text = text.replace("**作成者：** AI（xddp-specout-document-agent）", "**作成者：** AI（xddp-specout-prelim-agent）")
        text = text.replace("**版数：** 1.0", f"**版数：** {version}")
        text = re.sub(r"\| 1\.0 \| 2026-10-03 \| AI（xddp-specout-document-agent） \| 初版作成 \|",
                      "| 0.1 | 2026-10-03 | AI（xddp-specout-prelim-agent） | 下調べ（波紋調査前） |", text)
        (self.out / "modules").mkdir(exist_ok=True)
        (self.out / "modules" / f"{name}-spo.md").write_text(text, encoding="utf-8")


class DocAutoAssignTest(_DocBase):
    def test_assigns_parent_directories_and_is_idempotent(self):
        result = self._auto_assign()
        self.assertEqual(result["unassigned"], [])
        self.assertEqual(result["auto_assigned"], [{"module": "root", "module_dir": "."},
                                                    {"module": "src-util", "module_dir": "src/util"}])
        saved = json.loads(self.assign.read_text(encoding="utf-8"))
        self.assertEqual(saved, [{"module": "net", "module_dir": "src/net"},
                                 {"module": "root", "module_dir": "."},
                                 {"module": "src-util", "module_dir": "src/util"}])
        again = self._auto_assign()
        self.assertEqual(again["auto_assigned"], [])
        self.assertEqual(json.loads(self.assign.read_text(encoding="utf-8")), saved)
        self.assertEqual(self._run(["doc-targets", "--path", str(self.state_path), "--ledger", str(self.ledger),
                                    "--module-assignments", str(self.assign)])["unassigned"], [])

    def test_without_flag_files_stay_unassigned(self):
        result = self._run(["doc-targets", "--path", str(self.state_path), "--ledger", str(self.ledger),
                            "--module-assignments", str(self.assign)])
        self.assertEqual(sorted(result["unassigned"]), ["main.c", "src/util/helper.c"])
        self.assertEqual(result["auto_assigned"], [])

    def test_same_directory_files_share_one_module(self):
        self._write_file_in_repo("src/util/second.c", "int second(void) { return 0; }\n")
        data = self._state()
        data["confirmed_files"]["src/util/second.c"] = {"wave": 1, "confidence": "MEDIUM"}
        mod._write_state(self.state_path, data)
        result = self._auto_assign()
        names = [a["module"] for a in result["auto_assigned"]]
        self.assertEqual(names.count("src-util"), 1)
        targets = {t["file"]: t["module"] for t in result["doc_targets"]}
        self.assertEqual((targets["src/util/helper.c"], targets["src/util/second.c"]), ("src-util", "src-util"))

    def test_existing_module_directory_is_reused(self):
        # 台帳・module-assignments の組と同じディレクトリは、新しいモジュールを作らず既存のモジュールに割り当てる
        self.assign.write_text(json.dumps([{"module": "net", "module_dir": "src/net"},
                                           {"module": "util", "module_dir": "src/util"}]), encoding="utf-8")
        result = self._auto_assign()
        self.assertEqual([a["module"] for a in result["auto_assigned"]], ["root"])
        self.assertEqual({t["file"]: t["module"] for t in result["doc_targets"]}["src/util/helper.c"], "util")

    def test_name_collision_between_different_directories_fails_loud(self):
        self._write_file_in_repo("a/b-c/x.c", "int x(void) { return 0; }\n")
        self._write_file_in_repo("a-b/c/y.c", "int y(void) { return 0; }\n")
        data = self._state()
        data["confirmed_files"]["a/b-c/x.c"] = {"wave": 1, "confidence": "HIGH"}
        data["confirmed_files"]["a-b/c/y.c"] = {"wave": 1, "confidence": "HIGH"}
        mod._write_state(self.state_path, data)
        before = self.assign.read_text(encoding="utf-8")
        code, _out, err = self._run_exit(["doc-targets", "--path", str(self.state_path), "--ledger", str(self.ledger),
                                          "--module-assignments", str(self.assign), "--auto-assign"])
        self.assertEqual(code, 1)
        self.assertIn("a-b-c", err)
        self.assertIn("a/b-c", err)
        self.assertIn("a-b/c", err)
        self.assertEqual(self.assign.read_text(encoding="utf-8"), before)

    def test_collision_with_ledger_module_name_fails_loud(self):
        self.ledger.write_text(self.ledger.read_text(encoding="utf-8")
                               + "| lib/old.c | src-util | lib | 下調べ | x |\n", encoding="utf-8")
        code, _out, err = self._run_exit(["doc-targets", "--path", str(self.state_path), "--ledger", str(self.ledger),
                                          "--module-assignments", str(self.assign), "--auto-assign"])
        self.assertEqual(code, 1)
        self.assertIn("src-util", err)

    def _write_file_in_repo(self, rel, content):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


class RippleSummaryTest(_DocBase):
    def _json(self):
        return json.loads(self.summary_json.read_text(encoding="utf-8"))

    def test_module_table_full_output_and_json(self):
        result = self._make_summary()
        self.assertEqual((result["module_count"], result["summary_rows"], result["confirmed_file_count"]), (4, 4, 7))
        self.assertEqual(result["direct_modules"], ["auth"])
        self.assertEqual(result["prelim_gap_files"], [])
        self.assertFalse((self.work / "digest").exists())
        md = self.summary_md.read_text(encoding="utf-8")
        self.assertIn("LLM には渡さない", md)
        self.assertIn("> モジュール間の伝播は `ripple-graph.md`、関数単位の経路は `ripple-tree.md`", md)
        self.assertIn("| auth | 2 | 2 | 0 | — | あり | seed(session_start) → 第0波 |", md)
        self.assertIn("| net | 3 | 3 | 1 | — | なし | seed(session_start) → login_check → 第1波 |", md)
        # 並び: 最も浅い到達波 → 確定ファイル数の多い順 → 名前
        self.assertLess(md.index("| auth |"), md.index("| net |"))
        self.assertLess(md.index("| net |"), md.index("| root |"))
        self.assertLess(md.index("| root |"), md.index("| src-util |"))
        self.assertIn("## 2. 調査の打ち切り\n\nなし", md)
        self.assertIn("## 3. 下調べに無いシードの直接参照\n\nなし", md)
        self.assertIn("function-pointer-call", md[md.index("## 4. grep 未対応パターン"):])
        self.assertIn("### net（src/net）", md)
        self.assertIn("| src/net/sub/x.c | x_fn | 2 | name-only（名前の一致のみ） | — | — | "
                      "seed(session_start) → login_check → conn_open → 第2波 |", md)
        # スペックアウトはプロダクションコードだけを扱う（テストファイルは探さない）
        self.assertNotIn("tests/test_login.c", md)
        self.assertIn("| src/auth/login.c | login_check | 0 | name-only（名前の一致のみ） | — | あり |", md)
        # 偽陽性のヒットは関数に数えない
        self.assertNotIn("comment", md)
        data = self._json()
        self.assertEqual((data["seeds"], data["direct_modules"], data["seed_direct_file_count"]),
                         (["session_start"], ["auth"], 0))
        mods = {m["name"]: m for m in data["modules"]}
        self.assertEqual((mods["auth"]["documented"], mods["net"]["documented"]), (True, False))
        self.assertTrue(all(m["in_summary"] for m in data["modules"]))
        files = {fe["file"]: fe for m in data["modules"] for fe in m["files"]}
        self.assertNotIn("tests", files["src/auth/login.c"])
        self.assertEqual(files["src/net/conn.c"]["functions"], ["conn_open"])
        for key in ("line_budget", "max_modules", "truncated_functions"):
            self.assertNotIn(key, data)

    def test_order_prefers_resolved_and_caps_summary_rows(self):
        confirmed = self._state()["confirmed_files"]
        confirmed["main.c"]["identity"] = "resolved"
        self._set_state(confirmed_files=confirmed)
        with patch.object(mod, "SUMMARY_MAX_ROWS", 2):
            result = self._make_summary()
        self.assertEqual(result["summary_rows"], 2)
        # 同じ到達波では（確定ファイル数 − 名前の一致のみ）の多い root が net より先
        in_summary = {m["name"]: m["in_summary"] for m in self._json()["modules"]}
        self.assertEqual(in_summary, {"auth": True, "root": True, "net": False, "src-util": False})
        md = self.summary_md.read_text(encoding="utf-8")
        self.assertLess(md.index("| root | 1 | 0 | 1 |"), md.index("| net | 3 | 3 | 1 |"))

    def test_seed_direct_counts_and_gap_reasons(self):
        self._set_state(seed_direct_files=["src/auth/login.c", "src/auth/session.c", "src/net/conn.c"])
        result = self._make_summary()
        self.assertEqual(result["prelim_gap_files"], [
            {"file": "src/auth/session.c", "reason": "not-written", "module": "auth"},
            {"file": "src/net/conn.c", "reason": "not-written", "module": "net"}])
        md = self.summary_md.read_text(encoding="utf-8")
        self.assertIn("| auth | 2 | 2 | 0 | 2（⚠️1） | あり |", md)
        self.assertIn("| net | 3 | 3 | 1 | 1（⚠️1） | なし |", md)
        # 累計の上限で外したものは over-limit（doc-targets --only seed-direct の over_limit_files と一致する）
        r1 = self._run(self._ripple_argv(max_files=1))
        self.assertEqual([(g["file"], g["reason"]) for g in r1["prelim_gap_files"]],
                         [("src/auth/session.c", "not-written"), ("src/net/conn.c", "over-limit")])
        targets = self._run(["doc-targets", "--path", str(self.state_path), "--ledger", str(self.ledger),
                             "--module-assignments", str(self.assign), "--gap-reviewed", str(self.gap),
                             "--only", "seed-direct", "--max-files", "1"])
        self.assertEqual(targets["over_limit_files"], ["src/net/conn.c"])
        self.assertIn("上限超過", self.summary_md.read_text(encoding="utf-8"))

    def test_reviewed_files_leave_gap_and_are_listed(self):
        self._set_state(seed_direct_files=["src/auth/session.c", "src/net/conn.c"])
        self._write_reviewed([("src/net/conn.c", "名前が同じだけの別物")])
        result = self._make_summary()
        self.assertEqual([g["file"] for g in result["prelim_gap_files"]], ["src/auth/session.c"])
        self.assertEqual(self._json()["gap_reviewed_files"], [{"file": "src/net/conn.c", "reason": "名前が同じだけの別物"}])
        self.assertIn("| src/net/conn.c | 名前が同じだけの別物 |", self.summary_md.read_text(encoding="utf-8"))
        self.assertIn("| net | 3 | 3 | 1 | 1 | なし |", self.summary_md.read_text(encoding="utf-8"))

    def test_test_patterns_option_is_removed(self):
        self._auto_assign()
        code, _o, _err = self._run_exit(self._ripple_argv(extra=["--test-patterns", "test_{stem}.*"]))
        self.assertEqual(code, 2)

    def test_unassigned_files_fail_loud(self):
        code, _o, err = self._run_exit(self._ripple_argv())
        self.assertEqual(code, 1)
        self.assertIn("--auto-assign", err)

    def test_rerun_is_idempotent(self):
        self._make_summary()
        first = (self.summary_md.read_text(encoding="utf-8"), self.summary_json.read_text(encoding="utf-8"))
        state = self.state_path.read_text(encoding="utf-8")
        self._run(self._ripple_argv())
        self.assertEqual((self.summary_md.read_text(encoding="utf-8"), self.summary_json.read_text(encoding="utf-8")),
                         first)
        self.assertEqual(self.state_path.read_text(encoding="utf-8"), state)


SKILL_MD = Path(__file__).resolve().parents[2] / "SKILL.md"
SKILLS_DIR = Path(__file__).resolve().parents[3]
PROCEDURES_DIR = SKILLS_DIR / "xddp-common" / "procedures"
RUN_OUTPUTS_MD = PROCEDURES_DIR / "ripple-run-outputs.md"
TRACE_HEADER = ("| 行ID | コマンドID | 検索シンボル | ファイル | 行 | マッチ内容 | 含む関数/クラス | 伝播種別 | 確信度 | 同一性 | "
                "Wave {n} 追加シンボル | 派生元 |")


class RippleTraceTest(_DocBase):
    """ripple-trace（伝播グラフ ripple-graph.md・関数単位の階層表 ripple-tree.md）。
    合成の discovery-log と ripple-summary.json を入力にする（モジュールはディレクトリの先頭）。"""

    def setUp(self):
        super().setUp()
        self.graph = self.out / "ripple-graph.md"
        self.tree = self.out / "ripple-tree.md"
        self._set_state(slice_engine="slice")

    # -- 入力の組み立て --
    def _write_log(self, waves):
        """waves: {波: [(行ID, エントリ, ファイル, 行, 関数, 伝播種別, 同一性, 派生元)]}。"""
        out = ["# Discovery Log — CR-2026-970 / svc", ""]
        for w in sorted(waves):
            out += [f"## Wave {w}", "", TRACE_HEADER.format(n=w + 1), "|" + "---|" * 12]
            for lid, entry, f, line, func, label, ident, origin in waves[w]:
                out.append(mod._md_row([lid, f"W{w}-C1", f"`{entry}`", f, line, "`x`", f"`{func}`" if func else "-",
                                        label, "HIGH", ident, "—", origin]))
            out.append("")
        self.log_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    def _write_summary(self, files, documented=(), modules_of=None):
        """files: {ファイル: (state の確定の波, 同一性)}。モジュールは先頭のディレクトリ（modules_of で上書き）。"""
        mods = {}
        for f, (wave, ident) in files.items():
            name = (modules_of or {}).get(f) or f.split("/")[0]
            mods.setdefault(name, []).append({"file": f, "wave": wave, "identity": ident})
        modules = [{"name": n, "dir": n, "files": fs, "confirmed_count": len(fs),
                    "name_only_count": sum(1 for fe in fs if fe["identity"] != "resolved"),
                    "min_wave": min(fe["wave"] for fe in fs), "documented": n in documented}
                   for n, fs in sorted(mods.items())]
        self.summary_json.write_text(json.dumps({"cr": "CR-2026-970", "repo": "svc", "modules": modules},
                                                ensure_ascii=False), encoding="utf-8")

    def _argv(self):
        return ["ripple-trace", "--path", str(self.state_path), "--discovery-log", str(self.log_path),
                "--summary-json", str(self.summary_json), "--graph-out", str(self.graph), "--tree-out", str(self.tree)]

    def _trace(self):
        return self._run(self._argv())

    def _texts(self):
        return self.graph.read_text(encoding="utf-8"), self.tree.read_text(encoding="utf-8")

    GUIDE_CHARS = "├└│\u3000 "

    @classmethod
    def _tree_rows(cls, tree, keep_guides=False):
        """{(節, 階層の番号): セル}。節は `### 起点`。「関数」列の罫線は keep_guides でなければ取り除く。"""
        rows, section = {}, None
        for line in tree.split("\n"):
            if line.startswith("### "):
                section = line[4:]
            elif line.startswith("| ") and section and not line.startswith("| 階層") and not mod._is_sep_row(line):
                cells = mod._split_row(line)
                if keep_guides:
                    # _split_row の strip() は全角空白も取り除くため、罫線の字下げは半角空白だけを外して読む
                    raw = re.split(r"(?<!\\)\|", line)[1:-1]
                    cells[1] = raw[1].strip(" ").replace(r"\|", "|")
                else:
                    cells[1] = cells[1].lstrip(cls.GUIDE_CHARS)
                rows[(section, cells[0])] = cells
        return rows

    def _scenario(self):
        """直線・合流・偽陽性・スコープ外・同じ関数の複数の行・関数単位の循環・ログに無い派生元。"""
        self._write_log({
            0: [("W0-R1", "seed_fn", "a/a.c", 10, "seed_fn", "slice(none=self-def)", "resolved", "seed(seed_fn)"),
                ("W0-R2", "seed_fn", "a/a.c", 20, "caller", "slice(escape=return)", "resolved", "seed(seed_fn)"),
                ("W0-R3", "g_var", "a/a.c", 30, "caller", "slice(escape=return)", "resolved", "seed-global(g_var)"),
                ("W0-R4", "other_sym", "a/a.c", 20, "caller", "slice(escape=return)", "resolved", "seed(other_sym)"),
                ("W0-R5", "g_var", "h/h.c", 4, "h_fn", "slice(escape=return)", "resolved", "seed-global(g_var)")],
            1: [("W1-R1", "caller", "b/b.c", 5, "b_fn", "slice(escape=return)", "resolved", "W0-R2"),
                ("W1-R2", "caller", "c/c.c", 7, "c_fn", "slice(escape=return)", "name-only", "W0-R2"),
                ("W1-R3", "caller", "b/b.c", 9, "", "false-positive", "—", "W0-R2"),
                ("W1-R4", "caller", "d/d.c", 3, "d_fn", "out-of-scope-discard", "name-only", "W0-R2")],
            2: [("W2-R1", "b_fn", "e/e.c", 1, "merge_fn", "slice(escape=return)", "resolved", "W1-R1, W1-R2"),
                ("W2-R2", "c_fn", "e/e.c", 2, "merge_fn", "slice(escape=return)", "resolved", "W1-R2"),
                ("W2-R3", "ghost", "f/f.c", 1, "ghost_fn", "slice(escape=return)", "name-only", "W9-R9"),
                ("W2-R4", "b_fn", "f/f.c", 8, "", "slice(file-scope=global-init)", "name-only", "W1-R3")],
            3: [("W3-R1", "merge_fn", "b/b.c", 6, "b_fn", "slice(escape=return)", "resolved", "W2-R1")],
        })
        self._write_summary({"a/a.c": (0, "resolved"), "b/b.c": (1, "resolved"), "c/c.c": (1, "name-only"),
                             "d/d.c": (1, "name-only"), "e/e.c": (2, "resolved"), "f/f.c": (2, "name-only"),
                             "h/h.c": (0, "resolved"), "z/z.c": (2, "name-only")}, documented=("a",))

    # -- 階層表 --
    def test_tree_structure_merge_and_origins(self):
        self._scenario()
        result = self._trace()
        self.assertEqual((result["tree_node_count"], result["rowless_file_count"], result["unresolved_origin_count"],
                          result["cycle_guard_count"], result["identity_available"]), (9, 1, 2, 0, True))
        _graph, tree = self._texts()
        rows = self._tree_rows(tree)
        # 起点の節の並び: seed → seed-global → unknown-origin
        self.assertLess(tree.index("### seed(seed_fn)"), tree.index("### seed-global(g_var)"))
        self.assertLess(tree.index("### seed-global(g_var)"), tree.index("### unknown-origin"))
        self.assertNotIn("### seed(other_sym)", tree)   # 親にならない起点は節を作らない
        s = "seed(seed_fn)"
        # 直線: caller → b_fn → merge_fn（代表行の値）
        self.assertEqual(rows[(s, "1")], ["1", "`caller`", "`a/a.c:20`（ほか 1 行）", "a", "`seed_fn`",
                                          "slice(escape=return)", "resolved", "0", "W0-R2",
                                          "2（`seed(other_sym)`、`seed-global(g_var)`）"])
        self.assertEqual(rows[(s, "1.1")][:9], ["1.1", "`b_fn`", "`b/b.c:5`（ほか 1 行）", "b", "`caller`",
                                                "slice(escape=return)", "resolved", "1", "W1-R1"])
        self.assertEqual(rows[(s, "1.1.1")][:9], ["1.1.1", "`merge_fn`", "`e/e.c:1`（ほか 1 行）", "e", "`b_fn`",
                                                  "slice(escape=return)", "resolved", "2", "W2-R1"])
        # 行番号が1種類だけのノードには「ほか」が付かない
        self.assertEqual(rows[(s, "2")][1:3], ["`seed_fn`", "`a/a.c:10`"])
        # 子の並び: 波 → resolved を先 → ファイル（b_fn〔resolved〕→ c_fn → d_fn）
        self.assertEqual([rows[(s, k)][1] for k in ("1.1", "1.2", "1.3")], ["`b_fn`", "`c_fn`", "`d_fn`"])
        # 合流: merge_fn は1回だけ。他の派生元にもう一方の親（c_fn）。関数単位の循環（b_fn → merge_fn → b_fn）は他の派生元に出る
        self.assertEqual(sum(1 for c in rows.values() if c[1] == "`merge_fn`"), 1)
        self.assertEqual(rows[(s, "1.1.1")][9], "1（1.2）")
        self.assertEqual(rows[(s, "1.1")][9], "1（1.1.1）")
        # 偽陽性の行はノードにならない（b/b.c の関数の外のノードが無い）／スコープ外の行はノードになり子を持たない
        self.assertFalse(any(c[2].startswith("`b/b.c:9`") for c in rows.values()))
        self.assertEqual(rows[(s, "1.3")][5], "out-of-scope-discard")
        self.assertNotIn((s, "1.3.1"), rows)
        # seed-global の節・ログに無い行ID（W9-R9）と偽陽性の行（W1-R3）を指す派生元は unknown-origin
        self.assertEqual(rows[("seed-global(g_var)", "1")][1], "`h_fn`")
        self.assertEqual({rows[("unknown-origin", k)][1] for k in ("1", "2")}, {"`ghost_fn`", mod.NO_FUNCTION_LABEL})
        # 経路の行が無い確定ファイル
        self.assertIn("## 2. 経路の行が無い確定ファイル\n\n| ファイル | モジュール | 発見波 | 同一性 |\n|---|---|---|---|\n"
                      "| `z/z.c` | z | 2 | name-only |", tree)

    def test_function_column_tree_guides(self):
        self._scenario()
        self._trace()
        tree = self._texts()[1]
        rows = self._tree_rows(tree, keep_guides=True)
        s = "seed(seed_fn)"
        pipe, blank = "│ ", "\u3000"
        # 節の直下には罫線が無い。兄弟の最後は └─、それ以外は ├─。最後でない祖先の下は │、最後の祖先の下は空白
        self.assertEqual(rows[(s, "1")][1], "`caller`")
        self.assertEqual(rows[(s, "1.1")][1], "├ `b_fn`")
        self.assertEqual(rows[(s, "1.1.1")][1], pipe + "└ `merge_fn`")
        self.assertEqual(rows[(s, "1.2")][1], "├ `c_fn`")
        self.assertEqual(rows[(s, "1.3")][1], "└ `d_fn`")
        self.assertEqual(rows[(s, "2")][1], "`seed_fn`")
        self.assertEqual(rows[("unknown-origin", "1")][1], mod.NO_FUNCTION_LABEL)
        self.assertIn("「関数」列の罫線（├ └ │）は親子と兄弟を表す", tree)
        # 最後の子の下の孫は空白で字下げする
        self._write_log({
            0: [("W0-R1", "s", "a/a.c", 1, "f", "slice(escape=return)", "resolved", "seed(s)")],
            1: [("W1-R1", "f", "a/a.c", 2, "g", "slice(escape=return)", "resolved", "W0-R1")],
            2: [("W2-R1", "g", "a/a.c", 3, "h", "slice(escape=return)", "resolved", "W1-R1")],
            3: [("W3-R1", "h", "a/a.c", 4, "k", "slice(escape=return)", "resolved", "W2-R1")],
        })
        self._write_summary({"a/a.c": (0, "resolved")})
        self._trace()
        rows = self._tree_rows(self._texts()[1], keep_guides=True)
        self.assertEqual([rows[("seed(s)", k)][1] for k in ("1", "1.1", "1.1.1", "1.1.1.1")],
                         ["`f`", "└ `g`", blank + "└ `h`", blank + blank + "└ `k`"])

    def test_other_origins_in_other_sections_and_overflow(self):
        self._write_log({
            0: [("W0-R1", "s1", "a/a.c", 1, "f1", "slice(escape=return)", "resolved", "seed(s1)"),
                ("W0-R2", "s2", "a/a.c", 2, "f2", "slice(escape=return)", "resolved", "seed(s2)"),
                ("W0-R3", "s3", "a/a.c", 3, "f3", "slice(escape=return)", "resolved", "seed(s3)")],
            1: [("W1-R1", "f1", "b/b.c", 1, "g", "slice(escape=return)", "resolved", "W0-R1, W0-R2, W0-R3"),
                ("W1-R2", "f1", "b/b.c", 1, "g", "slice(escape=return)", "resolved", "seed(s9), unknown-origin")],
        })
        self._write_summary({"a/a.c": (0, "resolved"), "b/b.c": (1, "resolved")})
        self._trace()
        rows = self._tree_rows(self._texts()[1])
        self.assertEqual(rows[("seed(s1)", "1.1")][9],
                         "4（`seed(s9)`、`unknown-origin`、`seed(s2)`: 1…ほか 1）")

    def test_tree_identity_uses_row_pair_and_orders_children(self):
        # 親 P の行 p1（name-only）と p2（resolved）。子 C の代表行 c1 は p1 から、c2 は p2 から（ともに resolved）。
        # 階層表の C の同一性は name-only（行の組 p1 → c1）、グラフの関数の組 P → C は resolved。
        self._write_log({
            0: [("W0-R1", "s", "p/p.c", 1, "P", "slice(escape=return)", "name-only", "seed(s)"),
                ("W0-R2", "t", "p/p.c", 2, "P", "slice(escape=return)", "resolved", "seed(t)")],
            1: [("W1-R1", "P", "q/a.c", 1, "C", "slice(escape=return)", "resolved", "W0-R1"),
                ("W1-R2", "P", "q/a.c", 1, "C", "slice(escape=return)", "resolved", "W0-R2"),
                ("W1-R3", "P", "q/z.c", 1, "D", "slice(escape=return)", "resolved", "W0-R2")],
        })
        self._write_summary({"p/p.c": (0, "resolved"), "q/a.c": (1, "resolved"), "q/z.c": (1, "resolved")})
        self._trace()
        graph, tree = self._texts()
        rows = self._tree_rows(tree)
        self.assertEqual((rows[("seed(s)", "1.1")][1], rows[("seed(s)", "1.1")][6]), ("`D`", "resolved"))
        self.assertEqual((rows[("seed(s)", "1.2")][1], rows[("seed(s)", "1.2")][6]), ("`C`", "name-only"))
        self.assertIn("| p | q | 2 | 2 | 0 |", graph)

    # -- グラフ --
    def test_graph_module_edges_identity_and_labels(self):
        self._scenario()
        result = self._trace()
        graph, _tree = self._texts()
        # 起点の ID: seed(…) 名前の順 → seed-global → unknown-origin。モジュールの ID: 波 → 名前
        self.assertIn('    S1(["seed(other_sym)"])', graph)
        self.assertIn('    S2(["seed(seed_fn)"])', graph)
        self.assertIn('    S3(["seed-global(g_var)"])', graph)
        self.assertIn('    S4(["unknown-origin"])', graph)
        self.assertIn('    M1["a<br/>ファイル 1（名前の一致のみ 0）<br/>第0波〜 ・資料あり"]:::doc', graph)
        self.assertIn('    M2["h<br/>ファイル 1（名前の一致のみ 0）<br/>第0波〜 ・資料なし"]:::nodoc', graph)
        self.assertIn("    class M1,M2 wave0", graph)
        # 辺の同一性: b_fn（resolved）と c_fn（name-only）が同じシンボルを送り、受け手 merge_fn の行は resolved
        self.assertIn('M3 -->|"resolved 1・name-only 0"| M6', graph)    # b → e（実線）
        self.assertIn('M4 -.->|"resolved 0・name-only 1"| M6', graph)   # c → e（点線）
        self.assertIn("| c | e | 1 | 0 | 1 |", graph)
        self.assertEqual(self._tree_rows(self._texts()[1])[("seed(seed_fn)", "1.2")][6], "name-only")
        # 起点の辺もラベルは同じ書式
        self.assertIn('S2 -->|"resolved 2・name-only 0"| M1', graph)
        # 関数単位の循環（b_fn → merge_fn → b_fn）はモジュールの組 e → b として数える
        self.assertIn("| e | b | 1 | 1 | 0 |", graph)
        self.assertEqual((result["module_count"], result["drawn_module_count"], result["omitted_module_count"],
                          result["omitted_edge_count"]), (8, 8, 0, 0))
        self.assertNotIn("⚠️", graph)
        # 経路の行が無いモジュール（z）は確定の波
        self.assertIn('["z<br/>ファイル 1（名前の一致のみ 1）<br/>第2波〜（確定の波） ・資料なし"]:::nodoc', graph)

    def test_graph_limits(self):
        self._scenario()
        with patch.object(mod, "RIPPLE_GRAPH_MAX_MODULES", 3), patch.object(mod, "RIPPLE_GRAPH_MAX_EDGES", 2):
            result = self._trace()
        graph, _tree = self._texts()
        self.assertIn("> ⚠️ モジュールが 8 個あるため、3 個だけを描いた", graph)
        # 描くモジュール: 第0波（a, h）→ 波 → 確定ファイル数 → 名前（b）
        mermaid = graph[graph.index("```mermaid"):graph.index("## 2.")]
        self.assertEqual(re.findall(r'^    (M\d+)\["(\w+)<br/>', mermaid, re.M), [("M1", "a"), ("M2", "h"), ("M3", "b")])
        # 描くモジュールの間の辺 5 本（S1→a, S2→a, S3→a, S3→h, a→b）のうち、起点の辺 → resolved の多い順 → 名前の順で 2 本
        self.assertIn("> ⚠️ 辺が 5 本あるため、上位 2 本だけを描いた（全量は §2）", graph)
        self.assertEqual(len(re.findall(r"^    \w+ -\.?->", mermaid, re.M)), 2)
        self.assertIn('S2 -->|"resolved 2・name-only 0"| M1', mermaid)
        self.assertIn('S1 -->|"resolved 1・name-only 0"| M1', mermaid)
        self.assertEqual((result["drawn_module_count"], result["omitted_module_count"], result["drawn_edge_count"],
                          result["module_edge_count"], result["omitted_edge_count"]), (3, 5, 2, 11, 9))
        # §2 は全組
        self.assertIn("| c | e | 1 | 0 | 1 |", graph)

    def test_module_wave_uses_rows_and_state_waves(self):
        self._write_log({
            0: [("W0-R1", "s", "a/a.c", 1, "fa", "slice(escape=return)", "resolved", "seed(s)")],
            1: [("W1-R1", "fa", "c/c.c", 1, "fc", "slice(escape=return)", "resolved", "W0-R1")],
            2: [("W2-R1", "fc", "m/x.c", 1, "fx", "slice(escape=return)", "resolved", "W1-R1"),
                ("W2-R2", "fc", "b/b.c", 1, "fb", "slice(escape=return)", "resolved", "W1-R1")],
            3: [("W3-R1", "fb", "k/k.c", 1, "fk", "slice(escape=return)", "resolved", "W2-R2")],
        })
        # c/c.c: 行は第1波、state は確信度の書き換えで第4波 → 第1波（確定の波は付かない）
        # m: 行のある m/x.c（第2波）と行の無い m/y.c（state 第0波）→ 第0波〜（確定の波）・wave0
        # k/k.c: 行は第3波、state は第1波（縮退で先に確定）→ 第1波〜（確定の波）
        # n: 行が1行も無い → state の波と（確定の波）
        self._write_summary({"a/a.c": (0, "resolved"), "b/b.c": (2, "resolved"), "c/c.c": (4, "resolved"),
                             "m/x.c": (2, "resolved"), "m/y.c": (0, "name-only"), "k/k.c": (1, "resolved"),
                             "n/n.c": (3, "name-only")})
        self._trace()
        graph = self._texts()[0]
        labels = dict(re.findall(r'^    (M\d+)\["(\w+)<br/>', graph, re.M))
        waves = {name: re.search(rf'"{name}<br/>[^"]*<br/>(第[^"]*?) ・', graph).group(1) for name in labels.values()}
        self.assertEqual(waves, {"a": "第0波〜", "m": "第0波〜（確定の波）", "c": "第1波〜", "k": "第1波〜（確定の波）",
                                 "b": "第2波〜", "n": "第3波〜（確定の波）"})
        self.assertEqual(labels, {"M1": "a", "M2": "m", "M3": "c", "M4": "k", "M5": "b", "M6": "n"})
        self.assertIn("    class M1,M2 wave0", graph)
        summary = json.loads(self.summary_json.read_text(encoding="utf-8"))
        for m in summary["modules"]:
            self.assertLessEqual(int(re.search(r"\d+", waves[m["name"]]).group()), m["min_wave"])

    def test_escaping_and_entry_display(self):
        self._write_log({
            0: [("W0-R1", "s", "a/a.c", 1, "op|or", "slice(escape=return)", "resolved", "seed(s)")],
            1: [("W1-R1", "x[FILE:a/a.c]", "a/a.c", 5, "fx", "slice(escape=return)", "resolved", "W0-R1"),
                ("W1-R2", "m[CLASS:K]", "b/b.cpp", 2, "K::g", "slice(escape=return)", "resolved", "W0-R1"),
                ("W1-R3", "p[MEDIUM:c/c.c]", "c/c.c", 3, "fp", "propagation-argument", "name-only", "W0-R1")],
        })
        self._write_summary({"a/a.c": (0, "resolved"), "b/b.cpp": (1, "resolved"), "c/c.c": (1, "name-only")},
                            modules_of={"a/a.c": 'a#<b>&"q"'})
        self._trace()
        graph, tree = self._texts()
        self.assertIn('M1["a#35;#lt;b#gt;#amp;#quot;q#quot;<br/>', graph)
        rows = self._tree_rows(tree)
        self.assertEqual(rows[("seed(s)", "1")][1], "`op|or`")
        self.assertIn(r"`op\|or`", tree)
        self.assertEqual({rows[("seed(s)", k)][4] for k in ("1.1", "1.2", "1.3")},
                         {"`x[FILE:a/a.c]`", "`m[CLASS:K]`", "`p`（引数・`c/c.c`）"})
        for text in (graph, tree):
            self.assertNotIn("MEDIUM", text)
            self.assertNotIn("（要確認）", text)
            self.assertNotIn("（推定）", text)

    def test_old_format_log_has_no_identity(self):
        # 「同一性」列の無いフィクスチャの discovery-log（state の slice_engine を消す）
        self._make_summary()
        data = self._state()
        data.pop("slice_engine")
        mod._write_state(self.state_path, data)
        result = self._trace()
        self.assertFalse(result["identity_available"])
        graph, tree = self._texts()
        note = "> ⚠️ resolved の行が1行も無い（判定エンジン: —）。原因の候補:"
        self.assertIn(note, graph)
        self.assertIn(note, tree)
        self.assertLess(graph.index(note), graph.index("```mermaid"))
        self.assertNotRegex(graph, r"\w -->\|")
        self.assertIn('-.->|"resolved 0・name-only 2"|', graph)
        self.assertNotIn("| resolved |", tree)

    def test_no_identity_note_absent_with_any_resolved_row(self):
        self._scenario()
        self._trace()
        for text in self._texts():
            self.assertNotIn("resolved の行が1行も無い", text)
        self._set_state(slice_engine="rule")
        self._write_log({0: [("W0-R1", "s", "a/a.c", 1, "f", "rule(enclosing)", "name-only", "seed(s)")]})
        self._write_summary({"a/a.c": (0, "name-only")})
        result = self._trace()
        self.assertFalse(result["identity_available"])
        self.assertIn("（判定エンジン: rule）", self._texts()[0])

    def test_fixture_end_to_end(self):
        self._make_summary()
        result = self._trace()
        self.assertEqual((result["tree_node_count"], result["rowless_file_count"], result["cycle_guard_count"]), (7, 0, 0))
        graph, tree = self._texts()
        rows = self._tree_rows(tree)
        self.assertEqual(rows[("seed(session_start)", "1.2.2")][1:3], ["`x_fn`", "`src/net/sub/x.c:2`"])
        # 同じモジュールの中の組は §2 の表にだけ出る（グラフに自分への辺を描かない）
        self.assertIn("| net | net | 2 | 0 | 2 |", graph)
        self.assertFalse(re.search(r"^    (M\d+) -\.?->\|[^|]*\| \1$", graph, re.M))

    # -- 失敗・冪等 --
    def test_mismatch_fails_and_removes_previous_outputs(self):
        self._scenario()
        self._trace()
        self._write_summary({"a/a.c": (0, "resolved")})
        code, _out, err = self._run_exit(self._argv())
        self.assertEqual(code, 1)
        self.assertFalse(self.graph.exists())
        self.assertFalse(self.tree.exists())
        self.assertIn("（6 件）", err)
        self.assertIn("b/b.c", err)
        self.assertIn("ripple-summary を再実行する", err)
        self.assertIn("import で初期化した state", err)

    def test_missing_summary_json_fails(self):
        self._scenario()
        self.summary_json.unlink()
        code, _out, err = self._run_exit(self._argv())
        self.assertEqual(code, 1)
        self.assertIn("ripple-summary", err)

    def test_rerun_is_byte_identical(self):
        self._scenario()
        self._trace()
        first = self._texts()
        self._trace()
        self.assertEqual(self._texts(), first)

    def test_skill_command_line_parses(self):
        text = RUN_OUTPUTS_MD.read_text(encoding="utf-8")
        lines = [ln for ln in text.split("\n") if '"$BFS" ripple-trace' in ln]
        self.assertEqual(len(lines), 1)
        cmd = re.search(r"`(\"\$PY\" \"\$BFS\" ripple-trace[^`]*)`", lines[0]).group(1)
        cmd = re.sub(r"\{[A-Z_]+\}", "/tmp/x", cmd)
        argv = cmd.split()[2:]
        args = mod.build_parser().parse_args(argv)
        self.assertIs(args.func, mod.cmd_ripple_trace)
        for flag in ("--path", "--discovery-log", "--summary-json", "--graph-out", "--tree-out"):
            self.assertIn(flag, argv)

    def test_all_bfs_command_lines_in_skills_parse(self):
        """SKILL・共通プロシージャの `"$PY" "$BFS" …` の1行コマンドが、今の argparse で解析できる。"""
        import shlex
        files = [SKILL_MD, *sorted(PROCEDURES_DIR.glob("ripple-*.md")), PROCEDURES_DIR / "specout-finish.md",
                 SKILLS_DIR / "xddp-investigate" / "SKILL.md", SKILLS_DIR / "xddp-05-arch" / "SKILL.md"]
        seen = 0
        for f in files:
            for m in re.finditer(r"`\"\$PY\" \"\$BFS\" ([^`]*)`", f.read_text(encoding="utf-8")):
                cmd = m.group(1)
                if "{TPL}" in cmd or "{DOC_IN}" in cmd:
                    cmd = cmd.replace("{TPL}", "--repo-dir x --repo-path x --repo r --output-dir x --summary-template x "
                                                "--module-template x --max-files-per-module 1 --cr C --today t")
                    cmd = cmd.replace("{DOC_IN}", "--crs-file x --entry-points ''")
                # 置き換え先は整数の引数にも通る値（choices の引数は下で有効な値にする）
                cmd = re.sub(r"\{[^{}]*\}", "1", re.sub(r"\{[^{}]*\}", "1", cmd))
                cmd = cmd.replace("[", "").replace("]", "").split(" > ")[0]
                argv = shlex.split(cmd)
                choices = {"--origin": "human", "--by": "human", "--entry-identity": "resolved", "--detail-level": "standard"}
                argv = [choices[argv[i - 1]] if i and argv[i - 1] in choices and a == "1" else a for i, a in enumerate(argv)]
                with redirect_stderr(io.StringIO()) as err:
                    try:
                        mod.build_parser().parse_args(argv)
                    except SystemExit:
                        self.fail(f"{f.name}: {m.group(0)}\n{err.getvalue()}")
                seen += 1
        self.assertGreater(seen, 20)


class VerifySweepTest(_DocBase):
    def _sweep(self):
        return self._run_exit(self._sweep_argv())

    def _drop_confirmed(self, *files):
        confirmed = self._state()["confirmed_files"]
        for f in files:
            confirmed.pop(f)
        self._set_state(confirmed_files=confirmed)

    def test_undocumented_confirmed_files_are_recorded(self):
        # 突き合わせ先は波紋調査の帳簿（確定ファイル）。資料にしたか（台帳）は問わない
        code, out, _e = self._sweep()
        self.assertEqual(code, 0)
        self.assertEqual((out["unrecorded_hits"], out["swept_symbols"]), (0, 4))
        log = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## 検証スイープ結果", log)
        self.assertIn("このスイープはファイル単位の漏れを検出します。伝播パスの正しさは保証しません。", log)
        self.assertIn("| シンボル | grep ヒット（プロダクションコード） | 帳簿の記録 | 状態 |", log)
        self.assertIn("→ **未記録ヒット: なし。検証完了。**", log)
        self.assertNotIn("tests/test_login.c", log)  # 除外パターンは search と同じ設定

    def test_unrecorded_hit_exits_seven_and_is_logged(self):
        self._drop_confirmed("src/net/other.c")
        code, out, _e = self._sweep()
        self.assertEqual(code, mod.EXIT_UNRECORDED_SWEEP)
        self.assertEqual(mod.EXIT_UNRECORDED_SWEEP, 7)
        self.assertEqual((out["unrecorded_hits"], out["unrecorded_files"]), (1, ["src/net/other.c"]))
        log = self.log_path.read_text(encoding="utf-8")
        self.assertIn("波紋調査の帳簿（確定ファイル・関係なしとしたファイル）に無いヒットです。SPO §9 に転記しました。", log)
        self.assertIn("/xddp-investigate", log)
        self.assertNotIn("Phase 2 を再実施", log)
        self.assertIn("- `src/net/other.c`", log)
        self.assertIn("| `conn_open` |", log)
        # 再実行は結果の節を置き換える（重複しない）
        self._sweep()
        self.assertEqual(self.log_path.read_text(encoding="utf-8").count("## 検証スイープ結果"), 1)

    def test_exit_code_differs_from_count_mismatch(self):
        import specout_verify_counts as verify_mod
        self.assertNotEqual(mod.EXIT_UNRECORDED_SWEEP, 3)
        self.assertNotIn(mod.EXIT_UNRECORDED_SWEEP, (1, 2, mod.EXIT_EMPTY_SEED, mod.EXIT_ASSIGNMENTS_INVALID,
                                                      mod.EXIT_SEED_SUMMARY_PENDING))
        self.assertTrue(hasattr(verify_mod, "main"))

    def test_false_positive_files_are_matched_after_normalization(self):
        self._drop_confirmed("src/net/other.c")
        self._set_state(false_positive_files={"./src/net/other.c": 2})
        code, out, _e = self._sweep()
        self.assertEqual((code, out["unrecorded_hits"]), (0, 0))
        log = self.log_path.read_text(encoding="utf-8")
        self.assertIn("判定で関係なし（false-positive のみ）として突き合わせ済みにしたファイル: 1 件", log)
        self.assertIn("ファイル単位で突き合わせ済みにします", log)

    def test_medium_symbol_is_limited_to_its_scope(self):
        # util_fn[MEDIUM:src/util/helper.c] は helper.c のみ検索する（main.c の util_fn は対象外）
        self._drop_confirmed("main.c")
        code, out, _e = self._sweep()
        # main.c は login_check（HIGH）でヒットするため未記録。MEDIUM だけでは main.c を増やさないことを別途確認する
        self.assertEqual(out["unrecorded_files"], ["main.c"])
        log = self.log_path.read_text(encoding="utf-8")
        row = [ln for ln in log.split("\n") if ln.startswith("| `util_fn[MEDIUM:src/util/helper.c]`")][0]
        self.assertIn("src/util/helper.c", row)
        self.assertNotIn("main.c", row)

    def test_case_a_symbol_is_swept_globally_only_when_recorded(self):
        # shared は conn.c と other.c に現れる。MEDIUM スコープ限定なら conn.c のみ、ケースA なら全域
        (self.repo / "src" / "net" / "extra.c").write_text("int extra(void) { return shared(3); }\n", encoding="utf-8")
        self._set_state(visited=self._state()["visited"] + ["shared[MEDIUM:src/net/conn.c]"],
                        truncated=[], frontier=[])
        # ケースA の記録が無い: スコープ限定。extra.c の shared は検索されない
        code, out, _e = self._sweep()
        self.assertEqual((code, out["unrecorded_hits"]), (0, 0))
        log = self.log_path.read_text(encoding="utf-8")
        row = [ln for ln in log.split("\n") if ln.startswith("| `shared[MEDIUM:src/net/conn.c]`")][0]
        self.assertIn("src/net/conn.c", row)
        # ケースA の記録あり: HIGH として全域を検索する
        log_text = self.log_path.read_text(encoding="utf-8")
        log_text = log_text.replace("## 確定した波及ファイル一覧", mod.CASE_DUP_HEADING + "（発生時のみ記録）\n"
                                    "| Wave | シンボル | 検出スコープ一覧 | ケース | 処置 |\n|---|---|---|---|---|\n"
                                    "| Wave 1 | `shared` | `src/net/conn.c`, `src/net/other.c` | case-a | "
                                    "promote-high; discard=`src/net/other.c` |\n\n## 確定した波及ファイル一覧", 1)
        self.log_path.write_text(log_text, encoding="utf-8")
        code, out, _e = self._sweep()
        self.assertEqual((code, out["unrecorded_files"]), (mod.EXIT_UNRECORDED_SWEEP, ["src/net/extra.c"]))

    def test_ledger_and_digest_arguments_are_removed(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                mod.build_parser().parse_args(self._sweep_argv() + ["--digest-dir", str(self.work)])


DRAFT_NET = "## 2.A. net\n\n### 2.A.1 処理フロー\n\n接続。\n"


class AssembleLayoutTest(_DocBase):
    """assemble-spo --layout-only --only seed-direct（追加下調べの配置と書き先）。"""

    def setUp(self):
        super().setUp()
        self._auto_assign()

    def test_layout_only_requires_only_seed_direct(self):
        code, _o, _e = self._run_exit(["assemble-spo", "--path", str(self.state_path), *self._common_argv(10),
                                       "--layout-only"])
        self.assertEqual(code, 2)
        code, _o, _e = self._run_exit(["assemble-spo", "--path", str(self.state_path), *self._common_argv(10),
                                       "--layout-only", "--only", "seed-direct"])
        self.assertEqual(code, 2)

    def test_integrated_layout_returns_draft_outputs(self):
        self._set_state(seed_direct_files=["src/auth/login.c", "src/auth/session.c"])
        r = self._run(self._layout_argv())
        # 配置判定は台帳（login.c）＋追加下調べの対象（session.c）だけ。波紋調査の確定ファイル（7件）は数えない
        self.assertEqual((r["layout"], r["moved_to_split"], r["documented_total"]), ("integrated", False, 2))
        self.assertEqual([m["module"] for m in r["modules"]], ["auth"])
        self.assertEqual(r["file_outputs"], {"src/auth/session.c": {
            "module": "auth", "output_file": str(self.work / "module-drafts" / "auth.md")}})
        self.assertEqual(r["over_limit_files"], [])
        self.assertFalse((self.out / "modules").exists())

    def test_split_layout_when_ledger_plus_targets_exceed(self):
        self._set_state(seed_direct_files=["src/auth/session.c", "src/net/conn.c"])
        r = self._run(self._layout_argv(max_files=2))
        self.assertEqual((r["layout"], r["documented_total"]), ("split", 3))
        self.assertEqual(r["file_outputs"]["src/net/conn.c"],
                         {"module": "net", "output_file": str(self.out / "modules" / "net-spo.md")})
        self.assertEqual(r["module_file_counts"], {"auth": 2, "net": 1})

    def test_max_files_limits_targets(self):
        self._set_state(seed_direct_files=["src/auth/session.c", "src/net/conn.c", "src/net/sub/x.c"],
                        seed_direct_hits={"src/net/sub/x.c": 4})
        r = self._run(self._layout_argv(cap=1))
        self.assertEqual(list(r["file_outputs"]), ["src/net/sub/x.c"])
        self.assertEqual(r["over_limit_files"], ["src/auth/session.c", "src/net/conn.c"])
        self.assertEqual(r["documented_total"], 2)

    def test_subdirectory_split_file_outputs_and_filtering(self):
        self._write_ledger([("src/auth/login.c", "auth", "src/auth", "下調べ"),
                            ("src/net/conn.c", "net", "src/net", "下調べ"), ("src/net/other.c", "net", "src/net", "下調べ")])
        (self.out / "modules").mkdir()
        shutil.copy(DOC_FIXTURE / "modules" / "net-spo.md", self.out / "modules" / "net-spo.md")
        self._set_state(seed_direct_files=["src/net/sub/x.c"])
        r = self._run(self._layout_argv(max_files=2))
        self.assertEqual(r["layout"], "split")
        net = {m["module"]: m for m in r["modules"]}["net"]
        self.assertEqual(net["mode"], "subdir")
        self.assertEqual(r["file_outputs"]["src/net/sub/x.c"]["output_file"],
                         str(self.out / "modules" / "net" / "sub-spo.md"))
        sub = (self.out / "modules" / "net" / "sub-spo.md").read_text(encoding="utf-8")
        root = (self.out / "modules" / "net" / "root-spo.md").read_text(encoding="utf-8")
        self.assertIn("| x_fn | src/net/sub/x.c |", sub)
        self.assertNotIn("| conn_open |", sub)
        self.assertIn("| conn_open | src/net/conn.c |", root)
        self.assertIn("**文書番号：** SPO-CR-2026-970-net-sub", sub)
        index = (self.out / "modules" / "net-spo.md").read_text(encoding="utf-8")
        self.assertIn("## 2. サブモジュール一覧", index)
        self.assertIn("| sub | `modules/net/sub-spo.md` | 1 |", index)
        self.assertIn("**作成者：** AI（xddp-specout-prelim-agent）", index)
        self.assertIn("**版数：** 0.1", index)
        before = sub
        self._run(self._layout_argv(max_files=2))
        self.assertEqual((self.out / "modules" / "net" / "sub-spo.md").read_text(encoding="utf-8"), before)

    def test_module_without_subdirectories_gets_over_threshold_note(self):
        self._write_ledger([("src/net/conn.c", "net", "src/net", "下調べ"), ("src/net/other.c", "net", "src/net", "下調べ"),
                            ("src/net/sub/x.c", "net", "src/net", "下調べ")])
        (self.out / "modules").mkdir()
        shutil.copy(DOC_FIXTURE / "modules" / "net-spo.md", self.out / "modules" / "net-spo.md")
        shutil.rmtree(self.repo / "src" / "net" / "sub")
        r = self._run(self._layout_argv(max_files=2))
        net = {m["module"]: m for m in r["modules"]}["net"]
        self.assertEqual(net["mode"], "single")
        text = (self.out / "modules" / "net-spo.md").read_text(encoding="utf-8")
        self.assertIn("> ⚠️ 波及ファイル数（3）が SPECOUT_MAX_FILES_PER_MODULE（2）を超えています。", text)
        self._run(self._layout_argv(max_files=2))  # 件数の注記は二重に書かない
        self.assertEqual((self.out / "modules" / "net-spo.md").read_text(encoding="utf-8").count("波及ファイル数（"), 1)

    def test_layout_only_does_not_touch_entry_points_or_fingerprint(self):
        self._set_state(seed_direct_files=["src/auth/session.c"])
        self._run(self._layout_argv())
        self.assertFalse((self.work / "doc-entry-points.json").exists())
        self.assertFalse((self.work / "assemble-inputs.json").exists())


class AssembleSummaryTest(_DocBase):
    LEDGER = [("src/auth/login.c", "auth", "src/auth", "下調べ"), ("src/net/conn.c", "net", "src/net", "下調べ")]

    def _prepare(self, ledger=None, seed_direct=None):
        self._write_ledger(ledger or self.LEDGER)
        if seed_direct is not None:
            self._set_state(seed_direct_files=seed_direct)
        self._make_summary()
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2]), ("net", DRAFT_NET.split("\n", 2)[2])])

    def _section(self, start, end):
        spo = self._spo()
        return spo[spo.index(start):spo.index(end)]

    def test_creates_spo_with_script_sections(self):
        self._prepare()
        r = self._run(self._assemble_argv())
        self.assertEqual((r["layout"], r["ripple"]), ("integrated", True))
        self.assertEqual(sorted(r["sections_written"]), sorted(["1", "1.x", "5.0", "5.1", "5.2", "5.5", "8", "9"]))
        self.assertEqual(r["sections_missing"], [])
        spo = self._spo()
        self.assertIn("| 調査起点 | initial: `session_start` |", spo)
        self.assertIn("| 調査範囲 | 下調べ: 2 モジュール・2 ファイル（うち追加下調べ 0）／波紋調査: 採用 1 件"
                      "（initial 第0〜2波）・確定 7 件 |", spo)
        self.assertIn("| 検出モジュール数 | 4 モジュール |", spo)
        sec1x = self._section("### 1.x", "## 2.")
        self.assertIn("| " + " | ".join(mod.RUN_COLUMNS) + " |", sec1x)
        self.assertIn("| initial | 工程4a の初回 | `session_start` | 3 ／ 6 | 10000 ／ 160 | なし | なし |", sec1x)
        self.assertNotIn("資料化", sec1x)
        # 統合パス: §2.A… の各節の末尾に「波紋調査の結果」
        self.assertLess(spo.index("## 2.A. auth"), spo.index("## 2.B. net"))
        self.assertLess(spo.index("## 2.B. net"), spo.index("## 3."))
        sec2a = self._section("## 2.A. auth", "## 2.B. net")
        self.assertIn("### 2.A.7 既存仕様の文書化", sec2a)
        self.assertIn("### 2.A.9 波紋調査の結果\n" + mod.WRITER_SCRIPT_COMMENT, sec2a)
        self.assertIn("| src/auth/login.c | login_check | 0 | name-only | — | あり | seed(session_start) → 第0波 |", sec2a)
        self.assertIn("| src/auth/session.c | session_start | 0 | name-only | — | — |", sec2a)
        self.assertLess(sec2a.index("src/auth/login.c | login_check"), sec2a.index("src/auth/session.c | session_start"))
        sec2b = self._section("## 2.B. net", "## 3.")
        self.assertIn("### 2.B.9 波紋調査の結果", sec2b)
        self.assertLess(sec2b.index("| src/net/conn.c |"), sec2b.index("| src/net/other.c |"))
        # §5.0: 新しい列。資料の有無・最も浅い到達波
        sec50 = self._section("### 5.0", "### 5.1")
        self.assertIn("| " + " | ".join(mod.SUMMARY_COLUMNS) + " |", sec50)
        self.assertIn(mod.MIN_WAVE_NOTE, sec50)
        self.assertIn("| auth | 2 | 2 | 0 | — | あり | seed(session_start) → 第0波 |", sec50)
        self.assertIn("| net | 3 | 3 | 1 | — | あり | seed(session_start) → login_check → 第1波 |", sec50)
        self.assertIn("| root | 1 | 1 | 1 | — | なし |", sec50)
        self.assertNotIn("確認の観点", sec50)
        # §5.1 は第0波（全モジュール）
        sec51 = self._section("### 5.1", "### 5.2")
        self.assertIn("| src/auth/session.c | session_start | 変更必要 | auth | 第0波／派生元 seed(session_start)／判定 slice(none=self-def) |", sec51)
        self.assertIn("| src/auth/login.c | login_check | 参照のみ | auth |", sec51)
        # §5.2 は資料のあるモジュールだけ
        sec52 = self._section("### 5.2", "### 5.3")
        self.assertIn("| src/net/sub/x.c | x_fn | 要確認 | net | 第2波／派生元 W1-R1／判定 slice(escape=return) |", sec52)
        self.assertNotIn("helper", sec52)
        self.assertNotIn("| main.c |", sec52)
        self.assertIn(mod.SCOPE_52_NOTE, sec52)
        # §5.5: 台帳のファイルと資料のあるモジュールの確定ファイルのテスト可能性（テストファイルは探さない）
        sec55 = self._section("### 5.5", "### 5.6")
        self.assertIn("| ファイルパス | テスト可能性 | 備考 |", sec55)
        # 観察メモに行が無いファイルは `未確認`。備考は台帳の有無で分ける
        self.assertIn("### 5.5 テスト可能性\n" + mod.WRITER_SCRIPT_KEEP_COMMENT, sec55)
        self.assertIn(f"| src/auth/login.c | 未確認 | {mod.TESTABILITY_NOTE_NO_MEMO} |", sec55)
        self.assertIn(f"| src/auth/session.c | 未確認 | {mod.TESTABILITY_NOTE_UNREAD} |", sec55)
        self.assertIn(f"| src/net/sub/x.c | 未確認 | {mod.TESTABILITY_NOTE_UNREAD} |", sec55)
        self.assertNotIn("|  |  |", sec55)
        self.assertNotIn("tests/test_login.c", spo)
        self.assertNotIn("helper.c", sec55)
        self.assertNotIn("main.c", sec55)
        # §8 は資料のあるモジュールだけ
        sec8 = self._section("## 8.", "## 9.")
        self.assertIn("| auth | src/auth | SPO-CR-2026-970.md § 2.A, § 5（文書化ファイル数が閾値以下のため modules/ 未生成） |", sec8)
        self.assertIn("| net | src/net | SPO-CR-2026-970.md § 2.B, § 5", sec8)
        self.assertNotIn("| root |", sec8)
        self.assertNotIn("資料化の上限", spo)
        sec9 = self._section("## 9.", "## 10.")
        self.assertIn("[自動転記] grep未対応パターン: function-pointer-call", sec9)
        # 差し込んだ下書きは削除し、modules/ は作らない
        self.assertFalse((self.work / "module-drafts").exists())
        self.assertFalse((self.out / "modules").exists())

    def test_prelim_spo_becomes_confirmed_once(self):
        self._prepare()
        self._run(self._assemble_argv())
        spo = self._spo()
        self.assertIn("**作成者：** AI（xddp-specout-prelim-agent, xddp-specout-document-agent）", spo)
        self.assertIn("**版数：** 1.0", spo)
        self.assertNotIn("波紋調査前の資料です", spo)
        self.assertIn("| 0.1 | 2026-10-03 | AI（xddp-specout-prelim-agent） | 下調べ（波紋調査前） |\n"
                      "| 1.0 | 2026-10-04 | specout_bfs.py assemble-spo | 確定（波紋調査の結果を反映） |", spo)
        self._run(self._assemble_argv())
        self.assertEqual(self._spo().count("確定（波紋調査の結果を反映）"), 1)

    def test_ripple_kind_change_bumps_version(self):
        self._prepare()
        self._run(self._assemble_argv())
        # /xddp-revise の人の行が最後にあっても、最大の版の次の行を足す
        spo = self._spo().replace("| 1.0 | 2026-10-04 | specout_bfs.py assemble-spo | 確定（波紋調査の結果を反映） |",
                                  "| 1.0 | 2026-10-04 | specout_bfs.py assemble-spo | 確定（波紋調査の結果を反映） |\n"
                                  "| 1.1 | 2026-10-05 | 人 | レビュー指摘の反映 |")
        (self.out / "SPO-CR-2026-970.md").write_text(spo, encoding="utf-8")
        self._assemble_without_adopted()
        spo = self._spo()
        self.assertIn("**版数：** 1.2", spo)
        self.assertIn("| 1.2 | 2026-10-04 | specout_bfs.py assemble-spo | 波紋調査なしで作り直し |", spo)
        self._assemble_without_adopted()
        self.assertEqual(self._spo().count("波紋調査なしで作り直し"), 1)
        self._run(["run-adopt", "--repo-dir", str(self.out), "--run", "initial", "--by", "human", "--today", "t"])
        self._run(self._merged_ripple_argv())
        self._run(self._assemble_argv())
        self.assertIn("**版数：** 1.3", self._spo())
        self.assertIn("| 1.3 | 2026-10-04 | specout_bfs.py assemble-spo | 波紋調査の結果を反映 |", self._spo())

    def test_rerun_keeps_human_edits_and_is_idempotent(self):
        self._prepare()
        self._run(self._assemble_argv())
        spo = self._spo().replace("ログイン判定の流れ。", "人が直した流れ。")
        spo = spo.replace(f"| src/auth/login.c | 未確認 | {mod.TESTABILITY_NOTE_NO_MEMO} |", "| src/auth/login.c | DI可能 | 人の備考 |")
        spo = spo.replace("| # | 種別 | 内容 | 対応方針 |\n|---|---|---|---|\n",
                          "| # | 種別 | 内容 | 対応方針 |\n|---|---|---|---|\n| 1 | 質問 | 人が書いた行 | 保留 |\n")
        (self.out / "SPO-CR-2026-970.md").write_text(spo, encoding="utf-8")
        self._run(self._assemble_argv())
        again = self._spo()
        self.assertIn("人が直した流れ。", again)
        self.assertIn("| src/auth/login.c | DI可能 | 人の備考 |", again)
        self.assertEqual(again.count(mod.WRITER_SCRIPT_KEEP_COMMENT), 1)
        self.assertIn("| 1 | 質問 | 人が書いた行 | 保留 |", again)
        self.assertIn("| 2 | 懸念 | [自動転記] grep未対応パターン", again)
        self.assertEqual(again.count("### 2.A.9 波紋調査の結果"), 1)
        self.assertEqual(again.count("### 2.B.9 波紋調査の結果"), 1)
        self._run(self._assemble_argv())
        self.assertEqual(self._spo(), again)

    def test_drafts_are_reextracted_from_current_spo(self):
        self._prepare(seed_direct=["src/auth/login.c", "src/auth/session.c"])
        self._run(self._assemble_argv())
        (self.out / "SPO-CR-2026-970.md").write_text(self._spo().replace("ログイン判定の流れ。", "人が直した流れ。"),
                                                     encoding="utf-8")
        r = self._run(self._layout_argv())
        draft = Path(r["file_outputs"]["src/auth/session.c"]["output_file"]).read_text(encoding="utf-8")
        self.assertIn("人が直した流れ。", draft)
        self.assertNotIn("波紋調査の結果", draft)

    def test_section_5_5_takes_testability_and_note_from_observation_memo(self):
        self._prepare()
        (self.work / "observation-memo.md").write_text(
            "## テスト可能性\n| ファイルパス | テスト可能性 | 備考 |\n|---|---|---|\n"
            "| src/net/conn.c | 密結合 | 静的参照が多い |\n", encoding="utf-8")
        self._run(self._assemble_argv())
        self.assertIn("| src/net/conn.c | 密結合 | 静的参照が多い |", self._section("### 5.5", "### 5.6"))

    def test_section_5_5_rebuilds_unconfirmed_rows_and_keeps_other_comments(self):
        self._prepare()
        self._run(self._assemble_argv())
        self.assertIn(f"| src/auth/session.c | 未確認 | {mod.TESTABILITY_NOTE_UNREAD} |", self._section("### 5.5", "### 5.6"))
        # `未確認` の行のファイルが後で台帳に入ると、備考は台帳のファイルの文言に変わる（`未確認` は既存の値として残さない）
        self._write_ledger(self.LEDGER + [("src/auth/session.c", "auth", "src/auth", "追加下調べ")])
        self._run(self._assemble_argv())
        sec55 = self._section("### 5.5", "### 5.6")
        self.assertIn(f"| src/auth/session.c | 未確認 | {mod.TESTABILITY_NOTE_NO_MEMO} |", sec55)
        self.assertNotIn(f"| src/auth/session.c | 未確認 | {mod.TESTABILITY_NOTE_UNREAD} |", sec55)
        # §5.5 だけが専用の書き手のコメントで、他の節は今のまま
        self.assertEqual(self._spo().count(mod.WRITER_SCRIPT_KEEP_COMMENT), 1)
        self.assertIn(mod.WRITER_SCRIPT_COMMENT, self._section("### 5.1", "### 5.2"))

    def test_template_5_5_comment_matches_constant(self):
        tpl = SUMMARY_TPL.read_text(encoding="utf-8")
        self.assertIn("### 5.5 テスト可能性\n" + mod.WRITER_SCRIPT_KEEP_COMMENT + "\n", tpl)

    def test_brief_lists_representatives_with_note(self):
        self._prepare()
        with patch.object(mod, "BRIEF_REPRESENTATIVES", 2):
            self._run(self._assemble_argv(level="brief"))
        sec52 = self._section("### 5.2", "### 5.3")
        rows = [ln for ln in sec52.split("\n") if ln.startswith("| ") and "第" in ln]
        self.assertEqual(len(rows), 2)
        self.assertIn("第1波", rows[0])
        self.assertIn("> quick プロファイルのため代表例のみ記載。詳細は discovery-log.md を参照", sec52)
        self.assertIn(mod.SCOPE_52_NOTE, sec52)
        self._run(self._assemble_argv())  # full に戻すと注記は消える
        sec52 = self._section("### 5.2", "### 5.3")
        self.assertNotIn("quick プロファイルのため代表例のみ記載", sec52)
        self.assertEqual(sec52.count(mod.SCOPE_52_NOTE), 1)

    def test_summary_rows_are_capped(self):
        self._prepare()
        with patch.object(mod, "SUMMARY_MAX_ROWS", 2):
            self._make_summary()
            self._run(self._assemble_argv())
        sec50 = self._section("### 5.0", "### 5.1")
        self.assertIn("| ほか 2 モジュール・2 ファイル（`ripple-summary.md` を参照） | — |", sec50)
        self.assertNotIn("| src-util |", sec50)

    def test_module_ripple_rows_are_capped(self):
        self._prepare()
        with patch.object(mod, "MODULE_RIPPLE_MAX_ROWS", 1):
            self._run(self._assemble_argv())
        sec2b = self._section("## 2.B. net", "## 3.")
        self.assertIn("| ほか 2 ファイル（`ripple-summary.md` を参照） | — |", sec2b)

    def test_section_9_lists_gap_and_sweep_files(self):
        self._prepare(seed_direct=["src/auth/login.c", "src/auth/session.c"])
        sweep = self.run_work / "verify-sweep.json"
        sweep.write_text(json.dumps({"ok": True, "unrecorded_hits": 1, "unrecorded_files": ["src/net/extra.c"]}),
                         encoding="utf-8")
        self._run(self._assemble_argv())
        sec9 = self._section("## 9.", "## 10.")
        self.assertIn("[自動転記] シードの直接参照で資料の無いファイル: src/auth/session.c（追加下調べでも資料にできなかった。§5.0 の ⚠️）",
                      sec9)
        self.assertIn("[自動転記] 検証スイープの未記録ヒット 1 件（波紋調査の帳簿に無いファイル: src/net/extra.c）", sec9)
        self.assertIn("| auth | 2 | 2 | 0 | 2（⚠️1） | あり |", self._section("### 5.0", "### 5.1"))

    def test_final_assembly_does_not_create_documents_for_undocumented_modules(self):
        # net は確定ファイルが 3 件（> 2）でも資料が無いので modules/ を作らず、統合パスのまま
        self._prepare(ledger=[("src/auth/login.c", "auth", "src/auth", "下調べ")])
        r = self._run(self._assemble_argv(max_files=2))
        self.assertEqual((r["layout"], r["documented_total"]), ("integrated", 1))
        self.assertFalse((self.out / "modules").exists())
        # 分割パスでも、資料の無いモジュールの索引・資料は作らない
        self._write_module_doc("auth", "src/auth")
        r = self._run(self._assemble_argv(max_files=2))
        self.assertEqual(sorted(p.name for p in (self.out / "modules").iterdir()), ["auth-spo.md"])

    def test_split_layout_writes_module_ripple_sections_and_finalizes(self):
        self._prepare(ledger=self.LEDGER)
        (self.out / "SPO-CR-2026-970.md").unlink()
        self._write_module_doc("auth", "src/auth")
        shutil.copy(DOC_FIXTURE / "modules" / "net-spo.md", self.out / "modules" / "net-spo.md")
        r = self._run(self._assemble_argv(max_files=1))
        self.assertEqual(r["layout"], "split")
        auth = (self.out / "modules" / "auth-spo.md").read_text(encoding="utf-8")
        self.assertLess(auth.index("## 波紋調査の結果"), auth.index("## 5. 変更履歴"))
        self.assertIn("## 波紋調査の結果\n" + mod.WRITER_SCRIPT_COMMENT, auth)
        self.assertIn("| src/auth/session.c | session_start | 0 | name-only | — | — |", auth)
        self.assertIn("**作成者：** AI（xddp-specout-prelim-agent）", auth)
        self.assertIn("**版数：** 1.0", auth)
        self.assertIn("| 1.0 | 2026-10-04 | specout_bfs.py assemble-spo | 確定（波紋調査の結果を反映） |", auth)
        net = (self.out / "modules" / "net-spo.md").read_text(encoding="utf-8")
        self.assertIn("| src/net/sub/x.c | x_fn | 2 |", net)
        self._run(self._assemble_argv(max_files=1))
        again = (self.out / "modules" / "auth-spo.md").read_text(encoding="utf-8")
        self.assertEqual(again, auth)
        self.assertEqual(again.count("## 波紋調査の結果"), 1)
        sec8 = self._section("## 8.", "## 9.")
        self.assertIn("| auth | src/auth | [modules/auth-spo.md](modules/auth-spo.md) |", sec8)
        self.assertNotIn("| root |", sec8)

    def test_subdirectory_documents_get_their_own_files(self):
        self._prepare(ledger=[("src/net/conn.c", "net", "src/net", "下調べ"), ("src/net/other.c", "net", "src/net", "下調べ"),
                              ("src/net/sub/x.c", "net", "src/net", "下調べ")])
        (self.out / "SPO-CR-2026-970.md").unlink()
        (self.out / "modules").mkdir()
        shutil.copy(DOC_FIXTURE / "modules" / "net-spo.md", self.out / "modules" / "net-spo.md")
        self._run(self._layout_argv(max_files=2))
        self._run(self._assemble_argv(max_files=2))
        sub = (self.out / "modules" / "net" / "sub-spo.md").read_text(encoding="utf-8")
        root = (self.out / "modules" / "net" / "root-spo.md").read_text(encoding="utf-8")
        self.assertIn("| src/net/sub/x.c | x_fn |", sub)
        self.assertNotIn("| src/net/conn.c | conn_open |", sub)
        self.assertIn("| src/net/conn.c | conn_open |", root)
        index = (self.out / "modules" / "net-spo.md").read_text(encoding="utf-8")
        self.assertNotIn("## 波紋調査の結果", index)
        self.assertIn("**版数：** 1.0", index)

    def test_moved_documents_follow_spo_version_and_drop_ripple_subsection(self):
        for spo_version, expected in (("0.1", "0.1"), ("1.0", "1.0"), ("1.1", "1.0")):
            with self.subTest(spo_version=spo_version):
                self.setUp()
                self._prepare(seed_direct=["src/auth/login.c", "src/auth/session.c"])
                self._run(self._assemble_argv())
                spo = re.sub(r"\*\*版数：\*\* \S+", f"**版数：** {spo_version}", self._spo())
                (self.out / "SPO-CR-2026-970.md").write_text(spo, encoding="utf-8")
                r = self._run(self._layout_argv(max_files=2))
                self.assertEqual((r["layout"], r["moved_to_split"]), ("split", True))
                doc = (self.out / "modules" / "auth-spo.md").read_text(encoding="utf-8")
                self.assertIn("**作成者：** AI（xddp-specout-prelim-agent）", doc)
                self.assertIn(f"**版数：** {expected}", doc)
                self.assertNotIn("波紋調査の結果", doc)
                self.assertIn("| 0.1 | 2026-10-04 | AI（xddp-specout-prelim-agent） | 下調べ（波紋調査前） |", doc)
                if expected == "1.0":
                    self.assertIn("| 1.0 | 2026-10-04 | specout_bfs.py assemble-spo | 確定（統合パスから移し替え） |", doc)
                else:
                    self.assertNotIn("| 1.0 |", doc)
                self.assertIn("### 2.1 処理フロー", doc)
                self.assertIn("### 3.1 ログイン", doc)
                self.assertNotIn("## 2.A.", (self.out / "SPO-CR-2026-970.md").read_text(encoding="utf-8"))
                self._run(self._assemble_argv(max_files=2))
                doc = (self.out / "modules" / "auth-spo.md").read_text(encoding="utf-8")
                self.assertEqual(doc.count("## 波紋調査の結果"), 1)
                self.tearDown()

    def test_inputs_fingerprint_and_commit(self):
        self._prepare()
        r = self._run(self._assemble_argv())
        self.assertTrue(r["inputs_changed"])
        self.assertRegex(r["inputs_fingerprint"], r"^[0-9a-f]{64}$")
        self.assertFalse((self.work / "assemble-inputs.json").exists())   # assemble-spo は指紋を保存しない
        c = self._run(["commit-assemble-inputs", "--output-dir", str(self.out), "--fingerprint", r["inputs_fingerprint"]])
        self.assertTrue(c["ok"])
        self.assertEqual(json.loads((self.work / "assemble-inputs.json").read_text(encoding="utf-8")),
                         {"fingerprint": r["inputs_fingerprint"]})
        self.assertFalse(self._run(self._assemble_argv())["inputs_changed"])
        # CRS はパスが同じでも内容が変われば変わる
        original = self.crs.read_text(encoding="utf-8")
        self.crs.write_text(original + "SP-002: 追加\n", encoding="utf-8")
        self.assertTrue(self._run(self._assemble_argv())["inputs_changed"])
        self.crs.write_text(original, encoding="utf-8")
        self.assertFalse(self._run(self._assemble_argv())["inputs_changed"])
        # 波紋調査の要約・台帳が変われば変わる
        self.summary_json.write_text(self.summary_json.read_text(encoding="utf-8") + " ", encoding="utf-8")
        self.assertTrue(self._run(self._assemble_argv())["inputs_changed"])
        self._make_summary()
        self.assertFalse(self._run(self._assemble_argv())["inputs_changed"])
        self.ledger.write_text(self.ledger.read_text(encoding="utf-8")
                               + "| src/auth/session.c | auth | src/auth | 追加下調べ | x |\n", encoding="utf-8")
        self.assertTrue(self._run(self._assemble_argv())["inputs_changed"])
        self.assertEqual(self._run_exit(["commit-assemble-inputs", "--output-dir", str(self.out),
                                         "--fingerprint", "xyz"])[0], 1)

    def test_entry_points_accumulate_and_follow_adopted_runs(self):
        self._prepare()
        self._set_state(entry_point_symbols=["ep0"])
        r1 = self._run(self._assemble_argv(entry_points="foo,alpha"))
        self.assertEqual(r1["doc_entry_points"], ["alpha", "ep0", "foo"])
        self._run(["commit-assemble-inputs", "--output-dir", str(self.out), "--fingerprint", r1["inputs_fingerprint"]])
        # 引数なしの再実行でも ENTRY_POINTS と指紋は変わらない。累積には人の指定だけを書き戻す
        r2 = self._run(self._assemble_argv(entry_points=""))
        self.assertEqual(r2["doc_entry_points"], ["alpha", "ep0", "foo"])
        self.assertFalse(r2["inputs_changed"])
        self.assertEqual(json.loads((self.work / "doc-entry-points.json").read_text(encoding="utf-8")),
                         ["alpha", "foo"])
        # 人が足した調査を採用するとそのシードが入り、取り消すと外れる
        self._add_run("run-1", seeds=["bar"])
        self._run(["run-adopt", "--repo-dir", str(self.out), "--run", "run-1", "--by", "human", "--today", "t"])
        self._run(self._merged_ripple_argv())
        self.assertEqual(self._run(self._assemble_argv(entry_points=""))["doc_entry_points"],
                         ["alpha", "bar", "ep0", "foo"])
        self._run(["run-unadopt", "--repo-dir", str(self.out), "--run", "run-1", "--by", "human", "--today", "t"])
        self._run(self._merged_ripple_argv())
        self.assertEqual(self._run(self._assemble_argv(entry_points=""))["doc_entry_points"], ["alpha", "ep0", "foo"])
        # 人が新しいエントリポイントを指定した再実行は入力の変更になる
        self.assertTrue(self._run(self._assemble_argv(entry_points="beta"))["inputs_changed"])
        self._set_state(seed_direct_files=["src/auth/session.c"])
        self._run(self._layout_argv())
        self.assertEqual(json.loads((self.work / "doc-entry-points.json").read_text(encoding="utf-8")),
                         ["alpha", "beta", "foo"])

    def test_fingerprint_follows_documented_elements(self):
        import hashlib
        self._prepare()
        r = self._run(self._assemble_argv(entry_points="b,a"))
        h = hashlib.sha256()
        for name, value in (("ledger", self.ledger.read_bytes()), ("ripple_summary", self.summary_json.read_bytes()),
                            ("no_ripple", b"0"), ("crs", self.crs.read_bytes()), ("entry_points", b"a,b"),
                            ("request_log", b"")):
            h.update(name.encode("utf-8") + b"\n" + value + b"\n")
        self.assertEqual(r["inputs_fingerprint"], h.hexdigest())

    def test_metrics_line(self):
        self._prepare(seed_direct=["src/auth/login.c", "src/auth/session.c", "src/net/other.c"])
        self._write_reviewed([("src/net/other.c", "別物")])
        self._make_summary()
        metrics = self.root / "metrics.jsonl"
        self._run(self._assemble_argv(extra=["--metrics", str(metrics)]))
        line = json.loads(metrics.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual({k: line[k] for k in ("event", "ripple", "prelim_file_count", "additional_file_count",
                                                "seed_direct_file_count", "prelim_gap_count", "gap_over_limit_count",
                                                "gap_reviewed_unrelated_count")},
                         {"event": "specout_doc_summary", "ripple": True, "prelim_file_count": 2,
                          "additional_file_count": 0, "seed_direct_file_count": 3, "prelim_gap_count": 1,
                          "gap_over_limit_count": 0, "gap_reviewed_unrelated_count": 1})
        self._run(self._assemble_argv(extra=["--metrics", str(metrics)]))
        self.assertEqual(len(metrics.read_text(encoding="utf-8").splitlines()), 2)

    def test_usage_errors(self):
        self._prepare()
        base = ["assemble-spo", *self._common_argv(10)]
        crs = ["--crs-file", str(self.crs), "--entry-points", ""]
        cases = [
            base + ["--path", str(self.state_path), "--summary-json", str(self.summary_json)],          # crs なし
            base + ["--path", str(self.state_path), *crs],                                             # summary-json なし
            base + ["--path", str(self.state_path), "--summary-json", str(self.summary_json), *crs,
                    "--only", "seed-direct", "--max-files", "3"],                                      # --only は layout-only のみ
            base + ["--no-ripple", "--repo-path", str(self.repo), "--repo", "svc", *crs, "--path", str(self.state_path)],
            base + ["--no-ripple", "--repo-path", str(self.repo), "--repo", "svc", *crs,
                    "--summary-json", str(self.summary_json)],
            base + ["--no-ripple", "--repo-path", str(self.repo), "--repo", "svc", *crs, "--sweep-json", "x.json"],
            base + ["--no-ripple", *crs],                                                              # repo-path なし
            base + ["--no-ripple", "--repo-path", str(self.repo), "--repo", "svc", *crs,
                    "--layout-only", "--only", "seed-direct", "--max-files", "3"],
        ]
        for argv in cases:
            with self.subTest(argv=argv[len(base):]):
                self.assertEqual(self._run_exit(argv)[0], 2)

    def test_requires_summary_json_file(self):
        self._prepare()
        self.summary_json.unlink()
        code, _o, err = self._run_exit(self._assemble_argv())
        self.assertEqual(code, 1)
        self.assertIn("ripple-summary", err)

    def test_no_ripple_sections(self):
        self._write_ledger(self.LEDGER)
        shutil.rmtree(self.out / "ripple")
        (self.work / "no-ripple.json").write_text('{"cr": "CR-2026-970", "repo": "svc", "decided": "2026-10-04"}',
                                                  encoding="utf-8")
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2]), ("net", DRAFT_NET.split("\n", 2)[2])])
        metrics = self.root / "metrics.jsonl"
        self._run(self._merged_ripple_argv())
        r = self._run(self._assemble_argv(extra=["--metrics", str(metrics)]))
        self.assertEqual((r["ripple"], r["layout"]), (False, "integrated"))
        spo = self._spo()
        self.assertIn("| 調査範囲 | 下調べ: 2 モジュール・2 ファイル（うち追加下調べ 0）／波紋調査: 未実施（人の判断） |", spo)
        self.assertIn("| 波紋調査を行っていない（人の判断） | — | — | — | — | — | — |", self._section("### 1.x", "## 2."))
        sec50 = self._section("### 5.0", "### 5.1")
        self.assertIn("| auth | 1 | — | — | — | あり | — |", sec50)
        self.assertIn(mod.NO_RIPPLE_NOTE, sec50)
        self.assertIn("| src/auth/login.c | （モジュール資料を参照） | 下調べで特定 | auth | 振る舞い src/auth/login.c |",
                      self._section("### 5.1", "### 5.2"))
        sec52 = self._section("### 5.2", "### 5.3")
        self.assertIn(mod.NO_RIPPLE_NOTE, sec52)
        self.assertNotIn("要確認", sec52)
        sec55 = self._section("### 5.5", "### 5.6")
        self.assertIn(f"| src/auth/login.c | 未確認 | {mod.TESTABILITY_NOTE_NO_MEMO} |", sec55)
        self.assertNotIn("session.c", sec55)
        self.assertIn("### 2.A.9 波紋調査の結果\n" + mod.WRITER_SCRIPT_COMMENT + "\n\n波紋調査を行っていない（人の判断）", spo)
        self.assertIn("| 1.0 | 2026-10-04 | specout_bfs.py assemble-spo | 確定（波紋調査なし） |", spo)
        self.assertNotIn("[自動転記]", self._section("## 9.", "## 10."))
        line = json.loads(metrics.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(line, {**line, "event": "specout_doc_summary", "ripple": False, "prelim_file_count": 2,
                                "additional_file_count": 0})
        self.assertNotIn("seed_direct_file_count", line)
        # 波紋調査なしの指紋は ripple_summary が採用0件の要約・no_ripple が 1
        import hashlib
        h = hashlib.sha256()
        for name, value in (("ledger", self.ledger.read_bytes()), ("ripple_summary", self.summary_json.read_bytes()),
                            ("no_ripple", b"1"),
                            ("crs", self.crs.read_bytes()), ("entry_points", b""), ("request_log", b"")):
            h.update(name.encode("utf-8") + b"\n" + value + b"\n")
        self.assertEqual(r["inputs_fingerprint"], h.hexdigest())

    def test_truncation_summary_counts_records(self):
        rows = mod._truncation_summary([{"symbol": "a", "reason": "wave-limit"}, {"symbol": "a", "reason": "wave-limit"},
                                        {"symbol": "b", "reason": "wave-limit"}, {"symbol": "c", "reason": "hit-budget"}])
        counts = {reason: count for reason, count, _top in rows}
        self.assertEqual(counts, {"wave-limit": "2（記録 3 件）", "hit-budget": "1"})
        self._set_state(truncated=[{"symbol": "a", "reason": "wave-limit"}, {"symbol": "a", "reason": "wave-limit"},
                                   {"symbol": "b", "reason": "wave-limit"}])
        self._prepare()
        self._run(self._assemble_argv())
        self.assertIn("wave-limit: 2（記録 3 件）", self._section("### 1.x", "## 2."))
        self.assertIn("| wave-limit | 2（記録 3 件） |", self.summary_md.read_text(encoding="utf-8"))


class CommitAssembleInputsTest(_DocBase):
    def test_writes_fingerprint_file(self):
        fp = "a" * 64
        r = self._run(["commit-assemble-inputs", "--output-dir", str(self.out), "--fingerprint", fp])
        self.assertEqual(r["file"], str(self.work / "assemble-inputs.json"))
        self.assertEqual(json.loads((self.work / "assemble-inputs.json").read_text(encoding="utf-8")), {"fingerprint": fp})



class FalsePositiveConfirmedFilesTest(unittest.TestCase):
    """false-positive のヒットだけのファイルは確定ファイルにせず、false_positive_files に記録する。"""

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
        args = mod.build_parser().parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _init(self, symbols="sym", **kw):
        argv = ["init", "--path", str(self.state_path), "--repo-path", str(self.repo),
                "--discovery-log", str(self.log_path), "--symbols", symbols,
                "--today", "2026-10-10", "--cr", "CR-2026-999", "--repo", "svc"]
        for k, v in kw.items():
            argv += [f"--{k.replace('_', '-')}", str(v)]
        return self._run(argv)

    def _state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _commit(self, wave, rows, symbol="sym", pre_noisy=None, module_files=None, state_path=None):
        """rows: [(file, classification, next_symbols)]。1コマンド・1シンボルの波をコミットする。"""
        state_path = state_path or self.state_path
        hits = [{"line_id": f"W{wave}-R{i + 1}", "command_id": f"W{wave}-C1", "symbol": symbol, "scope_file": None,
                 "file": f, "line_no": i + 1, "matched_text": f"{symbol}(x)"} for i, (f, _c, _n) in enumerate(rows)]
        payload = {"wave": wave, "hits": hits, "frontier_medium_scopes": {}, "searched_frontier": [symbol],
                   "commands": [{"command_id": f"W{wave}-C1", "kind": "HIGH-compound", "pattern": symbol,
                                 "scope": "全域", "hit_count": len(rows)}]}
        if pre_noisy is not None:
            payload["pre_noisy"] = pre_noisy
            payload["module_files"] = module_files or {}
        classification = [{"line_id": h["line_id"], "classification": c, "next_symbols": n}
                          for h, (_f, c, n) in zip(hits, rows)]
        hits_path = self.root / f"h{wave}.json"
        class_path = self.root / f"c{wave}.json"
        hits_path.write_text(json.dumps(payload), encoding="utf-8")
        class_path.write_text(json.dumps(classification), encoding="utf-8")
        return self._run(["commit-wave", "--path", str(state_path), "--hits", str(hits_path),
                          "--classification", str(class_path), "--today", "2026-10-10"])

    def test_false_positive_only_file_is_not_confirmed(self):
        self._init()
        self._commit(0, [("src/comment.c", "false-positive", []), ("src/real.c", "propagation-direct", ["next"])])
        data = self._state()
        self.assertEqual(sorted(data["confirmed_files"]), ["src/real.c"])
        self.assertEqual(data["false_positive_files"], {"src/comment.c": 0})
        self.assertEqual(data["confirmed_file_count"], 1)
        brief = self._run(["status", "--path", str(self.state_path), "--brief"])
        self.assertEqual(brief["confirmed_file_count"], 1)

    def test_false_positive_and_real_hit_in_same_file_confirms(self):
        self._init()
        self._commit(0, [("src/a.c", "false-positive", []), ("src/a.c", "propagation-return", ["caller"])])
        data = self._state()
        self.assertIn("src/a.c", data["confirmed_files"])
        self.assertEqual(data["false_positive_files"], {})

    def test_later_real_hit_confirms_in_later_wave(self):
        self._init()
        self._commit(0, [("src/a.c", "false-positive", []), ("src/b.c", "propagation-direct", ["next"])])
        self.assertEqual(self._state()["false_positive_files"], {"src/a.c": 0})
        self._commit(1, [("src/a.c", "propagation-direct", ["more"])], symbol="next")
        data = self._state()
        self.assertEqual(data["confirmed_files"]["src/a.c"]["wave"], 1)
        self.assertEqual(data["false_positive_files"], {})

    def test_false_positive_after_confirmation_keeps_confirmed(self):
        self._init()
        self._commit(0, [("src/a.c", "propagation-direct", ["next"])])
        self._commit(1, [("src/a.c", "false-positive", [])], symbol="next")
        data = self._state()
        self.assertEqual(data["confirmed_files"]["src/a.c"]["wave"], 0)
        self.assertEqual(data["false_positive_files"], {})

    def test_out_of_scope_discard_only_file_is_confirmed(self):
        self._init()
        self._commit(0, [("src/a.c", "out-of-scope-discard", [])])
        data = self._state()
        self.assertIn("src/a.c", data["confirmed_files"])
        self.assertEqual(data["false_positive_files"], {})

    def test_pre_noisy_module_files_are_confirmed_even_if_representative_is_false_positive(self):
        self._init(max_files_per_module=1)
        self._commit(0, [("m/a.c", "false-positive", [])], pre_noisy=["sym"],
                     module_files={"sym": ["m/a.c", "m/b.c"]})
        data = self._state()
        self.assertEqual(sorted(data["confirmed_files"]), ["m/a.c", "m/b.c"])
        self.assertEqual(data["false_positive_files"], {})

    def test_pre_collapse_confirmed_files_are_superset_and_frontier_equal(self):
        """前倒し縮退ありの確定ファイルは縮退なしの上位集合になり、次の波の frontier は等しい。"""
        files = ["m/a.c", "m/b.c", "m/c.c"]
        labels = ["false-positive", "propagation-argument", "false-positive"]
        self._init(max_files_per_module=2)
        # 縮退あり: 代表行は m/a.c・m/b.c（m/c.c は非代表）
        self._commit(0, [(f, c, ["helper"] if c != "false-positive" else []) for f, c in zip(files[:2], labels[:2])],
                     pre_noisy=["sym"], module_files={"sym": files})
        collapsed = self._state()
        # 縮退なし: 全行を判定してコミットする
        old_state = self.root / "old-state.json"
        self._run(["init", "--path", str(old_state), "--repo-path", str(self.repo),
                   "--discovery-log", str(self.root / "old-log.md"), "--symbols", "sym",
                   "--today", "2026-10-10", "--cr", "CR-2026-999", "--repo", "svc", "--max-files-per-module", "2"])
        self._commit(0, [(f, c, ["helper"] if c != "false-positive" else []) for f, c in zip(files, labels)],
                     state_path=old_state)
        full = json.loads(old_state.read_text(encoding="utf-8"))
        self.assertTrue(set(full["confirmed_files"]) <= set(collapsed["confirmed_files"]))
        self.assertEqual(sorted(full["confirmed_files"]), ["m/b.c"])
        self.assertEqual(sorted(full["false_positive_files"]), ["m/a.c", "m/c.c"])
        self.assertEqual(sorted(collapsed["frontier"]), sorted(full["frontier"]))

    def test_wave0_module_priority_excludes_false_positive_only_directories(self):
        (self.repo / "real").mkdir()
        (self.repo / "noise").mkdir()
        self._init()
        self._commit(0, [("real/a.c", "propagation-direct", ["next"]), ("noise/b.c", "false-positive", [])])
        data = self._state()
        self.assertEqual(data["module_priority_mode"], "simple")
        self.assertEqual(data["module_priority_map"].get("real"), "HIGH")
        self.assertNotIn("noise", data["module_priority_map"])

    def test_discovery_log_section_legend_and_state_view(self):
        self._init()
        self._commit(0, [("src/comment.c", "false-positive", []), ("src/real.c", "propagation-direct", ["next"])])
        log = self.log_path.read_text(encoding="utf-8")
        self.assertIn(mod.FALSE_POSITIVE_FILES_HEADING + "\n", log)
        self.assertIn("| src/comment.c | Wave 0 |", log)
        self.assertNotIn("| src/comment.c | Wave 0 | ", log.split(mod.FALSE_POSITIVE_FILES_HEADING + "\n")[0])
        self.assertIn("この判定だけのファイルは確定ファイルにせず", log)
        # 確定ファイルの節の後ろに置き、波を重ねても1つだけ
        self.assertLess(log.rfind(mod.CONFIRMED_FILES_HEADING), log.rfind(mod.FALSE_POSITIVE_FILES_HEADING + "\n"))
        self._commit(1, [("src/x.c", "propagation-direct", [])], symbol="next")
        log = self.log_path.read_text(encoding="utf-8")
        self.assertEqual(log.count("\n" + mod.FALSE_POSITIVE_FILES_HEADING + "\n"), 1)
        self.assertEqual(log.count("\n" + mod.CONFIRMED_FILES_HEADING + "\n"), 1)
        self.assertLess(log.find("## Wave 1"), log.find("\n" + mod.CONFIRMED_FILES_HEADING + "\n"))
        self.assertLess(log.find("\n" + mod.CONFIRMED_FILES_HEADING + "\n"),
                        log.find("\n" + mod.FALSE_POSITIVE_FILES_HEADING + "\n"))
        md = self.state_path.with_suffix(".md").read_text(encoding="utf-8")
        self.assertIn("**判定で関係なしとしたファイル数：** 1", md)

    def test_section_says_none_when_empty(self):
        self._init()
        self._commit(0, [("src/real.c", "propagation-direct", [])])
        log = self.log_path.read_text(encoding="utf-8")
        section = log.split("\n" + mod.FALSE_POSITIVE_FILES_HEADING + "\n", 1)[1]
        self.assertIn("\nなし\n", section)

    def test_init_and_state_commands_keep_false_positive_files(self):
        self._init()
        self.assertEqual(self._state()["false_positive_files"], {})
        self._commit(0, [("src/comment.c", "false-positive", []), ("src/real.c", "propagation-direct", [])])
        self.assertEqual(self._state()["state"], "complete")
        self._run(["extend", "--path", str(self.state_path), "--max-wave", "9", "--today", "2026-10-10"])
        self.assertEqual(self._state()["false_positive_files"], {"src/comment.c": 0})
        self._run(["switch-engine", "--path", str(self.state_path), "--to", "rule", "--today", "2026-10-10"])
        self.assertEqual(self._state()["false_positive_files"], {"src/comment.c": 0})

    def test_import_resets_false_positive_files_and_warns(self):
        self._init()
        self._commit(0, [("src/comment.c", "false-positive", []), ("src/real.c", "propagation-direct", ["n"])])
        r = self._run(["import", "--path", str(self.state_path), "--from", str(self.state_path.with_suffix(".md"))])
        self.assertEqual(self._state()["false_positive_files"], {})
        self.assertIn("false_positive_files", " ".join(r["warnings"]))



# ---------------------------------------------------------------------------
# シンボルの同一性（エントリ表記 [FILE:…]・entry_identity・確定ファイルの identity）
# ---------------------------------------------------------------------------

class FileEntryFormatTest(unittest.TestCase):
    def test_parse_format_and_validate(self):
        self.assertEqual(mod._parse_entry("x[FILE:src/a.c]"), ("x", "src/a.c"))
        self.assertEqual(mod._parse_entry("x[MEDIUM:src/a.c]"), ("x", "src/a.c"))
        self.assertEqual([mod._entry_scope_kind(e) for e in ("x[FILE:a.c]", "x[MEDIUM:a.c]", "x")],
                         ["FILE", "MEDIUM", None])
        self.assertEqual(mod._format_entry("x", "a.c", "FILE"), "x[FILE:a.c]")
        self.assertEqual(mod._format_entry("x", "a.c"), "x[MEDIUM:a.c]")
        self.assertEqual(mod._format_entry("x", None, "FILE"), "x")
        mod._validate_frontier_format(["x[FILE:a.c]", "y[MEDIUM:b.c]", "z"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            mod._validate_frontier_format(["x[OTHER:a.c]"])


class FileEntrySeedTest(_PrelimTestBase):
    def test_candidates_accept_file_entries_and_preview_counts_in_file(self):
        self._write_file("src/a.c", "static int s_x;\nvoid f(void) { s_x = 1; }\n")
        self._write_file("src/b.c", "static int s_x;\n")
        self._write_candidates([("☑", "`s_x[FILE:src/a.c]`", "人が追加", "x", "", "", ""),
                                ("☑", "`s_x`", "CRS SP項目", "x", "", "", "")])
        seeds = mod._parse_seed_candidates(self.cand_path)
        self.assertEqual([c["symbol"] for c in seeds["candidates"]], ["s_x[FILE:src/a.c]", "s_x"])
        result = self._run(["seed-preview", "--seed-candidates", str(self.cand_path), "--repo-path", str(self.repo),
                            "--backend", "grep", "--max-files-per-module", "10"])
        self.assertEqual(result["zero_hit"], [])
        rows = {mod._split_row(l)[1]: mod._split_row(l) for l in self.cand_path.read_text(encoding="utf-8").split("\n")
                if l.startswith("| ☑")}
        self.assertEqual((rows["`s_x[FILE:src/a.c]`"][4], rows["`s_x[FILE:src/a.c]`"][5]), ("1", ""))
        self.assertEqual(rows["`s_x`"][4], "2")

    def test_seed_input_rejects_file_entries(self):
        inp = self.work / "seed-input.json"
        inp.write_text(json.dumps({"entry_points": ["s_x[FILE:src/a.c]"], "crs": [], "prelim": [],
                                   "code_derived": [], "inherit": [], "unresolved_entry_points": [],
                                   "unknown_behaviors": [], "unsupported_patterns": []}), encoding="utf-8")
        code, err = self._run_fail(["write-seed-candidates", "--input", str(inp), "--out", str(self.cand_path),
                                    "--unsupported-out", str(self.work / "u.json"), "--template",
                                    str(WriteSeedCandidatesTest.TEMPLATE), "--cr", "CR", "--repo", "svc"])
        self.assertEqual(code, 1)
        self.assertIn("FILE 形式", err)


class SymbolIdentityBfsTest(_SlicerBase):
    def _commit_direct(self, wave, commands, hits, classification, searched, medium_scopes=None, extra=None):
        payload = {"wave": wave, "commands": commands, "hits": hits, "searched_frontier": searched,
                   "frontier_medium_scopes": medium_scopes or {}}
        payload.update(extra or {})
        hp, cp = self.root / f"h{wave}.json", self.root / f"c{wave}.json"
        hp.write_text(json.dumps(payload), encoding="utf-8")
        cp.write_text(json.dumps(classification), encoding="utf-8")
        return self._run(["commit-wave", "--path", str(self.state_path), "--hits", str(hp),
                          "--classification", str(cp), "--today", "2026-10-11"])

    @staticmethod
    def _cmd(cid, kind, scope="全域", n=1, pattern="p"):
        return {"command_id": cid, "kind": kind, "pattern": pattern, "scope": scope, "hit_count": n}

    @staticmethod
    def _hit(lid, cid, sym, f, entry=None, scope=None, line=1):
        return {"line_id": lid, "command_id": cid, "symbol": sym, "scope_file": scope, "entry": entry or sym,
                "file": f, "line_no": line, "matched_text": sym, "route": "slice"}

    @staticmethod
    def _cls(lid, nxt=(), identity="resolved", kinds=None, name_only=(), cls="propagation-direct", enc="",
             summaries=None):
        return {"line_id": lid, "classification": cls, "next_symbols": list(nxt), "enclosing_function": enc,
                "is_external_api": False, "note": "t", "slice": {"engine": "slice", "status": "sliced", "escapes": []},
                "next_symbol_kinds": kinds or {}, "name_only_symbols": list(name_only), "identity": identity,
                "next_symbol_summaries": summaries or {}}

    # 24・35. search
    def test_search_file_entries(self):
        self._write("a.c", "static int s_x;\nvoid f(void) { s_x = p_y; }\n")
        self._write("b.c", "static int s_x;\nint g(void) { return s_x; }\n")
        self._init("seed_fn", engine="rule")
        self._set(frontier=["s_x[FILE:a.c]", "p_y[MEDIUM:a.c]", "s_x"], symbol_kinds={"s_x": "variable"})
        out = self._search()
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        kinds = {c["kind"]: c["scope"] for c in payload["commands"]}
        self.assertEqual(kinds, {"HIGH-compound": "全域", "FILE": "a.c", "MEDIUM": "a.c"})   # 種別の違う2つのコマンド
        file_hits = [h for h in payload["hits"] if h["entry"] == "s_x[FILE:a.c]"]
        self.assertEqual(sorted({h["file"] for h in file_hits}), ["a.c"])
        self.assertTrue(all("entry" in h for h in payload["hits"]))
        # 同じファイル・同じ行を HIGH と FILE で検索しても dedup の鍵は衝突しない
        self.assertEqual(len([h for h in payload["hits"] if h["file"] == "a.c" and h["symbol"] == "s_x"]), 4)
        self.assertEqual({h["loc_scope_class"] for h in file_hits}, {"FILE:a.c"})
        chunk = json.loads(Path(out["slice_chunk"]).read_text(encoding="utf-8"))
        self.assertEqual(chunk["frontier_kinds"], {"s_x": "variable"})
        self.assertEqual(chunk["seed_keys"], ["p_y", "s_x"])
        self.assertTrue(all("entry" in h for h in chunk["hits"]))

    def test_seed_global_file_entry_is_not_a_seed(self):
        self._write("a.c", "static int s_x;\nint seed_fn(void) { s_x = 1; return 0; }\n")
        self._init("seed_fn", engine="rule")
        self._set(frontier=["seed_fn", "s_x[FILE:a.c]"], seed_globals=["s_x[FILE:a.c]"])
        out = self._search()
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        self.assertEqual(payload["seed_symbols"], ["seed_fn"])
        self.assertEqual(out["wave0_seed_count"], 1)
        commit = self._classify_and_commit(out)
        self.assertEqual(commit["wave"], 0)
        self.assertIn("seed-global(s_x[FILE:a.c])", self._log())      # 28. 派生元

    # 25. commit-wave
    def test_file_entries_skip_crossing_and_case_abc(self):
        self._init("sym", engine="rule")
        self._set(visited=["s_x"], frontier=["p[MEDIUM:fileA.ts]", "p[MEDIUM:x.c]", "q[FILE:x.c]"])
        cmds = [self._cmd("W0-C1", "MEDIUM", "fileA.ts"), self._cmd("W0-C2", "MEDIUM", "x.c"),
                self._cmd("W0-C3", "FILE", "x.c")]
        hits = [self._hit("W0-R1", "W0-C1", "p", "fileA.ts", "p[MEDIUM:fileA.ts]", "fileA.ts"),
                self._hit("W0-R2", "W0-C2", "p", "x.c", "p[MEDIUM:x.c]", "x.c", line=2),
                self._hit("W0-R3", "W0-C3", "q", "x.c", "q[FILE:x.c]", "x.c", line=3)]
        cls = [dict(self._cls("W0-R1", cls="propagation-return"), is_external_api=True),
               self._cls("W0-R2", ["dropped"]),
               self._cls("W0-R3", ["s_x[FILE:x.c]", "f[FILE:x.c]"],
                         kinds={"s_x[FILE:x.c]": "variable", "f[FILE:x.c]": "function"})]
        r = self._commit_direct(0, cmds, hits, cls, ["p[MEDIUM:fileA.ts]", "p[MEDIUM:x.c]", "q[FILE:x.c]"],
                                medium_scopes={"p": ["fileA.ts", "x.c"]})
        self.assertEqual(r["case_a_promoted"], ["p"])
        data = self._state()
        self.assertIn("s_x[FILE:x.c]", data["frontier"])        # HIGH の s_x が visited でも入る
        self.assertNotIn("dropped", data["frontier"])            # ケースA の破棄は MEDIUM だけ
        self.assertIn("f[FILE:x.c]", data["frontier"])
        self.assertEqual(data["confirmed_files"]["x.c"]["confidence"], "HIGH")
        self.assertEqual((data["symbol_kinds"]["s_x"], data["symbol_kinds"]["f"]), ("variable", "function"))
        self.assertIn("`f`[FILE:x.c]", self._log())

    def test_symbol_kind_priority(self):
        self._init("sym", engine="rule")
        cmds = [self._cmd("W0-C1", "HIGH-compound", n=2)]
        hits = [self._hit("W0-R1", "W0-C1", "sym", "a.c"), self._hit("W0-R2", "W0-C1", "sym", "b.c", line=2)]
        cls = [self._cls("W0-R1", ["m", "v"], kinds={"m": "variable", "v": "variable"}),
               self._cls("W0-R2", ["m[FILE:b.c]", "v"], kinds={"m[FILE:b.c]": "macro", "v": "variable"})]
        self._commit_direct(0, cmds, hits, cls, ["sym"])
        kinds = self._state()["symbol_kinds"]
        self.assertEqual((kinds["m"], kinds["v"]), ("macro", "variable"))

    # 26・33・34. 同一性の連鎖
    def test_identity_chain(self):
        self._init("sym", engine="rule")
        self.assertEqual(self._state()["entry_identity"], {"sym": "resolved"})
        cmds = [self._cmd("W0-C1", "HIGH-compound", n=4)]
        hits = [self._hit(f"W0-R{i}", "W0-C1", "sym", f"f{i}.c", line=i) for i in range(1, 5)]
        cls = [self._cls("W0-R1", ["a"]), self._cls("W0-R2", ["b"], identity="name-only"),
               self._cls("W0-R3", ["c", "d"], name_only=["d"]),
               {"line_id": "W0-R4", "classification": "propagation-direct", "next_symbols": ["e", "a"],
                "enclosing_function": "", "is_external_api": False, "note": "llm"}]
        self._commit_direct(0, cmds, hits, cls, ["sym"])
        data = self._state()
        self.assertEqual({k: data["entry_identity"][k] for k in "abcde"},
                         {"a": "resolved", "b": "name-only", "c": "resolved", "d": "name-only", "e": "name-only"})
        self.assertEqual({f: data["confirmed_files"][f]["identity"] for f in ("f1.c", "f2.c", "f4.c")},
                         {"f1.c": "resolved", "f2.c": "name-only", "f4.c": "name-only"})
        self.assertIn("| HIGH | resolved | `a` |", self._log())
        self.assertIn("| f2.c | Wave 0 | HIGH | name-only | ⬜ 未 |", self._log())
        # 第1波: name-only の b から届いたヒットは name-only。visited の b に resolved の経路が届くと上がるが再検索しない
        cmds = [self._cmd("W1-C1", "HIGH-compound", n=2)]
        hits = [self._hit("W1-R1", "W1-C1", "b", "f2.c", line=9), self._hit("W1-R2", "W1-C1", "c", "f9.c")]
        cls = [self._cls("W1-R1", ["x"]), self._cls("W1-R2", ["b"])]
        self._commit_direct(1, cmds, hits, cls, ["b", "c"])
        data = self._state()
        self.assertEqual((data["entry_identity"]["x"], data["entry_identity"]["b"]), ("name-only", "resolved"))
        self.assertNotIn("b", data["frontier"])
        self.assertEqual(data["confirmed_files"]["f2.c"]["identity"], "name-only")
        # 34. 確信度が同じでも後の波の resolved の経路で上がり、下がらない
        cmds = [self._cmd("W2-C1", "HIGH-compound", n=2)]
        hits = [self._hit("W2-R1", "W2-C1", "c", "f2.c", line=5), self._hit("W2-R2", "W2-C1", "x", "f1.c", line=7)]
        cls = [self._cls("W2-R1"), self._cls("W2-R2")]
        self._set(frontier=["c", "x"])
        self._commit_direct(2, cmds, hits, cls, ["c", "x"])
        data = self._state()
        self.assertEqual((data["confirmed_files"]["f2.c"]["identity"], data["confirmed_files"]["f2.c"]["wave"]),
                         ("resolved", 0))
        self.assertEqual(data["confirmed_files"]["f1.c"]["identity"], "resolved")
        brief = self._run(["status", "--path", str(self.state_path), "--brief"])
        self.assertEqual(brief["name_only_file_count"], 1)    # f4.c（LLM 分類のヒットだけ）
        self.assertIn("**名前の一致のみの確定ファイル数：** 1", (self.work / "bfs-state.md").read_text(encoding="utf-8"))

    def test_entries_without_identity_are_name_only(self):
        self._init("sym", engine="rule")
        self._set(entry_identity={})
        cmds = [self._cmd("W0-C1", "HIGH-compound")]
        self._commit_direct(0, cmds, [self._hit("W0-R1", "W0-C1", "sym", "a.c")], [self._cls("W0-R1", ["n"])],
                            ["sym"])
        data = self._state()
        self.assertEqual((data["entry_identity"]["n"], data["confirmed_files"]["a.c"]["identity"]),
                         ("name-only", "name-only"))

    def test_noise_collapse_files_are_name_only(self):
        self._init("sym", engine="rule")
        cmds = [self._cmd("W0-C1", "HIGH-compound")]
        self._commit_direct(0, cmds, [self._hit("W0-R1", "W0-C1", "sym", "a.c")], [self._cls("W0-R1")], ["sym"],
                            extra={"pre_noisy": ["sym"], "module_files": {"sym": ["a.c", "z.c"]}})
        data = self._state()
        self.assertEqual((data["confirmed_files"]["a.c"]["identity"], data["confirmed_files"]["z.c"]["identity"]),
                         ("resolved", "name-only"))

    # 27. [FILE:…] の関数シンボルの再訪
    def test_file_function_entry_is_revisited_when_summary_grows(self):
        self._init("sym", engine="rule")
        self._set(visited=["f[FILE:a.c]"], symbol_kinds={"f": "function"},
                  symbol_summaries={"f": {"returns": False, "out": [], "globals": [], "side": False, "closure": []}})
        cmds = [self._cmd("W0-C1", "HIGH-compound")]
        cls = [self._cls("W0-R1", ["f[FILE:a.c]"], kinds={"f[FILE:a.c]": "function"}, enc="f",
                         summaries={"f": {"returns": True, "out": [], "globals": [], "side": False, "closure": []}})]
        r = self._commit_direct(0, cmds, [self._hit("W0-R1", "W0-C1", "sym", "a.c")], cls, ["sym"])
        self.assertEqual(r["revisit_count"], 1)
        self.assertIn("f[FILE:a.c]", self._state()["frontier"])

    # 28. merge-frontier --as-seed-globals
    def test_merge_frontier_seed_globals_identity(self):
        self._init("seed_fn", engine="rule")
        summ = self.work / "seed-summaries.json"
        summ.write_text(json.dumps({"targets": [], "summaries": {}, "globals": ["s_x[FILE:a.c]", "g"],
                                    "name_only": ["g"]}), encoding="utf-8")
        self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "s_x[FILE:a.c],g",
                   "--as-seed-globals", "--summaries-file", str(summ)])
        data = self._state()
        self.assertEqual(data["seed_globals"], ["s_x[FILE:a.c]", "g"])
        self.assertIn("s_x[FILE:a.c]", data["frontier"])
        self.assertEqual((data["entry_identity"]["s_x[FILE:a.c]"], data["entry_identity"]["g"]),
                         ("resolved", "name-only"))
        self.assertEqual(data["symbol_kinds"]["s_x"], "variable")
        # シードのグローバル以外の --symbols は既存の値を保つ（無ければ name-only）
        self._run(["merge-frontier", "--path", str(self.state_path), "--symbols", "other"])
        data = self._state()
        self.assertEqual((data["entry_identity"]["seed_fn"], data["entry_identity"]["other"]), ("resolved", "name-only"))

    # 31・33. init・re-discover・extend・switch-engine・import
    def test_entry_identity_across_state_commands(self):
        self._init("sym", engine="slice")
        self.assertEqual(self._state()["entry_identity"], {"sym": "resolved"})
        log = Path(self._state()["discovery_log"])
        self.state_path.unlink()
        (self.work / "bfs-state.md").unlink()
        log.unlink()
        self._run(["init", "--path", str(self.state_path), "--repo-path", str(self.repo), "--discovery-log",
                   str(log), "--symbols", "new2", "--entry-identity", "name-only", "--today", "2026-10-11",
                   "--cr", "CR-1", "--repo", "r", "--slice-engine", "slice"])
        self.assertEqual(self._state()["entry_identity"], {"new2": "name-only"})
        self._set(state="complete", last_completed_wave=0, seed_summary_pending=[])
        self._run(["extend", "--path", str(self.state_path), "--max-wave", "9", "--today", "2026-10-11"])
        self._run(["switch-engine", "--path", str(self.state_path), "--to", "rule", "--today", "2026-10-11"])
        self.assertEqual(self._state()["entry_identity"]["new2"], "name-only")
        r = self._run(["import", "--path", str(self.state_path)])
        self.assertEqual(self._state()["entry_identity"], {})
        self.assertIn("entry_identity", " ".join(r["warnings"]))

    def test_init_marks_file_seed_pending_as_entry(self):
        self._init("dup[FILE:a.c],plain", engine="slice")
        self.assertEqual(self._state()["seed_summary_pending"], ["dup[FILE:a.c]", "plain"])

    # 29. verify-sweep
    def test_verify_sweep_searches_file_entries_in_file(self):
        self._write("a.c", "static int s_x;\n")
        self._write("b.c", "static int s_x;\n")
        conf = {"repo_path": str(self.repo), "backend": "grep", "exclude_patterns": [], "include_extensions": []}
        _raw, files, _lines, _w = mod._preview_seed_hits(["s_x[FILE:a.c]", "s_x"], conf)
        self.assertEqual((sorted(files["s_x[FILE:a.c]"]), sorted(files["s_x"])), (["a.c"], ["a.c", "b.c"]))

    # 36・37. メッセージとログの冒頭
    def test_completed_wave_hint_and_header_has_file_note(self):
        self._init("sym", engine="rule")
        self._set(current_wave=0, last_completed_wave=0)
        code, err = self._run_fail(["search", "--path", str(self.state_path), "--hits-dir", str(self.waves)])
        self.assertEqual(code, 1)
        self.assertIn("run-remove", err)
        note = ("- `name[FILE:src/a.c]` はそのファイルの中でしか参照できない名前（static・無名名前空間・そのファイルで定義した\n"
                "  マクロ、extern の宣言が見えない定義）であり、指定ファイルの中だけを検索する。\n")
        self.assertIn(note, self._log())
        tpl = Path(mod.__file__).resolve().parent.parent / "templates" / "04_specout-discovery-log-template.md"
        self.assertIn(note, tpl.read_text(encoding="utf-8"))



def _have_tree_sitter() -> bool:
    try:
        slice_mod._ts()
        return True
    except slice_mod.EngineUnavailable:
        return False


@unittest.skipUnless(_have_tree_sitter(), "tree-sitter が無い")
class SymbolIdentityEndToEndTest(_SlicerBase):
    def test_static_variable_is_followed_only_in_its_file(self):
        self._write("a.c", "static int s_x;\nint seed_fn(int v) { s_x = v; return v; }\n"
                           "int caller(void) { return seed_fn(1); }\nint reader(void) { return s_x; }\n")
        self._write("b.c", "static int s_x;\nint other(void) { return s_x; }\n")
        self._init("seed_fn", engine="slice")
        self._set(seed_summary_pending=[])
        self._classify_and_commit(self._search())
        data = self._state()
        self.assertIn("s_x[FILE:a.c]", data["frontier"])
        self.assertEqual(data["entry_identity"]["s_x[FILE:a.c]"], "resolved")
        self.assertEqual(data["symbol_kinds"]["s_x"], "variable")
        out = self._search()
        payload = json.loads(Path(out["hits_file"]).read_text(encoding="utf-8"))
        self.assertEqual({h["file"] for h in payload["hits"] if h["symbol"] == "s_x"}, {"a.c"})
        self.assertIn({"kind": "FILE", "scope": "a.c"},
                      [{"kind": c["kind"], "scope": c["scope"]} for c in payload["commands"]])
        self._classify_and_commit(out)
        data = self._state()
        self.assertNotIn("b.c", data["confirmed_files"])
        self.assertEqual(data["confirmed_files"]["a.c"]["identity"], "resolved")
        self.assertEqual(self._verify()["mismatch_waves"], [])


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# 波紋調査の記録（ripple/runs.json）と採用した調査の合算
# ---------------------------------------------------------------------------

class RippleRunsTest(_DocBase):
    def _reg(self):
        return json.loads(self.runs_json.read_text(encoding="utf-8"))

    def _rows(self):
        return {r["run"]: r for r in self._reg()["runs"]}

    def _cmd(self, verb, run, *extra):
        return self._run_exit([verb, "--repo-dir", str(self.out), "--run", run, *extra])

    # run-add
    def test_run_add_validates_name_origin_and_duplicates(self):
        meta = self.root / "meta.json"
        meta.write_text(json.dumps({"approach": "B", "reason": "理由", "seeds": ["hdr.len", "set_len"]}), encoding="utf-8")
        code, out, _e = self._cmd("run-add", "arch-b", "--origin", "architect-agent", "--today", "t",
                                  "--meta-file", str(meta))
        self.assertEqual(code, 0)
        row = self._rows()["arch-b"]
        self.assertEqual((row["origin"], row["approach"], row["seeds"], row["adopted"], row["entry_identity"]),
                         ("architect-agent", "B", ["hdr.len", "set_len"], False, "resolved"))
        self.assertTrue((self.out / "ripple" / "arch-b").is_dir())
        self.assertRegex(row["created"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$")
        for run, origin in (("arch-b", "architect-agent"),      # 重複
                            ("Bad_Name", "human"),              # 書式
                            ("_removed", "human"),              # 予約
                            ("initial-2", "specout"),           # specout は initial だけ
                            ("cross-lib-1", "human"),           # cross- は伝播だけ
                            ("run-1", "architect-agent")):      # arch- 以外は人
            code, _o, err = self._cmd("run-add", run, "--origin", origin, "--today", "t")
            self.assertEqual(code, 1, (run, origin, err))

    def test_run_add_refuses_leftovers(self):
        (self.out / "ripple" / "run-1").mkdir()
        (self.out / "ripple" / "run-1" / "discovery-log.md").write_text("x", encoding="utf-8")
        code, _o, err = self._cmd("run-add", "run-1", "--origin", "human", "--today", "t")
        self.assertEqual(code, 1)
        self.assertIn("残骸", err)

    # run-adopt / run-unadopt
    def test_adopt_requires_complete_and_is_idempotent(self):
        self._cmd("run-add", "run-1", "--origin", "human", "--today", "t")
        code, _o, err = self._cmd("run-adopt", "run-1", "--by", "human", "--today", "t")
        self.assertEqual(code, 1)                       # not-started
        self.assertIn("not-started", err)
        code, out, _e = self._cmd("run-adopt", "initial", "--by", "human", "--today", "t")
        self.assertEqual((code, out["changed"], out["adopted_by"]), (0, False, "specout"))   # 採用者を変えない
        code, out, _e = self._cmd("run-unadopt", "initial", "--by", "human", "--today", "t2")
        self.assertEqual((code, out["changed"]), (0, True))
        self.assertEqual((self._rows()["initial"]["adopted"], self._rows()["initial"]["adopted_by"]), (False, None))
        self.assertFalse(self._cmd("run-unadopt", "initial", "--by", "human", "--today", "t2")[1]["changed"])
        code, out, _e = self._cmd("run-adopt", "initial", "--by", "step5", "--today", "t3")
        self.assertEqual((out["changed"], self._rows()["initial"]["adopted_by"]), (True, "step5"))
        self.assertEqual(self._cmd("run-adopt", "nothing", "--by", "human", "--today", "t")[0], 1)

    # run-remove
    def test_remove_moves_dir_unadopts_and_frees_name(self):
        code, out, _e = self._cmd("run-remove", "initial", "--today", "t")
        self.assertEqual((code, out["was_adopted"]), (0, True))
        self.assertNotIn("initial", self._rows())
        self.assertFalse(self.run_dir.exists())
        moved = list((self.out / "ripple" / "_removed").iterdir())
        self.assertEqual(len(moved), 1)
        self.assertTrue(moved[0].name.startswith("initial-"))
        self.assertTrue((moved[0] / "work" / "bfs-state.json").is_file())
        self.assertEqual(self._cmd("run-add", "initial", "--origin", "specout", "--today", "t")[0], 0)

    def test_remove_cross_run_resets_propagation_log(self):
        self._add_run("cross-lib-1", seeds=["bar"], origin="cross-propagation")
        log = self.root / "cross" / "work" / "cross-propagation-log.json"
        log.parent.mkdir(parents=True)
        log.write_text(json.dumps([
            {"repo": "out", "symbol": "bar", "providing_repo": "lib", "status": "running", "run": "cross-lib-1"},
            {"repo": "out", "symbol": "baz", "providing_repo": "lib", "status": "propagated", "run": "cross-lib-2"}]),
            encoding="utf-8")
        code, out, _e = self._cmd("run-remove", "cross-lib-1", "--today", "t")
        self.assertEqual((code, out["propagation_reset"]), (0, 1))
        items = json.loads(log.read_text(encoding="utf-8"))
        self.assertEqual(items[0], {"repo": "out", "symbol": "bar", "providing_repo": "lib", "status": "deferred"})
        self.assertEqual(items[1]["status"], "propagated")

    # run-list
    def test_run_list_states_and_totals(self):
        self._cmd("run-add", "run-1", "--origin", "human", "--today", "t")
        self._add_run("run-2", seeds=["x"])
        (self.out / "ripple" / "run-2" / "work" / "bfs-state.json").unlink()        # discovery-log だけ残る
        reg = self._reg()
        reg["runs"].append({"run": "run-3", "origin": "human", "adopted": False})   # ディレクトリが無い
        self.runs_json.write_text(json.dumps(reg), encoding="utf-8")
        self._set_state(seed_direct_files=["src/auth/login.c"])
        code, out, _e = self._run_exit(["run-list", "--repo-dir", str(self.out)])
        self.assertEqual(code, 0)
        states = {r["run"]: r["state"] for r in out["runs"]}
        self.assertEqual(states, {"initial": "complete", "run-1": "not-started", "run-2": "missing", "run-3": "missing"})
        initial = next(r for r in out["runs"] if r["run"] == "initial")
        self.assertEqual((initial["confirmed_file_count"], initial["last_completed_wave"], initial["adopted"]),
                         (7, 2, True))
        self.assertEqual((out["adopted_runs"], out["confirmed_file_count"], out["seed_direct_file_count"]),
                         (["initial"], 7, 1))
        self._cmd("run-unadopt", "initial", "--by", "human", "--today", "t")
        out = self._run_exit(["run-list", "--repo-dir", str(self.out)])[1]
        self.assertEqual(next(r for r in out["runs"] if r["run"] == "initial")["unadopted_by"], "human")
        self.assertIsNone(next(r for r in out["runs"] if r["run"] == "run-1")["unadopted_by"])

    def test_run_list_without_registry_is_empty(self):
        shutil.rmtree(self.out / "ripple")
        code, out, _e = self._run_exit(["run-list", "--repo-dir", str(self.out)])
        self.assertEqual((code, out["runs"], out["adopted_runs"]), (0, [], []))
        self.runs_json.parent.mkdir()
        self.runs_json.write_text("{", encoding="utf-8")
        self.assertEqual(self._run_exit(["run-list", "--repo-dir", str(self.out)])[0], 1)

    # finish-record / finish-needed
    def test_finish_needed(self):
        needed = lambda: self._run(["finish-needed", "--repo-dir", str(self.out)])["needed"]  # noqa: E731
        self.assertTrue(needed())                                                     # 記録なし
        self._run(["finish-record", "--repo-dir", str(self.out), "--status", "running", "--today", "t"])
        self.assertTrue(needed())                                                     # 途中で止まった
        self._run(["finish-record", "--repo-dir", str(self.out), "--status", "ok", "--today", "t"])
        self.assertFalse(needed())
        self._cmd("run-unadopt", "initial", "--by", "human", "--today", "t")
        self.assertTrue(needed())                                                     # 採用の集合が違う

    # 合算
    def _second_run(self):
        return self._add_run("run-1", seeds=["extra"], state_updates={
            "confirmed_files": {"src/net/conn.c": {"wave": 0, "confidence": "HIGH", "identity": "resolved"},
                                "src/net/new.c": {"wave": 1, "confidence": "MEDIUM"}},
            "seed_direct_files": ["src/net/conn.c"], "seed_direct_hits": {"src/net/conn.c": 3},
            "truncated": [{"wave": 1, "reason": "hit-budget", "symbol": "big", "hits": 99}]})

    def test_merge_unions_files_and_takes_min_wave_and_resolved(self):
        self._second_run()
        self._cmd("run-adopt", "run-1", "--by", "human", "--today", "t")
        merged = mod._load_adopted(self.out)
        cf = merged["data"]["confirmed_files"]
        self.assertEqual(len(cf), 8)
        self.assertEqual((cf["src/net/conn.c"]["wave"], cf["src/net/conn.c"]["identity"], cf["src/net/conn.c"]["runs"]),
                         (0, "resolved", ["initial", "run-1"]))
        self.assertEqual(cf["src/net/new.c"]["runs"], ["run-1"])
        self.assertEqual(merged["data"]["seed_direct_hits"], {"src/net/conn.c": 3})
        self.assertEqual([t["run"] for t in merged["data"]["truncated"]], ["run-1"])
        self.assertTrue(all(r["line_id"].split(":")[0] in ("initial", "run-1") for r in merged["rows"]))
        # 取り消すと元に戻る（行IDに調査の名前を付けない）
        self._cmd("run-unadopt", "run-1", "--by", "human", "--today", "t")
        merged = mod._load_adopted(self.out)
        self.assertEqual(len(merged["data"]["confirmed_files"]), 7)
        self.assertNotIn(":", merged["rows"][0]["line_id"])

    def test_merge_fails_when_adopted_state_is_missing_or_inconsistent(self):
        self._second_run()
        self._cmd("run-adopt", "run-1", "--by", "human", "--today", "t")
        state = self.out / "ripple" / "run-1" / "work" / "bfs-state.json"
        data = json.loads(state.read_text(encoding="utf-8"))
        state.write_text(json.dumps({**data, "repo": "other"}), encoding="utf-8")
        code, _o, err = self._run_exit(self._merged_ripple_argv())
        self.assertEqual(code, 1)
        self.assertIn("repo", err)
        state.unlink()
        code, _o, err = self._run_exit(self._merged_ripple_argv())
        self.assertEqual(code, 1)
        self.assertIn("unadopt --name run-1", err)

    def test_merged_summary_matches_single_run_summary(self):
        self._write_ledger(AssembleSummaryTest.LEDGER)
        self._auto_assign()
        self._run(self._ripple_argv())
        single = json.loads(self.summary_json.read_text(encoding="utf-8"))
        self._run(self._merged_ripple_argv())
        merged = json.loads(self.summary_json.read_text(encoding="utf-8"))
        self.assertEqual(merged.pop("adopted_runs"), ["initial"])
        for m in merged["modules"]:
            for fe in m["files"]:
                self.assertEqual(fe.pop("runs"), ["initial"])
        self.assertEqual(merged, single)
        self.assertIn("届いた調査", self.summary_md.read_text(encoding="utf-8"))

    def test_merged_summary_without_adopted_runs(self):
        self._write_ledger(AssembleSummaryTest.LEDGER)
        self._unadopt_all()
        self._run(self._merged_ripple_argv())
        summary = json.loads(self.summary_json.read_text(encoding="utf-8"))
        self.assertEqual((summary["modules"], summary["adopted_runs"]), ([], []))
        self.assertIn("採用した波紋調査なし", self.summary_md.read_text(encoding="utf-8"))

    def test_path_and_repo_dir_are_exclusive(self):
        both = ["doc-targets", "--path", str(self.state_path), "--repo-dir", str(self.out)]
        self.assertEqual(self._run_exit(both)[0], 2)
        self.assertEqual(self._run_exit(["doc-targets"])[0], 2)
        self.assertEqual(self._run_exit(["ripple-summary", "--path", str(self.state_path), "--out", "x", "--json", "y"])[0],
                         2)   # --path には --discovery-log が必要

    # doc-targets --repo-dir --auto-assign
    def test_auto_assign_is_rebuilt_from_adopted_runs(self):
        self._second_run()
        self.assign.write_text(json.dumps([{"module": "net", "module_dir": "src/net"},
                                           {"module": "human", "module_dir": "src/util"}]), encoding="utf-8")
        argv = ["doc-targets", "--repo-dir", str(self.out), "--ledger", str(self.ledger),
                "--module-assignments", str(self.assign), "--auto-assign"]
        self._cmd("run-adopt", "run-1", "--by", "human", "--today", "t")
        self._run(argv)
        saved = json.loads(self.assign.read_text(encoding="utf-8"))
        self.assertIn({"module": "root", "module_dir": ".", "auto": True}, saved)
        self.assertIn({"module": "human", "module_dir": "src/util"}, saved)
        # 初回の調査を取り消すと、初回の調査だけが届いたモジュールの自動の割り当ては残らない
        self._cmd("run-unadopt", "initial", "--by", "human", "--today", "t")
        self._run(argv)
        saved = json.loads(self.assign.read_text(encoding="utf-8"))
        self.assertNotIn("root", [x["module"] for x in saved])
        self.assertEqual(saved, [{"module": "net", "module_dir": "src/net"},
                                     {"module": "human", "module_dir": "src/util"}])

    def test_run_outputs_do_not_touch_repo_assignments(self):
        before = self.assign.read_text(encoding="utf-8")
        run_assign = self.run_work / "module-assignments.json"
        shutil.copy(self.assign, run_assign)
        self._run(["doc-targets", "--path", str(self.state_path), "--module-assignments", str(run_assign),
                   "--auto-assign"])
        self.assertEqual(self.assign.read_text(encoding="utf-8"), before)
        self.assertNotEqual(run_assign.read_text(encoding="utf-8"), before)

    # funcmap-counts --repo-dir
    def test_funcmap_counts_repo_dir(self):
        rdir = self._second_run()
        log = rdir / "discovery-log.md"
        text = log.read_text(encoding="utf-8").replace(
            "| W0-R2 | W0-C1 | `session_start` | src/auth/login.c |", "| W0-R2 | W0-C1 | `session_start` | src/x/other.c |")
        text = text.replace("| W0-R1 | W0-C1 | `session_start` | src/auth/session.c | 1 | `int session_start(const char *user) {` | `session_start` | slice(none=self-def) | HIGH | — | seed(session_start) |\n", "")
        log.write_text(text, encoding="utf-8")
        self._add_run("run-2", seeds=["y"])
        (self.out / "ripple" / "run-2" / "discovery-log.md").write_text("# Discovery Log\n", encoding="utf-8")
        for run in ("run-1", "run-2"):
            self._cmd("run-adopt", run, "--by", "human", "--today", "t")
        out_md = self.work / "counts.md"
        r = self._run(["funcmap-counts", "--repo-dir", str(self.out), "--out", str(out_md)])
        self.assertEqual([x["run"] for x in r["skipped_runs"]], ["run-2"])
        md = out_md.read_text(encoding="utf-8")
        self.assertIn("| `session_start` | 2 | `src/auth/login.c`, `src/auth/session.c` |", md)
        self.assertIn("## 値の食い違い", md)
        self.assertIn("| `session_start` | initial: 2, run-1: 1 |", md)
        self.assertIn("- 数えられなかった調査: run-2", md)
        self._unadopt_all()
        self._cmd("run-adopt", "run-2", "--by", "human", "--today", "t")
        self.assertEqual(self._run_exit(["funcmap-counts", "--repo-dir", str(self.out), "--out", str(out_md)])[0], 1)
        self.assertFalse(out_md.exists())

    # assemble-spo --repo-dir
    def test_assemble_without_adopted_runs_uses_no_adopted_texts(self):
        self._write_ledger(AssembleSummaryTest.LEDGER)
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2]), ("net", DRAFT_NET.split("\n", 2)[2])])
        r = self._assemble_without_adopted()
        self.assertEqual((r["ripple"], r["adopted_runs"]), (False, []))
        spo = self._spo()
        self.assertIn("／波紋調査: 採用なし（人の判断） |", spo)
        self.assertIn(f"| {mod.NO_ADOPTED_TEXT} |", spo)
        self.assertIn(mod.NO_ADOPTED_NOTE, spo[spo.index("### 5.0"):spo.index("### 5.1")])
        self.assertIn(mod.NO_ADOPTED_NOTE, spo[spo.index("### 5.2"):spo.index("### 5.3")])
        self.assertIn("### 2.A.9 波紋調査の結果\n" + mod.WRITER_SCRIPT_COMMENT + "\n\n" + mod.NO_ADOPTED_TEXT, spo)
        self.assertNotIn(f"| {mod.NO_RIPPLE_TEXT} |", spo)
        self.assertNotIn(mod.NO_RIPPLE_NOTE, spo)

    def test_assemble_merges_two_runs_and_notes_missing_sweeps(self):
        self._write_ledger(AssembleSummaryTest.LEDGER)
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2]), ("net", DRAFT_NET.split("\n", 2)[2])])
        self._second_run()
        self._cmd("run-adopt", "run-1", "--by", "human", "--today", "t")
        (self.run_work / "verify-sweep.json").write_text(json.dumps({"ok": True, "unrecorded_files": []}),
                                                         encoding="utf-8")
        self._run(["doc-targets", "--repo-dir", str(self.out), "--ledger", str(self.ledger),
                   "--module-assignments", str(self.assign), "--auto-assign"])
        self._run(self._merged_ripple_argv())
        r = self._run(self._assemble_argv())
        self.assertEqual(r["adopted_runs"], ["initial", "run-1"])
        spo = self._spo()
        sec1x = spo[spo.index("### 1.x"):spo.index("## 2.")]
        self.assertIn("| initial | 工程4a の初回 |", sec1x)
        self.assertIn("| run-1 | 人 | `extra` | 3 ／ 6 | 10000 ／ 160 | hit-budget: 1 | `big`（99） |", sec1x)
        self.assertIn("採用 2 件", spo)
        sec9 = spo[spo.index("## 9."):spo.index("## 10.")]
        self.assertIn("検証スイープ未実施（run-1）", sec9)
        self.assertNotIn("検証スイープ未実施（initial）", sec9)
        self.assertIn("〔initial〕", sec9)

    def test_assemble_requires_merged_summary_and_repo_args(self):
        code, _o, err = self._run_exit(self._assemble_argv())
        self.assertEqual(code, 1)
        self.assertIn("ripple-summary --repo-dir", err)
        argv = [a for a in self._assemble_argv() if a not in ("--repo-path", str(self.repo))]
        self.assertEqual(self._run_exit(argv)[0], 2)

    def test_layout_only_uses_merged_seed_direct(self):
        self._write_ledger(AssembleSummaryTest.LEDGER)
        self._second_run()
        self._cmd("run-adopt", "run-1", "--by", "human", "--today", "t")
        self._run(["doc-targets", "--repo-dir", str(self.out), "--ledger", str(self.ledger),
                   "--module-assignments", str(self.assign), "--auto-assign"])
        r = self._run(["assemble-spo", *self._common_argv(10), "--layout-only", "--only", "seed-direct",
                       "--max-files", "20"])
        self.assertEqual(sorted(r["file_outputs"]), [])          # conn.c は台帳にある
        self._set_state(seed_direct_files=["src/auth/session.c"])
        r = self._run(["assemble-spo", *self._common_argv(10), "--layout-only", "--only", "seed-direct",
                       "--max-files", "20"])
        self.assertEqual(sorted(r["file_outputs"]), ["src/auth/session.c"])

    # ripple-digest
    def _digest(self, summary, run="arch-b"):
        self.summary_json.write_text(json.dumps(summary), encoding="utf-8")
        out = self.root / "digest.md"
        self._run(["ripple-digest", "--path", str(self.state_path), "--summary-json", str(self.summary_json),
                   "--runs", str(self.runs_json), "--run", run, "--ledger-asof", "2026-10-14 09:41", "--out", str(out)])
        return out.read_text(encoding="utf-8")

    def test_ripple_digest_caps_rows_and_shows_run_info(self):
        meta = self.root / "meta.json"
        meta.write_text(json.dumps({"approach": "B", "reason": "長さの意味を変える", "seeds": ["hdr.len"]}),
                        encoding="utf-8")
        self._cmd("run-add", "arch-b", "--origin", "architect-agent", "--today", "t", "--meta-file", str(meta))
        mods = [{"name": f"m{k:02d}", "confirmed_count": 2, "name_only_count": 1, "min_wave": 1,
                 "seed_direct_count": 0, "prelim_gap_count": 0, "documented": k == 0, "path": "p"} for k in range(31)]
        text = self._digest({"confirmed_file_count": 62, "modules": mods})
        self.assertIn("# 波紋調査の要約 — arch-b / svc", text)
        self.assertIn("> 採用: なし（SPO に入っていない）", text)
        self.assertIn("| 名前・由来 | arch-b・方式検討エージェント（案B） |", text)
        self.assertIn("| 理由 | 長さの意味を変える |", text)
        self.assertIn("| シード | `hdr.len` |", text)
        self.assertIn("| 確定ファイル数 | 62（うち名前の一致のみ 31） |", text)
        self.assertIn("| 「資料」列の時点 | 2026-10-14 09:41（台帳の更新日時） |", text)
        table = [ln for ln in text.split("## 影響する機能（モジュール）一覧")[1].split("\n") if ln.startswith("| m")]
        self.assertEqual(len(table), 30)
        self.assertIn("| m00 | 2 | 1 | 1 | — | あり | p |", text)
        self.assertIn("| ほか 1 モジュール・2 ファイル（`ripple-summary.md` を参照） |", text)
        out = self.root / "digest2.md"
        self._run(["ripple-digest", "--path", str(self.state_path), "--summary-json", str(self.summary_json),
                   "--runs", str(self.runs_json), "--run", "initial", "--ledger", str(self.ledger), "--out", str(out)])
        self.assertRegex(out.read_text(encoding="utf-8"), r"\| 「資料」列の時点 \| \d{4}-\d\d-\d\d \d\d:\d\d（台帳の更新日時） \|")
        text = self._digest({"modules": []}, run="initial")
        self.assertIn("> 採用: あり（SPO に反映済み）", text)
        self.assertIn("| 名前・由来 | initial・工程4a の初回 |", text)


class InitEntryIdentityTest(_PrelimTestBase):
    def test_name_only_seeds_and_conflict_with_seed_candidates(self):
        base = ["init", "--path", str(self.state_path), "--repo-path", str(self.repo),
                "--discovery-log", str(self.root / "discovery-log.md"), "--today", "t", "--cr", "CR-1", "--repo", "r"]
        self._run(base + ["--symbols", "a,b", "--entry-identity", "name-only"])
        self.assertEqual(json.loads(self.state_path.read_text(encoding="utf-8"))["entry_identity"],
                         {"a": "name-only", "b": "name-only"})
        args = mod.build_parser().parse_args(base + ["--seed-candidates", "x.md", "--entry-identity", "name-only"])
        with self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
            args.func(args)
        self.assertEqual(cm.exception.code, 2)


# -- 依頼調査（/xddp-investigate document・suggest）-------------------------------------------------

class _RequestBase(_DocBase):
    def _ledger(self, rows):
        """rows: (ファイルパス, モジュール, モジュールディレクトリ, 工程[, 関係する振る舞い]) のタプル列。"""
        lines = ["# 文書化済みファイル台帳 — CR-2026-970 / svc", "",
                 "| ファイルパス | モジュール | モジュールディレクトリ | 工程 | 関係する振る舞い（CRS） |", "|---|---|---|---|---|"]
        for r in rows:
            f, m, d, ph = r[:4]
            beh = r[4] if len(r) > 4 else f"振る舞い {f}"
            lines.append(f"| {f} | {m} | {d} | {ph} | {beh} |")
        self.ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _file(self, rel, content="int f(void) { return 0; }\n"):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")

    def _req_argv(self, targets, append=None, exclude="tests/", include="", soft=20, batch=20):
        tf = self.work / "doc-request-targets.txt"
        tf.write_text("\n".join(targets) + "\n", encoding="utf-8")
        argv = ["doc-request", "--repo-dir", str(self.out), "--repo-path", str(self.repo), "--targets-file", str(tf),
                "--exclude", exclude, "--include-ext", include, "--soft-limit", str(soft), "--batch-size", str(batch),
                "--out", str(self.work / "doc-request-files.json")]
        if append is not None:
            af = self.work / "doc-request-append.txt"
            af.write_text("\n".join(append) + "\n", encoding="utf-8")
            argv += ["--append-file", str(af)]
        return argv

    def _req(self, targets, **kw):
        r = self._run(self._req_argv(targets, **kw))
        return r, json.loads((self.work / "doc-request-files.json").read_text(encoding="utf-8"))

    def _req_layout_argv(self, max_files=10):
        return ["assemble-spo", *self._common_argv(max_files), "--layout-only", "--only", "requested",
                "--files-file", str(self.work / "doc-request-files.json")]


class DocRequestTest(_RequestBase):
    def test_expands_files_directories_and_module_names(self):
        self.assign.write_text(json.dumps([{"module": "net", "module_dir": "src/net"},
                                           {"module": "netsub", "module_dir": "src/net/sub"}]), encoding="utf-8")
        before = self.assign.read_text(encoding="utf-8")
        self._file("src/net/blob.bin", b"\x00\x01binary")
        self._file("src/tests/t.c")
        self._file("docs/readme.txt", "x\n")
        r, out = self._req(["net", "src/util", "main.c", "src/auth/login.c", "nope", "docs"])
        files = {f["file"]: f for f in out["files"]}
        # モジュール名の展開は配下の別のモジュール（netsub）のファイルを含まない
        self.assertIn("src/net/conn.c", files)
        self.assertNotIn("src/net/sub/x.c", files)
        self.assertEqual(files["src/net/conn.c"]["module"], "net")
        self.assertEqual(files["src/util/helper.c"]["module"], "src-util")
        self.assertEqual(files["main.c"]["module"], "root")
        self.assertEqual(files["docs/readme.txt"]["module"], "docs")
        self.assertEqual(r["skipped_binary"], ["src/net/blob.bin"])
        self.assertEqual(r["not_found"], ["nope"])
        self.assertEqual(r["already_documented"], [{"file": "src/auth/login.c", "module": "auth", "appended_on": ""}])
        self.assertNotIn("src/auth/login.c", files)
        self.assertEqual(r["ext_counts"], {".c": 4, ".txt": 1})
        self.assertFalse(r["over_soft_limit"])
        # module-assignments.json は書かない
        self.assertEqual(self.assign.read_text(encoding="utf-8"), before)
        # 並び: 採用した調査の確定ファイル → それ以外
        self.assertEqual([f["file"] for f in out["files"]][-1], "docs/readme.txt")
        self.assertTrue(files["main.c"]["confirmed"])
        self.assertFalse(files["docs/readme.txt"]["confirmed"])

    def test_excluded_only_below_named_directory(self):
        self._file("src/tests/t.c")
        r, out = self._req(["src"])
        self.assertIn("src/tests/t.c", r["excluded"])
        self.assertNotIn("src/tests/t.c", {f["file"] for f in out["files"]})
        self.assertEqual(r["pattern_overridden"], [])

    def test_named_target_matching_exclude_pattern_is_overridden(self):
        self._file("src/tests/a.c")
        self._file("src/tests/fixtures/b.c")
        self._file("src/tests/unit/c.c")
        self._file("gen/x.pb.c")
        r, out = self._req(["src/tests", "tests/test_login.c"], exclude="tests/,fixtures/,*.pb.c")
        names = {f["file"] for f in out["files"]}
        # 名指ししたディレクトリには一致したパターン（tests/）だけを適用しない。配下の fixtures/ は今までどおり効く
        self.assertEqual(r["pattern_overridden"], ["src/tests/a.c", "src/tests/unit/c.c", "tests/test_login.c"])
        self.assertIn("src/tests/fixtures/b.c", r["excluded"])
        self.assertNotIn("src/tests/fixtures/b.c", names)
        # 名指ししたディレクトリが除外のディレクトリの配下（src/tests/unit）でも対象になる
        r2, _out = self._req(["src/tests/unit"], exclude="tests/")
        self.assertEqual(r2["pattern_overridden"], ["src/tests/unit/c.c"])
        # ファイル名のパターンはディレクトリに当てはめない。配下の *.pb.c は excluded、名指ししたファイルは pattern_overridden
        r3, _out = self._req(["gen"], exclude="*.pb.c")
        self.assertEqual((r3["pattern_overridden"], r3["excluded"]), ([], ["gen/x.pb.c"]))
        r4, _out = self._req(["gen/x.pb.c"], exclude="*.pb.c")
        self.assertEqual(r4["pattern_overridden"], ["gen/x.pb.c"])

    def test_include_ext_applies_to_directories_not_named_files(self):
        self._file("src/net/notes.txt", "x\n")
        r, out = self._req(["src/net", "src/net/notes.txt"], include=".c")
        self.assertIn("src/net/notes.txt", {f["file"] for f in out["files"]})
        r, out = self._req(["src/net"], include=".c")
        self.assertNotIn("src/net/notes.txt", {f["file"] for f in out["files"]})
        self.assertIn("src/net/notes.txt", r["skipped_ext"])

    def test_concerns_name_only_and_gap_reviewed(self):
        self._set_state(confirmed_files={**self._state()["confirmed_files"],
                                         "src/net/conn.c": {"wave": 1, "confidence": "HIGH", "identity": "resolved"}})
        self._write_reviewed([("src/net/other.c", "別物")])
        r, out = self._req(["src/net/conn.c", "src/net/other.c", "src/net/sub/x.c"])
        concerns = {c["file"]: c for c in r["concerns"]}
        self.assertNotIn("src/net/conn.c", concerns)
        self.assertEqual(concerns["src/net/other.c"], {"file": "src/net/other.c", "name_only": True,
                                                       "gap_reviewed": True, "gap_reason": "別物"})
        self.assertEqual(concerns["src/net/sub/x.c"], {"file": "src/net/sub/x.c", "name_only": True})
        files = {f["file"]: f for f in out["files"]}
        self.assertTrue(files["src/net/other.c"]["gap_reviewed"])
        # 並び: resolved → 名前の一致のみ
        self.assertEqual(out["files"][0]["file"], "src/net/conn.c")

    def test_new_module_name_collision_fails_loud(self):
        self._file("a/b-c/x.c")
        self._file("a-b/c/y.c")
        before = self.assign.read_text(encoding="utf-8")
        code, _o, err = self._run_exit(self._req_argv(["a/b-c/x.c", "a-b/c/y.c"]))
        self.assertEqual(code, 1)
        self.assertIn("a-b-c", err)
        self.assertEqual(self.assign.read_text(encoding="utf-8"), before)

    def test_batches_soft_limit_and_append(self):
        r, out = self._req(["net", "src/util"], batch=2, soft=3, append=["src/auth/login.c"])
        self.assertTrue(r["over_soft_limit"])
        self.assertEqual(r["file_count"], 5)
        self.assertEqual([(b["mode"], b["module"], len(b["files"])) for b in out["batches"]],
                         [("new", "net", 2), ("new", "net", 1), ("new", "src-util", 1), ("append", "auth", 1)])
        files = {f["file"]: f for f in out["files"]}
        self.assertEqual((files["src/auth/login.c"]["mode"], files["src/auth/login.c"]["module"],
                          files["src/auth/login.c"]["module_dir"]), ("append", "auth", "src/auth"))
        self.assertEqual(r["already_documented"], [])
        # 台帳に無いファイルの追記は exit 1
        code, _o, err = self._run_exit(self._req_argv(["net"], append=["src/net/conn.c"]))
        self.assertEqual(code, 1)
        self.assertIn("src/net/conn.c", err)

    def test_works_without_adopted_runs_and_stops_while_finishing(self):
        self._unadopt_all()
        r, out = self._req(["src/net/conn.c"])
        self.assertEqual((r["file_count"], out["files"][0]["confirmed"]), (1, False))
        (self.work / "specout-finish.json").write_text('{"status": "running", "date": "t"}', encoding="utf-8")
        code, _o, err = self._run_exit(self._req_argv(["src/net/conn.c"]))
        self.assertEqual(code, 1)
        self.assertIn("SPO の仕上げ", err)

    def test_outside_repo_fails(self):
        code, _o, _e = self._run_exit(self._req_argv(["../etc/passwd"]))
        self.assertEqual(code, 1)

    def test_already_documented_shows_appended_on(self):
        (self.work / "doc-request-log.md").write_text("\n".join(mod.DOC_REQUEST_LOG_HEAD + [
            "| 2026-10-05 | 追記 | src/auth/login.c | — |", "| 2026-10-07 | 追記 | src/auth/login.c | エラー時 |",
            "| 2026-10-08 | 新規 | src/auth/login.c | — |"]) + "\n", encoding="utf-8")
        r, _out = self._req(["src/auth/login.c"])
        self.assertEqual(r["already_documented"][0]["appended_on"], "2026-10-07")


class DocSuggestTest(_RequestBase):
    def _suggest(self, exclude="tests/"):
        return self._run(["doc-suggest", "--repo-dir", str(self.out), "--exclude", exclude])

    def _resolve(self, *files):
        cf = self._state()["confirmed_files"]
        for f in files:
            cf[f] = {**cf[f], "identity": "resolved"}
        self._set_state(confirmed_files=cf)

    def test_order_and_documented_modules(self):
        self._resolve("src/net/conn.c", "src/net/other.c", "src/util/helper.c")
        self._set_state(seed_direct_files=["src/util/helper.c"])
        r = self._suggest()
        names = [c["module"] for c in r["candidates"]]
        # ⚠️（シードの直接参照で資料の無いファイル）が先、名前の一致のみが全部のモジュール（root）は最後
        self.assertEqual(names, ["src-util", "net", "root"])
        net = r["candidates"][1]
        self.assertEqual((net["confirmed_count"], net["name_only_count"], net["min_wave"], net["runs"]),
                         (3, 1, 1, ["initial"]))
        self.assertEqual(r["candidates"][0]["seed_direct_gap"], 1)
        # 依頼調査で資料にしたモジュールは候補から消える（ripple-summary.json を読まない）
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ"),
                      ("src/net/conn.c", "net", "src/net", "依頼調査")])
        self.assertEqual([c["module"] for c in self._suggest()["candidates"]], ["src-util", "root"])

    def test_requested_exclude_pattern_rows_do_not_count_as_documented(self):
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ"),
                      ("src/net/tests/t.c", "net", "src/net", "依頼調査")])
        self.assertIn("net", [c["module"] for c in self._suggest()["candidates"]])
        # 工程 下調べ の行のテストコードは対象にしない（資料ありのまま）
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ"),
                      ("src/net/tests/t.c", "net", "src/net", "下調べ")])
        self.assertNotIn("net", [c["module"] for c in self._suggest()["candidates"]])

    def test_no_adopted_runs(self):
        self._unadopt_all()
        self.assertEqual(self._suggest(), {"ok": True, "candidates": [], "reason": "no-adopted-runs"})


class RequestedLayoutTest(_RequestBase):
    def test_usage_errors(self):
        self._req(["src/net/conn.c"])
        ff = ["--files-file", str(self.work / "doc-request-files.json")]
        base = ["assemble-spo", *self._common_argv(10), "--layout-only"]
        for argv in (base + ["--only", "requested"],                                   # --files-file なし
                     base + ["--only", "seed-direct", "--max-files", "3", *ff],        # seed-direct に --files-file
                     base + ["--only", "requested", "--max-files", "3", *ff]):         # requested に --max-files
            with self.subTest(argv=argv[len(base):]):
                self.assertEqual(self._run_exit(argv)[0], 2)

    def test_new_module_pair_and_integrated_layout(self):
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2])])
        self._req(["src/util/helper.c"])
        r = self._run(self._req_layout_argv())
        self.assertEqual(r["layout"], "integrated")
        self.assertEqual(r["file_outputs"], {"src/util/helper.c": {
            "module": "src-util", "output_file": str(self.work / "module-drafts" / "src-util.md")}})
        # 抜き出しは対象のモジュールだけ（auth は対象でないため下書きを作らない）
        self.assertFalse((self.work / "module-drafts" / "auth.md").exists())
        self.assertEqual(r["module_file_counts"], {"auth": 1, "src-util": 1})
        self.assertFalse(self.assign.read_text(encoding="utf-8").count("src-util"))

    def test_threshold_moves_integrated_to_split(self):
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2])])
        self._req(["src/net/conn.c", "src/net/other.c"])
        r = self._run(self._req_layout_argv(max_files=2))
        self.assertEqual((r["layout"], r["moved_to_split"]), ("split", True))
        self.assertTrue((self.out / "modules" / "auth-spo.md").is_file())
        self.assertEqual(r["file_outputs"]["src/net/conn.c"]["output_file"], str(self.out / "modules" / "net-spo.md"))
        self.assertNotIn("## 2.A. auth", self._spo())

    def test_collision_with_current_pairs_fails(self):
        self._req(["src/util/helper.c"])
        self.assign.write_text(json.dumps([{"module": "net", "module_dir": "src/net"},
                                           {"module": "util", "module_dir": "src/util"}]), encoding="utf-8")
        code, _o, _e = self._run_exit(self._req_layout_argv())
        self.assertEqual(code, 1)


class DraftRecordTest(_RequestBase):
    """統合パスの下書き（work/module-drafts）の抜き出し・移し替え・差し込みと抜き出し元の節の記録。"""

    def setUp(self):
        super().setUp()
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2])])
        self.drafts = self.work / "module-drafts"

    def _record(self):
        return json.loads((self.drafts / mod.DRAFT_SOURCE_RECORD).read_text(encoding="utf-8"))

    def test_extract_records_hash_and_insert_removes_record(self):
        self._req(["src/auth/session.c"])
        self._run(self._req_layout_argv())
        self.assertEqual(list(self._record()), ["auth"])
        draft = (self.drafts / "auth.md").read_text(encoding="utf-8")
        self.assertNotIn("sha256", draft)
        (self.drafts / "auth.md").write_text(draft + "\n### 2.A.2 主要な処理・ロジック（追記）\n\nセッション。\n",
                                             encoding="utf-8")
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ"),
                      ("src/auth/session.c", "auth", "src/auth", "依頼調査")])
        self._make_summary(merged=True)
        self._run(self._assemble_argv())
        self.assertIn("セッション。", self._spo())
        self.assertFalse(self.drafts.exists())

    def test_section_edited_after_extraction_stops_insert(self):
        self._req(["src/auth/session.c"])
        self._run(self._req_layout_argv())
        spo = self._spo().replace("ログイン判定の流れ。", "人が直した流れ。")
        (self.out / "SPO-CR-2026-970.md").write_text(spo, encoding="utf-8")
        self._make_summary(merged=True)
        code, _o, err = self._run_exit(self._assemble_argv())
        self.assertEqual(code, 1)
        self.assertIn("`auth` の §2.A… が下書きの抜き出しの後に変わっています", err)
        self.assertEqual(self._spo(), spo)
        self.assertTrue((self.drafts / "auth.md").is_file())

    def test_section_edited_stops_move_without_writing(self):
        self._req(["src/auth/session.c"])
        self._run(self._req_layout_argv())
        spo = self._spo().replace("ログイン判定の流れ。", "人が直した流れ。")
        (self.out / "SPO-CR-2026-970.md").write_text(spo, encoding="utf-8")
        drafts_before = sorted(p.name for p in self.drafts.iterdir())
        self._req(["src/net/conn.c", "src/net/other.c"])
        code, _o, _e = self._run_exit(self._req_layout_argv(max_files=2))
        self.assertEqual(code, 1)
        self.assertFalse((self.out / "modules").exists())
        self.assertEqual(self._spo(), spo)
        self.assertEqual(sorted(p.name for p in self.drafts.iterdir()), drafts_before)

    def test_move_uses_drafts_including_new_module_and_discards_unrecorded(self):
        # 1回目の依頼（session.c は auth、helper.c は新しいモジュール src-util）。エージェントが下書きに書いた
        self._req(["src/auth/session.c", "src/util/helper.c", "main.c"])
        self._run(self._req_layout_argv())
        (self.drafts / "auth.md").write_text((self.drafts / "auth.md").read_text(encoding="utf-8")
                                             + "\n### 2.A.10 追加調査（依頼調査）\n\n#### src/auth/login.c（2026-10-05。観点: —）\n\n追記した観察。\n",
                                             encoding="utf-8")
        self.drafts.joinpath("src-util.md").write_text("## 2.A. src-util\n\n### 2.A.1 処理フロー\n\nヘルパ。\n",
                                                        encoding="utf-8")
        self.drafts.joinpath("root.md").write_text("## 2.A. root\n\n### 2.A.1 処理フロー\n\n途中。\n", encoding="utf-8")
        # 台帳には src-util の行だけがある（root はエージェントが台帳を書く前に止まった）
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ"),
                      ("src/auth/session.c", "auth", "src/auth", "依頼調査"),
                      ("src/util/helper.c", "src-util", "src/util", "依頼調査")])
        # 2回目の依頼で閾値を超えて分割パスへ移る
        self._req(["src/net/conn.c"])
        r = self._run(self._req_layout_argv(max_files=2))
        self.assertTrue(r["moved_to_split"])
        self.assertEqual(r["discarded_drafts"], ["root"])
        auth = (self.out / "modules" / "auth-spo.md").read_text(encoding="utf-8")
        self.assertIn("ログイン判定の流れ。", auth)
        # 追記の節は §2 の末尾の ### 2.7 になり、§4 に入らない
        self.assertIn("### 2.7 追加調査（依頼調査）", auth)
        self.assertLess(auth.index("### 2.7 追加調査（依頼調査）"), auth.index("## 3. "))
        self.assertIn("追記した観察。", auth[:auth.index("## 3. ")])
        self.assertIn("ヘルパ。", (self.out / "modules" / "src-util-spo.md").read_text(encoding="utf-8"))
        self.assertFalse((self.out / "modules" / "root-spo.md").exists())
        self.assertFalse(self.drafts.exists())

    def test_additional_prelim_flow_unchanged(self):
        self._set_state(seed_direct_files=["src/auth/session.c"])
        self._run(["doc-targets", "--repo-dir", str(self.out), "--repo-path", str(self.repo), "--ledger", str(self.ledger),
                   "--module-assignments", str(self.assign), "--auto-assign"])
        self._run(self._layout_argv())
        self.assertEqual(list(self._record()), ["auth"])
        self._run(self._merged_ripple_argv())
        self._run(self._assemble_argv())
        self.assertFalse(self.drafts.exists())
        self.assertIn("ログイン判定の流れ。", self._spo())

    def test_insert_orders_ripple_before_append_section(self):
        body = DRAFT_AUTH.split("\n", 2)[2] + "\n### 2.A.10 追加調査（依頼調査）\n\n#### src/auth/login.c（2026-10-05。観点: —）\n\n追記。\n"
        self._write_prelim_spo([("auth", body), ("net", DRAFT_NET.split("\n", 2)[2])])
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ"), ("src/net/conn.c", "net", "src/net", "下調べ")])
        self._make_summary(merged=True)
        self._run(self._assemble_argv())
        self._run(self._assemble_argv())   # 再実行で節が重複しない
        spo = self._spo()
        sec = spo[spo.index("## 2.A. auth"):spo.index("## 2.B. net")]
        self.assertLess(sec.index("### 2.A.8"), sec.index("### 2.A.9 波紋調査の結果"))
        self.assertLess(sec.index("### 2.A.9 波紋調査の結果"), sec.index("### 2.A.10 追加調査（依頼調査）"))
        self.assertEqual(spo.count("### 2.A.10 追加調査（依頼調査）"), 1)
        self.assertEqual(spo.count("### 2.A.9 波紋調査の結果"), 1)
        self.assertNotIn("2.A.9 追加調査", spo)
        self.assertEqual(mod._normalize_draft("## 2.B. auth\n\n### 2.B.10 追加調査（依頼調査）\n\nx\n", "C"),
                         ["### 2.C.10 追加調査（依頼調査）", "", "x"])


class AppendSectionSplitTest(_RequestBase):
    def test_subdirectory_split_routes_append_blocks(self):
        self._ledger([("src/net/conn.c", "net", "src/net", "下調べ"), ("src/net/other.c", "net", "src/net", "下調べ")])
        (self.out / "modules").mkdir()
        text = (DOC_FIXTURE / "modules" / "net-spo.md").read_text(encoding="utf-8").replace(
            "\n---\n\n## 5. 変更履歴",
            "\n### 2.7 追加調査（依頼調査）\n\n#### src/net/conn.c（2026-10-05。観点: —）\n\n| a | b |\n|---|---|\n"
            "| src/net/sub/x.c | 参照 |\n\n#### src/net/sub/x.c（2026-10-05。観点: —）\n\nサブの観察。\n\n---\n\n## 5. 変更履歴")
        (self.out / "modules" / "net-spo.md").write_text(text, encoding="utf-8")
        self._set_state(seed_direct_files=["src/net/sub/x.c"])
        self._auto_assign()
        self._run(self._layout_argv(max_files=2))
        root = (self.out / "modules" / "net" / "root-spo.md").read_text(encoding="utf-8")
        sub = (self.out / "modules" / "net" / "sub-spo.md").read_text(encoding="utf-8")
        self.assertIn("#### src/net/conn.c", root)
        # 追記の節の中の表は振り分けない（conn.c の節の表の行は x.c を含んでも root に残る）
        self.assertIn("| src/net/sub/x.c | 参照 |", root)
        self.assertNotIn("サブの観察。", root)
        self.assertIn("サブの観察。", sub)
        self.assertNotIn("#### src/net/conn.c", sub)
        self.assertEqual(sub.count("### 2.7 追加調査（依頼調査）"), 1)


class RequestedSummaryTest(_RequestBase):
    def _assemble(self, ripple=True, exclude="tests/"):
        if not ripple:
            self._unadopt_all()
        self._make_summary(merged=True)
        return self._run(self._assemble_argv(extra=["--exclude", exclude]))

    def _section(self, start, end):
        spo = self._spo()
        return spo[spo.index(start):spo.index(end)]

    def test_zero_adopted_excludes_unconfirmed_and_override_rows(self):
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ", "ログイン判定"),
                      ("src/net/conn.c", "net", "src/net", "依頼調査", "接続"),
                      ("src/util/helper.c", "src-util", "src/util", "依頼調査", "確認できず"),
                      ("tests/test_login.c", "tests", "tests", "依頼調査", "ログイン判定")])
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2]), ("net", DRAFT_NET.split("\n", 2)[2])])
        metrics = self.root / "metrics.jsonl"
        self._unadopt_all()
        self._make_summary(merged=True)
        r = self._run(self._assemble_argv(extra=["--exclude", "tests/", "--metrics", str(metrics)]))
        self.assertEqual(r["pattern_override_files"], ["tests/test_login.c"])
        spo = self._spo()
        self.assertIn("| 調査範囲 | 下調べ: 4 モジュール・4 ファイル（うち追加下調べ 0・依頼調査 3）／", spo)
        self.assertIn("| 検出モジュール数 | 2 モジュール |", spo)
        sec50 = self._section("### 5.0", "### 5.1")
        self.assertIn("| net | 1 | — | — | — | あり | — |", sec50)
        self.assertNotIn("src-util", sec50)
        self.assertNotIn("| tests |", sec50)
        sec51 = self._section("### 5.1", "### 5.2")
        self.assertIn("| src/net/conn.c | （モジュール資料を参照） | 依頼調査で特定 | net | 接続 |", sec51)
        self.assertIn("| src/auth/login.c | （モジュール資料を参照） | 下調べで特定 |", sec51)
        self.assertNotIn("helper.c", sec51)
        self.assertNotIn("test_login.c", sec51)
        self.assertNotIn("test_login.c", self._section("### 5.5", "### 5.6"))
        sec8 = self._section("## 8.", "## 9.")
        self.assertIn("（依頼調査: CRS との関係を確認できないファイル 1 件。台帳を参照）", sec8)
        self.assertIn("（除外パターンの例外〔人の依頼〕1 件）", sec8)
        self.assertIn("| src-util |", sec8)
        line = json.loads(metrics.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(line["requested_file_count"], 3)

    def test_ripple_path_module_count_excludes_unreached_unconfirmed(self):
        self._file("lib/far.c")
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ"),
                      ("lib/far.c", "lib", "lib", "依頼調査", "確認できず"),
                      ("src/util/helper.c", "src-util", "src/util", "依頼調査", "確認できず")])
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2])])
        self._assemble()
        # 波紋調査が届いた src-util は要約のモジュールとして数え、届いていない lib は数えない（auth・net・root・src-util）
        self.assertIn("| 検出モジュール数 | 4 モジュール |", self._spo())
        self.assertIn("| lib | lib |", self._section("## 8.", "## 9."))

    def test_scope_text_unchanged_without_requested_rows(self):
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ")])
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2])])
        self._assemble()
        self.assertIn("（うち追加下調べ 0）／", self._spo())
        self.assertNotIn("依頼調査 0", self._spo())

    def test_ledger_requested_phase_not_counted_in_additional_cap(self):
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ"),
                      ("src/net/conn.c", "net", "src/net", "依頼調査")])
        self._set_state(seed_direct_files=["src/auth/session.c", "src/net/other.c"])
        r = self._run(["doc-targets", "--repo-dir", str(self.out), "--repo-path", str(self.repo), "--ledger", str(self.ledger),
                       "--module-assignments", str(self.assign), "--gap-reviewed", str(self.gap),
                       "--only", "seed-direct", "--max-files", "1"])
        self.assertEqual(len(r["doc_targets"]), 1)

    def test_ripple_summary_marks_reviewed_files_documented_by_request(self):
        self._write_reviewed([("src/net/other.c", "別物"), ("src/net/conn.c", "別物")])
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ"),
                      ("src/net/other.c", "net", "src/net", "依頼調査")])
        self._make_summary(merged=True)
        text = self.summary_md.read_text(encoding="utf-8")
        self.assertIn("| src/net/other.c | 別物（依頼調査で資料あり） |", text)
        self.assertIn("| src/net/conn.c | 別物 |", text)

    def test_fingerprint_follows_request_log(self):
        self._ledger([("src/auth/login.c", "auth", "src/auth", "下調べ")])
        self._write_prelim_spo([("auth", DRAFT_AUTH.split("\n", 2)[2])])
        first = self._assemble()["inputs_fingerprint"]
        self._req(["src/auth/login.c"], append=["src/auth/login.c"])
        done = self.work / "doc-request-done.txt"
        done.write_text("src/auth/login.c\n", encoding="utf-8")
        self._run(["doc-request-record", "--repo-dir", str(self.out), "--files-file",
                   str(self.work / "doc-request-files.json"), "--done-file", str(done), "--today", "2026-10-05"])
        self.assertNotEqual(self._run(self._assemble_argv())["inputs_fingerprint"], first)


class FinishNeededDocsTest(_RequestBase):
    def _needed(self):
        return self._run(["finish-needed", "--repo-dir", str(self.out)])

    def test_docs_changed(self):
        self._run(["finish-record", "--repo-dir", str(self.out), "--status", "ok", "--today", "t"])
        self.assertEqual((self._needed()["needed"], self._needed()["reason_code"]), (False, ""))
        self.ledger.write_text(self.ledger.read_text(encoding="utf-8")
                               + "| src/net/conn.c | net | src/net | 依頼調査 | 接続 |\n", encoding="utf-8")
        r = self._needed()
        self.assertEqual((r["needed"], r["reason_code"]), (True, "docs-changed"))
        self._run(["finish-record", "--repo-dir", str(self.out), "--status", "ok", "--today", "t"])
        self.assertFalse(self._needed()["needed"])
        (self.work / "doc-request-log.md").write_text("\n".join(mod.DOC_REQUEST_LOG_HEAD) + "\n", encoding="utf-8")
        self.assertEqual(self._needed()["reason_code"], "docs-changed")


class DocRequestRecordTest(_RequestBase):
    def test_records_done_files_only(self):
        self._req(["src/net/conn.c", "src/net/other.c"], append=["src/auth/login.c"])
        (self.work / "doc-request-focus.md").write_text("エラー時の\n後始末の流れ\n", encoding="utf-8")
        done = self.work / "doc-request-done.txt"
        done.write_text("src/net/conn.c\nsrc/auth/login.c\n", encoding="utf-8")
        argv = ["doc-request-record", "--repo-dir", str(self.out), "--files-file", str(self.work / "doc-request-files.json"),
                "--done-file", str(done), "--focus-file", str(self.work / "doc-request-focus.md"), "--today", "2026-10-05"]
        self.assertEqual(self._run(argv)["recorded"], 2)
        log = (self.work / "doc-request-log.md").read_text(encoding="utf-8")
        self.assertIn("| 2026-10-05 | 新規 | src/net/conn.c | エラー時の 後始末の流れ |", log)
        self.assertIn("| 2026-10-05 | 追記 | src/auth/login.c | エラー時の 後始末の流れ |", log)
        self.assertNotIn("other.c", log)
        done.write_text("src/util/helper.c\n", encoding="utf-8")
        code, _o, _e = self._run_exit(argv)
        self.assertEqual(code, 1)
        self.assertEqual((self.work / "doc-request-log.md").read_text(encoding="utf-8"), log)


class DocAppendCheckTest(_RequestBase):
    """doc-append-check（依頼調査の追記の写しと検査）。"""

    MODULE_BODY = ("\n---\n\n## 1. モジュール概要\n\n| 項目 | 内容 |\n|------|------|\n| モジュール名 | auth |\n\n---\n\n"
                   "## 2. 現状仕様\n\n### 2.1 処理フロー\n\nログイン。\n\n{fill}### 2.6 制約・前提条件\n\nなし。\n\n---\n\n"
                   "## 3. 既存仕様の文書化（仕様書がない場合）\n\n対象外\n\n---\n\n## 5. 変更履歴\n\n"
                   "| 版数 | 日付 | 変更者 | 変更内容 |\n|------|------|--------|----------|\n"
                   "| 1.0 | 2026-10-04 | specout_bfs.py assemble-spo | 確定（波紋調査の結果を反映） |\n")
    HEADER = ("# スペックアウト資料（モジュール個別）\n\n**文書番号：** SPO-CR-2026-970-auth  \n"
              "**作成者：** AI（xddp-specout-prelim-agent）  \n**版数：** 1.0\n")

    def setUp(self):
        super().setUp()
        self.mod_doc = self.out / "modules" / "auth-spo.md"
        self.mod_doc.parent.mkdir()
        fill = "".join(f"段落 {k}\n\n" for k in range(120))   # 200 行を超える資料
        self.original = self.HEADER + self.MODULE_BODY.replace("{fill}", fill)
        self.mod_doc.write_text(self.original, encoding="utf-8")
        self.memo = self.work / "observation-memo.md"
        self.memo.write_text("## 外部副作用\n\n| ファイルパス | x |\n|---|---|\n| src/auth/login.c | a |\n", encoding="utf-8")
        self._req(["src/auth/login.c"], append=["src/auth/login.c"])
        self.layout = self.work / "doc-request-layout.json"
        self.layout.write_text(json.dumps({"file_outputs": {"src/auth/login.c": {
            "module": "auth", "output_file": str(self.mod_doc)}}}), encoding="utf-8")

    def _check(self, action, *extra):
        return self._run_exit(["doc-append-check", action, "--repo-dir", str(self.out),
                               "--files-file", str(self.work / "doc-request-files.json"), "--layout", str(self.layout),
                               "--batch", "0", *extra])

    def _append_ok(self, text):
        sec = ("\n### 2.7 追加調査（依頼調査）\n\n#### src/auth/login.c（2026-10-05。観点: —）\n\n```sh\n# コメント\n---\n```\n\n"
               "| a | b |\n|---|---|\n| 1 | 2 |\n\n")
        text = text.replace("なし。\n\n---\n\n## 3.", "なし。\n" + sec + "---\n\n## 3.")
        text = text.replace("**版数：** 1.0", "**版数：** 1.1")
        return text.replace("確定（波紋調査の結果を反映） |\n",
                            "確定（波紋調査の結果を反映） |\n| 1.1 | 2026-10-05 | AI（xddp-specout-prelim-agent） | 依頼調査・追記（1 ファイル・—） |\n")

    def _backup(self):
        return self.work / "doc-append-backup"

    def test_append_in_section_passes(self):
        self.assertEqual(self._check("snapshot")[0], 0)
        self.mod_doc.write_text(self._append_ok(self.original), encoding="utf-8")
        self.memo.write_text(self.memo.read_text(encoding="utf-8") + "| src/auth/login.c | b |\n", encoding="utf-8")
        code, out, err = self._check("verify")
        self.assertEqual(code, 0, err)
        self.assertFalse(self._backup().exists())
        self.assertIn("### 2.7 追加調査（依頼調査）", self.mod_doc.read_text(encoding="utf-8"))

    def test_violations_restore(self):
        cases = {
            "rewrite_existing": lambda t: t.replace("ログイン。", "ログイン（直した）。"),
            "delete_blank": lambda t: t.replace("段落 3\n\n段落 4", "段落 3\n段落 4"),
            "outside_section": lambda t: t.replace("| モジュール名 | auth |\n", "| モジュール名 | auth |\n追加の行\n"),
            "rewrite_history": lambda t: t.replace("確定（波紋調査の結果を反映）", "確定"),
        }
        for name, change in cases.items():
            with self.subTest(case=name):
                self.mod_doc.write_text(self.original, encoding="utf-8")
                self.assertEqual(self._check("snapshot")[0], 0)
                self.mod_doc.write_text(change(self._append_ok(self.original)), encoding="utf-8")
                code, _o, err = self._check("verify")
                self.assertEqual(code, 3, name)
                self.assertEqual(self.mod_doc.read_text(encoding="utf-8"), self.original)
                self.assertFalse(self._backup().exists())

    def test_memo_and_ledger_changes_restore(self):
        memo_before = self.memo.read_text(encoding="utf-8")
        ledger_before = self.ledger.read_text(encoding="utf-8")
        self._check("snapshot")
        self.memo.write_text(memo_before.replace("| a |", "| a2 |"), encoding="utf-8")
        self.assertEqual(self._check("verify")[0], 3)
        self.assertEqual(self.memo.read_text(encoding="utf-8"), memo_before)
        self._check("snapshot")
        self.ledger.write_text(ledger_before + "| src/net/conn.c | net | src/net | 依頼調査 | x |\n", encoding="utf-8")
        self.assertEqual(self._check("verify")[0], 3)
        self.assertEqual(self.ledger.read_text(encoding="utf-8"), ledger_before)

    def test_restore_flag_always_restores(self):
        self._check("snapshot")
        self.mod_doc.write_text(self._append_ok(self.original), encoding="utf-8")
        self.assertEqual(self._check("verify", "--restore")[0], 3)
        self.assertEqual(self.mod_doc.read_text(encoding="utf-8"), self.original)

    def test_verify_without_backup_fails_without_changes(self):
        self.mod_doc.write_text(self._append_ok(self.original), encoding="utf-8")
        code, _o, _e = self._check("verify")
        self.assertEqual(code, 1)
        self.assertIn("### 2.7", self.mod_doc.read_text(encoding="utf-8"))

    def test_snapshot_left_restore_and_discard(self):
        self._check("snapshot")
        code, out, _e = self._check("snapshot")
        self.assertEqual(code, 4)
        self.assertTrue(out["backup_left"])
        self.mod_doc.write_text(self._append_ok(self.original), encoding="utf-8")
        # 台帳が変わっていれば restore は何も変えずに exit 1
        ledger_before = self.ledger.read_text(encoding="utf-8")
        self.ledger.write_text(ledger_before + "| src/net/conn.c | net | src/net | 依頼調査 | x |\n", encoding="utf-8")
        self.assertEqual(self._check("restore")[0], 1)
        self.assertIn("### 2.7", self.mod_doc.read_text(encoding="utf-8"))
        # SPO の仕上げの記録が変わっていても exit 1
        self.ledger.write_text(ledger_before, encoding="utf-8")
        (self.work / "specout-finish.json").write_text('{"status": "ok"}', encoding="utf-8")
        self.assertEqual(self._check("restore")[0], 1)
        (self.work / "specout-finish.json").unlink()
        self.assertEqual(self._check("restore")[0], 0)
        self.assertEqual(self.mod_doc.read_text(encoding="utf-8"), self.original)
        self.assertFalse(self._backup().exists())
        self._check("snapshot")
        self.assertEqual(self._check("discard")[0], 0)
        self.assertFalse(self._backup().exists())

    def test_integrated_append_section(self):
        draft = self.work / "module-drafts" / "auth.md"
        draft.parent.mkdir()
        base = "## 2.A. auth\n\n" + DRAFT_AUTH.split("\n", 2)[2]
        draft.write_text(base, encoding="utf-8")
        self.layout.write_text(json.dumps({"file_outputs": {"src/auth/login.c": {
            "module": "auth", "output_file": str(draft)}}}), encoding="utf-8")
        self._check("snapshot")
        draft.write_text(base + "\n\n### 2.A.10 追加調査（依頼調査）\n\n#### src/auth/login.c（2026-10-05。観点: —）\n\n"
                                "```python\n## not a heading\n```\n\n観察。\n", encoding="utf-8")
        code, _o, err = self._check("verify")
        self.assertEqual(code, 0, err)
        # 統合パスでも節の外（2.A.1 の本文）への追加は戻す
        draft.write_text(base, encoding="utf-8")
        self._check("snapshot")
        draft.write_text(base.replace("ログイン判定の流れ。", "ログイン判定の流れ。\n足した行"), encoding="utf-8")
        self.assertEqual(self._check("verify")[0], 3)
        self.assertEqual(draft.read_text(encoding="utf-8"), base)

    def test_append_after_move_passes(self):
        # 統合パスから移し替えた資料（### 2.7 は §2 の中）への追記
        doc = mod._section_to_module_doc(
            mod._normalize_draft("## 2.A. auth\n\n" + DRAFT_AUTH.split("\n", 2)[2]
                                 + "\n### 2.A.10 追加調査（依頼調査）\n\n#### src/auth/session.c（2026-10-04。観点: —）\n\n前の追記。\n", "A"),
            "auth", "src/auth", MODULE_TPL.read_text(encoding="utf-8"), "CR-2026-970", "2026-10-04", "1.0")
        self.mod_doc.write_text(doc, encoding="utf-8")
        self._check("snapshot")
        new = doc.replace("前の追記。\n", "前の追記。\n\n#### src/auth/login.c（2026-10-05。観点: —）\n\n新しい追記。\n")
        self.mod_doc.write_text(new, encoding="utf-8")
        code, _o, err = self._check("verify")
        self.assertEqual(code, 0, err)
