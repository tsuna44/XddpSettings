---
description: XDDP スキル共通ロジック。CR 番号の解決などを定義する。
user-invocable: false
---

# XDDP Common Logic

## CR Resolution

**Input:** `RAW_ARGS` = trimmed string of $ARGUMENTS  
**Output:** `CR` (resolved CR number), `REST_ARGS` (remaining args after CR)  
On failure, report error and stop.

Search for `xddp.config.md` upward from cwd to determine `WORKSPACE_ROOT`.
If not found, report error and stop.
Read `XDDP_DIR` (default: `xddp`) and `CR_PREFIX` (default: `CR`).

### Step 1: Identify CR from arguments

Let `FIRST_ARG` = first token of `RAW_ARGS`.

- `FIRST_ARG` starts with `{CR_PREFIX}-`
  → `CR = FIRST_ARG`, `REST_ARGS` = remaining tokens. Done.
- `FIRST_ARG` is empty or does not start with `{CR_PREFIX}-`
  → `REST_ARGS = RAW_ARGS` (treat all tokens as secondary args). Go to Step 2.

> **Skills that use secondary args:**
> - `xddp.review`: first token of `REST_ARGS` → `DOCUMENT_TYPE`
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
- `FIX_STRATEGY`（任意, default: `balanced`）: 修正方針。`efficiency`（最小インパクト優先）/ `ideal`（理想状態優先）/ `balanced`（コストと理想のバランス）。xddp.common が `FIX_STRATEGY.{DOCUMENT_TYPE}` として xddp.config.md から自動読み込みする（step 1 参照）。`FIXER_PARAMS` に含めてフィクサーエージェントへ伝達する。AI フィクサーエージェントでは `balanced` は `ideal` と同等に動作する（人への確認は xddp.plan-review のインライン修正のみサポート）。
- `NEXT_DOCUMENT_TYPE`（任意）: 次工程の文書種別（例: ANA→CRS, CRS→SPO, SPO→DSN, DSN→CHD, CHD→TSP）。指定時に xddp-reviewer へ渡し、次工程受け取り可否レビューを実施させる。ダウンストリーム ❌ 項目は xddp-reviewer が `## 2.` に 🔴 として転記するため、ループ判定ロジックの変更は不要。
- `PROGRESS_CR_PATH`（任意）: progress.md のある CR フォルダパス
- `PROGRESS_STEP_NUM`（任意）: 警告フラグを記録するステップ番号

**Process:**
0. If `max_rounds = 0`: レビューをスキップして終了する（`REVIEW_MAX_ROUNDS.*: 0` 設定時）。
1. Read `{WORKSPACE_ROOT}/xddp.config.md`.
   - Extract `{CONFIG_KEY}` (default: 2 if absent). Set `max_rounds`.
   - Extract `FIX_STRATEGY.{DOCUMENT_TYPE}` (default: `balanced` if absent). Set `fix_strategy`.
2. Initialize: `round = 1`, `issues_remain = true`
3. While `issues_remain` and `round ≤ max_rounds`:
   a. **Agent tool** `subagent_type=xddp-reviewer`:
      ```
      DOCUMENT_TYPE: {DOCUMENT_TYPE}
      TARGET_FILE: {TARGET_FILE}
      REFERENCE_FILES: {REFERENCE_FILES}
      REVIEW_ROUND: {round}
      OUTPUT_FILE: {REVIEW_OUTPUT_FILE}
      （NEXT_DOCUMENT_TYPE が指定されている場合のみ追加）NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE}
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
