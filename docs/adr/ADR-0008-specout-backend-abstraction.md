# ADR-0008: Discovery BFS の参照解決を差し替え可能な Backend として抽象化する

Status: Accepted
Date: 2026-08-01

## Context

Discovery BFS（`xddp.04.specout/scripts/specout_bfs.py`）の参照解決は本質的に
「シンボル名の文字列一致（grep/ripgrep）」であり、構造的に2つの誤差を抱える（分析レポート
`docs/xddp-ai-devtool-analysis-2026-07.md` の弱み W5）。

- **偽陽性:** 同名別物（複数クラスの `close()` 等）を区別できない。現行はこれを補償するため
  高ノイズ判定・MEDIUM スコープ管理・同名 MEDIUM のケース A/B/C 分岐といった複雑な規則群を積み上げている。
- **偽陰性:** grep で追えない動的系パターン（リフレクション・動的ディスパッチ・DI・イベント駆動・
  Go のインタフェース暗黙実装・デコレータ等）。これらは「本番で静かに壊れる」箇所に集中する。

型付き言語では LSP の参照検索・タグDB（ctags/GNU Global 系）・AST/コールグラフツールが参照解決を
決定的に行える。上記の複雑な補償規則の多くは「grep に型情報がない」ことへの代償であり、
参照解決を言語ツールへ委ねればその大半が不要になりうる。

実地調査の結果、grep/rg 実行は 100% 機械側（`specout_bfs.py` の `cmd_search`）に閉じており、
LLM の意味判定契約（`wave-{N}-hits.json` / `wave-{N}-class.json`）と `commit-wave` の帳簿ロジックは
参照解決の実装に依存しないことが確認された。したがって参照解決だけを差し替え可能にする
「継ぎ目（seam）」を低コストで導入できる。

## Decision

参照解決を **Backend プロトコル**（`search(symbols, scope) -> list[SearchCommand]`）として抽出し、
`SPECOUT_BACKEND` 設定でバックエンドを選択できるようにした（段階1）。

- `SearchCommand`（`pattern_repr` / `rows` / `candidates`）を返却単位とし、**コマンド分割の粒度を
  バックエンドが所有する**。これにより grep 経路が `_batch_symbols` で生む「複数コマンド」構造と
  跨バッチのシンボル帰属（`candidates`）が失われず、既存挙動をバイト等価に保つ。
- `GrepBackend`（HIGH を複数 SearchCommand へ分割）／`RgBackend`（patternfile で単一 SearchCommand）を
  現行の grep/rg 経路から再配置した。`cmd_search` は `resolve_backend(data)` の1点で実装を解決し、
  command_id/line_id 採番・シンボル帰属・帳簿構築は従来どおり `cmd_search` に残す。
- 既定は `auto`（rg があれば rg・無ければ grep）で**挙動不変**。`ctags`/`global`/`lsp` 等の静的
  バックエンドは段階2以降で実装し、未実装・バイナリ不在時は **grep へ明示フォールバックし警告を
  discovery-log と bfs-state.json に記録する**（無音の縮退を禁止）。

**不変条件（バックエンドを差し替えても変わらないもの）:**

- **LLM の classification 契約**（`wave-{N}-class.json` スキーマ）と `commit-wave` の帳簿ロジックは
  バックエンド非依存であり変更しない。`xddp-specout-agent.md` の classification 契約・参照解決手順・
  帳簿説明の本文も編集しない（エージェントの編集は `init --backend` の機械的配線に限定）。
- **grep未対応の動的系パターンの記録機構**（discovery-log の「grep未対応パターン」節）は維持する。
  リフレクション・DI・イベント駆動等の動的参照は**どのバックエンドでも残る**ため、人手確認記録の
  仕組みは引き続き必要である。

## Consequences

- 段階1は純リファクタ（挙動不変・新規外部依存なし・標準ライブラリのみ）であり、以降の静的
  バックエンド追加を `commit-wave`・LLM 契約・エージェント本文に触れずに行える基盤投資となる。
- 設定は既定 `auto` で「設定しなくても従来どおり」を保証。REPOS エントリ単位の上書き
  （`SPECOUT_BACKEND.{repo}`）で言語別のバックエンド選択に備える。`SPECOUT_BACKEND_BIN` は
  段階2以降の外部バイナリ解決用にキー名のみ予約した。
- **本文へ設計根拠を混入させない**方針（分析レポート P9）に従い、抽象化の設計判断は本 ADR に集約する。
  スキル・エージェント本文には参照1行のみを置く。
- **再検討条件:** 段階2で静的バックエンドを実装する際、定義DB（ctags）は「剪定用」・参照DB/LSP は
  「探索用」であり性質が異なる点を別プランで明確化する。また `xddp-specout-agent.md` の Wave 0
  継承伝播 grep（エージェントが BFS 本体の外で直接行う参照解決）の抽象化は本段階では非対象とし、
  段階2で「継承関係もバックエンドへ問い合わせる」拡張余地として扱う。
