---
name: xddp-common
description: XDDP スキル共通ロジック。CR 番号の解決・CR非依存の config 読み込みなどを定義する。
user-invocable: false
---

# XDDP Common Logic

## Load Config

xddp.config.md を探索・読み込み、CR に依存しない標準設定バンドルを返す共通手順。
CR 解決が不要なスキル（`xddp-status`・`xddp-codemap`・`xddp-update-knowledge`・
`xddp-fill-rulebook` 等）はこちらを直接使う。CR 解決が必要なスキルは `## CR Resolution` を使う。

**Input:** `NOT_FOUND_MESSAGE`（任意, default: `"xddp.config.md が見つかりません。ワークスペース
ルートまたはそのサブディレクトリで実行してください。"`）: 未検出時に表示するメッセージ。

**Output:** スクリプトが出力する JSON のトップレベルキー全て。
キー名・既定値・消費者の一覧は `xddp_config.py load --list-keys` で得られる。

**Process:**
1. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_config.py load --format json --start-dir .`
2. 終了コードで分岐する: 0=成功 / 1=実行時エラー（stderr を表示して停止）/
   2=使用法エラー（argparse 既定。stderr を表示して停止）/ 3=xddp.config.md 未検出
   （`{NOT_FOUND_MESSAGE}` を表示して停止）。
3. 出力 JSON をそのまま設定バンドルとして使う。stderr に警告があれば人に中継する。
4. `REPOS:` が未設定・空の場合の扱いは呼び出し元スキルの裁量。

## CR Resolution

**Input:**
- `RAW_ARGS` = trimmed string of $ARGUMENTS
- `SKIP_ABORT_GUARD`（任意, default: `false`）: `true` の場合、下記の「中止済み CR ガード」を
  スキップする。`/xddp-abort` 専用。他スキルはこの引数を渡さない。

**Output:** `CR`（解決済みCR番号）, `REST_ARGS`（CR以降の残り引数）、および `## Load Config` が
返す標準設定バンドル全て。
On failure, report error and stop.

apply "## Load Config"（本ファイル内）→ 標準設定バンドルを取得する。

### Step 1: Identify CR from arguments

Let `FIRST_ARG` = first token of `RAW_ARGS`.

List all directories directly under `{WORKSPACE_ROOT}/{XDDP_DIR}/`, excluding hidden directories
(dotfiles) and the reserved names `latest-specs` / `survey` (同じ除外規則を Step 2 とも共有する)。

- `FIRST_ARG` is non-empty AND exactly matches (完全一致。前方一致・部分一致ではない) the name of one
  of the listed directories
  → `CR = FIRST_ARG`, `REST_ARGS` = remaining tokens. Go to Step 1.X.
- otherwise (FIRST_ARG is empty, or no listed directory name equals `FIRST_ARG`)
  → `REST_ARGS = RAW_ARGS` (treat all tokens as secondary args). Go to Step 2.

> **命名上の注意:** CRフォルダ名は `{XDDP_DIR}/` 直下の実在ディレクトリとして解決されるため、
> `xddp-review`・`xddp-revise` 等が第2引数として使う予約語（`analysis`/`req`/`specout`/`arch`/
> `design`/`test`/`spec`/`full`/`quick`）、`xddp-04-specout` の `ENTRY_POINTS`（調査対象の関数・
> クラス名等の自由記述シンボル）、および予約ディレクトリ名（`latest-specs`・`survey`）と同名のCRを作成しないこと。
> 同名の場合、Step 1 がその引数を誤ってCR番号と解釈する可能性がある。

> **Skills that use secondary args:**
> - `xddp-review`: first token of `REST_ARGS` → `DOCUMENT_TYPE`（`DOCUMENT_TYPE = spec` の場合、2番目のトークン → `TARGET_ARG`（省略可））
> - `xddp-revise`: first token of `REST_ARGS` → `DOC_TYPE`
> - `xddp-excel2md`: first token of `REST_ARGS` → `EXCEL_PATH`
> - `xddp-04-specout`: remaining tokens of `REST_ARGS` → `ENTRY_POINTS`

### Step 2: Auto-detect

List all directories directly under `{WORKSPACE_ROOT}/{XDDP_DIR}/` as CR candidates,
excluding hidden directories (dotfiles) and the reserved names `latest-specs` / `survey`.

- **0 found** → report `"CRフォルダが見つかりません。{WORKSPACE_ROOT}/{XDDP_DIR}/ に CR フォルダを作成するか、CR番号を引数に指定してください。"` and stop.
- **1 found** → `CR = that directory name`. Report `"CR を自動検出しました: {CR}"` and continue.
- **Multiple found** → for each candidate directory `{dir}`, let `DIR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{dir}`
  （`{dir}` は直前の「List all directories directly under `{WORKSPACE_ROOT}/{XDDP_DIR}/`」で得られる
  ディレクトリの裸の名前であり絶対パスではない。`xddp_progress.py` の `_progress_path()` は
  `--cr-path` の値をそのまま `Path(cr_path)/"progress.md"` として解決するため、裸の名前を渡すと
  オーケストレータの cwd 次第で `progress.md` が見つからず全候補が異常系と誤判定される。
  `xddp-abort/SKILL.md`「Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`」と同一のパス構築パターンに
  倣う。`CR` 確定前（Step 1.X 到達前）のこの分岐では `CR_PATH` 変数が存在しないため、ここで
  `{dir}` ごとに個別のローカル変数 `DIR_PATH` を明示的に構築する）、run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py check-in-progress --cr-path {DIR_PATH}`
  → let `CHECK_RESULT`（stdout の JSON 1オブジェクト）。
  If it errors（e.g. `{DIR_PATH}/progress.md` が存在しない・破損している等の異常系）:
    treat `{dir}` as not in-progress for this candidate, and additionally warn:
    "⚠️ {dir} の progress.md を読み取れませんでした（不正な CR フォルダの可能性があります）。"
    （候補一覧からは除外しない——`{dir}` が実在する以上、人が最終的に選択肢として認識できる必要が
    あるため。in-progress 判定からのみ除外する）
  Else: a CR is "in progress" if `CHECK_RESULT.in_progress` is `true`
  （判定条件の実装は `check-in-progress` に一元化されている。条件(a)(b)の設計意図・除外条件の理由は
  `xddp_progress.py` の `cmd_check_in_progress` のコメントを参照）:
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
   手順1の初期値のまま次のステップに進む。`## CR Resolution` は `xddp-01-init` からは呼ばれず
   `xddp-01-init` の Step 5 で progress.md 生成後に初めて他スキルから呼ばれる想定のため、通常の
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
   呼び出し元スキルが本プロシージャの結果を上書きする — 例: `xddp-04-specout` Step 0.5 の人による確認・絞り込み。）
2. `FILTER_BY_SPO = true`（`xddp-11-specs` 専用 — 実際に specout・設計が完了したリポジトリのみを
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
- `xddp-04-specout`: cross 成果物自体がこの工程で初めて生成されるため、着手時点では
  存在チェック対象のファイルがまだない。`HAS_CROSS` は初期値 `IS_MULTI` とし、
  Discovery でリポジトリ間依存が見つからなければ `false` に降格する、成果物存在チェックとは
  異なる判定方式を用いる。
- `xddp-close`: 特定1ファイルの存在ではなく、CR 内の cross/ 配下に何らかの成果物が
  存在するか（工程4a〜8のどこかで cross 処理が行われたか）を広く問う棚卸し用途のため、
  「直前工程の特定ファイル」を前提とする本プロシージャの対象外とする。

## Progress Update

progress.md の指定ステップの状態・詳細ステップ・日付を更新する共通手順。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `STEP_NUM`: 更新するステップ番号
- `STATE`: 新しい状態（🔄 進行中 / ✅ 完了 / 👀 レビュー待ち / 🔁 修正中 / ⏸ 中断 / 🛑 中止）
- `DETAIL_STEP`（任意）: 詳細ステップ文字列（完了時は `"-"` とする）。省略時は既存の詳細ステップを
  変更しない（例: 差し戻し時に状態列だけを更新する場合）
- `ARTIFACT_LINK`（任意）: 成果物へのリンク文字列。指定時は STATE によらず成果物列を更新する
  （工程完了時のリンク設定に加え、`xddp-06-design`「## Step C': Generate Traceability Matrix (TM)」の
  ように工程進行中に成果物列だけを先行更新するケースにも使う）。
  `ARTIFACT_LINK` の書式は `xddp_progress.py` が検証する（不正な場合は非 0 終了して理由を表示する）。
  巻き戻し時に成果物列をクリアするには `-` を明示的に渡す（空文字は無視される）。

**Process:**
1. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py update --cr-path {CR_PATH} --step {STEP_NUM} --state "{STATE}" [--detail "{DETAIL_STEP}"] [--artifact-link "{ARTIFACT_LINK}"]`
   （`STATE` = ✅ 完了 のとき、スクリプトが `## 備考・メモ` の `⚠️ 工程{STEP_NUM}:` 行を自動削除する）
2. If the script is not found: tell the user to run `setup.sh` and stop.
   If it errors: display stderr to the user and stop.
3. If `{STATE}` = `✅ 完了`: also run via Bash（工程所要時間テレメトリ。ベストエフォート。
   `## Snapshot Phase Baseline` を経由していない工程では開始マーカーが無いため `duration_ms` は
   省略される。この場合もレコード自体は書き込まれる）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_metrics.py record --cr-path {CR_PATH} --step {STEP_NUM} --event phase_complete`
   If the script is not found or errors: display stderr as advisory only and continue — do not stop
   （手順1・2とは異なり、テレメトリ失敗は工程完了そのものをブロックしない）。

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

## Procedures Index

高頻度（直接参照ファイル数 ≥ 9）の6手順は本ファイルに残置し、それ以外は
`procedures/` 配下へ分割した。呼び出し元は該当ファイルを `Read ~/.claude/skills/xddp-common/procedures/{ファイル名}`
した上で、ファイル内の見出しを対象に `apply` する。

- `invoke-reviewer.md` — Invoke Reviewer: xddp-reviewer への Agent tool 呼び出し共通手順
- `review-loop.md` — Review Loop: AIレビュー→Fixer の反復ループ共通制御フロー
- `human-review-gate.md` — Human Review Gate: 人レビューゲート共通フロー
- `final-review-pass.md` — Final Review Pass: 最終確認パス
- `cross-artifact-review.md` — Cross Artifact Review: cross/ 成果物のAIレビュー→インライン修正フロー
- `snapshot-phase-baseline.md` — Snapshot Phase Baseline: 工程所要時間テレメトリの開始マーカー記録
- `regenerate-crs-excel.md` — Regenerate CRS Excel (UR-016): CRS Markdown → Excel 再生成
- `resolve-vcs-target-repos.md` — Resolve VCS Target Repos: VCS操作対象リポジトリの解決
- `vcs-commit-if-dirty.md` — VCS Commit If Dirty: 未コミット変更があるリポジトリへの自動コミット
- `vcs-auto-commit.md` — VCS Auto-Commit: 指定ステップでの自動コミット制御
- `load-lessons-context.md` — Load Lessons Context: 知見ログの読み込み
- `run-verification-tools.md` — Run Verification Tools: lint/build/typecheck の実ツール実行
- `load-steering-context.md` — Load Steering Context: project-rulebook.md の読み込み
- `load-domain-constraints.md` — Load Domain Constraints: ドメイン制約の読み込み
- `detect-test-framework.md` — Detect Test Framework: テストフレームワーク自動検出
- `build-design-spec-params.md` — Build Design Spec Params: xddp-designer-agent 呼び出しパラメータ構築
- `build-arch-agent-paths.md` — Build Arch Agent Paths: xddp-architect-agent 呼び出しパス構築
- `build-tsp-output-file.md` — Build TSP Output File: TSP 出力ファイルパス構築
