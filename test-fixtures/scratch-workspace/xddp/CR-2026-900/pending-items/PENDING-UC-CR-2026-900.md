# Step UC 保留事項
CR: CR-2026-900

## 生成/更新したユースケース一覧
- device-label-management — 新規（UR-001 デバイスへのラベル付与。related-modules: device-registry）
- alert-label-filtering — 新規（UR-002 ラベル単位のアラートフィルタ。related-modules: alert-dispatcher）
- label-based-notification-routing — 新規（UR-003 ラベル単位の通知振り分け。related-modules: subscription-manager, notifier, alert-dispatcher, report-generator）

## 廃止候補（人の削除確認待ち）
なし
（既存 `latest-specs/system/use-cases/` ディレクトリが存在しなかったため、今回が全ユースケースの初版生成。廃止候補の検出対象が存在しない）

## related-modules 照合不能ユースケース
なし
（3件すべて CRS §4 仕様一覧（SP-001〜SP-009）の対象モジュール列との照合により related-modules を確定できた）

## 命名衝突・重複記述
なし

## 補足：SPO 対応シーケンスなしのため AI 推定補完したシナリオ（要人確認）
- device-label-management — UR-001 のラベル付与・削除フロー。device-registry の SPO（全体・個別）にラベル付与操作のシーケンス図記載がないため、description.md §6/§7 を CRS UR-001 説明文のみから AI 推定で生成した。sequences/ は空（ファイル未生成）。
- alert-label-filtering — UR-002 のラベル絞り込み表示フロー。alert-dispatcher の SPO にアラート一覧フィルタのシーケンス図記載がないため、description.md §6 を CRS UR-002 説明文のみから AI 推定で生成した。sequences/ は空（ファイル未生成）。
- label-based-notification-routing — 以下2点は SPO に対応シーケンスなし：
  1. 管理者による通知先・ラベル紐付け登録（SP-006、subscription-binding シナリオ）— description.md §6 ステップ1 に記述したが sequences/ ファイルは未生成
  2. レポートのラベル絞り込み（SP-008、代替フロー7a）— sequences/ ファイルは未生成
  生成済みの `sequences/alert-dispatch-flow-seq.md` は cross SPO §3 + notify-svc/notifier モジュール SPO §3 を根拠とする実データ合成（推定ではない）。
  ただし alert-dispatch-flow の起動主体（人間の操作ではなくデバイス側アラート検知）は UR-003 に明示記述がないため、SPO のイベント発行元（device-svc.alert-dispatcher）から ExternalSystem として推定補完した（「（推定補完）」注記あり）。

## シングルリポジトリでの重複防止チェック
対象外（IS_MULTI=true）。なお label-based-notification-routing/sequences/alert-dispatch-flow-seq.md の「実装詳細参照」リンク（device-svc/notify-svc/cross の overview/sequences/）は、対象パスが本 CR の Step OV 実行で生成される前提のリンクであり、Step OV 完了前は broken リンクとなる（許容）。
