---
description: XDDP AIレビュー単体実行: 人が直接編集した成果物に対してAIレビューを実施する。「AIレビューして」「レビューして」などで起動する。
---

You are executing **XDDP Review — Standalone AI Review**.

> This review is the checkpoint before an artifact advances. Honest, thorough critique here prevents failures in every downstream step. Do not let familiarity or politeness dilute the quality of this review.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) DOCUMENT_TYPE
- CR_NUMBER: e.g. `CR-2026-001` (optional; auto-detected from XDDP_DIR if omitted)
- DOCUMENT_TYPE: `analysis` | `req` | `specout` | `arch` | `design` | `test` | (file path)

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `DOCUMENT_TYPE` = first token of `REST_ARGS`.

(xddp.config.md lookup done in xddp.common.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## 1. Resolve document mapping

| DOCUMENT_TYPE | DOCUMENT_TYPE (reviewer) | TARGET_FILE | REFERENCE_FILES | OUTPUT_FILE |
|---|---|---|---|---|
| `analysis` | `ANA` | `{CR_PATH}/02_analysis/ANA-{CR}.md` | `{CR_PATH}/01_requirements/` (all .md) | `{CR_PATH}/02_analysis/review/02_analysis-review.md` |
| `req` | `CRS` | `{CR_PATH}/03_change-requirements/CRS-{CR}.md` | `{CR_PATH}/01_requirements/` (all .md), `{CR_PATH}/02_analysis/ANA-{CR}.md` | `{CR_PATH}/03_change-requirements/review/03_change-requirements-review.md` |
| `specout` | `SPO` | `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` (ask user for `{repo}` if not specified; for single-repo use the only REPOS: entry) | `{CR_PATH}/01_requirements/` (all .md), `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/{repo}/modules/` (all *-spo.md), `{CR_PATH}/04_specout/cross/` (all .md, if exists) | `{CR_PATH}/04_specout/{repo}/review/04_specout-review.md` |
| `arch` | `DSN` | `{CR_PATH}/05_architecture/{repo}/DSN-{CR}.md` (ask user for `{repo}` if not specified) | `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` | `{CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md` |
| `design` | `CHD` | `{CR_PATH}/06_design/{repo}/CHD-{CR}.md` (ask user for `{repo}` if not specified) | `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` | `{CR_PATH}/06_design/{repo}/review/06_design-review.md` |
| `test` | `TSP` | `{CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md` (ask user for `{repo}` if not specified) | `{CR_PATH}/06_design/{repo}/CHD-{CR}.md`, `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` | `{CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md` |
| other | treat DOCUMENT_TYPE as file path | — | — | `{CR_PATH}/review/manual-review.md` |

If DOCUMENT_TYPE is omitted: ask the user which document to review.

## 2. Verify target file exists

Check that TARGET_FILE exists. If not found, tell the user and stop.

## 2.5. Ensure output directory exists

Run `mkdir -p {parent directory of OUTPUT_FILE}` using Bash to create the review output directory if it does not exist.

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
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.review.md`.
