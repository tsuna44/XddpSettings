---
description: XDDP フェーズ1: 変更要求仕様書（CRS）を作成し、AIレビュー→修正ループを実施する。「変更要求仕様書を作って」「CRSを作成して」などで起動する。
---

You are orchestrating **XDDP Step 03 — Create Change Requirements Specification**.

**Arguments:** $ARGUMENTS = [CR_NUMBER]（省略可）

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md の探索は xddp.common.md 内で完了済み。WORKSPACE_ROOT・XDDP_DIR を引き続き使用する)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 3 (変更要求仕様書作成) → 🔄 進行中, 詳細ステップ → `Step A: CRS生成中`, today. Write back.

## Step A: Generate CRS

Use the **Agent tool** with `subagent_type=xddp-spec-writer-agent` and pass:
```
CR_NUMBER: {CR}
MODE: create
REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
ANA_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
TEMPLATE_FILE: ~/.claude/templates/03_change-req-spec-template.md
TODAY: {TODAY}
AUTHOR_NOTE: 初版作成
```

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.CRS` rounds)

Update `{CR_PATH}/progress.md` step 3 詳細ステップ → `Step B: AIレビュー中`.

Read the `xddp.config.md` found earlier (`{WORKSPACE_ROOT}/xddp.config.md`). Extract `REVIEW_MAX_ROUNDS.CRS` (default: 2 if key absent). Set `max_rounds` = that value.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: CRS
   TARGET_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md), {CR_PATH}/02_analysis/ANA-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md
   ```

2. Read review file.
   - No 🔴/🟡 → `issues_remain = false`, exit.
   - 🔴/🟡 found, `round < max_rounds` → use **Agent tool** `subagent_type=xddp-spec-writer-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     MODE: fix
     CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
     REVIEW_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md
     TODAY: {TODAY}
     AUTHOR_NOTE: レビュー指摘修正 (round {round})
     ```
     Increment `round`.
   - `round = max_rounds`, issues remain → append "⚠️ 未解決の重大指摘あり。人間の判断が必要です。" to review file.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 3 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR_PATH}/03_change-requirements/CRS-{CR}.md`
> - AIレビュー結果: `{CR_PATH}/03_change-requirements/review/03_change-requirements-review.md`
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
  TARGET_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md), {CR_PATH}/02_analysis/ANA-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Generate Excel Output (UR-016)

Update `{CR_PATH}/progress.md` step 3 状態 → 🔄 進行中, 詳細ステップ → `Step C: Excel生成中`.

**Excel生成は `xddp.md2excel` スキルに委譲する。**

Use the **Agent tool** with `subagent_type=` the `xddp.md2excel` skill logic, passing:
```
CR_NUMBER: {CR}
```

> **設計方針:** Excel フォーマットの唯一の定義は `~/.claude/skills/xddp.md2excel.md` と `~/.claude/templates/crs_md2excel.py` にある。
> このスキルは独自にフォーマットを定義せず、常に xddp.md2excel に委譲することで、生成経路によるフォーマット差異を防ぐ。
> フォーマットを変更する場合は xddp.md2excel.md と crs_md2excel.py のみを修正すること。

## Step D: Update progress.md
Step 3 → ✅ 完了, 詳細ステップ → `-`. Next command → `/xddp.04.specout {CR}`

## Step E: Report in Japanese

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.03.req.md` の要約も合わせて更新すること。
