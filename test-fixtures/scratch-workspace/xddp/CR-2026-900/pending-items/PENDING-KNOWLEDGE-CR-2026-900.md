# Step C3.5-C3.6 保留事項
CR: CR-2026-900

## _domain名要確認一覧（_flows/_constants/_structures 生成時の暫定ドメイン名）
- `sensor`（device-svc） — 対象: `device-svc/knowledge/code-knowledge/_flows/sensor-alert-dispatch-sequence.md`（sensor-reader → alert-dispatcher のモジュール間シーケンス図。SPO に明示的なドメイン名がないため AI が内容から推定）
- `alert`（cross） — 対象: `cross/knowledge/code-knowledge/_constants/alert-constants.md`（SEVERITY_* 共有定数）
- `alert`（cross） — 対象: `cross/knowledge/code-knowledge/_structures/alert-relations.md`（AlertEvent 共有データ型関連図）
- `alert`（cross） — 対象: `cross/knowledge/code-knowledge/_flows/alert-publish-dispatch-sequence.md`（device-svc.alert-dispatcher → EventBus → notify-svc.notifier のリポジトリ間シーケンス図）

## notify-svc 知見昇格の未完了一覧（{DOCS}/notify-svc が通常ファイルのため ENOTDIR でブロック）
> 既知の事象（sibling agent xddp-close-promote-agent の Step C2-C7 で報告済み: `PENDING-PROMOTE-CR-2026-900.md` 参照）。本タスク（C3.5/C3.6）側でも独立に再現確認した。

- **Step C3.5（project-rulebook）への影響: なし。** project-rulebook-notify-svc.md は `{XDDP_DIR}`（`baseline_docs` ではない）配下のため、本問題の影響を受けず正常に作成・更新できた（LL-002 を Section 4 に追記）。
- **Step C3.6（code-knowledge）への影響: あり。** 以下の昇格はすべて `{DOCS}/notify-svc/...` への書き込みが必要なため `ENOTDIR` エラーで失敗し、未実施。
  - notify-svc SPO Section 5.6（非機能特性）2件の昇格未実施:
    - `src/notifier.py:dispatch()`（影響度: 高）→ `notify-svc/knowledge/code-knowledge/notifier/constraints.md`（パフォーマンス・非機能特性）
    - `src/report_generator.py:generate()`（影響度: 中）→ `notify-svc/knowledge/code-knowledge/report-generator/constraints.md`（パフォーマンス・非機能特性）
  - LL-002（#コーディング, repo: notify-svc）の code-knowledge 側への昇格は対象外（#コーディングタグは C3.6 の対象タグではないため、当初から code-knowledge への昇格対象ではない。project-rulebook 側へは昇格済み）
  - notify-svc 向け TRS は本CRに存在しないため、TRS由来の昇格は元々対象なし
- **対応方針（人への提案）:** `{DOCS}/notify-svc` の内容を確認し、不要なファイルであれば削除した上で `/xddp.close` の Step C3.6 を notify-svc に対して再実行することで、上記2件の昇格をやり直せる。

## その他の補足

- device-svc の `_flows/` ディレクトリに、生成時の命名ミスにより重複ファイルが残存している:
  - `device-svc/knowledge/code-knowledge/_flows/shared-module-間シーケンス図-sequence.md`（非ASCII・不適切な命名。誤って先に生成したファイル）
  - 正しいファイルは `device-svc/knowledge/code-knowledge/_flows/sensor-alert-dispatch-sequence.md`（内容は同一の sensor-reader↔alert-dispatcher フロー）
  - **対応方針（人への提案）:** 誤った命名のファイル（`shared-module-間シーケンス図-sequence.md`）を削除してください。本エージェントにはファイル削除権限がないため自動削除していません。
- cross SPO Section 4.2（DFD）は device-svc・notify-svc いずれも「対象外」のため、DFD 由来の昇格（code-knowledge-flows-dfd-template 使用）は本CRでは発生していません。
- LL-001（#リスク, device-svc）は project-rulebook の Section マッピング対象外（C3.5 のマッピング表に `#リスク` は含まれない）のため project-rulebook へは未反映だが、C3.6 の「LL #リスク/#見落とし タグエントリから昇格」ルールに従い `device-svc/knowledge/code-knowledge/sensor-reader/constraints.md`（既知の制約・落とし穴, CK-001）へ正常に昇格済み。
- LL-004（#プロセス, repo: unknown）は C3.5・C3.6 いずれも対象外（プロセス系タグは知見ログのみで管理され、project-rulebook・code-knowledge への昇格対象外）。repo: unknown のため knowledge/lessons-learned.md 側への昇格自体も別タスク（C3系）の保留事項として `PENDING-PROMOTE-CR-2026-900.md` に記録済み。
