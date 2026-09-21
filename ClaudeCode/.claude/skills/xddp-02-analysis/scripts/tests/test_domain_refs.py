import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import domain_refs as mod  # noqa: E402


def write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class NormalizeTokenTestCase(unittest.TestCase):
    def test_strips_delimiters_and_extension_case_insensitive(self):
        self.assertEqual(mod.normalize_token("mod_a2.py"), mod.normalize_token("mod-a2"))
        self.assertEqual(mod.normalize_token("Mod A2"), "moda2")


class ResolveMatchesTestCase(unittest.TestCase):
    def test_exact_match_no_length_limit(self):
        self.assertEqual(mod.resolve_matches(["ab", "cd"], ["ab"]), ["ab"])

    def test_partial_match_fallback_when_zero_exact(self):
        # "auth" (4 chars) partially matches candidate "auth-service"
        self.assertEqual(mod.resolve_matches(["auth-service", "billing"], ["auth"]), ["auth-service"])

    def test_partial_match_excluded_under_3_chars(self):
        # keyword normalized to 2 chars must not partial-match
        self.assertEqual(mod.resolve_matches(["ab-service"], ["ab"]), [])

    def test_exact_match_suppresses_partial_fallback_for_others(self):
        # one exact match exists among candidates -> partial matching is not applied at all
        result = mod.resolve_matches(["auth", "authentication"], ["auth"])
        self.assertEqual(result, ["auth"])


class ResolveNoAiIndexTestCase(unittest.TestCase):
    """AI_INDEX.md 不在時の直接列挙（3-1a）経路。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.docs = self.workspace / "baseline_docs"
        self.kw_file = self.root / "keywords.txt"

    def tearDown(self):
        self.tmp.cleanup()

    def _resolve(self, keywords, affected_repos=("repo-a",), is_multi=False):
        write(self.kw_file, "\n".join(keywords))
        return mod.resolve(
            workspace_root=self.workspace,
            xddp_dir="xddp",
            docs=self.docs,
            affected_repos=list(affected_repos),
            is_multi=is_multi,
            keywords=keywords,
        )

    def test_no_ai_index_direct_enumeration(self):
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md")
        write(self.docs / "repo-a" / "specs" / "billing" / "spec.md")
        result = self._resolve(["auth"])
        self.assertFalse(result["stats"]["ai_index_present"])
        self.assertEqual(result["domain_ref_mode"], "normal")
        self.assertIn("auth/spec.md", result["domain_ref_paths"])
        self.assertNotIn("billing/spec.md", result["domain_ref_paths"])

    def test_glossary_collected_unconditionally(self):
        write(self.docs / "glossary.md")
        write(self.docs / "repo-a" / "knowledge" / "glossary.md")
        result = self._resolve(["nomatch"])
        self.assertIn("glossary.md | 用語", result["domain_ref_paths"])
        self.assertEqual(result["domain_ref_paths"].count("用語"), 2)

    def test_lessons_learned_collected_unconditionally(self):
        write(self.docs / "repo-a" / "knowledge" / "lessons-learned.md")
        result = self._resolve(["nomatch"])
        self.assertIn("lessons-learned.md | 知見", result["domain_ref_paths"])

    def test_none_mode_when_nothing_found(self):
        result = self._resolve(["nomatch"])
        self.assertEqual(result["domain_ref_mode"], "none")
        self.assertEqual(result["domain_ref_paths"], "")


class ResolveAiIndexTestCase(unittest.TestCase):
    """AI_INDEX.md 実在時（3-2）経路。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.docs = self.workspace / "baseline_docs"
        self.docs.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _resolve(self, keywords, affected_repos=("repo-a",), is_multi=False):
        return mod.resolve(
            workspace_root=self.workspace,
            xddp_dir="xddp",
            docs=self.docs,
            affected_repos=list(affected_repos),
            is_multi=is_multi,
            keywords=keywords,
        )

    def _write_index(self, body: str):
        write(self.docs / "AI_INDEX.md", body)

    def test_module_matched_via_index_table(self):
        self._write_index(
            "## モジュール別最新仕様\n"
            "| リポジトリ | モジュール | spec | structure | state | 最終更新CR |\n"
            "|---|---|---|---|---|---|\n"
            "| repo-a | auth | [spec.md](repo-a/specs/auth/spec.md) | — | — | CR-1 |\n"
            "| repo-a | billing | [spec.md](repo-a/specs/billing/spec.md) | — | — | CR-1 |\n"
        )
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md")
        write(self.docs / "repo-a" / "specs" / "billing" / "spec.md")
        result = self._resolve(["auth"])
        self.assertTrue(result["stats"]["ai_index_present"])
        self.assertIn("auth/spec.md | 仕様", result["domain_ref_paths"])
        self.assertNotIn("billing/spec.md", result["domain_ref_paths"])

    def test_usecase_matched_via_purpose_column(self):
        self._write_index(
            "## ユースケース一覧\n"
            "| ユースケース | 目的（1行） | description | 関連モジュール | 最終更新CR |\n"
            "|---|---|---|---|---|\n"
            "| login-flow | ユーザー認証を行う | [description.md](system/specs/use-cases/login-flow/description.md) | auth | CR-1 |\n"
        )
        write(self.docs / "system" / "specs" / "use-cases" / "login-flow" / "description.md")
        result = self._resolve(["認証"])
        self.assertIn("login-flow/description.md | ユースケース", result["domain_ref_paths"])

    def test_malformed_table_recorded_in_stats(self):
        self._write_index("## ユースケース一覧\nこれはテーブルではない\n")
        result = self._resolve(["auth"])
        self.assertIn("ユースケース一覧", result["stats"]["ai_index_malformed_sections"])

    def test_code_knowledge_constraints_collected_for_matched_module(self):
        self._write_index(
            "## モジュール別最新仕様\n"
            "| リポジトリ | モジュール | spec | structure | state | 最終更新CR |\n"
            "|---|---|---|---|---|---|\n"
            "| repo-a | auth | [spec.md](repo-a/specs/auth/spec.md) | — | — | CR-1 |\n"
            "\n"
            "## code-knowledge インデックス\n"
            "| 知りたいこと | 参照先 |\n"
            "|---|---|\n"
            "| repo-a/auth 制約・注意事項 | [constraints.md](repo-a/knowledge/code-knowledge/auth/constraints.md) |\n"
        )
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md")
        write(self.docs / "repo-a" / "knowledge" / "code-knowledge" / "auth" / "constraints.md")
        result = self._resolve(["auth"])
        self.assertIn("constraints.md | 制約", result["domain_ref_paths"])


class FallbackTestCase(unittest.TestCase):
    """3-4 フォールバック列挙（{DOCS} 側ディレクトリ不在時）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.docs = self.workspace / "baseline_docs"

    def tearDown(self):
        self.tmp.cleanup()

    def _resolve(self, keywords, affected_repos=("repo-a",), is_multi=False):
        return mod.resolve(
            workspace_root=self.workspace,
            xddp_dir="xddp",
            docs=self.docs,
            affected_repos=list(affected_repos),
            is_multi=is_multi,
            keywords=keywords,
        )

    def test_repo_specs_missing_falls_back_to_latest_specs(self):
        # {DOCS}/repo-a/specs/ が存在しない -> latest-specs/repo-a/ から列挙
        write(self.workspace / "xddp" / "latest-specs" / "repo-a" / "auth" / "spec.md")
        result = self._resolve(["auth"])
        self.assertIn("a:repo-a", result["stats"]["fallback_applied"])
        self.assertIn("latest-specs", result["domain_ref_paths"])
        self.assertEqual(result["domain_ref_mode"], "degraded")

    def test_system_specs_missing_falls_back_to_latest_specs(self):
        write(self.workspace / "xddp" / "latest-specs" / "system" / "use-cases" / "login" / "description.md")
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md")  # repo specs dir exists (no fallback a)
        result = self._resolve(["login"])
        self.assertIn("b", result["stats"]["fallback_applied"])
        self.assertIn("login/description.md", result["domain_ref_paths"])

    def test_top_3_recency_completion_when_zero_matches(self):
        base = self.workspace / "xddp" / "latest-specs" / "repo-a"
        names = ["m1", "m2", "m3", "m4"]
        for i, name in enumerate(names):
            p = base / name / "spec.md"
            write(p)
            # ensure distinct, increasing mtimes (m4 newest)
            import os
            os.utime(p, (time.time() + i, time.time() + i))
        result = self._resolve(["nomatch-keyword-xyz"])
        # top 3 most-recent (m4, m3, m2) should be included, m1 excluded
        self.assertIn("m4/spec.md", result["domain_ref_paths"])
        self.assertIn("m3/spec.md", result["domain_ref_paths"])
        self.assertIn("m2/spec.md", result["domain_ref_paths"])
        self.assertNotIn("m1/spec.md", result["domain_ref_paths"])

    def test_no_fallback_when_docs_dir_exists(self):
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md")
        write(self.workspace / "xddp" / "latest-specs" / "repo-a" / "other" / "spec.md")
        result = self._resolve(["auth"])
        self.assertNotIn("a:repo-a", result["stats"]["fallback_applied"])
        self.assertNotIn("other/spec.md", result["domain_ref_paths"])


class DelimiterGuardTestCase(unittest.TestCase):
    def test_path_with_semicolon_excluded(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            docs = root / "workspace" / "baseline_docs"
            bad_dir = docs / "repo-a;evil" / "knowledge"
            write(bad_dir / "glossary.md")
            result = mod.resolve(
                workspace_root=root / "workspace",
                xddp_dir="xddp",
                docs=docs,
                affected_repos=["repo-a;evil"],
                is_multi=False,
                keywords=["x"],
            )
            self.assertNotIn("evil", result["domain_ref_paths"])
            self.assertGreaterEqual(result["stats"]["excluded_by_delimiter"], 1)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
