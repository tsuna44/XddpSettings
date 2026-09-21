import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import crs_ur_scope as mod  # noqa: E402

CRS_TEXT = """# 変更要求仕様書

**文書番号：** CRS-CR-TEST

## 1. 変更概要

| 項目 | 内容 |
|------|------|
| 変更理由 | テスト用 |

---

## 2. USDM 要求仕様

> **記述ルール**
> ここにガイダンスが入る。

### ＜機能要求＞

#### CR-TEST-UR-001 タイトル1

- **ステータス：** 確定
- **理由：** 理由1

##### ＜要求グループ1＞

- **分割軸：** 時系列分割

###### CR-TEST-SR-001-001 タイトル

**＜仕様グループ1＞**

- **CR-TEST-SP-001-001.010**: 仕様1
  - **Before：** なし
  - **After：** 仕様1を行う

#### CR-TEST-UR-002 タイトル2（1階層・SRなし）

- **ステータス：** 確定
- **理由：** 理由2

**＜仕様グループ2＞**

- **CR-TEST-SP-002-001.010**: 仕様2
  - **Before：** なし
  - **After：** 仕様2を行う

### ＜非機能要求＞

#### CR-TEST-UR-003 最後のUR（EOFまで続く）

- **ステータス：** 確定
- **理由：** 理由3

**＜仕様グループ3＞**

- **CR-TEST-SP-003-001.010**: 仕様3
  - **Before：** なし
  - **After：** 仕様3を行う
"""

CRS_TEXT_WITH_TM = CRS_TEXT + """
---

## 3. トレーサビリティマトリクス（TM）

### 3.1 要求〜仕様 対応表

| 要求ID（親） | 要求ID（子） | 仕様ID | 設計 | 実装 | テスト |
|------------|------------|--------|------|------|--------|
| CR-TEST-UR-001 | CR-TEST-SR-001-001 | CR-TEST-SP-001-001.010 | | | |
| CR-TEST-UR-002 | CR-TEST-UR-002 | CR-TEST-SP-002-001.010 | | | |

---

## 4. 影響範囲（暫定）

> スペックアウト完了後に更新する
"""


class CrsUrScopeTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.out_path = self.root / "out.md"

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, crs_text: str, ur_id: str):
        crs_path = self.root / "CRS-CR-TEST.md"
        crs_path.write_text(crs_text, encoding="utf-8")
        parser = mod.build_parser()
        args = parser.parse_args([
            "--crs", str(crs_path), "--ur-id", ur_id, "--out", str(self.out_path),
        ])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        result = json.loads(buf.getvalue())
        out_text = self.out_path.read_text(encoding="utf-8")
        return result, out_text

    def test_single_ur_with_sr_extracted(self):
        result, out_text = self._run(CRS_TEXT_WITH_TM, "CR-TEST-UR-001")
        self.assertTrue(result["ok"])
        self.assertTrue(result["ur_found"])
        self.assertIn("CR-TEST-UR-001 タイトル1", out_text)
        self.assertIn("CR-TEST-SR-001-001", out_text)
        self.assertIn("CR-TEST-SP-001-001.010", out_text)
        # 他 UR の本文は含まれない
        self.assertNotIn("CR-TEST-UR-002", out_text)
        self.assertNotIn("CR-TEST-UR-003", out_text)

    def test_flat_ur_without_sr_extracted(self):
        """1階層パターン（UR→仕様グループ→SP、SRなし）でも UR 配下の SP を過不足なく含む。"""
        result, out_text = self._run(CRS_TEXT_WITH_TM, "CR-TEST-UR-002")
        self.assertTrue(result["ur_found"])
        self.assertIn("CR-TEST-SP-002-001.010", out_text)
        self.assertNotIn("CR-TEST-SP-001-001.010", out_text)
        self.assertNotIn("CR-TEST-SP-003-001.010", out_text)

    def test_last_ur_extends_to_eof_boundary(self):
        """次に H1〜H4 見出しがない最後の UR は、次セクション（## 3.）の直前までを正しく含む。"""
        result, out_text = self._run(CRS_TEXT, "CR-TEST-UR-003")
        self.assertTrue(result["ur_found"])
        self.assertIn("CR-TEST-SP-003-001.010", out_text)

    def test_tm_rows_filtered_to_target_ur(self):
        result, out_text = self._run(CRS_TEXT_WITH_TM, "CR-TEST-UR-001")
        self.assertEqual(result["tm_rows"], 1)
        self.assertIn("CR-TEST-SP-001-001.010", out_text.split("### 3.1")[1])
        self.assertNotIn("CR-TEST-SP-002-001.010", out_text.split("### 3.1")[1])
        # ヘッダ2行は常に出力される
        self.assertIn("要求ID（親）", out_text)

    def test_tm_rows_zero_when_no_match_but_header_present(self):
        result, out_text = self._run(CRS_TEXT_WITH_TM, "CR-TEST-UR-003")
        self.assertEqual(result["tm_rows"], 0)
        self.assertIn("要求ID（親）", out_text)

    def test_ur_not_found_returns_false_and_section1_only(self):
        result, out_text = self._run(CRS_TEXT_WITH_TM, "CR-TEST-UR-999")
        self.assertTrue(result["ok"])
        self.assertFalse(result["ur_found"])
        self.assertEqual(result["tm_rows"], 0)
        self.assertIn("変更理由", out_text)
        self.assertNotIn("## 2. USDM 要求仕様", out_text)

    def test_no_tm_section_yields_no_rows(self):
        result, out_text = self._run(CRS_TEXT, "CR-TEST-UR-001")
        self.assertTrue(result["ur_found"])
        self.assertEqual(result["tm_rows"], 0)
        self.assertIn("## 3. トレーサビリティマトリクス（TM・UR抜粋）", out_text)

    def test_missing_crs_errors(self):
        parser = mod.build_parser()
        args = parser.parse_args([
            "--crs", str(self.root / "nope.md"), "--ur-id", "CR-TEST-UR-001",
            "--out", str(self.out_path),
        ])
        with self.assertRaises(SystemExit):
            args.func(args)


if __name__ == "__main__":
    unittest.main()
