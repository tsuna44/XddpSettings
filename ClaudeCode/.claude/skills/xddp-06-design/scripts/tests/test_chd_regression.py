import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chd_regression as mod  # noqa: E402

CR = "CR-1"
INDEX = """# 変更設計書 インデックス

## 2. UR別ファイル一覧

| UR ID | UR名 | バッチ | SP数 | ファイル | 該当変更 |
|---|---|---|---|---|---|
| CR-1-UR-001 | a | - | 1 | [CHD-CR-1-UR-001.md](./CHD-CR-1-UR-001.md) | あり |
"""

S4_HEADER = """# 変更設計書

## 4. トレーサビリティマトリクス

> 注記

| 仕様ID | 仕様名 | 変更ファイル | 変更シンボル | 種別 | 変更の内容 |
|--------|--------|------------|------------|------|-----------|
"""


def _s7(rows7, rows71=None):
    text = ("\n## 7. 確認項目（テスト観点）\n\n> 注記\n\n"
            "| # | 確認内容 | 確認種別 | 対応SP番号 | 回帰の候補 |\n|---|---|---|---|---|\n"
            + "".join(f"| {i + 1} | x | {k} | CR-1-SP-001-001.001 | {c} |\n" for i, (k, c) in enumerate(rows7))
            + "\n### 7.1 回帰の候補のうち確認項目にしなかったもの\n\n> 注記\n\n")
    if rows71 is None:
        return text + "なし\n"
    return (text + "| 回帰の候補 | 起点（変更シンボル） | 理由 |\n|---|---|---|\n"
            + "".join(f"| {c} | f | 戻り値を使わない |\n" for c in rows71))


class ChdRegressionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.design = self.root / "06_design"
        self.spec = self.root / "04_specout"
        for repo in ("svc", "lib"):
            (self.design / repo).mkdir(parents=True)
            (self.design / repo / f"CHD-{CR}.md").write_text(INDEX, encoding="utf-8")
            (self.spec / repo / "ripple").mkdir(parents=True)
        self.batch = self.design / "svc" / "CHD-CR-1-UR-001.md"
        self.lib_batch = self.design / "lib" / "CHD-CR-1-UR-001.md"
        self._s4(self.batch, [("a.c", "f", "関数", "振る舞い")])
        self._s4(self.lib_batch, [("lib.c", "g", "関数", "振る舞い")])

    def tearDown(self):
        self.tmp.cleanup()

    def _s4(self, path, rows, extra=""):
        body = "".join(f"| CR-1-SP-001-001.001 | n | {f} | {s} | {k} | {c} |\n" for f, s, k, c in rows)
        path.write_text(S4_HEADER + body + extra, encoding="utf-8")

    def _runs(self, repo, runs):
        (self.spec / repo / "ripple" / "runs.json").write_text(json.dumps(
            {"cr": CR, "repo": repo, "runs": [{"run": r, "adopted": True} for r in runs]}), encoding="utf-8")

    def _call(self, argv):
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

    def _common(self, repo="svc"):
        return ["--design-dir", str(self.design), "--specout-dir", str(self.spec), "--repos", "svc,lib",
                "--repo", repo, "--cr", CR]

    def _elements(self, repo="svc"):
        out = self.root / "el.json"
        code, _o, err = self._call(["elements", *self._common(repo), "--out", str(out)])
        return code, (json.loads(out.read_text(encoding="utf-8")) if code == 0 else None), err

    # -- elements --
    def test_elements_names_and_values(self):
        self._s4(self.batch, [("./a.c", "f", "関数", "振る舞い"), ("api.yaml", "POST /jobs", "インタフェース", "振る舞い"),
                              ("a.cpp", "operator()", "関数", "振る舞い"), ("a.cpp", "`Foo<A, B>::bar`", "関数", "シグネチャ"),
                              ("g.c", "g_state", "変数", "振る舞い"), ("-", "-", "-", "-"), ("x.c", "-", "関数", "追加")])
        code, data, err = self._elements()
        self.assertEqual(code, 0, err)
        self.assertEqual([(e["file"], e["symbol"], e["kind"]) for e in data["elements"]],
                         [("a.c", "f", "関数"), ("api.yaml", "POST /jobs", "インタフェース"), ("a.cpp", "operator()", "関数"),
                          ("a.cpp", "Foo<A, B>::bar", "関数"), ("g.c", "g_state", "変数")])
        self.assertEqual(data["elements"][0]["batch_name"], "CHD-CR-1-UR-001.md")
        self.assertEqual(data["relevant_repos"], ["svc"])

    def test_elements_fail_loud(self):
        self._s4(self.batch, [("a.c", "f, g", "関数", "振る舞い"), ("/abs/a.c", "f", "関数", "振る舞い"),
                              ("../a.c", "f", "関数", "振る舞い"), ("a.c", "f", "クラス", "変更")])
        code, _d, err = self._elements()
        self.assertEqual(code, 1)
        lines = [l for l in err.strip().split("\n") if l]
        self.assertEqual(len(lines), 5)                     # 複数・絶対パス・..・種別・変更の内容
        for l in lines:
            path, line_no, reason = l.split("\t")
            self.assertEqual(path, str(self.batch.resolve()))
            self.assertTrue(line_no.isdigit())
        self.assertIn("{型名}::{名前}", lines[0])
        self.assertIn("関数／データ構造／変数／定数／インタフェース", err)
        self.batch.write_text(S4_HEADER.replace(" 種別 | 変更の内容 |", "").replace("------|-----------|", "")
                              + "| CR-1-SP-001-001.001 | n | a.c | f |\n", encoding="utf-8")
        code, _d, err = self._elements()
        self.assertEqual(code, 1)
        self.assertIn("列が足りない", err)

    def test_elements_relevant_repos_only(self):
        self._s4(self.lib_batch, [("lib.c", "g, h", "関数", "振る舞い")])
        code, data, _e = self._elements()
        self.assertEqual(code, 0)                            # 関係しない repo の誤りでは止めない
        self._runs("svc", ["initial", "cross-lib-1"])
        code, _d, err = self._elements()
        self.assertEqual(code, 1)
        self.assertIn(str(self.lib_batch.resolve()), err)
        self._s4(self.lib_batch, [("lib.c", "g", "関数", "振る舞い")])
        code, data, _e = self._elements()
        self.assertEqual(data["relevant_repos"], ["svc", "lib"])
        self.assertEqual([e["repo"] for e in data["elements"]], ["svc", "lib"])

    # -- check --
    def _cands(self, items):
        p = self.root / "cands.json"
        p.write_text(json.dumps({"candidates": [{"key": k, "required": r} for k, r in items]}), encoding="utf-8")
        return p

    def test_check_unmapped_unknown_and_keys(self):
        cands = self._cands([("a.cpp::Foo<A, B>::bar", True), ("b.cpp::baz", True), ("c.c::f", True),
                             ("d.c", True), ("e.c::opt", False)])
        self._s4(self.batch, [("a.c", "f", "関数", "振る舞い")],
                 extra=_s7([("正常系", "-"), ("回帰", "`./a.cpp::Foo<A, B>::bar`, b.cpp::baz"), ("回帰", "e.c::opt"),
                            ("回帰", "old.c::gone")], ["c.c::f"]))
        code, out, err = self._call(["check", "--candidates", str(cands), "--design-dir", str(self.design),
                                     "--repo", "svc", "--cr", CR])
        self.assertEqual(code, 0, err)
        self.assertEqual(out["unmapped"], ["d.c"])
        self.assertEqual(out["unknown"], ["old.c::gone"])
        self.assertEqual((out["mapped_count"], out["excluded_count"]), (2, 1))

    def test_check_section_71_none_and_format_error(self):
        cands = self._cands([("a.c::g", True)])
        self._s4(self.batch, [("a.c", "f", "関数", "振る舞い")], extra=_s7([("正常系", "-")]))
        code, out, _e = self._call(["check", "--candidates", str(cands), "--design-dir", str(self.design),
                                    "--repo", "svc", "--cr", CR])
        self.assertEqual((code, out["unmapped"]), (0, ["a.c::g"]))
        bad = _s7([("回帰", "a.c::g")]).replace(" 回帰の候補 |\n|---|---|---|---|---|", "\n|---|---|---|---|")
        bad = bad.replace(" | a.c::g |", " |")
        self._s4(self.batch, [("a.c", "f", "関数", "振る舞い")], extra=bad)
        code, _o, err = self._call(["check", "--candidates", str(cands), "--design-dir", str(self.design),
                                    "--repo", "svc", "--cr", CR])
        self.assertEqual(code, 1, err)

    # -- record / status --
    def _record(self, key="full|index|||conservative|auto"):
        rec = self.root / "inputs.json"
        code, out, err = self._call(["record", *self._common(), "--params-key", key, "--out", str(rec)])
        self.assertEqual(code, 0, err)
        return rec

    def _status(self, rec, key="full|index|||conservative|auto", repo="svc"):
        return self._call(["status", *self._common(repo), "--params-key", key, "--recorded", str(rec)])

    def test_record_status_detects_changes(self):
        rec = self.root / "inputs.json"
        self.assertEqual(self._status(rec)[1], {"ok": True, "stale": False, "recorded": False})
        rec = self._record()
        self.assertFalse(self._status(rec)[1]["stale"])
        self.assertTrue(self._status(rec, key="quick|index|||conservative|auto")[1]["stale"])
        self._s4(self.batch, [("a.c", "f", "関数", "振る舞い"), ("a.c", "g", "関数", "振る舞い")])
        self.assertTrue(self._status(rec)[1]["stale"])
        rec = self._record()
        self._runs("svc", ["initial"])
        self.assertTrue(self._status(rec)[1]["stale"])
        rec = self._record()
        log = self.spec / "svc" / "ripple" / "initial" / "discovery-log.md"
        log.parent.mkdir(parents=True)
        log.write_text("x", encoding="utf-8")
        self.assertTrue(self._status(rec)[1]["stale"])
        rec = self._record()
        (self.spec / "svc" / "work").mkdir()
        (self.spec / "svc" / "work" / "no-ripple.json").write_text("{}", encoding="utf-8")
        self.assertTrue(self._status(rec)[1]["stale"])

    def test_status_other_repo_only_when_cross_run(self):
        rec = self._record()
        self._s4(self.lib_batch, [("lib.c", "h", "関数", "振る舞い")])
        self.assertFalse(self._status(rec)[1]["stale"])     # cross の調査が無い repo の §4 は関係しない
        self._s4(self.lib_batch, [("lib.c", "g, h", "関数", "振る舞い")])
        self.assertEqual(self._status(rec)[0], 0)
        self._runs("svc", ["cross-lib-1"])
        self.assertEqual(self._status(rec)[0], 1)           # 関係する repo の書式の誤り

    # -- invalidate --
    def test_invalidate(self):
        work = self.root / "work"
        work.mkdir()
        for n in ("regression-digest-a.md", "regression-inputs.json", "regression-candidates.json"):
            (work / n).write_text("x", encoding="utf-8")
        human = self.root / "regression-candidates.md"
        human.write_text("# 全量\n", encoding="utf-8")
        for _ in range(2):
            code, _o, _e = self._call(["invalidate", "--work-dir", str(work), "--human-out", str(human)])
            self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in work.iterdir()), ["regression-candidates.json"])
        self.assertEqual(human.read_text(encoding="utf-8").count("⚠️ 最新の回帰の範囲の算出に失敗した"), 1)
        self.assertEqual(self._call(["invalidate", "--work-dir", str(self.root / "none")])[0], 0)

    def test_split_names_and_keys(self):
        self.assertEqual(mod.split_names("a.cpp::Foo<A, B>::bar, b.cpp::baz"), ["a.cpp::Foo<A, B>::bar", "b.cpp::baz"])
        self.assertEqual(mod.split_names("f(a, b)、g"), ["f(a, b)", "g"])
        self.assertEqual(mod.norm_key("`./a.cpp::f`"), "a.cpp::f")
        self.assertEqual(mod.norm_key("./dir/x.c"), "dir/x.c")


if __name__ == "__main__":
    unittest.main()
