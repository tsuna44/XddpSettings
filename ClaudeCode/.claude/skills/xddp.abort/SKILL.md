---
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

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with RAW_ARGS: {CR_ARG}, SKIP_ABORT_GUARD: true → let `CR`, `REST_ARGS`.
（`SKIP_ABORT_GUARD: true` を明示的に渡すことで、下記「中止済み CR ガード」を本スキル自身では
発火させない。中止済み CR に対して再度 `/xddp.abort` を実行した場合は下記 Step 0 が専用メッセージで
検出・停止するため、`## CR Resolution` 側の汎用ブロッキング確認と二重に衝突することはない。）

Let `TODAY` = today's date (YYYY-MM-DD).
(xddp.config.md lookup done in xddp.common/SKILL.md「## CR Resolution」; reuse WORKSPACE_ROOT, XDDP_DIR,
REPOS_MAP, REPOS_KEYS, IS_MULTI, DEVELOPMENT_MODE, VCS_TYPE, VCS_BRANCH_PREFIX.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## Step 0: Precondition Check

Read `{CR_PATH}/progress.md`.
If a `## CR 中止` section already exists: report "この CR は既に中止済みです（中止日: {既存の中止日}）。" and stop.
If a `## CR クローズ` section already exists (`xddp.close` 完了済み): report "この CR は既に完了・クローズ済みのため中止できません。" and stop.
If a `## xddp.close 進捗` section が存在し、その状態が `⏸ 中断` または `🔄 進行中` の場合
（`xddp.close` が完了前に中断・進行中の状態。`xddp_progress.py` の `close-state` サブコマンドが
書き込む専用セクションで、Step C3.5/C3.6 等により既に一部成果物が `latest-specs/` へ昇格済みの
可能性がある）: report "この CR は `xddp.close` の処理が中断/進行中の状態です（詳細: {該当セクションの
detail 文言}）。`/xddp.close {CR}` を再実行して完了させるか、状態を十分確認したうえで中止の要否を
判断してください。" and stop（安全側に倒してブロックする。一部成果物が既に共有知識へ昇格済みの場合、
中止のみでは実態と整合しなくなるおそれがあるため）。

## Step 1: Confirm with User

Display current progress summary (最終完了工程 = `## 工程進捗` テーブルの最後に ✅ が付いた行、または全て ⬜ なら「未着手」).

If `REASON` is null: ask the user for a 中止理由（自由記述・必須）.

Tell the user:
> CR `{CR}`（{タイトル}）を中止します。最終完了工程: {最終完了工程}
> 中止理由: {REASON}
> この操作は取り消せません（CR は再開しない前提になります）。続行しますか？ [続行 / キャンセル]

Wait for user confirmation. If キャンセル: stop without any changes.

## Step 2: VCS Cleanup Guidance

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Resolve VCS Target Repos" with:
  REPO_CANDIDATES: {REPOS_KEYS}, CR_PATH: {CR_PATH}, CR: {CR}
→ let `VCS_TARGET_REPOS`.
（`xddp.close` Step C-Pre と同一パターン。以下の status 確認ループは情報提供目的のため全リポジトリ
（`REPOS_KEYS`）を対象とし、警告文言のみ `VCS_TARGET_REPOS`（本 CR のスコープ）に含まれるか否かで
出し分ける——`xddp.close` Step C-Pre がこの設計を採る理由と同一：スコープ外リポジトリの状態も
情報として見せたいが、それが本 CR 由来の変更だと誤認されないようにする）

For each `{repo}` in `REPOS_KEYS`:
  If `VCS_TYPE` is `none`: skip.
  Else:
    Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_vcs.py status --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE}`
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
>   {for each repo in VCS_TARGET_REPOS: `- {repo}`: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_vcs.py revert --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE} --untracked`}
>   （上記引用ブロックの `- ` 行は `VCS_TARGET_REPOS` の各 `{repo}` について1行ずつ展開して提示する。
>   この括弧書きは実装者・実行 AI 向けの生成指示であり、ユーザーへは表示しない）
> - 作業ブランチ `{VCS_BRANCH_PREFIX}{CR}` の削除: ご利用の VCS コマンドで手動削除してください
> - 既にコミット済みの変更を取り消す場合は、ご利用の VCS コマンドで revert / reverse merge 等を手動実行してください

## Step 3: Record Insight (Optional)

Tell the user:
> この CR で得られた気づき・改善案があれば、次の CR や `improvement-backlog.md` の入力として
> 残すことができます。`{CR_PATH}/progress.md` の「## 気づき・提案メモ」セクションに追記しますか？ [はい / いいえ]

If はい: prompt for entries and append to `## 気づき・提案メモ` table in `progress.md`
using the same row format as the template（`#`／種別／内容／対応方針の4列。`#` は既存行数+1から
の連番）.
(`improvement-backlog.md` / `lessons-learned.md` への昇格は行わない — CR フォルダ内に留め、
将来 `xddp.update-knowledge` 等で手動登録する運用とする。自動昇格しない理由は、
中止 CR は完了 CR と異なり品質・妥当性が確定していない気づきを含みうるため。)

## Step 4: Mark Progress as Aborted

Identify the last row in `## 工程進捗` whose 状態 is `🔄`, `👀`, or `🔁` (進行中の工程).
If found:
  Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Progress Update" with:
    CR_PATH: {CR_PATH}, STEP_NUM: {該当工程番号}, STATE: 🛑 中止, DETAIL_STEP: "CR中止により打ち切り"
  （`xddp_progress.py` を直接呼ばず共通プロシージャ経由にすることで、CLAUDE.md「決定的処理はスクリプト・
  意味判定はLLM」の一元化方針・既存の全スキルの呼び出しパターンに揃える。`DETAIL_STEP` を明示するのは、
  省略時は既存の詳細ステップ文字列が保持され「作業中」を示す古い文言が状態 `🛑 中止` と矛盾したまま
  残ってしまうため）
（マルチリポジトリ CR の「リポジトリ別」サブテーブル（工程4a/7等）は本ステップでは更新しない
——中止時点の各リポジトリの状態を監査目的でそのまま保持する意図的な設計であり、更新漏れではない）

`{CR_PATH}/progress.md` の「## 次に実行すべきコマンド」セクションのコードブロック内容を
以下に置き換える（`xddp.status` はこのセクションを読まず工程進捗テーブルから動的算出するため
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
```

## Step 5: Report in Japanese

Report: 中止日, 中止理由, VCS クリーンアップが必要なリポジトリ一覧（あれば）, 気づきメモの追記有無.
