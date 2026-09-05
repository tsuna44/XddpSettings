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
| [scratch-workspace-survey-flat/](scratch-workspace-survey-flat/README.md) | シングルリポジトリ（`flat-svc`、`module-catalog.md` 不在＝常に縮退モード） | `xddp.survey` の縮退モード時モジュール解決（ディレクトリ一致・ファイル名一致フォールバック・CamelCase・同名ファイル複数候補・一致なしエラー）の確認用 | PLAN-20260905-survey-flat-module-fallback |

各フィクスチャの詳細（構成・確認済み項目・未確認項目・再実行手順）はディレクトリ内の
`README.md` を参照すること。本ファイルでは重複させない。

## 開発時テストハーネス（`tools/harness/`）関連

`make smoke-full`（L4/L5 full-run スモーク）が使う入力・期待値を以下に置く（PLAN-20260725-p2-test-harness）。

| ディレクトリ | 用途 |
|---|---|
| [golden/](golden/README.md) | full-run スモークの構造性質ゴールデン（JSON。見出し集合・ID 集合・件数・状態値。散文は固定しない）。校正ランで確定 |
| [scratch-workspace-min/seeds/](scratch-workspace-min/seeds/README.md) | 工程別入口状態スナップショット（フェーズ単位起動用）。校正ランの生成物から起こす |

`make test`（L1〜L3・0トークン）はこれらを使わず `ClaudeCode/.claude/` を直接検査する。
