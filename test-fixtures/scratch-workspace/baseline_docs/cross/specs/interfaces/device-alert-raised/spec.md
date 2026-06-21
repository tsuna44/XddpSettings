---
version: "2.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
interface: "device-alert-raised"
breaking: true
provider: "device-svc"
affected-repos:
  - "notify-svc"
has_insights: true
---

# クロスリポジトリインタフェース仕様 — device-alert-raised

**インタフェース:** device-alert-raised
**提供リポジトリ:** device-svc
**最終更新CR:** CR-2026-900

---

## 1. 概要

| 項目 | 内容 |
|---|---|
| インタフェース種別 | イベント・キュー |
| 提供リポジトリ | device-svc |
| 影響リポジトリ | notify-svc |
| 現バージョン | 2.0.0 |
| 最終更新 CR | CR-2026-900 |

device-svc の alert-dispatcher がアラート発生時に発行するイベント。notify-svc の notifier がこれを購読し通知を行う。
CR-2026-900 でペイロードに `labels` フィールドを追加した。

---

## 2. インタフェース定義（イベント）

| 項目 | 内容 |
|---|---|
| イベント名 | device.alert.raised |
| 発行元 | device-svc.alert-dispatcher |
| 購読先 | notify-svc.notifier |
| 配信方式 | EventBus（非同期） |

**ペイロード:**

| フィールド | 型 | 必須 | 説明 |
|---|---|:---:|---|
| device_id | str | ○ | 対象デバイスID |
| severity | str | ○ | SEVERITY_LOW/MEDIUM/HIGH |
| labels | list[str] | ○（CR-2026-900で追加） | デバイスに付与されたラベル一覧 |
| raised_at | datetime | ○ | 発火日時 |

---

## 3. エラー・例外処理

| エラー条件 | エラーコード / 戻り値 | 対処 |
|---|---|---|
| labels フィールドを含まない旧形式イベント | — | notify-svc 側で欠損時は labels=[] として処理（本CRと同時デプロイが前提のため通常発生しない） |

---

## 4. バージョン履歴

| バージョン | 変更種別 | breaking | CR | 内容 |
|---|---|:---:|---|---|
| 2.0.0 | フィールド追加（必須） | true | CR-2026-900 | labels（必須）を追加 |
| 1.0.0 | 新規追加 | false | - | 初版 |

---

## 5. 影響範囲

| リポジトリ／モジュール | 影響内容 | 対応要否 |
|---|---|:---:|
| notify-svc.notifier | labels を必須フィールドとして受信・解釈する必要あり | 要 |

---

## 6. 移行ガイド（MAJOR バージョンアップ）

### v1 → v2 移行手順

```
1. notify-svc.notifier を CR-2026-900 と同時にデプロイし、labels フィールドの読み取りに対応する
2. device-svc.alert-dispatcher のデプロイ後、旧形式（labels なし）イベントは発生しない
```

**廃止スケジュール:**
旧バージョン（v1）サポート終了日: CR-2026-900 デプロイ完了時点

---

## 7. 気づき・提案メモ

| # | 種別 | 内容 | 対応方針 |
|---|------|------|----------|
| 1 | 懸念 | 旧形式イベントを notify-svc が受信した場合の挙動はテスト観点として記録済み（CHD §7） | 今回対応 |
