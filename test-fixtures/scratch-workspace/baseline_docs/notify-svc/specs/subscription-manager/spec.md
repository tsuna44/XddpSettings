---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: spo
module: "subscription-manager"
repo: "notify-svc"
has_insights: false
---

# モジュール機能仕様書 — subscription-manager

**リポジトリ:** notify-svc
**モジュール:** subscription-manager
**最終更新CR:** CR-2026-900

---

## 1. 文書概要

| 項目 | 内容 |
|---|---|
| 対象モジュール | subscription-manager |
| 主要ファイル | src/subscription_manager.py |
| バージョン | 1.0.0 |

---

## 2. 機能概要

通知先（チャネル種別・宛先）の登録・管理を行う。通知先はラベル単位で紐づけ管理できる。`NotificationTarget` は `channel, address` に加えて `label_filter: list[str]` を持つ（空配列は「全件対象」を意味する）。`label_filter` が空の通知先は従来通り全アラートを受信する（後方互換）。

---

## 3. 入出力

### 3.1 入力

| 項目 | 型 | 説明 | 制約 |
|---|---|---|---|
| target | NotificationTarget | 登録・更新対象の通知先 | `label_filter` は省略時は空配列 |

### 3.2 出力

| 項目 | 型 | 説明 |
|---|---|---|
| targets[] | list[NotificationTarget] | 登録済み通知先一覧（notifier から `get_targets()` で取得される） |

---

## 4. 処理フロー

1. 通知先（チャネル・宛先・`label_filter`）を登録・更新する
2. notifier からの要求に応じて通知先一覧を返す

---

## 5. 正常系・異常系

### 5.1 正常系

| 条件 | 結果 |
|---|---|
| `label_filter` を指定して通知先を登録 | ラベル単位の紐付けが成立する |
| `label_filter` を省略して通知先を登録 | 空配列として扱われ、全件対象（後方互換）になる |

### 5.2 異常系

| エラー条件 | エラー種別 | 処理・返却値 |
|---|---|---|
| - | - | - |

---

## 6. 制約・前提条件

- `label_filter` が空の通知先は従来通り全アラートを受信する（後方互換）。

---

## 7. 関連ドキュメント

> このモジュールの関連仕様書へのリンク。
> xddp.02.analysis が要求矛盾の確認に必要な場合に追加参照できる経路を確保する。

| ドキュメント | パス | 説明 |
|---|---|---|
| 構造図 | [structure.md](structure.md) | クラス図・データ構造定義 |

---

## 8. 気づき・提案メモ

| # | 種別 | 内容 | 対応方針 |
|---|------|------|----------|
| 1 | 修正点／改善案／懸念／質問 | （なし） | - |

---

## 9. 変更履歴

| バージョン | CR | 日付 | 変更内容 |
|---|---|---|---|
| 1.0.0 | CR-2026-900 | 2026-06-21 | 初版作成（SPO §2 + CHD SP-006 差分を反映）。Before: デバイス個別単位の紐付けのみ。After: NotificationTarget に label_filter（空配列=全件対象）を追加しラベル単位の紐付け管理が可能 |
