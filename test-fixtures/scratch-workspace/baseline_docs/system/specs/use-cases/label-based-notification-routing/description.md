---
version: "1.0.0"
last-updated-cr: "CR-2026-900"
last-verified-cr: "CR-2026-900"
source: ai-inferred
related-modules:
  - "subscription-manager"
  - "notifier"
  - "alert-dispatcher"
  - "report-generator"
has_insights: false
---

# ユースケース記述 — label-based-notification-routing

**ユースケース:** label-based-notification-routing
**最終更新CR:** CR-2026-900

> `source: ai-inferred` は AI が CRS UR + SPO §3 から合成した情報であることを示します。
> 内容を確認後、人手で `source: manual` に変更してください。
> `related-modules` は CRS §2 UR → SPO モジュール名の照合で自動生成されます。
> 照合できなかった場合は `[]` で初期生成し、人手で補完してください。

---

## 1. 文書概要

| 項目 | 内容 |
|---|---|
| ユースケース名 | label-based-notification-routing |
| 関連モジュール | subscription-manager, notifier, alert-dispatcher, report-generator |
| バージョン | 1.0.0 |

---

## 2. 目的・ゴール

管理者が通知先（メール・Slack等）をラベルに紐づけ、該当ラベルのデバイスでアラートが発生した際にその通知先にのみ送信されるようにする。担当者ごとに責任を持つデバイス群（ラベル）が異なるため、無関係な通知を減らすことを目的とする。レポート生成時もラベルでフィルタ可能にする。

---

## 3. アクター

| アクター | 種別 | 説明 |
|---|---|---|
| Admin | 人（Admin） | 通知先とラベルの紐付けを設定する利用者（UR-003 に明示記述あり） |
| ExternalSystem（デバイス側アラート発生） | システム（device-svc.alert-dispatcher が起点） | ラベル付きアラートイベントを発生させ通知振り分けをトリガーする起動主体（UR-003 にアクター記述なし・SPO §3 のイベント発行元から推定補完） |

---

## 4. 前提条件

- 通知先（チャネル・宛先）が subscription-manager に登録済みであること
- アラートイベントにラベル情報が含まれていること（SP-004）

---

## 5. 事後条件（成功時）

- 通知先とラベルの紐付けが設定されていること（管理シナリオ）
- アラートのラベルに合致する通知先にのみ通知が送信されていること（配信シナリオ）
- ラベル指定でレポート対象デバイスを絞り込めること（レポートシナリオ）

---

## 6. 主フロー概要

1. 管理者が通知先（メール・Slack等）を選択し、対象ラベルを指定して紐付けを登録する（subscription-manager, SP-006）
2. デバイス側でアラートが発生し、alert-dispatcher がラベル一覧を含む `device.alert.raised` イベントを生成する（SP-004）
3. notifier がイベントを受信し、イベントのラベルと一致する通知先を subscription-manager から取得する（SP-007）
4. notifier が合致する通知先にのみ通知を送信する

---

## 7. 代替フロー

### 7a. レポート生成時のラベル絞り込み

1. 利用者がレポート生成時に対象ラベルを指定する
2. report-generator が指定ラベルに合致するデバイスのみを対象にレポートを生成する（SP-008）

---

## 8. 関連UR

| UR番号 | タイトル | CR | 備考 |
|---|---|---|---|
| UR-003 | ラベル単位の通知振り分け | CR-2026-900 | 主要対応UR（通知振り分け＋レポート絞り込みの両方を含む） |

---

## 9. 関連シーケンス一覧

| シナリオ | ファイル | 説明 |
|---|---|---|
| alert-dispatch-flow | [sequences/alert-dispatch-flow-seq.md](sequences/alert-dispatch-flow-seq.md) | アラート発生からラベル一致通知先への配信までのフロー（cross SPO §3 + notify-svc/notifier モジュール SPO §3 をベースに合成） |

（subscription-binding シナリオ：SPO に対応シーケンスなし・手動作成が必要。sequences/ には生成していない。レポート絞り込み（代替フロー7a）も同様に SPO 記載なしのためシーケンスファイル未生成）

---

## 10. 気づき・提案メモ

| # | 種別 | 内容 | 対応方針 |
|---|------|------|----------|
| 1 | 懸念 | subscription-manager の通知先・ラベル紐付け管理（SP-006）に対応するシーケンス図が SPO に存在しない。subscription-binding シナリオは CRS UR-003 説明文のみから AI 推定で生成した | 今回対応（要人確認） |
| 2 | 懸念 | レポートのラベル絞り込み（SP-008・代替フロー7a）に対応するシーケンス図が SPO に存在しない（report-generator の個別 SPO は「対象外」）。シーケンスファイルは生成していない | 今回対応（要人確認） |

---

## 11. 変更履歴

| バージョン | CR | 日付 | 変更内容 |
|---|---|---|---|
| 1.0.0 | CR-2026-900 | 2026-06-21 | 初版作成（CRS UR-003 + cross SPO §3 + notify-svc/notifier モジュール SPO §3 から AI 合成。subscription-binding・レポート絞り込みは SPO に対応シーケンスなしのため AI 推定） |
