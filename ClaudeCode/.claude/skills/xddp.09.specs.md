---
description: XDDP フェーズ6: 最新仕様書（latest-specs/）を生成・更新してCRを完了する。「最新仕様書を作って」「latest-specsを更新して」「CRを完了して」などで起動する。
---

You are orchestrating **XDDP Step 09 (process step 15) — Generate/Update Latest Specifications**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

## Step 0: Mark In-Progress
Read `{CR}/progress.md`. Set step 15 (最新仕様書作成) → 🔄 進行中, 詳細ステップ → `Step A: 仕様書生成中`, today. Write back.

## Step A: Determine scope and update latest-specs/

Read:
- `{CR}/04_specout/SPO-{CR}.md` (changed modules list)
- `{CR}/06_design/CHD-{CR}.md` (changed file list, Section 2)
- `{CR}/03_change-requirements/CRS-{CR}.md` (final specs)
- All existing files in `latest-specs/` (if directory exists)

For each changed module/functional area:

**ファイルパスの決定:**
SPO Section 3.1 の変更ファイルリストからモジュール名を抽出し、
`latest-specs/{top-level-module}/{sub-module}-spec.md` 形式でパスを決定する。
（例: `src/auth/login.py` → `latest-specs/auth/login-spec.md`）
既存の `latest-specs/` ディレクトリ構造がある場合はそれに従う。

**If a matching spec file exists in `latest-specs/`:**
- Read the file.
- Apply changes described in the CHD to the relevant sections.
- Increment the spec version and add a 変更履歴 entry: CR={CR}, date=TODAY.

**If no spec file exists for this module:**
- Create `latest-specs/{module-path}/{name}-spec.md` using `~/.claude/templates/09_specification-template.md`.
- Synthesize from: SPO (existing behavior) + CRS (requirements) + CHD (new design).
- Version: 1.0. CR reference: {CR}.

All content in Japanese.

## Step A2: AI Review of Latest Specs

Update `{CR}/progress.md` step 15 詳細ステップ → `Step A2: AIレビュー中`.

For each newly created or updated spec file, use **Agent tool** `subagent_type=xddp-reviewer` and pass:
```
DOCUMENT_TYPE: CRS
TARGET_FILE: {spec file path}
REFERENCE_FILES: [{CR}/03_change-requirements/CRS-{CR}.md, {CR}/06_design/CHD-{CR}.md]
REVIEW_ROUND: 1
OUTPUT_FILE: {CR}/review/09_specs-review.md
```

If 🔴 issues are found: apply fixes directly to the spec file and re-run once.
If 🟡 issues remain after one fix pass: note them in the review file; do not block progress.

## Step A3: Human Review Gate (Latest Specs)

Update `{CR}/progress.md` step 15 状態 → 👀 レビュー待ち, 詳細ステップ → `Step A3: 人レビュー待ち`.

Tell the user:
> ✅ 最新仕様書の生成が完了しました。内容を確認してください。
> - 成果物: `latest-specs/` 配下の更新・作成ファイル一覧（Step A で報告）
> - AIレビュー結果: `{CR}/review/09_specs-review.md`
>
> 問題なければ「**確認完了**」と入力してください。

Wait for the user to confirm.

## Step B: Update progress.md
Step 15 (最新仕様書作成) → ✅ 完了, 詳細ステップ → `-`.
Set "次に実行すべきコマンド" → "このCRは完了です。次のCRは `/xddp.01.init {次のCR番号}` で開始してください。"

## Step C: Report in Japanese
List the spec files updated and created.

Tell the user:
> 工程15が完了しました。続いて CR クローズ処理（気づき集約・知見ログ更新）を実行してください。
> ```
> /xddp.close {CR}
> ```

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.09.specs.md` の要約も合わせて更新すること。
