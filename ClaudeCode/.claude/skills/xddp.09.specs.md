---
description: XDDP フェーズ6: 最新仕様書（{XDDP_DIR}/latest-specs/）を生成・更新してCRを完了する。「最新仕様書を作って」「latest-specsを更新して」「CRを完了して」などで起動する。
---

You are orchestrating **XDDP Step 09 (process step 15) — Generate/Update Latest Specifications**.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Build `REPOS_MAP` (repo name → path).
Let `REPOS_KEYS` = list of all repository names. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).

Identify `AFFECTED_REPOS`: read CRS "1.5 影響リポジトリ" section if present; otherwise use REPOS_KEYS.
Let `HAS_CROSS` = (IS_MULTI and `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` exists).

## Step 0: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 15 (最新仕様書作成) → 🔄 進行中, 詳細ステップ → `Step A: 仕様書生成中`, today. Write back.

## Step A: Generate/Update per-repo latest-specs

For each `{repo}` in `AFFECTED_REPOS`:

Read:
- `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` (changed modules list)
- `{CR_PATH}/06_design/{repo}/CHD-{CR}.md` (changed file list, Section 2)
- `{CR_PATH}/03_change-requirements/CRS-{CR}.md` (final specs)
- All existing files in `{XDDP_DIR}/latest-specs/{repo}/` (if directory exists)

For each changed module/functional area in `{repo}`:

**Determine file path:**
Extract module name from the changed file list in SPO Section 3.1.
Determine path as `{XDDP_DIR}/latest-specs/{repo}/{top-level-module}/{sub-module}-spec.md`.
(Example: `repo-a/src/auth/login.py` → `{XDDP_DIR}/latest-specs/{repo-a}/auth/login-spec.md`)
If an existing `{XDDP_DIR}/latest-specs/{repo}/` structure exists, follow it.

**If a matching spec file exists:**
- Read the file.
- Apply changes from CHD to the relevant sections.
- Increment spec version and add 変更履歴 entry: CR={CR}, date=TODAY.

**If no spec file exists:**
- Create `{XDDP_DIR}/latest-specs/{repo}/{module-path}/{name}-spec.md` using `~/.claude/templates/09_specification-template.md`.
- Synthesise from: SPO (existing behavior) + CRS (requirements) + CHD (new design).
- Version: 1.0. CR reference: {CR}.

All content in Japanese.

## Step A-cross: Generate/Update cross interface specs (only when HAS_CROSS = true)

Read `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` → "インタフェース変更サマリ" table.

For each interface in the table:

**Determine file path:** `{XDDP_DIR}/latest-specs/cross/interfaces/{interface-kebab-name}-spec.md`
(Example: `POST /jobs` → `latest-specs/cross/interfaces/post-jobs-spec.md`)

**If a matching interface spec exists:**
- Read the file. Determine new version from the change kind:
  - breaking: true (field removal / type change / endpoint deletion) → increment MAJOR (e.g., 1.0.0 → 2.0.0)
  - breaking: false, new fields/args → increment MINOR (e.g., 1.0.0 → 1.1.0)
  - doc-only change → increment PATCH
- Apply changes to spec. Update frontmatter: `version`, `last-updated-cr: {CR}`, `breaking`.

**If no interface spec exists (new interface):**
- Create using `~/.claude/templates/interface-spec-template.md`.
- Fill frontmatter: `interface`, `version: 1.0.0`, `last-updated-cr: {CR}`, `breaking: false`, `provider`, `downstream-repos`.

## Step A2: AI Review Loop of Latest Specs

Update `{CR_PATH}/progress.md` step 15 詳細ステップ → `Step A2: AIレビュー中`.

Read `REVIEW_MAX_ROUNDS.SPEC` from xddp.config.md (default: 2). Set `max_rounds` = that value.
(Single `SPEC` value applies to all repos and cross/ interfaces.)

For each repo's spec files and each cross/interfaces/ spec:

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: CRS
   TARGET_FILE: {spec file path}
   REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/06_design/{repo}/CHD-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/review/09_specs-{repo}-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit loop.
   - Issues found, `round < max_rounds` → apply fixes to spec file. Increment `round`.
   - `round = max_rounds`, issues remain → append warning; proceed.

## Step A3: Human Review Gate (Latest Specs)

Update `{CR_PATH}/progress.md` step 15 状態 → 👀 レビュー待ち, 詳細ステップ → `Step A3: 人レビュー待ち`.

Tell the user:
> ✅ 最新仕様書の生成が完了しました。内容を確認してください。
{for each repo in AFFECTED_REPOS:}
> - {repo}: `{XDDP_DIR}/latest-specs/{repo}/` 配下の更新・作成ファイル一覧
{if HAS_CROSS:}
> - cross: `{XDDP_DIR}/latest-specs/cross/interfaces/` 配下の更新・作成ファイル一覧
>
> 問題なければ「**確認完了**」と入力してください。

Wait for the user to confirm.

## Step B: Update progress.md

Step 15 (最新仕様書作成) → ✅ 完了, 詳細ステップ → `-`.
Set "次に実行すべきコマンド" → "このCRは完了です。次のCRは `/xddp.01.init {次のCR番号}` で開始してください。"

Write all updated/created file paths to the "工程15 更新仕様書ファイル一覧" section in `{CR_PATH}/progress.md`.
Include `{repo}/` prefix in all paths:

````markdown
## 工程15 更新仕様書ファイル一覧

<!-- xddp.09.specs が自動記録。xddp.close Step C0-3 で保護対象判定に使用する。 -->

- latest-specs/{repo-a}/auth/login-spec.md
- latest-specs/{repo-b}/queue/job-spec.md
- latest-specs/cross/interfaces/post-jobs-spec.md
````

(Overwrite the section if it already exists.)

## Step C: Report in Japanese
List the spec files updated and created per repo.

Tell the user:
> 工程15が完了しました。続いて CR クローズ処理（気づき集約・知見ログ更新）を実行してください。
> ```
> /xddp.close {CR}
> ```

---
> **Maintenance note:** When modifying this file, also update `.claude/commands/xddp.09.specs.md`.
