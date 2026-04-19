# リポジトリ責務・オーナー一覧

> AIはコードを直接読む代わりにこのファイルを参照します。
> クロスリポジトリ調査（xddp.04.specout）が参照するIF文書です。必ず最新状態に保ってください。

---

## リポジトリ一覧

| リポジトリ名 | 役割・責務 | 主要技術 | オーナー | 公開IFドキュメント |
|---|---|---|---|---|
| {repo-A} | （責務を記載） | （言語/FW） | （担当者） | [api-contracts/{repo-A}.yaml](api-contracts/{repo-A}.yaml) |
| {repo-B} | （責務を記載） | （言語/FW） | （担当者） | — |

---

## 依存方向サマリ

```
{repo-A} → {repo-B}（REST API）
{repo-B} → {repo-C}（イベント: OrderCreated）
```

詳細は [dependency-graph.md](dependency-graph.md) を参照。

---

## 更新ルール

- リポジトリ追加・廃止時に必ずこのファイルを更新する
- `xddp.close` 実行時に `xddp-analyst-agent` がレビューする
