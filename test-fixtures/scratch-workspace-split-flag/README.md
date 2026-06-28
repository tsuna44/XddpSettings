# scratch-workspace-split-flag（分割実行フラグ鮮度回帰テスト用フィクスチャ）

PLAN-20260623-e04-specs-close-aiindex-dedup の確認項目「分割実行（複数回の `/xddp.10.specs {CR}` 実行）後、
最終回の Step DONE で記録される `AI_INDEX_PREUPDATED` フラグが最新の状態を反映していること」を検証するための
合成XDDPワークスペース。

## 構成

- `xddp.config.md`: REPOS に `catalog-svc` のみ（シングルリポジトリ・本シナリオでは IS_MULTI は無関係）
- `catalog-svc/`: ダミーgitリポジトリ（`search-index`・`price-engine` の2モジュール）
- `xddp/CR-2026-700/`: ベースラインCR（完了済み）。`baseline_docs/` はこのCRの `xddp.close` 完了後の状態
- `xddp/CR-2026-701/`: 本検証用CR。Step MOD がモジュール単位で分割実行されたケースを2パスで再現する
  - `progress.md`（ライブファイル）: **PASS 2（最終回・全体完了）** 時点の状態。両モジュールが処理済みで
    process step 15 が ✅ 完了している
  - `evidence/progress.pass1-partial.md`: **PASS 1（中間・`search-index` のみ処理済み）** 時点の
    スナップショット。process step 15 は 🔄 進行中
  - `evidence/AI_INDEX.preupdate-pass1-partial.md`: PASS 1 の Step DONE が生成したであろう
    AI_INDEX.md 先行更新結果（`price-engine` 行は `CR-2026-700` のまま、実質的に不完全）
  - `evidence/AI_INDEX.preupdate-pass2-final.md`: PASS 2 の Step DONE が生成した最終的な
    AI_INDEX.md 先行更新結果（両モジュールが `CR-2026-701` に更新済み）

## このフィクスチャで確認済みの項目（PLAN-20260623-e04 Section 5）

- PASS 1（中間パス）では「## 工程15 AI_INDEX先行更新セクション」の「モジュール別最新仕様: 済」が、
  実質的に不完全な状態（`price-engine` 行が古いまま）でも記録され得ることを確認した
  （`xddp.10.specs/SKILL.md` の先行 upsert 指示は SPECOUT_MODULES の上限のみを規定し、
  Step MOD 自体の分割進捗とは独立に「済」を記録できる）
- しかし PASS 1 では process step 15 が 🔄 進行中のままであり、`xddp.close/SKILL.md` Step 0 の
  前提チェック（process step 15 が ✅ 完了でなければ `xddp.10.specs` を先に実行させる）により、
  `xddp.close` がこの不完全な「済」を読みに行くことは構造的に発生しない
- PASS 2（最終回）の Step DONE が「## 工程15 AI_INDEX先行更新セクション」を完全に上書きし、
  両モジュールを反映した正しい状態にしてから process step 15 を ✅ にするため、`xddp.close` が
  実際に読む値（ライブの `progress.md`）は常に最新かつ完全であることを確認した
  （PASS 1 と PASS 2 の `AI_INDEX.preupdate-*.md` の diff で `price-engine` 行のみが訂正されることを確認）

## 未確認の項目（今後の回帰テストで使える）

- 実際の `/xddp.10.specs CR-2026-701` を2回（PASS 1, PASS 2）に分けてライブ実行すること
  （本フィクスチャは両PASSの結果を手動シミュレーションして検証したのみ）
- UR単位分割（Step UC 部分完了）が絡む場合の同種シナリオ（本フィクスチャは Step MOD のモジュール単位
  分割のみを対象とする）

## 再実行する場合

```
cd test-fixtures/scratch-workspace-split-flag
# /xddp.close CR-2026-701 はそのまま実行可能（PASS 2 完了済み状態）
# PASS 1 の状態を再現する場合は evidence/progress.pass1-partial.md の内容を
# xddp/CR-2026-701/progress.md に戻し、price-engine/spec.md の last-updated-cr を
# CR-2026-700 に戻してから /xddp.10.specs CR-2026-701 を試す
```
