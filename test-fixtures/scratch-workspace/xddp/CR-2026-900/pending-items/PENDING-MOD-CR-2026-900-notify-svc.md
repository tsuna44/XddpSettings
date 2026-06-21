# Step MOD 保留事項
CR: CR-2026-900 / REPO: notify-svc

## 生成/更新したモジュール一覧
- notifier — 新規（spec.md / structure.md / sequences/main-seq.md。CHD SP-007 反映、state-machine.md は SPO「対象外」のためスキップ）
- subscription-manager — 新規（spec.md / structure.md。CHD SP-006 反映。state-machine.md・sequences/ は SPO「対象外」のためスキップ）
- report-generator — 新規（spec.md のみ。CRS §4 SP-008 反映、CHD に本モジュールの詳細設計記述なし。structure.md・state-machine.md・sequences/ は SPO「対象外」のためスキップ）
- audit-logger — 新規（spec.md のみ。CRS §4 SP-009 反映、CHD に本モジュールの詳細設計記述なし。structure.md・state-machine.md・sequences/ は SPO「対象外」のためスキップ）
- template-engine — 新規（spec.md のみ。対象 SP なし、SPO §2 のみから生成。structure.md・state-machine.md・sequences/ は SPO「対象外」のためスキップ）
- delivery-queue — 新規（spec.md のみ。対象 SP なし、SPO §2 のみから生成。structure.md・state-machine.md・sequences/ は SPO「対象外」のためスキップ）

## 廃止候補（人の削除確認待ち）
なし（今回が notify-svc の latest-specs モジュールディレクトリ初回生成のため、既存ディレクトリとの比較対象なし。`overview/architecture.md` のみ既存で、今回スコープ対象外＝予約名称のため変更せず）

## ケバブ名衝突・SPO照合不能モジュール
なし

## リネーム候補
なし

---

## 確認事項メモ（参考情報・ブロッキングなし）

1. **report-generator（SP-008）・audit-logger（SP-009）について：** CHD-CR-2026-900.md（notify-svc）には SP-006・SP-007 の詳細設計のみが記載されており、SP-008（レポートのラベル絞り込み）・SP-009（ラベル変更の監査ログ記録）に対応する詳細設計記述が存在しなかった。両モジュールの spec.md は CRS §4 の Before/After 記述のみを反映し、実装詳細（パラメータ名・記録フォーマット等）は「未確認」として明記した。設計フィードバック時の確認を推奨する。
2. **audit-logger の対象ファイルパスについて：** SP-009 の対象モジュールは CRS 上「audit-logger, device-registry」（device-svc 側）と記載されており、ラベル変更操作自体は device-svc 側で発生する。notify-svc 側 audit-logger がどのように記録するか（イベント連携方式等）は CHD に記述がないため未確認のまま記録した。
