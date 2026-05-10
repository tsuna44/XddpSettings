---
description: XDDP スキル共通ロジック。CR 番号の解決などを定義する。
---

# XDDP Common Logic

## CR Resolution

**入力:** `RAW_ARGS` = $ARGUMENTS のトリム済み文字列  
**出力:** `CR`（解決済み CR 番号）、`REST_ARGS`（CR 以外の残引数）  
失敗時はエラーを報告して停止する。

`xddp.config.md` をcwdから上位に向かって探し `WORKSPACE_ROOT` を確定する。
見つからない場合はエラーを報告して停止。
`XDDP_DIR`（デフォルト: `xddp`）と `CR_PREFIX`（デフォルト: `CR`）を取得する。

### ステップ1: 引数から CR を特定

`RAW_ARGS` の第1トークンを `FIRST_ARG` とする。

- `FIRST_ARG` が `{CR_PREFIX}-` で始まる
  → `CR = FIRST_ARG`、`REST_ARGS` = 残トークン。解決完了。
- `FIRST_ARG` が空、または `{CR_PREFIX}-` で始まらない
  → `REST_ARGS = RAW_ARGS`（全トークンを二次引数として扱う）。ステップ2へ。

> **二次引数を持つスキルの例:**
> - `xddp.review`: `REST_ARGS` の第1トークンを `DOCUMENT_TYPE` として取得する
> - `xddp.revise`: `REST_ARGS` の第1トークンを `DOC_TYPE` として取得する
> - `xddp.excel2md`: `REST_ARGS` の第1トークンを `EXCEL_PATH` として取得する
> - `xddp.04.specout`: `REST_ARGS` の残トークンを `ENTRY_POINTS` として取得する

### ステップ2: 自動検出

`{WORKSPACE_ROOT}/{XDDP_DIR}/` 直下のディレクトリのうち、
名前が `{CR_PREFIX}-` で始まるものを CR 候補として列挙する
（ファイル・隠しフォルダ・`latest-specs` 等の予約名は名前のフィルタで自然に除外される）。

- **0件** → `"CRフォルダが見つかりません。{WORKSPACE_ROOT}/{XDDP_DIR}/ に CR フォルダを作成するか、CR番号を引数に指定してください。"` と報告して停止。
- **1件** → `CR = そのディレクトリ名`。`"CR を自動検出しました: {CR}"` と報告して続行。
- **複数件** → 各ディレクトリの `progress.md` を読み、🔄・👀・🔁 のいずれかを持つステップがある CR を「進行中」と判定する:
  - 進行中が **1件のみ** → `CR = そのディレクトリ名`。`"CR を自動検出しました: {CR}"` と報告して続行。
  - 進行中が **0件または複数件** → 候補一覧を表示し、`"CR番号を引数に指定してください"` と報告して停止。
