---
name: xddp-04-specout
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
  1つ以上指定してください。例: `/xddp-04-specout <CR番号> --re-discover newSymbol`"
  Stop.

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.

Scan `REST_ARGS` tokens for the exact string `--re-discover` (position-independent):
If found:
  Set `RE_DISCOVER = true`.
  Remove the `--re-discover` token from `REST_ARGS`; remaining tokens become the new `REST_ARGS`.
  If remaining `REST_ARGS` is empty:
    Tell the user: "`--re-discover` を指定する場合は追加調査するエントリポイント（シンボル名またはファイルパス）を
    1つ以上指定してください。例: `/xddp-04-specout {CR} --re-discover newSymbol`"
    Stop.
Else:
  Set `RE_DISCOVER = false`.
Let `ENTRY_POINTS` = `REST_ARGS` (may be empty). Let `TODAY` = today's date.

(xddp.config.md lookup done in xddp-common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
DOCS_DIR, DOCS, REPOS_MAP, REPOS_KEYS, IS_MULTI, DEVELOPMENT_MODE, EXCLUDE_PATTERNS, INCLUDE_EXTENSIONS,
MAX_WAVE_DEPTH, SPECOUT_MAX_AFFECTED_FILES, SPECOUT_MAX_FILES_PER_MODULE, SPECOUT_DIAGRAM_LEVEL,
SPECOUT_SEQUENCE_LEVELS, SPECOUT_BACKEND, SPECOUT_BACKEND_OVERRIDES, SPECOUT_HIT_FILTER,
SPECOUT_CROSS_PROPAGATE, SPECOUT_CLASSIFY_CHUNK_SIZE, SPECOUT_CLASSIFY_PARALLEL, SPECOUT_SEED_GATE,
SPECOUT_WAVE_HIT_BUDGET, SPECOUT_LLM_HIT_BUDGET, SPECOUT_SLICE, SPECOUT_SLICE_IGNORE_CALLS, SPECOUT_SLICE_H_AS,
SPECOUT_SLICE_PYTHON_BIN, SPECOUT_DOC_LINE_BUDGET, SPECOUT_DOC_MAX_MODULES, SPECOUT_DOC_PARALLEL, CR_PROFILE.
`SPECOUT_HIT_FILTER` は未指定時 `conservative`。`SPECOUT_CLASSIFY_CHUNK_SIZE` は未指定時 `40`、
`SPECOUT_CLASSIFY_PARALLEL` は未指定時 `4`。`SPECOUT_SEED_GATE` は未指定時 `true`。`MAX_WAVE_DEPTH` は未指定時 `6`、
`SPECOUT_WAVE_HIT_BUDGET` は未指定時 `10000`、`SPECOUT_LLM_HIT_BUDGET` は未指定時 `160`、`SPECOUT_SLICE` は未指定時 `auto`、
`SPECOUT_SLICE_IGNORE_CALLS` は未指定時 空、`SPECOUT_SLICE_H_AS` は未指定時 `auto`、`SPECOUT_SLICE_PYTHON_BIN` は未指定時 空、
`SPECOUT_DOC_LINE_BUDGET` は未指定時 `2000`、`SPECOUT_DOC_MAX_MODULES` は未指定時 `30`、`SPECOUT_DOC_PARALLEL` は未指定時 `4`。)
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

If `CR_PROFILE` = `quick`:
  Let `EFFECTIVE_MAX_WAVE_DEPTH` = `MAX_WAVE_DEPTH`（quick でも探索の深さは制限しない）
  Let `EFFECTIVE_DIAGRAM_LEVEL` = `SPECOUT_DIAGRAM_LEVEL` が `minimal` の場合は `minimal`、それ以外は `standard`
    （quick は記載量を**下げることはあっても上げない**。運用者が `minimal` を明示している場合に
    `standard` へ引き上げると quick の方が `full` より重い SPO を生成する逆転が起きる）
  Let `EFFECTIVE_SEQUENCE_LEVELS` = `SPECOUT_SEQUENCE_LEVELS` の要素のうち `module` のみを残した値
    （`module` を含まない設定の場合は `SPECOUT_SEQUENCE_LEVELS` をそのまま使う。quick が粒度を
    上げないための規則。既定値 `module, class` では `module` に絞られる）
  Let `EFFECTIVE_HIT_FILTER` = `SPECOUT_HIT_FILTER`
    （運用者が `off` を明示している場合にその意図を踏み越えて `conservative` を強制しない。
    既定値は `conservative` のため、既定構成では従来どおりノイズ削減が効く。この2行は quick でも
    full と同値である — quick が簡略化するのは SPO 文書の記述量のみで、探索の深さ・ヒットフィルタは
    区別しない、という設計判断そのものであるため意図的にこの分岐内で下記 Else 分岐と同じ代入をしている）
  Read `{WORKSPACE_ROOT}/xddp.config.md` and extract `REVIEW_MAX_ROUNDS.SPO`（default: `3`）:
    If it is explicitly `0`: Let `EFFECTIVE_REVIEW_MAX_ROUNDS_SPO` = `0`
      （運用者が SPO レビューを明示的に無効化している場合はその意図を優先し、quick でも復活させない）
    Else: Let `EFFECTIVE_REVIEW_MAX_ROUNDS_SPO` = `1`
  Let `EFFECTIVE_SPO_DETAIL_LEVEL` = `brief`
Else:
  Let `EFFECTIVE_MAX_WAVE_DEPTH` = `MAX_WAVE_DEPTH`
  Let `EFFECTIVE_DIAGRAM_LEVEL` = `SPECOUT_DIAGRAM_LEVEL`
  Let `EFFECTIVE_SEQUENCE_LEVELS` = `SPECOUT_SEQUENCE_LEVELS`
  Let `EFFECTIVE_HIT_FILTER` = `SPECOUT_HIT_FILTER`
  Read `{WORKSPACE_ROOT}/xddp.config.md` and extract `REVIEW_MAX_ROUNDS.SPO`（default: `3`）
    → let `EFFECTIVE_REVIEW_MAX_ROUNDS_SPO` = that value
  Let `EFFECTIVE_SPO_DETAIL_LEVEL` = `full`

**判定エンジンの決定（CR_PROFILE によらない）:**
Let `SLICE_PY` = `SPECOUT_SLICE_PYTHON_BIN`（空なら `command -v python3 || command -v python` の結果）。
Run via Bash: `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py probe`
（ここではファイルに書かない。警告文を `init` に渡すファイルは、Step A-Seed で repo ごとに
`{CR_PATH}/04_specout/{repo}/work/slice-probe.json` に書く）
  スクリプトが見つからない場合は setup.sh 実行を案内して停止する。`SLICE_PY` が起動できない・exit 非0 の場合は
  stderr を表示し、`SPECOUT_SLICE_PYTHON_BIN` の確認を案内して停止する（設定の誤りを規則判定で黙って隠さない）。
Let `PROBE_ENGINE` = stdout の `engine`（`slice` / `unavailable`）。
If `SPECOUT_SLICE` = `off`: Let `EFFECTIVE_SLICE_ENGINE` = `rule`, `USE_PROBE_WARNING` = false。
Else if `PROBE_ENGINE` = `slice`: Let `EFFECTIVE_SLICE_ENGINE` = `slice`, `USE_PROBE_WARNING` = false。
Else: Let `EFFECTIVE_SLICE_ENGINE` = `rule`, `USE_PROBE_WARNING` = true（警告文は、Step A-Seed で repo ごとに書く probe の出力ファイルにあり、`init` が読む）。
`EFFECTIVE_SLICE_ENGINE` は、Step A-Seed の `init`（状態ファイルを新しく作る repo）でだけ使う。
既に状態ファイルがある repo の判定エンジンは state の `slice_engine` を正とする（Step A の「### 判定エンジンの照合」）。

`specout_bfs.py init`（Step A-Seed で SKILL が実行する）では `EFFECTIVE_MAX_WAVE_DEPTH` / `EFFECTIVE_HIT_FILTER` /
`EFFECTIVE_SLICE_ENGINE` / `SPECOUT_WAVE_HIT_BUDGET` / `SPECOUT_LLM_HIT_BUDGET` / `SPECOUT_SLICE_H_AS` /
`SPECOUT_SLICE_IGNORE_CALLS` を使用する。これらは `bfs-state.json` に保存され、以降の波ループで `specout_bfs.py search`・
`specout_slice.py` が読み込むため、`search`・`classify` には渡さない（再開を含むその CR の判定の単一情報源は state）。
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

For each `{repo}` in `AFFECTED_REPOS`, check whether `{CR_PATH}/04_specout/{repo}/work/bfs-state.json` exists.
If it exists, run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py status --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --brief`
→ 出力 JSON を以下の「### 判定エンジンの照合」・上限の更新・状態テーブルで使う（スクリプトが見つからない場合は setup.sh 実行を案内して停止。実行時エラーの場合は stderr を表示して停止）。
`--brief` はコンテキスト蓄積対策であり、
`ok`/`state`/`current_wave`/`wave_write_complete`/`remaining_frontier_count`/`confirmed_file_count`/`max_wave_depth`/
`truncated_wave_limit_count`/`slice_engine`/`seed_direct_file_count`/`seed_budget_truncated_count` のみを返す
（状態テーブルの判定・下記「件数一致検証」の前提ガードは `state`/`wave_write_complete` を、上限の更新は `max_wave_depth`/
`truncated_wave_limit_count` を、判定エンジンの照合は `slice_engine` を使う。`seed_direct_file_count`/`seed_budget_truncated_count`/
`confirmed_file_count`〔参考値〕は「## Step C5: Profile Fit Check」専用である）。

**RE_DISCOVER は repo ごとに決める:** RE_DISCOVER=true でも `ENTRY_POINTS_BY_REPO[repo]` が空の repo（マルチリポジトリで、人の
指定が別の repo にだけ割り当てられた repo）は、以降の判定エンジンの照合・状態テーブルで RE_DISCOVER=false の行として扱う
（空の `merge-frontier --reset-wave-origin` で起点だけが置き直されることと、空の frontier で `re-discover` が実行されて続く
`search` が失敗することを防ぐため）。

### 判定エンジンの照合

状態を書き換える処理（下記の上限の更新〔`extend`〕、状態テーブルの `merge-frontier`・Re-discover Processing、
「## Step A-cross-propagate」の `re-discover`）の前に照合する。照合の定義はこの小節の1つだけで、下記「適用する場所」の
2か所から適用する。照合の結果 `ENGINE_CHECK`（`ok` / `switched` / `blocked`）を返し、repo の扱いは適用した場所が決める。

対象の各 repo について、`status --brief` の `slice_engine` が `slice` で、「## Step 0.55」の「判定エンジンの決定」の
`PROBE_ENGINE` が `unavailable` の場合（`SPECOUT_SLICE_PYTHON_BIN` の Python で tree-sitter を import できない場合）、
次を人へ提示し、回答を待つ:
> ⚠️ {repo} はスライス判定（tree-sitter）で探索を始めましたが、この環境では tree-sitter を使えません。
> 1. tree-sitter を使える Python を指定して再実行する: `SPECOUT_SLICE_PYTHON_BIN` に tree-sitter を入れた Python のパスを
>    設定するか、今の Python に `pip install -r ~/.claude/skills/xddp-04-specout/scripts/requirements-slice.txt` で入れてから、
>    `/xddp-04-specout {CR}` を再実行する（探索の途中から、スライス判定のまま続く）。
> 2. この CR の残りの波を規則判定に切り替えて続ける（探索済みの波の結果は残る。以降の波は、グローバル変数の読み手・
>    関数の外のヒットの値を追わず、要約を使った判定と再訪をしない。discovery-log に切り替えが記録される）。
> 3. 状態ファイルを退避・削除し、規則判定で最初から探索する: `{CR_PATH}/04_specout/{repo}/work/bfs-state.json`・
>    `work/bfs-state.md`・`work/waves/`・`discovery-log.md`・`SPO-{CR}-funcmap.md` を退避・削除し、マルチリポジトリの場合は
>    `{CR_PATH}/04_specout/cross/work/cross-propagation-log.json` から `repo` が {repo} の要素を削除してから、
>    `SPECOUT_SLICE: off` で `/xddp-04-specout {CR}` を再実行する（伝播の記録を残すと、クロスリポジトリ伝播のシンボルが
>    再投入されないため）。
- 2 を選んだ場合: Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py switch-engine --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --to rule --today {TODAY}`
  （If it errors: display stderr and stop.）`ENGINE_CHECK` = `switched` とし、`SWITCHED_REPOS` に {repo} と stdout の `wave` を記録する。
- 1・3 を選んだ場合（または回答が無い場合）: state を変えず、`ENGINE_CHECK` = `blocked` とする。
- 照合が不要な場合（state の `slice_engine` が `rule`、または `PROBE_ENGINE` が `slice`）: `ENGINE_CHECK` = `ok` とする。
  state が `rule` なら、環境に tree-sitter があっても `rule` のまま続ける。

**適用する場所（2か所。どちらも状態を書き換える直前）:**
1. ここ（Step A の `status --brief` の直後、下記の上限の更新より前）: この実行で Step A の探索を進める repo
   （`in-progress` の repo、`complete` で `truncated_wave_limit_count` > 0 かつ `EFFECTIVE_MAX_WAVE_DEPTH` が `max_wave_depth`
   より大きい repo、RE_DISCOVER=true〔repo ごとの値〕の repo）だけを対象にする。`blocked` の repo は `ENGINE_BLOCKED_REPOS` に
   入れ、上限の更新と状態テーブルの処理を飛ばし、波ループに入れない（「**波ループ終了後**」の案内で Step A-Document へ
   進まずに停止する）。
2. 「## Step A-cross-propagate」で、`complete` の repo に Re-discover Processing を適用する直前: 伝播先として決まった repo
   だけを対象にする。`blocked` の repo は投入を見送り（伝播の記録は `deferred` のまま）、見送りの警告を出す。
   `ENGINE_BLOCKED_REPOS` には入れず、停止もしない（他の repo の伝播と Document は続ける）。

**上限の更新（状態テーブルの前。状態によらない）:** 状態ファイルがある repo のうち `ENGINE_BLOCKED_REPOS` に入っていない
ものについて:
- `status --brief` の `max_wave_depth` より `EFFECTIVE_MAX_WAVE_DEPTH` が大きい repo: Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py extend --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --max-wave {EFFECTIVE_MAX_WAVE_DEPTH} --today {TODAY}`
  If it errors: display stderr and stop.
  stdout の `state` を、以降の状態テーブルの判定に使う（`status --brief` を取り直さない）。
  `restored_count` > 0 なら、人へ「{repo}: 波数上限を {M} → {N} に上げ、打ち切った {restored_count} 件から探索を続けます」と
  伝える。それ以外は「{repo}: 波数上限を {M} → {N} に更新しました」と伝える（M は `status --brief` の `max_wave_depth`）。
- `EFFECTIVE_MAX_WAVE_DEPTH` が `max_wave_depth` より小さい repo: 「{repo}: 設定の波数上限 {N} は、この CR の探索で使っている
  {M} より小さいため、{M} のまま続けます」と伝える（state の値を使う）。

| bfs-state.json 状態 | RE_DISCOVER（repo ごと） | 対応 |
|---|---|---|
| ファイルが存在しない | false | Step A-Prelim → discovery-setup → Step A-Seed（`init` を含む）を実行してから波ループに入る |
| ファイルが存在しない | true | 既存 visited セットなし。Step A-Prelim → discovery-setup → Step A-Seed（`init` を含む）を実行してから波ループに入る（ユーザーに通知: "既存の探索履歴が存在しないため新規 Discovery として実行します"） |
| 状態: `in-progress` | false | 波ループが中断している（上限の更新で `in-progress` に戻った repo を含む）。Step A-Prelim・discovery-setup・Step A-Seed はスキップし、SKILL 側の波ループを `search` から再開する（Visited/Frontier は bfs-state.json から自動復元されるため、追加の引数は不要） |
| 状態: `in-progress` | true | `specout_bfs.py merge-frontier --reset-wave-origin` で ENTRY_POINTS_BY_REPO[repo] を既存 Frontier にマージ（HIGH 平文形式で追記）し、探索の起点を次に検索する波に置き直して（人の指定を上限の波数まで調べる）から SKILL 側の波ループを再開する |
| 状態: `complete` | false | Discovery 済み。Document フェーズへスキップ |
| 状態: `complete` | **true** | `recovery-procedures.md` の「## Re-discover Processing」を適用する（更新後の上限で数える） |

（上限の更新で `in-progress` に戻った repo に RE_DISCOVER=true が重なった場合は `in-progress` + true の行を適用し、
`re-discover`〔frontier を置き換える〕ではなく `merge-frontier --reset-wave-origin` で人の指定を加える。戻したエントリを失わず、
人の指定を上限の波数まで調べるため。）

**件数一致検証（独立回帰チェック。`bfs-state.json` が存在する repo すべてに適用する）:**

**適用対象ガード:** `bfs-state.json` が存在しない repo（新規 CR）では**本ブロック全体をスキップする**。
直前の `specout_bfs.py status --brief` 自体が実行されておらず、下記の前提ガードが参照する
`wave_write_complete` が得られないためである（status を追加実行してはならない — 状態ファイルが
無い以上エラーになる）。新規 CR は後述の**波ループ終了時の検証**で検証される。

**前提ガード:** 直前の `specout_bfs.py status --brief` の出力 JSON の `wave_write_complete` が `false` の場合、
**本検証は実行しない**。この状態は「`search` 済み・`commit-wave` 未完」を意味する。
`search` 自体は discovery-log.md へ **`## Wave N` セクションを**書かない（`## Wave N` の
書き込みは `cmd_commit_wave` のみ。`search` が書くのは `## 未ヒット投入シンボル（Wave N）`・`## ヒット過多の投入シンボル（Wave N）`
セクションの upsert と、バックエンド警告・パース不能ヒット警告の blockquote 追記に限られ、
いずれも `## Wave N` ブロックの外である）ため、`search` 直後に停止したケースでは当該波の `## Wave N` が
そもそも存在せず `--wave all` は当該波を列挙しない。問題になるのは
**`commit-wave` が `_append_to_file` の途中でクラッシュした場合**であり、このとき
`## Wave N` と実行コマンド一覧だけが書かれヒット行テーブルが欠けた**書きかけセクション**が残る。
これを検証すると不一致となり、`## Count Mismatch Handling` が
「Discovery やり直し / 承知で続行」という**誤った選択肢**を提示してしまう。
`wave_write_complete = false` は両ケースを区別せずに立つフラグであるため、
安全側に倒して一律スキップする（ガードを外してはならない理由がこれである）。

正しい復旧は「`search` から再開する」ことであり、これは
**`recovery-procedures.md`「## Wave 途中失敗からの再開（経路統一）」**が担う。
下記「波ループ」に入れば `wave_write_complete: false` を検出して自動的に `search` から再開し、
書きかけ Wave セクションはスクリプトが切り捨てて再構築する。
したがって SKILL 側は**本検証をスキップして通常の波ループへ進めばよい**。
再開が完了すれば `wave_write_complete` が `true` になり、
**波ループ終了時の検証（下記）で検証される**。

`wave_write_complete` が `true` の場合、Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_verify_counts.py --log {CR_PATH}/04_specout/{repo}/discovery-log.md --wave all --strict; echo "VERIFY_EXIT=$?"`
  （終了コードを stdout の `VERIFY_EXIT=` 行で明示的に受け取り、下記の分岐を決定的にする）
- **exit 3（件数不一致）:** stdout JSON の `mismatch_waves` を取得し、
  Read `~/.claude/skills/xddp-04-specout/recovery-procedures.md`,
  apply "## Count Mismatch Handling" with:
    CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, MISMATCH_WAVES: {mismatch_waves}
- **exit 1（検証の実行エラー。ログ破損・`## Wave N` 不在等）:** stderr を表示して停止する
  （不一致とは別事象であり、人がログを確認する必要がある）。
- **exit 2（実行環境エラー。件数不一致ではない）:** argparse の使用法エラー、または
  Python がスクリプトを開けなかった場合（`setup.sh` 未実行）である。
  stderr を表示し、`bash ClaudeCode/setup.sh` の実行を案内して停止する。
  **`## Count Mismatch Handling` を適用してはならない。**
- **exit 0:** 何も表示せず次へ進む（正常時に出力を増やさない）。
- **上記以外の非0:** stderr を表示して停止する（未知の失敗モードを不一致として扱わない）。

上記テーブルで `recovery-procedures.md` への参照が指示された場合、該当する呼び出しを実行する
（引数は recovery-procedures.md 側の各セクションが宣言する Inputs と厳密に一致させる。
xddp-common の apply 呼び出し規約と同じ方式）:

`in-progress` + RE_DISCOVER=true の場合:
Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py merge-frontier --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --symbols {ENTRY_POINTS_BY_REPO[repo] をカンマ区切りで展開} --entry-point-symbols {ENTRY_POINTS_BY_REPO[repo] をカンマ区切りで展開} --reset-wave-origin`
If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
（判定エンジンが `slice` の repo では、加えたシンボルのシード要約の取り込みを波ループ a の `search`〔exit 6〕から行う）
その後 SKILL 側の波ループを再開する（下記「波ループ」を参照）。

`complete` + RE_DISCOVER=true の場合:
Read `~/.claude/skills/xddp-04-specout/recovery-procedures.md`, apply "## Re-discover Processing" with:
  CR_PATH: {CR_PATH}, repo: {repo}, ENTRY_POINTS: {ENTRY_POINTS_BY_REPO[repo]}, TODAY: {TODAY}

→ bfs-state.json / discovery-log.md / progress.md はそのファイル内の記述に従って更新される。
  `{CR_PATH}/04_specout/{repo}/work/bfs-state.md` は bfs-state.json から自動生成される人可読ビューであり、直接参照・編集しない。

---

**Step A-Prelim: 下調べ（初回のみ）**

`{CR_PATH}/04_specout/{repo}/work/bfs-state.json` が**存在しない** `{repo}` のみを対象とする（以下「setup 対象 repo」。
Step A-Prelim・discovery-setup・Step A-Seed で同じ集合を使う）。state が既に存在する repo（上表で「波ループを再開する」と
判定された repo）は Step A-Prelim・discovery-setup・Step A-Seed のいずれも行わず、直接「波ループ」へ入る
（`specout_bfs.py init` は state 既存時に異常終了する）。
setup 対象 repo が無ければ、Step A-Prelim・discovery-setup・Step A-Seed を飛ばして「波ループ」へ進む。

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A-Prelim: 下調べ中`

For each setup 対象 repo:
  Let `MODULE_CATALOG_FILE[{repo}]` = `{DOCS}/{repo}/module-catalog.md`（存在しなければ空文字列）。
  Let `CRS_FILE` = `{CR_PATH}/03_change-requirements/CRS-{CR}.md`。
  下調べの再利用を判定する（「新しい」はファイルの更新時刻で比較する。例: Bash `test {A} -nt {B}`）:
  - `{CR_PATH}/04_specout/{repo}/work/prelim-index.md` が存在し、かつ `CRS_FILE` より新しい → 下調べを再利用する
    （起動対象に加えない）。`PRELIM_INDEX_FILE[{repo}]` = そのパス。
  - `work/prelim-index.md` が無く、`{CR_PATH}/04_specout/{repo}/work/seed-candidates.md` が存在し、かつ `CRS_FILE` より新しい
    → 下調べなしで再開する（起動対象に加えない）。何も削除しない（人が編集した候補表と `work/seed-unsupported.json` を保持する）。
    `PRELIM_INDEX_FILE[{repo}]` = 空。
  - それ以外 → 前回の残骸のうち存在するものを削除して、起動対象に加える:
    `{CR_PATH}/04_specout/{repo}/` 配下の `SPO-{CR}.md`、`modules/`、`work/prelim-index.md`、`work/observation-memo.md`、
    `work/documented-files.md`、`work/module-assignments.json`、`work/seed-candidates.md`、`work/seed-unsupported.json`

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
4. 起動対象の全 repo について（再利用・下調べなしで再開と判定した repo には適用しない。
   下調べなしで再開の repo に下記の削除を適用すると、保持した候補表が消える）:
   - `{CR_PATH}/04_specout/{repo}/work/prelim-index.md` があれば `PRELIM_INDEX_FILE[{repo}]` = そのパス。
   - 無ければ（下調べの失敗）、上記の残骸のうち存在するものを削除し、`PRELIM_INDEX_FILE[{repo}]` = 空として、次を提示して続行する:
     > ⚠️ {repo} の下調べが完了しませんでした。下調べなしで続行します（シード候補は CRS の記述と指定された
     > エントリポイントから作り、資料は波紋調査の後にすべてのファイルを読んで作成します）。

**Setup: discovery-setup（シード候補表の作成・初回のみ）**

setup 対象 repo ごとに、起動の要否と `APPEND_ONLY` を決める
（`{CR_PATH}/04_specout/{repo}/work/` を `{WORK}` と略記する。「新しい」「古い」はファイルの更新時刻で比較する）:
- `{WORK}/seed-candidates.md` が無い、または `{WORK}/prelim-index.md`（無ければ `CRS_FILE`）より古い
  → 起動する（`APPEND_ONLY` = `false`。候補表を新規に作る）。
- `{WORK}/seed-candidates.md` があり、`{WORK}/prelim-index.md`（無ければ `CRS_FILE`）より新しい（シード確認で止めた後の再実行）:
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
     [--ledger {CR_PATH}/04_specout/{repo}/work/documented-files.md]
   ```
   `--ledger` は `PRELIM_INDEX_FILE[{repo}]` が空でない場合のみ渡す。
   → 候補表の「ヒット（ファイル数）」「警告」列と、表の直前の注記行（採用シンボルの合計ヒット数）が更新され、stdout の JSON から
   `adopted_count` / `zero_hit` / `zero_after_filter` / `noisy` / `all_adopted_noisy` / `over_budget` /
   `all_adopted_noisy_or_over_budget` / `adopted_total_hits` / `over_budget_total`（`--ledger` 指定時は `prelim_module_count` /
   `prelim_file_count` も）を得る。
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
2. `GATE` = `SPECOUT_SEED_GATE` が `true`、またはいずれかの repo で `adopted_count` = 0 または
   `all_adopted_noisy_or_over_budget` = true。

全 setup 対象 repo 分をまとめて提示する（repo ごとに。候補表を Read して転記する）:
> 📋 **{repo} の波紋調査シード候補**
> {`PRELIM_INDEX_FILE[{repo}]` が空でない場合のみ}下調べ資料: `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`{`modules/` があれば「・`{CR_PATH}/04_specout/{repo}/modules/`」}（{prelim_module_count} モジュール・{prelim_file_count} ファイル）
> {候補表の「## 候補」の転記（表の直前の注記行を含む）}
> {「## 解決できなかった ENTRY_POINT」「## 識別子を特定できなかった振る舞い」にデータ行があれば転記}
> {`EXCLUDED_ENTRY_POINTS[{repo}]` の各要素について: 引数で指定された `{シンボル}` は候補表で除外されています（除外理由: {除外理由}）。採用する場合は採否を ☑ にしてください}
> {警告があれば: 未ヒット＝CRS の識別子の誤字・旧名称の可能性／フィルタ後0件＝`SPECOUT_HIT_FILTER` の設定を確認／ヒット過多＝一般語の疑い／予算超過＝1波の予算を超えるため、第0波で丸ごと打ち切られる}
> {`over_budget` が非空の場合: `予算超過` の候補は、波紋調査で丸ごと打ち切られます}
> {`adopted_count` = 0 の場合: ⚠️ 採用された候補がありません。候補を追加してください}
> {`all_adopted_noisy` = true の場合: ⚠️ 採用した候補の全件がヒット過多です。変更対象を特定できていない可能性が高いため、候補を見直してください}
> {`all_adopted_noisy` = false で `all_adopted_noisy_or_over_budget` = true の場合: ⚠️ 採用した候補の全件がヒット過多か予算超過です。予算超過の候補は波紋調査の第0波で丸ごと打ち切られるため、変更対象を追えない可能性があります。候補を見直すか、シンボルを分けて実行してください}

`over_budget_total` = true の repo は、候補表の注記行（採用シンボルの合計ヒット数と分割実行の案内）を必ず提示文に含める
（`GATE` = false で確認を待たない場合も含める）。

モジュール数・ファイル数は手順1 の stdout の `prelim_module_count`・`prelim_file_count` を使う（自分で数えない）。
「下調べ資料があるか」は `PRELIM_INDEX_FILE[{repo}]` が空でないことで判定する（台帳の有無では判定しない）。

`GATE` = true の場合、次を尋ねて待つ:
> 各 repo の候補表 `{CR_PATH}/04_specout/{repo}/work/seed-candidates.md` の「採否」列を編集するか、
> 「`{repo}`: `X` を除外（理由）、`Y` を追加」の形で指示してください。
> - **確定** → 採用した候補で全 repo の波紋調査を開始します
> - **編集した／指示した** → ヒット数を再試算して再提示します
> - **下調べ資料で止める** → 波紋調査を行わずに終了します（影響範囲は網羅されません）

どの setup 対象 repo でも `PRELIM_INDEX_FILE[{repo}]` が空の場合は、3つ目の選択肢を
「**ここで止める** → 候補表を残して、波紋調査を行わずに終了します（影響範囲は網羅されません）」と表示する
（動作は「下調べ資料で止める」と同じ。以下、両者をまとめて「下調べ資料で止める」と呼ぶ）。

- 指示で答えた場合: SKILL が候補表を Edit する（除外＝採否 ☐＋除外理由、追加＝行を追加し由来 `人が追加`・採否 ☑）。
  手順1 へ戻る。
- 「編集した」と答えた場合: 手順1 へ戻る。
- 「確定」の場合: 手順1 を全 setup 対象 repo について再実行し、最新の候補表で判定する。
  採用が0件の repo が残っている場合は確定させず、その repo の候補の追加を求めて再度尋ねる（`init` は起点なしでは開始できない）。
  0件の repo が無ければ手順3 へ進む。
- 「下調べ資料で止める」: CR 全体（全 setup 対象 repo）に適用する（repo ごとには選べない）。
  Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: ⏸ 中断, DETAIL_STEP: `Step A-Seed: 下調べ資料で停止（波紋調査未実施）`
  progress.md の「## 次に実行すべきコマンド」欄に `/xddp-04-specout {CR}` を記録する。
  資料のパス（`PRELIM_INDEX_FILE[{repo}]` が空でない repo の `SPO-{CR}.md`・`modules/`）を示し、次を案内して終了する
  （工程4b へ進まない）:
  > `/xddp-04-specout {CR}` を再実行すると、下調べ資料（下調べが完了した repo のみ）と候補表をそのまま使って
  > シード確認から再開します（エントリポイントを引数で指定した場合は候補表に追記されます）。
  {`PRELIM_INDEX_FILE[{repo}]` が空の repo があれば}
  > {repo} は下調べなしで再開します。下調べからやり直す場合は `{CR_PATH}/04_specout/{repo}/work/seed-candidates.md` を
  > 削除してから再実行してください（候補表の編集内容は失われます）。
- `GATE` = false の場合: 提示のみで手順3 へ進む（「下調べ資料で止める」は選べない）。

3. 全 setup 対象 repo について、`{CR_PATH}/04_specout/{repo}/discovery-log.md`・`{CR_PATH}/04_specout/{repo}/work/waves/`・
   `{CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md` のいずれかが残っていれば削除し、その旨を1行で通知する（状態ファイルの無い
   discovery-log・波ファイル・funcmap は前回の残骸であり、状態と整合しない。funcmap は資料の確定で作り直される）。
   続けて、判定エンジンの設定をファイルに書く（警告文・正規表現の自由文をシェルの引数で渡さないため）:
   - Run via Bash: `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py probe --out {CR_PATH}/04_specout/{repo}/work/slice-probe.json`
     （If it errors: display stderr and stop.）
   - `SPECOUT_SLICE_IGNORE_CALLS` の値を Write ツールで `{CR_PATH}/04_specout/{repo}/work/slice-ignore-calls.txt` に1行で書く
     （値が空なら空のファイル。値の前後の空白・引用符はそのまま書く）。
   続けて Run via Bash:
   ```
   PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py init \
     --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --repo-path {REPOS_MAP[repo]} \
     --discovery-log {CR_PATH}/04_specout/{repo}/discovery-log.md \
     --seed-candidates {CR_PATH}/04_specout/{repo}/work/seed-candidates.md \
     --unsupported-patterns {CR_PATH}/04_specout/{repo}/work/seed-unsupported.json \
     --today {TODAY} --cr {CR} --repo {repo} \
     --exclude "{EXCLUDE_PATTERNS}" --include-ext "{INCLUDE_EXTENSIONS}" --max-wave {EFFECTIVE_MAX_WAVE_DEPTH} \
     --max-files-per-module {SPECOUT_MAX_FILES_PER_MODULE} \
     --backend {SPECOUT_BACKEND_OVERRIDES.get(repo, SPECOUT_BACKEND)} --hit-filter {EFFECTIVE_HIT_FILTER} \
     --scope-summary-file {CR_PATH}/04_specout/{repo}/work/_scope-summary.md \
     --wave-hit-budget {SPECOUT_WAVE_HIT_BUDGET} --llm-hit-budget {SPECOUT_LLM_HIT_BUDGET} \
     --slice-engine {EFFECTIVE_SLICE_ENGINE} --probe-file {CR_PATH}/04_specout/{repo}/work/slice-probe.json \
     --slice-ignore-calls-file {CR_PATH}/04_specout/{repo}/work/slice-ignore-calls.txt --slice-h-as {SPECOUT_SLICE_H_AS} \
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

（`--module-catalog` を渡すと、Wave 0 の `commit-wave` 時にモジュール優先度の算出と以後の波での frontier の振り分けを
スクリプトが行う。`MODULE_CATALOG_FILE` が空の場合は優先度差別化なしの通常 BFS になる。）

### シード要約の取り込み（Input: repo）

波ループ a で `search` が終了コード 6（シード要約の取り込みが済んでいない）を返したときだけ適用する
（シードを入れる処理〔`init`・`merge-frontier --reset-wave-origin`・`re-discover`〕が判定エンジン `slice` の repo で
「取り込み待ち」の印を付け、`search` がそれを検出する。Step A-Seed・状態テーブル・Re-discover Processing からは直接呼ばない）。

Run via Bash:
  `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py seed-summary --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --out {CR_PATH}/04_specout/{repo}/work/seed-summaries.json`
  （`--symbols` は渡さない。対象は state の取り込み待ちのシード）
  exit 5 の場合は「### 判定エンジンの照合」の提示文（選択肢1〜3）を示し、当該 repo を取り込みの失敗とする。
  それ以外の exit 非0 は stderr を表示し、当該 repo を取り込みの失敗とする。
stdout の `globals` が空でなければ、Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py merge-frontier --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --symbols {globals をカンマ区切り} --as-seed-globals --summaries-file {stdout の summaries_file}`
`globals` が空なら、Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py merge-frontier --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --symbols '' --summaries-file {stdout の summaries_file}`
  （`--symbols` は空を受け付ける。要約だけを取り込む）
`merge-frontier` が exit 非0 の場合は stderr を表示し、当該 repo を取り込みの失敗とする。
（シードのグローバルの取り込みには `--reset-wave-origin` を付けない。起点の置き直しは人の指定を加えるときだけ行う）

**波ループ（ACTIVE_REPOS が空になるまで繰り返す。各周回が「1波」に相当する）:**

Let `ACTIVE_REPOS` = `AFFECTED_REPOS` のうち、上表の判定または Step A-Seed の `init` により
state が `in-progress` になった repo の集合（`complete` の repo と、「### 判定エンジンの照合」で外した repo
〔`ENGINE_BLOCKED_REPOS`〕は含めない）。

Repeat while `ACTIVE_REPOS` is not empty:

**a. search の実行（repo ごと）**

For each `{repo}` in `ACTIVE_REPOS`, run via Bash:
```
specout_bfs.py search --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json \
  --hits-dir {CR_PATH}/04_specout/{repo}/work/waves/ --chunk-size {SPECOUT_CLASSIFY_CHUNK_SIZE}
```
（`--hits-dir` はスクリプトが state の `current_wave` から `wave-{N}-hits.json` を組み立てるため、
呼び出し側が波番号を search 実行**前**に知る必要はない。波番号は本コマンドの stdout の `"wave"` キーから取得し、
以降の step b〜d の出力パス組み立てに使う）

- `search` が exit 6 の場合（シード要約の取り込みが済んでいない）: 当該 `{repo}` に「### シード要約の取り込み」を
  適用し、成功したら同じ `search` をもう一度実行する（2回目も exit 6 なら stderr を表示して当該 `{repo}` を
  `ACTIVE_REPOS` から外す）。取り込みの失敗（exit 5 を含む）と2回目の exit 6 で外した repo は `SEED_SUMMARY_FAILED_REPOS` に
  入れ、以降の step を行わない。
- 出力 JSON の `complete` が `true` の場合（波数上限に達し、打ち切り記録を残して自動完了した）: 当該 `{repo}` を
  `ACTIVE_REPOS` から外し、下記「波ループ終了時の検証」（件数一致検証と prelim-metrics）を当該 repo に対して実行する。
  per-repo progress table の更新は commit-wave で complete になった repo と同じ。
- `search` が exit 4 の場合（投入シンボルが0件）: 当該 `{repo}` を `ACTIVE_REPOS` から外し、次を人へ提示する
  （同じ波の他 repo は step b 以降を続行する）:
  > ⚠️ **{repo} の探索シードが0件のため、波紋調査を開始できません。**
  > {`{CR_PATH}/04_specout/{repo}/discovery-log.md` の `## 投入シンボルの由来` テーブルの転記（「シンボル不明」行を含む）}
  >
  > CRS から具体的な識別子を特定できませんでした。次のいずれかで探索の起点を指定してください:
  > {`REPOS` が1エントリ（シングルリポジトリ）の場合のみ}
  > - `/xddp-04-specout {CR} --re-discover {識別子またはファイルパス…}`（既存の探索状態に投入して再開します）
  > {常に}
  > - `{CR_PATH}/04_specout/{repo}/work/bfs-state.json`・`work/bfs-state.md`・`work/waves/`・`{CR_PATH}/04_specout/{repo}/discovery-log.md`・
  >   `{CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md` を退避・削除したうえで、`/xddp-04-specout {CR}` を再実行する（下調べ資料〔下調べが完了した repo のみ〕と候補表は残り、シード確認〔Step A-Seed〕から再開します。
  >   候補表 `work/seed-candidates.md` で採否を見直すか、`/xddp-04-specout {CR} {識別子またはファイルパス…}` で起点を追加してください）
- `search` がその他の exit 非0 の場合（frontier 空・バックエンド不整合等）: stderr を表示したうえで
  当該 `{repo}` のみを `ACTIVE_REPOS` から外し、同じ波の他 repo は step b 以降を続行する
  （波ループ全体を止めると他 repo が巻き添えで停止する。当該波は未コミットで state は前波の確定状態の
  ままのため、原因を除去すればそのまま再開して安全である）。波ループ終了後に失敗 repo の一覧と stderr を人へ提示する。
- 成功した repo について、stdout の `hits_file`、`slice_chunk`（**スライス用チャンク** `wave-{N}-hits-chunk-S.json`。
  常に1件。C / C++ / Python のヒットを LLM を使わずに判定する）、`chunks`（**LLM 用チャンク** `wave-{N}-hits-chunk-{K}.json` の
  一覧。関数の範囲を決定的に取れない言語のヒット。0件可）を保持する。
  **`HITS_CHUNKS[{repo}]`** = [`slice_chunk`] + `chunks`（この順。step c の `--hits-chunks` の供給元）、
  **`LLM_CHUNKS[{repo}]`** = `chunks`（step b-1 で classifier に渡す。スライス用チャンクを含まない）とする。
  （step c の `--chunks` に渡す classification 側のファイル群＝ `CLASS_CHUNKS[{repo}]` とは別物であり、混同すると
  classification が1件も読まれない）

**a-seed. 追加投入シードの人への提示（非ブロッキング）**

step a の stdout の `"wave"` が `1` 以上で、次のいずれかを満たす repo について、**step b へ進む前に**
以下を人へ提示する（`--re-discover` で人が投入したシンボルに関する警告である。Wave 0 のシードはシード確認〔Step A-Seed〕で提示済み）。
提示は通知のみで承認を待たない。
- `zero_hit_symbols` または `zero_after_filter_symbols` が非空（投入したシンボルが当該波でヒットしなかった）
- `noisy_seed_symbols` が非空（投入したシンボルが多数のファイルにヒットした）
- `budget_truncated_seed_symbols` が非空（投入したシンボルが1波の予算を超えたため探索しなかった）

参照するデータの取得元:
- 未ヒット一覧: step a の stdout の `zero_hit_symbols` / `zero_after_filter_symbols`
- ヒット過多一覧: step a の stdout の `noisy_seed_symbols`（各要素は `symbol` と `file_count`）と `all_seeds_noisy`
- 予算で打ち切った一覧: step a の stdout の `budget_truncated_seed_symbols`（各要素は `symbol` と `hits`）と `all_seeds_budget_truncated`
- 由来の内訳: `{CR_PATH}/04_specout/{repo}/discovery-log.md` を Read し
  `## 投入シンボルの由来` セクションのテーブルと、テーブル直後にある `> ⚠️` で始まる行
  （`_update_origin_entry_points` が捨てたトークンを記録した警告行。無ければ省略）を転記する
  （当該セクションが無い場合は転記を省略し、以降の警告のみを提示する）

> 📋 **{repo} の探索シード（Wave {wave}）**
> {`## 投入シンボルの由来` テーブルの転記（テーブル直後の `> ⚠️` 行があればそれも含める）}
>
> {`zero_hit_symbols` が非空の場合のみ}
> ⚠️ **母体コードに1件もヒットしなかった投入シンボル:** `{zero_hit_symbols をカンマ区切り}`
> 　 識別子の誤字・旧名称である可能性があります。
> {`zero_after_filter_symbols` が非空の場合のみ}
> ⚠️ **生ヒットはあったがフィルタで全件除外された投入シンボル:** `{zero_after_filter_symbols をカンマ区切り}`
> 　 `SPECOUT_HIT_FILTER` の設定と discovery-log.md の「## フィルタ除外一覧」を確認してください。
> {`noisy_seed_symbols` が非空の場合のみ}
> ⚠️ **多数のファイルにヒットした投入シンボル（一般語の疑い）:** `{symbol}`（{file_count} ファイル）, …
> 　 識別子ではない一般語がシードになっている可能性があります。LLM 分類に回るヒットは代表行だけが分類されます。
> {`budget_truncated_seed_symbols` が非空の場合のみ}
> ⚠️ **1波の予算を超えたため探索しなかった投入シンボル:** `{symbol}`（{hits} ヒット）, …
> 　 `SPECOUT_WAVE_HIT_BUDGET` を上げて状態ファイルから作り直すか、より具体的なシンボルを `--re-discover` で投入してください。
> {`all_seeds_noisy` または `all_seeds_budget_truncated` が `true` の場合のみ}
> 　 **投入シンボルの全件が該当します。この探索は変更対象を特定できていない可能性が高いため、中断を推奨します。**
> 　 中断した場合は、次の手順で最初からやり直してください（`--re-discover` による追加投入では、一般語のシードで確定したファイルが残ります）:
> 　 - `{CR_PATH}/04_specout/{repo}/work/bfs-state.json`・`work/bfs-state.md`・`work/waves/`・`{CR_PATH}/04_specout/{repo}/discovery-log.md`・
> 　   `{CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md` を退避・削除したうえで、`/xddp-04-specout {CR}` を再実行する（下調べ資料〔下調べが完了した repo のみ〕と候補表は残り、シード確認〔Step A-Seed〕から再開します。
> 　   候補表 `work/seed-candidates.md` で採否を見直すか、`/xddp-04-specout {CR} {識別子またはファイルパス…}` で起点を追加してください）
>
> {`all_seeds_noisy` と `all_seeds_budget_truncated` がいずれも `false` の場合のみ}
> このまま探索を継続します。シードに誤りがある場合はここで中断し、
> `{CR_PATH}/04_specout/{repo}/discovery-log.md` を確認のうえ
> `/xddp-04-specout {CR} --re-discover {正しいシンボル}` で追加投入してください
> （未ヒット一覧は波ごとに別セクションで上書き更新されるため、再 search で重複しません）。

`wave` = 0 の場合、および `wave` ≥ 1 でいずれの一覧も空の場合は提示しない。

**b. 判定（全 ACTIVE_REPOS）**

**b-0. スライス判定・規則判定（repo ごと。LLM を使わない）**

For each `{repo}` in `ACTIVE_REPOS`, run via Bash:
  `"{SLICE_PY}" ~/.claude/skills/xddp-04-specout/scripts/specout_slice.py classify --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --hits {slice_chunk（step a）} --out {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-chunk-S-class.json`
（判定エンジンは state の `slice_engine` で決まる。ヒット0件のスライス用チャンクでも実行し、空の classification を書く）
- exit 5（判定エンジンが使えない）: 「### 判定エンジンの照合」の提示文（選択肢1〜3）を示し、当該 `{repo}` を `ACTIVE_REPOS` から外す。
- その他の exit 非0: stderr を表示し、当該 `{repo}` を `ACTIVE_REPOS` から外す（step c の失敗と同じ扱い）。
- 成功: **`CLASS_CHUNKS[{repo}]`** の先頭に `{CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-chunk-S-class.json` を置く。

**b-1. classifier の並列起動（全 ACTIVE_REPOS の LLM 用チャンクを合算）**

対象は **`LLM_CHUNKS[{repo}]`（スライス用チャンクを含まない）だけ**である（スライス用チャンクを classifier に渡すと、
`OUT_FILE` が b-0 の結果を上書きし、C / C++ / Python のヒットが黙って LLM 分類される）。全 repo の `LLM_CHUNKS` が空なら
classifier を起動せず、step c へ進む。

`LLM_CHUNKS` を repo 単位で連続するように（`ACTIVE_REPOS` の順に、各 repo の chunk-0 から昇順に）
合算した列を作り、その先頭から `{SPECOUT_CLASSIFY_PARALLEL}` 件ずつバッチへ詰める
（ラウンドロビン的に repo を交互に詰めてはならない。実効並列度の事後判定式が「repo のチャンクが
バッチ列上で連続する」ことを前提に成立するため）。

**プロンプトキャッシュ有効化のための設計要件（必須）:** 各 classifier の起動プロンプトは、
チャンク固有情報（`CHUNK_FILE`・`OUT_FILE`・`chunk_id`）を末尾に置き、先頭側（分類ルール・判定手順に
関する指示文）を全チャンクでバイト単位に同一に保つこと。兄弟サブエージェント間で
プロンプトキャッシュが共有されるのはプレフィクスがバイト同一の場合のみであり、チャンク固有情報が
先頭側に混ざるとキャッシュが個体ごとに分離し、固定ブートストラップがチャンク数だけ複製される。
**波の最初のバッチは、チャンク0を単独で起動してキャッシュ書き込みを完了させてから残りのチャンクを
並列起動する**（またはバッチ内の起動タイミングを2〜3秒ずらす。コールドスタート時の競合窓対策）。

各 classifier には `CHUNK_FILE` として当該チャンクの `LLM_CHUNKS` エントリを、`OUT_FILE` として
`{CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-chunk-{K}-class.json`（`{K}` は `CHUNK_FILE` と同一）を渡す:

Use the **Agent tool** with `subagent_type=xddp-specout-classifier-agent` and pass:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CHUNK_FILE: {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-hits-chunk-{K}.json
OUT_FILE: {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-chunk-{K}-class.json
EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}
INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS}
```

classifier が書いた `OUT_FILE` を、`CLASS_CHUNKS[{repo}]` の先頭（b-0 のスライス用）の後に `K` の昇順で加える（step c で使う）。
各バッチの起動直前・完了直後に Bash `date +%s` を取り、
`{CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-batches.json` へ以下のスキーマで記録する（repo ごとに書く。
`{N}` は当該 repo の波番号。実効並列度の事後監査用。消費者は人と確認項目のみで、これを読むスクリプトはない）:
```json
[{"batch_index": 0, "chunk_files": ["…-chunk-0-class.json", "…"], "started_at": 1786000000, "ended_at": 1786000042}]
```
このファイルから求めた「当該 repo のチャンクが1件以上含まれていたバッチの数」を、
下記 step d の `--batch-count` に渡す（classifier を起動しなかった repo では `0`）。

**c. merge_classification.py の実行（repo ごと）**

For each `{repo}` in `ACTIVE_REPOS`, run via Bash（パスは step a の `hits_file` から導出する）:
```
merge_classification.py --hits {hits_file（step a）} \
  --hits-chunks {HITS_CHUNKS[{repo}]} --chunks {CLASS_CHUNKS[{repo}]} \
  --out {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-class.json \
  --unsupported-out {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-unsupported.json
```
（`--hits-chunks` には **`HITS_CHUNKS[{repo}]`**（スライス用チャンク＋LLM 用チャンク）を、`--chunks` には
**`CLASS_CHUNKS[{repo}]`**（b-0 の結果＋classifier が書いた `OUT_FILE`）を、同じ順（先頭がスライス用チャンク、続いて
LLM 用チャンクの `K` の昇順）で渡す。`merge_classification.py` は位置で対応させる。
取り違えるとフラグ名が一致するため機械検査では検出されない — 変数名を厳密に区別すること）

- stdout の `min_chunk_mtime` を保持する（非 `null` なら step d へ `--chunk-mtime-min` として渡す）。
- exit 非0（line_id の欠落・重複・未知値・チャンク単位の不一致・欠落チャンク）の場合: stderr を
  表示したうえで当該 `{repo}` のみを `ACTIVE_REPOS` から**このイテレーションでは**外し、
  同じ波の他 repo は step d まで完了させる。失敗 repo の state は `wave_write_complete=false` の
  まま残るため、`recovery-procedures.md`「## Wave 途中失敗からの再開（経路統一）」の手順2
  （欠落・stale チャンクのみを再投入する）にそのまま接続できる。波ループ終了後に失敗 repo の一覧と
  stderr を人へ提示する。

**d. commit-wave の実行（repo ごと）**

For each `{repo}` in `ACTIVE_REPOS`（step c を通過したもの）, run via Bash:
```
specout_bfs.py commit-wave --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json \
  --hits {hits_file（step a）} --classification {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-class.json \
  --unsupported-patterns {CR_PATH}/04_specout/{repo}/work/waves/wave-{N}-unsupported.json \
  --chunk-count {当該 repo の LLM 用チャンクの数（0 可）} --batch-count {step b-1 で求めた実バッチ数（0 可）} \
  --parallelism {SPECOUT_CLASSIFY_PARALLEL} \
  [--chunk-mtime-min {step c で得た値。非 null の場合のみ渡す}] --today {TODAY}
```
- `commit-wave` は per-wave metrics を `{CR_PATH}/04_specout/{repo}/work/metrics.jsonl` へ1行追記する（`--path` と同じディレクトリ）。
  打ち切り記録（1波の予算）・要約の拡大による再訪・シードの直接参照ファイルの記録もここで行う。
- stdout の `state` が `complete` になった repo を `ACTIVE_REPOS` から外し、下記「波ループ終了時の検証」を
  当該 repo に対して実行する（`commit-wave` 成功時は `wave_write_complete` が常に `true` になるため、
  status の再確認は不要）。
- exit 非0（fail-loud・スキーマ検証エラー等）の場合: stderr を表示したうえで当該 `{repo}` のみを
  `ACTIVE_REPOS` から外す。失敗 repo の state は `wave_write_complete=false` のまま残るため、
  step c の失敗と同じ再開手順に接続できる。波ループ終了後に失敗 repo の一覧と stderr を人へ提示する。

**e.** `ACTIVE_REPOS` が空でなければ a. に戻る（波番号は repo ごとに独立して進む）。

**波ループ終了時の検証（repo が `complete` になるたび）:**
上記「件数一致検証（独立回帰チェック）」と同じ手順（`specout_verify_counts.py --wave all --strict`
と `VERIFY_EXIT` による分岐）を、`complete` になった当該 repo に対して実行する。

続けて、`{CR_PATH}/04_specout/{repo}/work/seed-candidates.md` が存在する repo に限り、下調べとシード確認の計測を記録する
（ベストエフォート。失敗しても続行し、stderr を表示する）。Run via Bash:
```
PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py prelim-metrics \
  --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --seed-candidates {CR_PATH}/04_specout/{repo}/work/seed-candidates.md \
  [--ledger {CR_PATH}/04_specout/{repo}/work/documented-files.md] --seed-gate {SPECOUT_SEED_GATE}
```
`--ledger` は台帳ファイルが存在する場合のみ渡す。同じ repo で2回目以降に `complete` になった場合
（`--re-discover`・Step A-cross-propagate の後）は、スクリプトが追記をスキップする（stdout の `skipped`）。

**波ループ終了後（全 repo が `complete` または失敗で `ACTIVE_REPOS` から外れた場合）:**
`complete` になった repo について、per-repo progress table を更新: `| {repo} | ✅ 完了 | ⏳ 未着手 | - |`

波ループ中に失敗した repo は、次の2つに分けて一覧と直近の stderr を人へ提示する:
1. `SEED_SUMMARY_FAILED_REPOS`（step a のシード要約の取り込みの失敗・exit 5・2回目の exit 6 で外れた repo）: `search` が
   state を変える前に止まっている（`wave_write_complete` は `true` のまま）ため、「## Wave 途中失敗からの再開」は適用しない。
   exit 5 なら「### 判定エンジンの照合」の提示文（選択肢1〜3）を示し、原因を直して `/xddp-04-specout {CR}` を再実行するよう
   案内する（再実行すると `search` が exit 6 を返し、取り込みからやり直す）。
2. それ以外（step a のその他の失敗〔`search` exit 4＝投入シンボル0件で外れた repo を除く〕、step b-0 の `classify` の失敗
   〔exit 5 を含む。`search` の後なので `wave_write_complete` は `false`〕、step c・d の失敗）: `recovery-procedures.md`
   「## Wave 途中失敗からの再開（経路統一）」を適用してから `/xddp-04-specout {CR}` を再実行するよう案内する。
   b-0 の exit 5 なら、先に「### 判定エンジンの照合」の選択肢1（tree-sitter を使える Python を指定する）で環境を直すことを加える。
`SEED_FAILED_REPOS`（Step A-Seed 手順0 で外した repo。候補表が作られなかった repo）があれば、その一覧と
discovery-setup の返答を提示し、`/xddp-04-specout {CR}` を再実行するよう案内する（状態ファイルが無いため、再実行で
Step A-Prelim から始まる。下調べ資料は再利用される）。この場合は Step A-Document 以降へ進まずに停止する。
`ENGINE_BLOCKED_REPOS`（Step A の入口の「### 判定エンジンの照合」で外した repo だけ。Step A-cross-propagate の照合で見送った
repo は入らない）が空でなければ、その一覧と「### 判定エンジンの照合」の選択肢1・3の案内を再掲し、上記の per-repo progress table の
更新を行ったうえで "## Progress Update" を CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中,
DETAIL_STEP: `Step A: 判定エンジンが使えないため停止（{ENGINE_BLOCKED_REPOS をカンマ区切り}）` で適用し、Step A-Document 以降へ
進まずに停止する（`complete` になった他の repo の探索状態は保持され、再実行でそれらの波ループは再実行されない。外した repo は、
選択肢1で再実行すると波ループの途中から続く）。
`search` exit 4 で外れた repo が1つでもある場合は、上記の per-repo progress table の更新を行ったうえで、
"## Progress Update" を CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中,
DETAIL_STEP: `Step A: 投入シンボル0件のため停止（{exit 4 の repo をカンマ区切り}）` で適用し、
step a で提示した案内を再掲して、Step A-Document 以降へ進まずに停止する
（シードのない repo の SPO は作れないため。退避・削除による再実行の場合、`complete` になった他の repo の
探索状態は保持され、波ループは再実行されない）。

## Step A-Document: Per-repo Specout — Document Phase

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A-Document: Documentation 中`

Discovery が全リポジトリで "complete" になった後、各リポジトリを**順次**ドキュメント化する。
資料の確定は、スクリプトが機能（モジュール）単位の材料を作り、document agent が**モジュールごとに**材料だけを読んで
資料を書き、スクリプトが組み立てて検証する流れで進める。

For each `{repo}` in `AFFECTED_REPOS`:

Let `OUT` = `{CR_PATH}/04_specout/{repo}`、`WORK` = `{OUT}/work`、`DIGEST` = `{WORK}/digest`、
`PY` = `command -v python3 || command -v python` の結果、`BFS` = `~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py`。
以降の Bash 呼び出しで、スクリプトが見つからない場合は setup.sh の実行を案内して停止し、exit 非0（下記で別の扱いを
定めた終了コードを除く）の場合は stderr を表示して停止する。再開時は `recovery-procedures.md`
「## Document Phase Recovery」を適用する。

1. **文書化対象とモジュールの割り当て（スクリプト）** — Run via Bash:
   `"$PY" "$BFS" doc-targets --path {WORK}/bfs-state.json --ledger {WORK}/documented-files.md --memo {WORK}/observation-memo.md --module-assignments {WORK}/module-assignments.json --auto-assign`
   `--auto-assign` は、どのモジュールにも属さないファイルの親ディレクトリを新しいモジュールとして
   `{WORK}/module-assignments.json` に追記する。exit 1 でモジュール名の衝突が報告された場合は、stderr の内容と
   `{WORK}/module-assignments.json` の修正を人へ案内して停止する（修正後に `/xddp-04-specout {CR}` を再実行する）。
   exit 5（`module-assignments.json` の組の不正）と、台帳・観察メモの書式不正による exit 1 は、
   stderr が示す該当ファイルの該当行を人が直して `/xddp-04-specout {CR}` を再実行するよう案内して停止する
   （`work/prelim-index.md`・`work/seed-candidates.md` と状態ファイル類を退避・削除して下調べからやり直す場合は、
   候補表の編集内容も失われることを併せて伝える）。

2. **配置の確定（スクリプト）** — Run via Bash:
   `"$PY" "$BFS" assemble-spo --path {WORK}/bfs-state.json --output-dir {OUT} --digest-dir {DIGEST} --summary-template ~/.claude/skills/xddp-04-specout/templates/04_specout-summary-template.md --module-template ~/.claude/skills/xddp-04-specout/templates/04_specout-module-template.md --max-files-per-module {SPECOUT_MAX_FILES_PER_MODULE} --detail-level {SPO_DETAIL_LEVEL} --cr {CR} --today {TODAY} --layout-only`
   （`{SPO_DETAIL_LEVEL}` は `EFFECTIVE_SPO_DETAIL_LEVEL` を `--detail-level` の値へ写したもの: `full` → `standard`、`brief` → `brief`）
   stdout の `modules[]`（各要素の `module`・`mode`・`output_files`・`existing_doc`）を `MODULE_OUTPUTS`（モジュール名 → `output_files`）として保持する。

3. **材料作り（スクリプト）** —
   （repo が "cross" 以外かつ `{OUT}/discovery-log.md` が存在する場合のみ・ベストエフォート。失敗しても工程を止めない。
   失敗時は `FUNCMAP_COUNTS_FILE` = 空）Run via Bash:
   `"$PY" "$BFS" funcmap-counts --discovery-log {OUT}/discovery-log.md --out {WORK}/SPO-{CR}-funcmap-counts.md`
   → 成功時は `FUNCMAP_COUNTS_FILE` = `{WORK}/SPO-{CR}-funcmap-counts.md`。
   続けて Run via Bash:
   `"$PY" "$BFS" doc-digest --path {WORK}/bfs-state.json --discovery-log {OUT}/discovery-log.md --ledger {WORK}/documented-files.md --module-assignments {WORK}/module-assignments.json --out-dir {DIGEST} --line-budget {SPECOUT_DOC_LINE_BUDGET} --max-modules {SPECOUT_DOC_MAX_MODULES}`
   stdout の `index_file`・`module_files`・`direct_modules`・`skipped_modules` を保持する
   （`direct_modules` は Step A2 が使う。この変数は repo ごとに `{DIGEST}/index.md` から Step A2 で再取得できる）。
   `SPECOUT_MAX_AFFECTED_FILES` 超過の警告: `{DIGEST}/index.md` の確定ファイル数の合計が `SPECOUT_MAX_AFFECTED_FILES` を超える場合、
   人へ「⚠️ {repo} の確定ファイル数（{n}）が SPECOUT_MAX_AFFECTED_FILES（{値}）を超えています。CR の分割を検討してください」と伝える
   （調査・資料化は続ける）。

4. **モジュールごとの資料（LLM・並列）** — `module_files` の各モジュールについて、**Agent tool** で
   `subagent_type=xddp-specout-document-agent` を `DOC_MODE: module` で起動する。同時起動は `SPECOUT_DOC_PARALLEL` 件まで
   （超過分はバッチに分けて順次起動する。同じ repo のモジュール分を1つのメッセージにまとめて並列起動する）。渡す入力:
   ```
   DOC_MODE: module
   CR_NUMBER: {CR}
   REPO_NAME: {repo}
   REPO_PATH: {REPOS_MAP[repo]}
   CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
   MODULE_NAME: {モジュール名}
   DIGEST_FILE: {DIGEST}/modules/{モジュール名}.md
   OUTPUT_FILE: {MODULE_OUTPUTS[モジュール名]}
   EXISTING_MODULE_DOC: {OUTPUT_FILE が既に存在すれば OUTPUT_FILE と同じパス（下調べ・前回の資料の確定が書いたもの）。無ければ空}
   MODULE_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-module-template.md
   OUTPUT_DIR: {OUT}/
   TODAY: {TODAY}
   DOCS: {DOCS}
   SPECOUT_DIAGRAM_LEVEL: {EFFECTIVE_DIAGRAM_LEVEL}
   SPECOUT_SEQUENCE_LEVELS: {EFFECTIVE_SEQUENCE_LEVELS}
   SPO_DETAIL_LEVEL: {EFFECTIVE_SPO_DETAIL_LEVEL}
   LEDGER_FILE: {WORK}/documented-files.md
   LEDGER_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-documented-files-template.md
   ```
   各 agent の返答は1行（`OK: {書いたファイル}`）。`OK:` で始まらない返答、または失敗したモジュールが
   あれば、そのモジュール名と原因を人へ提示して停止する（再開は `recovery-procedures.md`「## Document Phase Recovery」）。

5. **組み立て（スクリプト）** — Run via Bash: 手順2と同じ引数から `--layout-only` を外した `assemble-spo`。
   統合パスならモジュール資料を `SPO-{CR}.md` の §2.A… に差し込み、台帳・累積観察メモへモジュール別の一時ファイルをマージし、
   SPO サマリーのスクリプトが書く欄（§1 調査概要・§1.x 調査の打ち切り・§5.0 の機能一覧〔「確認の観点」以外〕・§5.1・§5.2・
   §5.5 のテストファイルの候補・§8・§9 への転記）を書く。
   stdout の `coverage_gaps`・`unexpected_rows`・`dropped_rows` のいずれかが空でなければ、人へ伝える（処理は止めない）。
   空でない報告の行だけを出す:
   > ℹ️ {repo} の資料の確定で、台帳の取り込みに次の報告があります。影響範囲の把握に足りていれば、このまま進めてかまいません。
   > - `coverage_gaps`（{モジュール名: 件数, …}）: 材料を作ったのに台帳に行が無いファイルがあります。`/xddp-04-specout {CR}` を再実行すると、再び文書化の対象になります。
   > - `unexpected_rows`（{モジュール名: 件数, …}）: 材料に無いファイルの行が台帳に取り込まれました。台帳に行があるため、再実行しても文書化の対象には戻りません。必要なら `work/documented-files.md` から該当行を削除してください。
   > - `dropped_rows`（{モジュール名: 件数, …}）: 列数が合わない台帳の行を捨てました。捨てた行のファイルは `coverage_gaps` にも出ます（再実行で再び文書化の対象になります）。
   > 再実行の手順は `recovery-procedures.md`「## Document Phase Recovery」の「手順5（`assemble-spo`）が取り込みの報告を出した場合」の項にあります。

6. **サマリーと funcmap（LLM・1回）** — **Agent tool** で `subagent_type=xddp-specout-document-agent` を
   `DOC_MODE: summary` で起動する。渡す入力:
   ```
   DOC_MODE: summary
   CR_NUMBER: {CR}
   REPO_NAME: {repo}
   CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
   INDEX_FILE: {DIGEST}/index.md
   MODULE_DOC_FILES: {全モジュール資料の一覧。統合パスは SPO-{CR}.md の §2.A…、分割パスは modules/ 配下}
   FUNCMAP_COUNTS_FILE: {FUNCMAP_COUNTS_FILE}
   SUMMARY_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-summary-template.md
   FUNCMAP_TEMPLATE: ~/.claude/skills/xddp-04-specout/templates/04_specout-funcmap-template.md
   SUMMARY_FILE: {OUT}/SPO-{CR}.md
   OUTPUT_DIR: {OUT}/
   TODAY: {TODAY}
   LATEST_SPECS_DIR: {XDDP_DIR}/latest-specs/{repo}/
   BASELINE_SPECS_DIR: {DOCS}/{repo}/specs/
   CROSS_SPECS_DIR: {DOCS}/cross/specs/
   DOCS: {DOCS}
   ENTRY_POINTS: {ENTRY_POINTS_BY_REPO[repo]}
   SPECOUT_DIAGRAM_LEVEL: {EFFECTIVE_DIAGRAM_LEVEL}
   SPECOUT_SEQUENCE_LEVELS: {EFFECTIVE_SEQUENCE_LEVELS}
   SPO_DETAIL_LEVEL: {EFFECTIVE_SPO_DETAIL_LEVEL}
   ```
   Wait for completion. 返答は1行（`OK: SPO サマリー・funcmap を書いた`）。返答が `OK:` で始まらない、または agent が失敗した場合は、
   原因を人へ提示して停止する（再開は `recovery-procedures.md`「## Document Phase Recovery」の手順6 の項）。lint はその後に実行しない
   （前回の Step A-Document の funcmap が残っていると lint の F0 は出ないため、返答で先に止める）。`OK:` で始まれば続けて Run via Bash:
   `"$PY" ~/.claude/skills/xddp-common/scripts/artifact_lint.py --file {OUT}/SPO-{CR}.md --doc-type SPO`
   → 出力の `spo.issues` のうち `check` が `F3` の件数（`確認要` を含む funcmap の行の数）を `k` とする。
   `check` が `F0`（funcmap が無い・表が見つからない）の項目があれば、agent が funcmap を書き終えていないため、
   その内容を人へ提示して停止する（再開は `recovery-procedures.md`「## Document Phase Recovery」の手順6 の項）。
   lint が実行時エラー（exit 非0）になった場合は stderr を表示して停止する。
   lint の F3・F0 以外の項目は、ここでは見ない（工程4a の AI レビューで扱う）。
   - `確認要` がある場合（`k` > 0）、スキルは人に対して:
     > ⚠️ {repo} の funcmap 生成で `確認要`（直接呼び出し元数の要人的確認）が検出されました。
     > `{OUT}/discovery-log.md` の当該メッセージと `{FUNCMAP_COUNTS_FILE}` の
     > 「スキップされた行」テーブルを確認し、各識別子の直接呼び出し元数を判断のうえ、
     > `{n}(確認済)`（例: `3(確認済)`）の表記で `{OUT}/SPO-{CR}-funcmap.md` の
     > 該当セルを直接編集してください。
     と伝え、承認（編集完了の確認）されるまで次工程（工程4b CRS更新）へは進まない。

7. **検証スイープ（スクリプト）** — Run via Bash:
   `"$PY" "$BFS" verify-sweep --path {WORK}/bfs-state.json --discovery-log {OUT}/discovery-log.md --ledger {WORK}/documented-files.md --digest-dir {DIGEST}`
   - exit 0: 未記録ヒットなし。次へ進む。
   - **exit 7（未記録ヒットあり）**: 人に対して:
     > ⚠️ {repo} の検証スイープで未記録ヒットが発見されました。
     > `{OUT}/discovery-log.md` の「検証スイープ結果」を確認し、
     > 追加ドキュメント化するか、影響軽微として根拠を記録して承認してください。
     と伝え、承認されるまで待機する。
   - exit 3 は `verify-sweep` では返らない（件数不一致は Step A の件数一致検証が `recovery-procedures.md`
     「## Count Mismatch Handling」で扱う別の分岐）。

per-repo progress table を更新: `| {repo} | ✅ 完了 | ✅ 完了 | {TODAY} |`

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

Let `TARGETS_FILE` = `{CR_PATH}/04_specout/cross/work/cross-propagation-targets.json`.
`TARGETS_FILE` が存在しない、または中身が空配列 `[]` の場合: 本ステップ全体をスキップし、progress.md の
DETAIL_STEP に「Step A-cross-propagate: 対象なし（スキップ）」を記録して Step A2 へ進む。

Read `TARGETS_FILE`（JSON配列。各要素 `{"symbol", "providing_repo", "consuming_repo"}`）。
以下のいずれかに該当する要素は無視し、人へ警告する（「⚠️ cross-propagation-targets.json に不正な
エントリがあります: {entry}」）:
- `consuming_repo` が `AFFECTED_REPOS` に含まれない
- `consuming_repo` と `providing_repo` が同一

**冪等性ガード:**
Let `LOG_FILE` = `{CR_PATH}/04_specout/cross/work/cross-propagation-log.json`（存在しない場合は空配列
`[]` として扱う。`LOG_FILE` は本ステップだけが書き込む永続履歴であり（要素の追加と `status` の更新のみを
行い、要素を削除しない）、Step A-cross からは書き込まない。本ステップで `LOG_FILE` を「書き戻す」ときは、
読み取った JSON 配列全体に追加・更新を反映した配列でファイル全体を上書きする）。
Read `LOG_FILE`（JSON配列。各要素 `{"repo", "symbol", "providing_repo", "status"}`。`repo` は消費リポジトリ。
`status` は次のいずれか: `propagated`＝追加探索を投入済み／`deferred`＝追加探索が未投入（消費 repo が
`complete` でなかったため見送った、または投入前に停止した）／`chain-excluded`＝連鎖ガードで除外し人へ通知済み）。
有効な要素のうち、`(consuming_repo, symbol, providing_repo)` の組が `LOG_FILE` に `status` = `propagated`
または `chain-excluded` で記録済みのものを除外する（`deferred` の組は除外せず、再試行の対象とする）。

**連鎖ガード（CR 単位の1ラウンド制限）:**
Let `PROPAGATED_CONSUMERS` = `LOG_FILE` のうち `status` = `propagated` の要素の `repo` の集合（過去の実行で
追加探索の対象になった消費リポジトリ）。冪等性ガード通過後の要素のうち、`providing_repo` が
`PROPAGATED_CONSUMERS` に含まれ、かつ同じ組が `LOG_FILE` に `status` = `deferred` で記録されていないものは、
追加探索の結果として新たに識別された連鎖（B→C）の候補とみなして除外する（`deferred` の組は、
提供元が伝播対象になる前の実行で既に識別されていた正当な1段目であるため除外しない）。
除外した要素は `{"repo": consuming_repo, "symbol", "providing_repo", "status": "chain-excluded"}` として
`LOG_FILE` へ追加して書き戻し（次回以降は冪等性ガードで除外され、同じ通知を繰り返さない）、
除外した要素が1件以上ある場合、人へ通知する:
> ℹ️ 以下の共有インタフェースは、過去に追加探索を実施したリポジトリが提供元のため、連鎖的な追跡を
> 行わない設計により自動の追加探索対象から除外しました:
> {除外要素ごとに "- {symbol}（{providing_repo} → {consuming_repo}）"}
> 追跡が必要な場合は `/xddp-04-specout {CR} --re-discover {symbol}` を人が実行してください。

残った要素を `consuming_repo` でグルーピングし、repo ごとに `symbol` を重複排除する。
Let `PROPAGATION_MAP` = `{repo: [symbol, ...], ...}`（symbol リストが空の repo はキーごと除去する）。
`PROPAGATION_MAP` が空の場合: 本ステップ全体をスキップし、progress.md の DETAIL_STEP に
「Step A-cross-propagate: 新規対象なし」を記録して Step A2 へ進む。

**事前登録:** 下記ループへ入る**前に**、`PROPAGATION_MAP` に残った各組を
`{"repo": consuming_repo, "symbol", "providing_repo", "status": "deferred"}` として `LOG_FILE` へ追加して
書き戻す（同じ組が既に `deferred` で記録済みなら追加しない）。これにより、ループのどの時点で停止しても
未投入の組は `deferred` として残り、次回実行時に冪等性ガード・連鎖ガードのいずれでも除外されず再試行される。

For each `{repo}` in `PROPAGATION_MAP` のキー（repo 名の昇順で処理する）:
  Run via Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py status --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --brief`
  If it errors: display stderr and stop（当該 repo 以降の組は事前登録済みの `deferred` のまま残り、
  次回実行時に再試行される）。
  - 出力 JSON の `state` が `complete` でない場合: 当該 repo をスキップし、人へ警告する
    （「⚠️ {repo} の bfs-state.json が complete 状態ではないため、クロスリポジトリ伝播探索を
    スキップしました。」）。当該 repo の各対象は事前登録済みの `deferred` のまま残し、次回実行時に
    再試行される。
  - `complete` の場合: Re-discover Processing を適用する**直前**に、当該 repo に Step A の「### 判定エンジンの照合」を
    適用する（適用する場所2）。`blocked`（選択肢1・3、または回答なし）の場合は投入せず、人へ警告する（「⚠️ {repo} は
    判定エンジン（tree-sitter）が使えないため、クロスリポジトリ伝播（{PROPAGATION_MAP[repo] のシンボル}）を見送りました。
    tree-sitter を使える Python を指定して再実行するか、規則判定に切り替えると投入されます。」）。当該 repo の各対象は
    事前登録済みの `deferred` のまま残し（`propagated` にしない）、次の repo へ進む（停止しない）。`ok`・`switched` の場合は
    続けて投入する:
    Read `~/.claude/skills/xddp-04-specout/recovery-procedures.md`,
    apply "## Re-discover Processing" with:
      CR_PATH: {CR_PATH}, repo: {repo}, ENTRY_POINTS: {PROPAGATION_MAP[repo] をカンマ区切りで展開},
      TODAY: {TODAY}, ORIGIN_LABEL: `クロスリポジトリ伝播（Step A-cross-propagate）による追加エントリポイント`
    同プロシージャの手順3（波ループの開始）は、下記の波ループで全対象 repo をまとめて実行するため、
    ここでは手順1・2のみを適用する。同プロシージャ手順1がエラーになった場合は、同プロシージャの規定
    （stderr を表示して停止）どおりスキル全体を停止する（当該 repo をスキップして次の repo へ進む
    扱いはしない。当該 repo 以降の組は事前登録済みの `deferred` のまま残り、次回実行時に再試行される）。
    手順1・2が成功したら、**次の repo へ進む前に**以下の2つを行う（repo ごとの投入時点を記録点とする
    ことで、以降の波ループ・Document の途中や後続 repo の `re-discover` 失敗で停止しても、再実行時に
    当該 repo へ `re-discover` を二重投入しない。残りは再実行時の通常フロー——Step A が `in-progress` の repo を
    状態テーブルどおり再開し、Step A-Document が全 repo を再ドキュメント化する——で完了する）:
    1. `LOG_FILE` を更新する: 当該 `repo` について、`PROPAGATION_MAP[repo]` の各 `symbol` に対応する
       事前登録済みの `deferred` 要素（同一 `(repo, symbol)` に複数の提供元がある場合はそのすべて）の
       `status` を `propagated` に置き換え、書き戻す。
    2. `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md` の末尾（Section 11 より後）に監査用ノートを
       追記する（Section 2〜11 は変更しない）。下記の見出しがまだ無い場合のみ見出しと注記を先に追記し、
       続けて当該 repo の1行を追記する（冪等性ガードにより記録済みの組は `PROPAGATION_MAP` に残らない
       ため、同じ repo・シンボルの行が重複追記されることはない）:
       ```
       ## 追加探索の実施記録（自動追記・Step A-cross-propagate）
       > 本節は Step A-cross-propagate が追記する監査記録であり、テンプレート外の節である。
       > SPO レビュー・修正の対象外とし、削除・改変しないこと。
       - {TODAY}: {repo} で追加探索を投入: {PROPAGATION_MAP[repo] のシンボル一覧（カンマ区切り）}
       ```

Let `PROPAGATED_REPOS` = 上記で `re-discover` が成功した repo の集合。空の場合は progress.md の
DETAIL_STEP に「Step A-cross-propagate: 対象 repo が complete 状態ではなくすべてスキップ」を記録して
Step A2 へ進む。

続いて `## Step A`「波ループ」を `ACTIVE_REPOS = PROPAGATED_REPOS` として再実行する（既存の波ループ定義
（step a〜e・波ループ終了時の検証・波ループ終了後の失敗 repo 提示）をそのまま適用する。新しいループ
実装は追加しない。波番号は各 repo の `bfs-state.json` の `current_wave` から repo ごとに独立して継続する）。
- `re-discover` は探索の起点の波を再開する波に置き直すため、追加したシンボルは `SPECOUT_MAX_WAVE_DEPTH` の波数まで
  調べられる。上限に達した repo は、波ループ a のとおり打ち切り記録を残して `complete` になる。判定エンジンが `slice` の
  repo では、波ループ a の `search` が exit 6 を返し、追加したシンボルのシード要約の取り込みから行う。
- 波ループの `complete` 時の進捗表更新（`| {repo} | ✅ 完了 | ⏳ 未着手 | - |`）で Document 列が一時的に
  「未着手」へ戻るのは許容する（下記の Document 再適用で `✅ 完了` に戻る）。

Let `DOC_REPOS` = `PROPAGATED_REPOS` のうち、波ループ終了時点で `bfs-state.json` の `state` が `complete` の
repo。`PROPAGATED_REPOS` のうち `DOC_REPOS` に含まれない repo（失敗）があれば、その一覧を人へ
提示し、原因の解消後に `/xddp-04-specout {CR}` を再実行するよう案内する（`LOG_FILE` 記録済みのため
再実行時に `re-discover` は再投入されず、通常フローで波ループ・Document が完了する）。

`DOC_REPOS` の各 `{repo}` について、`## Step A-Document` の **`For each {repo} in AFFECTED_REPOS:` ループ本体**
（手順1〜7: `doc-targets --auto-assign` → `assemble-spo --layout-only` → `funcmap-counts`・`doc-digest` →
モジュールごとの document agent → `assemble-spo` → サマリー・funcmap の document agent → `verify-sweep`〔未記録ヒット時の人承認待ち〕、
funcmap `確認要` 検出時の人承認待ち、規模超過警告の伝達、per-repo progress table 更新）を再適用する。
節冒頭の Progress Update は再適用しない。
手順6 の `ENTRY_POINTS` のみ `ENTRY_POINTS_BY_REPO[repo]` の代わりに `PROPAGATION_MAP[repo]`
（本ステップが投入した共有インタフェースのシンボル一覧）を渡す。他の入力は Step A-Document の構築規則をそのまま流用する。

**重要（1ラウンド制限）:** 本ステップは Step A-cross を再実行せず、自身を再帰的に再実行しない。
`/xddp-04-specout {CR}` の再実行で Step A-cross が改めて識別した連鎖候補は、上記「連鎖ガード」が除外する。
連鎖的な波及（A→B→C→…）を追跡したい場合は、人が `/xddp-04-specout {CR} --re-discover {symbol}` を
該当リポジトリに対して手動で実行すること。

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A-cross-propagate: 完了（対象 {len(DOC_REPOS)} リポジトリ）`

## Step A2: SPO Review Loop

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A2: SPOレビュー中`

Set `max_rounds` = `EFFECTIVE_REVIEW_MAX_ROUNDS_SPO`（Step 0.55 で解決済み。quick 時は `1`（ただし `REVIEW_MAX_ROUNDS.SPO` が明示的に `0` の場合は `0`）、full 時は Step 0.55 が `xddp.config.md` から読んだ `REVIEW_MAX_ROUNDS.SPO`（既定 3））。

For each `{repo}` in `AFFECTED_REPOS` (run review loops sequentially per repo):

（repo が "cross" 以外の場合のみ）レビュアーに渡す資料を決める（ラウンドループの外・repo ループ内で1回のみ）:
- `DIGEST_INDEX` = `{CR_PATH}/04_specout/{repo}/work/digest/index.md`（Step A-Document 手順3の `doc-digest` が作った材料の一覧）。
- `DIRECT_MODULE_DOCS` = `DIGEST_INDEX` の「直接影響」列が ● のモジュール（`doc-digest` の `direct_modules`）の資料だけ。
  分割パス（`{CR_PATH}/04_specout/{repo}/modules/` がある）なら `modules/{モジュール名}-spo.md`
  （サブディレクトリ分割したモジュールは `modules/{モジュール名}/` 配下の `.md` も）。
  統合パスならモジュール資料が `SPO-{CR}.md` の §2.A… に入っているため追加しない（TARGET_FILE を読めばよい）。
  他のモジュールの資料は渡さない（SPO §5.0 の機能一覧と Step A3 の人のレビューで扱う）。

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. Read `~/.claude/skills/xddp-common/procedures/invoke-reviewer.md`, apply "## Invoke Reviewer" with:
   DOCUMENT_TYPE: SPO, NEXT_DOCUMENT_TYPE: DSN, TARGET_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md,
   REFERENCE_FILES: [
     {CR_PATH}/01_requirements/ (all .md),
     {CR_PATH}/03_change-requirements/CRS-{CR}.md,
     （repo が "cross" 以外の場合のみ追加）{DIGEST_INDEX},
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
- {repo}: `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`
  - モジュール: `{CR_PATH}/04_specout/{repo}/modules/`
  - Discovery ログ: `{CR_PATH}/04_specout/{repo}/discovery-log.md`
  - AIレビュー: `{CR_PATH}/04_specout/{repo}/review/04_specout-review.md`
{if HAS_CROSS:}
- cross: `{CR_PATH}/04_specout/cross/SPO-{CR}-cross.md`
  - AIレビュー: `{CR_PATH}/04_specout/cross/review/04_specout-cross-review.md`
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
1. For each `{repo}` in `AFFECTED_REPOS`（`{CR_PATH}/04_specout/{repo}/work/bfs-state.json` が存在する repo のみ）, run via Bash:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-04-specout/scripts/specout_bfs.py status --path {CR_PATH}/04_specout/{repo}/work/bfs-state.json --brief`
   → 出力 JSON の `seed_direct_file_count` を合算して `TOTAL_SEED_DIRECT_FILES`（シードの直接参照ファイル数。変更対象
   ファイル数の目安）、`confirmed_file_count` を合算して `TOTAL_CONFIRMED_FILES`（波及ファイル数。参考値）、
   `seed_budget_truncated_count` を合算して `TOTAL_SEED_TRUNCATED` とする
   （`bfs-state.json` を直接読んで辞書キーを数えてはならない。決定的処理はスクリプトが担う）。
   `bfs-state.json` を持つ repo が1つもない場合は本 Step C5 全体をスキップする。
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
加えて repo ごとに次を報告する（値は `{CR_PATH}/04_specout/{repo}/discovery-log.md` と `work/metrics.jsonl` から転記する。自分で数え直さない）:
- 判定エンジン（`slice` / `rule`）。discovery-log の「## 探索設定」に判定エンジンの警告があればその文面。
  `SWITCHED_REPOS` に入った repo は「Wave {wave} から規則判定に切り替え」。
- LLM 分類に回ったヒット数（`metrics.jsonl` の波ごとの `llm_hits` の合計）。
- 打ち切りの有無（「## 打ち切り記録」の理由別の件数）。`wave-limit` があれば「`SPECOUT_MAX_WAVE_DEPTH` を上げて再実行すると
  続きから探索します」、`hit-budget` / `llm-budget` があれば「`/xddp-04-specout {CR} --re-discover {シンボル}` で追えます」を添える。
- 予算で打ち切った投入シンボル（「## 予算で打ち切った投入シンボル（Wave N）」の各節の転記。あれば強調する）。
- 要約の拡大による再訪の件数（`metrics.jsonl` の `revisit_count` の合計）。
