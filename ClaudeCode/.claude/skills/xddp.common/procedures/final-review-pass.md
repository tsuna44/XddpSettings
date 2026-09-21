# Final Review Pass

> xddp.common の共通プロシージャ。呼び出し元スキルから apply される。

## Final Review Pass

Human Review Gate 通過後、`CHANGED = true` の場合に実施する最終 AI レビュー1回分の共通フロー。
各スキルの Step B2（または Step A3）直後の `If CHANGED:` 分岐から apply して使用する。
Fixer は呼ばない（レビューのみ。指摘が残る場合は人に判断を委ねる）。

**Input:**
- `DOCUMENT_TYPE`: レビュアーに渡す文書種別
- `NEXT_DOCUMENT_TYPE`（任意）: 次工程の文書種別
- `TARGET_FILE`: レビュー対象ファイルのパス
- `REFERENCE_FILES`: レビュー時に参照するファイル一覧
- `REVIEW_ROUND`: レビューラウンド番号（`last_round + 1` を呼び出し元が算出して渡す）
- `OUTPUT_FILE`: レビュー結果の出力先パス
- `EXTRA_REVIEWER_PARAMS`（任意, key-value 形式, default: 空）: `xddp-reviewer` への Agent tool 呼び出し
  （Process 手順1）に追加でそのまま渡すパラメータ。`DOCUMENT_TYPE` 固有の
  判定基準値を `xddp-reviewer` に伝える汎用の受け渡し口（例: `TSP` レビュー時の `MIN_COVERAGE`）。
  呼び出し元が指定しない場合は Process 手順1の呼び出しに何も追加しない（既存の呼び出しと完全に同一）。

**Process:**
1. Read `~/.claude/skills/xddp.common/procedures/invoke-reviewer.md`, apply "## Invoke Reviewer" with:
   DOCUMENT_TYPE: {DOCUMENT_TYPE}, TARGET_FILE: {TARGET_FILE}, REFERENCE_FILES: {REFERENCE_FILES},
   REVIEW_ROUND: {REVIEW_ROUND}, OUTPUT_FILE: {OUTPUT_FILE},
   （NEXT_DOCUMENT_TYPE が指定されている場合のみ）NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE},
   （EXTRA_REVIEWER_PARAMS が指定されている場合のみ）EXTRA_REVIEWER_PARAMS: {EXTRA_REVIEWER_PARAMS}
2. Read `{OUTPUT_FILE}`. If 🔴 issues remain: inform the user and ask whether to fix again or proceed.
