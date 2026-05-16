---
description: XDDP フェーズ4: 変更設計書に基づいてコーディングを実施し、静的検証を行う。「コーディングして」「実装して」などで起動する。
---

You are orchestrating **XDDP Step 07 (process steps 09-10) — Coding + Static Verification**.

> Code written in this step runs in production. Faithfulness to the CHD and attention to every edge case are non-negotiable. Orchestrate with discipline — a deviation here becomes a production incident.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Build `REPOS_MAP` (repo name → path).
Let `REPOS_KEYS` = list of all repository names. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).

Identify `AFFECTED_REPOS`: read CRS "1.5 影響リポジトリ" section if present; otherwise use REPOS_KEYS.
Let `HAS_CROSS` = (IS_MULTI and `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` exists).

Read `TEST_FRAMEWORK_REPOS:` if defined (repo → test framework override map).

## Step 0: Determine Implementation Order and Check for Circular Dependencies

Read `~/.claude/templates/xddp.coding.rules.md` to get `CODING_RULES`.

If `HAS_CROSS`:
  Read `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` and extract the "実装依存関係" table.

  **Circular dependency check:**
  Build a directed graph from the 実装依存関係 table (提供リポジトリ → 消費リポジトリ edges).
  Detect cycles using DFS or topological sort. If a cycle is found (e.g., repo-a → repo-b → repo-a):
  > ⛔ 循環依存が検出されました: {検出したパス（例: repo-a → repo-b → repo-a）}
  > `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` の「実装依存関係」テーブルを見直してください。
  Stop and wait for user to fix the cross/CHD.

  If no cycle: determine `IMPL_ORDER` by topological sort of the dependency graph.
  (Provider repos come before their consumers. E.g., if repo-a provides POST /jobs consumed by repo-b → implement repo-a first.)

Else:
  `IMPL_ORDER` = `AFFECTED_REPOS` in REPOS: definition order.

## Step 0.5: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 9 (コーディング) → 🔄 進行中, 詳細ステップ → `Step A: コーディング中`, today. Write back.
If `IS_MULTI`, append per-repo progress table for step 9:
```markdown
## 工程9 コーディング進捗（リポジトリ別）
| リポジトリ | 状態 | 完了日 |
|---|---|---|
{for each repo in IMPL_ORDER: | {repo} | ⏳ 未着手 | - |}
{if HAS_CROSS: | cross/検証 | ⏳ 未着手 | - |}
```

## Step A-Pre: Load Coding Quality Rules and Project Memory

Already loaded in Step 0. `CODING_RULES` and `STEERING_CONTEXT` (shared) are available.

## Step A: Implement Code Changes (in dependency order)

For each `{repo}` in `IMPL_ORDER` (sequentially — do not parallelise to respect implementation order):

Update per-repo progress table: `| {repo} | 🔄 進行中 | - |`

Read `{XDDP_DIR}/project-steering.md` (shared) + `{XDDP_DIR}/project-steering-{repo}.md` (if exists) as `STEERING_CONTEXT`.

**Agent tool** `subagent_type=xddp-coder-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CHD_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
OUTPUT_MEMO: {CR_PATH}/07_coding/CODING-{CR}-{repo}.md
TODAY: {TODAY}
CODING_RULES: {pass CODING_RULES content as-is}
STEERING_CONTEXT: {STEERING_CONTEXT}
ADDITIONAL_REFS: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md (pass if exists — interface contract reference)
```

Wait for completion. If the agent reports CHD Before/After discrepancies, relay to the user.

Update per-repo progress table: `| {repo} | ✅ 完了 | {TODAY} |`

## Step B: Static Verification (per repo)

Update `{CR_PATH}/progress.md` step 9 詳細ステップ → `Step B: 静的検証中`. Also set step 10 → 🔄 進行中.

For each `{repo}` in `IMPL_ORDER`:

**Agent tool** `subagent_type=xddp-verifier-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
CHD_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
CODING_MEMO: {CR_PATH}/07_coding/CODING-{CR}-{repo}.md
OUTPUT_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md
TODAY: {TODAY}
CODING_RULES: {pass CODING_RULES content as-is}
STEERING_CONTEXT: {STEERING_CONTEXT for this repo}
ADDITIONAL_REFS: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md (pass if exists — for interface contract verification)
```

Read the verification report.

## Step B-cross: Cross-repo Interface Verification (only when HAS_CROSS = true)

After all per-repo verification is complete, verify that the cross/CHD interface commitments were honoured.

Update per-repo progress table: `| cross/検証 | 🔄 進行中 | - |`

**Agent tool** `subagent_type=xddp-verifier-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: cross
CHD_FILE: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
CODING_MEMOS: [{CR_PATH}/07_coding/CODING-{CR}-{repo}.md for each repo in IMPL_ORDER]
OUTPUT_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}-cross.md
TODAY: {TODAY}
VERIFICATION_TASK: |
  Verify that the cross/CHD "インタフェース変更サマリ" is fully implemented:
  - "新規追加": confirm the interface was added in the provider repo's CODING memo
  - "変更": confirm the change matches the CODING memo
  - "削除": confirm the deletion was carried out
  For each mismatch, flag as NG with details.
```

Read the verification report. If NG items exist:
> ⚠️ クロスリポジトリ インタフェース検証NG: `{CR_PATH}/08_code-review/VERIFY-{CR}-cross.md` を確認してください。
> 実装とインタフェース変更サマリの不一致があります。実装を修正するか、cross/CHD を更新してください。

Update per-repo progress table: `| cross/検証 | ✅ 完了 | {TODAY} |` (even if NG — NG is handled above)

## Step C: Handle Verification Result

**If all ✅ pass (all repos + cross/ if applicable):**
- Update progress.md: step 9 (コーディング) ✅, 詳細ステップ → `-`; step 10 (静的検証) ✅, 詳細ステップ → `-`.
- Next command → `/xddp.08.test {CR}`

**If ❌ NG (any repo):**
- Read NG list and classify each:
  - **Implementation bug** (coding mistake): Fix directly in source code, then re-run Step B for that repo.
  - **Design error** (CHD itself is incorrect): DO NOT fix code. Instruct the user:
    > ❌ 静的検証NG：設計書（CHD）に誤りが検出されました。
    > `{CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md` の NG 内容を確認し、
    > `/xddp.06.design {CR}` を再実行して設計書を修正してください。
    > 設計書修正後に `/xddp.07.code {CR}` を再実行してください。
    Update progress.md step 10 → 🔁 差し戻し. Stop.
- If re-run after code fix is still NG: update progress.md step 10 → 🔁 差し戻し, instruct manual review.

## Step D: Report in Japanese

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.07.code.md`.
