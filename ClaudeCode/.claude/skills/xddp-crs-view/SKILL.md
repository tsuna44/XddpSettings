---
name: xddp-crs-view
description: CRS を階層的に閲覧できる HTML ビューア／CLIツリーを生成する。
  Excel が使えない環境向け。「CRSを見やすく表示して」「階層ビューを作って」などで起動する。
argument-hint: "[CR番号] [--format html|tree] [--status \"...\"]"
---

You are executing **XDDP CRS View — Hierarchical Viewer / CLI Tree** (Excel を要さない CRS レビュー手段)。

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) [--format html|tree] [--status "..."]
- CR_NUMBER: optional; auto-detected from XDDP_DIR if omitted
- `--format`: optional; `html`（既定）または `tree`
- `--status`: optional; `--format tree` のときのみ有効。カンマ区切りでステータスを絞り込む
  （例: `--status "🔍 要検討,❓ 未決"`）

---

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.

(xddp.config.md lookup done in xddp-common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.
Let `CRS_PATH` = `{CR_PATH}/03_change-requirements/CRS-{CR}.md`（`xddp-revise/SKILL.md` の `req` マッピングと同一パス）。

Parse REST_ARGS for `--format` (default: `html`) and `--status` (tree のみ有効).

If CRS_PATH が存在しない場合: エラー「CRS が見つかりません: {CRS_PATH}」で停止する。

## Step 1: Render

`--format html`（既定）の場合:
Run via Bash:
```
PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-crs-view/scripts/crs_view.py {CRS_PATH} --format html --out {CR_PATH}/03_change-requirements/CRS-{CR}-view.html
```

`--format tree` の場合、ファイルを作らずターミナルへ直接出力する:
```
PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-crs-view/scripts/crs_view.py {CRS_PATH} --format tree {--status "{STATUS}" があれば付与}
```
出力をそのままユーザーに提示する。

## Step 2: Report in Japanese

`--format html` の場合、生成したファイルパスを伝え、以下を日本語で簡潔に案内する:
- ステータスチップ・全文検索での絞り込み方法
- 「全展開」「全折畳」ボタン
- SP カードのコメント欄にレビュー指摘（重要度: 🔴 重大／🟡 軽微／🔵 提案）を入力できること
- 「指摘を.md出力」でダウンロードした `.md` を人が伝えてくれれば、後述の「取り込み手順」で
  `/xddp-revise {CR} req` に連携できること
- コメントはブラウザの localStorage に保存されるため、同じブラウザで再度開けば入力内容が復元されること

## エクスポートした .md の取り込み手順

人が `/xddp-crs-view` の HTML から「指摘を.md出力」または「指摘をコピー」で書き出した Markdown の
内容を伝えたら、以下の手順で取り込む。

書き出される Markdown は `## 2. 指摘事項と対応内容` テーブルを
`#`／`重要度`／`場所`（SP ID＋タイトル）／`指摘内容`（自由記述）／`対応内容`（空欄）／
`対応状況`（常に `⬜ 未対応`）の6列で持つ（`review-template.md` と同一列構成）。
コメント欄が空欄だった SP の行は出力されない（「問題なし」は無言で表現される）。

1. Let `REVIEW_FILE` = `{CR_PATH}/03_change-requirements/review/03_change-requirements-review.md`
   （`/xddp-revise req` が読む対象と同一パス。`xddp-revise/SKILL.md`「## 4. Record in review file」参照）。
2. **REVIEW_FILE が存在する場合:** 既存の `## 2. 指摘事項と対応内容` テーブルを読み、既存の最大 `#` の
   続き番号で人が伝えた行を **追記** する（既存の AI レビュー結果・対応状況は上書きしない）。
3. **REVIEW_FILE が存在しない場合:** `~/.claude/skills/xddp-common/templates/review-template.md` を用いて
   新規作成し、人が伝えた行を1番から採番する。レビュアーは「人間（CRS View 経由・今日の日付）」とする。
4. 追記・作成が終わったら、人に「`/xddp-revise {CR} req` を実行すれば、追記した指摘が `⬜ 未対応` として
   通常どおり取り込まれます」と案内する（自動実行はしない）。
