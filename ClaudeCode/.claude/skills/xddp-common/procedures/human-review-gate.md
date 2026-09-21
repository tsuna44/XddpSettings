# Human Review Gate

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## Human Review Gate

人レビュー待ちのゲート表示・入力待ち共通制御フロー。各スキルの Human Review Gate ステップから
apply して使用する。「レビュー完了」入力後の最終AIレビューパスは対象ファイル構成が工程ごとに異なるため
本プロシージャの範囲外とし、呼び出し元スキルが `CHANGED` を見て個別に実施する。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `STEP_NUM`: progress.md 上の対象ステップ番号
- `STEP_LABEL`: progress.md の詳細ステップ・`xddp-status` 表示に使う呼び出し元固有のステップ識別子
  （例: `Step A3`、`Step B2`。呼び出し元のステップ見出し名と一致させる）
- `ARTIFACTS_TEXT`: 成果物一覧（Markdown 箇条書き。**呼び出し元が `{for each...}`/`{if...}` を展開済みの
  最終テキストとして渡す**。単一ファイル／リポジトリ別＋cross 等、工程ごとに構造が異なるため、組み立て自体は
  呼び出し元の責務とする。本プロシージャは `AFFECTED_REPOS`・`HAS_CROSS` 等の呼び出し元ローカル変数を
  認識しないため、未展開のテンプレート構文を渡してはならない）
- `REVISE_COMMAND`（任意）: AI修正コマンドの案内文字列（例: `` `/xddp-revise {CR} analysis` ``）。
  省略時は「AIに修正を依頼する場合」の行を出力しない
- `INTRO_NOTE`（任意）: 標準の案内文の直後、`ARTIFACTS_TEXT` の前に挿入する追加テキスト
  （例: 05.arch の SP-ID 照合警告。`ARTIFACTS_TEXT` と同様に展開済みの最終テキストとして渡す）
- `OPTION_NOTE`（任意）: 修正方法ブロックの後、締めの入力案内の前に挿入する追加テキスト
  （例: 05.arch の `--detail` オプション案内）

**Output:** `CHANGED`（true/false。ユーザーがファイルを直接編集または `/xddp-revise` を実行したかどうか）

**Process:**
1. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
   CR_PATH: {CR_PATH}, STEP_NUM: {STEP_NUM}, STATE: 👀 レビュー待ち,
   DETAIL_STEP: `{STEP_LABEL}: 人レビュー待ち`
1.5. レビューブリーフを生成する（案内表示より前に実行すること）:
   Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_review_brief.py generate --root {CR_PATH} --step {STEP_NUM} --baseline {CR_PATH}/.phase-baseline-{STEP_NUM}.json --out {CR_PATH}/.review-brief.md`
   → stdout の JSON を `BRIEF_SUMMARY`（`top`/`counts`/`brief_path`/`est_total_min`）として取得する。
   If the script is not found: tell the user to run `setup.sh` and continue without a brief（ゲートは止めない）。
   If it errors: display stderr and continue without a brief.
2. Tell the user。以下のテキストを組み立て、**展開後の全行**（`ARTIFACTS_TEXT`・`INTRO_NOTE`・`OPTION_NOTE`
   が複数行の場合はその内部の各行も含む）の先頭に `>` を付与して出力する（変更前の6スキルすべてが
   blockquote 形式で出力していたため、表示形式を維持する）:
   ```
   ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
   {INTRO_NOTE が指定されている場合は挿入}
   {ARTIFACTS_TEXT}
   {BRIEF_SUMMARY が取得できている場合のみ挿入}
   📋 レビューブリーフを生成しました: {BRIEF_SUMMARY.brief_path}
   ⚠️ 重点確認箇所トップN:
   {BRIEF_SUMMARY.top の各件について} - {file}: {marker_type}（{location}）
   推奨レビュー時間の目安: 約 {BRIEF_SUMMARY.est_total_min} 分

   **修正方法：**
   - 直接ファイルを編集する
   {REVISE_COMMAND が指定されている場合}- AIに修正を依頼する場合: {REVISE_COMMAND}
   {OPTION_NOTE が指定されている場合は挿入}

   レビューと修正が完了したら「**レビュー完了**」と入力してください。
   変更がなければそのまま「**レビュー完了**」と入力してください。
   ```
2.5. CR フォルダ全体のスナップショットを取得する（ユーザーの確認待ちに入る前に実行すること）:
   Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_gate_snapshot.py snapshot --root {CR_PATH} --out {CR_PATH}/.gate-snapshot.json`
   If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
   （手順1.5で生成済みの `.review-brief.md` はこの時点で既に確定しており、このスナップショットの
   ベースラインに含まれる。`.phase-baseline-*.json` と併せて誤 `CHANGED` の原因にはならない。）
3. Wait for the user to confirm.
4. `CHANGED` の判定: Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_gate_snapshot.py diff --snapshot {CR_PATH}/.gate-snapshot.json`
   出力 JSON の `changed`（true/false）を `CHANGED` として採用する（`changed_files` は必要に応じて参考情報として利用する）。
   ユーザーの発言が具体的な修正内容に言及しているのに `changed=false` の場合のみ
   （CR フォルダ外のファイル編集の検出漏れ対策）、「ファイルを変更しましたか？」と確認してから判定を上書きする。
5. Return `CHANGED`.

**理由（設計判断の記録）:**
`DETAIL_STEP` を `STEP_LABEL` 経由の動的組み立てにしたのは、`xddp-status/SKILL.md` の表示例
「`| 5 | 実装方式検討 | 👀 レビュー待ち | Step B2: 人レビュー待ち | ... |`」が、工程ごとに異なる
ステップ識別子（`Step A3`／`Step B2` 等）を前提とした既存の公開済み挙動であるため。
`ARTIFACTS_TEXT`/`INTRO_NOTE` を「呼び出し元が展開済みの最終テキストを渡す」契約にしたのは、既存の
`apply` 呼び出し規約（呼び出し元が条件分岐・存在判定を済ませた確定値を渡す運用）からの逸脱を
避けるためである（詳細は上記 Input 節の該当項目を参照）。
