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

  ## 図の作成ルール（Mermaid）

  このCRの変更内容を分析し、理解に最も効果的な図を **1〜3枚** 選んで Mermaid で作成すること。
  図は「1.1 システム全体への影響コンテキスト」または各案の「システム全体への影響」欄に配置する。

  ### 図種別の選択基準（複数選択可）

  | 変更の性質 | 推奨図種別 | Mermaid 記法 |
  |-----------|-----------|-------------|
  | 複数モジュール・クラス・ファイルに影響が波及する | **影響範囲図**（モジュール依存グラフ） | `graph LR` / `graph TD` |
  | データがどこで生成・変換・蓄積されるか、データの流れと処理の影響範囲を示したい | **DFD**（データフロー図） | `graph LR`（DFD記法で作成） |
  | コンポーネント間の呼び出し順序・通信フローが変わる | **シーケンス図** | `sequenceDiagram` |
  | データモデル・クラス構造が変わる（フィールド追加・継承変更等） | **クラス図** | `classDiagram` |
  | 処理の分岐・ループ・アルゴリズムが変わる | **フローチャート** | `flowchart TD` |
  | 状態遷移・ライフサイクルが変わる | **状態遷移図** | `stateDiagram-v2` |
  | DBスキーマ・テーブル構造が変わる | **ER図** | `erDiagram` |
  | タスク・フェーズの前後関係が変わる | **タイムライン / ガントチャート** | `timeline` / `gantt` |

  ### スタイリング規則（影響範囲図の場合）
  - 変更あり（影響あり）ノード：`classDef changed fill:#ffcccc,stroke:#cc0000`
  - 変更なし（影響なし）ノード：`classDef unchanged fill:#eeeeee,stroke:#999999`
  - 新規追加ノード：`classDef added fill:#ccffcc,stroke:#009900`

  ### DFD 記法ガイド（Mermaid `graph LR` で表現）
  MermaidにDFD専用記法はないため、以下の約束でDFDを表現すること。

  | DFD要素 | Mermaid表現 | 例 |
  |--------|------------|-----|
  | 外部エンティティ（入力元・出力先） | 角括弧ノード `[ ]` | `User["ユーザー"]` |
  | プロセス（処理・変換） | 丸括弧ノード `( )` | `P1("1.0 優先度バリデーション")` |
  | データストア | 二重角括弧ノード `[[ ]]` | `DS1[["tasks.json"]]` |
  | データフロー（矢印） | ラベル付き矢印 `-->` | `User -->|"add title --priority"| P1` |

  - プロセスIDは `1.0`, `2.0` のように番号を付ける
  - データフローのラベルにデータ名・パラメータ名を記述する
  - 変更が発生するプロセス・ストアには上記スタイリング規則（changed / added）を適用する

  ### 判断フロー
  1. CRS・SPO から変更の中心的な性質を特定する
  2. 上記表から該当する図種別を選ぶ（「変更なし」なら図は省略してよい）
  3. 複数の性質が混在する場合は最大3枚まで組み合わせる
  4. 図ごとにキャプション（例：「図1: モジュール影響範囲」）を付ける

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
