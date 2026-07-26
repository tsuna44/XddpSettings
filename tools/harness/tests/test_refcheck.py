#!/usr/bin/env python3
"""test_refcheck.py — refcheck の検査A/B/C/D 検出ロジックの unittest（トークン0）。

正例（実リポジトリ = 現状クリーン）と異常系フィクスチャ（tests/fixtures/badrepo）で
各検査の検出・非検出を固定する。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import refcheck  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BADREPO = FIXTURES / "badrepo"
# 実リポジトリルート（tools/harness/tests → 3つ上）
REPO_ROOT = Path(__file__).resolve().parents[3]


def _errors(vs):
    return [v for v in vs if v["severity"] == "error"]


def _warnings(vs):
    return [v for v in vs if v["severity"] == "warning"]


def _msgs(vs, check=None, severity=None):
    return [v["message"] for v in vs
            if (check is None or v["check"] == check)
            and (severity is None or v["severity"] == severity)]


class TestNormalizeHeading(unittest.TestCase):
    def test_strips_trailing_parenthetical(self):
        self.assertEqual(
            refcheck.normalize_heading("## Regenerate CRS Excel (UR-016)"),
            "Regenerate CRS Excel")

    def test_strips_fullwidth_parenthetical(self):
        self.assertEqual(
            refcheck.normalize_heading("## レビュー（最大 N 回）"), "レビュー")

    def test_plain_heading_unchanged(self):
        self.assertEqual(refcheck.normalize_heading("## Load Config"), "Load Config")


class TestCheckA(unittest.TestCase):
    def setUp(self):
        self.vs = refcheck.run(BADREPO, checks="A")

    def test_detects_missing_heading(self):
        errs = _errors(self.vs)
        self.assertTrue(any("Missing Heading" in m for m in _msgs(errs, "A")),
                        f"got: {_msgs(errs, 'A')}")

    def test_resolves_good_and_normalized_headings(self):
        # "Good Heading" と正規化一致する "Numbered Section (X-01)" は違反にならない
        self.assertFalse(any("Good Heading" in m for m in _msgs(self.vs, "A")))
        self.assertFalse(any("Numbered Section" in m for m in _msgs(self.vs, "A")))


class TestCheckB(unittest.TestCase):
    def setUp(self):
        self.vs = refcheck.run(BADREPO, checks="B")

    def test_missing_agent_is_error(self):
        self.assertTrue(
            any("demo-missing-agent" in m for m in _msgs(_errors(self.vs), "B")))

    def test_name_frontmatter_mismatch_is_error(self):
        self.assertTrue(
            any("demo-wrongname" in m or "demo-badname-agent" in m
                for m in _msgs(_errors(self.vs), "B")))

    def test_unknown_key_is_warning_not_error(self):
        self.assertTrue(
            any("BOGUS_KEY" in m for m in _msgs(_warnings(self.vs), "B")))
        self.assertFalse(
            any("BOGUS_KEY" in m for m in _msgs(_errors(self.vs), "B")))


class TestCheckC(unittest.TestCase):
    def setUp(self):
        self.vs = refcheck.run(BADREPO, checks="C")

    def test_unmentioned_control_placeholder_warned(self):
        self.assertTrue(
            any("UNMENTIONED_CTRL" in m for m in _msgs(_warnings(self.vs), "C")))

    def test_domain_examples_excluded(self):
        joined = " ".join(_msgs(self.vs, "C"))
        self.assertNotIn("{DB}", joined)
        self.assertNotIn("{GPIO}", joined)

    def test_check_c_never_errors(self):
        self.assertEqual(_errors(refcheck.run(BADREPO, checks="C")), [])


class TestCheckD(unittest.TestCase):
    def setUp(self):
        skills_dir = BADREPO / "ClaudeCode/.claude/skills"
        skill_files = refcheck.discover_skill_md(skills_dir)
        # フィクスチャスクリプト名を対象集合に注入
        self.vs = refcheck.check_d_script_wiring(
            skill_files, skills_dir, BADREPO,
            deterministic_scripts={"demo_tool.py"})

    def test_undefined_subcommand_is_error(self):
        self.assertTrue(
            any("bogus-sub" in m for m in _msgs(_errors(self.vs), "D")),
            f"got: {_msgs(self.vs, 'D')}")

    def test_undefined_flag_is_error(self):
        self.assertTrue(
            any("--badflag" in m for m in _msgs(_errors(self.vs), "D")))

    def test_valid_calls_not_flagged(self):
        # run --path/--mode・stat --path は有効なので違反にならない
        for m in _msgs(self.vs, "D"):
            self.assertNotIn("未定義フラグ --mode", m)
            self.assertNotIn("未定義フラグ --path", m)


class TestRealRepoClean(unittest.TestCase):
    """回帰ガード: 現行リポジトリは refcheck エラー0（参照整合が保たれている）。"""

    def test_no_errors_in_real_repo(self):
        vs = refcheck.run(REPO_ROOT)
        errs = _errors(vs)
        self.assertEqual(
            errs, [],
            "実リポジトリに参照整合エラー: "
            + "; ".join(f"{v['check']} {v['file']}:{v['line']} {v['message']}"
                        for v in errs))


if __name__ == "__main__":
    unittest.main()
