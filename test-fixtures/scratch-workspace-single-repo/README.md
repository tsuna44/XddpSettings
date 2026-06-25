# scratch-workspace-single-repo（シングルリポジトリ回帰テスト用フィクスチャ）

PLAN-20260623-e04-specs-close-aiindex-dedup（`xddp.10.specs` 先行 upsert と `xddp.close` の
再導出スキップガード）のうち、`test-fixtures/scratch-workspace`（マルチリポジトリ・IS_MULTI=true固定）
では検証できない `IS_MULTI=false` シナリオを検証するための合成XDDPワークスペース。

## 構成

- `xddp.config.md`: REPOS に `inventory-svc` のみ（シングルリポジトリ・IS_MULTI=false固定）
- `inventory-svc/`: ダミーgitリポジトリ（最小限のPythonファイルのみ）
- `xddp/CR-2026-800/`: ベースラインCR（完了済み）。`baseline_docs/` はこのCRの `xddp.close` 完了後の
  状態を表す（手作業で作成）。`IS_MULTI=false` のため `baseline_docs/AI_INDEX.md` には
  「## クロスインタフェース一覧」セクション見出しが一度も存在しない。
- `xddp/CR-2026-801/`: 本検証用CR。SPECOUT_MODULES = `{reorder-planner}` のみ（`stock-tracker` は
  今回 specout 未実施）。`progress.md` に「## 工程15 AI_INDEX先行更新セクション」を
  `ユースケース一覧: 済 / モジュール別最新仕様: 済 / クロスインタフェース一覧: 対象外(IS_MULTI=false)`
  として記録済み。
- `baseline_docs/AI_INDEX.preupdate-CR-2026-801.md`: xddp.10.specs Step DONE の先行 upsert結果を
  手動シミュレーションした検証用アーティファクト（`reorder-planner` 行のみ `CR-2026-801` に更新、
  `stock-tracker` 行は不変、クロスインタフェース一覧見出しは作成されない）。

## このフィクスチャで確認済みの項目（PLAN-20260623-e04 Section 5）

- `IS_MULTI=false` のケースで「クロスインタフェース一覧」が `対象外(IS_MULTI=false)` と記録され、
  先行 upsert がこのセクション・見出しに一切触れないこと（誤って見出しが作成されないことを含む）
- `SPECOUT_MODULES` による行スコープ限定がシングルリポジトリ構成でも正しく機能すること
  （`stock-tracker` 行が変更されないことを確認）
- `xddp-close-promote-agent.md` のセクション4スキップガード（`「済」または「対象外(IS_MULTI=false)」`）が
  `対象外(IS_MULTI=false)` を正しく判定対象に含み、かつ元々 `IS_MULTI のみ` ゲートにより
  このセクションが実行されないケースと整合し実害がないこと

## 未確認の項目（今後の回帰テストで使える）

- 実際の `/xddp.10.specs CR-2026-801` / `/xddp.close CR-2026-801` のライブ実行（本フィクスチャは
  Step DONE の先行 upsert ロジックを手動シミュレーションして検証したのみ）
- シングルリポジトリ構成から `REPOS:` にエントリを追加して `IS_MULTI=true` に移行する初回CR
  （クロスインタフェース一覧見出しの新規作成シナリオ。`test-fixtures/scratch-workspace` 側で
  別途確認済みのロジックをシングルリポジトリ起点で再現する場合に使える）

## 再実行する場合

```
cd test-fixtures/scratch-workspace-single-repo
# /xddp.10.specs CR-2026-801 や /xddp.close CR-2026-801 を試す場合は
# progress.md の状態を確認の上、必要に応じてリセットしてから実行する
```
