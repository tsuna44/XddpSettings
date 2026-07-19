---
description: XDDP スキル共通ロジック。CR 番号の解決・CR非依存の config 読み込みなどを定義する。
user-invocable: false
---

# XDDP Common Logic

## Load Config

xddp.config.md を探索・読み込み、CR に依存しない標準設定バンドルを返す共通手順。CR解決が不要な
スキル（`xddp.status`・`xddp.codemap`・`xddp.update-knowledge`・`xddp.fill-rulebook` 等）はこちらを
直接使う。CR解決が必要なスキルは `## CR Resolution` を使う（内部で本プロシージャの処理を利用する）。

**Input:**
- `NOT_FOUND_MESSAGE`（任意, default: `"xddp.config.md が見つかりません。ワークスペースルートまたは
  そのサブディレクトリで実行してください。"`）: `xddp.config.md` が見つからない場合に表示するメッセージ。
  呼び出し元固有の案内文が必要な場合に上書きする（例: `xddp.fill-rulebook` の
  「`/xddp.01.init` を先に実行してください」）。

**Output:** `WORKSPACE_ROOT`, `XDDP_DIR`（default: `xddp`）, `CR_PREFIX`（default: `CR`）,
  `DOCS_DIR`（default: `baseline_docs`）, `DOCS`（= `{WORKSPACE_ROOT}/{DOCS_DIR}`）,
  `REPOS_MAP`（リポジトリ名→パスの辞書）, `REPOS_KEYS`（リポジトリ名一覧。`REPOS:` が未設定・空の場合は空リスト）,
  `IS_MULTI`（= len(REPOS_KEYS) ≥ 2）, `DEVELOPMENT_MODE`（default: `change`）,
  `MIN_COVERAGE`（default: `80`）, `TEST_COVERAGE_TARGET`（default: `C1`）,
  `EXCLUDE_PATTERNS`（default: `tests/,test/,__tests__/,spec/,specs/,__mocks__/,fixtures/,vendor/,node_modules/`）,
  `INCLUDE_EXTENSIONS`（default: 空）, `MAX_WAVE_DEPTH`（default: `10`）,
  `SPECOUT_MAX_AFFECTED_FILES`（default: `20`）, `SPECOUT_MAX_FILES_PER_MODULE`（default: `10`）,
  `SPECOUT_DIAGRAM_LEVEL`（default: `standard`）, `SPECOUT_SEQUENCE_LEVELS`（default: `module, class`）

**Process:**
1. Search for `xddp.config.md` upward from cwd to determine `WORKSPACE_ROOT`.
   If not found: report `{NOT_FOUND_MESSAGE}` and stop.
2. **`{WORKSPACE_ROOT}/xddp.config.md` を1回 Read し、以下の全標準キーをまとめて取得する**
   （個別スキルが同じファイルを再度 Read することを避けるため）:
   - `XDDP_DIR`（default: `xddp`）, `CR_PREFIX`（default: `CR`）, `DOCS_DIR`（default: `baseline_docs`）
   - `REPOS:` マッピング → `REPOS_MAP`（repo名→パス）, `REPOS_KEYS`（repo名一覧。`REPOS:` が未設定・空の場合は空リスト）
   - `DEVELOPMENT_MODE`（default: `change`）, `MIN_COVERAGE`（default: `80`）, `TEST_COVERAGE_TARGET`（default: `C1`）
   - `EXCLUDE_PATTERNS` = 設定キー `SPECOUT_EXCLUDE_PATTERNS`（default: 前述）,
     `INCLUDE_EXTENSIONS` = 設定キー `SPECOUT_INCLUDE_EXTENSIONS`（default: 空）,
     `MAX_WAVE_DEPTH` = 設定キー `SPECOUT_MAX_WAVE_DEPTH`（default: `10`）
     （注: 出力変数名は `xddp.04.specout/SKILL.md` が本文中で既に使用している短縮エイリアス名に合わせている。
     `xddp.config.md` 上のキー名は `SPECOUT_*` だが、出力変数名は本文側の既存名を優先する）
   - `SPECOUT_MAX_AFFECTED_FILES`（default: `20`）, `SPECOUT_MAX_FILES_PER_MODULE`（default: `10`）,
     `SPECOUT_DIAGRAM_LEVEL`（default: `standard`）, `SPECOUT_SEQUENCE_LEVELS`（default: `module, class`）
     （出力変数名は `xddp.config.md` 上のキー名をそのまま使う — `agents/xddp-specout-agent.md` の入力契約名
     と一致させ、呼び出し元スキルが変換なしで直接渡せるようにするため。`xddp.04.specout` がこれらを
     discovery・document 両フェーズのエージェント呼び出しにそのまま渡す）
3. Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`（パス文字列の構築のみ。存在チェックは呼び出し元が必要に応じて行う）。
4. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2)。
5. `REPOS:` が未設定または空の場合のエラー処理（停止するか・初回設定を促すか等）は呼び出し元スキルの裁量に
   委ねる（スキルによって `REPOS:` の必須/任意の扱いが異なるため。本プロシージャ自身はここでは停止しない）。
6. Return all Output values.

## CR Resolution

**Input:** `RAW_ARGS` = trimmed string of $ARGUMENTS
**Output:** `CR`（解決済みCR番号）, `REST_ARGS`（CR以降の残り引数）、および上記 `## Load Config` が
返す標準設定バンドル全て（`WORKSPACE_ROOT`/`XDDP_DIR`/`CR_PREFIX`/
`DOCS_DIR`/`DOCS`/`REPOS_MAP`/`REPOS_KEYS`/`IS_MULTI`/`DEVELOPMENT_MODE`/`MIN_COVERAGE`/
`TEST_COVERAGE_TARGET`/`EXCLUDE_PATTERNS`/`INCLUDE_EXTENSIONS`/`MAX_WAVE_DEPTH`/
`SPECOUT_MAX_AFFECTED_FILES`/`SPECOUT_MAX_FILES_PER_MODULE`/`SPECOUT_DIAGRAM_LEVEL`/
`SPECOUT_SEQUENCE_LEVELS`）
On failure, report error and stop.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Config"
→ let `WORKSPACE_ROOT`, `XDDP_DIR`, `CR_PREFIX`, `DOCS_DIR`, `DOCS`, `REPOS_MAP`, `REPOS_KEYS`,
`IS_MULTI`, `DEVELOPMENT_MODE`, `MIN_COVERAGE`, `TEST_COVERAGE_TARGET`, `EXCLUDE_PATTERNS`,
`INCLUDE_EXTENSIONS`, `MAX_WAVE_DEPTH`, `SPECOUT_MAX_AFFECTED_FILES`, `SPECOUT_MAX_FILES_PER_MODULE`,
`SPECOUT_DIAGRAM_LEVEL`, `SPECOUT_SEQUENCE_LEVELS`.

### Step 1: Identify CR from arguments

Let `FIRST_ARG` = first token of `RAW_ARGS`.

- `FIRST_ARG` starts with `{CR_PREFIX}-`
  → `CR = FIRST_ARG`, `REST_ARGS` = remaining tokens. Done.
- `FIRST_ARG` is empty or does not start with `{CR_PREFIX}-`
  → `REST_ARGS = RAW_ARGS` (treat all tokens as secondary args). Go to Step 2.

> **Skills that use secondary args:**
> - `xddp.review`: first token of `REST_ARGS` → `DOCUMENT_TYPE`（`DOCUMENT_TYPE = spec` の場合、2番目のトークン → `TARGET_ARG`（省略可））
> - `xddp.revise`: first token of `REST_ARGS` → `DOC_TYPE`
> - `xddp.excel2md`: first token of `REST_ARGS` → `EXCEL_PATH`
> - `xddp.04.specout`: remaining tokens of `REST_ARGS` → `ENTRY_POINTS`

### Step 2: Auto-detect

List all directories directly under `{WORKSPACE_ROOT}/{XDDP_DIR}/`
whose names start with `{CR_PREFIX}-` as CR candidates
(files, hidden folders, and reserved names like `latest-specs` are naturally excluded by the name filter).

- **0 found** → report `"CRフォルダが見つかりません。{WORKSPACE_ROOT}/{XDDP_DIR}/ に CR フォルダを作成するか、CR番号を引数に指定してください。"` and stop.
- **1 found** → `CR = that directory name`. Report `"CR を自動検出しました: {CR}"` and continue.
- **Multiple found** → read each directory's `progress.md`; a CR is "in progress" if any step has 🔄, 👀, or 🔁:
  - Exactly **1 in progress** → `CR = that directory name`. Report `"CR を自動検出しました: {CR}"` and continue.
  - **0 or multiple in progress** → display candidate list, report `"CR番号を引数に指定してください"` and stop.

## Resolve Affected Repos

**Input:** `REPOS_KEYS`, `IS_MULTI`, `CR_PATH`（`FILTER_BY_SPO=true` の場合のみ手続き内部で使用するが、
  呼び出し元は `FILTER_BY_SPO` の値によらず常に渡す）, `FILTER_BY_SPO`（true/false）,
  `HAS_CROSS`（`FILTER_BY_SPO=true` の場合のみ必須）,
  `CR`（CR番号。`FILTER_BY_SPO=true` の場合のみ使用 — `SPO-{CR}.md`・`CHD-{CR}-cross.md` の
  パス解決に必要。`FILTER_BY_SPO=false` の場合は不要。既存の `Discover CHD Files`・
  `Regenerate CRS Excel` プロシージャと同様、`CR` を明示 Input として受領する）
**Output:** `AFFECTED_REPOS`

**Process:**
1. `FILTER_BY_SPO = false`（既定・ほとんどのスキルで使用）の場合:
   `AFFECTED_REPOS` = `REPOS_KEYS` のコピー。
   （REPOS: に列挙された全リポジトリを対象とする。個別スキルによる絞り込みが別途必要な場合は
   呼び出し元スキルが本プロシージャの結果を上書きする — 例: `xddp.04.specout` Step 0.5 の人による確認・絞り込み。）
2. `FILTER_BY_SPO = true`（`xddp.11.specs` 専用 — 実際に specout・設計が完了したリポジトリのみを
   最新仕様書生成の対象とするため。存在しない SPO/DSN/CHD を前提にした生成を防ぐ）の場合:
   1. 基本: `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` が存在するリポジトリを対象とする。
   2. 追加条件（`IS_MULTI` and `HAS_CROSS` の場合）: `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` を
      Read し（存在する場合）、インタフェース変更サマリーで「影響リポジトリ」として列挙されている
      リポジトリを `AFFECTED_REPOS` に追加する（SPO がなくても overview/architecture.md 更新対象に
      なる可能性があるため）。CHD cross が存在しない場合はこの追加条件は適用しない。
   3. `AFFECTED_REPOS` = 上記1・2で確定したリポジトリのリスト。
3. Return `AFFECTED_REPOS`.

## Resolve HAS_CROSS

**Input:** `IS_MULTI`, `ARTIFACT_PATH`（直前工程の cross 成果物ファイルパス。工程により
  SPO-{CR}-cross.md / DSN-{CR}-cross.md / CHD-{CR}-cross.md のいずれか）
**Output:** `HAS_CROSS`

**Process:**
1. `HAS_CROSS` = (`IS_MULTI` and `ARTIFACT_PATH` が存在する)。
2. Return `HAS_CROSS`.

**注記（呼び出し元が明記すべき事項）:** `ARTIFACT_PATH` にどの工程の cross 成果物を渡すかは
呼び出し元スキルの工程位置によって決まる（自分の直前工程が生成した cross 成果物を見る、という
設計上の意図がある）。本プロシージャは存在チェックの実施のみを共通化し、
「どのファイルを見るべきか」の判断は呼び出し元の責務のまま残す。

**適用外（本プロシージャを使わないスキルとその理由）:**
- `xddp.04.specout`: cross 成果物自体がこの工程で初めて生成されるため、着手時点では
  存在チェック対象のファイルがまだない。`HAS_CROSS` は初期値 `IS_MULTI` とし、
  Discovery でリポジトリ間依存が見つからなければ `false` に降格する、成果物存在チェックとは
  異なる判定方式を用いる。
- `xddp.close`: 特定1ファイルの存在ではなく、CR 内の cross/ 配下に何らかの成果物が
  存在するか（工程4a〜8のどこかで cross 処理が行われたか）を広く問う棚卸し用途のため、
  「直前工程の特定ファイル」を前提とする本プロシージャの対象外とする。

## Cross Artifact Review

cross/ 配下の成果物（SPO/DSN/CHD の cross バージョン）に対する AI レビュー→インライン修正共通フロー。
`HAS_CROSS` が true の場合のみ、各スキルの Step A2-cross / Step B-cross から apply して使用する。
cross/ 成果物にはインタフェース仕様等に特化した性質上、専用の fixer agent が存在しないため、
指摘があれば呼び出し元スキルが直接 `TARGET_FILE` を編集する。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `STEP_NUM`: progress.md 上の対象ステップ番号（例: `4a`, `5`, `6a`）
- `STEP_LABEL`: progress.md の詳細ステップに使う呼び出し元固有のステップ識別子（例: `Step A2-cross`, `Step B-cross`）
- `DOCUMENT_TYPE`: レビュアーに渡す文書種別（SPO / DSN / CHD）
- `NEXT_DOCUMENT_TYPE`: 次工程の文書種別（DSN / CHD / TSP）
- `TARGET_FILE`: cross 成果物のパス
- `REFERENCE_FILES`: レビュー時に参照するファイル一覧
- `OUTPUT_FILE`: レビュー結果の出力先パス
- `DOC_DESCRIPTION`: 末尾注記に挿入する、この cross 成果物の性質を表す一文（例:
  `インタフェース仕様に特化した成果物`／`インタフェース仕様・実装依存順序に特化した成果物`／
  `インタフェース変更のサマリに特化した成果物`）

**Process:**
1. Update `{CR_PATH}/progress.md` のステップ番号 = `{STEP_NUM}` の行の詳細ステップ →
   `{STEP_LABEL}: cross {DOCUMENT_TYPE}レビュー中`.
2. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: {DOCUMENT_TYPE}
   NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE}
   TARGET_FILE: {TARGET_FILE}
   REFERENCE_FILES: {REFERENCE_FILES}
   REVIEW_ROUND: 1
   OUTPUT_FILE: {OUTPUT_FILE}
   ```
3. Read `{OUTPUT_FILE}`. If 🔴/🟡 issues found: directly edit `{TARGET_FILE}` to fix the issues
   （cross/ {DOCUMENT_TYPE} has no dedicated fixer agent — fix inline）. Output updated review summary.
4. After fixing, re-read `{OUTPUT_FILE}` and count remaining 🔴 rows.
   If 🔴 items remain: warn the human:
   > ⚠️ cross/ {DOCUMENT_TYPE} レビューで 🔴 指摘 {N} 件が残存しています。手動確認してください: `{OUTPUT_FILE}`
5. 注: cross/ {DOCUMENT_TYPE} は{DOC_DESCRIPTION}でサイズが小さく、1パスで修正が収束しやすい。
   per-repo の max_rounds ループは省略する（設計上の意図的省略）。

## Review Loop

AIレビュー → Fixer の反復ループ共通制御フロー。各スキルの Step B から apply して使用する。

**Input:**
- `DOCUMENT_TYPE`: レビュアーに渡す文書種別（ANA / CRS / DSN / CHD / TSP）
- `CONFIG_KEY`: xddp.config.md から読む REVIEW_MAX_ROUNDS のキー名（例: `REVIEW_MAX_ROUNDS.ANA`）。デフォルト値は 2。
- `TARGET_FILE`: レビュー対象ファイルのパス
- `REFERENCE_FILES`: レビュー時に参照するファイル一覧
- `REVIEW_OUTPUT_FILE`: レビュー結果の出力先パス
- `FIXER_AGENT`: 修正担当エージェントの subagent_type 名
- `FIXER_PARAMS`: 修正エージェントへの入力パラメータ（key-value 形式）
- `NEXT_DOCUMENT_TYPE`（任意）: 次工程の文書種別（例: ANA→CRS, CRS→SPO, SPO→DSN, DSN→CHD, CHD→TSP）。指定時に xddp-reviewer へ渡し、次工程受け取り可否レビューを実施させる。ダウンストリーム ❌ 項目は xddp-reviewer が `## 2.` に 🔴 として転記するため、ループ判定ロジックの変更は不要。
- `PROGRESS_CR_PATH`（任意）: progress.md のある CR フォルダパス
- `PROGRESS_STEP_NUM`（任意）: 警告フラグを記録するステップ番号
- `EXTRA_REVIEWER_PARAMS`（任意, key-value 形式, default: 空）: `xddp-reviewer` への Agent tool 呼び出し
  （Process 4a）に追加でそのまま渡すパラメータ。`DOCUMENT_TYPE` 固有の
  判定基準値を `xddp-reviewer` に伝える汎用の受け渡し口（例: `TSP` レビュー時の `MIN_COVERAGE`）。
  呼び出し元が指定しない場合は Process 4a の呼び出しに何も追加しない（既存の呼び出しと完全に同一）。

**Process:**
1. Read `{WORKSPACE_ROOT}/xddp.config.md`.
   - Extract `{CONFIG_KEY}` (default: 2 if absent). Set `max_rounds`.
   - Extract `FIX_STRATEGY.{DOCUMENT_TYPE}` (default: `balanced` if absent). Set `fix_strategy`.
     修正方針: `efficiency`（最小インパクト優先）/ `ideal`（理想状態優先）/ `balanced`（コストと理想の
     バランス）。`FIXER_PARAMS` に含めてフィクサーエージェントへ伝達する（Process 手順d参照）。
     AI フィクサーエージェントでは `balanced` は `ideal` と同等に動作する（人への確認は
     xddp.plan-review のインライン修正のみサポート）。
2. If `max_rounds = 0`: レビューをスキップして終了する（`REVIEW_MAX_ROUNDS.*: 0` 設定時）。
3. Initialize: `round = 1`, `issues_remain = true`
4. While `issues_remain` and `round ≤ max_rounds`:
   a. **Agent tool** `subagent_type=xddp-reviewer`:
      ```
      DOCUMENT_TYPE: {DOCUMENT_TYPE}
      TARGET_FILE: {TARGET_FILE}
      REFERENCE_FILES: {REFERENCE_FILES}
      REVIEW_ROUND: {round}
      OUTPUT_FILE: {REVIEW_OUTPUT_FILE}
      （NEXT_DOCUMENT_TYPE が指定されている場合のみ追加）NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE}
      （EXTRA_REVIEWER_PARAMS が指定されている場合のみ追加）{EXTRA_REVIEWER_PARAMS を展開}
      ```
   b. Read `{REVIEW_OUTPUT_FILE}`.
      - No 🔴/🟡 → `issues_remain = false`. Exit loop.
      - 🔴/🟡 found and `round < max_rounds`:
        c. **横展開調査:** 各指摘の根本原因パターンを特定する。対象ファイルの他セクションおよび REFERENCE_FILES に列挙された関連ファイルに同一パターンが存在しないかをスキャンし、追加修正箇所を `ADDITIONAL_FIXES` に記録する。
        d. `FIXER_PARAMS` に `FIX_STRATEGY` = `{fix_strategy}` と `ADDITIONAL_FIXES` を追加する。
        e. **Agent tool** `subagent_type={FIXER_AGENT}` with updated `{FIXER_PARAMS}`. Increment `round`. Continue loop.
      - `round = max_rounds` and issues remain:
        1. Append `"⚠️ 未解決の重大指摘あり。人間の判断が必要です。"` to `{REVIEW_OUTPUT_FILE}`.
        2. If PROGRESS_CR_PATH and PROGRESS_STEP_NUM are provided:
           Read `{PROGRESS_CR_PATH}/progress.md`. In the `## 備考・メモ` section,
           append the following line:
           `⚠️ 工程{PROGRESS_STEP_NUM}: 未解決指摘あり（{REVIEW_OUTPUT_FILE}）`
           If `## 備考・メモ` does not exist, create it at the end of the file before appending.
           Write back.
        Exit loop.

## Human Review Gate

人レビュー待ちのゲート表示・入力待ち共通制御フロー。各スキルの Human Review Gate ステップから
apply して使用する。「レビュー完了」入力後の最終AIレビューパスは対象ファイル構成が工程ごとに異なるため
本プロシージャの範囲外とし、呼び出し元スキルが `CHANGED` を見て個別に実施する。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `STEP_NUM`: progress.md 上の対象ステップ番号
- `STEP_LABEL`: progress.md の詳細ステップ・`xddp.status` 表示に使う呼び出し元固有のステップ識別子
  （例: `Step A3`、`Step B2`。呼び出し元のステップ見出し名と一致させる）
- `ARTIFACTS_TEXT`: 成果物一覧（Markdown 箇条書き。**呼び出し元が `{for each...}`/`{if...}` を展開済みの
  最終テキストとして渡す**。単一ファイル／リポジトリ別＋cross 等、工程ごとに構造が異なるため、組み立て自体は
  呼び出し元の責務とする。本プロシージャは `AFFECTED_REPOS`・`HAS_CROSS` 等の呼び出し元ローカル変数を
  認識しないため、未展開のテンプレート構文を渡してはならない）
- `REVISE_COMMAND`（任意）: AI修正コマンドの案内文字列（例: `` `/xddp.revise {CR} analysis` ``）。
  省略時は「AIに修正を依頼する場合」の行を出力しない
- `INTRO_NOTE`（任意）: 標準の案内文の直後、`ARTIFACTS_TEXT` の前に挿入する追加テキスト
  （例: 05.arch の SP-ID 照合警告。`ARTIFACTS_TEXT` と同様に展開済みの最終テキストとして渡す）
- `OPTION_NOTE`（任意）: 修正方法ブロックの後、締めの入力案内の前に挿入する追加テキスト
  （例: 05.arch の `--detail` オプション案内）

**Output:** `CHANGED`（true/false。ユーザーがファイルを直接編集または `/xddp.revise` を実行したかどうか）

**Process:**
1. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
   CR_PATH: {CR_PATH}, STEP_NUM: {STEP_NUM}, STATE: 👀 レビュー待ち,
   DETAIL_STEP: `{STEP_LABEL}: 人レビュー待ち`
2. Tell the user。以下のテキストを組み立て、**展開後の全行**（`ARTIFACTS_TEXT`・`INTRO_NOTE`・`OPTION_NOTE`
   が複数行の場合はその内部の各行も含む）の先頭に `>` を付与して出力する（変更前の6スキルすべてが
   blockquote 形式で出力していたため、表示形式を維持する）:
   ```
   ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
   {INTRO_NOTE が指定されている場合は挿入}
   {ARTIFACTS_TEXT}

   **修正方法：**
   - 直接ファイルを編集する
   {REVISE_COMMAND が指定されている場合}- AIに修正を依頼する場合: {REVISE_COMMAND}
   {OPTION_NOTE が指定されている場合は挿入}

   レビューと修正が完了したら「**レビュー完了**」と入力してください。
   変更がなければそのまま「**レビュー完了**」と入力してください。
   ```
3. Wait for the user to confirm.
4. `CHANGED` の判定: ユーザーの直後の発言内容を確認する。
   - ファイル編集や `/xddp.revise` 実行に言及している、またはレビュー指摘に対する具体的な修正内容に言及している
     → `true`
   - 「変更なし」の旨の発言、または単に「レビュー完了」とだけ入力した（修正への言及がない）
     → `false`
   いずれであるか判断に迷う場合は、ユーザーに「ファイルを変更しましたか？」と確認してから判定する。
5. Return `CHANGED`.

**理由（設計判断の記録）:**
`DETAIL_STEP` を `STEP_LABEL` 経由の動的組み立てにしたのは、`xddp.status/SKILL.md` の表示例
「`| 5 | 実装方式検討 | 👀 レビュー待ち | Step B2: 人レビュー待ち | ... |`」が、工程ごとに異なる
ステップ識別子（`Step A3`／`Step B2` 等）を前提とした既存の公開済み挙動であるため。
`ARTIFACTS_TEXT`/`INTRO_NOTE` を「呼び出し元が展開済みの最終テキストを渡す」契約にしたのは、既存の
`apply` 呼び出し規約（呼び出し元が条件分岐・存在判定を済ませた確定値を渡す運用）からの逸脱を
避けるためである（詳細は上記 Input 節の該当項目を参照）。

## Final Review Pass

Human Review Gate 通過後、`CHANGED = true` の場合に実施する最終 AI レビュー1回分の共通フロー。
各スキルの Step B2（または Step A3）直後の `If CHANGED:` 分岐から apply して使用する。
Fixer は呼ばない（レビューのみ。指摘が残る場合は人に判断を委ねる）。

**Input:**
- `DOCUMENT_TYPE`: レビュアーに渡す文書種別
- `NEXT_DOCUMENT_TYPE`（任意）: 次工程の文書種別
- `TARGET_FILE`: レビュー対象ファイルのパス
- `REFERENCE_FILES`: レビュー時に参照するファイル一覧
- `REVIEW_ROUND`: レビューラウンド番号（`last_round + 1` を呼び出し元が算出して渡す）
- `OUTPUT_FILE`: レビュー結果の出力先パス
- `EXTRA_REVIEWER_PARAMS`（任意, key-value 形式, default: 空）: `xddp-reviewer` への Agent tool 呼び出し
  （Process 手順1）に追加でそのまま渡すパラメータ。`DOCUMENT_TYPE` 固有の
  判定基準値を `xddp-reviewer` に伝える汎用の受け渡し口（例: `TSP` レビュー時の `MIN_COVERAGE`）。
  呼び出し元が指定しない場合は Process 手順1の呼び出しに何も追加しない（既存の呼び出しと完全に同一）。

**Process:**
1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: {DOCUMENT_TYPE}
   TARGET_FILE: {TARGET_FILE}
   REFERENCE_FILES: {REFERENCE_FILES}
   REVIEW_ROUND: {REVIEW_ROUND}
   OUTPUT_FILE: {OUTPUT_FILE}
   （NEXT_DOCUMENT_TYPE が指定されている場合のみ追加）NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE}
   （EXTRA_REVIEWER_PARAMS が指定されている場合のみ追加）{EXTRA_REVIEWER_PARAMS を展開}
   ```
2. Read `{OUTPUT_FILE}`. If 🔴 issues remain: inform the user and ask whether to fix again or proceed.

## Progress Update

progress.md の指定ステップの状態・詳細ステップ・日付を更新する共通手順。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `STEP_NUM`: 更新するステップ番号
- `STATE`: 新しい状態（🔄 進行中 / ✅ 完了 / 👀 レビュー待ち / 🔁 修正中 / ⏸ 保留）
- `DETAIL_STEP`: 詳細ステップ文字列（完了時は `"-"` とする）
- `ARTIFACT_LINK`（任意）: 完了時の成果物へのリンク文字列

**Process:**
1. Read `{CR_PATH}/progress.md`.
2. Find the row where ステップ番号 = `{STEP_NUM}`.
3. Update 状態 → `{STATE}`, 詳細ステップ → `{DETAIL_STEP}`, 更新日 → today's date.
4. If `ARTIFACT_LINK` is provided and `STATE` = ✅ 完了, update 成果物リンク column.
5. If `STATE` = ✅ 完了: in the `## 備考・メモ` section, remove all lines that start with
   `⚠️ 工程{STEP_NUM}:` (matches one or more lines; no-op if none found).
6. Write back to `{CR_PATH}/progress.md`.

## Regenerate CRS Excel (UR-016)

CRS Markdown から確認用 Excel を再生成する共通手順。各スキルの「Excel再生成」ステップから apply して使用する。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `CR`: CR番号

**Process:**
1. Let `CRS_PATH` = `{CR_PATH}/03_change-requirements/CRS-{CR}.md`.
2. Let `EXCEL_PATH` = `{CR_PATH}/03_change-requirements/CRS-{CR}.xlsx`.
3. Run via Bash: `python ~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py {CRS_PATH} {EXCEL_PATH}`
4. If `crs_md2excel.py` not found: tell the user to run `setup.sh`. If errors: display to user.
5. Report output path and UR/SR/SP counts from script stdout.

> **Design policy:** The sole definition of the Excel format is in `~/.claude/skills/xddp.md2excel/SKILL.md` and `~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py`.
> This skill does not define its own format; it always delegates to xddp.md2excel to prevent format divergence by generation path.
> To change the format, modify only xddp.md2excel/SKILL.md and crs_md2excel.py.
> **成果物の位置付け:** `CRS-{CR}.xlsx` は人間向け確認ツール（一時生成物）。xddp.close の DOCS_DIR 昇格対象外。

## Load Lessons Context

lessons-learned.md のタグ別インデックスを使い、対象タグに該当するエントリのみを選択的に読み取る共通手順
（全文読み取りによるコンテキスト消費を避ける。E-01 対応）。各スキルの「知見ログ参照」ステップから apply して使用する。

**Input:**
- `LESSONS_FILE`: lessons-learned.md のパス
- `TARGET_TAGS`: 対象タグのリスト（例: `[#要求分析, #仕様定義, #見落とし]`）

**Output:** `LESSONS_CONTEXT`（該当エントリの本文を連結した文字列。該当エントリがない場合は空文字列）

**Process:**
1. If `{LESSONS_FILE}` が存在しない: `LESSONS_CONTEXT` = 空文字列を返して終了する。
2. Read `{LESSONS_FILE}`。
3. `## タグ別インデックス` セクションを確認する。
   - セクションが存在しない、またはテーブル内の対象タグ行がすべて `—`（未 populate）の場合:
     **フォールバック** — `## 知見詳細` 全体を対象に `TARGET_TAGS` のいずれかをタグに含むエントリを
     抽出する（既存の互換動作。インデックス未整備の既存ファイルでも動作することを保証する）。
   - セクションが存在し、対象タグ行の少なくとも1行にエントリ番号が記載されている場合（`TARGET_TAGS` の一部のみ
     populate 済みの場合を含む）:
     `TARGET_TAGS` に対応する行のエントリ番号（カンマ区切り、例 `LL-003, LL-005`）を集約し重複を除いた
     `TARGET_IDS` を求める。未 populate（`—`）の行は0件として扱う（フォールバックには遷移しない。
     populate 済みの行から得られる結果のみで集約すれば安全に動作するため）。`## 知見詳細` セクションから
     `### {id}：` に一致するエントリのみを抽出する（他のエントリは `LESSONS_CONTEXT` に含めない）。
4. 抽出したエントリ本文（タイトル〜次のエントリ直前まで）を連結し `LESSONS_CONTEXT` とする。
5. Return `LESSONS_CONTEXT`.

## Discover CHD Files

CHD（変更設計書）がインデックス + UR別内容ファイルに分割されている前提で、
内容ファイル一覧を解決する共通手順。CHDを参照する全スキル・エージェント呼び出し元はこれを使うこと。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `REPO_NAME`: リポジトリ名（`"cross"` の場合は分割対象外のため単一ファイルを返す）
- `CR`: CR番号

**Output:**
- `CHD_INDEX_FILE`: インデックスファイルのパス
- `CHD_CONTENT_FILES`: 内容ファイルのパスのリスト（生成順）

**Process:**
1. `REPO_NAME` が `"cross"` の場合:
   `CHD_INDEX_FILE` = `CHD_CONTENT_FILES[0]` = `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md`。Return.
2. `CHD_INDEX_FILE` = `{CR_PATH}/06_design/{REPO_NAME}/CHD-{CR}.md`。
3. `CHD_INDEX_FILE` が存在しない場合: `CHD_CONTENT_FILES` = 空リストを返す（CHD未生成）。
4. `CHD_INDEX_FILE` を Read し、「## 2. UR別ファイル一覧」テーブルのファイルパス列から
   全リンクを抽出して `CHD_CONTENT_FILES` とする。
5. Return `CHD_INDEX_FILE`, `CHD_CONTENT_FILES`.

## Load Steering Context

プロジェクト規約ファイル（project-rulebook.md 系）を読み込んで RULEBOOK_CONTEXT を構築する共通手順。

**Input:**
- `XDDP_DIR`: XDDPディレクトリのパス
- `REPO_NAME`（任意）: リポジトリ名。指定時は project-rulebook-{REPO_NAME}.md も読み込む
- `INCLUDE_CROSS`（任意, default: false）: true の場合 project-rulebook-cross.md も読み込む

**Process:**
1. Read `{XDDP_DIR}/project-rulebook.md` (if exists). Set as base RULEBOOK_CONTEXT.
2. If `REPO_NAME` is provided: Read `{XDDP_DIR}/project-rulebook-{REPO_NAME}.md` (if exists). Append to RULEBOOK_CONTEXT.
3. If `INCLUDE_CROSS` = true: Read `{XDDP_DIR}/project-rulebook-cross.md` (if exists). Append to RULEBOOK_CONTEXT.
4. If none of the files exist: RULEBOOK_CONTEXT = empty (proceed without constraints).
5. Return `RULEBOOK_CONTEXT`.

## Detect Test Framework

リポジトリのテストフレームワークを自動検出して返す共通手順。

**Input:**
- `REPO_PATH`: リポジトリのルートパス
- `LANGUAGE`（任意）: 言語ヒント（`python`, `java`, `javascript`, `go`, `ruby` 等）。指定時は対応フレームワークのみを検出対象とする。

**Process:**
0. If `LANGUAGE` is provided: Limit detection to frameworks matching `{LANGUAGE}` (e.g., `python` → pytest のみチェック).
1. Check for framework configuration files in `{REPO_PATH}`:
   - `pytest.ini`, `setup.cfg [tool:pytest]`, `pyproject.toml [tool.pytest]` → Python/pytest
   - `pom.xml` with junit dependency → Java/JUnit
   - `package.json` with jest/vitest dependency → JavaScript/Jest or Vitest
   - `go.mod` → Go/testing
   - `Gemfile` with rspec → Ruby/RSpec
2. If exactly one framework is detected → return `(FRAMEWORK_NAME, VERSION, CONFIG_FILE)`.
3. If multiple or none detected:
   - Multiple: return all candidates, note ambiguity.
   - None: return `(unknown, -, -)` and recommend manual specification.
