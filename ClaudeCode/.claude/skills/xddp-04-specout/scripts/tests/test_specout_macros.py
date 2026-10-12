"""specout_macros.py のテスト（標準ライブラリのみ。tree-sitter を使わない）。"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import specout_macros as mod  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "slice" / "cppmacro"


class LexTest(unittest.TestCase):
    def test_comments_strings_and_directives(self):
        src = (b'#define A 1 /* c\n'
               b'  still */ 2\n'
               b'int x = 1\'000; char c = \'"\'; const char *s = "a // b";\n'
               b'auto r = R"x(  /* not a comment */ )x"; // tail\n'
               b'#if defined(B) && \\\n'
               b'    defined(C)\n'
               b'int y;\n')
        lx = mod.lex(src)
        self.assertTrue(lx.in_directive(src.index(b"still")))          # 指令の中のブロックコメントが改行をまたぐ
        self.assertTrue(lx.in_directive(src.index(b"defined(C)")))     # 継続行
        self.assertFalse(lx.in_directive(src.index(b"int x")))
        self.assertFalse(lx.in_directive(src.index(b"int y")))
        self.assertFalse(lx.in_comment_or_string(src.index(b"000")))  # 数字の区切りは文字リテラルにしない
        self.assertTrue(lx.in_comment_or_string(src.index(b"a // b")))
        self.assertTrue(lx.in_comment_or_string(src.index(b"not a comment")))
        self.assertTrue(lx.in_comment_or_string(src.index(b"tail")))
        self.assertFalse(lx.in_comment_or_string(src.index(b"const char")))

    def test_macro_definitions_skip_comments(self):
        src = (b"// #define A garbage(1)\n"
               b"/* #define B garbage(2)\n"
               b"#define C x\n"
               b"*/\n"
               b"#  define D(v) __attribute__((v))\n"
               b"#define E \\\n"
               b"    inline /* c */ static\n")
        self.assertEqual(mod.macro_definitions(src),
                         [("D", ["v"], "__attribute__((v))"), ("E", None, "inline static")])

    def test_macro_definition_branches(self):
        src = (b"#define A\n#ifdef X\n#define B 1\n#  if Y\n#define C\n#  endif\n#define D\n#else\n#define E\n#endif\n"
               b"#define F\n")
        self.assertEqual([(d[0], d[3]) for d in mod.macro_definitions(src, with_branch=True)],
                         [("A", 0), ("B", 1), ("C", 2), ("D", 1), ("E", 3), ("F", 0)])


class ClassifyTest(unittest.TestCase):
    def setUp(self):
        self.table = mod.neutralize_table(str(FIX))

    def test_fixture_table(self):
        t = {k: (v.kind, v.replacement) for k, v in self.table.items()}
        ns, deco = mod.KIND_NAMESPACE, mod.KIND_DECORATOR
        self.assertEqual(t["MY_NS_BEGIN"], (ns, "namespace MY_NAMESPACE {"))   # 識別子が別のマクロ名
        self.assertEqual(t["MY_NS_END"], (ns, "}"))
        self.assertEqual(t["MY_NESTED_BEGIN"], (ns, "namespace outer::inline v1 {"))
        for name in ("MY_INLINE", "MY_API", "MY_ALIAS", "MY_EXPORT", "MY_NODISCARD", "MY_FEATURE", "LONG_DEF",
                     "MACROS_H", "SOME_STATIC"):
            self.assertEqual(t[name], (deco, ""), name)
        self.assertEqual(t["VIRTUAL"], (deco, "virtual"))
        self.assertEqual(t["MAYBE_VIRTUAL"], (deco, "virtual"))   # 定義の1つだけが virtual を含む
        self.assertEqual(t["ALL_STATIC"], (deco, "static"))       # すべての定義が static を含む
        for name in ("MY_BEGIN_EXPORT", "MY_END_EXPORT", "MY_TRY", "MY_CATCH"):   # 空の定義を持つ開く側・閉じる側の組
            self.assertEqual(t[name], (mod.KIND_EMPTY_PAIR, ""), name)
        self.assertEqual(t["ASYM_END_EXPORT"], (ns, "}"))
        # 置き換えない: リポジトリに定義の無い名前・種類の混ざる定義・段数の違う名前空間マクロ・オブジェクト形式でない・
        # 閉じる側に空の定義が無い組の開く側
        for name in ("BAD_DECOR", "MIXED_DECOR", "NSX_BEGIN", "NSX_END", "MY_VIS", "MY_NAMESPACE",
                     "ASYM_BEGIN_EXPORT"):
            self.assertNotIn(name, t, name)

    def test_function_like_decorator_body(self):
        defs = {"VIS": [(["value"], "__attribute__((visibility(value)))"), (["value"], "")],
                "API": [(None, "__declspec(dllexport)"), (None, "__declspec(dllimport)"), (None, 'VIS("default")'),
                        (None, "")],
                "BADVIS": [(["v"], "v + 1")], "BAD": [(None, "BADVIS(1)")]}
        t = mod.classify_definitions(defs)
        self.assertEqual(t["API"].kind, mod.KIND_DECORATOR)
        self.assertNotIn("BAD", t)

    def test_cycles_and_depth(self):
        defs = {"A": [(None, "B")], "B": [(None, "A")]}
        self.assertEqual(mod.classify_definitions(defs), {})
        chain = {f"M{i}": [(None, f"M{i + 1}")] for i in range(12)}
        chain["M12"] = [(None, "inline")]
        t = mod.classify_definitions(chain)
        self.assertIn("M5", t)          # 深さ8以内
        self.assertNotIn("M0", t)       # 深さの超過

    def test_empty_pairs_need_both_sides_in_same_places(self):
        def d(*items):
            return [(None, b, w) for b, w in items]
        a, b, m = ("a.h", 1), ("a.h", 2), ("m.cc", 0)
        defs = {"B": d(("export {", m), ("", a)), "E": d(("}", m), ("", a)),
                "B2": d(("export {", m), ("", b)), "E2": d(("}", m), ("", ("b.h", 1))),   # 空の定義が別の場所
                "B3": d(("try", ("x.h", 0)), ("", ("y.h", 0))),
                "E3": d(("catch (...) { }", ("z.h", 0)), ("", ("y.h", 0))),                  # 空でない定義が別の場所
                "M": d(("export {", m), ("}", m), ("", a)),                                   # 開く側と閉じる側が混ざる
                "C": d(("catch (...) { x", m), ("", a))}                                      # 括弧が閉じない
        t = mod.empty_pairs(defs, {})
        self.assertEqual(sorted(t), ["B", "E"])
        self.assertEqual(sorted(mod.empty_pairs(defs, {"E": None})), [])     # 相手が表にあれば組にしない

    def test_counts(self):
        c = mod.table_counts(self.table)
        self.assertEqual(c["neutralized_macros"], c["namespace"] + c["decorator"] + c["empty_pair"])
        self.assertEqual(c["namespace"], 5)
        self.assertEqual(c["empty_pair"], 4)


class ApplyTest(unittest.TestCase):
    def test_keeps_lines_directives_comments_strings(self):
        table = mod.neutralize_table(str(FIX))
        src = (FIX / "sink.cpp").read_bytes()
        out = mod.apply_table(src, mod.table_key(table))
        self.assertEqual(out.count(b"\n"), src.count(b"\n"))
        lines_in, lines_out = src.split(b"\n"), out.split(b"\n")
        for a, b in zip(lines_in, lines_out):
            if a.lstrip().startswith(b"#") or a.startswith(b"    defined("):
                self.assertEqual(a, b)       # プリプロセッサ指令の行（継続行を含む）は置き換えない
        self.assertIn(b"// MY_INLINE is used in comments only", out)
        self.assertIn(b" MY_INLINE in a block comment", out)
        self.assertIn(b'"MY_INLINE"', out)
        self.assertIn(b"/* MY_INLINE */", out)
        self.assertNotIn(b"MY_NS_BEGIN", out.split(b"#endif")[-1])

    def test_include_guard_and_feature_flags_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            for name, body in (("guard.h", "#ifndef GUARD_H\n#define GUARD_H\n#define FEATURE_X\n"
                                            "#if defined(FEATURE_X) && \\\n    defined(GUARD_H)\nint on(void);\n"
                                            "#endif\n#ifndef FEATURE_X\nint off(void);\n#endif\n"
                                            "#undef FEATURE_X\n#endif\n"),
                               ("guard.c", "#define C_FLAG\n#ifdef C_FLAG\nint c_on;\n#endif\n")):
                Path(d, name).write_text(body, encoding="utf-8")
            table = mod.neutralize_table(d)
            self.assertEqual(set(table), {"GUARD_H", "FEATURE_X", "C_FLAG"})
            for name in ("guard.h", "guard.c"):
                src = Path(d, name).read_bytes()
                self.assertEqual(mod.apply_table(src, mod.table_key(table)), src)

    def test_line_occurrence(self):
        src = (b"/* start\n"
               b"   X_API in comment */ int a;\n"
               b"X_API int b; /* X_API */\n"
               b'const char *s = "X_API";\n'
               b"#define Y X_API\n")
        lx = mod.lex(src)
        self.assertEqual(mod.line_has_code_occurrence(lx, 2, "X_API"), (False, False))
        self.assertEqual(mod.line_has_code_occurrence(lx, 3, "X_API"), (False, True))
        self.assertEqual(mod.line_has_code_occurrence(lx, 4, "X_API"), (False, False))
        self.assertEqual(mod.line_has_code_occurrence(lx, 5, "X_API"), (True, False))


class ExtLangTest(unittest.TestCase):
    def test_c_cxx_lang(self):
        self.assertEqual(mod.c_cxx_lang("a.h", "cpp"), "cpp")
        self.assertEqual(mod.c_cxx_lang("a.h", "c"), "c")
        self.assertEqual(mod.c_cxx_lang("a.hpp", "c"), "cpp")
        self.assertIsNone(mod.c_cxx_lang("a.py"))
        for ext in mod.C_CXX_EXT_LANG:
            self.assertIsNone(mod.c_cxx_lang("a" + ext.upper()), ext)   # 大文字の拡張子は C/C++ にしない


if __name__ == "__main__":
    unittest.main()
