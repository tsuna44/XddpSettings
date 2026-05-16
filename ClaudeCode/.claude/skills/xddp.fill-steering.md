---
description: project-steering.md の未記入セクションをコード調査でドラフト生成し、人が確認・修正後に書き込む。「project-steering を埋めて」「リポジトリ構成を生成して」などで起動する。
---

You are executing **XDDP Fill Steering — Auto-draft project-steering.md**.

**Arguments:** $ARGUMENTS
- No arguments → target all unwritten sections
- Section number (e.g., `1.5`, `2`, `6`) → target only those sections (multiple allowed: `2 6`)

---

### 0. Parse arguments

Let `TARGET_SECTIONS` = list of section numbers from $ARGUMENTS. If empty, treat as "all".

### 1. Locate xddp.config.md

Search for `xddp.config.md` starting from the current working directory, then walk up to parent directories until found or filesystem root is reached.

If not found: tell the user "xddp.config.md が見つかりませんでした。`/xddp.01.init` を先に実行してください。" and stop.

Read it and extract:
- `XDDP_DIR` (default: `xddp`)
- `MULTI_REPO` (default: `false`)
- `REPOS:` mapping (only if MULTI_REPO: true)
- `REPO_NAME`

Let `XDDP_ABS` = resolved absolute path of `{cwd}/{XDDP_DIR}`.
Let `STEERING` = `{XDDP_ABS}/project-steering.md`.

### 2. Locate project-steering.md

Check if `{STEERING}` exists.

- If not found: copy `~/.claude/templates/project-steering-template.md` to `{STEERING}`.
  Tell the user "project-steering.md が存在しなかったためテンプレートからコピーしました。" and continue.
- If found: read it.

### 3. Identify unwritten sections

Scan the file for the following placeholder strings (each entry = that section is "unwritten"):

| Section | Placeholder strings (any remaining = unwritten) |
|---|---|
| §1 | `（プロジェクト名）`、`（主要言語: Python / TypeScript / Go / Java / etc.）`、`（フレームワーク: FastAPI / Next.js / Spring Boot / etc.）`、`（アーキテクチャ: モノリス / マイクロサービス / etc.）`、`（データベース: PostgreSQL / MySQL / DynamoDB / etc.）`、`（テストフレームワーク: pytest / Jest / JUnit / etc.）`、`（true / false）` |
| §1.5 | `（実際の依存関係をここに記述する）`、テーブル行が `\| （例）` で始まる |
| §2 | `（プロジェクト固有の命名規約をここに記述する）` |
| §3 | `（プロジェクト固有のアーキテクチャ決定をここに記録する）` |
| §4 | `（プロジェクト固有のパターンをここに記述する）` |
| §5 | `（プロジェクト固有の禁止事項・注意事項をここに記述する）` |
| §6 | `（プロジェクト固有のモジュール構成をここに記述する）` |

If `TARGET_SECTIONS` is specified: filter to only those sections.
If `MULTI_REPO: false`: exclude §1.5 from scope.

Let `UNWRITTEN` = list of sections to process.

If `UNWRITTEN` is empty: tell the user "すべてのセクションが記入済みです。" and stop.

### 4. Investigate codebase and draft each section

For each section in `UNWRITTEN`, run the investigation and generate a draft.

**§1 Project overview:**
Read `xddp.config.md` for already-set values. Then inspect:
- `requirements.txt` / `pyproject.toml` → Python project
- `package.json` → Node/TypeScript project
- `go.mod` → Go project
- `pom.xml` / `build.gradle` → Java project
- Root `README.md`

Draft the 7 config fields: `PROJECT_NAME`, `LANGUAGE`, `FRAMEWORK`, `ARCHITECTURE`, `DB`, `TEST_FRAMEWORK`, `MULTI_REPO`.

**§1.5 Repository structure (MULTI_REPO: true only):**
For each repo in `REPOS:`, investigate in parallel:
- `requirements.txt` / `pyproject.toml` / `package.json` / `go.mod` → main technologies
- `src/**/*.py` / `src/**/*.ts` import statements → inter-repo package dependencies
- `httpx.post` / `requests.post` / `fetch` / `axios` / `RestTemplate` calls → HTTP call targets
- `README.md` / `main.py` / `main.ts` / `app.py` → service role
- Shared package `__init__.py` or `index.ts` exports → shared interfaces

Draft:
1. Repository table (name / path / role / main tech)
2. Dependency block (package deps + HTTP calls)
3. Shared interfaces table

**§2 Naming conventions:**
Sample 5–10 source files from each repo and examine:
- File/directory names → naming pattern (snake_case, camelCase, kebab-case)
- Class names → PascalCase or other
- Function/method names → snake_case or camelCase
- Constants → UPPER_SNAKE_CASE or other
- DB table/column names (look for ORM model definitions or migration files)
- API endpoint paths (look for router definitions)

**§6 Module structure:**
Read directory structure. Then, based on `LANGUAGE` detected in §1:

| LANGUAGE | Entry point files to read |
|---|---|
| Python | `__init__.py` in each package directory |
| TypeScript / JavaScript | `index.ts` / `index.js` in each module directory |
| Go | Top-level `*.go` files in each package directory |
| Java | `src/main/` structure + `package-info.java` |
| Rust | `lib.rs` / `main.rs` |
| Other (unknown) | Directory structure only; skip file content |

Draft a concise module map showing each directory's role.

**§3 and §5 (not applicable):**
Insert the note: `（コード調査から確認できなかったため手動記入してください）`

**§4 (filled in during specout):**
Insert the note: `（スペックアウト（工程4）で調査・記入されます）`

### 5. Present all drafts and accept diff instructions

Show all drafted sections together in a single message:

```
以下のドラフトを生成しました。修正があればセクション番号と変更内容を指示してください。
問題なければ「OK」と入力してください。

---

## §1 プロジェクト概要（ドラフト）

{draft content}

---

## §1.5 リポジトリ構成（ドラフト）

{draft content}

---

（以降、対象セクション分を続ける）
```

Accept the user's response:
- `OK` / `ok` / `はい` / `問題ない` → proceed to Step 6
- Diff instructions (e.g., "§2 の命名規約は〇〇に変えてください") → apply changes and re-present the updated drafts
- Repeat until the user confirms with OK

### 6. Write to project-steering.md

For each section in `UNWRITTEN`, replace the placeholder content in `{STEERING}` with the confirmed draft.

Replace the entire section body (from the section heading to the next `---` separator) with the confirmed draft.

Tell the user:
```
project-steering.md に以下のセクションを記入しました:
- §X: {セクション名}
（対象セクション分を列挙）

次のステップ: 内容を確認し、必要に応じて手動で追記・修正してください。
スペックアウトを開始する場合は `/xddp.04.specout {CR番号}` を実行してください。
```

---
> **Maintenance note:** When modifying this file, also update `ClaudeCode/.claude/commands/xddp.fill-steering.md`.
