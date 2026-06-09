---
description: XDDP フェーズ5: テスト仕様書を生成し、AIレビュー→テスト実行→不具合修正→フィードバックを一括実施する。「テストして」「テスト仕様書を作って」「テストを実行して」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 08 (process steps 11-14) — Test Spec, Execution, Bug Fix, Feedback**.

> Tests written and executed here are the final gate before release. Coverage gaps become production incidents. Orchestrate with rigor — every skipped case is a risk accepted on behalf of every user.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Build `REPOS_MAP` (repo name → path).
Let `REPOS_KEYS` = list of all repository names. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).

Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.

`AFFECTED_REPOS` = all `REPOS_KEYS`.
Let `HAS_CROSS` = (IS_MULTI and `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` exists).

Read `TEST_FRAMEWORK_REPOS:` if defined (repo → test framework map).

## Step 0: Reference Past TSPs and TRSs from DOCS_DIR

For each `{repo}` in `AFFECTED_REPOS`:
1. Let `TEST_DIR` = `{DOCS}/{repo}/test/`.
2. If `{TEST_DIR}` exists:
   a. Read `{DOCS}/AI_INDEX.md` to find past TSP/TRS list for `{repo}`.
   b. Load up to 3 TSP files related to changed components.
   c. Load up to 2 TRS files related to changed components
      （`## 3. NG詳細` セクションのみ参照。目的: 過去に失敗した回帰テストの把握）
3. Record in TSP "referenced past test specs" section.

## Step 0.5: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 11 (テスト設計) → 🔄 進行中, 詳細ステップ → `Step A: TSP生成中`, today. Write back.

## Step A0: Reference Lessons Learned Log

If `{XDDP_DIR}/lessons-learned.md` exists, read it.
Focus on entries tagged `#テスト` `#不具合` `#テスト観点` `#見落とし` and extract patterns applicable to the current CHD's changed components.
Include relevant findings in `LESSONS_CONTEXT` when passing to the test-writer-agent.

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
TEMPLATE_FILE: ~/.claude/skills/xddp.templates/07_test-specification-template.md
OUTPUT_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
TODAY: {TODAY}
TEST_FRAMEWORK: {REPO_TEST_FRAMEWORK}
（Step A0 で LESSONS_CONTEXT が空でない場合のみ追加）LESSONS_CONTEXT: {LESSONS_CONTEXT}
```

If `HAS_CROSS`, after all per-repo TSPs are done, generate cross integration test spec:

Read `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md`.

**Agent tool** `subagent_type=xddp-test-writer-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: cross
CHD_FILE: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
TEMPLATE_FILE: ~/.claude/skills/xddp.templates/07_test-specification-template.md
OUTPUT_FILE: {CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md
TODAY: {TODAY}
TEST_FOCUS: |
  Focus on integration test cases that verify the inter-repo interface contract:
  - Each interface in "インタフェース変更サマリ" must have at least 1 happy-path TC and 1 error TC.
  - Verify consumer repos can receive and handle responses from provider repos correctly.
```

## Step B: Test Spec Review Loop (up to `REVIEW_MAX_ROUNDS.TSP` rounds)

Update `{CR_PATH}/progress.md` step 11 詳細ステップ → `Step B: AIレビュー中`.

For each `{repo}` in `AFFECTED_REPOS`:

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: TSP
  CONFIG_KEY: REVIEW_MAX_ROUNDS.TSP
  TARGET_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/06_design/{repo}/CHD-{CR}.md, {CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/{repo}/SPO-{CR}.md]
  REVIEW_OUTPUT_FILE: {CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md
  FIXER_AGENT: xddp-test-writer-agent
  FIXER_PARAMS:
    CR_NUMBER: {CR}
    REPO_NAME: {repo}
    OUTPUT_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
    REVIEW_FILE: {CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md
    TODAY: {TODAY}
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 11

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
RESULTS_TEMPLATE: ~/.claude/skills/xddp.templates/08_test-results-template.md
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
RESULTS_TEMPLATE: ~/.claude/skills/xddp.templates/08_test-results-template.md
TODAY: {TODAY}
RUN_NUMBER: {run_number}
OUTPUT_FILE: {CR_PATH}/10_test-results/cross/TRS-{CR}-0{run_number}.md
```

Read all TRS files.

## Step D: Handle Test Results

Read `MIN_COVERAGE` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `80`).
Let `COV_THRESHOLD` = `MIN_COVERAGE`.
# ⚠️ 移行注意: MIN_COVERAGE 未設定の既存プロジェクトはデフォルト 80% が適用される（従来動作は 100%）。
# 旧動作を維持する場合は xddp.config.md に MIN_COVERAGE: 100 を明示設定すること。

**If all TCs pass and coverage ≥ COV_THRESHOLD% (per TEST_COVERAGE_TARGET, all repos + cross/ if applicable):**
- Update progress.md: step 12 ✅; step 13 ✅ N/A; step 14 ✅ N/A.
- Next command → `/xddp.09.specs {CR}`

**If all TCs pass but coverage < COV_THRESHOLD% (any repo):**
- List repos/files below threshold with their actual coverage %.
- Tell the user:
  > ⚠️ 全 TC はパスしましたが、カバレッジが目標（{COV_THRESHOLD}%）を下回っています。
  > | リポジトリ | カバレッジ | 目標 |
  > |---|---|---|
  > {list per repo}
  >
  > **A（承認して続行）:** このカバレッジでよければ「A」と入力してください。
  > **B（テストケースを追加）:** TSP を修正してテストを追加する場合は `/xddp.revise {CR} test` を実行してください。
- Wait for user response.
  - If A: update progress.md (step 12 ✅ with coverage warning note) and continue to next command.
  - If B: update progress.md (step 12 ⏸ 中断, 詳細ステップ → `Step D: テスト追加待ち`); tell the user to run `/xddp.revise {CR} test` to add test cases, then re-run `/xddp.08.test {CR}` to execute the updated test suite; stop.

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
