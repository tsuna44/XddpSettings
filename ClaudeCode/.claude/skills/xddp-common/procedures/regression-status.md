# Regression Status

> xddp-common の共通プロシージャ。回帰の範囲を確かめるスキル（xddp-06-design・xddp-09-test・xddp-investigate・xddp-revise・xddp-feedback）から apply される。

## Regression Status

工程6 Step A3 の回帰の範囲（CHD §7 の回帰の行）が、今の CHD §4・採用した波紋調査・設定より古いかを確かめる。

**Input:** `CR`, `CR_PATH`, `REPO`, `MODE`（`params`＝キーだけを返す／`status`＝古さを確かめる。既定 `status`）
**Output:** `REGRESSION_PARAMS_KEY`, `REGRESSION_BACKEND`（MODE に依らず）、`STALE`, `RECORDED`, `FORMAT_ERROR`（MODE = status のとき）

**Process:**
1. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Load Config" → `REPOS_KEYS`・`SPECOUT_BACKEND`・`SPECOUT_BACKEND_OVERRIDES`・`EXCLUDE_PATTERNS`・`INCLUDE_EXTENSIONS`・`SPECOUT_HIT_FILTER`・`SPECOUT_SLICE_H_AS`。
   `CR_PROFILE` は CR 単位の値（`xddp-common/SKILL.md` の「### Step 1.X: Resolve CR Profile」と同じ解決。`{CR_PATH}/progress.md` の `**CRプロファイル：**` 行があればその値）を使う。呼び出し元の渡し方に依存しない（記録と比較で値が食い違わないように）。
2. `REGRESSION_BACKEND` = `SPECOUT_BACKEND_OVERRIDES[REPO]` があればその値、無ければ `SPECOUT_BACKEND`。
   `REGRESSION_PARAMS_KEY` = `{CR_PROFILE}|{REGRESSION_BACKEND}|{EXCLUDE_PATTERNS}|{INCLUDE_EXTENSIONS}|{SPECOUT_HIT_FILTER}|{SPECOUT_SLICE_H_AS}`。MODE = params なら返す。
3. Run via Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-06-design/scripts/chd_regression.py status --design-dir {CR_PATH}/06_design --specout-dir {CR_PATH}/04_specout --repos {REPOS_KEYS をカンマ区切り} --repo {REPO} --cr {CR} --params-key '{REGRESSION_PARAMS_KEY}' --recorded {CR_PATH}/06_design/{REPO}/work/regression/regression-inputs.json`
   → `STALE` = `stale`, `RECORDED` = `recorded`（入力の記録が無ければ `stale: false`・`recorded: false`）, `FORMAT_ERROR` = 空文字列。
   exit 1（関係する repo の §4 の書式の誤り）なら `STALE` = true, `RECORDED` = true, `FORMAT_ERROR` = stderr とする。
