import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chd_sp_coverage as mod  # noqa: E402

CRS_TEXT = """# 変更要求仕様書

## 1. 変更概要

## 2. USDM 要求仕様

##### UR-001 タイトル

###### SR-001-001 タイトル

####### SP-001-001.001 数値以外の入力を拒否する

- **ID:** SP-001-001.001

####### SP-001-001.002 空文字列を拒否する

- **ID:** SP-001-001.002

## 3. トレーサビリティマトリクス（TM）

| 要求ID（親） | 要求ID（子） | 仕様ID | 設計 | 実装 | テスト |
|---|---|---|---|---|---|
| UR-001 | SR-001-001 | SP-001-001.001 | | | |
| UR-001 | SR-001-001 | SP-001-001.002 | | | |

## 4. 影響範囲（暫定）
"""

CHD_INDEX_TEXT = """# 変更設計書 インデックス

## 2. UR別ファイル一覧

| UR ID | UR名 | バッチ | SP数 | ファイル | 該当変更 |
|---|---|---|---|---|---|
| UR-001 | 入力値の妥当性検証 | - | 2 | [CHD-CR-TEST-UR-001.md](./CHD-CR-TEST-UR-001.md) | あり |
"""

CHD_CONTENT_TEXT_PARTIAL = """# 変更設計書

## 4. トレーサビリティマトリクス

| 仕様ID | 仕様名 | 変更ファイル | 変更シンボル（関数・構造体・定数等） |
|--------|--------|------------|--------------------------------------|
| SP-001-001.001 | 数値以外の入力を拒否する | src/mod_a.py | process |
| SP-001-001.002 | 空文字列を拒否する | - | - |
"""

CHD_CONTENT_TEXT_FULL = """# 変更設計書

## 4. トレーサビリティマトリクス

| 仕様ID | 仕様名 | 変更ファイル | 変更シンボル（関数・構造体・定数等） |
|--------|--------|------------|--------------------------------------|
| SP-001-001.001 | 数値以外の入力を拒否する | src/mod_a.py | process |
| SP-001-001.002 | 空文字列を拒否する | src/mod_a.py | process |
"""

CHD_CONTENT_TEXT_WITH_GUIDANCE_NOTE = """# 変更設計書

## 4. トレーサビリティマトリクス

> 仕様IDと変更箇所（ファイル・モジュール・シンボル）の対応を一覧化する。

| 仕様ID | 仕様名 | 変更ファイル | 変更シンボル（関数・構造体・定数等） |
|--------|--------|------------|--------------------------------------|
| SP-001-001.001 | 数値以外の入力を拒否する | src/mod_a.py | process |
| SP-001-001.002 | 空文字列を拒否する | - | - |
"""


class ChdSpCoverageTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.crs_path = self.root / "CRS-CR-TEST.md"
        self.crs_path.write_text(CRS_TEXT, encoding="utf-8")
        self.design_dir = self.root / "06_design"
        (self.design_dir / "svc-a").mkdir(parents=True)
        (self.design_dir / "svc-a" / "CHD-CR-TEST.md").write_text(CHD_INDEX_TEXT, encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, extra_args):
        parser = mod.build_parser()
        args = parser.parse_args([
            "--crs", str(self.crs_path), "--design-dir", str(self.design_dir),
            "--cr", "CR-TEST",
        ] + extra_args)
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def test_missing_sp_detected_when_content_file_absent(self):
        result = self._run(["--repos", "svc-a"])
        self.assertEqual(result["expected"], ["SP-001-001.001", "SP-001-001.002"])
        self.assertEqual(result["missing"], ["SP-001-001.001", "SP-001-001.002"])

    def test_partial_coverage(self):
        (self.design_dir / "svc-a" / "CHD-CR-TEST-UR-001.md").write_text(
            CHD_CONTENT_TEXT_PARTIAL, encoding="utf-8"
        )
        result = self._run(["--repos", "svc-a"])
        self.assertEqual(result["covered"], ["SP-001-001.001"])
        self.assertEqual(result["missing"], ["SP-001-001.002"])

    def test_full_coverage_no_missing(self):
        (self.design_dir / "svc-a" / "CHD-CR-TEST-UR-001.md").write_text(
            CHD_CONTENT_TEXT_FULL, encoding="utf-8"
        )
        result = self._run(["--repos", "svc-a"])
        self.assertEqual(result["missing"], [])

    def test_partial_coverage_with_guidance_note(self):
        """テンプレート実態（見出し直後にガイダンス引用文あり）でも正しく検出できることを確認する
        回帰テスト（発見: PLAN-20260723-p4-verification-script-fixes）"""
        (self.design_dir / "svc-a" / "CHD-CR-TEST-UR-001.md").write_text(
            CHD_CONTENT_TEXT_WITH_GUIDANCE_NOTE, encoding="utf-8"
        )
        result = self._run(["--repos", "svc-a"])
        self.assertEqual(result["covered"], ["SP-001-001.001"])
        self.assertEqual(result["missing"], ["SP-001-001.002"])

    def test_cross_repo_single_file_resolution(self):
        (self.design_dir / "cross").mkdir()
        (self.design_dir / "cross" / "CHD-CR-TEST-cross.md").write_text(
            "# cross\n\n## 2. インタフェース変更サマリー\n", encoding="utf-8"
        )
        result = self._run(["--repos", "svc-a,cross", "--list-only"])
        self.assertEqual(len(result["by_repo"]["cross"]["content_files"]), 1)
        self.assertEqual(result["by_repo"]["cross"]["covered"], [])

    def test_missing_chd_index_yields_empty_content_files(self):
        result = self._run(["--repos", "svc-b", "--list-only"])
        self.assertEqual(result["by_repo"]["svc-b"]["content_files"], [])

    def test_missing_crs_errors(self):
        parser = mod.build_parser()
        args = parser.parse_args([
            "--crs", str(self.root / "nope.md"), "--design-dir", str(self.design_dir),
            "--cr", "CR-TEST", "--repos", "svc-a",
        ])
        with self.assertRaises(SystemExit):
            args.func(args)


if __name__ == "__main__":
    unittest.main()
