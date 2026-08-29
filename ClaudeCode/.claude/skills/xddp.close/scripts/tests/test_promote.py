import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import promote as mod  # noqa: E402


def _mk(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestPromoteSpecs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.xddp_dir = self.tmp / "xddp"
        self.docs = self.tmp / "baseline_docs"

    def test_promotes_repo_cross_system(self):
        _mk(self.xddp_dir / "latest-specs" / "repo-a" / "mod1" / "spec.md", "spec")
        _mk(self.xddp_dir / "latest-specs" / "cross" / "interfaces" / "if1" / "spec.md", "spec")
        _mk(self.xddp_dir / "latest-specs" / "system" / "use-cases" / "uc1" / "description.md", "d")

        repo_results = mod._init_repo_results(["repo-a"])
        mod.promote_specs(self.xddp_dir, self.docs, ["repo-a"], True, repo_results)
        self.assertTrue(repo_results["repo-a"]["ok"])
        self.assertTrue(repo_results["cross"]["ok"])
        self.assertTrue(repo_results["system"]["ok"])
        self.assertTrue((self.docs / "repo-a" / "specs" / "mod1" / "spec.md").exists())
        self.assertTrue((self.docs / "cross" / "specs" / "interfaces" / "if1" / "spec.md").exists())
        self.assertTrue((self.docs / "system" / "specs" / "use-cases" / "uc1" / "description.md").exists())

    def test_deletion_candidates_not_deleted(self):
        _mk(self.xddp_dir / "latest-specs" / "repo-a" / "mod1" / "spec.md", "spec")
        _mk(self.docs / "repo-a" / "specs" / "old-mod" / "spec.md", "old")

        repo_results = mod._init_repo_results(["repo-a"])
        deletion_candidates = mod.promote_specs(self.xddp_dir, self.docs, ["repo-a"], False, repo_results)
        self.assertTrue((self.docs / "repo-a" / "specs" / "old-mod").exists())
        self.assertIn(str(self.docs / "repo-a" / "specs" / "old-mod"), deletion_candidates)

    def test_partial_failure_isolated_per_repo(self):
        _mk(self.xddp_dir / "latest-specs" / "repo-ok" / "mod1" / "spec.md", "spec")
        _mk(self.xddp_dir / "latest-specs" / "repo-bad" / "mod1" / "spec.md", "spec")
        # repo-bad の昇格先を「同名ファイル」にして ENOTDIR 相当の copytree 失敗を誘発する
        (self.docs / "repo-bad").mkdir(parents=True)
        (self.docs / "repo-bad" / "specs").write_text("not a directory", encoding="utf-8")

        repo_results = mod._init_repo_results(["repo-ok", "repo-bad"])
        mod.promote_specs(self.xddp_dir, self.docs, ["repo-ok", "repo-bad"], False, repo_results)
        self.assertTrue(repo_results["repo-ok"]["ok"])
        self.assertFalse(repo_results["repo-bad"]["ok"])
        self.assertTrue((self.docs / "repo-ok" / "specs" / "mod1" / "spec.md").exists())


class TestAiIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.xddp_dir = self.tmp / "xddp"
        self.docs = self.tmp / "baseline_docs"
        self.docs.mkdir(parents=True)

    def test_initial_generation_from_skeleton(self):
        _mk(self.xddp_dir / "latest-specs" / "repo-a" / "mod1" / "spec.md", "spec")
        result = mod.update_ai_index(
            self.xddp_dir, self.docs, "CR-2026-001", ["repo-a"], False, False,
            False, {}, set())
        text = "\n".join(result["lines"])
        self.assertIn("## リポジトリ別仕様書", text)
        self.assertIn("repo-a", text)
        self.assertIn("mod1", text)

    def test_rerun_upsert_no_duplicate(self):
        _mk(self.xddp_dir / "latest-specs" / "repo-a" / "mod1" / "spec.md", "spec")
        r1 = mod.update_ai_index(
            self.xddp_dir, self.docs, "CR-2026-001", ["repo-a"], False, False,
            False, {}, set())
        mod._write_lines(self.docs / "AI_INDEX.md", r1["lines"])
        r2 = mod.update_ai_index(
            self.xddp_dir, self.docs, "CR-2026-001", ["repo-a"], False, False,
            False, {}, set())
        text2 = "\n".join(r2["lines"])
        self.assertEqual(text2.count("| repo-a | mod1 |"), 1)

    def test_preupdated_skip(self):
        _mk(self.xddp_dir / "latest-specs" / "repo-a" / "mod1" / "spec.md", "spec")
        preupdated = {"モジュール別最新仕様": "済"}
        result = mod.update_ai_index(
            self.xddp_dir, self.docs, "CR-2026-001", ["repo-a"], False, False,
            False, preupdated, set())
        text = "\n".join(result["lines"])
        # スキップ時はモジュール別最新仕様セクション自体が既存 AI_INDEX.md に無ければ生成されない
        # (スケルトンに見出しのみ存在するため見出しは残るが、行は追加されない)
        self.assertNotIn("| repo-a | mod1 |", text)

    def test_force_full_overrides_preupdated_skip(self):
        _mk(self.xddp_dir / "latest-specs" / "repo-a" / "mod1" / "spec.md", "spec")
        preupdated = {"モジュール別最新仕様": "済"}
        result = mod.update_ai_index(
            self.xddp_dir, self.docs, "CR-2026-001", ["repo-a"], False, False,
            True, preupdated, set())
        text = "\n".join(result["lines"])
        self.assertIn("| repo-a | mod1 |", text)

    def test_glossary_term_count(self):
        _mk(self.docs / "glossary.md",
            "# 用語集\n\n## 用語一覧\n\n"
            "| 正式表記 | 定義 |\n|---|---|\n| A | a |\n| B | b |\n| C | c |\n")
        count = mod._glossary_term_count(self.docs / "glossary.md")
        self.assertEqual(count, 3)

    def test_archive_candidates_detected_over_500_lines(self):
        lines = ["# AI_INDEX"] + [f"line {i}" for i in range(510)]
        lines.append("| entry-old | x | CR-2026-001 |")
        lines.append("| entry-new | x | CR-2026-900 |")
        candidates = mod.detect_archive_candidates(lines)
        self.assertTrue(any("CR-2026-001" in c for c in candidates))
        self.assertLess(
            [c for c in candidates].index([c for c in candidates if "CR-2026-001" in c][0]),
            [c for c in candidates].index([c for c in candidates if "CR-2026-900" in c][0]),
        )

    def test_no_archive_candidates_under_500_lines(self):
        lines = ["# AI_INDEX", "| entry | x | CR-2026-001 |"]
        self.assertEqual(mod.detect_archive_candidates(lines), [])


class TestLessonsLearned(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.docs = self.tmp / "baseline_docs"

    def _ll_source(self, entries: str) -> Path:
        path = self.tmp / "xddp" / "lessons-learned.md"
        _mk(path, "# 知見ログ\n\n## 知見詳細\n\n" + entries)
        return path

    def test_routes_by_repo_tag(self):
        entries = (
            "### LL-001：タイトルA\n\n"
            "**CR：** CR-2026-001 ／ **工程：** テスト ／ **repo：** repo-a ／ **タグ：** #テスト\n\n"
            "本文\n\n---\n\n"
            "### LL-002：タイトルB\n\n"
            "**CR：** CR-2026-001 ／ **工程：** 設計 ／ **repo：** cross ／ **タグ：** #設計\n\n"
            "本文\n\n---\n\n"
        )
        src = self._ll_source(entries)
        unresolved = mod.promote_lessons_learned(src, self.docs, "CR-2026-001", True, {})
        self.assertEqual(unresolved, [])
        self.assertIn("LL-001", (self.docs / "repo-a" / "knowledge" / "lessons-learned.md").read_text(encoding="utf-8"))
        self.assertIn("LL-002", (self.docs / "cross" / "knowledge" / "lessons-learned.md").read_text(encoding="utf-8"))

    def test_unknown_repo_not_promoted(self):
        entries = (
            "### LL-003：タイトルC\n\n"
            "**CR：** CR-2026-001 ／ **工程：** プロセス ／ **repo：** unknown ／ **タグ：** #プロセス\n\n"
            "本文\n\n---\n\n"
        )
        src = self._ll_source(entries)
        unresolved = mod.promote_lessons_learned(src, self.docs, "CR-2026-001", False, {})
        self.assertEqual(len(unresolved), 1)
        self.assertIn("LL-003", unresolved[0])
        self.assertFalse((self.docs / "unknown").exists())

    def test_other_cr_entries_not_promoted(self):
        entries = (
            "### LL-004：他CRのエントリ\n\n"
            "**CR：** CR-2026-999 ／ **工程：** テスト ／ **repo：** repo-a ／ **タグ：** #テスト\n\n"
            "本文\n\n---\n\n"
        )
        src = self._ll_source(entries)
        unresolved = mod.promote_lessons_learned(src, self.docs, "CR-2026-001", False, {})
        self.assertEqual(unresolved, [])
        self.assertFalse((self.docs / "repo-a" / "knowledge" / "lessons-learned.md").exists())

    def test_rerun_does_not_duplicate(self):
        entries = (
            "### LL-005：再実行テスト\n\n"
            "**CR：** CR-2026-001 ／ **工程：** テスト ／ **repo：** repo-a ／ **タグ：** #テスト\n\n"
            "本文\n\n---\n\n"
        )
        src = self._ll_source(entries)
        mod.promote_lessons_learned(src, self.docs, "CR-2026-001", False, {})
        mod.promote_lessons_learned(src, self.docs, "CR-2026-001", False, {})
        text = (self.docs / "repo-a" / "knowledge" / "lessons-learned.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("### LL-005："), 1)


class TestBreakingChanges(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cr_path = self.tmp / "xddp" / "CR-2026-001"

    def _write_chd(self, body: str) -> None:
        _mk(self.cr_path / "06_design" / "cross" / "CHD-CR-2026-001-cross.md", body)

    def test_detects_breaking_true(self):
        self._write_chd(
            "## インタフェース変更サマリ\n\n"
            "| インタフェース | 変更種別 | breaking |\n|---|---|---|\n"
            "| POST /jobs | 新規追加 | false |\n"
            "| event.x | フィールド追加 | true |\n"
        )
        found, interfaces, parseable = mod.detect_breaking_changes(self.cr_path, "CR-2026-001", True)
        self.assertTrue(parseable)
        self.assertTrue(found)
        self.assertEqual(interfaces, ["event.x"])

    def test_alternate_column_order_by_header_name(self):
        self._write_chd(
            "## インタフェース変更サマリ\n\n"
            "| # | インタフェース名 | 提供リポジトリ | 消費リポジトリ | 変更内容 | breaking |\n"
            "|---|---|---|---|---|---|\n"
            "| 1 | device.alert.raised | device-svc | notify-svc | ペイロード追加 | true |\n"
        )
        found, interfaces, parseable = mod.detect_breaking_changes(self.cr_path, "CR-2026-001", True)
        self.assertTrue(parseable)
        self.assertTrue(found)
        self.assertEqual(interfaces, ["device.alert.raised"])

    def test_missing_breaking_column_fails_loud(self):
        self._write_chd(
            "## インタフェース変更サマリ\n\n"
            "| 影響リポジトリ | インタフェース | 変更内容 |\n|---|---|---|\n"
            "| svc-a, svc-b | notify(value) | 契約変更 |\n"
        )
        found, interfaces, parseable = mod.detect_breaking_changes(self.cr_path, "CR-2026-001", True)
        self.assertFalse(parseable)
        self.assertIsNone(found)

    def test_no_cross_returns_false(self):
        found, interfaces, parseable = mod.detect_breaking_changes(self.cr_path, "CR-2026-001", False)
        self.assertFalse(found)
        self.assertTrue(parseable)


class TestPromoteBacklogAndRulebooks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.xddp_dir = self.tmp / "xddp"
        self.docs = self.tmp / "baseline_docs"

    def test_backlog_overwrite_not_append(self):
        _mk(self.xddp_dir / "improvement-backlog.md", "version1")
        mod.promote_backlog(self.xddp_dir, self.docs)
        _mk(self.xddp_dir / "improvement-backlog.md", "version2")
        mod.promote_backlog(self.xddp_dir, self.docs)
        text = (self.docs / "improvement-backlog.md").read_text(encoding="utf-8")
        self.assertEqual(text, "version2")

    def test_rulebooks_copied_per_repo_and_cross(self):
        _mk(self.xddp_dir / "project-rulebook.md", "common")
        _mk(self.xddp_dir / "project-rulebook-repo-a.md", "repo-a specific")
        _mk(self.xddp_dir / "project-rulebook-cross.md", "cross specific")
        repo_results = mod._init_repo_results(["repo-a"])
        mod.promote_rulebooks(self.xddp_dir, self.docs, ["repo-a"], True, repo_results, [])
        self.assertEqual((self.docs / "project-rulebook.md").read_text(encoding="utf-8"), "common")
        self.assertEqual(
            (self.docs / "repo-a" / "project-rulebook.md").read_text(encoding="utf-8"), "repo-a specific")
        self.assertEqual(
            (self.docs / "cross" / "project-rulebook.md").read_text(encoding="utf-8"), "cross specific")


class TestCrossStepFailureIsolation(unittest.TestCase):
    """1 repo の失敗が他 repo・他ステップを止めないことを Step C2〜C7 横断で確認する
    （test-fixtures/scratch-workspace/README.md の ENOTDIR 実機シナリオの単体テスト再現。
    レビュー指摘#10）。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.xddp_dir = self.tmp / "xddp"
        self.docs = self.tmp / "baseline_docs"
        self.cr_path = self.xddp_dir / "CR-2026-900"

    def test_ll_crs_test_rulebook_isolated_per_repo(self):
        # notify-svc 側の DOCS パスを「ファイル」にして ENOTDIR を誘発する（device-svc は正常）
        (self.docs / "notify-svc").mkdir(parents=True)
        (self.docs / "notify-svc").rmdir()
        _mk(self.docs / "notify-svc", "not a directory")

        _mk(self.xddp_dir / "lessons-learned.md",
            "### LL-001：device-svc向け\n\n"
            "**CR：** CR-2026-900 ／ **工程：** テスト ／ **repo：** device-svc ／ **タグ：** #テスト\n\n"
            "本文\n\n---\n\n"
            "### LL-002：notify-svc向け\n\n"
            "**CR：** CR-2026-900 ／ **工程：** コーディング ／ **repo：** notify-svc ／ **タグ：** #コーディング\n\n"
            "本文\n\n---\n\n")
        _mk(self.cr_path / "03_change-requirements" / "CRS-CR-2026-900.md", "crs")

        repo_results = mod._init_repo_results(["device-svc", "notify-svc"])
        mod.promote_lessons_learned(
            self.xddp_dir / "lessons-learned.md", self.docs, "CR-2026-900", False, repo_results)
        mod.promote_crs(self.cr_path, self.docs, "CR-2026-900", ["device-svc", "notify-svc"], False,
                         repo_results)

        self.assertTrue(repo_results["device-svc"]["ok"])
        self.assertFalse(repo_results["notify-svc"]["ok"])
        self.assertTrue(any("C3" in e for e in repo_results["notify-svc"]["errors"]))
        self.assertTrue(any("C4" in e for e in repo_results["notify-svc"]["errors"]))
        self.assertIn(
            "LL-001", (self.docs / "device-svc" / "knowledge" / "lessons-learned.md").read_text(encoding="utf-8"))
        self.assertTrue((self.docs / "device-svc" / "crs" / "CRS-CR-2026-900.md").exists())


if __name__ == "__main__":
    unittest.main()
