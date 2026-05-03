---
description: XDDP フェーズ6: 最新仕様書（{XDDP_DIR}/latest-specs/）を生成・更新してCRを完了する。「最新仕様書を作って」「latest-specsを更新して」「CRを完了して」などで起動する。
---

You are orchestrating **XDDP Step 09 (process step 15) — Generate/Update Latest Specifications**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

Read `xddp.config.md` (project root) and extract `XDDP_DIR` (default: `.` if the key is absent). Let `CR_PATH` = `{XDDP_DIR}/{CR}`.

## Step 0: Mark In-Progress
Read `{CR_PATH}/progress.md`. Set step 15 (最新仕様書作成) → 🔄 進行中, 詳細ステップ → `Step A: 仕様書生成中`, today. Write back.

## Step A: Determine scope and update {XDDP_DIR}/latest-specs/

Read:
- `{CR_PATH}/04_specout/SPO-{CR}.md` (changed modules list)
- `{CR_PATH}/06_design/CHD-{CR}.md` (changed file list, Section 2)
- `{CR_PATH}/03_change-requirements/CRS-{CR}.md` (final specs)
- All existing files in `{XDDP_DIR}/latest-specs/` (if directory exists)

For each changed module/functional area:

**ファイルパスの決定:**
SPO Section 3.1 の変更ファイルリストからモジュール名を抽出し、
`{XDDP_DIR}/latest-specs/{top-level-module}/{sub-module}-spec.md` 形式でパスを決定する。
（例: `src/auth/login.py` → `{XDDP_DIR}/latest-specs/auth/login-spec.md`）
既存の `{XDDP_DIR}/latest-specs/` ディレクトリ構造がある場合はそれに従う。

**If a matching spec file exists in `{XDDP_DIR}/latest-specs/`:**
- Read the file.
- Apply changes described in the CHD to the relevant sections.
- Increment the spec version and add a 変更履歴 entry: CR={CR}, date=TODAY.

**If no spec file exists for this module:**
- Create `{XDDP_DIR}/latest-specs/{module-path}/{name}-spec.md` using `~/.claude/templates/09_specification-template.md`.
- Synthesize from: SPO (existing behavior) + CRS (requirements) + CHD (new design).
- Version: 1.0. CR reference: {CR}.

All content in Japanese.

## Step A2: AI Review Loop of Latest Specs

Update `{CR_PATH}/progress.md` step 15 詳細ステップ → `Step A2: AIレビュー中`.

Read `xddp.config.md` (project root). Extract `REVIEW_MAX_ROUNDS.SPEC` (default: 2 if key absent). Set `max_rounds` = that value.

For each newly created or updated spec file:

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: CRS
   TARGET_FILE: {spec file path}
   REFERENCE_FILES: [{CR_PATH}/03_change-requirements/CRS-{CR}.md, {CR_PATH}/06_design/CHD-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/review/09_specs-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit loop.
   - Issues found, `round < max_rounds` → apply fixes directly to the spec file. Increment `round`.
   - `round = max_rounds`, issues remain → append warning to review file; proceed.

## Step A3: Human Review Gate (Latest Specs)

Update `{CR_PATH}/progress.md` step 15 状態 → 👀 レビュー待ち, 詳細ステップ → `Step A3: 人レビュー待ち`.

Tell the user:
> ✅ 最新仕様書の生成が完了しました。内容を確認してください。
> - 成果物: `{XDDP_DIR}/latest-specs/` 配下の更新・作成ファイル一覧（Step A で報告）
> - AIレビュー結果: `{CR_PATH}/review/09_specs-review.md`
>
> 問題なければ「**確認完了**」と入力してください。

Wait for the user to confirm.

## Step B: Update progress.md
Step 15 (最新仕様書作成) → ✅ 完了, 詳細ステップ → `-`.
Set "次に実行すべきコマンド" → "このCRは完了です。次のCRは `/xddp.01.init {次のCR番号}` で開始してください。"

Step A で作成・更新したすべてのファイルパス（`{XDDP_DIR}/latest-specs/` からの相対パス）を
`{CR_PATH}/progress.md` の「工程15 更新仕様書ファイル一覧」セクションに書き込む:

````markdown
## 工程15 更新仕様書ファイル一覧

<!-- xddp.09.specs が自動記録。xddp.close Step C0-3 で保護対象判定に使用する。 -->

- latest-specs/auth/login-spec.md
- latest-specs/auth/signup-spec.md
````

（セクションが既存の場合は上書きする）

## Step C: Report in Japanese
List the spec files updated and created.

Tell the user:
> 工程15が完了しました。続いて CR クローズ処理（気づき集約・知見ログ更新）を実行してください。
> ```
> /xddp.close {CR}
> ```

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.09.specs.md` の要約も合わせて更新すること。
