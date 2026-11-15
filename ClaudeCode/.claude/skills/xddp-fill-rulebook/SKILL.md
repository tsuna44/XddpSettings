---
name: xddp-fill-rulebook
description: project-rulebook.md の未記入セクションをコード調査でドラフト生成し、人が確認・修正後に書き込む。「project-rulebook を埋めて」「リポジトリ構成を生成して」などで起動する。
argument-hint: "[repo名 / cross / all] [節番号...]"
---

You are executing **XDDP Fill Steering — Auto-draft project-rulebook files**.

**Arguments:** $ARGUMENTS
- No arguments → multi-repo: the shared `project-rulebook.md`. Single-repo: the shared file + `project-rulebook-{repo}.md`（シングル構成の共通ファイルでコード調査から起こすのは「1. プロジェクト概要」だけのため）
- `{repo}` (a repository name matching a REPOS: key) → `project-rulebook-{repo}.md`（シングル構成でも使える）
- `cross` → `project-rulebook-cross.md`（REPOS: が2つ以上のときだけ）
- `all` → shared + all per-repo + cross (if REPOS: has ≥2 entries)
- Section number (e.g., `2`, `6`) after an optional repo/cross → target only those sections (multiple allowed: `2 6`). 節番号はファイルの種類ごとに意味が違う（例: 共通の 5 は禁止事項・注意事項、repo 別の 5 はアーキテクチャ決定記録（ADR））。`all` と節番号は一緒に指定できない

> Examples:
> - `/xddp-fill-rulebook` → draft the shared file (single-repo: shared + the repo)
> - `/xddp-fill-rulebook repo-a` → draft project-rulebook-repo-a.md
> - `/xddp-fill-rulebook repo-a 3` → draft only 「3. 命名規約」 of project-rulebook-repo-a.md
> - `/xddp-fill-rulebook cross` → draft project-rulebook-cross.md (interface conventions)
> - `/xddp-fill-rulebook all` → draft shared + all per-repo + cross

---

### 0. Parse arguments

Let `RAW_ARGS` = trimmed $ARGUMENTS.
Let tokens = split(RAW_ARGS).

Determine `TARGET_REPO`:
- If first token is a section number (matches `^\d`) → `TARGET_REPO` = `shared`, `TARGET_SECTIONS` = all tokens.
- If first token is `all` → `TARGET_REPO` = `all`, `TARGET_SECTIONS` = remaining tokens.
- If first token is `cross` → `TARGET_REPO` = `cross`, `TARGET_SECTIONS` = remaining tokens.
- If first token matches a REPOS: key (detected after reading xddp.config.md in Step 1) → `TARGET_REPO` = that token, `TARGET_SECTIONS` = remaining tokens.
- If no arguments → `TARGET_REPO` = `default`, `TARGET_SECTIONS` = [] (all sections).

If `TARGET_REPO = all` and `TARGET_SECTIONS` is not empty: tell the user the following and stop（引数の形の誤り）:
「節番号はファイルの種類ごとに意味が違います（例: 2 は共通では命名規約、repo 別ではアーキテクチャ概要、cross では API バージョニング規約）。`/xddp-fill-rulebook {repo} 2` のように種類を指定してください。」

### 1. Locate xddp.config.md

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Load Config" with:
  NOT_FOUND_MESSAGE: `"xddp.config.md が見つかりませんでした。\`/xddp-01-init\` を先に実行してください。"`
→ let `WORKSPACE_ROOT`, `XDDP_DIR`, `DOCS`, `REPOS_KEYS`, `REPOS_MAP`（他の戻り値は本スキルでは未使用）.

Let `XDDP_ABS` = `{WORKSPACE_ROOT}/{XDDP_DIR}`. Let `KEYS` = `REPOS_KEYS` joined with `,`.
Let `TODAY` = output of `date +%Y-%m-%d` (Bash).
Each repo's path is `{REPOS_MAP[repo] の値}`（ワークスペースルートからの相対パス）.

Now resolve `TARGET_REPO` if it was set from the first argument:
- If first token matches a REPOS_KEYS entry → confirmed as `TARGET_REPO`.
- If first token is not a section number, not `all`, not `cross`, and not in REPOS_KEYS → report error: "指定された引数 '{token}' はリポジトリ名でも `all`/`cross` でもありません。" and stop.
- If `TARGET_REPO = cross` and `len(REPOS_KEYS) == 1`: tell the user "シングルリポジトリ構成では project-rulebook-cross.md を扱いません（REPOS: が2つ以上のときだけ）。" and stop.

**Determine target files** (`TARGETS` = list of (kind, repo, file)):
- `TARGET_REPO = default` → `len(REPOS_KEYS) >= 2`: `[(shared, —, {XDDP_ABS}/project-rulebook.md)]`. `len(REPOS_KEYS) == 1`: shared + `(repo, {repo}, {XDDP_ABS}/project-rulebook-{repo}.md)` for the one repo.
- `TARGET_REPO = shared` → `[(shared, —, {XDDP_ABS}/project-rulebook.md)]`
- `TARGET_REPO = cross` → `[(cross, —, {XDDP_ABS}/project-rulebook-cross.md)]`
- `TARGET_REPO = {repo}` → `[(repo, {repo}, {XDDP_ABS}/project-rulebook-{repo}.md)]`
- `TARGET_REPO = all` → shared + each repo in REPOS_KEYS + cross (if `len(REPOS_KEYS) >= 2`)

### 2. Locate/create target project-rulebook file(s)

For each target in `TARGETS`, run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/rulebook_files.py ensure --kind {kind} [--repo {repo}] --xddp-dir {XDDP_ABS} --docs {DOCS} --today {TODAY} --repos-keys {KEYS}`
（`--cr` は渡さない。exit 2 は stderr を示して停止する）
- `created-from-template` / `copied-from-docs` / `updated-from-docs`: tell the user（テンプレートから作った・`{DOCS}` から戻した・`{DOCS}` の更新を取り込んだ）and continue.
- `conflict`: tell the user the following and continue（書き込みは Step 6 の記入箇所だけなので、人が書いた内容は消えない）:
  > ⚠️ `{file}` は、この作業場所と `{DOCS}` の両方で変わっています。どちらも書き換えていません。`rulebook_files.py diff --xddp-dir {XDDP_ABS} --docs {DOCS} --file {ファイル名}` で違いを確かめて人が合わせるか、`/xddp-close` の Step D で選んでください。
- Then read the file.

### 3. Identify unwritten sections

For each target, run via Bash:
`"$PY" ~/.claude/skills/xddp-common/scripts/rulebook_files.py unfilled --kind {kind} --file {file} --repos-keys {KEYS}`
→ JSON list of `{"number", "heading", "state", "unfilled_items", "draft"}`. Classify each section:
- `TARGET_SECTIONS` is empty: draft the sections whose `state` is `unfilled` and `draft` is true（全記入箇所をドラフトする）.
- `TARGET_SECTIONS` is given: for the sections whose `number` is in `TARGET_SECTIONS` and `draft` is true, draft only their `unfilled_items`（`partial` でも対象にする）. 節番号はそのファイルの種類の番号として扱う.
- Show in Step 5 (do not draft):
  - `draft` is false and `state` is `unfilled` / `partial`: 「コード調査からは起こさない節（人が記入する）」
  - `state` is `partial` (and not targeted): 「一部が未記入: {unfilled_items}」
  - `state` is `missing`: 「見出しが見つからない（見出しを変えた可能性）」
- Do not draft or show `filled` and `not-applicable` sections.

Let `UNWRITTEN` = sections (with their items) to draft.
If `UNWRITTEN` is empty for all targets: tell the user "コード調査から起こす未記入の節はありません。" and show the Step 5 lists, then stop.

### 4. Investigate codebase and draft each section

For each section in `UNWRITTEN`, investigate under `{REPOS_MAP[repo] の値}` of the target repo（共通・cross ではすべての repo）and draft only the items the code confirms. If an item cannot be confirmed, do not draft it; list it in Step 5 as 「確認できず」（記述欄はテンプレートのまま残す）.

| 種類 | 節（見出し） | 調べ方 |
|---|---|---|
| 共通 | 1. プロジェクト概要 | ビルド・パッケージの定義ファイル（例: `pyproject.toml`・`package.json`・`go.mod`・`pom.xml`・`Cargo.toml`・`CMakeLists.txt`・`Makefile`・`*.csproj`）とルートの README。`xddp.config.md` の値も参照する |
| 共通 | 1.5 リポジトリ構成（マルチのみ） | 各 repo の役割と主要技術（表の行だけ。依存関係は cross の「1. 対象リポジトリ一覧」に書く） |
| 共通 | 2. 命名規約 | 各 repo から 5〜10 個のソースを抜き出し、ファイル・型・関数・定数の命名。データ定義（スキーマ・構造体・テーブル定義等）やインタフェース定義（関数シグネチャ・エンドポイント・メッセージ定義等）があればその命名 |
| 共通 | 3. アーキテクチャ決定記録（ADR） | 各 repo の git log（下の「ADR の調べ方」） |
| 共通 | 4. 既存パターン・慣習 | エラーの扱い・並行・非同期の扱い・テストの置き場所と書き方を、抜き出したソースとテストから |
| 共通 | 6. モジュール構成メモ | ディレクトリ構成と各モジュールの入口のファイル（下の「入口のファイル」） |
| repo | 1. リポジトリ基本情報 | 共通 1. と同じ調べ方をその repo で。「主要モジュール役割」は共通 6. と同じ調べ方 |
| repo | 2. アーキテクチャ概要 | ディレクトリ構造の決まりと、モジュール間の参照の向き（import・include・呼び出し） |
| repo | 3. 命名規約 | 共通 2. と同じ調べ方をその repo で |
| repo | 4. コーディング規約・既存パターン | 共通 4. と同じ調べ方をその repo で |
| repo | 5. アーキテクチャ決定記録（ADR） | その repo の git log（下の「ADR の調べ方」） |
| cross | 1. 対象リポジトリ一覧 | repo どうしの参照（ビルドの依存の宣言・共有パッケージの import・通信のインタフェース〔関数呼び出し・HTTP/RPC・メッセージ・バス・共有ファイル等〕） |
| cross | 3. インタフェース命名規則 | repo の間で提供・消費するインタフェースの名前 |
| cross | 4. エラーコード・ステータスコード体系 | repo の間で受け渡すエラーの表現 |
| cross | 5. サービス間認証方式 | repo の間の通信の認証の扱い |

（共通 1.6・5、repo 6、cross 2・6 はコード調査から起こさない。`unfilled` の `draft` が false になる）

**共通と repo 別の書き分け:** 共通の 2.・3.・4.・6. には、すべての repo に共通して見られるものだけを書き、repo 固有のものは repo 別の対応する節に書く。シングル構成では `unfilled` が共通の 2.・3.・4.・6. を `draft: false` にするので、コードから分かることは repo 別の節に起こす。

**入口のファイル（モジュール構成）:** ディレクトリ構成を読み、言語ごとの入口のファイルを読む（例: Python は各パッケージの `__init__.py`、TypeScript/JavaScript は `index.ts`/`index.js`、Go は各パッケージ直下の `*.go`、Java は `src/main/` と `package-info.java`、Rust は `lib.rs`/`main.rs`、C/C++ は公開ヘッダ）。分からない言語はディレクトリ構成だけを使う。

**ADR の調べ方:** Run on each repo path:
```bash
git -C {REPOS_MAP[repo] の値} log --oneline --all --extended-regexp --grep="refactor|revert|rework|migrate|redesign" -20
git -C {REPOS_MAP[repo] の値} log --oneline --all -30 --name-only --format="%H %s"
```
AI judgment: if changed files span ≥3 distinct top-level directories → include as candidate. At most 5 candidates.
Draft each candidate as a block（番号は節の中の既存の `### ADR-NNN:` の最大＋1）:
```markdown
### ADR-NNN: {コミットメッセージから推定したタイトル}
- **決定:** {コミットメッセージから読み取れる設計上の判断}
- **理由:** {読み取れる範囲。読み取れなければ「確認できず」}
- **記録日:** {TODAY}（出典: git {hash[:7]} — 人による確認・修正が必要）
```
If no candidates are found: do not draft; list as 「確認できず」 in Step 5.

**ドラフトの書式:** 記述欄に書く内容は、規約・パターンは箇条書き（`- `）で末尾に `（出典: {調べたファイル・コミット}）` を付ける。`## 1.` のコードブロックの値はその行の `（…）` を置き換える。表は `| （例）` の行を置き換える（当てはまらなければ `| 該当なし | … |` の行を1つ書く）。

### 5. Present all drafts and accept diff instructions

Show all drafted sections together in a single message:

```
以下のドラフトを生成しました。修正があればファイル・節番号と変更内容を指示してください。
問題なければ「OK」と入力してください。

---

## {ファイル名} 「{節の見出し}」（ドラフト）

{draft content（サブセクションごとに、書く記述欄を示す）}

---

（以降、対象の節を続ける）

---

人が記入する節・一部が未記入の節・確認できなかった項目・見出しが見つからない節:
- {ファイル名} 「{節の見出し}」: {理由・未記入の項目}
```

Accept the user's response:
- `OK` / `ok` / `はい` / `問題ない` → proceed to Step 6
- Diff instructions (e.g., "repo-a の 3. は〇〇に変えてください") → apply changes and re-present the updated drafts
- Repeat until the user confirms with OK

### 6. Write to project-rulebook file(s)

For each target file and each section in `UNWRITTEN`, write only to the following places:
- サブセクションの記述欄（`（…をここに記述する）`・`（…をここに記録する）` の行）: replace the placeholder line with the confirmed draft.
- `## 1.` のコードブロックの `（…）` の値: replace the value.
- 表の `| （例）` の行: replace those rows.
Keep the example code blocks, default principles and section blockquotes unchanged.

Send a PushNotification:
- title: "xddp-fill-rulebook 完了"
- message: "{書き込んだファイル名と節番号の一覧}への書き込みが完了しました。内容を確認してください。"
  （例: "project-rulebook.md §1 / project-rulebook-repo-a.md §1 §3 への書き込みが完了しました。内容を確認してください。"）

Tell the user:
```
以下のファイルに記入しました:
- {ファイル名}: 「{節の見出し}」（対象の節を列挙）

人が記入する節: {Step 5 の一覧}

次のステップ: 内容を確認し、必要に応じて手動で追記・修正してください。
スペックアウトを開始する場合は `/xddp-04-specout {CR番号}` を実行してください。
```
