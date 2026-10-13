# Ripple Engine Setup

> xddp-common の共通プロシージャ。波紋調査を行うスキル（xddp-04-specout・xddp-investigate・xddp-05-arch）から apply される。

## Ripple Engine Setup

波紋調査の判定エンジン（スライス判定／規則判定）を決める。`CR_PROFILE` によらない。

**Input:** `SPECOUT_SLICE`, `SPECOUT_SLICE_PYTHON_BIN`

**Output:** `SLICE_PY`, `PROBE_ENGINE`, `EFFECTIVE_SLICE_ENGINE`, `USE_PROBE_WARNING`

**Process:**
1. Let `SLICE_PY` = `SPECOUT_SLICE_PYTHON_BIN`（空なら `command -v python3 || command -v python` の結果）。
2. Run via Bash: `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py probe`
   （ここではファイルに書かない。警告文を `init` に渡すファイルは、調査を始めるとき〔`init` の前〕に調査ごとに
   `{調査のディレクトリ}/work/slice-probe.json` に書く）
   スクリプトが見つからない場合は setup.sh 実行を案内して停止する。`SLICE_PY` が起動できない・exit 非0 の場合は
   stderr を表示し、`SPECOUT_SLICE_PYTHON_BIN` の確認を案内して停止する（設定の誤りを規則判定で黙って隠さない）。
3. Let `PROBE_ENGINE` = stdout の `engine`（`slice` / `unavailable`）。
4. If `SPECOUT_SLICE` = `off`: Let `EFFECTIVE_SLICE_ENGINE` = `rule`, `USE_PROBE_WARNING` = false。
   Else if `PROBE_ENGINE` = `slice`: Let `EFFECTIVE_SLICE_ENGINE` = `slice`, `USE_PROBE_WARNING` = false。
   Else: Let `EFFECTIVE_SLICE_ENGINE` = `rule`, `USE_PROBE_WARNING` = true（警告文は、調査ごとに書く probe の出力ファイルにあり、
   `init` が読む）。

`EFFECTIVE_SLICE_ENGINE` は、状態ファイルを新しく作る調査の `seed-preview` と `init` に渡す。`seed-preview` は候補表の
注記行の案内にこの値を使い、判定エンジンを state に保存するのは `init` である。既に状態ファイルがある調査の判定エンジンは
state の `slice_engine` を正とする（"## Ripple Engine Check"）。
