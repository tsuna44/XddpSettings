---
description: XDDP フェーズ0: CRワークスペースを初期化する。CR番号と要求書ファイルを引数に取り、成果物フォルダ・progress.mdを生成する。「ワークスペースを初期化して」「CRを開始して」などで起動する。
---

You are executing **XDDP Step 01 — Initialize CR Workspace**.

**Arguments:** $ARGUMENTS
- 1st token: CR number (e.g. `REQ-2026-001`)
- 2nd token (optional): path to the requirements `.md` file

---

Parse $ARGUMENTS. Let `CR` = first token, `REQ_FILE` = second token.

### 1. Locate requirements file
- If `REQ_FILE` given → use it.
- Otherwise search current directory for `REQ-{CR}.md` or `REQ-{CR}*.md`.
- If not found → tell the user and stop.

### 2. Create folder structure
Create directories (use `mkdir -p` via Bash):
```
{CR}/01_requirements/
{CR}/02_analysis/
{CR}/03_change-requirements/
{CR}/04_specout/
{CR}/05_architecture/
{CR}/06_design/
{CR}/07_coding/
{CR}/08_code-review/
{CR}/09_test-spec/
{CR}/10_test-results/
{CR}/review/
```

### 3. Copy requirements file
Copy the requirements file into `{CR}/01_requirements/REQ-{CR}.md`.
If the source filename is already `REQ-{CR}.md`, copy as-is. Otherwise rename on copy (do not keep the original filename).

### 4. Create xddp.config.md (if not exists)
Check if `xddp.config.md` exists in the current working directory.
If not found, copy `~/.claude/templates/xddp.config.md` to `./xddp.config.md`.
If already exists, leave it untouched.

### 5. Create progress.md
Read `~/.claude/templates/00_progress-management-template.md`, then create `{CR}/progress.md`:
- Replace all `{CR番号}` with `{CR}`.
- Set today's date as 開始日 and 最終更新.
- Step 1 (要求書作成) → ✅ 完了, today.
- All other steps → ⬜ 未着手.
- 次に実行すべきコマンド → `/xddp.02.analysis {CR}`

### 6. Report in Japanese
Tell the user what was created and show the next command to run.
If `xddp.config.md` was newly created, mention that it can be edited to adjust specout granularity, test framework, and test case granularity.

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.01.init.md` の要約も合わせて更新すること。
