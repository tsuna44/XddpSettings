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

    def _write_spo(self, module, spec_body="foo", structure_body="bar", state_body="baz", main_seq_body="qux"):
        write(
            self.spo_dir / f"{module}-spo.md",
            SPO_TEMPLATE.format(
                module=module, spec_body=spec_body, structure_body=structure_body,
                state_body=state_body, main_seq_body=main_seq_body,
            ),
        )

    def test_no_spo_file_skips_module(self):
        write(self.existing_root / "auth" / "spec.md", "old content")
        result = mod.precheck(self.existing_root, self.spo_dir, 20.0)
        self.assertEqual(result["diagnostics"]["auth"], {"skipped": "no_spo_file"})
        self.assertEqual(result["force_update_files"], [])

    def test_text_line_change_over_threshold_forces_update(self):
        write(self.existing_root / "auth" / "spec.md", "line1\nline2\n")
        self._write_spo("auth", spec_body="line1\nline2\nline3\nline4\nline5\n")
        result = mod.precheck(self.existing_root, self.spo_dir, 20.0)
        self.assertIn("auth/spec.md", result["force_update_files"])

    def test_text_line_change_under_threshold_no_force(self):
        write(self.existing_root / "auth" / "spec.md", "\n".join(f"line{i}" for i in range(20)))
        self._write_spo("auth", spec_body="\n".join(f"line{i}" for i in range(21)))
        result = mod.precheck(self.existing_root, self.spo_dir, 20.0)
        self.assertNotIn("auth/spec.md", result["force_update_files"])

    def test_mermaid_edge_change_forces_update_regardless_of_pct(self):
        old = "```mermaid\ngraph TD\nA-->B\n```\n"
        new = "```mermaid\ngraph TD\nA-->B\nB-->C\n```\n"
        write(self.existing_root / "auth" / "structure.md", old)
        self._write_spo("auth", structure_body=new)
        result = mod.precheck(self.existing_root, self.spo_dir, 20.0)
        self.assertIn("auth/structure.md", result["force_update_files"])
        self.assertTrue(result["diagnostics"]["auth/structure.md"]["mermaid_changed"])

    def test_no_matching_spo_section_is_skipped_safely(self):
        write(self.existing_root / "auth" / "state-machine.md", "some content")
        write(self.spo_dir / "auth-spo.md", "# SPO auth\n\n## 現状仕様\n\nno matching heading here\n")
        result = mod.precheck(self.existing_root, self.spo_dir, 20.0)
        self.assertEqual(
            result["diagnostics"]["auth/state-machine.md"], {"skipped": "no_matching_spo_section"}
        )
        self.assertNotIn("auth/state-machine.md", result["force_update_files"])

    def test_sequence_file_matched_by_kebab_feature_name(self):
        write(self.existing_root / "auth" / "sequences" / "main-seq.md", "old seq body\n")
        self._write_spo("auth", main_seq_body="new seq body with much more content added here now\n" * 3)
        result = mod.precheck(self.existing_root, self.spo_dir, 20.0)
        self.assertIn("auth/sequences/main-seq.md", result["force_update_files"])

    def test_overview_directory_excluded(self):
        write(self.existing_root / "overview" / "architecture.md", "x")
        result = mod.precheck(self.existing_root, self.spo_dir, 20.0)
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


if __name__ == "__main__":
    unittest.main()
