# test-fixtures（回帰テスト用フィクスチャ索引）

このディレクトリには、XDDPツール（`ClaudeCode/.claude/` 配下のスキル・エージェント）の
動作検証用に作成した合成XDDPワークスペースが入っている。各フィクスチャは特定のPLANの
検証用に作られたものだが、修正後の回帰確認に再利用できる。

ツールを修正したときにどのフィクスチャ・どの手順で確認すればよいかは
[docs/xddp-tool-verification-checklist.md](../docs/xddp-tool-verification-checklist.md) を参照。

## フィクスチャ一覧

| ディレクトリ | REPOS構成 | 主な用途 | 参照元PLAN |
|---|---|---|---|
| [scratch-workspace/](scratch-workspace/README.md) | マルチリポジトリ（`device-svc`／`notify-svc`、`HAS_CROSS=true`） | スキル分割（`xddp.10.specs`／`xddp.close`）の回帰テスト全般。陳腐化判定（CR-901/902/903）、フルパイプライン実行用の固定要求書（`xddp-fullrun-req.md`）もここに置く | PLAN-20260619-a01-split-long-skills 他 |
| [scratch-workspace-single-repo/](scratch-workspace-single-repo/README.md) | シングルリポジトリ（`inventory-svc`、`IS_MULTI=false`固定） | `IS_MULTI=false` 時の `xddp.10.specs`／`xddp.close` 先行upsert・再導出スキップガードの検証 | PLAN-20260623-e04-specs-close-aiindex-dedup |
| [scratch-workspace-split-flag/](scratch-workspace-split-flag/README.md) | シングルリポジトリ（`catalog-svc`、2モジュール） | `xddp.10.specs` の分割実行（複数パス）後、`AI_INDEX_PREUPDATED` フラグが最新状態を反映することの検証 | PLAN-20260623-e04-specs-close-aiindex-dedup |

各フィクスチャの詳細（構成・確認済み項目・未確認項目・再実行手順）はディレクトリ内の
`README.md` を参照すること。本ファイルでは重複させない。
