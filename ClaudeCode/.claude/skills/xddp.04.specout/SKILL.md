---
description: XDDP フェーズ2: スペックアウト（母体調査）を実施し、変更要求仕様書にフィードバックする。「スペックアウトして」「母体調査して」「影響範囲を調べて」などで起動する。
argument-hint: "[CR番号] [エントリポイント...]"
---

You are orchestrating **XDDP Step 04 — Specout (Motherbase Investigation) + Step 05 — CRS Update**.

> This step maps every ripple effect of the change. A missed dependency causes silent production failures that take days to diagnose. Orchestrate with thoroughness — leave no call chain unexamined.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) [ENTRY_POINTS...]
- First token: CR number (optional; auto-detected from XDDP_DIR if omitted)
- Remaining tokens (optional): entry point identifiers or file paths

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `ENTRY_POINTS` = `REST_ARGS` (may be empty). Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Build `REPOS_MAP` (repo name → path).
Let `REPOS_KEYS` = list of all repository names. Let `IS_MULTI` = (len(REPOS_KEYS) ≥ 2).

Read `DOCS_DIR` from `{WORKSPACE_ROOT}/xddp.config.md` (default: `baseline_docs`).
Let `DOCS` = `{WORKSPACE_ROOT}/{DOCS_DIR}`.

Read from `{WORKSPACE_ROOT}/xddp.config.md` (apply defaults if key absent):
- `EXCLUDE_PATTERNS`   = `SPECOUT_EXCLUDE_PATTERNS`   (default: `tests/,test/,__tests__/,spec/,specs/,__mocks__/,fixtures/,vendor/,node_modules/`)
- `INCLUDE_EXTENSIONS` = `SPECOUT_INCLUDE_EXTENSIONS`  (default: empty = all files)
- `MAX_WAVE_DEPTH`     = `SPECOUT_MAX_WAVE_DEPTH`       (default: `10`)

## Step 0: Identify Affected Repositories

`AFFECTED_REPOS` = all `REPOS_KEYS`.
`HAS_CROSS` = `IS_MULTI`.

(REPOS: in xddp.config.md lists only repositories potentially affected by this CR.
Specout all of them to determine actual impact.)

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

Read `{CR_PATH}/progress.md`. Set step 4 (スペックアウト) → 🔄 進行中, 詳細ステップ → `Step A: Discovery（探索）中`, today.
If `IS_MULTI`, append a per-repo progress table for step 4:
```markdown
## 工程4 スペックアウト進捗（リポジトリ別）
| リポジトリ | Discovery | Document | 完了日 |
|---|---|---|---|
{for each repo in AFFECTED_REPOS: | {repo} | ⏳ 未着手 | ⏳ 未着手 | - |}
{if HAS_CROSS: | cross | — | ⏳ 未着手 | - |}
```
Write back.

## Step A: Per-repo Specout — Discovery Phase

Update `{CR_PATH}/progress.md` 詳細ステップ → `Step A: Discovery（探索）中`.

For each `{repo}` in `AFFECTED_REPOS`, check `{CR_PATH}/04_specout/{repo}/checkpoint.md`:

| checkpoint.md 状態 | 対応 |
|---|---|
| ファイルが存在しない | 新規 Discovery を開始する |
| 状態: `in-progress` | Discovery エージェントが中断している。checkpoint.md の Visited/Frontier/Wave 番号を引数に加えて Discovery エージェントを再起動する |
| 状態: `paused-at-limit` | 最大波数上限に達して一時停止中（後述の paused-at-limit ハンドリングへ） |
| 状態: `paused-at-limit-2nd` | 2回目以降の上限到達。自動的に継続パス B を適用する（後述） |
| 状態: `complete` | Discovery 済み。Document フェーズへスキップ |

**paused-at-limit ハンドリング（継続パス A/B/C の選択）:**

状態が "paused-at-limit" の場合、人に対して以下を提示する:

> ⚠️ {repo} の Discovery が探索上限（{MAX_WAVE_DEPTH} 波）に達して一時停止しています。
> `{CR_PATH}/04_specout/{repo}/discovery-log.md` の残存フロンティア一覧を確認して、
> 以下 A/B/C のいずれかを選択してください:
>
> **A（フロンティア剪定・BFS 再開）:**
>   `{CR_PATH}/04_specout/{repo}/checkpoint.md` の Frontier から不要シンボルを削除し、
>   状態フィールドを `in-progress` に手動で書き換えてください。
>   その後 `/xddp.04.specout {CR}` を再実行すると、スキルが自動で Discovery を再起動します。
>   ※ Frontier の書式: HIGH シンボルは平文、MEDIUM シンボルは `symbol[MEDIUM:filepath]` 形式
>
> **B（モジュール一括記録）:**
>   残存フロンティアのシンボルが属するモジュール全体を `MODULE-LEVEL` として記録して Discovery を完了します。
>   「B を選択」と入力してください。
>
> **C（スコープ外承認）:**
>   残存フロンティアがスコープ外であることを確認した根拠を記録して Discovery を完了します。
>   「C を選択: {根拠}」と入力してください。

選択肢 B が選ばれた場合:
  1. checkpoint.md から Frontier を読み取り、各シンボルが所属するファイル・モジュールを特定する
  2. discovery-log.md に「⚠️ 継続パス B: 以下のモジュールは探索上限により一括記録。個別調査は設計・テスト工程で実施すること。」を記録する
  3. 該当モジュール配下の全ファイルを確定ファイル一覧に追加（確信度: MODULE-LEVEL）し discovery-log.md を更新する
  4. checkpoint.md の状態を "complete" に更新する

選択肢 C が選ばれた場合:
  1. discovery-log.md に「継続パス C: {ユーザーが提示した根拠}。残存フロンティアをスコープ外として承認。」を記録する
  2. checkpoint.md の状態を "complete" に更新する

**paused-at-limit-2nd ハンドリング（自動パス B）:**

状態が "paused-at-limit-2nd" の場合（エージェントが自動設定するが、エージェント終了前にクラッシュした場合の復旧用）:
  上記の選択肢 B と同じ手順を自動で適用する。

---

**Discovery エージェント呼び出し:**

`IS_MULTI` = true（マルチリポジトリ）の場合:
  Agent ツールで各リポジトリの Discovery を**並列呼び出し**する（各リポジトリは独立した discovery-log.md を持つため並列実行可能）。

`IS_MULTI` = false（シングルリポジトリ）の場合:
  順次呼び出しでよい。

For each `{repo}` in `AFFECTED_REPOS`（checkpoint 状態が "complete" 以外のもの）:

Let `MODULE_CATALOG_FILE` = `{DOCS}/{repo}/module-catalog.md`.
If `MODULE_CATALOG_FILE` does not exist: set `MODULE_CATALOG_FILE` = empty string.

Use the **Agent tool** with `subagent_type=xddp-specout-agent` and pass:
```
MODE: discovery
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
BASELINE_SPECS_DIR: {DOCS}/{repo}/specs/
CROSS_SPECS_DIR: {DOCS}/cross/specs/
DOCS: {DOCS}
ENTRY_POINTS: {ENTRY_POINTS}
SUMMARY_TEMPLATE: ~/.claude/skills/xddp.templates/04_specout-summary-template.md
MODULE_TEMPLATE: ~/.claude/skills/xddp.templates/04_specout-module-template.md
OUTPUT_DIR: {CR_PATH}/04_specout/{repo}/
TODAY: {TODAY}
EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}
INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS}
MAX_WAVE_DEPTH: {MAX_WAVE_DEPTH}
CHECKPOINT: {CR_PATH}/04_specout/{repo}/checkpoint.md
MODULE_CATALOG_FILE: {MODULE_CATALOG_FILE}
```

Discovery エージェント完了後、`{CR_PATH}/04_specout/{repo}/checkpoint.md` を再読みする。
状態が "paused-at-limit" の場合は上記の paused-at-limit ハンドリングを実施する。
状態が "complete" になったら Document フェーズへ進む。

per-repo progress table を更新: `| {repo} | ✅ 完了 | ⏳ 未着手 | - |`

## Step A-Document: Per-repo Specout — Document Phase

Update `{CR_PATH}/progress.md` 詳細ステップ → `Step A-Document: Documentation 中`.

Discovery が全リポジトリで "complete" になった後、各リポジトリを**順次**ドキュメント化する。

For each `{repo}` in `AFFECTED_REPOS`:

Use the **Agent tool** with `subagent_type=xddp-specout-agent` and pass:
```
MODE: document
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
LATEST_SPECS_DIR: {XDDP_DIR}/latest-specs/{repo}/
BASELINE_SPECS_DIR: {DOCS}/{repo}/specs/
CROSS_SPECS_DIR: {DOCS}/cross/specs/
ENTRY_POINTS: {ENTRY_POINTS}
SUMMARY_TEMPLATE: ~/.claude/skills/xddp.templates/04_specout-summary-template.md
MODULE_TEMPLATE: ~/.claude/skills/xddp.templates/04_specout-module-template.md
OUTPUT_DIR: {CR_PATH}/04_specout/{repo}/
TODAY: {TODAY}
EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}
INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS}
MAX_WAVE_DEPTH: {MAX_WAVE_DEPTH}
DISCOVERY_LOG: {CR_PATH}/04_specout/{repo}/discovery-log.md
```

Wait for completion. Agent creates:
- `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` — summary
- `{CR_PATH}/04_specout/{repo}/modules/` — per-module SPOs

Phase 3 検証スイープで未記録ヒットが発見された場合:
  エージェントがその旨を返す。スキルは人に対して:
  > ⚠️ {repo} の Phase 3 検証スイープで未記録ヒットが発見されました。
  > `{CR_PATH}/04_specout/{repo}/discovery-log.md` の「検証スイープ結果」を確認し、
  > 追加ドキュメント化するか、影響軽微として根拠を記録して承認してください。
  と伝え、承認されるまで待機する。

per-repo progress table を更新: `| {repo} | ✅ 完了 | ✅ 完了 | {TODAY} |`

Check if the agent emitted a scale warning (`SPECOUT_MAX_AFFECTED_FILES` exceeded). If so, relay to the user.

## Step A-cross: Cross-repo SPO Synthesis (only when HAS_CROSS = true)

Update progress table: `| cross | — | 🔄 進行中 | - |`

After all per-repo Document phases are complete, synthesise `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`:

Read all `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` files. Identify:
- Symbols, types, or functions from repo-A that are imported or called by repo-B
- HTTP API calls from one repo to another
- Shared data structures, event schemas, or message payloads
- Shared database tables (read/write by multiple repos)
- Shared constants, enum values, or macro definitions referenced across repos

Write `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` using `~/.claude/skills/xddp.templates/04_specout-cross-repo-template.md`:
- Section 2: リポジトリ間構造図 (Mermaid C4/component diagram)
- Section 3: リポジトリ間シーケンス図 (if `SPECOUT_SEQUENCE_LEVELS` includes `repository`)
- Section 4: 共有インタフェース一覧 (インタフェース名 / 提供リポジトリ / 消費リポジトリ / 型・プロトコル / バージョン / breaking変更有無 — 検出なしの場合は「なし」)
- Section 5: リポジトリ間共有定数・列挙値 (識別子 / 値 / 定義リポジトリ / 参照リポジトリ / 用途 — 検出なしの場合は「なし」)
- Section 6: リポジトリ間共有データ型関連図 (OOP言語: Mermaid classDiagram / 手続き型: テキスト表形式 — 共有データ型が検出された場合のみ。検出なしの場合は省略)
- Section 7: データアクセスマトリクス (full レベルのみ、または同一リソースへの並列書き込み・共有バッファアクセスが検出された場合)
- Section 8: データモデル（ER図・データ構造定義）(full レベルのみ、またはデータ構造変更がある場合。Mermaid `erDiagram` または `classDiagram`)
- Section 9: データフロー図（DFD）(リポジトリ間データフローが識別された場合のみ。識別されなかった場合は「対象外（理由：リポジトリ間データフローなし）」と記載)
- Section 10: 追加提案図 (タイミング図：リアルタイム・組み込み系プロジェクトでは★必須。その他は任意)
- Section 11: CRS への反映事項（cross）

If no inter-repo dependencies found → skip cross/ SPO creation; set `HAS_CROSS = false`.

Update progress table: `| cross | — | ✅ 完了 | {TODAY} |`

## Step A2: SPO Review Loop

Update `{CR_PATH}/progress.md` step 4 詳細ステップ → `Step A2: SPOレビュー中`.

Read `REVIEW_MAX_ROUNDS.SPO` from xddp.config.md (default: 3). Set `max_rounds` = that value.

For each `{repo}` in `AFFECTED_REPOS` (run review loops sequentially per repo):

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. **Agent tool** `subagent_type=xddp-reviewer`:
   ```
   DOCUMENT_TYPE: SPO
   NEXT_DOCUMENT_TYPE: DSN
   TARGET_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
   REFERENCE_FILES: [
     {CR_PATH}/01_requirements/ (all .md),
     {CR_PATH}/03_change-requirements/CRS-{CR}.md,
     （repo が "cross" 以外の場合のみ追加）{CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md,
     {CR_PATH}/04_specout/{repo}/modules/ (all .md, including subdirectories)
   ]
   REVIEW_ROUND: {round}
   OUTPUT_FILE: {CR_PATH}/04_specout/{repo}/review/04_specout-review.md
   ```

2. Read review file.
   - No 🔴/🟡 → `issues_remain = false`, exit loop.
   - 🔴/🟡 found, `round < max_rounds` → apply fixes, increment `round`, continue.
   - `round = max_rounds`, issues remain:
     1. Append `"⚠️ 未解決の重大指摘あり。人間の判断が必要です。"` to the review output file.
     2. Read `{CR_PATH}/progress.md`. In the `## 備考・メモ` section, append:
        `⚠️ 工程4: 未解決指摘あり（{CR_PATH}/04_specout/{repo}/review/04_specout-review.md）`
        If `## 備考・メモ` does not exist, create it at the end of the file before appending.
        Write back.
     Exit loop.

## Step A2-cross: Cross SPO AI Review (only when HAS_CROSS = true)

If `HAS_CROSS`:
  Update `{CR_PATH}/progress.md` step 4 詳細ステップ → `Step A2-cross: cross SPOレビュー中`.

  **Agent tool** `subagent_type=xddp-reviewer`:
  ```
  DOCUMENT_TYPE: SPO
  NEXT_DOCUMENT_TYPE: DSN
  TARGET_FILE: {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md
  REFERENCE_FILES: [
    {CR_PATH}/01_requirements/ (all .md),
    {CR_PATH}/03_change-requirements/CRS-{CR}.md,
    for each {repo} in AFFECTED_REPOS: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md (if exists)
  ]
  REVIEW_ROUND: 1
  OUTPUT_FILE: {CR_PATH}/04_specout/cross/review/04_specout-cross-review.md
  ```

  Read the review file. If 🔴/🟡 issues found: directly edit `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`
  to fix the issues (cross/ SPO has no dedicated fixer agent — fix inline). Output updated review summary.

  After fixing, re-read `{CR_PATH}/04_specout/cross/review/04_specout-cross-review.md` and count remaining 🔴 rows.
  If 🔴 items remain: warn the human:
  > ⚠️ cross/ SPO レビューで 🔴 指摘 {N} 件が残存しています。手動確認してください: `{CR_PATH}/04_specout/cross/review/04_specout-cross-review.md`

  注: cross/ SPO はインタフェース仕様に特化した成果物でサイズが小さく、1パスで修正が収束しやすい。
  per-repo の max_rounds ループは省略する（設計上の意図的省略）。

## Step A3: Human Review Gate (SPO)

Update `{CR_PATH}/progress.md` step 4 状態 → 👀 レビュー待ち, 詳細ステップ → `Step A3: 人レビュー待ち`.

Tell the user:
> ✅ SPOのAIレビューが完了しました。続いて人によるレビューをお願いします。
>
> **成果物:**
{for each repo in AFFECTED_REPOS:}
> - {repo}: `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`
>   - モジュール: `{CR_PATH}/04_specout/{repo}/modules/`
>   - Discovery ログ: `{CR_PATH}/04_specout/{repo}/discovery-log.md`
>   - AIレビュー: `{CR_PATH}/04_specout/{repo}/review/04_specout-review.md`
{if HAS_CROSS:}
> - cross: `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`
>   - AIレビュー: `{CR_PATH}/04_specout/cross/review/04_specout-cross-review.md`
>
> **修正方法：**
> - 直接ファイルを編集する
> - AIに修正を依頼する場合: `/xddp.revise {CR} specout`（対象リポジトリを指定）
>
> レビューと修正が完了したら「**レビュー完了**」と入力してください。

Wait for the user to confirm.

If the user made any changes:
- Run one final AI review pass per repo (same as Step A2 but `REVIEW_ROUND = last_round + 1`).
- If HAS_CROSS and the user changed cross/ SPO: run one final AI review pass for cross SPO
  (same as Step A2-cross but `REVIEW_ROUND = last_round + 1`).

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

Let `CRS_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.md`.
Let `EXCEL_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.xlsx`.
Run via Bash: `python ~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py {CRS_PATH} {EXCEL_PATH}`
If `crs_md2excel.py` not found: tell the user to run `setup.sh`. If errors: display to user.
Report output path and UR/SR/SP counts from script stdout.

> **Design policy:** The sole definition of the Excel format is in `~/.claude/skills/xddp.md2excel.md` and `~/.claude/skills/xddp.md2excel/scripts/crs_md2excel.py`.
> To change the format, modify only xddp.md2excel.md and crs_md2excel.py.
> **成果物の位置付け:** `CRS-{CR}.xlsx` は人間向け確認ツール（一時生成物）。xddp.close の DOCS_DIR 昇格対象外。

## Step D: Update progress.md

Step 4 (スペックアウト) → ✅ 完了, 詳細ステップ → `-`.
  Also remove all lines starting with `⚠️ 工程4:` from `## 備考・メモ` in `{CR_PATH}/progress.md` (no-op if none).
Step 5 (変更要求仕様書更新・TM作成) → ✅ 完了, 詳細ステップ → `-`.
Next command → `/xddp.05.arch {CR}`

## Step E: Report in Japanese
Report: repos investigated, waves executed per repo, affected file count per repo, cross/ synthesis result, review rounds.
