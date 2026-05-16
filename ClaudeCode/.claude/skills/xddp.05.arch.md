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

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Build `REPOS_MAP` (repo name → path).
Let `REPOS_KEYS` = list of all repository names. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).

Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.

Identify `AFFECTED_REPOS`: read CRS "1.5 影響リポジトリ" section if present; otherwise use REPOS_KEYS.
Let `HAS_CROSS` = (IS_MULTI and len(AFFECTED_REPOS) ≥ 2 and `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` exists).

## Step 0: Reference Past DSNs from DOCS_DIR

For each `{repo}` in `AFFECTED_REPOS`:
1. Let `DESIGN_DIR` = `{DOCS}/{repo}/design/`.
2. If `{DESIGN_DIR}` exists:
   a. Read `{DOCS}/AI_INDEX.md` to find past DSN list for `{repo}`.
   b. Load up to 3 most recent DSN files related to changed components.
3. If `{DOCS}/cross/design/` exists: also load up to 2 most recent DSN-*-cross.md files (past cross-repo design decisions).
4. Record loaded references in DSN "referenced past design documents" section.

## Step 0.5: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 6 (実装方式検討) → 🔄 進行中, 詳細ステップ → `Step A: DSN生成中`, today. Write back.
If `IS_MULTI`, append per-repo progress table for step 6 similar to step 4 table.

## Step A0: Reference Lessons Learned Log

If `{XDDP_DIR}/lessons-learned.md` exists, read it.
Focus on entries tagged `#方式検討` `#設計` `#リスク` `#依存関係` for `LESSONS_CONTEXT`.

## Step A-cross: Generate cross/DSN (API-first principle — only when HAS_CROSS = true)

**API-first principle:** Establish the interface contract (cross/DSN) before per-repo approach design.

Read `~/.claude/templates/xddp.arch.rules.md` to get `ARCH_RULES`.
Read `{XDDP_DIR}/project-steering.md` (shared) and `{XDDP_DIR}/project-steering-cross.md` (if exists) as `CROSS_STEERING_CONTEXT`.

Generate `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md` (write directly, not via agent):
- Read `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`
- Read `{DOCS}/cross/design/` (past cross-repo design docs, if exists)
- Content must include:
  - Section 2: クロスリポジトリ実装方式（how inter-repo interfaces will be implemented）
  - Section 3: インタフェース設計（API signatures, message schemas, shared types — concrete enough for CHD）
  - Section 4: 実装依存順序（which repo's changes must be built first）
  - Section 5: リスクと軽減策

If cross/SPO does not exist → skip this step.

## Step A: Generate per-repo Architecture Memos

Read `~/.claude/templates/xddp.arch.rules.md` to get `ARCH_RULES`.

For each `{repo}` in `AFFECTED_REPOS`:

Read `{XDDP_DIR}/project-steering.md` (shared) + `{XDDP_DIR}/project-steering-{repo}.md` (if exists) as `STEERING_CONTEXT`.

**Agent tool** `subagent_type=xddp-architect-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
SPO_MODULES_DIR: {CR_PATH}/04_specout/{repo}/modules/
TEMPLATE_FILE: ~/.claude/templates/05_design-approach-memo-template.md
OUTPUT_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
TODAY: {TODAY}
LESSONS_CONTEXT: {entries tagged #方式検討 #設計 #リスク #依存関係; empty if none}
STEERING_CONTEXT: {STEERING_CONTEXT}
ADDITIONAL_REFS: {CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md (pass if exists — must conform to interface contract)
PAST_CROSS_DESIGN_DIR: {DOCS}/cross/design/ (pass if exists)
ALTERNATIVES_TASK: {pass ARCH_RULES content as-is}
```

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.DSN` rounds)

Update `{CR_PATH}/progress.md` step 6 詳細ステップ → `Step B: AIレビュー中`.
Read `REVIEW_MAX_ROUNDS.DSN` (default: 2). Set `max_rounds` = that value.

For each `{repo}` in `AFFECTED_REPOS`:

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: DSN
   TARGET_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/{repo}/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit.
   - Issues found, `round < max_rounds` → use **Agent tool** `subagent_type=xddp-architect-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     REPO_NAME: {repo}
     OUTPUT_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
     REVIEW_FILE: {CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = max_rounds`, issues remain → append warning to review file.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 6 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
{for each repo in AFFECTED_REPOS:}
> - {repo}: `{CR_PATH}/05_architecture/{repo}/DSN-{CR}.md`
>   - AIレビュー: `{CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md`
{if HAS_CROSS:}
> - cross: `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} arch`（対象リポジトリを指定）
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。

Wait for user to confirm.

If the user made any changes:
- Run one final AI review pass per repo (same as Step B, `REVIEW_ROUND = last_round + 1`).

## Step C: Feed Architecture Decision Back to CRS

Update `{CR_PATH}/progress.md` step 6 状態 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

Read all per-repo DSN files and cross/DSN (if exists). Identify items not yet in CRS.

If there are changes:
**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
CHD_FEEDBACK: (list of new constraints, NF requirements, interface specs from adopted approaches)
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

## Step E: Update progress.md
Step 6 (実装方式検討) → ✅ 完了, 詳細ステップ → `-`. Next command → `/xddp.06.design {CR}`

## Step F: Report in Japanese

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.05.arch.md`.
