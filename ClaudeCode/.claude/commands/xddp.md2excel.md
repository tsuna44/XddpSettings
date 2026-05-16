---
description: CRS Markdown から USDM 形式の Excel を生成する。「ExcelファイルをCRSから生成して」「変更要求仕様書のExcelを出力して」などで起動する。
---

Delegate to the **xddp.md2excel** skill:

1. Run `~/.claude/templates/crs_md2excel.py` via Bash to generate Excel from CRS Markdown.
2. Save to `{CR}/03_change-requirements/CRS-{CR}.xlsx`.
3. Report UR/SR/SP counts and output path in Japanese.

See `ClaudeCode/.claude/skills/xddp.md2excel.md` for full orchestration logic.
