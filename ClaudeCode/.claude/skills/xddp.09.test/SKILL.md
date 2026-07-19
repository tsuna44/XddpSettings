---
description: XDDP フェーズ5: テスト仕様書（TSP）を生成し、AIレビュー→人レビューで品質を確定する。テスト実行は `/xddp.10.test-run` で行う。「テスト設計して」「テスト仕様書を作って」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 09 (process step 9) — Test Specification**.

> The test specification you produce here defines the release gate. Coverage gaps become production incidents. Orchestrate with rigor — every missed test case is a risk accepted on behalf of every user. Test execution is a separate command (`/xddp.10.test-run`); this skill stops once the TSP is reviewed and confirmed.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
REPOS_MAP, REPOS_KEYS, IS_MULTI, DOCS_DIR, DOCS, MIN_COVERAGE, TEST_COVERAGE_TARGET.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`.
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve HAS_CROSS" with:
  IS_MULTI: {IS_MULTI}, ARTIFACT_PATH: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
→ let `HAS_CROSS`.
（本工程は design の cross CHD の有無で cross 処理要否を判断する。CHD は工程6a・7で共通利用するため
07.code と同じ ARTIFACT_PATH を用いる）

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

Read `{CR_PATH}/progress.md`. Set step 9 (テスト設計) → 🔄 進行中, 詳細ステップ → `Step A: TSP生成中`, today. Write back.

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

Let `TEST_TEMPLATE_FILE` = ~/.claude/skills/xddp.09.test/templates/09_test-specification-template.md
（{repo} に依存しないため、本 Step A 内で逐次実行される per-repo 呼び出し・cross 呼び出しの両方からこの1箇所の定義をそのまま参照できる）

Let `WRITER_CALL_SHARED` =
  CR_NUMBER: {CR}
  TODAY: {TODAY}
  MIN_COVERAGE: {MIN_COVERAGE}
  TEST_COVERAGE_TARGET: {TEST_COVERAGE_TARGET}
（{repo} に依存しないため、Step A per-repo・Step A cross・Step B FIXER_PARAMS の3箇所から
この1箇所の定義をそのまま参照できる。REPO_NAME は呼び出し箇所ごとに値が異なるため
各呼び出し箇所に個別記述のまま残す）

For each `{repo}` in `AFFECTED_REPOS`:

Read `{XDDP_DIR}/project-rulebook.md` (shared) + `{XDDP_DIR}/project-rulebook-{repo}.md` (if exists) as `RULEBOOK_CONTEXT`.
Let `REPO_TEST_FRAMEWORK` = `TEST_FRAMEWORK_REPOS[{repo}]` if defined, else read `TEST_FRAMEWORK` (default: `auto`).

Let `TSP_OUTPUT_FILE`（current {repo}; この式は xddp.09.test/SKILL.md の Step A・Step B の2箇所に同一の
文字列で存在する。変更時は本ファイル内で `TSP_OUTPUT_FILE` を grep し2箇所すべてを同期させること） =
  {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `CHD_CONTENT_FILES`.

**Agent tool** `subagent_type=xddp-test-writer-agent`:
```
{WRITER_CALL_SHARED を展開}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CHD_FILES: {CHD_CONTENT_FILES}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
（{CR_PATH}/04_specout/{repo}/SPO-{CR}.md が存在する場合のみ追加）SPO_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
VERIFY_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md (if exists)
{TEST_TEMPLATE_FILE を展開}
OUTPUT_FILE: {TSP_OUTPUT_FILE を展開}
TEST_FRAMEWORK: {REPO_TEST_FRAMEWORK}
（Step A0 で LESSONS_CONTEXT が空でない場合のみ追加）LESSONS_CONTEXT: {LESSONS_CONTEXT}
```

If `HAS_CROSS`, after all per-repo TSPs are done, generate cross integration test spec:

Read `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md`.

**Agent tool** `subagent_type=xddp-test-writer-agent`:
```
{WRITER_CALL_SHARED を展開}
REPO_NAME: cross
CHD_FILES: [{CR_PATH}/06_design/cross/CHD-{CR}-cross.md]
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
{TEST_TEMPLATE_FILE を展開}
OUTPUT_FILE: {CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md
TEST_FOCUS: |
  Focus on integration test cases that verify the inter-repo interface contract:
  - Each interface in "インタフェース変更サマリ" must have at least 1 happy-path TC and 1 error TC.
  - Verify consumer repos can receive and handle responses from provider repos correctly.
```

## Step B: Test Spec Review Loop (up to `REVIEW_MAX_ROUNDS.TSP` rounds)

Update `{CR_PATH}/progress.md` step 9 詳細ステップ → `Step B: AIレビュー中`.

For each `{repo}` in `AFFECTED_REPOS`:

Let `TSP_OUTPUT_FILE`（current {repo}; この式は xddp.09.test/SKILL.md の Step A・Step B の2箇所に同一の
文字列で存在する。変更時は本ファイル内で `TSP_OUTPUT_FILE` を grep し2箇所すべてを同期させること） =
  {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `CHD_CONTENT_FILES`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: TSP
  CONFIG_KEY: REVIEW_MAX_ROUNDS.TSP
  TARGET_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
  REFERENCE_FILES: [{CHD_CONTENT_FILES を展開}, {CR_PATH}/03_change-requirements/CRS-{CR}.md, （{CR_PATH}/04_specout/{repo}/SPO-{CR}.md が存在する場合のみ追加）{CR_PATH}/04_specout/{repo}/SPO-{CR}.md]
  REVIEW_OUTPUT_FILE: {CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md
  FIXER_AGENT: xddp-test-writer-agent
  FIXER_PARAMS:
    {WRITER_CALL_SHARED を展開}
    REPO_NAME: {repo}
    OUTPUT_FILE: {TSP_OUTPUT_FILE を展開}
    REVIEW_FILE: {CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 9
  EXTRA_REVIEWER_PARAMS:
    MIN_COVERAGE: {MIN_COVERAGE}
    TEST_COVERAGE_TARGET: {TEST_COVERAGE_TARGET}

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
  STEP_NUM: 9
  STEP_LABEL: `Step B2`
  ARTIFACTS_TEXT: {built above}
  REVISE_COMMAND: `/xddp.revise {CR} test`（対象リポジトリを指定）
→ let `CHANGED`.

If `CHANGED`:
- For each `{repo}` in `AFFECTED_REPOS`: Read `~/.claude/skills/xddp.common/SKILL.md`,
  apply "## Final Review Pass" with:
    DOCUMENT_TYPE: TSP
    TARGET_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
    REFERENCE_FILES: {Step B と同一}
    REVIEW_ROUND: (last_round + 1)
    OUTPUT_FILE: {CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md
    EXTRA_REVIEWER_PARAMS:
      MIN_COVERAGE: {MIN_COVERAGE}
      TEST_COVERAGE_TARGET: {TEST_COVERAGE_TARGET}

## Step C: Mark Test Spec Complete

**状態遷移の注意（必須）:** `step 9`（テスト設計）→ ✅ 完了 は、本 Step C（＝ Step B2 人レビューゲート
通過後）でのみ付与する。Step B2 を経ずにセッションが中断された場合は `step 9` を ✅ にせず、
`👀 レビュー待ち`（Step B2 の Human Review Gate が設定した状態）のまま留めること。
これにより後続 `/xddp.10.test-run` の前提チェック「`step 9` ✅ = 人レビュー確定」が実効を持つ
（✅ を無条件付与すると人レビュー実施有無に関わらず常に ✅ となり前提チェックが機能しないため）。

Update `{CR_PATH}/progress.md`:
- step 9 (テスト設計) → ✅ 完了, 詳細ステップ → `-`, today.
- 次に実行すべきコマンド → `/xddp.10.test-run {CR}`
Write back.

## Step D: Report in Japanese

Report:
- 生成した TSP ファイル一覧（per repo + cross/ if applicable）
- AIレビューのラウンド数・残指摘の有無
- 次のアクション案内:
  > ✅ テスト仕様書（TSP）を生成し、AIレビュー→人レビューで確定しました。
  > - 修正が必要なら `/xddp.revise {CR} test`
  > - 問題なければ `/xddp.10.test-run {CR}` でテストを実行してください。
