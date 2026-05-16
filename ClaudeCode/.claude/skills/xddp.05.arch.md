---
description: XDDP フェーズ3: 実装方式検討メモ（DSN）を作成し、AIレビュー→修正ループを実施する。「方式検討して」「実装方針を決めて」などで起動する。
---

You are orchestrating **XDDP Step 05 (process step 06) — Implementation Approach Design**.

> The implementation approach chosen here shapes build quality and maintainability for the life of this code. A poorly examined recommendation means months of rework. Orchestrate with depth — every tradeoff deserves honest comparison.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: Reference Past DSNs from DOCS_DIR

1. Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
   Read `REPO_NAME` from the `xddp.config.md` found earlier. If absent or empty, report error and stop.
   Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`. Let `DESIGN_DIR` = `{DOCS}/{REPO_NAME}/design/`.

2. If `{DESIGN_DIR}` does not exist → skip; record "no references (first CR)".

3. If `{DESIGN_DIR}` exists:
   a. Read `{DOCS}/AI_INDEX.md` to find the design document list (DSN-*.md) for `{REPO_NAME}`.
   b. If `{CR_PATH}/03_change-requirements/CRS-{CR}.md` exists,
      extract changed modules/components and prioritize past DSNs related to them.
   c. Load up to 3 DSN files (most recent, or CRS-related ones).
   d. If `{DOCS}/shared/design/patterns.md` exists, read it.

4. Use the loaded content to:
   - Understand past implementation approach choices and their rationale for this decision.
   - Check alignment with existing architecture patterns.
   - Reference previously rejected approaches to avoid redundant analysis.

5. Record in the DSN document's "referenced past design documents" section the filenames read
   and a summary of the relevant insights extracted.

## Step 0.5: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 6 (実装方式検討) → 🔄 進行中, 詳細ステップ → `Step A: DSN生成中`, today. Write back.

## Step A0: Reference Lessons Learned Log

If `{XDDP_DIR}/lessons-learned.md` exists, read it.
Focus on entries tagged `#方式検討` `#設計` `#リスク` `#依存関係` to review lessons from
adopted/rejected approaches in past CRs.
If relevant insights are found, include them in `LESSONS_CONTEXT` passed to the architect-agent.

## Step A: Generate Architecture Memo

Read `~/.claude/templates/xddp.arch.rules.md` to get `ARCH_RULES`.
If `{XDDP_DIR}/project-steering.md` exists, read it to get `STEERING_CONTEXT`.

**Agent tool** `subagent_type=xddp-architect-agent`:
```
CR_NUMBER: {CR}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR_PATH}/04_specout/SPO-{CR}.md
SPO_MODULES_DIR: {CR_PATH}/04_specout/modules/
SPO_CROSS_MODULE_FILE: {CR_PATH}/04_specout/cross-module/SPO-{CR}-cross.md (if exists)
TEMPLATE_FILE: ~/.claude/templates/05_design-approach-memo-template.md
OUTPUT_FILE: {CR_PATH}/05_architecture/DSN-{CR}.md
TODAY: {TODAY}
LESSONS_CONTEXT: {entries tagged #方式検討 #設計 #リスク #依存関係 extracted from lessons-learned.md; empty if none}
STEERING_CONTEXT: {contents of project-steering.md, or empty if not found}
ALTERNATIVES_TASK: {pass ARCH_RULES content as-is}
```

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.DSN` rounds)

Update `{CR_PATH}/progress.md` step 6 詳細ステップ → `Step B: AIレビュー中`.

Read the `xddp.config.md` found earlier (`{WORKSPACE_ROOT}/xddp.config.md`). Extract `REVIEW_MAX_ROUNDS.DSN` (default: 2 if key absent). Set `max_rounds` = that value.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: DSN
   TARGET_FILE: {CR_PATH}/05_architecture/DSN-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/05_architecture/review/05_architecture-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit.
   - Issues found, `round < max_rounds` → use **Agent tool** `subagent_type=xddp-architect-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     OUTPUT_FILE: {CR_PATH}/05_architecture/DSN-{CR}.md
     REVIEW_FILE: {CR_PATH}/05_architecture/review/05_architecture-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = max_rounds`, issues remain → append warning to review file.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 6 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR_PATH}/05_architecture/DSN-{CR}.md`
> - AIレビュー結果: `{CR_PATH}/05_architecture/review/05_architecture-review.md`
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
  TARGET_FILE: {CR_PATH}/05_architecture/DSN-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/SPO-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/05_architecture/review/05_architecture-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Feed Architecture Decision Back to CRS

Update `{CR_PATH}/progress.md` step 6 状態 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

Read `{CR_PATH}/05_architecture/DSN-{CR}.md`. From the adopted approach, identify items not yet reflected in the CRS:

- Requirements/specs **made unnecessary by the adopted approach** (candidates for deletion or status change)
- **New constraints, non-functional requirements, or interface specs** revealed by the adopted approach
- **Modules or features now out of scope** due to the adopted approach

If there are **no changes, skip**. If there are changes:

**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: (not needed here, pass empty)
CHD_FEEDBACK: (list of change items based on adopted approach; distinguish deletions, additions, modifications)
TODAY: {TODAY}
AUTHOR_NOTE: 方式検討フィードバックを反映。採用方式に基づく要求・仕様の追加／削除／変更。
```

## Step D: Regenerate CRS Excel (UR-016)

Run only if CRS was updated in Step C.

**Excel generation is delegated to the `xddp.md2excel` skill.**

Use the **Agent tool** with the `xddp.md2excel` skill logic, passing:
```
CR_NUMBER: {CR}
```

> **Design policy:** The sole definition of the Excel format is in `~/.claude/skills/xddp.md2excel.md` and `~/.claude/templates/crs_md2excel.py`.
> To change the format, modify only xddp.md2excel.md and crs_md2excel.py.

## Step E: Update progress.md
Step 6 (実装方式検討) → ✅ 完了, 詳細ステップ → `-`. Next command → `/xddp.06.design {CR}`

## Step F: Report in Japanese

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.05.arch.md`.
