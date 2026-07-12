# XDDP プロジェクト設定（トークン最小・singleリポジトリ検証用フィクスチャ）

> このファイルは任意のXDDPスキル修正を素早く・無害に確認するための最小構成フィクスチャです。
> 本番のXDDPワークスペースではありません。詳細は [../README.md](../README.md) を参照。
>
> `REPOS:` は `../multi/svc-a` を相対パスで参照し、multi用フィクスチャとソースコードを共有します
> （ソースコードの二重管理を避けるため）。ただし変更対象ファイルは `src/mod_a2.py` とし、
> multi側の `src/mod_a.py` とは独立させています（`code` DOC_TYPE 検証で git diff が競合しないように
> するため）。

```
XDDP_DIR: xddp
```

```
CR_PREFIX: CR
```

```
DOCS_DIR: baseline_docs
```

## 0. リポジトリ設定

```
REPOS:
  svc-a: ../multi/svc-a
```

## 2. レビュー設定

```
REVIEW_MAX_ROUNDS:
  ANA: 1
  CRS: 1
  SPO: 1
  DSN: 1
  CHD: 1
  TSP: 1
  SPEC: 1
  PLAN: 1
```

```
FIX_STRATEGY:
  PLAN: ideal
  ANA: ideal
  CRS: ideal
  SPO: ideal
  DSN: ideal
  CHD: ideal
  TSP: ideal
  SPEC: ideal
```
