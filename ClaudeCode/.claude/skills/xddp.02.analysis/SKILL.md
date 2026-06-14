---
description: XDDP フェーズ1: 要求分析メモを生成し、別コンテキストでAIレビュー→修正ループを実施する。「要求分析して」「ANA作って」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 02 — Requirements Analysis**.

> This step determines whether the CR solves the right problem. A missed ambiguity or misclassified requirement here cascades as a costly defect through every downstream artifact. Orchestrate with rigor.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
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
   Read `REPOS:` mapping. Let `REPOS_KEYS` = list of all repository names from `REPOS:`.
   If `REPOS:` is absent or empty, report error and stop.

2. `AFFECTED_REPOS` = all `REPOS_KEYS`.

3. Read the following files if they exist and retain as analysis context (skip if absent):
   - `{DOCS}/AI_INDEX.md` — knowledge hub navigation index (read to understand available docs)
   - For each `{repo}` in `AFFECTED_REPOS`:
     - Target module spec files under `{DOCS}/{repo}/specs/` — **AI_INDEX.md の「モジュール別最新仕様」セクションで絞り込みを実施し、対象モジュールの `spec.md` のみを読み込む（ディレクトリ全スキャン不要）**
     - `{DOCS}/{repo}/knowledge/lessons-learned.md` — repo-specific lessons (from closed CRs)
   - `{DOCS}/system/specs/use-cases/` — **明示的に参照先として追加**（現行の `{repo}/specs/` と `cross/specs/` のみでは `system/specs/` が漏れるため必須）
     - AI_INDEX.md の「ユースケース一覧」セクションと変更要求書の UR キーワードを照合し、一致したユースケースの `description.md` を読み込む
   - If `IS_MULTI`:
     - Target interface spec files under `{DOCS}/cross/specs/` — **AI_INDEX.md の「クロスインタフェース一覧」セクションで絞り込み**
     - `{DOCS}/cross/knowledge/lessons-learned.md` — cross-repo lessons (if exists)

   **フォールバックロジック（xddp.close 未実施の場合）:**
   - `{DOCS}/system/specs/` が存在しない場合: `{XDDP_DIR}/latest-specs/system/` を代替参照先として使用する
   - `{DOCS}/{repo}/specs/` が存在しない場合: `{XDDP_DIR}/latest-specs/{repo}/` を代替参照先として使用する
   - フォールバック使用時は参照先コメントに「`{DOCS}` への昇格が未完了のため `latest-specs/` から直接参照（degraded mode）」と注記する

   **AI_INDEX.md を用いた絞り込みロジック（詳細）:**
   1. `{DOCS}/AI_INDEX.md` を Read する
   2. **「ユースケース一覧」セクション**（あれば）の照合:
      変更要求書の UR キーワードとユースケース名・目的列を照合し、一致したユースケースの `description.md` を `{DOCS}/system/specs/use-cases/{usecase}/description.md` から読み込む（フォールバック時は `latest-specs/system/use-cases/` から）
   3. **「モジュール別最新仕様」セクション**（あれば）の照合:
      一致したユースケースの「関連モジュール」列、または変更要求書のキーワードと「モジュール別最新仕様」のモジュール名を照合し、対象モジュールの `spec.md` のみを読み込む（ディレクトリ全スキャン不要）
   4. **「code-knowledge インデックス」セクション**（あれば）の照合:
      ステップ3で特定した対象モジュールに対応する `constraints.md` エントリを AI_INDEX.md の code-knowledge インデックスから検索し、存在するファイルを読み込む（ファイルが存在しない場合はスキップ）。
      `_structures/`・`_constants/` はリポジトリ横断のモジュール間知識（構造体関連図・共有定数）のため、対象モジュールの種別に関わらず、AI_INDEX.md の code-knowledge インデックスにエントリが存在すれば全件読み込む（ファイルが存在しない場合はスキップ）。
      読み込んだ制約・注意点は要求分析時の「仕様矛盾検出」・「暗黙の前提確認」に活用する。
   5. 既存の `{DOCS}/{repo}/specs/` 読み込み処理: AI_INDEX.md での絞り込み後は対象モジュールの `spec.md` のみを読み込む

4. Use the imported knowledge for:
   - Term consistency (verify that concepts in the requirements match existing spec terminology)
   - Reference to similar past CRs (extract similar patterns/cautions from past lessons-learned)
   - Consistency check against existing specs (verify the new requirements don't contradict approved specs)

5. Record in the ANA document's "参照した既存ドキュメント" section: files read and a summary of relevant findings.
   code-knowledge から制約・注意点を参照した場合はその内容の要約（どのモジュールのどの制約が今回の要求に関係するか）も記録する。
   フォールバック（degraded mode）を使用した場合はその旨も記録する。
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
TEMPLATE_FILE: ~/.claude/skills/xddp.02.analysis/templates/02_req-analysis-memo-template.md
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

## Step B: Review Loop

Update `{CR_PATH}/progress.md` step 2 詳細ステップ → `Step B: AIレビュー中`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: ANA
  NEXT_DOCUMENT_TYPE: CRS
  CONFIG_KEY: REVIEW_MAX_ROUNDS.ANA
  TARGET_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md files)]
  REVIEW_OUTPUT_FILE: {CR_PATH}/02_analysis/review/02_analysis-review.md
  FIXER_AGENT: xddp-analyst-agent
  FIXER_PARAMS:
    CR_NUMBER: {CR}
    REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
    OUTPUT_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
    REVIEW_FILE: {CR_PATH}/02_analysis/review/02_analysis-review.md
    TODAY: {TODAY}
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 2

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
  NEXT_DOCUMENT_TYPE: CRS
  TARGET_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md files)]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/02_analysis/review/02_analysis-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step B3: Extract project-rulebook Candidates

> **Timing:** Run after Step B2 (human review gate) is confirmed, before Step C (progress.md update).
> If Step B2 had changes, wait for the final AI review pass to complete before this step.
>
> ⚠️ **並行 CR がある場合は xddp.02.analysis の Step B3 を逐次実行してください。**
> 複数の CR が同時に Step B3 を実行すると `project-rulebook.md` の同一ファイルに競合する可能性があります。
> 並行 CR が進行中の場合は、他 CR の Step B3 完了後に本 CR の Step B3 を実行してください。

1. Check whether `{XDDP_DIR}/project-rulebook.md` exists.
   - If not found: tell the user "project-rulebook.md が見つかりませんでした（`{XDDP_DIR}/project-rulebook.md`）。
     `/xddp.01.init` を実行してファイルを生成してから再度お試しください。今回はスキップします。"
     and skip this step.

2. **Idempotency check:** check whether the "## 7. 変更履歴" section in project-rulebook.md already has an entry for {CR} (a row containing {CR}).
   If found: tell the user "{CR} のエントリが変更履歴に見つかりました。Step B3 をスキップします。" and skip this step.

   > **Per-repo steerings:** Candidates that are clearly specific to a single repository (e.g., naming rule for a specific module in one repo) should be noted as `→ project-rulebook-{repo}.md へ追記推奨` in the candidate list. The actual per-repo steering updates are done in xddp.close Step C3.5.

3. Read all `.md` files under `{CR_PATH}/01_requirements/`.

4. Extract items matching the following categories from the requirements and build a candidate list.
   **Identify the target heading in project-rulebook.md by heading name (not section number).**

   | Category | Example items to extract (cross-cutting only, not CR-specific) | Target heading in project-rulebook |
   |---|---|---|
   | Naming conventions | "Unify to 〇〇 naming", "Naming rule is 〇〇" | `## 2. 命名規約` |
   | Architecture decisions | "Adopt 〇〇 pattern", "Migrate to 〇〇 approach" | `## 3. アーキテクチャ決定記録（ADR）` |
   | Prohibitions | "〇〇 is prohibited", "Must not use 〇〇" | `## 5. 禁止事項・注意事項` |
   | Cross-cutting patterns | Error handling policy, async policy, logging policy, etc. — patterns applied codebase-wide.<br>**Exclude: implementation approach for a specific feature, or CR-specific procedures.** | `## 4. 既存パターン・慣習` |

5. If 0 candidates: skip this step (report nothing).

6. If 1 or more candidates: present them to the user in the following format.
   Assign each candidate a unique label `{CategoryName}-{N}`.

   ```
   📋 project-rulebook.md への追記候補が見つかりました。

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

   上記を project-rulebook.md に追記しますか？
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

8. If any items were appended, add an entry to **`## 7. 変更履歴`** in project-rulebook.md:
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
