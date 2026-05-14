---
description: XDDP フェーズ5: テスト仕様書を生成し、AIレビュー→テスト実行→不具合修正→フィードバックを一括実施する。「テストして」「テスト仕様書を作って」「テストを実行して」などで起動する。
---

You are orchestrating **XDDP Step 08 (process steps 11-14) — Test Spec, Execution, Bug Fix, Feedback**.

> Tests written and executed here are the final gate before release. Coverage gaps become production incidents. Orchestrate with rigor — every skipped case is a risk accepted on behalf of every user.

**Arguments:** $ARGUMENTS = [CR_NUMBER]（省略可）

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md の探索は xddp.common.md 内で完了済み。WORKSPACE_ROOT・XDDP_DIR を引き続き使用する)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: DOCS_DIR 過去 TSP 参照

1. ヘッダーで発見した `{WORKSPACE_ROOT}/xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
   Read `REPO_NAME` from the `xddp.config.md` found earlier. If absent or empty, report error and stop.
   Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`. Let `TEST_DIR` = `{DOCS}/{REPO_NAME}/test/`.

2. `{TEST_DIR}` が存在しない場合 → スキップし「参照なし（初回 CR）」と記録する。

3. `{TEST_DIR}` が存在する場合:
   a. `{DOCS}/AI_INDEX.md` を読み、`{REPO_NAME}` のテスト仕様一覧（TSP-*.md）を把握する。
   b. CHD（`{CR_PATH}/06_design/CHD-{CR}.md`）が存在する場合、
      変更対象コンポーネント・関数を抽出し、同一コンポーネントをテストした過去 TSP を優先する。
   c. 最新 3 件（または CHD 関連のもの）を上限として TSP ファイルを読み込む。
   d. `{DOCS}/shared/test/patterns.md` と `{DOCS}/shared/test/anti-patterns.md` が
      存在すれば読み込む。

4. 読み込んだ内容を以下の目的に活用する:
   - 過去の同一コンポーネントテストで使われたテストケース構造・命名規則を参考にする
   - 過去に発見されたバグパターンを参照し、回帰テストケースの充実度を上げる
   - anti-patterns（過去に失敗したテスト設計）を参照し、同じ失敗を避ける

5. TSP ドキュメントの「参照した過去テスト仕様」節に、読み込んだファイル名と
   抽出したパターン・anti-pattern の要約を記録する。

## Step 0.5: Mark In-Progress
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

Read the `xddp.config.md` found earlier (`{WORKSPACE_ROOT}/xddp.config.md`). Extract `REVIEW_MAX_ROUNDS.TSP` (default: 2 if key absent). Set `max_rounds` = that value.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: TSP
   TARGET_FILE: {CR_PATH}/09_test-spec/TSP-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/06_design/CHD-{CR}.md, {CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/09_test-spec/review/09_test-spec-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit loop.
   - Issues found, `round < max_rounds` → use **Agent tool** `subagent_type=xddp-test-writer-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     OUTPUT_FILE: {CR_PATH}/09_test-spec/TSP-{CR}.md
     REVIEW_FILE: {CR_PATH}/09_test-spec/review/09_test-spec-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = max_rounds` → append warning.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 11 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR_PATH}/09_test-spec/TSP-{CR}.md`
> - AIレビュー結果: `{CR_PATH}/09_test-spec/review/09_test-spec-review.md`
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
  OUTPUT_FILE: {CR_PATH}/09_test-spec/review/09_test-spec-review.md
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
