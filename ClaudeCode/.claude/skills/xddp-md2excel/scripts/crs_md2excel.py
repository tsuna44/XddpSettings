"""
crs_md2excel.py — XDDP 変更要求仕様書 Markdown → Excel 変換スクリプト

Usage: python crs_md2excel.py <CRS_MD_PATH> <OUTPUT_XLSX_PATH>

CRS Markdown のパース自体は `xddp-common/scripts/crs_model.py`（`xddp-crs-view` と共有する
共通パーサ）に委譲する。本ファイルは Excel レンダリングのみを担当する。

Expected CRS Markdown structure (USDM Canonical heading system — H1〜H6 のみ使用):
  ## 2. USDM 要求仕様
    ### ＜カテゴリ名＞                          (H3。機能要求／非機能要求)
      #### {CR}-UR-xxx タイトル                (H4。形式 B: CR 名前空間先頭。例 CR-2026-970-UR-001)
        ##### ＜要求グループ名＞                (H5)
          - **分割軸：** ...                    (要求グループ見出し直後の子リスト)
          ###### {CR}-SR-xxx-yyy タイトル      (H6。例 CR-2026-970-SR-001-001)
            **＜仕様グループ名＞**              (太字行)
            - **{CR}-SP-xxx-yyy.zzz**: タイトル (リスト項目。属性は2スペース子リスト。例 CR-2026-970-SP-001-001.010)
              - **Before：** ...
              - **After：** ...
              - **懸念・検討事項：** ...
  ## 5. 未決事項          (Markdown table)
  ## 6. 気づき・提案メモ  (Markdown table)
  ## 付記A. スコープ外事項              (Markdown table, optional)
  ## 付記B. 前提条件・実装参考情報      (Markdown table, optional)
  ## 付記C. 関連する既存処理            (Markdown table, optional)
  ## 7. 変更履歴          (Markdown table → 変更履歴 sheet)

1階層パターン（SR なし。UR→仕様グループ→SP）の SP は `URItem.direct_sp_list` に格納され、
SR ブロックを挟まず UR ブロックの直後に出力される。

Excel row structure (6 columns: A–F):
  カテゴリ バナー行 (1行): A=【カテゴリ】  B=name
  要求グループ バナー行 (1行): B=【要求グループ】  C=name  D=分割軸（あれば）
  仕様グループ バナー行 (1行): C=【仕様グループ】  D=name

  UR 3〜4行セット (D9E1F2, bold):
    Row1: A=【ユーザ要求】  B={CR}-UR-x  C=title  D=''  E=''  F=status
    Row2: A=''  B=理由  C=reason  ...
    Row3: A=''  B=説明  C=explanation  ...
    Row4（懸念があれば）: A=''  B=懸念・検討事項  C=kenen  ...

  SR 3〜4行セット (E7E6E6, bold):
    Row1: A=【システム要求】  B=''  C={CR}-SR-x-y  D=title  ...  F=status
    Row2: A=''  B=''  C=理由  D=reason  ...
    Row3: A=''  B=''  C=説明  D=explanation  ...
    Row4（懸念があれば）: A=''  B=''  C=懸念・検討事項  D=kenen  ...

  SP title  (F5F5F5, normal):  A–F = ''  C=title
  SP Before (FFF2CC): A=【仕様】  C={CR}-SP-x-y.z  D=■ Before  E=before  F=status
  SP After  (E2EFDA): D=■ After  E=after
  SP 理由   (色指定): D=■ 理由  E=reason  (省略可)
  SP 備考   (FFF2CC): D=■ 備考   E=biko  (省略可)
  SP 懸念   (FCE4D6): D=■ 懸念・検討事項  E=kenen  (省略可)

Column widths: A=14, B=13, C=32, D=48, E=37.5, F=18
"""

import os
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xddp-common" / "scripts"))
from crs_model import parse_crs_md, SPItem, SRItem, URItem, CategoryItem  # noqa: E402


# ── Palette ──────────────────────────────────────────────────────────────────
C_HEADER  = "4472C4"
C_UR      = "D9E1F2"
C_SR      = "E7E6E6"
C_SP      = "F5F5F5"
C_BEFORE  = "FFF2CC"
C_AFTER   = "E2EFDA"
C_REASON  = "DDEBF7"
C_BIKO    = "FFF2CC"
C_KENEN   = "FCE4D6"
C_PEND_H  = "BDD7EE"
C_PEND    = "DDEBF7"
C_NOTES_H    = "C6EFCE"
C_NOTES      = "EBF1DE"
C_SCOPE_H    = "F4CCCC"
C_SCOPE      = "FCF4F4"
C_IMPL_REF_H    = "FFE5B4"
C_IMPL_REF      = "FFF8EC"
C_EXIST_PROC_H  = "D9D2E9"
C_EXIST_PROC    = "EDE7F6"
C_CATEGORY   = "2F5597"
C_REQ_GROUP  = "8EA9DB"
C_SPEC_GROUP = "B4C7E7"

def _fill(hex6): return PatternFill("solid", fgColor=hex6)
def _al(wrap=True): return Alignment(horizontal="left", vertical="top", wrap_text=wrap, indent=0)
def _bdr():
    t = Side(style="thin", color="BBBBBB")
    return Border(left=t, right=t, top=t, bottom=t)

def _cell(ws, row, col, value, color, bold, row_h=None, wrap=True):
    c = ws.cell(row=row, column=col)
    c.value     = value
    c.fill      = _fill(color)
    c.font      = Font(bold=bold, color="FFFFFF" if color in (C_HEADER, C_CATEGORY) else "000000")
    c.alignment = _al(wrap=wrap)
    c.border    = _bdr()
    if row_h is not None:
        ws.row_dimensions[row].height = row_h
    return c

def _row(ws, row, values_colors_bolds, row_h=None, wrap=True):
    """Write one full row. values_colors_bolds = list of (value, color, bold)."""
    for col, (val, clr, bld) in enumerate(values_colors_bolds, 1):
        _cell(ws, row, col, val, clr, bld, row_h if col == 1 else None, wrap=wrap)


# ── Public API ────────────────────────────────────────────────────────────────

def add_header_row(ws, row=1):
    labels = ["レベル", "ID", "内容", "理由・説明 / Before・After", "", "ステータス"]
    _row(ws, row, [(l, C_HEADER, True) for l in labels], row_h=20)


def add_ur_row(ws, row, ur_id, title, reason, explanation="", status="", kenen=""):
    """UR 3〜4行セット（縦配置）。次の行番号を返す。"""
    _row(ws, row,
         [("【ユーザ要求】", C_UR, True),
          (ur_id,           C_UR, True),
          (title,           C_UR, True),
          ("",              C_UR, True),
          ("",              C_UR, True),
          (status or "",    C_UR, True)],
         row_h=40)
    _row(ws, row + 1,
         [("",           C_UR, True),
          ("理由",       C_UR, True),
          (reason or "", C_UR, True),
          ("",           C_UR, True),
          ("",           C_UR, True),
          ("",           C_UR, True)])
    _row(ws, row + 2,
         [("",                  C_UR, True),
          ("説明",              C_UR, True),
          (explanation or "",   C_UR, True),
          ("",                  C_UR, True),
          ("",                  C_UR, True),
          ("",                  C_UR, True)])
    r = row + 3
    if kenen:
        _row(ws, r,
             [("",                  C_UR, True),
              ("懸念・検討事項",    C_UR, True),
              (kenen,               C_UR, True),
              ("",                  C_UR, True),
              ("",                  C_UR, True),
              ("",                  C_UR, True)])
        r += 1
    return r


def add_sr_row(ws, row, sr_id, title, reason, explanation="", status="", kenen=""):
    """SR 3〜4行セット（縦配置）。次の行番号を返す。"""
    _row(ws, row,
         [("【システム要求】", C_SR, True),
          ("",          C_SR, True),
          (sr_id,       C_SR, True),
          (title,       C_SR, True),
          ("",          C_SR, True),
          (status or "", C_SR, True)],
         row_h=40)
    _row(ws, row + 1,
         [("",           C_SR, True),
          ("",           C_SR, True),
          ("理由",       C_SR, True),
          (reason or "", C_SR, True),
          ("",           C_SR, True),
          ("",           C_SR, True)])
    _row(ws, row + 2,
         [("",                  C_SR, True),
          ("",                  C_SR, True),
          ("説明",              C_SR, True),
          (explanation or "",   C_SR, True),
          ("",                  C_SR, True),
          ("",                  C_SR, True)])
    r = row + 3
    if kenen:
        _row(ws, r,
             [("",                  C_SR, True),
              ("",                  C_SR, True),
              ("懸念・検討事項",    C_SR, True),
              (kenen,               C_SR, True),
              ("",                  C_SR, True),
              ("",                  C_SR, True)])
        r += 1
    return r


def add_category_row(ws, row, name):
    """カテゴリ バナー行（1行）。次の行番号を返す。"""
    _row(ws, row,
         [("【カテゴリ】", C_CATEGORY, True),
          (name,          C_CATEGORY, True),
          ("",            C_CATEGORY, True),
          ("",            C_CATEGORY, True),
          ("",            C_CATEGORY, True),
          ("",            C_CATEGORY, True)],
         row_h=22)
    return row + 1


def add_req_group_row(ws, row, name, axis=""):
    """要求グループ バナー行（1行。分割軸を含む）。次の行番号を返す。"""
    _row(ws, row,
         [("",                  C_REQ_GROUP, True),
          ("【要求グループ】",  C_REQ_GROUP, True),
          (name,                C_REQ_GROUP, True),
          (f"分割軸: {axis}" if axis else "", C_REQ_GROUP, True),
          ("",                  C_REQ_GROUP, True),
          ("",                  C_REQ_GROUP, True)])
    return row + 1


def add_spec_group_row(ws, row, name):
    """仕様グループ バナー行（1行）。次の行番号を返す。"""
    _row(ws, row,
         [("",                  C_SPEC_GROUP, False),
          ("",                  C_SPEC_GROUP, False),
          ("【仕様グループ】",  C_SPEC_GROUP, False),
          (name,                C_SPEC_GROUP, False),
          ("",                  C_SPEC_GROUP, False),
          ("",                  C_SPEC_GROUP, False)])
    return row + 1


def add_sp_rows(ws, start_row, sp_id, title, before, after, biko="", kenen="", status="", reason="", spec=""):
    """SP 3〜7行セット。次の行番号を返す。
    reason 行は After/仕様行の後・備考の前に出力する。
    spec が空でない場合は Before/After の代わりに仕様行を1行出力する。
    """
    r = start_row

    _row(ws, r,
         [("",      C_SP, False),
          ("",      C_SP, False),
          (title,   C_SP, False),
          ("",      C_SP, False),
          ("",      C_SP, False),
          ("",      C_SP, False)],
         wrap=False)
    r += 1

    if spec:
        _row(ws, r,
             [("【仕様】",       C_BEFORE, False),
              ("",               C_BEFORE, False),
              (sp_id,            C_BEFORE, False),
              ("■ 仕様",        C_BEFORE, False),
              (spec,             C_BEFORE, False),
              (status or "",     C_BEFORE, False)],
             row_h=45)
        r += 1
    else:
        _row(ws, r,
             [("【仕様】",       C_BEFORE, False),
              ("",               C_BEFORE, False),
              (sp_id,            C_BEFORE, False),
              ("■ Before",       C_BEFORE, False),
              (before or "",     C_BEFORE, False),
              (status or "",     C_BEFORE, False)],
             row_h=45)
        r += 1

        _row(ws, r,
             [("",               C_AFTER, False),
              ("",               C_AFTER, False),
              ("",               C_AFTER, False),
              ("■ After",        C_AFTER, False),
              (after or "",      C_AFTER, False),
              ("",               C_AFTER, False)],
             row_h=45)
        r += 1

    if reason:
        _row(ws, r,
             [("",           C_REASON, False),
              ("",           C_REASON, False),
              ("",           C_REASON, False),
              ("■ 理由",     C_REASON, False),
              (reason,       C_REASON, False),
              ("",           C_REASON, False)])
        r += 1

    if biko:
        _row(ws, r,
             [("",           C_BIKO, False),
              ("",           C_BIKO, False),
              ("",           C_BIKO, False),
              ("■ 備考",     C_BIKO, False),
              (biko,         C_BIKO, False),
              ("",           C_BIKO, False)])
        r += 1

    if kenen:
        _row(ws, r,
             [("",                   C_KENEN, False),
              ("",                   C_KENEN, False),
              ("",                   C_KENEN, False),
              ("■ 懸念・検討事項",   C_KENEN, False),
              (kenen,                C_KENEN, False),
              ("",                   C_KENEN, False)])
        r += 1

    return r


def add_pending_section(ws, row, items):
    """未決事項セクション。items = list of (number, title, content, deadline)。次の行番号を返す。"""
    r = row
    _row(ws, r,
         [("■ 未決事項", C_PEND_H, True),
          ("#",           C_PEND_H, True),
          ("項目",        C_PEND_H, True),
          ("内容",        C_PEND_H, True),
          ("対応期限",    C_PEND_H, True),
          ("",            C_PEND_H, True)],
         row_h=20)
    r += 1
    for num, title, content, deadline in items:
        _row(ws, r,
             [("",           C_PEND, False),
              (str(num),     C_PEND, False),
              (title or "",  C_PEND, False),
              (content or "",C_PEND, False),
              (deadline or "",C_PEND, False),
              ("",           C_PEND, False)])
        r += 1
    return r


def add_notes_section(ws, row, items):
    """気づき・提案メモセクション。items = list of (number, kind, content, policy)。次の行番号を返す。"""
    r = row
    _row(ws, r,
         [("■ 気づき・提案メモ", C_NOTES_H, True),
          ("#",                  C_NOTES_H, True),
          ("種別",               C_NOTES_H, True),
          ("内容",               C_NOTES_H, True),
          ("対応方針",           C_NOTES_H, True),
          ("",                   C_NOTES_H, True)],
         row_h=20)
    r += 1
    for num, kind, content, policy in items:
        _row(ws, r,
             [("",           C_NOTES, False),
              (str(num),     C_NOTES, False),
              (kind or "",   C_NOTES, False),
              (content or "",C_NOTES, False),
              (policy or "", C_NOTES, False),
              ("",           C_NOTES, False)])
        r += 1
    return r


def add_scope_out_section(ws, row, items):
    """スコープ外事項セクション。items = list of (number, target, reason, cr_text)。次の行番号を返す。"""
    r = row
    _row(ws, r,
         [("■ スコープ外事項", C_SCOPE_H, True),
          ("#",                C_SCOPE_H, True),
          ("対象",             C_SCOPE_H, True),
          ("除外理由",         C_SCOPE_H, True),
          ("CR原文",           C_SCOPE_H, True),
          ("",                 C_SCOPE_H, True)],
         row_h=20)
    r += 1
    for num, target, reason, cr_text in items:
        _row(ws, r,
             [("",              C_SCOPE, False),
              (str(num),        C_SCOPE, False),
              (target or "",    C_SCOPE, False),
              (reason or "",    C_SCOPE, False),
              (cr_text or "",   C_SCOPE, False),
              ("",              C_SCOPE, False)])
        r += 1
    return r


def add_impl_ref_section(ws, row, items):
    """前提条件・実装参考情報セクション。items = list of (number, kind, content, cr_text)。次の行番号を返す。"""
    r = row
    _row(ws, r,
         [("■ 前提条件・実装参考情報", C_IMPL_REF_H, True),
          ("#",                        C_IMPL_REF_H, True),
          ("種別",                     C_IMPL_REF_H, True),
          ("内容",                     C_IMPL_REF_H, True),
          ("CR原文",                   C_IMPL_REF_H, True),
          ("",                         C_IMPL_REF_H, True)],
         row_h=20)
    r += 1
    for num, kind, content, cr_text in items:
        _row(ws, r,
             [("",              C_IMPL_REF, False),
              (str(num),        C_IMPL_REF, False),
              (kind or "",      C_IMPL_REF, False),
              (content or "",   C_IMPL_REF, False),
              (cr_text or "",   C_IMPL_REF, False),
              ("",              C_IMPL_REF, False)])
        r += 1
    return r


def add_existing_procs_section(ws, row, items):
    """関連する既存処理セクション。items = list of (no, module_path, entry_point, behavior, req_id)。次の行番号を返す。"""
    r = row
    _row(ws, r,
         [("■ 関連する既存処理",       C_EXIST_PROC_H, True),
          ("#",                        C_EXIST_PROC_H, True),
          ("モジュール／ファイルパス", C_EXIST_PROC_H, True),
          ("処理名／エントリポイント", C_EXIST_PROC_H, True),
          ("現在の動作・役割",         C_EXIST_PROC_H, True),
          ("関連要求ID",               C_EXIST_PROC_H, True)],
         row_h=20)
    r += 1
    for num, module_path, entry_point, behavior, req_id in items:
        _row(ws, r,
             [("",                 C_EXIST_PROC, False),
              (str(num),           C_EXIST_PROC, False),
              (module_path or "",  C_EXIST_PROC, False),
              (entry_point or "",  C_EXIST_PROC, False),
              (behavior or "",     C_EXIST_PROC, False),
              (req_id or "",       C_EXIST_PROC, False)])
        r += 1
    return r


def set_column_widths(ws):
    ws.column_dimensions['A'].width = 14.0
    ws.column_dimensions['B'].width = 13.0
    ws.column_dimensions['C'].width = 32.0
    ws.column_dimensions['D'].width = 48.0
    ws.column_dimensions['E'].width = 37.5
    ws.column_dimensions['F'].width = 18.0


def add_history_sheet(wb, history_rows):
    """history_rows: list of (version, date, author, description)"""
    ws = wb.create_sheet("変更履歴")
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 22
    ws.column_dimensions['D'].width = 65

    for col, h in enumerate(["版数", "日付", "変更者", "変更内容"], 1):
        c = ws.cell(row=1, column=col)
        c.value = h
        c.fill  = _fill(C_HEADER)
        c.font  = Font(bold=True, color="FFFFFF")
        c.alignment = _al()
        c.border = _bdr()
    ws.row_dimensions[1].height = 20

    for ri, (ver, date, author, desc) in enumerate(history_rows, 2):
        for col, val in enumerate([ver, date, author, desc], 1):
            c = ws.cell(row=ri, column=col)
            c.value = val
            c.fill  = _fill(C_SP)
            c.font  = Font(bold=False, color="000000")
            c.alignment = _al()
            c.border = _bdr()
        ws.row_dimensions[ri].height = 50


# ── Top-level builder ────────────────────────────────────────────────────────

def _add_sp_list(ws, r, sp_list):
    """フラットな SP リストを、直前の SP と spec_group が変わるたびにバナー行を差し込みつつ出力する。
    次の行番号を返す。
    """
    prev_spec_group = None
    for sp in sp_list:
        if sp.spec_group != prev_spec_group:
            r = add_spec_group_row(ws, r, sp.spec_group) if sp.spec_group else r
            prev_spec_group = sp.spec_group
        r = add_sp_rows(ws, r, sp.sp_id, sp.title, sp.before, sp.after,
                        sp.biko, sp.kenen, sp.status, sp.reason, sp.spec)
    return r


def build_excel_from_md(md_path: str, out_path: str) -> None:
    """CRS Markdown を Excel に変換して out_path に保存する。"""
    data = parse_crs_md(md_path)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "変更要求仕様書"
    set_column_widths(ws)

    r = 1
    add_header_row(ws, r)
    r += 1

    for cat in data['categories']:
        r = add_category_row(ws, r, cat.name)
        for ur in cat.ur_list:
            r = add_ur_row(ws, r, ur.ur_id, ur.title, ur.reason, ur.explanation, ur.status, ur.kenen)
            # 1階層パターン（SR なし）の SP は、SR ブロックを挟まず UR ブロックの直後に出力する
            r = _add_sp_list(ws, r, ur.direct_sp_list)

            prev_req_group = None
            for sr in ur.sr_list:
                req_group_key = (sr.req_group, sr.axis)
                if req_group_key != prev_req_group:
                    r = add_req_group_row(ws, r, sr.req_group, sr.axis) if sr.req_group else r
                    prev_req_group = req_group_key
                r = add_sr_row(ws, r, sr.sr_id, sr.title, sr.reason, sr.explanation, sr.status, sr.kenen)
                r = _add_sp_list(ws, r, sr.sp_list)

    if data['pending']:
        r = add_pending_section(ws, r, data['pending'])
    if data['notes']:
        r = add_notes_section(ws, r, data['notes'])
    # スコープ外・実装参考情報・関連する既存処理はリストが空でもヘッダ行のみ出力する
    r = add_scope_out_section(ws, r, data['scope_out'])
    r = add_impl_ref_section(ws, r, data['impl_ref'])
    r = add_existing_procs_section(ws, r, data['exist_proc'])

    if data['history']:
        add_history_sheet(wb, data['history'])

    wb.save(out_path)
    print(f"Generated: {out_path}  (rows: {r - 1})")


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: python crs_md2excel.py <CRS_MD_PATH> <OUTPUT_XLSX_PATH>")
    md_path, out_path = sys.argv[1], sys.argv[2]
    if not out_path.lower().endswith(".xlsx"):
        sys.exit(f"Error: OUTPUT_XLSX_PATH must end with .xlsx — got: {out_path!r}")
    if not os.path.exists(md_path):
        sys.exit(f"Error: Markdown file not found: {md_path!r}")
    build_excel_from_md(md_path, out_path)
