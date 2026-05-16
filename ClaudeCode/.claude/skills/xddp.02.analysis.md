---
description: XDDP フェーズ1: 要求分析メモを生成し、別コンテキストでAIレビュー→修正ループを実施する。「要求分析して」「ANA作って」などで起動する。
---

You are orchestrating **XDDP Step 02 — Requirements Analysis**.

> This step determines whether the CR solves the right problem. A missed ambiguity or misclassified requirement here cascades as a costly defect through every downstream artifact. Orchestrate with rigor.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md lookup done in xddp.common.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: Import Knowledge from DOCS_DIR

> **Role split with existing Step A0:**
> - Step 0 (this step): imports **approved knowledge from closed CRs** from `baseline_docs/`.
>   Targets: approved specs, finalized lessons, glossary.
> - Step A0 (existing): imports **in-progress knowledge from the current workspace** from `{XDDP_DIR}/lessons-learned.md`.
>   Filters on `#要求分析` `#仕様定義` `#見落とし` tags and passes results to analyst-agent as `LESSONS_CONTEXT`.
> Both steps read from different sources (finalized vs. in-progress) — their roles do not overlap.

1. Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` found earlier (default: `baseline_docs`).
   Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.
   Read `REPO_NAME` from the `xddp.config.md` found earlier. If absent or empty, report error and stop.

2. Read the following files if they exist and retain as analysis context (skip if absent):
   - `{DOCS}/shared/glossary.md` — cross-project glossary
   - `{DOCS}/shared/lessons-learned.md` — cross-project lessons (from closed CRs)
   - All `.md` files under `{DOCS}/{REPO_NAME}/specs/` — approved specs (latest version)
   - `{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md` — repo-specific lessons (from closed CRs)

3. Use the imported knowledge for:
   - Term consistency (verify that concepts in the requirements match existing spec terminology)
   - Reference to similar past CRs (extract similar patterns/cautions from past lessons-learned)
   - Consistency check against existing specs (verify the new requirements don't contradict approved specs)

4. Record in the ANA document's "参照した既存ドキュメント" section: files read and a summary of relevant findings.
   If DOCS_DIR does not exist or no target files were found, record "参照なし（初回 CR）".

## Step 0.5: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 2 (要求分析・整理) → 🔄 進行中, 詳細ステップ → `Step A: ANA生成中`, today. Write back.

## Step A0: Reference Lessons Learned Log

If `{XDDP_DIR}/lessons-learned.md` exists, read it.
Focus on entries tagged `#要求分析` `#仕様定義` `#見落とし` and cross-reference with the current requirements
to check whether similar oversights or ambiguities occurred in the past.
Include relevant findings in `LESSONS_CONTEXT` when passing to the analyst-agent.

## Step A: Generate Analysis Memo

Use the **Agent tool** with `subagent_type=xddp-analyst-agent` and pass:
```
CR_NUMBER: {CR}
REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
TEMPLATE_FILE: ~/.claude/templates/02_req-analysis-memo-template.md
OUTPUT_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
TODAY: {TODAY}
LESSONS_CONTEXT: {entries tagged #要求分析 #仕様定義 #見落とし extracted from lessons-learned.md; empty if none}
CLASSIFICATION_TASK: |
  In section "2. 要求レベル分類", process each UR in the requirements as follows:
  1. Transcribe the original text.
  2. Classify as UR / SR / SP:
     - UR: what the user wants to do (abstract, user perspective) → "〜したい" form
     - SR: what the system must do (behavior/constraint) → "〜のとき、〜して、〜する" form
     - SP: concrete spec (expressible as Before/After) → "〜を〜する" form
  3. Describe the classification rationale.
  4. Generate a CRS-ready expression (in the format matching the classification).
  5. Generate a rationale sentence for the CRS "理由" field (〜なので / 〜のため).
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

## Step B3: Extract project-steering Candidates

> **Timing:** Run after Step B2 (human review gate) is confirmed, before Step C (progress.md update).
> If Step B2 had changes, wait for the final AI review pass to complete before this step.

1. Check whether `{XDDP_DIR}/project-steering.md` exists.
   - If not found: tell the user "project-steering.md が見つかりませんでした（`{XDDP_DIR}/project-steering.md`）。
     `/xddp.01.init` を実行してファイルを生成してから再度お試しください。今回はスキップします。"
     and skip this step.

2. **Idempotency check:** check whether the "## 7. 変更履歴" section in project-steering.md already has an entry for {CR} (a row containing {CR}).
   If found: tell the user "{CR} のエントリが変更履歴に見つかりました。Step B3 をスキップします。" and skip this step.

3. Read all `.md` files under `{CR_PATH}/01_requirements/`.

4. Extract items matching the following categories from the requirements and build a candidate list.
   **Identify the target heading in project-steering.md by heading name (not section number).**

   | Category | Example items to extract (cross-cutting only, not CR-specific) | Target heading in project-steering |
   |---|---|---|
   | Naming conventions | "Unify to 〇〇 naming", "Naming rule is 〇〇" | `## 2. 命名規約` |
   | Architecture decisions | "Adopt 〇〇 pattern", "Migrate to 〇〇 approach" | `## 3. アーキテクチャ決定記録（ADR）` |
   | Prohibitions | "〇〇 is prohibited", "Must not use 〇〇" | `## 5. 禁止事項・注意事項` |
   | Cross-cutting patterns | Error handling policy, async policy, logging policy, etc. — patterns applied codebase-wide.<br>**Exclude: implementation approach for a specific feature, or CR-specific procedures.** | `## 4. 既存パターン・慣習` |

5. If 0 candidates: skip this step (report nothing).

6. If 1 or more candidates: present them to the user in the following format.
   Assign each candidate a unique label `{CategoryName}-{N}`.

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

7. Process the user's response:
   - "すべて追記" → append all candidates to the relevant heading's code block (or ADR heading format)
   - "{ラベル名} のみ追記" → append only the specified candidate(s)
   - "スキップ" → do nothing, proceed to next step

   **Append format rules:**
   - `## 2. 命名規約`, `## 4. 既存パターン・慣習`, `## 5. 禁止事項・注意事項`: append inside the existing code block (``` ``` ```) at the end
   - `## 3. アーキテクチャ決定記録（ADR）`: append outside code blocks as a `### ADR-NNN: {title}` heading
     (ADR number = existing max + 1)

8. If any items were appended, add an entry to **`## 7. 変更履歴`** in project-steering.md:
   ```
   | {TODAY} | {CR} | {categories appended and counts, e.g., 禁止事項1件・命名規約1件}（req より抽出） |
   ```

## Step C: Update progress.md
Read `{CR_PATH}/progress.md`, set step 2 → ✅ 完了, 詳細ステップ → `-`, today, link `ANA-{CR}.md`.
Set next command → `/xddp.03.req {CR}`.

## Step D: Report in Japanese
Summary: review rounds completed, final issue count, next command.

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.02.analysis.md`.
