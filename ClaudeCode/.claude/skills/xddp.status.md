---
description: XDDP 進捗確認: CRの現在フェーズと成果物の状態を一覧表示する。「進捗確認して」「どこまで進んでる？」などで起動する。
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
Scan all review files under `{XDDP_DIR}/{CR}/` — check `{XDDP_DIR}/{CR}/review/*.md` and each `{XDDP_DIR}/{CR}/*/review/*.md` — for "⚠️ 未解決の重大指摘あり". If found, display:
> ⚠️ {CR番号}: {file名}に未解決の重大指摘があります。人間の確認が必要です。

## 4. Artifact checklist
Show which output files exist in `{XDDP_DIR}/{CR}/`: ✅ exists / ⬜ not yet
```
ANA  CRS  SPO  DSN  CHD  VERIFY  TSP  TRS  {XDDP_DIR}/latest-specs/
```

## 5. Multi-CR conflict hint
If multiple CRs are listed, check whether any two CHD Section 2 file lists overlap. If so:
> ⚠️ {CR1} と {CR2} が同じファイルを変更しています。衝突の可能性があります。
