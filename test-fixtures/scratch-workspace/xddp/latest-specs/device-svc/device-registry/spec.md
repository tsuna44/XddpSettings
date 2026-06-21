---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
module: "device-registry"
repo: "device-svc"
has_insights: false
---

# モジュール機能仕様書 — device-registry

**リポジトリ:** device-svc
**モジュール:** device-registry
**最終更新CR:** CR-2026-900

---

## 1. 文書概要

| 項目 | 内容 |
|---|---|
| 対象モジュール | device-registry |
| 主要ファイル | src/device_registry.py |
| バージョン | 1.0.0 |

---

## 2. 機能概要

デバイスの登録・属性管理を行う。デバイスIDと基本属性（名称・設置場所）に加え、ラベル（文字列配列、デフォルト空配列）を保持する（SP-001）。
ラベルの付与・削除操作として `add_label(device_id, label)` / `remove_label(device_id, label)` を提供する（SP-002）。

---

## 3. 入出力

### 3.1 入力

| 項目 | 型 | 説明 | 制約 |
|---|---|---|---|
| device_id | str | 対象デバイスID | - |
| label | str | 付与・削除対象のラベル名 | add_label/remove_label のみ |

### 3.2 出力

| 項目 | 型 | 説明 |
|---|---|---|
| Device | object | device_id, name, location, labels（文字列配列）を含むデバイス情報 |

---

## 4. 処理フロー

1. デバイスIDと基本属性（名称・設置場所）を保持する
2. `add_label(device_id, label)` 呼び出し時、対象デバイスの labels にラベルを追加する（重複ラベルは無視・冪等）
3. `remove_label(device_id, label)` 呼び出し時、対象デバイスの labels からラベルを削除する

---

## 5. 正常系・異常系

### 5.1 正常系

| 条件 | 結果 |
|---|---|
| 未付与のラベルを add_label で追加 | labels に追加される |
| 既に付与済みのラベルを add_label で追加 | 何も変化しない（冪等） |

### 5.2 異常系

| エラー条件 | エラー種別 | 処理・返却値 |
|---|---|---|
| {未確認} | {未確認} | {未確認} |

---

## 6. 制約・前提条件

- 既存デバイスレコードは `labels=[]` として扱う（移行時のデフォルト）。
- ラベルの付与・削除操作は監査ログに記録される（SP-009、audit-logger 連携。device-registry はモジュールスコープ外につき詳細は audit-logger 側仕様を参照）。

---

## 7. 関連ドキュメント

| ドキュメント | パス | 説明 |
|---|---|---|
| 状態遷移図 | 対象外（SPO で「対象外」と確認済み） | - |
| 構造図 | 対象外（SPO で「対象外」と確認済み） | - |
| シーケンス図 | 対象外（SPO で「対象外」と確認済み） | - |

---

## 8. 気づき・提案メモ

| # | 種別 | 内容 | 対応方針 |
|---|------|------|----------|
| 1 | 修正点／改善案／懸念／質問 | {内容} | 今回対応／次回CR／保留／却下 |

---

## 9. 変更履歴

| バージョン | CR | 日付 | 変更内容 |
|---|---|---|---|
| 1.0.0 | CR-2026-900 | 2026-06-21 | 初版作成（SPO から生成）。SP-001 反映: Device に labels フィールド（文字列配列、デフォルト空配列）を追加（Before: device_id, name, location → After: device_id, name, location, labels）。SP-002 反映: ラベル付与・削除操作 add_label/remove_label を追加（Before: ラベル付与手段なし → After: add_label/remove_label を提供） |
