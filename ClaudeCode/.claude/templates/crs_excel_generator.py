"""
CRS Excel Generator — XDDP 変更要求仕様書 Excel 生成スクリプト
Usage: python crs_excel_generator.py <output_path> [--version 1.0]

Expected row structure (6 columns: A–F):

  UR row    (D9E1F2, bold):
    A=【ユーザ要求】  B=UR-x  C=title  D=reason  E=''  F=''

  SR row    (E7E6E6, bold):
    A=【SR】  B=''  C=SR-x-y  D=title  E=reason  F=''

  SP title  (F5F5F5, normal):
    A=''  B=''  C=SP-title  D=''  E=''  F=''

  SP Before (FFF2CC, normal):
    A=【仕様】  B=''  C=SP-x-y.z  D='■ Before'  E=before  F=''

  SP After  (E2EFDA, normal):
    A=''  B=''  C=''  D='■ After'  E=after  F=''

Column widths: A=14, B=13, C=32, D=48, E=37.5, F=10
Row heights: header=20, UR/SR=40, SP-title=auto, SP-Before/After=45
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


# ── Palette ──────────────────────────────────────────────────────────────────
C_HEADER = "4472C4"
C_UR     = "D9E1F2"
C_SR     = "E7E6E6"
C_SP     = "F5F5F5"
C_BEFORE = "FFF2CC"
C_AFTER  = "E2EFDA"

def _fill(hex6): return PatternFill("solid", fgColor=hex6)
def _al():       return Alignment(horizontal="left", vertical="top", wrap_text=True, indent=0)
def _bdr():
    t = Side(style="thin", color="BBBBBB")
    return Border(left=t, right=t, top=t, bottom=t)

def _cell(ws, row, col, value, color, bold, row_h=None):
    c = ws.cell(row=row, column=col)
    c.value     = value
    c.fill      = _fill(color)
    c.font      = Font(bold=bold, color="FFFFFF" if color == C_HEADER else "000000")
    c.alignment = _al()
    c.border    = _bdr()
    if row_h is not None:
        ws.row_dimensions[row].height = row_h
    return c

def _row(ws, row, values_colors_bolds, row_h=None):
    """Write one full row. values_colors_bolds = list of (value, color, bold)."""
    for col, (val, clr, bld) in enumerate(values_colors_bolds, 1):
        _cell(ws, row, col, val, clr, bld, row_h if col == 1 else None)


# ── Public API ────────────────────────────────────────────────────────────────

def add_header_row(ws, row=1):
    labels = ["レベル", "ID", "内容", "理由・説明 / Before・After", "", ""]
    _row(ws, row, [(l, C_HEADER, True) for l in labels], row_h=20)


def add_ur_row(ws, row, ur_id, title, reason):
    """UR行: A=【ユーザ要求】 B=UR-x C=title D=reason"""
    _row(ws, row,
         [("【ユーザ要求】", C_UR, True),
          (ur_id,           C_UR, True),
          (title,           C_UR, True),
          (reason or "",    C_UR, True),
          ("",              C_UR, True),
          ("",              C_UR, True)],
         row_h=40)


def add_sr_row(ws, row, sr_id, title, reason):
    """SR行: A=【SR】 B='' C=SR-x-y D=title E=reason"""
    _row(ws, row,
         [("【システム要求】", C_SR, True),
          ("",          C_SR, True),
          (sr_id,       C_SR, True),
          (title,       C_SR, True),
          (reason or "", C_SR, True),
          ("",          C_SR, True)],
         row_h=40)


def add_sp_rows(ws, start_row, sp_id, title, before, after):
    """SP 3行セット: タイトル行 + Before行 + After行。書き込んだ次の行番号を返す。"""
    r = start_row

    # SP title row (F5F5F5)
    _row(ws, r,
         [("",      C_SP, False),
          ("",      C_SP, False),
          (title,   C_SP, False),
          ("",      C_SP, False),
          ("",      C_SP, False),
          ("",      C_SP, False)])
    # row height は auto のまま (row_h=None)
    r += 1

    # Before row (FFF2CC)
    _row(ws, r,
         [("【仕様】",       C_BEFORE, False),
          ("",               C_BEFORE, False),
          (sp_id,            C_BEFORE, False),
          ("■ Before",       C_BEFORE, False),
          (before or "",     C_BEFORE, False),
          ("",               C_BEFORE, False)],
         row_h=45)
    r += 1

    # After row (E2EFDA)
    _row(ws, r,
         [("",               C_AFTER, False),
          ("",               C_AFTER, False),
          ("",               C_AFTER, False),
          ("■ After",        C_AFTER, False),
          (after or "",      C_AFTER, False),
          ("",               C_AFTER, False)],
         row_h=45)
    r += 1

    return r


def set_column_widths(ws):
    ws.column_dimensions['A'].width = 14.0
    ws.column_dimensions['B'].width = 13.0
    ws.column_dimensions['C'].width = 32.0
    ws.column_dimensions['D'].width = 48.0
    ws.column_dimensions['E'].width = 37.5
    ws.column_dimensions['F'].width = 10.0


def add_history_sheet(wb, history_rows):
    """
    history_rows: list of (version, date, author, description)
    """
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


# ── Example: CRS-CR-2026-001 ──────────────────────────────────────────────────

def build_crs_cr2026_001(out_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "変更要求仕様書"
    set_column_widths(ws)

    r = 1
    add_header_row(ws, r); r += 1

    # UR-001
    add_ur_row(ws, r, "UR-001", "タスク追加時に優先度を指定したい",
        "タスク生成時点で重要度を明示することで、タスク一覧での並び替えやフィルタリングの基準となり、"
        "ユーザが重要なタスクを即座に把握できるようにするため"); r += 1

    add_sr_row(ws, r, "SR-001-001", "Task オブジェクトに priority 属性を付与する",
        "タスクに優先度情報を保持するために、Task オブジェクトおよびデータ永続化層が priority 属性を"
        "記録・管理できる状態にする必要があるため"); r += 1

    r = add_sp_rows(ws, r, "SP-001-001.001", "Task モデルへの priority フィールド追加",
        "Task オブジェクトは priority 属性を持たない",
        'Task オブジェクトに `priority: str` フィールドを追加する。許容値は "high", "medium", "low" に限定する')

    r = add_sp_rows(ws, r, "SP-001-001.002", "tasks.json への priority フィールド保存",
        "tasks.json に priority キーを含めない",
        '新規作成タスクの JSON 記録に `"priority": "high" | "medium" | "low"` キーを含めて保存する')

    add_sr_row(ws, r, "SR-001-002", "`add` コマンドに `--priority` オプションを追加する",
        "ユーザが新規タスク追加時に priority を明示的に指定するための CLI インターフェースが必要なため"); r += 1

    r = add_sp_rows(ws, r, "SP-001-002.001", "`add` コマンドのオプション仕様",
        "`add <タイトル>` のみサポートし、priority を指定できない",
        "`add <タイトル> [--priority {high|medium|low}]` をサポートする。"
        "`--priority` オプション省略時はデフォルト値 `medium` を使用する（UR-002）")

    # UR-002
    add_ur_row(ws, r, "UR-002", "優先度を省略したときにデフォルト値を自動適用してほしい",
        "省略時の既定動作を定めることで、既存スクリプト・ワークフローの互換性を保ちながら新機能を導入できるようにするため"); r += 1

    add_sr_row(ws, r, "SR-002-001", "`--priority` 省略時に priority のデフォルト値 medium を適用する",
        "`add` コマンドで `--priority` が省略された場合、または既存タスクのロード時に "
        "priority フィールドが欠落している場合、medium をデフォルト値として一貫して適用する必要があるため"); r += 1

    r = add_sp_rows(ws, r, "SP-002-001.001", "`add` コマンド実行時のデフォルト値設定",
        "`add` コマンドで priority 指定が省略されると priority 属性を設定しない",
        "`add` コマンドで `--priority` が省略された場合、priority を自動的に `medium` として設定する")

    r = add_sp_rows(ws, r, "SP-002-001.002", "既存タスクデータの後方互換読み込み",
        "priority フィールドのない既存タスクをロードすると、priority 属性を保持しない",
        "tasks.json 読み込み時に priority フィールドが欠落しているタスクは、priority を `medium` として扱う")

    # UR-003
    add_ur_row(ws, r, "UR-003", "優先度でタスク一覧をフィルタしたい",
        "指定した優先度のタスクのみを表示することで、重要タスク・低優先タスク等の分類ビューが実現でき、"
        "ユーザの関心に応じた情報フォーカスが可能になるため"); r += 1

    add_sr_row(ws, r, "SR-003-001", "`list` コマンドに `--priority` フィルタオプションを追加する",
        "ユーザが優先度でタスク検索・絞り込みを行うための CLI インターフェースが必要なため"); r += 1

    r = add_sp_rows(ws, r, "SP-003-001.001", "`list` コマンドの priority フィルタオプション仕様",
        "`list` コマンドは priority フィルタを持たない",
        "`list [--priority {high|medium|low}]` をサポートする。`--priority` 指定時は、"
        "該当する priority を持つタスクのみ出力する。未指定時は全タスクを出力する（既存動作変更なし）")

    # UR-004
    add_ur_row(ws, r, "UR-004", "優先度と status を同時にフィルタしたい",
        "優先度と完了状態を組み合わせた絞り込みにより、「高優先度で未完了」「低優先度で完了済み」等、"
        "複数条件での検索が可能になり、ユーザの作業効率が向上するため"); r += 1

    add_sr_row(ws, r, "SR-004-001", "priority と status を AND 条件でフィルタする",
        "`list` コマンドで priority と status が同時に指定された場合、"
        "両方の条件に合致するタスクのみ出力する必要があるため"); r += 1

    r = add_sp_rows(ws, r, "SP-004-001.001", "`list` コマンドの複数オプション AND 動作",
        "`list` コマンドは単一条件フィルタのみ対応する（status フィルタが既存実装の場合）",
        "`list` コマンド実行時に `--priority` と `--status` の両方が指定されたとき、"
        "両方の条件に合致するタスクのみを表示する（AND フィルタ）")

    # UR-005
    add_ur_row(ws, r, "UR-005", "既存タスクデータの後方互換性を維持したい",
        "priority フィールドなし既存タスクを読み込む際、デフォルト値で自動補完することで、"
        "既存ユーザのデータ資産を無変換で継続利用できるようにするため"); r += 1

    add_sr_row(ws, r, "SR-005-001", "priority フィールドのない既存データを後方互換で読み込む",
        "旧バージョンの tasks.json（priority フィールドなし）を新バージョンで読み込む際、"
        "priority を `medium` として一貫して扱う仕組みが必要なため"); r += 1

    r = add_sp_rows(ws, r, "SP-005-001.001", "既存タスクデータの後方互換読み込み",
        "priority フィールドのない既存タスクをロードすると、priority 属性を保持しない",
        "tasks.json 読み込み時に priority フィールドが欠落しているタスクは、priority を `medium` として扱う")

    # UR-NF-001
    add_ur_row(ws, r, "UR-NF-001", "既存コマンドの互換性を維持したい",
        "priority 機能を追加する際、既存ユーザのワークフロー・スクリプト連携が破損しないようにするため。"
        "既存スクリプトが依存する add / list / done / delete コマンドの引数・出力・終了コードが変化してはいけない"); r += 1

    add_sr_row(ws, r, "SR-NF-001-001", "既存コマンドの動作・インターフェースを変更しない（制約）",
        "`--priority` オプション追加後も既存コマンドが同じインターフェース・出力を保つことで、"
        "既存スクリプト・自動化連携の継続性が保証されるため"); r += 1

    r = add_sp_rows(ws, r, "SP-NF-001-001.001", "既存コマンドの引数・出力・終了コード維持",
        "`add` / `list` / `done` / `delete` コマンドは既存仕様で動作する",
        "priority オプション追加後も、既存の引数形式・出力フォーマット・終了コードを変更しない。"
        "`add <タイトル>` 形式での呼び出しが正常に動作し（priority = medium）、"
        "`list` 呼び出しで全タスクを表示し、`done` / `delete` は一切変更しない")

    # UR-NF-002
    add_ur_row(ws, r, "UR-NF-002", "不正な優先度値を入力できないようにしたい",
        "priority 値が high / medium / low 以外の不正な値で汚染されるのを防ぎ、"
        "データ整合性・システム動作の予測可能性を保証するため"); r += 1

    add_sr_row(ws, r, "SR-NF-002-001", "`--priority` オプションの入力値を検証する",
        "`add` / `list` コマンドで `--priority` が指定される全箇所で、"
        "許容値（high / medium / low）以外を拒否する仕組みが必要なため"); r += 1

    r = add_sp_rows(ws, r, "SP-NF-002-001.001", "優先度値のバリデーション仕様 ⚠️ 懸念あり",
        "priority 値を検証しない（データベースに任意の値が入る可能性がある）",
        "`add` / `list` コマンドで `--priority` オプションに high / medium / low 以外の値が指定されたとき、"
        "エラーメッセージを標準エラー出力に表示してコマンドを終了コード 1 で終了する")

    add_history_sheet(wb, [
        ("1.0", "2026-04-10", "AI（xddp-spec-writer-agent）",
         "初版作成。ANA-CR-2026-001 セクション2の分類結果に基づき、9個のUR（7機能要求 + 2非機能要求）に対応するSR/SPを定義"),
        ("1.1", "2026-04-10", "AI（xddp-spec-writer-agent）",
         "レビュー指摘対応（CRT-001: UR-005を独立URとして追加、CRT-002: UR要件数修正、CRT-003: フォールバック方針明記）"),
        ("1.2", "2026-04-15", "AI（Excel再生成）",
         "ID体系をUR-x/SR-x-y/SP-x-y.z形式に変更。階層インデント対応。SP 3行構成（タイトル/Before/After）に修正"),
    ])

    wb.save(out_path)
    print(f"Saved: {out_path}  (total rows: {r - 1})")


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "CRS-output.xlsx"
    build_crs_cr2026_001(out)
