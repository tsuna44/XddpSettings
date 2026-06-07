---
description: XDDP 進捗確認: CRの現在フェーズと成果物の状態を一覧表示する。「進捗確認して」「どこまで進んでる？」などで起動する。
argument-hint: "[CR番号]"
---

You are executing **XDDP Status Check**.

**Arguments:** $ARGUMENTS = CR_NUMBER (optional)

---

Find `xddp.config.md` by searching upward from cwd: check cwd first, then each parent directory in order. Let `WORKSPACE_ROOT` = the directory where the file is found. If not found at filesystem root, report "xddp.config.md が見つかりません。ワークスペースルートまたはそのサブディレクトリで実行してください。" and stop.
Extract `XDDP_DIR` (default: `xddp` if the key is absent).

## 1. Locate progress files
- If CR_NUMBER given → read `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR_NUMBER}/progress.md`.
- If omitted → find all `{WORKSPACE_ROOT}/{XDDP_DIR}/*/progress.md`.

## 2. Display for each CR

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 CR: {CR番号} — {タイトル}
開始日: {開始日}  最終更新: {最終更新日}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
工程進捗: (show all 15 steps with emoji status, 詳細ステップ, and completion dates)
  - 状態が ⬜ 未着手 / ✅ 完了 の行は 詳細ステップ を省略してよい
  - 状態が 🔄 / 👀 / 🔁 の行は 詳細ステップ を必ず表示する
  - 例: `| 6 | 実装方式検討 | 👀 レビュー待ち | Step B2: 人レビュー待ち | ... |`

完了工程: {X} / 15
⚡ 次のコマンド: /xddp.XX.YYY {CR番号}
```

## 3. Check for unresolved review warnings
In the already-read progress.md content, scan the `## 備考・メモ` section for lines
starting with `⚠️ 工程`. For each found line, display:
> ⚠️ {CR番号} {その行の内容}
(No additional file reads required.)

## 2.5. Per-repo progress tables
If `progress.md` contains "リポジトリ別" tables (added by xddp.04.specout, xddp.07.code, etc.),
display them under the overall step status:

```
📦 リポジトリ別進捗:
  工程4（スペックアウト）: repo-a ✅  repo-b 🔄  cross ⏳
  工程9（コーディング）:   repo-a ✅  repo-b ⏳  cross/検証 ⏳
```

If no per-repo tables exist (single-repo or steps not yet run), skip this section.

## 4. Artifact checklist
For each step in the already-read progress.md 工程進捗テーブル, read the 成果物 column:
- Column is a Markdown link `[...]( ... )` → ✅
- Column is `-` or empty → ⬜

Display the step number, 工程名, and ✅/⬜ for each step.
(No individual file existence checks required.)

## 4.5. DOCS_DIR 昇格状態確認

For each CR displayed, check `{CR_PATH}/progress.md` for a "## CR クローズ" section.
If "## CR クローズ" exists and contains "✅ 完了・クローズ済み":
  Display: `📦 DOCS昇格: ✅ クローズ済み（{クローズ日}）`
Else if step 15 (最新仕様書作成) is ✅ 完了 but クローズ未実施:
  Display: `📦 DOCS昇格: ⬜ 未実施（/xddp.close {CR} で昇格）`
Else:
  Skip this display (工程15 未完了のため昇格対象外).

