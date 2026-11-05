import os
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


class ResolveDirectTestCase(unittest.TestCase):
    """{DOCS} の直接列挙。"""

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

    def test_direct_enumeration(self):
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md")
        write(self.docs / "repo-a" / "specs" / "billing" / "spec.md")
        result = self._resolve(["auth"])
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


UC_TEMPLATE = """---
version: "1.0.0"
last-updated-cr: "CR-1"
related-modules:
{related}
---

# ユースケース記述 — {name}

## 2. 目的・ゴール

{purpose}

---
"""


def write_usecase(root: Path, name: str, purpose: str, related=()) -> Path:
    body = "\n".join(f'  - "{m}"' for m in related) if related else "  []"
    if not related:
        text = UC_TEMPLATE.replace("related-modules:\n{related}", "related-modules: []")
    else:
        text = UC_TEMPLATE.replace("{related}", body)
    path = root / name / "description.md"
    write(path, text.replace("{name}", name).replace("{purpose}", purpose))
    return path


class ResolveTestCase(unittest.TestCase):
    """{DOCS} と latest-specs の直接列挙（AI_INDEX は読まない）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.docs = self.workspace / "baseline_docs"
        self.latest = self.workspace / "xddp" / "latest-specs"
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

    def _items(self, result):
        return [tuple(item.split(" | ")) for item in filter(None, result["domain_ref_paths"].split(" ; "))]

    def test_usecase_matched_via_purpose(self):
        write_usecase(self.docs / "system" / "specs" / "use-cases", "login-flow", "ユーザー認証を行う")
        result = self._resolve(["認証"])
        self.assertIn("login-flow/description.md | ユースケース", result["domain_ref_paths"])

    def test_related_modules_resolved_by_normalized_name(self):
        write_usecase(self.docs / "system" / "specs" / "use-cases", "login-flow", "ユーザー認証を行う",
                      related=("Auth_Service", "no-such-module"))
        write(self.docs / "repo-a" / "specs" / "auth-service" / "spec.md")
        write(self.docs / "repo-a" / "specs" / "billing" / "spec.md")
        result = self._resolve(["認証"])
        self.assertIn("auth-service/spec.md | 仕様", result["domain_ref_paths"])
        self.assertNotIn("billing/spec.md", result["domain_ref_paths"])
        self.assertEqual(result["stats"]["unresolved_related_modules"],
                         [{"repos": ["repo-a"], "usecase": "login-flow", "value": "no-such-module"}])

    def test_same_result_with_and_without_ai_index(self):
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md")
        write(self.docs / "repo-a" / "knowledge" / "code-knowledge" / "_structures" / "x-relations.md")
        without = self._resolve(["auth"])
        write(self.docs / "AI_INDEX.md",
              "## モジュール別最新仕様\n| リポジトリ | モジュール | spec | structure | state | 最終更新CR |\n"
              "|---|---|---|---|---|---|\n| repo-a | billing | — | — | — | CR-1 |\n")
        self.assertEqual(self._resolve(["auth"]), without)

    def test_shared_knowledge_collected_per_file(self):
        ck = self.docs / "repo-a" / "knowledge" / "code-knowledge"
        write(ck / "_structures" / "a-relations.md")
        write(ck / "_structures" / "b-relations.md")
        write(ck / "_structures" / "note.txt")
        write(ck / "_structures" / "nested" / "c.md")
        write(ck / "_constants" / "shared-constants.md")
        write(ck / "_flows" / "x-sequence.md")
        cross_ck = self.docs / "cross" / "knowledge" / "code-knowledge"
        write(cross_ck / "_constants" / "cross-constants.md")
        items = self._items(self._resolve(["nomatch"]))
        shared = sorted((Path(p).relative_to(self.docs.resolve()).as_posix(), t) for p, t in items
                        if t in ("共有構造体", "共有定数"))
        self.assertEqual(shared, [
            ("repo-a/knowledge/code-knowledge/_constants/shared-constants.md", "共有定数"),
            ("repo-a/knowledge/code-knowledge/_structures/a-relations.md", "共有構造体"),
            ("repo-a/knowledge/code-knowledge/_structures/b-relations.md", "共有構造体"),
        ])
        self.assertFalse(any("_flows" in p for p, _ in items))
        self.assertFalse(any(Path(p).is_dir() for p, _ in items))

    def test_shared_knowledge_cross_when_multi(self):
        cross_ck = self.docs / "cross" / "knowledge" / "code-knowledge"
        write(cross_ck / "_constants" / "cross-constants.md")
        result = self._resolve(["nomatch"], is_multi=True)
        self.assertIn("cross/knowledge/code-knowledge/_constants/cross-constants.md | 共有定数",
                      result["domain_ref_paths"])

    def test_latest_only_module_usecase_interface_are_degraded(self):
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md")
        write(self.latest / "repo-a" / "auth" / "spec.md")
        write(self.latest / "repo-a" / "authz" / "spec.md")
        write_usecase(self.latest / "system" / "use-cases", "authz-flow", "x")
        write(self.latest / "cross" / "interfaces" / "authz-event" / "spec.md")
        result = self._resolve(["auth", "authz", "authz-flow", "authz-event"], is_multi=True)
        items = self._items(result)
        paths = [p for p, _ in items]
        self.assertIn(str((self.docs / "repo-a" / "specs" / "auth" / "spec.md").resolve()), paths)
        self.assertNotIn(str((self.latest / "repo-a" / "auth" / "spec.md").resolve()), paths)
        self.assertIn(str((self.latest / "repo-a" / "authz" / "spec.md").resolve()), paths)
        self.assertIn(str((self.latest / "system" / "use-cases" / "authz-flow" / "description.md").resolve()),
                      paths)
        self.assertIn(str((self.latest / "cross" / "interfaces" / "authz-event" / "spec.md").resolve()), paths)
        self.assertEqual(result["domain_ref_mode"], "degraded")
        self.assertEqual(result["stats"]["fallback_applied"], [])

    def test_specs_readme_only_still_reads_latest(self):
        write(self.docs / "repo-a" / "specs" / "README.md")
        write(self.latest / "repo-a" / "auth" / "spec.md")
        result = self._resolve(["auth"])
        self.assertIn("latest-specs/repo-a/auth/spec.md | 仕様", result["domain_ref_paths"])
        self.assertEqual(result["domain_ref_mode"], "degraded")

    def test_cross_interface_path(self):
        write(self.docs / "cross" / "specs" / "interfaces" / "alert-event" / "spec.md")
        result = self._resolve(["alert-event"], is_multi=True)
        self.assertIn("cross/specs/interfaces/alert-event/spec.md | 仕様", result["domain_ref_paths"])

    def test_no_cross_interface_without_multi(self):
        write(self.docs / "cross" / "specs" / "interfaces" / "alert-event" / "spec.md")
        result = self._resolve(["alert-event"])
        self.assertNotIn("alert-event", result["domain_ref_paths"])


class ConstraintCollectionTestCase(unittest.TestCase):
    """制約は code-knowledge の直接列挙（置き場所の最後の要素の照合と祖先・_general・_root）。"""

    PLACES = ("src/auth/login", "src/auth", "src", "_general", "_root", "lib/net", "_flows/x")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.docs = self.workspace / "baseline_docs"
        self.know = self.docs / "repo-a" / "knowledge" / "code-knowledge"
        self.docs.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _places(self, *places):
        for p in places:
            write(self.know / p / "constraints.md")

    def _collected(self, keywords):
        result = mod.resolve(workspace_root=self.workspace, xddp_dir="xddp", docs=self.docs,
                             affected_repos=["repo-a"], is_multi=False, keywords=keywords)
        know = str(self.know.resolve())
        out = set()
        for item in filter(None, result["domain_ref_paths"].split(" ; ")):
            path, type_ = item.split(" | ")
            if type_ == "制約":
                out.add(path[len(know) + 1:-len("/constraints.md")])
        return out

    def test_last_element_and_ancestors_general_root(self):
        self._places(*self.PLACES)
        self.assertEqual(self._collected(["login"]),
                         {"src/auth/login", "src/auth", "src", "_general", "_root"})

    def test_same_with_and_without_ai_index(self):
        self._places(*self.PLACES)
        without = self._collected(["login"])
        write(self.docs / "AI_INDEX.md",
              "## code-knowledge インデックス\n| 知りたいこと | 参照先 |\n|---|---|\n"
              "| repo-a/src 制約・注意事項 | [constraints.md](repo-a/knowledge/code-knowledge/src/constraints.md) |\n")
        self.assertEqual(self._collected(["login"]), without)

    def test_first_element_only_does_not_collect_nested(self):
        self._places("src/auth", "_general")
        self.assertEqual(self._collected(["src"]), {"_general"})

    def test_single_element_place_matches_as_last(self):
        self._places("src", "lib")
        self.assertEqual(self._collected(["src"]), {"src"})

    def test_matched_module_name_collects_old_style_place(self):
        self._places("src-auth", "billing")
        write_usecase(self.docs / "system" / "specs" / "use-cases", "login-flow", "ユーザー認証を行う",
                      related=("src-auth",))
        write(self.docs / "repo-a" / "specs" / "src-auth" / "spec.md")
        self.assertEqual(self._collected(["認証"]), {"src-auth"})

    def test_nothing_without_code_knowledge(self):
        self.assertEqual(self._collected(["login"]), set())


class FallbackTestCase(unittest.TestCase):
    """キーワードに当たらず {DOCS} 側に1つも無いときの、latest-specs の更新日時の新しい順の上位 N 件。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.docs = self.workspace / "baseline_docs"
        self.latest = self.workspace / "xddp" / "latest-specs"

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

    def _touch_in_order(self, paths):
        for i, p in enumerate(paths):
            write(p)
            os.utime(p, (time.time() + i, time.time() + i))

    def test_keyword_match_from_latest_is_not_fallback(self):
        write(self.latest / "repo-a" / "auth" / "spec.md")
        result = self._resolve(["auth"])
        self.assertEqual(result["stats"]["fallback_applied"], [])
        self.assertIn("latest-specs/repo-a/auth/spec.md", result["domain_ref_paths"])
        self.assertEqual(result["domain_ref_mode"], "degraded")

    def test_module_top_3_when_docs_has_no_module(self):
        self._touch_in_order([self.latest / "repo-a" / n / "spec.md" for n in ("m1", "m2", "m3", "m4")])
        write(self.docs / "repo-a" / "specs" / "README.md")
        result = self._resolve(["nomatch-keyword-xyz"])
        self.assertIn("a:repo-a", result["stats"]["fallback_applied"])
        for n in ("m4", "m3", "m2"):
            self.assertIn(f"{n}/spec.md", result["domain_ref_paths"])
        self.assertNotIn("m1/spec.md", result["domain_ref_paths"])

    def test_usecase_top_3_when_docs_has_no_usecase(self):
        uc = self.latest / "system" / "use-cases"
        self._touch_in_order([uc / n / "description.md" for n in ("u1", "u2", "u3", "u4")])
        result = self._resolve(["nomatch-keyword-xyz"])
        self.assertIn("b", result["stats"]["fallback_applied"])
        self.assertIn("u4/description.md", result["domain_ref_paths"])
        self.assertNotIn("u1/description.md", result["domain_ref_paths"])

    def test_no_fallback_when_docs_has_one(self):
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md")
        write_usecase(self.docs / "system" / "specs" / "use-cases", "login", "x")
        write(self.latest / "repo-a" / "other" / "spec.md")
        write_usecase(self.latest / "system" / "use-cases", "other-uc", "y")
        result = self._resolve(["nomatch-keyword-xyz"])
        self.assertEqual(result["stats"]["fallback_applied"], [])
        self.assertNotIn("other", result["domain_ref_paths"])


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
