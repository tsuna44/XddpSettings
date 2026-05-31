---
description: XDDPツール修正プランのAIエキスパートレビューと修正を、Criticalがなくなるか最大ラウンド数（REVIEW_MAX_ROUNDS.PLAN）に達するまで繰り返す。「プランをレビューして」「plan-reviewして」などで起動する。
argument-hint: "[プランファイルパス]"
---

You are executing **XDDP Plan Review Loop — AI expert review + fix until no Critical findings**.

**Arguments:** $ARGUMENTS = [PLAN_FILE]
- PLAN_FILE: path to the plan .md file to review (relative to cwd, or absolute)
  Example: `plans/PLAN-20260531-fix-review-findings-M1M2A1A2K1.md`

> Note: This skill does not use CR Resolution. It operates directly on a plan file path.

---

## Step 1: Resolve plan file

Let `PLAN_FILE` = trim($ARGUMENTS).

If `PLAN_FILE` is empty:
- If `plans/` directory exists in cwd: run `ls plans/PLAN-*.md` (exclude `_template.md` by pattern).
  - If exactly 1 file found: `PLAN_FILE = that file`. Report `"プランを自動検出しました: {PLAN_FILE}"`.
  - If multiple found: list them and ask the user to specify via argument. Stop.
  - If none found: report error and stop.
- If `plans/` does not exist: report `"plans/ ディレクトリが見つかりません。プランファイルパスを引数で指定してください。"` and stop.

Verify `PLAN_FILE` exists (Read or Bash check). If not found: report error and stop.

Let `PLAN_NAME`  = filename without `.md` extension (e.g., `PLAN-20260531-fix-review-findings-M1M2A1A2K1`).
Let `PLAN_DIR`   = parent directory of `PLAN_FILE` (e.g., `plans`).
Let `REVIEW_FILE` = `{PLAN_DIR}/review/{PLAN_NAME}-review.md`.

Run `mkdir -p {PLAN_DIR}/review` via Bash.

---

## Step 1.5: Read config (MAX_ROUNDS and FIX_STRATEGY)

Search for `xddp.config.md` by scanning cwd, then parent directories (up to 3 levels).
If found:
  - Read `REVIEW_MAX_ROUNDS.PLAN` (default: `3`). Let `MAX_ROUNDS` = that value.
  - Read `FIX_STRATEGY.PLAN` (default: `ideal`). Let `FIX_STRATEGY` = that value.
    Valid values: `efficiency` / `ideal` / `balanced`.
    If invalid value: warn user and fall back to `ideal`.
If not found: `MAX_ROUNDS` = 3, `FIX_STRATEGY` = `ideal`.

---

## Step 2: Review → Fix Loop

Let `ROUND`         = 1.
Let `CRITICAL_COUNT` = 1.

WHILE `ROUND` ≤ `MAX_ROUNDS` AND `CRITICAL_COUNT` > 0:
# 最終ラウンド（ROUND = MAX_ROUNDS）は修正なし・確認のみ。修正試行は最大 MAX_ROUNDS - 1 回（例: 3 → 2回修正 + 1回確認）。

### 2A: Run AI review (isolated context)

Let `REF_CLAUDE`   = `CLAUDE.md` (path relative to cwd; reviewer skips if not found).
Let `REF_TEMPLATE` = `{PLAN_DIR}/_template.md` (path relative to cwd; reviewer skips if not found).

Use the **Agent tool** with `subagent_type=xddp-reviewer` and pass:
```
DOCUMENT_TYPE: PLAN
TARGET_FILE: {PLAN_FILE}
REFERENCE_FILES: [{REF_CLAUDE}, {REF_TEMPLATE}]
REVIEW_ROUND: {ROUND}
OUTPUT_FILE: {REVIEW_FILE}
```
(This is the same Agent tool invocation format used in xddp.review Step 3.)

### 2B: Count Critical findings

Read `{REVIEW_FILE}`. Count all 🔴 rows in Section 2 (指摘事項と対応内容).
(対応状況は問わない — レビューファイルはラウンドごとに上書き（xddp-reviewer の overwrite 設計）。
ラウンド履歴の保存はレビュアーエージェントの裁量動作であり、本スキルは保証しない。
カウント対象はそのラウンドのレビューで報告された 🔴 行の総数とする。)

Let `CRITICAL_COUNT` = that count.

**If `CRITICAL_COUNT` = 0:**
- Report: `"✅ ラウンド {ROUND}: Critical指摘ゼロ。"`
- Set `ROUND = ROUND + 1`. Break loop.

**If `CRITICAL_COUNT` > 0 AND `ROUND` = `MAX_ROUNDS`:**
- Report: `"⚠️ {MAX_ROUNDS} ラウンド後も 🔴 指摘が {CRITICAL_COUNT} 件残存しています。"`
- Append to `{REVIEW_FILE}`: `"⚠️ 最大ラウンド数（{MAX_ROUNDS}）到達。未解決のCritical指摘あり。人間の確認が必要です。"`
- Set `ROUND = ROUND + 1`. Break loop.

**If `CRITICAL_COUNT` > 0 AND `ROUND` < `MAX_ROUNDS`:**
  → Proceed to Step 2C.

### 2C: Cross-section and cross-file investigation (修正前の横展開調査)

Before planning fixes, investigate whether the same issues exist elsewhere:

1. For each 🔴 item, identify the **root cause pattern** (e.g., "パスの不一致", "理由ラベル欠落", "Before/Afterの曖昧記述").
2. **Cross-section scan:** Scan all other sections of `{PLAN_FILE}` for the same pattern. Add any matches to the fix list.
3. **Cross-file scan:** For files listed in Section 2 (変更対象ファイル) and Section 4 (影響範囲):
   - If the fix pattern implies those files might need corresponding changes (e.g., パス名変更、関連定義の追加), check those files.
   - Add any required cross-file fixes to the fix list.

Compile `FIX_LIST`: ordered list of `(対象ファイル/セクション, 修正内容, 単一解/複数案, 選択肢一覧)`.

### 2D: Fix strategy — FIX_STRATEGY に基づく適用方針の決定

Categorize `FIX_LIST`:
- **単一解:** one clear solution exists.
- **複数案:** multiple viable approaches exist. Prepare 2+ options, flagging which is the ideal-state option.

Apply behavior by `FIX_STRATEGY`:

**`FIX_STRATEGY = balanced` (default):**
- 単一解: apply without asking. Report the list with rationale before applying.
- 複数案: present ALL items (both categories) to the human in a single message. Wait for response before applying.

> **ラウンド {ROUND}: 🔴 Critical {CRITICAL_COUNT} 件 + 横展開 {N} 件の対応方針を確認します**
>
> **【自動適用】確認のみ:**
> | # | 対象 | 修正内容 | 理由 |
> |---|---|---|---|
> | A1 | … | … | … |
>
> **【選択が必要】番号と選択肢（A/B）で回答してください:**
> | # | 対象 | 選択A（推奨・理想状態） | 選択B（代替案） |
> |---|---|---|---|
> | C1 | … | … | … |

**`FIX_STRATEGY = ideal`:**
- 全項目: 複数案であっても理想状態（本来あるべき姿）の選択肢を自動選択。
- 人への確認なし。適用前に「適用する修正内容（理由付き）」を一覧表示してから実行。

**`FIX_STRATEGY = efficiency`:**
- 全項目: 複数案であっても最小インパクトの選択肢を自動選択。
- 人への確認なし。適用前に「適用する修正内容」を一覧表示してから実行。

### 2E: Apply all fixes

Apply confirmed fixes in `FIX_LIST` order:
1. Apply to `{PLAN_FILE}` (all sections including cross-section findings).
2. Apply cross-file fixes identified in Step 2C.
3. After all applied, verify:
   - Section 2 lists all files now being changed (including any cross-file additions).
   - Section 4 reflects the actual impact of the full fix set.
   - Section 5 covers any new test scenarios introduced by the fixes.

Set `ROUND = ROUND + 1`. Continue loop.

---

## Step 3: Final report (in Japanese)

Tell the user:

> **プランレビュー完了**
>
> | 項目 | 内容 |
> |---|---|
> | プランファイル | `{PLAN_FILE}` |
> | レビュー結果 | `{REVIEW_FILE}` |
> | 実施ラウンド数 | {ROUND - 1} |
> | 残存Critical件数 | {CRITICAL_COUNT} |
>
> {if CRITICAL_COUNT = 0:}
> ✅ Critical指摘はありません。承認者がプランを確認し、ステータスを「承認済み」に更新してください。
>
> {if CRITICAL_COUNT > 0:}
> ⚠️ {CRITICAL_COUNT} 件のCritical指摘が残存しています。`{REVIEW_FILE}` を確認して手動修正後、再度 `/xddp.plan-review {PLAN_FILE}` を実行してください。

---
> **保守メモ:** このファイルを変更した場合は、`README.md`（スキル一覧テーブル）、`CLAUDE.md`（ステップ番号体系テーブル）、および新規設定キーを追加した場合は `xddp.config.md` テンプレートと `CLAUDE.md`（xddp.config.md の位置付け節）も合わせて更新すること。
