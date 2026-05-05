---
description: CRS Markdown から USDM 形式の Excel を生成する（UR-017/018/020）。「ExcelファイルをCRSから生成して」「変更要求仕様書のExcelを出力して」などで起動する。
---

You are executing **XDDP CRS → Excel Generation** (Markdown → Excel).

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = first token (e.g. `CR-2026-001`).

Find `xddp.config.md` by searching upward from cwd: check cwd first, then each parent directory in order. Let `WORKSPACE_ROOT` = the directory where the file is found. If not found at filesystem root, report "xddp.config.md が見つかりません。ワークスペースルートまたはそのサブディレクトリで実行してください。" and stop.
Extract `XDDP_DIR` (default: `xddp` if the key is absent).
Let `CRS_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.md`
Let `OUT_PATH`  = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.xlsx`

---

## 1. Read the CRS Markdown

Read `CRS_PATH` and parse the full USDM 3-layer hierarchy using a streaming (line-by-line) approach:
- `##### UR-XXX` / `##### UR-NF-XXX` → UR level  (例: `UR-001`)
- `###### SR-XXX-YYY` / `###### SR-NF-XXX-YYY` → SR level  (例: `SR-001-001`)
- `####### 仕様グループ：{name}` → update current spec-group label (do NOT emit a row; optional — may be absent)
- `####### SP-XXX-YYY.ZZZ` / `####### SP-NF-XXX-YYY.ZZZ` → SP level  (例: `SP-001-001.001`)

Spec-group handling:
- Maintain `current_spec_group = ""`, reset each time a new SR heading is encountered.
- When `####### 仕様グループ：{name}` is found, update `current_spec_group`.
- When an SP heading is found, emit its rows regardless of whether a 仕様グループ heading appeared.
- The SP title row content is `{SP title}` — the spec-group label is not written to the Excel in this 6-column format.

For each item extract:
- **UR**: id, title, reason (「**理由：**」行), explanation (「**説明：**」行), status (「**ステータス：**」行)
- **SR**: id, title, reason (「**理由：**」行), explanation (「**説明：**」行), status (「**ステータス：**」行)
- **SP**: id, title, Before (「**Before：**」行), After (「**After：**」行), status (「**ステータス：**」行), biko (「**備考：**」行), kenen (「**懸念・検討事項：**」行)
  - `biko` and `kenen` are optional — emit rows only when the field is present and non-empty.

Also parse:
- **Section 5 未決事項** table: extract rows as list of (number, title, content, deadline).
  - Skip header row and separator rows (rows where all cells are `---` or empty).
- **Section 6 気づき・提案メモ** table: extract rows as list of (number, kind, content, policy).
  - Skip header row and separator rows.
- **Section 7 変更履歴** table: for the 変更履歴 sheet.

---

## 2. Generate Excel using the standard format

Use Python (`openpyxl`) to generate the Excel file.
Use the helper library at `ClaudeCode/.claude/templates/crs_excel_generator.py`
(copy the functions as needed, or `import` if the path is accessible).

Output order on the single `変更要求仕様書` sheet:
1. Header row
2. All UR/SR/SP (functional + non-functional in document order — same sheet, no split)
3. `add_pending_section()` — 未決事項 (Section 5)
4. `add_notes_section()` — 気づき・提案メモ (Section 6)

### Excel row layout (6 columns: A–F)

UR と SR は**縦配置**（理由・説明を下の行に配置）。

| Row type        | A              | B      | C        | D                    | E              | F（ステータス）  |
|----------------|----------------|--------|----------|----------------------|----------------|----------------|
| **Header**      | レベル          | ID     | 内容      | 理由・説明 / Before・After | *(空)*    | ステータス      |
| **UR title**    | 【ユーザ要求】  | UR-x   | UR title | *(空)*               | *(空)*         | ステータス値    |
| **UR 理由**     | *(空)*         | 理由   | UR reason| *(空)*               | *(空)*         | *(空)*          |
| **UR 説明**     | *(空)*         | 説明   | UR explanation | *(空)*         | *(空)*         | *(空)*          |
| **SR title**    | 【システム要求】| *(空)* | SR-x-y   | SR title             | *(空)*         | ステータス値    |
| **SR 理由**     | *(空)*         | *(空)* | 理由      | SR reason            | *(空)*         | *(空)*          |
| **SR 説明**     | *(空)*         | *(空)* | 説明      | SR explanation       | *(空)*         | *(空)*          |
| **SP title**    | *(空)*         | *(空)* | SP title | *(空)*               | *(空)*         | *(空)*          |
| **SP Before**   | 【仕様】        | *(空)* | SP-x-y.z | ■ Before            | Before content | ステータス値    |
| **SP After**    | *(空)*         | *(空)* | *(空)*   | ■ After              | After content  | *(空)*          |
| **SP 備考**     | *(空)*         | *(空)* | *(空)*   | ■ 備考               | 備考 content   | *(空)* *(備考が空の場合は行を省略)* |
| **SP 懸念**     | *(空)*         | *(空)* | *(空)*   | ■ 懸念・検討事項      | 懸念 content   | *(空)* *(懸念が空の場合は行を省略)* |
| **未決事項HDR** | ■ 未決事項     | #      | 項目     | 内容                 | 対応期限        | *(空)* *(Section 5の直前に1行)* |
| **未決事項**    | *(空)*         | Q#     | 項目名   | 内容                 | 対応期限        | *(空)*          |
| **気づきHDR**   | ■ 気づき・提案メモ | #   | 種別     | 内容                 | 対応方針        | *(空)* *(Section 6の直前に1行)* |
| **気づき**      | *(空)*         | #      | 種別     | 内容                 | 対応方針        | *(空)*          |

### Row heights
- Header: 20
- UR title / SR title rows: 40
- UR 理由・説明 / SR 理由・説明: auto (None)
- SP title row: auto (None)
- SP Before / After rows: 45
- SP 備考 / 懸念 rows: auto (None)
- 未決事項ヘッダ / 気づきヘッダ: 20
- 未決事項データ / 気づきデータ: auto (None)

### Column widths
A=14, B=13, C=32, D=48, E=37.5, F=18（ステータス）

### Colors (fgColor hex)
| 行種別              | カラー    |
|-------------------|---------|
| Header            | 4472C4  |
| UR                | D9E1F2  |
| SR                | E7E6E6  |
| SP title          | F5F5F5  |
| SP Before         | FFF2CC  |
| SP After          | E2EFDA  |
| SP 備考           | FFF2CC  |
| SP 懸念・検討事項  | FCE4D6  |
| 未決事項ヘッダ     | BDD7EE  |
| 未決事項データ     | DDEBF7  |
| 気づきヘッダ       | C6EFCE  |
| 気づきデータ       | EBF1DE  |

### Font
- Header: bold=True, color=FFFFFF
- UR / SR: bold=True, color=000000
- SP rows: bold=False, color=000000

### Alignment
- All cells: `horizontal='left'`, `vertical='top'`, `wrap_text=True`, `indent=0`
- SP title row only: `wrap_text=False`（改行させない）

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
