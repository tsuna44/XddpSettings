# Ripple Run

> xddp-common の共通プロシージャ。波紋調査を行うスキル（xddp-04-specout・xddp-investigate・xddp-05-arch）から apply される。

## Ripple Run

工程4a の初回以外の波紋調査を作り、または途中から続け、完了したら調査ごとの出力を作って（指定があれば）採用する。
調査は `{CR_PATH}/04_specout/{repo}/ripple/{run}/` に1つずつ独立した状態を持つ（他の調査と訪問済みの集合を共有しない）。
調査の記録 `ripple/runs.json` はスクリプトだけが書く。

**Input:** `CR`, `CR_PATH`, `REPO_RUNS`（repo → 調査のリスト。各要素 {`run`, `origin`, `symbols`（新しい調査のシード。空でよい）,
`meta_file`（新しい調査の `meta.json` のパス。呼び出し元が Write 済み）, `entry_identity`（`resolved` / `name-only`）,
`adopt`（完了したら採用するか）, `adopted_by`, `RERUN_COMMAND`}）, `REPOS_MAP`, `SLICE_PY`, `PROBE_ENGINE`, `EFFECTIVE_SLICE_ENGINE`,
`USE_PROBE_WARNING`（"## Ripple Engine Setup" の返り値）, `TODAY`, 設定（`EXCLUDE_PATTERNS`, `INCLUDE_EXTENSIONS`, `MAX_WAVE_DEPTH`,
`SPECOUT_MAX_FILES_PER_MODULE`, `SPECOUT_BACKEND`, `SPECOUT_BACKEND_OVERRIDES`, `SPECOUT_HIT_FILTER`, `SPECOUT_WAVE_HIT_BUDGET`,
`SPECOUT_LLM_HIT_BUDGET`, `SPECOUT_SLICE_IGNORE_CALLS`, `SPECOUT_SLICE_H_AS`, `SPECOUT_MAX_AFFECTED_FILES`, `SPECOUT_CLASSIFY_CHUNK_SIZE`,
`SPECOUT_CLASSIFY_PARALLEL`, `DOCS`）

**Output:** `DONE`（repo → 完了した調査の名前のリスト）, `FAILED`（repo → [{調査, 理由}]）

以下、`{O}` = `{CR_PATH}/04_specout/{repo}`、`{R}` = `{O}/ripple/{run}`、`PY` = `command -v python3 || command -v python` の結果、
`BFS` = `~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py`。スクリプトが見つからない場合は setup.sh の実行を案内して停止する。

**Process:** repo ごとのリストを先頭から1つずつ取り出し、各 repo の1つずつを並べて次の手順で進める。repo のリストが空になるまで
繰り返す（同じ repo の調査は順に、別の repo の調査は並べて進む）。

1. Run via Bash: `"$PY" "$BFS" run-list --repo-dir {O}` → 当該調査の行（`runs` の `run` が一致する要素）と `state` を得る（exit 非0 は
   stderr を表示して停止する）。
   - 調査が無い場合: `symbols` が空なら `FAILED` に「シンボルが無い」として入れて次の調査へ進む。あれば Run via Bash:
     `"$PY" "$BFS" run-add --repo-dir {O} --run {run} --origin {origin} --today {TODAY} --meta-file {meta_file}`
     （exit 1 は stderr を表示し、`FAILED` に入れて次の調査へ進む）。続けて「初期化」へ。
   - `state` が `not-started`（呼び出し元が先に `run-add` した場合を含む）: シンボルと `entry_identity` を行の `seeds`・`entry_identity`
     から取り、「初期化」へ。
   **初期化:**
   - Run via Bash: `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py probe --out {R}/work/slice-probe.json`
     （If it errors: display stderr, `FAILED` に入れて次の調査へ進む。）
   - `SPECOUT_SLICE_IGNORE_CALLS` の値を Write ツールで `{R}/work/slice-ignore-calls.txt` に1行で書く（値が空なら空のファイル。値の前後の
     空白・引用符はそのまま書く）。
   - Run via Bash:
     ```
     "$PY" "$BFS" init --path {R}/work/bfs-state.json --repo-path {REPOS_MAP[repo]} --discovery-log {R}/discovery-log.md \
       --symbols '{シンボルをカンマ区切り}' --entry-point-symbols '{シンボルをカンマ区切り}' --entry-identity {entry_identity} \
       --today {TODAY} --cr {CR} --repo {repo} \
       --exclude "{EXCLUDE_PATTERNS}" --include-ext "{INCLUDE_EXTENSIONS}" --max-wave {MAX_WAVE_DEPTH} \
       --max-files-per-module {SPECOUT_MAX_FILES_PER_MODULE} \
       --backend {SPECOUT_BACKEND_OVERRIDES.get(repo, SPECOUT_BACKEND)} --hit-filter {SPECOUT_HIT_FILTER} \
       --wave-hit-budget {SPECOUT_WAVE_HIT_BUDGET} --llm-hit-budget {SPECOUT_LLM_HIT_BUDGET} \
       --slice-engine {EFFECTIVE_SLICE_ENGINE} --probe-file {R}/work/slice-probe.json \
       --slice-ignore-calls-file {R}/work/slice-ignore-calls.txt --slice-h-as {SPECOUT_SLICE_H_AS} \
       [--use-probe-warning] [--module-catalog {DOCS}/{repo}/module-catalog.md] [--scope-summary-file {O}/work/_scope-summary.md]
     ```
     `--use-probe-warning` は `USE_PROBE_WARNING` が true の場合のみ、`--module-catalog` はそのファイルがある場合のみ渡す。
     `--scope-summary-file` は `{O}/work/_scope-summary.md` があり、`{CR_PATH}/03_change-requirements/CRS-{CR}.md` より新しい場合だけ渡す
     （古い・無い場合は渡さない。`init` が「要約なし」の警告を discovery-log に残す。古い要約で対象外の判定を誤らないため）。
     `--seed-candidates`・`--unsupported-patterns` は渡さない。exit 非0 は stderr を表示し、`FAILED` に入れて次の調査へ進む。
     → 手順4 へ。
2. `state` が `missing`（ディレクトリが無い、または discovery-log があるのに状態ファイルが無い）: `FAILED` に入れ、次を伝える:
   > {repo} の波紋調査 `{run}` の状態ファイルがありません。`specout_bfs.py run-remove --repo-dir {O} --run {run} --today {TODAY}` で
   > 取り除いてから `{RERUN_COMMAND}` を再実行してください。
3. `state` が `in-progress`・`complete`: Run via Bash: `"$PY" "$BFS" status --path {R}/work/bfs-state.json --brief` で状態を取り、次の順に分ける:
   - `in-progress` → Read `~/.claude/skills/xddp-common/procedures/ripple-engine-check.md`, apply "## Ripple Engine Check" with:
     CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, run: {run}, RUN_DIR: {R}, STATE_SLICE_ENGINE: {slice_engine},
     PROBE_ENGINE: {PROBE_ENGINE}, RERUN_COMMAND: {RERUN_COMMAND}, TODAY: {TODAY}
     （`blocked` は `FAILED` に入れて次の調査へ進む）→ 手順4 へ。
   - `complete` で `MAX_WAVE_DEPTH` が `max_wave_depth` より大きく `truncated_wave_limit_count` > 0 → "## Ripple Engine Check"（上と同じ。
     `blocked` は `FAILED`）→ Run via Bash: `"$PY" "$BFS" extend --path {R}/work/bfs-state.json --max-wave {MAX_WAVE_DEPTH} --today {TODAY}`
     （exit 非0 は stderr を表示し `FAILED`）。**`extend` の stdout の `state`** が `in-progress`（打ち切りを frontier に戻した）なら手順4 へ、
     `complete` のままなら手順5 へ（最初の `status --brief` の値で判定しない）。
   - それ以外の `complete` → 波ループを飛ばして手順5 へ。
4. この周回で手順4 に来た各 repo の調査を `ACTIVE_RUNS`（repo → {run, RUN_DIR: {R}, RERUN_COMMAND}）にして、
   Read `~/.claude/skills/xddp-common/procedures/ripple-wave-loop.md`, apply "## Ripple Wave Loop" with:
     CR: {CR}, CR_PATH: {CR_PATH}, ACTIVE_RUNS: {ACTIVE_RUNS}, REPOS_MAP: {REPOS_MAP}, SLICE_PY: {SLICE_PY}, PROBE_ENGINE: {PROBE_ENGINE},
     EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}, INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS},
     SPECOUT_CLASSIFY_CHUNK_SIZE: {SPECOUT_CLASSIFY_CHUNK_SIZE}, SPECOUT_CLASSIFY_PARALLEL: {SPECOUT_CLASSIFY_PARALLEL},
     SEED_GATE_DONE: false, TODAY: {TODAY}
   `SEED_SUMMARY_FAILED`・`WAVE_FAILED`・`ZERO_SEED` に入った調査は `FAILED` に入れる。`COMPLETED` の調査は手順5 へ。
5. 完了した調査について、`{R}/ripple-digest.md`・`{R}/work/verify-sweep.json` のどちらかが無ければ、
   Read `~/.claude/skills/xddp-common/procedures/ripple-run-outputs.md`, apply "## Ripple Run Outputs" with:
     CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, run: {run}, SPECOUT_MAX_AFFECTED_FILES: {SPECOUT_MAX_AFFECTED_FILES}, ONLY_SUMMARY: false
   （停止した場合は `FAILED` に入れて次の調査へ進む）。
   `adopt` が true なら Run via Bash: `"$PY" "$BFS" run-adopt --repo-dir {O} --run {run} --by {adopted_by} --today {TODAY}`
   （出力を作った後に採用する。exit 非0 は stderr を表示し `FAILED`）。当該調査を `DONE` に入れる。
6. `DONE` に入れた調査ごとに Run via Bash（失敗しても続行し、stderr を表示する）:
   `"$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py history-add --cr-path {CR_PATH} --step 4a --text "波紋調査 {run}（{origin}）/ {repo}: {シンボル}。{採用／未採用}（{TODAY}）"`
