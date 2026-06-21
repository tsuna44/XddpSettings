---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
module: "notifier"
repo: "notify-svc"
has_insights: false
---

# モジュール機能仕様書 — notifier

**リポジトリ:** notify-svc
**モジュール:** notifier
**最終更新CR:** CR-2026-900

---

## 1. 文書概要

| 項目 | 内容 |
|---|---|
| 対象モジュール | notifier |
| 主要ファイル | src/notifier.py |
| バージョン | 1.0.0 |

---

## 2. 機能概要

device-svc から受信したアラートイベント（`device.alert.raised`）を通知先へ配信する。

通知先（subscription-manager から取得）には `label_filter` を設定でき、アラートイベントの `AlertEvent.labels` と通知先の `label_filter` を照合し、一致する（または `label_filter` が空の）通知先にのみ送信する。照合条件は OR（いずれか1つのラベルが一致すれば送信）。`label_filter` が空の通知先は従来通り全アラートを受信する（後方互換）。`AlertEvent.labels` が空配列の場合は `label_filter` が空の通知先にのみ送信する。

---

## 3. 入出力

### 3.1 入力

| 項目 | 型 | 説明 | 制約 |
|---|---|---|---|
| event | AlertEvent | device-svc から publish される `device.alert.raised` イベント | `labels: list[str]` を含む |
| targets | list[NotificationTarget] | subscription-manager から取得する通知先一覧 | 各要素は `label_filter: list[str]` を持つ |

### 3.2 出力

| 項目 | 型 | 説明 |
|---|---|---|
| ack | bool | publish 元（alert-dispatcher）への受信確認 |
| 送信結果 | - | label_filter に合致した通知先への送信実行（delivery-queue 経由） |

---

## 4. 処理フロー

1. `device.alert.raised` イベントを受信する（`AlertEvent.labels` を含む）
2. subscription-manager から通知先一覧（`NotificationTarget.label_filter` を含む）を取得する
3. 各通知先について、`label_filter` が空ならば常に対象とする。空でなければ `AlertEvent.labels` とのOR照合を行い、1つでも一致すれば対象とする
4. 対象と判定された通知先にのみ通知を送信する
5. alert-dispatcher へ ack を返す

---

## 5. 正常系・異常系

### 5.1 正常系

| 条件 | 結果 |
|---|---|
| `label_filter` が空の通知先 | 常に送信対象となる（後方互換） |
| `AlertEvent.labels` と `label_filter` が1つ以上一致 | 送信対象となる |

### 5.2 異常系

| エラー条件 | エラー種別 | 処理・返却値 |
|---|---|---|
| `AlertEvent.labels` が空配列 | 仕様上の制約 | `label_filter` が空の通知先にのみ送信する |
| `AlertEvent.labels` と全通知先の `label_filter` が不一致 | 正常（送信なし） | 送信対象なしのまま ack を返す |

---

## 6. 制約・前提条件

- 照合はOR条件（いずれか1つのラベルが一致すれば送信）とする。
- `label_filter` が空の通知先は従来通り全アラートを受信する（後方互換）。

---

## 7. 関連ドキュメント

> このモジュールの関連仕様書へのリンク。
> xddp.02.analysis が要求矛盾の確認に必要な場合に追加参照できる経路を確保する。

| ドキュメント | パス | 説明 |
|---|---|---|
| 構造図 | [structure.md](structure.md) | クラス図（NotificationTarget） |
| シーケンス図 | [sequences/](sequences/) | モジュール内シーケンス |

---

## 8. 気づき・提案メモ

| # | 種別 | 内容 | 対応方針 |
|---|------|------|----------|
| 1 | 懸念 | SPO §5.6 で指摘の通り、通知先一覧の戻り件数がラベルフィルタ導入で変わるため呼び出し側の互換性確認が必要 | 次回CR |

---

## 9. 変更履歴

| バージョン | CR | 日付 | 変更内容 |
|---|---|---|---|
| 1.0.0 | CR-2026-900 | 2026-06-21 | 初版作成（SPO §2 + CHD SP-007 差分を反映）。Before: 全通知先に一律送信。After: AlertEvent.labels と通知先 label_filter のOR照合による振り分けを追加 |
