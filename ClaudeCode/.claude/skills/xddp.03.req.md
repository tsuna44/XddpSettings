---
description: XDDP フェーズ1: 変更要求仕様書（CRS）を作成し、AIレビュー→修正ループを実施する。「変更要求仕様書を作って」「CRSを作成して」などで起動する。
---

You are orchestrating **XDDP Step 03 — Create Change Requirements Specification**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date (YYYY-MM-DD).

## Step 0: Mark In-Progress
Read `{CR}/progress.md`. Set step 3 (変更要求仕様書作成) → 🔄 進行中, 詳細ステップ → `Step A: CRS生成中`, today. Write back.

## Step A: Generate CRS

Use the **Agent tool** with `subagent_type=xddp-spec-writer-agent` and pass:
```
CR_NUMBER: {CR}
MODE: create
REQUIREMENTS_DIR: {CR}/01_requirements/
ANA_FILE: {CR}/02_analysis/ANA-{CR}.md
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
TEMPLATE_FILE: ~/.claude/templates/03_change-req-spec-template.md
TODAY: {TODAY}
AUTHOR_NOTE: 初版作成
```

## Step B: Review Loop (max 5 iterations)

Update `{CR}/progress.md` step 3 詳細ステップ → `Step B: AIレビュー中`.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ 5`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: CRS
   TARGET_FILE: {CR}/03_change-requirements/CRS-{CR}.md
   REFERENCE_FILES: [{CR}/01_requirements/ (all .md), {CR}/02_analysis/ANA-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR}/review/03_change-requirements-review.md
   ```

2. Read review file.
   - No 🔴/🟡 → `issues_remain = false`, exit.
   - 🔴/🟡 found, `round < 5` → use **Agent tool** `subagent_type=xddp-spec-writer-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     MODE: fix
     CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
     REVIEW_FILE: {CR}/review/03_change-requirements-review.md
     TODAY: {TODAY}
     AUTHOR_NOTE: レビュー指摘修正 (round {round})
     ```
     Increment `round`.
   - `round = 5`, issues remain → append "⚠️ 未解決の重大指摘あり。人間の判断が必要です。" to review file.

## Step B2: Human Review Gate

Update `{CR}/progress.md` step 3 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR}/03_change-requirements/CRS-{CR}.md`
> - AIレビュー結果: `{CR}/review/03_change-requirements-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} req`
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。
> 変更がなければそのまま「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes (edited the file or ran `/xddp.revise`):
- Run one final AI review pass using **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: CRS
  TARGET_FILE: {CR}/03_change-requirements/CRS-{CR}.md
  REFERENCE_FILES: [{CR}/01_requirements/ (all .md), {CR}/02_analysis/ANA-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR}/review/03_change-requirements-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Generate Excel Output (UR-016)

Update `{CR}/progress.md` step 3 状態 → 🔄 進行中, 詳細ステップ → `Step C: Excel生成中`.

Read `{CR}/03_change-requirements/CRS-{CR}.md` and generate `{CR}/03_change-requirements/CRS-{CR}.xlsx` using Bash/Python.

Use the following procedure:
1. Check if `openpyxl` is available: run `python3 -c "import openpyxl" 2>/dev/null || pip install openpyxl -q`.
   - If installation fails (e.g. offline/proxy environment): warn the user and skip Excel generation. Do NOT silently continue.
2. Generate a safe temp file path: `TMPFILE=$(mktemp /tmp/crs_to_excel_XXXXXX.py)`. Write a Python script to `$TMPFILE` that:
   - Reads the CRS Markdown and parses the UR/SR/SP hierarchy plus document-level sections
   - Creates a workbook with one sheet: `変更要求仕様書`
   - Header row (16 columns):
     `行種別` | `カテゴリ` | `要求ID` | `要求` | `ステータス` | `懸念・検討事項` | `理由` | `説明` | `要求グループ名` | `システム要求ID` | `システム要求` | `仕様グループ名` | `仕様ID` | `Before` | `After` | `備考`
   
   **UR/SR/SP rows (Section 2):**
   - For each UR-X section:
     - Extract category from `#### カテゴリ：{name}` heading
     - Parse `##### UR-X ...` heading; extract `ステータス` and `懸念・検討事項` from its body
     - Fill UR row: `UR` | Category | UR-X | {要求文} | {ステータス} | {懸念・検討事項} | {理由} | {説明} | | | | | | | |
     - For each `###### 要求グループ：{name}` subsection:
       - Record group name (carries to SR/SP rows)
       - For each `###### SR-X-Y ...` (SR) subsection:
         - Parse ID, `ステータス`, `懸念・検討事項` from its body
         - Fill SR row: `SR` | | SR-X-Y | {要求文} | {ステータス} | {懸念・検討事項} | {理由} | {説明} | {要求グループ名} | | | | | | |
         - For each `####### 仕様グループ：{name}` sub-subsection:
           - Record group name
           - For each `####### SP-X-Y.Z ...` (SP) heading:
             - Parse ID, `ステータス`, `懸念・検討事項`, Before, After, 備考 from its body
             - Fill SP row: `SP` | | | | {ステータス} | {懸念・検討事項} | | | | | | {仕様グループ名} | SP-X-Y.Z | {before_text} | {after_text} | {備考}
   
   **未決事項 rows (Section 5):**
   - Parse `## 5. 未決事項` table rows
   - For each row: `未決事項` | | {項目名} | {内容} | | | | | | | | | | | | {対応期限}
   
   **提案メモ rows (Section 6):**
   - Parse `## 6. 気づき・提案メモ` table rows
   - For each row: `提案メモ` | | {種別} | {内容} | | | | | | | | | | | | {対応方針}
   
   - Apply column widths; light-blue fill for header row; `行種別` column values use color-coding:
     - `UR`: white, `SR`: light-grey, `SP`: lighter-grey
     - `未決事項`: light-yellow, `提案メモ`: light-green
   - Saves to `{CR}/03_change-requirements/CRS-{CR}.xlsx`
3. Run `python3 $TMPFILE && rm -f $TMPFILE`.
4. Confirm the file was created. On error, report the error message prominently and inform the user that Excel output (UR-016) is missing.

> **保守メモ（Excel生成）:** 同じロジックが `xddp.04.specout` Step C と `xddp.06.design` Step D でも使われる。この手順を変更した場合は必ずそれらのファイルの参照コメントと整合していることを確認すること。

## Step D: Update progress.md
Step 3 → ✅ 完了, 詳細ステップ → `-`. Next command → `/xddp.04.specout {CR}`

## Step E: Report in Japanese

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.03.req.md` の要約も合わせて更新すること。
