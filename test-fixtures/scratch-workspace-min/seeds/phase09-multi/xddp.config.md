# XDDP プロジェクト設定（トークン最小・multiリポジトリ検証用フィクスチャ・工程09入口）

> このファイルは任意のXDDPスキル修正を素早く・無害に確認するための最小構成フィクスチャです。
> 本番のXDDPワークスペースではありません。詳細は [../README.md](../README.md) を参照。
>
> multi 版シードは母体を内包する自己完結ワークスペースのため、`REPOS:` は相対パス `./svc-a` `./svc-b`
> でシード内の src/ を直接指す（single 版のように `../multi/` を参照しない。同ディレクトリの
> `README.md`「`--phase` 解決とステージ後レイアウト」参照）。
>
> `phase06-multi/` の続き（工程6a〜8完了後・工程9入口）。per-repo CHD（svc-a・svc-b）に加えて
> cross CHD（`06_design/cross/CHD-CR-2026-991-cross.md`）が生成済みで、母体コード（`svc-a/src/mod_a2.py`・
> `svc-b/src/mod_b.py`）も CHD どおり実装後の状態に揃えてある。工程9の
> `xddp-common/SKILL.md`「## Resolve HAS_CROSS」はこの cross CHD の存在で `HAS_CROSS=true` を
> 再解決するため、工程9の cross TSP 生成分岐を検証できる。

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
