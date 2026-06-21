---
version: "2.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
interface: "device-alert-raised"
provider: "device-svc"
has_insights: false
---

# インタフェーススキーマ定義 — device-alert-raised

**インタフェース:** device-alert-raised
**提供リポジトリ:** device-svc
**最終更新CR:** CR-2026-900

---

## 1. 文書概要

| 項目 | 内容 |
|---|---|
| インタフェース種別 | イベント・キュー |
| スキーマバージョン | 2.0.0 |

---

## 2. データ定義（イベントペイロード）

```json
{
  "device_id": "dev-001",
  "severity": "HIGH",
  "labels": ["1F-倉庫", "critical"],
  "raised_at": "2026-06-21T10:00:00Z"
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|:---:|---|
| device_id | string | ○ | 対象デバイスID |
| severity | string | ○ | SEVERITY_LOW/MEDIUM/HIGH |
| labels | array[string] | ○ | デバイスに付与されたラベル一覧（CR-2026-900で追加） |
| raised_at | string (ISO8601) | ○ | 発火日時 |

---

## 3. 変更履歴

| バージョン | CR | 日付 | 変更内容 |
|---|---|---|---|
| 2.0.0 | CR-2026-900 | 2026-06-21 | labels フィールド追加 |
| 1.0.0 | - | - | 初版作成 |
