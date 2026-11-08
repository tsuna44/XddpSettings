import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spec_version_delta as mod  # noqa: E402


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


SPO_TEMPLATE = """# SPO {module}

## 2. 現状仕様

{spec_body}

## 4. モジュール内ダイアグラム

### 4.3 データ構造

{structure_body}

### 4.1 状態遷移図

{state_body}

### 4.5 モジュール内シーケンス図

#### メイン処理

{main_seq_body}
"""


class PrecheckTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.existing_root = self.root / "latest-specs" / "repo-a"
        self.spo_dir = self.root / "specout" / "repo-a" / "modules"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_spo(self, module, spec_body="foo", structure_body="bar", state_body="baz", main_seq_body="qux",
                   seq_heading="メイン処理"):
        write(
            self.spo_dir / f"{module}-spo.md",
            SPO_TEMPLATE.format(
                module=module, spec_body=spec_body, structure_body=structure_body,
                state_body=state_body, main_seq_body=main_seq_body,
            ).replace("#### メイン処理", f"#### {seq_heading}"),
        )

    def _sources(self, *modules):
        return {"modules": [{"spec_dir": m, "source_files": [str(self.spo_dir / f"{m}-spo.md")]} for m in modules]}

    def test_no_spo_file_skips_module(self):
        write(self.existing_root / "auth" / "spec.md", "old content")
        result = mod.precheck(self.existing_root, self._sources("auth"), 20.0)
        self.assertEqual(result["diagnostics"]["auth"], {"skipped": "no_spo_file"})
        self.assertEqual(result["force_update_files"], [])

    def test_text_line_change_over_threshold_forces_update(self):
        write(self.existing_root / "auth" / "spec.md", "line1\nline2\n")
        self._write_spo("auth", spec_body="line1\nline2\nline3\nline4\nline5\n")
        result = mod.precheck(self.existing_root, self._sources("auth"), 20.0)
        self.assertIn("auth/spec.md", result["force_update_files"])

    def test_text_line_change_under_threshold_no_force(self):
        write(self.existing_root / "auth" / "spec.md", "\n".join(f"line{i}" for i in range(20)))
        self._write_spo("auth", spec_body="\n".join(f"line{i}" for i in range(21)))
        result = mod.precheck(self.existing_root, self._sources("auth"), 20.0)
        self.assertNotIn("auth/spec.md", result["force_update_files"])

    def test_only_spo_derived_sections_are_compared(self):
        # 文書概要・関連ドキュメント・気づき・変更履歴は比べない（A4-46）
        body = "\n".join(f"line{i}" for i in range(10))
        existing = ("---\nversion: \"1.0.0\"\n---\n\n## 1. 文書概要\n\n" + "\n".join(f"meta{i}" for i in range(30))
                    + f"\n\n## 2. 機能概要\n\n{body}\n\n## 8. 気づき・提案メモ\n\n" + "\n".join(f"note{i}" for i in range(30))
                    + "\n\n## 9. 変更履歴\n\n| a |\n")
        write(self.existing_root / "auth" / "spec.md", existing)
        self._write_spo("auth", spec_body=body)
        result = mod.precheck(self.existing_root, self._sources("auth"), 20.0)
        self.assertNotIn("auth/spec.md", result["force_update_files"])
        self.assertNotIn("existing_sections_not_found", result["diagnostics"]["auth/spec.md"])

    def test_structure_compares_data_type_relation_section(self):
        old = "## 1. 文書概要\n\nx\n\n## 2. データ型関連図\n\n```mermaid\ngraph TD\nA-->B\n```\n"
        new = "```mermaid\ngraph TD\nA-->B\nB-->C\n```\n"
        write(self.existing_root / "auth" / "structure.md", old)
        self._write_spo("auth", structure_body=new)
        self.spo_dir.joinpath("auth-spo.md").write_text(
            self.spo_dir.joinpath("auth-spo.md").read_text(encoding="utf-8").replace("### 4.3 データ構造", "### 4.2 データ型関連図"),
            encoding="utf-8")
        result = mod.precheck(self.existing_root, self._sources("auth"), 20.0)
        self.assertIn("auth/structure.md", result["force_update_files"])
        self.assertTrue(result["diagnostics"]["auth/structure.md"]["mermaid_changed"])

    def test_mermaid_edge_change_forces_update_regardless_of_pct(self):
        old = "```mermaid\ngraph TD\nA-->B\n```\n"
        new = "```mermaid\ngraph TD\nA-->B\nB-->C\n```\n"
        write(self.existing_root / "auth" / "structure.md", old)
        self._write_spo("auth", structure_body=new)
        result = mod.precheck(self.existing_root, self._sources("auth"), 20.0)
        self.assertIn("auth/structure.md", result["force_update_files"])
        self.assertTrue(result["diagnostics"]["auth/structure.md"]["mermaid_changed"])

    def test_no_matching_spo_section_is_skipped_safely(self):
        write(self.existing_root / "auth" / "state-machine.md", "some content")
        write(self.spo_dir / "auth-spo.md", "# SPO auth\n\n## 現状仕様\n\nno matching heading here\n")
        result = mod.precheck(self.existing_root, self._sources("auth"), 20.0)
        self.assertEqual(
            result["diagnostics"]["auth/state-machine.md"], {"skipped": "no_matching_spo_section"}
        )
        self.assertNotIn("auth/state-machine.md", result["force_update_files"])

    def test_sequence_file_matched_by_stem(self):
        write(self.existing_root / "auth" / "sequences" / "main-seq.md", "old seq body\n")
        self._write_spo("auth", main_seq_body="new seq body with much more content added here now\n" * 3)
        result = mod.precheck(self.existing_root, self._sources("auth"), 20.0)
        self.assertIn("auth/sequences/main-seq.md", result["force_update_files"])

    def test_japanese_sequence_heading_and_nfd_file_name(self):
        import unicodedata
        name = unicodedata.normalize("NFD", "ガード処理-seq.md")
        write(self.existing_root / "auth" / "sequences" / name, "old\n")
        self._write_spo("auth", seq_heading="ガード処理", main_seq_body="a\nb\nc\nd\n")
        self.spo_dir.joinpath("auth-spo.md").write_text(
            self.spo_dir.joinpath("auth-spo.md").read_text(encoding="utf-8").replace(
                "#### ガード処理", "#### ガード処理\n\nx\n\n#### 別の処理\n\ny\n\n#### ガード処理2").replace(
                "#### ガード処理\n\nx", "#### ガード処理\n\na\nb\nc\nd"), encoding="utf-8")
        result = mod.precheck(self.existing_root, self._sources("auth"), 20.0)
        key = f"auth/sequences/{name}"
        self.assertIn(key, result["diagnostics"])
        self.assertNotIn("skipped", result["diagnostics"][key])

    def test_modules_not_in_sources_are_not_compared(self):
        write(self.existing_root / "overview" / "architecture.md", "x")
        write(self.existing_root / "other" / "spec.md", "x")
        result = mod.precheck(self.existing_root, {"modules": []}, 20.0)
        self.assertEqual(result["diagnostics"], {})
        self.assertEqual(result["force_update_files"], [])


class MermaidMetricsTestCase(unittest.TestCase):
    def test_counts_nodes_and_edges(self):
        text = "```mermaid\ngraph TD\nA[Start]-->B[End]\n```\n"
        metrics = mod.mermaid_metrics(text)
        self.assertEqual(metrics["edge_count"], 1)
        self.assertEqual(metrics["node_count"], 2)

    def test_no_mermaid_block_returns_zero(self):
        metrics = mod.mermaid_metrics("plain text only")
        self.assertEqual(metrics, {"node_count": 0, "edge_count": 0, "block_count": 0})


def make_module_file(version="1.0.0", headings=("## 1. 文書概要", "## 2. 機能概要"), changelog_version="1.0.0"):
    body = "\n\n".join(f"{h}\n\nbody text for {h}" for h in headings)
    return (
        f'---\nversion: "{version}"\n---\n\n'
        f"{body}\n\n"
        "## 9. 変更履歴\n\n"
        "| バージョン | CR | 日付 | 変更内容 |\n"
        "|---|---|---|---|\n"
        f"| {changelog_version} | CR-1 | 2026-09-21 | 初版作成 |\n"
    )


class CompareTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.baseline = self.root / "baseline"
        self.current = self.root / "current"

    def tearDown(self):
        self.tmp.cleanup()

    def test_section_count_decrease_is_major(self):
        write(self.baseline / "auth" / "spec.md", make_module_file(headings=("## 1. A", "## 2. B")))
        write(self.current / "auth" / "spec.md", make_module_file(headings=("## 1. A",)))
        result = mod.compare(self.baseline, self.current)
        self.assertEqual(result["version_floors"]["auth/spec.md"]["level"], "MAJOR")

    def test_section_count_increase_is_minor(self):
        write(self.baseline / "auth" / "spec.md", make_module_file(headings=("## 1. A",)))
        write(self.current / "auth" / "spec.md", make_module_file(headings=("## 1. A", "## 2. B")))
        result = mod.compare(self.baseline, self.current)
        self.assertEqual(result["version_floors"]["auth/spec.md"]["level"], "MINOR")

    def test_heading_rename_is_minor(self):
        write(self.baseline / "auth" / "spec.md", make_module_file(headings=("## 1. Old Name",)))
        write(self.current / "auth" / "spec.md", make_module_file(headings=("## 1. New Name",)))
        result = mod.compare(self.baseline, self.current)
        self.assertEqual(result["version_floors"]["auth/spec.md"]["level"], "MINOR")

    def test_text_only_change_is_patch(self):
        write(self.baseline / "auth" / "spec.md", make_module_file())
        content = make_module_file().replace("body text for", "changed body text for")
        write(self.current / "auth" / "spec.md", content)
        result = mod.compare(self.baseline, self.current)
        self.assertEqual(result["version_floors"]["auth/spec.md"]["level"], "PATCH")

    def test_frontmatter_and_changelog_rewritten_when_below_floor(self):
        write(self.baseline / "auth" / "spec.md", make_module_file(version="1.0.0", headings=("## 1. A",)))
        content = make_module_file(version="1.0.1", changelog_version="1.0.1",
                                    headings=("## 1. A", "## 2. B"))
        write(self.current / "auth" / "spec.md", content)
        result = mod.compare(self.baseline, self.current)
        info = result["version_floors"]["auth/spec.md"]
        self.assertEqual(info["level"], "MINOR")
        self.assertEqual(info["floor_version"], "1.1.0")
        self.assertIn("auth/spec.md", result["rewritten_files"])
        rewritten = (self.current / "auth" / "spec.md").read_text(encoding="utf-8")
        self.assertIn('version: "1.1.0"', rewritten)
        self.assertIn("| 1.1.0 | CR-1 |", rewritten)

    def test_no_rewrite_when_current_already_meets_floor(self):
        write(self.baseline / "auth" / "spec.md", make_module_file(version="1.0.0", headings=("## 1. A",)))
        content = make_module_file(version="2.0.0", changelog_version="2.0.0",
                                    headings=("## 1. A", "## 2. B"))
        write(self.current / "auth" / "spec.md", content)
        result = mod.compare(self.baseline, self.current)
        self.assertNotIn("auth/spec.md", result["rewritten_files"])
        unchanged = (self.current / "auth" / "spec.md").read_text(encoding="utf-8")
        self.assertIn('version: "2.0.0"', unchanged)

    def test_identical_content_produces_no_floor(self):
        content = make_module_file()
        write(self.baseline / "auth" / "spec.md", content)
        write(self.current / "auth" / "spec.md", content)
        result = mod.compare(self.baseline, self.current)
        self.assertEqual(result["version_floors"], {})
        self.assertEqual(result["rewritten_files"], [])

    def test_removed_in_current_is_recorded(self):
        write(self.baseline / "auth" / "spec.md", make_module_file())
        result = mod.compare(self.baseline, self.current)
        self.assertEqual(result["diagnostics"]["auth/spec.md"], "removed_in_current")


class BumpVersionTestCase(unittest.TestCase):
    def test_major_resets_minor_and_patch(self):
        self.assertEqual(mod.bump_version("1.2.3", "MAJOR"), "2.0.0")

    def test_minor_resets_patch(self):
        self.assertEqual(mod.bump_version("1.2.3", "MINOR"), "1.3.0")

    def test_patch_increments_only_patch(self):
        self.assertEqual(mod.bump_version("1.2.3", "PATCH"), "1.2.4")


class CompareModulesTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.baseline = self.root / "baseline"
        self.current = self.root / "current"

    def tearDown(self):
        self.tmp.cleanup()

    def test_modules_limits_floors(self):
        for m in ("auth", "net"):
            write(self.baseline / m / "spec.md", make_module_file(headings=("## 1. A",)))
            write(self.current / m / "spec.md", make_module_file(headings=("## 1. A", "## 2. B")))
        result = mod.compare(self.baseline, self.current, ["auth"])
        self.assertEqual(list(result["version_floors"]), ["auth/spec.md"])

    def test_overview_version_row_is_rewritten(self):
        base = ('---\nversion: "1.0.0"\n---\n\n## 1. 文書概要\n\n| 項目 | 内容 |\n|---|---|\n| バージョン | 1.0.0 |\n\n'
                "## 2. 機能概要\n\nx\n\n## 9. 変更履歴\n\n| バージョン | CR | 日付 | 変更内容 |\n|---|---|---|---|\n"
                "| 1.0.0 | CR-1 | 2026-09-21 | 初版作成 |\n")
        cur = base.replace("## 2. 機能概要\n\nx\n", "## 2. 機能概要\n\nx\n\n## 3. 入出力\n\ny\n")
        write(self.baseline / "auth" / "spec.md", base)
        write(self.current / "auth" / "spec.md", cur)
        mod.compare(self.baseline, self.current, ["auth"])
        text = (self.current / "auth" / "spec.md").read_text(encoding="utf-8")
        self.assertIn("| バージョン | 1.1.0 |", text)
        self.assertIn('version: "1.1.0"', text)
        self.assertIn("| 1.1.0 | CR-1 |", text)


LEDGER_HEADER = ("| ファイルパス | モジュール | モジュールディレクトリ | 工程 | 関係する振る舞い（CRS） |\n"
                 "|---|---|---|---|---|\n")


def spec_md(module_dir=None, last_cr="CR-OLD"):
    md = "" if module_dir is None else f'module-dir: "{module_dir}"\n'
    return f'---\nversion: "1.0.0"\nlast-updated-cr: "{last_cr}"\n{md}---\n\n## 2. 機能概要\n\nx\n'


class SourcesTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cr = "CR-1"
        self.spo_dir = self.root / "xddp" / self.cr / "04_specout" / "svc"
        self.latest = self.root / "xddp" / "latest-specs" / "svc"
        self.docs = self.root / "docs" / "svc" / "specs"
        self.repo = self.root / "repo"
        for f in ("src/auth/login.c", "src/net/conn.c", "main.c", "src/gone/README.md"):
            write(self.repo / f, "x\n")
        ledger = LEDGER_HEADER + ("| src/auth/login.c | auth | src/auth | 下調べ | x |\n"
                                  "| main.c | root | . | 下調べ | x |\n")
        write(self.spo_dir / "work" / "documented-files.md", ledger)
        write(self.spo_dir / "modules" / "auth-spo.md", "# a\n\n## 2. 現状仕様\n\nx\n")
        write(self.spo_dir / "modules" / "root-spo.md", "# r\n\n## 2. 現状仕様\n\ny\n")
        write(self.spo_dir / f"SPO-{self.cr}.md",
              "# s\n\n## 3. モジュール間シーケンス図\n\n### 3.1 起動\n\nx\n\n### 3.2 Shut down\n\ny\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *extra):
        args = mod.build_parser().parse_args([
            "sources", "--spo-dir", str(self.spo_dir), "--cr", self.cr, "--latest-specs", str(self.latest),
            "--docs-specs", str(self.docs), "--out", str(self.root / "s.json"), *extra])
        return mod.sources(args)

    def test_modules_spec_dir_and_existing_spec(self):
        write(self.docs / "authentication" / "spec.md", spec_md("src/auth"))   # 名前が違っても同じ module-dir
        r = self._run()
        by = {m["name"]: m for m in r["modules"]}
        self.assertEqual(by["auth"]["spec_dir"], "authentication")
        self.assertEqual(by["auth"]["existing_spec"], str(self.docs / "authentication" / "spec.md"))
        self.assertEqual(by["root"]["module_dir"], ".")
        self.assertEqual(by["root"]["spec_dir"], "root")
        self.assertEqual(by["root"]["existing_spec"], "")
        self.assertEqual([s["file"] for s in r["overview_sequences"]], ["起動-seq.md", "shut-down-seq.md"])

    def test_latest_specs_wins_and_duplicates_are_reported(self):
        write(self.latest / "auth-x" / "spec.md", spec_md("src/auth"))
        write(self.latest / "auth-y" / "spec.md", spec_md("src/auth/"))
        write(self.docs / "authentication" / "spec.md", spec_md("src/auth"))
        r = self._run()
        auth = {m["name"]: m for m in r["modules"]}["auth"]
        self.assertEqual(auth["spec_dir"], "auth-x")
        dup = [c for c in r["conflicts"] if c["kind"] == "duplicate_module_dir"][0]
        self.assertEqual(dup["duplicates"], [str(self.latest / "auth-y"), str(self.docs / "authentication")])

    def test_spec_dir_collision(self):
        write(self.latest / "auth" / "spec.md", spec_md("lib/auth"))
        r = self._run()
        self.assertEqual([c["spec_dir"] for c in r["conflicts"] if c["kind"] == "spec_dir_collision"], ["auth"])

    def test_chd_rows_are_split_into_three_groups(self):
        write(self.latest / "net" / "spec.md", spec_md("src/net"))
        write(self.latest / "legacy" / "spec.md", spec_md(None))
        chd = self.root / "CHD.md"
        write(chd, "# CHD\n\n## 2. 変更対象ファイル一覧\n\n| # | リポジトリ | ファイルパス | 変更種別 | 対応SP番号 |\n"
                   "|---|---|---|---|---|\n| 1 | svc | src/auth/login.c | 変更 | SP |\n"
                   f"| 2 | svc | {self.repo}/src/net/conn.c | 変更 | SP |\n| 3 | svc | src/new/a.c | 追加 | SP |\n"
                   "| 4 | other | src/net/x.c | 変更 | SP |\n| 5 | svc | lib.c | 変更 | SP |\n"
                   "| 6 | {リポジトリ名} | {パス} | 追加 | SP |\n\n## 3. 詳細設計\n")
        r = self._run("--repo-path", str(self.repo), "--chd", str(chd))
        self.assertEqual(r["chd_only"], [{"spec_dir": "net", "module_dir": "src/net", "files": ["src/net/conn.c"]}])
        # main.c 以外の直下のファイル（lib.c）は root（`.`）に当たる。src/new/a.c はどれにも当たらない
        self.assertEqual(r["chd_unmatched"], ["src/new/a.c"])

    def test_chd_without_repository_column(self):
        write(self.latest / "net" / "spec.md", spec_md("src/net"))
        chd = self.root / "CHD.md"
        write(chd, "## 2. 変更対象ファイル一覧\n\n| # | ファイルパス | 変更種別 |\n|---|---|---|\n| 1 | src/net/conn.c | 変更 |\n")
        self.assertEqual(self._run("--chd", str(chd))["chd_only"][0]["files"], ["src/net/conn.c"])

    def test_missing_module_dirs_and_concurrent_protection(self):
        write(self.latest / "gone" / "spec.md", spec_md("src/gone"))             # 対象のファイル（.c）が無い
        write(self.latest / "vanished" / "spec.md", spec_md("src/vanished"))     # ディレクトリが無い
        write(self.latest / "other-cr" / "spec.md", spec_md("src/other", last_cr="CR-2"))
        write(self.latest / "closed-cr" / "spec.md", spec_md("src/closed", last_cr="CR-3"))
        write(self.latest / "single" / "spec.md", spec_md("src/net/conn.c"))     # 1ファイルのモジュール
        write(self.latest / "empty" / "spec.md", spec_md(""))                    # 範囲が決まらない
        write(self.latest / "rootmod" / "spec.md", spec_md("."))
        write(self.root / "xddp" / "CR-2" / "progress.md", "# p\n")
        write(self.root / "xddp" / "CR-3" / "progress.md", "# p\n\n## CR 中止\n")
        r = self._run("--repo-path", str(self.repo), "--include-ext", ".c", "--xddp-dir", str(self.root / "xddp"))
        self.assertEqual([(m["spec_dir"], m["reason"]) for m in r["missing_module_dirs"]],
                         [("closed-cr", "母体にディレクトリ・ファイルが無い"), ("gone", "母体に対象のファイルが無い"),
                          ("vanished", "母体にディレクトリ・ファイルが無い")])
        self.assertEqual([(m["spec_dir"], m["last_updated_cr"]) for m in r["protected_by_concurrent_cr"]],
                         [("other-cr", "CR-2")])

    def test_root_module_dir_matches_only_top_level_files(self):
        self.assertTrue(mod.in_module("main.c", "."))
        self.assertFalse(mod.in_module("src/a.c", "."))
        self.assertTrue(mod.in_module("src/net/conn.c", "src/net/conn.c"))
        self.assertFalse(mod.in_module("src/netx/a.c", "src/net"))
        write(self.latest / "rootmod" / "spec.md", spec_md("."))
        (self.repo / "main.c").unlink()
        r = self._run("--repo-path", str(self.repo), "--include-ext", ".c")
        self.assertEqual([m["spec_dir"] for m in r["missing_module_dirs"]], ["rootmod"])

    def test_spec_dir_cli_with_survey_fields(self):
        write(self.docs / "authentication" / "spec.md", spec_md("src/auth"))
        import io
        from contextlib import redirect_stdout, redirect_stderr
        out, err = io.StringIO(), io.StringIO()
        args = mod.build_parser().parse_args(["spec-dir", "--latest-specs", str(self.latest), "--docs-specs",
                                              str(self.docs), "--name", "auth", "--module-dir", "src/auth/"])
        with redirect_stdout(out), redirect_stderr(err):
            args.func(args)
        self.assertEqual(json.loads(out.getvalue())["spec_dir"], "authentication")
        args = mod.build_parser().parse_args(["spec-dir", "--latest-specs", str(self.latest), "--name", "AuthService"])
        out = io.StringIO()
        with redirect_stdout(out):
            args.func(args)
        self.assertEqual(json.loads(out.getvalue())["spec_dir"], "auth-service")


class SeqNamesTestCase(unittest.TestCase):
    def test_cross_level_names(self):
        text = ("## 3. シーケンス図\n\n### 3.1 repositoryレベルのシーケンス図\n\nx\n\n"
                "### 3.2 クラスレベルのシーケンス図（例: class）\n\ny\n\n## 4. 共有インタフェース一覧\n")
        subs = mod.sequence_subsections(text, mod.CROSS_SEQUENCE_HEADING, mod.docs_layout.cross_seq_stem)
        self.assertEqual([s["file"] for s in subs], ["repository-seq.md", "クラス-seq.md"])

    def test_single_body_defaults_to_main(self):
        text = "## 3. モジュール間シーケンス図\n\n```mermaid\nsequenceDiagram\n```\n"
        self.assertEqual([s["file"] for s in mod.sequence_subsections(text, mod.OVERVIEW_SEQUENCE_HEADING)],
                         ["main-seq.md"])
        self.assertEqual(mod.sequence_subsections("## 3. モジュール間シーケンス図\n\n対象外\n",
                                                  mod.OVERVIEW_SEQUENCE_HEADING), [])


TEMPLATES_11 = Path(__file__).resolve().parents[2] / "templates"
MODULE_TEMPLATE_04 = Path(__file__).resolve().parents[3] / "xddp-04-specout" / "templates" / "04_specout-module-template.md"


def _template_headings(path: Path, level: int) -> set:
    return {mod.normalize_heading_text(name) for _i, lvl, name in mod.iter_headings(
        path.read_text(encoding="utf-8").splitlines()) if lvl == level}


class TemplateContractTestCase(unittest.TestCase):
    """スクリプトの節の名前が、書く側のテンプレートにある（A4-6・A4-46 の型）。"""

    def test_spo_section_names_exist_in_module_template(self):
        h2 = _template_headings(MODULE_TEMPLATE_04, 2)
        h3 = _template_headings(MODULE_TEMPLATE_04, 3)
        for filename, spec in mod.FILE_TO_SPO_SECTION.items():
            names = h2 if spec["level"] == 2 else h3
            for name in spec["names"]:
                self.assertIn(name, names, f"{filename}: {name}")
        for name in mod.SEQUENCE_PARENT_HEADING["names"]:
            self.assertIn(name, h3)

    def test_existing_compared_sections_exist_in_11_templates(self):
        for kind, names in mod.EXISTING_COMPARED_SECTIONS.items():
            headings = _template_headings(TEMPLATES_11 / mod.EXISTING_COMPARED_TEMPLATES[kind], 2)
            for name in names:
                self.assertIn(name, headings, f"{kind}: {name}")


if __name__ == "__main__":
    unittest.main()
