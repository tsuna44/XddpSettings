"""
specout_verify_counts.py — discovery-log.md の件数一致検証 CLI

指定した Wave の「### 実行コマンド一覧」テーブル（各コマンドIDの claimed ヒット行数）と、
その直後のヒット行テーブル（実際にテーブルへ記録された行数）を突き合わせ、
「### 件数一致検証」テーブルを生成・上書きする。ケースA（HIGH昇格）で廃棄されたスコープの
コマンドは「➖ 廃棄」として不一致対象から除外する（`04_specout-discovery-log-template.md` の
仕様どおり）。

ケースA廃棄の自動検出は「## 同名 MEDIUM シンボル・異スコープ重複ログ」テーブルの処置列を
ヒューリスティックに解析するベストエフォート実装であり、検出漏れがあっても安全側に倒れる
（漏れた場合は ⚠️ 不一致として可視化されるだけで、自動停止はしない。段階3の specout_bfs.py
導入後は件数一致が構造的に保証されるため、本スクリプトは以後も独立した回帰チェックとして残す）。

Usage:
  python3 specout_verify_counts.py --log DISCOVERY_LOG_MD --wave N

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        失敗時は exit code 非0 + stderr にメッセージ。
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


def _split_row(line: str) -> list:
    if "|" not in line:
        return []
    return [p.strip() for p in line.split("|")[1:-1]]


def _join_row(cells: list) -> str:
    return "| " + " | ".join(cells) + " |"


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
    """「## 同名 MEDIUM シンボル・異スコープ重複ログ」の処置列からケースA廃棄スコープを抽出する。"""
    _, start, end = _find_section(
        lines, lambda s: s.startswith("## 同名 MEDIUM シンボル・異スコープ重複ログ")
    )
    if start is None:
        return set()
    header_idx, data_start, data_end = _find_table(
        lines, start, end, lambda cells: cells[0] == "Wave" and "処置" in cells
    )
    if header_idx is None:
        return set()
    header = _split_row(lines[header_idx])
    wave_col = header.index("Wave")
    action_col = header.index("処置")
    discarded = set()
    wave_label = f"Wave {wave}"
    for i in range(data_start, data_end):
        cells = _split_row(lines[i])
        if len(cells) <= max(wave_col, action_col):
            continue
        if wave_label not in cells[wave_col]:
            continue
        for m in DISCARD_RE.finditer(cells[action_col]):
            discarded.add(m.group(1))
    return discarded


def cmd_verify(args) -> None:
    log_path = Path(args.log)
    lines = _load(log_path)
    wave = args.wave
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
        cells = _split_row(lines[i])
        if len(cells) <= max(id_col, hit_col, scope_col):
            continue
        cmd_id = cells[id_col]
        claimed[cmd_id] = int(cells[hit_col]) if cells[hit_col].strip().lstrip("-").isdigit() else 0
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
            cells = _split_row(lines[i])
            if len(cells) <= hits_id_col:
                continue
            cmd_id = cells[hits_id_col]
            recorded[cmd_id] = recorded.get(cmd_id, 0) + 1
    else:
        hits_end = exec_end

    discarded_scopes = _detect_discarded_scopes(lines, wave)

    mismatches = []
    excluded = []
    result_rows = []
    for cmd_id in order:
        scope = scopes.get(cmd_id, "")
        is_discarded = any(ds in scope for ds in discarded_scopes) if discarded_scopes else False
        c = claimed[cmd_id]
        r = recorded.get(cmd_id, 0)
        if is_discarded:
            mark = "➖ 廃棄（ケースA, 次波でHIGH昇格済）"
            excluded.append(cmd_id)
        elif c == r:
            mark = "✅"
        else:
            mark = f"⚠️ {cmd_id} 件数不一致（ヒット{c}件/記録{r}件）"
            mismatches.append(cmd_id)
        result_rows.append([cmd_id, str(c), str(r), mark])

    table_lines = [
        "### 件数一致検証",
        "",
        "| コマンドID | ヒット行数（生） | 記録行数 | 一致 |",
        "|---|---|---|---|",
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
        replace_end = verify_end
        lines[replace_start:replace_end] = table_lines
    else:
        insertion_point = hits_end
        lines[insertion_point:insertion_point] = [""] + table_lines

    with open(log_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    print(json.dumps({
        "ok": True, "wave": wave, "checked": order, "mismatches": mismatches, "excluded": excluded,
    }, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--wave", required=True, type=int)
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
