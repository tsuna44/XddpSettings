---
description: XDDP 再修正: 人のレビュー指摘を成果物に反映する。「人のレビュー指摘を反映して」「修正して」などで起動する。
argument-hint: "[CR番号] analysis|req|specout|arch|design|test [repo名] [ID,ID,...]"
---

You are executing **XDDP Revise — Apply Human Review Comments**.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) DOCUMENT_TYPE [REPO_NAME] [IDS]
- CR_NUMBER: optional; auto-detected from XDDP_DIR if omitted
- DOCUMENT_TYPE: `analysis` | `req` | `arch` | `design` | `test` | (file path)
- REPO_NAME: optional; which repo's artifact to revise (for arch/design/test in multi-repo). If omitted and IS_MULTI, ask the user.
- IDS: optional; comma-separated review item numbers to apply (e.g. `1,3`). If omitted, all `⬜ 未対応` items are targeted.

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `DOC_TYPE` = first token of `REST_ARGS`.
Let remaining = tokens after DOC_TYPE.
If remaining is empty: let `IDS` = empty; let `REPO_NAME` = empty.
Else if last token of remaining matches `^[0-9]+(,[0-9]+)*$`:
  let `IDS` = that token (parse as comma-separated int list).
  let `REPO_NAME` = remaining minus IDS token (may be empty if remaining had only one token).
  Note: repo names consisting solely of digits are indistinguishable from IDS by this rule.
        Such names should not be used; if unavoidable, the user must specify REPO_NAME before IDS.
Else: let `IDS` = empty; let `REPO_NAME` = remaining (second token of REST_ARGS).
  Note: strings that do not match `^[0-9]+(,[0-9]+)*$` (e.g., `1,abc,3`) are intentionally treated as
        REPO_NAME, not IDS. Such tokens would cause a file-not-found error in Step 1, alerting the user.
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

## 2. Load review items
Let `REVIEW_FILE` = the review file path resolved from DOC_TYPE (Step 4 のパスマッピングと同一。Step 4 自体は変更なし)。

**Case A — REVIEW_FILE exists:**
Read REVIEW_FILE. Extract rows from `## 2. 指摘事項と対応内容` table where 対応状況 = `⬜ 未対応`.
Let `OPEN_ITEMS` = list of extracted rows (columns: #, 重要度, 場所, 指摘内容).

If IDS is specified: filter OPEN_ITEMS to those whose `#` matches any value in IDS.
  Let `MISSING_IDS` = values in IDS that had no matching row in OPEN_ITEMS.
  If MISSING_IDS is non-empty: warn "指定された ID が見つかりませんでした: {MISSING_IDS}（スキップします）".
  If no items remain after filtering: report "指定された ID に該当する未対応指摘が見つかりませんでした" and stop.
  (Partial match is intentional — found items are applied; missing IDs are skipped with a warning.)

If OPEN_ITEMS is empty: report "未対応の指摘はありません" and stop.

Display OPEN_ITEMS as a table and tell the user:
> 以下の指摘を成果物に反映します。よろしいですか？（修正不要な項目があれば番号で除外を指示してください）

Wait for user confirmation. If the user excludes items, remove them from OPEN_ITEMS.
Excluded items remain `⬜ 未対応` in the review file (対応状況は更新しない)。

**Case B — REVIEW_FILE does not exist:**
Tell the user:
> レビューファイルが見つかりません。修正したい箇所と内容を教えてください。セクション名や行番号（任意）と修正内容をリスト形式で入力してください。

Wait for user input. Treat the user input as OPEN_ITEMS (freeform).

## 3. Apply revisions
Read the target file. Apply each item in OPEN_ITEMS:
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

- If file exists:
  - For Case A (auto-loaded from review file): update `対応状況` column of each applied row from `⬜ 未対応` to `✅ 対応済`, and fill in `対応内容` column with a summary of the change applied.
  - For Case B (freeform input): append human review items and mark ✅ 対応済.
- If not: create using review template with reviewer "人間（今日の日付）".

## 5. Increment version
Add 変更履歴 entry: version +0.1, today, author "人", description of changes.

## 6. Report in Japanese
