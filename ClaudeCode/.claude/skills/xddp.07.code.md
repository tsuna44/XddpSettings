---
description: XDDP フェーズ4: 変更設計書に基づいてコーディングを実施し、静的検証を行う。「コーディングして」「実装して」などで起動する。
---

You are orchestrating **XDDP Step 07 (process steps 09-10) — Coding + Static Verification**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

## Step 0: Mark In-Progress
Read `{CR}/progress.md`. Set step 9 (コーディング) → 🔄 進行中, 詳細ステップ → `Step A: コーディング中`, today. Write back.

## Step A: Implement Code Changes

**Agent tool** `subagent_type=xddp-coder-agent`:
```
CR_NUMBER: {CR}
CHD_FILE: {CR}/06_design/CHD-{CR}.md
OUTPUT_MEMO: {CR}/07_coding/CODING-{CR}.md
TODAY: {TODAY}
```

Wait for completion. If the agent reports CHD Before/After discrepancies, read the memo and relay them to the user.

## Step B: Static Verification

Update `{CR}/progress.md` step 9 詳細ステップ → `Step B: 静的検証中`. Also set step 10 → 🔄 進行中.

**Agent tool** `subagent_type=xddp-verifier-agent`:
```
CR_NUMBER: {CR}
CHD_FILE: {CR}/06_design/CHD-{CR}.md
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
CODING_MEMO: {CR}/07_coding/CODING-{CR}.md
OUTPUT_FILE: {CR}/08_code-review/VERIFY-{CR}.md
TODAY: {TODAY}
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
    > `{CR}/08_code-review/VERIFY-{CR}.md` の NG 内容を確認し、
    > `/xddp.06.design {CR}` を再実行して設計書を修正してください。
    > 設計書修正後に `/xddp.07.code {CR}` を再実行してください。
    Update progress.md step 10 → 🔁 差し戻し, 詳細ステップ → `Step B: 静的検証NG`. Stop.
- If re-run after code fix is still NG: update progress.md step 10 → 🔁 差し戻し, and instruct the user to check `{CR}/08_code-review/VERIFY-{CR}.md` and run `/xddp.07.code {CR}` again after manual review.
- If ✅ after re-run: proceed to next step.

## Step D: Report in Japanese

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.07.code.md` の要約も合わせて更新すること。
