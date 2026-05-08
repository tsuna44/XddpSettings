---
description: XDDP AIレビュー単体実行: 人が直接編集した成果物に対してAIレビューを実施する。「AIレビューして」「レビューして」などで起動する。
---

You are executing **XDDP Review — Standalone AI Review**.

**Arguments:** $ARGUMENTS = CR_NUMBER DOCUMENT_TYPE
- CR_NUMBER: e.g. `REQ-2026-001`
- DOCUMENT_TYPE: `analysis` | `req` | `specout` | `arch` | `design` | `test` | (file path)

---

Let `CR` = first token of $ARGUMENTS.

Find `xddp.config.md` by searching upward from cwd: check cwd first, then each parent directory in order. Let `WORKSPACE_ROOT` = the directory where the file is found. If not found at filesystem root, report "xddp.config.md が見つかりません。ワークスペースルートまたはそのサブディレクトリで実行してください。" and stop.
Extract `XDDP_DIR` (default: `xddp` if the key is absent). Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## 1. Resolve document mapping

| DOCUMENT_TYPE | DOCUMENT_TYPE (reviewer) | TARGET_FILE | REFERENCE_FILES | OUTPUT_FILE |
|---|---|---|---|---|
| `analysis` | `ANA` | `{CR_PATH}/02_analysis/ANA-{CR}.md` | `{CR_PATH}/01_requirements/` (all .md) | `{CR_PATH}/02_analysis/review/02_analysis-review.md` |
| `req` | `CRS` | `{CR_PATH}/03_change-requirements/CRS-{CR}.md` | `{CR_PATH}/01_requirements/` (all .md), `{CR_PATH}/02_analysis/ANA-{CR}.md` | `{CR_PATH}/03_change-requirements/review/03_change-requirements-review.md` |
| `specout` | `SPO` | `{CR_PATH}/04_specout/SPO-{CR}.md` | `{CR_PATH}/01_requirements/` (all .md), `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/modules/` (all *-spo.md), `{CR_PATH}/04_specout/cross-module/` (all .md, if exists) | `{CR_PATH}/04_specout/review/04_specout-review.md` |
| `arch` | `DSN` | `{CR_PATH}/05_architecture/DSN-{CR}.md` | `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/SPO-{CR}.md` | `{CR_PATH}/05_architecture/review/05_architecture-review.md` |
| `design` | `CHD` | `{CR_PATH}/06_design/CHD-{CR}.md` | `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/SPO-{CR}.md` | `{CR_PATH}/06_design/review/06_design-review.md` |
| `test` | `TSP` | `{CR_PATH}/09_test-spec/TSP-{CR}.md` | `{CR_PATH}/06_design/CHD-{CR}.md`, `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/SPO-{CR}.md` | `{CR_PATH}/09_test-spec/review/09_test-spec-review.md` |
| other | treat DOCUMENT_TYPE as file path | — | — | `{CR_PATH}/review/manual-review.md` |

If DOCUMENT_TYPE is omitted: ask the user which document to review.

## 2. Verify target file exists

Check that TARGET_FILE exists. If not found, tell the user and stop.

## 3. Run AI review

Use the **Agent tool** with `subagent_type=xddp-reviewer` and pass:
```
DOCUMENT_TYPE: {resolved type}
TARGET_FILE: {resolved target}
REFERENCE_FILES: {resolved references}
REVIEW_ROUND: 1
OUTPUT_FILE: {resolved output}
```

## 4. Report in Japanese

Read OUTPUT_FILE and show the user:
- 総合判定（✅ 合格 / 🔁 要修正）
- 指摘件数（重大 / 軽微 / 提案）
- レビュー結果ファイルのパス

If 🔴 or 🟡 issues exist, suggest:
> 修正後に再度レビューする場合は `/xddp.review {CR} {DOCUMENT_TYPE}` を実行してください。
> 指摘を反映する場合は `/xddp.revise {CR} {DOCUMENT_TYPE}` を使用してください。

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.review.md` の要約も合わせて更新すること。
