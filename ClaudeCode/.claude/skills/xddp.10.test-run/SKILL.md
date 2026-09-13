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
REPOS_MAP, REPOS_KEYS, IS_MULTI, DOCS_DIR, DOCS, MIN_COVERAGE, TEST_COVERAGE_TARGET, DEVELOPMENT_MODE,
VCS_TYPE, VCS_BRANCH_PREFIX, VCS_COMMIT_ON_STEP, VCS_AUTO_BRANCH, VCS_BASE_BRANCH, VERIFY_LINT_COMMAND,
VERIFY_LINT_COMMAND_OVERRIDES, VERIFY_BUILD_COMMAND, VERIFY_BUILD_COMMAND_OVERRIDES,
VERIFY_TYPECHECK_COMMAND, VERIFY_TYPECHECK_COMMAND_OVERRIDES, VERIFY_TOOL_TIMEOUT_SEC.)
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

1. **TSP 未作成チェック:**
   - Let `MISSING_TSP_REPOS` = `[]`.
   - For each `{repo}` in `AFFECTED_REPOS`:
     - If `{CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md` does **not** exist, append `{repo}` to `MISSING_TSP_REPOS`.
   - If `HAS_CROSS` and `{CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md` does **not** exist, append `cross` to `MISSING_TSP_REPOS`.
   - If `MISSING_TSP_REPOS` is not empty:
     Tell the user: "以下のリポジトリのテスト仕様書（TSP）が見つかりません: {MISSING_TSP_REPOS}。先に `/xddp.09.test {CR}` で TSP を作成・確定してください。"
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

If `IS_MULTI`, append per-repo progress table for step 10a:
```markdown
## 工程10a テスト実行進捗（リポジトリ別・{run_number}回目）
| リポジトリ | 状態 | 完了日 |
|---|---|---|
{for each repo in AFFECTED_REPOS: | {repo} | ⏳ 未着手 | - |}
{if HAS_CROSS: | cross | ⏳ 未着手 | - |}
```

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

Update per-repo progress table: `| {repo} | 🔄 進行中 | - |`

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

Update per-repo progress table: `| {repo} | ✅ 完了 | {TODAY} |`

If `HAS_CROSS` and cross TSP exists:
Update per-repo progress table: `| cross | 🔄 進行中 | - |`

**Agent tool** `subagent_type=xddp-test-runner-agent`:
```
{RUNNER_CALL_SHARED を展開}
REPO_NAME: cross
TSP_FILE: {CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md
CHD_FILES: [{CR_PATH}/06_design/cross/CHD-{CR}-cross.md]
OUTPUT_FILE: {CR_PATH}/10_test-results/cross/TRS-{CR}-{RUN_NO}.md
```

Update per-repo progress table: `| cross | ✅ 完了 | {TODAY} |`

Read all TRS files.

## Step B: Handle Test Results

Let `COV_THRESHOLD` = `MIN_COVERAGE`（CR Resolution で取得済み）。
# ⚠️ 移行注意: MIN_COVERAGE 未設定の既存プロジェクトはデフォルト 80% が適用される（従来動作は 100%）。
# 旧動作を維持する場合は xddp.config.md に MIN_COVERAGE: 100 を明示設定すること。
Let `MEASURED_COVERAGE`（repo毎）= 各 TRS の Section 1 記載値のうち、`TEST_COVERAGE_TARGET` が `C0` なら
C0%、`C1`（デフォルト）なら C1% の値。

**If all TCs pass and MEASURED_COVERAGE ≥ COV_THRESHOLD% (all repos + cross/ if applicable):**
- Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 10a, STATE: ✅ 完了, DETAIL_STEP: `-`,
    ARTIFACT_LINK: `[10_test-results/](10_test-results/)`
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 10b, STATE: ✅ 完了, DETAIL_STEP: `N/A`
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 10c, STATE: ✅ 完了, DETAIL_STEP: `N/A`

  **VCS commit:**
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve VCS Target Repos" with:
    REPO_CANDIDATES: {AFFECTED_REPOS}, CR_PATH: {CR_PATH}, CR: {CR}
  → let `VCS_TARGET_REPOS`.
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## VCS Auto-Commit" with:
  PROCESS_STEP: 10, REPO_LIST: VCS_TARGET_REPOS, COMMIT_MESSAGE: "{CR} 工程10テスト完了"
  （`xddp.10.test-run` には工程7のような Step -1 が無く `VCS_TARGET_REPOS` が未解決のため、コミット
  直前に解決する。コミットを progress.md 更新の**後**に置く理由は `xddp.07.code/SKILL.md`「Step C
  完了時のコミット」の同名注記と同一——`docs/adr/ADR-0011-vcs-abstraction.md` Decision 20 参照）
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
      CR_PATH: {CR_PATH}, STEP_NUM: 10a, STATE: ✅ 完了, DETAIL_STEP: `カバレッジ目標未達（人承認済み）`,
      ARTIFACT_LINK: `[10_test-results/](10_test-results/)`
    Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
      CR_PATH: {CR_PATH}, STEP_NUM: 10b, STATE: ✅ 完了, DETAIL_STEP: `N/A`

    **VCS commit:**
    Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve VCS Target Repos" with:
      REPO_CANDIDATES: {AFFECTED_REPOS}, CR_PATH: {CR_PATH}, CR: {CR}
    → let `VCS_TARGET_REPOS`.
    Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## VCS Auto-Commit" with:
    PROCESS_STEP: 10, REPO_LIST: VCS_TARGET_REPOS, COMMIT_MESSAGE: "{CR} 工程10テスト完了"
    （コミットメッセージ・挿入位置規約は上記「全 TC パス・カバレッジ達成」ブロックの VCS commit と
    同一。カバレッジ未達でも「全 TC パス」という状態自体がコミット対象であるため、メッセージは
    分けない）
    and continue to next command.
  - If B: Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
      CR_PATH: {CR_PATH}, STEP_NUM: 10a, STATE: ⏸ 中断, DETAIL_STEP: `Step B: テスト追加待ち`
    tell the user to run `/xddp.revise {CR} test` to add test cases, then re-run `/xddp.10.test-run {CR}` to execute the updated test suite（TSP 再レビューは不要）; stop.

**If any NG:**

Read TRS Section 3 for each `{repo}` in `AFFECTED_REPOS` whose
`{CR_PATH}/10_test-results/{repo}/TRS-{CR}-{RUN_NO}.md`「## 1. テスト実施概要」の `NG` 件数が
1件以上であったもの（b-1 の判定基準と同一の基準を用いる）。If `HAS_CROSS`, also read
`{CR_PATH}/10_test-results/cross/TRS-{CR}-{RUN_NO}.md` Section 3 と同様に確認する（この場合の
`{repo}` は `cross` として扱い、以下 `DESIGN_IMPACT_REPOS` は `cross` を含みうる集合とする）。
Let `DESIGN_IMPACT_REPOS` = the subset of those repos（`cross` を含む）whose TRS Section 3 records
at least one NG entry with a「CHD変更提案」or「CRS変更提案」（`xddp-test-runner-agent.md`「### Phase D」の記録先）。
（1つのTRS内で実装バグ由来のNG（Phase Cで修正済み）と設計影響のNGが混在する場合、その repo は
`DESIGN_IMPACT_REPOS` に含める — 設計影響が1件でもあれば人による判断が必要なため。）

**b-1（常に実施）: 実装バグの再検証**
- Code fixes applied by test-runner-agent (Phase C) for any bug-type NGs.
- Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 10b, STATE: 🔄 進行中
- Re-run static verification for each `{repo}` in `AFFECTED_REPOS` whose
  `{CR_PATH}/10_test-results/{repo}/TRS-{CR}-{RUN_NO}.md`「## 1. テスト実施概要」の `NG` 件数が
  1件以上であったもの（`DESIGN_IMPACT_REPOS` に含まれる repo も、Phase C が実装バグ部分を
  修正している可能性があるため対象から除外しない。`cross` はこのループの対象に含めない —
  `xddp-test-runner-agent.md`「REPO_PATH (optional)」の契約上 `cross` は単一の実行可能な
  リポジトリパスを持たず、Phase C のコード修正対象になり得ないため、cross TRS 上のNGは常に
  b-2 の設計・要求影響の案内に委ねられる）:
  Read `~/.claude/skills/xddp.rules/xddp.coding.rules.md` to get `CODING_RULES`.
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Steering Context" with:
    XDDP_DIR: {XDDP_DIR}, REPO_NAME: {repo}
  → let `RULEBOOK_CONTEXT`.
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
    CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
  → let `CHD_CONTENT_FILES`.
  Let `CODING_MEMO` = `{CR_PATH}/07_coding/CODING-{CR}-{repo}.md`
  （test-runner-agent Phase C が実装バグ修正のたびに必ず追記するため、この時点で常に存在する。
  `(omit if file does not exist)` は付けない）。
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Run Verification Tools" with:
    REPO_NAME: {repo}, REPO_PATH: {REPOS_MAP[repo]}, CR_PATH: {CR_PATH}, CR: {CR}
  → let `TOOL_RESULTS_FILE`, `TOOL_ALL_PASS`, `TOOL_USAGE_ERROR`, `TOOL_USAGE_ERROR_DETAIL`.
  （辞書 `TOOL_ALL_PASS_BY_REPO[repo]`・`TOOL_USAGE_ERROR_BY_REPO[repo]`・
  `TOOL_USAGE_ERROR_DETAIL_BY_REPO[repo]` に記録する。
  Phase C のバグ修正で lint/build/typecheck が壊れていないかを確認するのが目的）
  **Agent tool** `subagent_type=xddp-verifier-agent`:
  ```
  CR_NUMBER: {CR}
  REPO_NAME: {repo}
  CHD_FILES: {CHD_CONTENT_FILES}
  CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
  CODING_MEMO: {CODING_MEMO}
  TOOL_RESULTS_FILE: {TOOL_RESULTS_FILE}（空文字列の場合は省略）
  TOOL_USAGE_ERROR_DETAIL: {TOOL_USAGE_ERROR_DETAIL}（空文字列の場合は省略。使用法エラー時に
    Section J が「➖ 未設定」と誤ってラベル付けされることを防ぐ）
  OUTPUT_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md
  TODAY: {TODAY}
  CODING_RULES: {pass CODING_RULES content as-is}
  RULEBOOK_CONTEXT: {RULEBOOK_CONTEXT}
  ADDITIONAL_REFS: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md (pass if exists)
  ```
  （OUTPUT_FILE は工程8で生成済みの `VERIFY-{CR}-{repo}.md` を上書きする。工程10bの再検証は
  工程8の検証結果を最新化する位置づけのため、別名の派生ファイルにはしない。）

まず、対象 repo 全件（b-1 のループが回った repo 全件）について `TOOL_USAGE_ERROR_BY_REPO` を
確認し終える（1件目で判定を打ち切らない）。`true` の repo が1件でもあれば、該当する repo **全件**
分のエラー内容を1回のブロックにまとめて案内し、後続の `TOOL_ALL_PASS_BY_REPO` チェック・
TRSベースのNG判定のいずれにも進まずその場で停止する（`xddp-verifier-agent` の総合判定・
TRSベースのNG分類とは独立の判定であり、後者より先に確認する）:
> ⚠️ 実ツール実行スクリプト（`xddp_verify_tools.py`）の呼び出し自体が失敗しました（{repo}）。
> 以下のエラー内容を確認し、`xddp.config.md` の
> `VERIFY_LINT_COMMAND`/`VERIFY_BUILD_COMMAND`/`VERIFY_TYPECHECK_COMMAND` 設定またはスクリプト
> 自体の不具合を確認してください:
> ```
> {TOOL_USAGE_ERROR_DETAIL_BY_REPO[repo]}
> ```
（上記引用ブロックは `TOOL_USAGE_ERROR_BY_REPO[repo] = true` の repo それぞれについて1つずつ、
まとめて提示する。）

対象 repo 全件で `TOOL_USAGE_ERROR_BY_REPO` が `false`（使用法エラーなし）だった場合のみ、
次に `TOOL_ALL_PASS_BY_REPO` を確認する。いずれかの repo で `false`（実ツール実行が真の検証失敗）の
場合、b-1 の再検証で得た `xddp-verifier-agent` の総合判定に関わらず、その repo は静的検証NGとして
扱い、`{CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md` の確認を促す（この判定は repo ごとに独立
——ある repo が静的検証NGでも他 repo の TRS ベース判定は継続する）。

既存分岐（b-1固定実施＋b-2の設計影響案内）の構造そのものは変更しない——本追加は TRS ベースの
NG 判定に**先立って**行う独立ゲートである。

**b-2: 設計・要求への影響の案内（`DESIGN_IMPACT_REPOS` が空でない場合のみ）**
If `DESIGN_IMPACT_REPOS` is not empty:
- DO NOT apply CHD/CRS changes automatically.
- Tell the user, listing every `{repo}` in `DESIGN_IMPACT_REPOS`（`cross` を含む場合はパス
  テンプレートの `{repo}` が `cross` に解決されるだけで特別扱いは不要）:
  > ❌ テストNG：以下のリポジトリで設計書または変更要求仕様書への変更が必要です。
  > {DESIGN_IMPACT_REPOS の各 repo を列挙}
  > `{CR_PATH}/10_test-results/{repo}/TRS-{CR}-{RUN_NO}.md` Section 3 の「CHD/CRS変更提案」を確認してください。
  >
  > **CHD の修正が必要な場合:** `/xddp.revise {CR} design` を実行して設計書を修正し
  > （`cross` の場合は `xddp.revise/SKILL.md` のリポジトリ選択で `cross` を選択する）、
  > その後 `/xddp.07.code {CR}` → `/xddp.09.test {CR}`（TSP再生成）→ `/xddp.10.test-run {CR}` の順に再実行してください。

  > 工程10で test-runner-agent が当てた修正を取り消す場合:
  > 以下を対象リポジトリごとに実行してください:
  > - `{repo}`: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_vcs.py revert --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE} --untracked`
  > VCS_TYPE: none の場合はこの操作はスキップされます。

  （上記引用ブロックの `- ` 行は `VCS_TARGET_REPOS`（未解決の場合はその場で `## Resolve VCS Target
  Repos` を apply して解決する）の各 `{repo}` について1行ずつ展開して提示する。`cross` は
  `REPOS_MAP` のキーではなく `VCS_TARGET_REPOS`（実リポジトリのみ）にも含まれ得ないため、この
  revert 案内には自然に登場しない。この括弧書きは実装者・実行 AI 向けの生成指示であり、ユーザーへは
  表示しない）

**b-3: 実装バグのみだった場合の案内（`DESIGN_IMPACT_REPOS` が空の場合のみ）**
If `DESIGN_IMPACT_REPOS` is empty:
- Instruct user to run `/xddp.10.test-run {CR}`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 10a, STATE: 🔁 差し戻し
（b-2・b-3 いずれの場合も再実行が必要な状態であることに変わりはないため、進捗更新は分岐後に1回だけ
共通で行う。）

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
  CR_PATH: {CR_PATH}, STEP_NUM: 10c, STATE: ✅ 完了, DETAIL_STEP: `-`,
  ARTIFACT_LINK: `[TM-{CR}.md](03_change-requirements/TM-{CR}.md)`
（TM/CRS へのテストケース反映が完了した場合）

Tell the user:
> ✅ TM にテストケースを反映しました。
> - `{CR_PATH}/03_change-requirements/TM-{CR}.md`
{if any SP row has テストケース = `-`:}
> ⚠️ テストケースに対応するSPマッピングがない SP があります。TSP Section 4.1 を確認してください。

## Step D: Report in Japanese
Summary: TC counts per repo, coverage %, NG count, next command.
