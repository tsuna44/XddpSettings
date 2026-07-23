---
description: XDDP 上位反映: arch/design/test/code 成果物の現在の内容（人が直接編集した内容、/xddp.sync-design 適用後の最新状態、または人がコードを直接修正した内容）を変更要求仕様書（CRS）に反映する。code の場合はコード差分から該当CHDバッチファイルを先に同期してから反映する。「上位仕様書に反映して」「CRSにフィードバックして」「コード修正をCHDに反映して」などで起動する。
argument-hint: "[CR番号] arch|design|test|code [repo名]"
---

You are executing **XDDP Feedback — Reflect Manually-Edited Artifacts Back to CRS**.

> This is an opt-in, on-demand command. It is NOT meant to run after every `/xddp.review` —
> only when the human has decided that accumulated manual edits are ready to be pushed
> upstream. Extract candidates, then let the human exclude any that shouldn't be reflected.
> For `DOC_TYPE: code`, the human has just fixed code directly (including bug fixes made while
> debugging a test failure) — this command first syncs the affected CHD batch file(s) from the
> code diff, then reuses the same CRS-feedback flow as `design`.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) DOC_TYPE [repo]
- DOC_TYPE: `arch` | `design` | `test` | `code`（省略時はユーザーに確認）
- repo（省略可）: 省略時は
  `AFFECTED_REPOS`（マルチリポジトリの場合は全リポジトリ）を対象に一括処理する
  （`xddp.05.arch`/`xddp.06.design` の Step C が per-repo + cross を1つの `FEEDBACK_ITEMS`
  に統合する設計と同一。単一のCR実行で複数repoの反映漏れをまとめて拾えるようにするため）。
  指定時はそのrepoのみに絞り込む。

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS
  → let `CR`, `REST_ARGS`.
Let `DOC_TYPE` = first token of `REST_ARGS`. If omitted: ask the user.
If `DOC_TYPE` が `arch` / `design` / `test` / `code` のいずれでもない場合: report error
  `"DOC_TYPE '{DOC_TYPE}' は不正です。arch / design / test / code のいずれかを指定してください。"`
  and stop.（`REPO_ARG` の不正値エラー〔後述〕と対称。不正値が「工程未実施」という誤解を招く
  エラーに落ちるのを防ぐ）
Let `REPO_ARG` = second token of `REST_ARGS`（`DOC_TYPE` の次のトークン）。存在しない場合は空文字。
Let `TODAY` = today's date.
(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR, REPOS_MAP, REPOS_KEYS, IS_MULTI.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve Affected Repos" with:
  REPOS_KEYS: {REPOS_KEYS}, IS_MULTI: {IS_MULTI}, CR_PATH: {CR_PATH}, FILTER_BY_SPO: false
→ let `AFFECTED_REPOS`（この時点では `REPOS_KEYS` の全コピー。`xddp.common`「## Resolve Affected
  Repos」自体は `repo` を Input として受け取らない設計のため、絞り込みは呼び出し元である
  本スキル側で以下のとおり明示的に行う）。

If `REPO_ARG` is non-empty:
  If `REPO_ARG` not in `REPOS_KEYS`: report error
    `"指定された repo '{REPO_ARG}' は xddp.config.md の REPOS: に存在しません。有効な repo: {REPOS_KEYS}"`
    and stop.
  Else: overwrite `AFFECTED_REPOS` = `[REPO_ARG]`（単一要素に絞り込む）。
Else: `AFFECTED_REPOS` はそのまま（全リポジトリ）を使う。

`DOC_TYPE = code` の場合、cross/ は対象外とする（コード変更は個別リポジトリに対して行われるもので
あり、cross/ は仮想リポジトリのためgit diffの対象にならない。`xddp.sync-design/SKILL.md` がそもそも
cross/を扱わない設計であるのと同一方針）。`HAS_CROSS` 判定・cross処理は `DOC_TYPE = code` の
分岐では一切行わない。

## Step 1: Resolve target files per DOC_TYPE

`DOC_TYPE = code` の場合は本Stepのテーブルを使わず「## Step 1-code」を適用する（TARGET_FILEが
静的パスではなくgit diffから動的に決定されるため、テーブル形式の解決ロジックとは構造が異なる）。
`arch` / `design` / `test` は以下のテーブルの通り。

For each `{repo}` in `AFFECTED_REPOS`:

| DOC_TYPE | TARGET_FILES（{repo}） | cross（HAS_CROSSの場合のみ追加） |
|---|---|---|
| `arch` | `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-rev*.md` が存在する場合は最大番号のrevファイル（`/xddp.sync-design` 適用後の最新状態を優先）。存在しない場合: `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md`（存在すれば）または `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-A.md` | `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md` |
| `design` | Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with: `CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}` → let `CHD_CONTENT_FILES`（全UR内容ファイル。`xddp.06.design/SKILL.md`「## Step C': Generate Traceability Matrix (TM)」冒頭の `Discover CHD Files` 呼び出しと同一の呼び出し規約） | `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` |
| `test` | `{CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md` | `{CR_PATH}/09_test-spec/cross/TSP-{CR}-cross.md` |

HAS_CROSS 判定: Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve HAS_CROSS" with
  IS_MULTI: {IS_MULTI}, ARTIFACT_PATH: {DOC_TYPE に対応する cross ファイルパス}
→ let `HAS_CROSS`.

いずれの TARGET_FILE も存在しない場合: 該当工程が未実施であることを報告し停止する。

## Step 1-code: Sync CHD from code diff (DOC_TYPE = code only)

このStepは `DOC_TYPE = code` の場合のみ実行し、完了後は「## Step 2」（design と同一の抽出ロジック）
に合流する。それ以外の `DOC_TYPE` はこのStep全体をスキップする。

### Step 1-code-a: Collect code diff

Run: `git -C {WORKSPACE_ROOT} diff HEAD` → let `GIT_DIFF`
（`xddp.sync-design/SKILL.md`「## Step 2: Collect code context」冒頭の取得方法・同一の空diff時
ガード（Ask分岐）を適用する）

If `GIT_DIFF` is empty:
  Report: "⚠️ git diff HEAD が空です（ワーキングツリー・インデックスに HEAD 比較の差分なし）。"
  Ask human: "続行しますか？コミット済みの変更を対象にする場合は続行を選択してください
    （`CHANGE_SUMMARY` は Step 1-code-c で GIT_DIFF の変更ファイル一覧から自動生成されます）。
    コミット前の状態からやり直す場合は「いいえ」を選択してください。"
  If No: Stop.

Let `CHANGED_FILES_MAP` = {}（repo → 変更ファイル一覧）
Let `REPO_DIFF_MAP` = {}（repo → diff抽出）
For each `{repo}` in `AFFECTED_REPOS`:
  Let `CHANGED_FILES_MAP[{repo}]` = GIT_DIFF から `{REPOS_MAP[{repo}]}` 配下の変更ファイル一覧
  Let `REPO_DIFF_MAP[{repo}]` = GIT_DIFF から `{REPOS_MAP[{repo}]}` 配下の差分のみ抽出
Let `AFFECTED_REPOS` = `{repo for repo in AFFECTED_REPOS if REPO_DIFF_MAP[{repo}] is not empty}`
（`xddp.sync-design/SKILL.md`「## Step 2: Collect code context」末尾の `AFFECTED_REPOS` 絞り込み
（`REPO_DIFF_MAP` が空でないrepoのみ残す）と同一のロジック。冒頭で `REPO_ARG` により単一repoへ
絞り込み済みの場合はその1repoのみが対象になる）
If `AFFECTED_REPOS` is empty:
  Report: "⚠️ いずれのリポジトリにも差分が検出されませんでした。"
  Stop.

### Step 1-code-b: Map changed files to CHD batch files

Let `NORMALIZE(path)` = 本Step内でのみ使用する内部ヘルパー関数。次の順で正規化する:
  1. 先頭の `./` を除去する
  2. パス区切り文字を `/` に統一する
  3. 末尾のスラッシュを除去する
  4. `{REPOS_MAP[{repo}]}` を基点とした相対パスに変換する（絶対パス表記・リポジトリルート基点の
     相対パス表記など、記法の違いを吸収するため）
変更ファイルとCHD Section 4「変更ファイル」列の突合は、素の文字列一致ではなくこの正規化後の値で行う。
相対パス基点の違いや先頭`./`の有無による偽陰性を防ぐ。

For each `{repo}` in `AFFECTED_REPOS`:
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
    CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
  → let `ALL_CHD_FILES`.
  If `ALL_CHD_FILES` is empty:
    Report: "⚠️ {repo}: CHDが見つかりません。先に /xddp.06.design {CR} を実施してください。"
    Skip this repo（以降のStep 1-code-b2以降の対象から除く）.

  Let `AFFECTED_CHD_FILES_MAP[{repo}]` = []（このrepoで同期対象となるCHDバッチファイルのリスト）
  Let `UNMATCHED_FILES_MAP[{repo}]` = []（どのCHDにも対応しない変更ファイルのリスト。正規化一致・
    ベースファイル名一致のいずれも成立しなかったもの）
  Let `PROBABLE_MATCHES_MAP[{repo}]` = []（正規化後も完全一致しないが、ベースファイル名が一致した
    ため「候補」として人の確認を要する変更ファイルのリスト。各要素は `{cf, 候補CHDファイル一覧}`）

  Let `NORMALIZED_CHANGED_SET` = `CHANGED_FILES_MAP[{repo}]` の各要素を `NORMALIZE()` した集合。

  For each `{file}` in `ALL_CHD_FILES`:
    Read `{file}` Section 4（SP→変更ファイル→変更シンボル）。「変更ファイル」列の値を `NORMALIZE()`
    した集合として抽出する。
    If この集合と `NORMALIZED_CHANGED_SET` に1件以上の重複がある:
      Append `{file}` to `AFFECTED_CHD_FILES_MAP[{repo}]`.

  For each `{cf}` in `CHANGED_FILES_MAP[{repo}]`:
    If `NORMALIZE({cf})` がいずれの `ALL_CHD_FILES` の正規化済みSection 4 集合にも出現しない:
      **フォールバック:** `{cf}` のベースファイル名（パス区切りの最後の
      要素）が、いずれかの `ALL_CHD_FILES` のSection 4記載パスのベースファイル名と一致するか確認する。
      If 一致する候補が1件以上ある:
        Append `{cf, 一致した候補CHDファイル一覧}` to `PROBABLE_MATCHES_MAP[{repo}]`
        （`AFFECTED_CHD_FILES_MAP` へは自動追加しない。誤って本文と無関係な同名ファイルを採用する
        リスクを避けるため、Step 1-code-b2 で人に確認を求める）。
      Else:
        Append `{cf}` to `UNMATCHED_FILES_MAP[{repo}]`.

  If `AFFECTED_CHD_FILES_MAP[{repo}]` と `PROBABLE_MATCHES_MAP[{repo}]` がともに空
  （そのrepoの変更が既存CHDのどのSPにも該当しない場合）:
    Skip this repo（以降のStep 1-code-b2以降の対象から除く）.

If 全repoで `AFFECTED_CHD_FILES_MAP[{repo}]` と `PROBABLE_MATCHES_MAP[{repo}]` がともに空:
  Report: "⚠️ 変更ファイルに対応するCHDエントリが見つかりませんでした。同期対象がありません。"
  （`UNMATCHED_FILES_MAP` の内容を合わせて表示する）
  Stop.

### Step 1-code-b2: Confirm probable-match candidates

`PROBABLE_MATCHES_MAP` に1件以上のrepoが該当する場合のみ実行する。全repoで空の場合はこのStepを
スキップし、直接 Step 1-code-b3 へ進む。

Show:
| repo | 変更ファイル | ベースファイル名が一致した候補CHDファイル |
|------|------------|---------------------------------|
（`PROBABLE_MATCHES_MAP` の全エントリを列挙）

Ask: "上記はパスの表記が完全一致しないため自動採用していません。対象に含める組み合わせを
番号で指定してください（含めない場合は何も指定しないでください）。"

指定された組み合わせについて:
  Let `CONFIRMED_PROBABLE_MAP[{repo}][{候補CHDファイル}]` に `{cf}` を追加する。
  `{候補CHDファイル}` が `AFFECTED_CHD_FILES_MAP[{repo}]` に含まれていない場合は追加する。
指定されなかった組み合わせは `UNMATCHED_FILES_MAP[{repo}]` に `{cf}` を追加する
（Step 1-code-e で他の未対応ファイルと合わせて警告表示するため）。

### Step 1-code-b3: Scale warning

Let `TOTAL_AFFECTED_FILES` = 全repoの `AFFECTED_CHD_FILES_MAP[{repo}]` の合計件数
（Step 1-code-b2で追加された分も含む）。

If `TOTAL_AFFECTED_FILES > 5`（閾値。`xddp.06.design/SKILL.md` Step A-scale の
`TOTAL_SP_COUNT > 50` 警告と同一の「オーケストレーター側での事前警告」パターンを踏襲する）:
  Show: "⚠️ この変更は{TOTAL_AFFECTED_FILES}件のCHDバッチファイルにまたがります。"
  （repo・file の一覧を表示する）
  Ask: "まとめて同期しますか？（大規模な横断的修正の場合、個別に確認しながら進めることを推奨します）"
  If 続行しない: Report: "対象を絞り込んで再実行してください（例: repo引数を指定する、
    コミットを分割してから再実行する）。" Stop.
  If 続行する: そのまま Step 1-code-c へ進む。
Else: 警告なしでそのまま Step 1-code-c へ進む。

### Step 1-code-c: Regenerate affected CHD batch files（ステージングファイルへ書き込み）

対象ファイルへの直接上書きは行わず、`{file}.pending`
（元のファイル名全体に `.pending` を付与したパス。例: `CHD-{CR}-UR-01.md` → `CHD-{CR}-UR-01.md.pending`）
という一時ステージングファイルに書き込む。`xddp.common`「## Discover CHD Files」は
`CHD-{CR}.md` インデックスの「## 2. UR別ファイル一覧」テーブルに登録されたパスのみを
`CHD_CONTENT_FILES` として返す方式であり（`*.md` グロブ走査ではない）、`.pending` ステージング
ファイルはこのインデックステーブルに登録されないため一切拾われない
— つまり、承認が確定するまで `07.code`・`09.test`・TM生成等の既存スキルからはこのステージング
ファイルは見えない。Step 1-code-e で人が承認した場合のみ、ステージングファイルの内容を対象
ファイルへ反映（コピー後にステージングファイルを削除）する。非承認の場合は対象ファイルを一切
変更せず、ステージングファイルは次回実行時の参考として残す（Step 1-code-e参照）。

For each `{repo}` in `AFFECTED_REPOS`（`AFFECTED_CHD_FILES_MAP[{repo}]` が非空のもののみ）:
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Load Steering Context" with:
    XDDP_DIR: {XDDP_DIR}, REPO_NAME: {repo}
  → let `RULEBOOK_CONTEXT`.

  For each `{file}` in `AFFECTED_CHD_FILES_MAP[{repo}]`:
    Let `PENDING_FILE` = `{file}.pending`
    Let `FILE_CHANGED_SET` = (`CHANGED_FILES_MAP[{repo}]` のうち `{file}` の正規化済みSection 4に
    出現するものの集合) ∪ (`CONFIRMED_PROBABLE_MAP[{repo}][{file}]`。Step 1-code-b2で人が確認した
    候補があれば含める)
    （このバッチファイルのスコープに関係する変更ファイルのみに絞り込む。1つの変更ファイルが
    複数のバッチファイルのSection 4にまたがる場合、該当する各バッチファイルの呼び出しにその都度
    含まれる — 1つの変更が複数SPにまたがる設計であるため二重処理ではなく正しい挙動）
    Let `FILE_DIFF` = `REPO_DIFF_MAP[{repo}]` から `FILE_CHANGED_SET` に該当する部分のみ抽出

    **Agent tool** `subagent_type=xddp-chd-sync-agent`:
    ```
    CR_NUMBER: {CR}
    REPO_NAME: {repo}
    CURRENT_CHD_FILE: {file}
    CHANGED_FILES: {FILE_CHANGED_SET}
    REPO_DIFF: {FILE_DIFF}
    CRS_FILE: {`{CR_PATH}/03_change-requirements/CRS-{CR}.md` if exists, else ""}
      （`xddp.sync-design/SKILL.md`「## Step 2: Collect code context」内 `CRS_FILE_MAP` と同一の
      存在チェック＋空文字フォールバック方式。`xddp-chd-sync-agent.md` の Inputs 説明・Process 4
      「If `CRS_FILE` is non-empty: read it」は非空/空の両方を前提とした契約であるため、
      呼び出し元もこれに合わせる）
    OUTPUT_FILE: {PENDING_FILE}（ステージングファイル。{file} 本体はStep 1-code-eの承認まで変更しない）
    CHANGE_SUMMARY: {REST_ARGSに変更サマリの指定があれば使用。なければGIT_DIFFの変更ファイル一覧
      から自動生成（xddp.sync-design/SKILL.md「## Step 2: Collect code context」の
      `CHANGE_SUMMARY` 自動生成と同一方針）}
    RULEBOOK_CONTEXT: {RULEBOOK_CONTEXT}
    TODAY: {TODAY}
    ```

### Step 1-code-d: AI review of synced CHD

For each `{repo}` in `AFFECTED_REPOS`, for each `{file}` in `AFFECTED_CHD_FILES_MAP[{repo}]`:
  Let `PENDING_FILE` = `{file}.pending`
  Let `FILE_NAME` = basename of `{file}`（例: `CHD-{CR}-UR-01.md`、`CHD-{CR}-UR-01-2.md`。
    `xddp.06.design/SKILL.md`「## Step A: Generate per-repo Change Design Documents (UR×バッチ単位)」の
    `FILE_NAME` 命名規則 `CHD-{CR}-{UR-ID}.md` / `CHD-{CR}-{UR-ID}-{N}.md` により
    生成されたファイル名）
  Let `REMAINDER` = `FILE_NAME` から先頭の固定文字列 `CHD-{CR}-`（`{CR}` は実行時に確定済みの
    具体値、例 `CR-2026-900`）と末尾の `.md` を除去した残り（`{CR}` 自体がハイフンを含みうるため、
    固定文字列としてのプレフィックス一致で除去する。正規表現的な曖昧一致は行わない）
  If `REMAINDER` が `UR-\d+-\d+` のパターンに一致する（末尾がハイフン+数字のみのマルチバッチ
  サフィックス）:
    Let `UR-ID` = 末尾の `-\d+` を除いた部分、`{N}` = 末尾の数字部分。
  Else（`REMAINDER` が `UR-\d+` のみに一致する単一バッチファイル）:
    Let `UR-ID` = `REMAINDER`、`{N}` は使用しない。
  Let `REVIEW_FILE` = `{CR_PATH}/06_design/{repo}/review/06_design-review-{UR-ID}[-{N}].md`
  （既存のdesignレビューファイルと同一パスを再利用する。`xddp.06.design/SKILL.md`
  「## Step B: Review Loop (up to `REVIEW_MAX_ROUNDS.CHD` rounds)」の Review Loop 呼び出しに
  おける `REVIEW_OUTPUT_FILE` と同一の命名規則。既存ファイルがあれば追記ラウンドとして扱う）

  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Invoke Reviewer" with:
    DOCUMENT_TYPE: CHD, TARGET_FILE: {PENDING_FILE},
    REFERENCE_FILES: [{file}（変更前の内容との比較用）, {CR_PATH}/03_change-requirements/CRS-{CR}.md],
    REVIEW_ROUND: {既存レビューファイルがあれば記載されている最終ラウンド+1、なければ1}, OUTPUT_FILE: {REVIEW_FILE}

### Step 1-code-e: Human approval gate

Show:
| repo | 同期済みファイル（ステージング） | レビュー判定 |
|------|--------------------------------|------------|
（`AFFECTED_REPOS` × `AFFECTED_CHD_FILES_MAP` ごとに repo / `{file}.pending` / 🔴件数・🟡件数 を列挙）

`UNMATCHED_FILES_MAP` に該当ファイルがあるrepoについては、あわせて次を表示する:
> ⚠️ {repo}: 以下の変更ファイルはどのCHDにも対応するSPエントリが見つかりませんでした。
> 設計外の変更である可能性があります: {UNMATCHED_FILES_MAP[{repo}]}

Ask: "上記のCHD同期内容（ステージングファイル）を承認しますか？承認するとステージングファイルの
内容が対象CHDファイルへ反映されます。"
If 承認:
  For each 承認された `{file}`:
    ステージングファイル `{file}.pending` の内容を `{file}` へコピーして反映し、
    `{file}.pending` を削除する。
    xddp-chd-sync-agent の報告（Section 3.7 Process手順8）に「該当変更」列の変更が必要との
    指摘があれば、CHD index file（`CHD-{CR}.md`、当該repo）の該当行を更新する
    （`xddp.06.design/SKILL.md`「## Step A: Generate per-repo Change Design Documents
    (UR×バッチ単位)」末尾の「該当変更」列自己申告更新規約を、承認後のこのタイミングで適用する）。
  Let `TARGET_FILES` = `AFFECTED_CHD_FILES_MAP` の全repoの全ファイルの和集合
  （以降「## Step 2」の `DOC_TYPE = design` 相当の処理へ合流する。3.1 Step 2 の追記を参照）
If 非承認:
  対象CHDファイル本体（`{file}`）は変更しない。ステージングファイル（`{file}.pending`）は
  参考用として残す（次回 `/xddp.feedback {CR} code` 実行時、同一ファイルが再度対象になれば
  Step 1-code-cで上書きされる。手動で内容を確認・流用したい場合は `{file}.pending` を直接
  参照できる）。
  Report: "修正後に再度 `/xddp.feedback {CR} code` を実行してください。ステージングファイルは
  `{CR_PATH}/06_design/{repo}/` 配下に `.pending` として残っています。"
  Stop.
（`xddp.sync-design/SKILL.md`「## Step 5: Report and request approval」と同一のUXパターンを
踏襲しつつ、対象ファイル本体への反映タイミングを承認後に遅らせている点が異なる —
ステージングファイル方式（本ファイル Step 1-code-c 参照）の核心）

## Step 2: Extract items not yet reflected in CRS

Read all TARGET_FILES（per-repo + cross）と `{CR_PATH}/03_change-requirements/CRS-{CR}.md`。
`DOC_TYPE = code` の場合、`TARGET_FILES` は Step 1-code-e で確定した `TARGET_FILES`（cross は
含まない。Step 1-code-a参照）を用いる。

**スコープの違い（注意）:** `design` は当該repoのCHD全ファイル（`Discover CHD Files` が返す
`CHD_CONTENT_FILES` 全件）を走査するのに対し、`code` は今回のコード差分が実際に触れたCHD
バッチファイルのみが対象となる。そのため `/xddp.feedback {CR} code` を実行しても、今回のコード
変更と無関係な既存のCHD未反映項目（例: 別の機会に人手編集されたが未反映のまま残っている項目）は
拾われない。網羅的にCRS未反映項目を洗い出したい場合は別途 `/xddp.feedback {CR} design` を
実行すること。

**DOC_TYPE = arch / design / code の場合:**
`xddp.05.arch/SKILL.md` Step C・`xddp.06.design/SKILL.md` Step C と同一の抽出ロジックを適用する。
CRSにまだ反映されていない項目（新規制約・NF要求・I/F仕様・エラー条件・スコープ外化項目）を
`FEEDBACK_ITEMS` として抽出する。各アイテムは:
`種別: {追加UR/追加SR/追加SP/廃止SR/廃止SP} | 内容: ... | 根拠: {DSN/CHD} §X [{repo}][cross]`
（`DOC_TYPE = code` の場合、根拠列は Step 1-codeで同期済みのCHD内容を指すため `CHD §X` を用いる。
Step 1-code自体でCHDが最新化されているため、抽出対象は `design` と全く同一の内容になる）

**DOC_TYPE = test の場合（対象範囲を以下に限定する）:**
TSPの前提条件・期待値の記述から、**CRS（SP一覧）に明記されていない仕様レベルの要求・制約**
（＝CRSに新規SP/SRとして計上できるもの）が読み取れる場合のみ対象とする。
**通常のテストケース追加・境界値パターンの拡充など、既存仕様の範囲内のテスト精緻化は対象外。**
各アイテムは arch/design と同一の種別のみを使う: `種別: {追加UR/追加SR/追加SP} | 内容: ... | 根拠: TSP §X [{repo}][cross]`

**スコープ外の明示:** TSPが明らかにする不足が「CRSのSPは十分だがCHDの確認項目の記載が
漏れているだけ」の場合（＝CRSレベルでは既存SPの範囲内、CHDレベルの記述漏れに過ぎない場合）は
本コマンドの対象外とする。「確認項目」（`06_change-design-document-template.md` の
「## 7. 確認項目（テスト観点）」見出し）はCHD固有の概念でありCRSのUSDM構造（UR/SR/SP）に
対応要素がないため、`種別: 追加確認項目` のような専用種別は設けない
（CHDへの反映は `/xddp.06.design` 実行中の人レビューゲートで人が直接追記するか、
`DOC_TYPE = code` によるコード起点の同期で行う。この2つの経路が揃ったため、CHDへの反映手段が
存在しないという初版時点の制約は本改訂で解消された）。

`FEEDBACK_ITEMS` が空の場合（`DOC_TYPE` で分岐する）:
- `DOC_TYPE` が `arch` または `test` の場合: 「反映すべき未反映項目は見つかりませんでした」と
  報告してコマンド全体を終了する。
- `DOC_TYPE` が `design` または `code` の場合: 「CRSへ反映すべきテキスト形式の未反映項目は
  見つかりませんでした。CHD→TM再生成・CRS Section 3.1 の更新のみ実行します」と報告した上で、
  Step 3・Step 4・Step 6・Step 7 をスキップし Step 5 へ直接進む（Step 5 見出し「再生成・更新」と
  同じ表現に統一する — Step 5 は TM-{CR}.md の書き出し・CRS Section 3.1 の in-place 更新を伴う
  ファイル変更処理であり、「整合性チェックのみ」という表現は用語上ずれるため使わない）。
  これは `xddp.06.design/SKILL.md`「## Step C': Generate Traceability Matrix (TM)」が
  Step C の `DESIGN_FEEDBACK` 有無と無関係に常に実行される「無条件実行」の性質を再現するための
  分岐であり、CHD Section 4（SP→変更ファイル対応表）のみが人手更新（または`DOC_TYPE=code`による
  コード起点更新）されテキストレベルの新規制約がないケースでも TM再生成・CHD未対応SP警告等を
  見落とさないようにする。`code` を `design` と同一分岐にするのは、Step 1-code完了時点でCHDは
  常に最新化されており、Step 2以降の処理内容が`design`と完全に一致するため（3.1 Step 2冒頭の
  「DOC_TYPE = arch / design / code の場合」参照）。

## Step 3: Human confirmation gate

`FEEDBACK_ITEMS` を番号付きで一覧表示する。

Ask: "以下の項目を CRS へ反映します。よろしいですか？（反映不要な項目があれば番号で除外を指示してください）"
（`xddp.revise/SKILL.md`「## 2. Load review items」内の確認プロンプトと同じUX）

除外指定があれば `FEEDBACK_ITEMS` から該当項目を除く。残りが空になった場合
（Step 2 の空判定と同一の理由・同一の分岐）:
- `DOC_TYPE` が `arch` または `test` の場合: 反映処理をスキップしコマンド全体を終了する。
- `DOC_TYPE` が `design` または `code` の場合: 「CRSへ反映するテキスト形式の項目はすべて除外
  されました。CHD→TM再生成・CRS Section 3.1 の更新のみ実行します」と報告した上で、Step 4・
  Step 6・Step 7 をスキップし Step 5 へ直接進む（Step 2 側の早期終了分岐と同種の状態メッセージを
  出し、除外操作の結果として何が続行されるかを利用者に明示する。`code` を `design` と同一分岐に
  する理由はStep 2末尾の注記と同一）。

## Step 4: Feed into CRS

**Agent tool** `subagent_type=xddp-spec-writer-agent`:
```
CR_NUMBER: {CR}
MODE: update-design
CRS_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md
DESIGN_FEEDBACK: {確認後の FEEDBACK_ITEMS}
TODAY: {TODAY}
AUTHOR_NOTE: {DOC_TYPE}成果物の人手修正内容を反映（xddp.feedback）
```

## Step 5: Regenerate TM（DOC_TYPE = design / code のみ）

**実行条件:** `DOC_TYPE = design` または `code` の場合、このステップは Step 2/Step 3 でテキスト
形式の `FEEDBACK_ITEMS` が空になった場合や Step 4 がスキップされた場合でも必ず実行する
（Step 2/Step 3 の分岐を参照）。TM再生成・CHD未対応SP警告等はCRSへのテキスト反映（Step 4）の
成否と無関係に独立して実行される、`xddp.06.design`「## Step C': Generate Traceability Matrix (TM)」
と同じ「無条件実行」の処理だからである。`code` の場合、Step 1-codeでCHD Section 4が更新されている
可能性が高く、TM再生成の実施価値は `design` の場合と同等以上に高い。

`xddp.06.design/SKILL.md`「## Step C'」のうち、以下の範囲を同一の処理として適用する:
- **適用する:** 見出し直後のコメント注記・progress.md書き込み行を除いた本文（`For each {repo} in
  AFFECTED_REPOS:` のCHD走査ループから、太字ラベル `**CRS TM Section 3.1 の「設計」「実装」列を
  更新する**` の内容まで。TM-{CR}.md書き出し・CRS Section 3.1 更新ロジックのみで構成される、
  progress.md への言及を含まない純粋なTM/CRS処理範囲）
- **適用する:** 太字ラベル `**警告の出力**` のブロック（「CHD未対応SPの警告」「SP間ファイル衝突の
  警告」「未実装SRの警告」の3種）
- **適用しない:** 見出し `## Step C'` 直後のコメント注記と `progress.md` 6b詳細ステップ更新行
  （処理指示ではない、または `/xddp.06.design` 固有のprogress.md書き込みのため。特に後者の
  `progress.md` 6b詳細ステップ更新行は見出し直後のコメント注記に紛れて見落としやすいため、
  複製実装時は見出し直下の2行〔コメント注記＋progress.md書き込み〕をまとめて対象外とすることを
  意識して確認すること）
- **適用しない:** 太字ラベル `**progress.md の 成果物 列を更新**` のブロック
  （`/xddp.06.design` 固有のprogress.md書き込みのため）
- **適用しない:** 末尾の「Tell the user」ブロック（`/xddp.06.design` 自身の完了報告。
  `xddp.feedback` は Step 8 で独自の完了報告を行うため、この重複する報告文言は適用しない）

（重複コード。変更時は両ファイルの該当ブロックを grep して同期させること。
`ARCH_AGENT_PATHS` 等が確立した本リポジトリの `_BASE` 系複製規約に倣う。
上記「適用しない」3ブロックの選定根拠、および `**警告の出力**` ブロックのみ複製する理由:
docs/adr/ADR-0007-feedback-design-excluded-blocks.md）

DOC_TYPE = arch / test の場合はこのステップをスキップする（`code` はスキップしない。上記実行条件参照）。

## Step 6: Regenerate CRS Excel

Step 4 で CRS が更新された場合のみ、Read `~/.claude/skills/xddp.common/SKILL.md`,
apply "## Regenerate CRS Excel" with: CR_PATH: {CR_PATH}, CR: {CR}

## Step 7: Follow-up AI review of updated CRS

Step 4 で CRS が更新された場合のみ実行する（Step 6 と同一のガード条件。Step 3 で全項目除外され
`FEEDBACK_ITEMS` が空になった場合はStep 4自体がスキップされるため、その場合はStep 6同様
Step 7も実行しない）。

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Invoke Reviewer" with:
  DOCUMENT_TYPE: CRS, TARGET_FILE: {CR_PATH}/03_change-requirements/CRS-{CR}.md,
  REFERENCE_FILES: {CR_PATH}/01_requirements/ (all .md), {CR_PATH}/02_analysis/ANA-{CR}.md,
  REVIEW_ROUND: 1, OUTPUT_FILE: {CR_PATH}/03_change-requirements/review/03_change-requirements-review.md
（`/xddp.review {CR} req` と同一の出力先を再利用する。`NEXT_DOCUMENT_TYPE` はあえて渡さない:
`/xddp.review {CR} req` の `NEXT_DOCUMENT_TYPE: SPO` は
「次工程（specout）が受け取れる状態か」を確認するためのものだが、`xddp.feedback` が実行される
時点ではspecout以降の工程（specout/arch/design/test）は既に完了済みであり、今さらCRS→SPOの
受け取り可否を再チェックする意味がない。よってこの用途では `NEXT_DOCUMENT_TYPE` を省略する）

## Step 8: Report in Japanese

- `DOC_TYPE = code` の場合: Step 1-codeで同期したCHDファイル一覧（repo・file・レビュー判定）を
  最初に報告する。`UNMATCHED_FILES_MAP` に該当ファイルがあれば併記する。
- 反映した項目一覧（種別・内容・根拠）。Step 2/Step 3 で空になり Step 4 がスキップされた場合は
  「CRSへのテキスト反映項目なし」と明記する
- `DOC_TYPE = design` または `code` の場合: Step 5 の実行結果（TM-{CR}.md 更新有無、CHD未対応SP・
  SP間ファイル衝突・未実装SRの3種の警告）。Step 4 がスキップされていても Step 5 は独立して実行
  されているため必ず報告する
- 更新後の CRS バージョン（Step 4 が実行された場合のみ）
- CRS レビュー結果サマリー（🔴/🟡件数、Step 7 が実行された場合のみ）
- 🔴/🟡がある場合: `修正が必要な場合は /xddp.revise {CR} req を実行してください。`

progress.md は更新しない（`/xddp.sync-design` と同様、フェーズ境界を跨いだ事後反映のため
工程ステータス管理の対象外とする）。

---
> **保守メモ:** このファイルを変更した場合は、`README.md`（スキル一覧テーブル）および
> `CLAUDE.md`（ステップ番号体系テーブル）を合わせて更新すること。
