---
description: XDDP フェーズ4: 変更設計書に基づいてコーディングを実施し、静的検証を行う。「コーディングして」「実装して」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 07 (process steps 7-8) — Coding + Static Verification**.

> Code written in this step runs in production. Faithfulness to the CHD and attention to every edge case are non-negotiable. Orchestrate with discipline — a deviation here becomes a production incident.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
DOCS_DIR, REPOS_MAP, REPOS_KEYS, IS_MULTI, DEVELOPMENT_MODE, VCS_TYPE, VCS_BRANCH_PREFIX,
VCS_COMMIT_ON_STEP, VCS_AUTO_BRANCH, VCS_BASE_BRANCH.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`.
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve HAS_CROSS" with:
  IS_MULTI: {IS_MULTI}, ARTIFACT_PATH: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
→ let `HAS_CROSS`.
（本工程は直前工程＝design の cross CHD の有無で cross 処理要否を判断する）

## Step -1: VCS Branch Setup

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve VCS Target Repos" with:
  REPO_CANDIDATES: {AFFECTED_REPOS}, CR_PATH: {CR_PATH}, CR: {CR}
→ let `VCS_TARGET_REPOS`.
（`AFFECTED_REPOS` は `FILTER_BY_SPO: false` のとき全リポジトリと同一になるため、VCS の副作用対象には
使わない。詳細は `xddp.common/SKILL.md`「## Resolve VCS Target Repos」参照）

For each `{repo}` in `VCS_TARGET_REPOS`:

1. If `VCS_TYPE` is `none`: skip this repo.

2. If `VCS_TYPE` is `auto`:
   Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_vcs.py detect --repo {REPOS_MAP[repo]} --vcs-type auto`
   → let `REPO_VCS_TYPE`.

3. If `VCS_TYPE` is `git`:
   Let `REPO_VCS_TYPE` = `VCS_TYPE`.

   （`VCS_TYPE` が `auto`/`git`/`none` 以外の値になることはない——`## Load Config` で読み込み時に
   一元的に `none` へ正規化・警告済みのため。この Step -1 では `auto`/`git`/`none` の3値のみを
   想定すればよい）

4. If `VCS_AUTO_BRANCH` is `true` and `REPO_VCS_TYPE` is not `none`:
   Let `BRANCH_NAME` = `{VCS_BRANCH_PREFIX}{CR}`.
   Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_vcs.py branch {BRANCH_NAME} --repo {REPOS_MAP[repo]} --vcs-type {REPO_VCS_TYPE} --base-ref {VCS_BASE_BRANCH} --ignore-path {WORKSPACE_ROOT}/{XDDP_DIR} --ignore-path {WORKSPACE_ROOT}/{DOCS_DIR}`
   If exit code ≠ 0: report the error and stop.
   （`--base-ref {VCS_BASE_BRANCH}` は新規ブランチ作成時のみ使用され、既存ブランチへの切替時は
   無視される。`--ignore-path` は dirty 判定の除外指定。`{XDDP_DIR}`・`{DOCS_DIR}` を当該リポジトリ内に
   置く構成では、工程1〜6 が生成した XDDP 成果物で必ず dirty になり工程7が冒頭で停止してしまうため、
   これらのディレクトリを判定対象から外す。両ディレクトリがリポジトリ外にある一般的な構成では
   スクリプト側で無視されるため従来と同一の判定になる）
   If exit code = 0: Tell the user `"✅ 作業ブランチ \`{BRANCH_NAME}\` に切り替えました"`。

**設計メモ（`{REPO_VCS_TYPE}` と `{VCS_TYPE}` の使い分け）:** 以降のコミット・status・revert 呼び出しは、
Step -1 で解決済みの `{REPO_VCS_TYPE}` ではなく生設定値 `{VCS_TYPE}` を渡す（意図的な選択）。
`{REPO_VCS_TYPE}` は Step -1 実行時点の一時変数であり、`/xddp.07.code {CR}` が設計エラー差し戻し後に
再実行される（Step -1 から再度実行される）運用を考えると、後続ステップで `{VCS_TYPE}` を毎回
`resolve_vcs_type()` に渡して再解決する方が、遠く離れたステップ間で一時変数を引き回すよりも状態管理が
単純で取り違えの余地がない（`resolve_vcs_type()` の再解決コストは `.git` 存在確認1回のみで軽微）。

## Step 0: Determine Implementation Order and Check for Circular Dependencies

Read `~/.claude/skills/xddp.rules/xddp.coding.rules.md` to get `CODING_RULES`.

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

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 7, STATE: 🔄 進行中, DETAIL_STEP: `Step A: コーディング中`
If `IS_MULTI`, append per-repo progress table for step 7:
```markdown
## 工程7 コーディング進捗（リポジトリ別）
| リポジトリ | 状態 | 完了日 |
|---|---|---|
{for each repo in IMPL_ORDER: | {repo} | ⏳ 未着手 | - |}
{if HAS_CROSS: | cross/検証 | ⏳ 未着手 | - |}
```

## Step A-Pre: Load Coding Quality Rules and Project Memory

`CODING_RULES` is already loaded in Step 0（repo非依存のためここでの再読み取りは不要）。
`RULEBOOK_CONTEXT` は repo 依存のため Step 0 では読み込んでいない。Step A・Step B それぞれの
`For each {repo}` ループ内で `## Load Steering Context` を呼び出し、repo ごとに取得する。

Let `CODE_AGENT_SHARED` =
  CR_NUMBER: {CR}
  TODAY: {TODAY}
  CODING_RULES: {pass CODING_RULES content as-is}
  ADDITIONAL_REFS: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md (pass if exists — interface contract reference)
（`{repo}` に依存しないため、Step A・Step B の両独立ループからこの1箇所の定義をそのまま参照できる）

## Step A: Implement Code Changes (in dependency order)

For each `{repo}` in `IMPL_ORDER` (sequentially — do not parallelise to respect implementation order):

Update per-repo progress table: `| {repo} | 🔄 進行中 | - |`

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Steering Context" with:
  XDDP_DIR: {XDDP_DIR}
  REPO_NAME: {repo}
→ let `RULEBOOK_CONTEXT`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `CHD_CONTENT_FILES`.

**Agent tool** `subagent_type=xddp-coder-agent`:
```
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CHD_FILES: {CHD_CONTENT_FILES}
OUTPUT_MEMO: {CR_PATH}/07_coding/CODING-{CR}-{repo}.md
{CODE_AGENT_SHARED を展開}
RULEBOOK_CONTEXT: {RULEBOOK_CONTEXT}
```

Wait for completion. If the agent reports CHD Before/After discrepancies, relay to the user.

Update per-repo progress table: `| {repo} | ✅ 完了 | {TODAY} |`

## Step B: Static Verification (per repo)

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 7, STATE: 🔄 進行中, DETAIL_STEP: `Step B: 静的検証・コードレビュー中`
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 8, STATE: 🔄 進行中, DETAIL_STEP: `Step B: 静的検証・コードレビュー中`

For each `{repo}` in `IMPL_ORDER`:

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Steering Context" with:
  XDDP_DIR: {XDDP_DIR}
  REPO_NAME: {repo}
→ let `RULEBOOK_CONTEXT`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `CHD_CONTENT_FILES`.

**Agent tool** `subagent_type=xddp-verifier-agent`:
```
REPO_NAME: {repo}
CHD_FILES: {CHD_CONTENT_FILES}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
CODING_MEMO: {CR_PATH}/07_coding/CODING-{CR}-{repo}.md
OUTPUT_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md
{CODE_AGENT_SHARED を展開}
RULEBOOK_CONTEXT: {RULEBOOK_CONTEXT}
```

Read the verification report.

## Step B-cross: Cross-repo Interface Verification (only when HAS_CROSS = true)

After all per-repo verification is complete, verify that the cross/CHD interface commitments were honoured.

Update per-repo progress table: `| cross/検証 | 🔄 進行中 | - |`

**Agent tool** `subagent_type=xddp-verifier-agent`
（`CODE_AGENT_SHARED` は使用しない。設計根拠: docs/adr/ADR-0003-verify-cross-agent-params.md）:
```
CR_NUMBER: {CR}
REPO_NAME: cross
CHD_FILES: [{CR_PATH}/06_design/cross/CHD-{CR}-cross.md]
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
- Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 7, STATE: ✅ 完了, DETAIL_STEP: `-`,
    ARTIFACT_LINK: `[07_coding/](07_coding/)`
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 8, STATE: ✅ 完了, DETAIL_STEP: `-`,
    ARTIFACT_LINK: `[08_code-review/](08_code-review/)`

  **VCS commit:**
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## VCS Auto-Commit" with:
  PROCESS_STEP: 7, REPO_LIST: VCS_TARGET_REPOS, COMMIT_MESSAGE: "{CR} 工程7コーディング完了"
  （`VCS_TARGET_REPOS` は Step -1 で解決済みの値をそのまま使う。コミットを progress.md 更新の**後**に
  置くのは意図的な配置——`git commit` の失敗（`user.email` 未設定・pre-commit フック拒否等）で
  コード変更・静的検証がすべて成功しているのに工程完了が progress.md に記録されないまま停止する
  事態を避けるため。設計判断の詳細は `docs/adr/ADR-0011-vcs-abstraction.md` Decision 20 を参照）
- Next command → `/xddp.09.test {CR}`

**If ❌ NG (any repo):**
- Read NG list and classify each:
  - **Implementation bug** (coding mistake): Fix directly in source code, then re-run Step B for that repo.
  - **Design error** (CHD itself is incorrect): DO NOT fix code. Instruct the user:
    > ❌ 静的検証NG：設計書（CHD）に誤りが検出されました。
    > `{CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md` の NG 内容を確認し、
    > `/xddp.06.design {CR}` を再実行して設計書を修正してください。
    > 設計書修正後に `/xddp.07.code {CR}` を再実行してください。
    Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
      CR_PATH: {CR_PATH}, STEP_NUM: 8, STATE: 🔁 差し戻し

    > {VCS_AUTO_BRANCH が true の場合} 工程7で作成した作業ブランチ `{VCS_BRANCH_PREFIX}{CR}` への変更を
    破棄する場合:
    > {VCS_AUTO_BRANCH が false の場合} 現在の作業ツリーへの変更を破棄する場合（`VCS_AUTO_BRANCH: false`
    のためブランチは自動作成されていません）:
    > 以下を対象リポジトリごとに実行してください:
    > - `{repo}`: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_vcs.py revert --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE} --untracked`
    > VCS_TYPE: none の場合はこの操作はスキップされます。

    （上記引用ブロックの `- ` 行は `VCS_TARGET_REPOS`（未解決の場合はその場で `## Resolve VCS Target
    Repos` を apply して解決する）の各 `{repo}` について1行ずつ展開して提示する。この括弧書きは
    実装者・実行 AI 向けの生成指示であり、ユーザーへは表示しない）
    Stop.
- If re-run after code fix is still NG: Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 8, STATE: 🔁 差し戻し
  instruct manual review.

## Step D: Report in Japanese
