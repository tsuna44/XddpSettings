# XDDP プロジェクト設定

このファイルをプロジェクトルートに置くことで、XDDPの各フェーズの動作をプロジェクトごとに調整できます。

---

## 0. マルチリポジトリ設定

```
MULTI_REPO: false
```

`true` に変更すると、スペックアウト（04）・コーディング（07）がリポジトリ境界をまたいで動作する。

```
# MULTI_REPO: true の場合、以下で各リポジトリのパスを定義する。
# パスはこのファイル（xddp.config.md）からの相対パス、または絶対パスで指定する。
# REPOS:
#   api: ../tasksaas-api
#   worker: ../tasksaas-worker
#   notify: ../tasksaas-notify
#   shared: ../tasksaas-shared
```

リポジトリ名（左辺）は CHD・SPO の `repo:` フィールドや変更対象ファイル一覧で使用される識別子になる。
`project-steering.md` の「リポジトリ構成」セクションと一致させること。

---

## 1. スペックアウト設定

### 調査打ち切り基準

```
SPECOUT_CUTOFF_MODULE_BOUNDARIES: 3
```

波及調査で依存関係が見つからないままモジュール境界をいくつ越えたら調査を打ち切るか。
デフォルト: 3

```
SPECOUT_MAX_AFFECTED_FILES: 20
```

直接・間接の波及ファイル数がこの値を超えたら CR 分割の警告を出す。
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

## 2. テスト設定

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
