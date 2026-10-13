# Ripple Count Check

> xddp-common の共通プロシージャ。波紋調査を行うスキル（xddp-04-specout・xddp-investigate・xddp-05-arch）から apply される。

## Ripple Count Check

波紋調査1つの discovery-log の件数一致検証（独立回帰チェック）と、不一致の扱い。

**Input:** `CR`, `CR_PATH`, `repo`, `run`, `RUN_DIR`（`{CR_PATH}/04_specout/{repo}/ripple/{run}`）, `RERUN_COMMAND`, `TODAY`,
`WAVE_WRITE_COMPLETE`（`status --brief` の `wave_write_complete`。波ループで `complete` になった直後は `true`）

**Output:** なし（不一致でやり直しを選んだら停止する）

**Process:**

**前提ガード:** `WAVE_WRITE_COMPLETE` が `false` の場合、**本検証は実行しない**。この状態は「`search` 済み・`commit-wave` 未完」を
意味する。`search` 自体は discovery-log.md へ **`## Wave N` セクションを**書かない（`## Wave N` の書き込みは `cmd_commit_wave` のみ。
`search` が書くのは `## 未ヒット投入シンボル（Wave N）`・`## ヒット過多の投入シンボル（Wave N）` セクションの upsert と、
バックエンド警告・パース不能ヒット警告の blockquote 追記に限られ、いずれも `## Wave N` ブロックの外である）ため、`search` 直後に
停止したケースでは当該波の `## Wave N` がそもそも存在せず `--wave all` は当該波を列挙しない。問題になるのは
**`commit-wave` が `_append_to_file` の途中でクラッシュした場合**であり、このとき `## Wave N` と実行コマンド一覧だけが書かれ
ヒット行テーブルが欠けた**書きかけセクション**が残る。これを検証すると不一致となり、下記「### 不一致の扱い」が
「やり直し / 承知で続行」という**誤った選択肢**を提示してしまう。`wave_write_complete = false` は両ケースを区別せずに立つ
フラグであるため、安全側に倒して一律スキップする（ガードを外してはならない理由がこれである）。
正しい復旧は「`search` から再開する」ことであり、これは "## Ripple Wave Loop" が `wave_write_complete: false` を検出して自動的に
行う（人が手で復旧する場合は "## Ripple Wave Resume"）。書きかけ Wave セクションはスクリプトが切り捨てて再構築する。
再開が完了すれば、波ループで `complete` になったときに本検証が行われる。

`WAVE_WRITE_COMPLETE` が `true` の場合、Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_verify_counts.py --log {RUN_DIR}/discovery-log.md --wave all --strict; echo "VERIFY_EXIT=$?"`
  （終了コードを stdout の `VERIFY_EXIT=` 行で明示的に受け取り、下記の分岐を決定的にする）
- **exit 3（件数不一致）:** stdout JSON の `mismatch_waves` を `MISMATCH_WAVES` とし、下記「### 不一致の扱い」を行う。
- **exit 1（検証の実行エラー。ログ破損・`## Wave N` 不在等）:** stderr を表示して停止する
  （不一致とは別事象であり、人がログを確認する必要がある）。
- **exit 2（実行環境エラー。件数不一致ではない）:** argparse の使用法エラー、または Python がスクリプトを開けなかった場合
  （`setup.sh` 未実行）である。stderr を表示し、`bash ClaudeCode/setup.sh` の実行を案内して停止する。
  **「### 不一致の扱い」を行ってはならない。**
- **exit 0:** 何も表示せず呼び出し元へ戻る（正常時に出力を増やさない）。
- **上記以外の非0:** stderr を表示して停止する（未知の失敗モードを不一致として扱わない）。

### 不一致の扱い

不一致は「参照解決が返した生ヒット数」と「discovery-log に記録された行数＋除外数」が合わないこと、すなわち
**調査結果の一部がログに残っていない**ことを意味する。確定影響ファイルの取りこぼしにつながるため、そのまま次へ進んではならない。

1. 人に次を提示する:
   > ⚠️ 波紋調査の件数一致検証で不一致が検出されました（repo: {repo} / 調査: {run} / 波: {MISMATCH_WAVES}）。
   > discovery-log.md の記録が生ヒット数と一致しません。調査結果の一部が記録されていない可能性があります。
   >
   > - A: この調査をやり直す
   > - B: 不一致を承知のうえで続行する（判断を progress.md へ記録します）
2. A が選ばれた場合: 次を案内して停止する:
   > `specout_bfs.py run-remove --repo-dir {CR_PATH}/04_specout/{repo} --run {run} --today {TODAY}` で調査を取り除き
   > （`ripple/_removed/` に退避されます。クロスリポジトリ伝播の調査なら、伝播の記録も未投入に戻ります）、`{RERUN_COMMAND}` を再実行してください。
   呼び出し元が追記の文を渡した場合は、それを続けて伝える。
3. B が選ばれた場合: Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py history-add --cr-path {CR_PATH} --step 4a --text "⚠️ 件数一致検証で不一致（repo: {repo} / 調査: {run} / 波: {MISMATCH_WAVES}）。人の判断により続行。"`
   そのうえで呼び出し元へ戻り、通常のフローを継続する。
