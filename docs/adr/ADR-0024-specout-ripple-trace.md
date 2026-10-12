# ADR-0024: 波紋調査の伝播グラフ（モジュール単位）と関数単位の階層表を discovery-log から作る理由

Status: Accepted（承認済み）
Date: 2026-10-12

- プラン: [plans/PLAN-20261012-specout-ripple-trace.md](../../plans/PLAN-20261012-specout-ripple-trace.md)（P3）。
  [PLAN-20260829-specout-ripple-trace-graph](../../plans/PLAN-20260829-specout-ripple-trace-graph.md) は廃止し、本 ADR の決定で置き換える
- 前提 ADR: [ADR-0019](ADR-0019-specout-static-slicer.md)（discovery-log の表の列の構成は変えない）、
  [ADR-0021](ADR-0021-specout-symbol-identity.md)・[ADR-0022](ADR-0022-specout-cpp-class-identity.md)（同一性 `resolved`／`name-only`）、
  [ADR-0023](ADR-0023-specout-two-layer-output.md)（出力の2層化・`ripple-summary.md`）
- 調査記録: [docs/specout-redesign-study-2026-10.md](../specout-redesign-study-2026-10.md)（§4.2・§6 の P3）

## Context

- ADR-0023 で、波紋調査の結果は「LLM 向けの上限つきの要約（SPO §5.0）」と「人向けの全量（`ripple-summary.md`）」の2層になった。
  `ripple-summary.md` は「どのモジュール・ファイルに届いたか」を全量で示すが、経路はファイルごとに代表1本だけである。
- P2・P2b の後も、frr の確定 444 件のうち 168 件が名前の一致のみ（`name-only`）で届いている（調査記録 §5.4）。
  人が誤った到達を見分けるには、届いた先だけでなく、どのシンボルを経由してどの関数から届いたかを追える必要がある。
- PLAN-20260829 は `commit-wave` が構造化データ `ripple-edges.jsonl` を追記し、関数単位のグラフと経路ごとに重複表示する階層表を作る設計だった。
  その後、`ripple-summary` が discovery-log のヒット表を読み直す関数（`_parse_log_hits`）を持ち、派生元の行IDがヒット表の「派生元」列に残ることが確かめられた。
  また M2（frr・CR-2026-803 の discovery-log。P2 適用前）の試算で、関数単位では 4,691 ノード・13,941 辺になり、
  Mermaid の辺の上限 `maxEdges` の既定 500 を大きく超える。経路ごとの重複表示の階層表は約 13,900 行・約 1.8MB になる。

## Decision

### 1. discovery-log を唯一の情報源にする

`ripple-trace`（`specout_bfs.py` のサブコマンド）は discovery-log のヒット表と `work/ripple-summary.json`（モジュールの割り当て）と
state の `repo_path`・`slice_engine` だけを読み、`ripple-graph.md` と `ripple-tree.md` を書く。`commit-wave`・state・discovery-log の表の列は変えない。
`_parse_log_hits` は「検索シンボル」のエントリ文字列（`[FILE:…]`・`[CLASS:…]` の修飾を残す）と「同一性」列も返す。

### 2. グラフはモジュール単位、関数単位の経路は階層表で見る

- `ripple-graph.md`: ノードは `ripple-summary.json` の全モジュールと起点（`seed(X)`・`seed-global(X)`・`unknown-origin`）。
  辺はモジュールの組ごとの「関数の組」（シンボルの送り手の関数 × そのシンボルが届いた関数）の数と、そのうち `resolved`・`name-only` の数。
  同じモジュールの中の伝播は表（§2）にだけ載せる。
- 描くモジュールは 60 個（`RIPPLE_GRAPH_MAX_MODULES`）、描く辺は 400 本（`RIPPLE_GRAPH_MAX_EDGES`。`maxEdges` の既定 500 より小さく）まで。
  超えた分はグラフの直前に ⚠️ で知らせ、全量は表に残す。上限はスクリプトの定数で、設定キーにしない（ADR-0023 の行数の上限と同じ扱い）。
- モジュールの「第N波〜」は、ファイルごとの波（discovery-log の行の最小の波と state の確定の波の小さい方）の最小を使う。
  state の確定の波は確信度が上がると後の波に書き換わり、行だけから求めると前倒し縮退で代表外だったファイルの波が落ちるため。
  state の確定の波から来た場合は「（確定の波）」を添える。

### 3. 階層表は各ノード（ファイル, 関数）を1回だけ置く

ノードの代表行（波が最も小さく、同じ波ではログの出現順で先の行。`ripple-summary` と同じ）の最初の派生元を親とする。
他の派生元は件数と最大3件の参照で示す。行数はノード数と同じになり、経路ごとの重複表示の約3分の1になる（M2 の試算）。
各行に行ID を出し、discovery-log と突き合わせられるようにする。
「関数」列の先頭に罫線（`├`・`└`・`│`。字下げは全角空白で、1段は全角約1文字）を付け、番号に加えて字下げでも階層が見えるようにする（2026-10-12 追記）。
入れ子のリストは字下げの幅と入れ子の解釈がビューアによって変わり、列（行ID・同一性・波）も失うため採らない。

### 4. 辺の同一性は送り手の行と受け手の行の両方から決める

行の組（派生元の行 → 受け手の行）の同一性は、両方の行の「同一性」がともに `resolved` なら `resolved`、それ以外は `name-only`
（派生元が起点なら受け手の行の同一性）。関数の組は、行の組の1つでも `resolved` なら `resolved`。
受け手の行の同一性は「ヒット自身」∧「検索したエントリの同一性」で、エントリの同一性は送り手の**どれか1つ**が `resolved` なら `resolved` になる。
一方、派生元はそのエントリの全送り手であるため、受け手の行だけで決めると名前の一致のみの送り手からの辺も `resolved` になる。
グラフは `resolved` を含む辺を実線、含まない辺を点線で描く。階層表の「同一性」は親から届いた行の組の同一性。

### 5. 設定キーを作らず、LLM に渡さない

波紋調査を行った repo では常に両ファイルを作る（Step A-Document の手順8。ベストエフォートで、失敗しても工程を止めない）。
SPO にはリンクを書かず、後工程の LLM・SPO レビューの入力にも含めない。人への案内は Step A3 の成果物一覧と `ripple-summary.md` の冒頭の注記。

### 6. 手順8 は Step A-Document の末尾に置く

`ripple-summary.json` の最終版（追加下調べの後に取り直したもの）を使うため、既存の手順の番号と参照を保つため、
番号の並びをそのまま実行順にするため。`ripple-trace` は入力を読む前に前回の2ファイルを消し、失敗した repo には2ファイルが残らない。

## 代替案と棄却理由

| 代替案 | 棄却理由 |
|---|---|
| `commit-wave` が `ripple-edges.jsonl` を追記する（PLAN-20260829） | discovery-log と情報源が二重になり、波の再実行時の重複追記への対策が要る。派生元の行IDはヒット表に既にある |
| 関数単位のグラフ | M2 で 4,691 ノード・13,941 辺。Mermaid で描けない |
| 経路ごとに重複表示する階層表（2026-09-22 の合意） | 行数が約3倍（約 13,900 行・約 1.8MB） |
| 設定キー（`SPECOUT_RIPPLE_GRAPH` 等） | ADR-0023 で資料化の設定キーを廃止した方針に合わせる |
| 辺の同一性を受け手の行だけで決める | 名前の一致のみの送り手からの辺が `resolved`（実線）になる |
| 手順6 の直後（手順6.1）に置く | 手順7 で止まっても両ファイルが残るが、手順7 で止まったときに人が調べるのは document agent の返答と lint の結果で、グラフ・階層表はその原因を示さない。末尾なら「手順1〜8」の範囲と番号の並びがそのまま実行順になる |

## Consequences

- discovery-log の表の列を変えると、`funcmap-counts`・`specout_verify_counts.py`・`ripple-summary` と同じく `_parse_log_hits` の追従が要る（ADR-0019 の「表の列の構成は変えない」と同じ制約）。
- **辺の同一性が `resolved` 側へ誤る場合が残る。** 送り手の行が `resolved` でも、その行の判定がそのシンボルだけを名前の一致のみとした場合
  （classification の `name_only_symbols`）、送り手からそのシンボルへの経路は `name-only` である。`name_only_symbols` は discovery-log に残らないため、
  別の送り手が `resolved` で届けていると `resolved` と判定する。直すには「Wave {N+1} 追加シンボル」列に印を残す等の表の書式の変更が要り、別プランで扱う。
- 同一性はスライス判定のヒットにだけ付く。LLM 分類の言語（C / C++ / Python 以外）と規則判定のヒットからの辺は常に点線・`name-only`（未検証の意味）。
  `resolved` の行が1行も無い repo では両ファイルの冒頭に注記を書く。
- 階層表の祖先はノード（関数）単位でつながるため、2段以上さかのぼると `ripple-summary.md` の「影響の経路の代表」（行単位で最初の派生元をたどる）と別の行を通ることがある。
- 両ファイルは `04_specout/{repo}/` 直下にあり、Human Review Gate のレビューブリーフの不確実性マーカーの走査と前工程差分の対象になる。
  固定の文言には「MEDIUM」「（要確認）」「（推定）」を書かない（スコープを限った引数のエントリは「（引数・スコープ）」と書く）。
  行数の多い `ripple-tree.md` はブリーフの目安時間を押し上げる（本 ADR ではブリーフの集計を変えない）。

## 再検討条件

- cross（複数の repo の伝播を1枚にまとめる図）が必要になったとき。
- 階層表の祖先と `ripple-summary.md` の代表の経路の食い違いで人が混乱したとき（`_hit_path` をノード単位に変えると SPO §5.0 が変わる）。
- 送り手ごとの名前の一致のみの記録を discovery-log に残すとき（辺の同一性の誤りを無くせる）。
