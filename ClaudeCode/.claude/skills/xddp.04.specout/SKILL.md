---
description: XDDP フェーズ2: スペックアウト（母体調査）を実施し、変更要求仕様書にフィードバックする。「スペックアウトして」「母体調査して」「影響範囲を調べて」などで起動する。
argument-hint: "[CR番号] [--re-discover] [エントリポイント...]"
---

You are orchestrating **XDDP Step 04 (process steps 4a-4b) — Specout (Motherbase Investigation) + CRS Update**.

> This step maps every ripple effect of the change. A missed dependency causes silent production failures that take days to diagnose. Orchestrate with thoroughness — leave no call chain unexamined.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) [--re-discover] [ENTRY_POINTS...]
- First token: CR number (optional; auto-detected from XDDP_DIR if omitted)
- `--re-discover`: optional flag (position-independent; recognized wherever it appears in $ARGUMENTS).
  Re-runs BFS Discovery from new ENTRY_POINTS while carrying over the existing visited set
  from a completed run. Requires at least one ENTRY_POINT.
- Remaining tokens (optional): entry point identifiers or file paths

---

**Pre-check（CR 解決前に実施。`$ARGUMENTS` 全体が `--re-discover` のみで他に一切トークンがない、
という完全に曖昧性のないケースのみを対象とするため、CR 番号の解決有無によらず判定結果が変わらない）:**
Scan raw `$ARGUMENTS` tokens for the exact string `--re-discover` (position-independent).
If found and removing `--re-discover` from `$ARGUMENTS` leaves zero remaining tokens
(i.e. `$ARGUMENTS` consisted solely of `--re-discover`, with no CR number and no entry point):
  Tell the user: "`--re-discover` を指定する場合は追加調査するエントリポイント（シンボル名またはファイルパス）を
  1つ以上指定してください。例: `/xddp.04.specout <CR番号> --re-discover newSymbol`"
  Stop.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.

Scan `REST_ARGS` tokens for the exact string `--re-discover` (position-independent):
If found:
  Set `RE_DISCOVER = true`.
  Remove the `--re-discover` token from `REST_ARGS`; remaining tokens become the new `REST_ARGS`.
  If remaining `REST_ARGS` is empty:
    Tell the user: "`--re-discover` を指定する場合は追加調査するエントリポイント（シンボル名またはファイルパス）を
    1つ以上指定してください。例: `/xddp.04.specout {CR} --re-discover newSymbol`"
    Stop.
Else:
  Set `RE_DISCOVER = false`.
Let `ENTRY_POINTS` = `REST_ARGS` (may be empty). Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
DOCS_DIR, DOCS, REPOS_MAP, REPOS_KEYS, IS_MULTI, DEVELOPMENT_MODE, EXCLUDE_PATTERNS, INCLUDE_EXTENSIONS,
MAX_WAVE_DEPTH.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step -1: DEVELOPMENT_MODE Check

If `DEVELOPMENT_MODE` = `new`:

1. Read `{CR_PATH}/progress.md`.
   - Set 工程4a（スペックアウト）→ ⏭️ スキップ（対象外）, 詳細ステップ → `-`, today.
   - Set 工程4b（変更要求仕様書更新・TM作成）→ ⏭️ スキップ（対象外）, 詳細ステップ → `-`, today.
   - 次に実行すべきコマンド → `/xddp.05.arch {CR}`
   - `## 備考・メモ` に以下を追記（セクションがなければ末尾に作成）:
     `ℹ️ 工程4a・4b: DEVELOPMENT_MODE=new のためスキップ（母体コードが存在しないため波及調査を省略）`
   - Write back.
2. Tell the user (Japanese):
   > ℹ️ `DEVELOPMENT_MODE: new`（新規開発モード）が設定されています。
   > 工程4a（スペックアウト）と工程4b（CRS更新・TM作成）は母体コードの波及調査を行う工程であるため、新規開発時はスキップします。
   > 工程5（実装方式検討）では母体コードが存在しない前提で実装方式を検討します。
   >
   > **次のコマンド:** `/xddp.05.arch {CR}`
3. Stop (do not execute Step 0 or later).

（`REPOS_MAP`/`REPOS_KEYS`/`IS_MULTI`/`DOCS`/`EXCLUDE_PATTERNS`/`INCLUDE_EXTENSIONS`/`MAX_WAVE_DEPTH` は
CR Resolution で取得済みのためここでの再読み取りは不要）

## Step 0: Identify Affected Repositories

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`.
`HAS_CROSS` = `IS_MULTI`.
（本工程はこの時点で cross 成果物がまだ存在しないため、他工程のような「cross 成果物ファイルの
存在チェック」ではなく IS_MULTI による仮決定を用いる。Discovery 完了後、リポジトリ間依存が
見つからなければ Step で `HAS_CROSS = false` に降格する（`SKILL.md:292` 付近）。xddp.common
「## Resolve HAS_CROSS」の対象外 — 詳細は同プロシージャの「適用外」注記を参照）

(REPOS: in xddp.config.md lists only repositories potentially affected by this CR.
Specout all of them to determine actual impact.)

## Step 0.5 (confirmation gate): Present scope to user

> Confirmation gate is executed before marking progress, to avoid polluting progress.md on cancellation.

Tell the user:
> 以下のリポジトリを対象にスペックアウト（工程4a）を開始します:
> {AFFECTED_REPOS リスト（各行に - {repo名} を表示）}
> リポジトリ間連携: {HAS_CROSS ? "あり（cross/ 成果物を生成します）" : "なし（cross/ 生成なし）"}
>
> よろしければ「OK」と入力してください。対象リポジトリを変更する場合は指定してください。

Wait for user response. If the user specifies different repos, update `AFFECTED_REPOS` accordingly.

## Step 0.6: Mark In-Progress

Read `{CR_PATH}/progress.md`. Set step 4a (スペックアウト) → 🔄 進行中, 詳細ステップ → `Step A: Discovery（探索）中`, today.
If `IS_MULTI`, append a per-repo progress table for step 4a:
```markdown
## 工程4a スペックアウト進捗（リポジトリ別）
| リポジトリ | Discovery | Document | 完了日 |
|---|---|---|---|
{for each repo in AFFECTED_REPOS: | {repo} | ⏳ 未着手 | ⏳ 未着手 | - |}
{if HAS_CROSS: | cross | — | ⏳ 未着手 | - |}
```
Write back.

## Step A: Per-repo Specout — Discovery Phase

Update `{CR_PATH}/progress.md` 詳細ステップ → `Step A: Discovery（探索）中`.

For each `{repo}` in `AFFECTED_REPOS`, check `{CR_PATH}/04_specout/{repo}/checkpoint.md`:

| checkpoint.md 状態 | RE_DISCOVER | 対応 |
|---|---|---|
| ファイルが存在しない | false | 新規 Discovery を開始する |
| ファイルが存在しない | true | 既存 visited セットなし。新規 Discovery として開始する（ユーザーに通知: "既存の探索履歴が存在しないため新規 Discovery として実行します"） |
| 状態: `in-progress` | false | Discovery エージェントが中断している。checkpoint.md の Visited/Frontier/Wave 番号を引数に加えて Discovery エージェントを再起動する |
| 状態: `in-progress` | true | ENTRY_POINTS を checkpoint.md の既存 Frontier にマージ（HIGH 平文形式で追記）してから Discovery エージェントを再起動する |
| 状態: `paused-at-limit` | false | 最大波数上限に達して一時停止中（後述の paused-at-limit ハンドリングへ） |
| 状態: `paused-at-limit` | true | ENTRY_POINTS を checkpoint.md の既存 Frontier にマージしてから paused-at-limit ハンドリングへ |
| 状態: `paused-at-limit-2nd` | any | 2回目以降の上限到達。自動的に継続パス B を適用する（後述） |
| 状態: `complete` | false | Discovery 済み。Document フェーズへスキップ |
| 状態: `complete` | **true** | **re-discover 処理を実施する（下記参照）** |

**【re-discover 処理（RE_DISCOVER = true かつ checkpoint 状態 = complete の場合）】**

1. `{CR_PATH}/04_specout/{repo}/checkpoint.md` を読み取り、
   既存の `Visited` セットと `最終完了 Wave` 番号（= N）を取得する。
2. checkpoint.md を以下の内容で上書きする（フィールド名は xddp-specout-agent.md Step 2d 準拠）:
   - 状態: `in-progress`
   - Visited: 既存の Visited セットをそのまま保持（平文改行区切り）
   - Frontier: ENTRY_POINTS の各シンボルを HIGH 平文形式（1行1シンボル）で設定
   - 現在 Wave 番号: N（最終完了 Wave の番号をそのまま設定。Wave 書き込み完了 = true との組み合わせで
     エージェントが自動的に Wave N+1 から再開するため、ここで +1 しない）
   - Wave 書き込み完了: `true`（エージェントの再開ロジック「Wave N は完了済み → Wave N+1 から継続（discovery-log.md に追記）」
     を利用するため `true` を設定する。`false` にするとエージェントが Wave N を書き直す動作になり不正な重複が生じる）
   - 上限到達回数: `0`（前回サイクルとは独立した新しい BFS セッションとして扱うためリセット。
     リセットしない場合、前回の上限到達回数を引き継いで不要な自動パス B 移行が発生しうる）
3. `{CR_PATH}/04_specout/{repo}/discovery-log.md` の末尾に以下を追記する
   （手順5のエージェント呼び出しより先に実行すること。エージェントが Wave N+1 を追記モードで書くため、
   マーカーはその直前に置く必要がある）:
   ```
   ---
   ## [re-discover] セッション開始: {TODAY}
   追加エントリポイント: {ENTRY_POINTS}
   Wave {N + 1} から再開（既存 visited セット引き継ぎ）
   ```
4. progress.md の `## 備考・メモ` に以下を追記する（セクションがなければ末尾に作成）:
   `re-discover 実施（{TODAY}）追加エントリポイント: {ENTRY_POINTS}`
   （備考追記は checkpoint 状態 = complete の場合のみ。checkpoint なし・in-progress・paused の場合は追記しない）
5. Discovery エージェントを通常通り呼び出す（エージェントは `in-progress` として再開ロジックを実行し、
   Wave N+1 から BFS を継続する）。

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
SUMMARY_TEMPLATE: ~/.claude/skills/xddp.04.specout/templates/04_specout-summary-template.md
MODULE_TEMPLATE: ~/.claude/skills/xddp.04.specout/templates/04_specout-module-template.md
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
SUMMARY_TEMPLATE: ~/.claude/skills/xddp.04.specout/templates/04_specout-summary-template.md
MODULE_TEMPLATE: ~/.claude/skills/xddp.04.specout/templates/04_specout-module-template.md
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

Write `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` using `~/.claude/skills/xddp.04.specout/templates/04_specout-cross-repo-template.md`:
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

Update `{CR_PATH}/progress.md` step 4a 詳細ステップ → `Step A2: SPOレビュー中`.

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
     （repo が "cross" 以外の場合のみ追加）{CR_PATH}/04_specout/{repo}/discovery-log.md,
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
        `⚠️ 工程4a: 未解決指摘あり（{CR_PATH}/04_specout/{repo}/review/04_specout-review.md）`
        If `## 備考・メモ` does not exist, create it at the end of the file before appending.
        Write back.
     Exit loop.

## Step A2-cross: Cross SPO AI Review (only when HAS_CROSS = true)

If `HAS_CROSS`:
  Update `{CR_PATH}/progress.md` step 4a 詳細ステップ → `Step A2-cross: cross SPOレビュー中`.

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

Build `ARTIFACTS_TEXT` by expanding the following (AFFECTED_REPOS/HAS_CROSS are already resolved
in this skill's scope; the expanded result is a plain multi-line string, not a template):
```
**成果物:**
{for each repo in AFFECTED_REPOS:}
- {repo}: `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`
  - モジュール: `{CR_PATH}/04_specout/{repo}/modules/`
  - Discovery ログ: `{CR_PATH}/04_specout/{repo}/discovery-log.md`
  - AIレビュー: `{CR_PATH}/04_specout/{repo}/review/04_specout-review.md`
{if HAS_CROSS:}
- cross: `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`
  - AIレビュー: `{CR_PATH}/04_specout/cross/review/04_specout-cross-review.md`
```

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Human Review Gate" with:
  CR_PATH: {CR_PATH}
  STEP_NUM: 4a
  STEP_LABEL: `Step A3`
  ARTIFACTS_TEXT: {built above}
  REVISE_COMMAND: `/xddp.revise {CR} specout`（対象リポジトリを指定）
→ let `CHANGED`.

If `CHANGED`:
- Run one final AI review pass per repo (same as Step A2 but `REVIEW_ROUND = last_round + 1`).
- If HAS_CROSS and the user changed cross/ SPO: run one final AI review pass for cross SPO
  (same as Step A2-cross but `REVIEW_ROUND = last_round + 1`).

## Step B: Update CRS with Specout Findings

Update `{CR_PATH}/progress.md` step 4a 状態 → 🔄 進行中, 詳細ステップ → `Step B: CRS更新中`. Also set step 4b → 🔄 進行中.

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

Update `{CR_PATH}/progress.md` step 4a 詳細ステップ → `Step C: Excel再生成中`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Regenerate CRS Excel" with:
  CR_PATH: {CR_PATH}
  CR: {CR}

## Step D: Update progress.md

Step 4a (スペックアウト) → ✅ 完了, 詳細ステップ → `-`.
  Also remove all lines starting with `⚠️ 工程4a:` from `## 備考・メモ` in `{CR_PATH}/progress.md` (no-op if none).
Step 4b (変更要求仕様書更新・TM作成) → ✅ 完了, 詳細ステップ → `-`.
Next command → `/xddp.05.arch {CR}`

## Step E: Report in Japanese
Report: repos investigated, waves executed per repo, affected file count per repo, cross/ synthesis result, review rounds.
