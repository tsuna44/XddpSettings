# XDDP プロジェクト設定（トークン最小・multiリポジトリ検証用フィクスチャ・工程05入口）

> このファイルは任意のXDDPスキル修正を素早く・無害に確認するための最小構成フィクスチャです。
> 本番のXDDPワークスペースではありません。詳細は [../README.md](../README.md) を参照。
>
> multi 版シードは母体を内包する自己完結ワークスペースのため、`REPOS:` は相対パス `./svc-a` `./svc-b`
> でシード内の src/ を直接指す（single 版のように `../multi/` を参照しない。同ディレクトリの
> `README.md`「`--phase` 解決とステージ後レイアウト」参照）。
>
> `phase04-multi/` の続き（工程4a/4b完了後・工程5入口）。svc-b の `notify()` が svc-a の
> `POST /validate` を呼ぶ既存インタフェースを specout が発見した想定で `04_specout/cross/
> SPO-CR-2026-991-cross.md` を追加しており、`HAS_CROSS`（= `IS_MULTI` かつ本ファイルが存在）が
> true になる（`xddp.common/SKILL.md`「## Resolve HAS_CROSS」）。これにより工程5・6の cross 分岐
> （per-repo DSN/CHD に加え cross DSN/CHD も生成する経路）を検証できる。

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
