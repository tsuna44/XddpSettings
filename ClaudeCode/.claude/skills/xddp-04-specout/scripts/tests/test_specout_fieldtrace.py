import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import specout_fieldtrace as mod  # noqa: E402
import specout_slice as SL  # noqa: E402

try:
    SL._ts()
    HAVE_TS = True
except SL.EngineUnavailable:
    HAVE_TS = False

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "fieldtrace"
BATCH = "CHD-CR-1-UR-001.md"
# 標準の題材の言語ごとの確認対象（ADAPTERS に言語を足したら、ここに期待値を足し、fixtures/fieldtrace/{言語}/ に題材を置く）
STANDARD = {
    "c": {"conv.c::to_msg", "conv.c::relay", "conv.c::dump", "types.h::M"},
    "cpp": {"conv.cpp::to_msg", "conv.cpp::relay", "conv.cpp::dump", "types.h::M"},
    "python": {"conv.py::to_msg", "conv.py::relay", "conv.py::dump", "model.py::M"},
}
NOT_CANDIDATES = {"only_one", "x_dump"}


def _el(symbol, change="追加", kind="データ構造", batch=BATCH, repo="r"):
    return {"repo": repo, "batch_name": batch, "sp": "CR-1-SP-001-001.001", "file": "x", "symbol": symbol,
            "kind": kind, "change": change}


class _Runner:
    def trace(self, repo_path, elements, engine="slice", extra=()):
        tmp = Path(self.tmp.name)
        el = tmp / "elements.json"
        el.write_text(json.dumps({"elements": elements}), encoding="utf-8")
        out_dir, human = tmp / "out", tmp / "human.md"
        argv = ["candidates", "--elements-file", str(el), "--repo", "r", "--repo-path", str(repo_path),
                "--design-dir", str(tmp / "design"), "--cr", "CR-1", "--engine", engine,
                "--out-dir", str(out_dir), "--human-out", str(human), *extra]
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                mod.main(argv)
            except SystemExit as e:
                code = e.code
        self.assertEqual(code, 0, err.getvalue())
        data = json.loads((out_dir / "cochange-candidates.json").read_text(encoding="utf-8"))
        return json.loads(out.getvalue()), data, out_dir, human

    def src(self, files: dict) -> Path:
        root = Path(self.tmp.name) / "repo"
        for name, text in files.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        return root


def _req(data):
    return {c["key"] for c in data["candidates"] if c["treatment"] == mod.REQUIRED}


def _cand(data, key):
    return next(c for c in data["candidates"] if c["key"] == key)


class StandardConformanceTest(_Runner, unittest.TestCase):
    """登録表のすべてのアダプタについて、標準の題材の確認対象を確かめる（言語を足したら STANDARD に足す）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_registered_language_has_standard_fixture(self):
        for lang in mod.ADAPTERS:
            self.assertIn(lang, STANDARD, f"{lang} の標準の題材の期待値が無い")
            self.assertTrue((FIXTURES / lang).is_dir(), f"fixtures/fieldtrace/{lang}/ が無い")

    @unittest.skipUnless(HAVE_TS, "tree-sitter が無い")
    def test_slice_standard_fixture(self):
        for lang in mod.ADAPTERS:
            with self.subTest(lang=lang):
                _o, data, _d, _h = self.trace(FIXTURES / lang, [_el("S::e")])
                self.assertEqual(_req(data), STANDARD[lang])
                keys = " ".join(c["key"] for c in data["candidates"])
                for name in NOT_CANDIDATES:
                    self.assertNotIn(name, keys)
                self.assertTrue(all(c["identity"] == "resolved" for c in data["candidates"]))
                dump = next(c for c in data["candidates"] if c["key"].endswith("::dump"))
                self.assertIn(mod.TAG_SINK, dump["tags"])
                self.assertEqual((dump["distance"], dump["path"]), (1, "S→M"))

    def test_rule_standard_fixture(self):
        for lang in mod.ADAPTERS:
            with self.subTest(lang=lang):
                out, data, _d, _h = self.trace(FIXTURES / lang, [_el("S::e")], engine="rule")
                expected = set(STANDARD[lang])
                if lang == "python":    # 規則判定は pickle.dumps(m2) の型を決められない
                    expected = {k for k in expected if not k.endswith("::relay")}
                self.assertTrue(expected <= _req(data), _req(data))
                self.assertNotIn("only_one", " ".join(_req(data)))
                self.assertTrue(all(c["identity"] == "name-only" for c in data["candidates"]))
                self.assertTrue(out["engine_warning"])


@unittest.skipUnless(HAVE_TS, "tree-sitter が無い")
class CopyFormsTest(_Runner, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_c_designated_and_positional_initializers(self):
        root = self.src({"t.h": "struct S { int a; int b; int c; };\nstruct M { int a; int b; int c; };\n"
                                "struct N { int x; int y; int z; };\n",
                         "f.c": '#include "t.h"\n'
                                "void d(const struct S *s) { struct M m = { .a = s->a, .b = s->b, .c = s->c }; (void)m; }\n"
                                "void p(const struct S *s) { struct N n = { s->a, s->b, s->c }; (void)n; }\n"})
        _o, data, _d, _h = self.trace(root, [_el("S::e")])
        self.assertIn("t.h::M", _req(data))
        self.assertIn("t.h::N", _req(data))
        self.assertIn(mod.TAG_COPY, _cand(data, "f.c::d")["tags"])

    def test_cpp_member_init_and_ctor_args(self):
        root = self.src({"t.hpp": "struct S { int a; int b; int c; };\n"
                                  "struct M { int a; int b; int c; M(const S &s) : a(s.a), b(s.b), c(s.c) {} };\n"
                                  "struct K { K(int, int, int); int x; int y; int z; };\n",
                         "f.cpp": '#include "t.hpp"\nK make(const S &s) { return K(s.a, s.b, s.c); }\n'})
        _o, data, _d, _h = self.trace(root, [_el("S::e")])
        self.assertIn("t.hpp::M", _req(data))
        self.assertIn("t.hpp::K", _req(data))
        self.assertTrue(_cand(data, "f.cpp::make")["unresolved_copy"])

    def test_python_kwargs_and_positional(self):
        root = self.src({"m.py": "from dataclasses import dataclass\n\n@dataclass\nclass S:\n    a: int\n    b: int\n    c: int\n\n"
                                 "@dataclass\nclass M:\n    a: int\n    b: int\n    c: int\n\n"
                                 "@dataclass\nclass N:\n    x: int\n    y: int\n    z: int\n\n"
                                 "def k(s: S):\n    return M(a=s.a, b=s.b, c=s.c)\n\n"
                                 "def p(s: S):\n    return N(s.a, s.b, s.c)\n"})
        _o, data, _d, _h = self.trace(root, [_el("S::e")])
        self.assertIn("m.py::M", _req(data))
        self.assertIn("m.py::N", _req(data))

    def test_inheritance_counts_base_fields_with_implicit_this(self):
        root = self.src({"t.hpp": "struct B { int p; int q; };\nstruct D : B { int r; void run(); };\n",
                         "d.cpp": '#include "t.hpp"\nvoid D::run() { p = q + r; }\n'})
        _o, data, _d, _h = self.trace(root, [_el("B::e")])
        c = _cand(data, "d.cpp::D::run")
        self.assertEqual((c["treatment"], c["distance"], c["fields_ref"], c["n_fields"]),
                         (mod.REQUIRED, 1, ["p", "q", "r"], 3))

    def test_delete_origin_field_lists_single_reference(self):
        root = self.src({"t.h": "struct S { int a; int b; int c; int d; };\n",
                         "f.c": '#include "t.h"\nint g(const struct S *s) { return s->d; }\n'})
        _o, data, _d, _h = self.trace(root, [_el("S::d", change="削除")])
        c = _cand(data, "f.c::g")
        self.assertEqual((c["table"], c["treatment"], c["tags"]), (1, mod.REQUIRED, [mod.TAG_ORIGIN_REF]))

    def test_method_element_is_skipped_and_unknown_type_reported(self):
        root = self.src({"t.hpp": "struct S { int a; void go(); };\n"})
        out, _data, _d, _h = self.trace(root, [_el("S::go", change="シグネチャ"), _el("Nope::x")])
        self.assertEqual([s["symbol"] for s in out["skipped_elements"]], ["S::go"])
        self.assertEqual(out["unresolved_types"], ["Nope"])

    def test_overloads_share_one_key(self):
        root = self.src({"t.hpp": "struct S { int a; int b; int c; };\n",
                         "f.cpp": '#include "t.hpp"\nint f(const S &s) { return s.a + s.b + s.c; }\n'
                                  "int f(const S &s, int k) { return s.a + s.b + s.c + k; }\n"})
        _o, data, _d, _h = self.trace(root, [_el("S::e")])
        c = _cand(data, "f.cpp::f")
        self.assertEqual((c["overloads"], c["lines"]), (2, [2, 3]))


class DigestAndLimitTest(_Runner, unittest.TestCase):
    """要約の上限・表・並び・全量の列（規則判定で動かす。tree-sitter によらない）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _enum_funcs(self, n, prefix="e", fields="s->a + s->b + s->c"):
        return "".join(f"int {prefix}{i}(const struct S *s) {{ return {fields}; }}\n" for i in range(n))

    def test_table2_over_limit_and_human_columns(self):
        root = self.src({"t.h": "struct S { int a; int b; int c; int d; };\n",
                         "f.c": '#include "t.h"\n' + self._enum_funcs(31)})
        out, data, out_dir, human = self.trace(root, [_el("S::e")], engine="rule")
        b = out["batches"][0]
        self.assertEqual((b["required_count"], b["over_limit_count"], b["over_limit_by_table"]), (30, 1, {"1": 0, "2": 1}))
        over = [c for c in data["candidates"] if c["treatment"] == mod.OVER_LIMIT]
        self.assertEqual((len(over), over[0]["table"], over[0]["rank"]), (1, 2, 31))
        digest = (out_dir / f"cochange-digest-{BATCH}").read_text(encoding="utf-8")
        self.assertIn("上限超過 1 件", digest)
        text = human.read_text(encoding="utf-8")
        self.assertIn("| 処理 | 要約での扱い | 表 | 書き先のバッチ |", text)
        first_row = text.split("|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")[1].split("\n")[0]
        self.assertTrue(first_row.startswith("| 未処理 | 上限超過 | 表2 |"), first_row)

    def test_table1_overflow_does_not_push_out_table2(self):
        root = self.src({"t.h": "struct S { int a; int b; int c; int d; };\n",
                         "f.c": '#include "t.h"\n' + self._enum_funcs(31, "r", "s->d")
                                + "int both(const struct S *s) { return s->a + s->b + s->d; }\n"})
        out, data, _o, _h = self.trace(root, [_el("S::d", change="シグネチャ")], engine="rule")
        b = out["batches"][0]
        self.assertEqual(b["over_limit_by_table"], {"1": 1, "2": 0})
        both = _cand(data, "f.c::both")
        self.assertEqual((both["table"], both["treatment"]), (2, mod.REQUIRED))
        self.assertIn(mod.TAG_ORIGIN_REF, both["tags"])
        self.assertIn(mod.TAG_ENUM, both["tags"])

    def test_batch_assignment_after_coding_and_key_format(self):
        root = self.src({"t.h": "struct S { int a; int b; int c; };\nstruct T { int x; int y; int z; };\n",
                         "f.c": '#include "t.h"\n'
                                "int fs(const struct S *s) { return s->a + s->b + s->c; }\n"
                                "int ft(const struct T *t) { return t->x + t->y + t->z; }\n"})
        out, data, out_dir, _h = self.trace(root, [_el("S::e"), _el("T::w", batch="CHD-CR-1-UR-002.md")],
                                          engine="rule", extra=["--after-coding"])
        self.assertEqual(_cand(data, "f.c::fs")["batch_name"], BATCH)
        self.assertEqual(_cand(data, "f.c::ft")["batch_name"], "CHD-CR-1-UR-002.md")
        self.assertTrue(data["after_coding"])
        self.assertIn("工程7 の後", (out_dir / f"cochange-digest-{BATCH}").read_text(encoding="utf-8"))
        self.assertEqual({b["batch_file"].split("/")[-1] for b in out["batches"]}, {BATCH, "CHD-CR-1-UR-002.md"})

    def test_no_origin_writes_empty_outputs(self):
        root = self.src({"t.h": "struct S { int a; };\n"})
        out, data, out_dir, human = self.trace(root, [_el("f", kind="関数", change="振る舞い")], engine="rule")
        self.assertEqual((out["batches"], data["candidates"]), ([], []))
        self.assertEqual(list(out_dir.glob("cochange-digest-*")), [])
        self.assertIn("なし", human.read_text(encoding="utf-8"))


class NormalizeTest(unittest.TestCase):
    def test_split_qual(self):
        self.assertEqual(mod.split_qual("ns::Foo<A, B>::bar(int)"), ["ns", "Foo", "bar"])
        self.assertEqual(mod.split_qual("Foo::operator()"), ["Foo", "operator()"])


if __name__ == "__main__":
    unittest.main()
