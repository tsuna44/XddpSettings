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
TEMPLATE_FILE: ~/.claude/skills/xddp.03.req/templates/03_change-req-spec-template.md
TODAY: {TODAY}
AUTHOR_NOTE: 初版作成
```

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.CRS` rounds)

Update `{CR_PATH}/progress.md` step 3 詳細ステップ → `Step B: AIレビュー中`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: CRS
  NEXT_DOCUMENT_TYPE: SPO
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
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 3

## Step B2: Human Review Gate

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Human Review Gate" with:
  CR_PATH: {CR_PATH}
  STEP_NUM: 3
  STEP_LABEL: `Step B2`
  ARTIFACTS_TEXT: |
    - 成果物: `{CR_PATH}/03_change-requirements/CRS-{CR}.md`
    - AIレビュー結果: `{CR_PATH}/03_change-requirements/review/03_change-requirements-review.md`
  REVISE_COMMAND: `/xddp.revise {CR} req`
→ let `CHANGED`.

If `CHANGED`:
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Final Review Pass" with:
  DOCUMENT_TYPE: CRS
  NEXT_DOCUMENT_TYPE: SPO
  TARGET_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md), {CR_PATH}/02_analysis/ANA-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md

## Step C: Generate Excel Output (UR-016)

Update `{CR_PATH}/progress.md` step 3 状態 → 🔄 進行中, 詳細ステップ → `Step C: Excel生成中`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Regenerate CRS Excel" with:
  CR_PATH: {CR_PATH}
  CR: {CR}

## Step D: Update progress.md
Step 3 → ✅ 完了, 詳細ステップ → `-`. Next command → `/xddp.04.specout {CR}`

## Step E: Report in Japanese
