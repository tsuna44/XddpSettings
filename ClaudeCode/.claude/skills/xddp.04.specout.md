---
description: XDDP フェーズ2: スペックアウト（母体調査）を実施し、変更要求仕様書にフィードバックする。「スペックアウトして」「母体調査して」「影響範囲を調べて」などで起動する。
---

You are orchestrating **XDDP Step 04 — Specout (Motherbase Investigation) + Step 05 — CRS Update**.

> This step maps every ripple effect of the change. A missed dependency causes silent production failures that take days to diagnose. Orchestrate with thoroughness — leave no call chain unexamined.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) [ENTRY_POINTS...]
- First token: CR number (optional; auto-detected from XDDP_DIR if omitted)
- Remaining tokens (optional): entry point identifiers or file paths

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `ENTRY_POINTS` = `REST_ARGS` (may be empty). Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Build `REPOS_MAP` (repo name → path).
Let `REPOS_KEYS` = list of all repository names. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).

Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.

## Step 0: Identify Affected Repositories

Read `{CR_PATH}/03_change-requirements/CRS-{CR}.md`.

Determine `AFFECTED_REPOS` (ordered list of repositories to investigate):
1. If the CRS has a "1.5 影響リポジトリ" section with a filled table → read from it.
2. If the section is absent or empty:
   - Analyse the CRS requirements text to infer which repos are involved (look for repo names, file paths, service names, API mentions).
   - If not determinable → use all `REPOS_KEYS` and report "影響リポジトリを CRS から特定できなかったため、全リポジトリを調査対象とします。".

Determine `HAS_CROSS`: set `true` if `IS_MULTI` and `len(AFFECTED_REPOS) ≥ 2` (repository interconnection exists).

## Step 0.5 (confirmation gate): Present scope to user

> Confirmation gate is executed before marking progress, to avoid polluting progress.md on cancellation.

Tell the user:
> 以下のリポジトリを対象にスペックアウト（工程4）を開始します:
> {AFFECTED_REPOS リスト（各行に - {repo名} を表示）}
> リポジトリ間連携: {HAS_CROSS ? "あり（cross/ 成果物を生成します）" : "なし（cross/ 生成なし）"}
>
> よろしければ「OK」と入力してください。対象リポジトリを変更する場合は指定してください。

Wait for user response. If the user specifies different repos, update `AFFECTED_REPOS` accordingly.

## Step 0.6: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 4 (スペックアウト) → 🔄 進行中, 詳細ステップ → `Step A: スペックアウト調査中`, today.
If `IS_MULTI`, append a per-repo progress table for step 4:
```markdown
## 工程4 スペックアウト進捗（リポジトリ別）
| リポジトリ | 状態 | 完了日 |
|---|---|---|
{for each repo in AFFECTED_REPOS: | {repo} | 🔄 進行中 | - |}
{if HAS_CROSS: | cross | ⏳ 未着手 | - |}
```
Write back.

## Step A: Per-repo Specout Investigation

**Ripple investigation policy:**
- Do not cut off the investigation; follow all dependencies to completion.
- Track visited nodes to prevent infinite loops from circular references.
- If affected file count exceeds `SPECOUT_MAX_AFFECTED_FILES`, emit CR-split warning but do not stop.

For each `{repo}` in `AFFECTED_REPOS`:

Use the **Agent tool** with `subagent_type=xddp-specout-agent` and pass:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
BASELINE_SPECS_DIR: {DOCS}/{repo}/specs/    ← per-repo approved specs
CROSS_SPECS_DIR: {DOCS}/cross/specs/         ← cross-repo interface specs (pass if exists)
ENTRY_POINTS: {ENTRY_POINTS}
SUMMARY_TEMPLATE: ~/.claude/templates/04_specout-template.md
MODULE_TEMPLATE: ~/.claude/templates/04_specout-module-template.md
OUTPUT_DIR: {CR_PATH}/04_specout/{repo}/
TODAY: {TODAY}
```

Wait for completion. Agent creates:
- `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` — summary
- `{CR_PATH}/04_specout/{repo}/modules/` — per-module SPOs

After each repo completes, update the per-repo progress table in progress.md:
`| {repo} | ✅ 完了 | {TODAY} |`

Check if the agent emitted a scale warning (`SPECOUT_MAX_AFFECTED_FILES` exceeded). If so, relay to the user and wait for their decision before continuing.

## Step A-cross: Cross-repo SPO Synthesis (only when HAS_CROSS = true)

Update progress table: `| cross | 🔄 進行中 | - |`

After all per-repo SPOs are complete, synthesise `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`:

Read all `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` files. Identify:
- Symbols, types, or functions from repo-A that are imported or called by repo-B
- HTTP API calls from one repo to another
- Shared data structures, event schemas, or message payloads
- Shared database tables (read/write by multiple repos)

Write `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` using `~/.claude/templates/04_specout-cross-module-template.md`:
- Section 2: リポジトリ間構造図 (Mermaid C4/component diagram)
- Section 3: リポジトリ間シーケンス図 (if `SPECOUT_SEQUENCE_LEVELS` includes `repository`)
- Section 4: 共有インタフェース一覧 (interface / provider-repo / consumer-repos / type)
- Section 5: CRS への反映事項（cross）

If no inter-repo dependencies found → skip cross/ SPO creation; set `HAS_CROSS = false`.

Update progress table: `| cross | ✅ 完了 | {TODAY} |`

## Step A2: SPO Review Loop

Update `{CR_PATH}/progress.md` step 4 詳細ステップ → `Step A2: SPOレビュー中`.

Read `REVIEW_MAX_ROUNDS.SPO` from xddp.config.md (default: 3). Set `max_rounds` = that value.

For each `{repo}` in `AFFECTED_REPOS` (run review loops sequentially per repo):

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: SPO
   TARGET_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
   REFERENCE_FILES: [
     {CR_PATH}/01_requirements/ (all .md),
     {CR_PATH}/03_change-requirements/CRS-{CR}.md,
     {CR_PATH}/04_specout/{repo}/modules/ (all .md, including subdirectories)
   ]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/04_specout/{repo}/review/04_specout-review.md
   ```

2. Read review file.
   - No 🔴/🟡 → `issues_remain = false`, exit loop.
   - 🔴/🟡 found, `round < max_rounds` → apply fixes, increment `round`, continue.
   - `round = max_rounds`, issues remain → append warning. Exit loop.

## Step A3: Human Review Gate (SPO)

Update `{CR_PATH}/progress.md` step 4 状態 → 👀 レビュー待ち, 詳細ステップ → `Step A3: 人レビュー待ち`.

Tell the user:
> ✅ SPOのAIレビューが完了しました。続いて人によるレビューをお願いします。
>
> **成果物:**
{for each repo in AFFECTED_REPOS:}
> - {repo}: `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`
>   - モジュール: `{CR_PATH}/04_specout/{repo}/modules/`
>   - AIレビュー: `{CR_PATH}/04_specout/{repo}/review/04_specout-review.md`
{if HAS_CROSS:}
> - cross: `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} specout`（対象リポジトリを指定）
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes:
- Run one final AI review pass per repo (same as Step A2 but `REVIEW_ROUND = last_round + 1`).

## Step B: Update CRS with Specout Findings

Update `{CR_PATH}/progress.md` step 4 状態 → 🔄 進行中, 詳細ステップ → `Step B: CRS更新中`. Also set step 5 → 🔄 進行中.

Use the **Agent tool** with `subagent_type=xddp-spec-writer-agent` and pass:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_DIR: {CR_PATH}/04_specout/
SPO_CROSS_FILE: {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md (pass only if exists)
TODAY: {TODAY}
AUTHOR_NOTE: スペックアウト結果を反映。影響範囲・SP更新。
```

## Step C: Regenerate CRS Excel (UR-016)

Update `{CR_PATH}/progress.md` step 4 詳細ステップ → `Step C: Excel再生成中`.

**Excel generation is delegated to the `xddp.md2excel` skill.**

Use the **Agent tool** with the `xddp.md2excel` skill logic, passing:
```
CR_NUMBER: {CR}
```

> **Design policy:** The sole definition of the Excel format is in `~/.claude/skills/xddp.md2excel.md` and `~/.claude/templates/crs_md2excel.py`.
> To change the format, modify only xddp.md2excel.md and crs_md2excel.py.

## Step D: Update progress.md

Step 4 (スペックアウト) → ✅ 完了, 詳細ステップ → `-`.
Step 5 (変更要求仕様書更新・TM作成) → ✅ 完了, 詳細ステップ → `-`.
Next command → `/xddp.05.arch {CR}`

## Step E: Report in Japanese
Report: repos investigated, affected file count per repo, cross/ synthesis result, review rounds.

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.04.specout.md`.
