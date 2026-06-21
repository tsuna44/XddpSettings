---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
has_insights: false
---

# クロスリポジトリシーケンス図 — main

**フロー:** main
**最終更新CR:** CR-2026-900

---

## 1. 文書概要

| 項目 | 内容 |
|---|---|
| フロー名 | main |
| 参加者スコープ | device-svc.alert-dispatcher → EventBus → notify-svc.notifier |

---

## 2. シナリオ説明

device-svc でアラートが発火した際、EventBus を介して notify-svc に非同期配信されるフロー。

---

## 3. シーケンス図

```mermaid
sequenceDiagram
    participant device-svc.alert-dispatcher
    participant EventBus
    participant notify-svc.notifier
    device-svc.alert-dispatcher->>+EventBus: publish(device.alert.raised)
    Note over EventBus: 非同期イベント配信
    EventBus-->>+notify-svc.notifier: dispatch(device.alert.raised)
    notify-svc.notifier-->>-EventBus: ack
```

---

## 4. 変更履歴

| バージョン | CR | 日付 | 変更内容 |
|---|---|---|---|
| 1.0.0 | CR-2026-900 | 2026-06-21 | 初版作成（クロスリポジトリ SPO から生成） |
