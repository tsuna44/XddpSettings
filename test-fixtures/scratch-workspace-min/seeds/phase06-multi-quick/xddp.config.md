# XDDP プロジェクト設定（トークン最小・multiリポジトリ検証用フィクスチャ・工程06入口・CR_PROFILE: quick版）

> このファイルは任意のXDDPスキル修正を素早く・無害に確認するための最小構成フィクスチャです。
> 本番のXDDPワークスペースではありません。詳細は [../README.md](../README.md) を参照。
>
> multi 版シードは母体を内包する自己完結ワークスペースのため、`REPOS:` は相対パス `./svc-a` `./svc-b`
> でシード内の src/ を直接指す（single 版のように `../multi/` を参照しない。同ディレクトリの
> `README.md`「`--phase` 解決とステージ後レイアウト」参照）。
>
> **quick版について:** `phase06-multi/` から per-repo DSN（svc-a・svc-b）を除いた手動フィクスチャ
> （`--update-golden` によるゴールデン未確定＝`make smoke-full` は `golden_missing` で止まる）。
> `phase05-multi-quick/` で `CR_PROFILE: quick` かつ `HAS_CROSS=true` のため、工程5は
> `xddp.05.arch/SKILL.md`「## Step -1」1（per-repo 方式比較スキップ・cross DSN のみ生成）を通り、
> `05_architecture/cross/DSN-CR-2026-991-cross.md` のみが存在し per-repo DSN は存在しない
> （progress.md 工程5行も `⏭️ スキップ（quick: cross DSN のみ生成）` — 同ステップ e の指示どおり）。
> 工程6の `HAS_CROSS` 解決はこの cross DSN の存在で true になるため、quick でも工程6の cross CHD
> 生成分岐を検証できる（前工程までの成果物md自体は full 生成物を流用しており、quick 経路で実際に
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
