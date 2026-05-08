---
description: XDDP フェーズ1: 要求分析メモを生成し、別コンテキストでAIレビュー→修正ループを実施する。「要求分析して」「ANA作って」などで起動する。
---

You are orchestrating **XDDP Step 02 — Requirements Analysis**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS (trim whitespace). Let `TODAY` = today's date (YYYY-MM-DD).

Find `xddp.config.md` by searching upward from cwd: check cwd first, then each parent directory in order. Let `WORKSPACE_ROOT` = the directory where the file is found. If not found at filesystem root, report "xddp.config.md が見つかりません。ワークスペースルートまたはそのサブディレクトリで実行してください。" and stop.
Extract `XDDP_DIR` (default: `xddp` if the key is absent). Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: DOCS_DIR 知識取り込み

> **既存 Step A0 との役割分担:**
> - Step 0（本ステップ）: `baseline_docs/` から**クローズ済み CR の承認済み知見**を取り込む。
>   承認済み仕様書・過去の確定した教訓・用語集が対象。
> - Step A0（既存）: `{XDDP_DIR}/lessons-learned.md` から**現ワークスペースで進行中の知見**を取り込む。
>   `#要求分析` `#仕様定義` `#見落とし` タグに絞り、analyst-agent の `LESSONS_CONTEXT` に渡す。
> 両ステップは読み元が異なり（確定済み vs 進行中）、役割は重複しない。

1. ヘッダーで発見した `{WORKSPACE_ROOT}/xddp.config.md` から `DOCS_DIR` を読む（デフォルト: `baseline_docs`）。
   Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.
   Read `REPO_NAME` from the `xddp.config.md` found earlier. If absent or empty, report error and stop.

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

Read the `xddp.config.md` found earlier (`{WORKSPACE_ROOT}/xddp.config.md`). Extract `REVIEW_MAX_ROUNDS.ANA` (default: 2 if key absent). Set `max_rounds` = that value.

Initialize: `round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. Use the **Agent tool** with `subagent_type=xddp-reviewer` and pass:
   ```
   DOCUMENT_TYPE: ANA
   TARGET_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
   REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md files)]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/02_analysis/review/02_analysis-review.md
   ```

2. Read `{CR_PATH}/02_analysis/review/02_analysis-review.md`.
   - If no 🔴 or 🟡 issues → set `issues_remain = false`, exit loop.
   - If 🔴/🟡 issues found and `round < max_rounds` → use **Agent tool** `subagent_type=xddp-analyst-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
     OUTPUT_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
     REVIEW_FILE: {CR_PATH}/02_analysis/review/02_analysis-review.md
     TODAY: {TODAY}
     ```
     Increment `round`, continue loop.
   - If `round = max_rounds` and issues remain → append "⚠️ 未解決の重大指摘あり。人間の判断が必要です。" to the review file. Exit loop.

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 2 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR_PATH}/02_analysis/ANA-{CR}.md`
> - AIレビュー結果: `{CR_PATH}/02_analysis/review/02_analysis-review.md`
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
  OUTPUT_FILE: {CR_PATH}/02_analysis/review/02_analysis-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step B3: project-steering 追記候補の抽出

> **実行タイミング:** Step B2（人レビューゲート）確認後・Step C（progress.md 更新）の前に実行する。
> Step B2 で変更があった場合は最終 AI レビューパスが完了してから本ステップに進む。

1. `{XDDP_DIR}/project-steering.md` が存在するか確認する。
   - 存在しない場合: 「project-steering.md が見つかりませんでした（`{XDDP_DIR}/project-steering.md`）。
     `/xddp.01.init` を実行してファイルを生成してから再度お試しください。今回はスキップします。」
     とユーザに伝え、このステップをスキップする。

2. **冪等性チェック:** project-steering.md の「## 7. 変更履歴」セクションに {CR} の追記済みエントリが
   存在するか確認する（列に {CR} が含まれる行の有無）。
   存在する場合: 「{CR} の追記済みエントリが変更履歴に見つかりました。Step B3 をスキップします。」
   とユーザに伝え、このステップをスキップする。

3. `{CR_PATH}/01_requirements/` 配下の全 `.md` ファイルを読み込む。

4. 以下のカテゴリに該当する記述を req から抽出し、追記候補リストを作成する。
   **カテゴリ名で project-steering.md の対象見出しを特定する（セクション番号ではなく見出し名で照合する）。**

   | カテゴリ | 抽出対象の例（この CR 固有でなく横断的に適用すべきもののみ） | project-steering の対象見出し |
   |---|---|---|
   | 命名規約 | 「〇〇という名前で統一する」「命名規則は〇〇とする」 | `## 2. 命名規約` |
   | アーキテクチャ決定 | 「〇〇パターンを採用する」「〇〇方式に移行する」 | `## 3. アーキテクチャ決定記録（ADR）` |
   | 禁止事項 | 「〇〇は使用禁止」「〇〇してはならない」 | `## 5. 禁止事項・注意事項` |
   | 横断パターン | エラーハンドリング方針・非同期処理方針・ログ方針など<br>コードベース全体に適用する横断的パターン。<br>**特定機能の実装方式・この CR 固有の手順は対象外。** | `## 4. 既存パターン・慣習` |

5. 候補が0件の場合はこのステップをスキップする（何も報告しない）。

6. 候補が1件以上ある場合は、以下の形式でユーザに提示する。
   各候補には「カテゴリ名-連番」の一意ラベルを付与する。

   ```
   📋 project-steering.md への追記候補が見つかりました。

   [禁止事項-1]
   根拠（req より）: 「〇〇ライブラリは使用禁止とする」
   追記先: ## 5. 禁止事項・注意事項
   追記案（コードブロック内末尾に追加）:
     ❌ 〇〇ライブラリの使用禁止（{CR} より）

   [命名規約-1]
   根拠（req より）: 「APIエンドポイントは /kebab-case/{id} に統一する」
   追記先: ## 2. 命名規約
   追記案（コードブロック内末尾に追加）:
     # APIエンドポイント: /kebab-case/{id}（{CR} より）

   上記を project-steering.md に追記しますか？
   ラベル名で指定してください（例: 「すべて追記」「禁止事項-1 のみ追記」「スキップ」）。
   ```

7. ユーザの回答に応じて処理する：
   - 「すべて追記」→ 全候補を該当見出しのコードブロック末尾（または ADR 見出し形式）に追記する
   - 「{ラベル名} のみ追記」→ 指定ラベルの候補のみ追記する
   - 「スキップ」→ 何もせず次のステップへ進む

   **追記フォーマットのルール:**
   - `## 2. 命名規約`・`## 4. 既存パターン・慣習`・`## 5. 禁止事項・注意事項`: 既存のコードブロック（``` ``` ）末尾に追記する
   - `## 3. アーキテクチャ決定記録（ADR）`: コードブロック外に `### ADR-NNN: {タイトル}` 見出し形式で追記する
     （ADR 番号は既存エントリの最大番号 +1 とする）

8. 追記した場合のみ、project-steering.md の **`## 7. 変更履歴`** にエントリを追加する：
   ```
   | {TODAY} | {CR} | {追記したカテゴリ名と件数を列挙。例: 禁止事項1件・命名規約1件}（req より抽出） |
   ```

## Step C: Update progress.md
Read `{CR_PATH}/progress.md`, set step 2 → ✅ 完了, 詳細ステップ → `-`, today, link `ANA-{CR}.md`.
Set next command → `/xddp.03.req {CR}`.

## Step D: Report in Japanese
Summary: review rounds completed, final issue count, next command.

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.02.analysis.md` の要約も合わせて更新すること。
