---
name: xddp-investigate
description: XDDP 母体調査の追加: CR の母体調査に波紋調査を足す・採用する・取り消す・取り除く。人の依頼でファイル・モジュールを調べて資料にする。工程4a の後でも、工程5以降でも実行できる。「このシンボルの影響を見たい」「この調査を SPO に入れて」「この調査は外して」「調査の一覧」「このモジュールを調べて資料にして」「資料にする候補を見せて」などで起動する。
argument-hint: "[CR番号] (ripple [--name 名前] [--adopt] シンボル... | adopt --name 名前 | unadopt --name 名前 | remove --name 名前 | list | finish | document 対象... [--focus 観点] | suggest) [--repo リポジトリ]"
---

You are orchestrating **XDDP — 母体調査の追加（波紋調査の実行・採用・取り消し・取り除き、人の依頼による資料の追加）**.

**Arguments:** $ARGUMENTS = [CR_NUMBER]（省略可）動詞 [オプション・シンボル…]
- 動詞（先頭）: `ripple`（波紋調査を作る・続ける）・`adopt`（採用する）・`unadopt`（採用を取り消す）・`remove`（取り除く）・
  `list`（一覧）・`finish`（SPO の仕上げのやり直し）・`document`（人の依頼でファイル・ディレクトリ・モジュールを調べて資料にする）・
  `suggest`（資料にする候補を示す）
- `--name 名前`: 調査の名前（`^[a-z0-9][a-z0-9-]{0,39}$`。`initial`・`cross-`・`arch-` で始まる名前は工程4a・クロスリポジトリ伝播・工程5が
  使うため、`ripple` では指定できない）
- `--adopt`（`ripple` のみ）: 完了したら採用して SPO に入れる
- `--repo リポジトリ`: 対象の repo
- それ以外の語（`ripple` のみ）: シンボル（`名前`・`名前[FILE:パス]`・`名前[CLASS:クラス名]`・`型名.メンバー名`）
- `document` の対象: リポジトリ相対のファイル・ディレクトリ、またはモジュール名（SPO §5.0・§8 の名前）
- `--focus 観点`（`document` のみ。最後に置く）: `--focus` より後の語の残り全部を観点の文とする（観点は空白を含む自由文のため）

---

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md lookup done in xddp-common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR, DOCS, REPOS_MAP, REPOS_KEYS, IS_MULTI,
DEVELOPMENT_MODE, CR_PROFILE, EXCLUDE_PATTERNS, INCLUDE_EXTENSIONS, MAX_WAVE_DEPTH, SPECOUT_MAX_AFFECTED_FILES, SPECOUT_MAX_FILES_PER_MODULE,
SPECOUT_DIAGRAM_LEVEL, SPECOUT_SEQUENCE_LEVELS, SPECOUT_BACKEND, SPECOUT_BACKEND_OVERRIDES, SPECOUT_HIT_FILTER, SPECOUT_CLASSIFY_CHUNK_SIZE,
SPECOUT_CLASSIFY_PARALLEL, SPECOUT_WAVE_HIT_BUDGET, SPECOUT_LLM_HIT_BUDGET, SPECOUT_SLICE, SPECOUT_SLICE_IGNORE_CALLS, SPECOUT_SLICE_H_AS,
SPECOUT_SLICE_PYTHON_BIN.
`SPECOUT_HIT_FILTER` は未指定時 `conservative`。`SPECOUT_CLASSIFY_CHUNK_SIZE` は未指定時 `40`、`SPECOUT_CLASSIFY_PARALLEL` は未指定時 `4`。
`MAX_WAVE_DEPTH` は未指定時 `6`、`SPECOUT_WAVE_HIT_BUDGET` は未指定時 `10000`、`SPECOUT_LLM_HIT_BUDGET` は未指定時 `160`、
`SPECOUT_SLICE` は未指定時 `auto`、`SPECOUT_SLICE_IGNORE_CALLS` は未指定時 空、`SPECOUT_SLICE_H_AS` は未指定時 `auto`、
`SPECOUT_SLICE_PYTHON_BIN` は未指定時 空、`SPECOUT_MAX_AFFECTED_FILES` は未指定時 `20`。)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.
Let `PY` = `command -v python3 || command -v python` の結果、`BFS` = `~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py`。
以降の Bash 呼び出しで、スクリプトが見つからない場合は setup.sh の実行を案内して停止し、exit 非0 の場合は stderr を表示して停止する
（下記で別の扱いを定めた場合を除く）。

`REST_ARGS` の先頭の語を `VERB`、`--focus` より後の語の残り全部を空白でつないだものを `FOCUS`（`document` のみ）、それより前の語について
`--name` の次の語を `NAME`、`--repo` の次の語を `REPO_ARG`、`--adopt` の有無を `ADOPT_FLAG`、残りの語を `SYMBOLS`（`document` では対象 `TARGETS`）
とする。`VERB` が無い・上記の8つ以外なら、上の **Arguments** の使い方を示して停止する。
人が言葉で頼んだ場合（例「案B の調査は外して」）は、`list` の結果から名前を特定してこの引数に置き換えて実行する（特定できなければ尋ねる）。
資料の依頼を言葉で受けた場合（例「{機能名} まわりを調べて資料にして」。通信の再接続処理まわり／在庫引当の処理まわり／センサ読み取りの
割り込み処理まわり等）は、SPO §5.0・`ripple-summary.md`・`suggest` の結果から対象を特定して `document` の引数に置き換え、
**置き換えた対象を人に示して確認してから**実行する（人の言葉とファイルの対応は推測であるため）。

## Step 0: 共通の前提

1. `DEVELOPMENT_MODE` = `new` なら「新規開発モードでは母体調査を行いません」と伝えて停止する。
2. 対象の repo（`TARGET_REPOS`）: `REPO_ARG` があればその repo（`REPOS_KEYS` に無ければ停止）。無ければ、シングルリポジトリはその repo、
   マルチリポジトリは `list` なら全 repo、それ以外は尋ねる。
3. 下調べが完了していない repo（`{CR_PATH}/04_specout/{repo}/work/prelim-index.md` が無い）は「先に `/xddp-04-specout {CR}` を実行して
   ください」と伝えて `TARGET_REPOS` から外す。空になれば停止する。
4. 人レビューゲートの待機中（progress.md の詳細ステップが人レビューの待機を示している）に実行すると、ゲートの変更判定に SPO の変更が
   混ざる。待機中なら、その旨を1行伝える（止めない）。
5. Read `~/.claude/skills/xddp-common/procedures/specout-doc-levels.md`, apply "## Specout Doc Levels" with:
     CR_PROFILE: {CR_PROFILE}, SPECOUT_DIAGRAM_LEVEL: {SPECOUT_DIAGRAM_LEVEL}, SPECOUT_SEQUENCE_LEVELS: {SPECOUT_SEQUENCE_LEVELS}
   → let `EFFECTIVE_DIAGRAM_LEVEL`, `EFFECTIVE_SEQUENCE_LEVELS`, `EFFECTIVE_SPO_DETAIL_LEVEL`.

以下 `{O}` = `{CR_PATH}/04_specout/{repo}`。

## Step 1: 動詞ごとの処理

### `ripple [--name 名前] [--adopt] シンボル…`

対象は `TARGET_REPOS` の1つの repo（`{repo}`）。
1. Run via Bash: `"$PY" "$BFS" run-list --repo-dir {O}` → `runs`。
2. 名前を決める: `NAME` が無ければ `run-{n}`（`runs` に無い最小の正の整数 `n`）。`NAME` が `initial`・`cross-`・`arch-` で始まる場合は、
   シンボルがあれば停止する（それらの調査は工程4a・クロスリポジトリ伝播・工程5が作る）。シンボルが無ければ、途中で止まった調査の続きとして
   手順4 へ進む。
3. - `NAME` の調査が無い: `SYMBOLS` が空なら停止する（シンボルを求める）。Write ツールで `{O}/ripple/{NAME}/meta.json` に
     `{"approach": null, "reason": null, "seeds": [{SYMBOLS…}], "entry_identity": "resolved"}` を書く。
   - `NAME` の調査があり `complete` で、`SYMBOLS` が空でない: 停止し、別の名前を指定するか `/xddp-investigate {CR} remove --name {NAME}` で
     取り除いてから実行するよう求める。
   - `NAME` の調査があり、それ以外（途中で止まった調査）: `SYMBOLS` は使わない（続きから行う）。
4. Read `~/.claude/skills/xddp-common/procedures/ripple-engine-setup.md`, apply "## Ripple Engine Setup" with:
     SPECOUT_SLICE: {SPECOUT_SLICE}, SPECOUT_SLICE_PYTHON_BIN: {SPECOUT_SLICE_PYTHON_BIN}
   → let `SLICE_PY`, `PROBE_ENGINE`, `EFFECTIVE_SLICE_ENGINE`, `USE_PROBE_WARNING`.
5. Read `~/.claude/skills/xddp-common/procedures/ripple-run.md`, apply "## Ripple Run" with:
     CR: {CR}, CR_PATH: {CR_PATH},
     REPO_RUNS: {{repo}: [{run: {NAME}, origin: `human`（`arch-`・`cross-` の続きはその調査の由来）, symbols: {SYMBOLS}, meta_file: {O}/ripple/{NAME}/meta.json,
       entry_identity: `resolved`, adopt: {ADOPT_FLAG}, adopted_by: `human`, RERUN_COMMAND: `/xddp-investigate {CR} ripple --name {NAME} --repo {repo}`}]},
     REPOS_MAP: {REPOS_MAP}, SLICE_PY: {SLICE_PY}, PROBE_ENGINE: {PROBE_ENGINE}, EFFECTIVE_SLICE_ENGINE: {EFFECTIVE_SLICE_ENGINE},
     USE_PROBE_WARNING: {USE_PROBE_WARNING}, TODAY: {TODAY},
     設定（EXCLUDE_PATTERNS, INCLUDE_EXTENSIONS, MAX_WAVE_DEPTH, SPECOUT_MAX_FILES_PER_MODULE, SPECOUT_BACKEND, SPECOUT_BACKEND_OVERRIDES,
     SPECOUT_HIT_FILTER, SPECOUT_WAVE_HIT_BUDGET, SPECOUT_LLM_HIT_BUDGET, SPECOUT_SLICE_IGNORE_CALLS, SPECOUT_SLICE_H_AS,
     SPECOUT_MAX_AFFECTED_FILES, SPECOUT_CLASSIFY_CHUNK_SIZE, SPECOUT_CLASSIFY_PARALLEL, DOCS）
   → let `DONE`, `FAILED`。`FAILED` なら理由を示し、`/xddp-investigate {CR} ripple --name {NAME} --repo {repo}` で続きから行えると伝えて停止する。
6. 報告: 調査の要約 `{O}/ripple/{NAME}/ripple-digest.md`・全量 `ripple-summary.md`・`ripple-graph.md`・`ripple-tree.md` のパス、
   確定ファイル数・機能数・打ち切り（`run-list` と要約から転記する）、採用の有無。
   名前が `arch-` で始まる調査（工程5の Step A-ripple で途中まで進んだもの）を完了させた場合は、「方式検討の DSN への反映は工程5の中だけで
   行います。`/xddp-05-arch {CR}` を再実行すると、Step A で方式検討エージェントがこの要約を読みます」と伝える。
7. `ADOPT_FLAG` があり採用した場合は、理由「波紋調査の採用・取り消し」で「## Step 2: SPO への反映」を行う。採用しなかった場合は、SPO は変わっていない旨と、
   `/xddp-investigate {CR} adopt --name {NAME} --repo {repo}` で後から SPO に入れられる旨を伝えて終わる。

### `adopt --name 名前` ／ `unadopt --name 名前`

`NAME` が無ければ停止する。対象は `TARGET_REPOS` の1つの repo。
- `unadopt` で `NAME` が `initial` の場合、または取り消すと採用した調査が0件になる場合（`run-list` の `adopted_runs` が `NAME` だけ）は、
  「SPO の波紋調査の欄から外れ、影響範囲が狭まります（影響漏れは後工程で気付きにくい）。取り消しますか」と確認してから行う。
- Run via Bash: `"$PY" "$BFS" run-adopt --repo-dir {O} --run {NAME} --by human --today {TODAY}`（`unadopt` は `run-unadopt`）。
  exit 1（調査が無い・完了していない）は stderr を示して停止する（完了していない調査は `/xddp-investigate {CR} ripple --name {NAME}` で続ける）。
- stdout の `changed` が false なら「既に{採用済み／取り消し済み}です」と伝えて終わる。true なら、理由「波紋調査の採用・取り消し」で「## Step 2: SPO への反映」を行う。

### `remove --name 名前`

`NAME` が無ければ停止する。対象は `TARGET_REPOS` の1つの repo。`run-list` で調査の採用の有無を確かめ、
「調査 `{NAME}` を `ripple/_removed/` へ退避し、記録から外します（{採用していれば: SPO の波紋調査の欄からも外れます}）。取り除きますか」と
確認してから、Run via Bash: `"$PY" "$BFS" run-remove --repo-dir {O} --run {NAME} --today {TODAY}`。
stdout の `moved_to`・`propagation_reset`（クロスリポジトリ伝播の調査なら、伝播の記録が未投入に戻り、次の `/xddp-04-specout {CR}` で
同じシンボルが新しい調査として再投入される）を伝える。`was_adopted` が true なら、理由「波紋調査の採用・取り消し」で「## Step 2: SPO への反映」を行う。

### `finish`

理由「波紋調査の採用・取り消し」で「## Step 2: SPO への反映」の手順2 以降だけを行う（SPO の仕上げが途中で止まった場合の再開）。

### `suggest`

対象は `TARGET_REPOS` の1つの repo。Run via Bash: `"$PY" "$BFS" doc-suggest --repo-dir {O} --exclude '{EXCLUDE_PATTERNS}'`
（除外パターンは設定の値。SPO を組み立てる `assemble-spo --exclude` と同じもの）。
- `reason` が `no-adopted-runs` なら「候補を出す波紋調査の結果がありません」と伝えて終わる。
- `candidates` を表で示す: | モジュール | 確定ファイル数 | うち名前の一致のみ | 最も浅い到達波 | シードの直接参照（うち資料に無い） | 届いた調査 |
  （値は stdout から転記する。自分で数えない。`candidate_count` が表の行数より多ければ「ほか {n} モジュール」と添える）
- 各候補に、SPO や `ripple-summary.md` から読み取れる根拠を1行添えてよい。依頼するかは人が決める（提案だけで `document` を実行しない）。
  依頼する場合は `/xddp-investigate {CR} document {モジュール名} --repo {repo}` で行える旨を伝える。

### `document 対象… [--focus 観点]`

対象は `TARGET_REPOS` の1つの repo。`TARGETS` が空なら停止する（対象を求める）。
同じ repo で工程4a・`finish`・別の `document` と同時に実行しないよう1行注意する（台帳・観察メモ・資料の書き込みが衝突するため）。

1. **準備** — Write ツールで `{O}/work/doc-request-focus.md` に `FOCUS` を書く（無ければ空のファイル。自由文をシェルの引数で渡さない）。
   `{O}/work/doc-request-append.txt` があれば削除する（前回の依頼の答えを持ち越さない）。
2. **対象の展開（スクリプト）** — Write ツールで `{O}/work/doc-request-targets.txt` に `TARGETS` を1行ずつ書き、Run via Bash:
   `"$PY" "$BFS" doc-request --repo-dir {O} --repo-path {REPOS_MAP[repo]} --targets-file {O}/work/doc-request-targets.txt --exclude '{EXCLUDE_PATTERNS}' --include-ext '{INCLUDE_EXTENSIONS}' --soft-limit {SPECOUT_MAX_AFFECTED_FILES} --batch-size {SPECOUT_MAX_AFFECTED_FILES} --out {O}/work/doc-request-files.json`
   （`doc-request-append.txt` がある場合は `--append-file {O}/work/doc-request-append.txt` を付ける）。exit 1 は stderr を示して停止する
   （SPO の仕上げが途中〔`specout-finish.json` が `running`〕と報告されたら、「先に `/xddp-investigate {CR} finish --repo {repo}` を実行してください」と伝える。
   新しいモジュール名の衝突は、`{O}/work/module-assignments.json` に組を人が書いて名前を分けるよう案内する）。stdout から次を示す:
   - `not_found`（リポジトリに無い・モジュール名に一致しない）・`excluded`（名指しした対象より下の階層で除外パターンに一致したため外した
     ファイル）・`skipped_ext`（`SPECOUT_INCLUDE_EXTENSIONS` に一致しないため外したファイル）・`skipped_binary`（バイナリのため外したファイル）。
   - `already_documented`（資料があるファイル）があれば、ファイルごとに（多ければモジュールごとにまとめて）
     「すでに資料として記述しています。追記が必要ですか？」と尋ねる（`appended_on` があれば「（{appended_on} に追記済み）」を添える。
     追記の要否は自分で判断しない）。「必要」と答えたファイルを `{O}/work/doc-request-append.txt` に1行ずつ Write し、`--append-file` を
     付けて手順2 のコマンドを再実行する（そのファイルは追記の対象として入る）。「不要」のファイルは外れる。この確認は件数の確認より前に行い、
     再実行の後は尋ねない。以下の確認は再実行の出力で行う。
   - `pattern_overridden`（名指しした対象が除外パターンに一致したため、除外パターンを適用せずに対象にしたファイル）は、質問せずに件数と対象を示す。
   - 依頼への疑問（拒否はしない）: `concerns` のあるファイル（`name_only`＝波紋調査の到達が名前の一致だけ、`gap_reviewed`＝追加下調べが関係なしと
     判断した〔理由 `gap_reason` を添える〕）と、SPO（§5.0・§7）・CRS から根拠を挙げられる懸念（例: CRS の変更対象の振る舞いと離れた機能に見える）が
     あれば、根拠とともにまとめて示し、「続けますか／対象を変えますか」と1回だけ尋ねる。根拠を挙げられない推測は示さない。
     決めるのは人で、「続ける」なら依頼どおりに行う。
   - 拡張子ごとのファイル数（`ext_counts`）と、モジュールごとのファイル数（`modules`）を示す。
   - `over_soft_limit` が true（ファイル数 `file_count` が `SPECOUT_MAX_AFFECTED_FILES` を超える）なら、「全部」／「絞る（対象を指定し直す）」を尋ねる。
   - `file_count` が 0 なら、その旨を伝えて終わる。
   - 「対象を変える」「絞る」が選ばれたら、人が指定し直した対象で手順2 をやり直す。同じ実行の中で既に答えたファイルには、追記の要否と
     依頼への疑問を再び尋ねない（追記の答えは `doc-request-append.txt` に残っている。依頼への疑問は新しく対象に加わったファイルの懸念だけを示す）。
3. **書き先の決定（スクリプト）** — Run via Bash:
   `"$PY" "$BFS" assemble-spo --repo-dir {O} --repo-path {REPOS_MAP[repo]} --repo {repo} --output-dir {O} --summary-template ~/.claude/skills/xddp-04-specout/templates/04_specout-summary-template.md --module-template ~/.claude/skills/xddp-04-specout/templates/04_specout-module-template.md --max-files-per-module {SPECOUT_MAX_FILES_PER_MODULE} --cr {CR} --today {TODAY} --layout-only --only requested --files-file {O}/work/doc-request-files.json > {O}/work/doc-request-layout.json`
   （stdout の `file_outputs` が書き先。`discarded_drafts` が空でなければ、そのモジュールの途中の下書きを捨てた〔台帳に行が無く、再依頼で資料にし直せる〕旨を伝える）。
   exit 0 以外（下書きの抜き出しの後に §2.A… が変わった・モジュール名の衝突・`module-assignments.json` の不正等）なら stderr を示して停止し、
   「原因を直してから、同じ `/xddp-investigate {CR} document …` を再実行してください」と伝える（エージェントを起動していないため、台帳・資料は変わっていない）。
4. **資料を書く（LLM）** — `{O}/work/doc-request-files.json` の `batches` を先頭から1つずつ順に処理する（並列にしない。統合パスでは同じ SPO の
   下書きに書くため）。バッチ `i`（0 始まり）ごとに:
   1. 追記のバッチ（`mode` が `append`）なら、Run via Bash:
      `"$PY" "$BFS" doc-append-check snapshot --repo-dir {O} --files-file {O}/work/doc-request-files.json --layout {O}/work/doc-request-layout.json --batch {i}`
      exit 4（前回の追記の写しが残っている）なら、stdout の写しの日時とファイルを示し、「元に戻す（前回の追記の前の状態に戻す）」／
      「捨てる（今の状態を残し、写しを消す）」を尋ねて、`"$PY" "$BFS" doc-append-check restore --repo-dir {O}`／`"$PY" "$BFS" doc-append-check discard --repo-dir {O}` を
      行ってから、もう一度 `snapshot` する（写しの後に工程4a・`finish` 等が台帳や資料を書いていることがあるため、黙って戻さない。
      `restore` が exit 1 なら stderr を示して停止する）。
   2. **Agent tool** で `subagent_type=xddp-specout-prelim-agent` を起動する。入力は "## Specout Finish"（`~/.claude/skills/xddp-common/procedures/specout-finish.md`）の
      追加下調べ（手順4.3）と同じ値で、次だけを変える（`GAP_REVIEWED_FILE` は渡さない。`ENTRY_POINTS` は空。`OUTPUT_DIR` は `{O}/`。
      資料の記載量は Step 0 の `EFFECTIVE_*` の値）:
      ```
      PRELIM_MODE: requested
      TARGETS: {バッチのファイルごとに「- {ファイル} → モジュール {doc-request-files.json の module}・書き先 {doc-request-layout.json の file_outputs の output_file}」。mode が append の行は末尾に「（追記）」}
      REQUEST_FOCUS_FILE: {O}/work/doc-request-focus.md
      ```
   3. 追記のバッチなら、返答によらず（`OK:`・`NG:`・起動の失敗のどれでも）Run via Bash:
      `"$PY" "$BFS" doc-append-check verify --repo-dir {O}`（返答が `OK:` で始まらなければ `--restore` を付ける）。
      - exit 0: 追記を残す。
      - exit 3（元に戻した）: 「追記で既存の記述・台帳が変わった、または追記が最後まで終わらなかったため、追記の前の状態に戻しました」と
        stderr の理由とともに示して停止する。
      - exit 1（検査の実行エラー）: stderr を示して停止する（写し `work/doc-append-backup/` は残り、次の `snapshot` が exit 4 で知らせる）。
   4. 返答が `OK:` で始まれば（追記のバッチは `verify` が exit 0 なら）、返答で「資料にできなかった」とされたファイルを除いたバッチのファイルを
      `{O}/work/doc-request-done.txt` に Write し、Run via Bash:
      `"$PY" "$BFS" doc-request-record --repo-dir {O} --files-file {O}/work/doc-request-files.json --done-file {O}/work/doc-request-done.txt --focus-file {O}/work/doc-request-focus.md --today {TODAY}`
   5. 返答の2行目以降の `確認できず`・`助言`・`追加の観察なし`・`資料にできなかった` の行を、理由・助言とともに示す。
   6. 返答が `OK:` で始まらなければ示して停止し、「同じ `/xddp-investigate {CR} document …` を再実行すると続きから行います（資料にしたファイルは
      「すでに資料として記述しています」と尋ねられるので、追記しない場合は「不要」と答えてください）」と伝える。今回の依頼で終えたバッチの
      ファイル（依頼調査の記録 `{O}/work/doc-request-log.md` に今日の日付で書いた行。新規・追記の別）を示し、「追記を終えたファイルは再実行で
      「（{日付} に追記済み）」と示されます。二重に追記しないよう「不要」と答えてください」と添える。
5. 理由「人の依頼による資料の追加」で「## Step 2: SPO への反映」を行う。
6. **報告:** 資料にしたファイル・追記したファイル・モジュール、書き先、資料にできなかったファイル。エージェントが返した `確認できず` の理由と
   `助言` をまとめて示し、依頼の意図（どの振る舞いとの関係を知りたいか）があれば `--focus` を付けた追記の依頼、または CRS の見直しを検討できる旨を
   添える。SPO の仕上げを行った場合は、SPO の書き直された節（"## Step 2: SPO への反映" の手順5 の報告）も示す。

### `list`

`TARGET_REPOS` の各 repo について Run via Bash: `"$PY" "$BFS" run-list --repo-dir {O}`。repo ごとに表で示す:
| 名前 | 由来 | 案 | シード | 状態 | 確定ファイル数（うち名前の一致のみ） | 打ち切り | 採用 |
（値は `run-list` の出力から転記する。自分で数えない）
根拠を添えて取り消しを提案してよい（例: 確定ファイルの大半が名前の一致のみ、シードが一般語）。決めるのは人であり、提案だけで
`unadopt`・`remove` を実行しない。

## Step 2: SPO への反映

入力: 理由（`ripple`・`adopt`・`unadopt`・`remove`・`finish` は「波紋調査の採用・取り消し」、`document` は「人の依頼による資料の追加」）。

1. Run via Bash: `"$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py show --cr-path {CR_PATH} --step 4a` → `state`。
   `✅ 完了` でなければ「SPO には工程4a の SPO の仕上げで、CRS には工程4b で反映されます（`/xddp-04-specout {CR}`）」と伝えて終わる。
2. 次を伝えて、続けるかを尋ねる:
   > SPO の仕上げを行います。スクリプトが書く欄と、入力が変わった場合は LLM が書く欄（§2〜§4・§5.3・§5.4・§5.6・§5.7・§7）が書き直されます。
   > 人が直した内容は `work/spo-backup/` に退避した SPO との差分で確かめられます。
   続けない場合は「`/xddp-investigate {CR} finish --repo {repo}` で後から仕上げられます」と伝えて終わる。
3. Read `~/.claude/skills/xddp-common/procedures/specout-finish.md`, apply "## Specout Finish" with:
     CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, REPOS_MAP: {REPOS_MAP}, ENTRY_POINTS: 空, IS_MULTI: {IS_MULTI}, XDDP_DIR: {XDDP_DIR},
     DOCS: {DOCS}, EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}, INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS},
     SPECOUT_MAX_FILES_PER_MODULE: {SPECOUT_MAX_FILES_PER_MODULE}, SPECOUT_MAX_AFFECTED_FILES: {SPECOUT_MAX_AFFECTED_FILES},
     EFFECTIVE_DIAGRAM_LEVEL: {EFFECTIVE_DIAGRAM_LEVEL}, EFFECTIVE_SEQUENCE_LEVELS: {EFFECTIVE_SEQUENCE_LEVELS},
     EFFECTIVE_SPO_DETAIL_LEVEL: {EFFECTIVE_SPO_DETAIL_LEVEL}, RERUN_COMMAND: `/xddp-investigate {CR} finish --repo {repo}`, TODAY: {TODAY}
   → let `FINISH_STATUS`, `REWRITTEN_SECTIONS`, `SPO_BACKUP`, `ADOPTED_RUNS`。`stopped` なら終わる（再開は `/xddp-investigate {CR} finish --repo {repo}`）。
4. CRS の扱い: Run via Bash: `"$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py show --cr-path {CR_PATH} --step 5` → 工程5の `state`。
   - `CR_PROFILE` = `full` かつ工程5が `⬜ 未着手` → 「工程5で方式検討エージェントが更新した SPO を読み、DSN を通じて Step C で CRS に
     反映されます」と伝える。
   - `CR_PROFILE` = `full` かつ工程5が `🔄 進行中` → 「DSN を作成済みなら、`/xddp-05-arch {CR}` の再実行か `/xddp-revise {CR} arch` で
     SPO の変更を DSN に反映してください。DSN に反映された内容が Step C で CRS に入ります（SPO の変更が自動で CRS に入るわけではありません）」
     と伝える。
   - それ以外（工程5が完了・スキップ、または quick）→ 「CRS を今更新しますか」と尋ねる。
     - 更新する: **Agent tool** で `subagent_type=xddp-spec-writer-agent` を起動する:
       ```
       CR_NUMBER: {CR}
       MODE: update
       CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
       SPO_DIR: {CR_PATH}/04_specout/
       SPO_CROSS_FILE: {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md (pass only if exists)
       TODAY: {TODAY}
       AUTHOR_NOTE: 母体調査（{理由}）の結果を反映。
       ```
       続けて Read `~/.claude/skills/xddp-common/procedures/regenerate-crs-excel.md`, apply "## Regenerate CRS Excel" with:
         CR_PATH: {CR_PATH}, CR: {CR}
       CHD・TSP 等は自動では更新していないと伝える。
     - 更新しない: Run via Bash:
       `"$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py note-add --cr-path {CR_PATH} --step 4a --text "{理由}を CRS に未反映（{TODAY}）"`
5. 報告: `REWRITTEN_SECTIONS`・`SPO_BACKUP`・`ADOPTED_RUNS`・SPO §5.0 の行数の変化（`SPO_BACKUP` があればその §5.0 と比べる）。
   SPO の AI レビューは行っていない旨と、`/xddp-review {CR} specout` で確認できる旨を伝える。
