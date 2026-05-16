---
description: project-steering.md の未記入セクションをコード調査でドラフト生成し、人が確認・修正後に書き込む。「project-steering を埋めて」「リポジトリ構成を生成して」などで起動する。
---

You are executing **XDDP Fill Steering — Auto-draft project-steering.md**.

**Arguments:** $ARGUMENTS
- No arguments → target the shared `project-steering.md`, all unwritten sections
- `{repo}` (a repository name matching REPOS: key) → target `project-steering-{repo}.md`
- `cross` → target `project-steering-cross.md`
- `all` → target shared + all per-repo + cross (if REPOS: has ≥2 entries)
- Section number (e.g., `2`, `6`) after an optional repo/cross/all → target only those sections (multiple allowed: `2 6`)

> Examples:
> - `/xddp.fill-steering` → draft shared project-steering.md
> - `/xddp.fill-steering repo-a` → draft project-steering-repo-a.md
> - `/xddp.fill-steering cross` → draft project-steering-cross.md (interface conventions)
> - `/xddp.fill-steering all` → draft shared + all per-repo + cross

---

### 0. Parse arguments

Let `RAW_ARGS` = trimmed $ARGUMENTS.
Let tokens = split(RAW_ARGS).

Determine `TARGET_REPO`:
- If first token is a section number (matches `^\d`) → `TARGET_REPO` = `shared`, `TARGET_SECTIONS` = all tokens.
- If first token is `all` → `TARGET_REPO` = `all`, `TARGET_SECTIONS` = remaining tokens (section numbers if any).
- If first token is `cross` → `TARGET_REPO` = `cross`, `TARGET_SECTIONS` = remaining tokens.
- If first token matches a REPOS: key (detected after reading xddp.config.md in Step 1) → `TARGET_REPO` = that token, `TARGET_SECTIONS` = remaining tokens.
- If no arguments → `TARGET_REPO` = `shared`, `TARGET_SECTIONS` = [] (all sections).

If `TARGET_SECTIONS` is empty, treat as "all sections".

### 1. Locate xddp.config.md

Search for `xddp.config.md` starting from the current working directory, then walk up to parent directories until found or filesystem root is reached.

If not found: tell the user "xddp.config.md が見つかりませんでした。`/xddp.01.init` を先に実行してください。" and stop.

Read it and extract:
- `XDDP_DIR` (default: `xddp`)
- `REPOS:` mapping → `REPOS_KEYS` = list of repository names

Let `XDDP_ABS` = resolved absolute path of `{cwd}/{XDDP_DIR}`.

Now resolve `TARGET_REPO` if it was set from the first argument (may need REPOS_KEYS to verify):
- If first token matches a REPOS_KEYS entry → confirmed as `TARGET_REPO`.
- If first token is not a section number, not `all`, not `cross`, and not in REPOS_KEYS → report error: "指定された引数 '{token}' はリポジトリ名でも `all`/`cross` でもありません。" and stop.

**Determine target files** (`TARGETS` = list of {repo → steering_file} pairs):
- `TARGET_REPO = shared` → `[{shared: {XDDP_ABS}/project-steering.md}]`
- `TARGET_REPO = cross` → `[{cross: {XDDP_ABS}/project-steering-cross.md}]`
- `TARGET_REPO = {repo}` → `[{{repo}: {XDDP_ABS}/project-steering-{repo}.md}]`
- `TARGET_REPO = all` → shared + each repo in REPOS_KEYS + cross (if len(REPOS_KEYS)≥2)

### 2. Locate/create target project-steering file(s)

For each target file in `TARGETS`:
- If not found:
  - `shared` → copy `~/.claude/templates/project-steering-template.md`
  - `cross` → copy `~/.claude/templates/project-steering-cross-template.md`
  - `{repo}` → copy `~/.claude/templates/project-steering-repo-template.md`; replace `{REPO_NAME}` placeholder with actual repo name
  - Tell the user "（ファイル名）が存在しなかったためテンプレートからコピーしました。" and continue.
- If found: read it.

### 3. Identify unwritten sections

For each target file, scan for placeholder strings:

**Shared project-steering.md:**
| Section | Placeholder strings |
|---|---|
| §1 | `（プロジェクト名）`、`（主要言語: Python / TypeScript / Go / Java / etc.）`、`（フレームワーク: FastAPI / Next.js / Spring Boot / etc.）`、`（アーキテクチャ: モノリス / マイクロサービス / etc.）`、`（データベース: PostgreSQL / MySQL / DynamoDB / etc.）`、`（テストフレームワーク: pytest / Jest / JUnit / etc.）` |
| §1.5 | テーブル行が `\| （例）` で始まる（REPOS: ≥2 entries の場合のみスコープ） |
| §2 | `（プロジェクト固有の命名規約をここに記述する）` |
| §3 | `（プロジェクト固有のアーキテクチャ決定をここに記録する）` |
| §4 | `（プロジェクト固有のパターンをここに記述する）` |
| §5 | `（プロジェクト固有の禁止事項・注意事項をここに記述する）` |
| §6 | `（プロジェクト固有のモジュール構成をここに記述する）` |

**Per-repo project-steering-{repo}.md:**
| Section | Placeholder strings |
|---|---|
| §1 | `（リポジトリ名 = xddp.config.md の REPOS: キー名と一致）`、`（主要言語: ...）` などの () 囲みプレースホルダー |
| §2 | `（このリポジトリ固有の命名規約をここに記述する）`、`（このリポジトリ固有の DB・API 命名規約をここに記述する）` |
| §3 | `（このリポジトリ固有のアーキテクチャ決定をここに記録する）` |
| §4 | `（このリポジトリ固有のエラーハンドリングパターンをここに記述する）` など |
| §5 | `（このリポジトリ固有の禁止事項・注意事項をここに記述する）` |
| §6 | `（このリポジトリ固有のモジュール構成をここに記述する）` (if §6 exists) |

**Cross project-steering-cross.md:**
| Section | Placeholder strings |
|---|---|
| §1 | テーブル行が `\| （例）` で始まる |
| §2 | `（プロジェクト固有の SemVer 運用ルールをここに追記する）` |
| §3 | `（プロジェクト固有の命名規則をここに追記する）` |
| §4 | `（プロジェクト固有のエラーコード一覧をここに記述する）` |
| §5 | `（プロジェクト固有の認証方式をここに記述する）` |
| §6 | `（プロジェクト固有の移行期間ルールをここに記述する）` |

If `TARGET_SECTIONS` is specified: filter to only those sections.
Let `UNWRITTEN` = sections to process.
If `UNWRITTEN` is empty for all targets: tell the user "すべてのセクションが記入済みです。" and stop.

### 4. Investigate codebase and draft each section

For each section in `UNWRITTEN`, run the investigation and generate a draft.

**§1 Project overview (shared):**
Read `xddp.config.md` for already-set values. Then inspect:
- `requirements.txt` / `pyproject.toml` → Python project
- `package.json` → Node/TypeScript project
- `go.mod` → Go project
- `pom.xml` / `build.gradle` → Java project
- Root `README.md`

Draft the 6 config fields: `PROJECT_NAME`, `LANGUAGE`, `FRAMEWORK`, `ARCHITECTURE`, `DB`, `TEST_FRAMEWORK`.

**§1 Repository basic info (per-repo):**
Inspect the target repo's root files to draft `REPO_NAME`, `LANGUAGE`, `FRAMEWORK`, `BUILD_TOOL`, `TEST_FRAMEWORK`, `ROLE`, and the module map.

**§1 / §2 Cross-repo overview (cross):**
For each repo in `REPOS:`, investigate the `upstream-repos` / `downstream-repos` relationships to draft the target repository table and dependency block.

**§1.5 Repository structure (shared — only when len(REPOS_KEYS) ≥ 2):**
For each repo in `REPOS:`, investigate in parallel:
- `requirements.txt` / `pyproject.toml` / `package.json` / `go.mod` → main technologies
- `src/**/*.py` / `src/**/*.ts` import statements → inter-repo package dependencies
- `httpx.post` / `requests.post` / `fetch` / `axios` / `RestTemplate` calls → HTTP call targets
- `README.md` / `main.py` / `main.ts` / `app.py` → service role

Draft:
1. Repository table (name / role / main tech)
2. Dependency block (package deps + HTTP calls)

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

### 6. Write to project-steering file(s)

For each target file in `TARGETS`, for each section in `UNWRITTEN`:
- Replace the placeholder content in the target file with the confirmed draft.
- Replace the entire section body (from the section heading to the next `---` separator) with the confirmed draft.

Tell the user:
```
以下のファイルにセクションを記入しました:
- {ファイル名}: §X {セクション名}（対象セクション分を列挙）

次のステップ: 内容を確認し、必要に応じて手動で追記・修正してください。
スペックアウトを開始する場合は `/xddp.04.specout {CR番号}` を実行してください。
```

---
> **Maintenance note:** When modifying this file, also update `ClaudeCode/.claude/commands/xddp.fill-steering.md`.
