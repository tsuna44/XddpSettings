# Ripple Wave Resume

> xddp-common の共通プロシージャ。人が波紋調査の波の途中の失敗を手で復旧するときに読む手順。
> スキルは "## Ripple Wave Loop" の step a で `wave_write_complete: false` を検出すると自動的に `search` から再開するため、
> 本手順へ自動で振り分ける経路は無い。両者は同じ条件（`wave_write_complete = false` かつ `current_wave > last_completed_wave`）を保つこと。

## Ripple Wave Resume

適用条件: 調査の `bfs-state.json` の `wave_write_complete` = `false` **かつ** `current_wave` > `last_completed_wave`
（＝当該波がまだ一度も正常コミットされていない、通常のクラッシュ再開）

> **`current_wave` <= `last_completed_wave` の場合は本手順を適用しないこと。**
> それは「完了済みの波に `set-state in-progress` で戻ってしまった」状態（または `import` で不整合な checkpoint を取り込んだ状態）であり、
> `search` が fail-loud で停止する（確定済みログを守るための正しい挙動）。`set-state` で完了済みの波へ戻さないこと。
> 戻した場合は `specout_bfs.py run-remove --repo-dir {CR_PATH}/04_specout/{repo} --run {run} --today {TODAY}` で調査を取り除き
> （`ripple/_removed/` に退避されます）、`{RERUN_COMMAND}` を再実行してやり直す。

**Input:** `CR`, `CR_PATH`, `repo`, `run`, `RUN_DIR`（`{CR_PATH}/04_specout/{repo}/ripple/{run}`）, `TODAY`,
`SPECOUT_CLASSIFY_PARALLEL`, `SPECOUT_CLASSIFY_CHUNK_SIZE`, `SPECOUT_SLICE_PYTHON_BIN`, `RERUN_COMMAND`

**Process（チャンク並列分類を前提とした手順）:**
`wave_write_complete` が `false` の波は、**必ず `search` から再開する**。
`search` を飛ばして `merge_classification.py`／`commit-wave` を直接再実行する手順は用いない
（分類区間の計測が中断中の待ち時間で汚染されるため）。

1. `search` を再実行する（`--hits-dir` 使用時は波番号を事前に取得する必要がない。
   スクリプト側が state の `current_wave` から出力パスを組み立てる）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py search --path {RUN_DIR}/work/bfs-state.json --hits-dir {RUN_DIR}/work/waves/ --chunk-size {SPECOUT_CLASSIFY_CHUNK_SIZE}`
   `current_wave` は進まず、line_id・チャンク構成は同一 state・同一コード内容であれば決定的に再生成される。
   stdout の `wave` を `{N}` とし、`hits_file`／`slice_chunk`（スライス用チャンク。常に1件）／`chunks`（LLM 用チャンク一覧。
   0件可）を控え、`HITS_CHUNKS` = [`slice_chunk`] + `chunks`（この順）とする。
   `search` が exit 6 を返した場合（シード要約の取り込みが済んでいない）は、本手順を中断し、`{RERUN_COMMAND}` を再実行するよう案内する
   （"## Ripple Wave Loop" の step a が取り込みと `search` のやり直しを行う）。
   If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
   続けて、スライス用チャンクを**必ず**判定し直す（決定的なので同じ結果になり、古い結果を再利用するかの判断が要らない）。
   Let `SLICE_PY` = `SPECOUT_SLICE_PYTHON_BIN`（空なら `command -v python3 || command -v python` の結果）。Run via Bash:
   `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py classify --path {RUN_DIR}/work/bfs-state.json --hits {slice_chunk} --out {RUN_DIR}/work/waves/wave-{N}-chunk-S-class.json`
   exit 5（判定エンジンが使えない）の場合は、"## Ripple Engine Check" の「### 提示文」（選択肢1〜3）を示して停止する。
   その他の exit 非0 は stderr を表示して停止する。
2. 既存の LLM 用チャンクの classification（`{RUN_DIR}/work/waves/wave-{N}-chunk-{K}-class.json`）は、
   **line_id 集合が一致することを条件にそのまま再利用**してよい（LLM 用チャンクが0件なら classifier の再分類は不要）。一致判定の主体は
   `merge_classification.py`（決定的処理）であり、人が目視照合する必要はない。**ただし中断中に対象コードを変更した場合は再利用してはならない**
   （line_id は位置カウンタでありコード変更後もヒット総数が同じなら line_id 集合は一致したまま各 id が別の行を指しうる。この場合は既存
   チャンクファイルを全て削除し、classifier による再分類からやり直す）。
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/merge_classification.py --hits {RUN_DIR}/work/waves/wave-{N}-hits.json --hits-chunks {HITS_CHUNKS} --chunks {wave-{N}-chunk-S-class.json を先頭に、LLM 用の wave-{N}-chunk-{K}-class.json を K の昇順で、HITS_CHUNKS と同じ順に並べる（{RUN_DIR}/work/waves/ 配下。欠落分も期待パスを並べてよい）} --out {RUN_DIR}/work/waves/wave-{N}-class.json --unsupported-out {RUN_DIR}/work/waves/wave-{N}-unsupported.json`
   exit 非0（欠落チャンク・stale チャンク・line_id 不一致）の場合、stderr が再投入すべき `chunk_id`／期待パスの一覧を示す。
   該当チャンクのみ classifier サブエージェント（`agents/xddp-specout-classifier-agent.md` の Inputs 節を参照）で再分類してから本手順を
   再実行する。成功時、stdout の `min_chunk_mtime` を保持する（非 `null` なら手順3 へ `--chunk-mtime-min` として渡す。チャンクを1件でも
   再利用した波はこれにより `classify_wall_ms_reused: true` として計測の集計対象から自動的に除外される）。
   If the script is not found: tell the user to run `setup.sh` and stop.
3. 以下を実行する（`--batch-count` は計測専用の観測値であり手動復旧時の正確な値は追跡していないため `1` を渡す。correctness には影響しない）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py commit-wave --path {RUN_DIR}/work/bfs-state.json --hits {RUN_DIR}/work/waves/wave-{N}-hits.json --classification {RUN_DIR}/work/waves/wave-{N}-class.json --unsupported-patterns {RUN_DIR}/work/waves/wave-{N}-unsupported.json --chunk-count {当該波の LLM 用チャンクの数（0 可）} --batch-count 1 --parallelism {SPECOUT_CLASSIFY_PARALLEL} [--chunk-mtime-min {手順2 で得た値。非 null の場合のみ渡す}] --today {TODAY}`
   discovery-log.md の書きかけ Wave セクションはスクリプトが自動的に切り捨てて再構築するため、二重記録は発生しない。
   If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
4. 調査が `complete` になっていなければ、`{RERUN_COMMAND}` を再実行して波ループを続ける。
