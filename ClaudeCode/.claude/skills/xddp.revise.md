---
description: XDDP 再修正: 人のレビュー指摘を成果物に反映する。「人のレビュー指摘を反映して」「修正して」などで起動する。
---

You are executing **XDDP Revise — Apply Human Review Comments**.

**Arguments:** $ARGUMENTS = CR_NUMBER DOCUMENT_TYPE
- DOCUMENT_TYPE: `analysis` | `req` | `arch` | `design` | `test` | (file path)

---

Let `CR` = first token. Let `DOC_TYPE` = second token.

Find `xddp.config.md` by searching upward from cwd: check cwd first, then each parent directory in order. Let `WORKSPACE_ROOT` = the directory where the file is found. If not found at filesystem root, report "xddp.config.md が見つかりません。ワークスペースルートまたはそのサブディレクトリで実行してください。" and stop.
Extract `XDDP_DIR` (default: `xddp` if the key is absent). Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## 1. Resolve target file
| DOC_TYPE | File |
|----------|------|
| `analysis` | `{CR_PATH}/02_analysis/ANA-{CR}.md` |
| `req` | `{CR_PATH}/03_change-requirements/CRS-{CR}.md` |
| `specout` | `{CR_PATH}/04_specout/SPO-{CR}.md` |
| `arch` | `{CR_PATH}/05_architecture/DSN-{CR}.md` |
| `design` | `{CR_PATH}/06_design/CHD-{CR}.md` |
| `test` | `{CR_PATH}/09_test-spec/TSP-{CR}.md` |
| other | treat as file path |

If DOC_TYPE omitted: ask the user which document to revise.

## 2. Request review comments
Tell the user:
> 修正したい箇所と内容を教えてください。セクション名や行番号（任意）と修正内容をリスト形式で入力してください。

Wait for user input.

## 3. Apply revisions
Read the target file. Apply each item the user specified:
- Minimal, targeted edits only — do not rewrite unaffected sections.
- Maintain document structure, numbering, and TM consistency.

## 3.5. Ensure output directory exists

Run `mkdir -p {parent directory of review file}` using Bash to create the review output directory if it does not exist.

## 4. Record in review file
Update the corresponding review file for the document type:

| DOC_TYPE | Review File |
|---|---|
| `analysis` | `{CR_PATH}/02_analysis/review/02_analysis-review.md` |
| `req` | `{CR_PATH}/03_change-requirements/review/03_change-requirements-review.md` |
| `specout` | `{CR_PATH}/04_specout/review/04_specout-review.md` |
| `arch` | `{CR_PATH}/05_architecture/review/05_architecture-review.md` |
| `design` | `{CR_PATH}/06_design/review/06_design-review.md` |
| `test` | `{CR_PATH}/09_test-spec/review/09_test-spec-review.md` |
| other | `{CR_PATH}/review/manual-review.md` |

- If file exists: append human review items and mark ✅ 対応済.
- If not: create using review template with reviewer "人間（今日の日付）".

## 5. Increment version
Add 変更履歴 entry: version +0.1, today, author "人", description of changes.

## 6. Report in Japanese
