---
description: XDDP フェーズ1: 要求分析メモを生成し、別コンテキストでAIレビュー→修正ループを実施する。「要求分析して」「ANA作って」などで起動する。
---

You are orchestrating **XDDP Step 02 — Requirements Analysis**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS (trim whitespace). Let `TODAY` = today's date (YYYY-MM-DD).

Read `xddp.config.md` (project root) and extract `XDDP_DIR` (default: `.` if the key is absent). Let `CR_PATH` = `{XDDP_DIR}/{CR}`.

## Step 0: DOCS_DIR 知識取り込み

> **既存 Step A0 との役割分担:**
> - Step 0（本ステップ）: `baseline_docs/` から**クローズ済み CR の承認済み知見**を取り込む。
>   承認済み仕様書・過去の確定した教訓・用語集が対象。
> - Step A0（既存）: `{XDDP_DIR}/lessons-learned.md` から**現ワークスペースで進行中の知見**を取り込む。
>   `#要求分析` `#仕様定義` `#見落とし` タグに絞り、analyst-agent の `LESSONS_CONTEXT` に渡す。
> 両ステップは読み元が異なり（確定済み vs 進行中）、役割は重複しない。

1. `xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`、ワークスペースルート相対）。
   Let `DOCS` = resolved absolute path of `DOCS_DIR`.
   Read `REPO_NAME` from `xddp.config.md`. If absent or empty, report error and stop.

2. 以下のファイルが存在すれば読み込み、分析コンテキストとして保持する（存在しなければスキップ）:
   - `{DOCS}/shared/glossary.md` — プロジェクト横断の用語集
   - `{DOCS}/shared/lessons-learned.md` — 横断的な知見・教訓（クローズ済み CR 由来）
   - `{DOCS}/{REPO_NAME}/specs/` 配下のすべての `.md` ファイル — 承認済み仕様書（最新版）
   - `{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md` — リポジトリ固有の知見（クローズ済み CR 由来）

3. 読み込んだ知識を以下の目的に使用する:
   - 用語の統一（要求書に現れる概念が既存仕様書の用語と一致しているか確認）
   - 類似 CR 事例の参照（過去の lessons-learned から類似パターン・注意点を抽出）
   - 既存仕様との整合チェック（今回の要求が既承認仕様と矛盾していないか確認）

4. 取り込んだ知識の概要（使用したファイル一覧と、見つかった関連情報の要約）を
   ANA ドキュメントの「参照した既存ドキュメント」節に記録する。
   DOCS_DIR が存在しない場合や対象ファイルがゼロの場合は「参照なし（初回 CR）」と記録する。

## Step 0.5: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 2 (要求分析・整理) → 🔄 進行中, 詳細ステップ → `Step A: ANA生成中`, today. Write back.

## Step A0: 知見ログの参照

`{XDDP_DIR}/lessons-learned.md` が存在する場合、読み込む。
`#要求分析` `#仕様定義` `#見落とし` タグを持つエントリに注目し、
今回の要求書の内容と照合して「過去に同種の漏れや曖昧さが発生していないか」を確認する。
該当する知見があれば、analyst-agent へ渡す際の `LESSONS_CONTEXT` に含める。

## Step A: Generate Analysis Memo

Use the **Agent tool** with `subagent_type=xddp-analyst-agent` and pass:
```
CR_NUMBER: {CR}
REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
TEMPLATE_FILE: ~/.claude/templates/02_req-analysis-memo-template.md
OUTPUT_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
TODAY: {TODAY}
LESSONS_CONTEXT: {lessons-learned.md から抽出した #要求分析 #仕様定義 #見落とし タグのエントリ。なければ空}
CLASSIFICATION_TASK: |
  セクション「2. 要求レベル分類」で、要求書の各 UR を以下の手順で処理すること:
  1. 原文を転記する
  2. UR / SR / SP のいずれに該当するかを判定する
     - UR: ユーザが何をしたいか（抽象的・ユーザ視点）→「〜したい」形式
     - SR: システムが何をすべきか（振る舞い・制約）→「〜のとき、〜して、〜する」形式
     - SP: 具体的な仕様（Before/After で表現できるレベル）→「〜を〜する」形式
  3. 分類根拠を記述する
  4. CRS で使える表現案（分類に合った形式）を生成する
  5. CRS の「理由」フィールド用の根拠文（〜なので / 〜のため）を生成する
```

Wait for the agent to complete and confirm the file was created.

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.ANA` rounds)

Update `{CR_PATH}/progress.md` step 2 詳細ステップ → `Step B: AIレビュー中`.

Read `xddp.config.md` (project root). Extract `REVIEW_MAX_ROUNDS.ANA` (default: 2 if key absent). Set `max_rounds` = that value.

Initialize: `round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. Use the **Agent tool** with `subagent_type=xddp-reviewer` and pass:
   ```
   DOCUMENT_TYPE: ANA
   TARGET_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md files)]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/review/02_analysis-review.md
   ```

2. Read `{CR_PATH}/review/02_analysis-review.md`.
   - If no 🔴 or 🟡 issues → set `issues_remain = false`, exit loop.
   - If 🔴/🟡 issues found and `round < max_rounds` → use **Agent tool** `subagent_type=xddp-analyst-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
     OUTPUT_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
     REVIEW_FILE: {CR_PATH}/review/02_analysis-review.md
     TODAY: {TODAY}
     ```
     Increment `round`, continue loop.
   - If `round = max_rounds` and issues remain → append "⚠️ 未解決の重大指摘あり。人間の判断が必要です。" to the review file. Exit loop.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 2 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR_PATH}/02_analysis/ANA-{CR}.md`
> - AIレビュー結果: `{CR_PATH}/review/02_analysis-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} analysis`
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。
> 変更がなければそのまま「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes (edited the file or ran `/xddp.revise`):
- Run one final AI review pass using **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: ANA
  TARGET_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md files)]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/review/02_analysis-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Update progress.md
Read `{CR_PATH}/progress.md`, set step 2 → ✅ 完了, 詳細ステップ → `-`, today, link `ANA-{CR}.md`.
Set next command → `/xddp.03.req {CR}`.

## Step D: Report in Japanese
Summary: review rounds completed, final issue count, next command.

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.02.analysis.md` の要約も合わせて更新すること。
