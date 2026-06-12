---
description: モジュールカタログを生成・更新する。リポジトリのモジュール構成・主要シンボル・依存関係を
  baseline_docs/{repo}/module-catalog.md に保存し、スペックアウトの BFS 優先度制御に活用する。
  「コードマップを生成して」「モジュールカタログを作って」などで起動する。
argument-hint: "[repo名 | all]"
---

You are executing **XDDP Codemap — Generate Module Catalog**.

> 本スキルは CR 非依存のため CR 解決行（xddp.common の "## CR Resolution"）は不要。

**Arguments:** $ARGUMENTS
- No args → all repos defined in REPOS:
- `{repo}` → specific repository (matches a REPOS: key)
- `all` → all repositories

---

### Step 0: Parse arguments, locate xddp.config.md

Search for `xddp.config.md` starting from the current working directory, walking up to parent
directories. If not found: report error and stop.

Read and extract:
- `WORKSPACE_ROOT` (directory containing xddp.config.md)
- `XDDP_DIR` (default: `xddp`)
- `DOCS_DIR` (default: `baseline_docs`)
- `REPOS:` mapping → `REPOS_MAP` (name → path), `REPOS_KEYS`
- `SPECOUT_EXCLUDE_PATTERNS` (default: `tests/,test/,__tests__/,spec/,specs/,__mocks__/,fixtures/,vendor/,node_modules/`)
- `SPECOUT_INCLUDE_EXTENSIONS` (default: empty = all)

Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.

**Resolve target repos:**
- No args or `all` → `TARGET_REPOS` = all REPOS_KEYS
- `{repo}` → if matches a REPOS_KEY: `TARGET_REPOS` = [{repo}]. Else: report error and stop.
- `cross` is reserved and not a valid target (report error).

### Step 1: For each repo in TARGET_REPOS — generate catalog

For each `{repo}` in `TARGET_REPOS`:

Let `REPO_PATH` = `REPOS_MAP[repo]`.

#### Step 1a: Detect language and project structure

Check for the following files in `{REPO_PATH}`:
- `package.json` → Node.js / TypeScript / JavaScript
- `pyproject.toml` or `requirements.txt` or `setup.py` → Python
- `go.mod` → Go
- `pom.xml` or `build.gradle` → Java / Kotlin
- `Cargo.toml` → Rust
- `CMakeLists.txt` or `Makefile` → C/C++ (or embedded)
- Fallback → inspect directory structure for language hints

Let `LANGUAGE` = detected language (or "Unknown").
Let `BUILD_FILE` = path to detected build file (or empty).

#### Step 1b: Identify module directories

**ツール選択（優先度順）:**
1. Glob ツール（`{REPO_PATH}/**/*` パターンでディレクトリ一覧を取得）を第一選択とする
2. Glob が使用できない場合: Bash で `find {REPO_PATH} -type d -maxdepth 3` にフォールバック

取得したディレクトリ一覧から EXCLUDE_PATTERNS を**後処理フィルタ**として適用する
（各ディレクトリパスが EXCLUDE_PATTERNS の任意エントリをサブストリングとして含む場合に除外）。

Apply heuristics to identify "module directories" (directories that contain source files at the
detected extension):
- If INCLUDE_EXTENSIONS set: directories containing files with those extensions
- Otherwise: directories containing source files (`.py`, `.ts`, `.go`, `.java`, `.rs`, `.c`, `.cpp`, `.h` etc.)
- Directories that contain only other directories (no source files) are treated as namespace containers, not modules themselves

Let `MODULE_DIRS` = list of identified module directories.

Limit to at most 50 module directories per repo. If more found: record the first 50 by path depth
(shallow-first) and add the following note to `CATALOG_FILE`:
```
> ⚠️ このリポジトリには {N} 件のモジュールが見つかりましたが、上限（50件）のため最初の 50 件のみ記録しています。
> 残りのモジュールを追加する場合: このファイルの「## 2. モジュール一覧」に手動でエントリを追記してください。
```

#### Step 1c: For each module directory — extract symbols and imports

For each `module_dir` in `MODULE_DIRS`:

**Detect entry point:**

| Language | Entry point files to check |
|---|---|
| Python | `__init__.py` in module_dir |
| TypeScript/JavaScript | `index.ts`, `index.js`, `index.tsx` in module_dir |
| Go | All `*.go` files in module_dir (package-level) |
| Java/Kotlin | `package-info.java` if present; else first `.java`/`.kt` file |
| Rust | `lib.rs`, `mod.rs`, `main.rs` in module_dir |
| C/C++ | Top-level `.h` files in module_dir |
| Unknown | First 3 source files found |

Read the entry point file(s).

**Extract exported/public symbols (top 10 per module):**
- Python: top-level `def`, `class`, entries in `__all__` if defined
- TypeScript/JS: `export function`, `export class`, `export const`, `export type`
- Go: capitalized top-level `func`, `type`, `var`, `const`
- Java/Kotlin: `public class`, `public interface`, `public fun`
- Rust: `pub fn`, `pub struct`, `pub enum`, `pub trait`
- C/C++: non-static function declarations in `.h` files
- Limit to 10 symbols per module; if more found, record top 10 and note count

**シンボル → モジュール逆引きテーブルの構築:**
各モジュールのシンボルを記録する際、以下の形式で `SYMBOL_TO_MODULE` マップを構築する:
  `SYMBOL_TO_MODULE[symbol_name] = module_dir`
このマップは specout エージェントの BFS 優先度計算（Wave 0 完了後）でシンボル→モジュール逆引きに使用する。
マップは `module-catalog.md` の「## 3. シンボル索引」セクションとして出力する。

**Extract module-level imports (dependencies within the same repo):**
Read the entry point file(s) and scan for import statements.
Filter to only internal imports (imports that reference another module within REPO_PATH).
Map import paths to module directory names.
Let `DEPS[module_dir]` = list of internal modules imported.

#### Step 1d: Build reverse dependency map

After processing all modules:
For each module M and each dep D in DEPS[M]:
  Add M to `RDEPS[D]` (D is depended on by M).

#### Step 1e: Infer module roles

For each module_dir, infer a one-line role description using:
1. Docstring / module-level comment in the entry point file
2. README.md in the module directory (if present)
3. Directory name heuristics (e.g., `auth/` → "認証・認可", `db/` → "データアクセス層")
4. If none available: "(役割未判定 — 手動記入推奨)"

#### Step 1f: Generate module-catalog.md from template

Read `~/.claude/skills/xddp.templates/module-catalog-template.md`.
Fill in all placeholders with the collected data.
Generate Mermaid dependency graph from DEPS/RDEPS.

Let `CATALOG_FILE` = `{DOCS}/{repo}/module-catalog.md`.
Ensure `{DOCS}/{repo}/` directory exists (`mkdir -p` via Bash).
Write `CATALOG_FILE`. (No human confirmation; overwrite if exists.)

### Step 2: Report (in Japanese)

Tell the user:

> **モジュールカタログ生成完了**
>
> | リポジトリ | 出力ファイル | モジュール数 |
> |---|---|---|
> | {repo} | `{CATALOG_FILE}` | {N} |
>
> **次のステップ:**
> - 内容を確認し、役割記述が不正確な場合は手動で修正してください
> - スペックアウト（`/xddp.04.specout`）実行時にカタログが自動参照されます
> - カタログを更新する場合: `/xddp.codemap {repo}` を再実行してください（上書き再生成）

---
> **保守メモ:** このファイルを変更した場合は、`README.md`（スキル一覧テーブル）、`CLAUDE.md`（ステップ番号体系テーブル）も合わせて更新すること。
