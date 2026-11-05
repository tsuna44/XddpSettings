# AI向けナビゲーションインデックス

> `{DOCS_DIR}` の中身の索引。`ai_index.py build` が `{DOCS_DIR}` を走査して下の節を作り直す（01-init・close・survey・update-knowledge が実行する）。
> 下の節を手で直しても、次の作り直しで戻る。ここに無い見出しの節（人が足した節）は残る。

## ユースケース一覧

| ユースケース | 目的（1行） | description | 関連モジュール | 最終更新CR |
|---|---|---|---|---|
| alert-label-filtering | オペレーターがアラート一覧画面でラベルを指定して絞り込み表示できるようにする。大量のアラートから特定ラベルのデバイスに関するものだけを確認したいという要求に対応する。 | [description.md](system/specs/use-cases/alert-label-filtering/description.md) | alert-dispatcher | CR-2026-900 |
| device-label-management | オペレーターがダッシュボードからデバイスに任意のラベル（例：「1F-倉庫」「critical」）を付与・削除できるようにする。1台のデバイスに複数ラベルを付与可能とし、設置場所や用途による分類を可能にすることで、異常時の対象特定を容易にする。 | [description.md](system/specs/use-cases/device-label-management/description.md) | device-registry | CR-2026-900 |
| label-based-notification-routing | 管理者が通知先（メール・Slack等）をラベルに紐づけ、該当ラベルのデバイスでアラートが発生した際にその通知先にのみ送信されるようにする。担当者ごとに責任を持つデバイス群（ラベル）が異なるため、無関係な通知を減らすことを目的とする。レポート生成時もラベルでフィルタ可能にする。 | [description.md](system/specs/use-cases/label-based-notification-routing/description.md) | subscription-manager, notifier, alert-dispatcher, report-generator | CR-2026-900 |

## リポジトリ別仕様書

| リポジトリ | バージョン | overview | モジュール数 | 最終更新CR |
|---|---|---|---|---|
| [device-svc](device-svc/specs/) | v1.0.0 | [overview](device-svc/specs/overview/) | 6 モジュール | CR-2026-900 |
| [notify-svc](notify-svc/specs/) | v1.0.0 | [overview](notify-svc/specs/overview/) | 6 モジュール | CR-2026-900 |

## モジュール別最新仕様

| リポジトリ | モジュール | spec | structure | state | 最終更新CR |
|---|---|---|---|---|---|
| device-svc | alert-dispatcher | [spec.md](device-svc/specs/alert-dispatcher/spec.md) | [structure.md](device-svc/specs/alert-dispatcher/structure.md) | — | CR-2026-900 |
| device-svc | calibration | [spec.md](device-svc/specs/calibration/spec.md) | — | — | CR-2026-900 |
| device-svc | device-registry | [spec.md](device-svc/specs/device-registry/spec.md) | — | — | CR-2026-900 |
| device-svc | firmware-updater | [spec.md](device-svc/specs/firmware-updater/spec.md) | — | — | CR-2026-900 |
| device-svc | power-monitor | [spec.md](device-svc/specs/power-monitor/spec.md) | — | — | CR-2026-900 |
| device-svc | sensor-reader | [spec.md](device-svc/specs/sensor-reader/spec.md) | [structure.md](device-svc/specs/sensor-reader/structure.md) | — | CR-2026-900 |
| notify-svc | audit-logger | [spec.md](notify-svc/specs/audit-logger/spec.md) | — | — | CR-2026-900 |
| notify-svc | delivery-queue | [spec.md](notify-svc/specs/delivery-queue/spec.md) | — | — | CR-2026-900 |
| notify-svc | notifier | [spec.md](notify-svc/specs/notifier/spec.md) | [structure.md](notify-svc/specs/notifier/structure.md) | — | CR-2026-900 |
| notify-svc | report-generator | [spec.md](notify-svc/specs/report-generator/spec.md) | — | — | CR-2026-900 |
| notify-svc | subscription-manager | [spec.md](notify-svc/specs/subscription-manager/spec.md) | [structure.md](notify-svc/specs/subscription-manager/structure.md) | — | CR-2026-900 |
| notify-svc | template-engine | [spec.md](notify-svc/specs/template-engine/spec.md) | — | — | CR-2026-900 |

## クロスインタフェース一覧

| インタフェース | spec | schema | バージョン | 最終更新の破壊的変更 | 最終更新CR |
|---|---|---|---|---|---|
| device-alert-raised | [spec.md](cross/specs/interfaces/device-alert-raised/spec.md) | [schema.md](cross/specs/interfaces/device-alert-raised/schema.md) | v2.0.0 | ⚠️ あり | CR-2026-900 |
| severity-values | [spec.md](cross/specs/interfaces/severity-values/spec.md) | — | v1.1.0 | — | CR-2026-900 |

## code-knowledge インデックス

| 知りたいこと | 参照先 |
|---|---|
| device-svc/sensor-reader 制約・注意事項 | [constraints.md](device-svc/knowledge/code-knowledge/sensor-reader/constraints.md) |
| device-svc 機能間フロー | [_flows/](device-svc/knowledge/code-knowledge/_flows/) |
| notify-svc/notifier 制約・注意事項 | [constraints.md](notify-svc/knowledge/code-knowledge/notifier/constraints.md) |
| notify-svc/report-generator 制約・注意事項 | [constraints.md](notify-svc/knowledge/code-knowledge/report-generator/constraints.md) |
| cross 共有構造体 | [_structures/](cross/knowledge/code-knowledge/_structures/) |
| cross 共有定数 | [_constants/](cross/knowledge/code-knowledge/_constants/) |
| cross 機能間フロー | [_flows/](cross/knowledge/code-knowledge/_flows/) |

## 変更要求仕様書（CRS）ナビゲーション

| リポジトリ | CR | CRS |
|---|---|---|
| device-svc | CR-2026-900 | [CRS-CR-2026-900.md](device-svc/crs/CRS-CR-2026-900.md) |
| notify-svc | CR-2026-900 | [CRS-CR-2026-900.md](notify-svc/crs/CRS-CR-2026-900.md) |
| cross | CR-2026-900 | [CRS-CR-2026-900.md](cross/crs/CRS-CR-2026-900.md) |

## テスト仕様（TSP）・テスト結果（TRS）

| リポジトリ | CR | TSP | TRS |
|---|---|---|---|
| device-svc | CR-2026-900 | — | [TRS-CR-2026-900-001.md](device-svc/test/TRS-CR-2026-900-001.md) |

## 用語集

| 対象 | 参照先 |
|---|---|

## 共通知識

| 対象 | project-rulebook |
|---|---|
| notify-svc | [project-rulebook.md](notify-svc/project-rulebook.md) |

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
