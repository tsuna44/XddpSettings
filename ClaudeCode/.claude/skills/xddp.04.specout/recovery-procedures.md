# xddp.04.specout Recovery Procedures

> このファイルは xddp.04.specout 専用の low-frequency リカバリ手順。SKILL.md 本体の主経路から分離し、
> 該当分岐が成立したときのみ Read される。他スキルから参照しないこと
> （xddp.common とは異なり specout 専用ロジックのため）。
>
> - `## Re-discover Processing`・`## Paused-at-limit Handling`・`## Paused-at-limit-2nd Handling`:
>   `xddp.04.specout/SKILL.md` の Step A（bfs-state.json 状態テーブル）および
>   同 SKILL.md の各 apply 呼び出しが参照する。
> - `## Wave 途中失敗からの再開（経路統一）`: **SKILL.md の状態テーブルには `wave_write_complete` の
>   行がなく、この節へ振り分ける自動経路は存在しない。人が直接読む手順である。**
>   PLAN-20260806 Phase 3 Stage 2 で波ループの実行主体が `xddp.04.specout/SKILL.md`「## Step A」の
>   波ループ（`search` → 並列 classifier 起動 → `merge_classification.py` → `commit-wave`）へ移設された
>   ため、SKILL 自身が波ループの step a で `wave_write_complete: false` を検出すると自動的に
>   `search` から再開する。本節は SKILL 実行を介さずに人が手動で復旧する場合の手順であり、
>   両者は同じ条件（`wave_write_complete = false` かつ `current_wave > last_completed_wave`）を保つこと。
> - `## Count Mismatch Handling`: `xddp.04.specout/SKILL.md` の Step A（件数一致検証ブロック、
>   配線箇所1・2 いずれも）が参照する。

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
> 1. `specout_bfs.py status --path {CR_PATH}/04_specout/{repo}/bfs-state.json` を実行し、
>    **`frontier` に残っているシンボルを控える**（手順3 で必要になる）。
>    `status` は state 全体を1行の JSON で出力し `visited`・`classified_locations`・
>    `confirmed_files` を含むため、実 CR では frontier が埋もれる。次のように抽出するとよい:
>    `… status --path {…}/bfs-state.json | python3 -c "import json,sys; print(json.load(sys.stdin)['frontier'])"`
> 2. `specout_bfs.py set-state --path {CR_PATH}/04_specout/{repo}/bfs-state.json --state complete`
>    （`re-discover` は `state == complete` でしか実行できないため、まず戻す）
> 3. `specout_bfs.py re-discover --path {CR_PATH}/04_specout/{repo}/bfs-state.json --symbols {手順1 の残存シンボル ＋ 追加シンボル} --today {TODAY}`
>    （`current_wave` が `last_completed_wave + 1` へ進み、以降は通常の BFS ループで再開できる）
>
> **手順1 が必要な理由:** `re-discover` は frontier を `--symbols` の内容で**置換する**
> （`merge-frontier` の追記とは異なる）。この状態では当該波がコミットできていないため
> frontier は未消費のまま残っており、`--symbols` に追加シンボルだけを渡すと**残存分が黙って失われる**。
>
> **CRS 改訂後の `scope_summary` 陳腐化に関する注意（PLAN-20260829-specout-classifier-scope-summary）:**
> `re-discover` は `bfs-state.json` の `scope_summary`（classifier の `out-of-scope-discard` 判定に
> 使う変更スコープ要約。`init` 時に一度だけ保存され以降は不変）を更新しない。`init` 実行後に
> CRS 本文が `xddp.revise`／`xddp.feedback` で改訂され、対象スコープが**拡大**している場合、
> `re-discover` 実行前にその有無を確認すること。拡大していた場合は `re-discover` を使わず、
> `init` からやり直す（またはやむを得ず `re-discover` を使う場合は `bfs-state.json` の
> `scope_summary` を手動編集して追記する）こと。確認を怠ると、新たに in-scope になったヒットが
> 古い（狭い）`scope_summary` に基づき誤って `out-of-scope-discard` される可能性がある
> （`xddp-specout-classifier-agent.md` の `out-of-scope-discard` 判定ルールにある保守的フォールバックにより
> discard 自体は最終手段として避けられるが、判定精度は古い scope_summary の分だけ低下する）。

適用条件: bfs-state.json 状態 = `complete` かつ `RE_DISCOVER = true`

**Input:** `CR_PATH`, `repo`, `ENTRY_POINTS`, `TODAY`

**Process:**
1. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py re-discover --path {CR_PATH}/04_specout/{repo}/bfs-state.json --symbols {ENTRY_POINTS をカンマ区切りで展開} --today {TODAY}`
   このコマンドが、状態=in-progress・Frontier=ENTRY_POINTS・現在Wave番号=最終完了Wave+1・
   Wave書き込み完了=true・上限到達回数=0 での状態上書きと、discovery-log.md 末尾への
   `[re-discover] セッション開始` マーカー追記をすべて行う（Visited セットは引き継がれる）。
   If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
2. Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py history-add --cr-path {CR_PATH} --step 4a --text "re-discover 実施（{TODAY}）追加エントリポイント: {ENTRY_POINTS}"`
   （この追記は bfs-state.json 状態 = complete の場合のみ実施する。状態なし・in-progress・paused の場合は
   実施しない。設計根拠（`note-add` ではなく `history-add` を使う理由）: docs/adr/ADR-0004-history-add-vs-note-add.md）
3. SKILL 側の波ループを通常通り開始する（状態が `in-progress` のため `discovery-setup` はスキップされ、
   次波から BFS を継続する）。

## Paused-at-limit Handling

適用条件: bfs-state.json 状態 = `paused-at-limit`

**Input:** `CR`, `CR_PATH`, `repo`, `MAX_WAVE_DEPTH`

**Process:**
状態が "paused-at-limit" の場合、人に対して以下を提示する:

> ⚠️ {repo} の Discovery が探索上限（{MAX_WAVE_DEPTH} 波）に達して一時停止しています。
> `{CR_PATH}/04_specout/{repo}/discovery-log.md` の残存フロンティア一覧を確認して、
> 以下 A/B/C のいずれかを選択してください:
>
> **A（フロンティア剪定・BFS 再開）:**
>   削除したいシンボルと削除根拠を指定してください（例: 「A: log, err / 高ノイズシンボルのため」）。
>   指定いただいた内容で以下を実行し、Frontier からの削除と discovery-log.md への根拠記録、
>   状態フィールドの `in-progress` への書き戻しを行います:
>   `specout_bfs.py prune --path {CR_PATH}/04_specout/{repo}/bfs-state.json --remove {削除シンボル} --reason "{削除根拠}"`
>   その後 `/xddp.04.specout {CR}` を再実行すると、スキルが自動で波ループを再開します。
>   ※ Frontier の書式: HIGH シンボルは平文、MEDIUM シンボルは `symbol[MEDIUM:filepath]` 形式
>
> **B（モジュール一括記録）:**
>   残存フロンティアのシンボルが属するモジュール全体を `MODULE-LEVEL` として記録して Discovery を完了します。
>   「B を選択」と入力してください。
>
> **C（スコープ外承認）:**
>   残存フロンティアがスコープ外であることを確認した根拠を記録して Discovery を完了します。
>   「C を選択: {根拠}」と入力してください。

選択肢 A が選ばれた場合（削除シンボル・削除根拠が提示された場合）:
  1. Run via Bash:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py prune --path {CR_PATH}/04_specout/{repo}/bfs-state.json --remove {削除シンボルをカンマ区切りで展開} --reason "{削除根拠}"`
     If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
  2. `/xddp.04.specout {CR}` の再実行を案内する（状態は `in-progress` に書き戻されているため、
     再実行時にスキルが自動で波ループを再開する）。

選択肢 B が選ばれた場合:
  Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py finish --path {CR_PATH}/04_specout/{repo}/bfs-state.json --mode complete --today {TODAY}`
  このコマンドが、残存フロンティア（frontier + low_priority_frontier）の各シンボルが所属するモジュールの
  特定、discovery-log.md への「⚠️ 継続パス B」記録、該当モジュール配下の全ファイルの確定ファイル一覧への
  追加（確信度: MODULE-LEVEL）、状態の `complete` への更新をすべて行う。
  If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
  出力 JSON の `unresolved`（モジュールが自動特定できなかったシンボル）が非空の場合は、人に手動確認を促す。

選択肢 C が選ばれた場合:
  Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py finish --path {CR_PATH}/04_specout/{repo}/bfs-state.json --mode out-of-scope --reason "{ユーザーが提示した根拠}" --today {TODAY}`
  このコマンドが discovery-log.md への根拠記録と状態の `complete` への更新を行う。
  If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.

## Paused-at-limit-2nd Handling

適用条件: bfs-state.json 状態 = `paused-at-limit-2nd`

**Input:** `CR_PATH`, `repo`, `TODAY`

**Process:**
2回目以降の上限到達につき、人への確認を挟まず自動でパス B を適用する。Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py finish --path {CR_PATH}/04_specout/{repo}/bfs-state.json --mode complete --today {TODAY}`
（内容は上記「Paused-at-limit Handling」選択肢 B と同一）。
If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.

## Wave 途中失敗からの再開（経路統一）

適用条件: bfs-state.json の `wave_write_complete` = `false` **かつ** `current_wave` > `last_completed_wave`
（＝当該波がまだ一度も正常コミットされていない、通常のクラッシュ再開）

> **`current_wave` <= `last_completed_wave` の場合は本セクションを適用しないこと。**
> それは「完了済みの波に `set-state in-progress` で戻ってしまった」状態
> （または `import` で不整合な checkpoint を取り込んだ状態）であり、
> `search` が fail-loud で停止する（確定済みログを守るための正しい挙動）。
> 復旧は「## Re-discover Processing」冒頭の3ステップ手順に従うこと。

**Input:** `CR_PATH`, `repo`, `TODAY`, `SPECOUT_CLASSIFY_PARALLEL`

**Process（PLAN-20260806 Phase 3 Stage 2: チャンク並列分類を前提とした手順）:**
`wave_write_complete` が `false` の波は、**必ず `search` から再開する**。
`search` を飛ばして `merge_classification.py`／`commit-wave` を直接再実行する手順は用いない
（分類区間の計測が中断中の待ち時間で汚染されるため）。

1. `search` を再実行する（`--hits-dir` 使用時は波番号を事前に取得する必要がない。
   スクリプト側が state の `current_wave` から出力パスを組み立てる）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py search --path {CR_PATH}/04_specout/{repo}/bfs-state.json --hits-dir {CR_PATH}/04_specout/{repo}/ --chunk-size {SPECOUT_CLASSIFY_CHUNK_SIZE}`
   `current_wave` は進まず、line_id・チャンク構成は同一 state・同一コード内容であれば決定的に再生成される。
   stdout の `wave` を `{N}` とし、`hits_file`／`chunks`（ヒットチャンク一覧。以下 `HITS_CHUNKS`）を控える。
   If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
2. 既存のチャンク classification（`wave-{N}-chunk-*-class.json`）は、**line_id 集合が一致することを
   条件にそのまま再利用**してよい。一致判定の主体は `merge_classification.py`（決定的処理）であり、
   人が目視照合する必要はない。**ただし中断中に対象コードを変更した場合は再利用してはならない**
   （line_id は位置カウンタでありコード変更後もヒット総数が同じなら line_id 集合は一致したまま
   各 id が別の行を指しうる。この場合は既存チャンクファイルを全て削除し、classifier による
   再分類からやり直す）。
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/merge_classification.py --hits {CR_PATH}/04_specout/{repo}/wave-{N}-hits.json --hits-chunks {HITS_CHUNKS} --chunks {既存の wave-{N}-chunk-*-class.json（欠落分は未指定でよい）} --out {CR_PATH}/04_specout/{repo}/wave-{N}-class.json --unsupported-out {CR_PATH}/04_specout/{repo}/wave-{N}-unsupported.json`
   exit 非0（欠落チャンク・stale チャンク・line_id 不一致）の場合、stderr が再投入すべき
   `chunk_id`／期待パスの一覧を示す。該当チャンクのみ classifier サブエージェント
   （`agents/xddp-specout-classifier-agent.md` の Inputs 節を参照）で再分類してから本手順を再実行する。
   成功時、stdout の `min_chunk_mtime` を保持する（非 `null` なら手順3 へ `--chunk-mtime-min` として渡す。
   チャンクを1件でも再利用した波はこれにより `classify_wall_ms_reused: true` として計測の集計対象から
   自動的に除外される）。
   If the script is not found: tell the user to run `setup.sh` and stop.
3. 以下を実行する（`--batch-count` は計測専用の観測値であり手動復旧時の正確な値は追跡していないため
   `1` を渡す。correctness には影響しない）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py commit-wave --path {CR_PATH}/04_specout/{repo}/bfs-state.json --hits {CR_PATH}/04_specout/{repo}/wave-{N}-hits.json --classification {CR_PATH}/04_specout/{repo}/wave-{N}-class.json --unsupported-patterns {CR_PATH}/04_specout/{repo}/wave-{N}-unsupported.json --chunk-count {当該波のチャンク数} --batch-count 1 --parallelism {SPECOUT_CLASSIFY_PARALLEL} [--chunk-mtime-min {手順2 で得た値。非 null の場合のみ渡す}] --today {TODAY}`
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
   `/xddp.04.specout {CR}` を再実行するよう案内し、停止する。
3. B が選ばれた場合: Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py history-add --cr-path {CR_PATH} --step 4a --text "⚠️ 件数一致検証で不一致（repo: {repo} / 波: {MISMATCH_WAVES}）。人の判断により続行。"`
   そのうえで呼び出し元へ戻り、通常のフローを継続する。
