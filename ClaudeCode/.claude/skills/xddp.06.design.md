---
description: XDDP フェーズ3: 変更設計書（CHD）を作成し、AIレビュー→修正ループ＋変更要求仕様書へのフィードバックを実施する。「変更設計書を作って」「設計書を書いて」などで起動する。
---

You are orchestrating **XDDP Step 06 (process steps 07-08) — Change Design Document + CRS Feedback**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

## Step 0: Mark In-Progress
Read `{CR}/progress.md`. Set step 7 (変更設計書作成) → 🔄 進行中, 詳細ステップ → `Step A: CHD生成中`, today. Write back.

## Step A: Generate Change Design Document

**Agent tool** `subagent_type=xddp-designer-agent`:
```
CR_NUMBER: {CR}
DSN_FILE: {CR}/05_architecture/DSN-{CR}.md
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR}/04_specout/SPO-{CR}.md
SPO_MODULES_DIR: {CR}/04_specout/modules/
TEMPLATE_FILE: ~/.claude/templates/06_change-design-document-template.md
OUTPUT_FILE: {CR}/06_design/CHD-{CR}.md
TODAY: {TODAY}
DESIGN_TASK: |
  ## 詳細設計（第3章）の記述ルール

  第3章は **仕様（SP）単位** で記述すること。ファイル単位で章を分けてはならない。

  ### 構成ルール
  - 各サブセクションの見出しは「SP-{番号}：{仕様名}」とする
  - CRS の SP を順番に走査し、設計内容のある SP をすべて記述する
  - 1つの SP が複数ファイルにまたがる場合は、そのセクション内でファイルごとにBefore/Afterを記述する
  - 変更のないファイルはこの章に記載しない
  - ファイル単位の全体像はセクション2「変更対象ファイル一覧」が担う

  ### Before/After の記述方針
  - Before：該当箇所のみを抜粋する（ファイル全体を貼らない）
  - After：変更後の該当箇所を記述する
  - 新規追加の場合は Before を「（新規追加）」と記載する
  - 変更箇所の説明は箇条書きで「何をどう変えるか」を明記する

  ### トレーサビリティマトリクス（第4章）
  全SP × 変更ファイル × 変更関数の対応表を必ず作成する。
  第3章の記述と整合していること。

  ## 図の作成ルール（Mermaid）

  **基本方針：CHD の図は DSN の図より狭いスコープ（SP単位の実装詳細）を担う。**
  DSN でシステム全体の影響範囲は既に示されているため、CHD の図は
  「Before/Afterコードだけでは構造変化が読み取りにくい場合」にのみ追加する。

  ### 図を追加する判断基準（いずれかに該当する場合のみ）

  | 判断基準 | 図種別 | Mermaid 記法 |
  |---------|--------|-------------|
  | 継承・実装関係を持つクラス階層が変わる | **クラス図** | `classDiagram` |
  | 3つ以上の関数をまたぐ呼び出しチェーンが変わる | **関数呼び出し図** | `graph LR` |
  | コンポーネント間の処理順序・非同期フローが変わる | **シーケンス図** | `sequenceDiagram` |
  | 条件分岐・ループを含む制御フローが変わる | **フローチャート** | `flowchart TD` |
  | 状態遷移・ライフサイクルが変わる | **状態遷移図** | `stateDiagram-v2` |
  | テーブル・スキーマのリレーションが変わる | **ER図** | `erDiagram` |

  ### 省略してよいケース（Before/Afterコードで十分）
  - フィールド・引数の単純追加（型・名前・デフォルト値が自明）
  - 関数シグネチャの変更のみ（呼び出し構造は変わらない）
  - ローカル変数の追加・条件式の変更

  ### 図を追加する場合の方針
  - Before/Afterの直後、または「変更箇所の説明」の後に配置する
  - 変更前後で構造が変わる場合は Before図・After図を並べる（差分が小さければ After図のみ）
  - キャプション例：「図: cmd_list 呼び出しフロー（変更後）」
  - スタイリング：変更箇所 `fill:#ffcccc,stroke:#cc0000`、新規追加 `fill:#ccffcc,stroke:#009900`
```

Check for scale warning (>500 lines changed). If present, relay to user.

## Step B: Review Loop (max 5 iterations)

Update `{CR}/progress.md` step 7 詳細ステップ → `Step B: AIレビュー中`.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ 5`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: CHD
   TARGET_FILE: {CR}/06_design/CHD-{CR}.md
   REFERENCE_FILES: [{CR}/03_change-requirements/CRS-{CR}.md, {CR}/04_specout/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR}/review/06_design-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit loop.
   - Issues found, `round < 5` → use **Agent tool** `subagent_type=xddp-designer-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     OUTPUT_FILE: {CR}/06_design/CHD-{CR}.md
     REVIEW_FILE: {CR}/review/06_design-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = 5`, issues remain → append warning to review file.

## Step B2: Human Review Gate

Update `{CR}/progress.md` step 7 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR}/06_design/CHD-{CR}.md`
> - AIレビュー結果: `{CR}/review/06_design-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} design`
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。
> 変更がなければそのまま「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes (edited the file or ran `/xddp.revise`):
- Run one final AI review pass using **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: CHD
  TARGET_FILE: {CR}/06_design/CHD-{CR}.md
  REFERENCE_FILES: [{CR}/03_change-requirements/CRS-{CR}.md, {CR}/04_specout/SPO-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR}/review/06_design-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Feed Design Results Back to CRS

Update `{CR}/progress.md` step 7 状態 → 🔄 進行中, step 8 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

Read `{CR}/06_design/CHD-{CR}.md`. Identify any new constraints, interface specs, or error conditions not yet in the CRS. If found:

**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
SPO_FILE: (not needed here, pass empty)
CHD_FEEDBACK: (list the new items found)
TODAY: {TODAY}
AUTHOR_NOTE: 設計フィードバックを反映。SP・影響範囲更新。
```

## Step D: Regenerate CRS Excel (UR-016)

If Step C added any items to the CRS, regenerate `{CR}/03_change-requirements/CRS-{CR}.xlsx` from the updated Markdown CRS.
Follow the same Excel generation procedure as **Step C (Generate Excel Output)** in `xddp.03.req`.
The output workbook has one sheet `変更要求仕様書` with 16 columns:
`行種別` | `カテゴリ` | `要求ID` | `要求` | `ステータス` | `懸念・検討事項` | `理由` | `説明` | `要求グループ名` | `システム要求ID` | `システム要求` | `仕様グループ名` | `仕様ID` | `Before` | `After` | `備考`
Rows: UR / SR / SP 階層、末尾に未決事項・提案メモ行。

## Step E: Update progress.md
Step 7 (変更設計書作成) → ✅ 完了, 詳細ステップ → `-`.
Step 8 (変更要求仕様書フィードバック) → ✅ 完了, 詳細ステップ → `-`.
Next command → `/xddp.07.code {CR}`

## Step F: Report in Japanese

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.06.design.md` の要約も合わせて更新すること。
