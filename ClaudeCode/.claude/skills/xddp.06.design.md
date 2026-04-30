---
description: XDDP フェーズ3: 変更設計書（CHD）を作成し、AIレビュー→修正ループ＋変更要求仕様書へのフィードバックを実施する。「変更設計書を作って」「設計書を書いて」などで起動する。
---

You are orchestrating **XDDP Step 06 (process steps 07-08) — Change Design Document + CRS Feedback**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

Read `xddp.config.md` (project root) and extract `XDDP_DIR` (default: `.` if the key is absent). Let `CR_PATH` = `{XDDP_DIR}/{CR}`.

## Step 0: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 7 (変更設計書作成) → 🔄 進行中, 詳細ステップ → `Step A: CHD生成中`, today. Write back.

## Step A: Generate Change Design Document

Read `~/.claude/templates/xddp.06.rules.md` to get `DESIGN_RULES`.
If `{XDDP_DIR}/project-steering.md` exists, read it to get `STEERING_CONTEXT`.

**Agent tool** `subagent_type=xddp-designer-agent`:
```
CR_NUMBER: {CR}
DSN_FILE: {CR_PATH}/05_architecture/DSN-{CR}.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR_PATH}/04_specout/SPO-{CR}.md
SPO_MODULES_DIR: {CR_PATH}/04_specout/modules/
TEMPLATE_FILE: ~/.claude/templates/06_change-design-document-template.md
OUTPUT_FILE: {CR_PATH}/06_design/CHD-{CR}.md
TODAY: {TODAY}
STEERING_CONTEXT: {project-steering.md の内容。なければ空}
DESIGN_TASK: {DESIGN_RULES の内容をそのまま渡す}
```

Check for scale warning (>500 lines changed). If present, relay to user.

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.CHD` rounds)

Update `{CR_PATH}/progress.md` step 7 詳細ステップ → `Step B: AIレビュー中`.

Read `xddp.config.md` (project root). Extract `REVIEW_MAX_ROUNDS.CHD` (default: 2 if key absent). Set `max_rounds` = that value.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: CHD
   TARGET_FILE: {CR_PATH}/06_design/CHD-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/review/06_design-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit loop.
   - Issues found, `round < max_rounds` → use **Agent tool** `subagent_type=xddp-designer-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     OUTPUT_FILE: {CR_PATH}/06_design/CHD-{CR}.md
     REVIEW_FILE: {CR_PATH}/review/06_design-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = max_rounds`, issues remain → append warning to review file.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 7 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR_PATH}/06_design/CHD-{CR}.md`
> - AIレビュー結果: `{CR_PATH}/review/06_design-review.md`
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
  TARGET_FILE: {CR_PATH}/06_design/CHD-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/SPO-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/review/06_design-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Feed Design Results Back to CRS

Update `{CR_PATH}/progress.md` step 7 状態 → 🔄 進行中, step 8 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

Read `{CR_PATH}/06_design/CHD-{CR}.md`. Identify any new constraints, interface specs, or error conditions not yet in the CRS. If found:

**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: (not needed here, pass empty)
CHD_FEEDBACK: (list the new items found)
TODAY: {TODAY}
AUTHOR_NOTE: 設計フィードバックを反映。SP・影響範囲更新。
```

## Step D: Regenerate CRS Excel (UR-016)

Step C で CRS を更新した場合のみ実施。

**Excel生成は `xddp.md2excel` スキルに委譲する。**

Use the **Agent tool** with the `xddp.md2excel` skill logic, passing:
```
CR_NUMBER: {CR}
```

> **設計方針:** Excel フォーマットの唯一の定義は `~/.claude/skills/xddp.md2excel.md` と `~/.claude/templates/crs_excel_generator.py` にある。
> フォーマットを変更する場合は xddp.md2excel.md と crs_excel_generator.py のみを修正すること。

## Step E: Update progress.md
Step 7 (変更設計書作成) → ✅ 完了, 詳細ステップ → `-`.
Step 8 (変更要求仕様書フィードバック) → ✅ 完了, 詳細ステップ → `-`.
Next command → `/xddp.07.code {CR}`

## Step F: Report in Japanese

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.06.design.md` の要約も合わせて更新すること。
