---
description: XDDP フェーズ3: 実装方式検討メモ（DSN）を作成し、AIレビュー→修正ループを実施する。「方式検討して」「実装方針を決めて」などで起動する。
---

You are orchestrating **XDDP Step 05 (process step 06) — Implementation Approach Design**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

## Step 0: Mark In-Progress
Read `{CR}/progress.md`. Set step 6 (実装方式検討) → 🔄 進行中, today. Write back.

## Step A: Generate Architecture Memo

**Agent tool** `subagent_type=xddp-architect-agent`:
```
CR_NUMBER: {CR}
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR}/04_specout/SPO-{CR}.md
SPO_MODULES_DIR: {CR}/04_specout/modules/
SPO_CROSS_MODULE_FILE: {CR}/04_specout/cross-module/SPO-{CR}-cross.md (if exists)
TEMPLATE_FILE: ~/.claude/templates/05_design-approach-memo-template.md
OUTPUT_FILE: {CR}/05_architecture/DSN-{CR}.md
TODAY: {TODAY}
```

## Step B: Review Loop (max 5 iterations)

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ 5`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: DSN
   TARGET_FILE: {CR}/05_architecture/DSN-{CR}.md
   REFERENCE_FILES: [{CR}/03_change-requirements/CRS-{CR}.md, {CR}/04_specout/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR}/review/05_architecture-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit.
   - Issues found, `round < 5` → use **Agent tool** `subagent_type=xddp-architect-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     OUTPUT_FILE: {CR}/05_architecture/DSN-{CR}.md
     REVIEW_FILE: {CR}/review/05_architecture-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = 5`, issues remain → append warning to review file.

## Step B2: Human Review Gate

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR}/05_architecture/DSN-{CR}.md`
> - AIレビュー結果: `{CR}/review/05_architecture-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} arch`
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。
> 変更がなければそのまま「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes (edited the file or ran `/xddp.revise`):
- Run one final AI review pass using **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: DSN
  TARGET_FILE: {CR}/05_architecture/DSN-{CR}.md
  REFERENCE_FILES: [{CR}/03_change-requirements/CRS-{CR}.md, {CR}/04_specout/SPO-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR}/review/05_architecture-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Update progress.md
Step 6 (実装方式検討) → ✅ 完了. Next command → `/xddp.06.design {CR}`

## Step D: Report in Japanese

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.05.arch.md` の要約も合わせて更新すること。
