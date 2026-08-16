# XDDP プロジェクト設定（トークン最小・multiリポジトリ検証用フィクスチャ・工程06入口）

> このファイルは任意のXDDPスキル修正を素早く・無害に確認するための最小構成フィクスチャです。
> 本番のXDDPワークスペースではありません。詳細は [../README.md](../README.md) を参照。
>
> multi 版シードは母体を内包する自己完結ワークスペースのため、`REPOS:` は相対パス `./svc-a` `./svc-b`
> でシード内の src/ を直接指す（single 版のように `../multi/` を参照しない。同ディレクトリの
> `README.md`「`--phase` 解決とステージ後レイアウト」参照）。
>
> `phase05-multi/` の続き（工程5完了後・工程6入口）。`HAS_CROSS=true`（`04_specout/cross/
> SPO-CR-2026-991-cross.md` が存在）のため、工程5では per-repo DSN（svc-a・svc-b）に加えて
> cross DSN（`05_architecture/cross/DSN-CR-2026-991-cross.md`）も生成済み。工程6の
> `xddp.common/SKILL.md`「## Resolve HAS_CROSS」はこの cross DSN の存在で `HAS_CROSS=true` を
> 再解決するため、工程6の cross CHD 生成分岐を検証できる。

```
XDDP_DIR: xddp
```


```
DOCS_DIR: baseline_docs
```

## 0. リポジトリ設定

```
REPOS:
  svc-a: ./svc-a
  svc-b: ./svc-b
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
