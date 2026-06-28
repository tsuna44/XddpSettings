# XDDP プロジェクト設定

このファイルをプロジェクトルートに置くことで、XDDPの各フェーズの動作をプロジェクトごとに調整できます。

---

## 成果物ディレクトリ設定

```
XDDP_DIR: xddp
```

XDDP の成果物（CR フォルダ・latest-specs・project-rulebook.md 等）を配置するディレクトリ。
ワークスペースルートからの相対パスで指定する（xddp.config.md と同じディレクトリが基点）。
デフォルト: `xddp`

```
# 例: XDDP_DIR: xddp  →  workspace/xddp/
# 例: XDDP_DIR: repo-A/xddp  →  workspace/repo-A/xddp/  リポジトリ内に置く場合
```

```
CR_PREFIX: CR
```

CR フォルダ名のプレフィックス。自動検出時に `{CR_PREFIX}-` で始まるディレクトリを CR として認識する。
スキル実行時に引数がこのプレフィックスに合致するかで CR 番号か否かを判定する。
デフォルト: `CR`

```
# 例: CR_PREFIX: CR   → CR-2026-001 を CR として認識
# 例: CR_PREFIX: REQ  → REQ-2026-001 を CR として認識
```

## 知識ハブディレクトリ設定

```
DOCS_DIR: baseline_docs
```

承認済み仕様書・知見ログを集約する中央知識ハブのパス。
ワークスペースルートからの相対パスで指定する（xddp.config.md と同じディレクトリが基点）。
デフォルト: `baseline_docs`

```
# 例: DOCS_DIR: baseline_docs  →  workspace/baseline_docs/
# 例: DOCS_DIR: repo-A/baseline_docs  →  workspace/repo-A/baseline_docs/  リポジトリ内に置く場合
```

---

## 開発モード設定

```
DEVELOPMENT_MODE: change
```

開発モードを指定する。
- `change`（デフォルト）: 既存コードへの変更（通常の CR）。工程04（スペックアウト）を実行する
- `new`: 新規開発（母体コードが存在しない状態からの開発）。工程04・05をスキップする

```
# 例: 既存システムへの機能追加 → DEVELOPMENT_MODE: change（デフォルトのため省略可）
# 例: ゼロからの新規開発       → DEVELOPMENT_MODE: new
```

---

## 0. リポジトリ設定

```
REPOS:
  repo-a: ../repo-a
```

対象リポジトリのパスマッピング。
パスはこのファイル（xddp.config.md）からの相対パス、または絶対パスで指定する。

**【重要】記載するリポジトリの選択:**
この作業セッションで修正可能性があるリポジトリのみ列挙する（例: VSCode ワークスペースに追加したリポジトリ）。
全リポジトリを列挙するのではなく、関係するものだけに絞ること。
XDDP の各フェーズはここに列挙された全リポジトリをスペックアウト・設計・実装対象として扱う。

**エントリ数による動作切り替え:**
- 1エントリ → シングルリポジトリ相当。`cross/` 成果物は生成しない
- 複数エントリ → マルチリポジトリ相当。`cross/` 成果物（SPO・DSN・CHD・TSP）を生成する

```
# 1エントリ（シングルリポジトリ）の例:
# REPOS:
#   my-app: ../my-app

# 複数エントリ（マルチリポジトリ）の例:
# REPOS:
#   tasksaas-api: ../tasksaas-api
#   tasksaas-worker: ../tasksaas-worker
#   tasksaas-notify: ../tasksaas-notify
#   tasksaas-shared: ../tasksaas-shared
```

**【重要】キー名の制約:**
- 左辺キーはリポジトリの実際のフォルダ名をそのまま使うこと（省略名禁止）
  - OK例: `tasksaas-api: ../tasksaas-api`（フォルダ名と一致）
  - NG例: `api: ../tasksaas-api`（省略名のため不可）
- **`cross` は予約名のため REPOS: のキーとして使用禁止。**
  `cross/` ディレクトリはシステムが自動生成するクロスリポジトリ成果物の格納先であり、
  リポジトリ名との衝突を防ぐため予約されている。

---

## 1. スペックアウト設定

### スペックアウト検索設定

```
SPECOUT_EXCLUDE_PATTERNS: tests/,test/,__tests__/,spec/,specs/,__mocks__/,fixtures/,vendor/,node_modules/
```

Discovery BFS でプロダクションコード以外を除外するパターン（カンマ区切り）。
`/` で終わるエントリはディレクトリとして `--exclude-dir` / `rg -g '!{x}'` に展開される。
`/` で終わらないエントリはファイルパターンとして `--exclude` / `rg -g '!{x}'` に展開される。
デフォルト: `tests/,test/,__tests__/,spec/,specs/,__mocks__/,fixtures/,vendor/,node_modules/`

**注意:** テスト除外は波及伝播のノイズ低減が目的。
既存テストの調査（SPO Section 5.5）はプロダクションファイルに対応するテストファイルを別途検索して実施する。

```
SPECOUT_INCLUDE_EXTENSIONS: .py,.go,.ts,.java,.kt,.swift,.rs,.cpp,.c,.h
```

Discovery BFS で検索対象とするファイル拡張子（カンマ区切り）。
`grep --include` / `rg -g` オプションに展開される。
空の場合は全ファイルを対象とする（オプションなし）。
デフォルト: 空（全ファイル）

```
# 例: .py,.go の場合は Python と Go ファイルのみを検索対象とする
```

```
SPECOUT_MAX_WAVE_DEPTH: 10
```

Discovery BFS の最大波数上限。
超過時は探索を終了せず一時停止（`paused-at-limit`）し、人が継続パス A/B/C を選択する。
デフォルト: `10`

```
# 継続パス A: フロンティアを剪定して BFS を再開（checkpoint.md を手動編集後に再実行）
# 継続パス B: 残存フロンティアのモジュールを一括記録して完了（MODULE-LEVEL として SPO に記録）
# 継続パス C: 残存フロンティアをスコープ外として根拠を記録して完了
```

### CR 分割警告ライン

```
SPECOUT_MAX_AFFECTED_FILES: 20
```

波及調査は打ち切らず全依存を追い切る。
直接・間接の波及ファイル数がこの値を超えた時点で CR 分割を推奨する警告を出す。
警告後も調査は継続し、判断（続行 or 分割）は人間が行う。
デフォルト: 20

### モジュールファイル分割ライン

```
SPECOUT_MAX_FILES_PER_MODULE: 10
```

1 モジュール内の波及ファイル数がこの値を超えた場合、
そのモジュールのスペックアウトファイルをサブモジュール（サブディレクトリ）単位に分割して出力する。
分割後の構成:
  - `modules/{module-name}-spo.md` → インデックス（概要 + サブモジュールへのリンク表）
  - `modules/{module-name}/{subdir}-spo.md` → サブモジュール個別詳細
サブディレクトリが存在しない場合（全ファイルがモジュールルートに集中）は分割せずそのまま出力する。
デフォルト: 10

### 調査粒度

```
SPECOUT_DIAGRAM_LEVEL: standard
```

生成するダイアグラムの範囲。以下から選択：
- `minimal` : 機能ソースコード対応表（6.1）のみ
- `standard` : 6.1〜6.4, 6.7, 6.8（機能対応表・構造図・シーケンス図・状態遷移図・クラス図・データ構造）
- `full`     : 6.1〜6.9 すべて（CRUD・ER・PAD含む）

**重要:** `standard`（デフォルト）では SPO サマリーの §4.3（データモデル）と §4.4（データアクセスマトリクス）が「対象外」となるため、
`latest-specs/overview/data-model.md` と `latest-specs/overview/crud.md` は生成されません。
データモデル・データアクセスマトリクスを知識ベース（latest-specs）に蓄積したい場合は `full` に設定してください。

### シーケンス図の粒度

```
SPECOUT_SEQUENCE_LEVELS: module, class
```

シーケンス図（6.3）を生成するエンティティレベルをカンマ区切りで指定。
複数指定した場合はレベルごとに独立したシーケンス図を生成する。

指定可能なレベルと用途:
- `repository` : リポジトリ（マイクロサービス・DB・外部API）間の通信フロー。
                 マイクロサービス構成や外部API連携がある場合に追加する。
                 単一リポジトリのモノリスでは情報量が薄くなるため省略推奨。
- `module`     : モジュール／パッケージ間の呼び出しフロー。
                 変更が他モジュールへ波及するか把握でき、影響範囲分析に直結する。
                 XDDPの波紋検索と最も相性が良い。
- `file`       : ソースファイル間の呼び出しフロー。
- `class`      : クラス間のメソッド呼び出しフロー。
                 設計書（CHD）のBefore/After記述の根拠になり、設計工程への橋渡しになる。
- `function`   : 関数／メソッド間の詳細呼び出しフロー。
                 詳細すぎて保守コストが高くなるため、複雑なアルゴリズムや
                 非同期処理など特定箇所に限定するのが一般的。

デフォルト: `module, class`

---

## 2. レビュー設定

### AIレビュー最大回数

成果物種別ごとに AI レビューループの最大回数を指定する。
この値を超えても未解決の指摘が残る場合は警告を出して人間レビューゲートへ進む。

```
REVIEW_MAX_ROUNDS:
  ANA: 2
  CRS: 2
  SPO: 3
  DSN: 2
  CHD: 2
  TSP: 2
  SPEC: 2
  PLAN: 3
```

種別の対応：`ANA`=要求分析、`CRS`=変更要求仕様書、`SPO`=スペックアウト、
`DSN`=実装方式設計書、`CHD`=変更設計書、`TSP`=テスト仕様書、`SPEC`=最新仕様書（全リポジトリ・cross/ 共通）、
`PLAN`=実装プランレビュー（xddp.plan-review スキル用）

```
FIX_STRATEGY:
  PLAN: ideal
  ANA: balanced
  CRS: balanced
  SPO: balanced
  DSN: balanced
  CHD: balanced
  TSP: balanced
  SPEC: balanced
```

`FIX_STRATEGY` は AI レビューで指摘された問題の修正方針を工程種別ごとに指定する。
- `ideal`（PLAN デフォルト）: 複数案がある場合、影響範囲が広くても本来あるべき姿（理想状態）の案を選択する。
- `balanced`（その他デフォルト）: 複数案がある場合は人に確認する（xddp.plan-review のみ有効。AI フィクサーエージェントでは `ideal` と同等に動作する）。
- `efficiency`: 複数案がある場合、最小インパクトの案を選択する。

`REVIEW_MAX_ROUNDS` と同様に種別ごとに設定し、未記載の種別は上記デフォルト値を使用する。

---

## 3. テスト設定

### テストフレームワーク

```
TEST_FRAMEWORK: auto
```

使用するテストフレームワークを指定。`auto` の場合はソースコードから自動検出する。
例: `pytest`, `unittest`, `JUnit`, `Jest`, `Vitest`, `Go testing`, `RSpec`

`REPOS:` に複数リポジトリが定義されている場合、リポジトリごとに個別指定できる
（指定のないリポジトリは `TEST_FRAMEWORK` にフォールバック）。

```
# TEST_FRAMEWORK_REPOS:
#   api: pytest
#   worker: pytest
#   notify: pytest
#   shared: pytest
```

### テストケース粒度

```
TEST_CASE_MAX_COUNT: 50
```

テストケース数がこの値を超えたら CR 分割の警告を出す。
デフォルト: 50

```
TEST_COVERAGE_TARGET: C1
```

目標カバレッジ。以下から選択：
- `C0` : ステートメントカバレッジ 100%
- `C1` : ブランチカバレッジ 100%（デフォルト）

```
MIN_COVERAGE: 80
```

`MIN_COVERAGE` はカバレッジ（TEST_COVERAGE_TARGET で指定した種別）の合格閾値（%）。
この値以上でテスト自動合格。未満の場合は人が A（承認）/ B（テスト追加）を選択する。
デフォルト: `80`

```
# 例: 100 → すべてのコードパスを網羅しないと自動合格しない（厳格モード）
# 例: 0 → TC 全パスのみで自動合格する（カバレッジ未計測環境向け）
# 移行注意: 本設定導入前の旧動作は 100% 強制だった。従来の動作を維持する場合は 100 に設定。
```

```
TEST_BOUNDARY_VALUES: true
```

境界値テストケース（min / min+1 / max-1 / max）を生成するか。
デフォルト: `true`

```
TEST_REGRESSION: true
```

SPO の間接影響範囲（Section 3.2）から回帰テストケースを生成するか。
デフォルト: `true`

---

## 4. 設計（CHD）ファイル分割設定

```
DESIGN_MAX_SP_PER_FILE: 10
```

1つのUR内のSP数がこの値を超える場合、CHD生成をバッチファイルに分割する
（`CHD-{CR}-{UR-ID}.md` → `CHD-{CR}-{UR-ID}-1.md`, `-2.md`, ...）。
1回の `xddp-designer-agent` 呼び出しが処理するSP数の上限。
デフォルト: `10`

**注（暫定値であることの明示）:** この `10` という値は、1SPあたりの平均出力トークン数からの
厳密な逆算ではなく暫定値である。運用しながら実測（実際に出力欠落が起きた／起きなかったCRの規模）に
基づき調整する前提の値である。欠落が観測された場合は値を下げ、逆に小規模CRで過剰にファイルが
分割される場合は値を上げる。

```
DESIGN_MAX_SYMBOLS_PER_FILE: 30
```

生成後の1ファイルあたりの変更シンボル数（CHD Section 4 行数）がこの値を超えた場合、
人レビューゲートで警告を表示する（自動分割はしない。人が `/xddp.revise` で手動分割する）。
デフォルト: `30`

**理由:** UR-035（CR全体の500行/50シンボル閾値によるCR分割推奨）とは目的が異なる、
ファイル単位の出力安全性のためのしきい値であるため、`TEST_CASE_MAX_COUNT` 等とは別の新規キーとする。
