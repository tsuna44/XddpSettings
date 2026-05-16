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

## Step 0: DOCS_DIR Baseline Reference (Read-only)

1. Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` found earlier (default: `baseline_docs`).
   Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.
   Read `REPO_NAME` from the `xddp.config.md` found earlier. If absent or empty, report error and stop.

2. If `{DOCS}/{REPO_NAME}/specs/` exists:
   a. Read all `.md` files under it and retain as motherbase investigation context.
   b. Record the file count and list in the SPO's "参照したベースライン仕様書" section.

3. If `{DOCS}/{REPO_NAME}/specs/` does not exist:
   - Skip and record "ベースラインなし（初回 CR）" in the SPO.

4. The loaded baseline is used as "existing specs before change" throughout the ripple investigation (Step 1 onward).
   Do not write to files (writing to latest-specs/ is handled by xddp.09.specs).

## Step 0.5: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 4 (スペックアウト) → 🔄 進行中, 詳細ステップ → `Step A: スペックアウト調査中`, today. Write back.

## Step A0: Load Multi-Repository Configuration

Read `{WORKSPACE_ROOT}/xddp.config.md` found earlier and extract:

- Whether `MULTI_REPO` is `true`.
- If `true`, read the `REPOS:` section to get repo name → path mapping as `REPOS_MAP`.
- If `false` or `REPOS:` is not defined, set `REPOS_MAP = {}` and proceed in single-repo mode.

**Ripple investigation policy (applies to all repos):**
- Do not cut off the investigation; follow all dependencies to completion.
- Track visited nodes (files/symbols) to prevent infinite loops from circular references.
- If the affected file count exceeds `SPECOUT_MAX_AFFECTED_FILES`, emit a CR-split warning but
  do not stop the investigation. The human decides whether to continue or split.

**Multi-repository investigation policy (added only when `MULTI_REPO: true`):**
- The specout-agent starts from the repo containing the entry point and investigates ripple effects.
- When symbols from another repo (imports, HTTP calls, messages, etc.) are detected during investigation,
  resolve the repo path from `REPOS_MAP` and extend the investigation to that repo.
- If `SPECOUT_SEQUENCE_LEVELS` includes `repository`, generate cross-repo sequence diagrams in `cross-module/`.

## Step A: Specout Investigation

Use the **Agent tool** with `subagent_type=xddp-specout-agent` and pass:
```
CR_NUMBER: {CR}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
LATEST_SPECS_DIR: {XDDP_DIR}/latest-specs/
ENTRY_POINTS: {ENTRY_POINTS}
REPOS_MAP: {repo mapping from Step A0; empty for single-repo}
SUMMARY_TEMPLATE: ~/.claude/templates/04_specout-template.md
MODULE_TEMPLATE: ~/.claude/templates/04_specout-module-template.md
CROSS_MODULE_TEMPLATE: ~/.claude/templates/04_specout-cross-module-template.md
OUTPUT_DIR: {CR_PATH}/04_specout/
TODAY: {TODAY}
```

Wait for completion. The agent creates:
- `{CR_PATH}/04_specout/SPO-{CR}.md` — summary (affected scope, function mapping, CRS reflection items)
- `{CR_PATH}/04_specout/modules/{module-name}-spo.md` — per-module (current specs, in-module diagrams)
- `{CR_PATH}/04_specout/cross-module/SPO-{CR}-cross.md` — cross-module (structure/sequence diagrams, etc.) — only if 2+ modules

Check if the agent emitted a scale warning (`SPECOUT_MAX_AFFECTED_FILES` exceeded). If so, relay the following to the user and **wait for their decision before continuing to Step A2**:

> ⚠️ **波及規模警告**: 影響ファイル数が `SPECOUT_MAX_AFFECTED_FILES`（{設定値}）を超えています。
> 調査は完了しており、影響範囲の漏れはありません。
>
> **このまま続行する場合:** 「続行」と入力してください。後続フェーズ（設計・コーディング）のコストが増大します。
> **CR を分割する場合:** 「分割」と入力してください。SPO の影響範囲を参考に CR を再分割し、`/xddp.01.init` から再実行してください。

If the user selects "続行", or if no warning occurred, proceed to Step A2.

## Step A2: SPO Review Loop (up to `REVIEW_MAX_ROUNDS.SPO` rounds)

Update `{CR_PATH}/progress.md` step 4 詳細ステップ → `Step A2: SPOレビュー中`.

Read the `xddp.config.md` found earlier (`{WORKSPACE_ROOT}/xddp.config.md`). Extract `REVIEW_MAX_ROUNDS.SPO` (default: 3 if key absent). Set `max_rounds` = that value.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: SPO
   TARGET_FILE: {CR_PATH}/04_specout/SPO-{CR}.md
   REFERENCE_FILES: [
     {CR_PATH}/01_requirements/ (all .md),
     {CR_PATH}/03_change-requirements/CRS-{CR}.md,
     {CR_PATH}/04_specout/modules/ (all .md, including subdirectories),
     {CR_PATH}/04_specout/cross-module/ (all .md, if exists)
   ]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/04_specout/review/04_specout-review.md
   ```

2. Read `{CR_PATH}/04_specout/review/04_specout-review.md`.
   - No 🔴/🟡 → `issues_remain = false`, exit loop.
   - 🔴/🟡 found, `round < max_rounds` → apply fixes to the appropriate file(s) (summary or relevant module/cross-module file), increment `round`, continue loop.
   - `round = max_rounds`, issues remain → append "⚠️ 未解決の重大指摘あり。人間の判断が必要です。" to review file. Exit loop.

## Step A3: Human Review Gate (SPO)

Update `{CR_PATH}/progress.md` step 4 状態 → 👀 レビュー待ち, 詳細ステップ → `Step A3: 人レビュー待ち`.

Tell the user:
> ✅ SPOのAIレビューが完了しました。続いて人によるレビューをお願いします。
>
> **成果物:**
> - サマリー: `{CR_PATH}/04_specout/SPO-{CR}.md`
> - モジュール個別: `{CR_PATH}/04_specout/modules/`
> - クロスモジュール: `{CR_PATH}/04_specout/cross-module/`（2モジュール以上の場合）
> - AIレビュー結果: `{CR_PATH}/04_specout/review/04_specout-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} specout`（サマリーSPO-{CR}.mdへの修正）
>   モジュール個別ファイルを修正する場合: `/xddp.revise {CR} {ファイルパス}`
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。
> 変更がなければそのまま「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes (edited files or ran `/xddp.revise`):
- Run one final AI review pass using **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: SPO
  TARGET_FILE: {CR_PATH}/04_specout/SPO-{CR}.md
  REFERENCE_FILES: [
    {CR_PATH}/01_requirements/ (all .md),
    {CR_PATH}/03_change-requirements/CRS-{CR}.md,
    {CR_PATH}/04_specout/modules/ (all .md, including subdirectories),
    {CR_PATH}/04_specout/cross-module/ (all .md, if exists)
  ]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR_PATH}/04_specout/review/04_specout-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step B: Update CRS with Specout Findings

Update `{CR_PATH}/progress.md` step 4 状態 → 🔄 進行中, 詳細ステップ → `Step B: CRS更新中`. Also set step 5 → 🔄 進行中.

Use the **Agent tool** with `subagent_type=xddp-spec-writer-agent` and pass:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR_PATH}/04_specout/SPO-{CR}.md
SPO_MODULES_DIR: {CR_PATH}/04_specout/modules/
SPO_CROSS_MODULE_FILE: {CR_PATH}/04_specout/cross-module/SPO-{CR}-cross.md (if exists)
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
>
> **Warning (P-3):** Do not execute `crs_md2excel.py` directly via Bash.
> Always use the xddp.md2excel skill via the Agent tool.

## Step D: Update progress.md
Step 4 (スペックアウト) → ✅ 完了, 詳細ステップ → `-`, link `SPO-{CR}.md`.
Step 5 (変更要求仕様書更新・TM作成) → ✅ 完了, 詳細ステップ → `-`.
  ※ The TM is embedded in the CRS document and updated by xddp-spec-writer-agent in Step B.
  ※ TM completeness was verified by xddp-reviewer during CRS review (CRS checklist item 4).
Next command → `/xddp.05.arch {CR}`

## Step E: Report in Japanese
Report: entry points investigated, affected file count, number of SP items added/modified, review rounds for SPO.

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.04.specout.md`.
