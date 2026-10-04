"""specout_slice.py のテスト。規則判定（rule）は常に実行し、スライス判定（slice）は tree-sitter が無い環境ではスキップする。"""
import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import specout_slice as mod  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "slice"

try:
    mod._ts()
    HAVE_TS = True
except mod.EngineUnavailable:
    HAVE_TS = False

SEED_RE = re.compile(r"(?<![A-Za-z0-9_])SEED(?![A-Za-z0-9_])")


def _seed_lines(path: Path, symbol: str = "SEED") -> list:
    rx = re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(symbol))
    return [i for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1) if rx.search(line)]


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        args = mod.build_parser().parse_args(argv)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _state(self, repo: Path, engine: str, h_as: str = "c", ignore: str = "", pending=None) -> Path:
        p = self.root / "bfs-state.json"
        p.write_text(json.dumps({
            "repo_path": str(repo), "slice_engine": engine, "slice_h_as": h_as, "exclude_patterns": [],
            "slice_ignore_calls": ignore, "seed_summary_pending": pending or [],
        }), encoding="utf-8")
        return p

    def _classify(self, repo: Path, hits: list, engine: str, summaries=None, h_as: str = "c", ignore: str = ""):
        """hits: [(file, line_no, symbol)]。line_id は W0-R{n}。戻り値: (出力 JSON, {line_id: エントリ})。"""
        state = self._state(repo, engine, h_as, ignore)
        chunk = self.root / "wave-0-hits-chunk-S.json"
        chunk.write_text(json.dumps({
            "chunk_id": "W0-KS", "wave": 0, "frontier_summaries": summaries or {},
            "hits": [{"line_id": f"W0-R{n}", "command_id": "W0-C1", "symbol": sym, "scope_file": None,
                      "file": f, "line_no": ln, "matched_text": ""} for n, (f, ln, sym) in enumerate(hits, 1)],
        }), encoding="utf-8")
        out = self.root / "wave-0-chunk-S-class.json"
        self._run(["classify", "--path", str(state), "--hits", str(chunk), "--out", str(out)])
        payload = json.loads(out.read_text(encoding="utf-8"))
        return payload, {e["line_id"]: e for e in payload["classification"]}


# ---------------------------------------------------------------------------
# 規則判定（常に実行）
# ---------------------------------------------------------------------------

class RuleEngineTest(_Base):
    def _verdicts(self, rel: str, lang: str) -> dict:
        rf = mod.RuleFile(str(FIX / rel), lang)
        return {ln: mod.rule_judge(rf, ln, "SEED") for ln in _seed_lines(FIX / rel)}

    def test_c_comment_string_include_label_prototype_are_false_positive(self):
        v = self._verdicts("rule/rule_sample.c", "c")
        self.assertEqual((v[1].status, v[1].note), ("fp", "include"))
        self.assertEqual(v[2].status, "fp")                       # ブロックコメント
        self.assertEqual((v[3].status, v[3].note), ("fp", "prototype-param"))
        self.assertEqual(v[11].status, "fp")                      # 行コメント
        self.assertEqual(v[12].status, "fp")                      # 文字列
        self.assertEqual((v[18].status, v[18].note), ("fp", "label"))   # goto SEED;
        self.assertEqual((v[19].status, v[19].note), ("fp", "label"))   # SEED:

    def test_c_enclosing_self_def_and_file_scope(self):
        v = self._verdicts("rule/rule_sample.c", "c")
        self.assertEqual(v[4].status, "file-scope")               # プロトタイプの型（引数名ではない）
        self.assertEqual(v[5].status, "file-scope")               # マクロ定義（rule は伝播させない）
        self.assertEqual(v[6].status, "file-scope")               # グローバルの初期化子
        self.assertEqual((v[13].status, v[13].func.name), ("rule", "multi_line_head"))  # 複数行の頭部
        self.assertEqual((v[15].status, v[15].func.name), ("rule", "multi_line_head"))
        self.assertEqual((v[22].status, v[22].func.name), ("self-def", "head_hit"))
        self.assertEqual(v[25].status, "file-scope")

    def test_cpp_function_names_are_unqualified(self):
        v = self._verdicts("rule/rule_sample.cpp", "cpp")
        self.assertEqual({ln: x.func.name for ln, x in v.items()},
                         {4: "Widget", 5: "~Widget", 6: "operator==", 7: "get", 11: "compute",
                          16: "twice", 20: "Widget"})
        self.assertTrue(all(x.status == "rule" for x in v.values()))

    def test_python_nested_decorated_and_module_scope(self):
        v = self._verdicts("rule/rule_sample.py", "python")
        self.assertEqual(v[2].status, "file-scope")               # モジュール本体
        self.assertEqual(v[4].status, "file-scope")               # クラス本体
        self.assertEqual((v[5].status, v[5].func.name), ("self-def", "method"))
        self.assertEqual((v[9].status, v[9].func.name), ("rule", "static_m"))
        self.assertEqual((v[11].status, v[11].func.name), ("rule", "outer"))   # デコレータは外側の関数の本体
        self.assertEqual((v[13].status, v[13].func.name), ("self-def", "inner"))  # 入れ子の関数の宣言部
        self.assertEqual((v[14].status, v[14].func.name), ("rule", "inner"))
        self.assertEqual(v[15].status, "fp")                      # 文字列
        self.assertEqual(v[16].status, "fp")                      # コメント
        self.assertEqual((v[17].status, v[17].func.name), ("rule", "outer"))   # f 文字列の式は残す
        self.assertEqual((v[20].status, v[20].func.name), ("rule", "coro"))
        self.assertEqual((v[21].status, v[21].func.name), ("rule", "one_liner"))
        self.assertEqual(v[23].status, "fp")                      # 三重引用符の文字列

    def test_root_field_symbol(self):
        repo = self.root / "repo"
        repo.mkdir()
        (repo / "a.c").write_text("void f(void) {\n    server.dirty++;\n    s->dirty = 0;\n"
                                  "    server->dirty = 1;\n}\n// server.dirty\n", encoding="utf-8")
        rf = mod.RuleFile(str(repo / "a.c"), "c")
        self.assertEqual(mod.rule_judge(rf, 2, "server.dirty").status, "rule")
        self.assertEqual(mod.rule_judge(rf, 3, "server.dirty").status, "fp")
        self.assertEqual(mod.rule_judge(rf, 4, "server.dirty").status, "rule")
        self.assertEqual(mod.rule_judge(rf, 6, "server.dirty").status, "fp")

    def test_classify_rule_entries_and_unsupported_patterns(self):
        hits = [("rule_sample.cpp", ln, "SEED") for ln in (4, 5, 6, 7)] + [("rule_sample.c", 3, "SEED"),
                                                                             ("rule_sample.c", 13, "SEED")]
        payload, by_id = self._classify(FIX / "rule", hits, "rule", h_as="cpp")
        self.assertEqual(by_id["W0-R1"]["next_symbols"], ["Widget"])
        self.assertEqual(by_id["W0-R2"]["next_symbols"], [])      # デストラクタは追わない
        self.assertEqual(by_id["W0-R3"]["next_symbols"], [])      # 演算子オーバーロードは追わない
        self.assertEqual(by_id["W0-R4"]["next_symbols"], ["get"])
        self.assertEqual(by_id["W0-R5"]["classification"], "false-positive")
        self.assertEqual(by_id["W0-R6"]["enclosing_function"], "multi_line_head")
        self.assertEqual(by_id["W0-R6"]["enclosing_range"], [7, 16])
        self.assertEqual(by_id["W0-R6"]["slice"], {"engine": "rule", "status": "rule", "escapes": []})
        self.assertEqual(by_id["W0-R6"]["next_symbol_summaries"], {})
        self.assertEqual(sorted(u["pattern"] for u in payload["unsupported_patterns"]),
                         ["destructor", "operator-overload"])
        self.assertEqual(payload["unsupported_patterns"][0]["location"], "rule_sample.cpp:5")
        self.assertIn("elapsed_ms", payload)
        self.assertEqual(payload["index_build_ms"], 0)

    def test_classify_empty_chunk_writes_empty_file(self):
        payload, by_id = self._classify(FIX / "rule", [], "slice")
        self.assertEqual((payload["chunk_id"], payload["classification"], payload["unsupported_patterns"]),
                         ("W0-KS", [], []))

    def test_rule_does_not_need_tree_sitter(self):
        def _boom():
            raise mod.EngineUnavailable("ModuleNotFoundError: No module named 'tree_sitter'")
        with patch.object(mod, "_ts", _boom):
            _payload, by_id = self._classify(FIX / "rule", [("rule_sample.c", 13, "SEED")], "rule")
        self.assertEqual(by_id["W0-R1"]["next_symbols"], ["multi_line_head"])


class ProbeAndEngineAvailabilityTest(_Base):
    def _unavailable(self):
        raise mod.EngineUnavailable("ModuleNotFoundError: No module named 'tree_sitter'")

    def test_probe_unavailable_writes_out_file(self):
        out = self.root / "probe.json"
        with patch.object(mod, "_ts", self._unavailable):
            result = self._run(["probe", "--out", str(out)])
        self.assertEqual(result["engine"], "unavailable")
        self.assertIn("No module named 'tree_sitter'", result["warning"])
        self.assertEqual(result["engine_exts"], mod.ENGINE_EXTS)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8")), result)

    @unittest.skipUnless(HAVE_TS, "tree-sitter が無い")
    def test_probe_available(self):
        result = self._run(["probe"])
        self.assertEqual((result["engine"], result["warning"]), ("slice", None))

    def test_classify_exits_5_when_slice_engine_unavailable(self):
        with patch.object(mod, "_ts", self._unavailable), redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as cm:
                self._classify(FIX / "rule", [("rule_sample.c", 13, "SEED")], "slice")
        self.assertEqual(cm.exception.code, mod.EXIT_ENGINE_UNAVAILABLE)
        self.assertIn("tree_sitter", err.getvalue())

    def test_seed_summary_exits_5_when_unavailable(self):
        state = self._state(FIX / "extra", "slice", pending=["seed_fn"])
        with patch.object(mod, "_ts", self._unavailable), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                self._run(["seed-summary", "--path", str(state), "--out", str(self.root / "s.json")])
        self.assertEqual(cm.exception.code, mod.EXIT_ENGINE_UNAVAILABLE)

    def test_seed_summary_rejects_rule_engine(self):
        state = self._state(FIX / "extra", "rule", pending=["seed_fn"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            self._run(["seed-summary", "--path", str(state), "--out", str(self.root / "s.json")])
        self.assertEqual(cm.exception.code, 1)


# ---------------------------------------------------------------------------
# スライス判定（tree-sitter が必要）
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAVE_TS, "tree-sitter が無い")
class SliceEngineTest(_Base):
    def test_basic_fixture_escapes_match_prototype(self):
        hits = [("sample.c", ln, "SEED") for ln in _seed_lines(FIX / "basic" / "sample.c")] + \
               [("sample.py", ln, "SEED") for ln in _seed_lines(FIX / "basic" / "sample.py")]
        _payload, by_id = self._classify(FIX / "basic", hits, "slice")
        got = {(by_id[f"W0-R{n}"]["enclosing_function"] or "-", tuple(by_id[f"W0-R{n}"]["next_symbols"]))
               for n in range(1, len(hits) + 1)}
        expected_c = {("ret_flow", ("ret_flow",)), ("local_only", ()), ("out_param", ("out_param",)),
                      ("global_write", ("g_count",)), ("control_dep", ("g_count",)),
                      ("early_return", ("early_return",)), ("macro_write", ("macro_write",)),
                      ("local_struct", ()), ("static_state", ("static_state",)), ("heap_ptr", ("heap_ptr",)),
                      ("flow_order", ()), ("branch_exit", ("branch_exit",)), ("check_only", ())}
        expected_py = {("ret_flow", ("ret_flow",)), ("mutate_param", ("mutate_param",)),
                       ("write_global", ("CACHE",)), ("m", ("m",)), ("gen", ("gen",)),
                       ("raise_it", ("raise_it",)), ("calls_mutator", ("calls_mutator",)),
                       ("with_ctx", ()), ("outer_fn", ())}
        self.assertLessEqual(expected_c | expected_py, got)

    def test_file_scope_values_propagate(self):
        hits = [("extra.c", 2, "SEED"), ("extra.c", 3, "SEED")]
        _payload, by_id = self._classify(FIX / "extra", hits, "slice")
        self.assertEqual(by_id["W0-R1"]["next_symbols"], ["g_init"])
        self.assertEqual(by_id["W0-R1"]["note"], "file-scope:global-init")
        self.assertEqual(by_id["W0-R2"]["next_symbols"], ["DOUBLE_SEED"])
        self.assertEqual(by_id["W0-R2"]["slice"]["file_scope"], "macro-def")
        self.assertTrue(by_id["W0-R2"]["slice"]["propagates"])
        self.assertIsNone(by_id["W0-R2"]["enclosing_range"])
        _payload, by_id = self._classify(FIX / "basic", [("sample.py", 32, "SEED")], "slice")
        self.assertEqual(by_id["W0-R1"]["next_symbols"], ["DERIVED"])
        self.assertEqual(by_id["W0-R1"]["note"], "file-scope:module/class-assign")

    def test_function_pointer_calls_are_unsupported_patterns(self):
        payload, by_id = self._classify(FIX / "extra", [("extra.c", 5, "SEED"), ("extra.c", 10, "SEED")], "slice")
        self.assertEqual(by_id["W0-R1"]["next_symbols"], ["dispatch"])
        self.assertEqual(by_id["W0-R1"]["next_symbol_summaries"]["dispatch"]["returns"], True)
        self.assertEqual({(u["pattern"], u["location"]) for u in payload["unsupported_patterns"]},
                         {("function-pointer-call", "extra.c:6"), ("function-pointer-call", "extra.c:10")})

    def test_frontier_summaries_are_used_as_callee_summaries(self):
        """ヒットのシンボル（KEY）以外の関数の要約が、解析中の関数が呼ぶ関数の影響の計算に効く。"""
        hit = [("extra.c", 16, "KEY")]
        _payload, by_id = self._classify(FIX / "extra", hit, "slice")
        self.assertEqual(by_id["W0-R1"]["next_symbols"], [])
        summ = {"side_effect_fn": {"returns": False, "out": [1], "globals": [], "side": False, "closure": []}}
        _payload, by_id = self._classify(FIX / "extra", hit, "slice", summaries=summ)
        self.assertEqual(by_id["W0-R1"]["next_symbols"], ["use_key"])
        self.assertIn(["out", 0, 17], by_id["W0-R1"]["slice"]["escapes"])

    def test_ignore_calls_regex_is_read_from_state(self):
        summ = {"side_effect_fn": {"returns": False, "out": [1], "globals": [], "side": False, "closure": []}}
        _payload, by_id = self._classify(FIX / "extra", [("extra.c", 16, "KEY")], "slice", summaries=summ,
                                         ignore="side_effect_fn|log_\\w+")
        self.assertEqual(by_id["W0-R1"]["next_symbols"], [])

    def test_cpp_naming_rules(self):
        lines = _seed_lines(FIX / "extra" / "naming.cpp")
        payload, by_id = self._classify(FIX / "extra", [("naming.cpp", ln, "SEED") for ln in lines], "slice",
                                        h_as="cpp")
        nxt = {ln: by_id[f"W0-R{n}"]["next_symbols"] for n, ln in enumerate(lines, 1)}
        self.assertEqual(nxt, {8: [], 11: [], 15: ["size"], 19: ["pick"]})
        self.assertEqual(sorted(u["pattern"] for u in payload["unsupported_patterns"]),
                         ["destructor", "operator-overload"])

    def test_seed_summary_targets_include_symbols_without_definition(self):
        state = self._state(FIX / "extra", "slice", pending=["seed_fn"])
        out = self.root / "seed-summaries.json"
        result = self._run(["seed-summary", "--path", str(state), "--symbols", "seed_fn,g_counter,NO_SUCH",
                            "--out", str(out)])
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(payload["targets"], ["seed_fn", "g_counter", "NO_SUCH"])
        self.assertEqual(sorted(payload["summaries"]), ["seed_fn"])
        self.assertEqual(payload["summaries"]["seed_fn"],
                         {"returns": True, "out": [], "globals": ["g_counter"], "side": False, "closure": []})
        self.assertEqual(payload["globals"], ["g_counter"])
        self.assertEqual(result["targets"], payload["targets"])
        self.assertEqual(result["summaries_file"], str(out))

    def test_seed_summary_defaults_to_pending(self):
        state = self._state(FIX / "extra", "slice", pending=["seed_fn", "VALUE_ONLY"])
        result = self._run(["seed-summary", "--path", str(state), "--out", str(self.root / "s.json")])
        self.assertEqual(result["targets"], ["seed_fn", "VALUE_ONLY"])
        self.assertEqual(result["globals"], ["g_counter"])

    def test_python_import_alias_propagates(self):
        """`from m import f as g`: モジュール本体では別名を次の波で追い、関数の中では別名の使用から影響を追う。"""
        hits = [("aliases.py", 1, "SEED"), ("aliases.py", 5, "SEED"), ("aliases.py", 10, "SEED")]
        _payload, by_id = self._classify(FIX / "extra", hits, "slice")
        self.assertEqual(by_id["W0-R1"]["next_symbols"], ["seed_alias"])
        self.assertEqual(by_id["W0-R1"]["note"], "file-scope:module/class-assign")
        self.assertEqual(by_id["W0-R2"]["next_symbols"], ["uses_alias_in_function"])
        self.assertEqual(by_id["W0-R3"]["next_symbols"], [])

    def test_analysis_error_falls_back_to_rule(self):
        def _broken(*_a, **_kw):
            raise RuntimeError("boom")
        with patch.object(mod, "judge_hit", _broken):
            _payload, by_id = self._classify(FIX / "basic", [("sample.c", 6, "SEED")], "slice")
        entry = by_id["W0-R1"]
        self.assertEqual(entry["next_symbols"], ["ret_flow"])
        self.assertTrue(entry["note"].startswith("slice-error RuntimeError"))
        self.assertEqual((entry["slice"]["engine"], entry["slice"]["status"]), ("slice", "rule"))


if __name__ == "__main__":
    unittest.main()
