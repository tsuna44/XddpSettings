---
description: XDDP フェーズ3: 実装方式検討メモ（DSN）を作成し、AIレビュー→修正ループを実施する。「方式検討して」「実装方針を決めて」などで起動する。
---

You are orchestrating **XDDP Step 05 (process step 06) — Implementation Approach Design**.

**Arguments:** $ARGUMENTS = CR_NUMBER

---

Let `CR` = $ARGUMENTS. Let `TODAY` = today's date.

## Step 0: Mark In-Progress
Read `{CR}/progress.md`. Set step 6 (実装方式検討) → 🔄 進行中, 詳細ステップ → `Step A: DSN生成中`, today. Write back.

## Step A0: 知見ログの参照

`lessons-learned.md`（プロジェクトルート）が存在する場合、読み込む。
`#方式検討` `#設計` `#リスク` `#依存関係` タグを持つエントリに注目し、
過去の CR で採用・不採用になった方式の教訓を確認する。
該当する知見があれば、architect-agent へ渡す際の `LESSONS_CONTEXT` に含める。

## Step A: Generate Architecture Memo

**Agent tool** `subagent_type=xddp-architect-agent`:
```
CR_NUMBER: {CR}
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
SPO_FILE: {CR}/04_specout/SPO-{CR}.md
SPO_MODULES_DIR: {CR}/04_specout/modules/
SPO_CROSS_MODULE_FILE: {CR}/04_specout/cross-module/SPO-{CR}-cross.md (if exists)
TEMPLATE_FILE: ~/.claude/templates/05_design-approach-memo-template.md
OUTPUT_FILE: {CR}/05_architecture/DSN-{CR}.md
TODAY: {TODAY}
LESSONS_CONTEXT: {lessons-learned.md から抽出した #方式検討 #設計 #リスク #依存関係 タグのエントリ。なければ空}
ALTERNATIVES_TASK: |
  セクション「1.1 システム全体への影響コンテキスト」を必ず埋めること。
  CRS・SPO を読み、関連モジュール・データフロー・既存API・非機能要件への影響を把握した上で各案を検討すること。

  セクション「2. 実装方式の候補」では必ず3案以上を検討すること。
  各案は以下の軸を意識して実質的に異なるアプローチにすること：
    - Where（変更を吸収する場所）：呼び出し元 / 呼び出し先 / 新レイヤー挿入
    - Depth（変更の深さ）：最小変更 / 部分リファクタリング / 抜本的再設計
    - Coupling（依存の持ち方）：既存拡張 / 新規独立 / 共通化
    - When（処理タイミング）：同期 / 非同期・イベント駆動 / バッチ
    - How（技術・パターン）：既存スタック / 新パターン / OSS活用
  案の名称は内容を端的に表す名前にする（例：「既存クラス拡張案」「新規サービス分離案」「ミドルウェア活用案」）。
  各案の「システム全体への影響」欄に、他モジュール・インターフェースへの波及を記述すること。

  セクション「3. 方式比較（QCD）」の Q / C / D 各表をすべての案の列で埋めること。
  評価は ◎ / ○ / △ / ✕ で記入し、根拠を採用方式セクションに反映すること。
```

## Step B: Review Loop (max 5 iterations)

Update `{CR}/progress.md` step 6 詳細ステップ → `Step B: AIレビュー中`.

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ 5`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: DSN
   TARGET_FILE: {CR}/05_architecture/DSN-{CR}.md
   REFERENCE_FILES: [{CR}/03_change-requirements/CRS-{CR}.md, {CR}/04_specout/SPO-{CR}.md]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR}/review/05_architecture-review.md
   ```

2. Read review.
   - No 🔴/🟡 → exit.
   - Issues found, `round < 5` → use **Agent tool** `subagent_type=xddp-architect-agent` to apply fixes:
     ```
     CR_NUMBER: {CR}
     OUTPUT_FILE: {CR}/05_architecture/DSN-{CR}.md
     REVIEW_FILE: {CR}/review/05_architecture-review.md
     TODAY: {TODAY}
     ```
     Increment `round`.
   - `round = 5`, issues remain → append warning to review file.

## Step B2: Human Review Gate

Update `{CR}/progress.md` step 6 状態 → 👀 レビュー待ち, 詳細ステップ → `Step B2: 人レビュー待ち`.

Tell the user:
> ✅ AIレビューが完了しました。続いて人によるレビューをお願いします。
> - 成果物: `{CR}/05_architecture/DSN-{CR}.md`
> - AIレビュー結果: `{CR}/review/05_architecture-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} arch`
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。
> 変更がなければそのまま「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes (edited the file or ran `/xddp.revise`):
- Run one final AI review pass using **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: DSN
  TARGET_FILE: {CR}/05_architecture/DSN-{CR}.md
  REFERENCE_FILES: [{CR}/03_change-requirements/CRS-{CR}.md, {CR}/04_specout/SPO-{CR}.md]
  REVIEW_ROUND: (last_round + 1)
  OUTPUT_FILE: {CR}/review/05_architecture-review.md
  ```
- Read the review file. If 🔴 issues remain, inform the user and ask whether to fix again or proceed.

## Step C: Feed Architecture Decision Back to CRS

Update `{CR}/progress.md` step 6 状態 → 🔄 進行中, 詳細ステップ → `Step C: CRSフィードバック中`.

Read `{CR}/05_architecture/DSN-{CR}.md`. From the adopted approach, identify items not yet reflected in the CRS:

- 採用方式によって**不要になった要求・仕様**（削除・ステータス変更候補）
- 採用方式によって**新たに判明した制約・非機能要件・インタフェース仕様**
- 採用方式によって**スコープ外となったモジュール・機能**

変更項目が**ない場合はスキップ**。変更項目がある場合:

**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update
CRS_FILE: {CR}/03_change-requirements/CRS-{CR}.md
SPO_FILE: (not needed here, pass empty)
CHD_FEEDBACK: (採用方式に基づく変更項目リスト。削除・追加・修正を区別して列挙)
TODAY: {TODAY}
AUTHOR_NOTE: 方式検討フィードバックを反映。採用方式に基づく要求・仕様の追加／削除／変更。
```

## Step D: Regenerate CRS Excel (UR-016)

Step C で CRS を更新した場合のみ、`{CR}/03_change-requirements/CRS-{CR}.xlsx` を再生成する。
`xddp.03.req` の **Step C (Generate Excel Output)** と同じ手順で実施。
出力ワークブックは1シート `変更要求仕様書`、16列:
`行種別` | `カテゴリ` | `要求ID` | `要求` | `ステータス` | `懸念・検討事項` | `理由` | `説明` | `要求グループ名` | `システム要求ID` | `システム要求` | `仕様グループ名` | `仕様ID` | `Before` | `After` | `備考`
Rows: UR / SR / SP 階層、末尾に未決事項・提案メモ行。

## Step E: Update progress.md
Step 6 (実装方式検討) → ✅ 完了, 詳細ステップ → `-`. Next command → `/xddp.06.design {CR}`

## Step F: Report in Japanese

---
> **保守メモ:** このファイルを変更した場合は、`.claude/commands/xddp.05.arch.md` の要約も合わせて更新すること。
