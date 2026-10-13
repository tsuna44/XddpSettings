# Ripple Engine Check

> xddp-common の共通プロシージャ。波紋調査を行うスキル（xddp-04-specout・xddp-investigate・xddp-05-arch）から apply される。

## Ripple Engine Check

状態ファイルのある波紋調査の判定エンジンを、この環境で使えるかと照合する。状態を書き換える処理（`extend`・波ループ）の
直前に、調査ごとに適用する。結果 `ENGINE_CHECK`（`ok` / `switched` / `blocked`）を返し、調査の扱いは呼び出し元が決める。

**Input:** `CR`, `CR_PATH`, `repo`, `run`, `RUN_DIR`（`{CR_PATH}/04_specout/{repo}/ripple/{run}`）,
`STATE_SLICE_ENGINE`（`status --brief` の `slice_engine`）, `PROBE_ENGINE`（"## Ripple Engine Setup" の返り値）,
`RERUN_COMMAND`（この調査を続けるために人が再実行するコマンド）, `TODAY`

**Output:** `ENGINE_CHECK`, `SWITCHED_WAVE`（`switched` のときだけ。規則判定に切り替えた波）

**Process:**
- 照合が不要な場合（`STATE_SLICE_ENGINE` が `rule`、または `PROBE_ENGINE` が `slice`）: `ENGINE_CHECK` = `ok` とする。
  state が `rule` なら、環境に tree-sitter があっても `rule` のまま続ける。
- `STATE_SLICE_ENGINE` が `slice` で `PROBE_ENGINE` が `unavailable` の場合（`SPECOUT_SLICE_PYTHON_BIN` の Python で
  tree-sitter を import できない場合）、下記「### 提示文」を人へ示し、回答を待つ:
  - 2 を選んだ場合: Run via Bash:
    `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py switch-engine --path {RUN_DIR}/work/bfs-state.json --to rule --today {TODAY}`
    （If it errors: display stderr and stop.）`ENGINE_CHECK` = `switched`、`SWITCHED_WAVE` = stdout の `wave` とする。
  - 1・3 を選んだ場合（または回答が無い場合）: state を変えず、`ENGINE_CHECK` = `blocked` とする。

### 提示文

> ⚠️ {repo} の波紋調査 `{run}` はスライス判定（tree-sitter）で探索を始めましたが、この環境では tree-sitter を使えません。
> 1. tree-sitter を使える Python を指定して再実行する: `SPECOUT_SLICE_PYTHON_BIN` に tree-sitter を入れた Python のパスを
>    設定するか、今の Python に `pip install -r ~/.claude/skills/xddp-04-specout/scripts/requirements-slice.txt` で入れてから、
>    `{RERUN_COMMAND}` を再実行する（探索の途中から、スライス判定のまま続く）。
> 2. この調査の残りの波を規則判定に切り替えて続ける（探索済みの波の結果は残る。以降の波は、グローバル変数の読み手・
>    関数の外のヒットの値を追わず、要約を使った判定と再訪をしない。discovery-log に切り替えが記録される）。
> 3. 調査を取り除き、規則判定で最初から探索する:
>    `specout_bfs.py run-remove --repo-dir {CR_PATH}/04_specout/{repo} --run {run} --today {TODAY}` で調査を取り除き
>    （`ripple/_removed/` に退避されます。クロスリポジトリ伝播の調査なら、伝播の記録も未投入に戻ります）、
>    `SPECOUT_SLICE: off` で `{RERUN_COMMAND}` を再実行する。

他のプロシージャが判定エンジンを使えない（exit 5）ことを人へ伝えるときは、この「### 提示文」を示す。
