# xddp.04.specout Recovery Procedures

> このファイルは `xddp.04.specout/SKILL.md` の Step A（bfs-state.json 状態テーブル）が参照する
> low-frequency リカバリ手順（re-discover・paused-at-limit）。SKILL.md 本体の主経路から分離し、
> 該当分岐が成立したときのみ Read される。他スキルから参照しないこと
> （xddp.common とは異なり specout 専用ロジックのため）。

## Re-discover Processing

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
   実施しない。`note-add` ではなく `history-add` を使う理由: この監査ログは工程4a が再度 ✅ 完了になっても
   `## 備考・メモ` の `⚠️ 工程4a:` 行自動削除ロジックの対象外として残す必要があるため）
3. Discovery エージェントを通常通り呼び出す（エージェントは `in-progress` として再開ロジックを実行し、
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
>   その後 `/xddp.04.specout {CR}` を再実行すると、スキルが自動で Discovery を再起動します。
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
     再実行時にスキルが自動で Discovery を再起動する）。

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
