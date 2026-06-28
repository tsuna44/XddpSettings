# XDDP プロジェクト設定（分割実行フラグ鮮度検証用スクラッチワークスペース）

> このファイルは PLAN-20260623-e04-specs-close-aiindex-dedup の「分割実行後、最終回の Step DONE で
> 記録される AI_INDEX_PREUPDATED フラグが最新の状態を反映していること」シナリオ検証用に作成した
> 一時的なテストフィクスチャです。本番の XDDP ワークスペースではありません。

```
XDDP_DIR: xddp
```

```
CR_PREFIX: CR
```

```
DOCS_DIR: baseline_docs
```

```
DEVELOPMENT_MODE: change
```

## 0. リポジトリ設定

```
REPOS:
  catalog-svc: ./catalog-svc
```

## 1. スペックアウト設定

（このフィクスチャでは specout を AI 実行せず手動で SPO を作成するため、デフォルト値を使用する）

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
