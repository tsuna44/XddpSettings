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
        self.assertEqual(nxt, {8: [], 11: [], 15: ["size[CLASS:Box]"], 19: ["pick"]})
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
                                     "frontier_kinds": kinds or {}, "seed_keys": list(seeds), "hits": rows}),
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
    def test_cpp_method_member_and_unresolved_global(self):
        es = self._cls([("d2.cpp", "x_ = SEED", "SEED"), ("d2.cpp", "last_secs_ = SEED", "SEED")], h_as="cpp")
        kinds0 = {k for k, *_ in es[0]["slice"]["escapes"]}
        self.assertEqual(kinds0, {"global", "out"})
        self.assertIn("x_[CLASS:X]", es[0]["next_symbols"])     # クラスの索引でメンバーと決まった書き込み
        self.assertNotIn("x_[CLASS:X]", es[0]["name_only_symbols"])
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
        self.assertEqual([e["next_symbols"] for e in es], [["fw[FILE:a.c]"], ["sm[CLASS:X]"], ["size[CLASS:X]"]])

    # 17・22. マクロ
    def test_macro_def_entries(self):
        es = self._cls([("a.c", "#define MIN2 (SEED", "SEED"), ("a.c", "#define LOCALMAC (SEED", "SEED")])
        self.assertEqual(es[0]["next_symbols"], ["MIN2"])
        self.assertEqual(es[1]["next_symbols"], ["LOCALMAC[FILE:a.c]"])
        self.assertEqual(es[1]["next_symbol_kinds"], {"LOCALMAC[FILE:a.c]": "macro"})



CMF = FIX / "cppmacro"


class LoopMacroTest(unittest.TestCase):
    """文のループマクロの書き換え（preprocess_c。tree-sitter を使わない）。"""

    def _pre(self, text: str) -> list:
        src = text.encode()
        out = mod.preprocess_c(src)
        self.assertEqual(out.count(b"\n"), src.count(b"\n"))      # 行数を変えない
        return out.decode().split("\n")

    def test_c_loop_macros_rewritten(self):
        lines = self._pre(
            "void f(struct interface *ifp)\n"
            "{\n"
            "\tfrr_each (if_connected, ifp->connected, ifc) {\n"
            "\t\tuse(ifc);\n"
            "\t}\n"
            "\tif (x)\n"
            "\t\tfrr_each (a, b, c) {\n"
            "\t\t}\n"
            "\telse\n"
            "\t\tfrr_each (a, b, c) {\n"
            "\t\t}\n"
            "\t/* comment */\n"
            "\tfrr_each (a, b, c) {\n"
            "\t}\n"
            "#endif\n"
            "\tfrr_each (a, b, c) {\n"
            "\t}\n"
            "\tfrr_each (if_connected, ifp->connected, ifc)\n"
            "\t{\n"
            "\t\tuse(ifc);\n"
            "\t}\n"
            "}\n")
        self.assertEqual(lines[2], "\tfor (;__xddp_iter(if_connected, ifp->connected, ifc);) {")
        for i in (6, 9, 12, 15):
            self.assertIn("__xddp_iter(a, b, c)", lines[i], i)
        self.assertEqual(lines[17], "\tfor (;__xddp_iter(if_connected, ifp->connected, ifc);)")   # Allman
        self.assertEqual(lines[18], "\t{")
        self.assertEqual(lines[19], "\t\tuse(ifc);")

    def test_cpp_constructs_not_rewritten(self):
        text = (
            "class periodic_worker {\n"
            "public:\n"
            "    periodic_worker(const std::function<void()> &callback_fun,\n"
            "                    std::chrono::seconds interval) {\n"
            "    }\n"
            "    periodic_worker(int a) {\n"
            "    }\n"
            "    holder(int a) : a_(a) {\n"
            "    }\n"
            "    holder(int v) const {\n"
            "    }\n"
            "    widget(int a) override {\n"
            "    }\n"
            "    widget(int a) noexcept {\n"
            "    }\n"
            "    template <typename T>\n"
            "    make(T v) {\n"
            "    }\n"
            "};\n"
            "void g() {\n"
            "    try {\n"
            "    }\n"
            "    catch (const std::exception &ex) {\n"
            "    }\n"
            "    catch (...)\n"
            "    {\n"
            "    }\n"
            "}\n"
            "    void\n"
            "    gnu_style(int a)\n"
            "    {\n"
            "    }\n")
        self.assertEqual(self._pre(text), text.split("\n"))


@unittest.skipUnless(HAVE_TS, "tree-sitter が無い")
class CppPreprocessTest(_Base):
    def _repo(self):
        r = mod.Repo(str(CMF), h_as="cpp")
        r.build_index()
        return r

    def test_no_namespace_function_and_plain_class_names(self):
        r = self._repo()
        sf = r.file("sink.cpp")
        funcs = {f.name: f for f in sf.funcs()}
        self.assertNotIn("namespace", funcs)
        self.assertEqual({n: funcs[n].cls for n in ("flush_", "flush_all", "run")},
                         {"flush_": "base_sink", "flush_all": "holder", "run": "wrapper"})
        self.assertEqual(sf.src.count(b"\n"), sf.orig_src.count(b"\n"))
        for name, needle in (("flush_", "MY_INLINE void base_sink::flush_"), ("nested_fn", "int nested_fn")):
            self.assertEqual(funcs[name].node.start_point[0] + 1, _line_of(CMF / "sink.cpp", needle))
        self.assertTrue(funcs["s_all"].static_kw)       # すべての定義が static を含むマクロは static を残す
        self.assertFalse(funcs["s_some"].static_kw)     # 一部の定義だけが含むマクロは残さない
        self.assertIn(b"    virtual void flush_();", sf.src)
        self.assertIn(b"    virtual       void log_(int v);", sf.src)
        self.assertFalse(any(n.type == "ERROR" for n in mod.walk(sf.root)))

    def test_neutralized_macro_hits(self):
        hits = [("sink.cpp", _line_of(CMF / "sink.cpp", "MY_INLINE void base_sink::flush_"), "MY_INLINE"),
                ("sink.cpp", _line_of(CMF / "sink.cpp", "MY_API int g_level"), "MY_API"),
                ("sink.cpp", _line_of(CMF / "sink.cpp", "// MY_INLINE is used"), "MY_INLINE"),
                ("sink.cpp", _line_of(CMF / "sink.cpp", " MY_INLINE in a block comment"), "MY_INLINE"),
                ("sink.cpp", _line_of(CMF / "sink.cpp", "MY_INLINE int also"), "MY_INLINE"),
                ("sink.cpp", _line_of(CMF / "sink.cpp", "MY_NS_BEGIN"), "MY_NS_BEGIN"),
                ("sink.cpp", _line_of(CMF / "sink.cpp", '"MY_INLINE"'), "MY_INLINE")]
        _payload, by_id = self._classify(CMF, hits, "slice", h_as="cpp")
        es = [by_id[f"W0-R{n}"] for n in range(1, len(hits) + 1)]
        for i in (0, 1, 4, 5):
            self.assertEqual((es[i]["note"], es[i]["next_symbols"]), ("file-scope:neutralized-macro", []), i)
            self.assertEqual(mod.LV.propagation_label(es[i]["classification"], es[i]["slice"]),
                             "slice(none=neutralized-macro)")
        for i in (2, 3, 6):
            self.assertEqual(es[i]["note"], "slice: comment/string/include", i)

    def test_macro_def_of_neutralized_macro_is_not_sent(self):
        hits = [("macros.h", _line_of(CMF / "macros.h", "#define MY_ALIAS MY_INLINE"), "MY_INLINE"),
                ("macros.h", _line_of(CMF / "macros.h", "#define MY_NS_BEGIN namespace MY_NAMESPACE"), "MY_NAMESPACE"),
                ("macros.h", _line_of(CMF / "macros.h", "#define BAD_DECOR"), "_NOT_DEFINED_HERE")]
        _payload, by_id = self._classify(CMF, hits, "slice", h_as="cpp")
        self.assertEqual(by_id["W0-R1"]["next_symbols"], [])
        self.assertEqual(by_id["W0-R1"]["slice"]["file_scope"], "macro-def")
        self.assertEqual(by_id["W0-R2"]["next_symbols"], [])
        self.assertEqual(by_id["W0-R3"]["next_symbols"], ["BAD_DECOR"])     # 置き換えないマクロは今どおり送る

    def test_reserved_word_is_parse_artifact(self):
        line = _line_of(CMF / "pool.cpp", "namespace details {")
        payload, by_id = self._classify(CMF, [("pool.cpp", line, "details"), ("pool.cpp", line, "details")],
                                        "slice", h_as="cpp")
        self.assertEqual([by_id[k]["next_symbols"] for k in ("W0-R1", "W0-R2")], [[], []])
        self.assertEqual(by_id["W0-R1"]["enclosing_function"], "namespace")
        pa = [u for u in payload["unsupported_patterns"] if u["pattern"] == "parse-artifact"]
        self.assertEqual(len(pa), 1)
        self.assertEqual(pa[0]["location"], "pool.cpp (namespace)")
        self.assertIn("2 件", pa[0]["note"])

    def test_c_keeps_cxx_reserved_words(self):
        hits = [("reserved.c", _line_of(CMF / "reserved.c", "return x + SEED"), "SEED"),
                ("reserved.c", _line_of(CMF / "reserved.c", "int new = SEED"), "SEED")]
        payload, by_id = self._classify(CMF, hits, "slice", h_as="cpp")
        self.assertEqual(by_id["W0-R1"]["next_symbols"], ["private"])
        self.assertEqual(by_id["W0-R2"]["next_symbols"], ["new[FILE:reserved.c]"])
        self.assertEqual(payload["unsupported_patterns"], [])

    def test_macro_body_call_extraction_keywords_unchanged(self):
        self.assertTrue({"defined", "typeof", "__typeof__", "_Generic"} <= mod._C_KEYWORDS)


class ReservedRuleTest(_Base):
    def test_rule_engine_drops_reserved_enclosing(self):
        rf = mod.RuleFile(str(CMF / "pool.cpp"), "cpp")
        unsupported = []
        hit = {"line_id": "W0-R1", "file": "pool.cpp", "line_no": 2, "symbol": "details"}
        e = mod.entry_from_rule(hit, mod.RuleVerdict("rule", func=mod.RuleFunc("namespace", 0, 10, 40)), rf,
                                unsupported)
        self.assertEqual(e["next_symbols"], [])
        self.assertEqual([u["pattern"] for u in unsupported], ["parse-artifact"])
        rfc = mod.RuleFile(str(CMF / "reserved.c"), "c")
        e = mod.entry_from_rule(dict(hit, file="reserved.c"),
                                mod.RuleVerdict("rule", func=mod.RuleFunc("private", 0, 10, 40)), rfc, [])
        self.assertEqual(e["next_symbols"], ["private"])

    def test_ext_lang_shared_with_macros(self):
        import specout_bfs as bfs
        import specout_macros as macros
        self.assertEqual({k: v for k, v in mod.EXT_LANG.items() if k != ".py"}, macros.C_CXX_EXT_LANG)
        self.assertEqual(set(bfs.CPP_SOURCE_EXTS), {e for e, l in macros.C_CXX_EXT_LANG.items() if l == "cpp"})
        for ext in macros.C_CXX_EXT_LANG:
            for h_as in ("c", "cpp"):
                self.assertEqual(mod.lang_of("a" + ext, h_as), macros.c_cxx_lang("a" + ext, h_as))
                self.assertIsNone(mod.lang_of("a" + ext.upper(), h_as))
            self.assertIn(ext, mod.ENGINE_EXTS)                 # search の判定先（_route）は ENGINE_EXTS で決まる
            self.assertNotIn(ext.upper(), mod.ENGINE_EXTS)



CCF = FIX / "cppclass"


@unittest.skipUnless(HAVE_TS, "tree-sitter が無い")
class CppClassTest(_Base):
    """C++ のクラス単位の同一性（[CLASS:…]）。"""

    def _repo(self):
        r = mod.Repo(str(CCF), h_as="cpp")
        r.build_index()
        return r

    def _hits(self, cases, summaries=None, kinds=None, seeds=()):
        """cases: [(file, needle, symbol, entry)]。戻り値: classification のエントリ（cases の順）と出力 JSON。"""
        state = self._state(CCF, "slice", "cpp")
        rows = [{"line_id": f"W1-R{n}", "command_id": "W1-C1", "symbol": sym, "scope_file": None, "entry": entry,
                 "file": f, "line_no": _line_of(CCF / f, needle), "matched_text": ""}
                for n, (f, needle, sym, entry) in enumerate(cases, 1)]
        chunk = self.root / "c.json"
        chunk.write_text(json.dumps({"chunk_id": "W1-KS", "frontier_summaries": summaries or {},
                                     "frontier_kinds": kinds or {}, "seed_keys": list(seeds), "hits": rows}),
                         encoding="utf-8")
        out = self.root / "o.json"
        self._run(["classify", "--path", str(state), "--hits", str(chunk), "--out", str(out)])
        payload = json.loads(out.read_text(encoding="utf-8"))
        by_id = {e["line_id"]: e for e in payload["classification"]}
        return [by_id[f"W1-R{n}"] for n in range(1, len(cases) + 1)]

    # 7. クラスの索引
    def test_class_index(self):
        r = self._repo()
        self.assertEqual(r.class_info("file_sink").bases, [("base_sink", False)])
        self.assertEqual(r.class_info("holder").members, {"fs_": "file_sink"})
        self.assertEqual(r.resolve_type("sink_ptr"), "sink")                 # using（スマートポインタを外す）
        self.assertTrue(r.method_virtual("rotating_sink", "flush_"))         # override の指定子
        self.assertTrue(r.method_virtual("file_sink", "sink_it_"))
        self.assertIsNone(r.method_virtual("error_t", "report"))             # 外部のクラス（std::exception）を継承・指定子なし
        self.assertIsNone(r.method_virtual("crtp", "tick"))                  # テンプレート引数を基底に持つ
        self.assertFalse(r.method_virtual("plain", "helper"))
        self.assertEqual(r.chain("error_t"), ([], False, True))
        self.assertEqual(r.declaring("rotating_sink", "sink_it_"), ("file_sink", True))
        self.assertEqual(r.declaring("crtp", "nope"), (None, False))        # 索引に無い基底で決まらない
        self.assertEqual(r.declaring("plain", "nope"), (None, True))
        self.assertEqual(r.subclasses("base_sink"), ["file_sink", "null_sink", "rotating_sink"])
        self.assertTrue(r.class_info("plain").methods["helper"] is False)    # クラスの外の定義（plain::helper）
        self.assertFalse(r.is_cpp_method(next(f for f in r.file("use.cpp").funcs() if f.name == "compute")))

    def test_type_alias_conflict_is_undetermined(self):
        r = self._repo()
        r._add_alias("dup_t", "file_sink")
        r._add_alias("dup_t", "null_sink")
        self.assertIsNone(r.resolve_type("dup_t"))

    # 10. 受け手のクラスと判定の表
    def test_receiver_relations(self):
        es = self._hits([
            ("use.cpp", "fs.sink_it_(1)", "sink_it_", "sink_it_[CLASS:file_sink]"),          # 引数の宣言の型 = X
            ("use.cpp", "ns->sink_it_(2)", "sink_it_", "sink_it_[CLASS:file_sink]"),         # 兄弟クラス
            ("use.cpp", "bs->sink_it_(4)", "sink_it_", "sink_it_[CLASS:file_sink]"),         # 基底の virtual
            ("use.cpp", "a->sink_it_(5)", "sink_it_", "sink_it_[CLASS:file_sink]"),          # auto（決められない）
            ("sinks.hpp", "void flush_() override { rotations_", "flush_", "flush_[CLASS:file_sink]"),  # 間で宣言し直し
            ("sinks.hpp", "void run() { fs_->sink_it_(9); }", "sink_it_", "sink_it_[CLASS:file_sink]"),  # メンバーの型
            ("use.cpp", "    helper();", "helper", "helper[CLASS:plain]"),                  # 自由関数の中（this が無い）
            ("use.cpp", "sp->log(3)", "log", "log[CLASS:base_sink]"),                         # 型の別名
            ("use.cpp", "void detail::compute", "compute", "compute[CLASS:detail]"),          # 名前空間名
            ("sinks.hpp", "void report(int code)", "report", "report[CLASS:error_t]"),
        ], kinds={"sink_it_[CLASS:file_sink]": "function"})
        self.assertEqual([e["identity"] for e in es],
                         ["resolved", "—", "resolved", "name-only", "—", "resolved", "—", "resolved",
                          "name-only", "resolved"])
        self.assertEqual([es[i]["note"] for i in (1, 4, 6)], ["slice: other-class"] * 3)

    def test_free_function_in_fully_indexed_method_is_other_class(self):
        r = self._repo()
        self.assertEqual(r.class_relation("plain", "free", None, "helper"), mod.REL_OTHER)
        self.assertEqual(r.class_relation("crtp", "class", "plain", "tick"), mod.REL_NAME_ONLY)   # 索引に無い基底
        self.assertEqual(r.class_relation("nope", "class", "plain", "x"), mod.REL_NAME_ONLY)    # X が索引に無い
        self.assertEqual(r.class_relation("error_t", "class", "plain", "report"), mod.REL_OTHER)

    def test_variable_and_parameter_names_are_not_methods(self):
        k = {"size[CLASS:helper_t]": "function", "name[CLASS:helper_t]": "function"}
        es = self._hits([
            ("use.cpp", "void use_names(const char *name", "name", "name[CLASS:helper_t]"),   # 引数の宣言子
            ("use.cpp", "int size = 0;", "size", "size[CLASS:helper_t]"),                      # 変数の宣言子
            ("use.cpp", "size = t.size() + v.size();", "size", "size[CLASS:helper_t]"),        # 素の出現は同名のローカル変数
            ("use.cpp", "make_loc().name;", "name", "name[CLASS:helper_t]"),                   # 呼ばずに参照する obj.m
            ("use.cpp", "    h.size();", "size", "size[CLASS:helper_t]"),
        ], kinds=k)
        self.assertEqual([e["note"] for e in es[:4]], ["slice: other-class"] * 4)
        self.assertEqual(es[4]["identity"], "resolved")
        es = self._hits([("use.cpp", "int size = 0;", "size", "size[CLASS:helper_t]")],
                        kinds={"size[CLASS:helper_t]": "variable"})
        self.assertNotEqual(es[0]["note"], "slice: other-class")                       # メソッドのエントリだけ

    def test_receiver_type_outside_repository(self):
        r = self._repo()
        f = next(f for f in r.file("use.cpp").funcs() if f.name == "use_names")
        xs = [x for x in mod.walk(f.body) if x.type == "field_identifier" and mod.txt(x) == "size"]
        self.assertEqual([r.outside_receiver(x, f, "helper_t") for x in xs], [True, True, False])  # 別名→std::string・vector・helper_t
        t = next(f for f in r.file("use.cpp").funcs() if f.name == "tsize")
        x = next(x for x in mod.walk(t.body) if x.type == "field_identifier")
        self.assertFalse(r.outside_receiver(x, t, "helper_t"))                          # テンプレート引数
        es = self._hits([("use.cpp", "template <typename T> void tsize", "size", "size[CLASS:helper_t]")],
                        kinds={"size[CLASS:helper_t]": "function"})
        self.assertEqual(es[0]["identity"], "name-only")

    def test_text_type_name(self):
        self.assertEqual(mod._text_type_name("const fmt::basic_memory_buffer<char, 250>"), "basic_memory_buffer")
        self.assertIsNone(mod._text_type_name("decltype(f())"))

    def test_member_variable_hits(self):
        k = {"size_[CLASS:file_sink]": "variable"}
        es = self._hits([
            ("sinks.hpp", "void set(int size_) { this->size_ = size_; }", "size_", "size_[CLASS:file_sink]"),
            ("sinks.hpp", "file_sink(int n) : size_(n) {}", "size_", "size_[CLASS:file_sink]"),
        ], kinds=k)
        self.assertEqual([e["identity"] for e in es], ["resolved", "resolved"])   # this->m・初期化子並び（手順 4）

    # 8. 次の波のシンボル
    def test_next_symbols(self):
        es = self._hits([
            ("sinks.hpp", "void sink_it_(int v) override { size_ += v; }", "v", "v"),
            ("use.cpp", "void detail::compute(int v) { g_state = v; }", "v", "v"),
            ("use.cpp", "void plain::helper() { value_ = 2; }", "value_", "value_"),
        ])
        # 暗黙の this のメンバーへの書き込み（out(this) でメソッドの呼び出し元もクラスを付けて送る）
        self.assertEqual(es[0]["next_symbols"], ["sink_it_[CLASS:file_sink]", "size_[CLASS:file_sink]"])
        self.assertEqual(es[0]["name_only_symbols"], [])
        self.assertEqual(es[0]["next_symbol_kinds"], {"sink_it_[CLASS:file_sink]": "function",
                                                     "size_[CLASS:file_sink]": "variable"})
        self.assertNotIn("compute[CLASS:detail]", es[1]["next_symbols"])          # 名前空間で修飾した自由関数
        r = self._repo()
        f = next(f for f in r.file("sinks.hpp").funcs() if f.name == "flush_" and f.cls == "file_sink")
        v = mod.HitVerdict("sliced", func=f, push_up=True, result=mod.Result())
        e = mod.entry_from_slice({"line_id": "x", "file": "sinks.hpp", "line_no": 1, "symbol": "s"}, v, [], r)
        self.assertEqual(e["next_symbols"], ["flush_[CLASS:file_sink]"])
        self.assertEqual(list(e["next_symbol_summaries"]), ["flush_[CLASS:file_sink]"])
        py = mod.Repo(str(FIX / "identity"), h_as="c")
        py.build_index()
        pf = next(f for f in py.file("mod.py").funcs() if f.is_method)
        e = mod.entry_from_slice({"line_id": "x", "file": "mod.py", "line_no": 1, "symbol": "s"},
                                 mod.HitVerdict("sliced", func=pf, push_up=True, result=mod.Result()), [], py)
        self.assertNotIn("[CLASS:", "".join(e["next_symbols"]))                  # Python のメソッドには付けない

    def test_free_function_struct_member_write_is_not_class_entry(self):
        es = self._hits([("sinks.hpp", "a->extra = v;", "v", "v")])
        self.assertFalse(any("[CLASS:" in n for n in es[0]["next_symbols"]), es[0]["next_symbols"])

    def test_this_and_typed_object_member_writes(self):
        es = self._hits([("sinks.hpp", "void set(int size_) { this->size_ = size_; }", "size_", "size_")],
                        kinds={"size_": "value"})
        self.assertIn("size_[CLASS:file_sink]", es[0]["next_symbols"])

    # 9. クラスを指定した要約
    def test_class_summary(self):
        r = self._repo()
        s_file = r.summary("sink_it_", cls="file_sink")
        self.assertEqual(s_file["globals"], {"size_[CLASS:file_sink]"})
        self.assertNotIn("cls_fallback", s_file)
        s_null = r.summary("sink_it_", cls="null_sink")
        self.assertEqual(s_null["globals"], set())                                 # 兄弟の要約が混ざらない
        s_base = r.summary("flush_", cls="base_sink")                             # 純粋仮想: 派生クラスの override だけ
        self.assertEqual(s_base["globals"], {"size_[CLASS:file_sink]", "rotations_[CLASS:rotating_sink]"})
        s_fs = r.summary("flush_", cls="file_sink")                                 # X の兄弟（null_sink）は入らない
        self.assertEqual(s_fs["globals"], {"size_[CLASS:file_sink]", "rotations_[CLASS:rotating_sink]"})
        s_rot = r.summary("sink_it_", cls="rotating_sink")                        # 継承しただけ: 基底の定義
        self.assertEqual(s_rot["globals"], {"size_[CLASS:file_sink]"})
        fb = r.summary("sink_it_", cls="nope")
        self.assertTrue(fb["cls_fallback"])
        plain = r.summary("sink_it_")
        self.assertNotIn("cls_fallback", plain)                                    # キャッシュを共有しない
        r2 = self._repo()
        r2.summary("sink_it_")
        self.assertTrue(r2.summary("sink_it_", cls="nope")["cls_fallback"])

    def test_call_effects_uses_class_summaries(self):
        r = self._repo()
        f = next(f for f in r.file("use.cpp").funcs() if f.name == "use_sinks")
        call = next(n for n in mod.walk(f.body) if n.type == "call_expression" and "ns->sink_it_" in mod.txt(n))
        esc, _w = mod.call_effects(call, f, r, {}, set(), {"sink_it_[CLASS:file_sink]": {
            "returns": False, "out": [], "globals": ["boom"], "side": False, "closure": []}}, 0)
        self.assertNotIn("boom", {d for _k, d, *_ in esc})                         # 兄弟クラスの要約は使わない
        call = next(n for n in mod.walk(f.body) if n.type == "call_expression" and "a->sink_it_" in mod.txt(n))
        esc, _w = mod.call_effects(call, f, r, {}, set(), {"sink_it_[CLASS:file_sink]": {
            "returns": False, "out": [], "globals": ["boom"], "side": False, "closure": []}}, 0)
        globals_ = {d for _k, d, *_ in esc}
        self.assertIn("boom", globals_)                                             # 決まらない: 全クラスの和
        self.assertIn("a", {w[0] for w in _w})                                      # ＋全定義の要約（out(this)）
        self.assertNotIn("size_[CLASS:file_sink]", globals_)                      # 呼び出し先のメンバー変数は加えない

    def test_callee_member_globals_are_not_caller_exits(self):
        r = self._repo()
        f = next(f for f in r.file("use.cpp").funcs() if f.name == "use_sinks")
        call = next(n for n in mod.walk(f.body) if n.type == "call_expression" and "fs.sink_it_" in mod.txt(n))
        esc, w = mod.call_effects(call, f, r, {}, set(), {}, 0)
        self.assertEqual(esc, [])                                                   # size_[CLASS:file_sink] を送らない
        self.assertEqual([x[0] for x in w], ["fs"])                                 # 受け手への書き込みで伝わる
        f = next(f for f in r.file("sinks.hpp").funcs() if f.name == "flush" and f.cls == "base_sink")
        call = next(n for n in mod.walk(f.body) if n.type == "call_expression")              # flush_();
        self.assertEqual(mod.call_effects(call, f, r, {}, set(), {}, 0), ([], [("this", "member", True, None)]))
        self.assertEqual(r.summary("flush", cls="base_sink")["out"], {"this"})            # this を省いた呼び出しでも伝わる
        self.assertEqual(sorted(mod._callee_globals({"globals": {"m[CLASS:B]", "g", "s[FILE:a.c]"},
                                                     "name_only": {"g"}})),
                         [("global", "g", True), ("global", "s[FILE:a.c]", False)])

    # 12. seed-summary
    def test_seed_summary_class_target(self):
        state = self._state(CCF, "slice", "cpp", pending=["sink_it_[CLASS:file_sink]", "sink_it_[CLASS:nope]"])
        out = self.root / "s.json"
        self._run(["seed-summary", "--path", str(state), "--out", str(out)])
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(payload["summaries"]["sink_it_[CLASS:file_sink]"]["name_only"], [])
        self.assertEqual(payload["summaries"]["sink_it_[CLASS:nope]"]["name_only"], ["size_[CLASS:file_sink]"])

    def test_seed_keys_and_value_judgment(self):
        es = self._hits([("use.cpp", "fs.sink_it_(1)", "sink_it_", "sink_it_[CLASS:file_sink]")],
                        seeds=["sink_it_[CLASS:file_sink]"],
                        summaries={"sink_it_[CLASS:file_sink]": {"returns": True, "out": [], "globals": [],
                                                                 "side": False, "closure": []}})
        self.assertEqual(es[0]["identity"], "resolved")
        self.assertNotEqual(es[0]["slice"]["status"], "write-only")

    def test_rule_engine_class_entry_is_name_only(self):
        state = self._state(CCF, "rule", "cpp")
        chunk = self.root / "c.json"
        chunk.write_text(json.dumps({"chunk_id": "W1-KS", "hits": [{
            "line_id": "W1-R1", "command_id": "W1-C1", "symbol": "sink_it_", "scope_file": None,
            "entry": "sink_it_[CLASS:file_sink]", "file": "use.cpp", "line_no": _line_of(CCF / "use.cpp", "fs.sink_it_"),
            "matched_text": ""}]}), encoding="utf-8")
        out = self.root / "o.json"
        self._run(["classify", "--path", str(state), "--hits", str(chunk), "--out", str(out)])
        [e] = json.loads(out.read_text(encoding="utf-8"))["classification"]
        self.assertEqual(e["identity"], "name-only")

    def test_summary_key_is_shared(self):
        import specout_bfs
        self.assertIs(mod.summary_key, specout_bfs.summary_key)
        self.assertEqual(mod.summary_key("f[CLASS:X]"), "f[CLASS:X]")
        self.assertEqual(mod.summary_key("f[FILE:a.c]"), "f")


CRF = FIX / "cppresolve"
FP_OTHER = ("fp", "other-class", None)


@unittest.skipUnless(HAVE_TS, "tree-sitter が無い")
class CppResolveTest(_Base):
    """受け手のクラスの決め方: 名前空間・列挙（A）、自由関数（B）、名前空間をまたぐ同名クラス（C）、同じ名前空間の同名クラス（D）、
    式の型（E）、テンプレートの包み、構文解析の誤り。"""

    def _repo(self, sub, excludes=None):
        r = mod.Repo(str(CRF / sub), excludes=excludes, h_as="cpp")
        r.build_index()
        return r

    def _judge(self, r, rel, needle, symbol, entry, kind="function"):
        v = mod.judge_hit(r, rel, _line_of(Path(r.root) / rel, needle), symbol, entry=entry, kind=kind)
        return (v.status, v.note, v.identity)

    def _recv(self, r, rel, needle, symbol):
        """needle の行の symbol の出現（行の中の順）ごとの受け手。"""
        sf = r.file(rel)
        row = _line_of(Path(r.root) / rel, needle) - 1
        xs = sorted(mod.find_occurrences(sf, row, symbol), key=lambda x: x.start_byte)
        return [r.receiver(x, sf.func_at(x), symbol) for x in xs]

    # 1. A: 名前空間・列挙
    def test_namespace_and_enum_are_not_methods(self):
        r = self._repo("a")
        for needle, sym, entry in [
            ("lvl_ = level::critical", "critical", "critical[CLASS:logger]"),           # 名前空間で修飾
            ("async_msg_type::flush", "flush", "flush[CLASS:logger]"),                 # enum class で修飾
            ("fmt_lib::format", "format", "format[CLASS:logger]"),                     # 名前空間の別名で修飾
            ("::close(lvl_)", "close", "close[CLASS:logger]"),                         # `::` の修飾
            ("std::swap", "swap", "swap[CLASS:logger]"),
            ("level::level_enum e", "level", "level[CLASS:logger]"),                   # 修飾子の位置
        ]:
            self.assertEqual(self._judge(r, "a.cpp", needle, sym, entry), FP_OTHER, needle)
        for rel, needle, sym in [("a.hpp", "namespace level {", "level"),             # 名前空間の定義の名前
                                 ("a.hpp", "enum class async_msg_type", "flush"),     # 列挙子の宣言
                                 ("a.cpp", "using namespace level;", "level")]:
            self.assertEqual(self._judge(r, rel, needle, sym, f"{sym}[CLASS:logger]"), FP_OTHER, needle)
        # 修飾子が索引のクラス（名前空間 cfg と同じ名前のクラス util::cfg）なら今どおりクラスとして扱う
        self.assertEqual(self._recv(r, "a.cpp", "util::cfg::flush()", "flush"), [("class", "cfg")])
        self.assertEqual(self._judge(r, "a.cpp", "util::cfg::flush()", "flush", "flush[CLASS:cfg]")[2], "resolved")
        # 修飾子がテンプレート引数なら決めない
        self.assertEqual(self._judge(r, "a.cpp", "T::flush()", "flush", "flush[CLASS:logger]")[2], "name-only")
        self.assertEqual(self._judge(r, "a.cpp", 'critical("m")', "critical", "critical[CLASS:logger]")[2],
                         "resolved")

    def test_namespace_with_class_in_excluded_directory_is_undetermined(self):
        # 除外したディレクトリにだけ `class yy` がある名前空間 yy で修飾した出現は、クラスの修飾の可能性があり決めない
        r = self._repo("a", excludes=["vendor/"])
        self.assertEqual(self._judge(r, "a.cpp", "yy::flush();", "flush", "flush[CLASS:logger]")[2], "name-only")

    def test_enum_class_text_is_not_class_name(self):
        r = self._repo("a")
        self.assertNotIn("async_msg_type", r._text_class_names())
        self.assertIn("logger", r._text_class_names())

    # 2. B: 自由関数
    def test_free_function_names_are_not_methods(self):
        r = self._repo("b")
        for rel, needle, sym in [
            ("b.hpp", "void helper();", "helper"),                    # 自由関数の宣言の名前
            ("b.hpp", "inline void log(int v)", "log"),               # 名前空間の関数の定義の名前
            ("b.hpp", "void f();", "f"),
            ("b.cpp", "void run() { helper(); }", "helper"),          # 自由関数の中の修飾なしの呼び出し
            ("b.cpp", "void detail::f() { helper(); }", "helper"),    # 名前空間で修飾した自由関数の中
        ]:
            self.assertEqual(self._recv(r, rel, needle, sym)[-1], ("free", None), needle)
            self.assertEqual(self._judge(r, rel, needle, sym, f"{sym}[CLASS:sink]"), FP_OTHER, needle)
        self.assertEqual(self._judge(r, "b.cpp", "void sink::flush() { helper(); }", "helper",
                                     "helper[CLASS:sink]")[2], "resolved")
        self.assertEqual(self._recv(r, "b.cpp", "void (*hp)() = helper;", "helper"), [(None, None)])  # ファイルスコープ

    # 3. C: 名前空間をまたぐ同名クラス
    def test_namespace_keys_for_same_named_classes(self):
        r = self._repo("c")
        self.assertEqual(sorted(r.class_keys_by_bare["X"]), ["::X", "a::X", "b::X", "outer::inner::X"])
        self.assertEqual(r.class_keys_by_bare["Only"], ["Only"])                    # 重ならないクラスは素の名前
        self.assertEqual(r.class_info("Only").key, "Only")
        self.assertEqual(r.class_info("X"), mod.AMBIGUOUS)
        self.assertEqual(self._recv(r, "c.cpp", "void use_a(X &x)", "foo"), [("class", "a::X")])   # 名前空間の中
        self.assertEqual(self._recv(r, "c.cpp", "void use_b(X &x)", "foo"), [("class", "b::X")])
        self.assertEqual(self._recv(r, "c.cpp", "void use_q(", "foo"), [("class", "a::X"), ("class", "b::X")])  # 修飾
        self.assertEqual(self._recv(r, "c.cpp", "void use_g(X &x)", "foo"), [("class", "::X")])     # 名前空間に属さない
        self.assertEqual(self._recv(r, "c.cpp", "void use_h(", "foo"), [("class", "a::X")])        # メンバー変数の型
        self.assertEqual(r.class_info("Y").bases, [("a::X", False)])                                 # 基底クラス
        self.assertEqual(self._judge(r, "c.cpp", "void use_a(X &x)", "foo", "foo[CLASS:a::X]")[2], "resolved")
        self.assertEqual(self._judge(r, "c.cpp", "void use_b(X &x)", "foo", "foo[CLASS:a::X]"), FP_OTHER)
        self.assertEqual(self._judge(r, "c.cpp", "void use_g(X &x)", "foo", "foo[CLASS:::X]")[2], "resolved")
        self.assertEqual(self._judge(r, "c.cpp", "void use_a(X &x)", "foo", "foo[CLASS:X]")[2], "name-only")
        self.assertEqual(r.cls_key("X", None), "X")                                # 経路を使えなければ決めない

    def test_namespace_macro_and_entry_class(self):
        r = self._repo("c")
        self.assertEqual(r.ns_macro, {"NS": "real", "ns_low": "lowreal"})          # 小文字のマクロ名も
        self.assertEqual(sorted(r.class_keys_by_bare["W"]), ["lowreal::W", "real::W"])
        self.assertEqual(self._recv(r, "c.cpp", "void use_w(", "go"), [("class", "real::W"), ("class", "lowreal::W")])
        self.assertEqual(r.entry_class("inner::X"), "outer::inner::X")             # 途中の経路
        self.assertEqual(r.entry_class("zz::X"), "zz::X")                          # 合わなければそのまま
        self.assertEqual(r.entry_class("a::X"), "a::X")

    def test_next_wave_entry_uses_namespace_key(self):
        r = self._repo("c")
        fs = [f for f in r.file("c.cpp").funcs() if f.name == "foo"]
        nexts = []
        for f in fs:
            v = mod.HitVerdict("sliced", func=f, push_up=True, result=mod.Result())
            nexts += mod.entry_from_slice({"line_id": "x", "file": "c.cpp", "line_no": 1, "symbol": "s"}, v, [], r)[
                "next_symbols"]
        self.assertEqual(nexts, ["foo[CLASS:a::X]", "foo[CLASS:b::X]"])

    # 4. D: 同じ名前空間の同名クラス
    def test_same_namespace_classes_are_merged(self):
        r = self._repo("d")
        info = r.class_info("client")
        self.assertNotEqual(info, mod.AMBIGUOUS)
        self.assertEqual(info.bases, [("base", False)])                            # 和
        self.assertEqual(set(info.methods), {"close", "send", "win_only"})
        self.assertTrue(r.method_virtual("client", "close"))                       # virtual も和
        self.assertIsNone(info.members["fd_"])                                     # 型が違うメンバーは決めない
        self.assertEqual(r.declaring("client", "send"), ("client", True))
        self.assertEqual(r.declaring("client", "win_only"), (None, False))        # 一部の版にしか無い
        self.assertEqual(len(r.class_keys_by_bare["local_t"]), 2)                  # 無名名前空間はまとめない

    # 5. E: 式の型
    def test_expression_receivers(self):
        r = self._repo("e")
        cases = [
            ("for (auto &p : foos_)", "f", "Foo"), ("for (auto &b : bars_)", "f", "Bar"),     # 範囲 for・型の別名の要素
            ("kv.second->f()", "f", "Bar"),                                                     # map の second
            ("make_shared<Foo>(); x->f()", "f", "Foo"), ("new Bar(); y->f()", "f", "Bar"), ("Bar().f();", "f", "Bar"),
            ("baz.bar()->f();", "f", "Bar"), ("make_bar()->f();", "f", "Bar"),                 # メソッド・自由関数の戻り値
            ("Base<int>::member_->f()", "f", "Bar"), ("(*pf).f();", "f", "Foo"), ("v[i].f();", "f", "Foo"),
            ("for (auto &s : xs_)", "f", "Foo"), ("for (auto &s : ys_)", "f", "Bar"),        # 同じ名前の範囲 for の変数
            ("[&](Bar s) { s.f(); }", "f", "Bar"), ("catch (Bar &s) { s.go(); }", "go", "Bar"),  # lambda・catch の引数
            ("if (Bar *s = make_bar())", "f", "Bar"), ("if (auto s = make_bar(); s)", "go", "Bar"),
            ("std::function<void(Bar s)> h; s.f();", "f", "Foo"),                              # 関数型の引数名は変数でない
            ("{ Bar s; s.f(); }", "f", "Bar"), ("{ Foo q; q.f(); }", "f", "Foo"),
        ]
        for needle, sym, cls in cases:
            self.assertEqual(self._recv(r, "e.cpp", needle, sym), [("class", cls)], needle)
        for needle, sym in [("baz.aut().f();", "f"), ("baz.over(1).f();", "f"), ("baz.tmpl<Foo>().f();", "f"),
                            ("    q.go();", "go"),                                          # 見える宣言が無い
                            ("for (auto &[s, lvl]", "go"),                                  # 範囲 for の構造化束縛
                            ("    x.go();", "go")]:                                         # 引数の型で決めない
            self.assertEqual(self._recv(r, "e.cpp", needle, sym), [(None, None)], needle)
        self.assertEqual(self._recv(r, "e.cpp", "[w = s.lock()](Bar s)", "lock"), [("class", "Foo")])  # キャプチャ
        self.assertEqual(self._recv(r, "e.cpp", "[w = s.lock()](Bar s)", "go"), [("class", "Bar")])
        f = next(f for f in r.file("e.cpp").funcs() if f.name == "lam")
        go = next(x for x in mod.walk(f.body) if x.type == "field_identifier" and mod.txt(x) == "go")
        self.assertEqual(r.receiver(go, f, "go"), ("class", "Foo"))                # lambda の外は Foo s
        f = next(f for f in r.file("e.cpp").funcs() if f.name == "bind")
        sf = next(x for x in mod.walk(f.body) if x.type == "field_identifier" and mod.txt(x) == "f")
        self.assertEqual(r.receiver(sf, f, "f"), (None, None))                    # 構造化束縛（同名のメンバー変数がある）
        f = next(f for f in r.file("e.cpp").funcs() if f.name == "shadow")
        xs = sorted((x for x in mod.walk(f.body) if x.type == "field_identifier"), key=lambda x: x.start_byte)
        self.assertEqual([r.receiver(x, f, mod.txt(x)) for x in xs],
                         [("class", "Foo"), ("class", "Bar"), ("class", "Foo")])   # 内側のブロックの同名の宣言

    def test_member_write_exit_with_duplicate_locals(self):
        _payload, es = self._classify(CRF / "e", [("e.cpp", _line_of(CRF / "e" / "e.cpp", "obj.n_ = v; }"), "v")],
                                      "slice", h_as="cpp")
        self.assertIn("n_[CLASS:Foo]", es["W0-R1"]["next_symbols"])

    # 6. テンプレートの包み
    def test_template_wrappers(self):
        r = self._repo("b")
        self.assertEqual(self._judge(r, "b.cpp", "F::template create<int>()", "create", "create[CLASS:sink]")[2],
                         "name-only")                                                # 修飾子はテンプレート引数
        self.assertEqual(self._judge(r, "b.cpp", "s.template flush<int>()", "flush", "flush[CLASS:sink]")[2],
                         "resolved")
        self.assertEqual(self._judge(r, "b.cpp", "bar<int>()", "bar", "bar[CLASS:sink]"), FP_OTHER)  # 自由関数の中

    # 7. 構文解析の誤り
    def test_parse_errors(self):
        r = self._repo("err")
        self.assertTrue(r.file("use.cpp").root.has_error)
        self.assertEqual(r.class_info("K"), mod.AMBIGUOUS)                          # 誤りのあるファイルに定義がある
        self.assertEqual(r.class_keys_by_bare["K"], ["K"])
        self.assertEqual(self._recv(r, "use.cpp", "void ok()", "run"), [("free", None), ("class", "Solo")])  # ERROR の外
        self.assertEqual(self._recv(r, "use.cpp", "in_err() {", "run"), [(None, None)])     # ERROR の中の ns1::run
        self.assertEqual(self._recv(r, "use.cpp", "in_err2() {", "run"), [(None, None)])
        for needle in ("void free_decl();", "use_err() { free_decl(); }"):            # B を当てない
            self.assertEqual(self._judge(r, "use.cpp", needle, "free_decl", "free_decl[CLASS:Solo]")[2], "name-only")

    # 8. 決定性
    def test_order_does_not_change_results(self):
        e = CRF / "e"
        hits = [("e.cpp", _line_of(e / "e.cpp", nd), sym) for nd, sym in [
            ("for (auto &s : xs_)", "f"), ("for (auto &s : ys_)", "f"), ("{ Bar s; s.f(); }", "f"),
            ("[&](Bar s) { s.f(); }", "f"), ("baz.bar()->f();", "f"), ("obj.n_ = v; }", "v")]]

        def by_hit(hs):
            _p, es = self._classify(e, hs, "slice", h_as="cpp")
            return {hs[int(k[4:]) - 1]: {kk: vv for kk, vv in v.items() if kk != "line_id"} for k, v in es.items()}
        self.assertEqual(by_hit(hits), by_hit(list(reversed(hits))))


if __name__ == "__main__":
    unittest.main()
