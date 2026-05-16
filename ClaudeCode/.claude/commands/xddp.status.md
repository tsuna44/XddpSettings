You are executing XDDP Status Check (進捗確認).

**Arguments:** $ARGUMENTS = CR_NUMBER (e.g., `REQ-2026-001`). If omitted, search the current directory for any `*/progress.md` files.

---

## Instructions

### 1. Locate progress files
If CR_NUMBER is given:
- Read `{CR_NUMBER}/progress.md`.

If no argument:
- Find all `*/progress.md` files in the current directory and read each.

### 2. Display status report in Japanese

For each CR found, display:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 CR: {CR番号} — {タイトル}
開始日: {開始日}  最終更新: {最終更新日}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

工程進捗:
| # | 工程              | 担当   | 状態   | 完了日     |
|---|-------------------|--------|--------|------------|
| 1 | 要求書作成        | 人     | ✅     | YYYY-MM-DD |
| 2 | 要求分析・整理    | AI     | ✅     | YYYY-MM-DD |
...

現在のフェーズ: {最後に完了した工程 + 1}
完了工程数: {X} / 15
```

### 2.5. Per-repo progress (when IS_MULTI)

If `progress.md` contains per-repo progress tables (e.g., "工程9 コーディング進捗（リポジトリ別）"):
- Display each table as-is so the user can see repo-level granularity.

### 3. Check for pending review issues
For each CR, scan `{CR_NUMBER}/review/` and all `{CR_NUMBER}/{step}/{repo}/review/` folders for review files containing "⚠️ 未解決の重大指摘あり". If found, display a warning.

### 4. List available artifacts
Read `REPOS:` from `xddp.config.md` (if present) to determine repo list.
Display which output files exist for the CR, organized by repo:

| 成果物 | {repo-a} | {repo-b} | cross/ |
|---|---|---|---|
| SPO | ✅/- | ✅/- | ✅/- |
| DSN | ✅/- | ✅/- | ✅/- |
| CHD | ✅/- | ✅/- | ✅/- |
| TSP | ✅/- | ✅/- | ✅/- |
| TRS | ✅/- | ✅/- | ✅/- |
| VERIFY | ✅/- | ✅/- | ✅/- |
| latest-specs | ✅/- | ✅/- | ✅/- |

Single-repo: show a simple flat list (ANA, CRS, SPO, DSN, CHD, TSP, TRS, VERIFY, latest-specs).

### 5. If multiple CRs are active
Check for file conflicts: if two CRs have modified the same source files (compare CHD Section 2 across CRs), warn about potential conflicts and suggest running `/xddp.conflict {CR1} {CR2}`.
