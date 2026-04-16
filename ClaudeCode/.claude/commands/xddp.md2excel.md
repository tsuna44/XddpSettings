---
description: CRS Markdown から USDM 形式の Excel を生成する。「ExcelファイルをCRSから生成して」「変更要求仕様書のExcelを出力して」などで起動する。
---

Delegate to the **xddp.md2excel** skill:

1. Read `{CR}/03_change-requirements/CRS-{CR}.md` and parse UR/SR/SP hierarchy.
2. Generate Excel with the standard 6-column USDM layout:
   - UR行: A=【ユーザ要求】 B=ID C=title D=reason
   - SR行: A=【SR】 B=空 C=ID D=title E=reason（1カラム右にインデント）
   - SP 3行構成: タイトル行(F5F5F5) + Before行(FFF2CC) + After行(E2EFDA)
3. Apply colors, fonts, borders, column widths per spec.
4. Add 変更履歴 sheet.
5. Save to `{CR}/03_change-requirements/CRS-{CR}.xlsx`.
6. Report UR/SR/SP 件数と出力パスを日本語で報告。

See `ClaudeCode/.claude/skills/xddp.md2excel.md` for full orchestration logic.
