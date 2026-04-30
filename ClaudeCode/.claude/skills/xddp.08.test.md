---
description: XDDP フェーズ5: テスト仕様書を生成し、AIレビュー→テスト実行→不具合修正→フィードバックを一括実施する。「テストして」「テスト仕様書を作って」「テストを実行して」などで起動する。
---

You are orchestrating **XDDP Step 08 (process steps 11-14) — Test Spec, Execution, Bug Fix, Feedback**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

Read `xddp.config.md` (project root) and extract `XDDP_DIR` (default: `.` if the key is absent). Let `CR_PATH` = `{XDDP_DIR}/{CR}`.

## Step 0: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 11 (テスト設計) → 🔄 進行中, 詳細ステップ → `Step A: TSP生成中`, today. Write back.

## Step A: Generate Test Specification

**Agent tool** `subagent_type=xddp-test-writer-agent`:
```
CR_NUMBER: {CR}
CHD_FILE: {CR_PATH}/06_design/CHD-{CR}.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR_PATH}/04_specout/SPO-{CR}.md
VERIFY_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}.md
TEMPLATE_FILE: ~/.claude/templates/07_test-specification-template.md
OUTPUT_FILE: {CR_PATH}/09_test-spec/TSP-{CR}.md
TODAY: {TODAY}
```

## Step B: Test Spec Review Loop (up to `REVIEW_MAX_ROUNDS.TSP` rounds)

Update `{CR_PATH}/progress.md` step 11 詳細ステップ → `Step B: AIレビュー中`.

Read `xddp.config.md` (project root). Extract `REVIEW_MAX_ROUNDS.TSP` (default: 2 if key absent). Set `max_rounds` = that value.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: TSP
   TARGET_FILE: {CR_PATH}/09_test-spec/TSP-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/06_design/CHD-{CR}.md, {CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/review/09_test-spec-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit loop.
   - Issues found, `round < max_rounds` → use **Agent tool** `subagent_type=xddp-test-writer-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     OUTPUT_FILE: {CR_PATH}/09_test-spec/TSP-{CR}.md
     REVIEW_FILE: {CR_PATH}/review/09_test-spec-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = max_rounds` → append warning.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 11 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR_PATH}/09_test-spec/TSP-{CR}.md`
> - AIレビュー結果: `{CR_PATH}/review/09_test-spec-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} test`
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。
> 変更がなければそのまま「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes (edited the file or ran `/xddp.revise`):
- Run one final AI review pass using **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: TSP
  TARGET_FILE: {CR_PATH}/09_test-spec/TSP-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/06_design/CHD-{CR}.md, {CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/SPO-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/review/09_test-spec-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Execute Tests

Update `{CR_PATH}/progress.md` step 11 状態 → ✅ 完了, 詳細ステップ → `-`; step 12 → 🔄 進行中, 詳細ステップ → `Step C: テスト実行中`.

`run_number = 1`

**Agent tool** `subagent_type=xddp-test-runner-agent` (Phase A–C):
```
CR_NUMBER: {CR}
TSP_FILE: {CR_PATH}/09_test-spec/TSP-{CR}.md
CHD_FILE: {CR_PATH}/06_design/CHD-{CR}.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
RESULTS_TEMPLATE: ~/.claude/templates/08_test-results-template.md
TODAY: {TODAY}
RUN_NUMBER: {run_number}
```

Read `{CR_PATH}/10_test-results/TRS-{CR}-0{run_number}.md`.

## Step D: Handle Test Results

**If all TCs pass and C0/C1 ≥ 100%:**
- Update progress.md: step 12 (テスト実行) ✅, 詳細ステップ → `-`; step 13 (不具合修正) ✅ N/A, 詳細ステップ → `-`; step 14 (不具合フィードバック) ✅ N/A, 詳細ステップ → `-`.
- Next command → `/xddp.09.specs {CR}`

**If any NG:**

Read TRS Section 3 and check each NG for CHD/CRS change proposals.

1. **実装バグのみ（CHD/CRS 変更提案なし）**:
   - Code fixes were applied by test-runner-agent (Phase C).
   - Re-run static verification using **Agent tool** `subagent_type=xddp-verifier-agent`:
     ```
     CR_NUMBER: {CR}
     CHD_FILE: {CR_PATH}/06_design/CHD-{CR}.md
     CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
     CODING_MEMO: {CR_PATH}/07_coding/CODING-{CR}.md
     OUTPUT_FILE: {CR_PATH}/08_code-review/VERIFY-{CR}.md
     TODAY: {TODAY}
     ```
     If ❌ NG after re-verification: treat as design error and escalate to case 2 below.
   - Update progress.md step 12 → 🔁 差し戻し, 詳細ステップ → `Step D: 不具合修正中`.
   - Instruct user: NGs recorded in `{CR_PATH}/10_test-results/TRS-{CR}-0{run_number}.md`. Run `/xddp.08.test {CR}` to re-execute.

2. **設計/要求への影響あり（CHD/CRS 変更提案が TRS に記録されている）**:
   - DO NOT apply CHD/CRS changes automatically.
   - Tell the user:
     > ❌ テストNG：設計書または変更要求仕様書への変更が必要です。
     > `{CR_PATH}/10_test-results/TRS-{CR}-0{run_number}.md` Section 3 の「CHD/CRS変更提案」を確認してください。
     >
     > **CHD の修正が必要な場合:** `/xddp.revise {CR} design` を実行して設計書を修正し、
     > その後 `/xddp.07.code {CR}` → `/xddp.08.test {CR}` の順に再実行してください。
     >
     > **CRS の修正が必要な場合:** `/xddp.revise {CR} req` を実行して変更要求仕様書を修正し、
     > その後 `/xddp.06.design {CR}` → `/xddp.07.code {CR}` → `/xddp.08.test {CR}` の順に再実行してください。
   - Update progress.md step 12 → 🔁 差し戻し, 詳細ステップ → `Step D: 設計/要求変更待ち`.

## Step E: Report in Japanese
Summary: TC counts, coverage %, NG count, next command.

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.08.test.md` の要約も合わせて更新すること。
