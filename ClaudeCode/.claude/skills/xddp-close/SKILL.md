---
name: xddp-close
description: XDDP CR クローズ処理: 各工程の気づきをバックログへ集約し、知見ログ（lessons-learned.md）を生成・更新してCRを完了する。「CRをクローズして」「知見をまとめて」などで起動する。
argument-hint: "[CR番号]"
---

You are orchestrating **XDDP Close — CR Closeout & Knowledge Capture**.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)

---

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `TODAY` = today's date (YYYY-MM-DD).

(xddp.config.md lookup done in xddp-common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
REPOS_MAP, REPOS_KEYS, IS_MULTI, DOCS_DIR, DOCS, DEVELOPMENT_MODE, VCS_TYPE, VCS_BRANCH_PREFIX,
VCS_COMMIT_ON_STEP, VCS_AUTO_BRANCH, VCS_BASE_BRANCH.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`.
Let `HAS_CROSS` = (IS_MULTI and any cross/ files exist under `{CR_PATH}/`).
（本工程はクローズ時の棚卸しのため、特定1ファイルではなく cross/ 配下の存在を広く問う。
xddp-common「## Resolve HAS_CROSS」の対象外 — 詳細は同プロシージャの「適用外」注記を参照）

## Step 0: Precondition Check

Read `{CR_PATH}/progress.md`.
If process step 11 (最新仕様書作成) is not ✅ 完了, instruct the user to run `/xddp-11-specs {CR}` first, then stop.

## Step C-Pre: All Repos VCS Status Check

Read `~/.claude/skills/xddp-common/procedures/resolve-vcs-target-repos.md`, apply "## Resolve VCS Target Repos" with:
  REPO_CANDIDATES: {REPOS_KEYS}, CR_PATH: {CR_PATH}, CR: {CR}
→ let `VCS_TARGET_REPOS`.
（本ステップの警告文の切り替えと、後段「正常クローズ時の最終コミット」の対象リポジトリの両方で使う。
同プロシージャは VCS 種別に依存しない純粋なファイル存在判定であり、`VCS_TYPE: none` でも解決してよい）

For each `{repo}` in `REPOS_KEYS`:
  If `VCS_TYPE` is `none`:
    Skip this repo.
  Else:
    Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_vcs.py status --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE}`
    → let `REPO_STATUS`.
    If `REPO_STATUS` is `dirty`:
      If `{repo}` is in `VCS_TARGET_REPOS`:
        Warn: "⚠️ {repo} に未コミット変更があります（クローズ処理の最終段で自動コミットされます）。"
      Else:
        Warn: "⚠️ {repo} に未コミット変更があります。コミット後に close を実行することを推奨します。"
    If `REPO_STATUS` is `unknown`:
      Warn: "⚠️ {repo} の VCS 状態が不明です。手動で確認してください。"

Tell the user:
> 全リポジトリの確認が完了しました。続行しますか？ [続行 / 中止]
(警告があっても続行は可能。意図的なワークスペース設定変更等であれば無視してよい。)

Wait for user to choose 続行 before proceeding.

## Step A: Collect Insight/Proposal Memos

Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-close/scripts/collect_insights.py collect --cr {CR} --cr-path {CR_PATH} --xddp-dir {XDDP_DIR} --docs {DOCS} --repos-keys {REPOS_KEYS をカンマ区切りで展開} --affected-repos {AFFECTED_REPOS をカンマ区切りで展開} {HAS_CROSS の場合は "--has-cross"} {IS_MULTI の場合は "--is-multi"} --output-file {CR_PATH}/pending-items/INSIGHTS-{CR}.md`

終了コードが 0 以外の場合は人に報告して停止する（気づきの取りこぼしは知見ログの欠落に直結するため、
ベストエフォートでの継続はしない）。

Read `{CR_PATH}/pending-items/INSIGHTS-{CR}.md`（このファイルのみを読む。個々の成果物は読まない）。
収集サマリの「抽出エントリ数」が 0 の場合はその旨を人に提示し、続行可否を確認する。

## Step B: Update Improvement Backlog

Run via Bash（ファイルを書かない事前確認）:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-close/scripts/promote.py index --check --cr {CR} --lessons-file {XDDP_DIR}/lessons-learned.md --backlog-file {XDDP_DIR}/improvement-backlog.md`

終了コードが 0 以外なら stderr を示して停止する（必要な節が無い）。
stdout の JSON の `cr_idea_count`・`cr_idea_ids`・`cr_ll_count`・`cr_ll_ids` を Let `PRE_CHECK` とする（Step C でも使う）。

If `PRE_CHECK.cr_idea_count` が 1 以上: IDEA を追記しない。Tell the user:
> 今の CR の IDEA が既に {cr_idea_count} 件（{cr_idea_ids}）あるので追記しません。作り直すなら、それらを消してから `/xddp-close {CR}` を再実行してください。
> 前回の close で `{DOCS}` に昇格済みなら、`{DOCS}/improvement-backlog.md` の同じ ID のエントリも消してください（消さなければ、作り直したエントリは `{DOCS}` の backlog で「内容が違う」として報告され、上書きされません）。

Else:
- Read `{XDDP_DIR}/improvement-backlog.md`. If not exists, create it from `~/.claude/skills/xddp-close/templates/10_improvement-backlog-template.md`（`{YYYY-MM-DD}` は `{TODAY}` に置き換え、他の `{…}` は残す）.
- From insights in Step A, add `IDEA-{CR}-{NN}` entries（`{NN}` は `01` からの2桁の連番）for items NOT "今回対応".
- 各エントリは `## 3. アイデア詳細` の末尾（次の `## ` の見出しの前）に足す（ファイルの末尾ではない）。
  §1・§2 の表は書かない（Step C の後の `promote.py index` が §3 から作り直す）。

**Set the `repo` row of each IDEA entry using this auto-detection logic:**
- Insight from `{CR_PATH}/06_design/{repo}/` の CHD内容ファイル（「## Discover CHD Files」で解決）または `{repo}/` related files → `{repo-name}`
- Insight about inter-repo interfaces / cross-repo flows → `cross`
- Insight affecting all repos equally (e.g., test framework change) → `全リポジトリ`
- Difficult to determine → `unknown`（Step D で「要確認 IDEA」として示す）

Entry format（項目・本文のラベルを変えない。`{DOCS}` の backlog への足し込みがこの書式で読む）:
```markdown
### IDEA-{CR}-{NN}：{タイトル}

| 項目 | 内容 |
|------|------|
| カテゴリ | {カテゴリ一覧から1つ} |
| 優先度 | 高／中／低 |
| repo | {repo名／cross／全リポジトリ／unknown}（{判定根拠、例: CHD/repo-a の変更ファイルに関連}） |
| 発生源 | {CR}の{資料名}「気づき・提案メモ」 |
| ステータス | 🆕 新規 |
| 対応CR | — |

**内容：**  
{改善アイデアの具体的な説明}

**発生経緯：**  
{どのCRの作業中に、何をきっかけに気づいたか}

**期待効果：**  
- {効果}

**推定影響範囲：**  
{影響するモジュール・ファイル・機能の概要}

**CR化の判断メモ：**  
{いつ・どの条件でCR化すべきか}

---
```

## Step C: Generate/Update Lessons Learned Log

<!-- lessons-learned 二層構造メモ（実装コメント）:
  Layer 1: {XDDP_DIR}/lessons-learned.md
    - 作業中の全CR横断・全リポジトリ混在の知見蓄積ファイル
    - xddp-02-analysis・xddp-05-arch・xddp-06-design・xddp-09-test の Step A0（load-lessons-context.md）で参照
    - xddp-close Step C3 でリポジトリ別に分類して Layer 2 へ昇格
  Layer 2: {DOCS}/{repo}/knowledge/lessons-learned.md
    - クローズ済み CR 由来のリポジトリ別・永続知見（xddp-update-knowledge の lesson も書く）
    - xddp-02-analysis の Step 0（domain_refs.py）で参照
  二重管理ではなく「作業中の混在参照（高鮮度）」と「クローズ後の分類済み参照（高精度）」の役割分担。-->

If `PRE_CHECK.cr_ll_count` が 1 以上: LL を追記しない（下の「ファイルサイズポリシー」へ進む）。Tell the user:
> 今の CR の LL が既に {cr_ll_count} 件（{cr_ll_ids}）あるので追記しません。作り直すなら、それらを消してから `/xddp-close {CR}` を再実行してください。
> 前回の close で `{DOCS}` に昇格済みなら、`{DOCS}/{repo}/knowledge/lessons-learned.md` の同じ ID のエントリも消してください（消さなければ、作り直したエントリは Layer 2 で「内容が違う」として報告され、上書きされません）。

Else:
- Read `{XDDP_DIR}/lessons-learned.md`. If not exists, create it from `~/.claude/skills/xddp-close/templates/lessons-learned-template.md`（`{YYYY-MM-DD}` は `{TODAY}` に置き換え、他の `{…}` は残す）.
- Add `LL-{CR}-{NN}` entries（`{NN}` は `01` からの2桁の連番）at the end of `## 知見詳細`.
  「エントリ一覧」「タグ別インデックス」の表と `最終更新CR` は書かない（下の `promote.py index` が作り直す）。

### Knowledge Extraction Perspectives

Step A の `INSIGHTS-{CR}.md` の項目から、後の CR で同じ判断・作業をするときに役立つものを LL にする。
観点は、要求分析・方式検討と設計・実装とテスト・進め方。タグはテンプレートの「タグ一覧」から選ぶ。

### Entry Format

```markdown
### LL-{CR}-{NN}：{タイトル}

**CR：** {CR} ／ **工程：** {工程名} ／ **repo：** {repo名 or cross or unknown} ／ **タグ：** {#タグ1, #タグ2}

**発生状況：**  
{どんな場面・判断でこの知見が生まれたか（1〜2文）}

**学んだこと：**  
{具体的な知見・教訓}

**次回への適用：**  
- {チェックポイント1}
- {チェックポイント2}

---
```

（タグはカンマ区切り。本文にコードを書くときはコードブロック〔```` ``` ````〕で囲み、必ず閉じる）

**Auto-assign `repo:` field to each LL entry:**
- Related to code changes in a specific `{repo}` → `repo: {repo-name}`
- Related to inter-repo interface or cross-repo flow → `repo: cross`
- Difficult to determine → `repo: unknown` (flag in closeout report as "要確認 LL"; do NOT promote to knowledge hub)

**ファイルサイズポリシー（アーカイブ提案）:**
Count the total number of `### LL-` heading lines in `{XDDP_DIR}/lessons-learned.md`.
Let `total` = count of `### LL-` lines.
If total > 100:
  Tell the user:
  > ⚠️ lessons-learned.md のエントリ数が {total} 件に達しました（推奨上限: 100 件）。
  > 読み込み時のコンテキスト消費量増大・検索精度低下を防ぐため、古いエントリのアーカイブを推奨します。
  >
  > アーカイブ手順（手動）:
  > 古い LL エントリを `{XDDP_DIR}/lessons-learned-archive-{YYYY}.md` に移す。
  > 表（エントリ一覧・タグ別インデックス）は、この後の `promote.py index` が作り直す（移した ID はタグ別インデックスからも消える）。
  >
  > 続行する場合はそのまま Enter を押してください。
  Wait for user to press Enter (allow continue without action).
  （自動アーカイブは行わない。次回 CR クローズ時も同様の警告が出る。）

**表の作り直し:**
Step B・C の追記の有無によらず必ず Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-close/scripts/promote.py index --cr {CR} --today {TODAY} --lessons-file {XDDP_DIR}/lessons-learned.md --backlog-file {XDDP_DIR}/improvement-backlog.md`

終了コードが 0 以外なら stderr を示して停止する。
stdout の JSON を Let `INDEX_RESULT` とする（Step D で `unknown_tags`・`cr_unknown_repo_ideas`・`bad_ideas`・`unparsed_ll`・`duplicate_ids`・`cr_idea_count`・`cr_ll_count` を使う）。

**Final VCS commit:**
If `VCS_TYPE` is not `none`:
  Read `~/.claude/skills/xddp-common/procedures/vcs-commit-if-dirty.md`, apply "## VCS Commit If Dirty" with:
  REPO_LIST: VCS_TARGET_REPOS, COMMIT_MESSAGE: "{CR} 完了", ON_FAILURE: ask
  → let `COMMIT_OUTCOME`, `UNCOMMITTED_REPOS`, `UNPROCESSED_REPOS`.
  If `COMMIT_OUTCOME` is `aborted`（ユーザーが「中止」を選んだ場合）: Run via Bash:
    `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py close-state --cr-path {CR_PATH} --state "⏸ 中断" --detail "最終コミット失敗（VCS 側の問題を解消後に /xddp-close {CR} を再実行）"`
    then stop.
  （`COMMIT_OUTCOME` が `partial` の場合はクローズ処理を続行する。未コミットのリポジトリは
  `## VCS Commit If Dirty` がループ終了後に警告表示済みであり、ユーザーが承知のうえで続行を
  選んだ結果であるため、ここでの追加処理は行わない）

（本ブロックの下流には Step C0（Parallel-CR 同期）・Step C2〜C7（成果物の `{DOCS_DIR}` 昇格）・
Step C3.5/C3.6（知見昇格）・Step D（Human Review Gate）・Step E（`## CR クローズ` の progress.md
追記）が並ぶため、既定の停止契約（`ON_FAILURE: stop`）のままだと `git commit` の失敗や `unknown` で
クローズ処理全体が中断し成果物昇格も CR 完了記録も実行されない。`ON_FAILURE: ask` により人が
「コミット漏れを承知で昇格まで進める」か「VCS 側を直して再実行する」かを選べるようにする。設計判断の
詳細は `docs/adr/ADR-0011-vcs-abstraction.md` Decision 20 を参照。
`VCS_TARGET_REPOS` は Step C-Pre で解決済みの値をそのまま使う）

## Step C0: Pre-close Sync (Parallel-CR Support)

### 1. Source Code Sync Check
If `VCS_TYPE` is `none`:
  Skip this sub-step (`git fetch`/`git log` は Git 専用のリモート追従確認のため実行しない)。
Else:
  - Run `git fetch origin` to get the latest remote state.
    - If fetch fails: display error and ask user 続行/中止.
  - Run `git rev-parse --abbrev-ref HEAD` → let `CURRENT_BRANCH`
    （コマンドが失敗した場合は `CURRENT_BRANCH` を空として扱う）。
  - Run `git log HEAD..origin/main --oneline` to check for un-merged remote commits.
  - If un-merged commits exist:
    - If `CURRENT_BRANCH` equals `{VCS_BRANCH_PREFIX}{CR}`（本ツールが作成した作業ブランチ上にいる場合）:
      Warn: "⚠️ 作業ブランチ `{CURRENT_BRANCH}` の分岐後に origin/main が進んでいます。
      統合時に取り込みが必要か確認してください（作業ブランチには upstream が設定されていないため
      `git pull` は使用しないでください。必要に応じて rebase / merge を検討してください）。"
      → 続行する（停止しない）。
    - Else（起点ブランチ相当の上にいる場合。`CURRENT_BRANCH` が空の場合を含む）:
      prompt user to run `git pull`（本プラン適用前と同一の既存挙動）。

### 2. {DOCS_DIR}/ Sync
Check whether `{DOCS}` is a git repository and run `git -C {DOCS} pull` if so.
If not git-managed: display warning and ask user 続行/中止.

Let `DOCS_PULL_FAILED` = false.

pull が失敗したら stderr を示す。続けて `git -C {DOCS} rev-parse --show-prefix` を実行し、出力を `PREFIX`
（`{DOCS}` のリポジトリのルートからの位置。末尾は `/`、ルートなら空）とする。git が返すパスはリポジトリの
ルートからなので、`AI_INDEX.md` は `{PREFIX}AI_INDEX.md` と比べる。パスの一覧は `-z`（NUL 区切り）で取る。
`{DOCS}` の状態で次の (a)〜(c) に分ける。

- **(a) merge の途中で止まった**（`git -C {DOCS} rev-parse -q --verify MERGE_HEAD` が成功する）:
  `git -C {DOCS} diff --name-only --diff-filter=U -z` で衝突したファイルを取る。
  - 衝突したのが `{PREFIX}AI_INDEX.md` だけなら、次を尋ねる。
    > ⚠️ `{DOCS}` の pull で `AI_INDEX.md` が衝突し、merge の途中で止まりました。
    > AI_INDEX は close の最後に `{DOCS}` から作り直すので、どちらの内容を採ってもかまいません。
    > 1. 取り込む側の AI_INDEX.md を採って merge を終える（推奨。`{DOCS}` に merge のコミットを作る）
    > 2. merge を取り消して（pull の前に戻して）続行する（C0-4 の競合検出を行わない）
    > 3. merge を取り消して中止する
    - 1.: `git -C {DOCS} checkout --theirs -- AI_INDEX.md`・`git -C {DOCS} add -- AI_INDEX.md`・
      `git -C {DOCS} commit --no-edit` を順に実行する。pull が済んだので、C0-4 は行う（`ORIG_HEAD` は pull の前を指す）。
      どれかが失敗したら（取り込む側が AI_INDEX.md を消した場合は `checkout --theirs` が失敗する。commit の
      フック等で commit が失敗する）、stderr を示し、`git -C {DOCS} merge --abort` で pull の前に戻してから
      「続行／中止」を尋ねる。
    - 2.・3.: `git -C {DOCS} merge --abort` の後に続行・中止する。
  - 衝突したのが `AI_INDEX.md` 以外にもあるか、衝突したファイルが無い（フックの失敗等で merge の途中で
    止まった）なら、stderr と衝突したファイルを示し、`git -C {DOCS} merge --abort` で pull の前に戻してから
    「続行／中止」を尋ねる（衝突は人が解消する。merge の途中のまま続行しない）。
- **(b) rebase の途中で止まった**（`git -C {DOCS} rev-parse --absolute-git-dir` が返すディレクトリの下に
  `rebase-merge` か `rebase-apply` がある）: 先に `git -C {DOCS} diff --name-only --diff-filter=U -z` で
  衝突したファイルを取り、`{PREFIX}AI_INDEX.md` と比べる（`rebase --abort` の後は取れない）。その後に
  `git -C {DOCS} rebase --abort` で pull の前に戻し、衝突したファイルを示して「続行／中止」を尋ねる。
  衝突が `{PREFIX}AI_INDEX.md` だけなら「どちらの内容を採ってもかまいません（close が作り直す）」と添え、
  衝突したファイルが無ければ stderr だけを示す（rebase の途中の解消は人が行う）。
- **(c) merge・rebase の途中ではない**（pull が始まる前に止まった）: `git -C {DOCS} status --porcelain -z -- .`
  （`-- .` で `{DOCS}` の配下に限る）で分ける。
  - `{DOCS}` の配下の未コミットの変更が `{PREFIX}AI_INDEX.md` の1つだけ（状態の2文字は問わない）なら、次を尋ねる。
    > ⚠️ `{DOCS}` の pull に失敗しました（stderr: …）。
    > `{DOCS}` の配下の未コミットの変更は `AI_INDEX.md` だけです。AI_INDEX は close の最後に `{DOCS}` から作り直すので、手元の変更を捨ててかまいません。
    > 1. AI_INDEX.md の手元の変更を捨てて pull し直す（推奨）
    > 2. pull せずに続行する（C0-4 の競合検出を行わない）
    > 3. 中止する
    - 1.: `git -C {DOCS} cat-file -e HEAD:./AI_INDEX.md` が成功する（HEAD にある）なら
      `git -C {DOCS} checkout HEAD -- AI_INDEX.md`。HEAD に無いなら
      `git -C {DOCS} rm -q --cached --ignore-unmatch -- AI_INDEX.md` の後に `{DOCS}/AI_INDEX.md` を消す。
      その後に `git -C {DOCS} pull` し直す。成功なら Step C0-3 へ進み、失敗ならもう一度この (a)〜(c) に戻る
      （2回目は (c) の 1. を示さない。(a) に入ったら (a) の 1. は示す）。
  - 未コミットの変更が無い（ネットワーク・upstream の未設定等）か、`AI_INDEX.md` 以外の変更もあれば、
    「続行／中止」を尋ねる。
- (a) の `merge --abort`・(b) の `rebase --abort` が失敗したら、「続行／中止」を尋ねずに stderr を示して
  中止する（人が `{DOCS}` を直す。merge・rebase の途中のまま昇格を書き込まない）。
- 中止を選んだら、その時点で停止する。続行したときは（(a) の 1. で merge のコミットを作った場合を除き）
  `DOCS_PULL_FAILED` = true とする（C0-4 の競合検出を行わず、Step D に ⚠️ を出す）。

### 3. Pull Baseline into latest-specs/
Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-close/scripts/promote.py sync-baseline --cr {CR} --xddp-dir {XDDP_DIR} --docs {DOCS} --affected-repos {AFFECTED_REPOS をカンマ区切りで展開} {HAS_CROSS の場合は "--has-cross"}`
- スクリプトは先に `spec_changes.py record` で progress.md の「## 工程11 更新仕様書ファイル一覧」「## 工程11 削除した仕様書ファイル一覧」を
  作り直し（工程11 の後・close の前の人の編集も入る）、AFFECTED_REPOS・cross（HAS_CROSS）・system について、`{DOCS}` の写しのうち
  どちらの一覧にも無いファイルを latest-specs へ写す（今の CR が更新・削除したものを書き戻さない）。写したファイルは基準にも合わせる。
- stdout の JSON を `SYNC_RESULT` とする（`protected_files`・`deleted_files`・`copied_files`。パスは `latest-specs/…`）。
- 終了コードが0以外（基準が無い・壊れている、progress.md が無い等）の場合は stderr を表示し、Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py close-state --cr-path {CR_PATH} --state "⏸ 中断" --detail "Step C0-3: latest-specs の変更の記録に失敗（原因を解消後に /xddp-close {CR} を再実行）"`
  を実行して停止する。基準（`{CR_PATH}/.latest-specs-baseline.json`）が無い場合は工程11 を実行していない CR なので、
  「`/xddp-11-specs {CR}` を先に実行してください」と案内する（C0-3 の前は `{DOCS}` にも latest-specs にも書いていないので、再実行で続きからできる）。

### 4. Detect conflicts with concurrent CR promotions (human decision)

**PROTECTED_FILES・DELETED_FILES の取得:**
Let `PROTECTED_FILES` = `SYNC_RESULT.protected_files`、`DELETED_FILES` = `SYNC_RESULT.deleted_files`（progress.md を読み直さない）。
各エントリは `{XDDP_DIR}` からの相対パス（例: `latest-specs/{repo}/overview/architecture.md`）。
どちらも空なら Step C0-4 の残りをスキップして続行する。

**git pull で取り込まれた変更を使った競合検出:**
DOCS が git 管理されていない場合（Step C0-2 で git pull がスキップされた場合）、または `DOCS_PULL_FAILED` が
true の場合: 競合検出をスキップして続行。

Run `git -C {DOCS} diff --name-only --relative ORIG_HEAD HEAD`（`--relative` で DOCS からの相対パスが返る）.
(ORIG_HEAD は Step C0-2 の `git -C {DOCS} pull` によってセットされる。)
- このコマンドが失敗する場合、または ORIG_HEAD が存在しない場合（pull で何も取り込まれなかった場合）: 競合なしとみなしてスキップして続行。
- 注意: `ORIG_HEAD` は `git pull` 以外（`git merge`/`git rebase`/`git reset` 等）でも更新される。このコマンドは Step C0-2 の `git pull` 直後に連続実行することを前提としており、Step C0-2 内での連続実行設計によって stale な ORIG_HEAD 参照リスクを最小化する。

Let `PULLED_FILES` = git pull によって DOCS に取り込まれたファイルの一覧（DOCS ルートからの相対パス）。

**競合候補の特定:**
For each `F` in `PROTECTED_FILES` and `DELETED_FILES`:
  Convert F from `{XDDP_DIR}`-relative to DOCS-relative path using the promotion mapping:
    - `latest-specs/{repo}/{path}` → `{repo}/specs/{path}`
    - `latest-specs/cross/{path}`  → `cross/specs/{path}`
    - `latest-specs/system/{path}` → `system/specs/{path}`
  If the converted path is in `PULLED_FILES` → mark as "競合候補".

Collect the "競合候補" from `PROTECTED_FILES` into `OVERLAP_FILES`.
Collect the "競合候補" from `DELETED_FILES` into `DELETED_PULLED_FILES`（この CR が削除し、他の CR が更新して昇格したファイル。
C2 の削除候補に出るので、Step D でその行に「他の CR が更新」と注記する。ここでは尋ねない）。

If `OVERLAP_FILES` is empty: continue to Step C2 without prompting.

If `OVERLAP_FILES` is non-empty:
  Tell the user:
  > 以下のファイルは Step C0-2 の git pull 中に他の CR によって更新されており、今回 CR の変更と競合しています。
  >
  > | ファイル |
  > |---|
  > {for each file in OVERLAP_FILES: | `{file}` |}
  >
  > **A（現状維持で続行）:** 取り込まれた内容と今回 CR の変更がそのまま混在します。
  >   軽微な競合や今回 CR とは無関係なモジュールの変更であれば通常は A で問題ありません。
  >   「A」と入力してください。
  >
  > **B（xddp-11-specs を再実行してから続行）:** 最新の SPO・CHD・CRS を反映した仕様書に
  >   再生成します。完了後に `/xddp-close {CR}` を再実行してください。
  >   「B」と入力してください。

  Wait for user response.
  - A: continue to Step C2.
  - B: Run via Bash:
      `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py close-state --cr-path {CR_PATH} --state "⏸ 中断" --detail "Step C0-4: xddp-11-specs 再実行待ち"`
      instruct user to run `/xddp-11-specs {CR}` and then re-run `/xddp-close {CR}`; then stop.
  ※ xddp-close の再実行は Step C0-1（git fetch・DOCS_DIR sync）からやり直す設計（意図的）。再実行時に Step C0-4 を再度評価するが、直前に xddp-11-specs を実行済みであれば git pull で取り込まれる他 CR の変更は解消されているため A を選択して続行できる。

## Step C3.5, C3.6: Knowledge Capture

Step C3.5・C3.6（knowledge agent が rulebook・code-knowledge に書く）は、Step C2〜C7 の `promote.py run`（`{DOCS}` への写し）より前に行う。

Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py close-state --cr-path {CR_PATH} --state "🔄 進行中" --detail "Step C: 昇格処理中"`

Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-close/scripts/promote.py extract-ll --cr {CR} --lessons-file {XDDP_DIR}/lessons-learned.md --out {CR_PATH}/pending-items/LL-{CR}.md --repos-keys {REPOS_KEYS をカンマ区切りで展開} {IS_MULTI の場合は "--is-multi"}`

終了コードが 0 以外なら stderr を示し、Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py close-state --cr-path {CR_PATH} --state "⏸ 中断" --detail "Step C2 前: extract-ll 失敗（DOCS への昇格は未実施。原因を解消後に /xddp-close {CR} を再実行）"`
を記録してから停止する。

成功したら stdout の JSON の `unparsed` を Let `LL_UNPARSED`、`dropped` を Let `LL_DROPPED`、`unrouted` を Let `LL_UNROUTED`、`count` を Let `LL_CR_COUNT` とする（Step D で使う）。

Let `KNOWLEDGE_STARTED_AT` = output of `date +%s` (Bash), recorded immediately before the agent call.

**Agent tool** `subagent_type=xddp-close-knowledge-agent`:
```
CR_NUMBER: {CR}
CR_PATH: {CR_PATH}
WORKSPACE_ROOT: {WORKSPACE_ROOT}
XDDP_DIR: {XDDP_DIR}
DOCS: {DOCS}
REPOS_MAP: {REPOS_MAP}
AFFECTED_REPOS: {AFFECTED_REPOS}
HAS_CROSS: {HAS_CROSS}
IS_MULTI: {IS_MULTI}
TODAY: {TODAY}
CR_LESSONS_FILE: {CR_PATH}/pending-items/LL-{CR}.md
TRS_PATTERN: {CR_PATH}/10_test-results/{repo}/TRS-{CR}-*.md
OUTPUT_FILE: {CR_PATH}/pending-items/PENDING-KNOWLEDGE-{CR}.md
```

Wait for completion. エージェントは `_domain名要確認一覧`（_flows/_constants/_structures 生成時の暫定ドメイン名）を
OUTPUT_FILE に書き込む（人の命名確認待ち。内部で対話しない）。
オーケストレーターは Agent tool 完了後に `{CR_PATH}/pending-items/PENDING-KNOWLEDGE-{CR}.md` を Read し、
内容を Let `KNOWLEDGE_RESULT` に保持し、Step D で人に提示する。

Let `KNOWLEDGE_FAILED` = true if any of the following holds, otherwise false（前回の close のファイルが残っていても、今回の失敗を見落とさないように確かめる。ファイルは消さない）:
- the Agent tool ended with an error
- `{CR_PATH}/pending-items/PENDING-KNOWLEDGE-{CR}.md` does not exist
- its mtime（Bash: `stat -f %m` on macOS / `stat -c %Y` on Linux）is earlier than `KNOWLEDGE_STARTED_AT`
- its last non-empty line is not `## 完了`（エージェントの完了の印。途中まで書いて失敗した場合に無い）

`KNOWLEDGE_FAILED` が true でも Step C2〜C7 は続ける（rulebook だけを写さない）。

## Step C2, C3, C4, C5, C6, C7: Promote All Artifacts → DOCS_DIR

Step C3.5・C3.6 の後に実行する。

Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-close/scripts/promote.py run --cr {CR} --cr-path {CR_PATH} --xddp-dir {XDDP_DIR} --docs {DOCS} --repos-keys {REPOS_KEYS をカンマ区切りで展開} --affected-repos {AFFECTED_REPOS をカンマ区切りで展開} {HAS_CROSS の場合は "--has-cross"} {IS_MULTI の場合は "--is-multi"} --today {TODAY} --lessons-file {XDDP_DIR}/lessons-learned.md --output-file {CR_PATH}/pending-items/PENDING-PROMOTE-{CR}.md {KNOWLEDGE_FAILED が true の場合は "--skip-rulebooks"}`

`promote.py` は以下を OUTPUT_FILE に書き込む:
- `処理結果一覧（repo・cross・system・共通ファイル）`（AFFECTED_REPOS の各 repo・IS_MULTI なら cross・latest-specs/system があれば system・`{DOCS}` 直下の共通ファイル〔project-rulebook.md・improvement-backlog.md〕ごとに「成功／失敗（理由）／対象外」）
- `要確認LL一覧`（repo 欄が unknown か REPOS に無い値で Layer 2 に入れなかった今の CR の LL と理由）
- `Layer 2 と内容が違う LL（上書きしていない）`（Layer 2 に同じ ID があり本文が違う今の CR の LL）
- `` `{DOCS}` と内容が違う今の CR の IDEA（上書きしていない） ``（`{DOCS}/improvement-backlog.md` に同じ ID があり、close が書く部分が違う今の CR の IDEA）
- `同じ ID が2つ以上あるエントリ`（書いた・表を作り直した Layer 2 と `{DOCS}` の backlog）
- `破壊的変更フラグ・対象インタフェース一覧`（Step C2 の cross/ チェック結果）
- `project-rulebook の写し`（共通・repo 別・cross の rulebook ごとに「写した／DOCS から取り込んだ／同じ内容／無い（写していない）／競合（写していない）／失敗（理由）」。`--skip-rulebooks` のときは「見送り」。写しは前回 `{XDDP_DIR}` と `{DOCS}` をそろえたときの内容と比べ、両方が変わっていれば書かない〔競合〕）
- `削除候補一覧（ディレクトリ・ファイル）`（Step C2 の削除伝播。latest-specs から消えた repo モジュール・ユースケースのディレクトリと、
  工程11 の削除一覧のうち `{DOCS}` に写しのあるもの〔ディレクトリごと消えたものはディレクトリにまとめる〕。各行に種別。人の削除確認待ち）

改善バックログは `{DOCS}/improvement-backlog.md` を正とし、`{DOCS}` に無い ID の IDEA だけを足し込む（同じ ID は上書きしない）。
`promote.py` は削除確認を行わない（OUTPUT_FILE に保留事項として書き込むのみ）。
オーケストレーターは Bash 完了後に `{CR_PATH}/pending-items/PENDING-PROMOTE-{CR}.md` を Read し、
内容を Let `PROMOTE_RESULT` に保持し、Step D で人に提示する。

## Step D: Human Review Gate

Let `FAILED_TARGETS` = `PROMOTE_RESULT` の処理結果一覧で「失敗」と記録された対象（repo・cross・system・共通ファイル）のリスト。`KNOWLEDGE_FAILED` が true なら、`project-rulebook（knowledge agent の失敗）` も加える（rulebook を `{DOCS}` に写していないため）。
（この定義は Step E でも再利用する。Step D・Step E の2箇所で再定義しない）

Tell the user:
> ✅ クローズ処理が完了しました。内容を確認してください。
>
> **生成・更新した資料：**
> - 改善バックログ: `improvement-backlog.md`（今の CR の IDEA {INDEX_RESULT.cr_idea_count} 件。要確認IDEA: {k} 件）。ステータスの変更・取り消しは `{DOCS}/improvement-backlog.md` の §3 で行う（取り消しはエントリを消さずステータスを `❌ 却下` にする。消すと次の close で `{XDDP_DIR}` 側から足し込まれて戻る）
> - 知見ログ: `lessons-learned.md`（今の CR の LL {INDEX_RESULT.cr_ll_count} 件。今の CR として取り込み対象にした LL: {LL_CR_COUNT} 件。要確認LL: {k} 件）
{`PROMOTE_RESULT` の「処理結果一覧」を対象ごとに参照する（AFFECTED_REPOS を単純にループするのではなく、
実際の処理結果を確認する。一部の対象が失敗している場合は誤って成功と報告しないこと）:}
{for each {repo} in AFFECTED_REPOS: 処理結果一覧の {成功/失敗/対象外}:}
> - {repo}: {成功の場合} 仕様書 `{DOCS}/{repo}/specs/` / 変更要求仕様書（CRS） `{DOCS}/{repo}/crs/` / テスト `{DOCS}/{repo}/test/` / 知見 `{DOCS}/{repo}/knowledge/` に昇格
> - {repo}: {失敗の場合} ⚠️ 昇格処理に失敗しました（{失敗ステップ名・理由}）。内容を確認してください
{if IS_MULTI: 処理結果一覧の cross の行で書き分ける:}
> - cross: {成功の場合} {HAS_CROSS なら「仕様書・変更要求仕様書（CRS）・テストを `{DOCS}/cross/` に昇格（インタフェース破壊的変更: {PROMOTE_RESULT の破壊的変更フラグ}）／」}知見を `{DOCS}/cross/knowledge/` に昇格
> - cross: {失敗の場合} ⚠️ 昇格処理に失敗しました（{理由}）
{処理結果一覧の system・共通ファイルの行が「失敗」なら同じく ⚠️ と理由を示す}
>
> **project-rulebook の写し:**
> {PROMOTE_RESULT の「## project-rulebook の写し」をそのまま示す}
> {if KNOWLEDGE_FAILED:} ⚠️ knowledge agent が失敗したため、rulebook は写していません。`{XDDP_DIR}` の rulebook を確かめてから、`/xddp-close {CR}` をもう一度実行してください（写しは前回そろえたときの内容との比較で行う）。
> {for each rulebook whose action is `conflict`:}
> ⚠️ `{XDDP_DIR}/{file}` と `{DOCS}/{docs_file}` の両方が、前回そろえた後に変わっています（別の作業場所の close が先に写した等）。どちらも書き換えていません。
> {Bash: `"$PY" ~/.claude/skills/xddp-common/scripts/rulebook_files.py diff --xddp-dir {XDDP_DIR} --docs {DOCS} --file {file}` の出力。長いときは先頭の部分と、このコマンドを示す}
> 1. `{XDDP_DIR}` の側を正として `{DOCS}` に写す（`{DOCS}` の側の変更は、先に人が `{XDDP_DIR}` の側に取り込んでおく）
> 2. `{DOCS}` の側を正として `{XDDP_DIR}` に写す（この作業場所の変更は消える）
> 3. 今は何もしない（次の close でもう一度判定する）
>
> **要確認 LL（repo 欄が unknown か REPOS に無い値 — 昇格スキップ）:**
> {PROMOTE_RESULT の要確認LL一覧（理由つき）, or "なし"。Step C2〜C7 の `run` が実行されなかったときだけ、代わりに LL_UNROUTED を「{id}（repo: {repo}。{reason が unknown なら「unknown」、invalid なら「REPOS に無い値」}）」で示す}
> （`lessons-learned.md` のその LL の `**repo：**` 欄を REPOS のキーか、マルチリポジトリなら `cross` に直して `/xddp-close {CR}` を再実行すると昇格する）
>
> **見出し・CR 欄を読めない LL（rulebook・code-knowledge にも、Layer 2 の知見ログにも取り込まない）:**
> {LL_UNPARSED の各項目を「{id}（{reason が heading なら「見出しの書式」、unclosed-fence なら「コードブロックが閉じていない」、no-meta なら「メタ行なし」、multi-meta なら「別のエントリが混ざっている」}）」で並べた一覧, or "なし"}
> （「別のエントリが混ざっている」は、そのエントリの中の2つ目の `**CR：** …` 行のあたりに、見出しの崩れた別のエントリが混ざっている。混ざったエントリの見出しを `### LL-{CR}-{NN}：{タイトル}` に直す。
> 別のエントリが見当たらず、本文にメタ行の書式の行を書いているだけなら、その行を消すかコードブロック〔```` ``` ````〕で囲む。
> 「コードブロックが閉じていない」は、エントリの中の ```` ``` ```` を閉じる。
> 今の CR のエントリなら、`lessons-learned.md` の見出し `### LL-{CR}-{NN}：{タイトル}` と `**CR：** … ／ **工程：** … ／ **repo：** … ／ **タグ：** …` 行の書式を直して `/xddp-close {CR}` を再実行すると取り込まれる
> 〔再実行では、今の CR のエントリが既にあれば Step B・C は追記しない〕。または rulebook（`{XDDP_DIR}` 側。次の close で `{DOCS}` に写る）・knowledge に人が直接書く。
> クローズ済みの CR のエントリは書式を直しても取り込まれない〔一覧からは消える〕。必要なら rulebook（`{XDDP_DIR}` 側。次の close で `{DOCS}` に写る）・knowledge に人が直接書く）
>
> **取り込まなかった今の CR の LL の部分（その見出しの行から後ろは rulebook・code-knowledge にも、Layer 2 の知見ログにも取り込まない）:**
> {LL_DROPPED の各項目を「{id}（{reason が cr-meta なら「見出しの崩れた今の CR のエントリ」、cut なら「エントリの途中で切った」}）」で並べた一覧, or "なし"}
> （「見出しの崩れた今の CR のエントリ」は、`lessons-learned.md` でその見出しを `### LL-{CR}-{NN}：{タイトル}` に、メタ行を見出しの2行後に直す。
> 「エントリの途中で切った」は、コードをコードブロックで囲まずに書いた行〔例: `# …` のコメント行〕なら、そのコードを ```` ``` ```` で囲む。
> 理由は目安で、2つの崩れが重なると外れることがある。見出しの行から後ろを見て、本文のコードの行なら ```` ``` ```` で囲み、別のエントリなら見出しとメタ行を直す。
> どちらも直して `/xddp-close {CR}` を再実行すると取り込まれる〔再実行の注意は上と同じ〕。または rulebook（`{XDDP_DIR}` 側。次の close で `{DOCS}` に写る）・knowledge に人が直接書く）
>
> **内容が違うので上書きしなかった今の CR のエントリ（どちらを採るかは人が `{DOCS}` 側を直して決める）:**
> {PROMOTE_RESULT の「Layer 2 と内容が違う LL」と「`{DOCS}` と内容が違う今の CR の IDEA」, or "なし"}
>
> **同じ ID が2つ以上あるエントリ（どちらかの ID を直す）:**
> {INDEX_RESULT.duplicate_ids と PROMOTE_RESULT の「同じ ID が2つ以上あるエントリ」を「{id}（{file}）」で, or "なし"}
>
> **タグ一覧に無いタグ（タグ別インデックスに入らない。タグ一覧に足すかタグを直す）:**
> {INDEX_RESULT.unknown_tags を「{id}: {tag}」で, or "なし"}
>
> **書式を読めない IDEA（§1・§2 の表に正しく入らない）:**
> {INDEX_RESULT.bad_ideas を「{id}（{reason が table なら「項目の表の行が足りない」、status なら「ステータスが5つの値に無い」、heading なら「見出しの書式」、outside-section なら「§3 の外にある」}）」で, or "なし"}
>
> **要確認 IDEA（repo: unknown）:**
> {INDEX_RESULT.cr_unknown_repo_ideas, or "なし"}
>
> **削除候補（人の削除確認待ち）:**
> {PROMOTE_RESULT の削除候補一覧（各行に種別〔ディレクトリ／ファイル〕。`DELETED_PULLED_FILES` に当たる行には「⚠️ 他の CR が更新」）, or "なし"}
>
> **ドメイン名要確認（_flows/_constants/_structures の暫定ドメイン名）:**
> {KNOWLEDGE_RESULT の _domain名要確認一覧, or "なし"}
>
> **置き場所の確認が要る制約:**
> {KNOWLEDGE_RESULT の「## 置き場所の確認が要る制約」, or "なし"}
>
> **前回のクローズで書き、今回は書かなかった制約（不要なら `constraints.md` から直接消してください）:**
> {KNOWLEDGE_RESULT の「## 前回のクローズで書き、今回は書かなかった制約」, or "なし"}
>
> **昇格見送り（code-knowledge の昇格条件を満たさなかったもの）:**
> {KNOWLEDGE_RESULT の「## 昇格見送り一覧」, or "なし"}
>
> **rulebook に書かなかった LL（必要なら `{XDDP_DIR}` の rulebook に人が書く）:**
> {KNOWLEDGE_RESULT の「## rulebook に書かなかった LL」, or "なし"}
>
> {if DOCS_PULL_FAILED:}
> ⚠️ `{DOCS}` の pull に失敗したため、並行 CR の昇格との競合を確かめていません
>
> **修正が必要な場合：** 直接ファイルを編集してください（AI_INDEX.md は「クローズ完了」の後に `{DOCS}` から作り直すので、直さなくてよい）
>
> {if FAILED_TARGETS が空でない:}
> ⚠️ 上記のとおり一部の対象（{FAILED_TARGETS}）の昇格が失敗しています。「クローズ完了」と入力すると CR は失敗状態のまま完了マークされます。
> 可能であれば問題を解消し `/xddp-close {CR}` を再実行することを推奨します。
>
> 確認が完了したら「**クローズ完了**」と入力してください。

Wait for user to confirm.

For each `conflict` rulebook, if the user chose 1 or 2, run via Bash:
`"$PY" ~/.claude/skills/xddp-common/scripts/rulebook_files.py resolve --xddp-dir {XDDP_DIR} --docs {DOCS} --file {file} --take {1 なら xddp、2 なら docs}`
（3 なら何もしない）

ユーザーが削除を選択した削除候補（`PROMOTE_RESULT` の削除候補一覧より）について、
オーケストレーターが候補の種別に従ってディレクトリまたはファイルの削除をファイル操作として直接実行する（エージェントを再呼び出ししない）。

## Step D2: Rebuild AI_INDEX.md

Step D の「クローズ完了」と削除候補の削除の後に実行する（人が Step D で `{DOCS}` を直接直した分と、削除を AI_INDEX に入れる）。

Run via Bash（affected repos ではなく全 repo を渡す）:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/ai_index.py build --docs {DOCS} --repos-keys {REPOS_KEYS をカンマ区切りで展開} {IS_MULTI の場合のみ "--is-multi"}`

- 終了コード 0: Let `AI_INDEX_RESULT` = 成功。stdout の JSON の `archive_candidates` を Let `ARCHIVE_CANDIDATES` とする。
- 終了コードが 0 以外: Let `AI_INDEX_RESULT` = 失敗（stderr の1行目）。`ARCHIVE_CANDIDATES` = 空。
  close は止めない（AI_INDEX は `{DOCS}` から作り直せるので、次の close か `ai_index.py build` の再実行で直る）。

## Step E: Mark CR Complete

Read `{CR_PATH}/progress.md`.
`FAILED_TARGETS` は Step D（前述）で定義済みの値を再利用する（再定義しない）。
Append at the end:

```
## CR クローズ

- **クローズ日：** {TODAY}
- **改善バックログ（今の CR の IDEA）：** {INDEX_RESULT.cr_idea_count} 件（要確認: {k} 件）
- **知見ログ（今の CR の LL）：** {INDEX_RESULT.cr_ll_count} 件（要確認: {k} 件）
- **AI_INDEX.md：** {AI_INDEX_RESULT が成功なら "作り直し済み"／失敗なら "⚠️ 作り直しに失敗（{stderr の1行目}）。`ai_index.py build` を再実行してください"}
- **ステータス：** {if FAILED_TARGETS が空: "✅ 完了・クローズ済み"}{if FAILED_TARGETS が空でない: "⚠️ 完了・クローズ済み（{FAILED_TARGETS} の昇格が未完了。`{DOCS}` の該当する場所の問題を解消して `/xddp-close {CR}` を再実行することを推奨）"}
```

## Step F: Report in Japanese

Report: IDEA/LL entries added per repo, main lesson titles, breaking-change alerts (if any).

If `AI_INDEX_RESULT` is 失敗: show stderr and the command to re-run（Step D2 と同じコマンド）.

If `ARCHIVE_CANDIDATES` is not empty, add:
> **AI_INDEX.md が500行を超えています（アーカイブ候補）:**
> | 節 | キー | CR | ファイル（`{DOCS}` からの相対パス） |
> |---|---|---|---|
> {ARCHIVE_CANDIDATES の各要素の `section`・`key`・`cr`・`file`（返された順）}
>
> AI_INDEX は `{DOCS}` から作り直すので、行だけを消しても戻ります。行を減らすには、該当するファイルを `{DOCS}/_archive/{元の相対パス}` 等の、AI_INDEX と工程2 が読まない場所へ移してから `ai_index.py build` を再実行してください（自動では移しません）。
