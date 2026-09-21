---
name: xddp-02-analysis
description: XDDP フェーズ1: 要求分析メモを生成し、別コンテキストでAIレビュー→修正ループを実施する。「要求分析して」「ANA作って」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 02 — Requirements Analysis**.

> This step determines whether the CR solves the right problem. A missed ambiguity or misclassified requirement here cascades as a costly defect through every downstream artifact. Orchestrate with rigor.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md lookup done in xddp-common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
DOCS_DIR, DOCS, REPOS_KEYS, IS_MULTI, CR_PROFILE.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: Import Knowledge from DOCS_DIR

> **Role split with existing Step A0:**
> - Step 0 (this step): imports **approved knowledge from closed CRs** from `baseline_docs/`.
>   Targets: approved specs, finalized lessons, glossary.
> - Step A0 (existing): imports **in-progress knowledge from the current workspace** from `{XDDP_DIR}/lessons-learned.md`.
>   Filters on `#要求分析` `#仕様定義` `#見落とし` tags via the tag index (selective read, not full-file read) and passes results to analyst-agent as `LESSONS_CONTEXT`.
> Both steps read from different sources (finalized vs. in-progress) — their roles do not overlap.

1. （`DOCS_DIR`/`DOCS`/`REPOS_KEYS` は CR Resolution で取得済みのためここでの再読み取りは不要）
   If `REPOS:` is absent or empty, report error and stop.

2. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Resolve Affected Repos" with:
     REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
   → let `AFFECTED_REPOS`.

3. **参照先パスの解決（決定的処理はスクリプトへ委譲）:**
   本手順で Read するのは絞り込みの入力となる `{CR_PATH}/01_requirements/` 配下の変更要求書のみ。
   AI_INDEX.md 照合・フォールバック・正規化・区切り文字ガード・`DOMAIN_REF_MODE` 判定は
   `domain_refs.py` が決定的に行い、絞り込んで確定した**既存知識の参照先ファイルは Read しない**
   （実体の読解は Step A で xddp-analyst-agent が行う）。

   3-0. `{CR_PATH}/01_requirements/` 配下の `.md` を Read し、以降の照合に使う
        **キーワード集合**（UR の対象語・モジュール名・機能名等）を抽出する。
        これは絞り込みの入力であり、既存知識の読解ではない（変更要求書は CR 固有の小さな文書であり、
        Step A で子エージェントも読むが、親側でも絞り込みのために必要なため重複を許容する）。
        抽出結果を改行区切りで一時ファイル `{CR_PATH}/.step0-keywords.txt` へ書き出す。

   3-1. 次を Bash 実行する:
        `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-02-analysis/scripts/domain_refs.py resolve --workspace-root {WORKSPACE_ROOT} --xddp-dir {XDDP_DIR} --docs {DOCS} --affected-repos {AFFECTED_REPOS をカンマ区切りにした文字列} {IS_MULTI の場合のみ}--is-multi --keywords-file {CR_PATH}/.step0-keywords.txt --out {CR_PATH}/.step0-domain-refs.json`

   3-2. 終了コード 0 の場合、`--out` で指定した JSON を Read し、
        `domain_ref_paths` を `DOMAIN_REF_PATHS`、`domain_ref_mode` を `DOMAIN_REF_MODE` として得る。
        終了コードが 0 以外の場合は人に報告して停止する（参照知識の欠落は ANA の品質に直結するため
        フォールバックしない）。

4. `DOMAIN_REF_PATHS`・`DOMAIN_REF_MODE` は手順3-2 で取得済みの値をそのまま使う
   （ANA への記録は Step A で xddp-analyst-agent が行う。Step 0 実行時点で ANA ファイルは未生成のため）。

## Step 0.5: Mark In-Progress
Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 2, STATE: 🔄 進行中, DETAIL_STEP: `Step A: ANA生成中`

Read `~/.claude/skills/xddp-common/procedures/snapshot-phase-baseline.md`, apply "## Snapshot Phase Baseline" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 2

## Step A0: Reference Lessons Learned Log

Read `~/.claude/skills/xddp-common/procedures/load-lessons-context.md`, apply "## Load Lessons Context" with:
  LESSONS_FILE: {XDDP_DIR}/lessons-learned.md
  TARGET_TAGS: [#要求分析, #仕様定義, #見落とし]
→ let `LESSONS_CONTEXT`.

## Step A0.5: Load Domain Constraints

Read `~/.claude/skills/xddp-common/procedures/load-domain-constraints.md`, apply "## Load Domain Constraints" with:
  XDDP_DIR: {XDDP_DIR}
→ let `DOMAIN_CONSTRAINTS`.

Let `CLASSIFICATION_TASK` =
  In section "2. 要求レベル分類", process each UR in the requirements as follows:
  1. Transcribe the original text.
  2. Classify as UR / SR / SP:
     - UR: what the user wants to do (abstract, user perspective) → "〜したい" form
     - SR: what the system must do (behavior/constraint) → "〜のとき、〜して、〜する" form
     - SP: concrete spec (expressible as Before/After) → "〜を〜する" form
  3. Describe the classification rationale.
  4. Generate a CRS-ready expression (in the format matching the classification).
  5. Generate a rationale sentence for the CRS "理由" field (〜なので / 〜のため).
（`CR_PROFILE` にも `{repo}` にも依存しないため、下記 Step A-profile（quick）と Step A（full）の
両方からこの1箇所の定義をそのまま参照する）

## Step A-profile: CR_PROFILE Branch

If `CR_PROFILE` = `quick`:
  1. Read `~/.claude/skills/xddp-02-analysis/templates/02_req-analysis-memo-template.md`
     （テンプレート存在確認のフェイルファストプリチェック。読み取り内容は変数に捕捉せず、ファイル不在時は
     Read 自体のエラーで停止する）。
  2. Use the **Agent tool** with `subagent_type=xddp-analyst-agent` and pass:
       ```
       CR_NUMBER: {CR}
       REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
       TEMPLATE_FILE: ~/.claude/skills/xddp-02-analysis/templates/02_req-analysis-memo-template.md
       OUTPUT_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
       TODAY: {TODAY}
       （LESSONS_CONTEXT が空でない場合のみ追加）LESSONS_CONTEXT: {LESSONS_CONTEXT}
       DOMAIN_REF_MODE: {DOMAIN_REF_MODE}
       （DOMAIN_REF_PATHS が空でない場合のみ追加）DOMAIN_REF_PATHS: {各要素を ` ; ` で連結した1行}
       （DOMAIN_CONSTRAINTS が空でない場合のみ追加）DOMAIN_CONSTRAINTS: |
         {DOMAIN_CONSTRAINTS}
       CLASSIFICATION_TASK: |
         {pass CLASSIFICATION_TASK content as-is}
       QUICK_PROFILE: `true`
       ```
     → generates `{CR_PATH}/02_analysis/ANA-{CR}.md`（軽量 ANA。出力範囲は `xddp-analyst-agent.md` の
     `QUICK_PROFILE` 定義に従う）。
  3. Wait for the agent to complete and confirm the file was created.
  4. Resolve Glossary Paths for the spec-writer:
       Let `GLOSSARY_PATHS` = 次の候補パスのうち実在するファイルの絶対パスを ` ; ` で連結した1行:
         - `{DOCS}/glossary.md`
         - For each `{repo}` in `AFFECTED_REPOS`: `{DOCS}/{repo}/knowledge/glossary.md`
         - If `IS_MULTI`: `{DOCS}/cross/knowledge/glossary.md`
       該当ファイルが1件もない場合、`GLOSSARY_PATHS` は空文字列とする。
       （`AFFECTED_REPOS` は Step 0 手順2 で解決済みの値をそのまま用いる）
  5. Use the **Agent tool** with `subagent_type=xddp-spec-writer-agent` and pass `MODE: create`:
       ```
       CR_NUMBER: {CR}
       MODE: create
       REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
       ANA_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
       CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
       TEMPLATE_FILE: ~/.claude/skills/xddp-03-req/templates/03_change-req-spec-template.md
       DEVELOPMENT_MODE: {DEVELOPMENT_MODE}
       （GLOSSARY_PATHS が空でない場合のみ追加）GLOSSARY_PATHS: {GLOSSARY_PATHS}
       TODAY: {TODAY}
       AUTHOR_NOTE: quick profile 統合生成
       QUICK_PROFILE: `true`
       ```
     → generates `{CR_PATH}/03_change-requirements/CRS-{CR}.md`（軽量 CRS）。
  6. Run `artifact_lint.py --doc-type CRS` on the generated CRS file
     （生成直後のフェイルファスト構造チェック。後段のレビューループでも同じ lint が毎ラウンド実行
     されるが、目的が異なるため二重実行ではない — 本手順は生成エージェント自体の構造バグを
     レビューラウンドに進む前に検出するゲート、後段はレビュアーへ検査結果を渡すためのもの）:
       `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/artifact_lint.py --file {CR_PATH}/03_change-requirements/CRS-{CR}.md --doc-type CRS`
     → let `LINT_RESULTS`（stdout の JSON 1オブジェクト）。
     If any element of `LINT_RESULTS.crs.issues` has `"level": "error"`: report the errors to the user and stop
     （fixer を介さず即座に停止する。`LINT_RESULTS.ok` は常に `true` を返すフィールドのため判定に
     使わない。実際の構造検査結果は `LINT_RESULTS.crs.issues` 配列の `"level": "error"` 要素の有無で
     判定する）。
  7. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
       CR_PATH: {CR_PATH}, STEP_NUM: 2, STATE: 🔄 進行中, DETAIL_STEP: `Step A-profile: AIレビュー中（quick、最大1ラウンド）`
  7b. Resolve the next document type:
       If `DEVELOPMENT_MODE` = `new`: Let `CRS_NEXT_DOCUMENT_TYPE` = `CHD`
         （`new` では工程4が `xddp-04-specout/SKILL.md` の「## Step -1: DEVELOPMENT_MODE Check」で
         即座にスキップされ、quick では同じ Step -1 が工程5のスキップも記録して `/xddp-06-design` を
         案内する。この経路では CRS を実際に受け取るのは CHD である）。
       Else: Let `CRS_NEXT_DOCUMENT_TYPE` = `SPO`（工程4が実行されるため）。
  8. Read `~/.claude/skills/xddp-common/procedures/review-loop.md`, apply "## Review Loop" with:
       DOCUMENT_TYPE: CRS
       NEXT_DOCUMENT_TYPE: {CRS_NEXT_DOCUMENT_TYPE}
       CONFIG_KEY: REVIEW_MAX_ROUNDS.CRS
       MAX_ROUNDS_OVERRIDE: `1`
       TARGET_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
       REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md), {CR_PATH}/02_analysis/ANA-{CR}.md]
       REVIEW_OUTPUT_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md
       FIXER_AGENT: xddp-spec-writer-agent
       FIXER_PARAMS:
         CR_NUMBER: {CR}
         MODE: fix
         CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
         REVIEW_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md
         TODAY: {TODAY}
         AUTHOR_NOTE: レビュー指摘修正（quick, round {round}）
         QUICK_PROFILE: `true`
       PROGRESS_CR_PATH: {CR_PATH}
       PROGRESS_STEP_NUM: 2
       EXTRA_REVIEWER_PARAMS:
         QUICK_PROFILE: `true`
  9. Read `~/.claude/skills/xddp-common/procedures/regenerate-crs-excel.md`, apply "## Regenerate CRS Excel" with:
       CR_PATH: {CR_PATH}
       CR: {CR}
  10. 実ファイルの「## Step B3: Extract project-rulebook Candidates」の手順をそのまま実行する
     （Step B3 は要求書から命名規約・ADR・禁止事項・ドメイン制約を抽出して project-rulebook.md へ
     蓄積する知識ベース更新処理であり、quick でも省略しない。CRS レビュー完了後・progress.md 更新前の
     本手順の位置で実行する）。
  11. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
       CR_PATH: {CR_PATH}, STEP_NUM: 2, STATE: ✅ 完了, DETAIL_STEP: `-`,
       ARTIFACT_LINK: `[ANA-{CR}.md](02_analysis/ANA-{CR}.md)`
  12. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
       CR_PATH: {CR_PATH}, STEP_NUM: 3, STATE: ⏭️ スキップ（工程2に統合）, DETAIL_STEP: `-`,
       ARTIFACT_LINK: `[CRS-{CR}.md](03_change-requirements/CRS-{CR}.md)`
  12b. Set next command → `/xddp-04-specout {CR}`
       （`DEVELOPMENT_MODE` によらず `/xddp-04-specout` を案内する。`new` の場合はそこで工程4a・4b・5の
       スキップが記録され `/xddp-06-design` へ案内が連鎖する）
  13. Tell the user:
     > `CR_PROFILE: quick` のため、工程2で軽量 ANA と CRS を統合生成し、CRS へ1ラウンドのAIレビューを実施しました。
     > **次のコマンド:** `/xddp-04-specout {CR}`
  14. Stop（実ファイルの Step A・Step B・Step B2・Step C・Step D には到達しない。Step B3 のみ上記
     手順10として quick パスからも実行する）。

Else（`CR_PROFILE` = `full`）:
  下記の Step A 以降にそのまま進む。

## Step A: Generate Analysis Memo

Use the **Agent tool** with `subagent_type=xddp-analyst-agent` and pass:
```
CR_NUMBER: {CR}
REQUIREMENTS_DIR: {CR_PATH}/01_requirements/
TEMPLATE_FILE: ~/.claude/skills/xddp-02-analysis/templates/02_req-analysis-memo-template.md
OUTPUT_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
TODAY: {TODAY}
（LESSONS_CONTEXT が空でない場合のみ追加）LESSONS_CONTEXT: {LESSONS_CONTEXT}
DOMAIN_REF_MODE: {DOMAIN_REF_MODE}
（DOMAIN_REF_PATHS が空でない場合のみ追加）DOMAIN_REF_PATHS: {各要素を ` ; ` で連結した1行}
（DOMAIN_CONSTRAINTS が空でない場合のみ追加）DOMAIN_CONSTRAINTS: |
  {DOMAIN_CONSTRAINTS}
CLASSIFICATION_TASK: |
  {pass CLASSIFICATION_TASK content as-is}
```

Wait for the agent to complete and confirm the file was created.

## Step B: Review Loop

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 2, STATE: 🔄 進行中, DETAIL_STEP: `Step B: AIレビュー中`

Read `~/.claude/skills/xddp-common/procedures/review-loop.md`, apply "## Review Loop" with:
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
    DOMAIN_REF_MODE: {DOMAIN_REF_MODE}
    （DOMAIN_REF_PATHS が空でない場合のみ追加）DOMAIN_REF_PATHS: {各要素を ` ; ` で連結した1行}
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 2

## Step B2: Human Review Gate

Read `~/.claude/skills/xddp-common/procedures/human-review-gate.md`, apply "## Human Review Gate" with:
  CR_PATH: {CR_PATH}
  STEP_NUM: 2
  STEP_LABEL: `Step B2`
  ARTIFACTS_TEXT: |
    - 成果物: `{CR_PATH}/02_analysis/ANA-{CR}.md`
    - AIレビュー結果: `{CR_PATH}/02_analysis/review/02_analysis-review.md`
  REVISE_COMMAND: `/xddp-revise {CR} analysis`
→ let `CHANGED`.

If `CHANGED`:
Read `~/.claude/skills/xddp-common/procedures/final-review-pass.md`, apply "## Final Review Pass" with:
  DOCUMENT_TYPE: ANA
  NEXT_DOCUMENT_TYPE: CRS
  TARGET_FILE: {CR_PATH}/02_analysis/ANA-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/01_requirements/ (all .md files)]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/02_analysis/review/02_analysis-review.md

## Step B3: Extract project-rulebook Candidates

> **Timing:** Run after Step B2 (human review gate) is confirmed, before Step C (progress.md update).
> If Step B2 had changes, wait for the final AI review pass to complete before this step.
>
> ⚠️ **並行 CR がある場合は xddp-02-analysis の Step B3 を逐次実行してください。**
> 複数の CR が同時に Step B3 を実行すると `project-rulebook.md` の同一ファイルに競合する可能性があります。
> 並行 CR が進行中の場合は、他 CR の Step B3 完了後に本 CR の Step B3 を実行してください。

1. Check whether `{XDDP_DIR}/project-rulebook.md` exists.
   - If not found: tell the user "project-rulebook.md が見つかりませんでした（`{XDDP_DIR}/project-rulebook.md`）。
     `/xddp-01-init` を実行してファイルを生成してから再度お試しください。今回はスキップします。"
     and skip this step.

2. **Idempotency check:** check whether the "## 7. 変更履歴" section in project-rulebook.md already has an entry for {CR} (a row containing {CR}).
   If found: tell the user "{CR} のエントリが変更履歴に見つかりました。Step B3 をスキップします。" and skip this step.

   > **Per-repo steerings:** Candidates that are clearly specific to a single repository (e.g., naming rule for a specific module in one repo) should be noted as `→ project-rulebook-{repo}.md へ追記推奨` in the candidate list. The actual per-repo steering updates are done in xddp-close Step C3.5.

3. Read all `.md` files under `{CR_PATH}/01_requirements/`.

4. Extract items matching the following categories from the requirements and build a candidate list.
   **Identify the target heading in project-rulebook.md by heading name (not section number).**

   | Category | Example items to extract (cross-cutting only, not CR-specific) | Target heading in project-rulebook |
   |---|---|---|
   | Naming conventions | "Unify to 〇〇 naming", "Naming rule is 〇〇" | `## 2. 命名規約` |
   | Architecture decisions | "Adopt 〇〇 pattern", "Migrate to 〇〇 approach" | `## 3. アーキテクチャ決定記録（ADR）` |
   | Prohibitions | "〇〇 is prohibited", "Must not use 〇〇" | `## 5. 禁止事項・注意事項` |
   | Cross-cutting patterns | Error handling policy, async policy, logging policy, etc. — patterns applied codebase-wide.<br>**Exclude: implementation approach for a specific feature, or CR-specific procedures.** | `## 4. 既存パターン・慣習` |
   | ドメイン制約 | 「〇〇規格に準拠すること」「〇〇の上限は〇〇」など、**外部由来で CR 横断的に効く制約**。<br>**除外: 今回の CR だけで有効な数値・条件。** | `## 1.6 ドメイン制約` |

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

   [ドメイン制約-1]
   根拠（req より）: 「〇〇規格 XYZ-123 に準拠すること」
   追記先: ## 1.6 ドメイン制約
   追記案（テーブル行として追加）:
     | 準拠すべき規格・法令 | 〇〇規格 XYZ-123 に準拠する | XYZ-123 | 〇〇に関する要求全般 |

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
   - `## 1.6 ドメイン制約`: append as a new row to the existing table
     （列: 種別 / 制約内容 / 根拠 / 影響する要求の観点）。種別列には project-rulebook-template.md §1.6
     で事前定義された6種別（準拠すべき規格・法令／安全性・信頼性の要件／性能・リソースの下限／上限／
     データの取り扱い制約／互換性の維持義務／運用・保守上の制約）のうち、制約内容に最も適合するものを
     選択する。根拠が req 原文から明確に読み取れない場合は根拠列に「未確認」と記載する
     （project-rulebook-template.md §1.6 の記入時の注意に合わせる）

8. If any items were appended, add an entry to **`## 7. 変更履歴`** in project-rulebook.md:
   ```
   | {TODAY} | {CR} | {categories appended and counts, e.g., 禁止事項1件・命名規約1件}（req より抽出） |
   ```

## Step C: Update progress.md
Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 2, STATE: ✅ 完了, DETAIL_STEP: `-`,
  ARTIFACT_LINK: `[ANA-{CR}.md](02_analysis/ANA-{CR}.md)`
Set next command → `/xddp-03-req {CR}`.

## Step D: Report in Japanese
Summary: review rounds completed, final issue count, next command.
