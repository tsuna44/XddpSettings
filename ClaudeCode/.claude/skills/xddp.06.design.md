---
description: XDDP フェーズ3: 変更設計書（CHD）を作成し、AIレビュー→修正ループ＋変更要求仕様書へのフィードバックを実施する。「変更設計書を作って」「設計書を書いて」などで起動する。
---

You are orchestrating **XDDP Step 06 (process steps 07-08) — Change Design Document + CRS Feedback**.

> The CHD produced here is the blueprint coders execute without asking questions. Every gap or ambiguity in the design becomes a defect in the code. Orchestrate with precision — completeness in Before/After code and confirmation items is non-negotiable.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: Reference Past CHDs from DOCS_DIR

1. Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
   Read `REPO_NAME` from the `xddp.config.md` found earlier. If absent or empty, report error and stop.
   Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`. Let `DESIGN_DIR` = `{DOCS}/{REPO_NAME}/design/`.

2. If `{DESIGN_DIR}` does not exist → skip; record "no references (first CR)".

3. If `{DESIGN_DIR}` exists:
   a. Read `{DOCS}/AI_INDEX.md` to find the design document list (CHD-*.md) for `{REPO_NAME}`.
   b. If `{CR_PATH}/05_architecture/DSN-{CR}.md` exists,
      extract changed files/classes/functions and prioritize past CHDs that modified the same components.
   c. Load up to 3 CHD files (most recent, or DSN-related ones).

4. Use the loaded content to:
   - Reference past change patterns for the same components (Before/After style and granularity).
   - Follow naming conventions and comment style used in past design documents.
   - Understand cumulative impact when the same location has been changed multiple times.

5. Record in the CHD document's "referenced past design documents" section the filenames read
   and a summary of the relevant patterns extracted.

## Step 0.5: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 7 (変更設計書作成) → 🔄 進行中, 詳細ステップ → `Step A: CHD生成中`, today. Write back.

## Step A: Generate Change Design Document

Read `~/.claude/templates/xddp.design.rules.md` to get `DESIGN_RULES`.
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
STEERING_CONTEXT: {contents of project-steering.md, or empty if not found}
DESIGN_TASK: {pass DESIGN_RULES content as-is}
```

Check for scale warning (>500 lines changed). If present, relay to user.

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.CHD` rounds)

Update `{CR_PATH}/progress.md` step 7 詳細ステップ → `Step B: AIレビュー中`.

Read the `xddp.config.md` found earlier (`{WORKSPACE_ROOT}/xddp.config.md`). Extract `REVIEW_MAX_ROUNDS.CHD` (default: 2 if key absent). Set `max_rounds` = that value.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: CHD
   TARGET_FILE: {CR_PATH}/06_design/CHD-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/06_design/review/06_design-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit loop.
   - Issues found, `round < max_rounds` → use **Agent tool** `subagent_type=xddp-designer-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     OUTPUT_FILE: {CR_PATH}/06_design/CHD-{CR}.md
     REVIEW_FILE: {CR_PATH}/06_design/review/06_design-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = max_rounds`, issues remain → append warning to review file.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 7 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR_PATH}/06_design/CHD-{CR}.md`
> - AIレビュー結果: `{CR_PATH}/06_design/review/06_design-review.md`
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
  OUTPUT_FILE: {CR_PATH}/06_design/review/06_design-review.md
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

Run only if CRS was updated in Step C.

**Excel generation is delegated to the `xddp.md2excel` skill.**

Use the **Agent tool** with the `xddp.md2excel` skill logic, passing:
```
CR_NUMBER: {CR}
```

> **Design policy:** The sole definition of the Excel format is in `~/.claude/skills/xddp.md2excel.md` and `~/.claude/templates/crs_md2excel.py`.
> To change the format, modify only xddp.md2excel.md and crs_md2excel.py.

## Step E: Update progress.md
Step 7 (変更設計書作成) → ✅ 完了, 詳細ステップ → `-`.
Step 8 (変更要求仕様書フィードバック) → ✅ 完了, 詳細ステップ → `-`.
Next command → `/xddp.07.code {CR}`

## Step F: Report in Japanese

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.06.design.md`.
