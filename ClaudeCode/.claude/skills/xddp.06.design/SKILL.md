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

(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
REPOS_MAP, REPOS_KEYS, IS_MULTI, DOCS_DIR, DOCS.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`.
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

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Lessons Context" with:
  LESSONS_FILE: {XDDP_DIR}/lessons-learned.md
  TARGET_TAGS: [#方式検討, #設計, #コーディング]
→ let `LESSONS_CONTEXT`.
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

## Step A-scale: CR Scale Warning (orchestrator-side)

`xddp-designer-agent` はバッチ単位のSPしか見えないため、CR全体の規模判定はオーケストレーター側で行う。

Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md` Section 4 (USDM トレーサビリティ). Count all SP entries → `TOTAL_SP_COUNT`.

If `TOTAL_SP_COUNT > 50`:
  Let `SCALE_WARNING` = `"⚠️ 総SP数が{TOTAL_SP_COUNT}件です。CR分割を検討してください（UR-035）。"`
Else:
  Let `SCALE_WARNING` = 空文字列。

（この警告は Step B2 の `INTRO_NOTE` に追加する。SP数50件は UR-035 の参考目安（500行超）に
近いか判断するための暫定的な代理指標であり、シンボル数→行数の換算根拠は今後要検証。）

## Step A: Generate per-repo Change Design Documents (UR×バッチ単位)

Read `~/.claude/skills/xddp.rules/xddp.design.rules.md` to get `DESIGN_RULES`.

Read `{CR_PATH}/xddp.config.md` lookup already done in CR Resolution; extract `DESIGN_MAX_SP_PER_FILE`
(default: `10`).

**1. Build BATCH_PLAN (once per CR, shared across all repos):**

Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md` Section 2 (USDM: UR→SR→SP 階層).
For each UR in CRS (記載順): collect all SP-IDs under it (across all SR).
- If SP数 ≤ `DESIGN_MAX_SP_PER_FILE`: 1バッチ。`FILE_NAME` = `CHD-{CR}-{UR-ID}.md`。
- If SP数 > `DESIGN_MAX_SP_PER_FILE`: `DESIGN_MAX_SP_PER_FILE` 件ごとに分割（CRS記載順）。
  `FILE_NAME` = `CHD-{CR}-{UR-ID}-{N}.md`（`N` = 1, 2, ...）。

`BATCH_PLAN` = list of `{UR_ID, UR_NAME, BATCH_INDEX (例 "1/2"。単一バッチは "-"), SP_IDS, FILE_NAME}`.

**2. Write index skeleton (per repo, direct Write — not via agent):**

For each `{repo}` in `AFFECTED_REPOS`:
  Using `~/.claude/skills/xddp.06.design/templates/06_change-design-document-index-template.md`,
  Write `{CR_PATH}/06_design/{repo}/CHD-{CR}.md` with Section 2 の全行を `BATCH_PLAN` から構築する
  （列: UR ID・UR名・バッチ・SP数・ファイル）。「該当変更」列は全行 `(生成中)` の placeholder とする。

**3. Invoke xddp-designer-agent per (repo, UR×バッチ):**

For each `{repo}` in `AFFECTED_REPOS`:

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Steering Context" with:
  XDDP_DIR: {XDDP_DIR}
  REPO_NAME: {repo}
→ let `RULEBOOK_CONTEXT`.

For each entry in `BATCH_PLAN`:

**Agent tool** `subagent_type=xddp-designer-agent`:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
DSN_INDEX_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md
（{CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md が存在する場合のみ追加）DSN_COMPARISON_FILE: {CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
（{CR_PATH}/04_specout/{repo}/SPO-{CR}.md が存在する場合のみ追加）SPO_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
（{CR_PATH}/04_specout/{repo}/modules/ が存在する場合のみ追加）SPO_MODULES_DIR: {CR_PATH}/04_specout/{repo}/modules/
TEMPLATE_FILE: ~/.claude/skills/xddp.06.design/templates/06_change-design-document-template.md
UR_SCOPE: {entry.SP_IDS}
OUTPUT_FILE: {CR_PATH}/06_design/{repo}/{entry.FILE_NAME}
INDEX_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
TODAY: {TODAY}
（LESSONS_CONTEXT が空でない場合のみ追加）LESSONS_CONTEXT: {LESSONS_CONTEXT}
RULEBOOK_CONTEXT: {RULEBOOK_CONTEXT}
ADDITIONAL_REFS: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md (pass if exists — must conform to interface contract)
PAST_CROSS_DESIGN_DIR: {DOCS}/cross/design/ (pass if exists)
DESIGN_TASK: {pass DESIGN_RULES content as-is}
（Step 0 で CURRENT_SPECS_REFS が空でない場合のみ追加）CURRENT_SPECS_REFS: {CURRENT_SPECS_REFS}
```

このリポジトリに該当変更がない場合はエージェントが「該当なし」の薄い内容を書く
（テンプレートの注記どおり）。エージェントは `OUTPUT_FILE` 書き込み直後に `INDEX_FILE` の自分の行の
「該当変更」列を自己申告で確定させる（実行はエージェント側、`xddp-designer-agent.md` 参照）。

## Step A2: SP Coverage Auto-Verification & Backfill

Update `{CR_PATH}/progress.md` step 7 詳細ステップ → `Step A2: カバレッジ検証中`.

1. CRS Section 4 の全SP-IDを `EXPECTED_SP_IDS` とする。
2. 各 `{repo}` について「## Discover CHD Files」を適用し（`CR_PATH`, `REPO_NAME: {repo}`, `CR`）
   `CHD_CONTENT_FILES` を取得、全ファイルの Section 4（トレーサビリティマトリクス）の仕様ID列を読み、
   変更ファイル列が `-` でない行のSP-IDを集約して `COVERED_SP_IDS` とする。
3. `MISSING = EXPECTED_SP_IDS - COVERED_SP_IDS`。空なら次のステップ（Step B）へ進む。
4. 各 missing SP-ID について:
   a. `BATCH_PLAN` からこのSPが属する (UR, バッチ) を特定する。
   b. 各 `{repo}` の該当バッチファイルを確認し、**同じバッチ内の他のSPがそのファイルで
      Section 4 に1件以上の変更エントリを持つ repo** を「有力repo」とする。
   c. **有力repoが「ちょうど1つ」の場合のみ**自動補完する（安全側に倒す）:
      Step A本体の呼び出しと同様に `CRS_FILE, SPO_FILE, DSN_INDEX_FILE` 等の既存パラメータは
      repo・UR に対応する値でそのまま渡し、加えて以下を指定して `xddp-designer-agent` を再呼び出しする:
      **Agent tool** `subagent_type=xddp-designer-agent`:
      ```
      CR_NUMBER: {CR}
      REPO_NAME: {その有力repo}
      DSN_INDEX_FILE: {CR_PATH}/05_architecture/{その有力repo}/DSN-{CR}.md
      （存在する場合のみ追加）DSN_COMPARISON_FILE: {CR_PATH}/05_architecture/{その有力repo}/DSN-{CR}-comparison.md
      CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
      （存在する場合のみ追加）SPO_FILE: {CR_PATH}/04_specout/{その有力repo}/SPO-{CR}.md
      （存在する場合のみ追加）SPO_MODULES_DIR: {CR_PATH}/04_specout/{その有力repo}/modules/
      OUTPUT_FILE: {その有力repoのバッチファイル}
      INDEX_FILE: {その有力repoのインデックスファイル（CHD-{CR}.md）}
      BACKFILL_SP_IDS: [missing SP-ID]
      TODAY: {TODAY}
      ```
      （`UR_SCOPE` は本呼び出しでは渡さない — `BACKFILL_SP_IDS` モードは `UR_SCOPE` を使わず
      `BACKFILL_SP_IDS` のみで対象SPを特定する。`REVIEW_FILE` モードとは排他。
      1 SP につき本ステップでの自動補完は1回のみ試行する）
      再呼び出し後、その repo のファイルを再チェックし、補完できたか確認する。
   d. **有力repoが0個、または2個以上（どのrepoの担当か一意に決まらない）の場合**、
      または c. の補完後も未解消の場合:
      自動補完を行わず `UNRESOLVED_MISSING` に記録する。
      （理由: 同一バッチ内に複数repo担当のSPが混在する場合、最初に見つかったrepoを採用すると
      誤ったリポジトリへの自動追記＝後続の工程9コーディングの誤実装につながるリスクがある。
      一意に決まらない場合は人の判断に委ねる）
5. `UNRESOLVED_MISSING` が空でない場合、Step B2 の `INTRO_NOTE` に追加する文言を
   `MISSING_SP_NOTE` として保持する:
   `"⚠️ 以下のSPはいずれのリポジトリのCHDにも設計エントリが見つかりませんでした（または
   担当リポジトリが一意に決まりません）。担当リポジトリを確認し手動で追記してください:
   {SP-ID一覧}"`

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.CHD` rounds)

Update `{CR_PATH}/progress.md` step 7 詳細ステップ → `Step B: AIレビュー中`.

Let `OVERSIZED_FILES` = [].

For each `{repo}` in `AFFECTED_REPOS`:

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `CHD_CONTENT_FILES`.

For each `{file}` in `CHD_CONTENT_FILES`（対応する `BATCH_PLAN` エントリの `UR_ID`／`BATCH_INDEX`／`SP_IDS` を特定する）:

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: CHD
  NEXT_DOCUMENT_TYPE: TSP
  CONFIG_KEY: REVIEW_MAX_ROUNDS.CHD
  TARGET_FILE: {file}
  REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, （{CR_PATH}/04_specout/{repo}/SPO-{CR}.md が存在する場合のみ追加）{CR_PATH}/04_specout/{repo}/SPO-{CR}.md]
  REVIEW_OUTPUT_FILE: {CR_PATH}/06_design/{repo}/review/06_design-review-{UR_ID}[-{N}].md
  FIXER_AGENT: xddp-designer-agent
  FIXER_PARAMS:
    CR_NUMBER: {CR}
    REPO_NAME: {repo}
    UR_SCOPE: {entry.SP_IDS}
    OUTPUT_FILE: {file}
    INDEX_FILE: {CR_PATH}/06_design/{repo}/CHD-{CR}.md
    REVIEW_FILE: {CR_PATH}/06_design/{repo}/review/06_design-review-{UR_ID}[-{N}].md
    TODAY: {TODAY}
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 7

Read `{file}` Section 4 (トレーサビリティマトリクス). Count rows.
If row count > `DESIGN_MAX_SYMBOLS_PER_FILE`（default: `30`）: append `{file}` to `OVERSIZED_FILES`.

**既存の孤立コードの処理:** 旧 Step A 末尾にあった「Check for scale warning (>500 lines changed). If
present, relay to user.」は、警告の発生源を Step A-scale（オーケストレーター側判定）に移設したため削除した。
SCALE_WARNING は Step B2 の `INTRO_NOTE` で中継表示する。

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

Build `ARTIFACTS_TEXT` by expanding the following (AFFECTED_REPOS/HAS_CROSS are already resolved
in this skill's scope。詳細は各UR別ファイルへのリンクをインデックス経由で案内し、全バッチファイルを
並べて冗長になることを避ける):
```
{for each repo in AFFECTED_REPOS:}
- {repo}: `{CR_PATH}/06_design/{repo}/CHD-{CR}.md`（インデックス。詳細は各UR別ファイルへのリンクを参照）
  - AIレビュー: `{CR_PATH}/06_design/{repo}/review/`
{if HAS_CROSS:}
- cross: `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md`
  - AIレビュー: `{CR_PATH}/06_design/cross/review/06_design-cross-review.md`
```

Build `INTRO_NOTE` by concatenating（空でないもののみ）: `SCALE_WARNING`（Step A-scale）、
`MISSING_SP_NOTE`（Step A2）。

Build `OPTION_NOTE`:
If `OVERSIZED_FILES` is non-empty:
  `OPTION_NOTE` = `"⚠️ 以下のファイルは変更シンボル数が{DESIGN_MAX_SYMBOLS_PER_FILE}件を超えています。
  /xddp.revise で手動分割を検討してください: {OVERSIZED_FILES一覧}"`
Else: `OPTION_NOTE` = 空文字列。

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Human Review Gate" with:
  CR_PATH: {CR_PATH}
  STEP_NUM: 7
  STEP_LABEL: `Step B2`
  ARTIFACTS_TEXT: {built above}
  INTRO_NOTE: {built above}
  OPTION_NOTE: {built above}
  REVISE_COMMAND: `/xddp.revise {CR} design`（対象リポジトリを指定）
→ let `CHANGED`.

If `CHANGED`:
- Run one final AI review pass per repo, per content file (same as Step B, `REVIEW_ROUND = last_round + 1`).
- If HAS_CROSS and the user changed cross/ CHD: run one final AI review pass for cross CHD
  (same as Step B-cross but `REVIEW_ROUND = last_round + 1`).

## Step C: Feed Design Results Back to CRS

Update `{CR_PATH}/progress.md` step 7 状態 → 🔄 進行中, step 8 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

For each `{repo}` in `AFFECTED_REPOS`: Read `~/.claude/skills/xddp.common/SKILL.md`, apply
"## Discover CHD Files" with `CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}` → let `CHD_CONTENT_FILES`,
then Read all files in `CHD_CONTENT_FILES`. Also read cross/CHD (if exists).
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

## Step C': Generate Traceability Matrix (TM)

（注: このステップでは step 8 の詳細ステップのみ更新する。step 8 の状態完了マークは Step E で行う。）

Update `{CR_PATH}/progress.md` step 8 詳細ステップ → `Step C': TM生成中`.

For each `{repo}` in `AFFECTED_REPOS`:
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
    CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
  → let `CHD_CONTENT_FILES`.
  For each file in `CHD_CONTENT_FILES`: Read Section 4 (SP→変更ファイル→変更シンボル). 全ファイルを横断して集約する
  （Step A2 のカバレッジ集約ロジックと同じ走査を再利用する）。
Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md` Section 2 (USDM: UR→SR→SP 階層).

**Section 1: SP→実装ファイル 対応表 の構築**

For each SP in CRS (order: UR→SR→SP):
  Identify parent SR and grandparent UR IDs.
  Search CHD Section 4 for rows where 仕様ID = this SP ID. (For each matched CHD Section 4 row, one TM row per 変更ファイル entry.)
  If multiple repos have CHD entries for the same SP, create one row per (SP, repo, ファイル) combination.
  テストケース列 → `-`（工程11完了後に更新）

If a SP in CRS has no corresponding CHD Section 4 entry:
  Create a row with 変更ファイル = `-`、変更シンボル = `-`、テストケース = `-`.

**Section 2: SP間修正ファイル衝突チェック（CR内）の構築**

Group TM Section 1 rows by 変更ファイル (across all repos).
For each file:
  If modified by ≥2 different SPs:
    Record: ファイルパス, 修正SP一覧（カンマ区切り）, 衝突リスク → ⚠️ 要確認, 備考（空欄）.
  Else: skip.
If no overlaps found → テーブルに1行追加:
  `| （なし） | 衝突なし（全SPが異なるファイルを修正） | — | — |`
  （テンプレートの Section 2 の注記 `※ 衝突なしの場合: 「衝突なし（全SPが異なるファイルを修正）」と記載する` と対応する）

**Section 3: SR完了確認の構築**

For each SR in CRS (order: UR→SR):
  Count SPs under this SR.
  Check TM Section 1: how many of those SPs have 変更ファイル ≠ `-`.
  実装ファイル有無: ✅ あり（1件以上）/ ⬜ なし（0件）.
  状態: ✅ 実装済み（全SP有り）/ ⚠️ 未実装（1件以上 ⬜）.

**TM-{CR}.md を書き出す**

Write `{CR_PATH}/03_change-requirements/TM-{CR}.md` using the template
`~/.claude/skills/xddp.06.design/templates/06_tm-template.md`.

**CRS TM Section 3.1 の「設計」「実装」列を更新する**

Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md`.
For each row in CRS Section 3.1 TM（仕様ID 列が SP ID の行）:
  設計列: ✅（CHD Section 4 に対応エントリがある場合）/ ⬜（ない場合）
  実装列: ✅（TM Section 1 でその SP に 変更ファイル ≠ `-` が1件以上ある場合）/ ⬜（ない場合）
Update CRS in-place. Increment version by 0.1, add 変更履歴 entry: `TM生成に伴い Section 3.1 の設計・実装列を更新`.

**progress.md の 成果物 列を更新**

Read `{CR_PATH}/progress.md`. Set step 8 成果物 →
`[TM-{CR}.md](../03_change-requirements/TM-{CR}.md)`.
Write back.

**警告の出力**

If any SP has no CHD Section 4 entry (変更ファイル = `-`):
  Warn user:
  > ⚠️ 以下のSPはCHDに対応する設計エントリが見つかりませんでした。CHD Section 4 を確認してください:
  > {SP ID 一覧}

If any SP間衝突 found (Section 2 に ⚠️ 要確認 行が1件以上):
  Warn user:
  > ⚠️ 同一ファイルを複数のSPが修正しています。TM Section 2 を確認し、修正箇所の競合がないか確認してください。
  > `{CR_PATH}/03_change-requirements/TM-{CR}.md`

If any SR has 状態 = ⚠️ 未実装（Section 3）:
  Warn user:
  > ⚠️ 実装ファイルが未確認のSRがあります。TM Section 3 を確認してください。

Tell the user:
> ✅ TM（トレーサビリティマトリクス）を生成しました。
> - TM: `{CR_PATH}/03_change-requirements/TM-{CR}.md`
> - CRS TM Section 3.1 の設計・実装列を更新しました。

## Step D: Regenerate CRS Excel (UR-016)

Run only if CRS was updated in Step C.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Regenerate CRS Excel" with:
  CR_PATH: {CR_PATH}
  CR: {CR}

## Step E: Update progress.md

Step 7 (変更設計書作成) → ✅ 完了, 詳細ステップ → `-`.
Step 8 (変更要求仕様書フィードバック・TM生成) → ✅ 完了, 詳細ステップ → `-`.
Next command → `/xddp.07.code {CR}`

## Step F: Report in Japanese
