import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import xddp_progress as mod  # noqa: E402

SAMPLE = """# 進捗管理

**CR番号：** CR-2026-999
**タイトル：** テスト用CR
**開始日：** 2026-01-01
**最終更新：** 2026-01-01

---

## 工程進捗

| # | 工程 | 担当 | 状態 | 詳細ステップ | 成果物 | 完了日 |
|---|------|------|------|------------|--------|--------|
| 1 | 要求書作成 | 人 | ✅ 完了 | - | [REQ.md](../REQ.md) | 2026-01-01 |
| 2 | 要求分析・整理 | AI | 🔄 進行中 | Step A: 分析中 | - | - |
| 4a | スペックアウト | AI | ⬜ 未着手 | - | - | - |

---

## 次に実行すべきコマンド

```
/xddp.02.analysis CR-2026-999
```

---

## 備考・メモ

既存の恒久メモ。

---

## 気づき・提案メモ
"""


class ProgressUpdateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.cr_path = Path(self.tmpdir.name)
        (self.cr_path / "progress.md").write_text(SAMPLE, encoding="utf-8", newline="\n")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, argv):
        parser = mod.build_parser()
        args = parser.parse_args(argv)
        args.func(args)

    def test_update_in_progress_keeps_dash_completed_date(self):
        self._run([
            "update", "--cr-path", str(self.cr_path), "--step", "4a",
            "--state", "🔄 進行中", "--detail", "Step A: Discovery中",
        ])
        text = (self.cr_path / "progress.md").read_text(encoding="utf-8")
        self.assertIn("| 4a | スペックアウト | AI | 🔄 進行中 | Step A: Discovery中 | - | - |", text)
        today = datetime.date.today().isoformat()
        self.assertIn(f"**最終更新：** {today}", text)

    def test_update_complete_sets_completed_date_and_artifact_link(self):
        self._run([
            "update", "--cr-path", str(self.cr_path), "--step", "2",
            "--state", "✅ 完了", "--detail", "-", "--artifact-link", "[ANA.md](ANA.md)",
        ])
        text = (self.cr_path / "progress.md").read_text(encoding="utf-8")
        today = datetime.date.today().isoformat()
        self.assertIn(f"| 2 | 要求分析・整理 | AI | ✅ 完了 | - | [ANA.md](ANA.md) | {today} |", text)

    def test_update_complete_removes_matching_warning_lines_only(self):
        self._run(["note-add", "--cr-path", str(self.cr_path), "--step", "2", "--text", "未解決指摘あり"])
        self._run(["note-add", "--cr-path", str(self.cr_path), "--step", "4a", "--text", "別工程の警告"])
        self._run([
            "update", "--cr-path", str(self.cr_path), "--step", "2",
            "--state", "✅ 完了", "--detail", "-",
        ])
        text = (self.cr_path / "progress.md").read_text(encoding="utf-8")
        self.assertNotIn("⚠️ 工程2: 未解決指摘あり", text)
        self.assertIn("⚠️ 工程4a: 別工程の警告", text)

    def test_update_artifact_link_applies_even_when_not_complete(self):
        self._run([
            "update", "--cr-path", str(self.cr_path), "--step", "4a",
            "--state", "🔄 進行中", "--detail", "Step C': TM生成中",
            "--artifact-link", "[TM.md](TM.md)",
        ])
        text = (self.cr_path / "progress.md").read_text(encoding="utf-8")
        self.assertIn("| 4a | スペックアウト | AI | 🔄 進行中 | Step C': TM生成中 | [TM.md](TM.md) | - |", text)

    def test_update_without_detail_preserves_existing_detail(self):
        self._run([
            "update", "--cr-path", str(self.cr_path), "--step", "2",
            "--state", "🔁 差し戻し",
        ])
        text = (self.cr_path / "progress.md").read_text(encoding="utf-8")
        self.assertIn("| 2 | 要求分析・整理 | AI | 🔁 差し戻し | Step A: 分析中 | - | - |", text)

    def test_update_unknown_step_errors(self):
        with self.assertRaises(SystemExit):
            self._run([
                "update", "--cr-path", str(self.cr_path), "--step", "99",
                "--state", "✅ 完了", "--detail", "-",
            ])

    def test_note_add_and_remove(self):
        self._run(["note-add", "--cr-path", str(self.cr_path), "--step", "4a", "--text", "件数不一致"])
        text = (self.cr_path / "progress.md").read_text(encoding="utf-8")
        self.assertIn("⚠️ 工程4a: 件数不一致", text)
        self._run(["note-remove", "--cr-path", str(self.cr_path), "--step", "4a"])
        text = (self.cr_path / "progress.md").read_text(encoding="utf-8")
        self.assertNotIn("⚠️ 工程4a: 件数不一致", text)

    def test_history_add_survives_complete_transition(self):
        self._run([
            "history-add", "--cr-path", str(self.cr_path), "--step", "4a",
            "--text", "re-discover 実施（2026-01-02）追加エントリポイント: foo",
        ])
        self._run([
            "update", "--cr-path", str(self.cr_path), "--step", "4a",
            "--state", "✅ 完了", "--detail", "-",
        ])
        text = (self.cr_path / "progress.md").read_text(encoding="utf-8")
        self.assertIn("re-discover 実施（2026-01-02）追加エントリポイント: foo", text)

    def test_close_state_creates_section_and_updates(self):
        self._run([
            "close-state", "--cr-path", str(self.cr_path),
            "--state", "🔄 進行中", "--detail", "Step C: 昇格処理中",
        ])
        text = (self.cr_path / "progress.md").read_text(encoding="utf-8")
        self.assertIn("## xddp.close 進捗", text)
        self.assertIn("**状態：** 🔄 進行中", text)
        self.assertIn("**詳細ステップ：** Step C: 昇格処理中", text)

        self._run([
            "close-state", "--cr-path", str(self.cr_path), "--state", "⏸ 中断",
        ])
        text = (self.cr_path / "progress.md").read_text(encoding="utf-8")
        self.assertIn("**状態：** ⏸ 中断", text)
        self.assertIn("**詳細ステップ：** Step C: 昇格処理中", text)
        self.assertEqual(text.count("## xddp.close 進捗"), 1)

    def test_show_returns_row_as_json(self):
        parser = mod.build_parser()
        args = parser.parse_args(["show", "--cr-path", str(self.cr_path), "--step", "1"])
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        result = json.loads(buf.getvalue())
        self.assertEqual(result["state"], "✅ 完了")
        self.assertEqual(result["completed_date"], "2026-01-01")

    def test_missing_file_errors(self):
        empty_dir = Path(self.tmpdir.name) / "nope"
        with self.assertRaises(SystemExit):
            self._run(["show", "--cr-path", str(empty_dir), "--step", "1"])


if __name__ == "__main__":
    unittest.main()
