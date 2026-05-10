You are executing XDDP Excel → Markdown Conversion.

**Arguments:** $ARGUMENTS = [CR_NUMBER]（省略可） [EXCEL_FILE_PATH]（CR省略時は XDDP_DIR 配下から自動検出）

Delegate to the **xddp.excel2md** skill:

1. Locate the Excel file in `{CR}/03_change-requirements/` or use EXCEL_FILE_PATH.
2. Parse USDM structure from Excel (UR → SR → SP hierarchy with before/after rows).
3. Detect changes vs. existing `CRS-{CR}.md`.
4. Apply additions, modifications, deletions to the Markdown CRS and update TM.
5. Report all changes applied.

See `.claude/skills/xddp.excel2md.md` for full orchestration logic.
