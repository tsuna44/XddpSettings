---
name: xddp-abort
description: XDDP CR 中止処理: 完了見込みのない CR を理由付きで取りやめ、VCS 後片付けを案内する。CR は再開しない前提の終端操作。一時的な中断（⏸ 中断）とは異なる。「CRを中止して」「CRを取りやめて」「CRを破棄して」などで起動する。
argument-hint: "[CR番号] [, 中止理由]"
---

You are orchestrating **XDDP Abort — CR 中止処理**.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) [, REASON (optional・自由記述)]

---

Let `RAW_INPUT` = $ARGUMENTS（トリム前の原文字列）。
If `RAW_INPUT` に `,` が含まれる場合:
  Let `CR_ARG` = 最初の `,` より前の部分（前後空白を除去）。
  Let `REASON` = 最初の `,` より後の部分（前後空白を除去）。結果が空文字列なら `null` とする。
Else:
  Let `CR_ARG` = `RAW_INPUT`（前後空白を除去）。
  Let `REASON` = `null`。
（`argument-hint` の `[, 中止理由]` はカンマ区切りの自由記述を想定しているため、空白区切りの
トークン分割ではなくカンマで一括分割する。中止理由に読点・スペースを含んでも正しく取得できる。）

Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## CR Resolution" with RAW_ARGS: {CR_ARG}, SKIP_ABORT_GUARD: true → let `CR`, `REST_ARGS`.
（`SKIP_ABORT_GUARD: true` を明示的に渡すことで、下記「中止済み CR ガード」を本スキル自身では
発火させない。中止済み CR に対して再度 `/xddp-abort` を実行した場合は下記 Step 0 が専用メッセージで
検出・停止するため、`## CR Resolution` 側の汎用ブロッキング確認と二重に衝突することはない。）

Let `TODAY` = today's date (YYYY-MM-DD).
(xddp.config.md lookup done in xddp-common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
REPOS_MAP, REPOS_KEYS, IS_MULTI, DOCS, DEVELOPMENT_MODE, VCS_TYPE, VCS_BRANCH_PREFIX.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: Precondition Check

Read `{CR_PATH}/progress.md`.
If a `## CR 中止` section already exists: report "この CR は既に中止済みです（中止日: {既存の中止日}）。" and stop.
If a `## CR クローズ` section already exists (`xddp-close` 完了済み): report "この CR は既に完了・クローズ済みのため中止できません。" and stop.
Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_progress.py check-in-progress --cr-path {CR_PATH}`
  → let `CHECK_RESULT`（stdout の JSON 1オブジェクト）。
If `CHECK_RESULT.close_progress_in_progress` is `true`
（`xddp-close` が完了前に中断・進行中の状態。`xddp_progress.py` の `close-state` サブコマンドが
書き込む専用セクションで、Step C3.5/C3.6 等により既に一部成果物が `{DOCS}` へ昇格済みの
可能性がある）: report "この CR は `xddp-close` の処理が中断/進行中の状態です（詳細: {`CHECK_RESULT.close_progress_detail`}）。`/xddp-close {CR}` を再実行して完了させるか、状態を十分確認したうえで中止の要否を
判断してください。" and stop（安全側に倒してブロックする。一部成果物が既に共有知識へ昇格済みの場合、
中止のみでは実態と整合しなくなるおそれがあるため）。
（`CHECK_RESULT` はここで初めて取得され、後続の「## Step 4: Mark Progress as Aborted」が
同じ値をそのまま再利用する。Step 0 は本 SKILL 内で最初に実行されるステップであるため、
`/xddp-abort` の実行中に `check-in-progress` を呼び出すのはここ1回のみになる）

## Step 1: Confirm with User

Display current progress summary (最終完了工程 = `## 工程進捗` テーブルの最後に ✅ が付いた行、または全て ⬜ なら「未着手」).

If `REASON` is null: ask the user for a 中止理由（自由記述・必須）.

Tell the user:
> CR `{CR}`（{タイトル}）を中止します。最終完了工程: {最終完了工程}
> 中止理由: {REASON}
> この操作は取り消せません（CR は再開しない前提になります）。続行しますか？ [続行 / キャンセル]

Wait for user confirmation. If キャンセル: stop without any changes.

## Step 2: VCS Cleanup Guidance

Read `~/.claude/skills/xddp-common/procedures/resolve-vcs-target-repos.md`, apply "## Resolve VCS Target Repos" with:
  REPO_CANDIDATES: {REPOS_KEYS}, CR_PATH: {CR_PATH}, CR: {CR}
→ let `VCS_TARGET_REPOS`.
（`xddp-close` Step C-Pre と同一パターン。以下の status 確認ループは情報提供目的のため全リポジトリ
（`REPOS_KEYS`）を対象とし、警告文言のみ `VCS_TARGET_REPOS`（本 CR のスコープ）に含まれるか否かで
出し分ける——`xddp-close` Step C-Pre がこの設計を採る理由と同一：スコープ外リポジトリの状態も
情報として見せたいが、それが本 CR 由来の変更だと誤認されないようにする）

For each `{repo}` in `REPOS_KEYS`:
  If `VCS_TYPE` is `none`: skip.
  Else:
    Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_vcs.py status --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE}`
    → let `REPO_STATUS`.
    If `REPO_STATUS` is `dirty`:
      If `{repo}` is in `VCS_TARGET_REPOS`:
        Warn: "⚠️ {repo} に未コミットの変更があります（本 CR の作業ブランチに残っている可能性があります）。"
      Else:
        Warn: "⚠️ {repo} に未コミットの変更があります（本 CR のスコープ外です。別の作業・CR による変更である可能性があります）。"
    If `REPO_STATUS` is `unknown`:
      Warn: "⚠️ {repo} の VCS 状態が不明です。手動で確認してください。"

Tell the user (VCS_TYPE が none でないリポジトリが1つ以上ある場合のみ):
> 中止に伴うクリーンアップは自動実行されません。必要に応じて以下を手動で実行してください:
> - 未コミット変更の破棄: 以下を対象リポジトリごとに実行してください:
>   {for each repo in VCS_TARGET_REPOS: `- {repo}`: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_vcs.py revert --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE} --untracked`}
>   （上記引用ブロックの `- ` 行は `VCS_TARGET_REPOS` の各 `{repo}` について1行ずつ展開して提示する。
>   この括弧書きは実装者・実行 AI 向けの生成指示であり、ユーザーへは表示しない）
> - 作業ブランチ `{VCS_BRANCH_PREFIX}{CR}` の削除: ご利用の VCS コマンドで手動削除してください
> - 既にコミット済みの変更を取り消す場合は、ご利用の VCS コマンドで revert / reverse merge 等を手動実行してください

## Step 2.5: latest-specs Cleanup

`{CR_PATH}/.latest-specs-baseline.json`（工程11 の基準）が無い場合: この Step をスキップする（`LATEST_SPECS_RESULT` = 「対象なし」）。

ある場合: Run via Bash:
`PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_changes.py revert --xddp-dir {WORKSPACE_ROOT}/{XDDP_DIR} --cr {CR} --docs {DOCS} --dry-run`
→ let `REVERT_PLAN`（`restored`〔`{DOCS}` の内容に戻す〕・`removed`〔この CR が足したので消す〕・`kept`〔戻せない。理由付き〕）。
終了コードが0以外なら stderr を表示し、`LATEST_SPECS_RESULT` = 「確認できず（{stderr の要約}）」として Step 3 へ進む。

Tell the user:
> この CR は工程11 で latest-specs を変えています。中止した CR の仕様は CR で検証されていないので、`{DOCS}` に入れないことを推奨します。
>
> | 扱い | ファイル |
> |---|---|
> {REVERT_PLAN の restored の各ファイル: | `{DOCS}` の内容に戻す | `{file}` |}
> {REVERT_PLAN の removed の各ファイル: | 消す（この CR が足した） | `{file}` |}
> {REVERT_PLAN の kept の各ファイル: | 戻せない（{reason}） | `{file}` |}
>
> 1. 元に戻す（推奨）: 戻せるファイルだけを `{DOCS}` の内容に戻し、この CR が足したファイルを消す。戻せないファイルは触らない
>    （他の CR の未昇格の変更を含みうるため。必要なら人が直す）
> 2. 残す: 足したファイルは、後の CR の close で `{DOCS}` へ昇格しうる。既存のファイルの変更・削除は、後の CR の close で
>    `{DOCS}` の版に戻る（後の CR も変えたファイルを除く）

Wait for user response.
- 1: Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-11-specs/scripts/spec_changes.py revert --xddp-dir {WORKSPACE_ROOT}/{XDDP_DIR} --cr {CR} --docs {DOCS}`
  → `LATEST_SPECS_RESULT` = 「元に戻した（戻した {restored の件数} 件・消した {removed の件数} 件・戻せなかった {kept の件数} 件: {kept のファイルと理由}）」。
  終了コードが0以外なら stderr を表示し、`LATEST_SPECS_RESULT` = 「元に戻すのに失敗（{stderr の要約}）」とする。
- 2: `LATEST_SPECS_RESULT` = 「残した（{REVERT_PLAN の3つの一覧の件数}）」。

## Step 3: Record Insight (Optional)

Tell the user:
> この CR で得られた気づき・改善案があれば、次の CR や `improvement-backlog.md` の入力として
> 残すことができます。`{CR_PATH}/progress.md` の「## 気づき・提案メモ」セクションに追記しますか？ [はい / いいえ]

If はい: prompt for entries and append to `## 気づき・提案メモ` table in `progress.md`
using the same row format as the template（`#`／種別／内容／対応方針の4列。`#` は既存行数+1から
の連番）. Then tell the user（`{XDDP_DIR}`・`{DOCS}`・`{TODAY}`・`{CR}` は値に置き換えて示す。人が埋める欄の
`{NN}`〔`01` からの連番〕・`{repo}`〔REPOS のキー〕は置き換えずにそのまま示す）:
> progress.md に書いた気づきは昇格しません。残すなら次のようにしてください。
> - IDEA: `{XDDP_DIR}/improvement-backlog.md` の `## 3. アイデア詳細` の末尾に `IDEA-{CR}-{NN}` で書く（書式は `~/.claude/skills/xddp-close/SKILL.md` の Step B。次の close で `{DOCS}/improvement-backlog.md` に足し込まれる）。
> - LL: `/xddp-update-knowledge {repo} lesson` で登録する。
{`{XDDP_DIR}/improvement-backlog.md` が無い場合のみ:}
> - `{XDDP_DIR}/improvement-backlog.md` が無いので、`~/.claude/skills/xddp-close/templates/10_improvement-backlog-template.md` を写して作る（`{YYYY-MM-DD}` は今日の日付に置き換え、他の `{…}` は残す）。
{IS_MULTI の場合のみ:}
> - cross の LL は update-knowledge で登録できないので、次のコマンドで ID（stdout の `next_manual_id`）を得て `{DOCS}/cross/knowledge/lessons-learned.md` の末尾に書き（書式は `~/.claude/skills/xddp-close/SKILL.md` の「### Entry Format」）、同じコマンドをもう一度実行して表を作り直す:
>   `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-close/scripts/promote.py index --today {TODAY} --layer2-file {DOCS}/cross/knowledge/lessons-learned.md --area cross`

## Step 4: Mark Progress as Aborted

Reuse `CHECK_RESULT` from「## Step 0: Precondition Check」（同一の `/xddp-abort` 実行内で既に
`check-in-progress --cr-path {CR_PATH}` を1回呼び出し済みであり、Step 1〜3（ユーザー確認・VCS
クリーンアップ案内・気づきメモ追記）は工程進捗テーブル・`## xddp-close 進捗` のいずれも変更しないため
再取得は不要。`check-in-progress` を呼び直さない）。
If `CHECK_RESULT.last_active_step` is not `null`:
  Read `~/.claude/skills/xddp-common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: {CHECK_RESULT.last_active_step}, STATE: 🛑 中止, DETAIL_STEP: "CR中止により打ち切り"
  （`xddp_progress.py` を直接呼ばず共通プロシージャ経由にすることで、CLAUDE.md「決定的処理はスクリプト・
  意味判定はLLM」の一元化方針・既存の全スキルの呼び出しパターンに揃える。`DETAIL_STEP` を明示するのは、
  省略時は既存の詳細ステップ文字列が保持され「作業中」を示す古い文言が状態 `🛑 中止` と矛盾したまま
  残ってしまうため。行検出自体は `check-in-progress` の走査結果（`last_active_step`）を再利用し、
  Step 4 独自の検出ロジックは持たない）
（マルチリポジトリ CR の「リポジトリ別」サブテーブル（工程4a/7等）は本ステップでは更新しない
——中止時点の各リポジトリの状態を監査目的でそのまま保持する意図的な設計であり、更新漏れではない）

`{CR_PATH}/progress.md` の「## 次に実行すべきコマンド」セクションのコードブロック内容を
以下に置き換える（`xddp-status` はこのセクションを読まず工程進捗テーブルから動的算出するため
3.3 の変更だけでは不十分——progress.md を直接読む人・別ツールが誤って旧コマンドを実行しないよう、
静的セクション自体も書き換える）:

```
（この CR は中止済みです。再開しない前提のため次に実行すべきコマンドはありません）
```

Append at the end of `{CR_PATH}/progress.md`:

```
## CR 中止

- **中止日：** {TODAY}
- **最終完了工程：** {最終完了工程}
- **中止理由：** {REASON}
- **latest-specs：** {LATEST_SPECS_RESULT}
```

## Step 5: Report in Japanese

Report: 中止日, 中止理由, VCS クリーンアップが必要なリポジトリ一覧（あれば）, latest-specs の扱い（`LATEST_SPECS_RESULT`）, 気づきメモの追記有無.
