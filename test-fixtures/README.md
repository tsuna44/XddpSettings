# test-fixtures（回帰テスト用フィクスチャ索引）

このディレクトリには、XDDPツール（`ClaudeCode/.claude/` 配下のスキル・エージェント）の
動作検証用に作成した合成XDDPワークスペースが入っている。各フィクスチャは特定のPLANの
検証用に作られたものだが、修正後の回帰確認に再利用できる。

ツールを修正したときにどのフィクスチャ・どの手順で確認すればよいかは
[docs/xddp-tool-verification-checklist.md](../docs/xddp-tool-verification-checklist.md) を参照。

## フィクスチャ一覧

| ディレクトリ | REPOS構成 | 主な用途 | 参照元PLAN |
|---|---|---|---|
| [scratch-workspace/](scratch-workspace/README.md) | マルチリポジトリ（`device-svc`／`notify-svc`、`HAS_CROSS=true`） | スキル分割（`xddp.11.specs`／`xddp.close`）の回帰テスト全般。陳腐化判定（CR-901/902/903）、フルパイプライン実行用の固定要求書（`xddp-fullrun-req.md`）もここに置く | PLAN-20260619-a01-split-long-skills 他 |
| [scratch-workspace-min/](scratch-workspace-min/README.md) | `multi/`（`svc-a`／`svc-b`、`HAS_CROSS=true`）＋`single/`（`svc-a`を相対パス共有、`IS_MULTI=false`）の対 | トークン最小・無害な動作確認用の汎用フィクスチャ。任意のXDDPスキル修正時に、`IS_MULTI=true/false` 両方の挙動を低コストで確認する（特定PLAN専用ではなく随時再利用する想定） | PLAN-20260711-feedback-to-crs-skill（作成の発端）＋汎用 |

各フィクスチャの詳細（構成・確認済み項目・未確認項目・再実行手順）はディレクトリ内の
`README.md` を参照すること。本ファイルでは重複させない。
