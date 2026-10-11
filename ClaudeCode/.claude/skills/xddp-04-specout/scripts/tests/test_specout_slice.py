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
        self.assertEqual(by_id["W0-R1"]["next_symbols"], ["multi_line_head[FILE:rule_sample.c]"])


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
                      ("global_write", ("g_count[FILE:sample.c]",)), ("control_dep", ("g_count[FILE:sample.c]",)),
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
        self.assertEqual(by_id["W0-R1"]["next_symbols"], ["g_init[FILE:extra.c]"])
        self.assertEqual(by_id["W0-R1"]["note"], "file-scope:global-init")
        self.assertEqual(by_id["W0-R2"]["next_symbols"], ["DOUBLE_SEED[FILE:extra.c]"])
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
                         {"returns": True, "out": [], "globals": ["g_counter[FILE:extra.c]"], "side": False,
                          "closure": [], "name_only": ["g_counter[FILE:extra.c]"]})
        self.assertEqual(payload["globals"], ["g_counter[FILE:extra.c]"])
        self.assertEqual(payload["name_only"], ["g_counter[FILE:extra.c]"])
        self.assertEqual(result["targets"], payload["targets"])
        self.assertEqual(result["summaries_file"], str(out))

    def test_seed_summary_defaults_to_pending(self):
        state = self._state(FIX / "extra", "slice", pending=["seed_fn", "VALUE_ONLY"])
        result = self._run(["seed-summary", "--path", str(state), "--out", str(self.root / "s.json")])
        self.assertEqual(result["targets"], ["seed_fn", "VALUE_ONLY"])
        self.assertEqual(result["globals"], ["g_counter[FILE:extra.c]"])

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



# ---------------------------------------------------------------------------
# シンボルの同一性（リンケージによる解決・ヒット側の除外・同一性の印）
# ---------------------------------------------------------------------------

IDF = FIX / "identity"


def _line_of(path: Path, needle: str) -> int:
    for i, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if needle in line:
            return i
    raise AssertionError(f"{needle!r} が {path} にありません")


@unittest.skipUnless(HAVE_TS, "tree-sitter が無い")
class IdentityTest(_Base):
    def _repo_index(self, repo=IDF, h_as="c"):
        r = mod.Repo(str(repo), h_as=h_as)
        r.build_index()
        return r

    def _cls(self, hits, engine="slice", kinds=None, seeds=(), repo=IDF, h_as="c", summaries=None):
        """hits: [(file, needle, symbol[, entry])]。needle を含む最初の行のヒット。戻り値: [エントリ]（hits の順）。"""
        state = self._state(repo, engine, h_as)
        rows = []
        for n, h in enumerate(hits, 1):
            f, needle, sym = h[:3]
            entry = h[3] if len(h) > 3 else sym
            rows.append({"line_id": f"W1-R{n}", "command_id": "W1-C1", "symbol": sym, "scope_file": None,
                         "entry": entry, "file": f, "line_no": _line_of(repo / f, needle), "matched_text": ""})
        chunk = self.root / "wave-1-hits-chunk-S.json"
        chunk.write_text(json.dumps({"chunk_id": "W1-KS", "wave": 1, "frontier_summaries": summaries or {},
                                     "frontier_kinds": kinds or {}, "seed_symbols": list(seeds), "hits": rows}),
                         encoding="utf-8")
        out = self.root / "wave-1-chunk-S-class.json"
        self._run(["classify", "--path", str(state), "--hits", str(chunk), "--out", str(out)])
        by_id = {e["line_id"]: e for e in json.loads(out.read_text(encoding="utf-8"))["classification"]}
        return [by_id[f"W1-R{n}"] for n in range(1, len(hits) + 1)]

    # 1. リンケージの索引
    def test_linkage_index_scans_nested_file_scope(self):
        r = self._repo_index()
        self.assertTrue({"bm", "g_ext", "a_g"} <= r.visible)          # #ifdef / extern "C" {} の中の extern
        self.assertIn("h_static_var", r.visible)                      # ヘッダの static は外部から見える
        self.assertNotIn("h_static_var", r.internal)
        self.assertNotIn("h_ret", r.internal)                          # ヘッダの static inline 関数
        self.assertEqual(r.internal["s_count"], {"a.c", "b.c"})       # static 変数
        self.assertEqual(r.internal["s_writer"], {"a.c"})             # static 関数
        self.assertEqual(r.internal["count"], {"d2.cpp"})             # 無名名前空間
        self.assertEqual(r.internal["LOCALMAC"], {"a.c"})             # .c で定義したマクロ
        self.assertIn("g_init2", r.file_decls["a.c"])                 # #ifdef の中の宣言

    # 2. resolve_global
    def test_resolve_global_steps(self):
        r = self._repo_index()
        self.assertEqual(r.resolve_global("s_count", "a.c"), ("file", "a.c", True))
        self.assertEqual(r.resolve_global("g_ext", "a.c"), ("extern", None, True))
        self.assertEqual(r.resolve_global("g_noext", "a.c"), ("file", "a.c", False))
        self.assertIsNone(r.resolve_global("nnode", "a.c"))
        self.assertIsNone(r.resolve_global("proto_with_param", "a.c"))   # 関数の宣言は書き込み先の解決に使わない
        self.assertEqual(r.resolve_global("CONF", "mod.py"), ("extern", None, True))
        for name in ("f", "A", "a"):   # def・class・import の名前は Python の解決に使わない
            self.assertIsNone(r.resolve_global(name, "mod.py"))

    # 3・4. ローカル変数を送らない
    def test_macro_declared_local_is_unknown_not_global(self):
        [e] = self._cls([("a.c", "nnode = SEED", "SEED")])
        self.assertEqual(e["next_symbols"], ["bgp_clear"])
        self.assertIn(["unknown", "undeclared nnode", _line_of(IDF / "a.c", "nnode = SEED")], e["slice"]["escapes"])

    def test_misparsed_local_stays_in_its_own_file(self):
        r = self._repo_index()
        self.assertEqual(r.file_decls["broken.c"], {"node", "nnode"})
        [e] = self._cls([("broken.c", "node = SEED", "SEED")])
        self.assertIn("node[FILE:broken.c]", e["next_symbols"])
        self.assertEqual(e["name_only_symbols"], ["node[FILE:broken.c]"])
        self.assertEqual(e["next_symbol_kinds"]["node[FILE:broken.c]"], "variable")

    # 5. global の出口の表記
    def test_global_write_entries(self):
        es = self._cls([("a.c", "s_count = SEED", "SEED"), ("a.c", "g_ext = SEED", "SEED"),
                        ("a.c", "h_static_var = SEED", "SEED"), ("a.c", "g_noext = SEED", "SEED"),
                        ("a.c", "s_writer(SEED)", "SEED"), ("a.c", "b_writer(SEED)", "SEED")])
        self.assertEqual(es[0]["next_symbols"], ["s_count[FILE:a.c]"])
        self.assertEqual(es[0]["name_only_symbols"], [])
        self.assertEqual(es[1]["next_symbols"], ["g_ext"])
        self.assertEqual(es[2]["next_symbols"], ["h_static_var"])
        self.assertEqual((es[3]["next_symbols"], es[3]["name_only_symbols"]),
                         (["g_noext[FILE:a.c]"], ["g_noext[FILE:a.c]"]))
        self.assertEqual(es[4]["next_symbols"], ["s_count[FILE:a.c]"])      # 呼び出し先の static 変数
        self.assertEqual((es[5]["next_symbols"], es[5]["name_only_symbols"]),
                         (["g_noext_b[FILE:b.c]"], ["g_noext_b[FILE:b.c]"]))  # 呼び出し先の手順3

    # 6. static 関数の呼び出し元
    def test_static_function_callers_are_file_scoped(self):
        es = self._cls([("a.c", "s_ret(void) { return SEED", "SEED"), ("lib.h", "h_ret(void)", "SEED")])
        self.assertEqual(es[0]["next_symbols"], ["s_ret[FILE:a.c]"])
        self.assertEqual(es[0]["next_symbol_kinds"], {"s_ret[FILE:a.c]": "function"})
        self.assertEqual(es[1]["next_symbols"], ["h_ret"])
        es = self._cls([("a.c", "s_ret(void) { return SEED", "SEED"), ("lib.h", "h_ret(void)", "SEED")],
                       engine="rule")
        self.assertEqual([e["next_symbols"] for e in es], [["s_ret[FILE:a.c]"], ["h_ret"]])

    # 7・15. 呼び出し先の解決
    def test_callee_resolution_prefers_callers_static(self):
        es = self._cls([("a.c", "if (x == SEED) dup();", "SEED"), ("c.c", "if (x == SEED) dup();", "SEED"),
                        ("a.c", "CALL_DUP();", "SEED"), ("c.c", "only_static();", "SEED")])
        self.assertEqual(es[0]["next_symbols"], ["a_g"])                # 呼び出し元のファイルの static
        self.assertEqual(es[1]["next_symbols"], ["c_g"])          # 他のファイルの static を除く
        self.assertEqual(es[2]["next_symbols"], ["a_g"])          # マクロ本体の中の呼び出し
        self.assertEqual(es[3]["next_symbols"], ["o_g"])          # 絞った結果が0件なら全定義

    def test_seed_summary_without_caller_uses_all_definitions(self):
        state = self._state(IDF, "slice", pending=["dup", "s_writer"])
        out = self.root / "s.json"
        self._run(["seed-summary", "--path", str(state), "--out", str(out)])
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(payload["summaries"]["dup"]["globals"], ["a_g", "b_g", "c_g"])
        self.assertEqual(payload["summaries"]["s_writer"]["globals"], ["s_count[FILE:a.c]"])
        self.assertEqual(payload["name_only"], ["a_g", "b_g", "c_g"])   # 同名の定義を2件以上使った要約

    def test_seed_summary_file_scoped_seed(self):
        state = self._state(IDF, "slice", pending=["dup[FILE:b.c]"])
        out = self.root / "s.json"
        self._run(["seed-summary", "--path", str(state), "--out", str(out)])
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(payload["summaries"]["dup"]["globals"], ["b_g"])
        self.assertEqual(payload["name_only"], [])

    # 8. ヒット側の除外
    def test_variable_hit_exclusions(self):
        v = {"g_v": "variable", "srv.dirty": "variable", "server.dirty": "variable"}
        es = self._cls([("a.c", "struct st { int g_v; }", "g_v"), ("a.c", "p->g_v = 1", "g_v"),
                        ("a.c", ".g_v = 1", "g_v"), ("a.c", "int g_v = 0; use(g_v)", "g_v"),
                        ("lib.h", "proto_with_param", "g_v"), ("a.c", "void reads_gv", "g_v"),
                        ("b.c", "server.dirty = 1", "server.dirty")], kinds=v)
        self.assertEqual([e["note"] for e in es[:5]] + [es[6]["note"]],
                         ["slice: member-name", "slice: member-name", "slice: member-name",
                          "slice: shadowed-local", "slice: param-name", "slice: shadowed-local"])
        self.assertNotEqual(es[5]["classification"], "false-positive")
        # 種類が分からないシンボルには other-static 以外を適用しない
        [e] = self._cls([("a.c", "p->g_v = 1", "g_v")])
        self.assertNotEqual(e["classification"], "false-positive")

    def test_other_static(self):
        es = self._cls([("b.c", "s_count = 1", "s_count"), ("b.c", "s_count = 1", "s_count", "s_count[FILE:b.c]"),
                        ("a.c", "srv.dirty = 1", "srv.dirty"), ("lib.h", "return h_inline_b(x)", "h_inline_b"),
                        ("a.c", "use(MIN(x, 1))", "MIN"), ("e.c", "return (foo)(3)", "foo"),
                        ("d2.cpp", "return x.size()", "size"), ("d2.cpp", "count++", "count")], h_as="c")
        self.assertEqual(es[0]["note"], "slice: other-static")
        self.assertNotEqual(es[1]["classification"], "false-positive")     # [FILE:…] のエントリ
        self.assertEqual(es[2]["note"], "slice: other-static")              # root.field は根の名前
        for e in es[3:7]:   # ヘッダの static inline／ヘッダにもあるマクロ／同じファイルの外部リンケージの定義
            self.assertNotEqual(e["classification"], "false-positive", e)
        self.assertEqual(es[7]["note"], "slice: other-static")              # 無名名前空間の変数
        [e] = self._cls([("b.c", "s_count = 1", "s_count")], seeds=["s_count"])   # シードは全域を判定する
        self.assertNotEqual(e["classification"], "false-positive")

    def test_cpp_member_and_default_value_are_not_excluded(self):
        es = self._cls([("d2.cpp", "this->x_ = 1", "x_"), ("d2.cpp", "int opt(int n = g_limit)", "g_limit")],
                       kinds={"x_": "variable", "g_limit": "variable"}, h_as="cpp")
        self.assertTrue(all(e["classification"] != "false-positive" for e in es), es)

    def test_python_member_import_and_default(self):
        k = {"CONF": "variable"}
        es = self._cls([("mod.py", "obj.CONF", "CONF"), ("mod.py", "a.b.CONF", "CONF"),
                        ("mod.py", "def f(x=CONF)", "CONF"), ("mod.py", "o.run()", "run")], kinds=k)
        self.assertEqual(es[0]["note"], "slice: member-name")
        self.assertNotEqual(es[1]["classification"], "false-positive")      # import 名から始まる属性の連鎖
        self.assertNotEqual(es[2]["classification"], "false-positive")      # 既定値の式
        self.assertEqual(es[3]["identity"], "name-only")                    # 2つのクラスに同名のメソッド

    # 9・19. 同一性
    def test_identity_values(self):
        es = self._cls([("a.c", "s_count = SEED", "s_count", "s_count[FILE:a.c]"),
                        ("a.c", "g_ext = SEED", "g_ext"), ("a.c", "use(g_twice)", "g_twice"),
                        ("a.c", "struct st { int g_v; }", "g_v")], kinds={"g_v": "variable"})
        self.assertEqual([e["identity"] for e in es], ["resolved", "resolved", "name-only", "—"])
        [e] = self._cls([("a.c", "use(g_twice)", "g_twice")], engine="rule")
        self.assertEqual(e["identity"], "name-only")

    def test_fallback_to_rule_is_name_only(self):
        def _broken(*_a, **_kw):
            raise RuntimeError("boom")
        with patch.object(mod, "judge_hit", _broken):
            [e] = self._cls([("a.c", "g_ext = SEED", "g_ext")])
        self.assertEqual(e["identity"], "name-only")

    def test_seed_identity_counts_other_files_statics(self):
        es = self._cls([("b.c", "s_count = 1", "s_count"), ("a.c", "s_ret(void)", "s_ret")],
                       seeds=["s_count", "s_ret"])
        self.assertEqual([e["identity"] for e in es], ["name-only", "resolved"])

    # 10. C++ のメソッド
    def test_cpp_method_unresolved_member_is_unknown(self):
        es = self._cls([("d2.cpp", "x_ = SEED", "SEED"), ("d2.cpp", "last_secs_ = SEED", "SEED")], h_as="cpp")
        kinds0 = {k for k, *_ in es[0]["slice"]["escapes"]}
        self.assertEqual(kinds0, {"unknown", "out"})
        self.assertIn("last_secs_", es[1]["next_symbols"])      # ヘッダの誤った解析で外部から見える名前
        self.assertIn("last_secs_", es[1]["name_only_symbols"])  # 暗黙の this のメンバーと区別できない

    # 11・13. global-init
    def test_global_init_in_ifdef_and_self(self):
        es = self._cls([("a.c", "int g_init2 = SEED", "SEED"),
                        ("a.c", "static int cnt = 0", "cnt", "cnt[FILE:a.c]")])
        self.assertEqual(es[0]["next_symbols"], ["g_init2[FILE:a.c]"])
        self.assertEqual(es[0]["note"], "file-scope:global-init")
        self.assertEqual(es[1]["next_symbols"], [])

    # 12. 関数ポインタの呼び出し
    def test_function_pointer_variable_declared_elsewhere(self):
        state = self._state(IDF, "slice")
        chunk = self.root / "c.json"
        chunk.write_text(json.dumps({"chunk_id": "W1-KS", "hits": [{
            "line_id": "W1-R1", "command_id": "W1-C1", "symbol": "SEED", "scope_file": None, "entry": "SEED",
            "file": "c.c", "line_no": _line_of(IDF / "c.c", "fp_var(SEED)"), "matched_text": ""}]}),
            encoding="utf-8")
        out = self.root / "o.json"
        self._run(["classify", "--path", str(state), "--hits", str(chunk), "--out", str(out)])
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual([u["pattern"] for u in payload["unsupported_patterns"]], ["function-pointer-call"])

    # 14. ブロックスコープの extern
    def test_block_scope_extern(self):
        es = self._cls([("a.c", "g_blk = SEED", "SEED"), ("a.c", "use(g_blk)", "g_blk")],
                       kinds={"g_blk": "variable"})
        self.assertEqual(es[0]["next_symbols"], ["g_blk"])
        self.assertNotEqual(es[1]["classification"], "false-positive")

    # 16・20. Repo.is_static_def
    def test_is_static_def(self):
        r = self._repo_index(h_as="c")
        f_of = {}
        for name in ("fw", "fw2", "foo", "size", "sm", "s_writer", "h_ret"):
            mod.load.cache_clear()   # キャッシュに依存しない
            f_of[name] = r.defs(name)
        self.assertTrue(r.is_static_def(f_of["fw"][0]))      # 前方宣言だけが static
        self.assertTrue(r.is_static_def(f_of["fw2"][0]))     # ポインタを返す前方宣言
        self.assertTrue(r.is_static_def(f_of["s_writer"][0]))
        self.assertFalse(r.is_static_def(f_of["foo"][0]))    # 同名の関数形式マクロ
        self.assertFalse(r.is_static_def(f_of["size"][0]))   # X::size（同名の static 変数）
        self.assertFalse(r.is_static_def(f_of["sm"][0]))     # クラス本体の中の static メソッド
        self.assertFalse(r.is_static_def(f_of["h_ret"][0]))  # ヘッダ
        es = self._cls([("a.c", "int fw(void) { return SEED", "SEED"), ("d2.cpp", "sm() { return SEED", "SEED"),
                        ("d2.cpp", "X::size() { return SEED", "SEED")], h_as="cpp")
        self.assertEqual([e["next_symbols"] for e in es], [["fw[FILE:a.c]"], ["sm"], ["size"]])

    # 17・22. マクロ
    def test_macro_def_entries(self):
        es = self._cls([("a.c", "#define MIN2 (SEED", "SEED"), ("a.c", "#define LOCALMAC (SEED", "SEED")])
        self.assertEqual(es[0]["next_symbols"], ["MIN2"])
        self.assertEqual(es[1]["next_symbols"], ["LOCALMAC[FILE:a.c]"])
        self.assertEqual(es[1]["next_symbol_kinds"], {"LOCALMAC[FILE:a.c]": "macro"})


if __name__ == "__main__":
    unittest.main()
