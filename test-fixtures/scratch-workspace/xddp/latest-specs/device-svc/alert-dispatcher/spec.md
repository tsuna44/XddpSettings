---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
module: "alert-dispatcher"
repo: "device-svc"
has_insights: false
---

# モジュール機能仕様書 — alert-dispatcher

**リポジトリ:** device-svc
**モジュール:** alert-dispatcher
**最終更新CR:** CR-2026-900

---

## 1. 文書概要

| 項目 | 内容 |
|---|---|
| 対象モジュール | alert-dispatcher |
| 主要ファイル | src/alert_dispatcher.py |
| バージョン | 1.0.0 |

---

## 2. 機能概要

sensor-reader からの閾値超過通知を受けてアラートイベントを生成し、notify-svc へ送出する。
`device.alert.raised` イベントに、device-registry から取得したラベル一覧を含める（SP-004）。

---

## 3. 入出力

### 3.1 入力

| 項目 | 型 | 説明 | 制約 |
|---|---|---|---|
| reading | SensorReading | sensor-reader からの閾値超過通知 | - |

### 3.2 出力

| 項目 | 型 | 説明 |
|---|---|---|
| AlertEvent | object | device_id, severity, raised_at, labels（文字列配列）を含むアラートイベント |

---

## 4. 処理フロー

1. sensor-reader から閾値超過の通知を受け取る
2. device-registry に問い合わせてラベル一覧を取得する
3. `device.alert.raised` イベント（labels を含む）を生成し、notify-svc へ送出する

---

## 5. 正常系・異常系

### 5.1 正常系

| 条件 | 結果 |
|---|---|
| device-registry への問い合わせ成功 | AlertEvent.labels に取得したラベル一覧が設定される |

### 5.2 異常系

| エラー条件 | エラー種別 | 処理・返却値 |
|---|---|---|
| device-registry への問い合わせ失敗 | 問い合わせエラー | `labels=[]` で送出する（アラート自体は欠落させない） |

---

## 6. 制約・前提条件

- アラート一覧はラベル指定でフィルタできる（SP-005）。

---

## 7. 関連ドキュメント

| ドキュメント | パス | 説明 |
|---|---|---|
| 状態遷移図 | 対象外（SPO で「対象外」と確認済み） | - |
| 構造図 | [structure.md](structure.md) | クラス図・データ構造定義 |
| シーケンス図 | [sequences/main-seq.md](sequences/main-seq.md) | モジュール内シーケンス |

---

## 8. 気づき・提案メモ

| # | 種別 | 内容 | 対応方針 |
|---|------|------|----------|
| 1 | 修正点／改善案／懸念／質問 | SP-005（アラート一覧のラベル絞り込み）の CHD 詳細設計（§3.x）が見つからず、CRS §4 の After 記述のみで本仕様書を作成した | 次回CR |

---

## 9. 変更履歴

| バージョン | CR | 日付 | 変更内容 |
|---|---|---|---|
| 1.0.0 | CR-2026-900 | 2026-06-21 | 初版作成（SPO から生成）。SP-004 反映: AlertEvent に labels フィールドを追加し device-registry から取得したラベルを設定（Before: device_id, severity, raised_at のみ → After: labels を追加）。SP-005 反映: アラート一覧のラベル絞り込み機能を追加（Before: ラベルで絞り込めない → After: ラベル指定でフィルタ可能） |
