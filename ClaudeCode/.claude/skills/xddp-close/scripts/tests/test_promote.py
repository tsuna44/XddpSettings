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
        self.assertIn({"path": str(self.docs / "repo-a" / "specs" / "old-mod"), "kind": "ディレクトリ"},
                      deletion_candidates)

    def test_step11_deleted_files_become_candidates(self):
        _mk(self.xddp_dir / "latest-specs" / "repo-a" / "mod1" / "spec.md", "spec")
        _mk(self.docs / "repo-a" / "specs" / "mod1" / "spec.md", "old")
        _mk(self.docs / "repo-a" / "specs" / "mod1" / "sequences" / "old-seq.md", "old")
        _mk(self.docs / "repo-a" / "specs" / "overview" / "sequences" / "gone-seq.md", "old")
        _mk(self.xddp_dir / "latest-specs" / "repo-a" / "overview" / "architecture.md", "a")
        _mk(self.docs / "cross" / "specs" / "interfaces" / "if-old" / "spec.md", "old")
        _mk(self.docs / "cross" / "specs" / "interfaces" / "if-old" / "schema.md", "old")
        _mk(self.xddp_dir / "latest-specs" / "cross" / "interfaces" / "if1" / "spec.md", "x")
        deleted = ["latest-specs/repo-a/mod1/sequences/old-seq.md",
                   "latest-specs/repo-a/overview/sequences/gone-seq.md",
                   "latest-specs/cross/interfaces/if-old/spec.md", "latest-specs/cross/interfaces/if-old/schema.md",
                   "latest-specs/repo-a/not-in-docs.md", "latest-specs/repo-b/x/spec.md"]
        repo_results = mod._init_repo_results(["repo-a"])
        cands = mod.promote_specs(self.xddp_dir, self.docs, ["repo-a"], True, repo_results, deleted)
        self.assertEqual(cands, [
            {"path": str(self.docs / "repo-a" / "specs" / "mod1" / "sequences"), "kind": "ディレクトリ"},
            {"path": str(self.docs / "repo-a" / "specs" / "overview" / "sequences"), "kind": "ディレクトリ"},
            {"path": str(self.docs / "cross" / "specs" / "interfaces" / "if-old"), "kind": "ディレクトリ"},
        ])
        _mk(self.xddp_dir / "latest-specs" / "repo-a" / "mod1" / "sequences" / "keep-seq.md", "k")
        cands = mod.promote_specs(self.xddp_dir, self.docs, ["repo-a"], False, repo_results, deleted[:1])
        self.assertEqual(cands, [{"path": str(self.docs / "repo-a" / "specs" / "mod1" / "sequences" / "old-seq.md"),
                                  "kind": "ファイル"}])


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


PROGRESS_11 = """# 進捗管理 — CR-1

## 工程11 更新仕様書ファイル一覧

---

## 次に実行すべきコマンド

x
"""


class TestSyncBaseline(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.xddp = self.tmp / "xddp"
        self.docs = self.tmp / "docs"
        self.latest = self.xddp / "latest-specs"
        _mk(self.xddp / "CR-1" / "progress.md", PROGRESS_11)

    def test_does_not_write_back_updated_or_deleted_files(self):
        for name in ("mine", "gone", "stale"):
            _mk(self.latest / "svc" / name / "spec.md", "v1")
            _mk(self.docs / "svc" / "specs" / name / "spec.md", "v1")
        mod.spec_changes.snapshot(self.xddp, "CR-1")
        _mk(self.latest / "svc" / "mine" / "spec.md", "mine-v2")              # 今の CR の更新
        (self.latest / "svc" / "gone" / "spec.md").unlink()                    # 今の CR の削除（GATE）
        _mk(self.docs / "svc" / "specs" / "stale" / "spec.md", "other-cr-v2")   # 他の CR が昇格
        _mk(self.docs / "svc" / "specs" / "new" / "spec.md", "other-cr-new")
        _mk(self.docs / "system" / "specs" / "use-cases" / "u" / "description.md", "d")
        r = mod.sync_baseline(self.xddp, self.docs, "CR-1", ["svc"], False)
        self.assertEqual(r["protected_files"], ["latest-specs/svc/mine/spec.md"])
        self.assertEqual(r["deleted_files"], ["latest-specs/svc/gone/spec.md"])
        self.assertEqual(r["copied_files"], ["latest-specs/svc/new/spec.md", "latest-specs/svc/stale/spec.md",
                                             "latest-specs/system/use-cases/u/description.md"])
        self.assertEqual((self.latest / "svc" / "mine" / "spec.md").read_text(encoding="utf-8"), "mine-v2")
        self.assertFalse((self.latest / "svc" / "gone" / "spec.md").exists())
        self.assertEqual((self.latest / "svc" / "stale" / "spec.md").read_text(encoding="utf-8"), "other-cr-v2")
        # 取り込んだものは次の record で今の CR の変更と数えない
        rec = mod.spec_changes.record(self.xddp, "CR-1")
        self.assertEqual((rec["updated"], rec["deleted"]), (["latest-specs/svc/mine/spec.md"],
                                                            ["latest-specs/svc/gone/spec.md"]))
        progress = (self.xddp / "CR-1" / "progress.md").read_text(encoding="utf-8")
        self.assertEqual(mod.layout.read_step11_list(progress, mod.layout.STEP11_DELETED_HEADING),
                         ["latest-specs/svc/gone/spec.md"])

    def test_cross_only_with_has_cross(self):
        mod.spec_changes.snapshot(self.xddp, "CR-1")
        _mk(self.docs / "cross" / "specs" / "interfaces" / "i" / "spec.md", "c")
        self.assertEqual(mod.sync_baseline(self.xddp, self.docs, "CR-1", ["svc"], False)["copied_files"], [])
        self.assertEqual(mod.sync_baseline(self.xddp, self.docs, "CR-1", ["svc"], True)["copied_files"],
                         ["latest-specs/cross/interfaces/i/spec.md"])

    def test_without_baseline_exits_nonzero(self):
        import io
        from contextlib import redirect_stderr
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            mod.sync_baseline(self.xddp, self.docs, "CR-1", ["svc"], False)
        self.assertEqual(cm.exception.code, 1)


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
        r = mod.promote_lessons_learned(src, self.docs, "CR-2026-001", ["repo-a"], True, {})
        self.assertEqual(r["unresolved"], [])
        self.assertIn("LL-001", (self.docs / "repo-a" / "knowledge" / "lessons-learned.md").read_text(encoding="utf-8"))
        self.assertIn("LL-002", (self.docs / "cross" / "knowledge" / "lessons-learned.md").read_text(encoding="utf-8"))

    def test_unknown_repo_not_promoted(self):
        entries = (
            "### LL-003：タイトルC\n\n"
            "**CR：** CR-2026-001 ／ **工程：** プロセス ／ **repo：** unknown ／ **タグ：** #プロセス\n\n"
            "本文\n\n---\n\n"
        )
        src = self._ll_source(entries)
        r = mod.promote_lessons_learned(src, self.docs, "CR-2026-001", ["repo-a"], False, {})
        self.assertEqual([(u["id"], u["reason"]) for u in r["unresolved"]], [("LL-003", "unknown")])
        self.assertFalse((self.docs / "unknown").exists())

    def test_other_cr_entries_not_promoted(self):
        entries = (
            "### LL-004：他CRのエントリ\n\n"
            "**CR：** CR-2026-999 ／ **工程：** テスト ／ **repo：** repo-a ／ **タグ：** #テスト\n\n"
            "本文\n\n---\n\n"
        )
        src = self._ll_source(entries)
        r = mod.promote_lessons_learned(src, self.docs, "CR-2026-001", ["repo-a"], False, {})
        self.assertEqual(r["unresolved"], [])
        self.assertFalse((self.docs / "repo-a" / "knowledge" / "lessons-learned.md").exists())

    def test_rerun_does_not_duplicate(self):
        entries = (
            "### LL-005：再実行テスト\n\n"
            "**CR：** CR-2026-001 ／ **工程：** テスト ／ **repo：** repo-a ／ **タグ：** #テスト\n\n"
            "本文\n\n---\n\n"
        )
        src = self._ll_source(entries)
        mod.promote_lessons_learned(src, self.docs, "CR-2026-001", ["repo-a"], False, {})
        r = mod.promote_lessons_learned(src, self.docs, "CR-2026-001", ["repo-a"], False, {})
        text = (self.docs / "repo-a" / "knowledge" / "lessons-learned.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("### LL-005："), 1)
        self.assertEqual(r["conflicts"], [])


CR = "CR-2026-001"
OLD = "CR-2026-900"
REPOS = ["repo-a"]


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
        return mod.extract_ll(self.src, CR, self.out, REPOS, True)

    def _out_text(self):
        return self.out.read_text(encoding="utf-8") if self.out.exists() else ""

    def _layer2_ids(self):
        """IS_MULTI・空の DOCS で振り分け、Layer 2 に書いた ID の集合と unresolved の ID の集合。"""
        r = mod.promote_lessons_learned(self.src, self.docs, CR, REPOS, True, {})
        ids = set()
        for p in self.docs.rglob("lessons-learned.md"):
            for line in p.read_text(encoding="utf-8").split("\n"):
                m = mod.LL_ENTRY_RE.match(line)
                if m:
                    ids.add(m.group(1))
        return ids, {u["id"] for u in r["unresolved"]}

    def _layer2_text(self):
        return "\n".join(p.read_text(encoding="utf-8") for p in self.docs.rglob("lessons-learned.md"))

    def _out_ids(self):
        entries, _ = mod._split_ll_blocks(self._out_text().split("\n"))
        return {m.group(1) for m in (mod.LL_ENTRY_RE.match(e[0]) for e in entries) if m}

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
        r = mod.extract_ll(self.tmp / "nothing.md", CR, self.out, REPOS, True)
        self.assertEqual(r, {"count": 0, "unparsed": [], "dropped": [], "unrouted": [], "out": None,
                             "removed": False})

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
                    "--out", str(self.out), "--repos-keys", "repo-a"]
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
        mod.promote_lessons_learned(self.src, self.docs, CR, REPOS, False, {})
        mod.promote_lessons_learned(self.src, self.docs, CR, REPOS, False, {})
        text = (self.docs / "repo-a" / "knowledge" / "lessons-learned.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("### LL-005："), 1)

    def test_promote_skips_no_meta_entry(self):
        _mk(self.src, "### LL-001：メタ行なし\n\n**CR：** 欄なし\n\n---\n\n")
        r = mod.promote_lessons_learned(self.src, self.docs, CR, REPOS, True, {})
        self.assertEqual(r["unresolved"], [])
        self.assertEqual(list(self.docs.rglob("lessons-learned.md")), [])

    def test_extract_and_layer2_agree(self):
        body = (_entry("LL-001") + _entry("LL-002", cr=OLD) + _entry("LL-003", repo="unknown")
                + _entry("LL-004", repo="cross") + "### LL-005: 崩れ\n\n" + _meta() + "\n\n---\n\n"
                + "### LL-006：メタなし\n\n本文\n")
        r = self._run(body)
        self.assertEqual(self._out_ids(), {"LL-001", "LL-004"})
        self.assertEqual(r["unrouted"], [{"id": "LL-003", "repo": "unknown", "reason": "unknown"}])
        written, unresolved = self._layer2_ids()
        self.assertEqual(written, self._out_ids())
        self.assertEqual(unresolved, {u["id"] for u in r["unrouted"]})

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
        self.assertEqual(self._layer2_ids(), (set(), set()))

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
        self.assertEqual(r["count"], 1)
        self.assertEqual(self._out_ids(), {"LL-002"})
        self.assertEqual(r["unparsed"], [{"id": "LL-001", "reason": "unclosed-fence"},
                                         {"id": "LL-003: 半角", "reason": "heading"}])

    # --- R2・R3: フェンスの中の見出し・短いフェンス ---

    def test_ll_heading_inside_fence_does_not_cut(self):
        body = (f"### LL-001：題\n\n{_meta()}\n\n```markdown\n### LL-099：例の見出し\n"
                f"{_meta(OLD)}\n```\n\n後ろの本文\n\n---\n\n" + _entry("LL-002"))
        r = self._run(body)
        self.assertEqual((r["unparsed"], r["dropped"], r["count"]), ([], [], 2))
        self.assertEqual(self._out_ids(), {"LL-001", "LL-002"})
        self.assertIn("後ろの本文", self._out_text())

    def test_short_fence_does_not_close_long_fence(self):
        body = (f"### LL-001：題\n\n{_meta()}\n\n````\n```\n### LL-099：例\n```\n````\n\n後ろの本文\n\n"
                + _entry("LL-002"))
        r = self._run(body)
        self.assertEqual((r["unparsed"], r["count"]), ([], 2))
        self.assertIn("後ろの本文", self._out_text())


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

    def test_rulebooks_copied_per_repo_and_cross(self):
        _mk(self.xddp_dir / "project-rulebook.md", "common")
        _mk(self.xddp_dir / "project-rulebook-repo-a.md", "repo-a specific")
        _mk(self.xddp_dir / "project-rulebook-cross.md", "cross specific")
        repo_results = mod._init_repo_results(["repo-a"])
        mod.promote_rulebooks(self.xddp_dir, self.docs, ["repo-a"], True, repo_results)
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
            self.xddp_dir / "lessons-learned.md", self.docs, "CR-2026-900", ["device-svc", "notify-svc"],
            False, repo_results)
        mod.promote_crs(self.cr_path, self.docs, "CR-2026-900", ["device-svc", "notify-svc"], False,
                         repo_results)

        self.assertTrue(repo_results["device-svc"]["ok"])
        self.assertFalse(repo_results["notify-svc"]["ok"])
        self.assertTrue(any("C3" in e for e in repo_results["notify-svc"]["errors"]))
        self.assertTrue(any("C4" in e for e in repo_results["notify-svc"]["errors"]))
        self.assertIn(
            "LL-001", (self.docs / "device-svc" / "knowledge" / "lessons-learned.md").read_text(encoding="utf-8"))
        self.assertTrue((self.docs / "device-svc" / "crs" / "CRS-CR-2026-900.md").exists())


# ---------------------------------------------------------------------------
# ID・index・振り分け・出力ファイル・backlog の足し込み
# ---------------------------------------------------------------------------

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
LL_TEMPLATE = TEMPLATES / "lessons-learned-template.md"
BACKLOG_TEMPLATE = TEMPLATES / "10_improvement-backlog-template.md"
TODAY = "2026-11-08"


def _ll(ll_id, cr=CR, repo="repo-a", tags="#テスト, #リスク", body="本文", title="題"):
    """close Step C の Entry Format のエントリ。"""
    return (f"### {ll_id}：{title}\n\n"
            f"**CR：** {cr} ／ **工程：** テスト ／ **repo：** {repo} ／ **タグ：** {tags}\n\n"
            f"**発生状況：**  \n{body}\n\n**学んだこと：**  \n学び\n\n**次回への適用：**  \n- 確認\n\n---\n\n")


def _idea(idea_id, title="題", repo="repo-a", status="🆕 新規", content="内容本文", priority="中",
          memo="判断メモ", cr=CR):
    """close Step B の書式の IDEA のエントリ。"""
    return (f"### {idea_id}：{title}\n\n"
            "| 項目 | 内容 |\n|------|------|\n"
            f"| カテゴリ | 機能改善 |\n| 優先度 | {priority} |\n| repo | {repo}（根拠） |\n"
            f"| 発生源 | {cr}のANA「気づき・提案メモ」 |\n| ステータス | {status} |\n| 対応CR | — |\n\n"
            f"**内容：**  \n{content}\n\n**発生経緯：**  \n経緯\n\n**期待効果：**  \n- 効果\n\n"
            f"**推定影響範囲：**  \n範囲\n\n**CR化の判断メモ：**  \n{memo}\n\n---\n\n")


def _layer1_lessons(path: Path, entries: str) -> Path:
    _mk(path, LL_TEMPLATE.read_text(encoding="utf-8").replace("{YYYY-MM-DD}", TODAY) + "\n" + entries)
    return path


def _backlog(path: Path, ideas: str) -> Path:
    """テンプレートから作り、IDEA を §3 の末尾（`## 4.` の前）に足す。"""
    text = BACKLOG_TEMPLATE.read_text(encoding="utf-8")
    i = text.index("## 4. CR化判断基準")
    _mk(path, text[:i] + ideas + text[i:])
    return path


def _cli(argv: list) -> dict:
    import io
    from contextlib import redirect_stdout
    old = sys.argv
    sys.argv = ["promote.py"] + argv
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            mod.main()
    finally:
        sys.argv = old
    return json.loads(buf.getvalue().strip().split("\n")[-1])


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.xddp = self.tmp / "xddp"
        self.docs = self.tmp / "baseline_docs"
        self.cr_path = self.xddp / CR
        self.lessons = self.xddp / "lessons-learned.md"
        self.backlog = self.xddp / "improvement-backlog.md"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_promote(self, repos="repo-a", affected="repo-a", multi=False, has_cross=False):
        argv = ["run", "--cr", CR, "--cr-path", str(self.cr_path), "--xddp-dir", str(self.xddp),
                "--docs", str(self.docs), "--repos-keys", repos, "--affected-repos", affected,
                "--today", TODAY, "--lessons-file", str(self.lessons),
                "--output-file", str(self.cr_path / "pending-items" / f"PENDING-PROMOTE-{CR}.md")]
        if multi:
            argv.append("--is-multi")
        if has_cross:
            argv.append("--has-cross")
        return _cli(argv)

    def _output(self):
        return (self.cr_path / "pending-items" / f"PENDING-PROMOTE-{CR}.md").read_text(encoding="utf-8")


class TestIndexLayer1(_Tmp):
    def test_tables_and_tags(self):
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01", tags="#テスト、#見落とし #独自")
                        + _ll(f"LL-{OLD}-01", cr=OLD, tags="#テスト,#リスク", title="旧"))
        r = mod.run_index(cr=CR, lessons_file=self.lessons)
        text = self.lessons.read_text(encoding="utf-8")
        self.assertIn(f"| LL-{CR}-01 | 題 | {CR} | テスト | #テスト, #見落とし, #独自 |", text)
        self.assertIn(f"| #テスト | LL-{CR}-01, LL-{OLD}-01 |", text)
        self.assertIn(f"| #見落とし | LL-{CR}-01 |", text)
        self.assertIn("| #設計 | — |", text)
        self.assertEqual(r["unknown_tags"], [{"id": f"LL-{CR}-01", "tag": "#独自"}])
        self.assertIn(f"**最終更新CR：** {CR}", text)
        self.assertEqual((r["cr_ll_count"], r["ll_count"]), (1, 2))

    def test_last_cr_unchanged_without_current_entries(self):
        _layer1_lessons(self.lessons, _ll(f"LL-{OLD}-01", cr=OLD))
        mod.run_index(cr=CR, lessons_file=self.lessons)
        self.assertIn("**最終更新CR：** —", self.lessons.read_text(encoding="utf-8"))

    def test_idempotent_and_check(self):
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01"))
        before = self.lessons.read_text(encoding="utf-8")
        r = mod.run_index(cr=CR, check=True, lessons_file=self.lessons)
        self.assertEqual(r["written"], [])
        self.assertEqual(self.lessons.read_text(encoding="utf-8"), before)
        self.assertEqual(mod.run_index(cr=CR, lessons_file=self.lessons)["written"], [str(self.lessons)])
        self.assertEqual(mod.run_index(cr=CR, lessons_file=self.lessons)["written"], [])

    def test_missing_files_count_zero(self):
        r = mod.run_index(cr=CR, lessons_file=self.lessons, backlog_file=self.backlog)
        self.assertEqual((r["cr_ll_count"], r["cr_idea_count"], r["written"]), (0, 0, []))
        self.assertFalse(self.lessons.exists())

    def test_missing_sections_exit_1(self):
        import io
        from contextlib import redirect_stderr
        _mk(self.lessons, "# 知見ログ\n\n## 知見詳細\n")
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
            _cli(["index", "--lessons-file", str(self.lessons)])
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("必要な節がありません: ## エントリ一覧, ## タグ別インデックス", err.getvalue())
        _mk(self.backlog, "# 改善バックログ\n\n## 3. アイデア詳細\n")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            _cli(["index", "--backlog-file", str(self.backlog)])

    def test_cr_counts_full_match(self):
        body = (_ll(f"LL-{CR}-01") + f"## LL-{CR}-02: 崩れ\n\n本文\n\n"
                + f"```\n### LL-{CR}-03：フェンスの中\n```\n\n" + _ll(f"LL-{CR}-2-01", cr=f"{CR}-2"))
        _layer1_lessons(self.lessons, body)
        r = mod.run_index(cr=CR, check=True, lessons_file=self.lessons)
        self.assertEqual(r["cr_ll_ids"], [f"LL-{CR}-01", f"LL-{CR}-02"])
        r2 = mod.run_index(cr=f"{CR}-2", check=True, lessons_file=self.lessons)
        self.assertEqual(r2["cr_ll_ids"], [f"LL-{CR}-2-01"])

    def test_duplicate_ids(self):
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01") + _ll(f"LL-{CR}-01", title="二つ目"))
        r = mod.run_index(cr=CR, check=True, lessons_file=self.lessons)
        self.assertEqual(r["duplicate_ids"], [{"id": f"LL-{CR}-01", "file": str(self.lessons)}])

    def test_unparsed_not_in_table(self):
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01") + f"### LL-{CR}-02：メタなし\n\n本文\n")
        r = mod.run_index(cr=CR, lessons_file=self.lessons)
        self.assertEqual(r["unparsed_ll"], [{"id": f"LL-{CR}-02", "reason": "no-meta"}])
        self.assertNotIn(f"| LL-{CR}-02 |", self.lessons.read_text(encoding="utf-8"))


class TestIndexBacklog(_Tmp):
    def test_summary_and_list(self):
        _backlog(self.backlog, _idea(f"IDEA-{CR}-01") + _idea(f"IDEA-{CR}-02", repo="unknown", status="❌ 却下")
                 + _idea(f"IDEA-{OLD}-01", status="未定", cr=OLD))
        r = mod.run_index(cr=CR, today=TODAY, backlog_file=self.backlog)
        text = self.backlog.read_text(encoding="utf-8")
        self.assertIn("| 🆕 新規 | 1 |", text)
        self.assertIn("| ❌ 却下 | 1 |", text)
        self.assertIn("| **合計** | 3 |", text)
        self.assertIn(f"| IDEA-{CR}-01 | 題 | 機能改善 | 中 | {CR}のANA「気づき・提案メモ」 | 🆕 新規 |", text)
        self.assertEqual(r["bad_ideas"], [{"id": f"IDEA-{OLD}-01", "reason": "status"}])
        self.assertEqual(r["cr_unknown_repo_ideas"], [f"IDEA-{CR}-02"])
        self.assertEqual((r["cr_idea_count"], r["idea_count"]), (2, 3))
        self.assertIn(f"**最終更新：** {TODAY}", text)

    def test_outside_section(self):
        _backlog(self.backlog, _idea(f"IDEA-{CR}-01"))
        with open(self.backlog, "a", encoding="utf-8") as f:
            f.write("\n" + _idea(f"IDEA-{CR}-02"))
        r = mod.run_index(cr=CR, backlog_file=self.backlog)
        self.assertEqual(r["bad_ideas"], [{"id": f"IDEA-{CR}-02", "reason": "outside-section"}])
        self.assertNotIn(f"| IDEA-{CR}-02 |", self.backlog.read_text(encoding="utf-8"))

    def test_last_updated_only_when_changed(self):
        _backlog(self.backlog, _idea(f"IDEA-{CR}-01"))
        mod.run_index(cr=CR, today=TODAY, backlog_file=self.backlog)
        r = mod.run_index(cr=CR, today="2026-12-31", backlog_file=self.backlog)
        self.assertEqual(r["written"], [])
        self.assertIn(f"**最終更新：** {TODAY}", self.backlog.read_text(encoding="utf-8"))


class TestIndexLayer2(_Tmp):
    def setUp(self):
        super().setUp()
        self.l2 = mod.layer2_path(self.docs, "repo-a")

    def test_creates_header(self):
        r = mod.run_index(today=TODAY, layer2_file=self.l2, area="repo-a")
        text = self.l2.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# 知見ログ: repo-a\n"))
        self.assertIn("## エントリ一覧", text)
        self.assertEqual(r["next_manual_id"], "LL-M20261108-01")

    def test_check_does_not_create(self):
        mod.run_index(today=TODAY, check=True, layer2_file=self.l2, area="repo-a")
        self.assertFalse(self.l2.exists())

    def test_adds_section_to_existing_files(self):
        cases = {
            "header-only": "# 知見ログ: repo-a\n> xddp-close が CR クローズ時に自動追記します。\n\n" + _ll("LL-001"),
            "breaking-only": "### 破壊的変更警告（CR-X）\n\n⚠️ 警告\n\n---\n",
            "detail-section": "# repo-a 知見ログ\n\n## 知見詳細\n\n" + _ll("LL-001"),
            "old-init": ("# 知見ログ: repo-a\n> xddp-close が CR クローズ時に自動追記します。\n\n## エントリ一覧\n"
                         "| ID | タイトル | タグ | CR | 日付 |\n|---|---|---|---|---|\n"
                         "| （xddp-close 実行後に追記） | — | — | — | — |\n\n" + _ll("LL-001")),
        }
        for name, content in cases.items():
            with self.subTest(name):
                _mk(self.l2, content)
                mod.run_index(layer2_file=self.l2, area="repo-a")
                lines = self.l2.read_text(encoding="utf-8").split("\n")
                if name != "detail-section":
                    self.assertEqual(lines[0], "# 知見ログ: repo-a")
                h = lines.index("## エントリ一覧")
                self.assertEqual(lines[h + 2], mod.LL_TABLE_HEADER[0])
                first_h3 = next(i for i, l in enumerate(lines) if l.startswith("### "))
                self.assertLess(h, first_h3)
                self.assertNotIn("（xddp-close 実行後に追記）", "\n".join(lines))
                if name != "breaking-only":
                    self.assertIn("| LL-001 | 題 |", "\n".join(lines))
                if name == "detail-section":
                    self.assertEqual(lines[0], "# repo-a 知見ログ")
                    self.assertLess(h, lines.index("## 知見詳細"))
                before = self.l2.read_text(encoding="utf-8")
                self.assertEqual(mod.run_index(layer2_file=self.l2, area="repo-a")["written"], [])
                self.assertEqual(self.l2.read_text(encoding="utf-8"), before)

    def test_next_manual_id_is_max_plus_one(self):
        _mk(self.l2, _ll("LL-M20261108-01", cr="—") + _ll("LL-M20261108-03", cr="—") + _ll("LL-M20261107-09", cr="—"))
        r = mod.run_index(today=TODAY, layer2_file=self.l2, area="repo-a")
        self.assertEqual(r["next_manual_id"], "LL-M20261108-04")
        self.assertEqual(r["unknown_tags"], [])

    def test_duplicate_ids(self):
        _mk(self.l2, _ll("LL-M20261108-01", cr="—") + _ll("LL-M20261108-01", cr="—", title="別"))
        r = mod.run_index(today=TODAY, layer2_file=self.l2, area="repo-a")
        self.assertEqual(r["duplicate_ids"], [{"id": "LL-M20261108-01", "file": str(self.l2)}])
        self.assertEqual(r["next_manual_id"], "LL-M20261108-02")

    def test_append_breaking_warning_writes_header(self):
        mod.append_breaking_warning(self.l2, CR, ["if.x"], "repo-a")
        text = self.l2.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# 知見ログ: repo-a\n"))
        self.assertIn(f"### 破壊的変更警告（{CR}）", text)
        self.assertIn("## エントリ一覧", text)


class TestLayer2Promotion(_Tmp):
    def test_cr_and_manual_ids_both_kept(self):
        l2 = mod.layer2_path(self.docs, "repo-a")
        _mk(l2, _ll("LL-M20261108-01", cr="—"))
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01"))
        out = self._run_promote()
        text = l2.read_text(encoding="utf-8")
        self.assertIn("### LL-M20261108-01：", text)
        self.assertIn(f"### LL-{CR}-01：", text)
        self.assertIn(f"| LL-{CR}-01 | 題 |", text)
        self.assertEqual(out["ll_conflicts"], [])

    def test_conflict_not_overwritten_and_rerun_clean(self):
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01"))
        self.assertEqual(self._run_promote()["ll_conflicts"], [])
        self.assertEqual(self._run_promote()["ll_conflicts"], [])
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01", body="作り直した本文"))
        out = self._run_promote()
        self.assertEqual(out["ll_conflicts"], [{"id": f"LL-{CR}-01", "area": "repo-a"}])
        text = mod.layer2_path(self.docs, "repo-a").read_text(encoding="utf-8")
        self.assertNotIn("作り直した本文", text)
        self.assertIn("## Layer 2 と内容が違う LL（上書きしていない）\n- " + f"LL-{CR}-01（repo-a）", self._output())

    def test_duplicate_in_layer2_not_compared(self):
        l2 = mod.layer2_path(self.docs, "repo-a")
        _mk(l2, _ll(f"LL-{CR}-01", body="A") + _ll(f"LL-{CR}-01", body="B"))
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01", body="C"))
        out = self._run_promote()
        self.assertEqual(out["ll_conflicts"], [])
        self.assertEqual(out["duplicate_ids"], [{"id": f"LL-{CR}-01", "file": str(l2)}])
        self.assertNotIn("\nC\n", l2.read_text(encoding="utf-8"))

    def test_heading_text_inside_fence_is_not_existing(self):
        l2 = mod.layer2_path(self.docs, "repo-a")
        _mk(l2, _ll("LL-M20261108-01", cr="—", body=f"```\n### LL-{CR}-01：例\n```"))
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01"))
        self._run_promote()
        entries, _ = mod._split_ll_blocks(l2.read_text(encoding="utf-8").split("\n"))
        self.assertIn(f"### LL-{CR}-01：題", [e[0] for e in entries])


class TestRouting(_Tmp):
    def test_unrouted_reasons(self):
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01", repo="全リポジトリ") + _ll(f"LL-{CR}-02", repo="cross")
                        + _ll(f"LL-{CR}-03", repo="unknown") + _ll(f"LL-{CR}-04", repo="repo-typo"))
        r = mod.extract_ll(self.lessons, CR, self.tmp / "LL.md", ["repo-a"], False)
        self.assertEqual([(u["id"], u["reason"]) for u in r["unrouted"]],
                         [(f"LL-{CR}-01", "invalid"), (f"LL-{CR}-02", "invalid"),
                          (f"LL-{CR}-03", "unknown"), (f"LL-{CR}-04", "invalid")])
        self.assertEqual(r["count"], 0)
        out = self._run_promote()
        self.assertEqual(len(out["unresolved_ll"]), 4)
        self.assertFalse((self.docs / "repo-typo").exists())
        self.assertFalse((self.docs / "cross").exists())
        self.assertIn("— repo: 全リポジトリ（REPOS に無い値）", self._output())
        self.assertIn("— repo: unknown（repo: unknown）", self._output())

    def test_cross_by_is_multi_without_cross_artifacts(self):
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01", repo="cross"))
        _mk(self.xddp / "project-rulebook-cross.md", "cross rules")
        out = self._run_promote(repos="repo-a,repo-b", affected="repo-a", multi=True)
        self.assertIn(f"### LL-{CR}-01：", mod.layer2_path(self.docs, "cross").read_text(encoding="utf-8"))
        self.assertEqual((self.docs / "cross" / "project-rulebook.md").read_text(encoding="utf-8"), "cross rules")
        self.assertTrue(out["repo_results"]["cross"]["done"])
        self.assertIn("- cross: 成功", self._output())


class TestOutputFile(_Tmp):
    def test_targets_and_failures(self):
        _mk(self.xddp / "latest-specs" / "system" / "use-cases" / "uc1" / "description.md", "d")
        _mk(self.docs / "system", "not a directory")
        _backlog(self.backlog, _idea(f"IDEA-{CR}-01"))
        _mk(self.docs / "improvement-backlog.md" / "x", "dir in the way")
        out = self._run_promote(repos="repo-a,repo-b", affected="repo-a", multi=True)
        self.assertEqual(out["failed"], ["system", mod.COMMON_TARGET])
        text = self._output()
        self.assertIn("## 処理結果一覧（repo・cross・system・共通ファイル）", text)
        self.assertIn("- repo-a: 対象外", text)
        self.assertIn("- cross: 対象外", text)
        self.assertIn("- system: 失敗（C2:", text)
        self.assertIn("- 共通ファイル（`{DOCS}` 直下）: 失敗（C7(improvement-backlog.md):", text)

    def test_cross_failure_reported(self):
        _mk(self.xddp / "project-rulebook-cross.md", "cross rules")
        _mk(self.docs / "cross", "not a directory")
        out = self._run_promote(repos="repo-a,repo-b", affected="repo-a", multi=True)
        self.assertIn("cross", out["failed"])
        self.assertIn("- cross: 失敗（C6:", self._output())


class TestBacklogMerge(_Tmp):
    def setUp(self):
        super().setUp()
        self.dst = self.docs / "improvement-backlog.md"

    def test_copy_when_docs_missing(self):
        _backlog(self.backlog, _idea(f"IDEA-{CR}-01"))
        out = self._run_promote()
        self.assertTrue(out["backlog_promoted"])
        self.assertEqual(self.dst.read_text(encoding="utf-8"), self.backlog.read_text(encoding="utf-8"))

    def test_adds_missing_ids_to_section_3(self):
        _backlog(self.dst, _idea(f"IDEA-{OLD}-01", status="📋 CR化済み", cr=OLD))
        _backlog(self.backlog, _idea(f"IDEA-{OLD}-01", cr=OLD) + _idea(f"IDEA-{CR}-01"))
        out = self._run_promote()
        self.assertEqual(out["backlog_added"], [f"IDEA-{CR}-01"])
        self.assertEqual(out["backlog_conflicts"], [])
        lines = self.dst.read_text(encoding="utf-8").split("\n")
        self.assertLess(lines.index(f"### IDEA-{CR}-01：題"), lines.index("## 4. CR化判断基準"))
        text = "\n".join(lines)
        self.assertIn("| 📋 CR化済み | 1 |", text)
        self.assertIn("| 🆕 新規 | 1 |", text)
        r = mod.run_index(backlog_file=self.dst, check=True)
        self.assertEqual(r["bad_ideas"], [])

    def test_current_cr_conflict_and_human_fields_ignored(self):
        _backlog(self.dst, _idea(f"IDEA-{CR}-01", status="❌ 却下", priority="高", memo="却下の理由"))
        _backlog(self.backlog, _idea(f"IDEA-{CR}-01"))
        self.assertEqual(self._run_promote()["backlog_conflicts"], [])
        self.assertEqual(self._run_promote()["backlog_conflicts"], [])
        _backlog(self.backlog, _idea(f"IDEA-{CR}-01", content="作り直した内容"))
        out = self._run_promote()
        self.assertEqual(out["backlog_conflicts"], [{"id": f"IDEA-{CR}-01"}])
        self.assertNotIn("作り直した内容", self.dst.read_text(encoding="utf-8"))
        self.assertIn(f"- IDEA-{CR}-01", self._output())

    def test_old_cr_differences_not_reported(self):
        _backlog(self.dst, _idea(f"IDEA-{OLD}-01", content="直した", cr=OLD))
        _backlog(self.backlog, _idea(f"IDEA-{OLD}-01", cr=OLD))
        self.assertEqual(self._run_promote()["backlog_conflicts"], [])

    def test_missing_sections_in_docs_is_common_failure(self):
        _mk(self.dst, "# 改善バックログ\n\n手で崩した\n")
        _backlog(self.backlog, _idea(f"IDEA-{CR}-01"))
        out = self._run_promote()
        self.assertIn(mod.COMMON_TARGET, out["failed"])
        self.assertEqual(self.dst.read_text(encoding="utf-8"), "# 改善バックログ\n\n手で崩した\n")
        self.assertIn("必要な節がありません: ## 1., ## 2., ## 3.", self._output())


class TestWriterReaderContract(_Tmp):
    """実物のテンプレートから作った Layer 1 に close Step B・C の書式のエントリを足し、
    index・extract-ll・run と読み手（load-lessons-context.md の読み方・domain_refs.py）に通す。"""

    def test_layer1_to_readers(self):
        _layer1_lessons(self.lessons, _ll(f"LL-{CR}-01", tags="#要求分析, #見落とし")
                        + _ll(f"LL-{CR}-02", tags="#テスト"))
        _backlog(self.backlog, _idea(f"IDEA-{CR}-01"))
        r = mod.run_index(cr=CR, today=TODAY, lessons_file=self.lessons, backlog_file=self.backlog)
        self.assertEqual((r["cr_ll_count"], r["cr_idea_count"], r["unparsed_ll"], r["bad_ideas"],
                          r["unknown_tags"]), (2, 1, [], [], []))

        # load-lessons-context.md: タグ別インデックスの行 → `### {id}：` のエントリ
        lines = self.lessons.read_text(encoding="utf-8").split("\n")
        h = lines.index("## タグ別インデックス")
        rows = {r[0]: r[1] for r in mod._section_table_rows(lines, h)}
        ids = [i.strip() for i in rows["#要求分析"].split(",")]
        self.assertEqual(ids, [f"LL-{CR}-01"])
        self.assertTrue(any(l.startswith(f"### {ids[0]}：") for l in lines))

        ex = mod.extract_ll(self.lessons, CR, self.cr_path / "pending-items" / f"LL-{CR}.md", ["repo-a"], False)
        self.assertEqual(ex["count"], 2)
        self._run_promote()

        # Layer 2 の読み手: domain_refs.py（工程2 の Step 0）
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "xddp-02-analysis" / "scripts"))
        import domain_refs  # noqa: E402
        res = domain_refs.resolve(self.tmp, "xddp", self.docs, ["repo-a"], False, [])
        self.assertIn(str(mod.layer2_path(self.docs, "repo-a")), json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
