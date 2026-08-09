"""
specout_verify_counts.py — discovery-log.md の件数一致検証 CLI

指定した Wave の「### 実行コマンド一覧」テーブル（各コマンドIDの claimed ヒット行数＝生）と、
その直後のヒット行テーブル（実際にテーブルへ記録された行数）を突き合わせ、
「### 件数一致検証」テーブルを生成・上書きする。ケースA（HIGH昇格）で廃棄されたスコープの
コマンドは「➖ 廃棄」として不一致対象から除外する（`04_specout-discovery-log-template.md` の
仕様どおり）。

PLAN-20260804 Phase 1 以降、commit-wave は dedup除外（過去波で分類済みの再出現）・フィルタ除外
（保守的な行コメント除外）を「### 件数一致検証」テーブルへ記録する。PLAN-20260806 Phase 2A 以降は
noise-collapse除外（前倒し縮退で代表行以外を除外した分）も同テーブルへ記録する。本スクリプトはそれを
入力として読み、**生 = 記録 + dedup除外 + フィルタ除外 + noise-collapse除外** で照合する（列が無い
旧ログでは該当列を 0 とみなし、従来どおり 生 == 記録 で照合する後方互換）。

ケースA廃棄の自動検出は「## 同名 MEDIUM シンボル・異スコープ重複ログ」テーブルの処置列を
ヒューリスティックに解析するベストエフォート実装であり、検出漏れがあっても安全側に倒れる
（漏れた場合は ⚠️ 不一致として可視化されるだけで、自動停止はしない。段階3の specout_bfs.py
導入後は件数一致が構造的に保証されるため、本スクリプトは以後も独立した回帰チェックとして残す）。

Usage:
  python3 specout_verify_counts.py --log DISCOVERY_LOG_MD --wave (N|all) [--strict]

Output: stdout に JSON 1オブジェクト
        {"ok": true, "waves": [{"wave", "checked", "mismatches", "excluded"}, ...], "mismatch_waves": [...]}。
        `--wave N` の単波指定でも `waves` は要素数1のリストになる。

終了コード: 0=成功 / 1=検証の実行エラー（ログ破損等） / 2=使用法エラー（argparse 既定） /
           3=件数不一致（`--strict` 指定時のみ）。
"""

import argparse
import json
import re
import sys
from pathlib import Path

DISCARD_RE = re.compile(r"`([^`]+)`[^`]{0,20}廃棄")


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _md_cell(value) -> str:
    """Markdown テーブルのセル値をエスケープする（specout_bfs.py の同名関数と同一規約）。"""
    s = "" if value is None else str(value)
    return s.replace("|", r"\|").replace("\n", " ").replace("\r", " ")


def _split_row(line: str) -> list:
    r"""Markdown テーブル行をセルへ分割する。

    `specout_bfs.py` は `_md_cell()` でセル内の `|` を `\|` へエスケープして書き出す。
    ここでは「直前が `\` でない `|`」のみを区切りとして扱い、分割後にエスケープを戻す。

    前提: 書き出し側は列区切りを必ず ` | ` と空白でパディングする（`_md_cell` の docstring 参照）。
    この前提により、セル値の末尾が `\` でも区切り判定は誤らない。
    """
    if "|" not in line:
        return []
    cells = re.split(r"(?<!\\)\|", line)[1:-1]
    return [c.strip().replace(r"\|", "|") for c in cells]


def _join_row(cells: list) -> str:
    r"""セル列を Markdown テーブル行へ組み立てる（`_split_row` の逆変換）。

    `_split_row` がアンエスケープして返す以上、書き戻し側は再エスケープしなければ
    読み書きが非対称になり、`\|` が生 `|` へ戻って列を壊す。
    """
    return "| " + " | ".join(_md_cell(c) for c in cells) + " |"


def _row_cells_or_err(line: str, line_no: int, header_cols: int, table_label: str) -> list:
    r"""データ行をセルへ分割し、列数がヘッダと一致しなければ fail-loud する。

    列数が合わない行は、セル内の未エスケープ `|` でテーブルが壊れている。
    従来はこれを黙って読み飛ばす／別セルを読むため、「生0件 / 記録N件」といった
    誤った検証結果を返していた（PLAN-20260808 不具合1）。サイレント縮退を禁止する。
    """
    cells = _split_row(line)
    if len(cells) != header_cols:
        _err(
            f"discovery-log.md の '{table_label}' 行 {line_no} の列数がヘッダと一致しません"
            f"（ヘッダ {header_cols} 列 / データ {len(cells)} 列）。"
            f"セル内の未エスケープ `|` が原因の可能性があります: {line[:120]}"
        )
    return cells


def _find_section(lines: list, heading_predicate, start: int = 0):
    for i in range(start, len(lines)):
        if heading_predicate(lines[i].strip()):
            section_start = i + 1
            end = section_start
            while end < len(lines) and not lines[end].strip().startswith("## "):
                end += 1
            return i, section_start, end
    return None, None, None


def _find_table(lines: list, start: int, end: int, header_predicate):
    for i in range(start, end):
        cells = _split_row(lines[i])
        if cells and header_predicate(cells):
            data_start = i + 2
            data_end = data_start
            while data_end < end and lines[data_end].strip().startswith("|"):
                data_end += 1
            return i, data_start, data_end
    return None, None, None


def _load(log_path: Path) -> list:
    if not log_path.exists():
        _err(f"discovery-log.md が見つかりません: {log_path}")
    return log_path.read_text(encoding="utf-8").split("\n")


def _detect_discarded_scopes(lines: list, wave: int) -> set:
    """「## 同名 MEDIUM シンボル・異スコープ重複ログ」の処置列からケースA廃棄スコープを抽出する。

    当該セクションは commit-wave が波ごとに新規追記するため文書内に複数存在しうる。
    全セクションを走査しないと、最初にケースAが発生した波以外で偽の不一致が出る。
    """
    discarded = set()
    wave_label = f"Wave {wave}"
    scan_from = 0
    while True:
        # commit-wave は当該セクションを波ごとに新規追記するため、同名の H2 見出しが
        # ケースA発生波の数だけ並ぶ（specout_bfs.py の `if case_rows:` 配下）。
        # 最初の1つだけを読むと、最初に発生した波以外の廃棄スコープを取りこぼす。
        _, sec_start, sec_end = _find_section(
            lines, lambda s: s.startswith("## 同名 MEDIUM シンボル・異スコープ重複ログ"),
            start=scan_from,
        )
        if sec_start is None:
            break
        header_idx, data_start, data_end = _find_table(
            lines, sec_start, sec_end, lambda cells: cells[0] == "Wave" and "処置" in cells
        )
        if header_idx is not None:
            header = _split_row(lines[header_idx])
            wave_col = header.index("Wave")
            action_col = header.index("処置")
            for i in range(data_start, data_end):
                cells = _row_cells_or_err(
                    lines[i], i + 1, len(header),
                    "## 同名 MEDIUM シンボル・異スコープ重複ログ（発生時のみ記録）",
                )
                if wave_label not in cells[wave_col]:
                    continue
                for m in DISCARD_RE.finditer(cells[action_col]):
                    discarded.add(m.group(1))
        scan_from = sec_end  # 次の同名セクションを探す
    return discarded


def _read_prev_drops(lines: list, start: int, end: int) -> dict:
    """既存の「### 件数一致検証」テーブルから dedup除外/フィルタ除外/noise-collapse除外 を読む
    （PLAN-20260804 Phase 1、PLAN-20260806 Phase 2A）。commit-wave が書いた列を独立再チェックの
    入力とする。列が無い旧ログでは空 dict（＝0扱い）。noise-collapse除外列のみ無い場合は 0 とみなす。"""
    header_idx, data_start, data_end = _find_table(
        lines, start, end, lambda cells: cells and cells[0] == "コマンドID" and "記録行数" in cells,
    )
    if header_idx is None:
        return {}
    header = _split_row(lines[header_idx])
    if "dedup除外" not in header or "フィルタ除外" not in header:
        return {}
    id_col = header.index("コマンドID")
    d_col = header.index("dedup除外")
    f_col = header.index("フィルタ除外")
    nc_col = header.index("noise-collapse除外") if "noise-collapse除外" in header else None
    drops = {}
    for i in range(data_start, data_end):
        cells = _row_cells_or_err(lines[i], i + 1, len(header), "### 件数一致検証")
        d = int(cells[d_col]) if cells[d_col].strip().lstrip("-").isdigit() else 0
        f = int(cells[f_col]) if cells[f_col].strip().lstrip("-").isdigit() else 0
        nc = 0
        # 列数は厳密一致が保証済みのため `len(cells) > nc_col` は常に真（到達不能ガードのため削除）。
        # 旧ログ（noise-collapse除外列なし）への後方互換は `nc_col is not None` が担う。
        if nc_col is not None and cells[nc_col].strip().lstrip("-").isdigit():
            nc = int(cells[nc_col])
        drops[cells[id_col]] = (d, f, nc)
    return drops


def _verify_one_wave(log_path: Path, lines: list, wave: int) -> dict:
    heading, wave_start, wave_end = _find_section(lines, lambda s: s == f"## Wave {wave}")
    if heading is None:
        _err(f"discovery-log.md に '## Wave {wave}' セクションが見つかりません")

    exec_header, exec_start, exec_end = _find_table(
        lines, wave_start, wave_end,
        lambda cells: cells[0] == "コマンドID" and "対象スコープ" in cells,
    )
    if exec_header is None:
        _err(f"Wave {wave} の '### 実行コマンド一覧' テーブルが見つかりません")
    exec_cols = _split_row(lines[exec_header])
    id_col = exec_cols.index("コマンドID")
    hit_col = exec_cols.index("ヒット行数（生）")
    scope_col = exec_cols.index("対象スコープ")

    claimed = {}
    scopes = {}
    order = []
    for i in range(exec_start, exec_end):
        # 列数チェックは旧 `continue` より前に置く。len(cells) == len(exec_cols) が成り立てば
        # 必ず len(cells) > max(id_col, hit_col, scope_col) となるため旧ガードは冗長であり、
        # 後置すると「列数が不足する行」が無音でスキップされて (D) の趣旨と矛盾する。
        cells = _row_cells_or_err(lines[i], i + 1, len(exec_cols), "### 実行コマンド一覧")
        cmd_id = cells[id_col]
        if not cells[hit_col].strip().lstrip("-").isdigit():
            _err(
                f"discovery-log.md の '### 実行コマンド一覧' 行 {i + 1} の"
                f"「ヒット行数（生）」が数値ではありません: {cells[hit_col]!r}"
            )
        claimed[cmd_id] = int(cells[hit_col])
        scopes[cmd_id] = cells[scope_col]
        order.append(cmd_id)

    hits_header, hits_start, hits_end = _find_table(
        lines, exec_end, wave_end,
        lambda cells: cells[0] == "行ID" and "コマンドID" in cells,
    )
    recorded = {cmd_id: 0 for cmd_id in order}
    if hits_header is not None:
        hits_cols = _split_row(lines[hits_header])
        hits_id_col = hits_cols.index("コマンドID")
        for i in range(hits_start, hits_end):
            cells = _row_cells_or_err(lines[i], i + 1, len(hits_cols), "ヒット行テーブル")
            cmd_id = cells[hits_id_col]
            recorded[cmd_id] = recorded.get(cmd_id, 0) + 1
    else:
        hits_end = exec_end

    discarded_scopes = _detect_discarded_scopes(lines, wave)
    # PLAN-20260804 Phase 1: dedup除外/フィルタ除外、PLAN-20260806 Phase 2A: noise-collapse除外 は
    # commit-wave が「### 件数一致検証」テーブルへ記録する。独立再チェックである本スクリプトはそれを
    # 入力として読み、生 = 記録 + dedup + filter + noise-collapse で照合する
    # （列が無い旧ログは該当分を 0 とみなし後方互換で照合）。
    prev_drops = _read_prev_drops(lines, exec_end, wave_end)

    mismatches = []
    excluded = []
    result_rows = []
    for cmd_id in order:
        scope = scopes.get(cmd_id, "")
        is_discarded = any(ds in scope for ds in discarded_scopes) if discarded_scopes else False
        c = claimed[cmd_id]
        r = recorded.get(cmd_id, 0)
        d, f, nc = prev_drops.get(cmd_id, (0, 0, 0))
        if is_discarded:
            mark = "➖ 廃棄（ケースA, 次波でHIGH昇格済）"
            excluded.append(cmd_id)
        elif c == r + d + f + nc:
            mark = "✅" if (d == 0 and f == 0 and nc == 0) else f"✅（dedup {d}/filter {f}/noise-collapse {nc} 除外）"
        else:
            mark = f"⚠️ {cmd_id} 件数不一致（生{c}件/記録{r}+除外{d + f + nc}件）"
            mismatches.append(cmd_id)
        result_rows.append([cmd_id, str(c), str(d), str(f), str(nc), str(r), mark])

    table_lines = [
        "### 件数一致検証",
        "",
        "| コマンドID | ヒット行数（生） | dedup除外 | フィルタ除外 | noise-collapse除外 | 記録行数 | 一致 |",
        "|---|---|---|---|---|---|---|",
    ]
    table_lines.extend(_join_row(row) for row in result_rows)
    table_lines.append("")

    verify_header, verify_start, verify_end = _find_table(
        lines, exec_end, wave_end,
        lambda cells: cells[0] == "コマンドID" and "記録行数" in cells,
    )
    if verify_header is not None:
        # 既存の「### 件数一致検証」見出し（テーブル直前の行）から次の空行までを丸ごと置換する
        heading_idx = verify_header - 2 if verify_header - 2 >= 0 and lines[verify_header - 2].strip() == "### 件数一致検証" else verify_header
        replace_start = heading_idx
        # table_lines は末尾に空行を含む（上記）。既存テーブル直後の空行を置換範囲へ含めないと
        # 再実行のたびに空行が1行ずつ増え、ログがドリフトする（冪等でなくなる）。
        replace_end = verify_end
        while replace_end < len(lines) and lines[replace_end].strip() == "":
            replace_end += 1
        lines[replace_start:replace_end] = table_lines
    else:
        insertion_point = hits_end
        lines[insertion_point:insertion_point] = [""] + table_lines

    with open(log_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    return {"wave": wave, "checked": order, "mismatches": mismatches, "excluded": excluded}


def cmd_verify(args) -> None:
    log_path = Path(args.log)
    lines = _load(log_path)
    if args.wave == "all":
        # discovery-log 内の `## Wave N` 見出しを昇順に列挙する。
        # 同一波の見出しが複数ある異常ログは重複検証になるため、番号で一意化する。
        waves = sorted({int(m.group(1)) for m in
                        (re.match(r"^## Wave (\d+)\s*$", ln.strip()) for ln in lines) if m})
        if not waves:
            # 波が1つも無い＝まだ commit-wave が1回も走っていない。検証対象なしは正常。
            print(json.dumps({"ok": True, "waves": [], "mismatch_waves": []}, ensure_ascii=False))
            return
    else:
        if not args.wave.lstrip("-").isdigit():
            _err(f"--wave には整数または `all` を指定してください: {args.wave!r}")
        waves = [int(args.wave)]

    results = []
    for w in waves:
        # _verify_one_wave はテーブルを書き戻すため、波ごとに読み直す
        lines = _load(log_path)
        results.append(_verify_one_wave(log_path, lines, w))

    mismatch_waves = [r["wave"] for r in results if r["mismatches"]]
    print(json.dumps({
        "ok": True,  # `ok` は「実行が成功したか」であり不一致の有無とは独立（他スクリプトと同義）
        "waves": results, "mismatch_waves": mismatch_waves,
    }, ensure_ascii=False))
    if args.strict and mismatch_waves:
        # 不一致は「discovery-log の記録が生ヒット数と合わない」＝成果物の欠落を意味する。
        # 自動実行（SKILL からの配線）では無音で流さず、終了コードで呼び出し側へ伝える。
        # 各波の ⚠️ 行は既に書き出し済みで stdout の JSON にも残るため監査証跡は失われない。
        sys.exit(EXIT_MISMATCH)


EXIT_MISMATCH = 3  # 件数不一致（--strict 時）。エラー（_err の exit 1）および
                   # argparse の使用法エラー／インタプリタのファイル未検出（いずれも exit 2）と区別する


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument(
        "--wave", required=True,
        help="検証する波番号。`all` を指定すると discovery-log 内の全 `## Wave N` を昇順に検証する",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help=f"件数不一致が1件でもあれば exit {EXIT_MISMATCH} とする（自動実行の配線用）",
    )
    parser.set_defaults(func=cmd_verify)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — CLI境界でのエラーはstderrへ集約する
        _err(f"予期しないエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
