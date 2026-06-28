---
description: XDDPツール修正プランのAIエキスパートレビューと修正を、Critical（🔴）と残指摘事項（🟡/🔵）がいずれもゼロになるか最大ラウンド数（REVIEW_MAX_ROUNDS.PLAN）に達するまで繰り返す。MAX_ROUNDS到達時にいずれかが残存する場合はボーナスラウンドを追加実施し、レビューファイルを最新状態に更新する。「プランをレビューして」「plan-reviewして」などで起動する。
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

Check if `xddp.config.md` exists in cwd (direct check only — do not scan parent directories).
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
Let `RESIDUAL_COUNT` = 1.
# RESIDUAL_COUNT（残指摘事項）= レビューファイル Section 2 の 🟡/🔵 行のうち、対応状況が
# `⬜ 未対応` である行の総数（`✅ 対応済`／`➖ 対応不要` はいずれも除外）。
# CRITICAL_COUNT も同様の規則（`⬜ 未対応` の行のみカウント対象。`✅ 対応済`／`➖ 対応不要` は除外）。
# 除外された行は Section 2 から削除されず残り続けるため、Step 3 の最終報告で除外件数を必ず提示し、
# 承認者が承認前にその理由を確認できるようにする（詳細は Step 2B・Step 3 参照）。

WHILE `ROUND` ≤ `MAX_ROUNDS` AND (`CRITICAL_COUNT` > 0 OR `RESIDUAL_COUNT` > 0):
# MAX_ROUNDS に達して Critical または残指摘事項が残存した場合は、修正を適用してボーナスラウンドレビューを実施する（後述）。

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

### 2B: Count Critical findings and residual items

Read `{REVIEW_FILE}`. Count rows in Section 2 (指摘事項と対応内容) where 重要度列が 🔴 で始まり、
かつ 対応状況列が `✅ 対応済` 以外（`⬜ 未対応`／`➖ 対応不要`）であるもの。
(`✅ 対応済` の行はレビュアーが直接検証・再確認した上で解消済みと判定した行であり、再度問題が
検出されない限りカウント対象から除外する。`➖ 対応不要` の行は引き続きカウント対象とする —
ここを除外すると、AI が不便な指摘を「対応不要」と自己判定してカウントを回避できる構造的欠陥が
再発するため（背景・目的参照）。レビューファイルはラウンドごとに上書きされるが、`✅ 対応済` の
判定は裁量動作ではなく、当該ラウンドにおける `TARGET_FILE` の最新内容への直接再検証を義務とする
規定（`agents/xddp-reviewer.md` の Output Contract）に基づく。カウント対象はそのラウンドの
レビューで報告された行のうち、上記条件を満たす 🔴 行の総数とする。)

Let `CRITICAL_COUNT` = that count.

Count rows in Section 2 where 重要度列が 🟡 または 🔵 で始まり、かつ 対応状況列が `✅ 対応済` 以外
（`⬜ 未対応`／`➖ 対応不要`）であるもの（残滓的事項）。
(CRITICAL_COUNT と同じ除外規則。カウント対象はそのラウンドのレビューで報告された行のうち、
上記条件を満たす 🟡/🔵 行の総数とする。)

Let `RESIDUAL_COUNT` = that count.

**If `CRITICAL_COUNT` = 0 AND `RESIDUAL_COUNT` = 0:**
- Report: `"✅ ラウンド {ROUND}: Critical指摘ゼロ・残滓的事項ゼロ。"`
- Set `ROUND = ROUND + 1`. Break loop.

**If (`CRITICAL_COUNT` > 0 OR `RESIDUAL_COUNT` > 0) AND `ROUND` = `MAX_ROUNDS`:**
- Proceed to Step 2C, 2D, 2E (通常の修正フローと同じ手順で修正を適用する).
- After fixes applied, run ONE "bonus" review: execute Step 2A with `REVIEW_ROUND = MAX_ROUNDS + 1`, writing result to `{REVIEW_FILE}`.
- Read `{REVIEW_FILE}`. Recount `CRITICAL_COUNT`（🔴 rows, `✅ 対応済` の行は除外）and `RESIDUAL_COUNT`
  （🟡/🔵 rows, `✅ 対応済` の行は除外。`➖ 対応不要` の行は引き続きカウント対象）in Section 2.
- If `CRITICAL_COUNT` = 0 AND `RESIDUAL_COUNT` = 0:
  - Report: `"✅ ボーナスラウンド: Critical指摘ゼロ・残滓的事項ゼロ。"`
  - Set `ROUND = MAX_ROUNDS + 2`.
    # ROUND = MAX_ROUNDS + 2 の意図: Step 3 で `ROUND - 1 = MAX_ROUNDS + 1` となり、
    # ボーナスラウンドを含む実施ラウンド数が正確に反映される。
    # Break はこの後 WHILE 条件とは独立してループを即時終了するために使用する。
  - Break loop.
- If `CRITICAL_COUNT` > 0 OR `RESIDUAL_COUNT` > 0:
  - Report: `"⚠️ ボーナスラウンド後も 🔴 指摘が {CRITICAL_COUNT} 件、残滓的事項（🟡/🔵）が {RESIDUAL_COUNT} 件残存しています。"`
  - Append to `{REVIEW_FILE}`: `"⚠️ 最大ラウンド数（{MAX_ROUNDS}）+ ボーナスラウンド後も未解決のCritical指摘または残滓的事項あり。人間の確認が必要です。"`
  - Set `ROUND = MAX_ROUNDS + 2`. Break loop.
    # 失敗パスも同様に ROUND = MAX_ROUNDS + 2 + Break でループを明示終了する。

**If (`CRITICAL_COUNT` > 0 OR `RESIDUAL_COUNT` > 0) AND `ROUND` < `MAX_ROUNDS`:**
  → Proceed to Step 2C.

### 2C: Cross-section and cross-file investigation (修正前の横展開調査)

Before planning fixes, investigate whether the same issues exist elsewhere:

1. For each 🔴 item AND each residual item（🟡/🔵 の項目全件。ここでの「全件」は Step 2B でカウント対象
   となった行——すなわち、その時点の `CRITICAL_COUNT`／`RESIDUAL_COUNT` に含まれる `✅ 対応済` 以外の
   行——を指す。`✅ 対応済` 行は当該ラウンドで既に解消済みと直接再検証されている（`agents/xddp-reviewer.md`
   の Output Contract 参照）ため、横展開調査の対象に含めない）, identify the **root cause pattern** (e.g., "パスの不一致", "理由ラベル欠落",
   "Before/Afterの曖昧記述").
   🔵（開放的な改善提案）について項目2〜5（横断スキャン）を行う場合は、提案文言自体が複数ファイル・
   複数箇所への言及を含む場合に限定する。範囲が明示されていない単発の文言改善等の🔵には、項目1の
   root cause pattern 特定のみを行い、項目2〜5の横断スキャンは行わない（過剰な調査コストを避ける）。
2. **Cross-section scan:** Scan all other sections of `{PLAN_FILE}` for the same pattern. Add any matches to the fix list.
3. **Cross-file scan (listed files):** For ALL files listed in Section 2 (変更対象ファイル) and Section 4 (影響範囲), always check whether the fix pattern requires corresponding changes — do not skip even if the connection seems indirect. Add any required cross-file fixes to the fix list.
4. **Proactive same-type scan:** Identify the category of each changed file (e.g., skill, agent, template). Search for other files of the same category that may have the same issue pattern (e.g., if one skill has a wrong path reference, check other skills using the same path). Add any matches to the fix list.
5. **Degradation risk assessment:** For each planned fix, assess whether it breaks existing correct behavior:
   - If changing a skill invocation contract (引数・出力形式), identify all callers and verify compatibility.
   - If changing a template, identify all skills that reference it and verify they remain valid.
   - If changing xddp.common or a shared definition, verify all dependent skills are unaffected.
   - Flag any degradation risk in the fix list.

Compile `FIX_LIST`: ordered list of `(対象ファイル/セクション, 修正内容, 単一解/複数案, 選択肢一覧, デグレードリスク)`.

### 2D: Fix strategy — FIX_STRATEGY に基づく適用方針の決定

Categorize `FIX_LIST`:
- **単一解:** one clear solution exists.
- **複数案:** multiple viable approaches exist. Prepare 2+ options, flagging which is the ideal-state option.
- **残滓的事項（🟡/🔵）の適用範囲制約（単一解・複数案いずれの分類でも適用）:** 提案文言が指す変更が
  一意に定まる場合のみ単一解とする。提案が開放的・抽象的で、複数の異なる具体的な変更がいずれも
  「対応した」と言えてしまう場合は単一解に分類してはならず、複数案として扱う。さらに、AIによる
  分類自体が誤る可能性（開放的な提案を誤って単一解と判定してしまう等）を考慮し、🟡/🔵 を `FIX_LIST`
  へ含めて適用する際は、**分類結果が単一解・複数案のいずれであっても**、`FIX_STRATEGY` の値に関わらず
  提案文言の範囲を超えない最小限の解釈のみを採用し、提案者の意図を超える拡張的な変更を行わない
  （🔴/🟡の客観的な欠陥修正とは異なり、🔵は本質的に開放的な改善提案であり「唯一の正しい適用」が
  定義できない場合があるため。この制約は分類の正確性に依存せず、適用そのものに直接かかる歯止めである）。
  「提案文言の範囲」の判定基準は Step 2C 項目1の制限条件と同一の基準を用いる：提案文中に複数のファイルパス・
  複数のセクション名・複数の関数/手順名などが明示的に列挙されている場合に限り、その明示された範囲までを
  「提案文言の範囲」とみなす。単一のファイル・単一のセクションのみを指す提案、または対象が明示されて
  いない抽象的・開放的な提案については、提案文中で言及されている最小単位（該当箇所1か所）のみを
  適用範囲とし、それを超える推測的な拡張は行わない。

Apply behavior by `FIX_STRATEGY`:

**`FIX_STRATEGY = balanced` (default):**
- 単一解: apply without asking. Report the list with rationale before applying.
- 複数案: present ALL items (both categories) to the human in a single message. Wait for response before applying.

> **ラウンド {ROUND}: 🔴 Critical {CRITICAL_COUNT} 件 + 🟡/🔵 残滓的事項 {RESIDUAL_COUNT} 件 + 横展開 {N} 件の対応方針を確認します**
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
2. Apply cross-file fixes identified in Step 2C (listed files and same-type files).
3. After all applied, verify:
   - Section 2 lists all files now being changed (including any cross-file and same-type additions).
   - Section 4 reflects the actual impact of the full fix set.
   - Section 5 covers any new test scenarios introduced by the fixes.
4. **Degradation prevention verification:** For each fix applied, confirm that existing correct behavior is maintained. If any degradation risk flagged in Step 2C item 5 cannot be fully mitigated at the plan level, explicitly note it in Section 4 of `{PLAN_FILE}` so the implementer is aware.

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
> | 残存残滓的事項件数（🟡/🔵） | {RESIDUAL_COUNT} |
>
> {if CRITICAL_COUNT = 0 AND RESIDUAL_COUNT = 0:}
> ✅ Critical指摘・残滓的事項ともにありません。承認者がプランを確認し、ステータスを「承認済み」に更新してください。
>
> {if CRITICAL_COUNT > 0 OR RESIDUAL_COUNT > 0:}
> ⚠️ Critical指摘が {CRITICAL_COUNT} 件、残滓的事項（🟡/🔵）が {RESIDUAL_COUNT} 件残存しています。`{REVIEW_FILE}` を確認して手動修正後、再度 `/xddp.plan-review {PLAN_FILE}` を実行してください。

---
> **保守メモ:** このファイルを変更した場合は、`README.md`（スキル一覧テーブル）、`CLAUDE.md`（ステップ番号体系テーブル）、および新規設定キーを追加した場合は `xddp.config.md` テンプレートと `CLAUDE.md`（xddp.config.md の位置付け節）も合わせて更新すること。
