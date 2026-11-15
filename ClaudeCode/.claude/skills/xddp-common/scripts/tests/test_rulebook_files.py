import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rulebook_files as rf  # noqa: E402


def _mk(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _tpl(kind: str) -> str:
    return rf.TEMPLATES[kind].read_text(encoding="utf-8")


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = rf.main(argv)
    return code, out.getvalue(), err.getvalue()


class TestSectionsMatchTemplates(unittest.TestCase):
    def test_every_template_heading_is_defined_and_vice_versa(self):
        for kind in ("shared", "repo", "cross"):
            headings = list(rf.split_sections(_tpl(kind)))
            defined = [s["heading"] for s in rf.SECTIONS[kind]]
            self.assertEqual(headings, defined, kind)

    def test_every_section_except_history_has_items(self):
        for kind in ("shared", "repo", "cross"):
            for sec in rf.SECTIONS[kind]:
                items = rf.template_items(kind, sec["heading"])
                if sec["number"] == "7":
                    self.assertEqual(items, [], kind)
                else:
                    self.assertTrue(items, f"{kind} {sec['heading']}")

    def test_every_subsection_ends_with_one_placeholder(self):
        for kind in ("shared", "repo", "cross"):
            for heading, body in rf.split_sections(_tpl(kind)).items():
                if heading.startswith("7."):
                    continue
                for name, lines in rf.split_regions(body):
                    if name is None:
                        continue
                    count = sum(1 for ln in lines if rf.PLACEHOLDER_RE.match(ln))
                    self.assertEqual(count, 1, f"{kind} {heading} / {name}")

    def test_history_initial_row_uses_init_tokens(self):
        for kind in ("shared", "repo", "cross"):
            text = _tpl(kind)
            self.assertIn("| {INIT_DATE} | {INIT_CR} | 初期作成 |", text, kind)
            self.assertIn("| 日付 | 更新CR | 更新内容 |", text, kind)


class _Ws(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.xddp = self.tmp / "xddp"
        self.docs = self.tmp / "baseline_docs"
        self.xddp.mkdir()


class TestEnsure(_Ws):
    def test_create_from_template_replaces_only_init_tokens(self):
        r = rf.ensure("repo", self.xddp, self.docs, ["repo-a"], "2026-11-15", repo="repo-a", cr="CR-1")
        self.assertEqual(r["action"], "created-from-template")
        text = (self.xddp / "project-rulebook-repo-a.md").read_text(encoding="utf-8")
        self.assertIn("# repo-a リポジトリ Steering", text)
        self.assertIn("| 2026-11-15 | CR-1 | 初期作成 |", text)
        self.assertIn("**記録日:** YYYY-MM-DD / **更新CR:** {CR}", text)
        self.assertNotIn("{INIT_", text)

    def test_create_without_cr_uses_dash(self):
        rf.ensure("cross", self.xddp, self.docs, ["a", "b"], "2026-11-15")
        text = (self.xddp / "project-rulebook-cross.md").read_text(encoding="utf-8")
        self.assertIn("| 2026-11-15 | — | 初期作成 |", text)
        self.assertIn("CRS-{CR}.md", text)

    def test_copied_from_docs_records_base(self):
        _mk(self.docs / "repo-a" / "project-rulebook.md", "from docs")
        r = rf.ensure("repo", self.xddp, self.docs, ["repo-a"], "2026-11-15", repo="repo-a")
        self.assertEqual(r["action"], "copied-from-docs")
        self.assertIn("project-rulebook-repo-a.md", rf.load_base(self.xddp))

    def test_single_repo_can_be_created_but_cross_is_rejected(self):
        rf.ensure("repo", self.xddp, self.docs, ["only"], "2026-11-15", repo="only")
        self.assertTrue((self.xddp / "project-rulebook-only.md").exists())
        code, _out, err = _run(["ensure", "--kind", "cross", "--xddp-dir", str(self.xddp), "--docs",
                                str(self.docs), "--today", "2026-11-15", "--repos-keys", "only"])
        self.assertEqual(code, 2)
        self.assertIn("2つ以上", err)

    def test_unknown_repo_is_rejected(self):
        code, _out, _err = _run(["ensure", "--kind", "repo", "--repo", "x", "--xddp-dir", str(self.xddp),
                                 "--docs", str(self.docs), "--today", "2026-11-15", "--repos-keys", "a"])
        self.assertEqual(code, 2)

    def test_existing_file_actions(self):
        x = self.xddp / "project-rulebook.md"
        d = self.docs / "project-rulebook.md"
        _mk(x, "v1")
        self.assertEqual(rf.ensure("shared", self.xddp, self.docs, ["a"], "t")["action"], "exists")
        _mk(d, "v1")
        self.assertEqual(rf.ensure("shared", self.xddp, self.docs, ["a"], "t")["action"], "same")
        _mk(d, "v2")
        self.assertEqual(rf.ensure("shared", self.xddp, self.docs, ["a"], "t")["action"], "updated-from-docs")
        self.assertEqual(x.read_text(encoding="utf-8"), "v2")
        _mk(x, "v3")
        self.assertEqual(rf.ensure("shared", self.xddp, self.docs, ["a"], "t")["action"], "exists")
        self.assertEqual(d.read_text(encoding="utf-8"), "v2")
        _mk(d, "v4")
        self.assertEqual(rf.ensure("shared", self.xddp, self.docs, ["a"], "t")["action"], "conflict")
        self.assertEqual(x.read_text(encoding="utf-8"), "v3")

    def test_no_base_and_different_is_conflict(self):
        _mk(self.xddp / "project-rulebook.md", "mine")
        _mk(self.docs / "project-rulebook.md", "theirs")
        self.assertEqual(rf.ensure("shared", self.xddp, self.docs, ["a"], "t")["action"], "conflict")


class TestUnfilled(unittest.TestCase):
    def _states(self, kind, text, keys):
        return {e["number"]: e for e in rf.unfilled(kind, text, keys)}

    def test_template_is_all_unfilled_and_history_omitted(self):
        for kind in ("shared", "repo", "cross"):
            states = self._states(kind, _tpl(kind), ["a", "b"])
            self.assertNotIn("7", states)
            self.assertTrue(all(e["state"] == "unfilled" for e in states.values()), kind)

    def test_partial_and_filled(self):
        text = _tpl("shared").replace("（プロジェクト固有の命名規約をここに記述する）", "- 名前は短く（出典: 人）", 1)
        e = self._states("shared", text, ["a", "b"])["2"]
        self.assertEqual(e["state"], "partial")
        self.assertEqual(e["unfilled_items"], ["クラス・関数・変数", "DB・API"])
        text = text.replace("（プロジェクト固有の命名規約をここに記述する）", "該当なし")
        self.assertEqual(self._states("shared", text, ["a", "b"])["2"]["state"], "filled")

    def test_code_values_and_example_rows(self):
        text = _tpl("shared").replace("DB: （データベース: PostgreSQL / MySQL / DynamoDB / etc.）", "DB: 該当なし")
        e = self._states("shared", text, ["a", "b"])["1"]
        self.assertEqual(e["state"], "partial")
        self.assertNotIn("DB", e["unfilled_items"])
        text = re.sub(r"^\| （例）.*\n", "", _tpl("shared"), flags=re.M)
        self.assertEqual(self._states("shared", text, ["a", "b"])["1.5"]["state"], "filled")

    def test_missing_heading(self):
        text = _tpl("repo").replace("## 2. アーキテクチャ概要", "## 2. 構成")
        self.assertEqual(self._states("repo", text, ["a"])["2"]["state"], "missing")

    def test_draft_depends_on_configuration(self):
        single = self._states("shared", _tpl("shared"), ["a"])
        multi = self._states("shared", _tpl("shared"), ["a", "b"])
        self.assertEqual(single["1.5"]["state"], "not-applicable")
        for n in ("1.5", "2", "3", "4", "6"):
            self.assertFalse(single[n]["draft"], n)
            self.assertTrue(multi[n]["draft"], n)
        self.assertTrue(single["1"]["draft"])
        self.assertFalse(multi["1.6"]["draft"])
        self.assertFalse(multi["5"]["draft"])


class TestDomainConstraints(unittest.TestCase):
    def test_template_and_not_applicable_are_empty(self):
        self.assertEqual(rf.domain_constraints(_tpl("shared")), "")
        text = _tpl("shared").replace("{制約内容}", "該当なし")
        self.assertEqual(rf.domain_constraints(text), "")

    def test_only_filled_rows_with_header(self):
        text = _tpl("shared").replace(
            "| 準拠すべき規格・法令 | {制約内容} | {根拠} |", "| 準拠すべき規格・法令 | XYZ に準拠 | 未確認 |", 1)
        out = rf.domain_constraints(text).splitlines()
        self.assertEqual(len(out), 3)
        self.assertIn("制約内容", out[0])
        self.assertIn("XYZ に準拠", out[2])


class TestPromoteResolveDiff(_Ws):
    def test_actions_and_base(self):
        _mk(self.xddp / "project-rulebook.md", "c1")
        _mk(self.xddp / "project-rulebook-a.md", "a1")
        res = {r["file"]: r["action"] for r in rf.promote(self.xddp, self.docs, ["a"])}
        self.assertEqual(res, {"project-rulebook.md": "copied", "project-rulebook-a.md": "copied"})
        self.assertEqual(rf.promote(self.xddp, self.docs, ["a"])[0]["action"], "same")
        _mk(self.xddp / "project-rulebook.md", "c2")
        self.assertEqual(rf.promote(self.xddp, self.docs, ["a"])[0]["action"], "copied")
        self.assertEqual((self.docs / "project-rulebook.md").read_text(encoding="utf-8"), "c2")
        _mk(self.docs / "project-rulebook.md", "c3")
        self.assertEqual(rf.promote(self.xddp, self.docs, ["a"])[0]["action"], "updated-from-docs")
        self.assertEqual((self.xddp / "project-rulebook.md").read_text(encoding="utf-8"), "c3")
        _mk(self.docs / "project-rulebook.md", "c4")
        _mk(self.xddp / "project-rulebook.md", "c5")
        self.assertEqual(rf.promote(self.xddp, self.docs, ["a"])[0]["action"], "conflict")
        self.assertEqual((self.docs / "project-rulebook.md").read_text(encoding="utf-8"), "c4")

    def test_single_copies_repo_not_cross(self):
        _mk(self.xddp / "project-rulebook-a.md", "a")
        _mk(self.xddp / "project-rulebook-cross.md", "x")
        res = {r["file"]: r["action"] for r in rf.promote(self.xddp, self.docs, ["a"])}
        self.assertEqual(res, {"project-rulebook.md": "absent", "project-rulebook-a.md": "copied"})
        self.assertFalse((self.docs / "cross").exists())
        res = {r["file"]: r["action"] for r in rf.promote(self.xddp, self.docs, ["a", "b"])}
        self.assertEqual(res["project-rulebook-cross.md"], "copied")
        self.assertEqual(res["project-rulebook-b.md"], "absent")

    def test_failed(self):
        _mk(self.xddp / "project-rulebook-a.md", "a")
        _mk(self.docs / "a", "not a directory")
        res = rf.promote(self.xddp, self.docs, ["a"])
        self.assertEqual(res[1]["action"], "failed")
        self.assertTrue(res[1]["error"])

    def test_resolve_and_diff(self):
        _mk(self.xddp / "project-rulebook.md", "mine\n")
        _mk(self.docs / "project-rulebook.md", "theirs\n")
        text = rf.diff(self.xddp, self.docs, "project-rulebook.md")
        self.assertIn("-theirs", text)
        self.assertIn("+mine", text)
        rf.resolve(self.xddp, self.docs, "project-rulebook.md", "docs")
        self.assertEqual((self.xddp / "project-rulebook.md").read_text(encoding="utf-8"), "theirs\n")
        self.assertEqual(rf.promote(self.xddp, self.docs, ["a"])[0]["action"], "same")
        _mk(self.xddp / "project-rulebook.md", "mine2\n")
        _mk(self.docs / "project-rulebook.md", "theirs2\n")
        code, out, _err = _run(["resolve", "--xddp-dir", str(self.xddp), "--docs", str(self.docs),
                                "--file", "project-rulebook.md", "--take", "xddp"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["action"], "resolved")
        self.assertEqual((self.docs / "project-rulebook.md").read_text(encoding="utf-8"), "mine2\n")

    def test_resolve_bad_name(self):
        code, _out, _err = _run(["resolve", "--xddp-dir", str(self.xddp), "--docs", str(self.docs),
                                 "--file", "other.md", "--take", "xddp"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
