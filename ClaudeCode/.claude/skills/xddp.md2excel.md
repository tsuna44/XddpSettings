---
description: CRS Markdown から USDM 形式の Excel を生成する（UR-017/018/020）。「ExcelファイルをCRSから生成して」「変更要求仕様書のExcelを出力して」などで起動する。
---

You are executing **XDDP CRS → Excel Generation** (Markdown → Excel).

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional)
- CR_NUMBER: optional; auto-detected from XDDP_DIR if omitted

---

Read `~/.claude/skills/xddp.common.md`, apply "## CR Resolution" with $ARGUMENTS → let `CR`, `REST_ARGS`.

(xddp.config.md lookup done in xddp.common.md; reuse WORKSPACE_ROOT, XDDP_DIR.)
Let `CRS_PATH` = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.md`
Let `OUT_PATH`  = `{WORKSPACE_ROOT}/{XDDP_DIR}/{CR}/03_change-requirements/CRS-{CR}.xlsx`

---

## 1. Generate Excel

`~/.claude/templates/crs_md2excel.py` handles all of: Markdown parsing, Excel generation, and change history sheet output.

Run via Bash:

```bash
python ~/.claude/templates/crs_md2excel.py {CRS_PATH} {OUT_PATH}
```

If errors occur, display them directly to the user.
If `~/.claude/templates/crs_md2excel.py` is not found, tell the user to run `setup.sh`.

---

## 2. Save and report

Report in Japanese: output path and UR/SR/SP counts.
Get counts from script stdout (`Generated: ... (rows: N)`).
Individual UR/SR/SP counts may be derived from `parse_crs_md()` output if needed.
