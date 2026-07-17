---
description: XDDP Step 08 静的検証（手動実行）: CHD・CRS に対する静的検証を実施する。xddp.07.code の自動検証と同一内容を人が任意のタイミングで実行できる。「静的検証して」「コードレビューして」「verify して」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 08 (process step 8) — Static Verification**.

> This skill runs the same verification as xddp.07.code Step B.
> The only difference is that xddp.07.code triggers it automatically after AI coding,
> while this skill is triggered manually — e.g., after a human modifies the code.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
REPOS_MAP, REPOS_KEYS, IS_MULTI.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`.
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve HAS_CROSS" with:
  IS_MULTI: {IS_MULTI}, ARTIFACT_PATH: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
→ let `HAS_CROSS`.
（本工程は xddp.07.code の自動検証と同一内容を人が手動実行する工程8の静的検証であり、
直前工程＝design の cross CHD の有無で cross 処理要否を判断する点も 07.code と同一）

Read `~/.claude/skills/xddp.rules/xddp.coding.rules.md` to get `CODING_RULES`
（`## Step 0` 見出しより前、ファイル冒頭で1回のみ実施。以降のステップで再読み取りしないこと）.

## Step 0: Determine Verification Order

If `HAS_CROSS`:
  Read `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` and extract the "実装依存関係" table.
  Build a directed graph from the 実装依存関係 table. Detect cycles using DFS.
  If a cycle is found: report ⛔ 循環依存検出。cross/CHD の「実装依存関係」テーブルを見直してください。Stop.
  Determine `IMPL_ORDER` by topological sort (provider repos before consumers).
Else:
  `IMPL_ORDER` = `REPOS_KEYS` in REPOS: definition order.

(xddp.07.code Step 0 と同一の依存解決ロジック。クロスリポジトリ CHD がある場合にインタフェース提供リポジトリを先に検証するために必要。)

## Step 0.5: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 8 (静的検証) → 🔄 進行中, 詳細ステップ → `静的検証・コードレビュー中`, today. Write back.
(step 8 が既に ✅ の場合も無条件に 🔄 へ上書きする。再実行時は最初から検証をやり直すことが目的のため、これは意図的な動作。)

## Step A: Static Verification (per repo)

For each `{repo}` in `IMPL_ORDER`:
(RULEBOOK_CONTEXT はリポジトリごとにループ内でロードする。xddp.07.code Step B と同一スコープ。
IMPL_ORDER を使用することで、クロスリポジトリ CHD がある場合にインタフェース提供リポジトリが先に検証される。)

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Steering Context" with:
  XDDP_DIR: {XDDP_DIR}
  REPO_NAME: {repo}
→ let `RULEBOOK_CONTEXT`.

Let `CODING_MEMO` = `{CR_PATH}/07_coding/CODING-{CR}-{repo}.md`.
(xddp-verifier-agent は CODING_MEMO をオプション入力として定義している
（`agents/xddp-verifier-agent.md` の `### Optional Inputs` セクション）。
xddp.07.code では coder-agent 実行後に必ず存在するため常に渡す。
xddp.08.verify では人手修正後は存在しない場合があるため、存在する場合のみ渡す。
これは xddp.08.verify と xddp.07.code の唯一の意図的な差分。検証ロジック自体は同一。)

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `CHD_CONTENT_FILES`.

**Agent tool** `subagent_type=xddp-verifier-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
CHD_FILES: {CHD_CONTENT_FILES}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
CODING_MEMO: {CODING_MEMO} (omit if file does not exist)
OUTPUT_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md
TODAY: {TODAY}
CODING_RULES: {pass CODING_RULES content as-is}
RULEBOOK_CONTEXT: {RULEBOOK_CONTEXT}
ADDITIONAL_REFS: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md (pass if exists)
```

Read the verification report.

## Step A-cross: Cross-repo Interface Verification (only when HAS_CROSS = true)

**Agent tool** `subagent_type=xddp-verifier-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: cross
CHD_FILES: [{CR_PATH}/06_design/cross/CHD-{CR}-cross.md]
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
CODING_MEMOS: [{CR_PATH}/07_coding/CODING-{CR}-{repo}.md for each repo in REPOS_KEYS (omit files that do not exist)]
OUTPUT_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}-cross.md
TODAY: {TODAY}
VERIFICATION_TASK: |
  Verify that the cross/CHD "インタフェース変更サマリ" is fully implemented:
  - "新規追加": confirm the interface was added in the provider repo's CODING memo or source code
  - "変更": confirm the change matches the CODING memo or source code
  - "削除": confirm the deletion was carried out
  For each mismatch, flag as NG with details.
```

Read the verification report. If NG items exist:
> ⚠️ クロスリポジトリ インタフェース検証NG: `{CR_PATH}/08_code-review/VERIFY-{CR}-cross.md` を確認してください。

## Step B: Handle Verification Result

**If all ✅ pass (all repos + cross/ if applicable):**
- Update progress.md: step 8 (静的検証) ✅, 詳細ステップ → `-`.
- Report: `✅ 静的検証が完了しました。次のコマンド → /xddp.09.test {CR}`

**If ❌ NG (any repo):**
- Read NG list and classify each:
  - **Implementation bug** (coding mistake): Fix directly in source code, then re-run `/xddp.08.verify {CR}` for that repo.
  - **Design error** (CHD itself is incorrect): DO NOT fix code. Instruct the user:
    > ❌ 静的検証NG：設計書（CHD）に誤りが検出されました。
    > `{CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md` の NG 内容を確認し、
    > `/xddp.06.design {CR}` を再実行して設計書を修正してください。
    > 設計書修正後に `/xddp.07.code {CR}` または `/xddp.08.verify {CR}` を再実行してください。
    Update progress.md step 8 → 🔁 差し戻し. Stop.
