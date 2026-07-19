"""
chd_sp_coverage.py — CRS×CHD トレーサビリティマトリクスの SP カバレッジ照合 CLI

CRS の「## 2. USDM 要求仕様」に定義された全SP-ID（`EXPECTED_SP_IDS`）と、各リポジトリの CHD
（変更設計書）「## 4. トレーサビリティマトリクス」に記載された SP-ID（変更ファイル列が `-` でない行、
`COVERED_SP_IDS`）を突き合わせ、欠落 SP-ID（`MISSING`）を JSON で出力する。CHD ファイルの解決は
`xddp.common/SKILL.md`「## Discover CHD Files」と同じロジック（インデックスファイルの
「## 2. UR別ファイル一覧」テーブルから内容ファイルを辿る。`cross` は分割対象外の単一ファイル）を
機械実装したもの。

Usage:
  python3 chd_sp_coverage.py --crs CRS_PATH --design-dir DESIGN_DIR --repos repo1,repo2[,cross] --cr CR
  python3 chd_sp_coverage.py --crs CRS_PATH --design-dir DESIGN_DIR --repos repo1,repo2 --cr CR --list-only

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import json
import re
import sys
from pathlib import Path

SP_ID_RE = re.compile(r"SP-\d+-\d+\.\d+")
SECTION2_HEADING_RE = re.compile(r"^## 2\.")
NEXT_H2_RE = re.compile(r"^## ")
CHD_INDEX_TABLE_HEADING = "## 2. UR別ファイル一覧"
TM_HEADING = "## 4. トレーサビリティマトリクス"
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _split(raw: str) -> list:
    return [s.strip() for s in raw.split(",") if s.strip()]


def _split_row(line: str) -> list:
    if "|" not in line:
        return []
    return [p.strip() for p in line.split("|")[1:-1]]


def extract_expected_sp_ids(crs_path: Path) -> list:
    if not crs_path.exists():
        _err(f"CRS ファイルが見つかりません: {crs_path}")
    lines = crs_path.read_text(encoding="utf-8").split("\n")
    start = None
    for i, line in enumerate(lines):
        if SECTION2_HEADING_RE.match(line.strip()):
            start = i + 1
            break
    if start is None:
        # Section 2 見出しが見つからない場合はファイル全体を対象にフォールバックする
        text = "\n".join(lines)
    else:
        end = start
        while end < len(lines) and not NEXT_H2_RE.match(lines[end].strip()):
            end += 1
        text = "\n".join(lines[start:end])
    ids = sorted(set(SP_ID_RE.findall(text)))
    return ids


def resolve_chd_content_files(design_dir: Path, repo: str, cr: str):
    if repo == "cross":
        f = design_dir / "cross" / f"CHD-{cr}-cross.md"
        if not f.exists():
            return None, []
        return f, [f]
    index_file = design_dir / repo / f"CHD-{cr}.md"
    if not index_file.exists():
        return index_file, []
    lines = index_file.read_text(encoding="utf-8").split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == CHD_INDEX_TABLE_HEADING:
            start = i + 2
            break
    content_files = []
    if start is not None:
        i = start
        while i < len(lines) and lines[i].strip().startswith("|"):
            cells = _split_row(lines[i])
            for cell in cells:
                for m in MD_LINK_RE.finditer(cell):
                    target = m.group(1).strip()
                    content_files.append((index_file.parent / target).resolve())
            i += 1
    return index_file, content_files


def extract_covered_sp_ids(content_file: Path) -> list:
    if not content_file.exists():
        return []
    lines = content_file.read_text(encoding="utf-8").split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == TM_HEADING:
            start = i + 2
            break
    if start is None:
        return []
    covered = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        cells = _split_row(lines[i])
        if len(cells) >= 3:
            sp_id, changed_file = cells[0], cells[2]
            if changed_file != "-" and SP_ID_RE.fullmatch(sp_id):
                covered.append(sp_id)
        i += 1
    return covered


def cmd_run(args) -> None:
    design_dir = Path(args.design_dir)
    repos = _split(args.repos)
    by_repo = {}
    covered_all = set()
    for repo in repos:
        index_file, content_files = resolve_chd_content_files(design_dir, repo, args.cr)
        repo_covered = set()
        for cf in content_files:
            repo_covered.update(extract_covered_sp_ids(Path(cf)))
        covered_all.update(repo_covered)
        by_repo[repo] = {
            "chd_index": str(index_file) if index_file else None,
            "content_files": [str(f) for f in content_files],
            "covered": sorted(repo_covered),
        }

    if args.list_only:
        print(json.dumps({"ok": True, "by_repo": by_repo}, ensure_ascii=False))
        return

    if not args.crs:
        _err("--crs は --list-only 指定時以外は必須です")
    expected = extract_expected_sp_ids(Path(args.crs))
    missing = sorted(set(expected) - covered_all)
    print(json.dumps({
        "ok": True,
        "expected": expected,
        "covered": sorted(covered_all),
        "missing": missing,
        "by_repo": by_repo,
    }, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crs", required=False, default=None)
    parser.add_argument("--design-dir", required=True)
    parser.add_argument("--repos", required=True)
    parser.add_argument("--cr", required=True)
    parser.add_argument("--list-only", action="store_true")
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
