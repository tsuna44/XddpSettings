# Ripple Wave Loop

> xddp-common の共通プロシージャ。波紋調査を行うスキル（xddp-04-specout・xddp-investigate・xddp-05-arch）から apply される。

## Ripple Wave Loop

状態ファイルが `in-progress` の波紋調査の波ループ（`search` → スライス判定・classifier → `merge_classification.py` →
`commit-wave`）を、すべての調査が `complete` になるか失敗で外れるまで回す。1つの repo で同時に回す調査は1つ
（複数の repo の調査は並べて進める）。per-repo progress table・`progress.md` は更新しない（結果は返り値で返す）。

**Input:** `CR`, `CR_PATH`, `ACTIVE_RUNS`（repo → {`run`, `RUN_DIR`〔`{CR_PATH}/04_specout/{repo}/ripple/{run}`〕, `RERUN_COMMAND`}。
repo ごとに1つ）, `REPOS_MAP`, `SLICE_PY`, `PROBE_ENGINE`, `EXCLUDE_PATTERNS`, `INCLUDE_EXTENSIONS`,
`SPECOUT_CLASSIFY_CHUNK_SIZE`, `SPECOUT_CLASSIFY_PARALLEL`, `SEED_GATE_DONE`（第0波のシードを人がシード確認で見た調査なら true）,
`SEED_GATE_NOTE`（任意。調査を取り除く案内に続けて伝える文。工程4a の初回の調査で使う）, `TODAY`

**Output:** `COMPLETED`（`complete` になった repo → 調査）, `SEED_SUMMARY_FAILED`（repo → {調査, stderr}）,
`WAVE_FAILED`（repo → {調査, stderr, 失敗した step}）, `ZERO_SEED`（`search` が exit 4 で外れた repo → 調査）

以下、`{R}` は当該 repo の `RUN_DIR`、`{STATE}` は `{R}/work/bfs-state.json`、`{WAVES}` は `{R}/work/waves/`、
`{LOG}` は `{R}/discovery-log.md` を表す。

### シード要約の取り込み（Input: repo）

波ループ a で `search` が終了コード 6（シード要約の取り込みが済んでいない）を返したときだけ適用する
（`init` が判定エンジン `slice` の調査で「取り込み待ち」の印を付け、`search` がそれを検出する）。

Run via Bash:
  `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py seed-summary --path {STATE} --out {R}/work/seed-summaries.json`
  （`--symbols` は渡さない。対象は state の取り込み待ちのシード）
  exit 5 の場合は "## Ripple Engine Check" の「### 提示文」（選択肢1〜3）を示し、当該 repo を取り込みの失敗とする。
  それ以外の exit 非0 は stderr を表示し、当該 repo を取り込みの失敗とする。
stdout の `globals` が空でなければ、Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py merge-frontier --path {STATE} --symbols '{globals をカンマ区切り}' --as-seed-globals --summaries-file {stdout の summaries_file}`
`globals` が空なら、Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py merge-frontier --path {STATE} --symbols '' --summaries-file {stdout の summaries_file}`
  （`--symbols` は空を受け付ける。要約だけを取り込む）
`merge-frontier` が exit 非0 の場合は stderr を表示し、当該 repo を取り込みの失敗とする。

### 調査を取り除く案内

`search` exit 4・一般語のシードの中断で示す文:
> `specout_bfs.py run-remove --repo-dir {CR_PATH}/04_specout/{repo} --run {run} --today {TODAY}` で調査を取り除き
> （`ripple/_removed/` に退避されます。クロスリポジトリ伝播の調査なら、伝播の記録も未投入に戻ります）、`{RERUN_COMMAND}` を再実行してください。
> {`SEED_GATE_NOTE` があれば続けて伝える}

### 波ループ

`ACTIVE` = `ACTIVE_RUNS` の repo の集合。Repeat while `ACTIVE` is not empty（各周回が「1波」に相当する）:

**a. search の実行（repo ごと）**

For each `{repo}` in `ACTIVE`, run via Bash:
```
specout_bfs.py search --path {STATE} --hits-dir {WAVES} --chunk-size {SPECOUT_CLASSIFY_CHUNK_SIZE}
```
（`--hits-dir` はスクリプトが state の `current_wave` から `wave-{N}-hits.json` を組み立てるため、
呼び出し側が波番号を search 実行**前**に知る必要はない。波番号は本コマンドの stdout の `"wave"` キーから取得し、
以降の step b〜d の出力パス組み立てに使う。`wave_write_complete: false` の調査もここから再開する）

- `search` が exit 6 の場合（シード要約の取り込みが済んでいない）: 当該 `{repo}` に「### シード要約の取り込み」を
  適用し、成功したら同じ `search` をもう一度実行する（2回目も exit 6 なら stderr を表示して当該 `{repo}` を
  `ACTIVE` から外す）。取り込みの失敗（exit 5 を含む）と2回目の exit 6 で外した repo は `SEED_SUMMARY_FAILED` に
  入れ、以降の step を行わない。
- 出力 JSON の `complete` が `true` の場合（波数上限に達し、打ち切り記録を残して自動完了した）: 当該 `{repo}` を
  `ACTIVE` から外し、下記「### 波ループ終了時の検証」を当該 repo に対して実行する。
- `search` が exit 4 の場合（投入シンボルが0件）: 当該 `{repo}` を `ACTIVE` から外して `ZERO_SEED` に入れ、次を人へ提示する
  （同じ波の他 repo は step b 以降を続行する）:
  > ⚠️ **{repo} の波紋調査 `{run}` の探索シードが0件のため、波紋調査を開始できません。**
  > {`{LOG}` の `## 投入シンボルの由来` テーブルの転記（「シンボル不明」行を含む）}
  >
  > 具体的な識別子を特定できませんでした。{「### 調査を取り除く案内」}
- `search` がその他の exit 非0 の場合（frontier 空・バックエンド不整合等）: stderr を表示したうえで当該 `{repo}` のみを
  `ACTIVE` から外して `WAVE_FAILED` に入れ、同じ波の他 repo は step b 以降を続行する（当該波は未コミットで state は前波の
  確定状態のままのため、原因を除去すればそのまま再開して安全である）。
- 成功した repo について、stdout の `hits_file`、`slice_chunk`（**スライス用チャンク** `wave-{N}-hits-chunk-S.json`。
  常に1件。C / C++ / Python のヒットを LLM を使わずに判定する）、`chunks`（**LLM 用チャンク** `wave-{N}-hits-chunk-{K}.json` の
  一覧。関数の範囲を決定的に取れない言語のヒット。0件可）を保持する。
  **`HITS_CHUNKS[{repo}]`** = [`slice_chunk`] + `chunks`（この順。step c の `--hits-chunks` の供給元）、
  **`LLM_CHUNKS[{repo}]`** = `chunks`（step b-1 で classifier に渡す。スライス用チャンクを含まない）とする。
  （step c の `--chunks` に渡す classification 側のファイル群＝ `CLASS_CHUNKS[{repo}]` とは別物であり、混同すると
  classification が1件も読まれない）

**a-seed. 投入シードの人への提示（非ブロッキング）**

`SEED_GATE_DONE` が true なら step a の stdout の `"wave"` が `1` 以上、false なら `0` 以上で、次のいずれかを満たす repo について、
**step b へ進む前に**以下を人へ提示する（`SEED_GATE_DONE` が true のとき、Wave 0 のシードはシード確認〔Step A-Seed〕で提示済み）。
提示は通知のみで承認を待たない。
- `zero_hit_symbols` または `zero_after_filter_symbols` が非空（投入したシンボルが当該波でヒットしなかった）
- `noisy_seed_symbols` が非空（投入したシンボルが多数のファイルにヒットした）
- `budget_truncated_seed_symbols` が非空（投入したシンボルが1波の予算を超えたため探索しなかった）

参照するデータの取得元:
- 未ヒット一覧: step a の stdout の `zero_hit_symbols` / `zero_after_filter_symbols`
- ヒット過多一覧: step a の stdout の `noisy_seed_symbols`（各要素は `symbol` と `file_count`）と `all_seeds_noisy`
- 予算で打ち切った一覧: step a の stdout の `budget_truncated_seed_symbols`（各要素は `symbol` と `hits`）と `all_seeds_budget_truncated`
- 由来の内訳: `{LOG}` を Read し `## 投入シンボルの由来` セクションのテーブルを転記する
  （当該セクションが無い場合は転記を省略し、以降の警告のみを提示する）

> 📋 **{repo} の波紋調査 `{run}` の探索シード（Wave {wave}）**
> {`## 投入シンボルの由来` テーブルの転記}
>
> {`zero_hit_symbols` が非空の場合のみ}
> ⚠️ **母体コードに1件もヒットしなかった投入シンボル:** `{zero_hit_symbols をカンマ区切り}`
> 　 識別子の誤字・旧名称である可能性があります。
> {`zero_after_filter_symbols` が非空の場合のみ}
> ⚠️ **生ヒットはあったがフィルタで全件除外された投入シンボル:** `{zero_after_filter_symbols をカンマ区切り}`
> 　 `SPECOUT_HIT_FILTER` の設定と discovery-log.md の「## フィルタ除外一覧」を確認してください。
> {`noisy_seed_symbols` が非空の場合のみ}
> ⚠️ **多数のファイルにヒットした投入シンボル（一般語の疑い）:** `{symbol}`（{file_count} ファイル）, …
> 　 識別子ではない一般語がシードになっている可能性があります。LLM 分類に回るヒットは代表行だけが分類されます。
> {`budget_truncated_seed_symbols` が非空の場合のみ}
> ⚠️ **1波の予算を超えたため探索しなかった投入シンボル:** `{symbol}`（{hits} ヒット）, …
> 　 より具体的なシンボルを `/xddp-investigate {CR} ripple --adopt {シンボル}` で新しい調査として追ってください。
> {`all_seeds_noisy` または `all_seeds_budget_truncated` が `true` の場合のみ}
> 　 **投入シンボルの全件が該当します。この探索は変更対象を特定できていない可能性が高いため、中断を推奨します。**
> 　 中断した場合は、調査を取り除いてやり直してください（一般語のシードで確定したファイルを残さないため）:
> 　 {「### 調査を取り除く案内」}
>
> {`all_seeds_noisy` と `all_seeds_budget_truncated` がいずれも `false` の場合のみ}
> このまま探索を継続します。シードに誤りがある場合はここで中断し、`{LOG}` を確認のうえ
> `/xddp-investigate {CR} ripple --adopt {正しいシンボル}` で新しい調査として追ってください
> （未ヒット一覧は波ごとに別セクションで上書き更新されるため、再 search で重複しません）。

条件に当たらない波、およびいずれの一覧も空の波では提示しない。

**b. 判定（全 ACTIVE）**

**b-0. スライス判定・規則判定（repo ごと。LLM を使わない）**

For each `{repo}` in `ACTIVE`, run via Bash:
  `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py classify --path {STATE} --hits {slice_chunk（step a）} --out {WAVES}wave-{N}-chunk-S-class.json`
（判定エンジンは state の `slice_engine` で決まる。ヒット0件のスライス用チャンクでも実行し、空の classification を書く）
- exit 5（判定エンジンが使えない）: "## Ripple Engine Check" の「### 提示文」（選択肢1〜3）を示し、当該 `{repo}` を `ACTIVE` から外して
  `WAVE_FAILED` に入れる。
- その他の exit 非0: stderr を表示し、当該 `{repo}` を `ACTIVE` から外して `WAVE_FAILED` に入れる（step c の失敗と同じ扱い）。
- 成功: **`CLASS_CHUNKS[{repo}]`** の先頭に `{WAVES}wave-{N}-chunk-S-class.json` を置く。

**b-1. classifier の並列起動（全 ACTIVE の LLM 用チャンクを合算）**

対象は **`LLM_CHUNKS[{repo}]`（スライス用チャンクを含まない）だけ**である（スライス用チャンクを classifier に渡すと、
`OUT_FILE` が b-0 の結果を上書きし、C / C++ / Python のヒットが黙って LLM 分類される）。全 repo の `LLM_CHUNKS` が空なら
classifier を起動せず、step c へ進む。

`LLM_CHUNKS` を repo 単位で連続するように（`ACTIVE` の順に、各 repo の chunk-0 から昇順に）合算した列を作り、その先頭から
`{SPECOUT_CLASSIFY_PARALLEL}` 件ずつバッチへ詰める（ラウンドロビン的に repo を交互に詰めてはならない。実効並列度の事後判定式が
「repo のチャンクがバッチ列上で連続する」ことを前提に成立するため）。

**プロンプトキャッシュ有効化のための設計要件（必須）:** 各 classifier の起動プロンプトは、チャンク固有情報（`CHUNK_FILE`・`OUT_FILE`・
`chunk_id`）を末尾に置き、先頭側（分類ルール・判定手順に関する指示文）を全チャンクでバイト単位に同一に保つこと。兄弟サブエージェント間で
プロンプトキャッシュが共有されるのはプレフィクスがバイト同一の場合のみであり、チャンク固有情報が先頭側に混ざるとキャッシュが
個体ごとに分離し、固定ブートストラップがチャンク数だけ複製される。**波の最初のバッチは、チャンク0を単独で起動してキャッシュ書き込みを
完了させてから残りのチャンクを並列起動する**（またはバッチ内の起動タイミングを2〜3秒ずらす。コールドスタート時の競合窓対策）。

各 classifier には `CHUNK_FILE` として当該チャンクの `LLM_CHUNKS` エントリを、`OUT_FILE` として
`{WAVES}wave-{N}-chunk-{K}-class.json`（`{K}` は `CHUNK_FILE` と同一）を渡す:

Use the **Agent tool** with `subagent_type=xddp-specout-classifier-agent` and pass:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CHUNK_FILE: {WAVES}wave-{N}-hits-chunk-{K}.json
OUT_FILE: {WAVES}wave-{N}-chunk-{K}-class.json
EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}
INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS}
```

classifier が書いた `OUT_FILE` を、`CLASS_CHUNKS[{repo}]` の先頭（b-0 のスライス用）の後に `K` の昇順で加える（step c で使う）。
各バッチの起動直前・完了直後に Bash `date +%s` を取り、`{WAVES}wave-{N}-batches.json` へ以下のスキーマで記録する（repo ごとに書く。
`{N}` は当該 repo の波番号。実効並列度の事後監査用。消費者は人と確認項目のみで、これを読むスクリプトはない）:
```json
[{"batch_index": 0, "chunk_files": ["…-chunk-0-class.json", "…"], "started_at": 1786000000, "ended_at": 1786000042}]
```
このファイルから求めた「当該 repo のチャンクが1件以上含まれていたバッチの数」を、下記 step d の `--batch-count` に渡す
（classifier を起動しなかった repo では `0`）。

**c. merge_classification.py の実行（repo ごと）**

For each `{repo}` in `ACTIVE`, run via Bash（パスは step a の `hits_file` から導出する）:
```
merge_classification.py --hits {hits_file（step a）} \
  --hits-chunks {HITS_CHUNKS[{repo}]} --chunks {CLASS_CHUNKS[{repo}]} \
  --out {WAVES}wave-{N}-class.json \
  --unsupported-out {WAVES}wave-{N}-unsupported.json
```
（`--hits-chunks` には **`HITS_CHUNKS[{repo}]`**（スライス用チャンク＋LLM 用チャンク）を、`--chunks` には
**`CLASS_CHUNKS[{repo}]`**（b-0 の結果＋classifier が書いた `OUT_FILE`）を、同じ順（先頭がスライス用チャンク、続いて
LLM 用チャンクの `K` の昇順）で渡す。`merge_classification.py` は位置で対応させる。
取り違えるとフラグ名が一致するため機械検査では検出されない — 変数名を厳密に区別すること）

- stdout の `min_chunk_mtime` を保持する（非 `null` なら step d へ `--chunk-mtime-min` として渡す）。
- exit 非0（line_id の欠落・重複・未知値・チャンク単位の不一致・欠落チャンク）の場合: stderr を表示したうえで当該 `{repo}` のみを
  `ACTIVE` から外して `WAVE_FAILED` に入れ、同じ波の他 repo は step d まで完了させる。失敗した調査の state は
  `wave_write_complete=false` のまま残るため、"## Ripple Wave Resume" の手順2（欠落・stale チャンクのみを再投入する）に
  そのまま接続できる。

**d. commit-wave の実行（repo ごと）**

For each `{repo}` in `ACTIVE`（step c を通過したもの）, run via Bash:
```
specout_bfs.py commit-wave --path {STATE} \
  --hits {hits_file（step a）} --classification {WAVES}wave-{N}-class.json \
  --unsupported-patterns {WAVES}wave-{N}-unsupported.json \
  --chunk-count {当該 repo の LLM 用チャンクの数（0 可）} --batch-count {step b-1 で求めた実バッチ数（0 可）} \
  --parallelism {SPECOUT_CLASSIFY_PARALLEL} \
  [--chunk-mtime-min {step c で得た値。非 null の場合のみ渡す}] --today {TODAY}
```
- `commit-wave` は per-wave metrics を `{R}/work/metrics.jsonl` へ1行追記する（`--path` と同じディレクトリ）。
  打ち切り記録（1波の予算）・要約の拡大による再訪・シードの直接参照ファイルの記録もここで行う。
- stdout の `state` が `complete` になった repo を `ACTIVE` から外し、下記「### 波ループ終了時の検証」を当該 repo に対して実行する
  （`commit-wave` 成功時は `wave_write_complete` が常に `true` になるため、status の再確認は不要）。
- exit 非0（fail-loud・スキーマ検証エラー等）の場合: stderr を表示したうえで当該 `{repo}` のみを `ACTIVE` から外して `WAVE_FAILED` に
  入れる。失敗した調査の state は `wave_write_complete=false` のまま残るため、step c の失敗と同じ再開手順に接続できる。

**e.** `ACTIVE` が空でなければ a. に戻る（波番号は repo ごとに独立して進む）。

### 波ループ終了時の検証（調査が `complete` になるたび）

Read `~/.claude/skills/xddp-common/procedures/ripple-count-check.md`, apply "## Ripple Count Check" with:
  CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, run: {run}, RUN_DIR: {R}, RERUN_COMMAND: {RERUN_COMMAND}, TODAY: {TODAY},
  WAVE_WRITE_COMPLETE: true
当該 repo → 調査を `COMPLETED` に入れる。

### 波ループ終了後（全 repo が `complete` または失敗で外れた場合）

失敗した調査があれば、次の2つに分けて一覧と直近の stderr を人へ提示する（`ZERO_SEED` は step a で提示済み）:
1. `SEED_SUMMARY_FAILED`（step a のシード要約の取り込みの失敗・exit 5・2回目の exit 6 で外れた調査）: `search` が state を変える前に
   止まっている（`wave_write_complete` は `true` のまま）ため、"## Ripple Wave Resume" は適用しない。exit 5 なら "## Ripple Engine Check" の
   「### 提示文」（選択肢1〜3）を示し、原因を直して `{RERUN_COMMAND}` を再実行するよう案内する（再実行すると `search` が exit 6 を返し、
   取り込みからやり直す）。
2. `WAVE_FAILED`（step a のその他の失敗、step b-0 の `classify` の失敗〔exit 5 を含む。`search` の後なので `wave_write_complete` は
   `false`〕、step c・d の失敗）: `{RERUN_COMMAND}` を再実行するよう案内する（波ループ a が `search` から再開する。人が手で復旧する場合は
   `~/.claude/skills/xddp-common/procedures/ripple-wave-resume.md` の手順）。b-0 の exit 5 なら、先に "## Ripple Engine Check" の
   選択肢1（tree-sitter を使える Python を指定する）で環境を直すことを加える。
