---
description: XDDP フェーズ0: CRワークスペースを初期化する。CR番号・タイトルを引数に取り、成果物フォルダ・progress.md・テンプレートから生成した要求書（REQ-{CR}.md）を作成する。引数省略時はAIが対話的に質問する。「ワークスペースを初期化して」「CRを開始して」などで起動する。
argument-hint: "CR番号 タイトル [要求書.md]"
---

You are executing **XDDP Step 01 — Initialize CR Workspace**.

**Arguments:** $ARGUMENTS
- 1st token: CR number (e.g. `REQ-2026-001`)
- 2nd token: title (自由記述のタイトル文字列)
- 3rd token (optional): path to an existing requirements note (メモ・チケット・議事録等。あれば参照コピーする)

---

Let `CR` = 1st token, `TITLE` = 2nd token, `REQ_FILE` = 3rd token (optional).

### 0. Resolve CR / title (ask if missing)
**このステップは既存 Step 0.5「Resolve XDDP_DIR」より前に実行する**（Step 0.5 が `CR_PATH = {XDDP_ABS}/{CR}` を確定するため、その前に `CR` を必ず確定させる。無引数実行時に空 `CR` で `CR_PATH` を組んでしまう順序矛盾を防ぐ）。
- If $ARGUMENTS has no tokens at all（完全な無引数実行）:
  Ask the user in Japanese for: CR番号、タイトル、既存の要求書ファイルパス（任意。手元になければ空欄でよい旨を伝える）。
  Set `CR`, `TITLE` from the answers. Set `REQ_FILE` from the answer only if the user provided a path.
- Else if `CR` is set but `TITLE` is missing:
  Ask the user in Japanese for the title only. Set `TITLE` from the answer.
- `REQ_FILE` is never prompted for when `CR` and `TITLE` were both supplied — it remains optional in that case.

### 0.5. Resolve XDDP_DIR

Check if `xddp.config.md` exists in the current working directory.
- If exists, read it and extract `XDDP_DIR` (default: `xddp` if the key is absent).
- If not exists (first run), use `XDDP_DIR = xddp`.

Resolve paths relative to the directory containing `xddp.config.md` (= workspace root).
Let `XDDP_ABS` = resolved absolute path of `{cwd}/{XDDP_DIR}`.
Let `CR_PATH`  = `{XDDP_ABS}/{CR}`.

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

### 3. Create requirements file from template
**冪等性ガード:** If `{CR_PATH}/01_requirements/REQ-{CR}.md` already exists → do NOT overwrite it. Skip Step 3 and Step 3.6 entirely, and report to the user that the existing requirements file was preserved（既存CRへの再実行時に人の編集内容を保護するため。既存 Step 4「Create xddp.config.md (if not exists)」と同じ "if not exists" 方針）。
Otherwise, copy `~/.claude/skills/xddp.01.init/templates/01_req-template.md` to `{CR_PATH}/01_requirements/REQ-{CR}.md`.
In the copied file, apply the following literal text replacements:
- `REQ-{YYYY}-{NNN}` → `{CR}`（文書番号はCR番号をそのまま機械的に流用する。連番管理は行わない）
- `{変更タイトル}` → `{TITLE}`
- `{YYYY-MM-DD}` → today's date（メタデータ欄の「作成日」と、末尾「8. 変更履歴」表の初版行の日付、両方の出現箇所に適用される。同じ日付でよいため区別しない）
`{氏名}`（作成者欄・変更履歴の変更者欄）と「版数：1.0」はプレースホルダーのまま変更しない（人が編集する）。

### 3.5. Create latest-specs/ (if not exists)
Check if `{XDDP_DIR}/latest-specs/` exists in the current working directory.
If not found, create it and place a `{XDDP_DIR}/latest-specs/README.md` with the following content:
```
# 最新仕様書

このディレクトリには `/xddp.11.specs` で生成された最新仕様書を格納します。
リポジトリ別サブディレクトリ（例: repo-a/、repo-b/）に分けて格納します。
クロスリポジトリのインタフェース仕様は cross/interfaces/ に格納します。
初回の `xddp.04.specout` 実行時は空でも問題ありません。
```

### 3.6. Attach reference requirements file (if provided)
（Step 3 が冪等性ガードでスキップされた場合は、本ステップもスキップする。）
If `REQ_FILE` is set:
- Copy `REQ_FILE` as-is into `{CR_PATH}/01_requirements/`, keeping its original filename.
  - If the source filename is literally `REQ-{CR}.md`（Step 3で作成したファイルと衝突する場合）→ 拡張子の前に `-original` を付与してリネームコピーする（例: `REQ-{CR}-original.md`）。
- Append the following line to `{CR_PATH}/01_requirements/REQ-{CR}.md`. 挿入位置は **メタデータ最終行 `**版数：** 1.0` の直後、最初の `---` の前** の1箇所に固定する（記入ガイダンス blockquote より前）:
  ```
  **参照:** <{コピー後のファイル名}を参照>
  ```
If `REQ_FILE` is not set → skip Step 3.6 entirely（参照注記は追加しない）。

### 4. Create xddp.config.md (if not exists)
Check if `xddp.config.md` exists in the current working directory.
If not found, copy `~/.claude/skills/xddp.01.init/templates/xddp.config.md` to `./xddp.config.md`.
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
   - For each `{repo}` in `REPOS_KEYS`:
     - `{DOCS}/{repo}/specs/README.md` (initial content: see below)
     - `{DOCS}/{repo}/knowledge/lessons-learned.md` (empty table)
     - `{DOCS}/{repo}/design/README.md` (initial content: see below)
     - `{DOCS}/{repo}/crs/README.md` (initial content: see below)
     - `{DOCS}/{repo}/test/README.md` (initial content: see below)
4. If `{DOCS}` exists → for each `{repo}` in `REPOS_KEYS`:
   - If `{DOCS}/{repo}/` does not exist → create only:
     - `{DOCS}/{repo}/specs/README.md`
     - `{DOCS}/{repo}/knowledge/lessons-learned.md`
     - `{DOCS}/{repo}/design/README.md`
     - `{DOCS}/{repo}/crs/README.md`
     - `{DOCS}/{repo}/test/README.md`
5. If `{DOCS}` and all per-repo dirs exist → skip.

**Initial file contents:**

`{DOCS}/AI_INDEX.md`:
````markdown
# AI向けナビゲーションインデックス
> 新規開発開始時に clone してこのファイルを AI に注入してください。

<!-- セクション管理: 各スキルが対応セクションを自動 upsert する。手動編集時は見出し名を変えないこと。 -->

## ユースケース一覧
<!-- xddp.11.specs（先行 upsert）と xddp.close Step C2 が更新する -->
| ユースケース | 目的（1行） | description | 関連モジュール | 最終更新CR |
|---|---|---|---|---|
| （xddp.11.specs / xddp.close 実行後に自動追記） | — | — | — | — |

## リポジトリ別仕様書
<!-- xddp.close Step C2 が更新する -->
| リポジトリ | バージョン | overview | モジュール数 | 最終更新CR |
|---|---|---|---|---|
| （xddp.close 実行後に自動追記） | — | — | — | — |

## モジュール別最新仕様
<!-- xddp.11.specs（先行 upsert）と xddp.close Step C2 が更新する -->
| リポジトリ | モジュール | spec | structure | state | 最終更新CR |
|---|---|---|---|---|---|
| （xddp.11.specs / xddp.close 実行後に自動追記） | — | — | — | — | — |

## クロスインタフェース一覧
<!-- マルチリポジトリ構成（REPOS: が2エントリ以上）の場合のみ使用。xddp.close Step C2 が更新する -->
| インタフェース | spec | schema | バージョン | 最終更新CR |
|---|---|---|---|---|
| （xddp.close 実行後に自動追記） | — | — | — | — |

## リポジトリ別設計書・テスト仕様書
<!-- xddp.close Step C4/C5 が更新する -->
| リポジトリ | 設計書（DSN・CHD） | テスト仕様（TSP） |
|---|---|---|
| （xddp.close 実行後に自動追記） | — | — |

## 共通知識
<!-- xddp.close Step C6 が更新する -->
| ドキュメント | 説明 |
|---|---|
| [project-rulebook.md](project-rulebook.md) | プロジェクト共通規約（最終更新CR: —） |
````

`{DOCS}/{repo}/specs/README.md` (substitute actual {repo} name):
````markdown
# 承認済み仕様書: {repo}
xddp.close で latest-specs/{repo}/ から昇格した承認済みの最新仕様書を格納します。
````

`{DOCS}/{repo}/design/README.md`:
````markdown
# 設計書参照: {repo}
このディレクトリは本ツールでは使用されていません。変更要求仕様書（CRS）は `../crs/` に、変更設計書（DSN・CHD）は各 CR フォルダ（git 履歴）に格納されます。
````

`{DOCS}/{repo}/crs/README.md`:
````markdown
# 変更要求仕様書アーカイブ: {repo}
xddp.close で各 CR の変更要求仕様書（CRS）を格納します。ファイル命名規則: CRS-{CR}.md
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

### 4.6. Initialize project-rulebook files (knowledge hub priority)

Read `REPOS:` (already read in 4.5). Let `REPOS_KEYS` = list of all repository names.
Let `DOCS` = resolved absolute path of `{cwd}/{DOCS_DIR}` (already resolved in 4.5).

**【共通 project-rulebook.md の初期化】**
- If `{XDDP_DIR}/project-rulebook.md` does not exist:
  - If `{DOCS}/project-rulebook.md` exists → copy it (inherit knowledge from previous CRs).
  - Otherwise → copy `~/.claude/skills/xddp.common/templates/project-rulebook-template.md`; replace `YYYY-MM-DD` with today, `CR番号` with `{CR}`.
- If already exists → leave untouched.

**【リポジトリ別 project-rulebook の初期化（REPOS: に2つ以上エントリがある場合のみ）】**
- If `len(REPOS_KEYS) >= 2`:
  - For each `{repo}` in `REPOS_KEYS`:
    - If `{XDDP_DIR}/project-rulebook-{repo}.md` does not exist:
      - If `{DOCS}/{repo}/project-rulebook.md` exists → copy it.
      - Otherwise → copy `~/.claude/skills/xddp.common/templates/project-rulebook-repo-template.md`; replace `{REPO_NAME}` with `{repo}`, `YYYY-MM-DD` with today, `{CR}` with `{CR}`.
    - If already exists → leave untouched.

**【cross/ project-rulebook の初期化（REPOS: に複数エントリがある場合のみ）】**
- If `len(REPOS_KEYS) >= 2`:
  - If `{XDDP_DIR}/project-rulebook-cross.md` does not exist:
    - If `{DOCS}/cross/project-rulebook.md` exists → copy it.
    - Otherwise → copy `~/.claude/skills/xddp.common/templates/project-rulebook-cross-template.md`; replace `YYYY-MM-DD` with today, `{CR}` with `{CR}`.
  - If already exists → leave untouched.

### 5. Create progress.md
**冪等性ガード:** If `{CR_PATH}/progress.md` already exists → do NOT overwrite it. Skip Step 5 entirely（既存CRへの再実行時に、人が手動で更新した工程ステータス（工程1の ✅ 完了 等）を保護するため。Step 3・Step 4 と同じ "if not exists" 方針）。
Otherwise, read `~/.claude/skills/xddp.01.init/templates/00_progress-management-template.md`, then create `{CR_PATH}/progress.md`:
- Replace all `{CR番号}` with `{CR}`.
- Replace `{変更タイトル}` with `{TITLE}`（progress.md のタイトル欄。REQ-{CR}.md 側と同じタイトルを記入し、生プレースホルダーが残らないようにする）。
- Set today's date as 開始日 and 最終更新.
- Step 1 (要求書作成) → 🔄 進行中, 詳細ステップ → `テンプレート配置済み・要編集`, 完了日 → `-`.
- `## 備考・メモ` セクションのプレースホルダー `{特記事項・ブロッカー・判断事項等}` を次の文言で **置換** する（追記ではなく置換。生プレースホルダーを残さない）:
  `ℹ️ 工程1: REQ-{CR}.md はテンプレートを元に文書番号・タイトル・作成日を自動記入した状態です。内容を編集し、編集が終わったら本ファイルの工程1のステータスを手動で ✅ 完了 に更新してください。`
- 次に実行すべきコマンド → `/xddp.02.analysis {CR}`
- All other steps → ⬜ 未着手.

### 6. Report in Japanese
Tell the user what was created and show the next command to run.
- If Step 3 が新規に `REQ-{CR}.md` を生成した場合（冪等性ガード非発火）:
  - `{CR_PATH}/01_requirements/REQ-{CR}.md` はテンプレートに文書番号・タイトル・作成日を自動記入したものです。内容を編集してから次のコマンドを実行してください。編集が終わったら `progress.md` の工程1のステータスも手動で `✅ 完了` に更新してください。
  - If `REQ_FILE` was set: `{コピー後のファイル名}` を `01_requirements/` に参照資料としてコピーし、`REQ-{CR}.md` から参照注記でリンクしました。
- If Step 3 の冪等性ガードが発火した場合（既存 `REQ-{CR}.md` を保持した場合）:
  - 既存の `REQ-{CR}.md` を検出したため上書きせず保持しました（テンプレートからの再生成・参照コピーの追記は行っていません）。内容を確認し、必要なら手動で編集してください。
If `xddp.config.md` was newly created, mention:
- Edit `REPOS:` to list all target repositories (1 entry = single-repo, multiple entries = multi-repo).
- `REPOS:` keys must be the actual repository folder names, not abbreviations (e.g., `api:` → NG, `tasksaas-api:` → OK).
- `cross` is reserved and cannot be used as a repository name.
If project-rulebook files were newly created, mention:
- `{XDDP_DIR}/project-rulebook.md` — fill with project-wide naming conventions and ADRs (run `/xddp.fill-rulebook` to auto-draft).
- If `len(REPOS_KEYS) >= 2`: `{XDDP_DIR}/project-rulebook-{repo}.md` — fill with per-repo coding conventions (run `/xddp.fill-rulebook {repo}` to auto-draft).
- `{XDDP_DIR}/project-rulebook-cross.md` (if created) — fill with cross-repo interface conventions (run `/xddp.fill-rulebook cross`).
If `{XDDP_DIR}/latest-specs/` was newly created, mention that it will be populated by `/xddp.11.specs` in per-repo subdirectories.
