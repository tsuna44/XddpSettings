---
description: XDDP フェーズ5: レビュー確定済みテスト仕様書（TSP）に基づきテストを実行し、不具合修正→TM/CRS フィードバックを実施する。「テストを実行して」「テスト実行して」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 10 (process steps 10a-10c) — Test Execution, Bug Fix, Feedback**.

> Tests executed here are the final gate before release. A skipped failure or coverage gap becomes a production incident. Orchestrate with rigor — this command runs only after the TSP has been reviewed and confirmed by `/xddp.09.test`.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
REPOS_MAP, REPOS_KEYS, IS_MULTI, DOCS_DIR, DOCS, MIN_COVERAGE, TEST_COVERAGE_TARGET.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

（本コマンドは `/xddp.09.test` とは別セッションで起動されうるため、AFFECTED_REPOS・HAS_CROSS・
MIN_COVERAGE・TEST_COVERAGE_TARGET を自己完結で再解決する。）

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`.
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve HAS_CROSS" with:
  IS_MULTI: {IS_MULTI}, ARTIFACT_PATH: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
→ let `HAS_CROSS`.
（本工程は design の cross CHD の有無で cross 処理要否を判断する。CHD は工程6a・7で共通利用するため
07.code と同じ ARTIFACT_PATH を用いる）

## Step -1: Precondition Check (TSP existence and review confirmation)

1. **TSP 未作成チェック:** For each `{repo}` in `AFFECTED_REPOS`, check whether
   `{CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md` exists.
   If **no** TSP file exists for any repo (and, if `HAS_CROSS`, `{CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md`
   also does not exist):
   Tell the user: "テスト仕様書（TSP）が見つかりません。先に `/xddp.09.test {CR}` で TSP を作成・確定してください。"
   Stop.

2. **人レビュー未確定チェック:** Read `{CR_PATH}/progress.md`. If step 9 (テスト設計) is not ✅ 完了:
   Warn the user:
   > ⚠️ テスト設計（工程9）が ✅ 完了になっていません（人レビュー未確定の可能性があります）。
   > TSP のレビューを確定せずにテストを実行しようとしています。
   > 続行しますか？（「続行」と入力／中止する場合は `/xddp.09.test {CR}` で TSP を確定してください）
   Wait for user response. If the user does not choose to continue, stop.
   （工程9 の ✅ は `/xddp.09.test` の Step B2 人レビューゲート通過後にのみ付与される。）

## Step A: Execute Tests (per repo)

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 10a, STATE: 🔄 進行中, DETAIL_STEP: `Step A: テスト実行中`

Determine `run_number`（実施回数の採番）:
  Glob `{CR_PATH}/10_test-results/*/TRS-{CR}-*.md`（repo 別・cross の全サブディレクトリを対象）。
  各ファイル名末尾の `-{数字列}.md` から数字列を抽出する（桁数は固定しない。可変長の数字列として
  読み取り、2桁・3桁いずれの既存ファイルにも対応する）。抽出した数値の最大値を `N` とする。
  `run_number = N + 1`。該当ファイルが1件もなければ `run_number = 1`。
  （差し戻し（🔁）後の再実行時に前回の TRS を上書きせず、実施履歴として保全するため）
Let `RUN_NO` = `run_number` のゼロ埋め2桁文字列（例: 1 → `01`、12 → `12`。2桁を超える場合は
桁数をそのまま使う。例: 123 → `123`）。

Let `RUNNER_CALL_SHARED` =
  CR_NUMBER: {CR}
  CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
  RESULTS_TEMPLATE: ~/.claude/skills/xddp.10.test-run/templates/10_test-results-template.md
  TODAY: {TODAY}
  RUN_NUMBER: {RUN_NO}
（{repo} に依存しないため、Step A per-repo・cross の両方からこの1箇所の定義をそのまま参照できる。
TSP_FILE・CHD_FILES・OUTPUT_FILE・REPO_NAME・REPO_PATH は呼び出し箇所ごとに値が異なるため
ここには含めない）

For each `{repo}` in `AFFECTED_REPOS`:

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `CHD_CONTENT_FILES`.

**Agent tool** `subagent_type=xddp-test-runner-agent` (Phase A–C):
```
{RUNNER_CALL_SHARED を展開}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
TSP_FILE: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md
CHD_FILES: {CHD_CONTENT_FILES}
OUTPUT_FILE: {CR_PATH}/10_test-results/{repo}/TRS-{CR}-{RUN_NO}.md
```

If `HAS_CROSS` and cross TSP exists:
**Agent tool** `subagent_type=xddp-test-runner-agent`:
```
{RUNNER_CALL_SHARED を展開}
REPO_NAME: cross
TSP_FILE: {CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md
CHD_FILES: [{CR_PATH}/06_design/cross/CHD-{CR}-cross.md]
OUTPUT_FILE: {CR_PATH}/10_test-results/cross/TRS-{CR}-{RUN_NO}.md
```

Read all TRS files.

## Step B: Handle Test Results

Let `COV_THRESHOLD` = `MIN_COVERAGE`（CR Resolution で取得済み）。
# ⚠️ 移行注意: MIN_COVERAGE 未設定の既存プロジェクトはデフォルト 80% が適用される（従来動作は 100%）。
# 旧動作を維持する場合は xddp.config.md に MIN_COVERAGE: 100 を明示設定すること。
Let `MEASURED_COVERAGE`（repo毎）= 各 TRS の Section 1 記載値のうち、`TEST_COVERAGE_TARGET` が `C0` なら
C0%、`C1`（デフォルト）なら C1% の値。

**If all TCs pass and MEASURED_COVERAGE ≥ COV_THRESHOLD% (all repos + cross/ if applicable):**
- Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 10a, STATE: ✅ 完了, DETAIL_STEP: `-`
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 10b, STATE: ✅ 完了, DETAIL_STEP: `N/A`
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 10c, STATE: ✅ 完了, DETAIL_STEP: `N/A`
- Next command → `/xddp.11.specs {CR}`

**If all TCs pass but MEASURED_COVERAGE < COV_THRESHOLD% (any repo):**
- List repos/files below threshold with their actual coverage %.
- Tell the user:
  > ⚠️ 全 TC はパスしましたが、{TEST_COVERAGE_TARGET}（C0=ステートメント/C1=ブランチ）カバレッジが目標（{COV_THRESHOLD}%）を下回っています。
  > | リポジトリ | MEASURED_COVERAGE（{TEST_COVERAGE_TARGET}） | 目標 |
  > |---|---|---|
  > {list per repo}
  >
  > **A（承認して続行）:** このカバレッジでよければ「A」と入力してください。
  > **B（テストケースを追加）:** TSP を修正してテストを追加する場合は `/xddp.revise {CR} test` を実行してください。
- Wait for user response.
  - If A: Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
      CR_PATH: {CR_PATH}, STEP_NUM: 10a, STATE: ✅ 完了, DETAIL_STEP: `カバレッジ目標未達（人承認済み）`
    and continue to next command.
  - If B: Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
      CR_PATH: {CR_PATH}, STEP_NUM: 10a, STATE: ⏸ 中断, DETAIL_STEP: `Step B: テスト追加待ち`
    tell the user to run `/xddp.revise {CR} test` to add test cases, then re-run `/xddp.10.test-run {CR}` to execute the updated test suite（TSP 再レビューは不要）; stop.

**If any NG:**

Read TRS Section 3 for each repo and check for CHD/CRS change proposals.

1. **Implementation bugs only:**
   - Code fixes applied by test-runner-agent (Phase C).
   - Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
       CR_PATH: {CR_PATH}, STEP_NUM: 10b, STATE: 🔄 進行中
   - Re-run static verification using **Agent tool** `subagent_type=xddp-verifier-agent` for the affected repo.
   - Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
       CR_PATH: {CR_PATH}, STEP_NUM: 10a, STATE: 🔁 差し戻し
     Instruct user to run `/xddp.10.test-run {CR}`.

2. **Design/requirement impact:**
   - DO NOT apply CHD/CRS changes automatically.
   - Tell the user:
     > ❌ テストNG：設計書または変更要求仕様書への変更が必要です。
     > `{CR_PATH}/10_test-results/{repo}/TRS-{CR}-{RUN_NO}.md` Section 3 の「CHD/CRS変更提案」を確認してください。
     >
     > **CHD の修正が必要な場合:** `/xddp.revise {CR} design` を実行して設計書を修正し、
     > その後 `/xddp.07.code {CR}` → `/xddp.09.test {CR}`（TSP再生成）→ `/xddp.10.test-run {CR}` の順に再実行してください。
   - Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
       CR_PATH: {CR_PATH}, STEP_NUM: 10a, STATE: 🔁 差し戻し

## Step C: Update TM with Test Cases

（Step B で `/xddp.11.specs` に進むと判定された場合に実行 — 全TC合格・カバレッジ閾値未達でのユーザー承認Aのケースを含む）

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

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 10c, STATE: ✅ 完了, DETAIL_STEP: `-`
（TM/CRS へのテストケース反映が完了した場合）

Tell the user:
> ✅ TM にテストケースを反映しました。
> - `{CR_PATH}/03_change-requirements/TM-{CR}.md`
{if any SP row has テストケース = `-`:}
> ⚠️ テストケースに対応するSPマッピングがない SP があります。TSP Section 4.1 を確認してください。

## Step D: Report in Japanese
Summary: TC counts per repo, coverage %, NG count, next command.
