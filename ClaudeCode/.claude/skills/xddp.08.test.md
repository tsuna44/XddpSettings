---
description: XDDP フェーズ5: テスト仕様書を生成し、AIレビュー→テスト実行→不具合修正→フィードバックを一括実施する。「テストして」「テスト仕様書を作って」「テストを実行して」などで起動する。
---

You are orchestrating **XDDP Step 08 (process steps 11-14) — Test Spec, Execution, Bug Fix, Feedback**.

> Tests written and executed here are the final gate before release. Coverage gaps become production incidents. Orchestrate with rigor — every skipped case is a risk accepted on behalf of every user.

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
Let `HAS_CROSS` = (IS_MULTI and `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` exists).

Read `TEST_FRAMEWORK_REPOS:` if defined (repo → test framework map).

## Step 0: Reference Past TSPs from DOCS_DIR

For each `{repo}` in `AFFECTED_REPOS`:
1. Let `TEST_DIR` = `{DOCS}/{repo}/test/`.
2. If `{TEST_DIR}` exists:
   a. Read `{DOCS}/AI_INDEX.md` to find past TSP list for `{repo}`.
   b. Load up to 3 TSP files related to changed components.
3. Record in TSP "referenced past test specs" section.

## Step 0.5: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 11 (テスト設計) → 🔄 進行中, 詳細ステップ → `Step A: TSP生成中`, today. Write back.

## Step A: Generate Test Specifications (per repo)

For each `{repo}` in `AFFECTED_REPOS`:

Read `{XDDP_DIR}/project-steering.md` (shared) + `{XDDP_DIR}/project-steering-{repo}.md` (if exists) as `STEERING_CONTEXT`.
Let `REPO_TEST_FRAMEWORK` = `TEST_FRAMEWORK_REPOS[{repo}]` if defined, else read `TEST_FRAMEWORK` (default: `auto`).

**Agent tool** `subagent_type=xddp-test-writer-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CHD_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
VERIFY_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md (if exists)
TEMPLATE_FILE: ~/.claude/templates/07_test-specification-template.md
OUTPUT_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
TODAY: {TODAY}
TEST_FRAMEWORK: {REPO_TEST_FRAMEWORK}
```

If `HAS_CROSS`, after all per-repo TSPs are done, generate cross integration test spec:

Read `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md`.

**Agent tool** `subagent_type=xddp-test-writer-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: cross
CHD_FILE: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
TEMPLATE_FILE: ~/.claude/templates/07_test-specification-template.md
OUTPUT_FILE: {CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md
TODAY: {TODAY}
TEST_FOCUS: |
  Focus on integration test cases that verify the inter-repo interface contract:
  - Each interface in "インタフェース変更サマリ" must have at least 1 happy-path TC and 1 error TC.
  - Verify consumer repos can receive and handle responses from provider repos correctly.
```

## Step B: Test Spec Review Loop (up to `REVIEW_MAX_ROUNDS.TSP` rounds)

Update `{CR_PATH}/progress.md` step 11 詳細ステップ → `Step B: AIレビュー中`.
Read `REVIEW_MAX_ROUNDS.TSP` (default: 2). Set `max_rounds` = that value.

For each `{repo}` in `AFFECTED_REPOS`:

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: TSP
   TARGET_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/06_design/{repo}/CHD-{CR}.md, {CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/{repo}/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit loop.
   - Issues found, `round < max_rounds` → use **Agent tool** `subagent_type=xddp-test-writer-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     REPO_NAME: {repo}
     OUTPUT_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
     REVIEW_FILE: {CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = max_rounds` → append warning.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 11 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
{for each repo in AFFECTED_REPOS:}
> - {repo}: `{CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md`
>   - AIレビュー: `{CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md`
{if HAS_CROSS:}
> - cross: `{CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md`
>
> 修正が完了したら「**レビュー完了**」と入力してください。

Wait for user to confirm. If changes: run final AI review pass per repo.

## Step C: Execute Tests (per repo)

Update `{CR_PATH}/progress.md` step 11 状態 → ✅ 完了, step 12 → 🔄 進行中, 詳細ステップ → `Step C: テスト実行中`.

`run_number = 1`

For each `{repo}` in `AFFECTED_REPOS`:

**Agent tool** `subagent_type=xddp-test-runner-agent` (Phase A–C):
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
TSP_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
CHD_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
RESULTS_TEMPLATE: ~/.claude/templates/08_test-results-template.md
TODAY: {TODAY}
RUN_NUMBER: {run_number}
OUTPUT_FILE: {CR_PATH}/10_test-results/{repo}/TRS-{CR}-0{run_number}.md
```

If `HAS_CROSS` and cross TSP exists:
**Agent tool** `subagent_type=xddp-test-runner-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: cross
TSP_FILE: {CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md
CHD_FILE: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
RESULTS_TEMPLATE: ~/.claude/templates/08_test-results-template.md
TODAY: {TODAY}
RUN_NUMBER: {run_number}
OUTPUT_FILE: {CR_PATH}/10_test-results/cross/TRS-{CR}-0{run_number}.md
```

Read all TRS files.

## Step D: Handle Test Results

**If all TCs pass and C0/C1 ≥ 100% (all repos + cross/ if applicable):**
- Update progress.md: step 12 ✅; step 13 ✅ N/A; step 14 ✅ N/A.
- Next command → `/xddp.09.specs {CR}`

**If any NG:**

Read TRS Section 3 for each repo and check for CHD/CRS change proposals.

1. **Implementation bugs only:**
   - Code fixes applied by test-runner-agent (Phase C).
   - Re-run static verification using **Agent tool** `subagent_type=xddp-verifier-agent` for the affected repo.
   - Update progress.md step 12 → 🔁 差し戻し. Instruct user to run `/xddp.08.test {CR}`.

2. **Design/requirement impact:**
   - DO NOT apply CHD/CRS changes automatically.
   - Tell the user:
     > ❌ テストNG：設計書または変更要求仕様書への変更が必要です。
     > `{CR_PATH}/10_test-results/{repo}/TRS-{CR}-0{run_number}.md` Section 3 の「CHD/CRS変更提案」を確認してください。
     >
     > **CHD の修正が必要な場合:** `/xddp.revise {CR} design` を実行して設計書を修正し、
     > その後 `/xddp.07.code {CR}` → `/xddp.08.test {CR}` の順に再実行してください。
   - Update progress.md step 12 → 🔁 差し戻し.

## Step E: Report in Japanese
Summary: TC counts per repo, coverage %, NG count, next command.

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.08.test.md`.
