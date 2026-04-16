---
description: CRS Markdown から USDM 形式の Excel を生成する（UR-017/018/020）。「ExcelファイルをCRSから生成して」「変更要求仕様書のExcelを出力して」などで起動する。
---

You are executing **XDDP CRS → Excel Generation** (Markdown → Excel).

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = first token (e.g. `CR-2026-001`).
Let `CRS_PATH` = `{CR}/03_change-requirements/CRS-{CR}.md`
Let `OUT_PATH`  = `{CR}/03_change-requirements/CRS-{CR}.xlsx`

---

## 1. Read the CRS Markdown

Read `CRS_PATH` and parse the full USDM 3-layer hierarchy:
- `### UR-x` / `### UR-NF-x` → UR level
- `#### SR-x-y` / `#### SR-NF-x-y` → SR level
- `##### SP-x-y.z` / `##### SP-NF-x-y.z` → SP level

For each item extract:
- **UR**: id, title, reason (「**理由：**」行)
- **SR**: id, title, reason
- **SP**: id, title, Before (「**Before：**」行), After (「**After：**」行)

Also parse the 変更履歴 table.

---

## 2. Generate Excel using the standard format

Use Python (`openpyxl`) to generate the Excel file.
Use the helper library at `ClaudeCode/.claude/templates/crs_excel_generator.py`
(copy the functions as needed, or `import` if the path is accessible).

### Excel column layout (6 columns: A–F)

| Row type     | A            | B      | C          | D                    | E              | F  |
|-------------|--------------|--------|------------|----------------------|----------------|----|
| **Header**  | レベル         | ID     | 内容        | 理由・説明 / Before・After |                |    |
| **UR**      | 【ユーザ要求】 | UR-x   | UR title   | UR reason            |                |    |
| **SR**      | 【SR】        | *(空)* | SR-x-y     | SR title             | SR reason      |    |
| **SP title**| *(空)*        | *(空)* | SP title   | *(空)*               | *(空)*         |    |
| **SP Before**| 【仕様】     | *(空)* | SP-x-y.z   | ■ Before             | Before content |    |
| **SP After** | *(空)*       | *(空)* | *(空)*     | ■ After              | After content  |    |

### Row heights
- Header: 20
- UR / SR rows: 40
- SP title row: auto (None)
- SP Before / After rows: 45

### Column widths
A=14, B=13, C=32, D=48, E=37.5, F=10

### Colors (fgColor hex)
| 行種別        | カラー    |
|-------------|---------|
| Header      | 4472C4  |
| UR          | D9E1F2  |
| SR          | E7E6E6  |
| SP title    | F5F5F5  |
| SP Before   | FFF2CC  |
| SP After    | E2EFDA  |

### Font
- Header: bold=True, color=FFFFFF
- UR / SR: bold=True, color=000000
- SP rows: bold=False, color=000000

### Alignment
- All cells: `horizontal='left'`, `vertical='top'`, `wrap_text=True`, `indent=0`

### Border
- All cells: thin border, color=BBBBBB

---

## 3. Write the 変更履歴 sheet

Second sheet named「変更履歴」with columns: 版数, 日付, 変更者, 変更内容.
Same header style (4472C4). Data rows use F5F5F5.

---

## 4. Save and report

Save to `OUT_PATH`.
Report in Japanese: how many UR/SR/SP were written, and the output path.
