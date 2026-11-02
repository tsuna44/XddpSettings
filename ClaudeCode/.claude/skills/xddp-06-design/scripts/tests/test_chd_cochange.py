import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chd_cochange as mod  # noqa: E402

CR = "CR-1"
INDEX = """# 変更設計書 インデックス

## 2. UR別ファイル一覧

| UR ID | UR名 | バッチ | SP数 | ファイル | 該当変更 |
|---|---|---|---|---|---|
| CR-1-UR-001 | a | - | 1 | [CHD-CR-1-UR-001.md](./CHD-CR-1-UR-001.md) | あり |
| CR-1-UR-002 | b | - | 1 | [CHD-CR-1-UR-002.md](./CHD-CR-1-UR-002.md) | あり |
"""
S4_HEADER = """# 変更設計書

## 4. トレーサビリティマトリクス

> 注記

| 仕様ID | 仕様名 | 変更ファイル | 変更シンボル | 種別 | 変更の内容 |
|--------|--------|------------|------------|------|-----------|
"""


def _s41(rows):
    head = "\n### 4.1 一緒に直す候補のうち変更にしなかったもの\n\n> 注記\n\n"
    if rows is None:
        return head + "なし\n"
    return (head + "| 候補 | 候補の種類 | 起点（変更シンボル） | 判断 | 理由 |\n|---|---|---|---|---|\n"
            + "".join(f"| {k} | 関数 | S::e | {j} | 出力に含めない項目と決まっている |\n" for k, j in rows))


class ChdCochangeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.design = self.root / "06_design"
        self.spec = self.root / "04_specout"
        (self.design / "svc").mkdir(parents=True)
        (self.spec / "svc").mkdir(parents=True)
        (self.design / "svc" / f"CHD-{CR}.md").write_text(INDEX, encoding="utf-8")
        self.b1 = self.design / "svc" / "CHD-CR-1-UR-001.md"
        self.b2 = self.design / "svc" / "CHD-CR-1-UR-002.md"
        self._chd(self.b1, [("types.h", "S::e", "データ構造", "追加")])
        self._chd(self.b2, [("x.c", "unrelated", "関数", "振る舞い")])

    def tearDown(self):
        self.tmp.cleanup()

    def _chd(self, path, rows, s41=None):
        body = "".join(f"| CR-1-SP-001-001.001 | n | {f} | {s} | {k} | {c} |\n" for f, s, k, c in rows)
        path.write_text(S4_HEADER + body + _s41(s41), encoding="utf-8")

    def _cands(self, items, type_names=("S", "M", "Bar")):
        p = self.root / "cands.json"
        rows = []
        for i, it in enumerate(items):
            key, kind, treatment, table = tuple(it) + ("関数", "required", 2)[len(it) - 1:]
            rows.append({"key": key, "kind": kind, "treatment": treatment, "table": table, "rank": i + 1,
                         "tags": ["並べて扱う"], "distance": 1, "batch_name": self.b1.name,
                         "batch_file": str(self.b1), "identity": "resolved"})
        p.write_text(json.dumps({"cr": CR, "repo": "svc", "engine": "slice", "params": {"min_fields": 3, "max_depth": 4},
                                 "type_names": list(type_names), "origins": [], "candidates": rows},
                                ensure_ascii=False), encoding="utf-8")
        return p

    def _call(self, argv):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                mod.main(argv)
            except SystemExit as e:
                code = e.code
        text = out.getvalue().strip()
        return code, (json.loads(text) if text else None), err.getvalue()

    def _check(self, cands, *extra):
        return self._call(["check", "--candidates", str(cands), "--design-dir", str(self.design), "--repo", "svc",
                           "--cr", CR, *extra])

    # -- check --
    def test_match_kinds_and_counts(self):
        cands = self._cands([("conv.c::dump",), ("types.h::M", "型"), ("conv.c", "ファイル"), ("conv.c::to_msg",),
                             ("conv.c::relay",), ("conv.c::open",)])
        self._chd(self.b1, [("types.h", "S::e", "データ構造", "追加"), ("conv.c", "ns::dump(int)", "関数", "振る舞い"),
                            ("types.h", "ns::M::e", "データ構造", "追加")],
                  [("conv.c::to_msg", "不要"), ("conv.c::relay", "確認できず"), ("old.c::gone", "不要")])
        code, out, err = self._check(cands)
        self.assertEqual(code, 0, err)
        self.assertEqual([u["key"] for u in out["unmapped"]], ["conv.c::open"])
        self.assertEqual(out["unmapped"][0]["batch_file"], str(self.b1))
        self.assertEqual(out["unknown"], ["old.c::gone"])
        self.assertEqual((out["mapped_count"], out["excluded_count"], out["unconfirmed_count"]), (3, 1, 1))
        self.assertEqual(out["mapped_count"] + out["excluded_count"] + out["unconfirmed_count"] + len(out["unmapped"]), 6)

    def test_free_function_does_not_match_method_row(self):
        cands = self._cands([("conv.c::foo",)])
        self._chd(self.b1, [("conv.c", "Bar::foo", "関数", "振る舞い")])
        _c, out, _e = self._check(cands)
        self.assertEqual([u["key"] for u in out["unmapped"]], ["conv.c::foo"])

    def test_template_and_overload_key(self):
        cands = self._cands([("a.cpp::Foo::bar",)])
        self._chd(self.b1, [("a.cpp", "`Foo<A, B>::bar`", "関数", "振る舞い")])
        _c, out, _e = self._check(cands)
        self.assertEqual(out["unmapped"], [])

    def test_other_batch_section41_and_priority_conflicts(self):
        cands = self._cands([("conv.c::dump",), ("conv.c::to_msg",)])
        self._chd(self.b1, [("types.h", "S::e", "データ構造", "追加"), ("conv.c", "dump", "関数", "振る舞い")],
                  [("conv.c::dump", "確認できず")])
        self._chd(self.b2, [("x.c", "unrelated", "関数", "振る舞い")],
                  [("conv.c::to_msg", "不要"), ("conv.c::to_msg", "確認できず")])
        _c, out, _e = self._check(cands)
        self.assertEqual(out["unmapped"], [])
        self.assertEqual(out["unknown"], [])
        self.assertEqual((out["mapped_count"], out["excluded_count"], out["unconfirmed_count"]), (1, 1, 0))
        self.assertEqual(sorted(c["key"] for c in out["conflicts"]), ["conv.c::dump", "conv.c::to_msg"])

    def test_over_limit_open_and_human_out(self):
        cands = self._cands([("a.c::r1",), ("a.c::o1", "関数", "over-limit", 2), ("a.c::o2", "関数", "over-limit", 2),
                             ("a.c::o3", "関数", "over-limit", 1)])
        self._chd(self.b1, [("types.h", "S::e", "データ構造", "追加"), ("a.c", "r1", "関数", "振る舞い")],
                  [("a.c::o1", "不要")])
        human = self.root / "human.md"
        _c, out, err = self._check(cands, "--human-out", str(human))
        self.assertEqual(out["unmapped"], [], err)
        self.assertEqual(out["over_limit_open_by_table"], {"1": 1, "2": 1})
        self.assertEqual([h["key"] for h in out["over_limit_open_head"]], ["a.c::o2"])
        text = human.read_text(encoding="utf-8")
        rows = [ln for ln in text.splitlines() if ln.startswith("| ") and "`a.c::" in ln]
        self.assertTrue(rows[0].startswith("| 未処理 | 上限超過 |"), rows[0])
        self.assertIn("| §4.1 不要 | 上限超過 |", text)
        self.assertIn("| §4 | 確認対象 |", text)

    def test_metrics_one_line(self):
        cands = self._cands([("a.c::r1",)])
        metrics = self.root / "metrics.jsonl"
        self._check(cands, "--metrics", str(metrics), "--today", "2026-11-02")
        lines = metrics.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        m = json.loads(lines[0])
        self.assertEqual((m["event"], m["required_count"], m["unmapped_count"]), ("cochange_summary", 1, 1))

    def test_format_errors_exit_codes(self):
        cands = self._cands([("a.c::r1",)])
        self._chd(self.b1, [("types.h", "S::e", "データ構造", "追加")], [("a.c::r1", "たぶん不要")])
        code, _o, err = self._check(cands)
        self.assertEqual(code, 4, err)
        self._chd(self.b1, [("/abs/types.h", "S::e", "データ構造", "追加")])
        code, _o, err = self._check(cands)
        self.assertEqual(code, 1, err)

    # -- record / status / invalidate --
    def _common(self, key="3|4|auto|||auto"):
        return ["--design-dir", str(self.design), "--specout-dir", str(self.spec), "--repos", "svc",
                "--repo", "svc", "--cr", CR, "--params-key", key]

    def test_record_status(self):
        rec = self.root / "inputs.json"
        code, out, _e = self._call(["status", *self._common(), "--recorded", str(rec)])
        self.assertEqual((out["stale"], out["recorded"]), (False, False))
        code, _o, err = self._call(["record", *self._common(), "--out", str(rec)])
        self.assertEqual(code, 0, err)
        _c, out, _e = self._call(["status", *self._common(), "--recorded", str(rec)])
        self.assertEqual((out["stale"], out["recorded"]), (False, True))
        _c, out, _e = self._call(["status", *self._common("5|4|auto|||auto"), "--recorded", str(rec)])
        self.assertTrue(out["stale"])
        self._chd(self.b1, [("types.h", "S::e", "データ構造", "追加")], [("a.c::r1", "不要")])
        _c, out, _e = self._call(["status", *self._common(), "--recorded", str(rec)])
        self.assertTrue(out["stale"])
        self._chd(self.b1, [("types.h", "S::e", "データ構造", "追加")], [("a.c::r1", "ほぼ不要")])
        before = rec.read_text(encoding="utf-8")
        code, _o, _e = self._call(["record", *self._common(), "--out", str(rec)])
        self.assertEqual(code, 4)
        self.assertEqual(rec.read_text(encoding="utf-8"), before)
        self._chd(self.b1, [("/abs/types.h", "S::e", "データ構造", "追加")])
        code, _o, _e = self._call(["status", *self._common(), "--recorded", str(rec)])
        self.assertEqual(code, 1)

    def test_invalidate(self):
        work = self.root / "work"
        work.mkdir()
        for n in ("cochange-candidates.json", "cochange-inputs.json", "cochange-digest-CHD-CR-1-UR-001.md"):
            (work / n).write_text("x", encoding="utf-8")
        human = self.root / "human.md"
        human.write_text("# 全量\n", encoding="utf-8")
        _c, out, _e = self._call(["invalidate", "--work-dir", str(work), "--human-out", str(human)])
        self.assertEqual(len(out["removed"]), 3)
        self.assertTrue(human.read_text(encoding="utf-8").startswith(mod.STALE_NOTE))


if __name__ == "__main__":
    unittest.main()
