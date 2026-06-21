---
version: "1.1.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
interface: "severity-values"
breaking: false
provider: "device-svc"
affected-repos:
  - "device-svc"
  - "notify-svc"
has_insights: false
---

# クロスリポジトリインタフェース仕様 — severity-values

**インタフェース:** severity-values
**提供リポジトリ:** device-svc
**最終更新CR:** CR-2026-900

---

## 1. 概要

| 項目 | 内容 |
|---|---|
| インタフェース種別 | その他（共有定数・列挙値） |
| 提供リポジトリ | device-svc |
| 影響リポジトリ | device-svc, notify-svc |
| 現バージョン | 1.1.0 |
| 最終更新 CR | CR-2026-900 |

アラート重大度レベルの共有列挙値。既存3値（LOW/MEDIUM/HIGH）は変更なし。CR-2026-900 で notify-svc が参照リポジトリとして追加された。

---

## 2. インタフェース定義（列挙値）

| 識別子 | 値 | 説明 |
|---|---|---|
| SEVERITY_LOW | "LOW" | 軽微なアラート（通知遅延可） |
| SEVERITY_MEDIUM | "MEDIUM" | 通常アラート |
| SEVERITY_HIGH | "HIGH" | 緊急アラート（即時通知） |

---

## 4. バージョン履歴

| バージョン | 変更種別 | breaking | CR | 内容 |
|---|---|:---:|---|---|
| 1.1.0 | 参照リポジトリ追加 | false | CR-2026-900 | notify-svc を参照リポジトリに追加（値自体は変更なし） |
| 1.0.0 | 新規追加 | false | - | 初版 |

---

## 5. 影響範囲

| リポジトリ／モジュール | 影響内容 | 対応要否 |
|---|---|:---:|
| notify-svc.notifier | severity 値の解釈にこの列挙値を使用 | 要 |

---

## 7. 気づき・提案メモ

| # | 種別 | 内容 | 対応方針 |
|---|------|------|----------|
| 1 | 修正点／改善案／懸念／質問 | （なし） | - |
