# AI向けナビゲーションインデックス

> `{DOCS_DIR}` の中身の索引。`ai_index.py build` が `{DOCS_DIR}` を走査して下の節を作り直す（01-init・close・survey・update-knowledge が実行する）。
> 下の節を手で直しても、次の作り直しで戻る。ここに無い見出しの節（人が足した節）は残る。

## ユースケース一覧

| ユースケース | 目的（1行） | description | 関連モジュール | 最終更新CR |
|---|---|---|---|---|

## リポジトリ別仕様書

| リポジトリ | バージョン | overview | モジュール数 | 最終更新CR |
|---|---|---|---|---|
| [svc-a](svc-a/specs/) | — | — | 1 モジュール | — |

## モジュール別最新仕様

| リポジトリ | モジュール | spec | structure | state | 最終更新CR |
|---|---|---|---|---|---|
| svc-a | mod_a2 | [spec.md](svc-a/specs/mod_a2/spec.md) | — | — | — |

## code-knowledge インデックス

| 知りたいこと | 参照先 |
|---|---|
| svc-a/mod_a2 制約・注意事項 | [constraints.md](svc-a/knowledge/code-knowledge/mod_a2/constraints.md) |

## 変更要求仕様書（CRS）ナビゲーション

| リポジトリ | CR | CRS |
|---|---|---|

## テスト仕様（TSP）・テスト結果（TRS）

| リポジトリ | CR | TSP | TRS |
|---|---|---|---|

## 用語集

| 対象 | 参照先 |
|---|---|

## 共通知識

| 対象 | project-rulebook |
|---|---|

## 知識参照ガイド

> `{repo}` は `xddp.config.md` の `REPOS:` のリポジトリ名。具体的なファイルは各節の表のリンクを参照する。

| 知りたいこと | 参照先パターン |
|---|---|
| 現在の機能仕様 | `{DOCS_DIR}/{repo}/specs/{module}/spec.md`（「モジュール別最新仕様」の表） |
| ユースケース | `{DOCS_DIR}/system/specs/use-cases/{usecase}/description.md`（「ユースケース一覧」の表） |
| リポジトリ間のインタフェース | `{DOCS_DIR}/cross/specs/interfaces/{interface}/spec.md`（「クロスインタフェース一覧」の表） |
| 変更要求の根拠 | `{DOCS_DIR}/{repo}/crs/CRS-{CR}.md`（「変更要求仕様書（CRS）ナビゲーション」の表） |
| コードの制約・共有の知見 | `{DOCS_DIR}/{repo}/knowledge/code-knowledge/`（「code-knowledge インデックス」の表） |
| 過去の実装パターン・知見 | `{XDDP_DIR}/lessons-learned.md`（作業中）／`{DOCS_DIR}/{repo}/knowledge/lessons-learned.md`（クローズ済み）。タグ例: `#方式検討` `#設計` `#コーディング` `#リスク` `#テスト` `#プロセス` |
| プロジェクト規約・禁止事項 | `{DOCS_DIR}/project-rulebook.md`・`{DOCS_DIR}/{repo}/project-rulebook.md`・`{DOCS_DIR}/cross/project-rulebook.md`（「共通知識」の表） |
| テスト仕様・テスト結果 | `{DOCS_DIR}/{repo}/test/`（「テスト仕様（TSP）・テスト結果（TRS）」の表） |
| 用語 | 「用語集」の表 |
