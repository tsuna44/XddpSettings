---
description: XDDP CR クローズ処理: 各工程の気づきをバックログへ集約し、知見ログ（lessons-learned.md）を生成・更新してCRを完了する。「CRをクローズして」「知見をまとめて」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Close — CR Closeout & Knowledge Capture**.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Build `REPOS_MAP` (repo name → path).
Let `REPOS_KEYS` = list of all repository names. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).

Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.

`AFFECTED_REPOS` = all `REPOS_KEYS`.
Let `HAS_CROSS` = (IS_MULTI and any cross/ files exist under `{CR_PATH}/`).

## Step 0: Precondition Check

Read `{CR_PATH}/progress.md`.
If process step 15 (最新仕様書作成) is not ✅ 完了, instruct the user to run `/xddp.10.specs {CR}` first, then stop.

## Step C-Pre: All Repos Git Status Check

For each `{repo}` in `REPOS_KEYS`:
  Check git status of `{REPOS_MAP[repo]}` (run `git -C {path} status --short`).
  If uncommitted changes exist:
  > ⚠️ {repo} に未コミット変更があります。コミット後に close を実行することを推奨します。

Tell the user:
> 全リポジトリの確認が完了しました。続行しますか？ [続行 / 中止]
(警告があっても続行は可能。意図的なワークスペース設定変更等であれば無視してよい。)

Wait for user to choose 続行 before proceeding.

## Step A: Collect Insight/Proposal Memos

Read the following files (those that exist) and extract all content from their "気づき・提案メモ" sections:

```
Target files:
- {CR_PATH}/01_requirements/ (all .md)
- {CR_PATH}/02_analysis/ANA-{CR}.md
- {CR_PATH}/03_change-requirements/CRS-{CR}.md
- {for each repo in AFFECTED_REPOS: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md}
- {if HAS_CROSS: {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md}
- {for each repo in AFFECTED_REPOS:
    - {CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md （exists の場合）
    - {CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-A.md （exists の場合）
    - {CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-B.md （exists の場合）
    - {CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-C.md （exists の場合）
  }
- {if HAS_CROSS: {CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md}
- {for each repo in AFFECTED_REPOS: {CR_PATH}/06_design/{repo}/CHD-{CR}.md}
- {if HAS_CROSS: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md}
- {for each repo in AFFECTED_REPOS: {CR_PATH}/07_coding/CODING-{CR}-{repo}.md}
- {for each repo in AFFECTED_REPOS: {CR_PATH}/08_code-review/VERIFY-{CR}-{repo}.md}
- {if HAS_CROSS: {CR_PATH}/08_code-review/VERIFY-{CR}-cross.md}
- {for each repo in AFFECTED_REPOS: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md}
- {for each repo in AFFECTED_REPOS: {CR_PATH}/10_test-results/{repo}/TRS-{CR}-*.md}
- {if HAS_CROSS: {CR_PATH}/10_test-results/cross/TRS-{CR}-*.md}
```

**latest-specs からの気づきメモ収集（新構造対応）:**
以下のパターンでファイルを収集する（気づきメモセクションを持つファイルのみ対象）:
- `{XDDP_DIR}/latest-specs/{repo}/**/*.md`（REPOS_KEYS の各 repo）
- `{if HAS_CROSS: {XDDP_DIR}/latest-specs/cross/**/*.md}`
- `{XDDP_DIR}/latest-specs/system/**/*.md`（IS_MULTI / HAS_CROSS の値によらず常に対象）

**気づきメモなしファイルの除外フィルター（コンテキスト圧迫防止）:**
以下のファイル名パターンは気づきメモセクションを持たないため収集対象から除外する:
- `*-seq.md`（シーケンス図ファイル）
- `schema.md`（インタフェーススキーマ定義）
- `crud.md`（データアクセスマトリクス）
- `dfd.md`（データフロー図）

**気づきメモありファイルの収集対象（上記除外後の残り）:**
`spec.md`・`state-machine.md`・`structure.md`・`architecture.md`・`data-model.md`・インタフェース `spec.md`（`cross/interfaces/*/spec.md`）・`description.md`（ユースケース記述）

旧形式ファイル（例: `latest-specs/{repo}/auth-spec.md`）が残存する移行期は旧ファイルもヒットするため気づきメモが一時的に重複収集される可能性があるが、これは移行期の意図的な動作として許容する（旧ファイルの気づきを取りこぼさないため）。重複エントリの除去は Step B のバックログ追記時に重複チェックとして処理する。

Compile all extracted entries into a list with source file and action plan.

## Step B: Update Improvement Backlog

Read `{XDDP_DIR}/improvement-backlog.md`. If not exists, create from template.

From insights in Step A, append `IDEA-{NNN}` entries for items NOT "今回対応".

**Append `repo:` field to each IDEA entry using this auto-detection logic:**
- Insight from `{CR_PATH}/06_design/{repo}/CHD-{CR}.md` or `{repo}/` related files → `repo: {repo-name}`
- Insight about inter-repo interfaces / cross-repo flows → `repo: cross`
- Insight affecting all repos equally (e.g., test framework change) → `repo: 全リポジトリ`
- Difficult to determine → `repo: unknown` (flag in closeout report as "要確認 IDEA")

Entry format:
```markdown
### IDEA-{NNN}：{タイトル}
**repo:** {repo名 or cross or 全リポジトリ}（{判定根拠、例: CHD/repo-a の変更ファイルに関連}）
**カテゴリ:** {カテゴリ}
...
```

Update summary table. Flag any `repo: unknown` entries in closeout report.

## Step C: Generate/Update Lessons Learned Log

<!-- lessons-learned 二層構造メモ（実装コメント）:
  Layer 1: {XDDP_DIR}/lessons-learned.md
    - 作業中の全CR横断・全リポジトリ混在の知見蓄積ファイル
    - xddp.02.analysis Step A0 / xddp.05.arch Step A0 で参照（現在進行形の知見として使用）
    - xddp.close Step C3 でリポジトリ別に分類して Layer 2 へ昇格
  Layer 2: {DOCS}/{repo}/knowledge/lessons-learned.md
    - クローズ済み CR 由来のリポジトリ別・永続知見
    - xddp.02.analysis Step 0 で参照（権威的・安定した知見として使用）
  二重管理ではなく「作業中の混在参照（高鮮度）」と「クローズ後の分類済み参照（高精度）」の役割分担。-->

Read `{XDDP_DIR}/lessons-learned.md`. If not exists, create from template.

Extract `LL-{NNN}` entries applicable to future CRs.

### Knowledge Extraction Perspectives

(same as before — requirements analysis, architecture/design, implementation/testing, process)

### Entry Format

```markdown
### LL-{NNN}：{タイトル}

**CR：** {CR番号} ／ **工程：** {工程名} ／ **repo：** {repo名 or cross} ／ **タグ：** {#タグ}

**発生状況：**  
{どんな場面・判断でこの知見が生まれたか（1〜2文）}

**学んだこと：**  
{具体的な知見・教訓}

**次回への適用：**  
- {チェックポイント1}
- {チェックポイント2}

---
```

**Auto-assign `repo:` field to each LL entry:**
- Related to code changes in a specific `{repo}` → `repo: {repo-name}`
- Related to inter-repo interface or cross-repo flow → `repo: cross`
- Difficult to determine → `repo: unknown` (flag in closeout report as "要確認 LL"; do NOT promote to knowledge hub)

After adding entries, append one row to the "エントリ一覧" table and update `最終更新CR` to {CR}.

**ファイルサイズポリシー（アーカイブ提案）:**
Count the total number of `### LL-` heading lines in `{XDDP_DIR}/lessons-learned.md`.
Let `total` = count of `### LL-` lines.
If total > 100:
  Tell the user:
  > ⚠️ lessons-learned.md のエントリ数が {total} 件に達しました（推奨上限: 100 件）。
  > 読み込み時のコンテキスト消費量増大・検索精度低下を防ぐため、古いエントリのアーカイブを推奨します。
  >
  > アーカイブ手順（手動）:
  > 1. 古い LL エントリを `{XDDP_DIR}/lessons-learned-archive-{YYYY}.md` に移動する
  > 2. メインファイルの「エントリ一覧」テーブルから移動分の行を削除する
  > 3. アーカイブファイルにも同形式の「エントリ一覧」テーブルを追加する
  >
  > 続行する場合はそのまま Enter を押してください。
  Wait for user to press Enter (allow continue without action).
  （自動アーカイブは行わない。次回 CR クローズ時も同様の警告が出る。）

## Step C0: Pre-close Sync (Parallel-CR Support)

### 1. Source Code Sync Check
- Run `git fetch origin` to get the latest remote state.
  - If fetch fails: display error and ask user 続行/中止.
- Run `git log HEAD..origin/main --oneline` to check for un-merged remote commits.
- If un-merged commits exist → prompt user to run `git pull`.

### 2. {DOCS_DIR}/ Sync
Check whether `{DOCS}` is a git repository and run `git -C {DOCS} pull` if so.
If not git-managed: display warning and ask user 続行/中止.

### 3. Pull Baseline into latest-specs/
- Execute only if `{DOCS}/{repo}/specs/` exists for any affected repo.
- Read the "工程15 更新仕様書ファイル一覧" section from `{CR_PATH}/progress.md` to identify protected files.
- For each `{repo}` in `AFFECTED_REPOS`:
  - If `{DOCS}/{repo}/specs/` exists: copy any non-protected files to `{XDDP_DIR}/latest-specs/{repo}/`.
- If `HAS_CROSS` and `{DOCS}/cross/specs/` exists: copy non-protected cross/ files to `{XDDP_DIR}/latest-specs/cross/`.
- **`system/` ディレクトリの取り込み（IS_MULTI / HAS_CROSS の値によらず常に実行）:**
  - If `{DOCS}/system/specs/` exists: copy any non-protected files to `{XDDP_DIR}/latest-specs/system/`.
  - `{DOCS}/system/specs/` が存在しない場合は取り込みをスキップする（初回は存在しないため）。
  ※ `system/` はリポジトリ横断の概念のため AFFECTED_REPOS ループの外側（`HAS_CROSS` 処理と同階層の独立ブロック）として配置する。
  ※ シングルリポジトリ（IS_MULTI=false）でも `system/use-cases/` が生成された場合は処理対象となる。

### 4. Detect conflicts with concurrent CR promotions (human decision)

**PROTECTED_FILES の取得:**
Read the "工程15 更新仕様書ファイル一覧" section from `{CR_PATH}/progress.md` → `PROTECTED_FILES` list.
(If this section is absent, skip the rest of Step C0-4 and continue.)

`PROTECTED_FILES` の各エントリは `{XDDP_DIR}` からの相対パス形式で記録されている
（例: `latest-specs/{repo}/overview/architecture.md`）。
パスの先頭が `latest-specs/` で始まることを前提とする（xddp.10.specs Step DONE の記録形式）。

**git pull で取り込まれた変更を使った競合検出:**
DOCS が git 管理されていない場合（Step C0-2 で git pull がスキップされた場合）: 競合検出をスキップして続行。

Run `git -C {DOCS} diff --name-only ORIG_HEAD HEAD`.
(ORIG_HEAD は Step C0-2 の `git -C {DOCS} pull` によってセットされる。)
- このコマンドが失敗する場合、または ORIG_HEAD が存在しない場合（pull で何も取り込まれなかった場合）: 競合なしとみなしてスキップして続行。
- 注意: `ORIG_HEAD` は `git pull` 以外（`git merge`/`git rebase`/`git reset` 等）でも更新される。このコマンドは Step C0-2 の `git pull` 直後に連続実行することを前提としており、Step C0-2 内での連続実行設計によって stale な ORIG_HEAD 参照リスクを最小化する。

Let `PULLED_FILES` = git pull によって DOCS に取り込まれたファイルの一覧（DOCS ルートからの相対パス）。

**競合候補の特定:**
For each `F` in `PROTECTED_FILES`:
  Convert F from `{XDDP_DIR}`-relative to DOCS-relative path using the promotion mapping:
    - `latest-specs/{repo}/{path}` → `{repo}/specs/{path}`
    - `latest-specs/cross/{path}`  → `cross/specs/{path}`
    - `latest-specs/system/{path}` → `system/specs/{path}`
  If the converted path is in `PULLED_FILES` → mark as "競合候補".

Collect all "競合候補" into `OVERLAP_FILES`.

If `OVERLAP_FILES` is empty: continue to Step C2 without prompting.

If `OVERLAP_FILES` is non-empty:
  Tell the user:
  > 以下のファイルは Step C0-2 の git pull 中に他の CR によって更新されており、今回 CR の変更と競合しています。
  >
  > | ファイル |
  > |---|
  > {for each file in OVERLAP_FILES: | `{file}` |}
  >
  > **A（現状維持で続行）:** 取り込まれた内容と今回 CR の変更がそのまま混在します。
  >   軽微な競合や今回 CR とは無関係なモジュールの変更であれば通常は A で問題ありません。
  >   「A」と入力してください。
  >
  > **B（xddp.10.specs を再実行してから続行）:** 最新の SPO・CHD・CRS を反映した仕様書に
  >   再生成します。完了後に `/xddp.close {CR}` を再実行してください。
  >   「B」と入力してください。

  Wait for user response.
  - A: continue to Step C2.
  - B: update `{CR_PATH}/progress.md`（xddp.close 状態 → ⏸ 中断, 詳細ステップ → `Step C0-4: xddp.10.specs 再実行待ち`）; instruct user to run `/xddp.10.specs {CR}` and then re-run `/xddp.close {CR}`; then stop.
  ※ xddp.close の再実行は Step C0-1（git fetch・DOCS_DIR sync）からやり直す設計（意図的）。再実行時に Step C0-4 を再度評価するが、直前に xddp.10.specs を実行済みであれば git pull で取り込まれる他 CR の変更は解消されているため A を選択して続行できる。

## Step C2: Promote Approved Specs → DOCS_DIR (per repo + cross/ + system/)

**Identify files:**
Read "工程15 更新仕様書ファイル一覧" from `{CR_PATH}/progress.md` (reference only).
Promote **all files** under `{XDDP_DIR}/latest-specs/**` (Step C0-3 already pulled other CRs' changes).
※ glob を `latest-specs/**` に統一することで新旧構造の双方を包含する。

**Per-repo promotion:**
For each `{repo}` in `AFFECTED_REPOS`:
- Copy `{XDDP_DIR}/latest-specs/{repo}/` → `{DOCS}/{repo}/specs/` (create if absent)

**cross/ promotion:**
If `HAS_CROSS` and `{XDDP_DIR}/latest-specs/cross/` exists:
- Create `{DOCS}/cross/specs/` if absent.
- Copy `{XDDP_DIR}/latest-specs/cross/` → `{DOCS}/cross/specs/`

**system/ promotion（IS_MULTI / HAS_CROSS の値によらず常に実行）:**
If `{XDDP_DIR}/latest-specs/system/` exists:
- Create `{DOCS}/system/specs/` if absent.
- Copy `{XDDP_DIR}/latest-specs/system/` → `{DOCS}/system/specs/`
※ シングルリポジトリでも `system/use-cases/` が生成された場合は昇格する。
※ IS_MULTI / HAS_CROSS 非依存であることを本コメントで明記する。
※ この C0-3 取り込みと C2 昇格の対称性により、初回は C0-3 スキップ・C2 で新規作成となる。

**削除伝播（system/ ユースケース）:**
`{DOCS}/system/specs/use-cases/` 配下のディレクトリを列挙する。
`{XDDP_DIR}/latest-specs/system/use-cases/` に対応するディレクトリが存在しないものを「削除候補」として検出する。
削除候補が存在する場合はユーザーに提示して削除確認を求める（自動削除はしない）。
※ xddp.10.specs Step UC で廃止 UR 処理によりユーザーが削除確認済みの場合でも `{DOCS}` 側の削除は本ステップが担う。

**削除伝播（repo/ モジュールディレクトリ）:**
For each `{repo}` in `AFFECTED_REPOS`:
  `{DOCS}/{repo}/specs/` 配下のモジュールディレクトリを列挙する（`overview/` 除く）。
  `{XDDP_DIR}/latest-specs/{repo}/` に対応するモジュールディレクトリが存在しないものを「削除候補」として検出する。
  削除候補が存在する場合はユーザーに提示して削除確認を求める（自動削除はしない）。

**AI_INDEX.md update（新構造対応・全セクション upsert）:**
Read `{DOCS}/AI_INDEX.md` (create from skeleton if absent).

1. **「ユースケース一覧」セクション（upsert）:**
   `{XDDP_DIR}/latest-specs/system/use-cases/` 配下の各 `description.md` を Read する。
   フロントマターの `related-modules`（`module:` キーではなく `related-modules:` リストを使用）・
   `last-updated-cr` および description.md の「目的・ゴール」1行要約を取得する。
   ユースケース名をキーにセクション行を upsert する。
   `system/use-cases/` が存在しない場合はこのセクションをスキップする。
   テーブル形式:
   | ユースケース | 目的（1行） | description | 関連モジュール | 最終更新CR |
   |---|---|---|---|---|
   | {usecase-kebab} | {1行説明} | [description.md](system/specs/use-cases/{usecase-kebab}/description.md) | {module1}, {module2} | CR-{NNN} |

2. **「リポジトリ別仕様書」セクション（既存 upsert を拡張）:**
   For each `{repo}` in `AFFECTED_REPOS`: upsert テーブル行:
   | [{repo}]({repo}/specs/) | v{X.Y}（最終更新CR: {CR}） | [overview]({repo}/specs/overview/) | {N} モジュール | CR-{CR} |
   モジュール数 = `{XDDP_DIR}/latest-specs/{repo}/` 直下のディレクトリ数（`overview/` 除く）。

3. **「モジュール別最新仕様」セクション（upsert）:**
   今回 CR で生成・更新した全モジュールの行を upsert（`{repo}/{module}` の組み合わせをキー）。
   各列（spec・structure・state）について、ファイルが存在する場合のみリンクを記載、なければ `—`。
   テーブル形式:
   | リポジトリ | モジュール | spec | structure | state | 最終更新CR |
   |---|---|---|---|---|---|
   | {repo} | {module} | [spec.md]({repo}/specs/{module}/spec.md) | [structure.md](...) | — | CR-{NNN} |

4. **「クロスインタフェース一覧」セクション（IS_MULTI のみ・upsert）:**
   `{XDDP_DIR}/latest-specs/cross/interfaces/` 配下の各インタフェースの `spec.md` フロントマターから
   バージョン・last-updated-cr を取得し、インタフェース名をキーに upsert する。
   IS_MULTI への移行対応: 既存 AI_INDEX.md にセクションが存在しない状態で IS_MULTI=true となった場合は新規追加する。
   テーブル形式:
   | インタフェース | spec | schema | バージョン | 最終更新CR |
   |---|---|---|---|---|
   | {interface-kebab} | [spec.md](cross/specs/interfaces/{interface-kebab}/spec.md) | [schema.md](...) | v{X.Y.Z} | CR-{NNN} |

5. **「知識参照ガイド」セクション（初回のみ生成）:**
   `{DOCS}/AI_INDEX.md` に「## 知識参照ガイド」セクションが**存在しない場合のみ**生成する。
   既存の場合はスキップする。
   （理由: 参照先パターンはディレクトリ構造定数であり、CR ごとの更新は不要）

   生成する内容:

   ```markdown
   ## 知識参照ガイド

   > `{repo}` は `xddp.config.md` の `REPOS:` エントリ名が入るパターン表記（例: `repo-a`）。
   > 具体的なファイルは上記各テーブルのリンクを参照のこと。

   | 知りたいこと | 参照先パターン |
   |---|---|
   | 現在の機能仕様（What it does） | `{DOCS_DIR}/{repo}/specs/{module}/spec.md`（→「モジュール別最新仕様」テーブル） |
   | 変更要求・設計判断の根拠（Why it was changed） | `{DOCS_DIR}/{repo}/design/CRS-{CR}.md`（→「変更要求仕様書」テーブル） |
   | 過去の実装パターン・知見 | `{XDDP_DIR}/lessons-learned.md`（作業中）/ `{DOCS_DIR}/{repo}/knowledge/lessons-learned.md`（クローズ済み）<br>タグ検索例: `#方式検討` `#設計` `#コーディング` `#リスク` `#テスト` `#プロセス` |
   | プロジェクト規約・禁止事項 | `{XDDP_DIR}/project-rulebook.md` / `{XDDP_DIR}/project-rulebook-{repo}.md` |
   | テスト仕様 | → 上記「テスト仕様（TSP）」テーブルを参照 |

   > このセクションは初回 xddp.close 時に自動生成されます。知識ディレクトリ構造変更後に更新するには、このセクションを削除して xddp.close を再実行してください。
   ```

6. **「code-knowledge インデックス」セクション（upsert）:**

   For each `{repo}` in `AFFECTED_REPOS`:
     For each `{MODULE}` dir in `{DOCS}/{repo}/knowledge/code-knowledge/`:
       If `{MODULE}/constraints.md` exists:
         Add entry: "`{repo}/{MODULE}` 制約・注意事項 → `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`"
     If `_structures/` exists under `{DOCS}/{repo}/knowledge/code-knowledge/`:
       Add entry: "`{repo}` 構造体関連図 → `{DOCS}/{repo}/knowledge/code-knowledge/_structures/`"
     If `_constants/` exists under `{DOCS}/{repo}/knowledge/code-knowledge/`:
       Add entry: "`{repo}` 共有定数 → `{DOCS}/{repo}/knowledge/code-knowledge/_constants/`"
     If `_flows/` exists under `{DOCS}/{repo}/knowledge/code-knowledge/`:
       Add entry: "`{repo}` 機能間フロー → `{DOCS}/{repo}/knowledge/code-knowledge/_flows/`"
   If `IS_MULTI` and `{DOCS}/cross/knowledge/code-knowledge/` exists:
     For each `{MODULE}` dir under that path:
       If `{MODULE}/constraints.md` exists:
         Add entry: "`cross/{MODULE}` 制約・注意事項 → `{DOCS}/cross/knowledge/code-knowledge/{MODULE}/constraints.md`"
     If `_structures/` exists: Add entry: "`cross` 構造体関連図 → `{DOCS}/cross/knowledge/code-knowledge/_structures/`"
     If `_constants/` exists: Add entry: "`cross` 共有定数 → `{DOCS}/cross/knowledge/code-knowledge/_constants/`"
     If `_flows/` exists: Add entry: "`cross` 機能間フロー → `{DOCS}/cross/knowledge/code-knowledge/_flows/`"

   code-knowledge ディレクトリが DOCS 配下に一切存在しない場合はこのセクションをスキップする。

7. **「変更要求仕様書（CRS）ナビゲーション」セクション（upsert）:**

   For each `{repo}` in `AFFECTED_REPOS`:
     If `{CR_PATH}/03_change-requirements/CRS-{CR}.md` exists:
       Upsert row: "`{CR}` 変更要求仕様 → `{DOCS}/{repo}/design/CRS-{CR}.md`"
   If `HAS_CROSS` and `{CR_PATH}/03_change-requirements/CRS-{CR}.md` exists:
     Upsert row: "`{CR}` cross 変更要求仕様 → `{DOCS}/cross/design/CRS-{CR}.md`"

   CRS ファイルが存在しない場合はこのセクションをスキップする。
   （リンク先は Step C4 の昇格完了後に有効になる。Step C4 より前に書き込まれるが broken リンクは許容する）

**AI_INDEX.md サイズポリシー:**
`{DOCS}/AI_INDEX.md` が 500 行を超えた場合、最も更新が古いエントリ（`最終更新CR` が最も古い）から順に
「アーカイブ候補」として人に提示し、別ファイル（例: `{DOCS}/AI_INDEX-archive.md`）への移動を提案する。自動削除はしない。

**cross/ 破壊的変更チェック:**
If `HAS_CROSS`, read `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` "インタフェース変更サマリ".
If any entry has `breaking: true`:
- Add `⚠️ 破壊的変更あり（CR: {CR}）` annotation to the cross/ AI_INDEX.md row.
- Append breaking-change warning LL entries to ALL repos' lessons-learned:
  `LL entry: 破壊的インタフェース変更あり。{interface名}の旧バージョンへの依存コードを確認すること。`

**xddp.close の AFFECTED_REPOS に関する仕様メモ（実装コメント）:**
xddp.close の AFFECTED_REPOS = all REPOS_KEYS（全リポジトリ）である。
xddp.10.specs の AFFECTED_REPOS は「SPO が存在するリポジトリ＋CHD cross 影響リポジトリ」（全リポジトリより少ない可能性がある）。
xddp.close Step C2 はすべてのリポジトリを昇格するため、今回の CR で specout していないリポジトリの
latest-specs も `baseline_docs` に昇格されるが、これは「前回CRの内容を再昇格する」動作であり意図的に許容する。

**git コンフリクト発生時のガイダンス（DOCS_DIR が git 管理されている場合）:**
Step C2 でファイルをコピー後、DOCS_DIR に git コンフリクトが発生した場合の解決方針:
- **仕様書ファイル（`{repo}/specs/`・`cross/specs/`・`system/specs/`）:** 今回 CR の変更を優先する（`git checkout --ours`）。他 CR の変更が必要な場合は xddp.close を再実行後に手動マージする。
- **AI_INDEX.md:** テーブル行単位で統合する。同一キー（ユースケース名・リポジトリ名・モジュール名）を持つ行は最新 CR のものを採用する。行が重複する場合は最新 CR の行を残す。
- **lessons-learned / project-rulebook:** 追記型のファイルのため通常はコンフリクトが発生しにくいが、発生した場合はどちらの変更も保持して末尾に追記する（エントリは重複しないため安全にマージできる）。
- コンフリクト解決後は `git add` して `git commit` し、DOCS_DIR のリモートにプッシュする。

> **注:** この競合リスクを根本的に防ぐには DOCS_DIR への書き込みを逐次化する（一度に 1 つの CR のみ `/xddp.close` を実行する）運用が最も確実です。

## Step C3: Promote Lessons Learned Log (per repo + cross/)

**repo: {repo-name} entries** → append to `{DOCS}/{repo}/knowledge/lessons-learned.md`
**repo: cross entries** → append to `{DOCS}/cross/knowledge/lessons-learned.md` (create if HAS_CROSS and not exists)
**repo: unknown entries** → do NOT promote; list in closeout report as "要確認 LL"

For each file, append only entries for this CR at the end.

## Step C3.5: Apply Lessons to project-rulebook files (repo-specific routing)

**Section mapping:**
| Target tag / content | Target section | 書き込み方針 |
|---|---|---|
| `#方式検討` `#設計` — design patterns (ADR) | Section 5 (ADR・設計判断記録) | **追記（Append）** — 変更履歴として保持 |
| `#コーディング` — implementation patterns | Section 4 (既存パターン・慣習) | **テーマ追記** — 同一 `### {テーマ}` があれば既存ブロック末尾に追記、なければ新規サブセクション追加 |
| `#テスト` — test patterns | Section 4 (テストパターン) | **テーマ追記** — 同一 `### {テーマ}` があれば既存ブロック末尾に追記、なければ新規サブセクション追加 |
| NG patterns / prohibitions | Section 6 (禁止事項・注意事項) | **Upsert（置換）** — 同一識別キーワードのルール行群があれば置換、なければ末尾追記 |
| `#プロセス` `#要求分析` `#仕様定義` | Not mapped | — |

> **注: `repo: cross` の LL エントリには上記 Upsert は適用しない。**
> `project-rulebook-cross.md` のセクション構成は repo テンプレートと異なるため、
> cross 宛ての書き込みは現行の Append 動作を維持する。

**Upsert の判定キーと置換範囲:**  
実際の LL フォーマット（フィールド: タイトル・CR・工程・repo・タグ・発生状況・学んだこと・次回への適用）には「対象」フィールドは存在しない。  
AI は LL エントリの「学んだこと」・「次回への適用」・タグから対象テーマ・禁止事項キーワードを導出し、以下の方針で Upsert を判定する。

**Section 4（コーディング規約・既存パターン / テストパターン）:**  
- 書き込み単位: `### {テーマ}` サブセクション（見出し行＋コードブロック）  
- Upsert キー: AI が導出したテーマ見出し（例: `エラーハンドリング`、`テストパターン`）  
- 既存テーマ一致: `### {テーマ}` が Section 4 内に存在する場合 → 既存コードブロック末尾に新コメント行を追記（重複行は追加しない）  
- 一致なし: Section 4 末尾に新 `### {テーマ}` ブロックを追加  

**Section 6（禁止事項・注意事項）:**  
- 書き込み単位: コードブロック内の個別ルール行群（`# ❌`/`# ⚠️` 行から次のルール行または空行まで）  
- Upsert キー: AI が LL エントリから導出した禁止事項の識別キーワード  
- 既存ルール一致: 同一識別キーワードを含む `# ❌/⚠️` 行が存在する場合 → 該当ルール行群をまるごと置換  
- 一致なし: コードブロック末尾に新ルール行群を追記  

追記・置換後は `（出典: LL-{NNN}, {CR}）` サフィックスを末尾コメントに付与する。

**Repository routing:**
- LL entry with `repo: {repo-name}` → append to `{XDDP_DIR}/project-rulebook-{repo}.md` (create if absent from template)
- LL entry with `repo: cross` → append to `{XDDP_DIR}/project-rulebook-cross.md` (create if absent from template)
- LL entry with `repo: unknown` → skip (not mapped)

(Dedup check, writing style matching.)

Append one row to Section 7 (変更履歴) of each modified steering file.

## Step C3.6: code-knowledge 昇格

For each `{repo}` in `AFFECTED_REPOS`:

  ### per-repo SPO Section 5.6（非機能特性・実装制約の観察）から昇格:
  Let `SPO_FILE` = `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`
  If `SPO_FILE` exists:
    For each entry in SPO Section 5.6 where 影響度 in [高, 中]:
      Let `MODULE` = 対象ファイル/識別子から推定されるモジュール名（ファイルパスの第1〜2階層ディレクトリ名。推定不可な場合は `"_general"` を使用）
      Upsert entry to `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`
        → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-constraints-template.md`
        → セクション: "パフォーマンス・非機能特性"
        → 出典フィールド: `{CR}`

  ### LL #リスク / #見落とし タグエントリから昇格:
  If `{XDDP_DIR}/lessons-learned.md` exists:
    For each LL entry tagged `#リスク` or `#見落とし`
      where entry contains specific reference to code / interface / library:
        Let `MODULE` = 対象モジュール名（推定不可な場合は `"_general"` を使用）
        Upsert entry to `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`
          → セクション: "既知の制約・落とし穴"

  ### LL #仕様定義 タグエントリから昇格:
  For each LL entry tagged `#仕様定義`:
    If entry contains "〜を前提とする" / "〜という制約がある" / "仕様上の制約"
       OR (コードへの具体的言及（ファイル名・関数名・型名）が含まれる AND 制約・注意点・落とし穴・前提の文脈を持つ):
      Upsert to `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`
        → セクション: "仕様上の暗黙の前提"

  ### per-repo SPO Section 3（シーケンス図）機能間フローから昇格:
  If `SPO_FILE` exists:
    For each figure in SPO Section 3 where 複数モジュールのアクターを含むシーケンス図（機能間フロー）:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
      Let `FLOW_NAME` = SPO 図タイトルから派生（スペース→ハイフン・小文字）
      Upsert to `{DOCS}/{repo}/knowledge/code-knowledge/_flows/{DOMAIN}-{FLOW_NAME}-sequence.md`
        → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-flows-sequence-template.md`

  ### per-repo SPO Section 4.2（DFD）から昇格:
  If `SPO_FILE` exists and SPO Section 4.2 に DFD が存在する場合:
    Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
    Let `FLOW_NAME` = DFD タイトルから派生（スペース→ハイフン・小文字）
    Upsert to `{DOCS}/{repo}/knowledge/code-knowledge/_flows/{DOMAIN}-{FLOW_NAME}-dfd.md`
      → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-flows-dfd-template.md`

  ### per-repo TRS 不具合エントリから昇格:
  For each TRS file in `{CR_PATH}/10_test-results/{repo}/TRS-{CR}-*.md`:
    If TRS に `## 3. NG詳細` セクションが存在し、かつ `### NG-` で始まるエントリが1件以上ある場合:
      For each 不具合エントリ（`### NG-NNN` ブロック）where
        「原因分析」フィールドにファイルパス（`/` 区切りまたは `.py`・`.ts`・`.c` 等の拡張子を含む文字列）
        または関数名・メソッド名（`()` を含む文字列）が記載されている:
          Let `MODULE` = 対象ファイル/識別子から推定されるモジュール名（ファイルパスの第1〜2階層ディレクトリ名。推定不可な場合は `"_general"` を使用）
          Let `UPSERT_KEY` = `CR-{CR} / NG-{NNN}`（例: `CR-2026-002 / NG-001`）
          Upsert entry to `{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/constraints.md`
            → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-constraints-template.md`
            → セクション: "既知の制約・落とし穴"
            → 内容: 不具合の概要・修正後の注意点・再発条件
            → **Upsertキー:** constraints.md の各 `[CK-NNN]` エントリの `出典` フィールドに
              `{UPSERT_KEY}` が含まれるか検索する。
              - 一致エントリが存在する場合: `[CK-NNN]` 番号を維持したままエントリ全体を置換
              - 一致なしの場合: 新規 `[CK-NNN]` エントリを追加（`NNN` = 既存最大番号 + 1、
                ファイルが存在しない場合は `001`）
            → 出典フィールド: `CR-{CR} / NG-{NNN} / 発見日: {TODAY}`

If `IS_MULTI`:
  ### cross SPO §5（リポジトリ間共有定数・列挙値）から昇格:
  If `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` exists:
    For each entry in §5 where 共有定数 / 列挙値が検出された場合:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を使用）
      Upsert entry to `{DOCS}/cross/knowledge/code-knowledge/_constants/{DOMAIN}-constants.md`
        → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-constants-template.md`

  ### cross SPO §6（リポジトリ間共有データ型関連図）から昇格:
  If cross SPO §6 に共有データ型が記録されている場合:
    Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を使用）
    Upsert diagram to `{DOCS}/cross/knowledge/code-knowledge/_structures/{DOMAIN}-relations.md`
      → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-structures-template.md`

  ### cross SPO §3（リポジトリ間シーケンス図）から昇格:
  If `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` exists and §3 にリポジトリ間シーケンス図がある場合:
    For each リポジトリ間シーケンス図 in cross SPO §3:
      Let `DOMAIN` = ドメイン名（推定できない場合は `"shared"` を暫定使用）
      Let `FLOW_NAME` = 図タイトルから派生（スペース→ハイフン・小文字）
      Upsert to `{DOCS}/cross/knowledge/code-knowledge/_flows/{DOMAIN}-{FLOW_NAME}-sequence.md`
        → テンプレート: `~/.claude/skills/xddp.close/templates/code-knowledge-flows-sequence-template.md`

  ※ _flows/ 昇格時の共通注意事項:
    - 機能間フロー識別（複数モジュールをまたぐか）の判定は AI が行うが、最終確認は人が実施すること
    - 初回生成時は {domain} 名を人が確認・修正すること（命名一貫性のため）

## Step C4: Promote Change Requirements Spec → DOCS_DIR (per repo + cross/)

CRS は変更の根拠・要求を記録した唯一の永続成果物として昇格する。
DSN・CHD・CODING・VERIFY は作業中の過程成果物であり、git 履歴・lessons-learned・latest-specs で代替できるため昇格しない。

For each `{repo}` in `AFFECTED_REPOS`:
  Let `DESIGN_TARGET` = `{DOCS}/{repo}/design/`.
  Create `{DESIGN_TARGET}` if absent.
  If `{CR_PATH}/03_change-requirements/CRS-{CR}.md` exists:
    copy to `{DESIGN_TARGET}/CRS-{CR}.md`

If `HAS_CROSS`:
  Create `{DOCS}/cross/design/` if absent.
  If `{CR_PATH}/03_change-requirements/CRS-{CR}.md` exists:
    copy to `{DOCS}/cross/design/CRS-{CR}.md`

Update AI_INDEX.md "変更要求仕様書（CRS）ナビゲーション" table (upsert per repo + cross).

## Step C5: Promote Test Specs and Results → DOCS_DIR (per repo + cross/)

For each `{repo}` in `AFFECTED_REPOS`:
  Let `TEST_TARGET` = `{DOCS}/{repo}/test/`.
  If `{CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md` exists: copy to `{TEST_TARGET}/TSP-{CR}.md`
  For each TRS file in `{CR_PATH}/10_test-results/{repo}/TRS-{CR}-*.md`: copy to `{TEST_TARGET}/`

If `HAS_CROSS`:
  Create `{DOCS}/cross/test/` if absent.
  If `{CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md` exists: copy to `{DOCS}/cross/test/`
  For each TRS in `{CR_PATH}/10_test-results/cross/TRS-{CR}-*.md`: copy to `{DOCS}/cross/test/`

Update AI_INDEX.md "テスト仕様（TSP）" columns (upsert).

## Step C6: Promote project-rulebook files → DOCS_DIR

`{XDDP_DIR}/project-rulebook.md` → `{DOCS}/project-rulebook.md` (overwrite)

For each `{repo}` in `REPOS_KEYS`:
  If `{XDDP_DIR}/project-rulebook-{repo}.md` exists:
    `{XDDP_DIR}/project-rulebook-{repo}.md` → `{DOCS}/{repo}/project-rulebook.md`

If `HAS_CROSS` and `{XDDP_DIR}/project-rulebook-cross.md` exists:
  Create `{DOCS}/cross/` if absent.
  `{XDDP_DIR}/project-rulebook-cross.md` → `{DOCS}/cross/project-rulebook.md`

Update AI_INDEX.md "共通知識" table (upsert per-repo and cross entries).

## Step C7: improvement-backlog を DOCS_DIR に昇格

If `{XDDP_DIR}/improvement-backlog.md` exists:
  Copy `{XDDP_DIR}/improvement-backlog.md` → `{DOCS}/improvement-backlog.md`
  （追記ではなく上書きコピー。`{XDDP_DIR}` 側が master）
  Log: "improvement-backlog.md を `{DOCS}/improvement-backlog.md` に昇格済み"

※ ファイルが存在しない場合はスキップ。
※ `{XDDP_DIR}` 側の improvement-backlog.md は削除しない（master として維持）。

## Step D: Human Review Gate

Tell the user:
> ✅ クローズ処理が完了しました。内容を確認してください。
>
> **生成・更新した資料：**
> - 改善バックログ: `improvement-backlog.md`（追加 {n} 件。要確認IDEA: {k} 件）
> - 知見ログ: `lessons-learned.md`（追加 {n} 件。要確認LL: {k} 件）
{for each repo in AFFECTED_REPOS:}
> - {repo}: 仕様書 `{DOCS}/{repo}/specs/` / 設計書 `{DOCS}/{repo}/design/` / テスト `{DOCS}/{repo}/test/` / 知見 `{DOCS}/{repo}/knowledge/` に昇格
> - {repo}: `project-rulebook-{repo}.md` を `{DOCS}/{repo}/project-rulebook.md` に昇格
{if HAS_CROSS:}
> - cross: 仕様書・設計書・テスト・知見を `{DOCS}/cross/` に昇格（インタフェース破壊的変更: {あり/なし}）
> - cross: `project-rulebook-cross.md` を `{DOCS}/cross/project-rulebook.md` に昇格
>
> **要確認 LL（repo: unknown — 昇格スキップ）:**
> {list of unknown LL entries, or "なし"}
>
> **要確認 IDEA（repo: unknown）:**
> {list of unknown IDEA entries, or "なし"}
>
> **修正が必要な場合：** 直接ファイルを編集してください
>
> 確認が完了したら「**クローズ完了**」と入力してください。

Wait for user to confirm.

## Step E: Mark CR Complete

Read `{CR_PATH}/progress.md`.
Append at the end:

```
## CR クローズ

- **クローズ日：** {TODAY}
- **改善バックログ追加：** {n} 件（要確認: {k} 件）
- **知見ログ追加：** {n} 件（要確認: {k} 件）
- **ステータス：** ✅ 完了・クローズ済み
```

## Step F: Report in Japanese

Report: IDEA/LL entries added per repo, main lesson titles, breaking-change alerts (if any).

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.close.md`.
