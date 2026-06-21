# Step MOD 保留事項
CR: CR-2026-900 / REPO: device-svc

## 生成/更新したモジュール一覧
- sensor-reader — 更新なし（SPO・CHD 内容に変化なし。spec.md/structure.md は既に CR-2026-900 で last-verified-cr 済み。フォーマット差異もなし）
- alert-dispatcher — 更新なし（SPO・CHD 内容に変化なし。spec.md/structure.md/sequences/main-seq.md は既に CR-2026-900 で last-verified-cr 済み）
- calibration — 更新なし（SPO 内容に変化なし。spec.md のみ既存・既に CR-2026-900 で last-verified-cr 済み）
- device-registry — 更新なし（SPO・CHD 内容に変化なし。spec.md のみ既存・既に CR-2026-900 で last-verified-cr 済み）
- firmware-updater — 更新なし（SPO 内容に変化なし。spec.md のみ既存・既に CR-2026-900 で last-verified-cr 済み）
- power-monitor — 更新なし（SPO 内容に変化なし。spec.md のみ既存・既に CR-2026-900 で last-verified-cr 済み）

（今回は再実行であり、前回実行時点から各モジュールの SPO・CHD・CRS 内容に差分が検出されなかったため、機械的先決基準・AIセマンティック判断のいずれにおいても「更新あり」の条件に該当しなかった。全6ファイル群はスキップ対象。）

## 廃止候補（人の削除確認待ち）
- `xddp/latest-specs/device-svc/legacy-stub/` — 理由: 今回CR（CR-2026-900）の `04_specout/device-svc/modules/*/`（sensor-reader, alert-dispatcher, calibration, device-registry, firmware-updater, power-monitor の6モジュール）に対応するディレクトリが存在しない。
  - `legacy-stub/spec.md` の `last-updated-cr: "CR-2026-900"` は現在のCRと一致しているため並行CR保護の除外対象には該当しない（保護対象外 = 廃止候補として記録する）。
  - `last-verified-cr: "CR-2026-800"`（旧CR）であり、今回CRのSPOで再確認されていない点も廃止候補としての裏付けとなる。
  - 予約名（`overview`）には該当しない。
  - 削除は実行せず、本ファイルへの記録のみ。削除実行は Step GATE 後にオーケストレーター側が人の確認を経て行う。

## ケバブ名衝突・SPO照合不能モジュール
なし（6モジュールすべて `04_specout/device-svc/modules/*/` に対応する既存 latest-specs ディレクトリがあり、予約名（overview/cross/system）との衝突もなし）

## リネーム候補
なし（`legacy-stub` は既存6モジュールのいずれとも名称・内容上のセマンティックな対応が見られず、リネーム候補ではなく廃止候補として判断した）
