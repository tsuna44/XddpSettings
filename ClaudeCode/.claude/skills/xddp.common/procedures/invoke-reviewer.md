# Invoke Reviewer

> xddp.common の共通プロシージャ。呼び出し元スキルから apply される。

## Invoke Reviewer

`artifact_lint.py`（決定的な機械検査）を実行してから `subagent_type=xddp-reviewer` を呼び出す
共通フロー。`subagent_type=xddp-reviewer` を直接呼ぶ全箇所はこの手続きを apply すること
（Mermaid構文・フロントマター必須キーの機械検査を一本化し、レビュアーは意味整合に集中できるようにする）。

**Input:**
- `DOCUMENT_TYPE`, `REFERENCE_FILES`, `REVIEW_ROUND`, `OUTPUT_FILE`
- `TARGET_FILE`（`TARGET_FILES` が指定される場合は省略される）
- `TARGET_FILES`（任意。`TARGET_FILE` とは相互排他。SPEC バッチレビュー専用 — xddp.11.specs 対応）
- `NEXT_DOCUMENT_TYPE`（任意）
- `EXTRA_REVIEWER_PARAMS`（任意, key-value 形式, default: 空）: `xddp-reviewer` への Agent tool 呼び出しに
  追加でそのまま渡すパラメータ（例: TSP レビュー時の `MIN_COVERAGE`）。既存の「## Review Loop」
  「## Final Review Pass」が持つ同名 Input と同一契約。呼び出し元が指定しない場合は何も追加しない
- `PROGRESS_CR_PATH`（任意）: metrics.jsonl の出力先 CR フォルダパス
- `PROGRESS_STEP_NUM`（任意）: 記録するステップ番号
- `METRICS_TARGET`（任意）: `record --target` にそのまま渡す識別子文字列

**Process:**
1. Run via Bash:
   ```
   PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/artifact_lint.py \
     （TARGET_FILES が指定されている場合）--files {TARGET_FILES をカンマ区切りで展開} \
     （TARGET_FILE が指定されている場合）--file {TARGET_FILE} \
     --doc-type {DOCUMENT_TYPE}
   ```
   → 結果 JSON を `LINT_RESULTS` とする。スクリプトが見つからない場合は setup.sh 実行を案内して停止する。
   スクリプトが見つかったが実行時エラーとなった場合（不正なパス・想定外のファイル内容での例外等）は
   stderr を表示して停止する。
2. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: {DOCUMENT_TYPE}
   （TARGET_FILES が指定されている場合）TARGET_FILES: {TARGET_FILES}
   （TARGET_FILE が指定されている場合）TARGET_FILE: {TARGET_FILE}
   REFERENCE_FILES: {REFERENCE_FILES}
   REVIEW_ROUND: {REVIEW_ROUND}
   OUTPUT_FILE: {OUTPUT_FILE}
   LINT_RESULTS: {LINT_RESULTS}
   （NEXT_DOCUMENT_TYPE が指定されている場合のみ追加）NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE}
   （EXTRA_REVIEWER_PARAMS が指定されている場合のみ追加）{EXTRA_REVIEWER_PARAMS を展開}
   ```
3. `PROGRESS_CR_PATH` と `PROGRESS_STEP_NUM` が両方指定されている場合、`REFERENCE_FILES` の各エントリを
   **プロース記法（先頭の条件句・末尾の説明文）を含む生の文字列のまま** 1つずつ
   `--reference-file {エントリ}` として列挙し（`,` 区切りの単一引数にはしない。説明文自体にカンマを
   含むエントリがあるため。条件句・説明文の除去はスクリプト側の正規化——先頭・末尾／全角・半角の
   両括弧を除去——が担う）、Bash で以下をベストエフォートで実行する（失敗してもレビュー結果には
   影響させない。計測は工程本体を止めない設計＝`## Snapshot Phase Baseline` と同じ方針）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_metrics.py record --cr-path {PROGRESS_CR_PATH} --step {PROGRESS_STEP_NUM} --event reviewer_call --document-type {DOCUMENT_TYPE} --reference-file '{エントリ1}' --reference-file '{エントリ2}' ... [--target '{METRICS_TARGET}']`
   （`--reference-file` は `argparse` の `action="append"` で複数回指定を受け付ける。既存の
   `artifact_lint.py --files` のカンマ区切りパターンは踏襲しない）
   **シェル引用の注意:** 各エントリは**単一引用符**で囲むこと。REFERENCE_FILES のエントリには
   半角二重引用符やバッククォートが実在し、二重引用符で囲むとこれらがシェルに解釈されて `record`
   呼び出し全体が失敗する。本フックはベストエフォート実行のため、失敗しても**無音で計測だけが
   欠落する**（レビュー品質には影響しないが計測目的を損なう）。エントリ自体が単一引用符を含む場合は
   該当エントリを計測対象から外してよい
