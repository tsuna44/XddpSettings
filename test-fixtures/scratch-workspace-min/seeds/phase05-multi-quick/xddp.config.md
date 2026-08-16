# XDDP プロジェクト設定（トークン最小・multiリポジトリ検証用フィクスチャ・工程05入口・CR_PROFILE: quick版）

> このファイルは任意のXDDPスキル修正を素早く・無害に確認するための最小構成フィクスチャです。
> 本番のXDDPワークスペースではありません。詳細は [../README.md](../README.md) を参照。
>
> multi 版シードは母体を内包する自己完結ワークスペースのため、`REPOS:` は相対パス `./svc-a` `./svc-b`
> でシード内の src/ を直接指す（single 版のように `../multi/` を参照しない。同ディレクトリの
> `README.md`「`--phase` 解決とステージ後レイアウト」参照）。
>
> **quick版について:** `phase05-multi/` を複製し `CR_PROFILE: quick` を追加した手動フィクスチャ
> （`--update-golden` によるゴールデン未確定＝`make smoke-full` は `golden_missing` で止まる）。
> `REPOS:` が2件＝`IS_MULTI`（`HAS_CROSS`）が true・`04_specout/cross/SPO-CR-2026-991-cross.md` が
> 存在するため、`xddp.05.arch` 実行時に `HAS_CROSS=true` と解決される（`xddp.common/SKILL.md`
> 「## Resolve HAS_CROSS」）。よって quick の cross 分岐（`xddp.05.arch/SKILL.md`「## Step -1」
> 1: per-repo 方式比較はスキップし cross DSN のみ生成）を検証できる。single 版の quick シードは
> `HAS_CROSS=false` のため工程5自体が丸ごとスキップされる別経路（「## Step -1」2）を通り、この2つは
> 互いに代替できない（前工程までの成果物md自体は full 生成物を流用しており、quick 経路で実際に
> 生成される簡略化ドキュメントの厳密な再現ではない点は他の quick 版シードと同様）。

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
