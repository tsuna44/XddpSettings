---
description: XDDP フェーズ3: 変更設計書（CHD）を作成し、AIレビュー→修正ループ＋変更要求仕様書へのフィードバックを実施する。「変更設計書を作って」「設計書を書いて」などで起動する。
---

You are orchestrating **XDDP Step 06 (process steps 07-08) — Change Design Document + CRS Feedback**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

## Step 0: Mark In-Progress
Read `{CR}/progress.md`. Set step 7 (変更設計書作成) → 🔄 進行中, today. Write back.

## Step A: Generate Change Design Document

**Agent tool** `subagent_type=xddp-designer-agent`:
```
CR_NUMBER: {CR}
DSN_FILE: {CR}/05_architecture/DSN-{CR}.md
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR}/04_specout/SPO-{CR}.md
SPO_MODULES_DIR: {CR}/04_specout/modules/
TEMPLATE_FILE: ~/.claude/templates/06_change-design-document-template.md
OUTPUT_FILE: {CR}/06_design/CHD-{CR}.md
TODAY: {TODAY}
```

Check for scale warning (>500 lines changed). If present, relay to user.

## Step B: Review Loop (max 5 iterations)

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ 5`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: CHD
   TARGET_FILE: {CR}/06_design/CHD-{CR}.md
   REFERENCE_FILES: [{CR}/03_change-requirements/CRS-{CR}.md, {CR}/04_specout/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR}/review/06_design-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit loop.
   - Issues found, `round < 5` → use **Agent tool** `subagent_type=xddp-designer-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     OUTPUT_FILE: {CR}/06_design/CHD-{CR}.md
     REVIEW_FILE: {CR}/review/06_design-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = 5`, issues remain → append warning to review file.

## Step B2: Human Review Gate

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR}/06_design/CHD-{CR}.md`
> - AIレビュー結果: `{CR}/review/06_design-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} design`
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。
> 変更がなければそのまま「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes (edited the file or ran `/xddp.revise`):
- Run one final AI review pass using **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: CHD
  TARGET_FILE: {CR}/06_design/CHD-{CR}.md
  REFERENCE_FILES: [{CR}/03_change-requirements/CRS-{CR}.md, {CR}/04_specout/SPO-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR}/review/06_design-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Feed Design Results Back to CRS

Read `{CR}/06_design/CHD-{CR}.md`. Identify any new constraints, interface specs, or error conditions not yet in the CRS. If found:

**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
SPO_FILE: (not needed here, pass empty)
CHD_FEEDBACK: (list the new items found)
TODAY: {TODAY}
AUTHOR_NOTE: 設計フィードバックを反映。SP・影響範囲更新。
```

## Step D: Regenerate CRS Excel (UR-016)

If Step C added any items to the CRS, regenerate `{CR}/03_change-requirements/CRS-{CR}.xlsx` from the updated Markdown CRS.
Follow the same Excel generation procedure as Step C (Generate Excel Output) in `xddp.03.req`.

## Step E: Update progress.md
Step 7 (変更設計書作成) → ✅ 完了.
Step 8 (変更要求仕様書フィードバック) → ✅ 完了.
Next command → `/xddp.07.code {CR}`

## Step F: Report in Japanese

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.06.design.md` の要約も合わせて更新すること。
