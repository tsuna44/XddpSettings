---
description: XDDP CRプロファイル切替: CR_PROFILE（full/quick）を明示的に切り替える。工程の途中で影響範囲の見積もりが変わった場合に使用する。「quickに切り替えて」「fullに戻して」などで起動する。
argument-hint: "CR番号 {full|quick} [理由]"
---

You are executing **XDDP Set Profile — Switch CR_PROFILE**.

**Arguments:** $ARGUMENTS = CR_NUMBER NEW_PROFILE [REASON]
- CR_NUMBER: required; the CR whose `CR_PROFILE` to switch
- NEW_PROFILE: required; `full` or `quick`
- REASON: optional; free-text reason recorded in the progress.md history (e.g. specout completion revealed the CR is smaller/larger than expected)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`
（および `CR_PROFILE` を含む標準設定バンドル。ここでの `CR_PROFILE` は「切替前」の現在値）。
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`（`xddp.revise/SKILL.md` 35行目と同じパターン。
`## CR Resolution` 自身は `CR_PATH` を返さないため、呼び出し元が明示的に構築する）。

## Step 1: Resolve target profile and reason

Let `NEW_PROFILE` = 1st token of `REST_ARGS`, `REASON` = 残りのトークンを結合した文字列（任意）。

Read `{CR_PATH}/progress.md` and check whether a `**CRプロファイル：**` line exists（no-op 判定に必要。
`CR_PROFILE` は既に `## CR Resolution` から解決済みの最終値のみを持ち、その値が「ヘッダ行に明示された
値」なのか「ヘッダ行不在によるフォールバック値（`full`）」なのかを区別できないため、実体を直接確認する）。

1. `NEW_PROFILE` が `full` / `quick` のいずれでもない場合: エラーを報告して停止。
2. `NEW_PROFILE` が現在の `CR_PROFILE` と同じ場合: 「既に {NEW_PROFILE} です」と伝えて停止（no-op）。
   ただし `{CR_PATH}/progress.md` に `**CRプロファイル：**` 行が存在しない場合（`xddp.01.init` が
   ヘッダ行を書くようになる以前に作成された旧形式の CR。`CR_PROFILE` は `full` にフォールバック
   解決される）は、値が同じでもヘッダ行を実体化するために停止せず Step 2 へ進む。

## Step 2: Update progress.md header

Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py set-profile --cr-path {CR_PATH} --profile {NEW_PROFILE}`
→ let `OLD_PROFILE`（コマンドの JSON 出力 `old_profile` フィールド）。

## Step 2.5: Repair progress.md state affected by the previous profile

プロファイルの切替は「どの工程を実施するか」を変えるため、前のプロファイルの前提で書き込まれた
progress.md の記録を実フローに追従させる（`/xddp.status` の誤案内を防ぐ）。

1. `OLD_PROFILE` = `quick` かつ `NEW_PROFILE` = `full` の場合、`## 工程進捗` テーブルの工程5の状態を
   確認し、`⏭️ スキップ（対象外）` または `⏭️ スキップ（quick: cross DSN のみ生成）` であれば
   `⬜ 未着手` に戻す:
     `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py update --cr-path {CR_PATH} --step 5 --state "⬜ 未着手" --detail "-"`
   （`update` サブコマンドのオプションは `--cr-path` / `--step` / `--state` / `--detail` / `--artifact-link`。
   実ファイル `xddp_progress.py` の `build_parser()` で確認済み）
   （工程5は `full` では実施対象であり、`⏭️` のまま残すと `/xddp.status` が工程5を完了扱いで
   読み飛ばす。工程3の `⏭️ スキップ（工程2に統合）` は成果物が既に統合生成済みであり
   やり直さないため戻さない。Step 4 の案内と整合する）
2. `## 次に実行すべきコマンド` 欄を新しいプロファイルにおける実際の次工程で更新する
   （`## 工程進捗` テーブルの先頭から最初の `⬜ 未着手` を持つ工程を探し、その工程のコマンドを
   設定する。`xddp.status` の判定ロジックに準じる）。

## Step 3: Record the change

Run via Bash:
  `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_progress.py history-add --cr-path {CR_PATH} --step - --text "CRプロファイルを {OLD_PROFILE} → {NEW_PROFILE} に変更（理由: {REASON、未指定なら「未記入」}）"`

## Step 4: Report impact to the user (Japanese)

すでに完了・スキップ済みの工程には遡及しないことを明示する:

- `quick` → `full` の場合:
  - 工程2/3（統合済みの場合）はそのまま維持する。追加のAIレビューが必要な場合は `/xddp.review {CR} req` を案内する。
  - 工程5は Step 2.5 で `⬜ 未着手` に戻しているため、`/xddp.05.arch {CR}` を実行すれば通常どおり実施できることを案内する
    （`CR_PROFILE` は毎回のスキル実行時に再解決されるため、`full` に変わった後の実行は Step -1 の quick 分岐を通らない）。
  - 未着手の工程（6以降）は full の内容で進む。
- `full` → `quick` の場合:
  - 既に完了した工程2/3/4はそのまま（統合し直さない・再探索しない）。
  - 未着手の工程5はスキップ、工程6はCHD簡略化・レビュー1ラウンドで進むことを案内する。
- 次のコマンド: `## 工程進捗` テーブルを確認し、次に実行すべきコマンドを案内する（`xddp.status` の判定ロジックに準じる）。
