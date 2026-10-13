# Ripple Run Outputs

> xddp-common の共通プロシージャ。波紋調査を行うスキル（xddp-04-specout・xddp-investigate・xddp-05-arch）から apply される。

## Ripple Run Outputs

完了した波紋調査1つの出力（スクリプトのみ。LLM を使わない）を、調査のディレクトリに書く。

**Input:** `CR`, `CR_PATH`, `repo`, `run`, `SPECOUT_MAX_AFFECTED_FILES`, `ONLY_SUMMARY`（true なら手順1〜3 だけ。SPO の仕上げの後に
「資料」列を新しい台帳で作り直すときに使う）

以下、`{O}` = `{CR_PATH}/04_specout/{repo}`、`{R}` = `{O}/ripple/{run}`、`PY` = `command -v python3 || command -v python` の結果、
`BFS` = `~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py`。`[--ledger …]`・`[--gap-reviewed …]` はそのファイルがある場合だけ渡す。
スクリプトが見つからない場合は setup.sh の実行を案内して停止し、exit 非0（下記で別の扱いを定めた終了コードを除く）の場合は stderr を
表示して停止する。

**Process:**
1. **モジュールの割り当て（調査の中だけ）:** `{O}/work/module-assignments.json` があれば `{R}/work/module-assignments.json` に写す
   （無ければ写しを作らない。`ONLY_SUMMARY` が true のときも写しを取り直す）。Run via Bash:
   `"$PY" "$BFS" doc-targets --path {R}/work/bfs-state.json [--ledger {O}/work/documented-files.md] --module-assignments {R}/work/module-assignments.json --auto-assign`
   **repo の割り当て（`{O}/work/module-assignments.json`）は、SPO の仕上げ（採用した調査の合算）だけが書く。** 採用していない調査で
   SPO §5.0 のモジュールの粒度が変わらないようにするため。exit 1 のモジュール名の衝突は、stderr と `{R}/work/module-assignments.json` の
   修正を人へ案内して停止する。
2. Run via Bash:
   `"$PY" "$BFS" ripple-summary --path {R}/work/bfs-state.json --discovery-log {R}/discovery-log.md [--ledger {O}/work/documented-files.md] --module-assignments {R}/work/module-assignments.json [--gap-reviewed {O}/work/prelim-gap-reviewed.md] --max-files {SPECOUT_MAX_AFFECTED_FILES} --out {R}/ripple-summary.md --json {R}/work/ripple-summary.json`
3. Run via Bash:
   `"$PY" "$BFS" ripple-digest --path {R}/work/bfs-state.json --summary-json {R}/work/ripple-summary.json --runs {O}/ripple/runs.json --run {run} [--ledger {O}/work/documented-files.md] --out {R}/ripple-digest.md`
   （`ripple-digest.md` は方式検討エージェントが読む上限つきの要約。`ripple-summary.md` は人向けの全量で、LLM には渡さない）
   `ONLY_SUMMARY` が true ならここで終わる。
4. Run via Bash:
   `"$PY" "$BFS" verify-sweep --path {R}/work/bfs-state.json --discovery-log {R}/discovery-log.md > {R}/work/verify-sweep.json`
   - exit 0: 未記録ヒットなし。
   - exit 7（未記録ヒットあり）: 人の承認を待たずに次へ進む（SPO の仕上げが、採用した調査の分を SPO §9 に転記する）。
   - それ以外の exit 非0: stderr を表示して停止する。
5. **伝播グラフ・階層表（ベストエフォート）** — 失敗しても止めない（exit 非0 なら stderr を人へ伝えて次へ進む）。Run via Bash:
   `"$PY" "$BFS" ripple-trace --path {R}/work/bfs-state.json --discovery-log {R}/discovery-log.md --summary-json {R}/work/ripple-summary.json --graph-out {R}/ripple-graph.md --tree-out {R}/ripple-tree.md`
   `ripple-graph.md`・`ripple-tree.md` は人向けで、LLM には渡さない。stdout の `omitted_module_count` または `omitted_edge_count` が
   0 より大きければ、「{repo} / {run}: 伝播グラフはモジュール・辺が多いため一部だけを描きました（全量は ripple-graph.md の §2）」と伝える。
