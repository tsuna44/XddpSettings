import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crs_model import parse_crs_md  # noqa: E402

CRS_NO_CATEGORY = """# 変更要求仕様書

## 2. USDM 要求仕様

#### CR-2026-970-UR-001 カテゴリなしのUR

##### ＜要求グループ＞

###### CR-2026-970-SR-001-001 通常のSR

**＜仕様グループ＞**

- **CR-2026-970-SP-001-001.001**: 通常のSP

## 3. トレーサビリティマトリクス（TM）
"""

CRS_MULTI_CATEGORY = """# 変更要求仕様書

## 2. USDM 要求仕様

### ＜機能要求＞

#### CR-2026-970-UR-001 機能要求のUR1

##### ＜要求グループ＞

###### CR-2026-970-SR-001-001 SR1

**＜仕様グループ＞**

- **CR-2026-970-SP-001-001.001**: SP1

#### CR-2026-970-UR-002 機能要求のUR2

##### ＜要求グループ＞

###### CR-2026-970-SR-002-001 SR2

**＜仕様グループ＞**

- **CR-2026-970-SP-002-001.001**: SP2

### ＜非機能要求＞

#### CR-2026-970-UR-003 非機能要求のUR1

##### ＜要求グループ＞

###### CR-2026-970-SR-003-001 SR3

**＜仕様グループ＞**

- **CR-2026-970-SP-003-001.001**: SP3

## 3. トレーサビリティマトリクス（TM）
"""

CRS_REQ_GROUP_AXIS = """# 変更要求仕様書

## 2. USDM 要求仕様

### ＜機能要求＞

#### CR-2026-970-UR-001 通常のUR

##### ＜画面別＞

- **分割軸：** 画面

###### CR-2026-970-SR-001-001 SR1

**＜仕様グループ＞**

- **CR-2026-970-SP-001-001.001**: SP1

###### CR-2026-970-SR-001-002 SR2

**＜仕様グループ＞**

- **CR-2026-970-SP-001-002.001**: SP2

## 3. トレーサビリティマトリクス（TM）
"""

CRS_SPEC_GROUP = """# 変更要求仕様書

## 2. USDM 要求仕様

### ＜機能要求＞

#### CR-2026-970-UR-001 通常のUR

##### ＜要求グループ＞

###### CR-2026-970-SR-001-001 通常のSR

**＜仕様グループA＞**

- **CR-2026-970-SP-001-001.001**: SP1

**＜仕様グループB＞**

- **CR-2026-970-SP-001-001.002**: SP2

## 3. トレーサビリティマトリクス（TM）
"""

CRS_ONE_LAYER = """# 変更要求仕様書

## 2. USDM 要求仕様

### ＜機能要求＞

#### CR-2026-970-UR-001 1階層パターンのUR

**＜仕様グループ＞**

- **CR-2026-970-SP-001-001.001**: 1階層パターンのSP

## 3. トレーサビリティマトリクス（TM）
"""

CRS_KENEN = """# 変更要求仕様書

## 2. USDM 要求仕様

### ＜機能要求＞

#### CR-2026-970-UR-001 懸念ありのUR

- **懸念・検討事項：** UR懸念事項

##### ＜要求グループ＞

###### CR-2026-970-SR-001-001 懸念ありのSR

- **懸念・検討事項：** SR懸念事項

**＜仕様グループ＞**

- **CR-2026-970-SP-001-001.001**: 通常のSP

## 3. トレーサビリティマトリクス（TM）
"""


class CrsModelTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write(self, text, name="CRS-CR-2026-970.md"):
        md_path = self.root / name
        md_path.write_text(text, encoding="utf-8")
        return str(md_path)

    def test_ur_without_category_raises_fail_loud(self):
        md_path = self._write(CRS_NO_CATEGORY)
        with self.assertRaises(ValueError) as ctx:
            parse_crs_md(md_path)
        self.assertIn("CR-2026-970-UR-001", str(ctx.exception))

    def test_categories_nest_urs_correctly(self):
        md_path = self._write(CRS_MULTI_CATEGORY)
        data = parse_crs_md(md_path)
        self.assertEqual(len(data["categories"]), 2)

        cat1, cat2 = data["categories"]
        self.assertEqual(cat1.name, "機能要求")
        self.assertEqual([ur.ur_id for ur in cat1.ur_list],
                          ["CR-2026-970-UR-001", "CR-2026-970-UR-002"])

        self.assertEqual(cat2.name, "非機能要求")
        self.assertEqual([ur.ur_id for ur in cat2.ur_list], ["CR-2026-970-UR-003"])

        # 後方互換フラットリストは全カテゴリを跨いで全 UR を保持する
        self.assertEqual([ur.ur_id for ur in data["urs"]],
                          ["CR-2026-970-UR-001", "CR-2026-970-UR-002", "CR-2026-970-UR-003"])

    def test_sr_req_group_and_axis_are_captured(self):
        md_path = self._write(CRS_REQ_GROUP_AXIS)
        data = parse_crs_md(md_path)
        ur = data["urs"][0]
        self.assertEqual(len(ur.sr_list), 2)
        for sr in ur.sr_list:
            self.assertEqual(sr.req_group, "画面別")
            self.assertEqual(sr.axis, "画面")

    def test_sp_spec_group_is_captured(self):
        md_path = self._write(CRS_SPEC_GROUP)
        data = parse_crs_md(md_path)
        sr = data["urs"][0].sr_list[0]
        self.assertEqual(len(sr.sp_list), 2)
        self.assertEqual(sr.sp_list[0].spec_group, "仕様グループA")
        self.assertEqual(sr.sp_list[1].spec_group, "仕様グループB")

    def test_direct_sp_list_holds_one_layer_pattern_sps(self):
        md_path = self._write(CRS_ONE_LAYER)
        data = parse_crs_md(md_path)
        ur = data["urs"][0]
        self.assertEqual(len(ur.sr_list), 0)
        self.assertEqual(len(ur.direct_sp_list), 1)
        sp = ur.direct_sp_list[0]
        self.assertEqual(sp.sp_id, "CR-2026-970-SP-001-001.001")
        self.assertEqual(sp.spec_group, "仕様グループ")

    def test_ur_and_sr_kenen_are_captured(self):
        md_path = self._write(CRS_KENEN)
        data = parse_crs_md(md_path)
        ur = data["urs"][0]
        self.assertEqual(ur.kenen, "UR懸念事項")
        sr = ur.sr_list[0]
        self.assertEqual(sr.kenen, "SR懸念事項")


if __name__ == "__main__":
    unittest.main()
