import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crs_view import parse_crs_md, render_html, render_tree, _extract_meta, JS  # noqa: E402

CRS_TEXT = """**タイトル：** サンプルCRS
**対象CR：** CR-2026-970
**版数：** 1.0
**作成日：** 2026-09-13

## 2. USDM 要求仕様

### ＜機能要求＞

#### CR-2026-970-UR-001 通常のUR

##### ＜画面別＞

- **分割軸：** 画面

###### CR-2026-970-SR-001-001 通常のSR

**＜仕様グループA＞**

- **CR-2026-970-SP-001-001.001**: 確定済のSP
  - **ステータス：** 確定
  - **Before：** 旧処理
  - **After：** 新処理

- **CR-2026-970-SP-001-001.002**: 未決のSP
  - **ステータス：** ❓ 未決
  - **Before：** 旧処理2
  - **After：** 新処理2

## 3. トレーサビリティマトリクス（TM）
"""


class CrsViewTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.md_path = self.root / "CRS-CR-2026-970.md"
        self.md_path.write_text(CRS_TEXT, encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _data(self):
        return parse_crs_md(str(self.md_path))

    def test_html_contains_all_sp_ids(self):
        data = self._data()
        meta = _extract_meta(str(self.md_path))
        out = render_html(data, meta, "CR-2026-970")
        self.assertIn("CR-2026-970-SP-001-001.001", out)
        self.assertIn("CR-2026-970-SP-001-001.002", out)

    def test_html_status_data_attribute_matches(self):
        data = self._data()
        meta = _extract_meta(str(self.md_path))
        out = render_html(data, meta, "CR-2026-970")
        self.assertIn(
            '<div class="sp" id="CR-2026-970-SP-001-001.001" data-status="確定">', out
        )
        self.assertIn(
            '<div class="sp" id="CR-2026-970-SP-001-001.002" data-status="❓ 未決">', out
        )

    def test_tree_status_filter_excludes_others(self):
        data = self._data()
        meta = _extract_meta(str(self.md_path))
        text = render_tree(data, meta, color=False, only_status={"確定"})
        self.assertIn("CR-2026-970-SP-001-001.001", text)
        self.assertNotIn("CR-2026-970-SP-001-001.002", text)

    def test_html_category_and_req_group_rendered(self):
        data = self._data()
        meta = _extract_meta(str(self.md_path))
        out = render_html(data, meta, "CR-2026-970")
        self.assertIn("＜機能要求＞", out)
        self.assertIn("＜画面別＞", out)
        self.assertIn("画面", out)
        self.assertIn("＜仕様グループA＞", out)

    def test_export_md_matches_revise_table_shape(self):
        self.assertIn("## 2. 指摘事項と対応内容", JS)
        self.assertIn(
            "| # | 重要度 | 場所 | 指摘内容 | 対応内容 | 対応状況 |", JS
        )
        self.assertIn("⬜ 未対応", JS)

    def test_export_md_omits_blank_comment_rows(self):
        # buildMd() は textarea が空欄（trim後に空文字）の場合、rows へ push せず return する
        # ガード節を持つこと（ブラウザ実行のシミュレートはできないため静的に検証する）。
        m = re.search(r"function buildMd\(\)\{(.*?)\n\}", JS, re.S)
        self.assertIsNotNone(m)
        body = m.group(1)
        self.assertIn("if(!ta)return", body.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
