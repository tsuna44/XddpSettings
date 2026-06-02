---
description: XDDP フェーズ3: 実装方式検討メモ（DSN）を作成し、AIレビュー→修正ループを実施する。「方式検討して」「実装方針を決めて」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Step 05 (process step 06) — Implementation Approach Design**.

> The implementation approach chosen here shapes build quality and maintainability for the life of this code. A poorly examined recommendation means months of rework. Orchestrate with depth — every tradeoff deserves honest comparison.

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
Let `HAS_CROSS` = (IS_MULTI and `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` exists).

## Step 0: Reference Past DSNs and Current Specs from DOCS_DIR

For each `{repo}` in `AFFECTED_REPOS`:
1. Let `DESIGN_DIR` = `{DOCS}/{repo}/design/`.
2. If `{DESIGN_DIR}` exists:
   a. Read `{DOCS}/AI_INDEX.md` to find past DSN list for `{repo}`.
   b. Load up to 3 most recent DSN files related to changed components.
3. If `{DOCS}/cross/design/` exists: also load up to 2 most recent DSN-*-cross.md files (past cross-repo design decisions).
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
5. Record loaded references (past DSNs + `CURRENT_SPECS_REFS`) in DSN "referenced past design documents" section.

## Step 0.5: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 6 (実装方式検討) → 🔄 進行中, 詳細ステップ → `Step A: DSN生成中`, today. Write back.
If `IS_MULTI`, append per-repo progress table for step 6 similar to step 4 table.

## Step A0: Reference Lessons Learned Log

If `{XDDP_DIR}/lessons-learned.md` exists, read it.
Focus on entries tagged `#方式検討` `#設計` `#リスク` `#依存関係` for `LESSONS_CONTEXT`.

## Step A-cross: Generate cross/DSN (API-first principle — only when HAS_CROSS = true)

**API-first principle:** Establish the interface contract (cross/DSN) before per-repo approach design.

Read `~/.claude/skills/xddp.rules/xddp.arch.rules.md` to get `ARCH_RULES`.
Read `{XDDP_DIR}/project-steering.md` (shared) and `{XDDP_DIR}/project-steering-cross.md` (if exists) as `CROSS_STEERING_CONTEXT`.

Generate `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md` (write directly, not via agent):
- Read `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`
- Read `{DOCS}/cross/design/` (past cross-repo design docs, if exists)
- Content must include:
  - Section 2: クロスリポジトリ実装方式（how inter-repo interfaces will be implemented）
  - Section 3: インタフェース設計（API signatures, message schemas, shared types — concrete enough for CHD）
  - Section 4: 実装依存順序（which repo's changes must be built first）
  - Section 5: リスクと軽減策

If cross/SPO does not exist → skip this step.

## Step A: Generate per-repo Architecture Memos

Read `~/.claude/skills/xddp.rules/xddp.arch.rules.md` to get `ARCH_RULES`.

For each `{repo}` in `AFFECTED_REPOS`:

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Steering Context" with:
  XDDP_DIR: {XDDP_DIR}
  REPO_NAME: {repo}
→ let `STEERING_CONTEXT`.

architect agent を呼び出す前に、以下の SP-ID 照合チェックを実行する:

**設計根拠（工程6開始時照合の理由）:** 工程5（CRS 更新）で SP 項目が追加される場合があるため、工程5完了後・工程6開始時に照合することで最新 CRS との乖離を検出できる。工程4完了時点で照合しても工程5更新分が含まれないため、工程6開始時の照合が適切な配置となる。乖離が検出されても「警告のみ・処理続行」とするのは、CRS への SP 追加が軽微な修正（定義補完）であることが多く、アーキテクトの判断で吸収できると想定しているためである。

**前提確認:** `repo` が `"cross"` の場合は SP-ID 照合チェックをスキップし、`ADDITIONAL_CONTEXT` を設定しない（cross/ SPO には funcmap が存在しない。architect agent の cross/ 代替読み込みロジックで処理する）。
`repo` が `"cross"` 以外かつ `SPO-{CR}-funcmap.md` が存在しない場合も SP-ID 照合チェックをスキップし、`ADDITIONAL_CONTEXT` を設定しない（architect agent 側でエラー停止して対処させる）。
1. CRS §4 の SP-ID 一覧を取得する。方法: CRS ファイルを Read して §4 セクション内に絞り、テーブル行（`\|\s*SP-` のパターン — Markdown フォーマッタによる先頭スペース挿入に対応）の第 1 列から識別子を抽出・重複排除する（本文参照・変更履歴等のノイズを排除するため `SP-` プレフィックスを持つセルに限定する）
2. `SPO-{CR}-funcmap.md` の §1 テーブルの機能ID列（1列目）から SP-ID 一覧を取得する（ヘッダ行・区切り行・テンプレートプレースホルダー行（`{機能ID}` を含む行）を除く・重複排除）
3. 2つの ID 集合を比較し、以下のケースで警告を収集する（処理は中断しない）:
   - CRS にあって funcmap にない SP-ID が存在する場合（工程5での SP 追加または funcmap 未収録）:
     「⚠️ funcmap 未収録 SP 項目: {ID一覧}。funcmap は工程4時点のスナップショットです。これらの SP 項目のシグネチャは CRS §4 を直接照合し、方式比較に組み込んでください。DSN Section 5 リスクに記録してください。」
   - funcmap にあって CRS にない SP-ID が存在する場合（工程5での SP 変更・削除による旧 ID 残存）:
     「⚠️ funcmap 余剰エントリ: {ID一覧}。CRS §4 に対応する SP 項目が存在しません。方式比較では CRS §4 の最新 SP 項目を正として扱ってください。」
   - 両者が完全に一致する場合: 警告不要（照合完了のみ記録）
   警告が存在する場合、収集した警告メッセージを `ADDITIONAL_CONTEXT` として architect agent 呼び出し時に渡す
   （agent タスク記述の `ADDITIONAL_CONTEXT:` フィールドとして追記する。警告がない場合は省略する）。

**Agent tool** `subagent_type=xddp-architect-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
（repo が "cross" 以外の場合のみ追加）FUNCMAP_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md
SPO_MODULES_DIR: {CR_PATH}/04_specout/{repo}/modules/
TEMPLATE_FILE: ~/.claude/skills/xddp.templates/05_design-approach-memo-template.md
OUTPUT_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
TODAY: {TODAY}
LESSONS_CONTEXT: {entries tagged #方式検討 #設計 #リスク #依存関係; empty if none}
STEERING_CONTEXT: {STEERING_CONTEXT}
ADDITIONAL_REFS: {CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md (pass if exists — must conform to interface contract)
PAST_CROSS_DESIGN_DIR: {DOCS}/cross/design/ (pass if exists)
ALTERNATIVES_TASK: {pass ARCH_RULES content as-is}
（SP-ID 照合チェックで警告が生成された場合のみ追加）ADDITIONAL_CONTEXT: {ADDITIONAL_CONTEXT}
（Step 0 で CURRENT_SPECS_REFS が空でない場合のみ追加）CURRENT_SPECS_REFS: {CURRENT_SPECS_REFS}
```

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.DSN` rounds)

Update `{CR_PATH}/progress.md` step 6 詳細ステップ → `Step B: AIレビュー中`.

For each `{repo}` in `AFFECTED_REPOS`:

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: DSN
  CONFIG_KEY: REVIEW_MAX_ROUNDS.DSN
  TARGET_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
  REFERENCE_FILES: [
    {CR_PATH}/03_change-requirements/CRS-{CR}.md,
    {CR_PATH}/04_specout/{repo}/SPO-{CR}.md,
    （repo が "cross" 以外の場合のみ追加）{CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md
  ]
  REVIEW_OUTPUT_FILE: {CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md
  FIXER_AGENT: xddp-architect-agent
  FIXER_PARAMS:
    CR_NUMBER: {CR}
    REPO_NAME: {repo}
    OUTPUT_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
    REVIEW_FILE: {CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md
    TODAY: {TODAY}

## Step B-cross: Cross DSN AI Review (only when HAS_CROSS = true)

If `HAS_CROSS`:
  Update `{CR_PATH}/progress.md` step 6 詳細ステップ → `Step B-cross: cross DSNレビュー中`.

  **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: DSN
  TARGET_FILE: {CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md
  REFERENCE_FILES: [
    {CR_PATH}/03_change-requirements/CRS-{CR}.md,
    {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md (if exists),
    for each {repo} in AFFECTED_REPOS: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md (if exists)
  ]
  REVIEW_ROUND: 1
  OUTPUT_FILE: {CR_PATH}/05_architecture/cross/review/05_architecture-cross-review.md
  ```

  If 🔴/🟡 found: directly edit `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md` to fix issues.

  After fixing, re-read `{CR_PATH}/05_architecture/cross/review/05_architecture-cross-review.md` and count remaining 🔴 rows.
  If 🔴 items remain: warn the human:
  > ⚠️ cross/ DSN レビューで 🔴 指摘 {N} 件が残存しています。手動確認してください: `{CR_PATH}/05_architecture/cross/review/05_architecture-cross-review.md`

  注: cross/ DSN はインタフェース仕様・実装依存順序に特化した成果物でサイズが小さく、1パスで修正が収束しやすい。
  per-repo の max_rounds ループは省略する（設計上の意図的省略）。

## Step B2: Human Review Gate

Update `{CR_PATH}/progress.md` step 6 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
{for each repo in AFFECTED_REPOS:}
> - {repo}: `{CR_PATH}/05_architecture/{repo}/DSN-{CR}.md`
>   - AIレビュー: `{CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md`
{if HAS_CROSS:}
> - cross: `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md`
>   - AIレビュー: `{CR_PATH}/05_architecture/cross/review/05_architecture-cross-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} arch`（対象リポジトリを指定）
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。

Wait for user to confirm.

If the user made any changes:
- Run one final AI review pass per repo (same as Step B, `REVIEW_ROUND = last_round + 1`).
- If HAS_CROSS and the user changed cross/ DSN: run one final AI review pass for cross DSN
  (same as Step B-cross but `REVIEW_ROUND = last_round + 1`).

## Step C: Feed Architecture Decision Back to CRS

Update `{CR_PATH}/progress.md` step 6 状態 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

Read all per-repo DSN files and cross/DSN (if exists).
For each file, extract items that are not yet reflected in CRS (new constraints, NF requirements,
interface specs, out-of-scope items). Compose a unified `DESIGN_FEEDBACK` list in the format:
`種別: {追加UR/追加SR/追加SP/廃止SR/廃止SP} | 内容: ... | 根拠: DSN §X [cross]`
Append `[cross]` to items from cross/DSN. Merge per-repo and cross items into one list.

If the list is non-empty:
**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update-design
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
DESIGN_FEEDBACK: (the composed list from above)
TODAY: {TODAY}
AUTHOR_NOTE: 方式検討フィードバックを反映。採用方式に基づく要求・仕様の追加／削除／変更。
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
Step 6 (実装方式検討) → ✅ 完了, 詳細ステップ → `-`. Next command → `/xddp.06.design {CR}`

## Step F: Report in Japanese

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.05.arch.md`.
