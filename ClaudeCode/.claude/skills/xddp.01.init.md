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
2. Read `REPO_NAME` from `xddp.config.md`.
   If absent or empty, show: "xddp.config.md の REPO_NAME を設定してから再実行してください（例: REPO_NAME: repo-A）"
   and skip Step 4.5 (skip DOCS_DIR init and continue).
3. If `{DOCS}` does not exist → create the following files and directories:
   - `{DOCS}/AI_INDEX.md` (initial content: see below)
   - `{DOCS}/shared/glossary.md` (empty)
   - `{DOCS}/shared/lessons-learned.md` (empty table: see below)
   - `{DOCS}/shared/design/notes.md` (empty template)
   - `{DOCS}/shared/design/patterns.md` (empty template)
   - `{DOCS}/shared/test/patterns.md` (empty template)
   - `{DOCS}/shared/test/anti-patterns.md` (empty template)
   - `{DOCS}/shared/inter-repo/repo-map.md` (empty template)
   - `{DOCS}/shared/inter-repo/dependency-graph.md` (empty template)
   - `{DOCS}/shared/inter-repo/design/sequence/` (empty folder)
   - `{DOCS}/shared/inter-repo/design/dfd/` (empty folder)
   - `{DOCS}/shared/inter-repo/design/architecture/` (empty folder)
   - `{DOCS}/shared/inter-repo/design/interface/` (empty folder)
   - `{DOCS}/{REPO_NAME}/specs/README.md` (initial content: see below)
   - `{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md` (empty table)
   - `{DOCS}/{REPO_NAME}/design/README.md` (initial content: see below)
   - `{DOCS}/{REPO_NAME}/test/README.md` (initial content: see below)
4. If `{DOCS}` exists but `{DOCS}/{REPO_NAME}/` does not → create only:
   - `{DOCS}/{REPO_NAME}/specs/README.md`
   - `{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md`
   - `{DOCS}/{REPO_NAME}/design/README.md`
   - `{DOCS}/{REPO_NAME}/test/README.md`
5. If both exist → skip.

**Initial file contents:**

`{DOCS}/AI_INDEX.md`:
````markdown
# AI向けナビゲーションインデックス
> 新規開発開始時に clone してこのファイルを AI に注入してください。

## 共通知識
| ファイル | 内容 |
|---|---|
| [shared/glossary.md](shared/glossary.md) | 全リポジトリ共通用語集 |
| [shared/lessons-learned.md](shared/lessons-learned.md) | 横断的な知見・教訓 |

## リポジトリ別仕様書
| リポジトリ | 承認済み仕様書 | 知見 |
|---|---|---|
| （xddp.close 実行後に自動追記） | — | — |

## リポジトリ別設計書・テスト仕様書
| リポジトリ | 設計書（DSN・CHD） | テスト仕様（TSP） |
|---|---|---|
| （xddp.close 実行後に自動追記） | — | — |
````

`{DOCS}/{REPO_NAME}/specs/README.md`:
````markdown
# 承認済み仕様書: {REPO_NAME}
xddp.close で latest-specs/ から昇格した承認済みの最新仕様書を格納します。
ドラフト（未レビュー）は各リポジトリの latest-specs/ にあります。
````

`{DOCS}/{REPO_NAME}/design/README.md`:
````markdown
# 設計書アーカイブ: {REPO_NAME}
xddp.close で各 CR の DSN（実装方式設計書）と CHD（変更設計書）を格納します。
ファイル命名規則: DSN-{CR}.md / CHD-{CR}.md
AI が過去の設計判断を参照する際のインデックスとして使用されます。
````

`{DOCS}/{REPO_NAME}/test/README.md`:
````markdown
# テスト仕様書アーカイブ: {REPO_NAME}
xddp.close で各 CR の TSP（テスト仕様書）を格納します。
ファイル命名規則: TSP-{CR}.md
AI が過去のテスト戦略・テストパターンを参照する際のインデックスとして使用されます。
````

`{DOCS}/shared/lessons-learned.md` (cross-repository shared):
````markdown
# 知見ログ: 横断（全リポジトリ共通）
> xddp.close が CR クローズ時に自動追記します。

## エントリ一覧
| ID | タイトル | タグ | CR | リポジトリ | 日付 |
|---|---|---|---|---|---|
| （xddp.close 実行後に追記） | — | — | — | — | — |
````

`{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md` (per-repository):
````markdown
# 知見ログ: {REPO_NAME}
> xddp.close が CR クローズ時に自動追記します。

## エントリ一覧
| ID | タイトル | タグ | CR | 日付 |
|---|---|---|---|---|
| （xddp.close 実行後に追記） | — | — | — | — |
````

### 4.6. Create project-steering.md (if not exists)
Check if `{XDDP_DIR}/project-steering.md` exists in the current working directory.
If not found, copy `~/.claude/templates/project-steering-template.md` to `{XDDP_DIR}/project-steering.md`.
Replace `YYYY-MM-DD` in the 変更履歴 table with today's date, and `CR番号` with `{CR}`.
If already exists, leave it untouched.

### 5. Create progress.md
Read `~/.claude/templates/00_progress-management-template.md`, then create `{CR_PATH}/progress.md`:
- Replace all `{CR番号}` with `{CR}`.
- Set today's date as 開始日 and 最終更新.
- Step 1 (要求書作成) → ✅ 完了, today.
- All other steps → ⬜ 未着手.
- 次に実行すべきコマンド → `/xddp.02.analysis {CR}`

### 6. Report in Japanese
Tell the user what was created and show the next command to run.
If `xddp.config.md` was newly created, mention that it can be edited to adjust specout granularity, test framework, and test case granularity. For multi-repo configurations, instruct them to set `MULTI_REPO: true` and configure the `REPOS:` section. Emphasize that `REPOS:` keys must be the actual repository folder names (not abbreviations: e.g., `api:` → NG, `tasksaas-api:` → OK). Same rule applies to `REPO_NAME`.
If `{XDDP_DIR}/project-steering.md` was newly created, mention that it should be filled with project-specific naming conventions, architecture decisions, and existing patterns before starting Step 04 (specout). For multi-repo, also prompt them to fill in the "1.5 リポジトリ構成" section.
If `{XDDP_DIR}/latest-specs/` was newly created, mention that it will be populated by `/xddp.09.specs` and can be left empty for now.

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.01.init.md`.
