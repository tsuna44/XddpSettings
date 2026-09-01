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
MAX_WAVE_DEPTH, SPECOUT_MAX_AFFECTED_FILES, SPECOUT_MAX_FILES_PER_MODULE, SPECOUT_DIAGRAM_LEVEL,
SPECOUT_SEQUENCE_LEVELS, SPECOUT_BACKEND, SPECOUT_BACKEND_OVERRIDES, SPECOUT_HIT_FILTER,
SPECOUT_CLASSIFY_CHUNK_SIZE, SPECOUT_CLASSIFY_PARALLEL, CR_PROFILE.
`SPECOUT_HIT_FILTER` は未指定時 `conservative`。`SPECOUT_CLASSIFY_CHUNK_SIZE` は未指定時 `40`、
`SPECOUT_CLASSIFY_PARALLEL` は未指定時 `4`（PLAN-20260806 Phase 3 Stage 2 §4.8）。)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step -1: DEVELOPMENT_MODE Check

If `DEVELOPMENT_MODE` = `new`:

1. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
     CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: ⏭️ スキップ（対象外）, DETAIL_STEP: `-`
   Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
     CR_PATH: {CR_PATH}, STEP_NUM: 4b, STATE: ⏭️ スキップ（対象外）, DETAIL_STEP: `-`
   - If `CR_PROFILE` = `quick`:
       Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
         CR_PATH: {CR_PATH}, STEP_NUM: 5, STATE: ⏭️ スキップ（対象外）, DETAIL_STEP: `-`
       （`new` では cross SPO が生成されないため §3.8 の cross DSN 分岐に入らず、工程5は完全に
       スキップされる。この経路では `/xddp.05.arch` を起動しないため、ここで記録しないと工程5が
       `⬜ 未着手` のまま残る）
   - 次に実行すべきコマンド → （`CR_PROFILE` = `quick` の場合）`/xddp.06.design {CR}` ／
     （それ以外）`/xddp.05.arch {CR}`
   - Run via Bash:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py history-add --cr-path {CR_PATH} --step 4a --text "ℹ️ 工程4a・4b: DEVELOPMENT_MODE=new のためスキップ（母体コードが存在しないため波及調査を省略）"`
2. Tell the user (Japanese):
   > ℹ️ `DEVELOPMENT_MODE: new`（新規開発モード）が設定されています。
   > 工程4a（スペックアウト）と工程4b（CRS更新）は母体コードの波及調査を行う工程であるため、新規開発時はスキップします。
   {If CR_PROFILE ≠ quick: > 工程5（実装方式検討）では母体コードが存在しない前提で実装方式を検討します。}
   >
   > **次のコマンド:** （`CR_PROFILE` = `quick` の場合）`/xddp.06.design {CR}` ／
   > （それ以外）`/xddp.05.arch {CR}`
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
見つからなければ `## Step A-cross` の `If no inter-repo dependencies found` 行で
`HAS_CROSS = false` に降格する。xddp.common「## Resolve HAS_CROSS」の対象外 —
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

`specout_bfs.py init`（`discovery-setup` エージェント経由）では `EFFECTIVE_MAX_WAVE_DEPTH` / `EFFECTIVE_HIT_FILTER` を使用する。これらは `bfs-state.json` に保存され、以降の波ループで `specout_bfs.py search` が読み込むため、`search` コマンド自体には `--max-wave-depth` / `--hit-filter` を渡さない。

## Step 0.6: Mark In-Progress

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
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

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Snapshot Phase Baseline" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a

## Step A: Per-repo Specout — Discovery Phase

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A: Discovery（探索）中`

For each `{repo}` in `AFFECTED_REPOS`, check whether `{CR_PATH}/04_specout/{repo}/bfs-state.json` exists.
If it exists, run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py status --path {CR_PATH}/04_specout/{repo}/bfs-state.json --brief`
→ 出力 JSON の `state` を以下のテーブルで判定する（スクリプトが見つからない場合は setup.sh 実行を案内して停止。実行時エラーの場合は stderr を表示して停止）。
`--brief` はコンテキスト蓄積対策（PLAN-20260806 Phase 3 Stage 2 §4.5(f)）であり、
`ok`/`state`/`current_wave`/`wave_write_complete`/`remaining_frontier_count`/`confirmed_file_count`
のみを返す（本テーブルの判定・下記「件数一致検証」の前提ガードはいずれも `state`/`wave_write_complete`
のみを使う。`confirmed_file_count` は「## Step C5: Profile Fit Check」専用の追加キーである）。

| bfs-state.json 状態 | RE_DISCOVER | 対応 |
|---|---|---|
| ファイルが存在しない | false | 新規 `discovery-setup` を実行してから波ループに入る |
| ファイルが存在しない | true | 既存 visited セットなし。新規 `discovery-setup` として開始する（ユーザーに通知: "既存の探索履歴が存在しないため新規 Discovery として実行します"） |
| 状態: `in-progress` | false | 波ループが中断している。`discovery-setup` はスキップし、SKILL 側の波ループを `search` から再開する（Visited/Frontier は bfs-state.json から自動復元されるため、追加の引数は不要） |
| 状態: `in-progress` | true | `specout_bfs.py merge-frontier` で ENTRY_POINTS を既存 Frontier にマージ（HIGH 平文形式で追記）してから SKILL 側の波ループを再開する |
| 状態: `paused-at-limit` | false | 最大波数上限に達して一時停止中 → `recovery-procedures.md` の「## Paused-at-limit Handling」を適用する |
| 状態: `paused-at-limit` | true | ENTRY_POINTS を既存 Frontier にマージしてから `recovery-procedures.md` の「## Paused-at-limit Handling」を適用する |
| 状態: `paused-at-limit-2nd` | any | 2回目以降の上限到達 → `recovery-procedures.md` の「## Paused-at-limit-2nd Handling」を適用する |
| 状態: `complete` | false | Discovery 済み。Document フェーズへスキップ |
| 状態: `complete` | **true** | `recovery-procedures.md` の「## Re-discover Processing」を適用する |

**波ループへ入れてはならない repo（重要）:** `paused-at-limit`/`paused-at-limit-2nd` の repo は、
上表に従って `recovery-procedures.md` へ振り分けてから、継続パス選択の結果 `in-progress` に戻った
repo のみを後述の `ACTIVE_REPOS` に含める。`cmd_search` は `paused` 状態で呼び出されると
「prune / finish で継続パスを選択してから search してください」で異常終了するため、
paused のまま波ループに入れると step a でいきなり停止する。

**件数一致検証（独立回帰チェック。`bfs-state.json` が存在する repo すべてに適用する）:**

**適用対象ガード:** `bfs-state.json` が存在しない repo（新規 CR）では**本ブロック全体をスキップする**。
直前の `specout_bfs.py status --brief` 自体が実行されておらず、下記の前提ガードが参照する
`wave_write_complete` が得られないためである（status を追加実行してはならない — 状態ファイルが
無い以上エラーになる）。新規 CR は後述の**波ループ終了時の検証**で検証される。

**前提ガード:** 直前の `specout_bfs.py status --brief` の出力 JSON の `wave_write_complete` が `false` の場合、
**本検証は実行しない**。この状態は「`search` 済み・`commit-wave` 未完」を意味する。
`search` 自体は discovery-log.md へ Wave セクションを書かない（書き込みは `cmd_commit_wave` の
`_append_to_file` のみ）ため、`search` 直後に停止したケースでは当該波の `## Wave N` が
そもそも存在せず `--wave all` は当該波を列挙しない。問題になるのは
**`commit-wave` が `_append_to_file` の途中でクラッシュした場合**であり、このとき
`## Wave N` と実行コマンド一覧だけが書かれヒット行テーブルが欠けた**書きかけセクション**が残る。
これを検証すると不一致となり、`## Count Mismatch Handling` が
「Discovery やり直し / 承知で続行」という**誤った選択肢**を提示してしまう。
`wave_write_complete = false` は両ケースを区別せずに立つフラグであるため、
安全側に倒して一律スキップする（ガードを外してはならない理由がこれである）。

正しい復旧は「`search` から再開する」ことであり、これは
**`recovery-procedures.md`「## Wave 途中失敗からの再開（経路統一）」**が担う
（PLAN-20260806 Phase 3 Stage 2 で波ループの実行主体が本 SKILL 側へ移設されたため、
クラッシュ再開手順も `xddp-specout-agent.md` ではなく `recovery-procedures.md` 側に一本化されている）。
下記「波ループ」に入れば `wave_write_complete: false` を検出して自動的に `search` から再開し、
書きかけ Wave セクションはスクリプトが切り捨てて再構築する。
したがって SKILL 側は**本検証をスキップして通常の波ループへ進めばよい**。
再開が完了すれば `wave_write_complete` が `true` になり、
**波ループ終了時の検証（下記）で検証される**。

`wave_write_complete` が `true` の場合、Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_verify_counts.py --log {CR_PATH}/04_specout/{repo}/discovery-log.md --wave all --strict; echo "VERIFY_EXIT=$?"`
  （終了コードを stdout の `VERIFY_EXIT=` 行で明示的に受け取り、下記の分岐を決定的にする）
- **exit 3（件数不一致）:** stdout JSON の `mismatch_waves` を取得し、
  Read `~/.claude/skills/xddp.04.specout/recovery-procedures.md`,
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
xddp.common の apply 呼び出し規約と同じ方式）:

`in-progress` + RE_DISCOVER=true の場合:
Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py merge-frontier --path {CR_PATH}/04_specout/{repo}/bfs-state.json --symbols {ENTRY_POINTS をカンマ区切りで展開}`
If the script is not found: tell the user to run `setup.sh` and stop. If it errors: display stderr and stop.
その後 SKILL 側の波ループを再開する（下記「波ループ」を参照）。

`complete` + RE_DISCOVER=true の場合:
Read `~/.claude/skills/xddp.04.specout/recovery-procedures.md`, apply "## Re-discover Processing" with:
  CR_PATH: {CR_PATH}, repo: {repo}, ENTRY_POINTS: {ENTRY_POINTS}, TODAY: {TODAY}

`paused-at-limit` の場合:
Read `~/.claude/skills/xddp.04.specout/recovery-procedures.md`, apply "## Paused-at-limit Handling" with:
  CR: {CR}, CR_PATH: {CR_PATH}, repo: {repo}, MAX_WAVE_DEPTH: {EFFECTIVE_MAX_WAVE_DEPTH}

`paused-at-limit-2nd` の場合:
Read `~/.claude/skills/xddp.04.specout/recovery-procedures.md`, apply "## Paused-at-limit-2nd Handling" with:
  CR_PATH: {CR_PATH}, repo: {repo}

→ bfs-state.json / discovery-log.md / progress.md はそのファイル内の記述に従って更新される。
  checkpoint.md は bfs-state.json から自動生成される人可読ビューであり、直接参照・編集しない。

---

**Setup: discovery-setup（Wave 0 構築・初回のみ）**

`{CR_PATH}/04_specout/{repo}/bfs-state.json` が**存在しない** `{repo}` のみを対象に `discovery-setup`
を実行する。state が既に存在する repo（上表で「波ループを再開する」と判定された repo）は本ステップを
スキップし、直接「波ループ」へ入る（`specout_bfs.py init` は state 既存時に「bfs-state.json が
既に存在します（re-discover か import を使用してください）」で異常終了するため、無条件起動すると
再開時にループが停止する）。

`IS_MULTI` = true（マルチリポジトリ）の場合は対象 repo を Agent ツールで**並列呼び出し**する
（各 repo は独立した discovery-log.md を持つため並列実行可能）。
`IS_MULTI` = false（シングルリポジトリ）の場合は順次でよい。

For each `{repo}` requiring setup:

Let `MODULE_CATALOG_FILE` = `{DOCS}/{repo}/module-catalog.md`.
If `MODULE_CATALOG_FILE` does not exist: set `MODULE_CATALOG_FILE` = empty string.

Use the **Agent tool** with `subagent_type=xddp-specout-agent` and pass:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
BASELINE_SPECS_DIR: {DOCS}/{repo}/specs/
CROSS_SPECS_DIR: {DOCS}/cross/specs/
ENTRY_POINTS: {ENTRY_POINTS}
OUTPUT_DIR: {CR_PATH}/04_specout/{repo}/
TODAY: {TODAY}
EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}
INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS}
MAX_WAVE_DEPTH: {EFFECTIVE_MAX_WAVE_DEPTH}
SPECOUT_MAX_FILES_PER_MODULE: {SPECOUT_MAX_FILES_PER_MODULE}
SPECOUT_BACKEND: {SPECOUT_BACKEND_OVERRIDES.get(repo, SPECOUT_BACKEND)}
SPECOUT_HIT_FILTER: {EFFECTIVE_HIT_FILTER}
CHECKPOINT: {CR_PATH}/04_specout/{repo}/bfs-state.json
MODULE_CATALOG_FILE: {MODULE_CATALOG_FILE}
```

（`SPECOUT_BACKEND` は Discovery BFS の参照解決バックエンド。repo 単位上書き `SPECOUT_BACKEND.{repo}` があれば
`SPECOUT_BACKEND_OVERRIDES` 経由で当該 repo 値へ解決し、無ければグローバル `SPECOUT_BACKEND`（既定 `auto`）を使う。
既定 `auto` は「rg があれば rg・無ければ grep」で従来と同一挙動。エージェントはこの値を `specout_bfs.py init --backend`
へ渡すのみで、`grep`/`rg` 以外の値は未実装のため grep へフォールバックする。document フェーズは `init` を実行しないため
このキーは discovery-setup 呼び出しにのみ渡す。）

（`SPECOUT_HIT_FILTER` は Discovery BFS の保守的ヒット事前フィルタ（既定 `conservative`／`off`）。エージェントは
この値を `specout_bfs.py init --hit-filter` へ渡すのみ。`SPECOUT_BACKEND` と同様 discovery-setup 呼び出しにのみ渡す
（document フェーズは `init` を実行しないため）。）

全 setup 呼び出しの完了を待ってから波ループへ進む。

**波ループ（ACTIVE_REPOS が空になるまで繰り返す。各周回が「1波」に相当する。
PLAN-20260806 Phase 3 Stage 2 §4.2）:**

Let `ACTIVE_REPOS` = `AFFECTED_REPOS` のうち、上表の判定または setup 完了により
state が `in-progress` になった repo の集合（`complete` の repo・上記で `recovery-procedures.md` へ
振り分け済みの `paused-at-limit`/`paused-at-limit-2nd` の repo は含めない）。

Repeat while `ACTIVE_REPOS` is not empty:

**a. search の実行（repo ごと）**

For each `{repo}` in `ACTIVE_REPOS`, run via Bash:
```
specout_bfs.py search --path {CR_PATH}/04_specout/{repo}/bfs-state.json \
  --hits-dir {CR_PATH}/04_specout/{repo}/ --chunk-size {SPECOUT_CLASSIFY_CHUNK_SIZE}
```
（`--hits-dir` はスクリプトが state の `current_wave` から `wave-{N}-hits.json` を組み立てるため、
呼び出し側が波番号を search 実行**前**に知る必要はない。波番号は本コマンドの stdout の `"wave"` キーから取得し、
以降の step b〜d の出力パス組み立てに使う）

- 出力 JSON の `paused` が `true` の場合: `state`（`paused-at-limit`/`paused-at-limit-2nd`）に応じて
  上記の状態判定テーブルと同じ `recovery-procedures.md` の該当セクションを適用し、当該 `{repo}` を
  `ACTIVE_REPOS` から外す。
- `search` が exit 非0 の場合（frontier 空・バックエンド不整合等）: stderr を表示したうえで
  当該 `{repo}` のみを `ACTIVE_REPOS` から外し、同じ波の他 repo は step b 以降を続行する
  （波ループ全体を止めると他 repo が巻き添えで停止する。当該波は未コミットで state は前波の確定状態の
  ままのため、原因を除去すればそのまま再開して安全である）。波ループ終了後に失敗 repo の一覧と stderr を人へ提示する。
- 成功した repo について、stdout の `hits_file` と `chunks`（**ヒットチャンク**
  `wave-{N}-hits-chunk-{K}.json` の一覧。必ず1件以上）を保持する。以降これを **`HITS_CHUNKS[{repo}]`** と呼ぶ
  （step c の `--hits-chunks` の供給元。step c の `--chunks` に渡す classification 側のファイル群
  ＝ `CLASS_CHUNKS[{repo}]` とは別物であり、混同すると classification が1件も読まれない）。

**b. classifier の並列起動（全 ACTIVE_REPOS のチャンクを合算）**

`HITS_CHUNKS` を repo 単位で連続するように（`ACTIVE_REPOS` の順に、各 repo の chunk-0 から昇順に）
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

各 classifier には `CHUNK_FILE` として当該チャンクの `HITS_CHUNKS` エントリを、`OUT_FILE` として
`wave-{N}-chunk-{K}-class.json`（`{K}` は `CHUNK_FILE` と同一）を渡す:

Use the **Agent tool** with `subagent_type=xddp-specout-classifier-agent` and pass:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CHUNK_FILE: {CR_PATH}/04_specout/{repo}/wave-{N}-hits-chunk-{K}.json
OUT_FILE: {CR_PATH}/04_specout/{repo}/wave-{N}-chunk-{K}-class.json
EXCLUDE_PATTERNS: {EXCLUDE_PATTERNS}
INCLUDE_EXTENSIONS: {INCLUDE_EXTENSIONS}
```

この `OUT_FILE` の集合を repo ごとに **`CLASS_CHUNKS[{repo}]`** として保持する（step c で使う）。
各バッチの起動直前・完了直後に Bash `date +%s` を取り、
`{CR_PATH}/04_specout/{repo}/wave-{N}-batches.json` へ以下のスキーマで記録する（repo ごとに書く。
`{N}` は当該 repo の波番号。実効並列度の事後監査用。消費者は人と確認項目のみで、これを読むスクリプトはない）:
```json
[{"batch_index": 0, "chunk_files": ["…-chunk-0-class.json", "…"], "started_at": 1786000000, "ended_at": 1786000042}]
```
このファイルから求めた「当該 repo のチャンクが1件以上含まれていたバッチの数」を、
下記 step d の `--batch-count` に渡す。

**c. merge_classification.py の実行（repo ごと）**

For each `{repo}` in `ACTIVE_REPOS`, run via Bash（パスは step a の `hits_file` から導出する）:
```
merge_classification.py --hits {hits_file（step a）} \
  --hits-chunks {HITS_CHUNKS[{repo}]} --chunks {CLASS_CHUNKS[{repo}]} \
  --out {CR_PATH}/04_specout/{repo}/wave-{N}-class.json \
  --unsupported-out {CR_PATH}/04_specout/{repo}/wave-{N}-unsupported.json
```
（`--hits-chunks` には **`HITS_CHUNKS[{repo}]`**＝`search` が出力したヒットチャンク群を、
`--chunks` には **`CLASS_CHUNKS[{repo}]`**＝classifier が書いた `OUT_FILE` 群を渡す。
取り違えるとフラグ名が一致するため機械検査では検出されない — 変数名を厳密に区別すること）

- stdout の `min_chunk_mtime` を保持する（非 `null` なら step d へ `--chunk-mtime-min` として渡す）。
- exit 非0（line_id の欠落・重複・未知値・チャンク単位の不一致・欠落チャンク）の場合: stderr を
  表示したうえで当該 `{repo}` のみを `ACTIVE_REPOS` から**このイテレーションでは**外し、
  同じ波の他 repo は step d まで完了させる。失敗 repo の state は `wave_write_complete=false` の
  まま残るため、`recovery-procedures.md`「## Wave 途中失敗からの再開（経路統一）」の【S2】手順
  （欠落・stale チャンクのみを再投入する）にそのまま接続できる。波ループ終了後に失敗 repo の一覧と
  stderr を人へ提示する。

**d. commit-wave の実行（repo ごと）**

For each `{repo}` in `ACTIVE_REPOS`（step c を通過したもの）, run via Bash:
```
specout_bfs.py commit-wave --path {CR_PATH}/04_specout/{repo}/bfs-state.json \
  --hits {hits_file（step a）} --classification {CR_PATH}/04_specout/{repo}/wave-{N}-class.json \
  --unsupported-patterns {CR_PATH}/04_specout/{repo}/wave-{N}-unsupported.json \
  --chunk-count {当該 repo のチャンク数} --batch-count {step b で求めた実バッチ数} \
  --parallelism {SPECOUT_CLASSIFY_PARALLEL} \
  [--chunk-mtime-min {step c で得た値。非 null の場合のみ渡す}] --today {TODAY}
```
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

**波ループ終了後（全 repo が `complete` または失敗で `ACTIVE_REPOS` から外れた場合）:**
波ループ中に失敗した repo（step a/c/d で `ACTIVE_REPOS` から外れた repo）があれば、
一覧と直近の stderr を人へ提示し、`recovery-procedures.md`「## Wave 途中失敗からの再開（経路統一）」を
適用してから `/xddp.04.specout {CR}` を再実行するよう案内する。

`complete` になった repo について、per-repo progress table を更新: `| {repo} | ✅ 完了 | ⏳ 未着手 | - |`

## Step A-Document: Per-repo Specout — Document Phase

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A-Document: Documentation 中`

Discovery が全リポジトリで "complete" になった後、各リポジトリを**順次**ドキュメント化する。

Let `SCALE_WARNING_EMITTED` = `false`（§3.7b「## Step C5: Profile Fit Check」が参照する規模超過警告の
追跡用フラグ。下記ループ内でいずれかの repo が警告を出した場合に true へ更新し、以降このイテレーション内
では false に戻さない）。

For each `{repo}` in `AFFECTED_REPOS`:

Use the **Agent tool** with `subagent_type=xddp-specout-document-agent` and pass:
```
CR_NUMBER: {CR}
REPO_NAME: {repo}
REPO_PATH: {REPOS_MAP[repo]}
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
LATEST_SPECS_DIR: {XDDP_DIR}/latest-specs/{repo}/
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
SPECOUT_MAX_AFFECTED_FILES: {SPECOUT_MAX_AFFECTED_FILES}
SPECOUT_MAX_FILES_PER_MODULE: {SPECOUT_MAX_FILES_PER_MODULE}
SPECOUT_DIAGRAM_LEVEL: {EFFECTIVE_DIAGRAM_LEVEL}
SPECOUT_SEQUENCE_LEVELS: {EFFECTIVE_SEQUENCE_LEVELS}
DISCOVERY_LOG: {CR_PATH}/04_specout/{repo}/discovery-log.md
SPO_DETAIL_LEVEL: {EFFECTIVE_SPO_DETAIL_LEVEL}
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

Check if the agent emitted a scale warning (`SPECOUT_MAX_AFFECTED_FILES` exceeded). If so, relay to the user
and set `SCALE_WARNING_EMITTED = true`。

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
- Section 3: リポジトリ間シーケンス図 (if `EFFECTIVE_SEQUENCE_LEVELS` includes `repository`)
- Section 4: 共有インタフェース一覧 (インタフェース名 / 提供リポジトリ / 消費リポジトリ / 型・プロトコル / バージョン / breaking変更有無 — 検出なしの場合は「なし」)
- Section 5: リポジトリ間共有定数・列挙値 (識別子 / 値 / 定義リポジトリ / 参照リポジトリ / 用途 — 検出なしの場合は「なし」)
- Section 6: リポジトリ間共有データ型関連図 (OOP言語: Mermaid classDiagram / 手続き型: テキスト表形式 — 共有データ型が検出された場合のみ。検出なしの場合は省略)
- Section 7: データアクセスマトリクス (`EFFECTIVE_DIAGRAM_LEVEL` = `full` の場合のみ、または同一リソースへの並列書き込み・共有バッファアクセスが検出された場合)
- Section 8: データモデル（ER図・データ構造定義）(`EFFECTIVE_DIAGRAM_LEVEL` = `full` の場合のみ、またはデータ構造変更がある場合。Mermaid `erDiagram` または `classDiagram`)
- Section 9: データフロー図（DFD）(リポジトリ間データフローが識別された場合のみ。識別されなかった場合は「対象外（理由：リポジトリ間データフローなし）」と記載)
- Section 10: 追加提案図 (タイミング図：リアルタイム・組み込み系プロジェクトでは★必須。その他は任意)
- Section 11: CRS への反映事項（cross）

If no inter-repo dependencies found → skip cross/ SPO creation; set `HAS_CROSS = false`.

Update progress table: `| cross | — | ✅ 完了 | {TODAY} |`

## Step A2: SPO Review Loop

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step A2: SPOレビュー中`

Set `max_rounds` = `EFFECTIVE_REVIEW_MAX_ROUNDS_SPO`（Step 0.55 で解決済み。quick 時は `1`（ただし `REVIEW_MAX_ROUNDS.SPO` が明示的に `0` の場合は `0`）、full 時は Step 0.55 が `xddp.config.md` から読んだ `REVIEW_MAX_ROUNDS.SPO`（既定 3））。

For each `{repo}` in `AFFECTED_REPOS` (run review loops sequentially per repo):

（repo が "cross" 以外かつ `{CR_PATH}/04_specout/{repo}/discovery-log.md` が存在する場合のみ）
Run via Bash（ベストエフォート——抽出に失敗しても discovery-log.md 原本へフォールバックし工程を
止めない。抽出は監査用の全文を要約するだけで、失敗時に原本を使えばレビュー品質は劣化しない。
ラウンドループの外・repo ループ内で1回のみ実行する）:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py extract-review-scope --discovery-log {CR_PATH}/04_specout/{repo}/discovery-log.md --out {CR_PATH}/04_specout/{repo}/discovery-log-review-scope.md`
→ 成功時は `DISCOVERY_LOG_REF` = `{CR_PATH}/04_specout/{repo}/discovery-log-review-scope.md`、
   失敗時（discovery-log.md 不在含む）は `DISCOVERY_LOG_REF` = `{CR_PATH}/04_specout/{repo}/discovery-log.md`。

`round = 1`, `issues_remain = true`

While `issues_remain` and `round ≤ max_rounds`:

1. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Invoke Reviewer" with:
   DOCUMENT_TYPE: SPO, NEXT_DOCUMENT_TYPE: DSN, TARGET_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md,
   REFERENCE_FILES: [
     {CR_PATH}/01_requirements/ (all .md),
     {CR_PATH}/03_change-requirements/CRS-{CR}.md,
     （repo が "cross" 以外の場合のみ追加）{CR_PATH}/04_specout/{repo}/SPO-{CR}-funcmap.md,
     （repo が "cross" 以外かつ discovery-log.md が存在する場合のみ追加）{DISCOVERY_LOG_REF},
     {CR_PATH}/04_specout/{repo}/modules/ (all .md, including subdirectories)
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
        `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py note-add --cr-path {CR_PATH} --step 4a --text "未解決指摘あり（{CR_PATH}/04_specout/{repo}/review/04_specout-review.md）"`
     Exit loop.

## Step A2-cross: Cross SPO AI Review (only when HAS_CROSS = true)

If `HAS_CROSS`:
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Cross Artifact Review" with:
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

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Human Review Gate" with:
  CR_PATH: {CR_PATH}
  STEP_NUM: 4a
  STEP_LABEL: `Step A3`
  ARTIFACTS_TEXT: {built above}
  REVISE_COMMAND: `/xddp.revise {CR} specout`（対象リポジトリを指定）
→ let `CHANGED`.

If `CHANGED`:
- For each `{repo}` in `AFFECTED_REPOS`: Read `~/.claude/skills/xddp.common/SKILL.md`,
  apply "## Final Review Pass" with:
    DOCUMENT_TYPE: SPO
    NEXT_DOCUMENT_TYPE: DSN
    TARGET_FILE: {CR_PATH}/04_specout/{repo}/SPO-{CR}.md
    REFERENCE_FILES: {Step A2 と同一}
    REVIEW_ROUND: (last_round + 1)
    OUTPUT_FILE: {CR_PATH}/04_specout/{repo}/review/04_specout-review.md
- If HAS_CROSS and the user changed cross/ SPO: Read `~/.claude/skills/xddp.common/SKILL.md`,
  apply "## Final Review Pass" with:
    DOCUMENT_TYPE: SPO
    NEXT_DOCUMENT_TYPE: DSN
    TARGET_FILE: {CR_PATH}/04_specout/cross/SPO-{CR}-cross.md
    REFERENCE_FILES: {Step A2-cross と同一}
    REVIEW_ROUND: (last_round + 1)
    OUTPUT_FILE: {CR_PATH}/04_specout/cross/review/04_specout-cross-review.md

## Step B: Update CRS with Specout Findings

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step B: CRS更新中`
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
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

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: 🔄 進行中, DETAIL_STEP: `Step C: Excel再生成中`

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Regenerate CRS Excel" with:
  CR_PATH: {CR_PATH}
  CR: {CR}

## Step C5: Profile Fit Check

0. Let `ESCALATION_SUGGESTED` = `false`（本 Step 内で quick → full の昇格を推奨したかを保持する。
   Step D の分岐が参照する）。
1. For each `{repo}` in `AFFECTED_REPOS`（`{CR_PATH}/04_specout/{repo}/bfs-state.json` が存在する repo のみ）, run via Bash:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.04.specout/scripts/specout_bfs.py status --path {CR_PATH}/04_specout/{repo}/bfs-state.json --brief`
   → 出力 JSON の `confirmed_file_count` を合算し `TOTAL_CONFIRMED_FILES` とする
   （`bfs-state.json` を直接読んで辞書キーを数えてはならない。決定的処理はスクリプトが担う）。
   `bfs-state.json` を持つ repo が1つもない場合は本 Step C5 全体をスキップする。
2. If `CR_PROFILE` = `quick`:
     `TOTAL_CONFIRMED_FILES` > 5（quick 推奨基準「変更対象ファイル数 5 ファイル以下」）の場合、または `SCALE_WARNING_EMITTED` が `true` の場合（Step A-Document 内で `SPECOUT_MAX_AFFECTED_FILES` 超過警告が出ていた場合）:
       ユーザーに通知:
       > ⚠️ 波及ファイル数（{TOTAL_CONFIRMED_FILES}）が quick プロファイルの推奨基準（5ファイル以下）を超えています。
       > `full` プロファイルへの切替を推奨します。切り替える場合は `/xddp.set-profile {CR} full` を実行してください
       > （工程5は quick では未実施のため、切替後に工程5から着手することを推奨します）。
       Run via Bash:
         `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py note-add --cr-path {CR_PATH} --step 4a --text "quick規模超過警告: 波及ファイル数{TOTAL_CONFIRMED_FILES}件"`
       Set `ESCALATION_SUGGESTED` = `true`（Step D が工程5のスキップ記録・`/xddp.06.design` 案内を
       抑止するためのフラグ）。
   Else（`CR_PROFILE` = `full`）:
     `TOTAL_CONFIRMED_FILES` ≤ 5 かつ `SCALE_WARNING_EMITTED` が `false` の場合（Step A-Document 内で `SPECOUT_MAX_AFFECTED_FILES` 超過警告が出ていない場合）:
       ユーザーに通知:
       > ℹ️ 波及ファイル数（{TOTAL_CONFIRMED_FILES}）は quick プロファイルの推奨基準（5ファイル以下）を満たしています。
       > 以降の工程（5・6）を `quick` に切り替えることもできます。切り替える場合は `/xddp.set-profile {CR} quick` を実行してください
       > （工程2・3・4は完了済みのためやり直しません。工程5のスキップ・工程6の簡略化・レビュー1ラウンド化が以降に適用されます）。
3. いずれの通知も処理を停止しない（人が判断する）。

## Step D: Update progress.md

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4a, STATE: ✅ 完了, DETAIL_STEP: `-`,
  ARTIFACT_LINK: `[04_specout/](04_specout/)`
  （STATE = ✅ 完了 のため、スクリプトが `## 備考・メモ` の `⚠️ 工程4a:` 行を自動削除する）
Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
  CR_PATH: {CR_PATH}, STEP_NUM: 4b, STATE: ✅ 完了, DETAIL_STEP: `-`,
  ARTIFACT_LINK: `[CRS-{CR}.md](03_change-requirements/CRS-{CR}.md)`

If `ESCALATION_SUGGESTED` = true（Step C5 が quick → full の昇格を推奨した場合）:
  工程5のスキップ記録は行わない（`⬜ 未着手` のまま残す）。人がプロファイルを確定するまで
  工程5の要否が決まらないため、ここでスキップを確定させるとツール自身の昇格推奨を打ち消す。
  Set next command → `プロファイル確定待ち（/xddp.set-profile {CR} full で昇格、または quick のまま続行）`
  （progress.md の「## 次に実行すべきコマンド」欄に上記の文字列を記録する）
  ユーザーに通知:
  > 工程5の扱いはプロファイル確定後に決まります。
  > **昇格する場合:** `/xddp.set-profile {CR} full` → `/xddp.05.arch {CR}`
  > **quick のまま続行する場合:** （`HAS_CROSS` = false）`/xddp.06.design {CR}` ／
  > （`HAS_CROSS` = true）`/xddp.05.arch {CR}`
Else if `CR_PROFILE` = `quick` and `HAS_CROSS` = false:
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: 5, STATE: ⏭️ スキップ（対象外）, DETAIL_STEP: `-`
  （この経路では `/xddp.05.arch` を起動しないため、工程5のスキップを記録する箇所が他に存在しない）
  Next command → `/xddp.06.design {CR}`
Else:
  Next command → `/xddp.05.arch {CR}`
（`quick` でも `HAS_CROSS` = true の場合は工程5で cross DSN のみ生成するため `/xddp.05.arch` を案内する）

## Step E: Report in Japanese
Report: repos investigated, waves executed per repo, affected file count per repo, cross/ synthesis result, review rounds.
