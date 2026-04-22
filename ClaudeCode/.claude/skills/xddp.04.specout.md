---
description: XDDP フェーズ2: スペックアウト（母体調査）を実施し、変更要求仕様書にフィードバックする。「スペックアウトして」「母体調査して」「影響範囲を調べて」などで起動する。
---

You are orchestrating **XDDP Step 04 — Specout (Motherbase Investigation) + Step 05 — CRS Update**.

**Arguments:** $ARGUMENTS = CR_NUMBER [ENTRY_POINTS...]
- First token: CR number
- Remaining tokens (optional): entry point identifiers or file paths

---

Let `CR` = first token of $ARGUMENTS. Let `ENTRY_POINTS` = remaining tokens (may be empty). Let `TODAY` = today's date.

## Step 0: Mark In-Progress
Read `{CR}/progress.md`. Set step 4 (スペックアウト) → 🔄 進行中, 詳細ステップ → `Step A: スペックアウト調査中`, today. Write back.

## Step A0: マルチリポジトリ設定の読み込み

`xddp.config.md` を読み込み、以下を取得する。

- `MULTI_REPO` が `true` かどうかを確認する。
- `true` の場合、`REPOS:` セクションからリポジトリ名→パスのマッピングを `REPOS_MAP` として取得する。
- `false` または `REPOS:` が未定義の場合、`REPOS_MAP = {}` とし、単一リポジトリモードで進む。

**マルチリポジトリ調査方針（`MULTI_REPO: true` の場合のみ適用）:**
- specout-agent は、エントリポイントが属するリポジトリを起点に波及調査を行う。
- 調査中に他リポジトリのシンボル（import, HTTP呼び出し, メッセージ等）を検出した場合、
  `REPOS_MAP` を参照して該当リポジトリのパスを解決し、そのリポジトリに波及調査を延長する。
- リポジトリ境界をまたいだ場合でも `SPECOUT_CUTOFF_MODULE_BOUNDARIES` のカウントは継続する
  （リポジトリ境界越えを1回の境界越えとしてカウントする）。
- `SPECOUT_SEQUENCE_LEVELS` に `repository` が含まれる場合、
  クロスリポジトリシーケンス図を `cross-module/` に追加生成する。

## Step A: Specout Investigation

Use the **Agent tool** with `subagent_type=xddp-specout-agent` and pass:
```
CR_NUMBER: {CR}
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
LATEST_SPECS_DIR: latest-specs/
ENTRY_POINTS: {ENTRY_POINTS}
REPOS_MAP: {Step A0 で取得したリポジトリマッピング。単一リポジトリの場合は空}
SUMMARY_TEMPLATE: ~/.claude/templates/04_specout-template.md
MODULE_TEMPLATE: ~/.claude/templates/04_specout-module-template.md
CROSS_MODULE_TEMPLATE: ~/.claude/templates/04_specout-cross-module-template.md
OUTPUT_DIR: {CR}/04_specout/
TODAY: {TODAY}
```

Wait for completion. The agent creates:
- `{CR}/04_specout/SPO-{CR}.md` — サマリー（影響範囲・機能対応表・CRS反映事項）
- `{CR}/04_specout/modules/{module-name}-spo.md` — モジュール個別（現状仕様・モジュール内ダイアグラム）
- `{CR}/04_specout/cross-module/SPO-{CR}-cross.md` — クロスモジュール（構造図・シーケンス図等）※2モジュール以上の場合のみ

Check if the agent emitted a scale warning (20+ files). If so, relay the warning to the user and ask whether to proceed or split the CR.

## Step A2: SPO Review Loop (max 5 iterations)

Update `{CR}/progress.md` step 4 詳細ステップ → `Step A2: SPOレビュー中`.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ 5`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: SPO
   TARGET_FILE: {CR}/04_specout/SPO-{CR}.md
   REFERENCE_FILES: [
     {CR}/01_requirements/ (all .md),
     {CR}/03_change-requirements/CRS-{CR}.md,
     {CR}/04_specout/modules/ (all *-spo.md),
     {CR}/04_specout/cross-module/ (all .md, if exists)
   ]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR}/review/04_specout-review.md
   ```

2. Read `{CR}/review/04_specout-review.md`.
   - No 🔴/🟡 → `issues_remain = false`, exit loop.
   - 🔴/🟡 found, `round < 5` → apply fixes to the appropriate file(s) (summary or relevant module/cross-module file), increment `round`, continue loop.
   - `round = 5`, issues remain → append "⚠️ 未解決の重大指摘あり。人間の判断が必要です。" to review file. Exit loop.

## Step A3: Human Review Gate (SPO)

Update `{CR}/progress.md` step 4 状態 → 👀 レビュー待ち, 詳細ステップ → `Step A3: 人レビュー待ち`.

Tell the user:
> ✅ SPOのAIレビューが完了しました。続いて人によるレビューをお願いします。
>
> **成果物:**
> - サマリー: `{CR}/04_specout/SPO-{CR}.md`
> - モジュール個別: `{CR}/04_specout/modules/`
> - クロスモジュール: `{CR}/04_specout/cross-module/`（2モジュール以上の場合）
> - AIレビュー結果: `{CR}/review/04_specout-review.md`
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
  TARGET_FILE: {CR}/04_specout/SPO-{CR}.md
  REFERENCE_FILES: [
    {CR}/01_requirements/ (all .md),
    {CR}/03_change-requirements/CRS-{CR}.md,
    {CR}/04_specout/modules/ (all *-spo.md),
    {CR}/04_specout/cross-module/ (all .md, if exists)
  ]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR}/review/04_specout-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step B: Update CRS with Specout Findings

Update `{CR}/progress.md` step 4 状態 → 🔄 進行中, 詳細ステップ → `Step B: CRS更新中`. Also set step 5 → 🔄 進行中.

Use the **Agent tool** with `subagent_type=xddp-spec-writer-agent` and pass:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR}/04_specout/SPO-{CR}.md
SPO_MODULES_DIR: {CR}/04_specout/modules/
SPO_CROSS_MODULE_FILE: {CR}/04_specout/cross-module/SPO-{CR}-cross.md (if exists)
TODAY: {TODAY}
AUTHOR_NOTE: スペックアウト結果を反映。影響範囲・SP更新。
```

## Step C: Regenerate CRS Excel (UR-016)

Update `{CR}/progress.md` step 4 詳細ステップ → `Step C: Excel再生成中`.

Generate `{CR}/03_change-requirements/CRS-{CR}.xlsx` from the updated Markdown CRS using Bash/Python.
Follow the same Excel generation procedure as **Step C (Generate Excel Output)** in `xddp.03.req`.
The output workbook has one sheet `変更要求仕様書` with 16 columns:
`行種別` | `カテゴリ` | `要求ID` | `要求` | `ステータス` | `懸念・検討事項` | `理由` | `説明` | `要求グループ名` | `システム要求ID` | `システム要求` | `仕様グループ名` | `仕様ID` | `Before` | `After` | `備考`
Rows: UR / SR / SP 階層、末尾に未決事項・提案メモ行。

## Step D: Update progress.md
Step 4 (スペックアウト) → ✅ 完了, 詳細ステップ → `-`, link `SPO-{CR}.md`.
Step 5 (変更要求仕様書更新・TM作成) → ✅ 完了, 詳細ステップ → `-`.
  ※ TM は CRS 文書内に埋め込まれており、Step B で xddp-spec-writer-agent が更新している。
  ※ TM の完全性は xddp-reviewer が CRS レビュー時に確認済み（CRS チェックリスト項目4）。
Next command → `/xddp.05.arch {CR}`

## Step E: Report in Japanese
Report: entry points investigated, affected file count, number of SP items added/modified, review rounds for SPO.

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.04.specout.md` の要約も合わせて更新すること。
