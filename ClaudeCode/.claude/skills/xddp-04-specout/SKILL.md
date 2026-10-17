---
name: xddp-04-specout
description: XDDP フェーズ2: スペックアウト（母体調査）を実施し、変更要求仕様書にフィードバックする。「スペックアウトして」「母体調査して」「影響範囲を調べて」などで起動する。
argument-hint: "[CR番号] [エントリポイント...]"
---

You are orchestrating **XDDP Step 04 (process steps 4a-4b) — Specout (Motherbase Investigation) + CRS Update**.

> This step maps every ripple effect of the change. A missed dependency causes silent production failures that take days to diagnose. Orchestrate with thoroughness — leave no call chain unexamined.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) [ENTRY_POINTS...]
- First token: CR number (optional; auto-detected from XDDP_DIR if omitted)
- Remaining tokens (optional): entry point identifiers or file paths

工程4a の完了後にシンボルを足して調べる・調査を採用する・取り消す場合は `/xddp-investigate` を使う。

---

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.

Let `ENTRY_POINTS` = `REST_ARGS` (may be empty). Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp-common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
DOCS_DIR, DOCS, REPOS_MAP, REPOS_KEYS, IS_MULTI, DEVELOPMENT_MODE, EXCLUDE_PATTERNS, INCLUDE_EXTENSIONS,
MAX_WAVE_DEPTH, SPECOUT_MAX_AFFECTED_FILES, SPECOUT_MAX_FILES_PER_MODULE, SPECOUT_DIAGRAM_LEVEL,
SPECOUT_SEQUENCE_LEVELS, SPECOUT_BACKEND, SPECOUT_BACKEND_OVERRIDES, SPECOUT_HIT_FILTER,
SPECOUT_CROSS_PROPAGATE, SPECOUT_CLASSIFY_CHUNK_SIZE, SPECOUT_CLASSIFY_PARALLEL, SPECOUT_SEED_GATE,
SPECOUT_WAVE_HIT_BUDGET, SPECOUT_LLM_HIT_BUDGET, SPECOUT_SLICE, SPECOUT_SLICE_IGNORE_CALLS, SPECOUT_SLICE_H_AS,
SPECOUT_SLICE_PYTHON_BIN, CR_PROFILE.
`SPECOUT_HIT_FILTER` は未指定時 `conservative`。`SPECOUT_CLASSIFY_CHUNK_SIZE` は未指定時 `40`、
`SPECOUT_CLASSIFY_PARALLEL` は未指定時 `4`。`SPECOUT_SEED_GATE` は未指定時 `true`。`MAX_WAVE_DEPTH` は未指定時 `6`、
`SPECOUT_WAVE_HIT_BUDGET` は未指定時 `10000`、`SPECOUT_LLM_HIT_BUDGET` は未指定時 `160`、`SPECOUT_SLICE` は未指定時 `auto`、
`SPECOUT_SLICE_IGNORE_CALLS` は未指定時 空、`SPECOUT_SLICE_H_AS` は未指定時 `auto`、`SPECOUT_SLICE_PYTHON_BIN` は未指定時 空、
`SPECOUT_MAX_AFFECTED_FILES` は未指定時 `20`（変更の中心として扱うファイル数の目安。Step A-Document の CR 分割の警告と、
追加下調べの上限〔repo ごとの累計〕に使う）。)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step -1: DEVELOPMENT_MODE Check

If `DEVELOPMENT_MODE` = `new`:

1. Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
     CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: ⏭️ スキップ（対象外）, DETAIL_STEP: `-`
   Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
     CR_PATH: {CR_PATH}, STEP_NUM: 4b, STATE: ⏭️ スキップ（対象外）, DETAIL_STEP: `-`
   - If `CR_PROFILE` = `quick`:
       Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
         CR_PATH: {CR_PATH}, STEP_NUM: 5, STATE: ⏭️ スキップ（対象外）, DETAIL_STEP: `-`
       （`new` では cross SPO が生成されないため §3.8 の cross DSN 分岐に入らず、工程5は完全に
       スキップされる。この経路では `/xddp-05-arch` を起動しないため、ここで記録しないと工程5が
       `⬜ 未着手` のまま残る）
   - 次に実行すべきコマンド → （`CR_PROFILE` = `quick` の場合）`/xddp-06-design {CR}` ／
     （それ以外）`/xddp-05-arch {CR}`
   - Run via Bash:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py history-add --cr-path {CR_PATH} --step 4a --text "ℹ️ 工程4a・4b: DEVELOPMENT_MODE=new のためスキップ（母体コードが存在しないため波及調査を省略）"`
2. Tell the user (Japanese):
   > ℹ️ `DEVELOPMENT_MODE: new`（新規開発モード）が設定されています。
   > 工程4a（スペックアウト）と工程4b（CRS更新）は母体コードの波及調査を行う工程であるため、新規開発時はスキップします。
   {If CR_PROFILE ≠ quick: > 工程5（実装方式検討）では母体コードが存在しない前提で実装方式を検討します。}
   >
   > **次のコマンド:** （`CR_PROFILE` = `quick` の場合）`/xddp-06-design {CR}` ／
   > （それ以外）`/xddp-05-arch {CR}`
3. Stop (do not execute Step 0 or later).

（`REPOS_MAP`/`REPOS_KEYS`/`IS_MULTI`/`DOCS`/`EXCLUDE_PATTERNS`/`INCLUDE_EXTENSIONS`/`MAX_WAVE_DEPTH` は
CR Resolution で取得済みのためここでの再読み取りは不要）

## Step 0: Identify Affected Repositories

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`.
`HAS_CROSS` = `IS_MULTI`.
（本工程はこの時点で cross 成果物がまだ存在しないため、他工程のような「cross 成果物ファイルの
存在チェック」ではなく IS_MULTI による仮決定を用いる。Discovery 完了後、リポジトリ間依存が
見つからなければ `## Step A-cross` の `If no inter-repo dependencies found` 行で
`HAS_CROSS = false` に降格する。xddp-common「## Resolve HAS_CROSS」の対象外 —
詳細は同プロシージャの「適用外」注記を参照）

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

Let `ENTRY_POINTS_BY_REPO` = 各 repo に渡すエントリポイント集合のマップ。
- `IS_MULTI` = false、または `ENTRY_POINTS` が空の場合:
  全 repo に `ENTRY_POINTS` をそのまま割り当てる（`ENTRY_POINTS` が空なら空集合）。
- `IS_MULTI` = true かつ `ENTRY_POINTS` が非空の場合、追加で次を尋ねる:
  > 指定されたエントリポイント（{ENTRY_POINTS}）はどのリポジトリのものですか？
  > 「{repo名}: {シンボル} {シンボル}」の形式で指定してください。
  > 全リポジトリで共通の場合は「共通」と入力してください（各リポジトリで探索され、
  > 該当しないリポジトリでは未ヒット警告が出ます）。
  回答に従って `ENTRY_POINTS_BY_REPO` を構築する。「共通」と回答された場合、
  または回答が得られなかった場合は全 repo に `ENTRY_POINTS` を割り当てる。

## Step 0.55: Resolve Effective Specout Parameters

Read `~/.claude/skills/xddp-common/procedures/specout-doc-levels.md`, apply "## Specout Doc Levels" with:
  CR_PROFILE: {CR_PROFILE}, SPECOUT_DIAGRAM_LEVEL: {SPECOUT_DIAGRAM_LEVEL}, SPECOUT_SEQUENCE_LEVELS: {SPECOUT_SEQUENCE_LEVELS}
→ let `EFFECTIVE_DIAGRAM_LEVEL`, `EFFECTIVE_SEQUENCE_LEVELS`, `EFFECTIVE_SPO_DETAIL_LEVEL`.

Let `EFFECTIVE_MAX_WAVE_DEPTH` = `MAX_WAVE_DEPTH`（quick でも探索の深さは制限しない）
Let `EFFECTIVE_HIT_FILTER` = `SPECOUT_HIT_FILTER`
  （運用者が `off` を明示している場合にその意図を踏み越えて `conservative` を強制しない。既定値は `conservative` のため、既定構成では
  ノイズ削減が効く。quick が簡略化するのは SPO 文書の記述量のみで、探索の深さ・ヒットフィルタは区別しない）
If `CR_PROFILE` = `quick`:
  Read `{WORKSPACE_ROOT}/xddp.config.md` and extract `REVIEW_MAX_ROUNDS.SPO`（default: `3`）:
    If it is explicitly `0`: Let `EFFECTIVE_REVIEW_MAX_ROUNDS_SPO` = `0`
      （運用者が SPO レビューを明示的に無効化している場合はその意図を優先し、quick でも復活させない）
    Else: Let `EFFECTIVE_REVIEW_MAX_ROUNDS_SPO` = `1`
Else:
  Read `{WORKSPACE_ROOT}/xddp.config.md` and extract `REVIEW_MAX_ROUNDS.SPO`（default: `3`）
    → let `EFFECTIVE_REVIEW_MAX_ROUNDS_SPO` = that value

Read `~/.claude/skills/xddp-common/procedures/ripple-engine-setup.md`, apply "## Ripple Engine Setup" with:
  SPECOUT_SLICE: {SPECOUT_SLICE}, SPECOUT_SLICE_PYTHON_BIN: {SPECOUT_SLICE_PYTHON_BIN}
→ let `SLICE_PY`, `PROBE_ENGINE`, `EFFECTIVE_SLICE_ENGINE`, `USE_PROBE_WARNING`.
`EFFECTIVE_SLICE_ENGINE` は、Step A-Seed（初回の調査を新しく作る repo）の `seed-preview` と `init`、Step A-cross-propagate が作る調査の
`init`（"## Ripple Run"）に渡す。既に状態ファイルがある調査の判定エンジンは state の `slice_engine` を正とする（"## Ripple Engine Check"）。

`specout_bfs.py init`（Step A-Seed で SKILL が実行する）では `EFFECTIVE_MAX_WAVE_DEPTH` / `EFFECTIVE_HIT_FILTER` /
`EFFECTIVE_SLICE_ENGINE` / `SPECOUT_WAVE_HIT_BUDGET` / `SPECOUT_LLM_HIT_BUDGET` / `SPECOUT_SLICE_H_AS` /
`SPECOUT_SLICE_IGNORE_CALLS` を使用する。これらは調査の `bfs-state.json` に保存され、以降の波ループで `specout_bfs.py search`・
`specout_slice.py` が読み込むため、`search`・`classify` には渡さない（再開を含むその調査の判定の単一情報源は state）。
波数上限だけは、設定で上げた値を Step A の「上限の更新」（`extend`）で state に反映する。

下調べ（Step A-Prelim）の調査範囲は `CR_PROFILE` によらず同一である。下調べが書く資料の記載量は
`EFFECTIVE_DIAGRAM_LEVEL` / `EFFECTIVE_SEQUENCE_LEVELS` / `EFFECTIVE_SPO_DETAIL_LEVEL` に従う。

## Step 0.6: Mark In-Progress

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A: Discovery（探索）中`
If `IS_MULTI`, append a per-repo progress table for step 4a:
```markdown
## 工程4a スペックアウト進捗（リポジトリ別）
| リポジトリ | Discovery | Document | 完了日 |
|---|---|---|---|
{for each repo in AFFECTED_REPOS: | {repo} | ⏳ 未着手 | ⏳ 未着手 | - |}
{if HAS_CROSS: | cross | — | ⏳ 未着手 | - |}
```
Write back.

Read `~/.claude/skills/xddp-common/procedures/snapshot-phase-baseline.md`, apply "## Snapshot Phase Baseline" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a

## Step A: Per-repo Specout — Discovery Phase

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A: Discovery（探索）中`

波紋調査は1回＝1フォルダの独立した記録で、`{CR_PATH}/04_specout/{repo}/ripple/{調査}/` に置き、`ripple/runs.json`（スクリプトだけが
書く）に名前・由来・シード・採用の有無を記録する。SPO の波紋調査の欄は**採用した調査**を合わせて作る。工程4a は初回の調査
`initial`（`{CR_PATH}/04_specout/{repo}/ripple/initial/`。以下 `{R0}`）を作り、完了したら採用する。

For each `{repo}` in `AFFECTED_REPOS`, run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py run-list --repo-dir {CR_PATH}/04_specout/{repo}`
→ `runs` のうち `run` が `initial` の要素（以下「初回の調査の行」）とその `state` を得る（スクリプトが見つからない場合は setup.sh 実行を
案内して停止。実行時エラーの場合は stderr を表示して停止）。初回の調査の行の `state` が `in-progress`・`complete` なら、Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py status --path {R0}/work/bfs-state.json --brief`
→ 出力 JSON を以下の判定エンジンの照合・上限の更新・状態テーブル・件数一致検証で使う（`state`/`wave_write_complete`/`max_wave_depth`/
`truncated_wave_limit_count`/`slice_engine`）。

**判定エンジンの照合:** この実行で初回の調査の探索を進める repo（`in-progress` の repo と、`complete` で `truncated_wave_limit_count` > 0
かつ `EFFECTIVE_MAX_WAVE_DEPTH` が `max_wave_depth` より大きい repo）について、
Read `~/.claude/skills/xddp-common/procedures/ripple-engine-check.md`, apply "## Ripple Engine Check" with:
  CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, run: initial, RUN_DIR: {R0}, STATE_SLICE_ENGINE: {slice_engine},
  PROBE_ENGINE: {PROBE_ENGINE}, RERUN_COMMAND: `/xddp-04-specout {CR}`, TODAY: {TODAY}
`switched` の repo は `SWITCHED_REPOS` に {repo} と `SWITCHED_WAVE` を記録する。`blocked` の repo は `ENGINE_BLOCKED_REPOS` に入れ、上限の更新と
状態テーブルの処理を飛ばし、波ループに入れない（「**波ループ終了後**」の案内で Step A-Document へ進まずに停止する）。

**上限の更新（状態テーブルの前。状態によらない）:** 初回の調査に状態ファイルがある repo のうち `ENGINE_BLOCKED_REPOS` に入っていない
ものについて:
- `status --brief` の `max_wave_depth` より `EFFECTIVE_MAX_WAVE_DEPTH` が大きい repo: Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py extend --path {R0}/work/bfs-state.json --max-wave {EFFECTIVE_MAX_WAVE_DEPTH} --today {TODAY}`
  If it errors: display stderr and stop.
  stdout の `state` を、以降の状態テーブルの判定に使う（`status --brief` を取り直さない）。
  `restored_count` > 0 なら、人へ「{repo}: 波数上限を {M} → {N} に上げ、打ち切った {restored_count} 件から探索を続けます」と
  伝える。それ以外は「{repo}: 波数上限を {M} → {N} に更新しました」と伝える（M は `status --brief` の `max_wave_depth`）。
- `EFFECTIVE_MAX_WAVE_DEPTH` が `max_wave_depth` より小さい repo: 「{repo}: 設定の波数上限 {N} は、この CR の探索で使っている
  {M} より小さいため、{M} のまま続けます」と伝える（state の値を使う）。

| 初回の調査の行（`state`） | 対応 |
|---|---|
| 行が無く、`work/no-ripple.json` がある | 初回の調査を作らないと人が決めた repo。Step A-Prelim・discovery-setup・Step A-Seed・波ループをスキップし、Step A-Document へ進む（下調べの資料・台帳・人が直した SPO を消さない） |
| 行が無い、または `not-started` | Step A-Prelim → discovery-setup → Step A-Seed（`run-add`・`init` を含む）を実行してから波ループに入る |
| `missing` | 「{repo} の初回の調査の状態ファイルがありません。`specout_bfs.py run-remove --repo-dir {CR_PATH}/04_specout/{repo} --run initial --today {TODAY}` で取り除いてから `/xddp-04-specout {CR}` を再実行してください（下調べ資料と候補表は残り、シード確認から再開します）」と伝えて停止する |
| `in-progress` | 波ループが中断している（上限の更新で `in-progress` に戻った repo を含む）。Step A-Prelim・discovery-setup・Step A-Seed はスキップし、波ループを `search` から再開する（Visited/Frontier は bfs-state.json から自動復元される） |
| `complete` | Discovery 済み。下記「**初回の調査の出力と採用**」の対象かを確かめて、Document フェーズへ進む |

（`work/no-ripple.json` の行は、行が無い場合の他の行より先に判定する。）

**件数一致検証:** 初回の調査に状態ファイルがある repo（この実行の前から状態ファイルがあった repo）について、
Read `~/.claude/skills/xddp-common/procedures/ripple-count-check.md`, apply "## Ripple Count Check" with:
  CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, run: initial, RUN_DIR: {R0}, RERUN_COMMAND: `/xddp-04-specout {CR}`, TODAY: {TODAY},
  WAVE_WRITE_COMPLETE: {`status --brief` の `wave_write_complete`}
（不一致で A〔やり直し〕を選んだ場合の案内には「下調べ資料と候補表は残り、シード確認（Step A-Seed）から再開します」を添える。
状態ファイルが無い repo は、波ループで `complete` になったときに検証される）

`{R0}/work/bfs-state.md` は bfs-state.json から自動生成される人可読ビューであり、直接参照・編集しない。

---

**Step A-Prelim: 下調べ（初回のみ）**

初回の調査の行が無いか `not-started` で、`{CR_PATH}/04_specout/{repo}/work/no-ripple.json` も**存在しない** `{repo}` のみを対象とする
（以下「setup 対象 repo」。Step A-Prelim・discovery-setup・Step A-Seed で同じ集合を使う）。
初回の調査が `in-progress`・`complete` の repo は Step A-Prelim・discovery-setup・Step A-Seed のいずれも行わない
（`specout_bfs.py init` は state 既存時に異常終了する）。
`work/no-ripple.json` がある repo は Step A-Prelim・discovery-setup・Step A-Seed・波ループのいずれも行わず、Step A-Document へ進む。
setup 対象 repo が無ければ、Step A-Prelim・discovery-setup・Step A-Seed を飛ばして「### 波ループ」へ進む。

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A-Prelim: 下調べ中`

For each setup 対象 repo:
  Let `MODULE_CATALOG_FILE[{repo}]` = `{DOCS}/{repo}/module-catalog.md`（存在しなければ空文字列）。
  Let `CRS_FILE` = `{CR_PATH}/03_change-requirements/CRS-{CR}.md`。
  下調べの再利用を判定する（「新しい」はファイルの更新時刻で比較する。例: Bash `test {A} -nt {B}`）:
  - `{CR_PATH}/04_specout/{repo}/work/prelim-index.md` が存在し、かつ `CRS_FILE` より新しい → 下調べを再利用する
    （起動対象に加えない）。`PRELIM_INDEX_FILE[{repo}]` = そのパス。
  - それ以外 → 前回の残骸のうち存在するものを削除して、起動対象に加える:
    `{CR_PATH}/04_specout/{repo}/` 配下の `SPO-{CR}.md`、`modules/`、`work/prelim-index.md`、`work/observation-memo.md`、
    `work/documented-files.md`、`work/module-assignments.json`、`work/seed-candidates.md`、`work/seed-unsupported.json`、
    `work/prelim-gap-reviewed.md`、`work/module-drafts/`、`work/assemble-inputs.json`、`work/doc-entry-points.json`、
    `work/specout-finish.json`
    （前回の追加下調べの「関係なし」の判断・途中で止まった下書き・前回の入力の指紋とエントリポイントの累積を、新しい下調べに
    持ち越さないため）

1. 起動対象の全 repo について Run via Bash:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_metrics.py phase-start --cr-path {CR_PATH} --step 4a-prelim-{repo}`
   （計測の step 名は repo ごとに分ける。並列起動で開始マーカーが衝突しないようにするため。失敗しても続行し、stderr を表示する）
2. 起動対象の全 repo について Agent `xddp-specout-prelim-agent` を起動する（`IS_MULTI` = true なら並列起動）:

Use the **Agent tool** with `subagent_type=xddp-specout-prelim-agent` and pass:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
BASELINE_SPECS_DIR: {DOCS}/{repo}/specs/
CROSS_SPECS_DIR: {DOCS}/cross/specs/
LATEST_SPECS_DIR: {XDDP_DIR}/latest-specs/{repo}/
DOCS: {DOCS}
MODULE_CATALOG_FILE: {MODULE_CATALOG_FILE[repo]}
ENTRY_POINTS: {ENTRY_POINTS_BY_REPO[repo]}
SUMMARY_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-summary-template.md
MODULE_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-module-template.md
INDEX_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-prelim-index-template.md
LEDGER_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-documented-files-template.md
OUTPUT_DIR: {CR_PATH}/04_specout/{repo}/
TODAY: {TODAY}
EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}
INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS}
SPECOUT_MAX_FILES_PER_MODULE: {SPECOUT_MAX_FILES_PER_MODULE}
SPECOUT_DIAGRAM_LEVEL: {EFFECTIVE_DIAGRAM_LEVEL}
SPECOUT_SEQUENCE_LEVELS: {EFFECTIVE_SEQUENCE_LEVELS}
SPO_DETAIL_LEVEL: {EFFECTIVE_SPO_DETAIL_LEVEL}
```

3. 各 repo のエージェントが戻ったら Run via Bash（失敗しても続行し、stderr を表示する）:
   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_metrics.py record --cr-path {CR_PATH} --step 4a-prelim-{repo} --event phase_complete --target {repo}`
4. 起動対象の全 repo について（再利用と判定した repo には適用しない）:
   - `{CR_PATH}/04_specout/{repo}/work/prelim-index.md` があれば `PRELIM_INDEX_FILE[{repo}]` = そのパス。
   - 無ければ（下調べの失敗）、上記の残骸のうち存在するものを削除し、当該 repo を `PRELIM_FAILED_REPOS` に加えて
     setup 対象から外す（discovery-setup・Step A-Seed・波ループの対象にしない。下調べは母体調査の本体であり、下調べの無い repo は
     SPO の資料を持てないため）。エージェントの返答を保持する（「**波ループ終了後**」で提示する）。他の repo は続ける。

**Setup: discovery-setup（シード候補表の作成・初回のみ）**

setup 対象 repo ごとに、起動の要否と `APPEND_ONLY` を決める
（`{CR_PATH}/04_specout/{repo}/work/` を `{WORK}` と略記する。「新しい」「古い」はファイルの更新時刻で比較する）:
- `{WORK}/seed-candidates.md` が無い、または `{WORK}/prelim-index.md` より古い
  → 起動する（`APPEND_ONLY` = `false`。候補表を新規に作る）。
- `{WORK}/seed-candidates.md` があり、`{WORK}/prelim-index.md` より新しい（シード確認で中断した後の再実行）:
  - `ENTRY_POINTS_BY_REPO[repo]` が空 → 起動しない（人が編集した候補表をそのまま使う）。
  - 空でない → `APPEND_ONLY` = `true` で起動する（エージェントは既存の行を変更せず、指定されたエントリポイント由来の行だけを追記する）。

`IS_MULTI` = true（マルチリポジトリ）の場合は起動する repo を Agent ツールで**並列呼び出し**する
（各 repo は独立した出力ディレクトリを持つため並列実行可能）。
`IS_MULTI` = false（シングルリポジトリ）の場合は順次でよい。

For each `{repo}` to launch:

Use the **Agent tool** with `subagent_type=xddp-specout-agent` and pass:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
BASELINE_SPECS_DIR: {DOCS}/{repo}/specs/
CROSS_SPECS_DIR: {DOCS}/cross/specs/
ENTRY_POINTS: {ENTRY_POINTS_BY_REPO[repo]}
PRELIM_INDEX_FILE: {PRELIM_INDEX_FILE[repo]}
SEED_CANDIDATES_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-seed-candidates-template.md
APPEND_ONLY: {true|false}
OUTPUT_DIR: {CR_PATH}/04_specout/{repo}/
TODAY: {TODAY}
EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}
INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS}
```

`APPEND_ONLY` = `true` で起動した repo について、エージェントが「引数で指定されたが候補表で除外済みのシンボル」を返した場合は、
`EXCLUDED_ENTRY_POINTS[{repo}]` として保持する（Step A-Seed の提示に使う）。

全 setup 呼び出しの完了を待ってから Step A-Seed へ進む。

**Step A-Seed: シード確認と探索状態の初期化（初回のみ）**

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A-Seed: シード確認中`

For each setup 対象 repo（discovery-setup を起動しなかった repo を含む）:
0. `{CR_PATH}/04_specout/{repo}/work/seed-candidates.md` が無い場合、または `APPEND_ONLY` = `false` で起動した repo に
   `{CR_PATH}/04_specout/{repo}/work/seed-input.json` が無い場合（discovery-setup の失敗）: stderr・エージェントの返答を提示し、
   当該 repo を setup 対象から外す（以降の手順・波ループの対象にしない）。`SEED_FAILED_REPOS` に加え、
   波ループ終了後に失敗した repo として提示する。
1. Run via Bash:
   ```
   PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py seed-preview \
     --seed-candidates {CR_PATH}/04_specout/{repo}/work/seed-candidates.md --repo-path {REPOS_MAP[repo]} \
     --exclude "{EXCLUDE_PATTERNS}" --include-ext "{INCLUDE_EXTENSIONS}" \
     --backend {SPECOUT_BACKEND_OVERRIDES.get(repo, SPECOUT_BACKEND)} \
     --hit-filter {EFFECTIVE_HIT_FILTER} --max-files-per-module {SPECOUT_MAX_FILES_PER_MODULE} \
     --wave-hit-budget {SPECOUT_WAVE_HIT_BUDGET} --slice-engine {EFFECTIVE_SLICE_ENGINE} \
     --slice-h-as {SPECOUT_SLICE_H_AS} \
     --ledger {CR_PATH}/04_specout/{repo}/work/documented-files.md
   ```
   → 候補表の「ヒット（ファイル数）」「警告」列と、表の直前の注記行（採用シンボルの合計ヒット数）が更新され、stdout の JSON から
   `adopted_count` / `zero_hit` / `zero_after_filter` / `noisy` / `all_adopted_noisy` / `over_budget` /
   `all_adopted_noisy_or_over_budget` / `adopted_total_hits` / `over_budget_total` / `prelim_module_count` /
   `prelim_file_count` を得る。
   スクリプトが見つからない場合は setup.sh の実行を案内して停止する。
   exit 1 の場合は stderr を提示し、stderr が示す原因ファイルのパスで分ける:
   - 候補表のパス: 「`{CR_PATH}/04_specout/{repo}/work/seed-candidates.md` を修正してから『再試算』と答えてください」と依頼して待つ
     （SKILL が指示を Edit した直後に起きた場合も同じ。SKILL 自身が修正してもよい）。応答を受けたら手順1 を再実行する。
   - 台帳のパス: 候補表の修正では解消しないため、次を案内して待つ:
     > `{CR_PATH}/04_specout/{repo}/work/documented-files.md` を修正して『再試算』と答えるか、
     > `{CR_PATH}/04_specout/{repo}/work/prelim-index.md` と `{CR_PATH}/04_specout/{repo}/work/seed-candidates.md` を削除して
     > `/xddp-04-specout {CR}` を再実行してください（下調べからやり直します。候補表の編集内容は失われます）。
     `prelim-index.md` だけを削除するよう案内しないこと（候補表が残っていると下調べが再起動されない）。
   - どちらのパスも示されない: stderr を提示して停止する。
   その他の実行時エラーは stderr を表示して停止する。
2. `GATE` = `SPECOUT_SEED_GATE` が `true`、またはいずれかの repo（`NO_RIPPLE_REPOS` に入っていない repo。初回の提示では空）で
   `adopted_count` = 0 または `all_adopted_noisy_or_over_budget` = true。
   `NO_RIPPLE_REPOS`（波紋調査を行わないと人が指示した repo）は空で始める。

全 setup 対象 repo 分をまとめて提示する（repo ごとに。候補表を Read して転記する）:
> 📋 **{repo} の波紋調査シード候補**（波紋調査: {`NO_RIPPLE_REPOS` に入っていれば「行わない（人の指示）」、それ以外は「行う（既定）」}）
> 下調べ資料: `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`{`modules/` があれば「・`{CR_PATH}/04_specout/{repo}/modules/`」}（{prelim_module_count} モジュール・{prelim_file_count} ファイル）
> {候補表の「## 候補」の転記（表の直前の注記行を含む）}
> {「## 解決できなかった ENTRY_POINT」「## 識別子を特定できなかった振る舞い」にデータ行があれば転記}
> {`EXCLUDED_ENTRY_POINTS[{repo}]` の各要素について: 引数で指定された `{シンボル}` は候補表で除外されています（除外理由: {除外理由}）。採用する場合は採否を ☑ にしてください}
> {警告があれば: 未ヒット＝CRS の識別子の誤字・旧名称の可能性／フィルタ後0件＝`SPECOUT_HIT_FILTER` の設定を確認／ヒット過多＝一般語の疑い／予算超過＝1波の予算を超えるため、第0波で丸ごと打ち切られる。C++ のメソッド・メンバー変数なら `名前[CLASS:クラス名]`（名前空間をまたいで同じ名前のクラスがあれば `名前[CLASS:名前空間::クラス名]`。名前空間は内側の部分だけでもよい。名前空間に属さないクラスは `名前[CLASS:::クラス名]`）の形で追加すると、波紋調査の判定でそのクラス（とその派生・基底の virtual）に絞れます（`seed-preview` の試算と1波の予算の消費は、クラスで絞る前の件数です）}
> {`over_budget` が非空の場合: `予算超過` の候補は、波紋調査で丸ごと打ち切られます}
> {`adopted_count` = 0 の場合: ⚠️ 採用された候補がありません。候補を追加してください}
> {`all_adopted_noisy` = true の場合: ⚠️ 採用した候補の全件がヒット過多です。変更対象を特定できていない可能性が高いため、候補を見直してください}
> {`all_adopted_noisy` = false で `all_adopted_noisy_or_over_budget` = true の場合: ⚠️ 採用した候補の全件がヒット過多か予算超過です。予算超過の候補は波紋調査の第0波で丸ごと打ち切られるため、変更対象を追えない可能性があります。候補を見直すか、シンボルを分けて実行してください}

`over_budget_total` = true の repo は、候補表の注記行（採用シンボルの合計ヒット数と分割実行の案内）を必ず提示文に含める
（`GATE` = false で確認を待たない場合も含める）。

モジュール数・ファイル数は手順1 の stdout の `prelim_module_count`・`prelim_file_count` を使う（自分で数えない）。

`GATE` = true の場合、次を尋ねて待つ:
> 各 repo の候補表 `{CR_PATH}/04_specout/{repo}/work/seed-candidates.md` の「採否」列を編集するか、
> 「`{repo}`: `X` を除外（理由）、`Y` を追加」の形で指示してください。
> 波紋調査（シードからの機械的な調査）は既定で行います。行わない repo は「`{repo}`: 波紋調査なし」と指示してください
> （その repo は下調べ資料で工程4a を完了します。影響範囲は下調べで読んだ範囲に限られます）。
> - **確定** → 「行う」の repo は採用した候補で波紋調査を開始し、「行わない」の repo は下調べ資料で SPO を仕上げます
> - **編集した／指示した** → ヒット数を再試算して再提示します
> - **中断する** → 波紋調査を始めずに中断します（`/xddp-04-specout {CR}` で、この確認から再開します）

- 指示で答えた場合: SKILL が候補表を Edit する（除外＝採否 ☐＋除外理由、追加＝行を追加し由来 `人が追加`・採否 ☑）。
  「`{repo}`: 波紋調査なし」は `NO_RIPPLE_REPOS` に {repo} を加え、「`{repo}`: 波紋調査あり」は `NO_RIPPLE_REPOS` から外す
  （どちらも候補表は変えない）。手順1 へ戻る。
- 「編集した」と答えた場合: 手順1 へ戻る。
- 「確定」の場合: 手順1 を全 setup 対象 repo について再実行し、最新の候補表で判定する。
  採用が0件の repo（`NO_RIPPLE_REPOS` に入っていない repo に限る）が残っている場合は確定させず、その repo の候補の追加か
  「波紋調査なし」を求めて再度尋ねる（`init` は起点なしでは開始できない）。0件の repo が無ければ:
  - `NO_RIPPLE_REPOS` の各 repo について、Write ツールで `{CR_PATH}/04_specout/{repo}/work/no-ripple.json` に
    `{"cr": "{CR}", "repo": "{repo}", "decided": "{TODAY}"}` を書く（初回の波紋調査を作らないと人が決めたことの唯一の記録。
    状態テーブル・Step A-cross-propagate・Step E と、SPO の「波紋調査なし」の文言〔スクリプト〕が同じ印で判定する）。
    `NO_RIPPLE_REPOS` が空でなければ、次を伝える:
    > ℹ️ {repo…} は波紋調査を行わず、下調べ資料で SPO を仕上げます。工程4a の完了前に考えを変える場合は、
    > `{CR_PATH}/04_specout/{repo}/work/no-ripple.json` を削除して `/xddp-04-specout {CR}` を再実行すると、シード確認から再開します
    > （工程4b で CRS が更新された後に削除すると、下調べからやり直しになります）。工程4a の完了後に影響を調べる場合は、
    > `/xddp-investigate {CR} ripple --adopt --repo {repo} {シンボル…}` で波紋調査を足せます。
  - 手順3 へ進む。
- 「中断する」: Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: ⏸ 中断, DETAIL_STEP: `Step A-Seed: シード確認で中断`
  progress.md の「## 次に実行すべきコマンド」欄に `/xddp-04-specout {CR}` を記録する。
  下調べ資料のパス（各 repo の `SPO-{CR}.md`・`modules/`）を示し、次を案内して終了する（工程4b へ進まない）:
  > `/xddp-04-specout {CR}` を再実行すると、下調べ資料と候補表をそのまま使ってシード確認から再開します
  > （エントリポイントを引数で指定した場合は候補表に追記されます）。
- `GATE` = false の場合: 提示のみで手順3 へ進み、全 setup 対象 repo で波紋調査を行う（`NO_RIPPLE_REPOS` は空のまま。
  「中断する」は選べない）。

3. `NO_RIPPLE_REPOS` に入っていない全 setup 対象 repo について（`NO_RIPPLE_REPOS` の repo には手順3 を行わない）:
   - 初回の調査の行が無い場合: `{R0}/`（`{CR_PATH}/04_specout/{repo}/ripple/initial/`）・`{CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md` の
     いずれかが残っていれば削除し、その旨を1行で通知する（記録の無い調査のディレクトリと funcmap は前回の残骸であり、状態と整合しない。
     funcmap は SPO の仕上げで作り直される）。続けて Run via Bash:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py run-add --repo-dir {CR_PATH}/04_specout/{repo} --run initial --origin specout --today {TODAY}`
     （If it errors: display stderr and stop.）
   - 初回の調査の行が `not-started` の場合: `{R0}/discovery-log.md`・`{R0}/work/waves/` が残っていれば削除する。
   続けて、判定エンジンの設定をファイルに書く（警告文・正規表現の自由文をシェルの引数で渡さないため）:
   - Run via Bash: `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py probe --out {R0}/work/slice-probe.json`
     （If it errors: display stderr and stop.）
   - `SPECOUT_SLICE_IGNORE_CALLS` の値を Write ツールで `{R0}/work/slice-ignore-calls.txt` に1行で書く
     （値が空なら空のファイル。値の前後の空白・引用符はそのまま書く）。
   続けて Run via Bash:
   ```
   PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py init \
     --path {R0}/work/bfs-state.json --repo-path {REPOS_MAP[repo]} \
     --discovery-log {R0}/discovery-log.md \
     --seed-candidates {CR_PATH}/04_specout/{repo}/work/seed-candidates.md \
     --unsupported-patterns {CR_PATH}/04_specout/{repo}/work/seed-unsupported.json \
     --today {TODAY} --cr {CR} --repo {repo} \
     --exclude "{EXCLUDE_PATTERNS}" --include-ext "{INCLUDE_EXTENSIONS}" --max-wave {EFFECTIVE_MAX_WAVE_DEPTH} \
     --max-files-per-module {SPECOUT_MAX_FILES_PER_MODULE} \
     --backend {SPECOUT_BACKEND_OVERRIDES.get(repo, SPECOUT_BACKEND)} --hit-filter {EFFECTIVE_HIT_FILTER} \
     --scope-summary-file {CR_PATH}/04_specout/{repo}/work/_scope-summary.md \
     --wave-hit-budget {SPECOUT_WAVE_HIT_BUDGET} --llm-hit-budget {SPECOUT_LLM_HIT_BUDGET} \
     --slice-engine {EFFECTIVE_SLICE_ENGINE} --probe-file {R0}/work/slice-probe.json \
     --slice-ignore-calls-file {R0}/work/slice-ignore-calls.txt --slice-h-as {SPECOUT_SLICE_H_AS} \
     [--use-probe-warning] [--module-catalog {MODULE_CATALOG_FILE[repo]}]
   ```
   `--use-probe-warning` は `USE_PROBE_WARNING` が true の場合のみ渡す（discovery-log の「## 探索設定」に判定エンジンの警告が残る）。
   `--module-catalog` は `MODULE_CATALOG_FILE[{repo}]` が空でない場合のみ渡す。`--symbols` と `--entry-point-symbols` は渡さない
   （初期シンボル・由来テーブルは候補表から作られる）。`EFFECTIVE_SLICE_ENGINE` が `slice` の場合、`init` は初期シンボルに
   「シード要約の取り込み待ち」の印を付け、波ループ a の `search` が exit 6 で取り込みを求める。
   `init` が exit 1 で止まった場合（影響なしとみなす呼び出しの正規表現が不正等）は stderr を表示して停止する。
   スクリプトが見つからない場合は setup.sh の実行を案内して停止する。実行時エラーは stderr を表示して停止する。

（`SPECOUT_BACKEND` は Discovery BFS の参照解決バックエンド。repo 単位上書き `SPECOUT_BACKEND.{repo}` があれば
`SPECOUT_BACKEND_OVERRIDES` 経由で当該 repo 値へ解決し、無ければグローバル `SPECOUT_BACKEND`（既定 `auto`）を使う。
既定 `auto` は識別子索引 `index`（索引で引けないシンボルは rg があれば rg・無ければ grep に委譲）。`grep`/`rg` を明示すると
索引を使わない。それ以外の値は未実装のため grep へフォールバックする。
discovery-setup・document フェーズは `init` を実行しないため、この値は Step A-Seed の `seed-preview`・`init` にのみ渡す。）

（`SPECOUT_HIT_FILTER` は Discovery BFS の保守的ヒット事前フィルタ（既定 `conservative`／`off`）。
`SPECOUT_BACKEND` と同様、Step A-Seed の `seed-preview`・`init` にのみ渡す。）

（`SPECOUT_SLICE_H_AS` は `.h` の解析言語（既定 `auto`）。`SPECOUT_BACKEND` と同様、Step A-Seed の `seed-preview`・`init` にのみ渡す。
`seed-preview` は `name[CLASS:X]` の候補を検索する C++ のファイルの範囲を決めるのに使う。）

（`--module-catalog` を渡すと、Wave 0 の `commit-wave` 時にモジュール優先度の算出と以後の波での frontier の振り分けを
スクリプトが行う。`MODULE_CATALOG_FILE` が空の場合は優先度差別化なしの通常 BFS になる。）

### クロスリポジトリ伝播の調査の再開（`IS_MULTI` = true で `{CR_PATH}/04_specout/cross/work/cross-propagation-log.json` がある場合のみ）

前回の実行で作ったクロスリポジトリ伝播の調査（伝播の記録で `status` = `running` の組）を、ここで完了・採用させる。
1. 「## Step A-cross-propagate」の「**照合**」を行う。
2. 伝播の記録の `running` の組の `run`（調査の名前）を、消費 repo（組の `repo`）ごとに重複を除いて集める（`run-list` の `state` が
   `in-progress`・`not-started`・`complete` の調査。採用の有無によらない。採用済みで記録だけが `running` のまま止まった組も含める）。
   1件も無ければ本節を終える。
3. `REPO_RUNS[repo]` = 各調査について {run, origin: `cross-propagation`, symbols: 空, meta_file: 空, entry_identity: `name-only`,
   adopt: true, adopted_by: `cross-propagation`, RERUN_COMMAND: `/xddp-04-specout {CR}`} のリスト。
   Read `~/.claude/skills/xddp-common/procedures/ripple-run.md`, apply "## Ripple Run" with:
     CR: {CR}, CR_PATH: {CR_PATH}, REPO_RUNS: {REPO_RUNS}, REPOS_MAP: {REPOS_MAP}, SLICE_PY: {SLICE_PY}, PROBE_ENGINE: {PROBE_ENGINE},
     EFFECTIVE_SLICE_ENGINE: {EFFECTIVE_SLICE_ENGINE}, USE_PROBE_WARNING: {USE_PROBE_WARNING}, TODAY: {TODAY},
     設定（EXCLUDE_PATTERNS, INCLUDE_EXTENSIONS, MAX_WAVE_DEPTH: {EFFECTIVE_MAX_WAVE_DEPTH}, SPECOUT_MAX_FILES_PER_MODULE, SPECOUT_BACKEND,
     SPECOUT_BACKEND_OVERRIDES, SPECOUT_HIT_FILTER: {EFFECTIVE_HIT_FILTER}, SPECOUT_WAVE_HIT_BUDGET, SPECOUT_LLM_HIT_BUDGET,
     SPECOUT_SLICE_IGNORE_CALLS, SPECOUT_SLICE_H_AS, SPECOUT_MAX_AFFECTED_FILES, SPECOUT_CLASSIFY_CHUNK_SIZE, SPECOUT_CLASSIFY_PARALLEL, DOCS）
4. `DONE` に入った調査の組（`run` がその名前の要素）の `status` を `propagated` にして伝播の記録を書き戻す。`FAILED` の調査は組を
   `running` のまま残す（次の `/xddp-04-specout {CR}` で同じ調査を再開する）。採用した調査は、Step A-Document で SPO に入る。

### 波ループ

Let `ACTIVE_RUNS` = `AFFECTED_REPOS` のうち、上表の判定または Step A-Seed の `init` により初回の調査が `in-progress` になった repo
（`ENGINE_BLOCKED_REPOS`、`work/no-ripple.json` がある repo、`PRELIM_FAILED_REPOS`・`SEED_FAILED_REPOS` は含めない）→
{run: `initial`, RUN_DIR: {R0}, RERUN_COMMAND: `/xddp-04-specout {CR}`}。
`ACTIVE_RUNS` が空でなければ、Read `~/.claude/skills/xddp-common/procedures/ripple-wave-loop.md`, apply "## Ripple Wave Loop" with:
  CR: {CR}, CR_PATH: {CR_PATH}, ACTIVE_RUNS: {ACTIVE_RUNS}, REPOS_MAP: {REPOS_MAP}, SLICE_PY: {SLICE_PY}, PROBE_ENGINE: {PROBE_ENGINE},
  EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}, INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS},
  SPECOUT_CLASSIFY_CHUNK_SIZE: {SPECOUT_CLASSIFY_CHUNK_SIZE}, SPECOUT_CLASSIFY_PARALLEL: {SPECOUT_CLASSIFY_PARALLEL},
  SEED_GATE_DONE: true,
  SEED_GATE_NOTE: `下調べ資料と候補表は残り、シード確認（Step A-Seed）から再開します。候補表 work/seed-candidates.md で採否を見直すか、/xddp-04-specout {CR} {識別子またはファイルパス…} で起点を追加してください`,
  TODAY: {TODAY}
→ let `COMPLETED`, `SEED_SUMMARY_FAILED`, `WAVE_FAILED`, `ZERO_SEED`.

**初回の調査の出力と採用:** 次の repo（`INITIAL_DONE_REPOS`）について、
Read `~/.claude/skills/xddp-common/procedures/ripple-run-outputs.md`, apply "## Ripple Run Outputs" with:
  CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, run: initial, SPECOUT_MAX_AFFECTED_FILES: {SPECOUT_MAX_AFFECTED_FILES}, ONLY_SUMMARY: false
を適用し、続けて Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py run-adopt --repo-dir {CR_PATH}/04_specout/{repo} --run initial --by specout --today {TODAY}`
  （If it errors: display stderr and stop.）
- この実行の波ループで `COMPLETED` に入った repo。
- Step A の開始時に初回の調査が `complete` で、採用されておらず（`adopted` が false）、一度も取り消されていない（`unadopted_by` が空）
  repo（出力・採用の前に止まった repo）。人が取り消した repo（`unadopted_by` がある）は採用し直さない。
続けて、`INITIAL_DONE_REPOS` のうち `{CR_PATH}/04_specout/{repo}/work/seed-candidates.md` が存在する repo に限り、下調べとシード確認の
計測を記録する（ベストエフォート。失敗しても続行し、stderr を表示する）。Run via Bash:
```
PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py prelim-metrics \
  --path {R0}/work/bfs-state.json --seed-candidates {CR_PATH}/04_specout/{repo}/work/seed-candidates.md \
  [--ledger {CR_PATH}/04_specout/{repo}/work/documented-files.md] --seed-gate {SPECOUT_SEED_GATE}
```
`--ledger` は台帳ファイルが存在する場合のみ渡す。同じ調査で2回目以降に記録しようとした場合は、スクリプトが追記をスキップする
（stdout の `skipped`）。

**波ループ終了後:**
初回の調査が `complete` の repo について、per-repo progress table を更新: `| {repo} | ✅ 完了 | ⏳ 未着手 | - |`
`work/no-ripple.json` がある repo について、per-repo progress table を更新: `| {repo} | ⏭️ 初回なし（人の判断） | ⏳ 未着手 | - |`

`SEED_SUMMARY_FAILED`・`WAVE_FAILED` は "## Ripple Wave Loop" の「### 波ループ終了後」が案内を提示済みである。どちらかが空でなければ、
"## Progress Update" を CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中,
DETAIL_STEP: `Step A: 波紋調査の途中で停止（{repo をカンマ区切り}）` で適用し、Step A-Document 以降へ進まずに停止する
（`complete` になった他の repo の探索状態は保持され、再実行でそれらの波ループは再実行されない）。
`PRELIM_FAILED_REPOS`（Step A-Prelim 手順4 で外した repo。下調べが完了しなかった repo）があれば、その一覧と
下調べのエージェントの返答を提示し、`/xddp-04-specout {CR}` を再実行するよう案内する（再実行で下調べからやり直す）。
この場合は Step A-Document 以降へ進まずに停止する。
`SEED_FAILED_REPOS`（Step A-Seed 手順0 で外した repo。候補表が作られなかった repo）があれば、その一覧と
discovery-setup の返答を提示し、`/xddp-04-specout {CR}` を再実行するよう案内する（初回の調査が無いため、再実行で
Step A-Prelim から始まる。下調べ資料は再利用される）。この場合は Step A-Document 以降へ進まずに停止する。
`ENGINE_BLOCKED_REPOS` が空でなければ、その一覧と "## Ripple Engine Check" の「### 提示文」の選択肢1・3の案内を再掲し、上記の
per-repo progress table の更新を行ったうえで "## Progress Update" を CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中,
DETAIL_STEP: `Step A: 判定エンジンが使えないため停止（{ENGINE_BLOCKED_REPOS をカンマ区切り}）` で適用し、Step A-Document 以降へ
進まずに停止する（外した repo は、選択肢1で再実行すると波ループの途中から続く）。
`ZERO_SEED` が空でなければ、上記の per-repo progress table の更新を行ったうえで、
"## Progress Update" を CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中,
DETAIL_STEP: `Step A: 投入シンボル0件のため停止（{ZERO_SEED の repo をカンマ区切り}）` で適用し、
"## Ripple Wave Loop" が提示した案内を再掲して、Step A-Document 以降へ進まずに停止する（シードのない repo の SPO は作れないため）。

## Step A-Document: Per-repo Specout — SPO の仕上げ

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A-Document: SPO の仕上げ中`

各リポジトリの SPO を、下調べの資料と採用した波紋調査の合算から**順次**仕上げる。For each `{repo}` in `AFFECTED_REPOS`:

Read `~/.claude/skills/xddp-common/procedures/specout-finish.md`, apply "## Specout Finish" with:
  CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, REPOS_MAP: {REPOS_MAP}, ENTRY_POINTS: {ENTRY_POINTS_BY_REPO[repo]}, IS_MULTI: {IS_MULTI},
  XDDP_DIR: {XDDP_DIR}, DOCS: {DOCS}, EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}, INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS},
  SPECOUT_MAX_FILES_PER_MODULE: {SPECOUT_MAX_FILES_PER_MODULE}, SPECOUT_MAX_AFFECTED_FILES: {SPECOUT_MAX_AFFECTED_FILES},
  EFFECTIVE_DIAGRAM_LEVEL: {EFFECTIVE_DIAGRAM_LEVEL}, EFFECTIVE_SEQUENCE_LEVELS: {EFFECTIVE_SEQUENCE_LEVELS},
  EFFECTIVE_SPO_DETAIL_LEVEL: {EFFECTIVE_SPO_DETAIL_LEVEL}, RERUN_COMMAND: `/xddp-04-specout {CR}`, TODAY: {TODAY}
→ let `FINISH_STATUS`, `ADOPTED_RUNS`。
- `FINISH_STATUS` = `stopped`: "## Progress Update" を CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中,
  DETAIL_STEP: `Step A-Document: SPO の仕上げで停止（{repo}）` で適用し、停止する（再実行は `/xddp-04-specout {CR}`）。
- `ok`: per-repo progress table を更新: `| {repo} | {Discovery 列} | ✅ 完了 | {TODAY} |`（Discovery 列は、`work/no-ripple.json` がある
  repo は `⏭️ 初回なし（人の判断）`、それ以外は `✅ 完了`。`ADOPTED_RUNS` が空でなければ `（採用 {件数} 件）` を添える）。

## Step A-cross: Cross-repo SPO Synthesis (only when HAS_CROSS = true)

Update progress table: `| cross | — | 🔄 進行中 | - |`

After all per-repo Document phases are complete, synthesise `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`:

Read all `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` files. Identify:
- Symbols, types, or functions from repo-A that are imported or called by repo-B
- HTTP API calls from one repo to another
- Shared data structures, event schemas, or message payloads
- Shared database tables (read/write by multiple repos)
- Shared constants, enum values, or macro definitions referenced across repos

Write `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` using `~/.claude/skills/xddp-04-specout/templates/04_specout-cross-repo-template.md`:
- Section 2: リポジトリ間構造図 (Mermaid C4/component diagram)
- Section 3: リポジトリ間シーケンス図 (if `EFFECTIVE_SEQUENCE_LEVELS` includes `repository`)
- Section 4: 共有インタフェース一覧 (インタフェース名 / 提供リポジトリ / 消費リポジトリ / 型・プロトコル / バージョン / breaking変更有無 — 検出なしの場合は「なし」)
- Section 5: リポジトリ間共有定数・列挙値 (識別子 / 値 / 定義リポジトリ / 参照リポジトリ / 用途 — 検出なしの場合は「なし」)
- Section 6: リポジトリ間共有データ型関連図 (OOP言語: Mermaid classDiagram / 手続き型: テキスト表形式 — 共有データ型が検出された場合のみ。検出なしの場合は省略)
- Section 7: データアクセスマトリクス (`EFFECTIVE_DIAGRAM_LEVEL` = `full` の場合のみ、または同一リソースへの並列書き込み・共有バッファアクセスが検出された場合)
- Section 8: データモデル（ER図・データ構造定義）(`EFFECTIVE_DIAGRAM_LEVEL` = `full` の場合のみ、またはデータ構造変更がある場合。Mermaid `erDiagram` または `classDiagram`)
- Section 9: データフロー図（DFD）(リポジトリ間データフローが識別された場合のみ。識別されなかった場合は「対象外（理由：リポジトリ間データフローなし）」と記載)
- Section 10: 追加提案図 (タイミング図：リアルタイム・組み込み系プロジェクトでは★必須。その他は任意)
- Section 11: CRS への反映事項（cross）

Write の前に既存の `SPO-{CR}-cross.md` を確認し、「## 追加探索の実施記録（自動追記・Step A-cross-propagate）」
節があれば、その節（見出しから末尾まで）を改変せずに新しいファイルの末尾（Section 11 より後）へ引き継ぐ
（Step A-cross-propagate の監査記録であり、再実行で消してはならない）。

If no inter-repo dependencies found → skip cross/ SPO creation; set `HAS_CROSS = false`.
Otherwise（cross/ SPO を実際に作成した場合）、`SPECOUT_CROSS_PROPAGATE = true` かつ上記
Section 4「共有インタフェース一覧」で1件以上識別した場合に限り、その識別項目を
`{CR_PATH}/04_specout/cross/work/cross-propagation-targets.json` へ以下のスキーマの JSON 配列として
書き出す（Section 4 の Markdown 表と同一の意味判定結果を機械可読な形でも保持するだけであり、
新たな判定は行わない）:
```json
[
  {"symbol": "{シンボル名}", "providing_repo": "{提供リポジトリ}", "consuming_repo": "{消費リポジトリ}"}
]
```
1つのインタフェースが複数の消費リポジトリを持つ場合（Section 4 の「消費リポジトリ」列がカンマ区切り等で
複数記載される場合）は、`(symbol, providing_repo, consuming_repo)` の組ごとに配列要素を分ける
（1消費リポジトリ＝1要素）。以下のいずれの場合も、このファイルは書き出さない（存在させない）:
- `SPECOUT_CROSS_PROPAGATE = false` の場合
- cross/ SPO 自体がスキップされた場合（`HAS_CROSS = false`）
- Section 4 が「なし」（共有インタフェースが1件も識別されなかった）場合

上記いずれかに該当し、前回までの実行で書き出された `{CR_PATH}/04_specout/cross/work/cross-propagation-targets.json` が残っている場合は
削除する（古い識別結果が後続ステップに読まれないようにするため）。
後続の「## Step A-cross-propagate」は本ファイルの不在をスキップ条件として扱う。

Update progress table: `| cross | — | ✅ 完了 | {TODAY} |`

## Step A-cross-propagate: Cross-repo Symbol Propagation（HAS_CROSS = true かつ SPECOUT_CROSS_PROPAGATE = true の場合のみ）

If `HAS_CROSS` != `true` or `SPECOUT_CROSS_PROPAGATE` != `true`: このセクション全体をスキップし、
Step A2 へ進む。

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A-cross-propagate: クロスリポジトリ伝播探索中`

あるリポジトリが提供し別のリポジトリが消費するシンボルについて、消費リポジトリに**新しい波紋調査**（`cross-{提供 repo}-{n}`）を
作り、完了したら採用する（1ラウンドだけ）。

Let `TARGETS_FILE` = `{CR_PATH}/04_specout/cross/work/cross-propagation-targets.json`.
`TARGETS_FILE` が存在しない、または中身が空配列 `[]` の場合: 本ステップ全体をスキップし、progress.md の
DETAIL_STEP に「Step A-cross-propagate: 対象なし（スキップ）」を記録して Step A2 へ進む。

Read `TARGETS_FILE`（JSON配列。各要素 `{"symbol", "providing_repo", "consuming_repo"}`）。
以下のいずれかに該当する要素は無視し、人へ警告する（「⚠️ cross-propagation-targets.json に不正な
エントリがあります: {entry}」）:
- `consuming_repo` が `AFFECTED_REPOS` に含まれない
- `consuming_repo` と `providing_repo` が同一

**伝播の記録:**
Let `LOG_FILE` = `{CR_PATH}/04_specout/cross/work/cross-propagation-log.json`（存在しない場合は空配列 `[]` として扱う。`LOG_FILE` は
本ステップと Step A の「### クロスリポジトリ伝播の調査の再開」と `specout_bfs.py run-remove` だけが書き込む永続履歴であり、
要素の追加と `status`・`run` の更新のみを行い、要素を削除しない。「書き戻す」ときは、読み取った JSON 配列全体に追加・更新を反映した
配列でファイル全体を上書きする）。
各要素は `{"repo", "symbol", "providing_repo", "status", "run"}`。`repo` は消費リポジトリ、`run` は `running`・`propagated` の組の調査の名前。
`status` は次のいずれか: `deferred`＝未投入（消費 repo の初回の調査が `complete` でなかったため見送った、または投入前に停止した）／
`running`＝消費 repo に調査を作った（完了・採用の前）／`propagated`＝調査が完了し採用された／`chain-excluded`＝連鎖ガードで除外し
人へ通知済み／`no-ripple`＝消費 repo が初回の調査を作らないと決めた repo のため見送った〔再試行しない〕。

**照合**（冪等性ガードの前と、Step A の「### クロスリポジトリ伝播の調査の再開」の前に行う）: `status` = `running` の組のうち、
`run` が消費 repo の `specout_bfs.py run-list --repo-dir {CR_PATH}/04_specout/{repo}` の `runs` に無い、または `state` が `missing` のものを
`deferred` に戻して `run` を消し、書き戻す（人が調査を取り除いた・ディレクトリが失われた場合に、その伝播が二度と実行されなくなるのを防ぐ）。

**冪等性ガード:**
有効な要素のうち、`(consuming_repo, symbol, providing_repo)` の組が `LOG_FILE` に `status` = `propagated`・`chain-excluded`・`no-ripple`・
`running` のいずれかで記録済みのものを除外する（`deferred` の組は除外せず、再試行の対象とする。`running` は Step A の再開が完了させる）。

**連鎖ガード（CR 単位の1ラウンド制限）:**
Let `PROPAGATED_CONSUMERS` = `LOG_FILE` のうち `status` = `propagated`・`running` の要素の `repo` の集合（過去の実行で追加探索の対象に
なった消費リポジトリ）。冪等性ガード通過後の要素のうち、`providing_repo` が `PROPAGATED_CONSUMERS` に含まれ、かつ同じ組が `LOG_FILE` に
`status` = `deferred` で記録されていないものは、追加探索の結果として新たに識別された連鎖（B→C）の候補とみなして除外する（`deferred` の
組は、提供元が伝播対象になる前の実行で既に識別されていた正当な1段目であるため除外しない）。
除外した要素は `{"repo": consuming_repo, "symbol", "providing_repo", "status": "chain-excluded"}` として `LOG_FILE` へ追加して書き戻し
（次回以降は冪等性ガードで除外され、同じ通知を繰り返さない）、除外した要素が1件以上ある場合、人へ通知する:
> ℹ️ 以下の共有インタフェースは、過去に追加探索を実施したリポジトリが提供元のため、連鎖的な追跡を
> 行わない設計により自動の追加探索対象から除外しました:
> {除外要素ごとに "- {symbol}（{providing_repo} → {consuming_repo}）"}
> 追跡が必要な場合は `/xddp-investigate {CR} ripple --adopt --repo {consuming_repo} {symbol}` を人が実行してください。

残った要素を `consuming_repo` と `providing_repo` でグルーピングし、組ごとに `symbol` を重複排除する。
Let `PROPAGATION_MAP` = `{repo: {providing_repo: [symbol, ...]}, ...}`（symbol リストが空の組は除去する）。
`PROPAGATION_MAP` が空の場合: 本ステップ全体をスキップし、progress.md の DETAIL_STEP に
「Step A-cross-propagate: 新規対象なし」を記録して Step A2 へ進む。

**事前登録:** 下記ループへ入る**前に**、`PROPAGATION_MAP` に残った各組を
`{"repo": consuming_repo, "symbol", "providing_repo", "status": "deferred"}` として `LOG_FILE` へ追加して
書き戻す（同じ組が既に `deferred` で記録済みなら追加しない）。これにより、ループのどの時点で停止しても
未投入の組は `deferred` として残り、次回実行時に冪等性ガード・連鎖ガードのいずれでも除外されず再試行される。

**調査の作成:** `REPO_RUNS` = 空。For each `{repo}` in `PROPAGATION_MAP` のキー（repo 名の昇順で処理する）:
- `{CR_PATH}/04_specout/{repo}/work/no-ripple.json` がある場合: 投入せず、人へ警告する（「⚠️ {repo} は初回の波紋調査を作らないと
  決めた repo のため、クロスリポジトリ伝播（{シンボル}）を見送りました。{repo} 側の影響は下調べで読んだ範囲に限られます。
  影響を調べる場合は `/xddp-investigate {CR} ripple --adopt --repo {repo} {シンボル}` を実行してください」）。当該 repo の事前登録済みの
  `deferred` 要素の `status` を `no-ripple` に置き換えて `LOG_FILE` を書き戻し（再試行しない）、次の repo へ進む。
- Run via Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py run-list --repo-dir {CR_PATH}/04_specout/{repo}`
  If it errors: display stderr and stop（当該 repo 以降の組は事前登録済みの `deferred` のまま残り、次回実行時に再試行される）。
  初回の調査（`initial`）の `state` が `complete` でない場合: 当該 repo をスキップし、人へ警告する（「⚠️ {repo} の初回の波紋調査が
  complete 状態ではないため、クロスリポジトリ伝播探索をスキップしました。」）。当該 repo の各対象は `deferred` のまま残し、次回実行時に
  再試行される。
- 初回の調査が `complete` の場合、`PROPAGATION_MAP[repo]` の提供 repo ごと（昇順）に:
  1. 調査の名前 `{name}` = `cross-{providing_repo}-{n}`（`n` は、`run-list` の `runs` に無い最小の正の整数。同じ提供元から再び伝播しても
     新しい調査になる）。
  2. Write ツールで `{CR_PATH}/04_specout/{repo}/ripple/{name}/meta.json` に
     `{"approach": null, "reason": "クロスリポジトリ伝播（{providing_repo} → {repo}）", "seeds": [{シンボル…}], "entry_identity": "name-only"}`
     を書く。Run via Bash:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py run-add --repo-dir {CR_PATH}/04_specout/{repo} --run {name} --origin cross-propagation --today {TODAY} --meta-file {CR_PATH}/04_specout/{repo}/ripple/{name}/meta.json`
     If it errors: display stderr and stop（組は `deferred` のまま残る）。
  3. 当該組（`repo`・`providing_repo` と各 `symbol`）の `deferred` 要素の `status` を `running`、`run` を `{name}` にして `LOG_FILE` を書き戻す
     （途中で止まっても組は `running` で調査の名前を持つため、再実行の Step A「### クロスリポジトリ伝播の調査の再開」が同じ調査を再開し、
     同じシンボルで2つ目の調査を作らない）。
  4. `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` の末尾（Section 11 より後）に監査用ノートを追記する（Section 2〜11 は変更しない）。
     下記の見出しがまだ無い場合のみ見出しと注記を先に追記し、続けて1行を追記する:
     ```
     ## 追加探索の実施記録（自動追記・Step A-cross-propagate）
     > 本節は Step A-cross-propagate が追記する監査記録であり、テンプレート外の節である。
     > SPO レビュー・修正の対象外とし、削除・改変しないこと。
     - {TODAY}: {repo} で追加探索を投入（調査 {name}）: {シンボル一覧（カンマ区切り）}
     ```
  5. `REPO_RUNS[repo]` に {run: {name}, origin: `cross-propagation`, symbols: {シンボル…}, meta_file: 上記のパス, entry_identity: `name-only`,
     adopt: true, adopted_by: `cross-propagation`, RERUN_COMMAND: `/xddp-04-specout {CR}`} を加える（同じ消費 repo の調査は順に回る）。

`REPO_RUNS` が空の場合は progress.md の DETAIL_STEP に「Step A-cross-propagate: 対象 repo が complete 状態ではなくすべてスキップ」を
記録して Step A2 へ進む。

**調査の実行:** Read `~/.claude/skills/xddp-common/procedures/ripple-run.md`, apply "## Ripple Run" with:
  CR: {CR}, CR_PATH: {CR_PATH}, REPO_RUNS: {REPO_RUNS}, REPOS_MAP: {REPOS_MAP}, SLICE_PY: {SLICE_PY}, PROBE_ENGINE: {PROBE_ENGINE},
  EFFECTIVE_SLICE_ENGINE: {EFFECTIVE_SLICE_ENGINE}, USE_PROBE_WARNING: {USE_PROBE_WARNING}, TODAY: {TODAY},
  設定（EXCLUDE_PATTERNS, INCLUDE_EXTENSIONS, MAX_WAVE_DEPTH: {EFFECTIVE_MAX_WAVE_DEPTH}, SPECOUT_MAX_FILES_PER_MODULE, SPECOUT_BACKEND,
  SPECOUT_BACKEND_OVERRIDES, SPECOUT_HIT_FILTER: {EFFECTIVE_HIT_FILTER}, SPECOUT_WAVE_HIT_BUDGET, SPECOUT_LLM_HIT_BUDGET,
  SPECOUT_SLICE_IGNORE_CALLS, SPECOUT_SLICE_H_AS, SPECOUT_MAX_AFFECTED_FILES, SPECOUT_CLASSIFY_CHUNK_SIZE, SPECOUT_CLASSIFY_PARALLEL, DOCS）
→ let `DONE`, `FAILED`.
`DONE` に入った調査の組の `status` を `propagated` にして `LOG_FILE` を書き戻す。調査は新しい調査として第0波から上限の波数まで調べられ、
上限に達した調査は打ち切り記録を残して `complete` になる。
`FAILED` があれば、その一覧と理由を人へ提示し、原因の解消後に `/xddp-04-specout {CR}` を再実行するよう案内する（組は `running` のまま残り、
再実行の Step A が同じ調査を再開・採用する）。

Let `DOC_REPOS` = `DONE` に調査が1つ以上入った repo。`DOC_REPOS` の各 `{repo}` について、`## Step A-Document` の
**`For each {repo} in AFFECTED_REPOS:` ループ本体**（"## Specout Finish" の適用と per-repo progress table 更新）を再適用する。
節冒頭の Progress Update は再適用しない。伝播のシンボルは、採用した `cross-*` の調査のシードとして document agent の `ENTRY_POINTS` に入る。

**重要（1ラウンド制限）:** 本ステップは Step A-cross を再実行せず、自身を再帰的に再実行しない。
`/xddp-04-specout {CR}` の再実行で Step A-cross が改めて識別した連鎖候補は、上記「連鎖ガード」が除外する。
連鎖的な波及（A→B→C→…）を追跡したい場合は、人が `/xddp-investigate {CR} ripple --adopt --repo {repo} {symbol}` を実行すること。

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A-cross-propagate: 完了（対象 {len(DOC_REPOS)} リポジトリ）`

## Step A2: SPO Review Loop

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A2: SPOレビュー中`

Set `max_rounds` = `EFFECTIVE_REVIEW_MAX_ROUNDS_SPO`（Step 0.55 で解決済み。quick 時は `1`（ただし `REVIEW_MAX_ROUNDS.SPO` が明示的に `0` の場合は `0`）、full 時は Step 0.55 が `xddp.config.md` から読んだ `REVIEW_MAX_ROUNDS.SPO`（既定 3））。

For each `{repo}` in `AFFECTED_REPOS` (run review loops sequentially per repo):

（repo が "cross" 以外の場合のみ）レビュアーに渡す資料を決める（ラウンドループの外・repo ループ内で1回のみ）:
- `DIRECT_MODULE_DOCS` = 分割パス（`{CR_PATH}/04_specout/{repo}/modules/` がある）の場合だけ、次のモジュールの資料
  （`modules/{モジュール名}-spo.md`。サブディレクトリ分割したモジュールは `modules/{モジュール名}/` 配下の `.md` も）:
  - 採用した波紋調査がある repo: `{CR_PATH}/04_specout/{repo}/work/ripple-summary.json`（採用した調査の合算）の `direct_modules`
    （第0波のファイルを含むモジュール）のうち、資料のあるもの（`modules/` に資料があるもの）。
  - 採用した波紋調査が0件の repo（同じファイルの `adopted_runs` が空）: `modules/` 配下の資料すべて。
  統合パスならモジュール資料が `SPO-{CR}.md` の §2.A… に入っているため空（TARGET_FILE を読めばよい）。
  他のモジュールの資料は渡さない。波紋調査の要約は TARGET_FILE の §5.0 にある（全量の `ripple-summary.md` は渡さない）。

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. Read `~/.claude/skills/xddp-common/procedures/invoke-reviewer.md`, apply "## Invoke Reviewer" with:
   DOCUMENT_TYPE: SPO, NEXT_DOCUMENT_TYPE: DSN, TARGET_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md,
   REFERENCE_FILES: [
     {CR_PATH}/01_requirements/ (all .md),
     {CR_PATH}/03_change-requirements/CRS-{CR}.md,
     （repo が "cross" 以外の場合のみ追加）{DIRECT_MODULE_DOCS},
     （repo が "cross" の場合のみ追加）{CR_PATH}/04_specout/{repo}/modules/ (all .md, including subdirectories)
   ],
   REVIEW_ROUND: {round}, OUTPUT_FILE: {CR_PATH}/04_specout/{repo}/review/04_specout-review.md,
   （`CR_PROFILE` = `quick` の場合のみ追加）EXTRA_REVIEWER_PARAMS: QUICK_PROFILE: `true`,
   PROGRESS_CR_PATH: {CR_PATH}, PROGRESS_STEP_NUM: 4a, METRICS_TARGET: {repo}

2. Read review file.
   - No 🔴/🟡 → `issues_remain = false`, exit loop.
   - 🔴/🟡 found, `round < max_rounds` → apply fixes, increment `round`, continue.
   - `round = max_rounds`, issues remain:
     1. Append `"⚠️ 未解決の重大指摘あり。人間の判断が必要です。"` to the review output file.
     2. Run via Bash:
        `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py note-add --cr-path {CR_PATH} --step 4a --text "未解決指摘あり（{CR_PATH}/04_specout/{repo}/review/04_specout-review.md）"`
     Exit loop.

## Step A2-cross: Cross SPO AI Review (only when HAS_CROSS = true)

If `HAS_CROSS`:
  Read `~/.claude/skills/xddp-common/procedures/cross-artifact-review.md`, apply "## Cross Artifact Review" with:
    CR_PATH: {CR_PATH}
    STEP_NUM: 4a
    STEP_LABEL: `Step A2-cross`
    DOCUMENT_TYPE: SPO
    NEXT_DOCUMENT_TYPE: DSN
    TARGET_FILE: {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md
    REFERENCE_FILES: [
      {CR_PATH}/01_requirements/ (all .md),
      {CR_PATH}/03_change-requirements/CRS-{CR}.md,
      for each {repo} in AFFECTED_REPOS: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md (if exists)
    ]
    OUTPUT_FILE: {CR_PATH}/04_specout/cross/review/04_specout-cross-review.md
    DOC_DESCRIPTION: `インタフェース仕様に特化した成果物`
    （`CR_PROFILE` = `quick` の場合のみ追加）EXTRA_REVIEWER_PARAMS: QUICK_PROFILE: `true`

## Step A3: Human Review Gate (SPO)

Build `ARTIFACTS_TEXT` by expanding the following (AFFECTED_REPOS/HAS_CROSS are already resolved
in this skill's scope; the expanded result is a plain multi-line string, not a template):
```
**成果物:**
{for each repo in AFFECTED_REPOS:}
- {repo}: `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`{`work/no-ripple.json` がある repo は「（初回の波紋調査なし・人の判断）」}{採用した調査があれば「（採用した調査 {件数} 件: {名前…}）」}
  {`modules/` がある場合のみ}- モジュール: `{CR_PATH}/04_specout/{repo}/modules/`
  {採用した調査がある repo のみ}- 波紋調査の結果（採用した調査の合算の全量）: `{CR_PATH}/04_specout/{repo}/ripple-summary.md`
  {採用した調査ごとに、`ripple-graph.md` と `ripple-tree.md` の両方がある場合のみ}- 伝播の経路（{名前}）: `{CR_PATH}/04_specout/{repo}/ripple/{名前}/ripple-graph.md`（モジュール単位）・`{CR_PATH}/04_specout/{repo}/ripple/{名前}/ripple-tree.md`（関数単位）
  {採用した調査ごとに}- Discovery ログ（{名前}）: `{CR_PATH}/04_specout/{repo}/ripple/{名前}/discovery-log.md`
  - AIレビュー: `{CR_PATH}/04_specout/{repo}/review/04_specout-review.md`
{if HAS_CROSS:}
- cross: `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`
  - AIレビュー: `{CR_PATH}/04_specout/cross/review/04_specout-cross-review.md`

モジュール資料への修正は再実行でも残ります。再実行で調査結果・CRS・エントリポイントが変わると、SPO の §2〜§4・§5.3・§5.4・§5.6・§5.7・§7 は書き直されます。
工程4a の完了後にシンボルを足して調べる・調査を採用する・取り消す場合は `/xddp-investigate {CR}` を使います。
```

Read `~/.claude/skills/xddp-common/procedures/human-review-gate.md`, apply "## Human Review Gate" with:
  CR_PATH: {CR_PATH}
  STEP_NUM: 4a
  STEP_LABEL: `Step A3`
  ARTIFACTS_TEXT: {built above}
  REVISE_COMMAND: `/xddp-revise {CR} specout`（対象リポジトリを指定）
→ let `CHANGED`.

If `CHANGED`:
- For each `{repo}` in `AFFECTED_REPOS`: Read `~/.claude/skills/xddp-common/procedures/final-review-pass.md`,
  apply "## Final Review Pass" with:
    DOCUMENT_TYPE: SPO
    NEXT_DOCUMENT_TYPE: DSN
    TARGET_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
    REFERENCE_FILES: {Step A2 と同一}
    REVIEW_ROUND: (last_round + 1)
    OUTPUT_FILE: {CR_PATH}/04_specout/{repo}/review/04_specout-review.md
- If HAS_CROSS and the user changed cross/ SPO: Read `~/.claude/skills/xddp-common/procedures/final-review-pass.md`,
  apply "## Final Review Pass" with:
    DOCUMENT_TYPE: SPO
    NEXT_DOCUMENT_TYPE: DSN
    TARGET_FILE: {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md
    REFERENCE_FILES: {Step A2-cross と同一}
    REVIEW_ROUND: (last_round + 1)
    OUTPUT_FILE: {CR_PATH}/04_specout/cross/review/04_specout-cross-review.md

## Step B: Update CRS with Specout Findings

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step B: CRS更新中`
Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4b, STATE: 🔄 進行中, DETAIL_STEP: `Step B: CRS更新中`

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

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step C: Excel再生成中`

Read `~/.claude/skills/xddp-common/procedures/regenerate-crs-excel.md`, apply "## Regenerate CRS Excel" with:
  CR_PATH: {CR_PATH}
  CR: {CR}

## Step C5: Profile Fit Check

0. Let `ESCALATION_SUGGESTED` = `false`（本 Step 内で quick → full の昇格を推奨したかを保持する。
   Step D の分岐が参照する）。
1. For each `{repo}` in `AFFECTED_REPOS`, run via Bash:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py run-list --repo-dir {CR_PATH}/04_specout/{repo}`
   → 出力 JSON の `adopted_runs` が空でない repo（採用した調査がある repo）について、採用した調査の合算の `seed_direct_file_count` を
   合算して `TOTAL_SEED_DIRECT_FILES`（シードの直接参照ファイル数。変更対象ファイル数の目安）、`confirmed_file_count` を合算して
   `TOTAL_CONFIRMED_FILES`（波及ファイル数。参考値）、`seed_budget_truncated_count` を合算して `TOTAL_SEED_TRUNCATED` とする
   （`bfs-state.json` を直接読んで辞書キーを数えてはならない。決定的処理はスクリプトが担う）。
   採用した調査がある repo が1つもない場合は、「採用した波紋調査が無いため、規模の判定を省略しました」と1行伝えて本 Step C5 全体を
   スキップする。一部の repo だけ採用した調査が0件の場合は、手順2 の通知に
   「{repo…} は採用した波紋調査が無いため数えていません（実際の規模はこれより大きい可能性があります）」を1行添える。
2. If `CR_PROFILE` = `quick`:
     `TOTAL_SEED_DIRECT_FILES` > 5（quick 推奨基準「変更対象ファイル数 5 ファイル以下」）の場合:
       ユーザーに通知:
       > ⚠️ シードの直接参照ファイル数（{TOTAL_SEED_DIRECT_FILES}。変更対象ファイル数の目安。波及ファイル数は {TOTAL_CONFIRMED_FILES}）が
       > quick プロファイルの推奨基準（5ファイル以下）を超えています。
       > {`TOTAL_SEED_TRUNCATED` > 0 の場合: 予算で打ち切った投入シンボルが {TOTAL_SEED_TRUNCATED} 件あるため、実際より少ない可能性があります。}
       > `full` プロファイルへの切替を推奨します。切り替える場合は `/xddp-set-profile {CR} full` を実行してください
       > （工程5は quick では未実施のため、切替後に工程5から着手することを推奨します）。
       Run via Bash:
         `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py note-add --cr-path {CR_PATH} --step 4a --text "quick規模超過警告: シードの直接参照ファイル数{TOTAL_SEED_DIRECT_FILES}件（波及ファイル数{TOTAL_CONFIRMED_FILES}件）"`
       Set `ESCALATION_SUGGESTED` = `true`（Step D が工程5のスキップ記録・`/xddp-06-design` 案内を
       抑止するためのフラグ）。
   Else（`CR_PROFILE` = `full`）:
     `TOTAL_SEED_DIRECT_FILES` ≤ 5 の場合:
       ユーザーに通知:
       > ℹ️ シードの直接参照ファイル数（{TOTAL_SEED_DIRECT_FILES}。変更対象ファイル数の目安。波及ファイル数は {TOTAL_CONFIRMED_FILES}）は
       > quick プロファイルの推奨基準（5ファイル以下）を満たしています。
       > {`TOTAL_SEED_TRUNCATED` > 0 の場合: 予算で打ち切った投入シンボルが {TOTAL_SEED_TRUNCATED} 件あるため、実際より少ない可能性があります。}
       > 以降の工程（5・6）を `quick` に切り替えることもできます。切り替える場合は `/xddp-set-profile {CR} quick` を実行してください
       > （工程2・3・4は完了済みのためやり直しません。工程5のスキップ・工程6の簡略化・レビュー1ラウンド化が以降に適用されます）。
3. いずれの通知も処理を停止しない（人が判断する）。

## Step D: Update progress.md

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: ✅ 完了, DETAIL_STEP: `-`,
  ARTIFACT_LINK: `[04_specout/](04_specout/)`
  （STATE = ✅ 完了 のため、スクリプトが `## 備考・メモ` の `⚠️ 工程4a:` 行を自動削除する）
Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4b, STATE: ✅ 完了, DETAIL_STEP: `-`,
  ARTIFACT_LINK: `[CRS-{CR}.md](03_change-requirements/CRS-{CR}.md)`

If `ESCALATION_SUGGESTED` = true（Step C5 が quick → full の昇格を推奨した場合）:
  工程5のスキップ記録は行わない（`⬜ 未着手` のまま残す）。人がプロファイルを確定するまで
  工程5の要否が決まらないため、ここでスキップを確定させるとツール自身の昇格推奨を打ち消す。
  Set next command → `プロファイル確定待ち（/xddp-set-profile {CR} full で昇格、または quick のまま続行）`
  （progress.md の「## 次に実行すべきコマンド」欄に上記の文字列を記録する）
  ユーザーに通知:
  > 工程5の扱いはプロファイル確定後に決まります。
  > **昇格する場合:** `/xddp-set-profile {CR} full` → `/xddp-05-arch {CR}`
  > **quick のまま続行する場合:** （`HAS_CROSS` = false）`/xddp-06-design {CR}` ／
  > （`HAS_CROSS` = true）`/xddp-05-arch {CR}`
Else if `CR_PROFILE` = `quick` and `HAS_CROSS` = false:
  Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 5, STATE: ⏭️ スキップ（対象外）, DETAIL_STEP: `-`
  （この経路では `/xddp-05-arch` を起動しないため、工程5のスキップを記録する箇所が他に存在しない）
  Next command → `/xddp-06-design {CR}`
Else:
  Next command → `/xddp-05-arch {CR}`
（`quick` でも `HAS_CROSS` = true の場合は工程5で cross DSN のみ生成するため `/xddp-05-arch` を案内する）

## Step E: Report in Japanese
Report: repos investigated, waves executed per repo, affected file count per repo, cross/ synthesis result, review rounds.
加えて repo ごとに次を報告する（値は `specout_bfs.py run-list --repo-dir {CR_PATH}/04_specout/{repo}` の出力・採用した各調査の
`ripple/{名前}/discovery-log.md`・`ripple/{名前}/work/metrics.jsonl`・`ripple/{名前}/work/verify-sweep.json`・`work/ripple-summary.json`・
`work/documented-files.md`・`work/prelim-gap-reviewed.md`・`{CR_PATH}/metrics.jsonl` の `specout_doc_summary` の最新の行から転記する。
自分で数え直さない）:
- 波紋調査: 調査ごとに名前・由来・状態・採用の有無（`run-list`）。初回の調査を作らなかった repo は「未実施（人の判断。`work/no-ripple.json`）」。
  以下の判定エンジン〜再訪の項目は採用した調査ごとに出す（採用した調査が無い repo は出さない）。
- 追加下調べで資料にしたファイル数（`additional_file_count`）・関係なしと判断したファイル数（`gap_reviewed_unrelated_count`）・
  資料にできなかったシードの直接参照の数（`prelim_gap_count`。うち上限超過 `gap_over_limit_count`）・
  依頼調査で資料にしたファイル数（`requested_file_count`。1件以上のときだけ）。
- 検証スイープの未記録ファイル数（調査ごとの `work/verify-sweep.json` の `unrecorded_hits`。あれば SPO §9 を参照するよう添える）。
- 判定エンジン（`slice` / `rule`）。discovery-log の「## 探索設定」に判定エンジンの警告があればその文面。
  `SWITCHED_REPOS` に入った repo は「Wave {wave} から規則判定に切り替え」。
- LLM 分類に回ったヒット数（`metrics.jsonl` の波ごとの `llm_hits` の合計）。
- 打ち切りの有無（「## 打ち切り記録」の理由別の件数）。`wave-limit` があれば「`SPECOUT_MAX_WAVE_DEPTH` を上げて再実行すると
  続きから探索します」、`hit-budget` / `llm-budget` があれば「`/xddp-investigate {CR} ripple --adopt {シンボル}` で新しい調査として追えます」を添える。
- 予算で打ち切った投入シンボル（「## 予算で打ち切った投入シンボル（Wave N）」の各節の転記。あれば強調する）。
- 要約の拡大による再訪の件数（`metrics.jsonl` の `revisit_count` の合計）。
`HAS_CROSS` = true の場合は、`{CR_PATH}/04_specout/cross/work/cross-propagation-log.json` の `status` = `no-ripple` の要素の数
（初回の波紋調査を作らない repo のため見送ったクロスリポジトリ伝播）を報告する（0 なら省略）。
