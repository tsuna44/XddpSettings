---
description: 人が編集したExcel形式の変更要求仕様書をMarkdownに変換する（UR-017/019/020）。「ExcelをMarkdownに変換して」「Excel仕様書を取り込んで」などで起動する。
argument-hint: "[CR番号] [Excelファイル]"
---

You are executing **XDDP Excel → Markdown Conversion** (UR-017, UR-019, UR-020).

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) [EXCEL_FILE_PATH]
- CR_NUMBER: optional; auto-detected from XDDP_DIR if omitted
- EXCEL_FILE_PATH: optional; searched in CR_PATH/03_change-requirements/ if omitted

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `EXCEL_PATH` = first token of `REST_ARGS`.

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR, MD2EXCEL_PYTHON_BIN.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

If EXCEL_PATH omitted: search for `*.xlsx` or `*.xls` in `{CR_PATH}/03_change-requirements/`.

## 1. Read the Excel file
Run via Bash:
- `MD2EXCEL_PYTHON_BIN` が設定されている場合: `"{MD2EXCEL_PYTHON_BIN}" ~/.claude/skills/xddp.excel2md/scripts/excel_dump.py {EXCEL_PATH}`
- 未設定の場合（デフォルト）: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.excel2md/scripts/excel_dump.py {EXCEL_PATH}`

（全行をタブ区切りテキストとして標準出力へダンプする。`openpyxl` は `crs_md2excel.py` が既に依存する
ライブラリと同一のため新規依存追加ではない）。Read the resulting data.

## 2. Parse USDM structure
The Excel follows USDM table structure (UR-037):
- Columns: カテゴリ名・記号, 要求, 要求ID, 理由, 説明, 仕様グループ名, 仕様ID
- After each 仕様 row: `■ Before` row then `■ After` row (UR-038). An optional `■ 理由` row may follow
  `■ After`（SP レベルの設計判断根拠。crs_md2excel.py の往路出力と同順）, followed by optional
  `■ 備考` and `■ 懸念・検討事項` rows.
- Each row has 更新日 and 更新者 cells (UR-040)

Parse all rows and reconstruct the 3-layer hierarchy: UR → SR → SP. For each SP, map the D-column
label (`■ Before`/`■ After`/`■ 理由`/`■ 備考`/`■ 懸念・検討事項`) to the corresponding Markdown field
(`- **Before：**`/`- **After：**`/`- **理由：**`/`- **備考：**`/`- **懸念・検討事項：**`), preserving the
ステータス → Before → After → 理由 → 備考 → 懸念 order.

### 見出し体系（USDM Canonical。crs_md2excel.py（MD→Excel）と往復整合させること）
Reconstruct CRS Markdown with the following heading system (H1〜H6 のみ使用。H7 は使わない):
- カテゴリ（機能要求／非機能要求）: `### ＜{カテゴリ名}＞`（H3）
- ユーザ要求（UR）: `#### {CR番号}-UR-XXX {タイトル}`（H4。形式 B: CR 名前空間先頭。例 `CR-2026-970-UR-001`）
- 要求グループ: `##### ＜{要求グループ名}＞`（H5）
- システム要求（SR）: `###### {CR番号}-SR-XXX-YYY {タイトル}`（H6。例 `CR-2026-970-SR-001-001`）
- 仕様グループ: `**＜{仕様グループ名}＞**`（太字行。見出しではない）
- 仕様（SP）: `- **{CR番号}-SP-XXX-YYY.ZZZ**: {タイトル}`（リスト項目。属性は 2 スペースインデントの子リスト。例 `CR-2026-970-SP-001-001.001`）

Excel の ID セルは CR プレフィクス付きフル ID（形式 B）で入力されている前提。Excel から読み取った
ID をそのまま見出し・リスト項目に転記すること（CR プレフィクスを剥がしたり付け直したりしない）。
往復（`crs_md2excel.py`）で CR プレフィクス付きフル ID が保持される。

**ID行・カテゴリ属性行は出力しない:** UR・SR は ID を見出しに、SP は ID をリスト項目の先頭に保持するため、
独立した `- **ID:**` 行は UR・SR・SP のいずれにも出力しない。UR の `- **カテゴリ：**` 属性行も出力しない
（カテゴリは H3 見出し `### ＜…＞` で表現する）。

SP のリスト項目・子リスト記法（`crs_md2excel.py` が再パースできるよう完全一致させる。6 属性
`ステータス`/`Before`/`After`/`理由`/`備考`/`懸念・検討事項` を漏れなく出力し、`懸念・検討事項` の欠落に注意する）:

```
- **{CR番号}-SP-XXX-YYY.ZZZ**: {仕様タイトル}
  - **ステータス：** {ステータス}
  - **Before：** {現行動作}
  - **After：** {変更後動作}
  - **理由：** {変更理由}
  - **備考：** {補足}
  - **懸念・検討事項：** {不明点・リスク・確認が必要な内容}
```

## 3. Detect changes from previous Markdown CRS
Read the existing `{CR_PATH}/03_change-requirements/CRS-{CR}.md` (if it exists).
Identify additions, modifications, and deletions made by the human in Excel.
Log each change found.

## 4. Update CRS Markdown
Apply all detected changes to `{CR_PATH}/03_change-requirements/CRS-{CR}.md`:
- New requirements → add UR/SR/SP with correct IDs.
- Modified specs → update Before/After/理由 content.
- Deleted items → remove or mark as deleted.
- Update TM rows accordingly.
- Update 変更履歴: increment version, today's date, author "人（Excel編集）".

## 5. Report in Japanese
List every change applied (additions, modifications, deletions). Confirm the Markdown is ready for the next AI step.
