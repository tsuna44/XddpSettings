---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
module: "subscription-manager"
repo: "notify-svc"
has_insights: false
---

# 構造図（クラス図・データ構造） — subscription-manager

**リポジトリ:** notify-svc
**モジュール:** subscription-manager
**最終更新CR:** CR-2026-900

---

## 1. 文書概要

| 項目 | 内容 |
|---|---|
| 対象モジュール | subscription-manager |
| 主要クラス・構造体 | NotificationTarget |
| バージョン | 1.0.0 |

---

## 2. クラス図

```mermaid
classDiagram
    class NotificationTarget {
        +channel: str
        +address: str
        +label_filter: list~str~
    }
```

---

## 3. データ構造定義表

| 名前 | 型 | 説明 | 備考 |
|---|---|---|---|
| NotificationTarget | class | 通知先（チャネル・宛先・ラベル条件）を表す | subscription-manager がこのデータの登録・管理元 |
| `channel` | str | 通知チャネル種別（例: email, slack） | |
| `address` | str | 送信先アドレス | |
| `label_filter` | list[str] | 対象とするラベル一覧。空配列は「全件対象」を意味する（後方互換） | CR-2026-900 で追加 |

---

## 4. PAD（問題分析図）

> 対象外（このモジュールの主要処理は単純な登録・参照CRUDのみ）

---

## 5. 気づき・提案メモ

| # | 種別 | 内容 | 対応方針 |
|---|------|------|----------|
| 1 | 修正点／改善案／懸念／質問 | （なし） | - |

---

## 6. 変更履歴

| バージョン | CR | 日付 | 変更内容 |
|---|---|---|---|
| 1.0.0 | CR-2026-900 | 2026-06-21 | 初版作成（CHD SP-006 反映で label_filter フィールドを追加） |
