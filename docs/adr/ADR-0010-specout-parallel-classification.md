# ADR-0010: Discovery BFS の波内 classification をチャンク並列化する理由

Status: Accepted
Date: 2026-08-09

## Context

Discovery BFS（`xddp.04.specout/scripts/specout_bfs.py`）は、1波のヒット数が多い場合、その波の
全ヒット行を単一コンテキストで LLM が判定する classification が壁時計のボトルネックになる
（`PLAN-20260804-specout-performance.md` の親プラン計測で確認済み。ADR-0009 の前倒し縮退・
簡易 module-priority は「分類対象そのものを削る」対策であり、削った後も残る分類量に対する
レイテンシ対策は別軸として必要だった）。

Stage 1（`classify_wall_ms` 等の metrics 追加）の実測（`PLAN-20260806-specout-phase3-stage1-measurement.md`）
で、`classify_wall_ms ≥ 60,000ms` の波が有効波の 20% 以上を占め、該当波の `classified`
（post-dedup/filter の実分類行数）中央値が既定チャンクサイズ 40 の2倍に達するというゲート条件が
成立した。

判定手順は「今波の他ヒット行（current-wave-hits）」「前波 frontier」「visited」への参照を含み、
かつ CRS が定義する変更スコープの理解に依存するため、素朴なチャンク分割は判定入力を縮小し、
探索漏れまたは探索肥大を招く（親プランの不変条件「確定影響ファイルの取りこぼしゼロ」に抵触する）。

## Decision

### ループ移設先: SKILL（案X）

BFS ループ（`search` → 分類 → `commit-wave`）の実行主体を、Discovery 用サブエージェント
（`xddp-specout-agent`）から、Agent ツールを保持するオーケストレータ（`xddp.04.specout/SKILL.md`）へ
移設した。

代替案（案Y: `xddp-specout-agent` 自身に Agent/Task ツール権限を付与し、エージェントが波ごとに
分類サブエージェントを並列起動する）は不採用とした。理由:

1. このリポジトリの `ClaudeCode/.claude/agents/*.md` にネストしたサブエージェント起動の前例がなく、
   分離度・レビュー可能性が未検証（Stage 1 の最小スパイクで技術的な起動可否のみは確認できたが、
   `tools:` への `Agent` 明示列挙で当該ツールが実際に付与されるかは別セッションでの検証が必要なまま）。
2. エージェントが「自身の BFS 状態管理」と「子エージェントの並列制御」を同時に担うことになり、
   CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」の役割分離に逆行する。
3. `tools:` の拡張は最小権限方針と要調整。

案Xは「決定的処理のスクリプト集約」「状態の単一書き手維持」という既存アーキテクチャ方針に整合する
一方、「BFS ループをサブエージェントに隔離する」という Stage 1 までの設計方針を反転させるため、
オーケストレータのコンテキスト蓄積が新たなリスクとなる（下記「コンテキスト蓄積対策」参照）。

`xddp-specout-agent` は `MODE: discovery-setup` へ再定義し、Wave 0 のシンボル構築・BFS state
初期化・code-knowledge 参照のみを担う（`init` 実行のみで `commit-wave` を実行しないため、
`confirmed_files` は常に空 — 既存の code-knowledge 参照 no-op 欠陥は本変更のスコープ外として
`agents/xddp-specout-agent.md`「スコープ外として記録する既存欠陥」に記録し、別プランで対応する）。
波ごとの意味判定は新設の `xddp-specout-classifier-agent`（チャンク1件を読み classification を
書き出す軽量エージェント。`tools: Read/Grep/Write`）へ逐語移設した。

### 判定入力の等価性: `known_symbols` の明示複製

`search` の出力に `known_symbols`（`visited`/`searched_frontier`/`current_wave` を素名正規化した
配列）を追加し、全チャンクへ同一内容を複製配布する。CRS が定義する変更スコープの理解は
`CRS_FILE` を classifier の Inputs として都度渡すことで回復する。これにより「チャンク分割によって
判定入力が単一コンテキスト時より狭まらない」という不変条件を、分割境界に依存しない決定的な参照へ
置き換えた。

### 単一書き手の維持

`bfs-state.json`・`discovery-log.md` の書き手は `commit-wave`（Bash・単一）に集約したまま変えない。
並列化するのは classification のみであり、classifier の Write 先はチャンク単位の `OUT_FILE` のみ
とする。grep未対応パターンの discovery-log 追記も、classifier が `unsupported_patterns` として
`OUT_FILE` へ報告し、`commit-wave --unsupported-patterns` が単一書き手として追記する
（並列 classifier が discovery-log.md を各自 Edit すると書き込み競合が起きるため）。

チャンク結果の結合・検証（line_id 欠落/重複/未知値検出・unsupported_patterns 集約・チャンク mtime
収集）は新規スクリプト `merge_classification.py`（決定的処理）が担う。`commit-wave` の入力契約
（`--hits`/`--classification` の形式）は変更しないため、下流の集約ロジック（HIGH/MEDIUM 交差・
ケースA/B/C分岐・高ノイズ判定）は無改修のまま並列化の恩恵を受ける。

### コンテキスト蓄積リスクの緩和

波ループが SKILL 側へ移ることで、メインコンテキストに「波数 × リポジトリ数」分の履歴が蓄積する
リスクが生じる。`search`/`commit-wave` の stdout を必要キーのみへ絞り、`status --brief`
（判定に必要な最小キーのみを返す軽量出力）を新設して波ごとの `status` 呼び出しを回避することで
緩和した。将来的にこれでも枯渇する場合の退避先（repo ごとの wave driver を別サブエージェントへ
切り出す構成）は、案Y の実現可否（`tools:` への `Agent` 明示列挙）に依存するため、必要になった
時点で改めてスパイクを行う。

## Consequences

- 1波のヒット数が多い場合の壁時計レイテンシは、`chunk_count` 分の並列度で短縮される。トークン総量は
  ほぼ不変（並列化は時間短縮であってトークン削減ではない）。実測ではチャンク固有情報を起動プロンプト
  末尾に置きプレフィクスをバイト同一に保つ設計要件を満たす場合、プロンプトキャッシュにより固定
  ブートストラップ分の複製コストがキャッシュ共有で実質無害化される
  （`PLAN-20260806-specout-phase3-stage1-measurement.md` §5.5・§5.6）。要件を満たさない実装では
  トークン増分が現行実測の2倍を超える現実的なケースがある。
- マルチリポジトリの分離モデルが変わる: 従来は「リポジトリ＝独立 Agent コンテキスト」だったが、
  波ループ移設後は discovery-setup（Wave 0 構築）のみがリポジトリ単位で分離し、波ループ本体は
  SKILL が全リポジトリを単一コンテキストで駆動する。リポジトリ間の並列度は「1波あたり全リポジトリの
  チャンクを合算してバッチ起動する classifier」で維持する。
- `SPECOUT_CLASSIFY_CHUNK_SIZE: 0` で分割を完全に無効化でき、常に単一チャンク（移設前と同一の
  分類）に戻せる（退路の担保）。ループ移設自体も定義ファイルの `git revert` で復元可能だが、
  移設後に開始した進行中 CR の途中状態は追従しない（後方互換性ポリシー上、再実行を求めてよい）。
- **再検討条件:** コンテキスト蓄積が実測で許容量を超えると判明した場合、案Y（波ドライバのサブ
  エージェント化）の実現可否を別セッションで再スパイクしたうえで退避先の設計に着手する。
