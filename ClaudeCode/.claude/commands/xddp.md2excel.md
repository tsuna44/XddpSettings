---
description: CRS Markdown から USDM 形式の Excel を生成する。「ExcelファイルをCRSから生成して」「変更要求仕様書のExcelを出力して」などで起動する。
---

Delegate to the **xddp.md2excel** skill:

1. `~/.claude/templates/crs_md2excel.py` を Bash 経由で実行し、CRS Markdown から Excel を生成する。
2. Save to `{CR}/03_change-requirements/CRS-{CR}.xlsx`.
3. Report UR/SR/SP 件数と出力パスを日本語で報告。

See `ClaudeCode/.claude/skills/xddp.md2excel.md` for full orchestration logic.
