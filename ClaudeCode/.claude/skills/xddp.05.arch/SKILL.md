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

(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
REPOS_MAP, REPOS_KEYS, IS_MULTI, DOCS_DIR, DOCS.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`.
Let `HAS_CROSS` = (IS_MULTI and `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` exists).
Let `DETAIL_MODE` = (`REST_ARGS` に `--detail` が含まれる). If `DETAIL_MODE` = true: skip to Step B3.

Let `ARCH_TEMPLATE_PATHS` =
  INDEX_TEMPLATE_FILE: ~/.claude/skills/xddp.05.arch/templates/05_design-approach-memo-template.md
  APPROACH_TEMPLATE_FILE: ~/.claude/skills/xddp.05.arch/templates/05_design-approach-memo-approach-template.md
  COMPARISON_TEMPLATE_FILE: ~/.claude/skills/xddp.05.arch/templates/05_design-approach-memo-comparison-template.md
（{repo} に依存しないため、Step A/B/B3 のどの独立ループからもこの1箇所の定義をそのまま参照できる）

Read `~/.claude/skills/xddp.rules/xddp.arch.rules.md` to get `ARCH_RULES`
（{repo} に依存しないため、Step A-cross・Step A の両方——Step A の `For each {repo}` ループ内にある
architect agent 呼び出しの `ALTERNATIVES_TASK: {pass ARCH_RULES content as-is}`（`:147`）を
含む——から、この1箇所の定義をそのまま参照できる。二重読み取りを避けるためここで1回のみ実施する。
本注記は上記 `ARCH_TEMPLATE_PATHS` 注記と同一形式のスコープ継続性注記である）.

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

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Lessons Context" with:
  LESSONS_FILE: {XDDP_DIR}/lessons-learned.md
  TARGET_TAGS: [#方式検討, #設計, #リスク, #依存関係]
→ let `LESSONS_CONTEXT`.

## Step A-cross: Generate cross/DSN (API-first principle — only when HAS_CROSS = true)

**API-first principle:** Establish the interface contract (cross/DSN) before per-repo approach design.

（`ARCH_RULES` は `DETAIL_MODE` 分岐直後・ファイル冒頭で読み込み済みのためここでの再読み取りは不要。
147行目の `ALTERNATIVES_TASK` を含め、本ファイル内のどこからでも参照可能）
Read `{XDDP_DIR}/project-rulebook.md` (shared) and `{XDDP_DIR}/project-rulebook-cross.md` (if exists) as `CROSS_RULEBOOK_CONTEXT`.

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

（`ARCH_RULES` は `DETAIL_MODE` 分岐直後・ファイル冒頭で読み込み済みのためここでの再読み取りは不要。
147行目の `ALTERNATIVES_TASK` を含め、本ファイル内のどこからでも参照可能）

Let `REPO_WARNINGS_MAP` = `{}`（空の辞書。key: repo名 → value: その repo の `WARNINGS` リスト。
Step B2 でこの辞書を参照して全 repo の警告をまとめて提示するため、for-each ループの外側で宣言し、
ループの全イテレーションを通じて保持する）。

For each `{repo}` in `AFFECTED_REPOS`:

Let `ARCH_AGENT_PATHS`（current {repo}; この式は xddp.05.arch/SKILL.md の Step A・Step B・Step B3 の
3箇所に同一の文字列で存在する。変更時は本ファイル内で `ARCH_AGENT_PATHS` を grep し3箇所すべてを同期させること） =
  INDEX_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
  APPROACHES_DIR: {CR_PATH}/05_architecture/{repo}/

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Steering Context" with:
  XDDP_DIR: {XDDP_DIR}
  REPO_NAME: {repo}
→ let `RULEBOOK_CONTEXT`.

architect agent を呼び出す前に、以下の SP-ID 照合チェックを実行する:

**設計根拠（工程6開始時照合の理由）:** 工程5（CRS 更新）で SP 項目が追加される場合があるため、工程5完了後・工程6開始時に照合することで最新 CRS との乖離を検出できる。工程4完了時点で照合しても工程5更新分が含まれないため、工程6開始時の照合が適切な配置となる。乖離が検出された場合に `WARNINGS` リストへ追加し処理を継続するのは、CRS への SP 追加が軽微な修正（定義補完）であることが多く、アーキテクトの判断で吸収できると想定しているためである。

**前提確認:** `repo` が `"cross"` の場合は SP-ID 照合チェックをスキップし、`ADDITIONAL_CONTEXT` を設定しない（cross/ SPO には funcmap が存在しない。architect agent の cross/ 代替読み込みロジックで処理する）。
`repo` が `"cross"` 以外かつ `SPO-{CR}-funcmap.md` が存在しない場合も SP-ID 照合チェックをスキップし、`ADDITIONAL_CONTEXT` を設定しない（新規開発モード時は新規開発モード処理で正常動作する。提供されたが存在しないファイルの場合のみ agent 側でエラー停止する）。
1. CRS §4 の SP-ID 一覧を取得する。方法: CRS ファイルを Read して §4 セクション内に絞り、テーブル行（`\|\s*SP-` のパターン — Markdown フォーマッタによる先頭スペース挿入に対応）の第 1 列から識別子を抽出・重複排除する（本文参照・変更履歴等のノイズを排除するため `SP-` プレフィックスを持つセルに限定する）
2. `SPO-{CR}-funcmap.md` の §1 テーブルの機能ID列（1列目）から SP-ID 一覧を取得する（ヘッダ行・区切り行・テンプレートプレースホルダー行（`{機能ID}` を含む行）を除く・重複排除）
3. Let `WARNINGS` = `[]`（この repo についての警告リスト）。2つの ID 集合を比較し、以下のケースで `WARNINGS` に追加する:
   - CRS にあって funcmap にない SP-ID が存在する場合（工程5での SP 追加または funcmap 未収録）:
     「⚠️ funcmap 未収録 SP 項目: {ID一覧}。funcmap は工程4時点のスナップショットです。これらの SP 項目のシグネチャは CRS §4 を直接照合し、方式比較に組み込んでください。DSN Section 5 リスクに記録してください。」
   - funcmap にあって CRS にない SP-ID が存在する場合（工程5での SP 変更・削除による旧 ID 残存）:
     「⚠️ funcmap 余剰エントリ: {ID一覧}。CRS §4 に対応する SP 項目が存在しません。方式比較では CRS §4 の最新 SP 項目を正として扱ってください。」
   - 両者が完全に一致する場合: `WARNINGS` への追加は不要（照合完了のみ記録）
   `WARNINGS` が空でない場合:
   - その内容を `ADDITIONAL_CONTEXT` として architect agent 呼び出し時に渡す
     （agent タスク記述の `ADDITIONAL_CONTEXT:` フィールドとして追記する）。
   - `REPO_WARNINGS_MAP[repo] = WARNINGS` を設定する（Step B2 で読み出すために永続化する）。
   `WARNINGS` が空の場合は `ADDITIONAL_CONTEXT` を省略し、`REPO_WARNINGS_MAP` には何も追加しない。
   **このチェックの結果に関わらず、このイテレーション内でユーザーへの確認を挟まずそのまま architect agent 呼び出しに進み、次の repo のイテレーションへ移る
   （Step A 内では確認を行わない、という意味であり、Step B2 以降の人レビュー自体は別途実施される）。
   `REPO_WARNINGS_MAP` に蓄積された全 repo の警告は、Step B2（Human Review Gate）で他のレビュー結果と合わせてまとめて提示する。**

**Agent tool** `subagent_type=xddp-architect-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
（{CR_PATH}/04_specout/{repo}/SPO-{CR}.md が存在する場合のみ追加）SPO_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
（repo が "cross" 以外 かつ {CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md が存在する場合のみ追加）FUNCMAP_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md
（{CR_PATH}/04_specout/{repo}/modules/ が存在する場合のみ追加）SPO_MODULES_DIR: {CR_PATH}/04_specout/{repo}/modules/
{ARCH_TEMPLATE_PATHS の全キーを展開}
{ARCH_AGENT_PATHS の全キーを展開}
TODAY: {TODAY}
（LESSONS_CONTEXT が空でない場合のみ追加）LESSONS_CONTEXT: {LESSONS_CONTEXT}
RULEBOOK_CONTEXT: {RULEBOOK_CONTEXT}
ADDITIONAL_REFS: {CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md (pass if exists — must conform to interface contract)
PAST_CROSS_DESIGN_DIR: {DOCS}/cross/design/ (pass if exists)
ALTERNATIVES_TASK: {pass ARCH_RULES content as-is}
（SP-ID 照合チェックで警告が生成された場合のみ追加）ADDITIONAL_CONTEXT: {ADDITIONAL_CONTEXT}
（Step 0 で CURRENT_SPECS_REFS が空でない場合のみ追加）CURRENT_SPECS_REFS: {CURRENT_SPECS_REFS}
```

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.DSN` rounds)

Update `{CR_PATH}/progress.md` step 6 詳細ステップ → `Step B: AIレビュー中`.

For each `{repo}` in `AFFECTED_REPOS`:

Let `ARCH_AGENT_PATHS`（current {repo}; この式は xddp.05.arch/SKILL.md の Step A・Step B・Step B3 の
3箇所に同一の文字列で存在する。変更時は本ファイル内で `ARCH_AGENT_PATHS` を grep し3箇所すべてを同期させること） =
  INDEX_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
  APPROACHES_DIR: {CR_PATH}/05_architecture/{repo}/

architect agent 完了後に `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md` の存在チェックを行い、
存在する場合は「2案以上モード」、存在しない場合は「1案モード」として TARGET_FILE を決定する:
- 2案以上モード: TARGET_FILE = `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md`
- 1案モード: TARGET_FILE = `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-A.md`

また REFERENCE_FILES に approach ファイルを追加する（comparison.md が TARGET の場合）:
- `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-A.md` （comparison.md が TARGET の場合）
- `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-B.md` （exists の場合）
- `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-C.md` （exists の場合）

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: DSN
  NEXT_DOCUMENT_TYPE: CHD
  CONFIG_KEY: REVIEW_MAX_ROUNDS.DSN
  TARGET_FILE: {上記で決定した TARGET_FILE}
  REFERENCE_FILES: [
    {CR_PATH}/03_change-requirements/CRS-{CR}.md,
    （{CR_PATH}/04_specout/{repo}/SPO-{CR}.md が存在する場合のみ追加）{CR_PATH}/04_specout/{repo}/SPO-{CR}.md,
    （repo が "cross" 以外 かつ {CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md が存在する場合のみ追加）{CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md,
    （comparison.md が TARGET の場合のみ追加）{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-A.md,
    （exists の場合のみ追加）{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-B.md,
    （exists の場合のみ追加）{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-C.md
  ]
  REVIEW_OUTPUT_FILE: {CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md
  FIXER_AGENT: xddp-architect-agent
  FIXER_PARAMS:
    CR_NUMBER: {CR}
    REPO_NAME: {repo}
    {ARCH_AGENT_PATHS の INDEX_FILE / APPROACHES_DIR を展開}
    {ARCH_TEMPLATE_PATHS の INDEX_TEMPLATE_FILE / APPROACH_TEMPLATE_FILE / COMPARISON_TEMPLATE_FILE を展開}
    REVIEW_FILE: {CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md
    TODAY: {TODAY}
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 6

## Step B-cross: Cross DSN AI Review (only when HAS_CROSS = true)

If `HAS_CROSS`:
  Update `{CR_PATH}/progress.md` step 6 詳細ステップ → `Step B-cross: cross DSNレビュー中`.

  **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: DSN
  NEXT_DOCUMENT_TYPE: CHD
  TARGET_FILE: {CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md
  REFERENCE_FILES: [
    {CR_PATH}/03_change-requirements/CRS-{CR}.md,
    {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md (if exists),
    for each {repo} in AFFECTED_REPOS:
      - {CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md （exists かつ 2案以上の場合）
      - {CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-A.md （exists の場合）
      - {CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-B.md （exists の場合）
      - {CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-C.md （exists の場合）
    （インデックスファイル DSN-{CR}.md は省略。採用方式・アプローチ詳細が含まれるファイルを直接渡す）
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

Build `INTRO_NOTE` by expanding the following (REPO_WARNINGS_MAP is already resolved in this
skill's scope; omit `INTRO_NOTE` entirely if REPO_WARNINGS_MAP is empty):
```
⚠️ SP-ID 照合チェックで以下の警告が見つかりました（Step A で検出・処理は続行済みです）:
{for each (repo, WARNINGS) in REPO_WARNINGS_MAP: - {repo}: {WARNINGS の内容}}
```

Build `ARTIFACTS_TEXT` by expanding the following (AFFECTED_REPOS/HAS_CROSS are already resolved
in this skill's scope):
```
{for each repo in AFFECTED_REPOS:}
- {repo}: インデックス `{CR_PATH}/05_architecture/{repo}/DSN-{CR}.md`
  - 案A: `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-A.md`
  - 案B: `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-B.md` （存在する場合）
  - 比較: `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md` （2案以上の場合）
  - AIレビュー: `{CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md`
{if HAS_CROSS:}
- cross: `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md`
  - AIレビュー: `{CR_PATH}/05_architecture/cross/review/05_architecture-cross-review.md`
```

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Human Review Gate" with:
  CR_PATH: {CR_PATH}
  STEP_NUM: 6
  STEP_LABEL: `Step B2`
  INTRO_NOTE: {built above, omit if REPO_WARNINGS_MAP is empty}
  ARTIFACTS_TEXT: {built above}
  REVISE_COMMAND: `/xddp.revise {CR} arch`（対象リポジトリを指定）
  OPTION_NOTE: |
    **詳細図（構造体関連図・主処理シーケンス図）が必要な場合：**
    全案を統一粒度で生成します（比較可能な形式）:
    `/xddp.05.arch {CR} --detail`
→ let `CHANGED`.

If `CHANGED`:
- Run one final AI review pass per repo (same as Step B, `REVIEW_ROUND = last_round + 1`).
- If HAS_CROSS and the user changed cross/ DSN: run one final AI review pass for cross DSN
  (same as Step B-cross but `REVIEW_ROUND = last_round + 1`).

## Step B3: Detail Diagram Generation (--detail mode only)

`DETAIL_MODE` = true の場合のみ実行。通常フロー（Step 0〜B2）はスキップ済み。

For each `{repo}` in `AFFECTED_REPOS`:
  **cross/ はスキップ:** `{repo}` が `"cross"` の場合、`DSN-{CR}-cross.md` は
  approach-*.md 構造を持たないためスキップする。
  If `{repo}` = `"cross"`: continue.
  （`REPOS:` キーに `"cross"` は使用不可（CLAUDE.md 予約名）のため実際には到達しない防衛的ガード）

  If `{CR_PATH}/05_architecture/{repo}/DSN-{CR}.md` does not exist:
    Warn the user:
    > ⚠️ {repo}: DSN が存在しません。先に通常モードで `/xddp.05.arch {CR}` を実行してください。
    Skip this repo.

  Let `ARCH_AGENT_PATHS`（current {repo}; この式は xddp.05.arch/SKILL.md の Step A・Step B・Step B3 の
  3箇所に同一の文字列で存在する。変更時は本ファイル内で `ARCH_AGENT_PATHS` を grep し3箇所すべてを同期させること） =
    INDEX_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
    APPROACHES_DIR: {CR_PATH}/05_architecture/{repo}/

  **Agent tool** `subagent_type=xddp-architect-agent`:
  ```
  CR_NUMBER: {CR}
  REPO_NAME: {repo}
  {ARCH_AGENT_PATHS の INDEX_FILE / APPROACHES_DIR を展開}
  {ARCH_TEMPLATE_PATHS の APPROACH_TEMPLATE_FILE を展開}
  DETAIL_MODE: true
  TODAY: {TODAY}
  ```

Report to user (Japanese):
> ✅ 詳細図を生成しました。
{for each repo where repo ≠ "cross":}
> - {repo}: 更新ファイル一覧（INDEX_FILE から発見した approach-*.md）

`DETAIL_MODE` = true の場合、Step C 以降はすべてスキップする。詳細図生成の結果報告は Step B3 内の Report to user で完結する（progress.md の更新もしない）。

## Step C: Feed Architecture Decision Back to CRS

Update `{CR_PATH}/progress.md` step 6 状態 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

Read all per-repo DSN files: 各 {repo} の comparison.md（2案以上の場合）または approach-A.md（1案の場合）、
および cross/DSN-{CR}-cross.md（if exists）。
フィードバック抽出は採用方式・設計指針が記載されているファイルから行う。
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

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Regenerate CRS Excel" with:
  CR_PATH: {CR_PATH}
  CR: {CR}

## Step E: Update progress.md
Step 6 (実装方式検討) → ✅ 完了, 詳細ステップ → `-`. Next command → `/xddp.06.design {CR}`

## Step F: Report in Japanese
