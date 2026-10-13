# Specout Finish

> xddp-common の共通プロシージャ。SPO を仕上げるスキル（xddp-04-specout・xddp-investigate・xddp-05-arch）から apply される。

## Specout Finish

repo 1つの SPO を、下調べの資料と**採用した波紋調査の合算**から仕上げる。シードが直接参照するのに資料の無いファイルは追加下調べで
資料にし（採用した全調査のシードが対象）、波紋調査の結果はスクリプトが SPO と資料に反映する。採用した調査が0件の repo は、下調べの
資料だけで SPO を仕上げる（`work/no-ripple.json` の有無で文言をスクリプトが書き分ける）。per-repo progress table は更新しない。

**Input:** `CR`, `CR_PATH`, `repo`, `REPOS_MAP`, `ENTRY_POINTS`（人が引数で指定したエントリポイント。工程4a の引数のときだけ。空でよい。
採用した調査のシードは `assemble-spo` が加える）, `IS_MULTI`, `XDDP_DIR`, `DOCS`, `EXCLUDE_PATTERNS`, `INCLUDE_EXTENSIONS`,
`SPECOUT_MAX_FILES_PER_MODULE`, `SPECOUT_MAX_AFFECTED_FILES`, `EFFECTIVE_DIAGRAM_LEVEL`, `EFFECTIVE_SEQUENCE_LEVELS`,
`EFFECTIVE_SPO_DETAIL_LEVEL`（"## Specout Doc Levels" の返り値）, `RERUN_COMMAND`（止まったときに人が再実行するコマンド）, `TODAY`

**Output:** `FINISH_STATUS`（`ok` / `stopped`）, `REWRITTEN_SECTIONS`（スクリプト・document agent が書き直した SPO の節）,
`SPO_BACKUP`（退避した SPO のパス。無ければ空）, `ADOPTED_RUNS`（採用した調査の名前）

Let `OUT` = `{CR_PATH}/04_specout/{repo}`、`WORK` = `{OUT}/work`、
`PY` = `command -v python3 || command -v python` の結果、`BFS` = `~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py`、
`TPL` = `--repo-dir {OUT} --repo-path {REPOS_MAP[repo]} --repo {repo} --output-dir {OUT} --summary-template ~/.claude/skills/xddp-04-specout/templates/04_specout-summary-template.md --module-template ~/.claude/skills/xddp-04-specout/templates/04_specout-module-template.md --max-files-per-module {SPECOUT_MAX_FILES_PER_MODULE} --detail-level {SPO_DETAIL_LEVEL} --cr {CR} --today {TODAY}`
（`{SPO_DETAIL_LEVEL}` は `EFFECTIVE_SPO_DETAIL_LEVEL` を `--detail-level` の値へ写したもの: `full` → `standard`、`brief` → `brief`）、
`DOC_IN` = `--crs-file {CR_PATH}/03_change-requirements/CRS-{CR}.md --entry-points '{ENTRY_POINTS をカンマ区切り}' --metrics {CR_PATH}/metrics.jsonl`。
以降の Bash 呼び出しで、スクリプトが見つからない場合は setup.sh の実行を案内して停止し、exit 非0（下記で別の扱いを定めた終了コードを
除く）の場合は stderr を表示して `FINISH_STATUS` = `stopped` で呼び出し元へ戻る。止まった後の再開は「### 途中で止まった場合」。

**Process:**

0. **開始の記録と SPO の退避** — Run via Bash: `"$PY" "$BFS" finish-record --repo-dir {OUT} --status running --today {TODAY}`。
   `{OUT}/SPO-{CR}.md` があれば `{WORK}/spo-backup/SPO-{CR}-{日時（YYYYmmddHHMMSS）}.md` に写し、`SPO_BACKUP` = そのパス
   （人が直した欄が書き直されても差分で確かめられるように）。Run via Bash: `"$PY" "$BFS" run-list --repo-dir {OUT}` →
   `ADOPTED_RUNS` = stdout の `adopted_runs`（`adopted_unreadable` が空でなければ、その調査を `/xddp-investigate {CR} unadopt --name {名前}`
   か `remove --name {名前}` で外すよう案内して `stopped`）。`DISCOVERY_LOGS` = `ADOPTED_RUNS` の各 `{OUT}/ripple/{名前}/discovery-log.md`。

1. **モジュールの割り当て（スクリプト）** — Run via Bash:
   `"$PY" "$BFS" doc-targets --repo-dir {OUT} --repo-path {REPOS_MAP[repo]} --ledger {WORK}/documented-files.md --memo {WORK}/observation-memo.md --module-assignments {WORK}/module-assignments.json --auto-assign`
   自動の割り当て（`"auto": true`）をいったん外し、採用した調査の確定ファイルのうちどのモジュールにも属さないものの親ディレクトリを
   新しいモジュールとして割り当て直す（人が書いた要素・台帳のモジュールは変えない）。exit 1 でモジュール名の衝突が報告された場合は、
   stderr の内容と `{WORK}/module-assignments.json` の修正を人へ案内して `stopped`（修正後に `{RERUN_COMMAND}` を再実行する）。
   exit 5（`module-assignments.json` の組の不正）と、台帳・観察メモの書式不正による exit 1 は、stderr が示す該当ファイルの該当行を人が
   直して `{RERUN_COMMAND}` を再実行するよう案内して `stopped`。

2. **funcmap の機械算出値（スクリプト・ベストエフォート）** — `ADOPTED_RUNS` が空なら行わない（`FUNCMAP_COUNTS_FILE` = 空）。
   失敗しても止めない（失敗時は `FUNCMAP_COUNTS_FILE` = 空）。Run via Bash:
   `"$PY" "$BFS" funcmap-counts --repo-dir {OUT} --out {WORK}/SPO-{CR}-funcmap-counts.md`
   → 成功時は `FUNCMAP_COUNTS_FILE` = `{WORK}/SPO-{CR}-funcmap-counts.md`（stdout の `skipped_runs` が空でなければ、その調査の
   第0波を数えられなかった旨を1行伝える）。

3. **波紋調査の要約（スクリプト。採用した調査の合算）** — Run via Bash:
   `"$PY" "$BFS" ripple-summary --repo-dir {OUT} --repo-path {REPOS_MAP[repo]} --ledger {WORK}/documented-files.md --module-assignments {WORK}/module-assignments.json --gap-reviewed {WORK}/prelim-gap-reviewed.md --max-files {SPECOUT_MAX_AFFECTED_FILES} --out {OUT}/ripple-summary.md --json {WORK}/ripple-summary.json`
   stdout の `seed_direct_file_count`・`confirmed_file_count`・`prelim_gap_files`・`direct_modules` を保持する
   （`{OUT}/ripple-summary.md` は人向けの全量で、LLM には渡さない）。
   `prelim-gap-reviewed.md` の書式不正による exit 1 は、stderr が示す該当行を人が直して `{RERUN_COMMAND}` を再実行するよう案内して `stopped`。
   CR 分割の警告: `seed_direct_file_count` が `SPECOUT_MAX_AFFECTED_FILES` を超える場合、人へ伝える（処理は止めない）:
   > ⚠️ {repo} のシードが直接参照するファイル数（{seed_direct_file_count}。変更の中心の目安。波及ファイル数は {confirmed_file_count}）が
   > SPECOUT_MAX_AFFECTED_FILES（{値}）を超えています。CR の分割を検討してください。

4. **追加下調べ（`prelim_gap_files` が空でない場合のみ。採用した全調査のシードの直接参照が対象）:**
   1. Run via Bash:
      `"$PY" "$BFS" doc-targets --repo-dir {OUT} --repo-path {REPOS_MAP[repo]} --ledger {WORK}/documented-files.md --memo {WORK}/observation-memo.md --module-assignments {WORK}/module-assignments.json --gap-reviewed {WORK}/prelim-gap-reviewed.md --only seed-direct --max-files {SPECOUT_MAX_AFFECTED_FILES}`
      → `doc_targets`（追加下調べで書くファイルとモジュール。上限の残りまで）と `over_limit_files`（上限を超えて外したファイル）を得る。
      上限は repo ごとの**累計**で、残り = `SPECOUT_MAX_AFFECTED_FILES` −（台帳の工程 `追加下調べ` の行数 ＋ `prelim-gap-reviewed.md` の行数）
      （スクリプトが数える）。`doc_targets` が空なら手順4.2〜4.4 を飛ばして 4.5 へ進む。
      `over_limit_files` が空でなければ、人へ伝える（処理は止めない）:
      > ℹ️ {repo}: 追加下調べの対象のうち、上限（`SPECOUT_MAX_AFFECTED_FILES` = {値}。この repo の累計）を超えた {m} 件は追加下調べしません。
      > 上限を上げて `{RERUN_COMMAND}` を再実行すると、続きを追加下調べします。
   2. **書き先の決定（スクリプト）** — Run via Bash:
      `"$PY" "$BFS" assemble-spo {TPL} --layout-only --only seed-direct --max-files {SPECOUT_MAX_AFFECTED_FILES}`
      → 配置（成長型。台帳＋追加下調べのファイルで数え、閾値を超えた単位だけを分割へ移す）と、stdout の `file_outputs`
      （`{ファイル: {"module", "output_file"}}`）を得る。
   3. **Agent tool** で `subagent_type=xddp-specout-prelim-agent` を起動する（repo ごとに1回）。渡す入力:
      ```
      CR_NUMBER: {CR}
      REPO_NAME: {repo}
      REPO_PATH: {REPOS_MAP[repo]}
      CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
      BASELINE_SPECS_DIR: {DOCS}/{repo}/specs/
      CROSS_SPECS_DIR: {DOCS}/cross/specs/
      LATEST_SPECS_DIR: {XDDP_DIR}/latest-specs/{repo}/
      DOCS: {DOCS}
      MODULE_CATALOG_FILE: {{DOCS}/{repo}/module-catalog.md があればそのパス、無ければ空}
      ENTRY_POINTS: {ENTRY_POINTS}
      SUMMARY_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-summary-template.md
      MODULE_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-module-template.md
      INDEX_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-prelim-index-template.md
      LEDGER_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-documented-files-template.md
      OUTPUT_DIR: {OUT}/
      TODAY: {TODAY}
      EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}
      INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS}
      SPECOUT_MAX_FILES_PER_MODULE: {SPECOUT_MAX_FILES_PER_MODULE}
      SPECOUT_DIAGRAM_LEVEL: {EFFECTIVE_DIAGRAM_LEVEL}
      SPECOUT_SEQUENCE_LEVELS: {EFFECTIVE_SEQUENCE_LEVELS}
      SPO_DETAIL_LEVEL: {EFFECTIVE_SPO_DETAIL_LEVEL}
      PRELIM_MODE: additional
      TARGETS: {file_outputs の各要素を「- {ファイル} → モジュール {module}・書き先 {output_file}」の1行にした一覧（対応づけを変えずに転記する）}
      GAP_REVIEWED_FILE: {WORK}/prelim-gap-reviewed.md
      ```
      返答は1行（`OK: …`）。`OK:` で始まらない場合も、返答を人へ提示して手順4.4・4.5 へ進む（書けなかったファイルは
      `prelim_gap_files` に残り、4.5 の警告になる）。
   4. 手順3 の `ripple-summary` を再実行する（台帳が変わったため。`prelim_gap_files` を取り直す）。
   5. `prelim_gap_files` がなお空でなければ、人へ伝える（処理は止めない）:
      > ⚠️ {repo}: シードが直接参照するファイルのうち、追加下調べでも資料にできなかったものが {n} 件あります（{ファイル…}）。
      > SPO §5.0 の「シードの直接参照」列（⚠️）と `{OUT}/ripple-summary.md` を確認してください。`{RERUN_COMMAND}` を再実行すると、
      > 上限（`SPECOUT_MAX_AFFECTED_FILES`。この repo の累計）の残りの範囲で追加下調べをやり直します。

5. **組み立て（スクリプト）** — Run via Bash:
   `"$PY" "$BFS" assemble-spo {TPL} {DOC_IN} --exclude '{EXCLUDE_PATTERNS}'`
   配置は台帳のファイルだけで判定し（資料の無いモジュールの `modules/` は作らない）、統合パスなら追加下調べの資料を
   `SPO-{CR}.md` の §2.A… に差し込み、モジュール資料の「波紋調査の結果」、SPO とモジュール資料の版の確定、SPO のスクリプトが書く欄
   （§1・§1.x〔採用した調査ごとの1行〕・§5.0・§5.1・§5.2・§5.5・§8・§9〔採用した各調査の検証スイープの未記録・未実施の転記を含む〕）を書く。
   名指しで調べた除外パターンのファイル（台帳の工程 `依頼調査` の行のうち除外パターンに一致するもの）は、§5.5・影響の一覧
   （§1 の検出モジュール数・採用した調査が0件の §5.0・§5.1）から外し、§8 に注記する。
   stdout の `sections_written`・`inputs_changed`・`inputs_fingerprint`・`doc_entry_points`・`missing_drafts`・`pattern_override_files` を保持する。
   exit 1 で「§2.A… が下書きの抜き出しの後に変わっています」と報告された場合は、stderr を示し、人が `work/module-drafts/{モジュール名}.md` と
   SPO の節を見比べて残す方に揃え、`work/module-drafts/.source-sha256.json` からそのモジュールの行を消してから `{RERUN_COMMAND}` を
   再実行するよう案内して `stopped`。
   `missing_drafts` が空でなければ、そのモジュールに資料が無い旨を人へ伝える（処理は止めない）。

6. **SPO の LLM が書く欄と funcmap（LLM・1回）** — 下記「### document agent の起動と lint」を行う。止まった場合は `stopped`。

7. **調査ごとの要約の「資料」列の作り直し（スクリプト・ベストエフォート）** — 手順0 の `run-list` で状態が `complete` の調査
   （採用の有無によらない。`in-progress`・`not-started`・`missing` の調査は対象外）ごとに、
   Read `~/.claude/skills/xddp-common/procedures/ripple-run-outputs.md`, apply "## Ripple Run Outputs" with:
     CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, run: {名前}, SPECOUT_MAX_AFFECTED_FILES: {SPECOUT_MAX_AFFECTED_FILES}, ONLY_SUMMARY: true
   失敗しても止まらず、警告だけを出す。

8. **成功の記録** — Run via Bash: `"$PY" "$BFS" finish-record --repo-dir {OUT} --status ok --today {TODAY}`。
   `FINISH_STATUS` = `ok`。`REWRITTEN_SECTIONS` = 手順5 の `sections_written` と、document agent を起動した場合は LLM が書く欄
   （§2〜§4・§5.3・§5.4・§5.6・§5.7・§7）。

### document agent の起動と lint

`inputs_changed` が false で、`{OUT}/SPO-{CR}-funcmap.md` がある場合は agent を起動せず、
「{repo}: SPO の入力に変更が無いため、LLM が書く欄は前回のまま残しました」と伝えて、下記の lint だけを行う。
それ以外は **Agent tool** で `subagent_type=xddp-specout-document-agent` を起動する。渡す入力:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
MODULE_DOC_FILES: {資料のあるモジュールの資料の一覧。統合パスは SPO-{CR}.md の §2.A…、分割パスは modules/ 配下}
PATTERN_OVERRIDE_FILES: {pattern_override_files（組み立ての stdout）をカンマ区切り。空可}
FUNCMAP_COUNTS_FILE: {FUNCMAP_COUNTS_FILE}
DISCOVERY_LOGS: {DISCOVERY_LOGS（採用した調査が0件なら空）}
SUMMARY_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-summary-template.md
FUNCMAP_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-funcmap-template.md
SUMMARY_FILE: {OUT}/SPO-{CR}.md
OUTPUT_DIR: {OUT}/
TODAY: {TODAY}
LATEST_SPECS_DIR: {XDDP_DIR}/latest-specs/{repo}/
BASELINE_SPECS_DIR: {DOCS}/{repo}/specs/
CROSS_SPECS_DIR: {DOCS}/cross/specs/
DOCS: {DOCS}
ENTRY_POINTS: {doc_entry_points（組み立ての stdout）をカンマ区切り}
SPECOUT_DIAGRAM_LEVEL: {EFFECTIVE_DIAGRAM_LEVEL}
SPECOUT_SEQUENCE_LEVELS: {EFFECTIVE_SEQUENCE_LEVELS}
SPO_DETAIL_LEVEL: {EFFECTIVE_SPO_DETAIL_LEVEL}
```
Wait for completion. 返答は1行（`OK: SPO サマリー・funcmap を書いた`）。返答が `OK:` で始まらない、または agent が失敗した場合は、
原因を人へ提示して止まる（再開は「### 途中で止まった場合」の手順6 の項）。lint はその後に実行しない
（前回の funcmap が残っていると lint の F0 は出ないため、返答で先に止める）。`OK:` で始まれば（または agent を起動しなかった場合は）
続けて Run via Bash:
`"$PY" ~/.claude/skills/xddp-common/scripts/artifact_lint.py --file {OUT}/SPO-{CR}.md --doc-type SPO`
→ 出力の `spo.issues` のうち `check` が `F3` の件数（`確認要` を含む funcmap の行の数）を `k` とする。
`check` が `F0`（funcmap が無い・表が見つからない）の項目があれば、agent が funcmap を書き終えていないため、
その内容を人へ提示して止まる（再開は「### 途中で止まった場合」の手順6 の項）。
lint が実行時エラー（exit 非0）になった場合は stderr を表示して止まる。
lint の F3・F0 以外の項目は、ここでは見ない（SPO の AI レビューで扱う。採用した調査が無い repo は lint の F4 の対象外になる）。
agent を起動し、返答が `OK:` で、lint に F0 が無く止まらなかった場合だけ、Run via Bash:
`"$PY" "$BFS" commit-assemble-inputs --output-dir {OUT} --fingerprint {inputs_fingerprint}`
（document agent の入力の指紋を保存する。保存しなかった場合は、再実行で必ず agent が起動される）
- `確認要` がある場合（`k` > 0）、人に対して:
  > ⚠️ {repo} の funcmap 生成で `確認要`（直接呼び出し元数の要人的確認）が検出されました。
  > `DISCOVERY_LOGS` の当該メッセージと `{FUNCMAP_COUNTS_FILE}` の「スキップされた行」テーブルを確認し、各識別子の直接呼び出し元数を
  > 判断のうえ、`{n}(確認済)`（例: `3(確認済)`）の表記で `{OUT}/SPO-{CR}-funcmap.md` の該当セルを直接編集してください。
  と伝え、承認（編集完了の確認）されるまで呼び出し元の次の手順へ進まない。

### 途中で止まった場合

`{RERUN_COMMAND}` の再実行で本プロシージャが先頭から走る（波紋調査の波ループは再実行しない）。`finish-needed` は、前回の SPO の仕上げが
`ok` で終わっていなければ `needed: true` を返す。

- 手順1（`doc-targets --auto-assign`）・手順2（`funcmap-counts`）・手順3（`ripple-summary`）・手順5（`assemble-spo`）・
  手順7（調査ごとの要約）はスクリプトで冪等であり、先頭から再実行してよい。人が `work/module-assignments.json` に書いた組は変わらない
  （自動の割り当ては採用した調査で作り直す）。モジュール資料・台帳・累積観察メモは変えず、スクリプトが書く欄（SPO の §1・§1.x・§5.0・
  §5.1・§5.2・§8・§9 の自動転記の行と、モジュール資料の「波紋調査の結果」）だけを作り直す。SPO §5.5 は行を作り直し、累積観察メモに
  行の無いファイルは既存の値（`未確認` 以外）を残す。
- 手順4（追加下調べ）の途中で止まった場合: 再実行すると、手順3 の `prelim_gap_files` に残ったファイルだけが再び対象になる
  （台帳に行のあるファイルと `work/prelim-gap-reviewed.md` に記録したファイルは対象外。下調べのエージェントは資料・観察メモを
  書いた後に台帳の行を書くため、台帳に行があれば資料と観察メモは書き終えている）。対象の件数は `SPECOUT_MAX_AFFECTED_FILES`
  （この repo の累計）の残りまで。書き先に前回の途中の記述があれば、エージェントがそのファイルの記述を置き換える（二重にしない）。
- 手順6（document agent の起動と lint）で止まった場合: 手順5 の `assemble-spo` を再実行する（スクリプトが書く欄は同じ内容になり、
  LLM が書く欄は変えない）。document agent の入力の指紋（`work/assemble-inputs.json`）は、agent が成功し lint で止まらなかった
  ときにだけ保存される。保存された指紋が今回の `inputs_fingerprint` と一致すれば（`inputs_changed` が false）、LLM が書く欄
  （§2・§3・§4 の集約・§5.3・§5.4・§5.6・§5.7・§7）と funcmap は書き終えているため、agent を起動せず lint だけを行う。
  一致しなければ agent を再起動する（SPO サマリーへの書き込みは Edit 置換で、funcmap は作り直しが正のため、二重にならない）。
