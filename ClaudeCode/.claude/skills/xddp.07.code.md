---
description: XDDP フェーズ4: 変更設計書に基づいてコーディングを実施し、静的検証を行う。「コーディングして」「実装して」などで起動する。
---

You are orchestrating **XDDP Step 07 (process steps 09-10) — Coding + Static Verification**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

Read `xddp.config.md` (project root) and extract `XDDP_DIR` (default: `.` if the key is absent). Let `CR_PATH` = `{XDDP_DIR}/{CR}`.

## Step 0: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 9 (コーディング) → 🔄 進行中, 詳細ステップ → `Step A: コーディング中`, today. Write back.

## Step A-Pre: コーディング品質ルールの読み込み

Read `~/.claude/templates/xddp.07.rules.md` to get `CODING_RULES`.
Pass `CODING_RULES` to the coder-agent and verifier-agent as the quality gate definition for this step.

## Step A0: マルチリポジトリ設定の読み込み

`xddp.config.md` を読み込み、以下を取得する。

- `MULTI_REPO` が `true` かどうかを確認する。
- `true` の場合、`REPOS:` セクションからリポジトリ名→パスのマッピングを `REPOS_MAP` として取得する。
- `TEST_FRAMEWORK_REPOS:` が定義されていれば `TEST_FRAMEWORK_REPOS_MAP` として取得する。
- `false` または未定義の場合、`REPOS_MAP = {}` とし単一リポジトリモードで進む。

coder-agent は CHD の各 Before/After ブロックに記載された `リポジトリ:` フィールドを読み取り、
`REPOS_MAP` を参照して実際のファイルパスを解決してコードを適用する。

## Step A: Implement Code Changes

**Agent tool** `subagent_type=xddp-coder-agent`:
```
CR_NUMBER: {CR}
CHD_FILE: {CR_PATH}/06_design/CHD-{CR}.md
OUTPUT_MEMO: {CR_PATH}/07_coding/CODING-{CR}.md
REPOS_MAP: {Step A0 で取得したリポジトリマッピング。単一リポジトリの場合は空}
TODAY: {TODAY}
CODING_RULES: {CODING_RULES の内容をそのまま渡す}
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
CODING_RULES: {CODING_RULES の内容をそのまま渡す}
```

Read the verification report.

## Step C: Handle Verification Result

**If ✅ 合格:**
- Update progress.md: step 9 (コーディング) ✅, 詳細ステップ → `-`; step 10 (静的検証) ✅, 詳細ステップ → `-`.
- Next command → `/xddp.08.test {CR}`

**If ❌ NG:**
- Read the NG list from VERIFY file and classify each NG:
  - **実装バグ**（コーディングミス）: Fix directly in source code, then re-run Step B once.
  - **設計ミス**（CHD の After コード自体が誤り）: DO NOT fix code. Instead, instruct the user:
    > ❌ 静的検証NG：設計書（CHD）に誤りが検出されました。
    > `{CR_PATH}/08_code-review/VERIFY-{CR}.md` の NG 内容を確認し、
    > `/xddp.06.design {CR}` を再実行して設計書を修正してください。
    > 設計書修正後に `/xddp.07.code {CR}` を再実行してください。
    Update progress.md step 10 → 🔁 差し戻し, 詳細ステップ → `Step B: 静的検証NG`. Stop.
- If re-run after code fix is still NG: update progress.md step 10 → 🔁 差し戻し, and instruct the user to check `{CR_PATH}/08_code-review/VERIFY-{CR}.md` and run `/xddp.07.code {CR}` again after manual review.
- If ✅ after re-run: proceed to next step.

## Step D: Report in Japanese

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.07.code.md` の要約も合わせて更新すること。
