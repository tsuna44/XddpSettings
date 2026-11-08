import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spec_changes as mod  # noqa: E402

PROGRESS = """# 進捗管理 — CR-1

## 工程11 更新仕様書ファイル一覧

<!-- 古い注記 -->

---

## 次に実行すべきコマンド

```
/xddp-close CR-1
```
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def spec(cr: str, body: str = "x") -> str:
    return f'---\nversion: "1.0.0"\nlast-updated-cr: "{cr}"\n---\n\n{body}\n'


class SpecChangesTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.xddp = self.root / "xddp"
        self.docs = self.root / "docs"
        self.latest = self.xddp / "latest-specs"
        write(self.xddp / "CR-1" / "progress.md", PROGRESS)

    def tearDown(self):
        self.tmp.cleanup()

    def _exit_code(self, fn, *args):
        with redirect_stderr(io.StringIO()):
            try:
                fn(*args)
            except SystemExit as e:
                return e.code
        return 0

    def _progress(self) -> str:
        return (self.xddp / "CR-1" / "progress.md").read_text(encoding="utf-8")

    # --- snapshot・record -------------------------------------------------

    def test_snapshot_is_written_only_once(self):
        write(self.latest / "svc" / "a" / "spec.md", spec("CR-0"))
        self.assertTrue(mod.snapshot(self.xddp, "CR-1")["created"])
        write(self.latest / "svc" / "b" / "spec.md", spec("CR-1"))
        r = mod.snapshot(self.xddp, "CR-1")
        self.assertEqual((r["created"], r["files"]), (False, 1))

    def test_record_updated_and_deleted(self):
        write(self.latest / "svc" / "a" / "spec.md", spec("CR-0"))
        write(self.latest / "svc" / "gone" / "spec.md", spec("CR-0"))
        write(self.latest / "svc" / "same" / "spec.md", spec("CR-0"))
        mod.snapshot(self.xddp, "CR-1")
        write(self.latest / "svc" / "a" / "spec.md", spec("CR-1", "changed"))
        write(self.latest / "svc" / "new" / "spec.md", spec("CR-1"))
        (self.latest / "svc" / "gone" / "spec.md").unlink()
        r = mod.record(self.xddp, "CR-1")
        self.assertEqual(r["updated"], ["latest-specs/svc/a/spec.md", "latest-specs/svc/new/spec.md"])
        self.assertEqual(r["deleted"], ["latest-specs/svc/gone/spec.md"])
        text = self._progress()
        self.assertIn("- latest-specs/svc/new/spec.md", text)
        self.assertIn("## 工程11 削除した仕様書ファイル一覧", text)
        self.assertIn("- latest-specs/svc/gone/spec.md", text)
        self.assertNotIn("<!-- 古い注記 -->", text)
        self.assertLess(text.index("## 工程11 削除した仕様書ファイル一覧"), text.index("## 次に実行すべきコマンド"))
        self.assertFalse(mod.record(self.xddp, "CR-1")["written"])   # 同じ内容なら書かない

    def test_record_creates_sections_when_missing(self):
        write(self.xddp / "CR-1" / "progress.md", "# 進捗管理 — CR-1\n\n## 次に実行すべきコマンド\n\nx\n")
        mod.snapshot(self.xddp, "CR-1")
        write(self.latest / "svc" / "a" / "spec.md", spec("CR-1"))
        mod.record(self.xddp, "CR-1")
        text = self._progress()
        self.assertLess(text.index("## 工程11 更新仕様書ファイル一覧"), text.index("## 工程11 削除した仕様書ファイル一覧"))
        self.assertLess(text.index("## 工程11 削除した仕様書ファイル一覧"), text.index("## 次に実行すべきコマンド"))

    def test_record_dry_run_does_not_write(self):
        mod.snapshot(self.xddp, "CR-1")
        write(self.latest / "svc" / "a" / "spec.md", spec("CR-1"))
        r = mod.record(self.xddp, "CR-1", dry_run=True)
        self.assertEqual(r["updated"], ["latest-specs/svc/a/spec.md"])
        self.assertEqual(self._progress(), PROGRESS)

    def test_record_without_baseline_fails(self):
        self.assertEqual(self._exit_code(mod.record, self.xddp, "CR-1"), 1)
        write(self.xddp / "CR-1" / mod.BASELINE_FILE, "{broken")
        self.assertEqual(self._exit_code(mod.record, self.xddp, "CR-1"), 1)

    # --- seed -------------------------------------------------------------

    def test_seed_copies_docs_only_files(self):
        write(self.docs / "svc" / "specs" / "auth" / "spec.md", spec("CR-0", "docs"))
        write(self.docs / "svc" / "specs" / "net" / "spec.md", spec("CR-0", "docs"))
        write(self.latest / "svc" / "net" / "spec.md", spec("CR-9", "unpromoted"))   # latest-specs にあるものは写さない
        write(self.docs / "system" / "specs" / "use-cases" / "u" / "description.md", spec("CR-0"))
        r = mod.seed(self.xddp, "CR-1", self.docs, ["svc", "system"])
        self.assertEqual(r["copied"], ["latest-specs/svc/auth/spec.md", "latest-specs/system/use-cases/u/description.md"])
        self.assertIn("unpromoted", (self.latest / "svc" / "net" / "spec.md").read_text(encoding="utf-8"))
        mod.snapshot(self.xddp, "CR-1")
        self.assertEqual(mod.record(self.xddp, "CR-1")["updated"], [])   # 写したものは今の CR の変更ではない

    def test_seed_on_rerun_does_not_restore_this_crs_deletion(self):
        write(self.docs / "svc" / "specs" / "a" / "spec.md", spec("CR-0"))
        mod.seed(self.xddp, "CR-1", self.docs, ["svc"])
        mod.snapshot(self.xddp, "CR-1")
        (self.latest / "svc" / "a" / "spec.md").unlink()            # 今の CR が GATE で削除
        mod.record(self.xddp, "CR-1")
        r = mod.seed(self.xddp, "CR-1", self.docs, ["svc"])          # 再実行（分割実行・C0-4 の B）
        self.assertEqual((r["copied"], r["skipped_deleted_by_this_cr"]), ([], ["latest-specs/svc/a/spec.md"]))
        self.assertFalse((self.latest / "svc" / "a" / "spec.md").exists())
        self.assertEqual(mod.record(self.xddp, "CR-1")["deleted"], ["latest-specs/svc/a/spec.md"])

    def test_seed_does_not_restore_unpromoted_deletions_of_in_progress_crs(self):
        write(self.docs / "svc" / "specs" / "b" / "spec.md", spec("CR-0"))
        write(self.docs / "svc" / "specs" / "c" / "spec.md", spec("CR-0"))
        write(self.xddp / "CR-2" / "progress.md", "# p\n\n## 工程11 削除した仕様書ファイル一覧\n\n- latest-specs/svc/b/spec.md\n")
        write(self.xddp / "CR-3" / "progress.md",
              "# p\n\n## 工程11 削除した仕様書ファイル一覧\n\n- latest-specs/svc/c/spec.md\n\n## CR 中止\n")
        r = mod.seed(self.xddp, "CR-1", self.docs, ["svc"])          # 最初の実行（基準なし）
        self.assertEqual(r["skipped_deleted_by_other_cr"], [{"path": "latest-specs/svc/b/spec.md", "cr": "CR-2"}])
        self.assertEqual(r["copied"], ["latest-specs/svc/c/spec.md"])   # 中止した CR の削除一覧は見ない

    def test_seed_on_rerun_adds_copied_files_to_baseline(self):
        mod.snapshot(self.xddp, "CR-1")
        write(self.docs / "svc" / "specs" / "late" / "spec.md", spec("CR-0"))   # 基準の後に他の CR が昇格
        self.assertEqual(mod.seed(self.xddp, "CR-1", self.docs, ["svc"])["copied"], ["latest-specs/svc/late/spec.md"])
        self.assertEqual(mod.record(self.xddp, "CR-1")["updated"], [])

    # --- revert -----------------------------------------------------------

    def _setup_revert(self):
        for name in ("mine", "shared", "deleted", "other"):
            write(self.docs / "svc" / "specs" / name / "spec.md", spec("CR-0", "docs"))
            write(self.latest / "svc" / name / "spec.md", spec("CR-0", "docs"))
        write(self.latest / "svc" / "unpromoted" / "spec.md", spec("CR-2", "other cr"))   # 基準の時点で {DOCS} と違う
        write(self.docs / "svc" / "specs" / "unpromoted" / "spec.md", spec("CR-0", "docs"))
        mod.snapshot(self.xddp, "CR-1")
        write(self.latest / "svc" / "mine" / "spec.md", spec("CR-1", "changed"))
        write(self.latest / "svc" / "unpromoted" / "spec.md", spec("CR-1", "changed again"))
        write(self.latest / "svc" / "other" / "spec.md", spec("CR-2", "overwritten by other cr"))
        (self.latest / "svc" / "deleted" / "spec.md").unlink()
        write(self.latest / "svc" / "added" / "spec.md", spec("CR-1"))
        write(self.latest / "svc" / "added-by-other" / "spec.md", spec("CR-2"))

    def test_revert_dry_run_classifies_without_writing(self):
        self._setup_revert()
        r = mod.revert(self.xddp, "CR-1", self.docs, dry_run=True)
        self.assertEqual(r["restored"], ["latest-specs/svc/deleted/spec.md", "latest-specs/svc/mine/spec.md"])
        self.assertEqual(r["removed"], ["latest-specs/svc/added/spec.md"])
        kept = {k["path"]: k["reason"] for k in r["kept"]}
        self.assertIn("基準の時点で `{DOCS}` と違う", kept["latest-specs/svc/unpromoted/spec.md"])
        self.assertIn("別の CR（CR-2）", kept["latest-specs/svc/other/spec.md"])
        self.assertIn("別の CR（CR-2）", kept["latest-specs/svc/added-by-other/spec.md"])
        self.assertTrue((self.latest / "svc" / "added" / "spec.md").exists())
        self.assertIn("changed", (self.latest / "svc" / "mine" / "spec.md").read_text(encoding="utf-8"))

    def test_revert_restores_only_safe_files(self):
        self._setup_revert()
        mod.revert(self.xddp, "CR-1", self.docs)
        self.assertIn("docs", (self.latest / "svc" / "mine" / "spec.md").read_text(encoding="utf-8"))
        self.assertTrue((self.latest / "svc" / "deleted" / "spec.md").is_file())
        self.assertFalse((self.latest / "svc" / "added").exists())        # 空になったディレクトリも消す
        self.assertIn("changed again", (self.latest / "svc" / "unpromoted" / "spec.md").read_text(encoding="utf-8"))
        self.assertIn("overwritten", (self.latest / "svc" / "other" / "spec.md").read_text(encoding="utf-8"))
        self.assertTrue((self.latest / "svc" / "added-by-other" / "spec.md").is_file())
        r = mod.record(self.xddp, "CR-1", dry_run=True)   # 残った変更は戻せなかったものだけ
        self.assertEqual(r["updated"], ["latest-specs/svc/added-by-other/spec.md", "latest-specs/svc/other/spec.md",
                                        "latest-specs/svc/unpromoted/spec.md"])

    def test_cli_outputs_json(self):
        buf = io.StringIO()
        from contextlib import redirect_stdout
        with redirect_stdout(buf):
            mod.main(["snapshot", "--xddp-dir", str(self.xddp), "--cr", "CR-1"])
        self.assertTrue(json.loads(buf.getvalue())["created"])


if __name__ == "__main__":
    unittest.main()
