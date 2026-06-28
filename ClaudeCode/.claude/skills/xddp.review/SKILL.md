---
description: XDDP AIレビュー単体実行: 人が直接編集した成果物に対してAIレビューを実施する。「AIレビューして」「レビューして」などで起動する。
argument-hint: "[CR番号] analysis|req|specout|arch|design|test"
---

You are executing **XDDP Review — Standalone AI Review**.

> This review is the checkpoint before an artifact advances. Honest, thorough critique here prevents failures in every downstream step. Do not let familiarity or politeness dilute the quality of this review.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) DOCUMENT_TYPE
- CR_NUMBER: e.g. `CR-2026-001` (optional; auto-detected from XDDP_DIR if omitted)
- DOCUMENT_TYPE: `analysis` | `req` | `specout` | `arch` | `design` | `test` | (file path)

---

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.
Let `DOCUMENT_TYPE` = first token of `REST_ARGS`.

(xddp.config.md lookup done in xddp.common/SKILL.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CR_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}`.

## 1. Resolve document mapping

| DOCUMENT_TYPE | DOCUMENT_TYPE (reviewer) | TARGET_FILE | REFERENCE_FILES | OUTPUT_FILE |
|---|---|---|---|---|
| `analysis` | `ANA` | `{CR_PATH}/02_analysis/ANA-{CR}.md` | `{CR_PATH}/01_requirements/` (all .md) | `{CR_PATH}/02_analysis/review/02_analysis-review.md` |
| `req` | `CRS` | `{CR_PATH}/03_change-requirements/CRS-{CR}.md` | `{CR_PATH}/01_requirements/` (all .md), `{CR_PATH}/02_analysis/ANA-{CR}.md` | `{CR_PATH}/03_change-requirements/review/03_change-requirements-review.md` |
| `specout` | `SPO` | `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` (ask user for `{repo}` if not specified; for single-repo use the only REPOS: entry) | `{CR_PATH}/01_requirements/` (all .md), `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/{repo}/modules/` (all *-spo.md), `{CR_PATH}/04_specout/cross/` (all .md, if exists) | `{CR_PATH}/04_specout/{repo}/review/04_specout-review.md` |
| `arch` | `DSN` | TARGET_FILE の決定: `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-comparison.md` が存在する場合（2案以上）: これを TARGET_FILE とする。存在しない場合（1案）: `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-A.md` を TARGET_FILE とする。（`{repo}` が未指定の場合: IS_MULTI ならユーザーに確認、単一リポジトリなら REPOS_KEYS[0]） | `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md`, `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-A.md` （comparison.md が TARGET の場合）, `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-B.md` （exists の場合）, `{CR_PATH}/05_architecture/{repo}/DSN-{CR}-approach-C.md` （exists の場合） | `{CR_PATH}/05_architecture/{repo}/review/05_architecture-review.md` |
| `design` | `CHD` | 単一バッチファイル（「## 1b. design TARGET_FILE の解決」参照） | `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` | `{CR_PATH}/06_design/{repo}/review/06_design-review-{UR-ID}[-{N}].md` |
| `test` | `TSP` | `{CR_PATH}/09_test-spec/{repo}/TSP-{CR}.md` (ask user for `{repo}` if not specified) | `{CR_PATH}/06_design/{repo}/` の CHD内容ファイル全件（「## 1c. test REFERENCE_FILES の解決」参照）, `{CR_PATH}/03_change-requirements/CRS-{CR}.md`, `{CR_PATH}/04_specout/{repo}/SPO-{CR}.md` | `{CR_PATH}/09_test-spec/{repo}/review/09_test-spec-review.md` |
| other | treat DOCUMENT_TYPE as file path | — | — | `{CR_PATH}/review/manual-review.md` |

If DOCUMENT_TYPE is omitted: ask the user which document to review.

## 1b. design TARGET_FILE の解決

CHDは現在インデックス＋UR別内容ファイルに分割されている。`design` の単体AIレビューは元々1ファイル単位の
ため、複数ファイル一括レビューには拡張しない。

1. `{repo}` が未指定の場合: IS_MULTI ならユーザーに確認、単一リポジトリなら REPOS_KEYS[0]。
2. Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
   CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
   → let `CHD_CONTENT_FILES`.
3. `CHD_CONTENT_FILES` が複数件の場合: 候補一覧（UR ID・バッチ番号）をユーザーに提示し、
   レビュー対象とする単一ファイルを選ばせる。1件のみの場合はそのまま使用する。
4. 選択されたファイルを `TARGET_FILE` とする。

**明示する限界:** 単一バッチファイルのみを対象とする単体AIレビューでは、選んだファイルが属するUR
（SP範囲）が、CRS全体や他バッチとの間でどう整合するか（バッチ間の重複・矛盾・参照漏れ等）はレビュー対象外。
バッチ間整合性は `/xddp.06.design` の Step A2（カバレッジ自動検証）と工程8 TM生成の衝突チェックでのみ
機械的に検証される。複数バッチに渡る設計意図の整合性確認は人レビューの責務として残る。

## 1c. test REFERENCE_FILES の解決

`test` 行では CHD は TARGET_FILE（`TSP-{CR}.md`）ではなく REFERENCE_FILES として現れる。
「ユーザーに単一ファイルを選ばせる」処理（1b.）は適用しない（選ぶべきTARGET_FILEが存在しないため）。

Read `~/.claude/skills/xddp.common/SKILL.md`, apply "## Discover CHD Files" with:
  CR_PATH: {CR_PATH}, REPO_NAME: {repo}, CR: {CR}
→ let `CHD_CONTENT_FILES`.
REFERENCE_FILES に `CHD_CONTENT_FILES` の全件を展開する（TSPレビューがCRS全体のSP網羅性を確認するために
CHD全体への参照が必要なため。1ファイルに絞ると退化する）。

## 1a. Resolve NEXT_DOCUMENT_TYPE

| DOCUMENT_TYPE (reviewer) | NEXT_DOCUMENT_TYPE |
|---|---|
| `ANA` | `CRS` |
| `CRS` | `SPO` |
| `SPO` | `DSN` |
| `DSN` | `CHD` |
| `CHD` | `TSP` |
| `TSP` | （なし） |
| `SPEC` | （なし） |
| `PLAN` | （なし） |
| `other`（ファイルパス直指定） | （なし） |

Set `NEXT_DOC` = the mapped value above. If "（なし）", set `NEXT_DOC` = empty string.

## 2. Verify target file exists

Check that TARGET_FILE exists. If not found, tell the user and stop.

## 2.5. Ensure output directory exists

Run `mkdir -p {parent directory of OUTPUT_FILE}` using Bash to create the review output directory if it does not exist.

## 3. Run AI review

Use the **Agent tool** with `subagent_type=xddp-reviewer` and pass:
```
DOCUMENT_TYPE: {resolved type}
TARGET_FILE: {resolved target}
REFERENCE_FILES: {resolved references}
REVIEW_ROUND: 1
OUTPUT_FILE: {resolved output}
（NEXT_DOC が空でない場合のみ）NEXT_DOCUMENT_TYPE: {NEXT_DOC}
```

## 4. Report in Japanese

Read OUTPUT_FILE and show the user:
- 総合判定（✅ 合格 / 🔁 要修正）
- 指摘件数（重大 / 軽微 / 提案）
- レビュー結果ファイルのパス

If 🔴 or 🟡 issues exist, suggest:
> 修正後に再度レビューする場合は `/xddp.review {CR} {DOCUMENT_TYPE}` を実行してください。
> 指摘を反映する場合は `/xddp.revise {CR} {DOCUMENT_TYPE}` を使用してください。
