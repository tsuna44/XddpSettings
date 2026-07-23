"""
excel_dump.py — Excelファイルの全セルをタブ区切りテキストとして標準出力にダンプする

xddp.excel2md/SKILL.md から、人が編集したExcel（USDM形式のCRS）の内容を読み取るために呼び出される。

Usage: python excel_dump.py <EXCEL_PATH>
"""
import sys

import openpyxl


def dump(excel_path: str) -> None:
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active
    for row in ws.iter_rows():
        print("\t".join("" if c.value is None else str(c.value) for c in row))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python excel_dump.py <EXCEL_PATH>")
    dump(sys.argv[1])
