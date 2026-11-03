import json
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

    def test_code_knowledge_constraints_rows_use_places(self):
        know = self.docs / "repo-a" / "knowledge" / "code-knowledge"
        for rel in ("src", "src/auth/login", "_general", "_root", "_flows/x", "lib/_flows"):
            _mk(know / rel / "constraints.md", "# c")
        _mk(know / "_flows" / "shared-x-sequence.md", "# f")
        result = mod.update_ai_index(
            self.xddp_dir, self.docs, "CR-2026-001", ["repo-a"], False, False,
            False, {}, set())
        text = "\n".join(result["lines"])
        self.assertIn("| repo-a/src 制約・注意事項 | [constraints.md](repo-a/knowledge/code-knowledge/src/constraints.md) |",
                      text)
        for place in ("src/auth/login", "_general", "_root", "lib/_flows"):
            self.assertIn(f"| repo-a/{place} 制約・注意事項 | "
                          f"[constraints.md](repo-a/knowledge/code-knowledge/{place}/constraints.md) |", text)
        self.assertNotIn("_flows/x", text)
        self.assertIn("| repo-a 機能間フロー | [_flows/](repo-a/knowledge/code-knowledge/_flows/) |", text)
        order = [text.index(f"repo-a/{p} 制約") for p in ("_general", "_root", "lib/_flows", "src", "src/auth/login")]
        self.assertEqual(order, sorted(order))


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


CR = "CR-2026-001"
OLD = "CR-2026-900"


def _meta(cr=CR, repo="repo-a", tag="#リスク"):
    return f"**CR：** {cr} ／ **工程：** テスト ／ **repo：** {repo} ／ **タグ：** {tag}"


def _entry(ll_id, cr=CR, repo="repo-a", body="本文", title="題"):
    return f"### {ll_id}：{title}\n\n{_meta(cr, repo)}\n\n{body}\n\n---\n\n"


class TestExtractLL(unittest.TestCase):
    """extract-ll と Layer 2 への振り分けの区切り・判定（_ll_entry_meta）を確かめる。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.docs = self.tmp / "baseline_docs"
        self.src = self.tmp / "xddp" / "lessons-learned.md"
        self.out = self.tmp / "cr" / "pending-items" / f"LL-{CR}.md"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, body: str, prefix="# 知見ログ\n\n## 知見詳細\n\n"):
        _mk(self.src, prefix + body)
        return mod.extract_ll(self.src, CR, self.out)

    def _out_text(self):
        return self.out.read_text(encoding="utf-8") if self.out.exists() else ""

    def _layer2_ids(self):
        """has_cross=True・空の DOCS で振り分け、Layer 2 に書いた ID と unresolved の ID の集合。"""
        unresolved = mod.promote_lessons_learned(self.src, self.docs, CR, True, {})
        ids = set()
        for p in self.docs.rglob("lessons-learned.md"):
            for line in p.read_text(encoding="utf-8").split("\n"):
                m = mod.LL_ENTRY_RE.match(line)
                if m:
                    ids.add(m.group(1))
        for u in unresolved:
            ids.add(u.split("：", 1)[0])
        return ids

    def _layer2_text(self):
        return "\n".join(p.read_text(encoding="utf-8") for p in self.docs.rglob("lessons-learned.md"))

    def _out_ids(self):
        return {m.group(1) for m in (mod.LL_ENTRY_RE.match(l) for l in self._out_text().split("\n")) if m}

    # --- 基本 ---

    def test_only_current_cr_entries_in_order(self):
        r = self._run(_entry("LL-001", body="本文A") + _entry("LL-002", cr=OLD)
                      + _entry("LL-003", repo="cross", body="本文C"))
        self.assertEqual(r["count"], 2)
        self.assertEqual(r["out"], str(self.out))
        text = self._out_text()
        self.assertIn("本文A", text)
        self.assertNotIn("LL-002", text)
        self.assertLess(text.index("LL-001"), text.index("LL-003"))
        self.assertIn(_meta(CR, "cross"), text)

    def test_no_meta_entry_unparsed_even_in_other_cr_position(self):
        r = self._run(_entry("LL-001", cr=OLD) + "### LL-002：メタ行なし\n\n本文\n\n---\n\n")
        self.assertEqual(r["unparsed"], [{"id": "LL-002", "reason": "no-meta"}])
        self.assertEqual(r["count"], 0)

    def test_missing_lessons_file(self):
        r = mod.extract_ll(self.tmp / "nothing.md", CR, self.out)
        self.assertEqual(r, {"count": 0, "unparsed": [], "dropped": [], "out": None, "removed": False})

    def test_zero_entries_removes_previous_out(self):
        self._run(_entry("LL-001"))
        self.assertTrue(self.out.exists())
        r = self._run(_entry("LL-001", cr=OLD))
        self.assertEqual(r["count"], 0)
        self.assertIsNone(r["out"])
        self.assertTrue(r["removed"])
        self.assertFalse(self.out.exists())

    def test_cli_wiring(self):
        import io
        from contextlib import redirect_stdout
        _mk(self.src, _entry("LL-001"))
        argv = sys.argv
        sys.argv = ["promote.py", "extract-ll", "--cr", CR, "--lessons-file", str(self.src),
                    "--out", str(self.out)]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                mod.main()
        finally:
            sys.argv = argv
        lines = buf.getvalue().strip().split("\n")
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["count"], 1)
        self.assertIn("dropped", data)
        self.assertTrue(self.out.exists())

    def test_title_with_fullwidth_colon(self):
        r = self._run(_entry("LL-005", title="境界値判定：同値を含める"))
        self.assertEqual(r["count"], 1)
        self.assertEqual(self._out_ids(), {"LL-005"})
        mod.promote_lessons_learned(self.src, self.docs, CR, False, {})
        mod.promote_lessons_learned(self.src, self.docs, CR, False, {})
        text = (self.docs / "repo-a" / "knowledge" / "lessons-learned.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("### LL-005："), 1)

    def test_promote_skips_no_meta_entry(self):
        _mk(self.src, "### LL-001：メタ行なし\n\n**CR：** 欄なし\n\n---\n\n")
        unresolved = mod.promote_lessons_learned(self.src, self.docs, CR, True, {})
        self.assertEqual(unresolved, [])
        self.assertEqual(list(self.docs.rglob("lessons-learned.md")), [])

    def test_extract_and_layer2_agree(self):
        body = (_entry("LL-001") + _entry("LL-002", cr=OLD) + _entry("LL-003", repo="unknown")
                + _entry("LL-004", repo="cross") + "### LL-005: 崩れ\n\n" + _meta() + "\n\n---\n\n"
                + "### LL-006：メタなし\n\n本文\n")
        self._run(body)
        self.assertEqual(self._out_ids(), {"LL-001", "LL-003", "LL-004"})
        self.assertEqual(self._layer2_ids(), self._out_ids())

    # --- 見出しの崩れたエントリ（LL- あり） ---

    def test_broken_ll_headings_not_mixed(self):
        broken = ""
        for h in ("### LL-006: 半角", "## LL-007：浅い", "#### LL-008：深い", "###LL-009：空白なし"):
            broken += f"{h}\n\n{_meta(OLD)}\n\n崩れ本文\n\n---\n\n"
        r = self._run(_entry("LL-001") + broken + "## 付録\n\n付録の本文\n")
        self.assertEqual([u["id"] for u in r["unparsed"]],
                         ["LL-006: 半角", "LL-007：浅い", "LL-008：深い", "LL-009：空白なし"])
        self.assertTrue(all(u["reason"] == "heading" for u in r["unparsed"]))
        text = self._out_text()
        self.assertNotIn("崩れ本文", text)
        self.assertNotIn("付録の本文", text)
        self._layer2_ids()
        self.assertNotIn("崩れ本文", self._layer2_text())
        self.assertNotIn("付録の本文", self._layer2_text())

    def test_broken_ll_heading_after_other_cr_entry(self):
        r = self._run(_entry("LL-001", cr=OLD) + f"### LL-002: 半角\n\n{_meta()}\n\n本文\n")
        self.assertEqual(r["unparsed"], [{"id": "LL-002: 半角", "reason": "heading"}])
        self.assertEqual(r["count"], 0)

    # --- 見出しの崩れたエントリ（LL- なし） ---

    def test_broken_heading_without_ll_found_by_meta(self):
        body = (_entry("LL-001")
                + f"### 知見005：題\n\n{_meta()}\n\n混ざる本文5\n\n---\n\n"
                + f"#### 知見006：題\n\n{_meta()}\n\n混ざる本文6\n\n---\n\n")
        r = self._run(body)
        self.assertEqual(r["unparsed"], [{"id": "知見005：題", "reason": "heading"},
                                         {"id": "知見006：題", "reason": "heading"}])
        self.assertEqual(r["count"], 1)
        self.assertNotIn("混ざる本文", self._out_text())
        self._layer2_ids()
        self.assertNotIn("混ざる本文", self._layer2_text())

    def test_first_entry_broken_after_template_section(self):
        r = self._run(f"### 知見001：題\n\n{_meta()}\n\n本文\n",
                      prefix="# 知見ログ\n\n## タグ一覧\n\n| タグ | 説明 |\n|---|---|\n\n## 知見詳細\n\n")
        self.assertEqual(r["unparsed"], [{"id": "知見001：題", "reason": "heading"}])
        self.assertEqual(r["dropped"], [])

    # --- 窓の境界 ---

    def test_window_fixture_order(self):
        r = self._run(_entry("LL-001"), prefix="# 知見ログ\n\n## タグ一覧\n\n---\n\n## 知見詳細\n\n")
        self.assertEqual(r["unparsed"], [])
        self.assertEqual(r["dropped"], [])
        self.assertEqual(r["count"], 1)

    def test_trailing_subheading_stays_in_previous_entry(self):
        body = (f"### LL-001：題\n\n{_meta()}\n\n本文\n\n#### 補足\n\n補足本文\n"
                + f"### LL-002：題\n\n{_meta()}\n\n本文2\n")
        r = self._run(body)
        self.assertEqual(r["count"], 2)
        self.assertEqual(r["unparsed"], [])
        text = self._out_text()
        self.assertLess(text.index("補足本文"), text.index("### LL-002"))

    def test_meta_inside_fence_after_heading_not_entry(self):
        body = (_entry("LL-001", body="本文")
                + f"## 例\n```\n{_meta()}\n```\n")
        r = self._run(body)
        self.assertEqual(r["unparsed"], [])
        self.assertEqual(r["dropped"], [{"id": "例", "reason": "cut"}])

    # --- メタ行を2つ以上持つエントリ ---

    def test_headless_entry_mixed_makes_multi_meta(self):
        body = (f"### LL-001：題\n\n{_meta()}\n\n本文\n\n詳細1\n\n詳細2\n\n"
                + f"**LL-005：見出しなし**\n\n{_meta(OLD)}\n\n本文5\n")
        r = self._run(body)
        self.assertEqual(r["unparsed"], [{"id": "LL-001", "reason": "multi-meta"}])
        self.assertEqual(r["count"], 0)
        self.assertEqual(self._layer2_ids(), set())

    def test_multi_meta_within_first_five_lines(self):
        body = f"### LL-001：題\n{_meta()}\n**LL-005：見出しなし**\n{_meta(OLD)}\n"
        r = self._run(body)
        self.assertEqual(r["unparsed"], [{"id": "LL-001", "reason": "multi-meta"}])

    def test_meta_inside_fence_is_not_multi_meta(self):
        body = f"### LL-001：題\n\n{_meta()}\n\n```\n{_meta(OLD)}\n```\n"
        r = self._run(body)
        self.assertEqual(r["unparsed"], [])
        self.assertEqual(r["count"], 1)

    # --- 落とした塊 ---

    def test_unfenced_comment_cuts_current_entry(self):
        body = (f"### LL-001：題\n\n{_meta()}\n\n本文\n\n# 閾値は >= で比べる\n後ろの本文\n\n"
                + _entry("LL-002", cr=OLD, body="旧本文") + "# 旧コメント\n旧後ろ\n")
        r = self._run(body)
        self.assertEqual(r["dropped"], [{"id": "閾値は >= で比べる", "reason": "cut"}])
        self.assertNotIn("後ろの本文", self._out_text())
        self.assertIn("本文", self._out_text())

    def test_cr_meta_chunk_after_old_entry(self):
        late_meta = f"### 知見005：題\n\n一\n\n二\n\n三\n{_meta()}\n\n本文\n"
        r = self._run(_entry("LL-001", cr=OLD) + late_meta)
        self.assertEqual(r["dropped"], [{"id": "知見005：題", "reason": "cr-meta"}])

    def test_cr_meta_chunk_after_current_entry(self):
        late_meta = f"### 知見005：題\n\n一\n\n二\n\n三\n{_meta()}\n\n本文\n"
        r = self._run(_entry("LL-001") + late_meta)
        self.assertEqual(r["dropped"], [{"id": "知見005：題", "reason": "cr-meta"}])

    def test_old_meta_chunk_after_old_entry_not_dropped(self):
        late_meta = f"### 知見005：題\n\n一\n\n二\n\n三\n{_meta(OLD)}\n\n本文\n"
        r = self._run(_entry("LL-001", cr=OLD) + late_meta)
        self.assertEqual(r["dropped"], [])

    def test_hash_rules_do_not_cut(self):
        body = f"### LL-001：題\n\n{_meta()}\n\n本文\n#####\n#--------\n後ろの本文\n"
        r = self._run(body)
        self.assertEqual(r["dropped"], [])
        self.assertIn("後ろの本文", self._out_text())

    # --- 区切りを変えない場合 ---

    def test_fenced_hash_lines_do_not_cut(self):
        for fence in ("```", "~~~"):
            with self.subTest(fence=fence):
                body = (f"### LL-001：題\n\n{_meta()}\n\n{fence}python\n# コメント\n# ❌ 悪い例\n"
                        f"## 二つ\n# LL-099 例\n{fence}\n\n後ろの本文\n\n#### 小見出し\n\n小見出し本文\n")
                r = self._run(body)
                self.assertEqual((r["unparsed"], r["dropped"], r["count"]), ([], [], 1))
                self.assertIn("後ろの本文", self._out_text())
                self.assertIn("小見出し本文", self._out_text())

    def test_unclosed_fence(self):
        body = (f"### LL-001：題\n\n{_meta()}\n\n```\n# 閉じない\n"
                + _entry("LL-002", body="本文2")
                + f"### LL-003: 半角\n\n{_meta()}\n\n本文3\n")
        r = self._run(body)
        self.assertEqual(r["count"], 2)
        self.assertEqual(self._out_ids(), {"LL-001", "LL-002"})
        self.assertEqual(r["unparsed"], [{"id": "LL-003: 半角", "reason": "heading"}])


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
