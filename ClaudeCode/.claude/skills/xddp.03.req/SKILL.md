---
description: XDDP フェーズ1: 変更要求仕様書（CRS）を作成し、AIレビュー→修正ループを実施する。「変更要求仕様書を作って」「CRSを作成して」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 03 — Create Change Requirements Specification**.

> The CRS you produce is the contract the entire team works from. Imprecision or missing traceability here costs weeks and erodes trust in every downstream artifact. Orchestrate with precision.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
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
TEMPLATE_FILE: ~/.claude/skills/xddp.templates/03_change-req-spec-template.md
TODAY: {TODAY}
AUTHOR_NOTE: 初版作成
```

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.CRS` rounds)

Update `{CR_PATH}/progress.md` step 3 詳細ステップ → `Step B: AIレビュー中`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: CRS
  CONFIG_KEY: REVIEW_MAX_ROUNDS.CRS
  TARGET_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md), {CR_PATH}/02_analysis/ANA-{CR}.md]
  REVIEW_OUTPUT_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md
  FIXER_AGENT: xddp-spec-writer-agent
  FIXER_PARAMS:
    CR_NUMBER: {CR}
    MODE: fix
    CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
    REVIEW_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md
    TODAY: {TODAY}
    AUTHOR_NOTE: レビュー指摘修正 (round {round})

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

**Excel generation is delegated to the `xddp.md2excel` skill.**

Let `CRS_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.md`.
Let `EXCEL_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.xlsx`.
Run via Bash: `python ~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py {CRS_PATH} {EXCEL_PATH}`
If `crs_md2excel.py` not found: tell the user to run `setup.sh`. If errors: display to user.
Report output path and UR/SR/SP counts from script stdout.

> **Design policy:** The sole definition of the Excel format is in `~/.claude/skills/xddp.md2excel.md` and `~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py`.
> This skill does not define its own format; it always delegates to xddp.md2excel to prevent format divergence by generation path.
> To change the format, modify only xddp.md2excel.md and crs_md2excel.py.
> **成果物の位置付け:** `CRS-{CR}.xlsx` は人間向け確認ツール（一時生成物）。xddp.close の DOCS_DIR 昇格対象外。

## Step D: Update progress.md
Step 3 → ✅ 完了, 詳細ステップ → `-`. Next command → `/xddp.04.specout {CR}`

## Step E: Report in Japanese

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.03.req.md`.
