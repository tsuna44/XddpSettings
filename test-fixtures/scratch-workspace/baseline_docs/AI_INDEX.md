# AI_INDEX

> 知識ハブの目次。各セクションは xddp.close 実行時に自動 upsert される。

## リポジトリ別仕様書

| リポジトリ | バージョン | overview | モジュール数 | 最終更新CR |
|---|---|---|---|---|
| [device-svc](device-svc/specs/) | v1.0.0（最終更新CR: CR-2026-900） | [overview](device-svc/specs/overview/) | 6 モジュール | CR-2026-900 |
| [notify-svc](notify-svc/specs/) | v1.0.0（最終更新CR: CR-2026-900） | [overview](notify-svc/specs/overview/) | 6 モジュール | CR-2026-900 |

## ユースケース一覧

| ユースケース | 目的（1行） | description | 関連モジュール | 最終更新CR |
|---|---|---|---|---|
| device-label-management | デバイスにラベルを付与する | [description.md](system/specs/use-cases/device-label-management/description.md) | device-registry | CR-2026-900 |
| alert-label-filtering | ラベル単位でアラート一覧を絞り込む | [description.md](system/specs/use-cases/alert-label-filtering/description.md) | alert-dispatcher | CR-2026-900 |
| label-based-notification-routing | ラベルに応じて通知先を振り分ける | [description.md](system/specs/use-cases/label-based-notification-routing/description.md) | subscription-manager, notifier, alert-dispatcher, report-generator | CR-2026-900 |

## モジュール別最新仕様

| リポジトリ | モジュール | spec | structure | state | 最終更新CR |
|---|---|---|---|---|---|
| device-svc | sensor-reader | [spec.md](device-svc/specs/sensor-reader/spec.md) | [structure.md](device-svc/specs/sensor-reader/structure.md) | — | CR-2026-900 |
| device-svc | alert-dispatcher | [spec.md](device-svc/specs/alert-dispatcher/spec.md) | [structure.md](device-svc/specs/alert-dispatcher/structure.md) | — | CR-2026-900 |
| device-svc | calibration | [spec.md](device-svc/specs/calibration/spec.md) | — | — | CR-2026-900 |
| device-svc | device-registry | [spec.md](device-svc/specs/device-registry/spec.md) | — | — | CR-2026-900 |
| device-svc | firmware-updater | [spec.md](device-svc/specs/firmware-updater/spec.md) | — | — | CR-2026-900 |
| device-svc | power-monitor | [spec.md](device-svc/specs/power-monitor/spec.md) | — | — | CR-2026-900 |
| notify-svc | notifier | [spec.md](notify-svc/specs/notifier/spec.md) | [structure.md](notify-svc/specs/notifier/structure.md) | — | CR-2026-900 |
| notify-svc | subscription-manager | [spec.md](notify-svc/specs/subscription-manager/spec.md) | [structure.md](notify-svc/specs/subscription-manager/structure.md) | — | CR-2026-900 |
| notify-svc | report-generator | [spec.md](notify-svc/specs/report-generator/spec.md) | — | — | CR-2026-900 |
| notify-svc | template-engine | [spec.md](notify-svc/specs/template-engine/spec.md) | — | — | CR-2026-900 |
| notify-svc | delivery-queue | [spec.md](notify-svc/specs/delivery-queue/spec.md) | — | — | CR-2026-900 |
| notify-svc | audit-logger | [spec.md](notify-svc/specs/audit-logger/spec.md) | — | — | CR-2026-900 |

## クロスインタフェース一覧

| インタフェース | spec | schema | バージョン | 最終更新CR |
|---|---|---|---|---|
| device-alert-raised ⚠️ 破壊的変更あり（CR: CR-2026-900） | [spec.md](cross/specs/interfaces/device-alert-raised/spec.md) | [schema.md](cross/specs/interfaces/device-alert-raised/schema.md) | v2.0.0 | CR-2026-900 |
| severity-values | [spec.md](cross/specs/interfaces/severity-values/spec.md) | — | v1.1.0 | CR-2026-900 |

## 変更要求仕様書（CRS）ナビゲーション

| 知りたいこと | 参照先 |
|---|---|
| CR-2026-900 device-svc 変更要求仕様 | [CRS-CR-2026-900.md](device-svc/crs/CRS-CR-2026-900.md) |
| CR-2026-900 notify-svc 変更要求仕様 | [CRS-CR-2026-900.md](notify-svc/crs/CRS-CR-2026-900.md) |
| CR-2026-900 cross 変更要求仕様 | [CRS-CR-2026-900.md](cross/crs/CRS-CR-2026-900.md) |

## テスト仕様（TSP）・テスト結果（TRS）

| リポジトリ | TSP | TRS | 最終更新CR |
|---|---|---|---|
| device-svc | — | [TRS-CR-2026-900-001.md](device-svc/test/TRS-CR-2026-900-001.md) | CR-2026-900 |

## 共通知識

| リポジトリ | project-rulebook | 最終更新CR |
|---|---|---|
| notify-svc | [project-rulebook.md](notify-svc/project-rulebook.md) | CR-2026-900 |
| cross | [project-rulebook.md](cross/project-rulebook.md) | CR-2026-900 |

## code-knowledge インデックス

| 知りたいこと | 参照先 |
|---|---|
| device-svc/sensor-reader 制約・注意事項 | [constraints.md](device-svc/knowledge/code-knowledge/sensor-reader/constraints.md) |
| notify-svc/notifier 制約・注意事項 | [constraints.md](notify-svc/knowledge/code-knowledge/notifier/constraints.md) |
| notify-svc/report-generator 制約・注意事項 | [constraints.md](notify-svc/knowledge/code-knowledge/report-generator/constraints.md) |
| device-svc 機能間フロー | [_flows/](device-svc/knowledge/code-knowledge/_flows/) |
| cross 共有定数 | [_constants/](cross/knowledge/code-knowledge/_constants/) |
| cross 構造体関連図 | [_structures/](cross/knowledge/code-knowledge/_structures/) |
| cross 機能間フロー | [_flows/](cross/knowledge/code-knowledge/_flows/) |

## 知識参照ガイド

> `{repo}` は `xddp.config.md` の `REPOS:` エントリ名が入るパターン表記（例: `repo-a`）。
> 具体的なファイルは上記各テーブルのリンクを参照のこと。

| 知りたいこと | 参照先パターン |
|---|---|
| 現在の機能仕様（What it does） | `{DOCS_DIR}/{repo}/specs/{module}/spec.md`（→「モジュール別最新仕様」テーブル） |
| 変更要求・設計判断の根拠（Why it was changed） | `{DOCS_DIR}/{repo}/crs/CRS-{CR}.md`（→「変更要求仕様書」テーブル） |
| 過去の実装パターン・知見 | `{XDDP_DIR}/lessons-learned.md`（作業中）/ `{DOCS_DIR}/{repo}/knowledge/lessons-learned.md`（クローズ済み）<br>タグ検索例: `#方式検討` `#設計` `#コーディング` `#リスク` `#テスト` `#プロセス` |
| プロジェクト規約・禁止事項 | `{XDDP_DIR}/project-rulebook.md` / `{XDDP_DIR}/project-rulebook-{repo}.md` |
| テスト仕様 | → 上記「テスト仕様（TSP）」テーブルを参照 |

> このセクションは初回 xddp.close 時に自動生成されます。知識ディレクトリ構造変更後に更新するには、このセクションを削除して xddp.close を再実行してください。
