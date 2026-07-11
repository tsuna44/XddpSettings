# XDDPツール動作確認チェックリスト

`ClaudeCode/.claude/` 配下（skills・agents・templates）を修正したときに、
「何を確認すれば一通り動くと判断できるか」を整理したチェックリスト。

運用方針: **部分実行チェックリスト＋フルパイプライン1本**。

- 変更箇所が特定のスキル・工程に限定される場合は、2節の表で該当行だけ再実行して確認する
- 変更箇所が `xddp.common` など全スキル共通部分、テンプレート構造、`xddp.config.md` の
  読み込みロジックなど広範囲に影響する場合は、3節のフルパイプライン手順で
  `/xddp.01.init` 〜 `/xddp.close` を通しで実行する

実際にどちらを使うかは修正内容に応じて判断する（本ドキュメントは判断材料の提供までで、
強制ルールではない）。

---

## 1. 既存フィクスチャ

`test-fixtures/` 配下の各フィクスチャの用途は [test-fixtures/README.md](../test-fixtures/README.md) を参照。

---

## 2. 部分実行チェックリスト（変更箇所別）

| 変更箇所 | 影響するスキル | 確認内容 | 使うフィクスチャ／コマンド |
|---|---|---|---|
| `xddp.common`（CR解決等の共通ロジック） | 全スキル | 全スキルが引き続きCRを解決できるか | 3節のフルパイプラインを実施 |
| `xddp.01.init` | ワークスペース初期化 | フォルダ構成・`progress.md`・`xddp.config.md` の生成内容 | `scratch-workspace-single-repo` / `scratch-workspace` で新規CRを作成 |
| `xddp.02.analysis` 〜 `xddp.06.design`（AIレビュー系） | 各工程のレビュールール | レビュー→修正ループのラウンド数・終了条件 | `xddp.plan-review` 単体実行、または対象スキルを既存CRに対して再実行 |
| `xddp.04.specout` | Discovery BFS | `SPECOUT_MAX_WAVE_DEPTH` 等の設定が効くか | `scratch-workspace`（device-svc/notify-svc）で再実行 |
| `xddp.06.design`（CHD分割生成） | CHD分割ロジック | UR数が多いCRで分割実行・継続マーカーが機能するか | `scratch-workspace-split-flag` |
| `xddp.07.code` / `xddp.08.verify` | コーディング・静的検証 | 設計適合性チェックが動くか | 既存CRに対し再実行 |
| `xddp.09.test` | テスト仕様（TSP）生成・AIレビュー→人レビューゲート | TSP生成で停止しテスト実行を含まないこと | 既存CRに対し再実行 |
| `xddp.10.test-run` | テスト実行・`MIN_COVERAGE`・不具合修正 | 独立起動での自己完結（CR解決・AFFECTED_REPOS再解決）・閾値判定（自動合格／人承認の分岐）・TSP未作成時の`/xddp.09.test`誘導停止 | 既存CRに対し再実行 |
| `xddp.11.specs` | `latest-specs/` 生成（Kruchten 4+1ビュー） | ディレクトリ構造・既存ファイルとの重複検出 | `scratch-workspace`（CR-2026-903が参考例） |
| `xddp.close` | 知見集約・project-rulebook upsert・AI_INDEX更新・分割実行 | 部分失敗検出・並行CR保護・陳腐化判定 | `scratch-workspace`（CR-2026-901/902/903） |
| `xddp.fill-rulebook` / `xddp.codemap` / `xddp.excel2md` / `xddp.md2excel` | 単体スキル | 個別実行のみで十分（他工程への波及がない） | 任意のフィクスチャで単体実行 |
| `xddp.config.md` テンプレートにキー追加・変更 | 設定読み込み全般 | single-repo と multi-repo（+cross）の両方で設定が反映されるか | `scratch-workspace-single-repo` と `scratch-workspace` |

表に対応しない変更（新規スキル追加など）の場合は、影響する工程を
[README.md の フェーズ一覧](../README.md) から特定し、最も近い行に倣って確認する。

---

## 3. フルパイプライン実行手順

影響範囲が広い変更、または2節の表で判断できない変更があったときに実施する。

- **対象フィクスチャ**: `test-fixtures/scratch-workspace`
  （マルチリポジトリ・`HAS_CROSS=true`。既存の回帰テスト用フィクスチャを再利用し、
  新規にダミーリポジトリを作らない）
- **CR番号**: `CR-2026-910` 以降を「フルパイプライン専用」として予約する。
  900番台のシナリオ専用CR（901〜903、将来追加分含む）とは番号が重複しないようにする
- **入力要求書**: [test-fixtures/scratch-workspace/xddp-fullrun-req.md](../test-fixtures/scratch-workspace/xddp-fullrun-req.md)
  を毎回同じ入力として使う（再現性を優先し、要求内容は都度変えない）
- **実行コマンド列**:
  ```
  /xddp.01.init CR-2026-910 xddp-fullrun-req.md
  /xddp.02.analysis CR-2026-910
  /xddp.03.req CR-2026-910
  /xddp.04.specout CR-2026-910
  /xddp.05.arch CR-2026-910
  /xddp.06.design CR-2026-910
  /xddp.07.code CR-2026-910
  /xddp.09.test CR-2026-910
  /xddp.10.test-run CR-2026-910
  /xddp.11.specs CR-2026-910
  /xddp.close CR-2026-910
  ```
- **合格基準**:
  - 各工程がエラーで停止せず、対応する成果物ファイルが生成される
  - `progress.md` の工程番号が順に更新される
  - AIレビュー→修正ループが最低1回は回る（レビュー指摘が0件で即終了する場合は
    レビューが機能しているか別途確認する）
  - `xddp.close` 完了後、`lessons-learned.md` と `baseline_docs/AI_INDEX.md` が更新される
- **実行後の扱い**: 完了後はCRをクローズ済みのまま残し、次回フルパイプライン確認時は
  新しいCR番号（911, 912, ...）を使う。フィクスチャの再利用性より再現性を優先する
