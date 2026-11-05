import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
SKILLS = SCRIPTS.parent.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SKILLS / "xddp-close" / "scripts"))
sys.path.insert(0, str(SKILLS / "xddp-02-analysis" / "scripts"))

import ai_index as mod  # noqa: E402
import domain_refs  # noqa: E402
import promote  # noqa: E402


def write(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def spec(cr: str = "", **extra) -> str:
    lines = ["---", 'version: "1.2.0"']
    if cr:
        lines.append(f'last-updated-cr: "{cr}"')
    lines += [f"{k}: {v}" for k, v in extra.items()]
    return "\n".join(lines + ["---", "", "# spec", ""])


def usecase(cr: str, purpose: str, related=()) -> str:
    rel = "related-modules:\n" + "".join(f'  - "{m}"\n' for m in related) if related else "related-modules: []\n"
    return (f'---\nversion: "1.0.0"\nlast-updated-cr: "{cr}"\n{rel}---\n\n# uc\n\n'
            f"## 2. 目的・ゴール\n\n{purpose}\n\n---\n")


def section(text: str, heading: str) -> list:
    lines = text.split("\n")
    i = lines.index(heading)
    out = []
    for line in lines[i + 1:]:
        if line.startswith("## "):
            break
        if line.startswith("|") and not line.startswith("|---"):
            out.append(line)
    return out[1:]  # ヘッダを除く


class BuildTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.docs = self.tmp / "baseline_docs"
        self.docs.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _build(self, repos=("repo-a",), is_multi=False):
        result = mod.build(self.docs, list(repos), is_multi)
        return result, (self.docs / "AI_INDEX.md").read_text(encoding="utf-8")

    def test_docs_missing_does_nothing(self):
        result = mod.build(self.tmp / "nope", ["repo-a"], False)
        self.assertTrue(result["skipped"])
        self.assertFalse((self.tmp / "nope").exists())

    def test_rows_follow_docs_contents(self):
        specs = self.docs / "repo-a" / "specs"
        write(specs / "overview" / "architecture.md", spec("CR-2026-002"))
        write(specs / "auth" / "spec.md", spec("CR-2026-001"))
        write(specs / "auth" / "structure.md")
        write(specs / "auth" / "state-machine.md")
        write(specs / "billing" / "spec.md", spec())
        write(specs / "no-spec" / "structure.md")
        write(specs / "README.md")
        write(self.docs / "system" / "specs" / "use-cases" / "login" / "description.md",
              usecase("SURVEY-20261101", "ログインする", ("auth",)))
        _, text = self._build()
        self.assertEqual(section(text, "## モジュール別最新仕様"), [
            "| repo-a | auth | [spec.md](repo-a/specs/auth/spec.md) | [structure.md](repo-a/specs/auth/structure.md)"
            " | [state-machine.md](repo-a/specs/auth/state-machine.md) | CR-2026-001 |",
            "| repo-a | billing | [spec.md](repo-a/specs/billing/spec.md) | — | — | — |",
        ])
        self.assertEqual(section(text, "## リポジトリ別仕様書"), [
            "| [repo-a](repo-a/specs/) | v1.2.0 | [overview](repo-a/specs/overview/) | 2 モジュール | CR-2026-002 |",
        ])
        self.assertEqual(section(text, "## ユースケース一覧"), [
            "| login | ログインする | [description.md](system/specs/use-cases/login/description.md) | auth"
            " | SURVEY-20261101 |",
        ])

    def test_idempotent(self):
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md", spec("CR-1"))
        first, text1 = self._build()
        second, text2 = self._build()
        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(text1, text2)

    def test_unmanaged_kept_retired_removed_no_placeholder(self):
        write(self.docs / "AI_INDEX.md",
              "# 古いタイトル\n\n"
              "## モジュール別最新仕様\n| a |\n|---|\n| （xddp-close 実行後に自動追記） |\n\n"
              "## 人のメモ\n\n本文\n\n```\n## フェンスの中\n```\n\n"
              "## 設計書ナビゲーション\n| x |\n\n"
              "## 工程11 AI_INDEX先行更新セクション\n- a: 済\n\n"
              "## もう一つ\n\nB\n")
        _, text = self._build()
        self.assertNotIn("古いタイトル", text)
        self.assertNotIn("自動追記", text)
        self.assertNotIn("設計書ナビゲーション", text)
        self.assertNotIn("先行更新", text)
        self.assertIn("## 人のメモ\n\n本文\n\n```\n## フェンスの中\n```", text)
        self.assertLess(text.index("## 知識参照ガイド"), text.index("## 人のメモ"))
        self.assertLess(text.index("## 人のメモ"), text.index("## もう一つ"))
        self.assertEqual(section(text, "## モジュール別最新仕様"), [])

    def test_pipe_escaped(self):
        write(self.docs / "system" / "specs" / "use-cases" / "uc" / "description.md",
              usecase("CR-1", "A | B"))
        _, text = self._build()
        self.assertIn("| A \\| B |", text)

    def test_interfaces_breaking_column(self):
        ifs = self.docs / "cross" / "specs" / "interfaces"
        write(ifs / "a-if" / "spec.md", spec("CR-1", breaking="true"))
        write(ifs / "b-if" / "spec.md", spec("CR-1", breaking="false"))
        write(ifs / "c-if" / "spec.md", spec("CR-1"))
        write(ifs / "c-if" / "schema.md")
        _, text = self._build(is_multi=True)
        rows = section(text, "## クロスインタフェース一覧")
        self.assertEqual(rows, [
            "| a-if | [spec.md](cross/specs/interfaces/a-if/spec.md) | — | v1.2.0 | ⚠️ あり | CR-1 |",
            "| b-if | [spec.md](cross/specs/interfaces/b-if/spec.md) | — | v1.2.0 | — | CR-1 |",
            "| c-if | [spec.md](cross/specs/interfaces/c-if/spec.md) | [schema.md](cross/specs/interfaces/c-if/schema.md)"
            " | v1.2.0 | — | CR-1 |",
        ])
        _, text2 = self._build(is_multi=True)
        self.assertEqual(section(text2, "## クロスインタフェース一覧"), rows)

    def test_no_interface_section_without_multi_or_dir(self):
        _, text = self._build()
        self.assertNotIn("## クロスインタフェース一覧", text)

    def test_deleted_module_row_disappears(self):
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md", spec("CR-1"))
        write(self.docs / "repo-a" / "specs" / "old" / "spec.md", spec("CR-1"))
        write(self.docs / "system" / "specs" / "use-cases" / "gone" / "description.md", usecase("CR-1", "x"))
        self._build()
        shutil.rmtree(self.docs / "repo-a" / "specs" / "old")
        shutil.rmtree(self.docs / "system" / "specs" / "use-cases" / "gone")
        _, text = self._build()
        self.assertNotIn("| old |", text)
        self.assertNotIn("gone", text)

    def test_crs_tsp_trs_rows_per_cr(self):
        a = self.docs / "repo-a"
        write(a / "crs" / "CRS-CR-2026-001.md")
        write(a / "crs" / "CRS-CR-2026-002.md")
        write(a / "test" / "TSP-CR-2026-001.md")
        write(a / "test" / "TRS-CR-2026-001-001.md")
        write(a / "test" / "TRS-CR-2026-001-002.md")
        write(a / "test" / "TRS-CR-2026-002-001.md")
        write(a / "test" / "TRS-CR-2026-003-001.md", "# テスト結果記録\n\n**対象CR：** CR-2026-003  \n")
        write(self.docs / "cross" / "test" / "TSP-CR-2026-001-cross.md")
        _, text = self._build(is_multi=True)
        self.assertEqual(section(text, "## 変更要求仕様書（CRS）ナビゲーション"), [
            "| repo-a | CR-2026-001 | [CRS-CR-2026-001.md](repo-a/crs/CRS-CR-2026-001.md) |",
            "| repo-a | CR-2026-002 | [CRS-CR-2026-002.md](repo-a/crs/CRS-CR-2026-002.md) |",
        ])
        self.assertEqual(section(text, "## テスト仕様（TSP）・テスト結果（TRS）"), [
            "| repo-a | CR-2026-001 | [TSP-CR-2026-001.md](repo-a/test/TSP-CR-2026-001.md)"
            " | [TRS-CR-2026-001-001.md](repo-a/test/TRS-CR-2026-001-001.md),"
            " [TRS-CR-2026-001-002.md](repo-a/test/TRS-CR-2026-001-002.md) |",
            "| repo-a | CR-2026-002 | — | [TRS-CR-2026-002-001.md](repo-a/test/TRS-CR-2026-002-001.md) |",
            "| repo-a | CR-2026-003 | — | [TRS-CR-2026-003-001.md](repo-a/test/TRS-CR-2026-003-001.md) |",
            "| cross | CR-2026-001 | [TSP-CR-2026-001-cross.md](cross/test/TSP-CR-2026-001-cross.md) | — |",
        ])

    def test_trs_cr_fallback_to_last_dash(self):
        self.assertEqual(mod.trs_cr(Path("/nope/TRS-CR-9-001.md"), set()), "CR-9")

    def test_common_knowledge_and_glossary(self):
        write(self.docs / "project-rulebook.md")
        write(self.docs / "repo-a" / "project-rulebook.md")
        write(self.docs / "glossary.md",
              "# 用語集\n\n## 用語一覧\n\n| 正式表記 | 定義 |\n|---|---|\n| A | a |\n| B | b |\n| C | c |\n")
        _, text = self._build()
        self.assertEqual(section(text, "## 共通知識"), [
            "| プロジェクト共通 | [project-rulebook.md](project-rulebook.md) |",
            "| repo-a | [project-rulebook.md](repo-a/project-rulebook.md) |",
        ])
        self.assertEqual(section(text, "## 用語集"), [
            "| プロジェクト共通 | [glossary.md](glossary.md)（用語数: 3） |",
        ])

    def test_code_knowledge_rows(self):
        know = self.docs / "repo-a" / "knowledge" / "code-knowledge"
        for rel in ("src", "src/auth/login", "_general", "_root", "_flows/x", "lib/_flows"):
            write(know / rel / "constraints.md", "# c")
        write(know / "_flows" / "shared-x-sequence.md")
        write(know / "_structures" / "a-relations.md")
        write(know / "_structures" / "b-relations.md")
        write(know / "_constants" / "shared-constants.md")
        _, text = self._build()
        rows = section(text, "## code-knowledge インデックス")
        self.assertEqual(rows, [
            "| repo-a/_general 制約・注意事項 | [constraints.md](repo-a/knowledge/code-knowledge/_general/constraints.md) |",
            "| repo-a/_root 制約・注意事項 | [constraints.md](repo-a/knowledge/code-knowledge/_root/constraints.md) |",
            "| repo-a/lib/_flows 制約・注意事項 | [constraints.md](repo-a/knowledge/code-knowledge/lib/_flows/constraints.md) |",
            "| repo-a/src 制約・注意事項 | [constraints.md](repo-a/knowledge/code-knowledge/src/constraints.md) |",
            "| repo-a/src/auth/login 制約・注意事項 |"
            " [constraints.md](repo-a/knowledge/code-knowledge/src/auth/login/constraints.md) |",
            "| repo-a 共有構造体 | [_structures/](repo-a/knowledge/code-knowledge/_structures/) |",
            "| repo-a 共有定数 | [_constants/](repo-a/knowledge/code-knowledge/_constants/) |",
            "| repo-a 機能間フロー | [_flows/](repo-a/knowledge/code-knowledge/_flows/) |",
        ])

    def test_archive_candidates(self):
        specs = self.docs / "repo-a" / "specs"
        for i in range(250):
            write(specs / f"m{i:03d}" / "spec.md", spec(f"CR-2026-{i:03d}"))
        uc = self.docs / "system" / "specs" / "use-cases"
        write(uc / "u-new" / "description.md", usecase("SURVEY-2026-11-02", "x"))
        write(uc / "u-old" / "description.md", usecase("SURVEY-20261101", "y"))
        for i in range(250):
            write(self.docs / "repo-a" / "crs" / f"CRS-CR-2025-{i:03d}.md")
        write(specs / "no-cr" / "spec.md", spec())
        write(self.docs / "project-rulebook.md")
        result, _ = self._build()
        cands = result["archive_candidates"]
        self.assertGreater(result["line_count"], 500)
        self.assertEqual(len(cands), 250 + 250 + 2)
        self.assertEqual(cands[0], {"section": "変更要求仕様書（CRS）ナビゲーション", "key": "repo-a",
                                    "cr": "CR-2025-000", "file": "repo-a/crs/CRS-CR-2025-000.md"})
        self.assertEqual([c["cr"] for c in cands[-2:]], ["SURVEY-20261101", "SURVEY-2026-11-02"])
        self.assertEqual(cands[-1]["file"], "system/specs/use-cases/u-new/description.md")
        crs = [c["cr"] for c in cands if c["cr"].startswith("CR-")]
        self.assertEqual(crs, sorted(crs))
        self.assertFalse(any(c["key"] == "no-cr" for c in cands))
        self.assertFalse(any(c["section"] == "共通知識" for c in cands))

    def test_no_archive_candidates_under_threshold(self):
        write(self.docs / "repo-a" / "specs" / "auth" / "spec.md", spec("CR-1"))
        result, _ = self._build()
        self.assertEqual(result["archive_candidates"], [])

    def test_cli(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            mod.main(["build", "--docs", str(self.docs), "--repos-keys", "repo-a,repo-b"])
        out = json.loads(buf.getvalue())
        self.assertTrue(out["ok"])
        self.assertTrue((self.docs / "AI_INDEX.md").is_file())


class WriterReaderTestCase(unittest.TestCase):
    """latest-specs → promote.promote_specs → {DOCS} → domain_refs.resolve・ai_index.build。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = self.tmp / "ws"
        self.xddp = self.workspace / "xddp"
        self.docs = self.workspace / "baseline_docs"
        latest = self.xddp / "latest-specs"
        write(latest / "repo-a" / "overview" / "architecture.md", spec("CR-1"))
        write(latest / "repo-a" / "label-store" / "spec.md", spec("CR-1"))
        write(latest / "system" / "use-cases" / "label-filter" / "description.md",
              usecase("CR-1", "ラベルで絞り込む", ("label-store",)))
        write(latest / "cross" / "interfaces" / "label-event" / "spec.md", spec("CR-1", breaking="true"))
        ck = self.docs / "repo-a" / "knowledge" / "code-knowledge"
        write(ck / "_structures" / "label-relations.md")
        write(ck / "_constants" / "shared-constants.md")
        write(ck / "label-store" / "constraints.md")
        results = promote._init_repo_results(["repo-a"])
        promote.promote_specs(self.xddp, self.docs, ["repo-a"], True, results)
        self.assertTrue(all(r["ok"] for r in results.values()))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_domain_refs_reads_what_promote_wrote(self):
        result = domain_refs.resolve(self.workspace, "xddp", self.docs, ["repo-a"], True, ["ラベル", "label-event"])
        items = {(Path(p).relative_to(self.docs.resolve()).as_posix(), t)
                 for p, t in (i.split(" | ") for i in result["domain_ref_paths"].split(" ; "))}
        self.assertEqual(result["domain_ref_mode"], "normal")
        for expected in [
            ("system/specs/use-cases/label-filter/description.md", "ユースケース"),
            ("repo-a/specs/label-store/spec.md", "仕様"),
            ("cross/specs/interfaces/label-event/spec.md", "仕様"),
            ("repo-a/knowledge/code-knowledge/_structures/label-relations.md", "共有構造体"),
            ("repo-a/knowledge/code-knowledge/_constants/shared-constants.md", "共有定数"),
            ("repo-a/knowledge/code-knowledge/label-store/constraints.md", "制約"),
        ]:
            self.assertIn(expected, items)

    def test_ai_index_lists_what_promote_wrote(self):
        mod.build(self.docs, ["repo-a"], True)
        text = (self.docs / "AI_INDEX.md").read_text(encoding="utf-8")
        self.assertIn("| label-filter | ラベルで絞り込む |", text)
        self.assertIn("| repo-a | label-store | [spec.md](repo-a/specs/label-store/spec.md) |", text)
        self.assertIn("| label-event | [spec.md](cross/specs/interfaces/label-event/spec.md) | — | v1.2.0 | ⚠️ あり"
                      " | CR-1 |", text)
        self.assertIn("| repo-a 共有構造体 | [_structures/](repo-a/knowledge/code-knowledge/_structures/) |", text)
        self.assertIn("| repo-a 共有定数 | [_constants/](repo-a/knowledge/code-knowledge/_constants/) |", text)
        self.assertIn("| repo-a/label-store 制約・注意事項 |", text)


if __name__ == "__main__":
    unittest.main()
