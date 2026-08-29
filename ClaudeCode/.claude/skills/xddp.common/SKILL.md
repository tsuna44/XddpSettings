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

**Output:** `WORKSPACE_ROOT`, `XDDP_DIR`（default: `xddp`）,
  `DOCS_DIR`（default: `baseline_docs`）, `DOCS`（= `{WORKSPACE_ROOT}/{DOCS_DIR}`）,
  `REPOS_MAP`（リポジトリ名→パスの辞書）, `REPOS_KEYS`（リポジトリ名一覧。`REPOS:` が未設定・空の場合は空リスト）,
  `IS_MULTI`（= len(REPOS_KEYS) ≥ 2）, `DEVELOPMENT_MODE`（default: `change`）,
  `CR_PROFILE`（default: `full`）,
  `MIN_COVERAGE`（default: `80`）, `TEST_COVERAGE_TARGET`（default: `C1`）,
  `EXCLUDE_PATTERNS`（default: `tests/,test/,__tests__/,spec/,specs/,__mocks__/,fixtures/,vendor/,node_modules/`）,
  `INCLUDE_EXTENSIONS`（default: 空）, `MAX_WAVE_DEPTH`（default: `10`）,
  `SPECOUT_MAX_AFFECTED_FILES`（default: `20`）, `SPECOUT_MAX_FILES_PER_MODULE`（default: `10`）,
  `SPECOUT_DIAGRAM_LEVEL`（default: `standard`）, `SPECOUT_SEQUENCE_LEVELS`（default: `module, class`）,
  `SPECOUT_BACKEND`（default: `auto`）, `SPECOUT_BACKEND_OVERRIDES`（repo→backend の辞書。default: `{}`）,
  `SPECOUT_CLASSIFY_CHUNK_SIZE`（default: `40`）, `SPECOUT_CLASSIFY_PARALLEL`（default: `4`）,
  `SPECOUT_HIT_FILTER`（default: `conservative`）,
  `DESIGN_MAX_SP_PER_FILE`（default: `10`）, `DESIGN_MAX_SYMBOLS_PER_FILE`（default: `30`）,
  `TEST_FRAMEWORK`（default: `auto`）, `TEST_FRAMEWORK_REPOS`（repo→フレームワークの辞書。default: `{}`）,
  `MD2EXCEL_PYTHON_BIN`（default: 空文字列）,
  `VCS_TYPE`（default: `auto`）, `VCS_BRANCH_PREFIX`（default: `feature/`）,
  `VCS_AUTO_BRANCH`（default: `true`）, `VCS_COMMIT_ON_STEP`（default: `7,10`）,
  `VCS_BASE_BRANCH`（default: `auto`）

**Process:**
1. Search for `xddp.config.md` upward from cwd to determine `WORKSPACE_ROOT`.
   If not found: report `{NOT_FOUND_MESSAGE}` and stop.
2. **`{WORKSPACE_ROOT}/xddp.config.md` を1回 Read し、以下の全標準キーをまとめて取得する**
   （個別スキルが同じファイルを再度 Read することを避けるため）:
   - `XDDP_DIR`（default: `xddp`）, `DOCS_DIR`（default: `baseline_docs`）
   - `REPOS:` マッピング → `REPOS_MAP`（repo名→パス）, `REPOS_KEYS`（repo名一覧。`REPOS:` が未設定・空の場合は空リスト）
   - `DEVELOPMENT_MODE`（default: `change`）, `CR_PROFILE`（default: `full`。ここでは
     `xddp.config.md` のワークスペース既定値のみを解決する。CR 単位の上書きは
     `## CR Resolution`「### Step 1.X」が progress.md から再解決する）,
     `MIN_COVERAGE`（default: `80`）, `TEST_COVERAGE_TARGET`（default: `C1`）
   - `EXCLUDE_PATTERNS` = 設定キー `SPECOUT_EXCLUDE_PATTERNS`（default: 前述）,
     `INCLUDE_EXTENSIONS` = 設定キー `SPECOUT_INCLUDE_EXTENSIONS`（default: 空）,
     `MAX_WAVE_DEPTH` = 設定キー `SPECOUT_MAX_WAVE_DEPTH`（default: `10`）
     （注: 出力変数名は `xddp.04.specout/SKILL.md` が本文中で既に使用している短縮エイリアス名に合わせている。
     `xddp.config.md` 上のキー名は `SPECOUT_*` だが、出力変数名は本文側の既存名を優先する）
   - `SPECOUT_MAX_AFFECTED_FILES`（default: `20`）, `SPECOUT_MAX_FILES_PER_MODULE`（default: `10`）,
     `SPECOUT_DIAGRAM_LEVEL`（default: `standard`）, `SPECOUT_SEQUENCE_LEVELS`（default: `module, class`）
   - `SPECOUT_BACKEND`（default: `auto`）= 設定キー `SPECOUT_BACKEND`（Discovery BFS の参照解決バックエンド。
     `auto`/`grep`/`rg`/静的種別）。加えて `SPECOUT_BACKEND.{repo}` 形式のサフィックスキー行を全て集約し、
     `SPECOUT_BACKEND_OVERRIDES`（repo名→backend の辞書。該当行が無ければ `{}`）を構築する。
     `xddp.04.specout` が repo ごとに `SPECOUT_BACKEND_OVERRIDES.get(repo, SPECOUT_BACKEND)` で有効値を解決し、
     discovery-setup エージェント呼び出しの Task Input として渡す（既定 `auto` で従来と同一挙動）
   - `SPECOUT_CLASSIFY_CHUNK_SIZE`（default: `40`）, `SPECOUT_CLASSIFY_PARALLEL`（default: `4`）
     （PLAN-20260806 Phase 3 Stage 2: `xddp.04.specout` の波内 classification チャンク分割・並列度。
     `xddp.04.specout/SKILL.md` の波ループが `specout_bfs.py search --chunk-size` と
     classifier サブエージェントの同時起動数上限へそのまま渡す。`SPECOUT_BACKEND` と異なり repo 単位の
     上書きキーは持たない）
   - `SPECOUT_HIT_FILTER`（default: `conservative`）= 設定キー `SPECOUT_HIT_FILTER`（Discovery BFS の
     保守的ヒット事前フィルタ。`conservative`/`off`）
   - `DESIGN_MAX_SP_PER_FILE`（default: `10`）, `DESIGN_MAX_SYMBOLS_PER_FILE`（default: `30`）
     （`xddp.06.design` が CHD ファイル分割判定に使用）
   - `TEST_FRAMEWORK`（default: `auto`）, `TEST_FRAMEWORK_REPOS`（repo→フレームワークの辞書。default: `{}`）
     （`xddp.09.test` がテストフレームワーク解決に使用）
   - `MD2EXCEL_PYTHON_BIN`（default: 空文字列）（`crs_md2excel.py` 呼び出し専用。
     「## Regenerate CRS Excel」・`xddp.md2excel/SKILL.md` のみが参照する）
   - `VCS_TYPE`（default: `auto`）, `VCS_BRANCH_PREFIX`（default: `feature/`）,
     `VCS_AUTO_BRANCH`（default: `true`）, `VCS_COMMIT_ON_STEP`（default: `7,10`）,
     `VCS_BASE_BRANCH`（default: `auto`。新規ブランチ作成時の起点 ref。`auto` の場合は
     `xddp_vcs.py branch --base-ref auto` 実行時にリモート既定ブランチ／`main`／`master`の順で
     解決される。詳細は `docs/adr/ADR-0011-vcs-abstraction.md` 参照）
     読み込んだ `VCS_TYPE` が `auto`/`git`/`none` のいずれでもない場合（設定ミス等）:
     Warn: "⚠️ VCS_TYPE の値 `{生の設定値}` は認識できません（有効値: auto/git/none）。none として扱います。"
     し、`VCS_TYPE` = `none` に正規化する（`CR_PROFILE` が `full`/`quick` 以外の値のときに `full` へ
     フォールバックする既存パターン——`## CR Resolution`「### Step 1.X」——と同一方針。ここで一元的に
     正規化することで、`## Load Config` を経由する全スキル（`xddp.07.code`/`xddp.08.verify`/
     `xddp.10.test-run`/`xddp.close`）の `{VCS_TYPE}` は常に `auto`/`git`/`none` のいずれかであることが
     保証され、各呼び出し箇所で個別に不正値ハンドリングを複製する必要がなくなる）
3. Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`（パス文字列の構築のみ。存在チェックは呼び出し元が必要に応じて行う）。
4. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2)。
5. `REPOS:` が未設定または空の場合のエラー処理（停止するか・初回設定を促すか等）は呼び出し元スキルの裁量に
   委ねる（スキルによって `REPOS:` の必須/任意の扱いが異なるため。本プロシージャ自身はここでは停止しない）。
6. Return all Output values.

## CR Resolution

**Input:**
- `RAW_ARGS` = trimmed string of $ARGUMENTS
- `SKIP_ABORT_GUARD`（任意, default: `false`）: `true` の場合、下記の「中止済み CR ガード」を
  スキップする。`/xddp.abort` 専用。他スキルはこの引数を渡さない。

**Output:** `CR`（解決済みCR番号）, `REST_ARGS`（CR以降の残り引数）、および上記 `## Load Config` が
返す標準設定バンドル全て（`WORKSPACE_ROOT`/`XDDP_DIR`/
`DOCS_DIR`/`DOCS`/`REPOS_MAP`/`REPOS_KEYS`/`IS_MULTI`/`DEVELOPMENT_MODE`/`CR_PROFILE`/`MIN_COVERAGE`/
`TEST_COVERAGE_TARGET`/`EXCLUDE_PATTERNS`/`INCLUDE_EXTENSIONS`/`MAX_WAVE_DEPTH`/
`SPECOUT_MAX_AFFECTED_FILES`/`SPECOUT_MAX_FILES_PER_MODULE`/`SPECOUT_DIAGRAM_LEVEL`/
`SPECOUT_SEQUENCE_LEVELS`/`SPECOUT_BACKEND`/`SPECOUT_BACKEND_OVERRIDES`/
`SPECOUT_CLASSIFY_CHUNK_SIZE`/`SPECOUT_CLASSIFY_PARALLEL`/`SPECOUT_HIT_FILTER`/
`DESIGN_MAX_SP_PER_FILE`/`DESIGN_MAX_SYMBOLS_PER_FILE`/`TEST_FRAMEWORK`/
`TEST_FRAMEWORK_REPOS`/`MD2EXCEL_PYTHON_BIN`/
`VCS_TYPE`/`VCS_BRANCH_PREFIX`/`VCS_AUTO_BRANCH`/`VCS_COMMIT_ON_STEP`/`VCS_BASE_BRANCH`）
On failure, report error and stop.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Config"
→ let `WORKSPACE_ROOT`, `XDDP_DIR`, `DOCS_DIR`, `DOCS`, `REPOS_MAP`, `REPOS_KEYS`,
`IS_MULTI`, `DEVELOPMENT_MODE`, `CR_PROFILE`, `MIN_COVERAGE`, `TEST_COVERAGE_TARGET`, `EXCLUDE_PATTERNS`,
`INCLUDE_EXTENSIONS`, `MAX_WAVE_DEPTH`, `SPECOUT_MAX_AFFECTED_FILES`, `SPECOUT_MAX_FILES_PER_MODULE`,
`SPECOUT_DIAGRAM_LEVEL`, `SPECOUT_SEQUENCE_LEVELS`, `SPECOUT_BACKEND`, `SPECOUT_BACKEND_OVERRIDES`,
`SPECOUT_CLASSIFY_CHUNK_SIZE`, `SPECOUT_CLASSIFY_PARALLEL`, `SPECOUT_HIT_FILTER`,
`DESIGN_MAX_SP_PER_FILE`, `DESIGN_MAX_SYMBOLS_PER_FILE`, `TEST_FRAMEWORK`, `TEST_FRAMEWORK_REPOS`,
`MD2EXCEL_PYTHON_BIN`, `VCS_TYPE`, `VCS_BRANCH_PREFIX`, `VCS_AUTO_BRANCH`, `VCS_COMMIT_ON_STEP`,
`VCS_BASE_BRANCH`.

### Step 1: Identify CR from arguments

Let `FIRST_ARG` = first token of `RAW_ARGS`.

List all directories directly under `{WORKSPACE_ROOT}/{XDDP_DIR}/`, excluding hidden directories
(dotfiles) and the reserved name `latest-specs` (同じ除外規則を Step 2 とも共有する)。

- `FIRST_ARG` is non-empty AND exactly matches (完全一致。前方一致・部分一致ではない) the name of one
  of the listed directories
  → `CR = FIRST_ARG`, `REST_ARGS` = remaining tokens. Go to Step 1.X.
- otherwise (FIRST_ARG is empty, or no listed directory name equals `FIRST_ARG`)
  → `REST_ARGS = RAW_ARGS` (treat all tokens as secondary args). Go to Step 2.

> **命名上の注意:** CRフォルダ名は `{XDDP_DIR}/` 直下の実在ディレクトリとして解決されるため、
> `xddp.review`・`xddp.revise` 等が第2引数として使う予約語（`analysis`/`req`/`specout`/`arch`/
> `design`/`test`/`spec`/`full`/`quick`）、`xddp.04.specout` の `ENTRY_POINTS`（調査対象の関数・
> クラス名等の自由記述シンボル）、および予約ディレクトリ名（`latest-specs`）と同名のCRを作成しないこと。
> 同名の場合、Step 1 がその引数を誤ってCR番号と解釈する可能性がある。

> **Skills that use secondary args:**
> - `xddp.review`: first token of `REST_ARGS` → `DOCUMENT_TYPE`（`DOCUMENT_TYPE = spec` の場合、2番目のトークン → `TARGET_ARG`（省略可））
> - `xddp.revise`: first token of `REST_ARGS` → `DOC_TYPE`
> - `xddp.excel2md`: first token of `REST_ARGS` → `EXCEL_PATH`
> - `xddp.04.specout`: remaining tokens of `REST_ARGS` → `ENTRY_POINTS`

### Step 2: Auto-detect

List all directories directly under `{WORKSPACE_ROOT}/{XDDP_DIR}/` as CR candidates,
excluding hidden directories (dotfiles) and the reserved name `latest-specs`.

- **0 found** → report `"CRフォルダが見つかりません。{WORKSPACE_ROOT}/{XDDP_DIR}/ に CR フォルダを作成するか、CR番号を引数に指定してください。"` and stop.
- **1 found** → `CR = that directory name`. Report `"CR を自動検出しました: {CR}"` and continue.
- **Multiple found** → read each directory's `progress.md`; a CR is "in progress" if any step has 🔄, 👀, or 🔁:
  - Exactly **1 in progress** → `CR = that directory name`. Report `"CR を自動検出しました: {CR}"` and continue.
  - **0 or multiple in progress** → display candidate list, report `"CR番号を引数に指定してください"` and stop.

### Step 1.X: Resolve CR Profile（追加。`CR` 確定後・`## Resolve Affected Repos` の前に実行）

Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`（この手続き内部限定のローカル変数。呼び出し元
スキルは `## CR Resolution` から戻った後、別途同じ式で `CR_PATH` を構築して使う — 両者は独立した
構築だが同じ式のため値は一致する）。

1. `CR_PROFILE` の初期値は上記 apply "## Load Config" で既に解決済みの値（`xddp.config.md` の
   `CR_PROFILE`、未設定なら `full`）とする。
2. `{CR_PATH}/progress.md` が存在する場合: Read し、`**CRプロファイル：**` 行があればその値で
   `CR_PROFILE` を上書きする（progress.md が存在しない、または該当行がない場合は上書きせず、
   手順1の初期値のまま次のステップに進む。`## CR Resolution` は `xddp.01.init` からは呼ばれず
   `xddp.01.init` の Step 5 で progress.md 生成後に初めて他スキルから呼ばれる想定のため、通常の
   フローではこの分岐に到達しない。到達するのは CR フォルダが手動作成された等の異常系のみ）。
3. 上書き後の値が `full` / `quick` 以外の場合は `full` にフォールバックし、警告を出力する。

### Step 1.Y: Abort Guard（追加。`CR` 確定後・戻り値返却前）

If `SKIP_ABORT_GUARD` is `true`: このガード全体をスキップする。
Else: CR 確定後、`{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/progress.md` が存在する場合、
`## CR 中止` セクションの有無を確認する。存在する場合:
> ⚠️ CR `{CR}` は {中止日} に中止済みです（理由: {中止理由}）。
> このまま処理を続行しますか？ [続行 / 中止]
Wait for user confirmation. If 中止 が選択された場合、呼び出し元スキルの処理を停止する。

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
- `EXTRA_REVIEWER_PARAMS`（任意, key-value 形式, default: 空）: `xddp-reviewer` への Agent tool 呼び出し
  （Process 手順2）に追加でそのまま渡すパラメータ。`## Review Loop`・`## Invoke Reviewer` と同一契約
  （例: cross SPO/CHD/TSP レビュー時の `QUICK_PROFILE`）。呼び出し元が指定しない場合は Process 手順2の
  呼び出しに何も追加しない（既存の呼び出しと完全に同一）。

**Process:**
1. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
   CR_PATH: {CR_PATH}, STEP_NUM: {STEP_NUM}, STATE: 🔄 進行中,
   DETAIL_STEP: `{STEP_LABEL}: cross {DOCUMENT_TYPE}レビュー中`
2. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Invoke Reviewer" with:
   DOCUMENT_TYPE: {DOCUMENT_TYPE}, NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE}, TARGET_FILE: {TARGET_FILE},
   REFERENCE_FILES: {REFERENCE_FILES}, REVIEW_ROUND: 1, OUTPUT_FILE: {OUTPUT_FILE},
   （EXTRA_REVIEWER_PARAMS が指定されている場合のみ）EXTRA_REVIEWER_PARAMS: {EXTRA_REVIEWER_PARAMS}
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
- `MAX_ROUNDS_OVERRIDE`（任意）: 指定時は、`{CONFIG_KEY}` が明示的に `0`（レビュー完全スキップ）で
  ない限り `CONFIG_KEY` の値より優先して `max_rounds` に採用する。`{CONFIG_KEY}` が明示的に `0` の
  場合は運用者がレビューを意図的にスキップした設定であるため、`MAX_ROUNDS_OVERRIDE` より優先して
  常にスキップする（quick プロファイルが「1ラウンドに強制」しても、運用者が明示的に無効化した
  レビューを復活させない）。`CR_PROFILE: quick` 等、呼び出し元スキルがプロファイルに応じてラウンド数を
  強制上書きしたい場合に使用する。
- `TARGET_FILE`: レビュー対象ファイルのパス
- `REFERENCE_FILES`: レビュー時に参照するファイル一覧
- `REVIEW_OUTPUT_FILE`: レビュー結果の出力先パス
- `FIXER_AGENT`: 修正担当エージェントの subagent_type 名
- `FIXER_PARAMS`: 修正エージェントへの入力パラメータ（key-value 形式）
- `NEXT_DOCUMENT_TYPE`（任意）: 次工程の文書種別（例: ANA→CRS, CRS→SPO（change モード）/ CRS→DSN（新規開発モード）/ CRS→CHD（新規開発モード × `CR_PROFILE: quick`。工程4・5がともにスキップされる経路）, SPO→DSN, DSN→CHD, CHD→TSP）。指定時に xddp-reviewer へ渡し、次工程受け取り可否レビューを実施させる。ダウンストリーム ❌ 項目は xddp-reviewer が `## 2.` に 🔴 として転記するため、ループ判定ロジックの変更は不要。
- `PROGRESS_CR_PATH`（任意）: progress.md のある CR フォルダパス
- `PROGRESS_STEP_NUM`（任意）: 警告フラグを記録するステップ番号
- `EXTRA_REVIEWER_PARAMS`（任意, key-value 形式, default: 空）: `xddp-reviewer` への Agent tool 呼び出し
  （Process 5a）に追加でそのまま渡すパラメータ。`DOCUMENT_TYPE` 固有の
  判定基準値を `xddp-reviewer` に伝える汎用の受け渡し口（例: `TSP` レビュー時の `MIN_COVERAGE`）。
  呼び出し元が指定しない場合は Process 5a の呼び出しに何も追加しない（既存の呼び出しと完全に同一）。
- `METRICS_TARGET`（任意, default: 空）: `record --event review_loop` の `--target` にそのまま渡す
  識別子文字列（例: リポジトリ名・`{repo}/{UR_ID}`）。1つの工程内で `## Review Loop` を複数回
  呼び出すスキル（`xddp.05.arch`／`xddp.06.design`／`xddp.09.test`）が、`metrics.jsonl` の
  `review_loop` イベントをどの呼び出しか事後に区別するために渡す。単一呼び出しのスキル（02/03）は
  省略可（省略時は `--target` オプション自体を付与しない）。

**Process:**
1. Read `{WORKSPACE_ROOT}/xddp.config.md`.
   - Extract `{CONFIG_KEY}` (default: 2 if absent). Set `config_max_rounds`.
   - Extract `FIX_STRATEGY.{DOCUMENT_TYPE}` (default: `balanced` if absent). Set `fix_strategy`.
     修正方針: `efficiency`（最小インパクト優先）/ `ideal`（理想状態優先）/ `balanced`（コストと理想の
     バランス）。`FIXER_PARAMS` に含めてフィクサーエージェントへ伝達する（Process 手順5d参照）。
     AI フィクサーエージェントでは `balanced` は `ideal` と同等に動作する（人への確認は
     xddp.plan-review のインライン修正のみサポート）。
2. `max_rounds` を決定する（優先順位: `{CONFIG_KEY}` が明示的に `0` > `MAX_ROUNDS_OVERRIDE` > `{CONFIG_KEY}` の値）:
   - `config_max_rounds` が明示的に `0` の場合: `max_rounds` = `0`（`MAX_ROUNDS_OVERRIDE` の指定有無に
     関わらずスキップする。運用者の明示的なスキップ意図を尊重する）。
   - 上記以外で `MAX_ROUNDS_OVERRIDE` が指定されている場合: `max_rounds` = `MAX_ROUNDS_OVERRIDE`。
   - 上記いずれでもない場合: `max_rounds` = `config_max_rounds`。
3. If `max_rounds = 0`: レビューをスキップして終了する（`REVIEW_MAX_ROUNDS.*: 0` 設定時、または上記
   手順2の優先順位判定によりスキップと決定した場合）。PROGRESS_CR_PATH と PROGRESS_STEP_NUM が
   指定されている場合、Bash で以下を実行する（ベストエフォート）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_metrics.py record --cr-path {PROGRESS_CR_PATH} --step {PROGRESS_STEP_NUM} --event review_loop --document-type {DOCUMENT_TYPE} --review-rounds 0 --review-max-rounds 0 --review-outcome skipped [--target "{METRICS_TARGET}"]`
   （`METRICS_TARGET` が指定されている場合のみ `--target` を付与する。以下2箇所の `record` 呼び出しも同様）
4. Initialize: `round = 1`, `issues_remain = true`
5. While `issues_remain` and `round ≤ max_rounds`:
   a. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Invoke Reviewer" with:
      DOCUMENT_TYPE: {DOCUMENT_TYPE}, TARGET_FILE: {TARGET_FILE}, REFERENCE_FILES: {REFERENCE_FILES},
      REVIEW_ROUND: {round}, OUTPUT_FILE: {REVIEW_OUTPUT_FILE},
      （NEXT_DOCUMENT_TYPE が指定されている場合のみ）NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE},
      （EXTRA_REVIEWER_PARAMS が指定されている場合のみ）EXTRA_REVIEWER_PARAMS: {EXTRA_REVIEWER_PARAMS}
   b. Read `{REVIEW_OUTPUT_FILE}`.
      - No 🔴/🟡 → `issues_remain = false`. If PROGRESS_CR_PATH and PROGRESS_STEP_NUM are
        provided, run via Bash（ベストエフォート）:
        `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_metrics.py record --cr-path {PROGRESS_CR_PATH} --step {PROGRESS_STEP_NUM} --event review_loop --document-type {DOCUMENT_TYPE} --review-rounds {round} --review-max-rounds {max_rounds} --review-outcome converged [--target "{METRICS_TARGET}"]`
        Exit loop.
      - 🔴/🟡 found and `round < max_rounds`:
        c. **横展開調査:** 各指摘の根本原因パターンを特定する。対象ファイルの他セクションおよび REFERENCE_FILES に列挙された関連ファイルに同一パターンが存在しないかをスキャンし、追加修正箇所を `ADDITIONAL_FIXES` に記録する。
        d. `FIXER_PARAMS` に `FIX_STRATEGY` = `{fix_strategy}` と `ADDITIONAL_FIXES` を追加する。
        e. **Agent tool** `subagent_type={FIXER_AGENT}` with updated `{FIXER_PARAMS}`. Increment `round`. Continue loop.
      - `round = max_rounds` and issues remain:
        1. Append `"⚠️ 未解決の重大指摘あり。人間の判断が必要です。"` to `{REVIEW_OUTPUT_FILE}`.
        2. If PROGRESS_CR_PATH and PROGRESS_STEP_NUM are provided, run via Bash:
           `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py note-add --cr-path {PROGRESS_CR_PATH} --step {PROGRESS_STEP_NUM} --text "未解決指摘あり（{REVIEW_OUTPUT_FILE}）"`
        3. Same condition, also run via Bash（ベストエフォート）:
           `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_metrics.py record --cr-path {PROGRESS_CR_PATH} --step {PROGRESS_STEP_NUM} --event review_loop --document-type {DOCUMENT_TYPE} --review-rounds {round} --review-max-rounds {max_rounds} --review-outcome max_rounds_exhausted [--target "{METRICS_TARGET}"]`
        Exit loop.

## Snapshot Phase Baseline

工程開始時点（成果物生成前）のCRフォルダ状態を記録する共通手順。人レビューゲートの
レビューブリーフ（## Human Review Gate 参照）が「前工程からの差分」を算出するために使う。
各スキルの「Mark In-Progress」ステップ直後から apply する。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `STEP_NUM`: progress.md 上の対象ステップ番号（ゲートに渡すものと同一値）

**Process:**
1. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_review_brief.py baseline --root {CR_PATH} --step {STEP_NUM} --out {CR_PATH}/.phase-baseline-{STEP_NUM}.json`
   （スキル再実行時はベースラインを上書きする＝今回の実行が生んだ増減を差分とする意図的挙動）
2. If the script is not found: tell the user to run `setup.sh` and continue（ベースラインが無くてもブリーフは差分省略で動作するため、停止はしない）。If it errors: display stderr and continue.
3. Also run via Bash（工程所要時間テレメトリの開始マーカー。ベストエフォート）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_metrics.py phase-start --cr-path {CR_PATH} --step {STEP_NUM}`
   If the script is not found or errors: continue silently（テレメトリは工程本体を止めない。
   `## Progress Update` 側で `duration_ms` が省略されるのみ）。

> 停止しない設計理由: ベースラインはブリーフの補助情報であり、取得失敗が工程本体を止めるべきではない
> （`generate` はベースライン欠損時に差分を省略して正常動作する）。

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
1.5. レビューブリーフを生成する（案内表示より前に実行すること）:
   Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_review_brief.py generate --root {CR_PATH} --step {STEP_NUM} --baseline {CR_PATH}/.phase-baseline-{STEP_NUM}.json --out {CR_PATH}/.review-brief.md`
   → stdout の JSON を `BRIEF_SUMMARY`（`top`/`counts`/`brief_path`/`est_total_min`）として取得する。
   If the script is not found: tell the user to run `setup.sh` and continue without a brief（ゲートは止めない）。
   If it errors: display stderr and continue without a brief.
2. Tell the user。以下のテキストを組み立て、**展開後の全行**（`ARTIFACTS_TEXT`・`INTRO_NOTE`・`OPTION_NOTE`
   が複数行の場合はその内部の各行も含む）の先頭に `>` を付与して出力する（変更前の6スキルすべてが
   blockquote 形式で出力していたため、表示形式を維持する）:
   ```
   ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
   {INTRO_NOTE が指定されている場合は挿入}
   {ARTIFACTS_TEXT}
   {BRIEF_SUMMARY が取得できている場合のみ挿入}
   📋 レビューブリーフを生成しました: {BRIEF_SUMMARY.brief_path}
   ⚠️ 重点確認箇所トップN:
   {BRIEF_SUMMARY.top の各件について} - {file}: {marker_type}（{location}）
   推奨レビュー時間の目安: 約 {BRIEF_SUMMARY.est_total_min} 分

   **修正方法：**
   - 直接ファイルを編集する
   {REVISE_COMMAND が指定されている場合}- AIに修正を依頼する場合: {REVISE_COMMAND}
   {OPTION_NOTE が指定されている場合は挿入}

   レビューと修正が完了したら「**レビュー完了**」と入力してください。
   変更がなければそのまま「**レビュー完了**」と入力してください。
   ```
2.5. CR フォルダ全体のスナップショットを取得する（ユーザーの確認待ちに入る前に実行すること）:
   Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_gate_snapshot.py snapshot --root {CR_PATH} --out {CR_PATH}/.gate-snapshot.json`
   If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
   （手順1.5で生成済みの `.review-brief.md` はこの時点で既に確定しており、このスナップショットの
   ベースラインに含まれる。`.phase-baseline-*.json` と併せて誤 `CHANGED` の原因にはならない。）
3. Wait for the user to confirm.
4. `CHANGED` の判定: Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_gate_snapshot.py diff --snapshot {CR_PATH}/.gate-snapshot.json`
   出力 JSON の `changed`（true/false）を `CHANGED` として採用する（`changed_files` は必要に応じて参考情報として利用する）。
   ユーザーの発言が具体的な修正内容に言及しているのに `changed=false` の場合のみ
   （CR フォルダ外のファイル編集の検出漏れ対策）、「ファイルを変更しましたか？」と確認してから判定を上書きする。
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
1. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Invoke Reviewer" with:
   DOCUMENT_TYPE: {DOCUMENT_TYPE}, TARGET_FILE: {TARGET_FILE}, REFERENCE_FILES: {REFERENCE_FILES},
   REVIEW_ROUND: {REVIEW_ROUND}, OUTPUT_FILE: {OUTPUT_FILE},
   （NEXT_DOCUMENT_TYPE が指定されている場合のみ）NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE},
   （EXTRA_REVIEWER_PARAMS が指定されている場合のみ）EXTRA_REVIEWER_PARAMS: {EXTRA_REVIEWER_PARAMS}
2. Read `{OUTPUT_FILE}`. If 🔴 issues remain: inform the user and ask whether to fix again or proceed.

## Invoke Reviewer

`artifact_lint.py`（決定的な機械検査）を実行してから `subagent_type=xddp-reviewer` を呼び出す
共通フロー。`subagent_type=xddp-reviewer` を直接呼ぶ全箇所はこの手続きを apply すること
（Mermaid構文・フロントマター必須キーの機械検査を一本化し、レビュアーは意味整合に集中できるようにする）。

**Input:**
- `DOCUMENT_TYPE`, `REFERENCE_FILES`, `REVIEW_ROUND`, `OUTPUT_FILE`
- `TARGET_FILE`（`TARGET_FILES` が指定される場合は省略される）
- `TARGET_FILES`（任意。`TARGET_FILE` とは相互排他。SPEC バッチレビュー専用 — xddp.11.specs 対応）
- `NEXT_DOCUMENT_TYPE`（任意）
- `EXTRA_REVIEWER_PARAMS`（任意, key-value 形式, default: 空）: `xddp-reviewer` への Agent tool 呼び出しに
  追加でそのまま渡すパラメータ（例: TSP レビュー時の `MIN_COVERAGE`）。既存の「## Review Loop」
  「## Final Review Pass」が持つ同名 Input と同一契約。呼び出し元が指定しない場合は何も追加しない

**Process:**
1. Run via Bash:
   ```
   PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/artifact_lint.py \
     （TARGET_FILES が指定されている場合）--files {TARGET_FILES をカンマ区切りで展開} \
     （TARGET_FILE が指定されている場合）--file {TARGET_FILE} \
     --doc-type {DOCUMENT_TYPE}
   ```
   → 結果 JSON を `LINT_RESULTS` とする。スクリプトが見つからない場合は setup.sh 実行を案内して停止する。
   スクリプトが見つかったが実行時エラーとなった場合（不正なパス・想定外のファイル内容での例外等）は
   stderr を表示して停止する。
2. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: {DOCUMENT_TYPE}
   （TARGET_FILES が指定されている場合）TARGET_FILES: {TARGET_FILES}
   （TARGET_FILE が指定されている場合）TARGET_FILE: {TARGET_FILE}
   REFERENCE_FILES: {REFERENCE_FILES}
   REVIEW_ROUND: {REVIEW_ROUND}
   OUTPUT_FILE: {OUTPUT_FILE}
   LINT_RESULTS: {LINT_RESULTS}
   （NEXT_DOCUMENT_TYPE が指定されている場合のみ追加）NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE}
   （EXTRA_REVIEWER_PARAMS が指定されている場合のみ追加）{EXTRA_REVIEWER_PARAMS を展開}
   ```

## Progress Update

progress.md の指定ステップの状態・詳細ステップ・日付を更新する共通手順。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `STEP_NUM`: 更新するステップ番号
- `STATE`: 新しい状態（🔄 進行中 / ✅ 完了 / 👀 レビュー待ち / 🔁 修正中 / ⏸ 保留 / 🛑 中止）
- `DETAIL_STEP`（任意）: 詳細ステップ文字列（完了時は `"-"` とする）。省略時は既存の詳細ステップを
  変更しない（例: 差し戻し時に状態列だけを更新する場合）
- `ARTIFACT_LINK`（任意）: 成果物へのリンク文字列。指定時は STATE によらず成果物列を更新する
  （工程完了時のリンク設定に加え、`xddp.06.design`「## Step C': Generate Traceability Matrix (TM)」の
  ように工程進行中に成果物列だけを先行更新するケースにも使う）。
  **フォーマット規約（全スキル共通）:**
  - 必ず `[表示名](progress.md からの相対パス)` の Markdown リンク形式にする（生パス文字列は不可。
    `xddp.status`「## 6. Artifact checklist」がこの形式の有無で ✅/⬜ を判定するため）。
  - 相対パスは progress.md の位置（`{CR_PATH}` 直下）を起点とする。`{CR_PATH}` 配下のファイル・
    ディレクトリを指す場合は先頭に `../` を付けない。`{CR_PATH}` の外（`{XDDP_DIR}/latest-specs/` 等）
    を指す場合のみ `../` を使う。
  - 単一ファイルに定まる成果物（REQ・ANA・CRS・TM）はそのファイルへの直接リンクにする。
  - per-repo + cross で複数ファイルに分かれる成果物（SPO・DSN・CHD・CODING/VERIFY・TSP・TRS）は
    工程の出力ディレクトリへのリンク（例: `[04_specout/](04_specout/)`）にする。
    ただし当該経路で実際に生成される成果物が単一ファイルに定まる場合（例: `CR_PROFILE: quick` で
    cross DSN のみを生成する経路）は、そのファイルへの直接リンクとする。
  - 付与してよい STATE: `✅ 完了` および工程進行中の先行更新（`🔄 進行中`）には付与する。
    `⏭️ スキップ` の行には、成果物が実在する場合（他工程に統合されて生成済み等）のみ付与し、
    `⏭️ スキップ（対象外）` のように成果物が生成されないスキップには付与しない
    （付与すると未実施の工程が Artifact checklist で ✅ と表示される）。
  - 工程をやり直すために状態を巻き戻す場合（`⬜ 未着手` へ戻す等）は、`ARTIFACT_LINK` に `-` を
    明示的に渡して成果物列をクリアする（省略すると旧リンクが残り、状態と食い違う）。
    空文字 `""` は falsy のため無視される点に注意（`xddp_progress.py` の `if args.artifact_link:`）。

**Process:**
1. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py update --cr-path {CR_PATH} --step {STEP_NUM} --state "{STATE}" [--detail "{DETAIL_STEP}"] [--artifact-link "{ARTIFACT_LINK}"]`
   （`STATE` = ✅ 完了 のとき、スクリプトが `## 備考・メモ` の `⚠️ 工程{STEP_NUM}:` 行を自動削除する）
2. If the script is not found: tell the user to run `setup.sh` and stop.
   If it errors: display stderr to the user and stop.
3. If `{STATE}` = `✅ 完了`: also run via Bash（工程所要時間テレメトリ。ベストエフォート。
   `## Snapshot Phase Baseline` を経由していない工程では開始マーカーが無いため `duration_ms` は
   省略される。この場合もレコード自体は書き込まれる）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_metrics.py record --cr-path {CR_PATH} --step {STEP_NUM} --event phase_complete`
   If the script is not found or errors: display stderr as advisory only and continue — do not stop
   （手順1・2とは異なり、テレメトリ失敗は工程完了そのものをブロックしない）。

## Regenerate CRS Excel (UR-016)

CRS Markdown から確認用 Excel を再生成する共通手順。各スキルの「Excel再生成」ステップから apply して使用する。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `CR`: CR番号
- `MD2EXCEL_PYTHON_BIN`（暗黙。呼び出し元が `## CR Resolution` 経由で解決済みの値をそのまま参照する。
  `DEVELOPMENT_MODE` 等と同じ扱いのため、apply 呼び出し時に明示的に渡す必要はない）

**Process:**
1. Let `CRS_PATH` = `{CR_PATH}/03_change-requirements/CRS-{CR}.md`.
2. Let `EXCEL_PATH` = `{CR_PATH}/03_change-requirements/CRS-{CR}.xlsx`.
3. Run via Bash:
   - `MD2EXCEL_PYTHON_BIN` が設定されている場合: `"{MD2EXCEL_PYTHON_BIN}" ~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py {CRS_PATH} {EXCEL_PATH}`
   - 未設定の場合（デフォルト）: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py {CRS_PATH} {EXCEL_PATH}`
4. If `crs_md2excel.py` not found: tell the user to run `setup.sh`. If errors（`ModuleNotFoundError: No module named 'openpyxl'` を含む）: display to user, and if `MD2EXCEL_PYTHON_BIN` is unset, additionally suggest configuring it in `xddp.config.md`「## 5. 実行環境設定」.
5. Report output path and UR/SR/SP counts from script stdout.

> **Design policy:** The sole definition of the Excel format is in `~/.claude/skills/xddp.md2excel/SKILL.md` and `~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py`.
> This skill does not define its own format; it always delegates to xddp.md2excel to prevent format divergence by generation path.
> To change the format, modify only xddp.md2excel/SKILL.md and crs_md2excel.py.
> **成果物の位置付け:** `CRS-{CR}.xlsx` は人間向け確認ツール（一時生成物）。xddp.close の DOCS_DIR 昇格対象外。

## Resolve VCS Target Repos

VCS の副作用（ブランチ作成/切替・コミット・revert 案内）の対象となるリポジトリ集合を、
当該 CR が実際に変更設計を持つリポジトリに限定して解決する共通手順。

**Input:**
- `REPO_CANDIDATES`: 候補リポジトリ名のリスト（呼び出し元が `AFFECTED_REPOS` または `REPOS_KEYS` を渡す）
- `CR_PATH`: CRフォルダのパス
- `CR`: CR番号
- `DEVELOPMENT_MODE`（暗黙）: `## CR Resolution`/`## Load Config` 経由で解決済みの値をそのまま参照する
  （`MD2EXCEL_PYTHON_BIN` と同じ扱いのため、apply 呼び出し時に明示的に渡す必要はない）
- `VCS_TYPE`（暗黙）: 同上。手順3の警告の要否判定にのみ使用する（判定ロジック本体は VCS 種別に
  依存しない純粋なファイル存在確認である）

**Output:** `VCS_TARGET_REPOS`

**Process:**
1. If `DEVELOPMENT_MODE` is `new`:
   `VCS_TARGET_REPOS` = `REPO_CANDIDATES` のうち `{CR_PATH}/06_design/{repo}/CHD-{CR}.md`
   （CHD インデックスファイル）が存在するリポジトリのみ。Go to 手順3。
   （`DEVELOPMENT_MODE: new` では工程4がスキップされ SPO が原理的に存在しないため、手順2の判定材料が
   使えない。新規開発ではワークスペース全体が CR の対象であるのが通常であり、CHD ベースの判定＝
   実質的に全リポジトリになることは想定内である）
2. Else（`DEVELOPMENT_MODE` is `change`。既定）:
   `VCS_TARGET_REPOS` = `REPO_CANDIDATES` のうち `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`
   （スペックアウト成果物）が存在するリポジトリのみ。
   （本プロシージャは同ファイルの Read を行わず**存在確認のみ**を行う）
3. `VCS_TARGET_REPOS` が空の場合:
   - If `VCS_TYPE` is `none`: 警告を出さずに空リストを返す（`VCS_TYPE: none` は利用者が VCS 統合機能を
     明示的に無効化した状態であり、そもそも VCS 操作が一切行われない。この状態で「VCS 操作をスキップ
     します／必要に応じて手動でコミットしてください」と案内するのは無意味なノイズであり、`none` を
     選んだ意図とも矛盾する）。
   - Else（`VCS_TYPE` が `auto`/`git`）: `DEVELOPMENT_MODE` に応じた以下の警告を出して空リストを返す
     （`DEVELOPMENT_MODE: new` では工程4が仕様上スキップされるため、「工程4を実施済みか確認」という
     案内は誤誘導になる。判定材料が異なる以上、警告文も分ける）。
     - `DEVELOPMENT_MODE` is `new` の場合:
       Warn: "⚠️ 本 CR の変更設計書（CHD）を持つリポジトリが見つからないため、VCS 操作（ブランチ作成・
       コミット）の対象を特定できません。VCS 操作をスキップします。工程6（変更設計書作成）を実施済みか
       確認し、必要に応じて手動でコミットしてください。"
     - `DEVELOPMENT_MODE` is `change` の場合:
       Warn: "⚠️ 本 CR のスペックアウト成果物（SPO）を持つリポジトリが見つからないため、VCS 操作
       （ブランチ作成・コミット）の対象を特定できません。VCS 操作をスキップします。工程4を実施済みか
       確認し、必要に応じて手動でコミットしてください。"
   （呼び出し元は空リストを受け取ると For each ループが0回になり、結果として VCS 操作が行われない。
   該当工程を完了していれば対象リポジトリの成果物は必ず存在するため、通常フローでこの分岐には到達しない）

**この判定で残る限界:** SPO の存在が表すのは「調査対象にしたリポジトリ」であって「調査の結果、影響ありと
確定したリポジトリ」ではない。`xddp.04.specout/SKILL.md` は全リポジトリのスペックアウトを推奨しており、
Step 0.5 の確認ゲートで人が絞り込まない既定フローでは `VCS_TARGET_REPOS` は結果的に `REPOS_KEYS` と
一致する。すなわち本プロシージャは「限定できる**手段**を用意し、人の絞り込みが VCS 側にも反映される経路を
作る」ものであって、「すべての構成で必ず限定される」ことを保証するものではない。利用者への当面の回避
手段は、`xddp.04.specout` の Step 0.5 で本 CR に無関係なリポジトリを対象から外すことである（この操作が
SPO の有無を通じて VCS 対象にも反映される）。設計判断の詳細は `docs/adr/ADR-0011-vcs-abstraction.md`
Decision 5 を参照。

## VCS Commit If Dirty

対象リポジトリ群に対し status を確認し、dirty ならコミットする共通ループ本体。

**Input:**
- `REPO_LIST`: 対象リポジトリ名のリスト。呼び出し元は `## Resolve VCS Target Repos` が返した
  `VCS_TARGET_REPOS` を渡すこと（`AFFECTED_REPOS` はマルチリポジトリ構成では `REPOS_KEYS` と
  同一＝全リポジトリであり、CR のスコープ限定にならないため使わない）
- `COMMIT_MESSAGE`: コミットメッセージ（本プロシージャの Bash ステップは `commit "{COMMIT_MESSAGE}"`
  の形でダブルクォートの中に直接埋め込むため、`COMMIT_MESSAGE` にはダブルクォート・バッククォート・
  `$()` を含まない静的定型文のみを渡すこと）
- `ON_FAILURE`（任意, default: `stop`）: 失敗時（`commit` の exit code ≠ 0、または `REPO_STATUS` が
  `unknown`）の扱い。
  - `stop`: エラーを表示して停止する（既定。工程7・工程10の呼び出し元はこれを使う）。
  - `ask`: エラーを表示したうえで続行/中止をユーザーに確認する。「中止」なら残りのリポジトリを
    処理せず、`COMMIT_OUTCOME` = `aborted` として**呼び出し元へ戻る**（プロシージャ内では停止せず、
    中止後の処理——`progress.md` への中断記録等——は呼び出し元の責務とする）。
    「続行」なら当該リポジトリのコミットを行わないまま次のリポジトリへ進む。
    `xddp.close` の最終コミットのみが使う（設計判断の詳細は `docs/adr/ADR-0011-vcs-abstraction.md`
    Decision 20 を参照）。
- `VCS_TYPE`（暗黙）: `## CR Resolution`/`## Load Config` 経由で解決済みの値をそのまま参照する
  （`MD2EXCEL_PYTHON_BIN` と同じ扱いのため、apply 呼び出し時に明示的に渡す必要はない）
- `REPOS_MAP`（暗黙）: 同上

**Output:**（`ON_FAILURE` 省略時（`stop`）は失敗時にプロシージャ内で停止するため、呼び出し元へ制御が
戻る場合の `COMMIT_OUTCOME` は必ず `ok` になり、既存の呼び出し元は出力を参照しなくてよい）
- `COMMIT_OUTCOME`: `ok`（全リポジトリを処理し、失敗による中断・スキップが無かった）／
  `partial`（`ask` で「続行」が選ばれ、コミットされなかったリポジトリがある）／
  `aborted`（`ask` で「中止」が選ばれ、残りのリポジトリを処理していない）
- `UNCOMMITTED_REPOS`: **status を確認したうえでコミットされなかった**リポジトリ名のリスト
  （`ok` の場合は空）。`aborted` の場合、中止時点で未処理だった残りのリポジトリは status 確認自体を
  行っていない（clean かもしれない）ため、**このリストには含めない**。
- `UNPROCESSED_REPOS`: `aborted` の場合に、中止によって status 確認すら行わなかった残りの
  リポジトリ名のリスト（`ok`／`partial` の場合は空）

**Process:**
Initialize `COMMIT_OUTCOME` = `ok`, `UNCOMMITTED_REPOS` = 空リスト, `UNPROCESSED_REPOS` = 空リスト。
For each `{repo}` in `{REPO_LIST}`:
  Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_vcs.py status --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE}`
  → let `REPO_STATUS`.
  If `REPO_STATUS` is `dirty`:
    Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_vcs.py commit "{COMMIT_MESSAGE}" --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE}`
    If exit code ≠ 0:
      If `ON_FAILURE` is `ask`: エラーを表示し、続行/中止を確認する。
        中止なら `COMMIT_OUTCOME` = `aborted`、`UNCOMMITTED_REPOS` に `{repo}` を追加し、
        `UNPROCESSED_REPOS` に `{REPO_LIST}` の未処理の残りリポジトリを設定して、ループを抜けて
        呼び出し元へ戻る（プロシージャ内では停止しない。残りのリポジトリは status 確認自体を
        行っていないため `UNCOMMITTED_REPOS` とは区別する）。
        続行なら `COMMIT_OUTCOME` = `partial`、`UNCOMMITTED_REPOS` に `{repo}` を追加し、
        次の `{repo}` へ進む。
      Else（`stop`。既定）: report the error and stop.
  If `REPO_STATUS` is `unknown`:
    If `ON_FAILURE` is `ask`: 上記 exit code ≠ 0 と同じ扱い（エラー表示＋続行/中止の確認、および
      `COMMIT_OUTCOME`／`UNCOMMITTED_REPOS`／`UNPROCESSED_REPOS` の更新）とする（中止時は exit code ≠ 0
      の場合と同様に `UNPROCESSED_REPOS` へ `{REPO_LIST}` の未処理の残りリポジトリを設定する）。
    Else（`stop`。既定）: Report error and stop.
    （既定は「停止」に確定する。本プロシージャは commit という副作用を伴う処理であり、status が不明な
    状態で commit を試みるとコミット漏れ・意図しない内容の巻き込みに気付けないまま進行するリスクが
    ある。「status 確認等の読み取り専用処理は続行を許容し、commit/branch/revert 等の副作用を伴う処理は
    安全側に倒して停止する」という本設計の原則（`docs/adr/ADR-0011-vcs-abstraction.md` Decision 15）と
    整合させる。`ON_FAILURE: ask` はこの原則の例外ではなく、「AI が黙って先へ進まない」という原則の核を
    保ったまま、判断を人に委ねる第3の選択肢である。`xddp.close` のように、停止することで失われる下流
    処理（成果物昇格・CR 完了記録）がある呼び出し元にのみ適用する）

ループ終了後（`COMMIT_OUTCOME` によって文面を分ける——`aborted` では処理を「続行」していないため、
`partial` と同じ文面では事実と食い違う）:
  If `COMMIT_OUTCOME` is `partial`:
    Warn: "⚠️ 未コミットのまま処理を続行したリポジトリ: {UNCOMMITTED_REPOS を列挙}"
  If `COMMIT_OUTCOME` is `aborted`:
    Warn: "⚠️ コミット処理を中止しました。未コミットのリポジトリ: {UNCOMMITTED_REPOS を列挙}／
    未処理（status 未確認）のリポジトリ: {UNPROCESSED_REPOS を列挙。空の場合は「なし」}"
Return `COMMIT_OUTCOME`, `UNCOMMITTED_REPOS`, `UNPROCESSED_REPOS`.

## VCS Auto-Commit

指定ステップの自動コミットを行う共通手順。`VCS_COMMIT_ON_STEP` に対象ステップが含まれる場合のみ
`## VCS Commit If Dirty` を呼び出す。

**Input:**
- `PROCESS_STEP`: `VCS_COMMIT_ON_STEP` と照合する工程番号（例: `7`, `10`。`## Progress Update` の
  `STEP_NUM`（例: `10a`/`10b`/`10c`）とは意味が異なるため、同名の `STEP_NUM` ではなく `PROCESS_STEP`
  という別名を用いる。呼び出し元 SKILL.md で `## Progress Update` と `## VCS Auto-Commit` の呼び出しが
  近接していても、コピー&ペースト時に誤って `## Progress Update` のステップ識別子（`10a` 等）を
  渡してしまうリスクを構造的に排除するため）
- `REPO_LIST`: 対象リポジトリ名のリスト（`## VCS Commit If Dirty` と同一契約。呼び出し元は
  `VCS_TARGET_REPOS` を渡す）
- `COMMIT_MESSAGE`: コミットメッセージ（例: `{CR} 工程7コーディング完了`）
- `VCS_TYPE`（暗黙）, `VCS_COMMIT_ON_STEP`（暗黙）: `## VCS Commit If Dirty` と同じ扱い

**Process:**
1. If `VCS_TYPE` is `none`: 何もせず終了する。
2. Let `COMMIT_STEPS` = `VCS_COMMIT_ON_STEP` をカンマ区切りで分割し、前後の空白を除去したリスト。
   `none` または空の場合は空リスト。
3. If `{PROCESS_STEP}` is not in `COMMIT_STEPS`: 何もせず終了する。
4. apply "## VCS Commit If Dirty" with REPO_LIST: {REPO_LIST}, COMMIT_MESSAGE: {COMMIT_MESSAGE}.

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

## Load Domain Constraints

`project-rulebook.md` から「ドメイン制約」節のみを抽出する共通手順。
`Load Steering Context` が rulebook 全体を返すのに対し、本手順は該当節のみを返す。

**Input:**
- `XDDP_DIR`: XDDPディレクトリのパス

**Output:** `DOMAIN_CONSTRAINTS`（抽出した節の本文。該当なしの場合は空文字列）

**Process:**
1. Read `{XDDP_DIR}/project-rulebook.md` (if exists)。見出し `## 1.6 ドメイン制約` を**見出し名で**探す
   （節番号が変わっても追随できるよう、番号ではなく「ドメイン制約」の語で照合する）。
   見つかった場合、次の `## ` 見出しの直前までを抽出する。
2. 抽出結果の全行が未記入（プレースホルダー `{...}` のみ、または全行「該当なし」）の場合は
   `DOMAIN_CONSTRAINTS` = 空文字列とする（未記入のテンプレートを渡してもノイズにしかならないため）。
3. Return `DOMAIN_CONSTRAINTS`.

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

## Build Design Spec Params

xddp-designer-agent 呼び出しに渡す DSN_INDEX_FILE／DSN_COMPARISON_FILE／CRS_FILE／SPO_FILE／
SPO_MODULES_DIR のパラメータブロックを構築する共通手順（`xddp.06.design` Step A・Step A2 backfill が
条件文の詳細度が異なる状態で複製していたものを1箇所に統合し、詳細度は Step A 側の
「条件部にファイルパスを明記」する形へ統一する）。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `REPO_NAME`: リポジトリ名
- `CR`: CR番号

**Output:** `DESIGN_SPEC_PARAMS_BASE`（Agent tool 呼び出しへそのまま展開する複数行ブロック）

**Process:**
1. 以下のブロックを構築する:
   ```
   （{CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}.md が存在する場合のみ追加）DSN_INDEX_FILE: {CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}.md
   （{CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}-comparison.md が存在する場合のみ追加）DSN_COMPARISON_FILE: {CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}-comparison.md
   CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
   （{CR_PATH}/04_specout/{REPO_NAME}/SPO-{CR}.md が存在する場合のみ追加）SPO_FILE: {CR_PATH}/04_specout/{REPO_NAME}/SPO-{CR}.md
   （{CR_PATH}/04_specout/{REPO_NAME}/modules/ が存在する場合のみ追加）SPO_MODULES_DIR: {CR_PATH}/04_specout/{REPO_NAME}/modules/
   ```
2. Return `DESIGN_SPEC_PARAMS_BASE`.

## Build Arch Agent Paths

xddp-architect-agent 呼び出しに渡す INDEX_FILE／APPROACHES_DIR を構築する共通手順（`xddp.05.arch`
Step A・Step B・Step B3 が同一の値を複製していたものを1箇所に統合）。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `REPO_NAME`: リポジトリ名
- `CR`: CR番号

**Output:** `ARCH_INDEX_FILE`, `ARCH_APPROACHES_DIR`

**Process:**
1. `ARCH_INDEX_FILE` = `{CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}.md`
2. `ARCH_APPROACHES_DIR` = `{CR_PATH}/05_architecture/{REPO_NAME}/`
3. Return `ARCH_INDEX_FILE`, `ARCH_APPROACHES_DIR`.

## Build TSP Output File

TSP 出力ファイルのパスを構築する共通手順（`xddp.09.test` Step A・Step B が同一定義を複製していた
ものを1箇所に統合）。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `REPO_NAME`: リポジトリ名
- `CR`: CR番号

**Output:** `TSP_OUTPUT_FILE`

**Process:**
1. `TSP_OUTPUT_FILE` = `{CR_PATH}/09_test-spec/{REPO_NAME}/TSP-{CR}.md`
2. Return `TSP_OUTPUT_FILE`.
