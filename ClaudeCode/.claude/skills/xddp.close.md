---
description: XDDP CR クローズ処理: 各工程の気づきをバックログへ集約し、知見ログ（lessons-learned.md）を生成・更新してCRを完了する。「CRをクローズして」「知見をまとめて」などで起動する。
---

You are orchestrating **XDDP Close — CR Closeout & Knowledge Capture**.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md lookup done in xddp.common.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Build `REPOS_MAP` (repo name → path).
Let `REPOS_KEYS` = list of all repository names. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).

Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.

Identify `AFFECTED_REPOS`: read CRS "1.5 影響リポジトリ" section if present; otherwise use REPOS_KEYS.
Let `HAS_CROSS` = (IS_MULTI and any cross/ files exist under `{CR_PATH}/`).

## Step 0: Precondition Check

Read `{CR_PATH}/progress.md`.
If process step 15 (最新仕様書作成) is not ✅ 完了, instruct the user to run `/xddp.09.specs {CR}` first, then stop.

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
- {for each repo in AFFECTED_REPOS: {CR_PATH}/05_architecture/{repo}/DSN-{CR}.md}
- {if HAS_CROSS: {CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md}
- {for each repo in AFFECTED_REPOS: {CR_PATH}/06_design/{repo}/CHD-{CR}.md}
- {if HAS_CROSS: {CR_PATH}/06_design/cross/CHD-{CR}-cross.md}
- {for each repo in AFFECTED_REPOS: {CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md}
- {for each repo in AFFECTED_REPOS: {CR_PATH}/10_test-results/{repo}/TRS-{CR}-*.md}
- {if HAS_CROSS: {CR_PATH}/10_test-results/cross/TRS-{CR}-*.md}
```

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

### 4. Decide Whether to Regenerate Specs (human decision)
(Same logic as before — present overlap analysis and ask user.)

## Step C2: Promote Approved Specs → DOCS_DIR (per repo + cross/)

**Identify files:**
Read "工程15 更新仕様書ファイル一覧" from `{CR_PATH}/progress.md` (reference only).
Promote **all files** under `{XDDP_DIR}/latest-specs/` (Step C0-3 already pulled other CRs' changes).

**Per-repo promotion:**
For each `{repo}` in `AFFECTED_REPOS`:
- Copy `{XDDP_DIR}/latest-specs/{repo}/` → `{DOCS}/{repo}/specs/` (create if absent)

**cross/ promotion:**
If `HAS_CROSS` and `{XDDP_DIR}/latest-specs/cross/` exists:
- Create `{DOCS}/cross/specs/` if absent.
- Copy `{XDDP_DIR}/latest-specs/cross/` → `{DOCS}/cross/specs/`

**AI_INDEX.md update (upsert):**
Read `{DOCS}/AI_INDEX.md` (create if absent).
For each `{repo}` in `AFFECTED_REPOS`: upsert "リポジトリ別仕様書" table row:
| [{repo}]({repo}/specs/) | v{X.Y}（最終更新CR: {CR}） | [lessons-learned]({repo}/knowledge/lessons-learned.md) |

For `cross` (if HAS_CROSS):
| [cross](cross/specs/) | v{X.Y}（最終更新CR: {CR}）{if breaking_change: " ⚠️ 破壊的変更あり（CR: {CR}）"} | [lessons-learned](cross/knowledge/lessons-learned.md) |

**Interface breaking change check:**
If `HAS_CROSS`, read `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` "インタフェース変更サマリ".
If any entry has `breaking: true`:
- Add `⚠️ 破壊的変更あり（CR: {CR}）` annotation to the cross/ AI_INDEX.md row.
- Append breaking-change warning LL entries to ALL repos' lessons-learned:
  `LL entry: 破壊的インタフェース変更あり。{interface名}の旧バージョンへの依存コードを確認すること。`

## Step C3: Promote Lessons Learned Log (per repo + cross/)

**repo: {repo-name} entries** → append to `{DOCS}/{repo}/knowledge/lessons-learned.md`
**repo: cross entries** → append to `{DOCS}/cross/knowledge/lessons-learned.md` (create if HAS_CROSS and not exists)
**repo: unknown entries** → do NOT promote; list in closeout report as "要確認 LL"

For each file, append only entries for this CR at the end.

## Step C3.5: Apply Lessons to project-steering files (repo-specific routing)

**Section mapping** (same categories as before):
| Target tag / content | Append to |
|---|---|
| `#方式検討` `#設計` — design patterns | Section 3 (ADR) or Section 4 |
| `#コーディング` — implementation patterns | Section 4 (既存パターン・慣習) |
| `#テスト` — test patterns | Section 4 (テストパターン) |
| NG patterns / prohibitions | Section 5 (禁止事項・注意事項) |
| `#プロセス` `#要求分析` `#仕様定義` | Not mapped |

**Repository routing:**
- LL entry with `repo: {repo-name}` → append to `{XDDP_DIR}/project-steering-{repo}.md` (create if absent from template)
- LL entry with `repo: cross` → append to `{XDDP_DIR}/project-steering-cross.md` (create if absent from template)
- LL entry with `repo: unknown` → skip (not mapped)

(Dedup check, writing style matching, and `（出典: LL-{NNN}, {CR}）` suffix apply as before.)

Append one row to Section 7 (変更履歴) of each modified steering file.

## Step C4: Promote Design Documents → DOCS_DIR (per repo + cross/)

For each `{repo}` in `AFFECTED_REPOS`:
  Let `DESIGN_TARGET` = `{DOCS}/{repo}/design/`.
  If `{CR_PATH}/05_architecture/{repo}/DSN-{CR}.md` exists: copy to `{DESIGN_TARGET}/DSN-{CR}.md`
  If `{CR_PATH}/06_design/{repo}/CHD-{CR}.md` exists: copy to `{DESIGN_TARGET}/CHD-{CR}.md`

If `HAS_CROSS`:
  Create `{DOCS}/cross/design/` if absent.
  If `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md` exists: copy to `{DOCS}/cross/design/`
  If `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` exists: copy to `{DOCS}/cross/design/`

Update AI_INDEX.md "リポジトリ別設計書・テスト仕様書" table (upsert per repo + cross).

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

## Step C6: Promote project-steering files → DOCS_DIR

`{XDDP_DIR}/project-steering.md` → `{DOCS}/project-steering.md` (overwrite)

For each `{repo}` in `REPOS_KEYS`:
  If `{XDDP_DIR}/project-steering-{repo}.md` exists:
    `{XDDP_DIR}/project-steering-{repo}.md` → `{DOCS}/{repo}/project-steering.md`

If `HAS_CROSS` and `{XDDP_DIR}/project-steering-cross.md` exists:
  Create `{DOCS}/cross/` if absent.
  `{XDDP_DIR}/project-steering-cross.md` → `{DOCS}/cross/project-steering.md`

Update AI_INDEX.md "共通知識" table (upsert per-repo and cross entries).

## Step D: Human Review Gate

Tell the user:
> ✅ クローズ処理が完了しました。内容を確認してください。
>
> **生成・更新した資料：**
> - 改善バックログ: `improvement-backlog.md`（追加 {n} 件。要確認IDEA: {k} 件）
> - 知見ログ: `lessons-learned.md`（追加 {n} 件。要確認LL: {k} 件）
{for each repo in AFFECTED_REPOS:}
> - {repo}: 仕様書 `{DOCS}/{repo}/specs/` / 設計書 `{DOCS}/{repo}/design/` / テスト `{DOCS}/{repo}/test/` / 知見 `{DOCS}/{repo}/knowledge/` に昇格
> - {repo}: `project-steering-{repo}.md` を `{DOCS}/{repo}/project-steering.md` に昇格
{if HAS_CROSS:}
> - cross: 仕様書・設計書・テスト・知見を `{DOCS}/cross/` に昇格（インタフェース破壊的変更: {あり/なし}）
> - cross: `project-steering-cross.md` を `{DOCS}/cross/project-steering.md` に昇格
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
