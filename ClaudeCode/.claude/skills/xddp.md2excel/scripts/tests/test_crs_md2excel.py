import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crs_md2excel import build_excel_from_md, parse_crs_md  # noqa: E402

UR_BLOCK_START = "【ユーザ要求】"  # add_ur_row()が全UR行セット（実UR・プレースホルダ共通）の
                                    # 1行目・列Aに出力する固定ラベル。行ブロックの境界マーカーとして使う。

CRS_TEXT_NORMAL = """# 変更要求仕様書

## 2. USDM 要求仕様

##### UR-001 通常のUR

###### SR-001-001 通常のSR

####### SP-001-001.001 通常のSP

- **ID:** SP-001-001.001

## 3. トレーサビリティマトリクス（TM）
"""

CRS_TEXT_ORPHAN_SR = """# 変更要求仕様書

## 2. USDM 要求仕様

##### UR-001 通常のUR

###### SR-001-001 通常のSR

####### SP-001-001.001 通常のSP

- **ID:** SP-001-001.001

##### 本CRの対象範囲を限定する（形式的なURを持たないスコープ宣言）

###### SR-999-001 スコープ除外の宣言（親URなし）

- **ID:** SR-999-001

## 3. トレーサビリティマトリクス（TM）
"""


class CrsMd2ExcelTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _build(self, text):
        md_path = self.root / "CRS-TEST.md"
        md_path.write_text(text, encoding="utf-8")
        out_path = self.root / "out.xlsx"
        build_excel_from_md(str(md_path), str(out_path))
        wb = openpyxl.load_workbook(out_path)
        return wb.active

    def test_normal_ur_sr_sp_hierarchy_is_parsed(self):
        md_path = self.root / "CRS-TEST.md"
        md_path.write_text(CRS_TEXT_NORMAL, encoding="utf-8")
        data = parse_crs_md(str(md_path))
        self.assertEqual(len(data["urs"]), 1)
        ur = data["urs"][0]
        self.assertEqual(ur.ur_id, "UR-001")
        self.assertEqual(len(ur.sr_list), 1)
        sr = ur.sr_list[0]
        self.assertEqual(sr.sr_id, "SR-001-001")
        self.assertEqual(len(sr.sp_list), 1)
        self.assertEqual(sr.sp_list[0].sp_id, "SP-001-001.001")

    def test_sr_without_parent_ur_is_not_misattached(self):
        ws = self._build(CRS_TEXT_ORPHAN_SR)

        ur001_row = next(
            r for r in range(1, ws.max_row + 1)
            if ws.cell(r, 1).value == UR_BLOCK_START and ws.cell(r, 2).value == "UR-001"
        )
        # UR-001の次のUR行セット（実UR・プレースホルダいずれか。またはシート末尾）までの
        # 範囲にSR-999-001が出現しないこと
        next_ur_block_row = next(
            (r for r in range(ur001_row + 1, ws.max_row + 1)
             if ws.cell(r, 1).value == UR_BLOCK_START),
            ws.max_row + 1,
        )
        sr_ids_under_ur001 = [
            ws.cell(r, 3).value for r in range(ur001_row + 1, next_ur_block_row)
        ]
        self.assertNotIn("SR-999-001", sr_ids_under_ur001)

        # SR-999-001自体はどこかに出力されている（サイレントに消えていない）こと
        all_sr_ids = [ws.cell(r, 3).value for r in range(1, ws.max_row + 1)]
        self.assertIn("SR-999-001", all_sr_ids)

        # 親URなしグループの見出し行が、UR-001とは別の独立したUR行セットとして
        # 出力されていること（＝サイレントにUR-001へ吸収されていないことの直接確認）
        placeholder_row = next(
            r for r in range(1, ws.max_row + 1)
            if ws.cell(r, 1).value == UR_BLOCK_START
            and ws.cell(r, 2).value in (None, "")
            and ws.cell(r, 3).value and "スコープ宣言" in ws.cell(r, 3).value
        )
        self.assertGreater(placeholder_row, ur001_row)


if __name__ == "__main__":
    unittest.main()
