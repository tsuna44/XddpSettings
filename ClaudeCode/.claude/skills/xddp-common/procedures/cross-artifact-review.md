# Cross Artifact Review

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## Cross Artifact Review

cross/ 配下の成果物（SPO/DSN/CHD の cross バージョン）に対する AI レビュー→インライン修正共通フロー。
`HAS_CROSS` が true の場合のみ、各スキルの Step A2-cross / Step B-cross から apply して使用する。
cross/ 成果物にはインタフェース仕様等に特化した性質上、専用の fixer agent が存在しないため、
指摘があれば呼び出し元スキルが直接 `TARGET_FILE` を編集する。

**Input:**
- `CR_PATH`: CRフォルダのパス
- `STEP_NUM`: progress.md 上の対象ステップ番号（例: `4a`, `5`, `6a`）
- `STEP_LABEL`: progress.md の詳細ステップに使う呼び出し元固有のステップ識別子（例: `Step A2-cross`, `Step B-cross`）
- `DOCUMENT_TYPE`: レビュアーに渡す文書種別（SPO / DSN / CHD）
- `NEXT_DOCUMENT_TYPE`: 次工程の文書種別（DSN / CHD / TSP）
- `TARGET_FILE`: cross 成果物のパス
- `REFERENCE_FILES`: レビュー時に参照するファイル一覧
- `OUTPUT_FILE`: レビュー結果の出力先パス
- `DOC_DESCRIPTION`: 末尾注記に挿入する、この cross 成果物の性質を表す一文（例:
  `インタフェース仕様に特化した成果物`／`インタフェース仕様・実装依存順序に特化した成果物`／
  `インタフェース変更のサマリに特化した成果物`）
- `EXTRA_REVIEWER_PARAMS`（任意, key-value 形式, default: 空）: `xddp-reviewer` への Agent tool 呼び出し
  （Process 手順2）に追加でそのまま渡すパラメータ。`## Review Loop`・`## Invoke Reviewer` と同一契約
  （例: cross SPO/CHD/TSP レビュー時の `QUICK_PROFILE`）。呼び出し元が指定しない場合は Process 手順2の
  呼び出しに何も追加しない（既存の呼び出しと完全に同一）。

**Process:**
1. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
   CR_PATH: {CR_PATH}, STEP_NUM: {STEP_NUM}, STATE: 🔄 進行中,
   DETAIL_STEP: `{STEP_LABEL}: cross {DOCUMENT_TYPE}レビュー中`
2. Read `~/.claude/skills/xddp-common/procedures/invoke-reviewer.md`, apply "## Invoke Reviewer" with:
   DOCUMENT_TYPE: {DOCUMENT_TYPE}, NEXT_DOCUMENT_TYPE: {NEXT_DOCUMENT_TYPE}, TARGET_FILE: {TARGET_FILE},
   REFERENCE_FILES: {REFERENCE_FILES}, REVIEW_ROUND: 1, OUTPUT_FILE: {OUTPUT_FILE},
   （EXTRA_REVIEWER_PARAMS が指定されている場合のみ）EXTRA_REVIEWER_PARAMS: {EXTRA_REVIEWER_PARAMS}
3. Read `{OUTPUT_FILE}`. If 🔴/🟡 issues found: directly edit `{TARGET_FILE}` to fix the issues
   （cross/ {DOCUMENT_TYPE} has no dedicated fixer agent — fix inline）. Output updated review summary.
4. After fixing, re-read `{OUTPUT_FILE}` and count remaining 🔴 rows.
   If 🔴 items remain: warn the human:
   > ⚠️ cross/ {DOCUMENT_TYPE} レビューで 🔴 指摘 {N} 件が残存しています。手動確認してください: `{OUTPUT_FILE}`
5. 注: cross/ {DOCUMENT_TYPE} は{DOC_DESCRIPTION}でサイズが小さく、1パスで修正が収束しやすい。
   per-repo の max_rounds ループは省略する（設計上の意図的省略）。
