# XDDP プロジェクト設定（トークン最小・singleリポジトリ検証用フィクスチャ・CR_PROFILE: quick版）

> このファイルは任意のXDDPスキル修正を素早く・無害に確認するための最小構成フィクスチャです。
> 本番のXDDPワークスペースではありません。詳細は [../README.md](../README.md) を参照。
>
> `REPOS:` は `../multi/svc-a` を相対パスで参照し、multi用フィクスチャとソースコードを共有します
> （ソースコードの二重管理を避けるため）。ただし変更対象ファイルは `src/mod_a2.py` とし、
> multi側の `src/mod_a.py` とは独立させています（`code` DOC_TYPE 検証で git diff が競合しないように
> するため）。
>
> **quick版について:** 対応する `phaseNN-single/` を複製し `CR_PROFILE: quick` を追加しただけの
> 手作業フィクスチャ（`--update-golden` によるゴールデン未確定＝`make smoke-full` は `golden_missing`
> で止まる。advisory 照合を得るには先に `--update-golden` を実行すること）。前工程までの成果物md
> 自体は full 生成物を流用しており、quick 経路で実際に生成される簡略化ドキュメントの厳密な再現では
> ない点に注意（progress.md の状態遷移＝スキップ行・成果物有無は quick の実挙動どおりに手で合わせてある）。

```
XDDP_DIR: xddp
```


```
DOCS_DIR: baseline_docs
```

## CR プロファイル設定

```
CR_PROFILE: quick
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
