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

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Build `REPOS_MAP` (repo name → path).
Let `REPOS_KEYS` = list of all repository names. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).

Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.

Identify `AFFECTED_REPOS`: read CRS "1.5 影響リポジトリ" section if present; otherwise use REPOS_KEYS.
Let `HAS_CROSS` = (IS_MULTI and `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md` exists).

## Step 0: Reference Past CHDs from DOCS_DIR

For each `{repo}` in `AFFECTED_REPOS`:
1. Let `DESIGN_DIR` = `{DOCS}/{repo}/design/`.
2. If `{DESIGN_DIR}` exists:
   a. Read `{DOCS}/AI_INDEX.md` to find past CHD list for `{repo}`.
   b. Load up to 3 CHD files related to changed components.
3. If `{DOCS}/cross/design/` exists: also load past CHD-*-cross.md files (cross-repo design patterns).

## Step 0.5: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 7 (変更設計書作成) → 🔄 進行中, 詳細ステップ → `Step A: CHD生成中`, today. Write back.

## Step A-cross: Generate cross/CHD (API-first principle — only when HAS_CROSS = true)

**API-first principle:** Establish the implementation dependency and interface change summary before per-repo CHD design.

Read `{XDDP_DIR}/project-steering-cross.md` (if exists) as `CROSS_STEERING_CONTEXT`.

Generate `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` (write directly, not via agent):
- Read `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md`
- Read `{DOCS}/cross/design/` (past cross-repo CHDs, if exists)
- Content must include:

### 実装依存関係

| 提供リポジトリ | 消費リポジトリ | インタフェース | 実装順序 |
|---|---|---|---|
| （例）repo-a | repo-b | POST /jobs API | repo-a → repo-b |

### インタフェース変更サマリ

| インタフェース | 変更種別 | breaking |
|---|---|---|
| （例）POST /jobs | 新規追加 | false |

Derive these tables from the cross/DSN interface design.

If cross/DSN does not exist → skip this step.

## Step A: Generate per-repo Change Design Documents

Read `~/.claude/templates/xddp.design.rules.md` to get `DESIGN_RULES`.

For each `{repo}` in `AFFECTED_REPOS`:

Read `{XDDP_DIR}/project-steering.md` (shared) + `{XDDP_DIR}/project-steering-{repo}.md` (if exists) as `STEERING_CONTEXT`.

**Agent tool** `subagent_type=xddp-designer-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
DSN_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
SPO_MODULES_DIR: {CR_PATH}/04_specout/{repo}/modules/
TEMPLATE_FILE: ~/.claude/templates/06_change-design-document-template.md
OUTPUT_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
TODAY: {TODAY}
STEERING_CONTEXT: {STEERING_CONTEXT}
ADDITIONAL_REFS: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md (pass if exists — must conform to interface contract)
PAST_CROSS_DESIGN_DIR: {DOCS}/cross/design/ (pass if exists)
DESIGN_TASK: {pass DESIGN_RULES content as-is}
```

Check for scale warning (>500 lines changed). If present, relay to user.

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.CHD` rounds)

Update `{CR_PATH}/progress.md` step 7 詳細ステップ → `Step B: AIレビュー中`.
Read `REVIEW_MAX_ROUNDS.CHD` (default: 2). Set `max_rounds` = that value.

For each `{repo}` in `AFFECTED_REPOS`:

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: CHD
   TARGET_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/{repo}/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/06_design/{repo}/review/06_design-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit loop.
   - Issues found, `round < max_rounds` → use **Agent tool** `subagent_type=xddp-designer-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     REPO_NAME: {repo}
     OUTPUT_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
     REVIEW_FILE: {CR_PATH}/06_design/{repo}/review/06_design-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = max_rounds`, issues remain → append warning to review file.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 7 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
{for each repo in AFFECTED_REPOS:}
> - {repo}: `{CR_PATH}/06_design/{repo}/CHD-{CR}.md`
>   - AIレビュー: `{CR_PATH}/06_design/{repo}/review/06_design-review.md`
{if HAS_CROSS:}
> - cross: `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} design`（対象リポジトリを指定）
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。

Wait for user to confirm.

If the user made any changes:
- Run one final AI review pass per repo (same as Step B, `REVIEW_ROUND = last_round + 1`).

## Step C: Feed Design Results Back to CRS

Update `{CR_PATH}/progress.md` step 7 状態 → 🔄 進行中, step 8 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

Read all per-repo CHD files and cross/CHD (if exists). Identify new constraints, interface specs, or error conditions not yet in CRS.

If found:
**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
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

## Step E: Update progress.md

Step 7 (変更設計書作成) → ✅ 完了, 詳細ステップ → `-`.
Step 8 (変更要求仕様書フィードバック) → ✅ 完了, 詳細ステップ → `-`.
Next command → `/xddp.07.code {CR}`

## Step F: Report in Japanese

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.06.design.md`.
