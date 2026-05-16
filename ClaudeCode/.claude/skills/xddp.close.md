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

## Step 0: Precondition Check

Read `{CR_PATH}/progress.md`.
If process step 15 (最新仕様書作成) is not ✅ 完了, instruct the user to run `/xddp.09.specs {CR}` first, then stop.

## Step A: Collect Insight/Proposal Memos

Read the following files (those that exist) and extract all content from their "気づき・提案メモ" sections:

```
Target files:
- {CR_PATH}/01_requirements/ (all .md)
- {CR_PATH}/02_analysis/ANA-{CR}.md
- {CR_PATH}/03_change-requirements/CRS-{CR}.md
- {CR_PATH}/04_specout/SPO-{CR}.md
- {CR_PATH}/05_architecture/DSN-{CR}.md
- {CR_PATH}/06_design/CHD-{CR}.md
- {CR_PATH}/09_test-spec/TSP-{CR}.md
- {CR_PATH}/10_test-results/ (all TRS-{CR}-*.md)
```

Compile all extracted entries into a list, together with their source file and action plan.

## Step B: Update Improvement Backlog

Read `{XDDP_DIR}/improvement-backlog.md`. If the file does not exist,
create it from `~/.claude/templates/10_improvement-backlog-template.md`.

From the insights collected in Step A, append as `IDEA-{NNN}` entries any item
whose action plan is **not** "今回対応" (i.e., 次回CR / 保留 / 検討中).

- Use sequential numbering continuing from existing entries.
- Derive the category from the content: `機能改善` `潜在的バグ` `リファクタリング` `技術的負債` `セキュリティ` `パフォーマンス` `テスト強化` `ドキュメント整備`
- Record the CR number and document name as the source.
- Update the summary table (Section 1) entry count.

## Step C: Generate/Update Lessons Learned Log

Read `{XDDP_DIR}/lessons-learned.md`. If the file does not exist,
create it from `~/.claude/templates/lessons-learned-template.md`.

Analyze the insights collected in Step A, together with lessons learned throughout this CR,
and extract as `LL-{NNN}` entries any knowledge **applicable to future CRs**.

### Knowledge Extraction Perspectives

Extract knowledge that answers the following questions. Skip a category if nothing applicable.

- **Requirements analysis / spec definition** (`#要求分析` `#仕様定義`)
  - Were there gaps or ambiguities discovered during analysis or design that weren't visible in the requirements?
  - What were the difficult judgment calls in decomposing UR → SR → SP?
- **Architecture / design** (`#方式検討` `#設計`)
  - Did the chosen approach produce unexpected impacts or constraints?
  - Was a rejected alternative later found to be the right choice?
- **Implementation / testing** (`#コーディング` `#テスト`)
  - Were there spec gaps or design errors only discovered through testing?
  - What modules showed regression impact, and is there a pattern?
- **Process** (`#プロセス`)
  - Which steps went smoothly or got stuck in this CR?
  - Are there process decisions or procedures to improve next time?

### Entry Format

Append each entry at the end of the "知見詳細" section in `lessons-learned.md` using this format:

```markdown
### LL-{NNN}：{タイトル}

**CR：** {CR番号} ／ **工程：** {工程名} ／ **タグ：** {#タグ1 #タグ2}

**発生状況：**  
{どんな場面・判断でこの知見が生まれたか（1〜2文）}

**学んだこと：**  
{具体的な知見・教訓}

**次回への適用：**  
- {チェックポイント1}
- {チェックポイント2}

---
```

After adding entries, append one row to the "エントリ一覧" table and update `最終更新CR` to {CR}.

## Step C0: Pre-close Sync (Parallel-CR Support)

### 1. Source Code Sync Check
- Run `git fetch origin` to get the latest remote state.
  - **If fetch fails** (offline / auth error / timeout):
    Display "fetch に失敗しました（理由: {エラー内容}）。最後に fetch した時点のリモート情報で判断します。続行しますか？ [続行 / 中止]" and wait for the user. Proceed only if "続行".
- Run `git log HEAD..origin/main --oneline` to check for un-merged remote commits.
- If un-merged commits exist → prompt the user to run `git pull`.
  - Proceed once the user confirms pull is complete.
  - Proceed only if the user explicitly says "スキップする" (warn that spec drift may result).

### 2. {DOCS_DIR}/ Sync
Check whether `{DOCS}` is a git repository (presence of `.git`) and run one of the following:

**Case A: {DOCS_DIR}/ is git-managed (recommended):**
- Run `git -C {DOCS} pull`.
- If conflicts occur → instruct the user to resolve them and resume, then stop.

**Case B: {DOCS_DIR}/ is not git-managed or does not exist yet:**
- Skip git pull.
- Display the following warning:
  ```
  ⚠️ DOCS_DIR（{DOCS}）は git 管理されていません。
  複数人・複数マシンで並行作業している場合、他のCRによる変更と
  競合しても自動検出できません。
  {DOCS_DIR}/ を git リポジトリとして管理することを推奨します。
  このまま続行しますか？ [続行 / 中止]
  ```
- Proceed only if the user chooses "続行".
- For local single-user work, the baseline pull in Step 3 still functions correctly.
- **Note (network drives)**: Treat NFS/SMB mounts of `{DOCS}` the same as unmanaged. On multi-machine setups sharing the same mount path, changes from other machines are not auto-detected — manual sync (copy or rsync) is required.

### 3. Pull Baseline into latest-specs/
- Execute only if `{DOCS}/{REPO_NAME}/specs/` exists (skip otherwise).
- Read the "**工程15 更新仕様書ファイル一覧**" section from `{CR_PATH}/progress.md` and extract the bullet-listed paths (`- latest-specs/...` format) as **protected files**.
  - If the section is absent (step 15 skipped or not yet run) → treat as no protected files (copy everything).
  - If the section exists but is empty (xddp.09.specs ran but updated 0 files) → skip this entire step (no files to promote, so pre-sync is unnecessary).
- List all files under `{DOCS}/{REPO_NAME}/specs/` and copy any that are **not** protected files to `{XDDP_DIR}/latest-specs/` (pulling in other CRs' approved changes).
- Do not overwrite protected files (preserve this CR's work).
- **Unmanaged / single-user work**: This step reads only the local {DOCS_DIR}/ and works normally.

### 4. Decide Whether to Regenerate Specs (human decision)
If Step 1 found new commits in the source code, present the following to the user for a decision:

```
ソースコードに N 件の新しいコミットがありました。
変更ファイル: [一覧]
このCRの影響範囲（progress.md 工程15）: [一覧]
重複ファイル: [あり/なし + 一覧]

→ xddp.09.specs の再実行を推奨します。実行しますか？
  [実行する / スキップする]
```

- User chooses "実行する" → run `/xddp.09.specs {CR}`, then proceed to Step C2.
- User chooses "スキップする" → warn that specs may drift from the latest source, then proceed to Step C2.
- **AI must not skip autonomously.** Always let the human decide.
- **Resuming after session disconnect**: Re-running `/xddp.close {CR}` restarts from Step C0.

## Step C2: Promote Approved Specs ({XDDP_DIR}/latest-specs/ → DOCS_DIR/{REPO_NAME}/specs/)

Read the "工程15 更新仕様書ファイル一覧" section from `{CR_PATH}/progress.md` to identify the files this CR updated (for reference only).

**Promotion target: all files under `{XDDP_DIR}/latest-specs/`.**
Step C0-3 has already pulled other CRs' approved specs into latest-specs/, so promoting all files keeps baseline_docs fully current. Files from other CRs already exist in baseline_docs, so overwriting them is safe (content is identical).

**Determine target path:**

Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.
Read `REPO_NAME` from the `xddp.config.md` found earlier. If absent or empty, report error and stop.
Let `SPECS_TARGET` = `{DOCS}/{REPO_NAME}/specs/`.

**Promotion process:**

For each file, copy `{XDDP_DIR}/latest-specs/{path}` → `{SPECS_TARGET}/{path}`.
Overwrite existing files (version history is managed inside the file's 変更履歴 section).

Then read `{DOCS}/AI_INDEX.md` (create if absent) and add/update the `{REPO_NAME}` row
in the "リポジトリ別仕様書" table:

| リポジトリ | 承認済み仕様書 | 知見 |
|---|---|---|
| [{REPO_NAME}]({REPO_NAME}/specs/) | v{X.Y}（最終更新CR: {CR}） | [{REPO_NAME}/knowledge/lessons-learned.md]({REPO_NAME}/knowledge/lessons-learned.md) |

## Step C3: Promote Lessons Learned Log ({XDDP_DIR}/lessons-learned.md → DOCS_DIR/{REPO_NAME}/knowledge/)

Append the entries added in Step C for this CR (LL entries for {CR}) to
`{DOCS}/{REPO_NAME}/knowledge/lessons-learned.md`.
Append only at the end — do not overwrite existing entries.

## Step C3.5: Apply Lessons to project-steering.md

If `{XDDP_DIR}/project-steering.md` does not exist, skip and record the skip.

Target the LL entries added in Step C for this CR (those containing **CR: {CR}**).

Append to the appropriate section of `project-steering.md` using the following mapping:

**Section mapping:**

| Target tag / content | Append to |
|---|---|
| `#方式検討` `#設計` — adopted design patterns | Section 3 (ADR) or Section 4 |
| `#コーディング` — implementation patterns / conventions | Section 4 (既存パターン・慣習) |
| `#テスト` — test patterns | Section 4 (テストパターン) |
| NG patterns / constraints / prohibitions | Section 5 (禁止事項・注意事項) |
| `#プロセス` `#要求分析` `#仕様定義` | Not mapped (not a technical pattern) |

**Append rules:**
- If an equivalent pattern is already documented, do not append (dedup check).
- Match the writing style of existing content in the section (code block or bullet list).
- Suffix each appended item with `（出典: LL-{NNN}, {CR}）` as a comment.
- Do not insert into code blocks; append directly below or as a new code block.

Append one row to Section 7 (変更履歴):

```
| {TODAY} | {CR} | LL反映: {list of appended LL-NNN entries} |
```

If no LL entries map to any section (e.g., all are `#プロセス`), skip and append "反映対象 LL なし" to Section 7.

## Step C4: Promote Design Documents (DSN・CHD → DOCS_DIR/{REPO_NAME}/design/)

Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
Let `DESIGN_TARGET` = `{DOCS}/{REPO_NAME}/design/`.

If the following files exist, copy them to `DESIGN_TARGET` (overwrite existing):
- `{CR_PATH}/05_architecture/DSN-{CR}.md` → `{DESIGN_TARGET}/DSN-{CR}.md`
  (matches xddp.05.arch OUTPUT_FILE: `{CR_PATH}/05_architecture/DSN-{CR}.md`)
- `{CR_PATH}/06_design/CHD-{CR}.md` → `{DESIGN_TARGET}/CHD-{CR}.md`
  (matches xddp.06.design OUTPUT_FILE: `{CR_PATH}/06_design/CHD-{CR}.md`)

After copying, read `{DOCS}/AI_INDEX.md` and add/update the `{REPO_NAME}` row
in the "リポジトリ別設計書・テスト仕様書" table.
Keep the "テスト仕様（TSP）" column value as-is; initialize to `—（未昇格）` only if the row does not exist yet (Step C5 will overwrite it):

| リポジトリ | 設計書（DSN・CHD） | テスト仕様（TSP） |
|---|---|---|
| [{REPO_NAME}]({REPO_NAME}/design/) | DSN・CHD（最終更新CR: {CR}） | —（未昇格） ← 既存値がある場合は保持 |

If neither file exists, skip and record the reason.

## Step C5: Promote Test Specifications (TSP → DOCS_DIR/{REPO_NAME}/test/)

Let `TEST_TARGET` = `{DOCS}/{REPO_NAME}/test/`.

If the following file exists, copy it to `TEST_TARGET` (overwrite existing):
- `{CR_PATH}/09_test-spec/TSP-{CR}.md` → `{TEST_TARGET}/TSP-{CR}.md`

After copying, update **only** the "テスト仕様（TSP）" column of the `{REPO_NAME}` row
in the "リポジトリ別設計書・テスト仕様書" table in `{DOCS}/AI_INDEX.md`
(leave the design document column unchanged):

| リポジトリ | 設計書（DSN・CHD） | テスト仕様（TSP） |
|---|---|---|
| [{REPO_NAME}]({REPO_NAME}/design/) | （既存値を保持） | TSP（最終更新CR: {CR}） |

If the file does not exist, skip and record the reason.
If the row itself does not exist (Step C4 was also skipped), create the row with `—（未昇格）` for the design column.

## Step C6: Promote project-steering.md ({XDDP_DIR}/ → DOCS_DIR/{REPO_NAME}/)

Check whether `{XDDP_DIR}/project-steering.md` exists.

If it exists:
1. Copy it to `{DOCS}/{REPO_NAME}/project-steering.md` (overwrite existing).
2. Add/update the following row in the "共通知識" table of `{DOCS}/AI_INDEX.md`
   (if the row already exists, update only the `最終更新CR` column):
   ```
   | [project-steering.md]({REPO_NAME}/project-steering.md) | 命名規約・ADR・コーディングパターン・禁止事項（最終更新CR: {CR}） |
   ```

If it does not exist: skip and record the skip.

## Step D: Human Review Gate

Tell the user:
> ✅ クローズ処理が完了しました。内容を確認してください。
>
> **生成・更新した資料：**
> - 改善バックログ: `improvement-backlog.md`（追加 {n} 件）
> - 知見ログ: `lessons-learned.md`（追加 {n} 件）
> - 承認済み仕様書: `{DOCS}/{REPO_NAME}/specs/` に昇格（{n} ファイル）
> - 設計書: `{DOCS}/{REPO_NAME}/design/` に昇格（DSN・CHD）
> - テスト仕様書: `{DOCS}/{REPO_NAME}/test/` に昇格（TSP）
> - project-steering: `{DOCS}/{REPO_NAME}/project-steering.md` に昇格（Step C6 がスキップされた場合はこの行を省略）
>
> **仕様書の昇格内容（{XDDP_DIR}/latest-specs/ → {DOCS}/{REPO_NAME}/specs/）：**
> {昇格したファイル一覧}
>
> **修正が必要な場合：**
> - 直接ファイルを編集してください
>
> 確認が完了したら「**クローズ完了**」と入力してください。

Wait for the user to confirm.

## Step E: Mark CR Complete

Read `{CR_PATH}/progress.md`.
Append the following at the end:

```
## CR クローズ

- **クローズ日：** {TODAY}
- **改善バックログ追加：** {n} 件
- **知見ログ追加：** {n} 件
- **ステータス：** ✅ 完了・クローズ済み
```

## Step F: Report in Japanese

Report the number of IDEA entries and LL entries added, and the main lesson titles.

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.close.md`.
