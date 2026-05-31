---
description: XDDP 再修正: 人のレビュー指摘を成果物に反映する。「人のレビュー指摘を反映して」「修正して」などで起動する。
argument-hint: "[CR番号] analysis|req|specout|arch|design|test [repo名]"
---

You are executing **XDDP Revise — Apply Human Review Comments**.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) DOCUMENT_TYPE [REPO_NAME]
- CR_NUMBER: optional; auto-detected from XDDP_DIR if omitted
- DOCUMENT_TYPE: `analysis` | `req` | `arch` | `design` | `test` | (file path)
- REPO_NAME: optional; which repo's artifact to revise (for arch/design/test in multi-repo). If omitted and IS_MULTI, ask the user.

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `DOC_TYPE` = first token of `REST_ARGS`.
Let `REPO_NAME` = second token of `REST_ARGS` (remaining after DOC_TYPE is consumed).
Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).
If IS_MULTI and arch/design/test/specout is selected and REPO_NAME is empty: ask the user which repo.
If NOT IS_MULTI and arch/design/test/specout is selected and REPO_NAME is empty:
  If REPOS_KEYS is empty: error "REPOS: が xddp.config.md に設定されていません"; stop.
  set REPO_NAME = REPOS_KEYS[0].

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## 1. Resolve target file
| DOC_TYPE | File |
|----------|------|
| `analysis` | `{CR_PATH}/02_analysis/ANA-{CR}.md` |
| `req` | `{CR_PATH}/03_change-requirements/CRS-{CR}.md` |
| `specout` | `{CR_PATH}/04_specout/{REPO_NAME}/SPO-{CR}.md`（REPO_NAME 未指定かつ IS_MULTI: ユーザーに確認; 単一リポジトリ: REPOS_KEYS[0] を REPO_NAME として使用） |
| `arch` | `{CR_PATH}/05_architecture/{REPO_NAME}/DSN-{CR}.md`（REPO_NAME 未指定かつ IS_MULTI: ユーザーに確認; 単一リポジトリ: REPOS_KEYS[0] を REPO_NAME として使用） |
| `design` | `{CR_PATH}/06_design/{REPO_NAME}/CHD-{CR}.md`（REPO_NAME 未指定かつ IS_MULTI: ユーザーに確認; 単一リポジトリ: REPOS_KEYS[0] を REPO_NAME として使用） |
| `test` | `{CR_PATH}/09_test-spec/{REPO_NAME}/TSP-{CR}.md`（REPO_NAME 未指定かつ IS_MULTI: ユーザーに確認; 単一リポジトリ: REPOS_KEYS[0] を REPO_NAME として使用） |
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
| `specout` | `{CR_PATH}/04_specout/{REPO_NAME}/review/04_specout-review.md`（REPO_NAME は上記と同様に解決） |
| `arch` | `{CR_PATH}/05_architecture/{REPO_NAME}/review/05_architecture-review.md`（REPO_NAME は上記と同様に解決） |
| `design` | `{CR_PATH}/06_design/{REPO_NAME}/review/06_design-review.md`（REPO_NAME は上記と同様に解決） |
| `test` | `{CR_PATH}/09_test-spec/{REPO_NAME}/review/09_test-spec-review.md`（REPO_NAME は上記と同様に解決） |
| other | `{CR_PATH}/review/manual-review.md` |

- If file exists: append human review items and mark ✅ 対応済.
- If not: create using review template with reviewer "人間（今日の日付）".

## 5. Increment version
Add 変更履歴 entry: version +0.1, today, author "人", description of changes.

## 6. Report in Japanese
