# xddp-04-specout Recovery Procedures

> このファイルは xddp-04-specout 専用の low-frequency リカバリ手順。SKILL.md 本体の主経路から分離し、
> 該当分岐が成立したときのみ Read される。他スキルから参照しないこと
> （xddp-common とは異なり specout 専用ロジックのため）。
>
> - `## Re-discover Processing`:
>   `xddp-04-specout/SKILL.md` の Step A（bfs-state.json 状態テーブル）および
>   同 SKILL.md の各 apply 呼び出しが参照する。
> - `## Wave 途中失敗からの再開（経路統一）`: **SKILL.md の状態テーブルには `wave_write_complete` の
>   行がなく、この節へ振り分ける自動経路は存在しない。人が直接読む手順である。**
>   SKILL 自身は波ループ（`search` → 並列 classifier 起動 → `merge_classification.py` → `commit-wave`）の
>   step a で `wave_write_complete: false` を検出すると自動的に `search` から再開する。
>   本節は SKILL 実行を介さずに人が手動で復旧する場合の手順であり、
>   両者は同じ条件（`wave_write_complete = false` かつ `current_wave > last_completed_wave`）を保つこと。
> - `## Count Mismatch Handling`: `xddp-04-specout/SKILL.md` の Step A（件数一致検証ブロック、
>   配線箇所1・2 いずれも）が参照する。
> - `## Document Phase Recovery`: `xddp-04-specout/SKILL.md` の Step A-Document（手順1〜7）の途中で止まった
>   場合の再開手順。同 SKILL.md の「## Step A-Document」から参照される。

## Re-discover Processing

> **`complete` 状態から追加探索する場合は必ず `re-discover` を使うこと。**
> `set-state in-progress` は `current_wave` を進めないため、
> 続く `search` が完了済みの波番号のまま走り、`commit-wave` が確定済みの
> `## Wave {N}` セクションを切り捨てる。`re-discover` は `current_wave` を
> `last_completed_wave + 1` へ進めるため、この問題は起きない。
>
> **既に `set-state in-progress` で再開してしまった場合の復旧手順**
> （`current_wave` <= `last_completed_wave` かつ `wave_write_complete = false` の状態。
> 「## Wave 途中失敗からの再開（経路統一）」からはこちらへ誘導される）:
> `search` は fail-loud で停止するためデータは壊れない。以下で復旧する。
>
> 1. `specout_bfs.py status --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json` を実行し、
>    **`frontier` に残っているシンボルを控える**（手順3 で必要になる）。
>    `status` は state 全体を1行の JSON で出力し `visited`・`classified_locations`・
>    `confirmed_files` を含むため、実 CR では frontier が埋もれる。次のように抽出するとよい:
>    `… status --path {…}/bfs-state.json | python3 -c "import json,sys; print(json.load(sys.stdin)['frontier'])"`
> 2. `specout_bfs.py set-state --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --state complete`
>    （`re-discover` は `state == complete` でしか実行できないため、まず戻す）
> 3. `specout_bfs.py re-discover --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --symbols {手順1 の残存シンボル ＋ 追加シンボル} --entry-point-symbols {追加シンボルのみ} --today {TODAY}`
>    （`current_wave` が `last_completed_wave + 1` へ進み、以降は通常の BFS ループで再開できる。
>    `--entry-point-symbols` には**人が追加したシンボルだけ**を渡す。手順1 の残存シンボルは
>    伝播由来であり人の指定ではないため含めない。省略した場合は由来テーブルが更新されず、
>    未ヒット検出の対象も前回の投入シンボルのままになる）
>
> **手順1 が必要な理由:** `re-discover` は frontier を `--symbols` の内容で**置換する**
> （`merge-frontier` の追記とは異なる）。この状態では当該波がコミットできていないため
> frontier は未消費のまま残っており、`--symbols` に追加シンボルだけを渡すと**残存分が黙って失われる**。
>
> **CRS 改訂後の `scope_summary` 陳腐化に関する注意:**
> `re-discover` は `bfs-state.json` の `scope_summary`（classifier の `out-of-scope-discard` 判定に
> 使う変更スコープ要約。LLM 分類に回るヒット＝C / C++ / Python 以外の言語のヒットだけに使う。`init` 時に一度だけ保存され以降は不変）を更新しない。`init` 実行後に
> CRS 本文が `xddp-revise`／`xddp-feedback` で改訂され、対象スコープが**拡大**している場合、
> `re-discover` 実行前にその有無を確認すること。拡大していた場合は `re-discover` を使わず、
> `init` からやり直す（またはやむを得ず `re-discover` を使う場合は `bfs-state.json` の
> `scope_summary` を手動編集して追記する）こと。確認を怠ると、新たに in-scope になったヒットが
> 古い（狭い）`scope_summary` に基づき誤って `out-of-scope-discard` される可能性がある
> （`xddp-specout-classifier-agent.md` の `out-of-scope-discard` 判定ルールにある保守的フォールバックにより
> discard 自体は最終手段として避けられるが、判定精度は古い scope_summary の分だけ低下する）。

適用条件: bfs-state.json 状態 = `complete` かつ `RE_DISCOVER = true`、または `xddp-04-specout/SKILL.md`
「## Step A-cross-propagate」からの呼び出し（`RE_DISCOVER` を参照せず、呼び出し元が `complete` を確認済み）

**Input:** `CR_PATH`, `repo`, `ENTRY_POINTS`（呼び出し元が当該 `repo` 向けに振り分け済みの集合）, `TODAY`,
`ORIGIN_LABEL`（任意。history に記録する投入シンボルの由来ラベル。未指定時は `追加エントリポイント`）

**Process:**
1. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py re-discover --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --symbols {ENTRY_POINTS をカンマ区切りで展開} --entry-point-symbols {ENTRY_POINTS をカンマ区切りで展開} --today {TODAY}`
   このコマンドが、状態=in-progress・Frontier=ENTRY_POINTS・現在Wave番号=最終完了Wave+1・
   探索の起点の波=最終完了Wave+1（波数上限はこの波から数え直す）・Wave書き込み完了=true での状態上書きと、
   discovery-log.md 末尾への `[re-discover] セッション開始` マーカー追記をすべて行う（Visited セットは引き継がれる。
   判定エンジンが slice の場合は、投入したシンボルに「シード要約の取り込み待ち」の印を付ける）。
   If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
2. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py history-add --cr-path {CR_PATH} --step 4a --text "re-discover 実施（{TODAY}）{ORIGIN_LABEL}: {ENTRY_POINTS}"`
   （この追記は bfs-state.json 状態 = complete の場合のみ実施する。状態なし・in-progress の場合は
   実施しない。設計根拠（`note-add` ではなく `history-add` を使う理由）: docs/adr/ADR-0004-history-add-vs-note-add.md）
3. SKILL 側の波ループを通常通り開始する（状態が `in-progress` のため Step A-Prelim・`discovery-setup`・Step A-Seed はスキップされ、
   次波から BFS を継続する。判定エンジンが slice の場合は、波ループ a の `search` が exit 6 を返し、SKILL.md の
   「### シード要約の取り込み」を適用してから検索する）。

## Wave 途中失敗からの再開（経路統一）

適用条件: bfs-state.json の `wave_write_complete` = `false` **かつ** `current_wave` > `last_completed_wave`
（＝当該波がまだ一度も正常コミットされていない、通常のクラッシュ再開）

> **`current_wave` <= `last_completed_wave` の場合は本セクションを適用しないこと。**
> それは「完了済みの波に `set-state in-progress` で戻ってしまった」状態
> （または `import` で不整合な checkpoint を取り込んだ状態）であり、
> `search` が fail-loud で停止する（確定済みログを守るための正しい挙動）。
> 復旧は「## Re-discover Processing」冒頭の3ステップ手順に従うこと。

**Input:** `CR`, `CR_PATH`, `repo`, `TODAY`, `SPECOUT_CLASSIFY_PARALLEL`, `SPECOUT_CLASSIFY_CHUNK_SIZE`, `SPECOUT_SLICE_PYTHON_BIN`

**Process（チャンク並列分類を前提とした手順）:**
`wave_write_complete` が `false` の波は、**必ず `search` から再開する**。
`search` を飛ばして `merge_classification.py`／`commit-wave` を直接再実行する手順は用いない
（分類区間の計測が中断中の待ち時間で汚染されるため）。

1. `search` を再実行する（`--hits-dir` 使用時は波番号を事前に取得する必要がない。
   スクリプト側が state の `current_wave` から出力パスを組み立てる）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py search --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --hits-dir {CR_PATH}/04_specout/{repo}/work/waves/ --chunk-size {SPECOUT_CLASSIFY_CHUNK_SIZE}`
   `current_wave` は進まず、line_id・チャンク構成は同一 state・同一コード内容であれば決定的に再生成される。
   stdout の `wave` を `{N}` とし、`hits_file`／`slice_chunk`（スライス用チャンク。常に1件）／`chunks`（LLM 用チャンク一覧。
   0件可）を控え、`HITS_CHUNKS` = [`slice_chunk`] + `chunks`（この順）とする。
   `search` が exit 6 を返した場合（中断中に `--re-discover` でシンボルを加えた等で、シード要約の取り込みが済んでいない）は、
   本手順を中断し、`/xddp-04-specout {CR}` を再実行するよう案内する（波ループ a が取り込みと `search` のやり直しを行う）。
   If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
   続けて、スライス用チャンクを**必ず**判定し直す（決定的なので同じ結果になり、古い結果を再利用するかの判断が要らない）。
   Let `SLICE_PY` = `SPECOUT_SLICE_PYTHON_BIN`（空なら `command -v python3 || command -v python` の結果）。Run via Bash:
   `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py classify --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --hits {slice_chunk} --out {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-chunk-S-class.json`
   exit 5（判定エンジンが使えない）の場合は、SKILL.md の「### 判定エンジンの照合」の提示文（選択肢1〜3）を示して停止する。
   その他の exit 非0 は stderr を表示して停止する。
2. 既存の LLM 用チャンクの classification（`{CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-chunk-{K}-class.json`）は、
   **line_id 集合が一致することを条件にそのまま再利用**してよい（LLM 用チャンクが0件なら classifier の再分類は不要）。一致判定の主体は `merge_classification.py`（決定的処理）であり、
   人が目視照合する必要はない。**ただし中断中に対象コードを変更した場合は再利用してはならない**
   （line_id は位置カウンタでありコード変更後もヒット総数が同じなら line_id 集合は一致したまま
   各 id が別の行を指しうる。この場合は既存チャンクファイルを全て削除し、classifier による
   再分類からやり直す）。
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/merge_classification.py --hits {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-hits.json --hits-chunks {HITS_CHUNKS} --chunks {wave-{N}-chunk-S-class.json を先頭に、LLM 用の wave-{N}-chunk-{K}-class.json を K の昇順で、HITS_CHUNKS と同じ順に並べる（{CR_PATH}/04_specout/{repo}/work/waves/ 配下。欠落分も期待パスを並べてよい）} --out {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-class.json --unsupported-out {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-unsupported.json`
   exit 非0（欠落チャンク・stale チャンク・line_id 不一致）の場合、stderr が再投入すべき
   `chunk_id`／期待パスの一覧を示す。該当チャンクのみ classifier サブエージェント
   （`agents/xddp-specout-classifier-agent.md` の Inputs 節を参照）で再分類してから本手順を再実行する。
   成功時、stdout の `min_chunk_mtime` を保持する（非 `null` なら手順3 へ `--chunk-mtime-min` として渡す。
   チャンクを1件でも再利用した波はこれにより `classify_wall_ms_reused: true` として計測の集計対象から
   自動的に除外される）。
   If the script is not found: tell the user to run `setup.sh` and stop.
3. 以下を実行する（`--batch-count` は計測専用の観測値であり手動復旧時の正確な値は追跡していないため
   `1` を渡す。correctness には影響しない）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py commit-wave --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --hits {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-hits.json --classification {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-class.json --unsupported-patterns {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-unsupported.json --chunk-count {当該波の LLM 用チャンクの数（0 可）} --batch-count 1 --parallelism {SPECOUT_CLASSIFY_PARALLEL} [--chunk-mtime-min {手順2 で得た値。非 null の場合のみ渡す}] --today {TODAY}`
   discovery-log.md の書きかけ Wave セクションはスクリプトが自動的に切り捨てて再構築するため、
   二重記録は発生しない。
   If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.

## Count Mismatch Handling

適用条件: `bfs-state.json` の `wave_write_complete` = `true` かつ
`specout_verify_counts.py --wave all --strict` が exit 3（件数不一致）で終了した場合
（exit 1＝検証の実行エラー・exit 2＝使用法エラー／スクリプト未デプロイ の場合は本セクションを適用しない）

**Input:** `CR`, `CR_PATH`, `repo`, `MISMATCH_WAVES`

**Process:**

> **前提の再確認:** `wave_write_complete` が `false` の場合は本セクションを適用してはならない。
> その状態の不一致は「commit-wave 途中失敗による書きかけ」であり、
> 正しい復旧は「## Wave 途中失敗からの再開（経路統一）」（`search` から再開）である。
> 呼び出し元（SKILL.md Step A）が前提ガードで振り分けるが、本セクションを直接適用する場合も
> 必ず `wave_write_complete` を確認すること。

不一致は「参照解決が返した生ヒット数」と「discovery-log に記録された行数＋除外数」が
合わないこと、すなわち **調査結果の一部がログに残っていない**ことを意味する。
確定影響ファイルの取りこぼしにつながるため、そのまま次フェーズへ進んではならない。

1. 人に次を提示する:
   > ⚠️ 工程4a の件数一致検証で不一致が検出されました（repo: {repo} / 波: {MISMATCH_WAVES}）。
   > discovery-log.md の記録が生ヒット数と一致しません。調査結果の一部が記録されていない可能性があります。
   >
   > - A: 当該 repo の Discovery をやり直す
   > - B: 不一致を承知のうえで続行する（判断を progress.md へ記録します）

2. A が選ばれた場合: `{CR_PATH}/04_specout/{repo}/` を退避・削除したうえで
   `/xddp-04-specout {CR}` を再実行するよう案内し、停止する。
3. B が選ばれた場合: Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py history-add --cr-path {CR_PATH} --step 4a --text "⚠️ 件数一致検証で不一致（repo: {repo} / 波: {MISMATCH_WAVES}）。人の判断により続行。"`
   そのうえで呼び出し元へ戻り、通常のフローを継続する。

## Document Phase Recovery

適用条件: `xddp-04-specout/SKILL.md`「## Step A-Document」の手順1〜7 のいずれかの途中で止まった repo を再開する場合
（`/xddp-04-specout {CR}` の再実行で Step A-Document が先頭から走る。Discovery が `complete` の repo は波ループを再実行しない）。

**Input:** `CR`, `CR_PATH`, `repo`, `TODAY`

**Process:**

- 手順1（`doc-targets --auto-assign`）・手順2（`assemble-spo --layout-only`）・手順3（`funcmap-counts`・`doc-digest`）・
  手順5（`assemble-spo`）は再実行すると同じ結果を作る（冪等）。先頭から再実行してよい。
  既に `work/module-assignments.json` に書かれた組は変わらない。
- 手順4（モジュールごとの `DOC_MODE: module` 起動）の途中で止まった場合: 手順3 まで再実行したうえで、
  **`OUTPUT_FILE`（`{CR_PATH}/04_specout/{repo}/modules/{モジュール名}-spo.md`、サブディレクトリ分割なら
  `modules/{モジュール名}/` 配下。統合パスは `work/module-drafts/{モジュール名}.md`）が存在しないか、
  `work/digest/ledger-rows/{モジュール名}.md`・`work/digest/observation-rows/{モジュール名}.md` が揃っていない
  モジュールだけ** document agent（`DOC_MODE: module`）を再起動し、手順5 から続ける。揃っているモジュールは再起動しない。
- 手順6（`DOC_MODE: summary` 起動）で止まった場合: 手順5 の `assemble-spo` を再実行する（スクリプトが書く欄は同じ内容になり、
  LLM が書く欄は書かれていれば変えない）。続けて LLM が書く欄（§2・§3・§4 の集約・§5.0 の「確認の観点」・§5.3・§5.4・§5.6・§5.7・§7）
  が空のままであることを確認し、`DOC_MODE: summary` を再起動する。
- 手順7（`verify-sweep`）:
  - exit 7（未記録ヒットあり）: 人の判断を待つ。`{CR_PATH}/04_specout/{repo}/discovery-log.md` の「検証スイープ結果」を確認し、
    追加ドキュメント化するか、影響軽微として根拠を記録して承認する（SKILL.md の手順7 の文面）。
  - exit 3（件数不一致）は `verify-sweep` の終了コードではない。Step A の件数一致検証が返した場合は
    「## Count Mismatch Handling」へ。
  - exit 1: stderr を表示して停止する。原因の解消後に `/xddp-04-specout {CR}` を再実行する。
