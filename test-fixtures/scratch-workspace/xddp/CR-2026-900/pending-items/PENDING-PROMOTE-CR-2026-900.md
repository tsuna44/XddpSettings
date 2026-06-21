# Step C2-C7 保留事項
CR: CR-2026-900

## リポジトリ別処理結果一覧

- device-svc: 成功（C2/C3/C4/C5/C6 すべて完了。project-rulebook-device-svc.md は XDDP_DIR に存在しないため C6 は対象外＝該当なし。C5 は TSP なし・TRS-CR-2026-900-001.md のみ昇格）
- notify-svc: 失敗（C2/C3/C4/C5/C6 のすべてのステップで失敗）
  - 失敗ステップ: C2（仕様書昇格）
    - 理由: `{DOCS}/notify-svc` がディレクトリではなく通常ファイルとして存在しているため、`{DOCS}/notify-svc/specs/...` 配下へのファイル作成が `ENOTDIR` エラーで失敗した（実際に `overview/architecture.md` 等の書き込みを試行し再現確認済み）。
  - 失敗ステップ: C3（知見ログ昇格）
    - 理由: 同上の理由により `{DOCS}/notify-svc/knowledge/lessons-learned.md` への書き込みが `ENOTDIR` で失敗した。LL-002（フィルタ条件「空配列=全件対象」は明示的にテストすべき／repo: notify-svc）は昇格未完了。
  - 失敗ステップ: C4（CRS昇格）
    - 理由: 同上の理由により `{DOCS}/notify-svc/crs/CRS-CR-2026-900.md` への書き込みが `ENOTDIR` で失敗した。
  - 失敗ステップ: C5（テスト仕様・結果昇格）
    - 理由: notify-svc 向け TSP・TRS は今回 CR に存在しなかったため実質的な対象ファイルはなかったが、`{DOCS}/notify-svc/test/` も同じ親ディレクトリ問題のため作成不可と判断する（同根の障害）。
  - 失敗ステップ: C6（project-rulebook昇格）
    - 理由: `{XDDP_DIR}/project-rulebook-notify-svc.md` 自体が存在せず対象ファイルはなかったが、仮に存在していても同じ `ENOTDIR` 障害で `{DOCS}/notify-svc/project-rulebook.md` の作成は失敗していたと推定される。
  - **対応方針（人への提案）:** `{DOCS}/notify-svc` の内容を確認し、不要なファイルであれば削除した上で `/xddp.close` を再実行することで notify-svc 側の昇格をやり直せる。ファイルの内容に必要な情報が含まれる場合は、退避してから削除すること。

## 要確認LL一覧（repo:unknown スキップ分）

- LL-004：レビュー観点の引き継ぎが工程間で漏れることがある — repo: unknown（昇格先リポジトリ不明のため device-svc/cross いずれの knowledge/lessons-learned.md にも昇格していない。人が repo を確定後、手動で該当 knowledge/lessons-learned.md に追記してください）

## 破壊的変更フラグ・対象インタフェース一覧

- 破壊的変更: あり
- 対象インタフェース: device-alert-raised（device-svc → notify-svc、v1.0.0 → v2.0.0、`labels` フィールド必須追加）
- 対応: AI_INDEX.md の cross インタフェース一覧行に ⚠️ 破壊的変更あり（CR: CR-2026-900）の注記を追加済み。device-svc 側の knowledge/lessons-learned.md には破壊的変更警告 LL を追記済み。notify-svc 側の knowledge/lessons-learned.md には本来同じ警告を追記すべきだが、上記 C3 失敗（ENOTDIR）により未追記。`{DOCS}/notify-svc` の問題解消後、xddp.close 再実行または手動追記が必要。

## 削除候補一覧（system/use-cases・repo モジュールディレクトリ）

なし
（`{XDDP_DIR}/latest-specs/system/use-cases/` 配下の3ディレクトリ（device-label-management, alert-label-filtering, label-based-notification-routing）はすべて今回新規昇格であり、`{DOCS}/system/specs/use-cases/` は今回 CR で初めて作成されたため、削除候補となる既存ディレクトリは存在しない。
device-svc については `{DOCS}/device-svc/specs/` 配下のモジュールディレクトリ（sensor-reader, alert-dispatcher, calibration, device-registry, firmware-updater, power-monitor）はすべて `{XDDP_DIR}/latest-specs/device-svc/` に対応するディレクトリが存在し、削除候補なし。
notify-svc は `{DOCS}/notify-svc/specs/` 自体が存在しない（ファイルにブロックされている）ため、削除候補の判定は実施できなかった。）

## AI_INDEX.md アーカイブ候補

なし（更新後の AI_INDEX.md は76行であり、500行のアーカイブ閾値を超えていない）

## git コンフリクト発生時のガイダンス（参考情報・本CRでは未発生）

- 仕様書ファイル（`{repo}/specs/`・`cross/specs/`・`system/specs/`）: 今回 CR の変更を優先する（`git checkout --ours`）。他 CR の変更が必要な場合は xddp.close を再実行後に手動マージする。
- AI_INDEX.md: テーブル行単位で統合する。同一キー（ユースケース名・リポジトリ名・モジュール名）を持つ行は最新 CR のものを採用する。
- lessons-learned / project-rulebook: 追記型のため通常コンフリクトしにくいが、発生した場合は両方の変更を保持して末尾に追記する。
- コンフリクト解決後は `git add` して `git commit` し、DOCS_DIR のリモートにプッシュする（オーケストレーター・人が実施）。

## 補足：既存 AI_INDEX.md「モジュール別最新仕様」テーブルの notify-svc 行について

`{DOCS}/AI_INDEX.md` には本タスク実行前から notify-svc の6モジュール（notifier, subscription-manager, report-generator, template-engine, delivery-queue, audit-logger）の行が既に存在していたが、リンク先 `notify-svc/specs/.../spec.md` は実体が存在しない（`{DOCS}/notify-svc` がファイルのため）。今回の C2 昇格失敗により、この不整合は解消されなかった。`{DOCS}/notify-svc` の問題解消後に xddp.close を再実行し、リンクの実体化を確認すること。
