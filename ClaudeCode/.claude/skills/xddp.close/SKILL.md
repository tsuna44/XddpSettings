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

## Step C2, C3, C4, C5, C6, C7: Promote All Artifacts → DOCS_DIR

Update `{CR_PATH}/progress.md` xddp.close 状態 → 🔄 進行中, 詳細ステップ → `Step C: 昇格処理中`.

**Agent tool** `subagent_type=xddp-close-promote-agent`:
```
CR_NUMBER: {CR}
CR_PATH: {CR_PATH}
XDDP_DIR: {XDDP_DIR}
DOCS: {DOCS}
REPOS_MAP: {REPOS_MAP}
REPOS_KEYS: {REPOS_KEYS}
AFFECTED_REPOS: {AFFECTED_REPOS}
HAS_CROSS: {HAS_CROSS}
IS_MULTI: {IS_MULTI}
TODAY: {TODAY}
LESSONS_FILE: {XDDP_DIR}/lessons-learned.md
OUTPUT_FILE: {CR_PATH}/pending-items/PENDING-PROMOTE-{CR}.md
```

Wait for completion. エージェントは以下を OUTPUT_FILE に書き込む:
- `リポジトリ別処理結果一覧`（AFFECTED_REPOS 各 repo について C2/C4/C5/C6 が成功したか・失敗した場合は理由。一部 repo のみ失敗した場合の検出に使う）
- `要確認LL一覧`（Step C3 の repo:unknown スキップ分）
- `破壊的変更フラグ・対象インタフェース一覧`（Step C2 の cross/ チェック結果）
- `削除候補一覧`（Step C2 の system/use-cases・repo モジュールディレクトリの削除伝播。人の削除確認待ち）
エージェントは内部でユーザーへの削除確認を行わない（OUTPUT_FILE に保留事項として書き込むのみ）。
オーケストレーターは Agent tool 完了後に `{CR_PATH}/pending-items/PENDING-PROMOTE-{CR}.md` を Read し、
内容を Let `PROMOTE_RESULT` に保持し、Step D で人に提示する。

## Step C3.5, C3.6: Knowledge Capture

**Agent tool** `subagent_type=xddp-close-knowledge-agent`:
```
CR_NUMBER: {CR}
CR_PATH: {CR_PATH}
XDDP_DIR: {XDDP_DIR}
DOCS: {DOCS}
REPOS_MAP: {REPOS_MAP}
AFFECTED_REPOS: {AFFECTED_REPOS}
HAS_CROSS: {HAS_CROSS}
IS_MULTI: {IS_MULTI}
TODAY: {TODAY}
LESSONS_FILE: {XDDP_DIR}/lessons-learned.md
TRS_PATTERN: {CR_PATH}/10_test-results/{repo}/TRS-{CR}-*.md
OUTPUT_FILE: {CR_PATH}/pending-items/PENDING-KNOWLEDGE-{CR}.md
```

Wait for completion. エージェントは `_domain名要確認一覧`（_flows/_constants/_structures 生成時の暫定ドメイン名）を
OUTPUT_FILE に書き込む（人の命名確認待ち。内部で対話しない）。
オーケストレーターは Agent tool 完了後に `{CR_PATH}/pending-items/PENDING-KNOWLEDGE-{CR}.md` を Read し、
内容を Let `KNOWLEDGE_RESULT` に保持し、Step D で人に提示する。

## Step D: Human Review Gate

Tell the user:
> ✅ クローズ処理が完了しました。内容を確認してください。
>
> **生成・更新した資料：**
> - 改善バックログ: `improvement-backlog.md`（追加 {n} 件。要確認IDEA: {k} 件）
> - 知見ログ: `lessons-learned.md`（追加 {n} 件。要確認LL: {k} 件）
{`PROMOTE_RESULT` の「リポジトリ別処理結果一覧」を repo ごとに参照する（AFFECTED_REPOS を単純にループするのではなく、
実際の処理結果を確認する。一部 repo が失敗している場合は誤って成功と報告しないこと）:}
{for each {repo}: {成功/失敗} in PROMOTE_RESULT のリポジトリ別処理結果一覧:}
> - {repo}: {成功の場合} 仕様書 `{DOCS}/{repo}/specs/` / 変更要求仕様書（CRS） `{DOCS}/{repo}/crs/` / テスト `{DOCS}/{repo}/test/` / 知見 `{DOCS}/{repo}/knowledge/` に昇格 / `project-rulebook-{repo}.md` を `{DOCS}/{repo}/project-rulebook.md` に昇格
> - {repo}: {失敗の場合} ⚠️ 昇格処理に失敗しました（{失敗ステップ名・理由}）。内容を確認してください
{if HAS_CROSS:}
> - cross: 仕様書・変更要求仕様書（CRS）・テスト・知見を `{DOCS}/cross/` に昇格（インタフェース破壊的変更: {PROMOTE_RESULT の破壊的変更フラグ}）
> - cross: `project-rulebook-cross.md` を `{DOCS}/cross/project-rulebook.md` に昇格
>
> **要確認 LL（repo: unknown — 昇格スキップ）:**
> {PROMOTE_RESULT の要確認LL一覧, or "なし"}
>
> **要確認 IDEA（repo: unknown）:**
> {list of unknown IDEA entries, or "なし"}
>
> **削除候補（人の削除確認待ち）:**
> {PROMOTE_RESULT の削除候補一覧, or "なし"}
>
> **ドメイン名要確認（_flows/_constants/_structures の暫定ドメイン名）:**
> {KNOWLEDGE_RESULT の _domain名要確認一覧, or "なし"}
>
> **修正が必要な場合：** 直接ファイルを編集してください
>
> 確認が完了したら「**クローズ完了**」と入力してください。

Wait for user to confirm.

ユーザーが削除を選択した削除候補（`PROMOTE_RESULT` の削除候補一覧より）について、
オーケストレーターがディレクトリ削除をファイル操作として直接実行する（エージェントを再呼び出ししない）。

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
