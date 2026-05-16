---
description: 人が編集したExcel形式の変更要求仕様書をMarkdownに変換する（UR-017/019/020）。「ExcelをMarkdownに変換して」「Excel仕様書を取り込んで」などで起動する。
---

You are executing **XDDP Excel → Markdown Conversion** (UR-017, UR-019, UR-020).

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) [EXCEL_FILE_PATH]
- CR_NUMBER: optional; auto-detected from XDDP_DIR if omitted
- EXCEL_FILE_PATH: optional; searched in CR_PATH/03_change-requirements/ if omitted

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `EXCEL_PATH` = first token of `REST_ARGS`.

(xddp.config.md lookup done in xddp.common.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

If EXCEL_PATH omitted: search for `*.xlsx` or `*.xls` in `{CR_PATH}/03_change-requirements/`.

## 1. Read the Excel file
Use Bash to convert the Excel to text/CSV if needed (e.g., `python3 -c "import openpyxl; ..."` or similar available tool). Read the resulting data.

## 2. Parse USDM structure
The Excel follows USDM table structure (UR-037):
- Columns: カテゴリ名・記号, 要求, 要求ID, 理由, 説明, 仕様グループ名, 仕様ID
- After each 仕様 row: `before` row and `after` row (UR-038)
- Each row has 更新日 and 更新者 cells (UR-040)

Parse all rows and reconstruct the 3-layer hierarchy: UR → SR → SP.

## 3. Detect changes from previous Markdown CRS
Read the existing `{CR_PATH}/03_change-requirements/CRS-{CR}.md` (if it exists).
Identify additions, modifications, and deletions made by the human in Excel.
Log each change found.

## 4. Update CRS Markdown
Apply all detected changes to `{CR_PATH}/03_change-requirements/CRS-{CR}.md`:
- New requirements → add UR/SR/SP with correct IDs.
- Modified specs → update Before/After content.
- Deleted items → remove or mark as deleted.
- Update TM rows accordingly.
- Update 変更履歴: increment version, today's date, author "人（Excel編集）".

## 5. Report in Japanese
List every change applied (additions, modifications, deletions). Confirm the Markdown is ready for the next AI step.
