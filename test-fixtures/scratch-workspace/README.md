# scratch-workspace（回帰テスト用フィクスチャ）

PLAN-20260619-a01-split-long-skills（`xddp.10.specs`／`xddp.close` のエージェント分割）の動作検証用に作成した、
合成XDDPワークスペース。完了済みCR（CR-2026-900）が1件入っている。

## 構成

- `xddp.config.md`: REPOS に `device-svc`／`notify-svc`（マルチリポジトリ・HAS_CROSS=true）
- `device-svc/`・`notify-svc/`: ダミーgitリポジトリ（最小限のPythonファイルのみ）
- `xddp/CR-2026-900/`: 合成CR。CRS（UR×3, SP×9）・SPO（device-svc/notify-svc 各6モジュール＋cross）・
  CHD（cross に breaking:true のインタフェース変更を含む）・TRS（NG×1）を手作業＋AIで作成
- `xddp/lessons-learned.md`: LL×4（repo: device-svc/notify-svc/cross/unknown を1件ずつ含む）
- `baseline_docs/`: `/xddp.close` 完了後の状態（AI_INDEX.md・各repoのspecs/crs/test/knowledge）

## このフィクスチャで実機確認済みの項目

- `xddp-specs-uc-agent`／`xddp-specs-mod-agent`（CRS/SPOからの仕様生成、CHD欠落検出）
- モジュール数>10のコンテキスト圧迫チェック発火
- Step GATE/Step D での保留事項集約表示（廃止候補・破壊的変更・要確認LL等）
- **`xddp-close-promote-agent` の部分失敗検出**（`baseline_docs/notify-svc` を一時的にファイル化してENOTDIRを誘発し、
  notify-svcのみ失敗・device-svcは成功という結果が正しく記録され、Step Dが「全repo成功」と誤報告しないことを確認）
- `xddp-close-knowledge-agent`（project-rulebook upsert・code-knowledge昇格、C3.5/C3.6の責務分離）

## 未確認の項目（今後の回帰テストで使える）

- UR>20 / モジュール>10 での実際の分割実行（RESUME_UR_LIST/MODULE_SCOPEへの非空値の伝達）
- 分割実行継続マーカーをまたぐ複数セッション実行
- シングルリポジトリ構成（IS_MULTI=false）
- 並行CR競合シナリオ（Step C0-4: OVERLAP_FILES）— `baseline_docs` をgit管理下に置けば再現可能

## 再実行する場合

```
cd test-fixtures/scratch-workspace
# /xddp.10.specs CR-2026-900 や /xddp.close CR-2026-900 を再実行可能
# （CR-2026-900は完了済みなので、新規CRを作って試すか、progress.mdの状態を戻してから再実行する）
```
