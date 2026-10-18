---
name: xddp-06-design
description: XDDP フェーズ3: 変更設計書（CHD）を作成し、AIレビュー→修正ループ＋変更要求仕様書へのフィードバックを実施する。「変更設計書を作って」「設計書を書いて」などで起動する。
argument-hint: "[CR番号] [regression [--repo リポジトリ]]"
---

You are orchestrating **XDDP Step 06 (process steps 6a-6b) — Change Design Document + CRS Feedback**.

> The CHD produced here is the design specification coders execute without asking questions. Every gap or ambiguity becomes a defect in the code. Orchestrate with precision — completeness in interface definitions, Before/After design diagrams, and confirmation items is non-negotiable.
> The CHD is a design document, not source code. Coders implement from the design specs.

**Arguments:** $ARGUMENTS = [CR_NUMBER] [regression [--repo リポジトリ]] (optional)

---

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp-common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
REPOS_MAP, REPOS_KEYS, IS_MULTI, DOCS_DIR, DOCS, CR_PROFILE.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`.
Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Resolve HAS_CROSS" with:
  IS_MULTI: {IS_MULTI}, ARTIFACT_PATH: {CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md
→ let `HAS_CROSS`.
（本工程は直前工程＝arch の cross DSN の有無で cross 処理要否を判断する）

## Regression Rerun Entry（`REST_ARGS` の先頭の語が `regression` の場合だけ）

回帰の範囲のやり直し。progress.md の工程の状態は変えない。`REST_ARGS` の先頭の語が `regression` でなければこの節を飛ばして「## Step 0」へ進む。
1. `--repo` の次の語を `REGRESSION_REPOS`（1件）とする。省略時は AFFECTED_REPOS の全件。
2. 工程6a が `✅ 完了` または `🔄 進行中` で、`REGRESSION_REPOS` の各 repo の `{CR_PATH}/06_design/{repo}/CHD-{CR}.md` があることを確かめる。
   無ければ「先に /xddp-06-design {CR} を実行してください」と伝えて終わる。
   `REGRESSION_RERUN` = 工程6a が `✅ 完了` なら `true`、`🔄 進行中` なら `false`（初版の作成中〔Step B2 で止まっている間等〕は版数を上げない）。
3. 準備: `PY=$(command -v python3 || command -v python)`。`DESIGN_CALL_SHARED` を「## Step 0.5」と同じ内容で定義する。`~/.claude/skills/xddp-rules/xddp.design.rules.md` を Read して `DESIGN_RULES` とする（「## Step A」と同じ。Step A3 の `SECTION4_ERRORS` の呼び出しで使う）。
   `BATCH_PLAN` を「## Step A」の 1. と同じ手順で作る（インデックスの骨格は書かない）。
   各バッチファイルのレビュー回数 `last_round` は `{CR_PATH}/06_design/{repo}/review/06_design-review-{UR_ID}[-{N}].md` の「レビュー回数」の値（ファイルが無ければ 0）。
   CRS の UR 抜粋 `crs-scope-{UR_ID}.md` が無ければ「## Step B」と同じコマンドで作る。
4. 「## Step A3: Regression Scope」を `REGRESSION_RERUN: {REGRESSION_RERUN}` で `REGRESSION_REPOS` について行い、続けて「## Step A3-review: Review Regression Rows」を行う（Step A3 は repo の単位で止まらないので、失敗した repo があっても、書き換えたファイルはすべてレビューされる）。
5. 日本語で報告して終わる（「## Step 0」以降は行わない）: `REGRESSION_REPOS` の各 repo の `REGRESSION_NOTES[repo]`、書き換えたバッチファイル、Final Review Pass の結果のファイル、`A3_FAILED_REPOS` があれば失敗の種類ごとに「⚠️ 次の repo は回帰の範囲を算出できませんでした: {repo と stderr}」と次の案内（`kind: section4` は「/xddp-revise {CR} design で CHD §4 を直してから /xddp-06-design {CR} regression --repo {repo} を実行してください」、`kind: candidates` は「stderr の原因〔採用した波紋調査の状態ファイル・CHD のインデックスとバッチファイル等〕を確かめてください〔波紋調査の状態は /xddp-investigate {CR} list〕。直したら /xddp-06-design {CR} regression --repo {repo} を実行してください」）、
   「TSP を作成済みなら /xddp-09-test {CR} を再実行してください」。

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

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6a, STATE: 🔄 進行中, DETAIL_STEP: `Step A: CHD生成中`
If `IS_MULTI`, append a per-repo progress table for step 6a:
```markdown
## 工程6a 変更設計書進捗（リポジトリ別）
| リポジトリ | 設計 | レビュー | 完了日 |
|---|---|---|---|
{for each repo in AFFECTED_REPOS: | {repo} | ⏳ 未着手 | ⏳ 未着手 | - |}
{if HAS_CROSS: | cross | — | ⏳ 未着手 | - |}
```
Write back.

Read `~/.claude/skills/xddp-common/procedures/snapshot-phase-baseline.md`, apply "## Snapshot Phase Baseline" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6a

Let `DESIGN_CALL_SHARED` =
  CR_NUMBER: {CR}
  TODAY: {TODAY}
  （`CR_PROFILE` = `quick` の場合のみ追加）QUICK_PROFILE: `true`
（{repo} に依存しないため、Step A・Step A2 backfill・Step B のどの独立ループからもこの1箇所の
定義をそのまま参照できる。REPO_NAME はループ変数のため各呼び出し箇所に個別記述のまま残す。
`QUICK_PROFILE` も同じ理由で共通定義に含める — quick 時は3箇所すべての呼び出しで単一設計案・
簡略化された確認項目を生成する必要があるため。`full` 時は行自体を追加しないため、エージェント側は
デフォルト値 `false` を受け取り現行動作を維持する）

## Step A0: Reference Lessons Learned Log

Read `~/.claude/skills/xddp-common/procedures/load-lessons-context.md`, apply "## Load Lessons Context" with:
  LESSONS_FILE: {XDDP_DIR}/lessons-learned.md
  TARGET_TAGS: [#方式検討, #設計, #コーディング]
→ let `LESSONS_CONTEXT`.
※ `{DOCS}/{repo}/knowledge/lessons-learned.md`（Layer 2: クローズ済みCR知見）は参照しない
  （xddp-05-arch と同一設計。Layer 1 の作業中高鮮度知見を優先する）。

## Step A-cross: Generate cross/CHD (API-first principle — only when HAS_CROSS = true)

※ LESSONS_CONTEXT は Step A-cross では明示的に使用しない（設計上の意図的省略）。
  cross/CHD はリポジトリ間インタフェース変更サマリに特化した成果物であり、
  過去知見の参照は per-repo CHD 設計（Step A）で行う。xddp-05-arch の Step A-cross と同一方針。

**API-first principle:** Establish the implementation dependency and interface change summary before per-repo CHD design.

Read `{XDDP_DIR}/project-rulebook-cross.md` (if exists) as `CROSS_RULEBOOK_CONTEXT`.

Generate `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` (write directly, not via agent):
- Read `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md`
- Read `{DOCS}/cross/design/` (past cross-repo CHDs, if exists)
- If `CROSS_RULEBOOK_CONTEXT` is non-empty: apply its interface change conventions
  （project-rulebook-cross.md §2 API バージョニング規約・§6 インタフェース変更手順）
  when filling in インタフェース変更サマリ（breaking 判定含む）.
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
（cross行は Step 0.5 の初期値 `| cross | — | ⏳ 未着手 | - |` のまま更新しない — cross/CHD 生成は
エージェントを介さない同期的な直接 Writeのため即時完了し、`設計` 列は恒久的に `—` のまま、
`レビュー` 列も Step B-cross の開始まで `⏳ 未着手` を維持する）

## Step A-scale: CR Scale Warning (orchestrator-side)

`xddp-designer-agent` はバッチ単位のSPしか見えないため、CR全体の規模判定はオーケストレーター側で行う。

Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md` Section 2 (USDM: UR→SR→SP 階層). Count all SP entries → `TOTAL_SP_COUNT`.

If `TOTAL_SP_COUNT > 50`:
  Let `SCALE_WARNING` = `"⚠️ 総SP数が{TOTAL_SP_COUNT}件です。CR分割を検討してください（UR-035）。"`
Else:
  Let `SCALE_WARNING` = 空文字列。

（この警告は Step B2 の `INTRO_NOTE` に追加する。SP数50件は UR-035 の参考目安（500行超）に
近いか判断するための暫定的な代理指標であり、シンボル数→行数の換算根拠は今後要検証。）

## Step A: Generate per-repo Change Design Documents (UR×バッチ単位)

Read `~/.claude/skills/xddp-rules/xddp.design.rules.md` to get `DESIGN_RULES`.

Read `{WORKSPACE_ROOT}/xddp.config.md` lookup already done in CR Resolution; extract `DESIGN_MAX_SP_PER_FILE`
(default: `10`).

**1. Build BATCH_PLAN (once per CR, shared across all repos):**

Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md` Section 2 (USDM: UR→SR→SP 階層).
For each UR in CRS (記載順): collect all SP-IDs under it (across all SR)。UR-ID・SP-ID は CR プレフィクス
付きフル ID（形式 B。例 `CR-2026-970-UR-001`・`CR-2026-970-SP-001-001.010`）。
- CHD ファイル名は**フル UR-ID から生成する**（`CHD-{UR-ID}.md`。`{UR-ID}` はフル UR-ID）。
  例 `CHD-CR-2026-970-UR-001.md`。`CHD-` の直後にフル UR-ID を置くため CR を二重に付けない
  （従来の `CHD-{CR}-UR-XXX.md` とバイト列が一致する）。
- If SP数 ≤ `DESIGN_MAX_SP_PER_FILE`: 1バッチ。`FILE_NAME` = `CHD-{UR-ID}.md`。
- If SP数 > `DESIGN_MAX_SP_PER_FILE`: `DESIGN_MAX_SP_PER_FILE` 件ごとに分割（CRS記載順）。
  `FILE_NAME` = `CHD-{UR-ID}-{N}.md`（`N` = 1, 2, ...）。

`BATCH_PLAN` = list of `{UR_ID, UR_NAME, BATCH_INDEX (例 "1/2"。単一バッチは "-"), SP_IDS, FILE_NAME}`.

**2. Write index skeleton (per repo, direct Write — not via agent):**

For each `{repo}` in `AFFECTED_REPOS`:
  Using `~/.claude/skills/xddp-06-design/templates/06_change-design-document-index-template.md`,
  Write `{CR_PATH}/06_design/{repo}/CHD-{CR}.md` with Section 2 の全行を `BATCH_PLAN` から構築する
  （列: UR ID・UR名・バッチ・SP数・ファイル）。「該当変更」列は全行 `(生成中)` の placeholder とする。

**3. Invoke xddp-designer-agent per (repo, UR×バッチ):**

For each `{repo}` in `AFFECTED_REPOS`:

Update per-repo progress table: `| {repo} | 🔄 進行中 | ⏳ 未着手 | - |`

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Discover CHD Files" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `CHD_INDEX_FILE`（`CHD_CONTENT_FILES` は本呼び出しでは未使用。`## Discover CHD Files` は
インデックスファイル未存在時に `CHD_CONTENT_FILES` を空リストで返す設計のため、Step A 時点で
CHD が未生成の repo に対して呼び出しても `CHD_INDEX_FILE`（パス文字列）の取得は安全に行える）.

Read `~/.claude/skills/xddp-common/procedures/build-design-spec-params.md`, apply "## Build Design Spec Params" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `DESIGN_SPEC_PARAMS_BASE`.

Read `~/.claude/skills/xddp-common/procedures/load-steering-context.md`, apply "## Load Steering Context" with:
  XDDP_DIR: {XDDP_DIR}
  REPO_NAME: {repo}
→ let `RULEBOOK_CONTEXT`.

For each entry in `BATCH_PLAN`:

**Agent tool** `subagent_type=xddp-designer-agent`:
```
{DESIGN_CALL_SHARED を展開}
REPO_NAME: {repo}
{DESIGN_SPEC_PARAMS_BASE を展開}
TEMPLATE_FILE: ~/.claude/skills/xddp-06-design/templates/06_change-design-document-template.md
UR_SCOPE: {entry.SP_IDS}
OUTPUT_FILE: {CR_PATH}/06_design/{repo}/{entry.FILE_NAME}
INDEX_FILE: {CHD_INDEX_FILE}
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

`BATCH_PLAN` の全エントリについてこのリポジトリの生成が終わったら、
Update per-repo progress table: `| {repo} | ✅ 完了 | ⏳ 未着手 | - |`

## Step A2: SP Coverage Auto-Verification & Backfill

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6a, STATE: 🔄 進行中, DETAIL_STEP: `Step A2: カバレッジ検証中`

1. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-06-design/scripts/chd_sp_coverage.py --crs {CR_PATH}/03_change-requirements/CRS-{CR}.md --design-dir {CR_PATH}/06_design --repos {AFFECTED_REPOS をカンマ区切りで展開}{HAS_CROSS の場合は ",cross" を追加} --cr {CR}`
   → 出力 JSON の `expected`（`EXPECTED_SP_IDS`）・`covered`（`COVERED_SP_IDS`）・`missing`（`MISSING`）・
   `by_repo`（各repoの `chd_index`・`content_files`・`covered`）を採用する。
   If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
2. `MISSING` が空なら次のステップ（Step B）へ進む。
4. 各 missing SP-ID について:
   a. `BATCH_PLAN` からこのSPが属する (UR, バッチ) を特定する。
   b. 各 `{repo}` の該当バッチファイルを確認し、**同じバッチ内の他のSPがそのファイルで
      Section 4 に1件以上の変更エントリを持つ repo** を「有力repo」とする。
   c. **有力repoが「ちょうど1つ」の場合のみ**自動補完する（安全側に倒す）:
      Step A本体の呼び出しと同様に `CRS_FILE, SPO_FILE, DSN_INDEX_FILE` 等の既存パラメータは
      repo・UR に対応する値でそのまま渡し、加えて以下を指定して `xddp-designer-agent` を再呼び出しする:

      Read `~/.claude/skills/xddp-common/procedures/build-design-spec-params.md`, apply "## Build Design Spec Params" with:
        CR_PATH: {CR_PATH}, REPO_NAME: {その有力repo}, CR: {CR}
      → let `DESIGN_SPEC_PARAMS_BASE`.

      **Agent tool** `subagent_type=xddp-designer-agent`:
      ```
      {DESIGN_CALL_SHARED を展開}
      REPO_NAME: {その有力repo}
      {DESIGN_SPEC_PARAMS_BASE を展開}
      OUTPUT_FILE: {その有力repoのバッチファイル}
      INDEX_FILE: {その有力repoのインデックスファイル（CHD-{CR}.md）}
      BACKFILL_SP_IDS: [missing SP-ID]
      ```
      （`CHD_INDEX_FILE` は `{repo}` にバインドされた Step A/Step B 用の定義であり、
      `{その有力repo}` はそれとは異なる変数のため再利用せず、この1箇所のみで個別に `INDEX_FILE` を
      記述する。1箇所のみの使用であれば重複のリスクがないため、専用の共有変数は導入しない）
      （`UR_SCOPE` は本呼び出しでは渡さない — `BACKFILL_SP_IDS` モードは `UR_SCOPE` を使わず
      `BACKFILL_SP_IDS` のみで対象SPを特定する。`REVIEW_FILE` モードとは排他。
      1 SP につき本ステップでの自動補完は1回のみ試行する）
      再呼び出し後、その repo のファイルを再チェックし、補完できたか確認する。
   d. **有力repoが0個、または2個以上（どのrepoの担当か一意に決まらない）の場合**、
      または c. の補完後も未解消の場合:
      自動補完を行わず `UNRESOLVED_MISSING` に記録する
      （設計根拠: docs/adr/ADR-0002-coverage-backfill-ambiguous-repo.md）。
5. `UNRESOLVED_MISSING` が空でない場合、Step B2 の `INTRO_NOTE` に追加する文言を
   `MISSING_SP_NOTE` として保持する:
   `"⚠️ 以下のSPはいずれのリポジトリのCHDにも設計エントリが見つかりませんでした（または
   担当リポジトリが一意に決まりません）。担当リポジトリを確認し手動で追記してください:
   {SP-ID一覧}"`

## Step A3: Regression Scope

Input: 対象の repo（既定は AFFECTED_REPOS）、`REGRESSION_RERUN`（既定 `false`）。
Let `PY` = `$(command -v python3 || command -v python)`. Let `A3_CHANGED_FILES` = []. Let `A3_FAILED_REPOS` = []. Let `A3_FIXED_FILES` = []（この呼び出しで `SECTION4_ERRORS` で直したバッチファイル）。
`A3_CHANGED_FILES`・`A3_FIXED_FILES` に足すときは、既にあれば足さない。
このステップは repo の単位で止まらない（失敗した repo は飛ばして `A3_FAILED_REPOS` に足し、次の repo へ進む）。
Let `CODE_CHANGED_FLAG` = progress.md の工程7 が `⬜ 未着手` でなければ `--code-changed`、それ以外は空文字列。
`REGRESSION_NOTES`（repo → 注記）が未定義なら {} とする（呼ばれるたびに、対象の repo の分だけを置き換え、他の repo の分は残す）。
If `DEVELOPMENT_MODE` = `new`: `REGRESSION_NOTE` = 空文字列とし、このステップの残りを行わない（既存の動作が無いため回帰の対象が無い。§7.1 は Step A の「なし」のまま）.

（Step A2 の後に続けて行う場合だけ。`regression` のやり直し・Step A3-refresh から呼ばれた場合は行わない）Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6a, STATE: 🔄 進行中, DETAIL_STEP: `Step A3: 回帰の範囲の算出中`

For each `{repo}` in 対象の repo:
0. `REGRESSION_NOTES[repo]` = 空文字列。
1. `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` が無ければこの repo を飛ばす（§7.1 は「なし」のまま）。
2. Read `~/.claude/skills/xddp-common/procedures/regression-status.md`, apply "## Regression Status" with CR: {CR}, CR_PATH: {CR_PATH}, REPO: {repo}, MODE: `params` → let `REGRESSION_PARAMS_KEY`, `REGRESSION_BACKEND`.
3. Run via Bash: `"$PY" ~/.claude/skills/xddp-06-design/scripts/chd_regression.py elements --design-dir {CR_PATH}/06_design --specout-dir {CR_PATH}/04_specout --repos {REPOS_KEYS をカンマ区切り} --repo {repo} --cr {CR} --out {CR_PATH}/06_design/{repo}/work/regression/regression-elements.json`
   exit 1 なら（§4 の書式の誤り。stderr は1行に1件 `{バッチファイル}\t{行番号}\t{理由}`）:
   a. stderr をバッチファイルごとにまとめる（`elements` は関係する他の repo の §4 も読むので、他の repo のバッチファイルも含みうる）。`A3_FIXED_FILES` に無い各バッチファイルについて（同じ呼び出しの中で、別の repo の処理で直したファイルを2回直さない）、そのファイルの repo（`{CR_PATH}/06_design/{err_repo}/` の `err_repo`）の "## Discover CHD Files" で `ERR_INDEX_FILE` を解決し、**Agent tool** `subagent_type=xddp-designer-agent` を1回呼ぶ:
      ```
      {DESIGN_CALL_SHARED を展開}
      REPO_NAME: {err_repo}
      REPO_PATH: {REPOS_MAP[err_repo]}
      OUTPUT_FILE: {そのバッチファイル}
      INDEX_FILE: {ERR_INDEX_FILE}
      TEMPLATE_FILE: ~/.claude/skills/xddp-06-design/templates/06_change-design-document-template.md
      DESIGN_TASK: {DESIGN_RULES の内容をそのまま渡す}
      SECTION4_ERRORS: {そのバッチファイルの stderr の行}
      REGRESSION_RERUN: {REGRESSION_RERUN}
      ```
      Append そのバッチファイル to `A3_CHANGED_FILES` and `A3_FIXED_FILES`.
   b. 3. のコマンドをもう一度実行する。exit 0 なら 4. へ進む。
   c. なお exit 1 なら: Run via Bash: `"$PY" ~/.claude/skills/xddp-06-design/scripts/chd_regression.py invalidate --work-dir {CR_PATH}/06_design/{repo}/work/regression --human-out {CR_PATH}/06_design/{repo}/regression-candidates.md`。`{repo, kind: section4, stderr}` を `A3_FAILED_REPOS` に足し、`REGRESSION_NOTES[repo]` = `"⚠️ {repo}: CHD §4 の書式の誤りで回帰の範囲を算出できなかった（回帰の行は書いていない。誤りのあるファイル: {stderr のバッチファイルの一覧〔他の repo のファイルを含みうる〕}）: {stderr}。/xddp-revise {CR} design で §4 を直すと、Step B2 で回帰の範囲を算出し直す（工程6 の後なら /xddp-06-design {CR} regression --repo {repo}）"` とし、この repo の残り（4.〜9.）を行わない（`invalidate` が入力の記録を消すので、Step A3-refresh と /xddp-09-test の Step 0.3 が `RECORDED: false` として拾う）。
4. Run via Bash: `"$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py regression-candidates --repo-dir {CR_PATH}/04_specout/{repo} --repo {repo} --repo-path {REPOS_MAP[repo]} --elements-file {CR_PATH}/06_design/{repo}/work/regression/regression-elements.json --design-dir {CR_PATH}/06_design （CR_PROFILE = quick の場合のみ）--max-distance 1 --backend {REGRESSION_BACKEND} --exclude '{EXCLUDE_PATTERNS}' --include-ext '{INCLUDE_EXTENSIONS}' --hit-filter {SPECOUT_HIT_FILTER} --slice-h-as {SPECOUT_SLICE_H_AS} {CODE_CHANGED_FLAG} --out-dir {CR_PATH}/06_design/{repo}/work/regression --human-out {CR_PATH}/06_design/{repo}/regression-candidates.md`
   → let `RC_RESULT`。exit 1・2 なら: 3. の c と同じく `invalidate` を実行し、`{repo, kind: candidates, stderr}` を `A3_FAILED_REPOS` に足し、`REGRESSION_NOTES[repo]` = `"⚠️ {repo}: 回帰の候補を算出できなかった（回帰の行は書いていない）: {stderr}"` とし、この repo の残り（5.〜9.）を行わない。
5. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Discover CHD Files"（CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}）→ `CHD_INDEX_FILE`。
6. For each entry in `RC_RESULT.batches` で `digest_file` があるもの（確認対象のあるバッチ）:
   **Agent tool** `subagent_type=xddp-designer-agent`:
   ```
   {DESIGN_CALL_SHARED を展開}
   REPO_NAME: {repo}
   REPO_PATH: {REPOS_MAP[repo]}
   OUTPUT_FILE: {entry.batch_file}
   INDEX_FILE: {CHD_INDEX_FILE}
   REGRESSION_DIGEST: {entry.digest_file}
   REGRESSION_RERUN: {REGRESSION_RERUN}
   ```
   Append `{entry.batch_file}` to `A3_CHANGED_FILES`.
7. Run via Bash: `"$PY" ~/.claude/skills/xddp-06-design/scripts/chd_regression.py check --candidates {CR_PATH}/06_design/{repo}/work/regression/regression-candidates.json --design-dir {CR_PATH}/06_design --repo {repo} --cr {CR}` → let `CHECK`。
   `CHECK.unmapped` があれば、その候補の書き先のバッチごとに 6. のエージェントを1回だけ `REGRESSION_UNMAPPED: {そのバッチの unmapped}` を足して再度呼び、7. をもう一度行う（候補の書き先のバッチは `regression-candidates.json` の `candidates[].batch_file`）。
   exit 1（§7・§7.1 の表の書式の誤り）なら stderr を `REGRESSION_NOTES[repo]` に `"⚠️ {repo}: CHD §7・§7.1 の表を読めない: {stderr}"` として書き、8. へ進む。
8. `REGRESSION_NOTES[repo]` に次を書く（空の項目は書かない）:
   - `"{repo}: 回帰の確認対象 {required の合計} 件（§7 の回帰の行 {mapped_count}・§7.1 {excluded_count}）。確認対象にしなかった候補: 名前の一致のみ {name_only_count}・上限超過 {over_limit_count}（全量: {CR_PATH}/06_design/{repo}/regression-candidates.md。確認項目にする場合は /xddp-revise {CR} design で §7 に回帰の行を足す）"`（件数は `RC_RESULT.batches` の合計）
   - `CHECK.unmapped` が残れば `"⚠️ §7・§7.1 のどちらにも無い回帰の候補: {一覧}"`
   - `CHECK.unknown` があれば `"候補に無くなった回帰の行・§7.1 の行（消すかは人が決める）: {一覧}"`
   - `direct_search_elements`・`self_truncated_elements` があれば `"波紋調査でたどりきれなかった変更シンボル（直接の参照元を候補に足した）: {一覧}。深く追う場合は /xddp-investigate {CR} ripple --adopt --repo {repo} {シンボル}"`
   - `direct_search_impossible` があれば `"⚠️ 識別子として検索できない変更シンボル（回帰の候補を出せない。人が確認する）: {一覧}"`
   - `missing_files` があれば `"⚠️ CHD §4 の変更ファイルがリポジトリに見つからない変更シンボル（素の名前で検索した。§4 のパスを確認する）: {一覧}"`
   - `truncated_elements` があれば `"下流が打ち切られた変更シンボル: {シンボルと理由}"`
   - `after_coding_elements` があれば `"工程7 の後のコードで直接の参照元を検索した変更シンボル（変更前の参照元は含まない。人が確認する）: {一覧}"`
9. Run via Bash: `"$PY" ~/.claude/skills/xddp-06-design/scripts/chd_regression.py record --design-dir {CR_PATH}/06_design --specout-dir {CR_PATH}/04_specout --repos {REPOS_KEYS をカンマ区切り} --repo {repo} --cr {CR} --params-key '{REGRESSION_PARAMS_KEY}' --out {CR_PATH}/06_design/{repo}/work/regression/regression-inputs.json`

Let `REGRESSION_NOTE` = AFFECTED_REPOS の順に、`REGRESSION_NOTES` の空でない値を改行でつないだもの（今回やり直さなかった repo の分も含む。Step B2 の `INTRO_NOTE` はこれを使う）。

## Step A3-review: Review Regression Rows

Step A3 のあと Step B を通らない場合（やり直しの入口・Step A3-refresh）だけ行う（Step A3 の後に続けて Step B へ進む通常の流れでは行わない）。
For each `{file}` in `A3_CHANGED_FILES`（対応する `BATCH_PLAN` エントリの `UR_ID` を特定する）:
  Read `~/.claude/skills/xddp-common/procedures/final-review-pass.md`, apply "## Final Review Pass" with:
    DOCUMENT_TYPE: CHD, NEXT_DOCUMENT_TYPE: TSP, TARGET_FILE: {file}, REFERENCE_FILES: {Step B と同一}, REVIEW_ROUND: (last_round + 1),
    OUTPUT_FILE: {CR_PATH}/06_design/{file の repo}/review/06_design-review-{UR_ID}[-{N}].md（`last_round` も file の repo のレビューファイルから読む。A3_CHANGED_FILES は §4 の書式を直した他の repo のファイルを含みうる）

## Step A3-refresh: Refresh Regression Scope If Stale

呼ばれたときだけ行う（Step B・Step B2 から呼ぶ。Step A3 の後に続けて行わない）。
Input: 確かめる repo の一覧（既定は AFFECTED_REPOS）、`WITH_REVIEW`（既定 `true`。`false` なら Step A3-review を行わない）。
1. Let `A3_CHANGED_FILES` = []. Let `REFRESHED_REPOS` = [].
2. For each `{repo}`（DEVELOPMENT_MODE ≠ new かつ SPO がある repo）:
   Read `~/.claude/skills/xddp-common/procedures/regression-status.md`, apply "## Regression Status" with CR: {CR}, CR_PATH: {CR_PATH}, REPO: {repo}, MODE: `status` → `STALE`, `RECORDED`.
   `STALE` が true または `RECORDED` が false なら、`{repo}` を `REFRESHED_REPOS` に足す。
3. `REFRESHED_REPOS` が空なら終わる（`A3_CHANGED_FILES` は空のまま。`REGRESSION_NOTES` は変えない）。
4. 「## Step A3」を1回だけ、対象の repo＝`REFRESHED_REPOS`・`REGRESSION_RERUN: false` で行う（repo ごとに呼ばない。工程6 の初版の作成の流れの中なので版数を上げない。`REFRESHED_REPOS` の分の `REGRESSION_NOTES` だけが置き換わり、`A3_CHANGED_FILES` はその全 repo の書き換えたファイルになる）。
   `WITH_REVIEW` が true なら続けて「## Step A3-review」を行う。
   （1つの呼び出しにつき1回だけ。やり直した後にさらに古いと判定されても繰り返さない）

## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.CHD` rounds)

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6a, STATE: 🔄 進行中, DETAIL_STEP: `Step B: AIレビュー中`

Let `OVERSIZED_FILES` = [].

For each `{repo}` in `AFFECTED_REPOS`:

Update per-repo progress table: `| {repo} | ✅ 完了 | 🔄 進行中 | - |`

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Discover CHD Files" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `CHD_INDEX_FILE`, `CHD_CONTENT_FILES`.

For each `{file}` in `CHD_CONTENT_FILES`（対応する `BATCH_PLAN` エントリの `UR_ID`／`BATCH_INDEX`／`SP_IDS` を特定する）:

Run via Bash（当該 UR の Review Loop 初回のみ実行し、ラウンド間は再生成せず使い回す。CRS は
Step B 実行中に変わらないため）:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/crs_ur_scope.py --crs {CR_PATH}/03_change-requirements/CRS-{CR}.md --ur-id {entry.UR_ID} --out {CR_PATH}/06_design/{repo}/crs-scope-{entry.UR_ID}.md`
→ 失敗時（`ur_found: false` を含む）は工程を止めて人に報告する（ベストエフォート化しない。CRS の
  該当UR欠落はレビュー対象の完全性に関わる異常系のため）。

Read `~/.claude/skills/xddp-common/procedures/review-loop.md`, apply "## Review Loop" with:
  DOCUMENT_TYPE: CHD
  NEXT_DOCUMENT_TYPE: TSP
  CONFIG_KEY: REVIEW_MAX_ROUNDS.CHD
  （`CR_PROFILE` = `quick` の場合のみ追加）MAX_ROUNDS_OVERRIDE: `1`
  TARGET_FILE: {file}
  REFERENCE_FILES: [{CR_PATH}/06_design/{repo}/crs-scope-{entry.UR_ID}.md, （{CR_PATH}/04_specout/{repo}/SPO-{CR}.md が存在する場合のみ追加）{CR_PATH}/04_specout/{repo}/SPO-{CR}.md, （{CR_PATH}/06_design/{repo}/work/regression/regression-digest-{file のファイル名} が存在する場合のみ追加）その要約]
  REVIEW_OUTPUT_FILE: {CR_PATH}/06_design/{repo}/review/06_design-review-{UR_ID}[-{N}].md
  FIXER_AGENT: xddp-designer-agent
  （`CR_PROFILE` = `quick` の場合のみ追加）EXTRA_REVIEWER_PARAMS: QUICK_PROFILE: `true`
  FIXER_PARAMS:
    {DESIGN_CALL_SHARED を展開}
    REPO_NAME: {repo}
    REPO_PATH: {REPOS_MAP[repo]}
    UR_SCOPE: {entry.SP_IDS}
    OUTPUT_FILE: {file}
    INDEX_FILE: {CHD_INDEX_FILE}
    REVIEW_FILE: {CR_PATH}/06_design/{repo}/review/06_design-review-{UR_ID}[-{N}].md
    （要約が存在する場合のみ追加）REGRESSION_DIGEST_REF: {その要約}
  PROGRESS_CR_PATH: {CR_PATH}
  PROGRESS_STEP_NUM: 6a
  METRICS_TARGET: {repo}/{UR_ID}

Read `{file}` Section 4 (トレーサビリティマトリクス). Count rows.
If row count > `DESIGN_MAX_SYMBOLS_PER_FILE`（default: `30`）: append `{file}` to `OVERSIZED_FILES`.

`CHD_CONTENT_FILES` の全ファイルについてこのリポジトリのレビューが終わったら、
Update per-repo progress table: `| {repo} | ✅ 完了 | ✅ 完了 | {TODAY} |`

全 repo の Review Loop の後に「## Step A3-refresh」を行う（レビューの修正で §4 が変わった repo の回帰の範囲を作り直す）。

SCALE_WARNING は「## Step B2: Human Review Gate」の `INTRO_NOTE` で中継表示する。

## Step B-cross: Cross CHD AI Review (only when HAS_CROSS = true)

If `HAS_CROSS`:
  Update per-repo progress table: `| cross | — | 🔄 進行中 | - |`

  Read `~/.claude/skills/xddp-common/procedures/cross-artifact-review.md`, apply "## Cross Artifact Review" with:
    CR_PATH: {CR_PATH}
    STEP_NUM: 6a
    STEP_LABEL: `Step B-cross`
    DOCUMENT_TYPE: CHD
    NEXT_DOCUMENT_TYPE: TSP
    TARGET_FILE: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
    REFERENCE_FILES: [
      {CR_PATH}/03_change-requirements/CRS-{CR}.md,
      {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md (if exists),
      {CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md (if exists),
      for each {repo} in AFFECTED_REPOS: {CR_PATH}/06_design/{repo}/CHD-{CR}.md (if exists)
    ]
    OUTPUT_FILE: {CR_PATH}/06_design/cross/review/06_design-cross-review.md
    DOC_DESCRIPTION: `インタフェース変更のサマリに特化した成果物`
    （`CR_PROFILE` = `quick` の場合のみ追加）EXTRA_REVIEWER_PARAMS: QUICK_PROFILE: `true`

  Update per-repo progress table: `| cross | — | ✅ 完了 | {TODAY} |`

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
`MISSING_SP_NOTE`（Step A2）、`REGRESSION_NOTE`（Step A3。全 repo の `REGRESSION_NOTES` をつないだもの）。

Build `OPTION_NOTE`:
If `OVERSIZED_FILES` is non-empty:
  `OPTION_NOTE` = `"⚠️ 以下のファイルは変更シンボル数が{DESIGN_MAX_SYMBOLS_PER_FILE}件を超えています。
  /xddp-revise で手動分割を検討してください: {OVERSIZED_FILES一覧}"`
Else: `OPTION_NOTE` = 空文字列。

Read `~/.claude/skills/xddp-common/procedures/human-review-gate.md`, apply "## Human Review Gate" with:
  CR_PATH: {CR_PATH}
  STEP_NUM: 6a
  STEP_LABEL: `Step B2`
  ARTIFACTS_TEXT: {built above}
  INTRO_NOTE: {built above}
  OPTION_NOTE: {built above}
  REVISE_COMMAND: `/xddp-revise {CR} design`（対象リポジトリを指定）
→ let `CHANGED`.

If `CHANGED`:
- 「## Step A3-refresh」を `WITH_REVIEW: false` で行う（書き換えたファイルは直後の Final Review Pass でレビューされる）。
- For each `{repo}` in `AFFECTED_REPOS`, for each `{file}` in `CHD_CONTENT_FILES`（Step B と同一の解決方法）:
  Read `~/.claude/skills/xddp-common/procedures/final-review-pass.md`, apply "## Final Review Pass" with:
    DOCUMENT_TYPE: CHD
    NEXT_DOCUMENT_TYPE: TSP
    TARGET_FILE: {file}
    REFERENCE_FILES: {Step B と同一}
    REVIEW_ROUND: (last_round + 1)
    OUTPUT_FILE: {CR_PATH}/06_design/{repo}/review/06_design-review-{UR_ID}[-{N}].md
- If HAS_CROSS and the user changed cross/ CHD: Read `~/.claude/skills/xddp-common/procedures/final-review-pass.md`,
  apply "## Final Review Pass" with:
    DOCUMENT_TYPE: CHD
    NEXT_DOCUMENT_TYPE: TSP
    TARGET_FILE: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md
    REFERENCE_FILES: {Step B-cross と同一}
    REVIEW_ROUND: (last_round + 1)
    OUTPUT_FILE: {CR_PATH}/06_design/cross/review/06_design-cross-review.md
- `A3_CHANGED_FILES` が空でなければ、Read `~/.claude/skills/xddp-common/procedures/human-review-gate.md`, apply "## Human Review Gate" with
  CR_PATH: {CR_PATH}, STEP_NUM: 6a, STEP_LABEL: `Step B2（回帰の範囲）`, ARTIFACTS_TEXT: {A3_CHANGED_FILES の一覧と `REFRESHED_REPOS` の各 repo の `{CR_PATH}/06_design/{repo}/regression-candidates.md`}, INTRO_NOTE: {`REFRESHED_REPOS` の順に `REGRESSION_NOTES[repo]` の空でない値を改行でつないだもの}, OPTION_NOTE: 空, REVISE_COMMAND: `/xddp-revise {CR} design`
  → `CHANGED` なら A3_CHANGED_FILES について Final Review Pass を（上と同じ引数で）行う（ここでは Step A3-refresh を繰り返さない。なお古ければ /xddp-09-test の Step 0.3 が知らせる）。

## Step C: Feed Design Results Back to CRS

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6a, STATE: 🔄 進行中, DETAIL_STEP: `Step C: CRSフィードバック中`
Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6b, STATE: 🔄 進行中, DETAIL_STEP: `Step C: CRSフィードバック中`

For each `{repo}` in `AFFECTED_REPOS`: Read `~/.claude/skills/xddp-common/SKILL.md`, apply
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

（注: このステップでは step 6b の詳細ステップのみ更新する。step 6b の状態完了マークは Step E で行う。）

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6b, STATE: 🔄 進行中, DETAIL_STEP: `Step C': TM生成中`

For each `{repo}` in `AFFECTED_REPOS`:
  Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Discover CHD Files" with:
    CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
  → let `CHD_CONTENT_FILES`.
  For each file in `CHD_CONTENT_FILES`: Read Section 4 (SP→変更ファイル→変更シンボル。1行1識別子). 全ファイルを横断して集約する
  （Step A2 のカバレッジ集約ロジックと同じ走査を再利用する）。
Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md` Section 2 (USDM: UR→SR→SP 階層).

**Section 1: SP→実装ファイル 対応表 の構築**

For each SP in CRS (order: UR→SR→SP):
  Identify parent SR and grandparent UR IDs.
  Search CHD Section 4 for rows where 仕様ID = this SP ID. (Group matched CHD Section 4 rows by (SP, repo, 変更ファイル); one TM row per group, 変更シンボル = その group の変更シンボルをカンマ区切りで連結.)
  If multiple repos have CHD entries for the same SP, create one row per (SP, repo, ファイル) combination.
  テストケース列 → `-`（工程9完了後に更新）

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
`~/.claude/skills/xddp-06-design/templates/06_tm-template.md`.

**CRS TM Section 3.1 の「設計」「実装」列を更新する**

Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md`.
For each row in CRS Section 3.1 TM（仕様ID 列が SP ID の行）:
  設計列: ✅（CHD Section 4 に対応エントリがある場合）/ ⬜（ない場合）
  実装列: ✅（TM Section 1 でその SP に 変更ファイル ≠ `-` が1件以上ある場合）/ ⬜（ない場合）
Update CRS in-place. Increment version by 0.1, add 変更履歴 entry: `TM生成に伴い Section 3.1 の設計・実装列を更新`.

**progress.md の 成果物 列を更新**

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6b, STATE: 🔄 進行中, DETAIL_STEP: `Step C': TM生成中`,
  ARTIFACT_LINK: `[TM-{CR}.md](03_change-requirements/TM-{CR}.md)`

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

Read `~/.claude/skills/xddp-common/procedures/regenerate-crs-excel.md`, apply "## Regenerate CRS Excel" with:
  CR_PATH: {CR_PATH}
  CR: {CR}

## Step E: Update progress.md

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6a, STATE: ✅ 完了, DETAIL_STEP: `-`,
  ARTIFACT_LINK: `[06_design/](06_design/)`
Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 6b, STATE: ✅ 完了, DETAIL_STEP: `-`
Next command → `/xddp-07-code {CR}`

## Step F: Report in Japanese
