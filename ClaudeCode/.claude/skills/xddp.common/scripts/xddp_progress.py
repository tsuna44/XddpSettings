"""
xddp_progress.py — progress.md 更新 CLI

XDDPのprogress.mdは「工程進捗」Markdownテーブル（列: #, 工程, 担当, 状態, 詳細ステップ,
成果物, 完了日）と「## 備考・メモ」セクション（⚠️ 行＝一時的な警告・平文行＝恒久的な履歴）で
状態を管理する。本スクリプトはこのテーブル・セクションの読み書きを決定的に行い、
LLM は結果JSONを確認するだけでよいようにする。

Usage:
  python3 xddp_progress.py update --cr-path CR_PATH --step STEP --state STATE [--detail DETAIL] [--artifact-link LINK]
  python3 xddp_progress.py note-add --cr-path CR_PATH --step STEP --text TEXT
  python3 xddp_progress.py note-remove --cr-path CR_PATH --step STEP
  python3 xddp_progress.py history-add --cr-path CR_PATH --step STEP --text TEXT
  python3 xddp_progress.py show --cr-path CR_PATH --step STEP
  python3 xddp_progress.py close-state --cr-path CR_PATH --state STATE [--detail DETAIL]

`close-state` は「## 工程進捗」テーブル（工程1〜11専用）とは別枠の `xddp.close` 自身の実行状態
（`## xddp.close 進捗` セクション）を管理する（xddp.close はテーブルに行を持たないため）。

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

PROGRESS_TABLE_HEADER = "| # | 工程 | 担当 | 状態 | 詳細ステップ | 成果物 | 完了日 |"
NOTES_HEADING = "## 備考・メモ"
CLOSE_STATE_HEADING = "## xddp.close 進捗"
LAST_UPDATED_PREFIX = "**最終更新：**"
COMPLETE_STATE = "✅ 完了"


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _progress_path(cr_path: str) -> Path:
    return Path(cr_path) / "progress.md"


def _read(path: Path) -> list:
    if not path.exists():
        _err(f"progress.md が見つかりません: {path}")
    return path.read_text(encoding="utf-8").split("\n")


def _write(path: Path, lines: list) -> None:
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _today() -> str:
    return datetime.date.today().isoformat()


def _split_row(line: str) -> list:
    if "|" not in line:
        return []
    parts = line.split("|")
    return [p.strip() for p in parts[1:-1]]


def _join_row(cells: list) -> str:
    return "| " + " | ".join(cells) + " |"


def _find_table_bounds(lines: list):
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip() == PROGRESS_TABLE_HEADER:
            header_idx = i
            break
    if header_idx is None:
        _err("工程進捗テーブルが見つかりません（ヘッダ行不一致）。テンプレートが変更されていないか確認してください。")
    start = header_idx + 2  # ヘッダ行の次（区切り行）の、さらに次から
    end = start
    while end < len(lines) and lines[end].strip().startswith("|"):
        end += 1
    return start, end


def _find_row(lines: list, step: str):
    start, end = _find_table_bounds(lines)
    for i in range(start, end):
        cells = _split_row(lines[i])
        if cells and cells[0] == step:
            return i, cells
    return None, None


def _update_last_updated(lines: list) -> None:
    for i, line in enumerate(lines):
        if line.startswith(LAST_UPDATED_PREFIX):
            lines[i] = f"{LAST_UPDATED_PREFIX} {_today()}"
            return


def _find_section_bounds(lines: list, heading: str):
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i + 1
            break
    if start is None:
        return None, None
    end = start
    while end < len(lines) and not (lines[end].strip().startswith("## ") or lines[end].strip() == "---"):
        end += 1
    return start, end


def _ensure_notes_section(lines: list):
    start, end = _find_section_bounds(lines, NOTES_HEADING)
    if start is not None:
        return start, end
    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(NOTES_HEADING)
    lines.append("")
    start = len(lines)
    return start, start


def _remove_warning_lines(lines: list, step: str) -> int:
    start, end = _find_section_bounds(lines, NOTES_HEADING)
    if start is None:
        return 0
    prefix = f"⚠️ 工程{step}:"
    removed = 0
    i = start
    while i < end:
        if lines[i].strip().startswith(prefix):
            del lines[i]
            end -= 1
            removed += 1
        else:
            i += 1
    return removed


def cmd_update(args) -> None:
    path = _progress_path(args.cr_path)
    lines = _read(path)
    idx, cells = _find_row(lines, args.step)
    if idx is None:
        _err(f"ステップ番号 {args.step} の行が見つかりません")
    if len(cells) != 7:
        _err(f"工程進捗テーブルの列数が想定と異なります（{len(cells)}列): {lines[idx]}")
    cells[3] = args.state
    if args.detail is not None:
        cells[4] = args.detail
    if args.artifact_link:
        cells[5] = args.artifact_link
    cells[6] = _today() if args.state == COMPLETE_STATE else "-"
    lines[idx] = _join_row(cells)
    _update_last_updated(lines)
    removed = _remove_warning_lines(lines, args.step) if args.state == COMPLETE_STATE else 0
    _write(path, lines)
    print(json.dumps({
        "ok": True, "step": args.step, "state": args.state, "detail": cells[4],
        "warning_lines_removed": removed,
    }, ensure_ascii=False))


def cmd_note_add(args) -> None:
    path = _progress_path(args.cr_path)
    lines = _read(path)
    start, end = _ensure_notes_section(lines)
    text = f"⚠️ 工程{args.step}: {args.text}"
    lines.insert(end, text)
    _write(path, lines)
    print(json.dumps({"ok": True, "added": text}, ensure_ascii=False))


def cmd_note_remove(args) -> None:
    path = _progress_path(args.cr_path)
    lines = _read(path)
    removed = _remove_warning_lines(lines, args.step)
    _write(path, lines)
    print(json.dumps({"ok": True, "removed_count": removed}, ensure_ascii=False))


def cmd_history_add(args) -> None:
    path = _progress_path(args.cr_path)
    lines = _read(path)
    start, end = _ensure_notes_section(lines)
    lines.insert(end, args.text)
    _write(path, lines)
    print(json.dumps({"ok": True, "added": args.text}, ensure_ascii=False))


def cmd_close_state(args) -> None:
    path = _progress_path(args.cr_path)
    lines = _read(path)
    start, end = _find_section_bounds(lines, CLOSE_STATE_HEADING)
    if start is None:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append(CLOSE_STATE_HEADING)
        lines.append("")
        start = len(lines)
        end = start
    detail = args.detail
    if detail is None:
        for i in range(start, end):
            m = re.match(r"^\*\*詳細ステップ：\*\*\s*(.*)$", lines[i].strip())
            if m:
                detail = m.group(1)
                break
        if detail is None:
            detail = "-"
    new_block = [f"**状態：** {args.state}", f"**詳細ステップ：** {detail}", ""]
    lines[start:end] = new_block
    _write(path, lines)
    print(json.dumps({"ok": True, "state": args.state, "detail": detail}, ensure_ascii=False))


def cmd_show(args) -> None:
    path = _progress_path(args.cr_path)
    lines = _read(path)
    idx, cells = _find_row(lines, args.step)
    if idx is None:
        _err(f"ステップ番号 {args.step} の行が見つかりません")
    print(json.dumps({
        "ok": True, "step": cells[0], "phase": cells[1], "owner": cells[2],
        "state": cells[3], "detail": cells[4], "artifact": cells[5],
        "completed_date": cells[6],
    }, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_update = sub.add_parser("update")
    p_update.add_argument("--cr-path", required=True)
    p_update.add_argument("--step", required=True)
    p_update.add_argument("--state", required=True)
    p_update.add_argument("--detail", default=None,
                           help="省略時は既存の詳細ステップを変更しない（例: 🔁 差し戻し時に状態のみ更新する場合）")
    p_update.add_argument("--artifact-link", default=None)
    p_update.set_defaults(func=cmd_update)

    p_note_add = sub.add_parser("note-add")
    p_note_add.add_argument("--cr-path", required=True)
    p_note_add.add_argument("--step", required=True)
    p_note_add.add_argument("--text", required=True)
    p_note_add.set_defaults(func=cmd_note_add)

    p_note_remove = sub.add_parser("note-remove")
    p_note_remove.add_argument("--cr-path", required=True)
    p_note_remove.add_argument("--step", required=True)
    p_note_remove.set_defaults(func=cmd_note_remove)

    p_history_add = sub.add_parser("history-add")
    p_history_add.add_argument("--cr-path", required=True)
    p_history_add.add_argument("--step", required=True)
    p_history_add.add_argument("--text", required=True)
    p_history_add.set_defaults(func=cmd_history_add)

    p_close_state = sub.add_parser("close-state")
    p_close_state.add_argument("--cr-path", required=True)
    p_close_state.add_argument("--state", required=True)
    p_close_state.add_argument("--detail", default=None)
    p_close_state.set_defaults(func=cmd_close_state)

    p_show = sub.add_parser("show")
    p_show.add_argument("--cr-path", required=True)
    p_show.add_argument("--step", required=True)
    p_show.set_defaults(func=cmd_show)

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
