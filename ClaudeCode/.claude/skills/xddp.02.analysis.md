---
description: XDDP フェーズ1: 要求分析メモを生成し、別コンテキストでAIレビュー→修正ループを実施する。「要求分析して」「ANA作って」などで起動する。
---

You are orchestrating **XDDP Step 02 — Requirements Analysis**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS (trim whitespace). Let `TODAY` = today's date (YYYY-MM-DD).

## Step 0: Mark In-Progress
Read `{CR}/progress.md`. Set step 2 (要求分析・整理) → 🔄 進行中, today. Write back.

## Step A: Generate Analysis Memo

Use the **Agent tool** with `subagent_type=xddp-analyst-agent` and pass:
```
CR_NUMBER: {CR}
REQUIREMENTS_DIR: {CR}/01_requirements/
TEMPLATE_FILE: ~/.claude/templates/02_req-analysis-memo-template.md
OUTPUT_FILE: {CR}/02_analysis/ANA-{CR}.md
TODAY: {TODAY}
```

Wait for the agent to complete and confirm the file was created.

## Step B: Review Loop (max 5 iterations)

Initialize: `round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ 5`:

1. Use the **Agent tool** with `subagent_type=xddp-reviewer` and pass:
   ```
   DOCUMENT_TYPE: ANA
   TARGET_FILE: {CR}/02_analysis/ANA-{CR}.md
   REFERENCE_FILES: [{CR}/01_requirements/ (all .md files)]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR}/review/02_analysis-review.md
   ```

2. Read `{CR}/review/02_analysis-review.md`.
   - If no 🔴 or 🟡 issues → set `issues_remain = false`, exit loop.
   - If 🔴/🟡 issues found and `round < 5` → use **Agent tool** `subagent_type=xddp-analyst-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     REQUIREMENTS_DIR: {CR}/01_requirements/
     OUTPUT_FILE: {CR}/02_analysis/ANA-{CR}.md
     REVIEW_FILE: {CR}/review/02_analysis-review.md
     TODAY: {TODAY}
     ```
     Increment `round`, continue loop.
   - If `round = 5` and issues remain → append "⚠️ 未解決の重大指摘あり。人間の判断が必要です。" to the review file. Exit loop.

## Step B2: Human Review Gate

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR}/02_analysis/ANA-{CR}.md`
> - AIレビュー結果: `{CR}/review/02_analysis-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} analysis`
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。
> 変更がなければそのまま「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes (edited the file or ran `/xddp.revise`):
- Run one final AI review pass using **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: ANA
  TARGET_FILE: {CR}/02_analysis/ANA-{CR}.md
  REFERENCE_FILES: [{CR}/01_requirements/ (all .md files)]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR}/review/02_analysis-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Update progress.md
Read `{CR}/progress.md`, set step 2 → ✅ 完了, today, link `ANA-{CR}.md`.
Set next command → `/xddp.03.req {CR}`.

## Step D: Report in Japanese
Summary: review rounds completed, final issue count, next command.

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.02.analysis.md` の要約も合わせて更新すること。
