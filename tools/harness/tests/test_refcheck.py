#!/usr/bin/env python3
"""test_refcheck.py — refcheck の検査A/B/C/D/E 検出ロジックの unittest（トークン0）。

正例（実リポジトリ = 現状クリーン）と異常系フィクスチャ（tests/fixtures/badrepo）で
各検査の検出・非検出を固定する。
"""
import sys
import tempfile
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


REVIEWERREPO = FIXTURES / "reviewerrepo"


class TestCheckEReviewerChecklists(unittest.TestCase):
    """検査E: reviewer チェックリストの実在・構造整合。"""

    @classmethod
    def setUpClass(cls):
        cls.vs = refcheck.run(REVIEWERREPO, checks="E")

    def test_missing_checklist_file_is_error(self):
        self.assertTrue(any("SPO.md が無い" in m
                            for m in _msgs(self.vs, "E", "error")))

    def test_missing_required_heading_is_error(self):
        self.assertTrue(any("Primary Checklist" in m
                            for m in _msgs(self.vs, "E", "error")))

    def test_downstream_origin_mismatch_is_error(self):
        self.assertTrue(any("一致しない" in m
                            for m in _msgs(self.vs, "E", "error")))

    def test_missing_downstream_heading_is_error(self):
        self.assertTrue(any("次工程チェックリストを持つ型だが" in m
                            for m in _msgs(self.vs, "E", "error")))

    def test_stray_file_is_warning_not_error(self):
        self.assertTrue(any("STRAY" in v["file"]
                            for v in self.vs if v["severity"] == "warning"))
        self.assertFalse(any("STRAY" in v["file"]
                             for v in self.vs if v["severity"] == "error"))

    def test_valid_file_not_flagged(self):
        self.assertFalse(any("ANA.md" in v["file"] for v in self.vs))

    def test_noop_when_reviewer_agent_absent(self):
        self.assertEqual(refcheck.run(BADREPO, checks="E"), [])


class TestCheckF(unittest.TestCase):
    """検査F: デプロイ対象における設計根拠・変更履歴記述の検出。"""

    def _write(self, root: Path, rel: str, content: str) -> Path:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_detects_plan_reference_as_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self._write(root, "ClaudeCode/.claude/skills/demo.skill/SKILL.md",
                            "See PLAN-20260913 for details.\n")
            vs = refcheck.check_f_history_leakage([f], root)
            self.assertTrue(any(v["severity"] == "error" and "PLAN-" in v["message"]
                                for v in vs), vs)

    def test_detects_old_step_reference_as_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self._write(root, "ClaudeCode/.claude/skills/demo.skill/SKILL.md",
                            "旧 Step A did something that is now removed.\n")
            vs = refcheck.check_f_history_leakage([f], root)
            self.assertTrue(any(v["severity"] == "error" for v in vs), vs)

    def test_history_phrase_is_warning_only_and_does_not_fail_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self._write(root, "ClaudeCode/.claude/skills/demo.skill/SKILL.md",
                            "従来は手動で行っていた。\n")
            vs = refcheck.check_f_history_leakage([f], root)
            self.assertTrue(any(v["severity"] == "warning" for v in vs), vs)
            self.assertFalse(any(v["severity"] == "error" for v in vs), vs)

    def test_templates_dir_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self._write(root, "ClaudeCode/.claude/skills/demo.skill/templates/t.md",
                            "PLAN-20260913 example content.\n")
            vs = refcheck.check_f_history_leakage([f], root)
            self.assertEqual(vs, [])

    def test_scripts_dir_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self._write(root, "ClaudeCode/.claude/skills/demo.skill/scripts/notes.md",
                            "PLAN-20260913 internal note.\n")
            vs = refcheck.check_f_history_leakage([f], root)
            self.assertEqual(vs, [])

    def test_plan_review_skill_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self._write(root, "ClaudeCode/.claude/skills/xddp.plan-review/SKILL.md",
                            "Example: PLAN-20260531-foo.md\n")
            vs = refcheck.check_f_history_leakage([f], root)
            self.assertEqual(vs, [])

    def test_adr_reference_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self._write(root, "ClaudeCode/.claude/skills/demo.skill/SKILL.md",
                            "設計根拠は ADR-0016 を参照。\n")
            vs = refcheck.check_f_history_leakage([f], root)
            self.assertEqual(vs, [])

    def test_run_default_checks_include_f(self):
        self.assertIn("F", "ABCDEF")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "ClaudeCode/.claude/skills/demo.skill/SKILL.md",
                        "See PLAN-20260913 for details.\n")
            vs = refcheck.run(root)
            self.assertTrue(any(v["check"] == "F" for v in vs), vs)


class TestCheckG(unittest.TestCase):
    """検査G: xddp.common/procedures/ と「## Procedures Index」の整合。"""

    def _write(self, root: Path, rel: str, content: str) -> Path:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _base_skill_md(self, indexed_items: str) -> str:
        return (
            "---\ndescription: demo\n---\n\n# XDDP Common Logic\n\n"
            "## Load Config\n\nbody\n\n"
            "## Procedures Index\n\n"
            f"{indexed_items}\n"
        )

    def test_missing_from_index_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/SKILL.md",
                        self._base_skill_md(""))
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/procedures/foo-bar.md",
                        "# Foo Bar\n\n> scope note\n\n## Foo Bar\n\nbody\n")
            vs = refcheck.check_g_procedures_index(root)
            self.assertTrue(any("foo-bar.md" in v["message"] and "記載されていない" in v["message"]
                                for v in vs), vs)

    def test_stale_index_entry_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/SKILL.md",
                        self._base_skill_md("- `ghost.md` — Ghost: not real"))
            (root / "ClaudeCode/.claude/skills/xddp.common/procedures").mkdir(parents=True)
            vs = refcheck.check_g_procedures_index(root)
            self.assertTrue(any("ghost.md" in v["message"] and "実在しない" in v["message"]
                                for v in vs), vs)

    def test_multiple_h2_headings_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/SKILL.md",
                        self._base_skill_md("- `foo-bar.md` — Foo Bar: desc"))
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/procedures/foo-bar.md",
                        "# Foo Bar\n\n> scope\n\n## Foo Bar\n\nbody\n\n## Extra Heading\n\nmore\n")
            vs = refcheck.check_g_procedures_index(root)
            self.assertTrue(any("1ファイル1見出し" in v["message"] for v in vs), vs)

    def test_filename_mismatch_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/SKILL.md",
                        self._base_skill_md("- `wrong-name.md` — Foo Bar: desc"))
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/procedures/wrong-name.md",
                        "# Foo Bar\n\n> scope\n\n## Foo Bar\n\nbody\n")
            vs = refcheck.check_g_procedures_index(root)
            self.assertTrue(any("kebab-case" in v["message"] for v in vs), vs)

    def test_clean_case_no_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/SKILL.md",
                        self._base_skill_md("- `foo-bar.md` — Foo Bar: desc"))
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/procedures/foo-bar.md",
                        "# Foo Bar\n\n> scope\n\n## Foo Bar\n\nbody\n")
            vs = refcheck.check_g_procedures_index(root)
            self.assertEqual(vs, [])

    def test_no_index_heading_but_files_exist_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/SKILL.md",
                        "---\ndescription: demo\n---\n\n## Load Config\n\nbody\n")
            self._write(root, "ClaudeCode/.claude/skills/xddp.common/procedures/foo-bar.md",
                        "# Foo Bar\n\n> scope\n\n## Foo Bar\n\nbody\n")
            vs = refcheck.check_g_procedures_index(root)
            self.assertTrue(any("Procedures Index」が無い" in v["message"] for v in vs), vs)


class TestDeterministicScripts(unittest.TestCase):
    def test_xddp_config_registered(self):
        self.assertIn("xddp_config.py", refcheck.DETERMINISTIC_SCRIPTS)


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
