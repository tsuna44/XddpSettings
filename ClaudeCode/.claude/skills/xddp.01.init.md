---
description: XDDP フェーズ0: CRワークスペースを初期化する。CR番号と要求書ファイルを引数に取り、成果物フォルダ・progress.mdを生成する。「ワークスペースを初期化して」「CRを開始して」などで起動する。
---

You are executing **XDDP Step 01 — Initialize CR Workspace**.

**Arguments:** $ARGUMENTS
- 1st token: CR number (e.g. `REQ-2026-001`)
- 2nd token (optional): path to the requirements `.md` file

---

Parse $ARGUMENTS. Let `CR` = first token, `REQ_FILE` = second token.

### 0.5. Resolve XDDP_DIR

Check if `xddp.config.md` exists in the current working directory.
- If exists, read it and extract `XDDP_DIR` (default: `xddp` if the key is absent).
- If not exists (first run), use `XDDP_DIR = xddp`.

Resolve paths relative to the directory containing `xddp.config.md` (= workspace root).
Let `XDDP_ABS` = resolved absolute path of `{cwd}/{XDDP_DIR}`.
Let `CR_PATH`  = `{XDDP_ABS}/{CR}`.

### 1. Locate requirements file
- If `REQ_FILE` given → use it.
- Otherwise search current directory for `REQ-{CR}.md` or `REQ-{CR}*.md`.
- If not found → tell the user and stop.

### 2. Create folder structure
Create directories (use `mkdir -p` via Bash):
```
{CR_PATH}/01_requirements/
{CR_PATH}/02_analysis/
{CR_PATH}/03_change-requirements/
{CR_PATH}/04_specout/
{CR_PATH}/05_architecture/
{CR_PATH}/06_design/
{CR_PATH}/07_coding/
{CR_PATH}/08_code-review/
{CR_PATH}/09_test-spec/
{CR_PATH}/10_test-results/
{CR_PATH}/review/
```

### 3. Copy requirements file
Copy the requirements file into `{CR_PATH}/01_requirements/REQ-{CR}.md`.
If the source filename is already `REQ-{CR}.md`, copy as-is. Otherwise rename on copy (do not keep the original filename).

### 3.5. Create latest-specs/ (if not exists)
Check if `{XDDP_DIR}/latest-specs/` exists in the current working directory.
If not found, create it and place a `{XDDP_DIR}/latest-specs/README.md` with the following content:
```
# 最新仕様書

このディレクトリには `/xddp.09.specs` で生成された最新仕様書を格納します。
リポジトリ別サブディレクトリ（例: repo-a/、repo-b/）に分けて格納します。
クロスリポジトリのインタフェース仕様は cross/interfaces/ に格納します。
初回の `xddp.04.specout` 実行時は空でも問題ありません。
```

### 4. Create xddp.config.md (if not exists)
Check if `xddp.config.md` exists in the current working directory.
If not found, copy `~/.claude/templates/xddp.config.md` to `./xddp.config.md`.
If already exists, leave it untouched.

### 4.5. Create DOCS_DIR structure (if not exists)

1. Read `DOCS_DIR` from `xddp.config.md` (just created/confirmed in Step 4).
   Default: `baseline_docs` if the key is absent.
   Let `DOCS` = resolved absolute path of `{cwd}/{DOCS_DIR}`.
2. Read `REPOS:` mapping from `xddp.config.md`. Let `REPOS_KEYS` = list of all repository names.
   If `REPOS:` is absent or empty, show: "xddp.config.md の REPOS: を設定してから再実行してください。"
   and skip Step 4.5 (skip DOCS_DIR init and continue).
3. If `{DOCS}` does not exist → create the following:
   - `{DOCS}/AI_INDEX.md` (initial content: see below)
   - `{DOCS}/project-steering.md` (empty — will be populated by xddp.01.init Step 4.6)
   - For each `{repo}` in `REPOS_KEYS`:
     - `{DOCS}/{repo}/specs/README.md` (initial content: see below)
     - `{DOCS}/{repo}/knowledge/lessons-learned.md` (empty table)
     - `{DOCS}/{repo}/design/README.md` (initial content: see below)
     - `{DOCS}/{repo}/test/README.md` (initial content: see below)
4. If `{DOCS}` exists → for each `{repo}` in `REPOS_KEYS`:
   - If `{DOCS}/{repo}/` does not exist → create only:
     - `{DOCS}/{repo}/specs/README.md`
     - `{DOCS}/{repo}/knowledge/lessons-learned.md`
     - `{DOCS}/{repo}/design/README.md`
     - `{DOCS}/{repo}/test/README.md`
5. If `{DOCS}` and all per-repo dirs exist → skip.

**Initial file contents:**

`{DOCS}/AI_INDEX.md`:
````markdown
# AI向けナビゲーションインデックス
> 新規開発開始時に clone してこのファイルを AI に注入してください。

## リポジトリ別仕様書
| リポジトリ | 承認済み仕様書 | 知見 |
|---|---|---|
| （xddp.close 実行後に自動追記） | — | — |

## リポジトリ別設計書・テスト仕様書
| リポジトリ | 設計書（DSN・CHD） | テスト仕様（TSP） |
|---|---|---|
| （xddp.close 実行後に自動追記） | — | — |

## 共通知識
| ドキュメント | 説明 |
|---|---|
| [project-steering.md](project-steering.md) | プロジェクト共通規約（最終更新CR: —） |
````

`{DOCS}/{repo}/specs/README.md` (substitute actual {repo} name):
````markdown
# 承認済み仕様書: {repo}
xddp.close で latest-specs/{repo}/ から昇格した承認済みの最新仕様書を格納します。
````

`{DOCS}/{repo}/design/README.md`:
````markdown
# 設計書アーカイブ: {repo}
xddp.close で各 CR の DSN・CHD を格納します。ファイル命名規則: DSN-{CR}.md / CHD-{CR}.md
````

`{DOCS}/{repo}/test/README.md`:
````markdown
# テスト仕様書アーカイブ: {repo}
xddp.close で各 CR の TSP を格納します。ファイル命名規則: TSP-{CR}.md
````

`{DOCS}/{repo}/knowledge/lessons-learned.md` (per-repository):
````markdown
# 知見ログ: {repo}
> xddp.close が CR クローズ時に自動追記します。

## エントリ一覧
| ID | タイトル | タグ | CR | 日付 |
|---|---|---|---|---|
| （xddp.close 実行後に追記） | — | — | — | — |
````

### 4.6. Initialize project-steering files (knowledge hub priority)

Read `REPOS:` (already read in 4.5). Let `REPOS_KEYS` = list of all repository names.
Let `DOCS` = resolved absolute path of `{cwd}/{DOCS_DIR}` (already resolved in 4.5).

**【共通 project-steering.md の初期化】**
- If `{XDDP_DIR}/project-steering.md` does not exist:
  - If `{DOCS}/project-steering.md` exists → copy it (inherit knowledge from previous CRs).
  - Otherwise → copy `~/.claude/templates/project-steering-template.md`; replace `YYYY-MM-DD` with today, `CR番号` with `{CR}`.
- If already exists → leave untouched.

**【リポジトリ別 project-steering の初期化（REPOS: の各 {repo} について）】**
- For each `{repo}` in `REPOS_KEYS`:
  - If `{XDDP_DIR}/project-steering-{repo}.md` does not exist:
    - If `{DOCS}/{repo}/project-steering.md` exists → copy it.
    - Otherwise → copy `~/.claude/templates/project-steering-repo-template.md`; replace `{REPO_NAME}` with `{repo}`, `YYYY-MM-DD` with today, `{CR}` with `{CR}`.
  - If already exists → leave untouched.

**【cross/ project-steering の初期化（REPOS: に複数エントリがある場合のみ）】**
- If `len(REPOS_KEYS) >= 2`:
  - If `{XDDP_DIR}/project-steering-cross.md` does not exist:
    - If `{DOCS}/cross/project-steering.md` exists → copy it.
    - Otherwise → copy `~/.claude/templates/project-steering-cross-template.md`; replace `YYYY-MM-DD` with today, `{CR}` with `{CR}`.
  - If already exists → leave untouched.

### 5. Create progress.md
Read `~/.claude/templates/00_progress-management-template.md`, then create `{CR_PATH}/progress.md`:
- Replace all `{CR番号}` with `{CR}`.
- Set today's date as 開始日 and 最終更新.
- Step 1 (要求書作成) → ✅ 完了, today.
- All other steps → ⬜ 未着手.
- 次に実行すべきコマンド → `/xddp.02.analysis {CR}`

### 6. Report in Japanese
Tell the user what was created and show the next command to run.
If `xddp.config.md` was newly created, mention:
- Edit `REPOS:` to list all target repositories (1 entry = single-repo, multiple entries = multi-repo).
- `REPOS:` keys must be the actual repository folder names, not abbreviations (e.g., `api:` → NG, `tasksaas-api:` → OK).
- `cross` is reserved and cannot be used as a repository name.
If project-steering files were newly created, mention:
- `{XDDP_DIR}/project-steering.md` — fill with project-wide naming conventions and ADRs.
- `{XDDP_DIR}/project-steering-{repo}.md` — fill with per-repo coding conventions (run `/xddp.fill-steering {repo}` to auto-draft).
- `{XDDP_DIR}/project-steering-cross.md` (if created) — fill with cross-repo interface conventions (run `/xddp.fill-steering cross`).
If `{XDDP_DIR}/latest-specs/` was newly created, mention that it will be populated by `/xddp.09.specs` in per-repo subdirectories.

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.01.init.md`.
