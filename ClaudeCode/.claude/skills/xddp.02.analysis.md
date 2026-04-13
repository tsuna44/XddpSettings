---
description: XDDP フェーズ1: 要求分析メモを生成し、別コンテキストでAIレビュー→修正ループを実施する。「要求分析して」「ANA作って」などで起動する。
---

You are orchestrating **XDDP Step 02 — Requirements Analysis**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS (trim whitespace). Let `TODAY` = today's date (YYYY-MM-DD).

## Step 0: Mark In-Progress
Read `{CR}/progress.md`. Set step 2 (要求分析・整理) → 🔄 進行中, 詳細ステップ → `Step A: ANA生成中`, today. Write back.

## Step A0: 知見ログの参照

`lessons-learned.md`（プロジェクトルート）が存在する場合、読み込む。
`#要求分析` `#仕様定義` `#見落とし` タグを持つエントリに注目し、
今回の要求書の内容と照合して「過去に同種の漏れや曖昧さが発生していないか」を確認する。
該当する知見があれば、analyst-agent へ渡す際の `LESSONS_CONTEXT` に含める。

## Step A: Generate Analysis Memo

Use the **Agent tool** with `subagent_type=xddp-analyst-agent` and pass:
```
CR_NUMBER: {CR}
REQUIREMENTS_DIR: {CR}/01_requirements/
TEMPLATE_FILE: ~/.claude/templates/02_req-analysis-memo-template.md
OUTPUT_FILE: {CR}/02_analysis/ANA-{CR}.md
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

## Step B: Review Loop (max 5 iterations)

Update `{CR}/progress.md` step 2 詳細ステップ → `Step B: AIレビュー中`.

Initialize: `round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ 5`:

1. Use the **Agent tool** with `subagent_type=xddp-reviewer` and pass:
   ```
   DOCUMENT_TYPE: ANA
   TARGET_FILE: {CR}/02_analysis/ANA-{CR}.md
   REFERENCE_FILES: [{CR}/01_requirements/ (all .md files)]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR}/review/02_analysis-review.md
   ```

2. Read `{CR}/review/02_analysis-review.md`.
   - If no 🔴 or 🟡 issues → set `issues_remain = false`, exit loop.
   - If 🔴/🟡 issues found and `round < 5` → use **Agent tool** `subagent_type=xddp-analyst-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     REQUIREMENTS_DIR: {CR}/01_requirements/
     OUTPUT_FILE: {CR}/02_analysis/ANA-{CR}.md
     REVIEW_FILE: {CR}/review/02_analysis-review.md
     TODAY: {TODAY}
     ```
     Increment `round`, continue loop.
   - If `round = 5` and issues remain → append "⚠️ 未解決の重大指摘あり。人間の判断が必要です。" to the review file. Exit loop.

## Step B2: Human Review Gate

Update `{CR}/progress.md` step 2 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR}/02_analysis/ANA-{CR}.md`
> - AIレビュー結果: `{CR}/review/02_analysis-review.md`
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
  TARGET_FILE: {CR}/02_analysis/ANA-{CR}.md
  REFERENCE_FILES: [{CR}/01_requirements/ (all .md files)]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR}/review/02_analysis-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Update progress.md
Read `{CR}/progress.md`, set step 2 → ✅ 完了, 詳細ステップ → `-`, today, link `ANA-{CR}.md`.
Set next command → `/xddp.03.req {CR}`.

## Step D: Report in Japanese
Summary: review rounds completed, final issue count, next command.

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.02.analysis.md` の要約も合わせて更新すること。
