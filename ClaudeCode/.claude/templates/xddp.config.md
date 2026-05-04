# XDDP プロジェクト設定

このファイルをプロジェクトルートに置くことで、XDDPの各フェーズの動作をプロジェクトごとに調整できます。

---

## 成果物ディレクトリ設定

```
XDDP_DIR: xddp
```

XDDP の成果物（CR フォルダ・latest-specs・project-steering.md 等）を配置するディレクトリ。
ワークスペースルートからの相対パスで指定する（xddp.config.md と同じディレクトリが基点）。
デフォルト: `xddp`

```
# 例: XDDP_DIR: xddp  →  workspace/xddp/
# 例: XDDP_DIR: repo-A/xddp  →  workspace/repo-A/xddp/  リポジトリ内に置く場合
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

```
REPO_NAME: repo-A
```

baseline_docs/ 以下のリポジトリサブディレクトリ名。
リポジトリの実際のフォルダ名をそのまま指定すること（省略名禁止）。
MULTI_REPO: true の場合は REPOS: の左辺キー名と一致させること。

```
# 例: REPO_NAME: repo-A  →  baseline_docs/repo-A/ 以下に仕様書・知見を格納
```

---

## 0. マルチリポジトリ設定

```
MULTI_REPO: false
```

`true` に変更すると、スペックアウト（04）・コーディング（07）がリポジトリ境界をまたいで動作する。

```
# MULTI_REPO: true の場合、以下で各リポジトリのパスを定義する。
# パスはこのファイル（xddp.config.md）からの相対パス、または絶対パスで指定する。
# 【重要】左辺キーはリポジトリの実際のフォルダ名をそのまま使うこと（省略名禁止）。
#   OK例: tasksaas-api: ../tasksaas-api  （フォルダ名と一致）
#   NG例: api: ../tasksaas-api           （省略名のため不可）
# REPOS:
#   tasksaas-api: ../tasksaas-api
#   tasksaas-worker: ../tasksaas-worker
#   tasksaas-notify: ../tasksaas-notify
#   tasksaas-shared: ../tasksaas-shared
```

リポジトリ名（左辺）は CHD・SPO の `repo:` フィールドや変更対象ファイル一覧で使用される識別子になる。
`project-steering.md` の「リポジトリ構成」セクションと一致させること。

---

## 1. スペックアウト設定

### CR 分割警告ライン

```
SPECOUT_MAX_AFFECTED_FILES: 20
```

波及調査は打ち切らず全依存を追い切る。
直接・間接の波及ファイル数がこの値を超えた時点で CR 分割を推奨する警告を出す。
警告後も調査は継続し、判断（続行 or 分割）は人間が行う。
デフォルト: 20

### 調査粒度

```
SPECOUT_DIAGRAM_LEVEL: standard
```

生成するダイアグラムの範囲。以下から選択：
- `minimal` : 機能ソースコード対応表（6.1）のみ
- `standard` : 6.1〜6.4, 6.7, 6.8（機能対応表・構造図・シーケンス図・状態遷移図・クラス図・データ構造）
- `full`     : 6.1〜6.9 すべて（CRUD・ER・PAD含む）

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
```

種別の対応：`ANA`=要求分析、`CRS`=変更要求仕様書、`SPO`=スペックアウト、
`DSN`=実装方式設計書、`CHD`=変更設計書、`TSP`=テスト仕様書、`SPEC`=最新仕様書

---

## 3. テスト設定

### テストフレームワーク

```
TEST_FRAMEWORK: auto
```

使用するテストフレームワークを指定。`auto` の場合はソースコードから自動検出する。
例: `pytest`, `unittest`, `JUnit`, `Jest`, `Vitest`, `Go testing`, `RSpec`

`MULTI_REPO: true` の場合、リポジトリごとに個別指定できる（指定のないリポジトリは `TEST_FRAMEWORK` にフォールバック）。

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
TEST_BOUNDARY_VALUES: true
```

境界値テストケース（min / min+1 / max-1 / max）を生成するか。
デフォルト: `true`

```
TEST_REGRESSION: true
```

SPO の間接影響範囲（Section 3.2）から回帰テストケースを生成するか。
デフォルト: `true`
