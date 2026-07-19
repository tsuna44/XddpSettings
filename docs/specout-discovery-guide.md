# スペックアウト（波紋検索）詳細ガイド

`/xddp.04.specout` が内部で行う Discovery BFS（波紋検索）の仕組みを説明する。
基本的なコマンド引数・成果物一覧は [README.md](../README.md) の「フェーズ一覧」を参照。
本ドキュメントは内部挙動・コンテキスト管理・実行方法の詳細を扱う。

実装の正本は以下の3ファイル。本ドキュメントの記述と食い違う場合はコードを正とする。

- [ClaudeCode/.claude/skills/xddp.04.specout/SKILL.md](../ClaudeCode/.claude/skills/xddp.04.specout/SKILL.md)（オーケストレーション）
- [ClaudeCode/.claude/agents/xddp-specout-agent.md](../ClaudeCode/.claude/agents/xddp-specout-agent.md)（Discovery BFS の hits 意味判定・classification 作成）
- [ClaudeCode/.claude/skills/xddp.04.specout/scripts/specout_bfs.py](../ClaudeCode/.claude/skills/xddp.04.specout/scripts/specout_bfs.py)（BFS 帳簿エンジン本体。visited/frontier管理・grep実行・状態遷移・discovery-log書き出しはこちらが担う）

---

## 1. 実行方法

### 1.1 トリガーフレーズ

スキル定義上の起動フレーズは「スペックアウトして」「母体調査して」「影響範囲を調べて」
（`xddp.04.specout/SKILL.md` フロントマター `description`）。
「波紋検索して」は登録フレーズではないが、意味が近いため Claude が意図を汲んで起動する可能性はある（保証はない）。

### 1.2 確実な実行方法（推奨）

CR番号とエントリポイント（探索起点シンボル）を明示したスラッシュコマンドが最も確実。

```
/xddp.04.specout {CR番号} {エントリポイント...}
```

エントリポイントは省略可能（省略時は CRS の SP 項目から自動抽出。1.3節参照）。

### 1.3 CR番号の解決

CR番号を省略した場合、`xddp.common/SKILL.md` の CR Resolution ロジックが自動検出する。

| `{XDDP_DIR}/` 配下の CR候補数 | 動作 |
|---|---|
| 0件 | エラーで停止（「CRフォルダが見つかりません」） |
| 1件のみ進行中 | 自動検出して続行 |
| 複数が進行中 | 「CR番号を引数に指定してください」と聞き返される |

specout は CR ワークフローの工程4であり、**工程3（`/xddp.03.req`）で CRS が作成済みであること**が前提。
CRS が無い状態では Wave 0 の初期シンボル抽出が成立しない。

---

## 2. 検索対象シンボルの決定方法

### 2.1 Wave 0（初期シンボル）

`xddp-specout-agent.md` Step 1 で以下を統合する。

1. **CRS の SP 項目から抽出**：コードブロック内の識別子、および「変更対象」「追加」「削除」等の動詞に続く名詞句のコード表記。識別子が不明な場合は「シンボル不明」として discovery-log に記録し人手確認を要求する
2. **インスタンスフィールドの場合**：`self.{field}` / `this.{field}` 等の属性参照パターンも追加
3. **継承伝播**：変更対象クラスのサブクラス・実装クラスを言語別パターンで検索し追加
4. **モジュール再エクスポート検索**：`export { Symbol }` 形式の re-export ファイルも記録
5. **ENTRY_POINTS 引数**：コマンドで明示的に渡したシンボル・ファイルパスも初期探索対象に加わる

### 2.2 Wave 1以降（自動拡張）

人が追加指定するのではなく、grep ヒットの文脈から機械的に次波のシンボルを導出する（伝播ルール）。

| 伝播種別 | 検出条件 | 次波へ追加するもの | 確信度 |
|---|---|---|---|
| 制御フロー | 任意のヒット行 | その行を含む関数/メソッド/クラス名 | HIGH |
| データフロー（代入） | `lhs = ... symbol ...` | lhs | HIGH |
| 引数伝播 | `func(..., symbol, ...)` | 対応する仮引数名（スコープ付き） | MEDIUM |

grep では追跡できないパターン（リフレクション・動的ディスパッチ・ジェネリクス等）は
「grep未対応パターン」として記録され、自動探索の対象にはならず人手確認を要求する。

---

## 3. リポジトリ単位 vs シンボル単位の分離

| 分離単位 | 状態 | 効果 |
|---|---|---|
| リポジトリ | 分離（独立 Agent コンテキスト。マルチリポ時は並列呼び出し） | リポジトリ間でコンテキスト・visited/frontier が混ざらない |
| 検索対象シンボル | 分離しない（波単位で複合パターン1コマンドに統合） | コマンド呼び出し数を抑制し、コンテキスト消費を削減 |

マルチリポジトリ構成では各リポジトリが独立した `discovery-log.md` / `checkpoint.md` を持ち、
Agent ツールで並列呼び出しされる（`xddp.04.specout/SKILL.md` Discovery エージェント呼び出し節）。
単一リポジトリ内では、複数シンボルを正規表現の OR パターンに結合し「1波 = 原則1コマンド」で検索する。

---

## 4. 中断耐性（チェックポイント機構）

真実の状態は `{CR_PATH}/04_specout/{repo}/bfs-state.json`（`specout_bfs.py` が読み書きする）。
`checkpoint.md` はこの JSON から自動生成される人可読ビューであり、直接編集しない
（`prune`/`merge-frontier`/`re-discover`/`finish` 等の専用サブコマンド経由でのみ状態を変更する）。

- `search` 実行時：状態の `wave_write_complete` を `false` に更新する（grep 実行結果を
  `wave-{N}-hits.json` に出力するのみで、discovery-log.md はまだ書かない）
- LLM が hits を意味判定し `wave-{N}-class.json` を作成
- `commit-wave` 実行時：discovery-log.md への Wave セクション書き出し・次波 frontier の算出・
  状態更新（`wave_write_complete: true`）を一括して行う

再開時、`status` が `wave_write_complete: false` を返す場合（`commit-wave` 前にクラッシュした場合）、
同じ `wave-{N}-hits.json` を使って classification を作り直し `commit-wave` を再実行すればよい。
discovery-log.md の書きかけ Wave セクションは `commit-wave` が自動的に切り捨てて再構築するため
（重複防止）、二重記録は発生しない。visited/frontier は波開始前の状態が bfs-state.json に
保存されているため、クラッシュで途中まで進んだ波をやり直しても探索対象シンボルが失われることはない。

件数一致検証（4.1節）は `commit-wave` が全ヒット行の classification 存在を構造的に検証したうえで
discovery-log.md へ書き出すため、書き込み自体が1トランザクションとして完結する
（旧方式にあった「検証テーブルのみ欠落する」ギャップは解消済み）。

最大探索波数（`SPECOUT_MAX_WAVE_DEPTH`）に達した場合は打ち切りではなく一時停止し、
人が継続パス A（フロンティア剪定・再開）/ B（モジュール一括記録）/ C（スコープ外承認）を選択する
（`specout_bfs.py prune` / `finish --mode complete` / `finish --mode out-of-scope` で機械化されている。
2回目の上限到達は人の確認を挟まず自動的に継続パス B が適用される）。

---

## 4.1 シンボル混在防止策（追跡可能性）

1波内で複数シンボルを複合パターン検索するため、結果の出自を追跡する仕組みが用意されている。

- **行ID・コマンドID**：全ヒット行に `W{wave}-R{n}`、実行コマンドに `W{wave}-C{n}` を付与
- **検索シンボル列**：ヒット行ごとに、複合検索パターンのうち実際にマッチしたシンボル名
  （MEDIUM の場合は `symbol[MEDIUM:scope_file]`）を明示する。1コマンドで複数シンボルを
  複合検索した場合でも、行を読むだけでどのシンボルのヒットかが分かる
- **SYMBOL_ORIGIN_MAP**：新規発見シンボルがどの行（＝どの元シンボル）から伝播したかを波ごとに記録・継承
- **visited セットのスコープ分離**：HIGH（全域）と MEDIUM（`(symbol, scope_file)` ペア）を別管理し、同名シンボルが異なるスコープで混同されないようにする
- **件数一致検証**：複合検索コマンドのヒット数と discovery-log.md に記録された行数を波ごとに突合し、不一致があれば `⚠️` マーカーを記録

不一致マーカーは自動停止ではなく可視化止まり（人レビュー時に気づく前提）。
長時間の specout 実行後は discovery-log.md の「件数一致検証」セクションに `⚠️` が残っていないか確認すると安全。

---

## 5. 未確認・既知のギャップ

- bfs-state.json / discovery-log.md 自体のファイル書き込み操作は `specout_bfs.py` 内で逐次実行されるが、
  プロセス自体が書き込み途中で強制終了された場合の部分書き込みまでは保証しない（4節の再開手順で復旧する）
- 1波内で HIGH grep と MEDIUM grep 群を並列実行する設計だが、`specout_bfs.py` の現行実装は
  Bash 内で逐次実行している（結果の正しさに影響はないが、大規模リポジトリでは波あたりの実行時間が
  シンボル数・スコープファイル数に比例して伸びる点は留意）
- 継続パスA（フロンティア剪定）は `specout_bfs.py prune` の形式検証を通るため、
  旧方式で発生していた `checkpoint.md` 手動編集時の書式崩れ（`[MEDIUM:...]` 形式の欠落等）は解消済み
