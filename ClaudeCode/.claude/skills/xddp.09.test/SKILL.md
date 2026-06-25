---
description: XDDP フェーズ5: テスト仕様書を生成し、AIレビュー→テスト実行→不具合修正→フィードバックを一括実施する。「テストして」「テスト仕様書を作って」「テストを実行して」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 09 (process steps 11-14) — Test Spec, Execution, Bug Fix, Feedback**.

> Tests written and executed here are the final gate before release. Coverage gaps become production incidents. Orchestrate with rigor — every skipped case is a risk accepted on behalf of every user.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
REPOS_MAP, REPOS_KEYS, IS_MULTI, DOCS_DIR, DOCS, MIN_COVERAGE.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

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

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Lessons Context" with:
  LESSONS_FILE: {XDDP_DIR}/lessons-learned.md
  TARGET_TAGS: [#テスト, #不具合, #テスト観点, #見落とし]
→ let `LESSONS_CONTEXT`.

## Step A: Generate Test Specifications (per repo)

`IS_MULTI` = true（マルチリポジトリ）の場合:
  Agent ツールで各リポジトリの TSP 生成を**並列呼び出し**する（各リポジトリの CHD・SPO は独立しており、TSP 生成に相互依存がないため並列実行可能。xddp.04.specout の Discovery Phase と同様のパターン）。

`IS_MULTI` = false（シングルリポジトリ）の場合:
  順次呼び出しでよい。

Let `TEST_TEMPLATE_FILE` = ~/.claude/skills/xddp.09.test/templates/07_test-specification-template.md
（{repo} に依存しないため、本 Step A 内で逐次実行される per-repo 呼び出し・cross 呼び出しの両方からこの1箇所の定義をそのまま参照できる）

For each `{repo}` in `AFFECTED_REPOS`:

Read `{XDDP_DIR}/project-rulebook.md` (shared) + `{XDDP_DIR}/project-rulebook-{repo}.md` (if exists) as `RULEBOOK_CONTEXT`.
Let `REPO_TEST_FRAMEWORK` = `TEST_FRAMEWORK_REPOS[{repo}]` if defined, else read `TEST_FRAMEWORK` (default: `auto`).

Let `TSP_OUTPUT_FILE`（current {repo}; この式は xddp.09.test/SKILL.md の Step A・Step B の2箇所に同一の
文字列で存在する。変更時は本ファイル内で `TSP_OUTPUT_FILE` を grep し2箇所すべてを同期させること） =
  {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md

**Agent tool** `subagent_type=xddp-test-writer-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CHD_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
（{CR_PATH}/04_specout/{repo}/SPO-{CR}.md が存在する場合のみ追加）SPO_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
VERIFY_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md (if exists)
{TEST_TEMPLATE_FILE を展開}
OUTPUT_FILE: {TSP_OUTPUT_FILE を展開}
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
{TEST_TEMPLATE_FILE を展開}
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

Let `TSP_OUTPUT_FILE`（current {repo}; この式は xddp.09.test/SKILL.md の Step A・Step B の2箇所に同一の
文字列で存在する。変更時は本ファイル内で `TSP_OUTPUT_FILE` を grep し2箇所すべてを同期させること） =
  {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: TSP
  CONFIG_KEY: REVIEW_MAX_ROUNDS.TSP
  TARGET_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/06_design/{repo}/CHD-{CR}.md, {CR_PATH}/03_change-requirements/CRS-{CR}.md, （{CR_PATH}/04_specout/{repo}/SPO-{CR}.md が存在する場合のみ追加）{CR_PATH}/04_specout/{repo}/SPO-{CR}.md]
  REVIEW_OUTPUT_FILE: {CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md
  FIXER_AGENT: xddp-test-writer-agent
  FIXER_PARAMS:
    CR_NUMBER: {CR}
    REPO_NAME: {repo}
    OUTPUT_FILE: {TSP_OUTPUT_FILE を展開}
    REVIEW_FILE: {CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md
    TODAY: {TODAY}
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 11

## Step B2: Human Review Gate

Build `ARTIFACTS_TEXT` by expanding the following (AFFECTED_REPOS/HAS_CROSS are already resolved
in this skill's scope):
```
{for each repo in AFFECTED_REPOS:}
- {repo}: `{CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md`
  - AIレビュー: `{CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md`
{if HAS_CROSS:}
- cross: `{CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md`
```

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Human Review Gate" with:
  CR_PATH: {CR_PATH}
  STEP_NUM: 11
  STEP_LABEL: `Step B2`
  ARTIFACTS_TEXT: {built above}
  REVISE_COMMAND: `/xddp.revise {CR} test`（対象リポジトリを指定）
→ let `CHANGED`.

If `CHANGED`: run final AI review pass per repo.

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
RESULTS_TEMPLATE: ~/.claude/skills/xddp.09.test/templates/08_test-results-template.md
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
RESULTS_TEMPLATE: ~/.claude/skills/xddp.09.test/templates/08_test-results-template.md
TODAY: {TODAY}
RUN_NUMBER: {run_number}
OUTPUT_FILE: {CR_PATH}/10_test-results/cross/TRS-{CR}-0{run_number}.md
```

Read all TRS files.

## Step D: Handle Test Results

Let `COV_THRESHOLD` = `MIN_COVERAGE`（CR Resolution で取得済み）。
# ⚠️ 移行注意: MIN_COVERAGE 未設定の既存プロジェクトはデフォルト 80% が適用される（従来動作は 100%）。
# 旧動作を維持する場合は xddp.config.md に MIN_COVERAGE: 100 を明示設定すること。

**If all TCs pass and coverage ≥ COV_THRESHOLD% (per TEST_COVERAGE_TARGET, all repos + cross/ if applicable):**
- Update progress.md: step 12 ✅; step 13 ✅ N/A; step 14 ✅ N/A.
- Next command → `/xddp.10.specs {CR}`

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
  - If B: update progress.md (step 12 ⏸ 中断, 詳細ステップ → `Step D: テスト追加待ち`); tell the user to run `/xddp.revise {CR} test` to add test cases, then re-run `/xddp.09.test {CR}` to execute the updated test suite; stop.

**If any NG:**

Read TRS Section 3 for each repo and check for CHD/CRS change proposals.

1. **Implementation bugs only:**
   - Code fixes applied by test-runner-agent (Phase C).
   - Re-run static verification using **Agent tool** `subagent_type=xddp-verifier-agent` for the affected repo.
   - Update progress.md step 12 → 🔁 差し戻し. Instruct user to run `/xddp.09.test {CR}`.

2. **Design/requirement impact:**
   - DO NOT apply CHD/CRS changes automatically.
   - Tell the user:
     > ❌ テストNG：設計書または変更要求仕様書への変更が必要です。
     > `{CR_PATH}/10_test-results/{repo}/TRS-{CR}-0{run_number}.md` Section 3 の「CHD/CRS変更提案」を確認してください。
     >
     > **CHD の修正が必要な場合:** `/xddp.revise {CR} design` を実行して設計書を修正し、
     > その後 `/xddp.07.code {CR}` → `/xddp.09.test {CR}` の順に再実行してください。
   - Update progress.md step 12 → 🔁 差し戻し.

## Step D': Update TM with Test Cases

（Step D で /xddp.10.specs に進むと判定された場合に実行 — 全TC合格・カバレッジ閾値未達でのユーザー承認Aのケースを含む）

If `{CR_PATH}/03_change-requirements/TM-{CR}.md` does not exist: skip this step.

`TC_MAP` = {}  (key: SP ID → value: list of TC IDs)

For each `{repo}` in `AFFECTED_REPOS`:
  Let `TSP_FILE` = `{CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md`.
  If `TSP_FILE` does not exist: skip this repo.
  Read TSP Section 4.1「SP網羅マトリックス（SP × TC）」.
  For each row (SP番号, TC列一覧):
    Collect all TC番号 where セル = ○.
    Append to `TC_MAP[SP_ID]` (merge across repos; same SP may appear in multiple repo TSPs).

If `HAS_CROSS` and `{CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md` exists:
  Read TSP Section 4.1 from cross TSP similarly.
  Merge into `TC_MAP`.

Update `{CR_PATH}/03_change-requirements/TM-{CR}.md`:
  Section 1 の各行: SP ID が `TC_MAP` に存在すれば テストケース列 → TC IDをカンマ区切りで記入。存在しない場合は `-` のまま。
  Section 4 変更履歴: 版数 +0.1, 変更内容 → `テストケース列を追記（TSP-{CR}より）`.

Update `{CR_PATH}/03_change-requirements/CRS-{CR}.md`:
  Section 3.1 TM の各SP行の テスト列: ✅（TC_MAP にそのSPが存在する場合）/ ⬜（存在しない場合）.
  Increment CRS version by 0.1, add 変更履歴 entry: `TM更新に伴い Section 3.1 のテスト列を更新`.

Tell the user:
> ✅ TM にテストケースを反映しました。
> - `{CR_PATH}/03_change-requirements/TM-{CR}.md`
{if any SP row has テストケース = `-`:}
> ⚠️ テストケースに対応するSPマッピングがない SP があります。TSP Section 4.1 を確認してください。

## Step E: Report in Japanese
Summary: TC counts per repo, coverage %, NG count, next command.
