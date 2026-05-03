---
description: XDDP フェーズ3: 実装方式検討メモ（DSN）を作成し、AIレビュー→修正ループを実施する。「方式検討して」「実装方針を決めて」などで起動する。
---

You are orchestrating **XDDP Step 05 (process step 06) — Implementation Approach Design**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

Read `xddp.config.md` (project root) and extract `XDDP_DIR` (default: `.` if the key is absent). Let `CR_PATH` = `{XDDP_DIR}/{CR}`.

## Step 0: DOCS_DIR 過去 DSN 参照

1. `xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
   Read `REPO_NAME` from `xddp.config.md`. If absent or empty, report error and stop.
   Let `DESIGN_DIR` = `{DOCS}/{REPO_NAME}/design/`.

2. `{DESIGN_DIR}` が存在しない場合 → スキップし「参照なし（初回 CR）」と記録する。

3. `{DESIGN_DIR}` が存在する場合:
   a. `{DOCS}/AI_INDEX.md` を読み、`{REPO_NAME}` の設計書一覧（DSN-*.md）を把握する。
   b. CRS（`{CR_PATH}/03_change-requirements/CRS-{CR}.md`）が存在する場合、
      変更対象モジュール・コンポーネントを抽出し、関連する過去 DSN を優先する。
   c. 最新 3 件（または CRS 関連のもの）を上限として DSN ファイルを読み込む。
   d. `{DOCS}/shared/design/patterns.md` が存在すれば読み込む。

4. 読み込んだ内容を以下の目的に活用する:
   - 過去の実装方式選択とその理由を把握し、今回の方式決定に活用する
   - 既存アーキテクチャパターンとの整合性を確認する
   - 過去に却下された方式案があれば参照し、同じ検討の重複を避ける

5. DSN ドキュメントの「参照した過去設計書」節に、読み込んだファイル名と
   抽出した関連知見の要約を記録する。

## Step 0.5: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 6 (実装方式検討) → 🔄 進行中, 詳細ステップ → `Step A: DSN生成中`, today. Write back.

## Step A0: 知見ログの参照

`{XDDP_DIR}/lessons-learned.md` が存在する場合、読み込む。
`#方式検討` `#設計` `#リスク` `#依存関係` タグを持つエントリに注目し、
過去の CR で採用・不採用になった方式の教訓を確認する。
該当する知見があれば、architect-agent へ渡す際の `LESSONS_CONTEXT` に含める。

## Step A: Generate Architecture Memo

Read `~/.claude/templates/xddp.05.rules.md` to get `ARCH_RULES`.
If `{XDDP_DIR}/project-steering.md` exists, read it to get `STEERING_CONTEXT`.

**Agent tool** `subagent_type=xddp-architect-agent`:
```
CR_NUMBER: {CR}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR_PATH}/04_specout/SPO-{CR}.md
SPO_MODULES_DIR: {CR_PATH}/04_specout/modules/
SPO_CROSS_MODULE_FILE: {CR_PATH}/04_specout/cross-module/SPO-{CR}-cross.md (if exists)
TEMPLATE_FILE: ~/.claude/templates/05_design-approach-memo-template.md
OUTPUT_FILE: {CR_PATH}/05_architecture/DSN-{CR}.md
TODAY: {TODAY}
LESSONS_CONTEXT: {lessons-learned.md から抽出した #方式検討 #設計 #リスク #依存関係 タグのエントリ。なければ空}
STEERING_CONTEXT: {project-steering.md の内容。なければ空}
ALTERNATIVES_TASK: {ARCH_RULES の内容をそのまま渡す}
```

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.DSN` rounds)

Update `{CR_PATH}/progress.md` step 6 詳細ステップ → `Step B: AIレビュー中`.

Read `xddp.config.md` (project root). Extract `REVIEW_MAX_ROUNDS.DSN` (default: 2 if key absent). Set `max_rounds` = that value.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: DSN
   TARGET_FILE: {CR_PATH}/05_architecture/DSN-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/review/05_architecture-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit.
   - Issues found, `round < max_rounds` → use **Agent tool** `subagent_type=xddp-architect-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     OUTPUT_FILE: {CR_PATH}/05_architecture/DSN-{CR}.md
     REVIEW_FILE: {CR_PATH}/review/05_architecture-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = max_rounds`, issues remain → append warning to review file.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 6 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR_PATH}/05_architecture/DSN-{CR}.md`
> - AIレビュー結果: `{CR_PATH}/review/05_architecture-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} arch`
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。
> 変更がなければそのまま「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes (edited the file or ran `/xddp.revise`):
- Run one final AI review pass using **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: DSN
  TARGET_FILE: {CR_PATH}/05_architecture/DSN-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/SPO-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/review/05_architecture-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Feed Architecture Decision Back to CRS

Update `{CR_PATH}/progress.md` step 6 状態 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

Read `{CR_PATH}/05_architecture/DSN-{CR}.md`. From the adopted approach, identify items not yet reflected in the CRS:

- 採用方式によって**不要になった要求・仕様**（削除・ステータス変更候補）
- 採用方式によって**新たに判明した制約・非機能要件・インタフェース仕様**
- 採用方式によって**スコープ外となったモジュール・機能**

変更項目が**ない場合はスキップ**。変更項目がある場合:

**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: (not needed here, pass empty)
CHD_FEEDBACK: (採用方式に基づく変更項目リスト。削除・追加・修正を区別して列挙)
TODAY: {TODAY}
AUTHOR_NOTE: 方式検討フィードバックを反映。採用方式に基づく要求・仕様の追加／削除／変更。
```

## Step D: Regenerate CRS Excel (UR-016)

Step C で CRS を更新した場合のみ実施。

**Excel生成は `xddp.md2excel` スキルに委譲する。**

Use the **Agent tool** with the `xddp.md2excel` skill logic, passing:
```
CR_NUMBER: {CR}
```

> **設計方針:** Excel フォーマットの唯一の定義は `~/.claude/skills/xddp.md2excel.md` と `~/.claude/templates/crs_excel_generator.py` にある。
> フォーマットを変更する場合は xddp.md2excel.md と crs_excel_generator.py のみを修正すること。

## Step E: Update progress.md
Step 6 (実装方式検討) → ✅ 完了, 詳細ステップ → `-`. Next command → `/xddp.06.design {CR}`

## Step F: Report in Japanese

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.05.arch.md` の要約も合わせて更新すること。
