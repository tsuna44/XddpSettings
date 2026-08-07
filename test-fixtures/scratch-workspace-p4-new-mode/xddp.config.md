# XDDP プロジェクト設定（新規開発モード動的検証用スクラッチワークスペース）

> このファイルは PLAN-20260719-p4-new-development-profile の動的検証用に作成した一時的なテストフィクスチャです。
> 本番の XDDP ワークスペースではありません。

```
XDDP_DIR: xddp
```


```
DOCS_DIR: baseline_docs
```

```
DEVELOPMENT_MODE: new
```

## 0. リポジトリ設定

```
REPOS:
  widget-svc: ./widget-svc
```

## 1. スペックアウト設定

（新規開発モードでは工程4a/4bをスキップするため、このフィクスチャではデフォルト値を使用する）

## 2. レビュー設定

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

## 3. テスト設定

```
MIN_COVERAGE: 80
```

## 5. 実行環境設定

```
MD2EXCEL_PYTHON_BIN: /usr/bin/python3
```
