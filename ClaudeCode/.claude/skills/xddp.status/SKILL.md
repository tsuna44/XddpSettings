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

## 2.4. 工程15 分割実行の残タスク表示

（既存の「## 2.5. Per-repo progress tables」は見出し番号上は「## 2」の直後に見えるが、
ファイル内では物理的に「## 3」の後に配置されている。本セクションもこの既存の配置慣習に合わせ、
「## 3」の直後・「## 2.5」の直前に挿入する。
**注意（今後の編集者向け）:** このファイルは見出し番号の連番と物理的な出現順序が一致しない箇所がある。
新たなセクションを追加・移動する際は、見出し番号だけでなく前後セクションの物理的な配置も必ず確認すること。）

If `progress.md` contains a "## 工程15 分割実行メモ" section (written by xddp.10.specs when split execution was chosen):

Read `REPOS:` from `{WORKSPACE_ROOT}/xddp.config.md`. Let `IS_MULTI` = (リポジトリ数 ≥ 2).
（xddp.10.specs/SKILL.md Step 0 と同じ定義をそのまま再利用する。本セクション専用に毎回算出し、他セクションの状態には影響しない。
注: 同ファイル内の既存セクション「## 5. CR間修正ファイル衝突チェック」には未定義の `REPOS_KEYS` への参照が既存バグとして存在するが、これは本プランのスコープ外である。本セクションの `REPOS:`/`IS_MULTI` はそれとは独立したローカル算出であり、`REPOS_KEYS` の定義不備を解消するものではない。）

Parse the section's fields and display:

```
🧩 工程15（最新仕様書作成）分割実行中:
  完了済みステップ: {完了済みステップ}
  未処理ステップ: {未処理ステップ一覧}（算出式は `xddp.10.specs/SKILL.md` Step DONE で定義したものと同一。「全体ステップ一覧（UC・OV・MOD、IS_MULTI の場合のみ CROSS も含む）から完了済みステップを除いたもの」を本セクションでも同じ式で再計算する）
  {未処理リポジトリ がある場合} 未処理リポジトリ: {未処理リポジトリ}
  {処理済みモジュール がある場合} 処理済みモジュール: {処理済みモジュール} in {repo}
  {未処理UR がある場合} 未処理UR: {未処理UR}
  ⚡ 継続コマンド: /xddp.10.specs {CR番号}
```
If the section does not exist, skip this display.

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
Let `STATUS_LINE` = "## CR クローズ" セクション内の `**ステータス：**` で始まる行（他の3行「クローズ日」
「改善バックログ追加」「知見ログ追加」は対象としない）。
If `STATUS_LINE` exists and contains "完了・クローズ済み"（先頭の ✅/⚠️ は問わない）:
  If `STATUS_LINE` also contains "⚠️":
    Display: `📦 DOCS昇格: ⚠️ クローズ済み（{クローズ日}・一部リポジトリ昇格未完了）`
  Else:
    Display: `📦 DOCS昇格: ✅ クローズ済み（{クローズ日}）`
Else if step 15 (最新仕様書作成) is ✅ 完了 but クローズ未実施:
  Display: `📦 DOCS昇格: ⬜ 未実施（/xddp.close {CR} で昇格）`
Else:
  Skip this display (工程15 未完了のため昇格対象外).

## 5. CR間修正ファイル衝突チェック

（表示CRが2件以上の場合のみ実行。単一CRの場合はスキップ）

`FILE_CR_MAP` = {}  (key: ファイルパス → value: list of CR番号)

For each displayed `{cr}` in the set of CRs:
  Let `TM_FILE` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{cr}/03_change-requirements/TM-{cr}.md`.
  If `TM_FILE` exists:
    Read Section 1 (SP→実装ファイル対応表). Extract 変更ファイル列 (skip `-` rows).
    For each ファイルパス: append `{cr}` to `FILE_CR_MAP[ファイルパス]`.
  Else:
    For each `{repo}` in `REPOS_KEYS`:
      Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
        CR_PATH: {WORKSPACE_ROOT}/{XDDP_DIR}/{cr}, REPO_NAME: {repo}, CR: {cr}
      → let `CHD_CONTENT_FILES`.
      For each ファイル in `CHD_CONTENT_FILES`:
        Read ファイル, Section 2 (変更対象ファイル一覧). Extract ファイルパス列.
        For each ファイルパス: append `{cr}` to `FILE_CR_MAP[ファイルパス]`.

`CONFLICTS` = { path: crs for path, crs in FILE_CR_MAP if len(crs) >= 2 }

Display:
> 📊 CR間修正ファイル衝突チェック
{if CONFLICTS is non-empty:}
> ⚠️ 以下のファイルが複数のCRで修正されています（マージ競合リスクあり）:
> | ファイルパス | 修正CR一覧 |
> |------------|----------|
> {for each path, crs in CONFLICTS: | {path} | {crs カンマ区切り} |}
{else:}
> ✅ 修正ファイルの重複なし（調査した{len(FILE_CR_MAP)}ファイル）

