---
description: XDDP フェーズ3: 変更設計書（CHD）を作成し、AIレビュー→修正ループ＋変更要求仕様書へのフィードバックを実施する。「変更設計書を作って」「設計書を書いて」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 06 (process steps 07-08) — Change Design Document + CRS Feedback**.

> The CHD produced here is the design specification coders execute without asking questions. Every gap or ambiguity becomes a defect in the code. Orchestrate with precision — completeness in interface definitions, Before/After design diagrams, and confirmation items is non-negotiable.
> The CHD is a design document, not source code. Coders implement from the design specs.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Build `REPOS_MAP` (repo name → path).
Let `REPOS_KEYS` = list of all repository names. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).

Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.

`AFFECTED_REPOS` = all `REPOS_KEYS`.
Let `HAS_CROSS` = (IS_MULTI and `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md` exists).

## Step 0: Reference Past CHDs and Current Specs from DOCS_DIR

For each `{repo}` in `AFFECTED_REPOS`:
1. Let `DESIGN_DIR` = `{DOCS}/{repo}/design/`.
2. If `{DESIGN_DIR}` exists:
   a. Read `{DOCS}/AI_INDEX.md` to find past CHD list for `{repo}`.
   b. Load up to 3 CHD files related to changed components.
3. If `{DOCS}/cross/design/` exists: also load past CHD-*-cross.md files (cross-repo design patterns).
4. **現状仕様の読み込み（既存仕様との整合確認用）:**
   Let `SPO_SUMMARY` = `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`.
   If `SPO_SUMMARY` does not exist: skip to Step 5 (note "SPO 未存在のためスキップ").
   Read `SPO_SUMMARY` to identify affected module names.
   Let `SPEC_FILE_PATHS` = [].
   For each affected module `{mod}`:
     - Primary:  `{XDDP_DIR}/latest-specs/{repo}/{mod}/spec.md` (if exists) → append to `SPEC_FILE_PATHS`
     - Fallback: `{DOCS}/{repo}/specs/{mod}/spec.md` (if primary absent and DOCS exists) → append to `SPEC_FILE_PATHS`
   If neither path exists for a module: note as "現状仕様なし（初回 CR）".
   Let `CURRENT_SPECS_REFS` = `SPEC_FILE_PATHS` (may be empty).
5. Record loaded references (past CHDs + `CURRENT_SPECS_REFS`) in CHD "referenced past design documents and current specifications" section.

## Step 0.5: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 7 (変更設計書作成) → 🔄 進行中, 詳細ステップ → `Step A: CHD生成中`, today. Write back.

## Step A0: Reference Lessons Learned Log

If `{XDDP_DIR}/lessons-learned.md` exists, read it.
Focus on entries tagged `#方式検討` `#設計` `#コーディング` for `LESSONS_CONTEXT`.
※ `{DOCS}/{repo}/knowledge/lessons-learned.md`（Layer 2: クローズ済みCR知見）は参照しない
  （xddp.05.arch と同一設計。Layer 1 の作業中高鮮度知見を優先する）。

## Step A-cross: Generate cross/CHD (API-first principle — only when HAS_CROSS = true)

※ LESSONS_CONTEXT は Step A-cross では明示的に使用しない（設計上の意図的省略）。
  cross/CHD はリポジトリ間インタフェース変更サマリに特化した成果物であり、
  過去知見の参照は per-repo CHD 設計（Step A）で行う。xddp.05.arch の Step A-cross と同一方針。

**API-first principle:** Establish the implementation dependency and interface change summary before per-repo CHD design.

Read `{XDDP_DIR}/project-rulebook-cross.md` (if exists) as `CROSS_RULEBOOK_CONTEXT`.

Generate `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` (write directly, not via agent):
- Read `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md`
- Read `{DOCS}/cross/design/` (past cross-repo CHDs, if exists)
- Content must include:

### 実装依存関係

| 提供リポジトリ | 消費リポジトリ | インタフェース | 実装順序 |
|---|---|---|---|
| （例）repo-a | repo-b | POST /jobs API | repo-a → repo-b |

### インタフェース変更サマリ

| インタフェース | 変更種別 | breaking |
|---|---|---|
| （例）POST /jobs | 新規追加 | false |

Derive these tables from the cross/DSN interface design.

If cross/DSN does not exist → skip this step.

## Step A: Generate per-repo Change Design Documents

Read `~/.claude/skills/xddp.rules/xddp.design.rules.md` to get `DESIGN_RULES`.

For each `{repo}` in `AFFECTED_REPOS`:

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Steering Context" with:
  XDDP_DIR: {XDDP_DIR}
  REPO_NAME: {repo}
→ let `RULEBOOK_CONTEXT`.

**Agent tool** `subagent_type=xddp-designer-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
DSN_INDEX_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
（{CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md が存在する場合のみ追加）DSN_COMPARISON_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
SPO_MODULES_DIR: {CR_PATH}/04_specout/{repo}/modules/
TEMPLATE_FILE: ~/.claude/skills/xddp.templates/06_change-design-document-template.md
OUTPUT_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
TODAY: {TODAY}
（LESSONS_CONTEXT が空でない場合のみ追加）LESSONS_CONTEXT: {LESSONS_CONTEXT}
RULEBOOK_CONTEXT: {RULEBOOK_CONTEXT}
ADDITIONAL_REFS: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md (pass if exists — must conform to interface contract)
PAST_CROSS_DESIGN_DIR: {DOCS}/cross/design/ (pass if exists)
DESIGN_TASK: {pass DESIGN_RULES content as-is}
（Step 0 で CURRENT_SPECS_REFS が空でない場合のみ追加）CURRENT_SPECS_REFS: {CURRENT_SPECS_REFS}
```

Check for scale warning (>500 lines changed). If present, relay to user.

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.CHD` rounds)

Update `{CR_PATH}/progress.md` step 7 詳細ステップ → `Step B: AIレビュー中`.

For each `{repo}` in `AFFECTED_REPOS`:

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: CHD
  NEXT_DOCUMENT_TYPE: TSP
  CONFIG_KEY: REVIEW_MAX_ROUNDS.CHD
  TARGET_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
  REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/04_specout/{repo}/SPO-{CR}.md]
  REVIEW_OUTPUT_FILE: {CR_PATH}/06_design/{repo}/review/06_design-review.md
  FIXER_AGENT: xddp-designer-agent
  FIXER_PARAMS:
    CR_NUMBER: {CR}
    REPO_NAME: {repo}
    OUTPUT_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
    REVIEW_FILE: {CR_PATH}/06_design/{repo}/review/06_design-review.md
    TODAY: {TODAY}
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 7

## Step B-cross: Cross CHD AI Review (only when HAS_CROSS = true)

If `HAS_CROSS`:
  Update `{CR_PATH}/progress.md` step 7 詳細ステップ → `Step B-cross: cross CHDレビュー中`.

  **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: CHD
  NEXT_DOCUMENT_TYPE: TSP
  TARGET_FILE: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
  REFERENCE_FILES: [
    {CR_PATH}/03_change-requirements/CRS-{CR}.md,
    {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md (if exists),
    {CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md (if exists),
    for each {repo} in AFFECTED_REPOS: {CR_PATH}/06_design/{repo}/CHD-{CR}.md (if exists)
  ]
  REVIEW_ROUND: 1
  OUTPUT_FILE: {CR_PATH}/06_design/cross/review/06_design-cross-review.md
  ```

  If 🔴/🟡 found: directly edit `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` to fix issues.

  After fixing, re-read `{CR_PATH}/06_design/cross/review/06_design-cross-review.md` and count remaining 🔴 rows.
  If 🔴 items remain: warn the human:
  > ⚠️ cross/ CHD レビューで 🔴 指摘 {N} 件が残存しています。手動確認してください: `{CR_PATH}/06_design/cross/review/06_design-cross-review.md`

  注: cross/ CHD はインタフェース変更のサマリに特化した成果物でサイズが小さく、1パスで修正が収束しやすい。
  per-repo の max_rounds ループは省略する（設計上の意図的省略）。

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 7 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
{for each repo in AFFECTED_REPOS:}
> - {repo}: `{CR_PATH}/06_design/{repo}/CHD-{CR}.md`
>   - AIレビュー: `{CR_PATH}/06_design/{repo}/review/06_design-review.md`
{if HAS_CROSS:}
> - cross: `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md`
>   - AIレビュー: `{CR_PATH}/06_design/cross/review/06_design-cross-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} design`（対象リポジトリを指定）
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。

Wait for user to confirm.

If the user made any changes:
- Run one final AI review pass per repo (same as Step B, `REVIEW_ROUND = last_round + 1`).
- If HAS_CROSS and the user changed cross/ CHD: run one final AI review pass for cross CHD
  (same as Step B-cross but `REVIEW_ROUND = last_round + 1`).

## Step C: Feed Design Results Back to CRS

Update `{CR_PATH}/progress.md` step 7 状態 → 🔄 進行中, step 8 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

Read all per-repo CHD files and cross/CHD (if exists).
For each file, extract items that are not yet reflected in CRS (new constraints, interface specs,
error conditions, out-of-scope items). Compose a unified `DESIGN_FEEDBACK` list in the format:
`種別: {追加UR/追加SR/追加SP/廃止SR/廃止SP} | 内容: ... | 根拠: CHD §X [cross]`
Append `[cross]` to items from cross/CHD. Merge per-repo and cross items into one list.

If the list is non-empty:
**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update-design
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
DESIGN_FEEDBACK: (the composed list from above)
TODAY: {TODAY}
AUTHOR_NOTE: 設計フィードバックを反映。SP・影響範囲更新。
```

## Step D: Regenerate CRS Excel (UR-016)

Run only if CRS was updated in Step C.

**Excel generation is delegated to the `xddp.md2excel` skill.**

Let `CRS_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.md`.
Let `EXCEL_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.xlsx`.
Run via Bash: `python ~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py {CRS_PATH} {EXCEL_PATH}`
If `crs_md2excel.py` not found: tell the user to run `setup.sh`. If errors: display to user.
Report output path and UR/SR/SP counts from script stdout.

> **Design policy:** The sole definition of the Excel format is in `~/.claude/skills/xddp.md2excel.md` and `~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py`.
> To change the format, modify only xddp.md2excel.md and crs_md2excel.py.
> **成果物の位置付け:** `CRS-{CR}.xlsx` は人間向け確認ツール（一時生成物）。xddp.close の DOCS_DIR 昇格対象外。

## Step E: Update progress.md

Step 7 (変更設計書作成) → ✅ 完了, 詳細ステップ → `-`.
Step 8 (変更要求仕様書フィードバック) → ✅ 完了, 詳細ステップ → `-`.
Next command → `/xddp.07.code {CR}`

## Step F: Report in Japanese

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.06.design.md`.
