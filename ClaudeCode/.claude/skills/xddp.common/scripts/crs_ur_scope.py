"""
crs_ur_scope.py — CRS Markdown から指定 UR のスコープを抽出する CLI

CRS（変更要求仕様書）全文のうち、`xddp.06.design` Step B・`xddp.feedback` Step 1-code-d の
per-UR CHD レビューが実際に参照する範囲——「1. 変更概要」（Section 1）・指定 UR の見出し
サブツリー（Section 2 該当部分。USDM Canonical: UR=H4）・「3.1 要求〜仕様 対応表」の該当UR行
（Section 3.1）——のみを機械的に抽出し `--out` に書き出す。意味判定を含まない決定的処理であり、
CRS 全体の CRS×CHD 網羅性チェックは別途 `chd_sp_coverage.py` が担う（本スクリプトは代替しない）。

Usage:
  python3 crs_ur_scope.py --crs CRS_PATH --ur-id UR_ID --out OUT_PATH

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, "ur_found": bool, "tm_rows": N}）。
        `--ur-id` に一致する UR 見出しが見つからない場合も exit 0・`ur_found: false` を返す
        （呼び出し元 SKILL.md 側で BATCH_PLAN との不整合として fail-loud に扱う）。
        `--crs` が存在しない場合等の使用法エラーのみ exit 非0 + stderr。
"""

import argparse
import json
import re
import sys
from pathlib import Path

SECTION2_HEADING_RE = re.compile(r"^## 2\.")
NEXT_H1_TO_H4_RE = re.compile(r"^#{1,4}\s")
TM_SUBSECTION_RE = re.compile(r"^### 3\.1")


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _split_row(line: str) -> list:
    r"""Markdown テーブル行をセルへ分割する（`chd_sp_coverage.py` と同じ `\|` エスケープ対応）。"""
    if "|" not in line:
        return []
    return [p.strip().replace(r"\|", "|") for p in re.split(r"(?<!\\)\|", line)[1:-1]]


def extract_section1(lines: list) -> str:
    """ファイル先頭から最初の `## 2.` 見出し行の直前までを丸ごと返す。"""
    end = len(lines)
    for i, line in enumerate(lines):
        if SECTION2_HEADING_RE.match(line.strip()):
            end = i
            break
    return "\n".join(lines[:end]).rstrip("\n")


def extract_ur_subtree(lines: list, ur_id: str):
    """指定 UR の見出し（H4）行から、次の H1〜H4 見出し行の直前までを返す。

    見つからない場合は None（BATCH_PLAN と CRS の不整合を示す）。
    """
    ur_heading_re = re.compile(rf"^####\s+{re.escape(ur_id)}\b")
    start = None
    for i, line in enumerate(lines):
        if ur_heading_re.match(line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if NEXT_H1_TO_H4_RE.match(lines[i]):
            end = i
            break
    return "\n".join(lines[start:end]).rstrip("\n")


def extract_tm_rows(lines: list, ur_id: str):
    """`### 3.1` 見出し・テーブルヘッダ2行・対象 UR に一致する行のみを返す。

    戻り値: (heading_line または None, header_lines（0〜2行）, matched_rows)。
    `### 3.1` 見出しが見つからない場合は (None, [], [])。
    """
    heading_idx = None
    for i, line in enumerate(lines):
        if TM_SUBSECTION_RE.match(line.strip()):
            heading_idx = i
            break
    if heading_idx is None:
        return None, [], []
    heading_line = lines[heading_idx]
    j = heading_idx + 1
    while j < len(lines) and not lines[j].strip().startswith("|"):
        if lines[j].strip().startswith("## "):
            return heading_line, [], []
        j += 1
    if j >= len(lines):
        return heading_line, [], []
    header_lines = lines[j:j + 2]
    matched = []
    k = j + 2
    while k < len(lines) and lines[k].strip().startswith("|"):
        cells = _split_row(lines[k])
        if cells and cells[0] == ur_id:
            matched.append(lines[k])
        k += 1
    return heading_line, header_lines, matched


def build_output(section1: str, ur_id: str, ur_body: str, tm_heading, tm_header_lines: list, tm_rows: list) -> str:
    parts = [section1, "", f"## 2. USDM 要求仕様（UR抜粋: {ur_id}）", ""]
    if ur_body:
        parts.append(ur_body)
        parts.append("")
    parts.append("## 3. トレーサビリティマトリクス（TM・UR抜粋）")
    if tm_heading is not None:
        parts.append("")
        parts.append(tm_heading)
        if tm_header_lines:
            parts.append("")
            parts.extend(tm_header_lines)
            parts.extend(tm_rows)
    return "\n".join(parts).rstrip("\n") + "\n"


def cmd_run(args) -> None:
    crs_path = Path(args.crs)
    if not crs_path.exists():
        _err(f"CRS ファイルが見つかりません: {crs_path}")
    lines = crs_path.read_text(encoding="utf-8").split("\n")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    section1 = extract_section1(lines)
    ur_body = extract_ur_subtree(lines, args.ur_id)
    if ur_body is None:
        out_path.write_text(section1.rstrip("\n") + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "ur_found": False, "tm_rows": 0}, ensure_ascii=False))
        return

    tm_heading, tm_header_lines, tm_rows = extract_tm_rows(lines, args.ur_id)
    out_path.write_text(
        build_output(section1, args.ur_id, ur_body, tm_heading, tm_header_lines, tm_rows),
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "ur_found": True, "tm_rows": len(tm_rows)}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crs", required=True)
    parser.add_argument("--ur-id", required=True, dest="ur_id")
    parser.add_argument("--out", required=True)
    parser.set_defaults(func=cmd_run)
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
