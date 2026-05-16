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

## Step 0: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 9 (コーディング) → 🔄 進行中, 詳細ステップ → `Step A: コーディング中`, today. Write back.

## Step A-Pre: Load Coding Quality Rules and Project Memory

Read `~/.claude/templates/xddp.coding.rules.md` to get `CODING_RULES`.

If `{XDDP_DIR}/project-steering.md` exists, read it to get `STEERING_CONTEXT`.
If not found, set `STEERING_CONTEXT` = empty string.

Pass `CODING_RULES` and `STEERING_CONTEXT` to the coder-agent and verifier-agent as
the quality gate definition and project-specific constraints for this step.

## Step A0: Load Multi-Repository Configuration

Read `{WORKSPACE_ROOT}/xddp.config.md` (found earlier) and extract:

- Whether `MULTI_REPO` is `true`.
- If `true`, read the `REPOS:` section and build `REPOS_MAP` (repo name → path).
- If `TEST_FRAMEWORK_REPOS:` is defined, read it as `TEST_FRAMEWORK_REPOS_MAP`.
- If `false` or undefined, set `REPOS_MAP = {}` and proceed in single-repo mode.

The coder-agent reads the `リポジトリ:` field of each Before/After block in the CHD,
resolves the actual file path via `REPOS_MAP`, and applies the code change.

## Step A: Implement Code Changes

**Agent tool** `subagent_type=xddp-coder-agent`:
```
CR_NUMBER: {CR}
CHD_FILE: {CR_PATH}/06_design/CHD-{CR}.md
OUTPUT_MEMO: {CR_PATH}/07_coding/CODING-{CR}.md
REPOS_MAP: {repository mapping from Step A0; empty for single-repo}
TODAY: {TODAY}
CODING_RULES: {pass CODING_RULES content as-is}
STEERING_CONTEXT: {contents of project-steering.md, or empty if not found}
```

Wait for completion. If the agent reports CHD Before/After discrepancies, read the memo and relay them to the user.

## Step B: Static Verification

Update `{CR_PATH}/progress.md` step 9 詳細ステップ → `Step B: 静的検証中`. Also set step 10 → 🔄 進行中.

**Agent tool** `subagent_type=xddp-verifier-agent`:
```
CR_NUMBER: {CR}
CHD_FILE: {CR_PATH}/06_design/CHD-{CR}.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
CODING_MEMO: {CR_PATH}/07_coding/CODING-{CR}.md
OUTPUT_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}.md
TODAY: {TODAY}
CODING_RULES: {pass CODING_RULES content as-is}
STEERING_CONTEXT: {contents of project-steering.md, or empty if not found}
```

Read the verification report.

## Step C: Handle Verification Result

**If ✅ pass:**
- Update progress.md: step 9 (コーディング) ✅, 詳細ステップ → `-`; step 10 (静的検証) ✅, 詳細ステップ → `-`.
- Next command → `/xddp.08.test {CR}`

**If ❌ NG:**
- Read the NG list from VERIFY file and classify each NG:
  - **Implementation bug** (coding mistake): Fix directly in source code, then re-run Step B once.
  - **Design error** (the CHD After code itself is incorrect): DO NOT fix code. Instead, instruct the user:
    > ❌ 静的検証NG：設計書（CHD）に誤りが検出されました。
    > `{CR_PATH}/08_code-review/VERIFY-{CR}.md` の NG 内容を確認し、
    > `/xddp.06.design {CR}` を再実行して設計書を修正してください。
    > 設計書修正後に `/xddp.07.code {CR}` を再実行してください。
    Update progress.md step 10 → 🔁 差し戻し, 詳細ステップ → `Step B: 静的検証NG`. Stop.
- If re-run after code fix is still NG: update progress.md step 10 → 🔁 差し戻し, and instruct the user to check `{CR_PATH}/08_code-review/VERIFY-{CR}.md` and run `/xddp.07.code {CR}` again after manual review.
- If ✅ after re-run: proceed to next step.

## Step D: Report in Japanese

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.07.code.md`.
