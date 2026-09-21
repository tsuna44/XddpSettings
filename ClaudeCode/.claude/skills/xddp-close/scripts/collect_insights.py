"""collect_insights.py — xddp-close Step A 気づき・提案メモ収集 CLI

CR の全成果物（ANA/CRS/SPO/DSN/CHD/CODING/VERIFY/TSP/TRS と各 cross 版）および
`{XDDP_DIR}/latest-specs/**` から「気づき・提案メモ」節を決定的に抽出・集約する。
旧 SKILL.md Step A（LLM が全成果物を Read して該当節を抜き出す構造）を置き換える決定的処理
（判断業務を含まない。CHD 内容ファイルの解決は `xddp-common/SKILL.md`
「## Discover CHD Files」と同じロジック（`chd_sp_coverage.py` の `resolve_chd_content_files` と
同一方針）を用いる）。

Usage:
  python3 collect_insights.py collect \
    --cr CR --cr-path CR_PATH --xddp-dir XDDP_DIR \
    --repos-keys r1,r2 --affected-repos r1,r2 [--has-cross] [--is-multi] \
    --output-file OUTPUT_FILE

Output: 成功時は `--output-file` に気づき・提案メモの集約 Markdown を書き込む（stdout には何も
        出力しない）。失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 共通ユーティリティ（promote.py / chd_sp_coverage.py と同一方針）
# ---------------------------------------------------------------------------


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _split(raw: str) -> list:
    return [s.strip() for s in raw.split(",") if s.strip()]


def _split_row(line: str) -> list:
    """Markdown テーブル行をセルへ分割する（`\\|` エスケープ対応。chd_sp_coverage.py と同一方針）。"""
    if "|" not in line:
        return []
    return [p.strip().replace(r"\|", "|") for p in re.split(r"(?<!\\)\|", line)[1:-1]]


def _write_lines(path: Path, lines: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# CHD 内容ファイル解決（xddp-common「## Discover CHD Files」と同期すること）
# ---------------------------------------------------------------------------

CHD_INDEX_TABLE_HEADING = "## 2. UR別ファイル一覧"
NEXT_H2_RE = re.compile(r"^## ")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _find_table_start(lines: list, heading: str):
    for i, line in enumerate(lines):
        if line.strip() == heading:
            j = i + 1
            while j < len(lines):
                s = lines[j].strip()
                if s.startswith("|"):
                    return j
                if s.startswith("## "):
                    return None
                j += 1
            return None
    return None


def resolve_chd_content_files(design_dir: Path, repo: str, cr: str):
    """`design_dir`（`{CR_PATH}/06_design`）配下の CHD インデックス・内容ファイルを解決する。

    戻り値: (index_file: Path, content_files: list[Path])。`repo == "cross"` は分割対象外の
    単一ファイル。インデックスが存在しない場合は content_files が空リストになる。
    """
    if repo == "cross":
        f = design_dir / "cross" / f"CHD-{cr}-cross.md"
        return f, ([f] if f.exists() else [])
    index_file = design_dir / repo / f"CHD-{cr}.md"
    if not index_file.exists():
        return index_file, []
    lines = index_file.read_text(encoding="utf-8").split("\n")
    start = _find_table_start(lines, CHD_INDEX_TABLE_HEADING)
    content_files = []
    if start is not None:
        i = start
        while i < len(lines) and lines[i].strip().startswith("|"):
            cells = _split_row(lines[i])
            for cell in cells:
                for m in MD_LINK_RE.finditer(cell):
                    # `.resolve()` はしない（symlink 経由の一時ディレクトリ等で `cr_path` との
                    # `relative_to` が失敗し、出典パスが絶対パスにフォールバックしてしまうため）。
                    target = index_file.parent / m.group(1).strip()
                    if target.exists():
                        content_files.append(target)
            i += 1
    return index_file, content_files


# ---------------------------------------------------------------------------
# 対象ファイル列挙
# ---------------------------------------------------------------------------

LATEST_SPECS_EXCLUDE_NAMES = {"schema.md", "crud.md", "dfd.md"}
LATEST_SPECS_EXCLUDE_SUFFIX = "-seq.md"


def _scan_latest_specs_dir(base: Path) -> list:
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.rglob("*.md")):
        name = p.name
        if name in LATEST_SPECS_EXCLUDE_NAMES or name.endswith(LATEST_SPECS_EXCLUDE_SUFFIX):
            continue
        out.append(p)
    return out


def enumerate_targets(cr_path: Path, xddp_dir: Path, cr: str, repos_keys: list,
                       affected_repos: list, has_cross: bool) -> dict:
    """走査対象ファイルをカテゴリ別に列挙する。

    戻り値の `literal`／`chd_index` は「存在して当然」の単一パス群（存在しなければ
    `存在しなかった想定ファイル数` として計上する）。`chd_content`／`glob`／`latest_specs` は
    存在するものだけが自然に集まる（glob・インデックス解決の結果であるため）。
    """
    literal = [
        cr_path / "02_analysis" / f"ANA-{cr}.md",
        cr_path / "03_change-requirements" / f"CRS-{cr}.md",
    ]
    for repo in affected_repos:
        literal.append(cr_path / "04_specout" / repo / f"SPO-{cr}.md")
    if has_cross:
        literal.append(cr_path / "04_specout" / "cross" / f"SPO-{cr}-cross.md")

    for repo in affected_repos:
        for variant in ("comparison", "approach-A", "approach-B", "approach-C"):
            literal.append(cr_path / "05_architecture" / repo / f"DSN-{cr}-{variant}.md")
    if has_cross:
        literal.append(cr_path / "05_architecture" / "cross" / f"DSN-{cr}-cross.md")

    chd_index = []
    chd_content = []
    design_dir = cr_path / "06_design"
    for repo in affected_repos:
        idx, content = resolve_chd_content_files(design_dir, repo, cr)
        chd_index.append(idx)
        chd_content.extend(content)
    if has_cross:
        idx, content = resolve_chd_content_files(design_dir, "cross", cr)
        chd_index.append(idx)
        chd_content.extend(content)

    for repo in affected_repos:
        literal.append(cr_path / "07_coding" / f"CODING-{cr}-{repo}.md")
    for repo in affected_repos:
        literal.append(cr_path / "08_code-review" / f"VERIFY-{cr}-{repo}.md")
    if has_cross:
        literal.append(cr_path / "08_code-review" / f"VERIFY-{cr}-cross.md")
    for repo in affected_repos:
        literal.append(cr_path / "09_test-spec" / repo / f"TSP-{cr}.md")

    glob_files = []
    for repo in affected_repos:
        glob_files.extend(sorted((cr_path / "10_test-results" / repo).glob(f"TRS-{cr}-*.md")))
    if has_cross:
        glob_files.extend(sorted((cr_path / "10_test-results" / "cross").glob(f"TRS-{cr}-*.md")))

    latest_specs_files = []
    for repo in repos_keys:
        latest_specs_files.extend(_scan_latest_specs_dir(xddp_dir / "latest-specs" / repo))
    if has_cross:
        latest_specs_files.extend(_scan_latest_specs_dir(xddp_dir / "latest-specs" / "cross"))
    latest_specs_files.extend(_scan_latest_specs_dir(xddp_dir / "latest-specs" / "system"))

    return {
        "literal": literal,
        "chd_index": chd_index,
        "chd_content": chd_content,
        "glob": glob_files,
        "latest_specs": latest_specs_files,
    }


# ---------------------------------------------------------------------------
# 「気づき・提案メモ」節の切り出し
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s*(.*)$")
ORDINAL_PREFIX_RE = re.compile(r"^\d+[.．]\s*")
FULLWIDTH_SPACE = "　"
TARGET_HEADING_TEXT = "気づき・提案メモ"
PLACEHOLDER_EMPTY_TEXTS = {"（なし）", "(なし)"}
BRACE_PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")


def _normalize_heading_text(text: str) -> str:
    t = text.replace(FULLWIDTH_SPACE, " ").strip()
    t = ORDINAL_PREFIX_RE.sub("", t)
    return t.strip()


def _find_insight_section_bodies(text: str) -> list:
    """本文中の「気づき・提案メモ」見出し配下の本文（生テキスト）を全て返す。

    見出しレベル（##/### 等）を問わず検出し、次の同レベル以上の見出し直前までを本文とする。
    """
    lines = text.split("\n")
    n = len(lines)
    bodies = []
    i = 0
    while i < n:
        m = HEADING_RE.match(lines[i])
        if m and _normalize_heading_text(m.group(2)) == TARGET_HEADING_TEXT:
            level = len(m.group(1))
            j = i + 1
            while j < n:
                m2 = HEADING_RE.match(lines[j])
                if m2 and len(m2.group(1)) <= level:
                    break
                j += 1
            bodies.append(lines[i + 1:j])
            i = j
        else:
            i += 1
    return bodies


def _is_placeholder_or_empty(body_lines: list) -> bool:
    """本文が空、またはテンプレートのプレースホルダのみ（ガイダンス引用文・次見出し直前の `---`
    区切り線・空テーブル・`{内容}` 等の未記入プレースホルダ行のみ）の場合に True を返す。"""
    content_lines = [s.strip() for s in body_lines if s.strip()]
    content_lines = [s for s in content_lines if not s.startswith(">") and s != "---"]
    if not content_lines:
        return True
    if all(s in PLACEHOLDER_EMPTY_TEXTS for s in content_lines):
        return True
    table_lines = [s for s in content_lines if s.startswith("|")]
    non_table_lines = [s for s in content_lines if not s.startswith("|")]
    if non_table_lines:
        return False
    if len(table_lines) < 2:
        return False
    data_rows = table_lines[2:]
    if not data_rows:
        return True
    return all(BRACE_PLACEHOLDER_RE.search(row) for row in data_rows)


def _trim_blank_edges(lines: list) -> list:
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _strip_trailing_hr(lines: list) -> list:
    """次見出し直前に置かれる `---` 区切り線（テンプレート標準の節区切り）を本文末尾から除く。"""
    trimmed = _trim_blank_edges(lines)
    if trimmed and trimmed[-1].strip() == "---":
        trimmed = _trim_blank_edges(trimmed[:-1])
    return trimmed


# ---------------------------------------------------------------------------
# 収集本体
# ---------------------------------------------------------------------------


def collect(cr_path: Path, xddp_dir: Path, cr: str, repos_keys: list, affected_repos: list,
            has_cross: bool) -> dict:
    targets = enumerate_targets(cr_path, xddp_dir, cr, repos_keys, affected_repos, has_cross)

    missing_count = sum(1 for p in targets["literal"] if not p.exists())
    missing_count += sum(1 for p in targets["chd_index"] if not p.exists())

    scan_groups = [
        ("cr_path", [p for p in targets["literal"] if p.exists()]),
        ("cr_path", targets["chd_content"]),
        ("cr_path", targets["glob"]),
        ("xddp_dir", targets["latest_specs"]),
    ]

    scanned = 0
    with_section = 0
    entries = []  # list of (source_path_str, body_text)
    for base_kind, files in scan_groups:
        base = cr_path if base_kind == "cr_path" else xddp_dir
        for f in files:
            scanned += 1
            text = f.read_text(encoding="utf-8")
            bodies = _find_insight_section_bodies(text)
            if bodies:
                with_section += 1
            for body_lines in bodies:
                if _is_placeholder_or_empty(body_lines):
                    continue
                trimmed = _strip_trailing_hr(body_lines)
                if not trimmed:
                    continue
                try:
                    rel = f.relative_to(base)
                except ValueError:
                    rel = f
                entries.append((str(rel), "\n".join(trimmed)))

    return {
        "entries": entries,
        "scanned": scanned,
        "with_section": with_section,
        "missing": missing_count,
    }


def render_output(cr: str, result: dict) -> list:
    lines = [f"# 気づき・提案メモ集約（{cr}）", "",
             "> `collect_insights.py` が生成する中間ファイル（昇格対象外）。", ""]
    for source_path, body in result["entries"]:
        lines.append(f"## {source_path}")
        lines.append("")
        lines.extend(body.split("\n"))
        lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## 収集サマリ")
    lines.append(f"- 走査ファイル数: {result['scanned']}")
    lines.append(f"- 気づきメモ節ありファイル数: {result['with_section']}")
    lines.append(f"- 抽出エントリ数: {len(result['entries'])}")
    lines.append(f"- 存在しなかった想定ファイル数: {result['missing']}")
    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_collect(args) -> None:
    cr_path = Path(args.cr_path)
    if not cr_path.is_dir():
        _err(f"CR_PATH が見つかりません: {cr_path}")
    xddp_dir = Path(args.xddp_dir)
    if not xddp_dir.is_dir():
        _err(f"XDDP_DIR が見つかりません: {xddp_dir}")

    repos_keys = _split(args.repos_keys)
    affected_repos = _split(args.affected_repos)

    result = collect(cr_path, xddp_dir, args.cr, repos_keys, affected_repos, args.has_cross)
    _write_lines(Path(args.output_file), render_output(args.cr, result))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect")
    p_collect.add_argument("--cr", required=True)
    p_collect.add_argument("--cr-path", required=True)
    p_collect.add_argument("--xddp-dir", required=True)
    p_collect.add_argument("--repos-keys", required=True)
    p_collect.add_argument("--affected-repos", required=True)
    p_collect.add_argument("--has-cross", action="store_true")
    p_collect.add_argument("--is-multi", action="store_true")
    p_collect.add_argument("--output-file", required=True)
    p_collect.set_defaults(func=cmd_collect)

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
