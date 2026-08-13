import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import artifact_lint as mod  # noqa: E402

MODULE_SPEC_OK = """---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
module: "sensor-reader"
repo: "device-svc"
has_insights: false
---

# spec
"""

MODULE_SPEC_MISSING_MODULE = """---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
repo: "device-svc"
has_insights: false
---

# spec
"""

OVERVIEW_OK = """---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
repo: "device-svc"
has_insights: false
---

# overview
"""

USE_CASE_DESCRIPTION_MISSING_RELATED = """---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: ai-inferred
has_insights: false
---

# description
"""

NO_FRONTMATTER = "# no frontmatter\n\nsome content\n"

MERMAID_OK = """# doc

```mermaid
sequenceDiagram
  A->>B: hello
```
"""

MERMAID_MISSING_KEYWORD = """# doc

```mermaid
A --> B
```
"""

MERMAID_EMPTY = """# doc

```mermaid
```
"""

MERMAID_UNBALANCED = """# doc

```mermaid
graph TD
  A[Start --> B[End]
```
"""

MERMAID_BROKEN_ARROW = """# doc

```mermaid
graph TD
  A -> B
```
"""

MERMAID_DOTTED_EDGE = """# doc

```mermaid
graph TD
  A -.-> B
  C -. label .-> D
```
"""

TABLE_MISMATCH = """# doc

| a | b | c |
|---|---|---|
| 1 | 2 |
"""

TABLE_OK = """# doc

| a | b | c |
|---|---|---|
| 1 | 2 | 3 |
"""


class ArtifactLintTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name) / "latest-specs"
        self.root.mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, path: Path, doc_type: str = "SPEC"):
        parser = mod.build_parser()
        args = parser.parse_args(["--file", str(path), "--doc-type", doc_type])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def test_module_spec_ok_no_missing_keys(self):
        p = self.root / "device-svc" / "sensor-reader" / "spec.md"
        p.parent.mkdir(parents=True)
        p.write_text(MODULE_SPEC_OK, encoding="utf-8")
        result = self._run(p)
        self.assertTrue(result["frontmatter"]["applicable"])
        self.assertEqual(result["frontmatter"]["missing_keys"], [])

    def test_module_spec_missing_module_key_detected(self):
        p = self.root / "device-svc" / "sensor-reader" / "spec.md"
        p.parent.mkdir(parents=True)
        p.write_text(MODULE_SPEC_MISSING_MODULE, encoding="utf-8")
        result = self._run(p)
        self.assertIn("module", result["frontmatter"]["missing_keys"])
        self.assertNotIn("repo", result["frontmatter"]["missing_keys"])

    def test_overview_does_not_require_module(self):
        p = self.root / "device-svc" / "overview" / "architecture.md"
        p.parent.mkdir(parents=True)
        p.write_text(OVERVIEW_OK, encoding="utf-8")
        result = self._run(p)
        self.assertEqual(result["frontmatter"]["missing_keys"], [])
        self.assertNotIn("module", result["frontmatter"]["required_keys"])

    def test_use_case_description_requires_related_modules(self):
        p = self.root / "system" / "use-cases" / "foo" / "description.md"
        p.parent.mkdir(parents=True)
        p.write_text(USE_CASE_DESCRIPTION_MISSING_RELATED, encoding="utf-8")
        result = self._run(p)
        self.assertIn("related-modules", result["frontmatter"]["missing_keys"])

    def test_non_spec_doc_type_skips_frontmatter(self):
        p = self.root / "device-svc" / "sensor-reader" / "spec.md"
        p.parent.mkdir(parents=True)
        p.write_text(MODULE_SPEC_MISSING_MODULE, encoding="utf-8")
        result = self._run(p, doc_type="CHD")
        self.assertFalse(result["frontmatter"]["applicable"])

    def test_no_frontmatter_file_skips_check(self):
        p = self.root / "plan.md"
        p.write_text(NO_FRONTMATTER, encoding="utf-8")
        result = self._run(p)
        self.assertFalse(result["frontmatter"]["applicable"])

    def test_mermaid_ok_no_issues(self):
        p = self.root / "doc.md"
        p.write_text(MERMAID_OK, encoding="utf-8")
        result = self._run(p, doc_type="SPEC")
        self.assertEqual(result["mermaid"][0]["issues"], [])

    def test_mermaid_missing_keyword_detected(self):
        p = self.root / "doc.md"
        p.write_text(MERMAID_MISSING_KEYWORD, encoding="utf-8")
        result = self._run(p)
        self.assertTrue(any("図種別キーワード" in i for i in result["mermaid"][0]["issues"]))

    def test_mermaid_empty_block_detected(self):
        p = self.root / "doc.md"
        p.write_text(MERMAID_EMPTY, encoding="utf-8")
        result = self._run(p)
        self.assertTrue(any("空です" in i for i in result["mermaid"][0]["issues"]))

    def test_mermaid_unbalanced_brackets_detected(self):
        p = self.root / "doc.md"
        p.write_text(MERMAID_UNBALANCED, encoding="utf-8")
        result = self._run(p)
        self.assertTrue(any("角括弧" in i for i in result["mermaid"][0]["issues"]))

    def test_mermaid_broken_arrow_detected(self):
        p = self.root / "doc.md"
        p.write_text(MERMAID_BROKEN_ARROW, encoding="utf-8")
        result = self._run(p)
        self.assertTrue(any("エッジ記法" in i for i in result["mermaid"][0]["issues"]))

    def test_mermaid_dotted_edge_not_flagged(self):
        """flowchart 内の `-.->` / `-. label .->`（点線エッジ）は正当な記法であり誤検出しない。"""
        p = self.root / "doc.md"
        p.write_text(MERMAID_DOTTED_EDGE, encoding="utf-8")
        result = self._run(p)
        # エッジ記法の issue が出ていないこと
        self.assertFalse(any("エッジ記法" in i for i in result["mermaid"][0]["issues"]))

    def test_mermaid_broken_arrow_still_detected_with_dotted_edge_present(self):
        """同じ図に点線エッジと破損単矢印が混在する場合、破損のみを検出する。"""
        mixed = """# doc

```mermaid
graph TD
  A -.-> B
  C -> D
```
"""
        p = self.root / "doc.md"
        p.write_text(mixed, encoding="utf-8")
        result = self._run(p)
        issues = result["mermaid"][0]["issues"]
        self.assertTrue(any("エッジ記法" in i and "C -> D" in i for i in issues))
        self.assertFalse(any("エッジ記法" in i and "-.->" in i for i in issues))

    def test_table_column_mismatch_detected(self):
        p = self.root / "doc.md"
        p.write_text(TABLE_MISMATCH, encoding="utf-8")
        result = self._run(p)
        self.assertEqual(len(result["tables"]), 1)
        self.assertIn("列数", result["tables"][0]["issue"])

    def test_table_ok_no_issues(self):
        p = self.root / "doc.md"
        p.write_text(TABLE_OK, encoding="utf-8")
        result = self._run(p)
        self.assertEqual(result["tables"], [])

    # -- PLAN-20260808 不具合1・二次被害B（GFM のパイプエスケープ）--------

    def test_table_lint_accepts_escaped_pipe(self):
        """GFM の正規のエスケープ `\\|` を含む3列テーブルを列数不一致として報告しない。"""
        p = self.root / "doc.md"
        p.write_text(
            "# T\n\n"
            "| 項目 | 内容 | 備考 |\n"
            "|---|---|---|\n"
            r"| A | `expire_flags \|= FLAG` | `\b(a\|b)\b` |" "\n",
            encoding="utf-8",
        )
        result = self._run(p)
        self.assertEqual(result["tables"], [])

    def test_table_lint_still_detects_real_mismatch(self):
        """非回帰: 本当に列数が違うテーブルは従来どおり検出される。"""
        p = self.root / "doc.md"
        p.write_text(
            "# T\n\n"
            "| 項目 | 内容 | 備考 |\n"
            "|---|---|---|\n"
            r"| A | `x \|= y` | 追加 | 余分 |" "\n",
            encoding="utf-8",
        )
        result = self._run(p)
        self.assertEqual(len(result["tables"]), 1)
        self.assertIn("列数", result["tables"][0]["issue"])

    def test_table_lint_backslash_terminated_cell_without_padding(self):
        """`\\` 終端セルの直後にパディング無しで区切りが続く記法の現在の判定を固定する
        （GFM ではエスケープとして解釈されるため1列扱いになる。望ましさの主張ではなく挙動固定）。"""
        p = self.root / "doc.md"
        p.write_text(
            "# T\n\n"
            "| 項目 | 内容 |\n"
            "|---|---|\n"
            "| C:\\| 次 |\n",
            encoding="utf-8",
        )
        result = self._run(p)
        self.assertEqual(len(result["tables"]), 1)
        self.assertIn("1列", result["tables"][0]["issue"])

    def test_files_mode_returns_array(self):
        p1 = self.root / "a.md"
        p1.write_text(TABLE_OK, encoding="utf-8")
        p2 = self.root / "b.md"
        p2.write_text(TABLE_MISMATCH, encoding="utf-8")
        parser = mod.build_parser()
        args = parser.parse_args(["--files", f"{p1},{p2}", "--doc-type", "SPEC"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        result = json.loads(buf.getvalue())
        self.assertEqual(len(result["results"]), 2)

    def test_missing_file_errors(self):
        parser = mod.build_parser()
        args = parser.parse_args(["--file", str(self.root / "nope.md"), "--doc-type", "SPEC"])
        with self.assertRaises(SystemExit):
            args.func(args)


# ── CRS 構造チェック（L1〜L13）用フィクスチャ ──────────────────────────────────
# ID 形式は形式 B（CR 名前空間先頭。例 CR-2026-970-UR-001）。

CRS_CLEAN = """## 2. USDM 要求仕様

### ＜機能要求＞

#### CR-2026-970-UR-001 検索したい

- **理由：** 業務効率化のため

##### ＜検索条件のグループ＞

- **分割軸：** 構成分割

###### CR-2026-970-SR-001-001 条件を保存する

- **理由：** 再利用のため

**＜プリセット仕様＞**

- **CR-2026-970-SP-001-001.001**: 保存する
  - **Before：** なし
  - **After：** 検索条件をプリセットに保存する
  - **理由：** UI簡略化
"""

CRS_L1_NOISE = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** ボタン等を表示する
"""

CRS_L2_UR_NO_REASON = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：**
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""

CRS_L3_SR_NO_REASON = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：**
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""

CRS_L3_FORCED_TWO_LAYER = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
##### ＜要求グループ＞
- **分割軸：** 構成分割
###### CR-2026-970-SR-001-001 s
- **理由：**
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""

CRS_L4_EMPTY_SPEC_GROUP = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜空グループ＞**
"""

CRS_L4_SP_PRESENT = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜充足グループ＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""

CRS_L5_THREE_LEVEL_SR = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""

CRS_L6_DUP_BODY = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** 旧処理をする
  - **After：** 新処理をする
- **CR-2026-970-SP-001-001.002**: u
  - **Before：** 旧処理をする
  - **After：** 新処理をする
"""

CRS_L7_DUP_ID = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** aする
- **CR-2026-970-SP-001-001.001**: u
  - **Before：** なし
  - **After：** bする
"""

CRS_L8_NO_CATEGORY = """#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""

CRS_L9_BAD_GROUP_NAME = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
##### 要求グループ：旧式
- **分割軸：** 構成分割
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜プリセット仕様＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""

CRS_L10_NEGATION = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** エラーを表示しない
"""

CRS_L11_BAD_AXIS = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
##### ＜要求グループ＞
- **分割軸：** てきとう分割
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""

CRS_L11_PLACEHOLDER_AXIS = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
##### ＜要求グループ＞
- **分割軸：** {時系列分割／構成分割／状態分割／共通分割 から1つを選択}
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""

CRS_L12_H7_HEADING = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
####### ＜g＞
####### CR-2026-970-SP-001-001.001 t
- **Before：** なし
- **After：** 保存する
"""

# L13: CR プレフィクスを欠く旧形式 ID（種別プレフィクスが先頭）。厳格化で黙殺される代わりに error 化する。
CRS_L13_UR_NO_CR = """### ＜機能要求＞
#### UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""

CRS_L13_SP_NO_CR = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **SP-001-001.001**: t
  - **Before：** なし
  - **After：** 保存する
"""


class CrsLintTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run_crs(self, content, doc_type="CRS"):
        p = self.root / "CRS.md"
        p.write_text(content, encoding="utf-8")
        parser = mod.build_parser()
        args = parser.parse_args(["--file", str(p), "--doc-type", doc_type])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def _checks(self, result):
        """crs.issues を {check: level} の dict にまとめる（重複 check はレベルで代表）。"""
        out = {}
        for it in result["crs"]["issues"]:
            out.setdefault(it["check"], it["level"])
        return out

    def test_clean_crs_no_issues(self):
        result = self._run_crs(CRS_CLEAN)
        self.assertTrue(result["crs"]["applicable"])
        self.assertEqual(result["crs"]["issues"], [])
        # 新形式（CR プレフィクス付き）は L13 を発火しない（no-fire）
        self.assertNotIn("L13", self._checks(result))

    def test_non_crs_doc_type_skips(self):
        result = self._run_crs(CRS_CLEAN, doc_type="ANA")
        self.assertFalse(result["crs"]["applicable"])
        self.assertNotIn("issues", result["crs"])

    def test_l1_noise_term_warning(self):
        checks = self._checks(self._run_crs(CRS_L1_NOISE))
        self.assertEqual(checks.get("L1"), "warning")

    def test_l2_ur_reason_error(self):
        checks = self._checks(self._run_crs(CRS_L2_UR_NO_REASON))
        self.assertEqual(checks.get("L2"), "error")

    def test_l3_sr_reason_warning(self):
        checks = self._checks(self._run_crs(CRS_L3_SR_NO_REASON))
        self.assertEqual(checks.get("L3"), "warning")

    def test_l3_forced_two_layer_excluded(self):
        checks = self._checks(self._run_crs(CRS_L3_FORCED_TWO_LAYER))
        self.assertNotIn("L3", checks)

    def test_l4_empty_spec_group_error(self):
        # #23 fire: SP を持たない仕様グループ（太字行）→ L4 発火（太字仕様グループ検出漏れによる沈黙を検出）
        checks = self._checks(self._run_crs(CRS_L4_EMPTY_SPEC_GROUP))
        self.assertEqual(checks.get("L4"), "error")

    def test_l4_sp_present_no_error(self):
        # #23 no-fire: SP を1件以上持つ仕様グループ → L4 非発火（SPリスト項目検出漏れによる過剰発火を検出）
        checks = self._checks(self._run_crs(CRS_L4_SP_PRESENT))
        self.assertNotIn("L4", checks)

    def test_l5_three_level_sr_error(self):
        checks = self._checks(self._run_crs(CRS_L5_THREE_LEVEL_SR))
        self.assertEqual(checks.get("L5"), "error")

    def test_l6_dup_body_warning(self):
        checks = self._checks(self._run_crs(CRS_L6_DUP_BODY))
        self.assertEqual(checks.get("L6"), "warning")

    def test_l6_dup_body_new_mode_warning(self):
        # new モードでは SP は **仕様：** で記述される
        fixture = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **仕様：** 新規処理を実装する
- **CR-2026-970-SP-001-001.002**: u
  - **仕様：** 新規処理を実装する
"""
        checks = self._checks(self._run_crs(fixture))
        self.assertEqual(checks.get("L6"), "warning")

    def test_l6_new_mode_distinct_specs_no_warning(self):
        fixture = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **仕様：** 処理Aを実装する
- **CR-2026-970-SP-001-001.002**: u
  - **仕様：** 処理Bを実装する
"""
        self.assertNotIn("L6", self._checks(self._run_crs(fixture)))

    def test_l6_new_mode_placeholder_specs_no_warning(self):
        # new モードで仕様が未編集プレースホルダの場合は重複判定から除外する
        fixture = """### ＜機能要求＞
#### CR-2026-970-UR-001 T
- **理由：** r
###### CR-2026-970-SR-001-001 s
- **理由：** r
**＜g＞**
- **CR-2026-970-SP-001-001.001**: t
  - **仕様：** {実現する仕様・動作}
- **CR-2026-970-SP-001-001.002**: u
  - **仕様：** {実現する仕様・動作}
"""
        self.assertNotIn("L6", self._checks(self._run_crs(fixture)))

    def test_l6_placeholder_after_not_flagged(self):
        # 未編集テンプレート（After が {…} プレースホルダ）の SP は L6 重複と判定しない
        result = self._run_crs(CRS_CLEAN)  # After は実文言だが単一SP
        self.assertNotIn("L6", self._checks(result))
        placeholder = (
            "### ＜機能要求＞\n"
            "#### CR-2026-970-UR-001 T\n- **理由：** r\n"
            "###### CR-2026-970-SR-001-001 s\n- **理由：** r\n"
            "**＜g＞**\n"
            "- **CR-2026-970-SP-001-001.001**: t\n  - **Before：** なし\n  - **After：** {変更後の仕様}\n"
            "- **CR-2026-970-SP-001-001.002**: u\n  - **Before：** なし\n  - **After：** {変更後の仕様}\n"
        )
        self.assertNotIn("L6", self._checks(self._run_crs(placeholder)))

    def test_l7_dup_id_error(self):
        checks = self._checks(self._run_crs(CRS_L7_DUP_ID))
        self.assertEqual(checks.get("L7"), "error")

    def test_l8_no_category_error(self):
        checks = self._checks(self._run_crs(CRS_L8_NO_CATEGORY))
        self.assertEqual(checks.get("L8"), "error")

    def test_l9_bad_group_name_warning(self):
        # #21 fire: 要求グループ（H5）が ＜＞ 表記でない → L9 発火。req_groups 登録移設が失われると沈黙する回帰を検出
        checks = self._checks(self._run_crs(CRS_L9_BAD_GROUP_NAME))
        self.assertEqual(checks.get("L9"), "warning")

    def test_l10_negation_warning(self):
        checks = self._checks(self._run_crs(CRS_L10_NEGATION))
        self.assertEqual(checks.get("L10"), "warning")

    def test_l11_bad_axis_warning(self):
        checks = self._checks(self._run_crs(CRS_L11_BAD_AXIS))
        self.assertEqual(checks.get("L11"), "warning")

    def test_l11_placeholder_axis_excluded(self):
        checks = self._checks(self._run_crs(CRS_L11_PLACEHOLDER_AXIS))
        self.assertNotIn("L11", checks)

    def test_l12_h7_heading_error(self):
        # 新体系では H7 見出し（#######）は使用しない。旧構文の残存を検出する
        checks = self._checks(self._run_crs(CRS_L12_H7_HEADING))
        self.assertEqual(checks.get("L12"), "error")

    def test_clean_crs_has_no_h7(self):
        # CRS_CLEAN（新体系）に H7 が残っていないこと（L12 が発火しない）
        self.assertNotIn("L12", self._checks(self._run_crs(CRS_CLEAN)))

    def test_l13_ur_sr_sp_without_cr_prefix_error(self):
        # CR プレフィクスを欠く UR 見出し（`#### UR-001`）を黙殺せず error 化する（fail-loud fire）
        result = self._run_crs(CRS_L13_UR_NO_CR)
        checks = self._checks(result)
        self.assertEqual(checks.get("L13"), "error")
        # 黙って消えず ident が報告される
        l13_ids = [it["id"] for it in result["crs"]["issues"] if it["check"] == "L13"]
        self.assertIn("UR-001", l13_ids)

    def test_l13_sp_item_without_cr_prefix_error(self):
        # CR プレフィクスを欠く SP 項目（`- **SP-001-001.001**：`）を error 化する（fail-loud fire）
        result = self._run_crs(CRS_L13_SP_NO_CR)
        checks = self._checks(result)
        self.assertEqual(checks.get("L13"), "error")
        l13_ids = [it["id"] for it in result["crs"]["issues"] if it["check"] == "L13"]
        self.assertIn("SP-001-001.001", l13_ids)


# ── ANA §0 degraded mode 注記チェック（A1）用フィクスチャ ──────────────────────

ANA_DEGRADED_SOURCE_WITH_NOTE = """# ANA

## 0. 参照した既存ドキュメント

承認済み知識ハブへの昇格が未完了のため、作業中の最新仕様置き場（`latest-specs/`）から直接参照（degraded mode）

| 出典ファイル | 種別 | 状態 | 今回の要求に関係する内容の要約 |
|---|---|---|---|
| /ws/xddp/latest-specs/device-svc/sensor-reader/spec.md | 仕様 | 参照済 | 関連あり |

## 1. 要求の整理

本文
"""

ANA_DEGRADED_SOURCE_MISSING_NOTE = """# ANA

## 0. 参照した既存ドキュメント

| 出典ファイル | 種別 | 状態 | 今回の要求に関係する内容の要約 |
|---|---|---|---|
| /ws/xddp/latest-specs/device-svc/sensor-reader/spec.md | 仕様 | 参照済 | 関連あり |

## 1. 要求の整理

本文
"""

ANA_NORMAL_SOURCE_NO_NOTE = """# ANA

## 0. 参照した既存ドキュメント

| 出典ファイル | 種別 | 状態 | 今回の要求に関係する内容の要約 |
|---|---|---|---|
| /ws/baseline_docs/device-svc/specs/sensor-reader/spec.md | 仕様 | 参照済 | 関連あり |

## 1. 要求の整理

本文
"""

ANA_NO_SECTION0 = """# ANA

## 1. 要求の整理

本文
"""

ANA_NONE_MODE = """# ANA

## 0. 参照した既存ドキュメント

参照なし（初回 CR）

## 1. 要求の整理

本文
"""

ANA_DEGRADED_SOURCE_WITH_SPACED_NOTE = """# ANA

## 0. 参照した既存ドキュメント

承認済み知識ハブへの昇格が未完了のため、作業中の最新仕様置き場から直接参照（degraded  mode）

| 出典ファイル | 種別 | 状態 | 今回の要求に関係する内容の要約 |
|---|---|---|---|
| /ws/xddp/latest-specs/device-svc/sensor-reader/spec.md | 仕様 | 参照済 | 関連あり |

## 1. 要求の整理

本文
"""

# 要約列（テーブル本体、テーブル直前の注記段落の外）に "degraded mode" という語がそのまま
# （半角スペース区切りのみで）出現するケース。_crs_normalize は空白類のみを除去するため、
# 探索範囲をセクション全体のままにすると（旧設計）この行も「注記あり」と誤って判定してしまう
# （false negative）。探索範囲をテーブル直前の段落に限定した新設計であれば、この行は無視され
# 正しく「注記なし」として検出される。この差を検証することが本フィクスチャの目的であるため、
# "degraded" と "mode" の間に日本語の助詞など、正規化後も連結を妨げる文字を挟んではならない。
ANA_DEGRADED_SOURCE_MARKER_ONLY_IN_SUMMARY_COLUMN = """# ANA

## 0. 参照した既存ドキュメント

| 出典ファイル | 種別 | 状態 | 今回の要求に関係する内容の要約 |
|---|---|---|---|
| /ws/xddp/latest-specs/device-svc/sensor-reader/spec.md | 仕様 | 参照済 | 旧仕様（degraded mode）からの移行に関連 |

## 1. 要求の整理

本文
"""


class AnaLintTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run_ana(self, content, doc_type="ANA"):
        p = self.root / "ANA.md"
        p.write_text(content, encoding="utf-8")
        parser = mod.build_parser()
        args = parser.parse_args(["--file", str(p), "--doc-type", doc_type])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue())

    def test_degraded_source_with_note_no_issue(self):
        result = self._run_ana(ANA_DEGRADED_SOURCE_WITH_NOTE)
        self.assertTrue(result["ana"]["applicable"])
        self.assertEqual(result["ana"]["issues"], [])

    def test_degraded_source_missing_note_flagged(self):
        result = self._run_ana(ANA_DEGRADED_SOURCE_MISSING_NOTE)
        issues = result["ana"]["issues"]
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["check"], "A1")
        self.assertEqual(issues[0]["level"], "error")

    def test_normal_source_no_note_required(self):
        result = self._run_ana(ANA_NORMAL_SOURCE_NO_NOTE)
        self.assertEqual(result["ana"]["issues"], [])

    def test_missing_section0_flagged(self):
        result = self._run_ana(ANA_NO_SECTION0)
        issues = result["ana"]["issues"]
        self.assertEqual(len(issues), 1)
        self.assertIn("見出し", issues[0]["message"])

    def test_none_mode_no_table_no_issue(self):
        result = self._run_ana(ANA_NONE_MODE)
        self.assertEqual(result["ana"]["issues"], [])

    def test_whitespace_variant_marker_recognized(self):
        result = self._run_ana(ANA_DEGRADED_SOURCE_WITH_SPACED_NOTE)
        self.assertEqual(result["ana"]["issues"], [])

    def test_marker_words_in_summary_column_not_treated_as_note(self):
        # 要約列の自由記述に「degraded」「mode」に相当する語が偶発的に現れても、
        # 注記段落（テーブル直前）を対象範囲としているため、注記なしとして正しく検出される
        result = self._run_ana(ANA_DEGRADED_SOURCE_MARKER_ONLY_IN_SUMMARY_COLUMN)
        issues = result["ana"]["issues"]
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["check"], "A1")

    def test_degraded_source_relative_path_flagged(self):
        content = """# ANA

## 0. 参照した既存ドキュメント

| 出典ファイル | 種別 | 状態 | 今回の要求に関係する内容の要約 |
|---|---|---|---|
| latest-specs/device-svc/sensor-reader/spec.md | 仕様 | 参照済 | 関連あり |

## 1. 要求の整理

本文
"""
        result = self._run_ana(content)
        issues = result["ana"]["issues"]
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["check"], "A1")

    def test_degraded_source_relative_path_with_note_no_issue(self):
        content = """# ANA

## 0. 参照した既存ドキュメント

承認済み知識ハブへの昇格が未完了のため、作業中の最新仕様置き場（`latest-specs/`）から直接参照（degraded mode）

| 出典ファイル | 種別 | 状態 | 今回の要求に関係する内容の要約 |
|---|---|---|---|
| latest-specs/device-svc/sensor-reader/spec.md | 仕様 | 参照済 | 関連あり |

## 1. 要求の整理

本文
"""
        self.assertEqual(self._run_ana(content)["ana"]["issues"], [])

    def test_not_applicable_for_other_doc_type(self):
        result = self._run_ana(ANA_DEGRADED_SOURCE_MISSING_NOTE, doc_type="CRS")
        self.assertFalse(result["ana"]["applicable"])
        self.assertNotIn("issues", result["ana"])


if __name__ == "__main__":
    unittest.main()
