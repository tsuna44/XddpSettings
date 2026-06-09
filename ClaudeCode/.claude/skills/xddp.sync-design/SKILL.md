---
description: コードから DSN を再生成してリビジョンとして記録し、AIレビュー→人承認を実施する。「設計を同期して」「DSN を更新して」などで起動する。
argument-hint: "[CR番号] [変更サマリ（省略可）]"
---

You are orchestrating **XDDP sync-design — Code-to-DSN Revision Generation**.

Arguments: $ARGUMENTS = [CR_NUMBER] (optional) [, 変更サマリ（省略可）]

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS
  → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.
Let `CHANGE_SUMMARY` = `REST_ARGS`（空の場合は Step 2 で git diff から自動生成）

(xddp.config.md lookup done in xddp.common; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.
Read `REPOS:` from xddp.config.md → `REPOS_MAP`, `REPOS_KEYS`.

## Step 1: Determine revision numbers

Let `CURRENT_DSN_MAP`  = {}  （repo → 現在の最新 DSN ファイルパス）
Let `NEW_DSN_FILE_MAP` = {}  （repo → 今回生成するリビジョンファイルパス）
Let `NEXT_REV_NUM_MAP` = {}  （repo → 今回の rev 番号）

For each `{repo}` in `REPOS_KEYS`:
  Let `EXISTING_REVS` = glob `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-rev*.md`
    （rev ファイルが存在しない場合は空リスト）
  Let `NEXT_REV_NUM_MAP[{repo}]`  = len(EXISTING_REVS) + 1
  Let `CURRENT_DSN_MAP[{repo}]`   =
    if EXISTING_REVS is not empty: 最大番号の rev ファイル
    else: `{CR_PATH}/05_architecture/{repo}/DSN-{CR}.md`
  Let `NEW_DSN_FILE_MAP[{repo}]`  = `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-rev{NEXT_REV_NUM_MAP[{repo}]}.md`

## Step 2: Collect code context

Run: `git -C {WORKSPACE_ROOT} diff HEAD` → let `GIT_DIFF`
（`git diff HEAD` は HEAD とワーキングツリーの差分を返す。`git add` 済みのステージング変更も未ステージングの変更も両方含む（ステージング済みのみは `git diff --staged HEAD`、未ステージングのみは `git diff`）。
コミット済みの変更を対象にする場合は `git diff {base_ref}..HEAD` 等が必要であり、
その場合は REST_ARGS に変更サマリと共に明示する）

If `GIT_DIFF` is empty:
  Report: "⚠️ git diff HEAD が空です（ワーキングツリー・インデックスに HEAD 比較の差分なし）。"
  Ask human: "続行しますか？コミット済みの変更を対象にする場合は
    `/xddp.sync-design {CR} {変更サマリ}` で変更サマリを指定するか、
    コミット前の状態に戻して再実行してください。"
  If No: Stop.

If `CHANGE_SUMMARY` is empty:
  Let `CHANGE_SUMMARY` = GIT_DIFF の変更ファイル一覧と変更行数の概要を自動生成

Let `CHANGED_FILES_MAP` = {}  （repo → 変更ファイル一覧）
Let `REPO_DIFF_MAP`     = {}  （repo → diff 抽出）
Let `CRS_FILE_MAP`      = {}  （repo → CRS ファイルパス。存在しない場合は空文字）
Let `STEERING_MAP`      = {}  （repo → steering context）

For each `{repo}` in `REPOS_KEYS`:
  Let `CHANGED_FILES_MAP[{repo}]` = GIT_DIFF から `{REPOS_MAP[{repo}]}` 配下の変更ファイル一覧
  Let `REPO_DIFF_MAP[{repo}]`     = GIT_DIFF から `{REPOS_MAP[{repo}]}` 配下の差分のみ抽出
  Let `CRS_PATH` = `{CR_PATH}/03_change-requirements/CRS-{CR}.md`
  Let `CRS_FILE_MAP[{repo}]` = `CRS_PATH` if exists, else ""
  Read Steering Context（xddp.common "## Load Steering Context" with XDDP_DIR, REPO_NAME={repo}）
    → let `STEERING_MAP[{repo}]`

Let `AFFECTED_REPOS` = `{repo for repo in REPOS_KEYS if REPO_DIFF_MAP[{repo}] is not empty}`
If `AFFECTED_REPOS` is empty:
  Report: "⚠️ いずれのリポジトリにも差分が検出されませんでした。処理を終了します。"
  Stop.

## Step 3: Regenerate DSN per repo

For each `{repo}` in `AFFECTED_REPOS`:
  Let `CURRENT_DSN`  = `CURRENT_DSN_MAP[{repo}]`
  If `CURRENT_DSN` does not exist:
    Report error: "DSN-{CR}.md が存在しません（repo: {repo}）。工程05（xddp.05.arch）を先に実施してください。"
    Stop.
  Let `NEW_DSN_FILE` = `NEW_DSN_FILE_MAP[{repo}]`
  Let `NEXT_REV_NUM` = `NEXT_REV_NUM_MAP[{repo}]`

  **Agent tool** `subagent_type=xddp-design-sync-agent`:
  ```
  CR_NUMBER: {CR}
  REPO_NAME: {repo}
  CURRENT_DSN_FILE: {CURRENT_DSN}
  CHANGED_FILES: {CHANGED_FILES_MAP[{repo}]}
  REPO_DIFF: {REPO_DIFF_MAP[{repo}]}
  CRS_FILE: {CRS_FILE_MAP[{repo}]}（空文字の場合は省略）
  OUTPUT_FILE: {NEW_DSN_FILE}
  CHANGE_SUMMARY: {CHANGE_SUMMARY}
  STEERING_CONTEXT: {STEERING_MAP[{repo}]}
  TODAY: {TODAY}
  ```

## Step 4: AI review

For each `{repo}` in `AFFECTED_REPOS`:
  Let `CURRENT_DSN`  = `CURRENT_DSN_MAP[{repo}]`
  Let `NEW_DSN_FILE` = `NEW_DSN_FILE_MAP[{repo}]`
  Let `NEXT_REV_NUM` = `NEXT_REV_NUM_MAP[{repo}]`
  Let `REVIEW_FILE`  = `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-rev{NEXT_REV_NUM}-review.md`

  **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: DSN
  TARGET_FILE: {NEW_DSN_FILE}
  REFERENCE_FILES: [{CURRENT_DSN}]（CRS_FILE_MAP[{repo}] が非空の場合は追加）
  REVIEW_ROUND: 1
  OUTPUT_FILE: {REVIEW_FILE}
  ```

## Step 5: Report and request approval

For each `{repo}` in `AFFECTED_REPOS`:
  Let `NEW_DSN_FILE` = `NEW_DSN_FILE_MAP[{repo}]`
  Let `NEXT_REV_NUM` = `NEXT_REV_NUM_MAP[{repo}]`
  Let `REVIEW_FILE`  = `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-rev{NEXT_REV_NUM}-review.md`
  Show: `{repo}` のレビュー結果サマリー（`{REVIEW_FILE}` から重要度別件数を表示）

承認確認として以下の一覧を表示する:
  | repo | リビジョンファイル | レビュー判定 |
  |------|-----------------|------------|
  （AFFECTED_REPOS ごとに `{repo}` / `NEW_DSN_FILE_MAP[{repo}]` / 🔴件数・🟡件数 を列挙）

Ask: "上記 {len(AFFECTED_REPOS)} リポジトリの DSN リビジョンを承認しますか？"
If approved → proceed to Step 6.
If not approved:
  Report: "修正後に再度 `/xddp.sync-design {CR}` を実行してください。"
  Stop.

## Step 6 (承認後): latest-specs 更新ガイダンス

以下を案内する:

```
✅ 以下の DSN リビジョンが承認されました:
  （AFFECTED_REPOS ごとに NEW_DSN_FILE_MAP[{repo}] を列挙）

latest-specs を最新状態に更新するには、以下を実行してください:
  /xddp.09.specs {CR}

（xddp.09.specs は現状コードと CHD を参照して latest-specs を生成・更新します）

⚠️ 注意: このスキルは DSN のみ更新し、CHD は更新しません。
  DSN と CHD に大きな乖離がある場合、xddp.09.specs が CHD ベースで仕様を生成するため
  最新 DSN と整合しない仕様書が生成されるリスクがあります。
  CHD も更新が必要な場合は先に /xddp.06.design を実行してください。
```

---
> **保守メモ:** このファイルを変更した場合は、`README.md`（スキル一覧テーブル）および
> `CLAUDE.md`（ステップ番号体系テーブル）を合わせて更新すること。
> このスキルに対応する `commands/` ファイルは不要（スキル名が直接スラッシュコマンド名になる）。
