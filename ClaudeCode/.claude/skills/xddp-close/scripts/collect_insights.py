"""collect_insights.py — xddp-close Step A 気づき・提案メモ収集 CLI

CR の成果物（ANA/CRS/SPO/DSN/CHD/CODING/VERIFY/TSP/TRS と各 cross 版・progress.md）と、
今の CR が更新した latest-specs のファイルから「気づき・提案メモ」節の項目を決定的に抽出・集約する
（判断業務を含まない。CHD 内容ファイルの解決は `xddp-common/SKILL.md`「## Discover CHD Files」と
同じロジック（`chd_sp_coverage.py` の `resolve_chd_content_files` と同一方針）を用いる）。

節の見出し・項目の定義（数えない行・「なし」の語・表の行の取り方）・`has_insights` の読み方は
`docs_layout.py` の単一定義を使う。

latest-specs は、progress.md の「## 工程11 更新仕様書ファイル一覧」のファイルと、フロントマターの
`last-updated-cr` が今の CR のファイルの和集合を走査する。`has_insights: false` のファイルは飛ばす。
項目のうち `{DOCS}` の同じファイル（`latest-specs/{area}/{path}` → `{DOCS}/{area}/specs/{path}`）の
節にあるものは除く。`{DOCS}` の同じファイルの `last-updated-cr` が今の CR なら（前回の close が昇格した
後の再実行）、`{DOCS}` と比べず、書き出す前の `--output-file`（前回の結果）のそのファイルの節を引き継ぐ。

Usage:
  python3 collect_insights.py collect \
    --cr CR --cr-path CR_PATH --xddp-dir XDDP_DIR --docs DOCS \
    --repos-keys r1,r2 --affected-repos r1,r2 [--has-cross] [--is-multi] \
    --output-file OUTPUT_FILE

Output: 成功時は `--output-file` に気づき・提案メモの集約 Markdown を書き込む（stdout には何も
        出力しない）。失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xddp-common" / "scripts"))
import docs_layout as layout  # noqa: E402

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

def step11_listed_files(progress: Path):
    """progress.md の工程11 の更新一覧（`docs_layout.STEP11_UPDATED_HEADING`）の `latest-specs/…` のパス。
    節が無ければ None（見出しと読み方は `docs_layout.read_step11_list`）。"""
    if not progress.is_file():
        return None
    return layout.read_step11_list(progress.read_text(encoding="utf-8"), layout.STEP11_UPDATED_HEADING)


def select_latest_specs(cr_path: Path, xddp_dir: Path, cr: str) -> dict:
    """走査する latest-specs のファイル（`{XDDP_DIR}` からの相対パス）を決める。

    工程11 の一覧と、フロントマターの `last-updated-cr` が今の CR のファイルの和集合。
    戻り値: {"files": [相対パス], "not_listed": [一覧に無く last-updated-cr で見つけたもの],
             "skipped": 一覧の節が無く last-updated-cr でも見つからず走査しない}
    """
    listed = step11_listed_files(cr_path / "progress.md")
    root = xddp_dir / "latest-specs"
    by_cr = []
    if root.is_dir():
        for p in sorted(root.rglob("*.md")):
            if layout.last_updated_cr(p) == cr:
                by_cr.append(p.relative_to(xddp_dir).as_posix())
    files = list(listed or [])
    not_listed = [rel for rel in by_cr if rel not in files]
    files.extend(not_listed)
    return {"files": files, "not_listed": not_listed if listed is not None else [],
            "skipped": listed is None and not by_cr}


def enumerate_targets(cr_path: Path, cr: str, affected_repos: list, has_cross: bool) -> dict:
    """CR の成果物の走査対象ファイルをカテゴリ別に列挙する（latest-specs は select_latest_specs）。

    戻り値の `literal`／`chd_index` は「存在して当然」の単一パス群（存在しなければ
    `存在しなかった想定ファイル数` として計上する）。`chd_content`／`glob` は
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
    if has_cross:
        literal.append(cr_path / "09_test-spec" / "cross" / f"TSP-{cr}-cross.md")

    glob_files = []
    for repo in affected_repos:
        glob_files.extend(sorted((cr_path / "10_test-results" / repo).glob(f"TRS-{cr}-*.md")))
    if has_cross:
        glob_files.extend(sorted((cr_path / "10_test-results" / "cross").glob(f"TRS-{cr}-*.md")))

    literal.append(cr_path / "progress.md")

    return {
        "literal": literal,
        "chd_index": chd_index,
        "chd_content": chd_content,
        "glob": glob_files,
    }


# ---------------------------------------------------------------------------
# 「気づき・提案メモ」節の項目（定義は docs_layout）
# ---------------------------------------------------------------------------


def file_items(path: Path) -> tuple:
    """ファイルの全部の「気づき・提案メモ」節の (節の数, 項目のリスト)。"""
    bodies = layout.find_insight_sections(path.read_text(encoding="utf-8"))
    items = []
    for body in bodies:
        items.extend(layout.insight_items(body))
    return len(bodies), items


def read_previous_output(path) -> dict:
    """前回の出力（INSIGHTS-{CR}.md）の `## {出典のパス}` ごとの本文。ファイルが無ければ None。"""
    if path is None or not Path(path).is_file():
        return None
    sections = {}
    current = None
    for line in Path(path).read_text(encoding="utf-8").split("\n"):
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    sections.pop(SUMMARY_HEADING_TEXT, None)
    return sections


# ---------------------------------------------------------------------------
# 収集本体
# ---------------------------------------------------------------------------

SUMMARY_HEADING_TEXT = "収集サマリ"


def _rel(f: Path, base: Path) -> str:
    try:
        return f.relative_to(base).as_posix()
    except ValueError:
        return str(f)


def collect(cr_path: Path, xddp_dir: Path, cr: str, repos_keys: list, affected_repos: list,
            has_cross: bool, docs=None, previous_output=None) -> dict:
    """気づき・提案メモを集める。

    latest-specs は、今の CR が足した項目だけ: `{DOCS}` の同じファイルの節にある項目を除く。
    `{DOCS}` の同じファイルの `last-updated-cr` が今の CR（前回の close が昇格した後の再実行）なら、
    `{DOCS}` と比べず、前回の出力（previous_output）のそのファイルの節を引き継ぐ。
    """
    targets = enumerate_targets(cr_path, cr, affected_repos, has_cross)

    missing_count = sum(1 for p in targets["literal"] if not p.exists())
    missing_count += sum(1 for p in targets["chd_index"] if not p.exists())

    scanned = 0
    with_section = 0
    entries = []  # list of (source_path_str, body_text)

    def _add(source: str, items: list) -> None:
        if items:
            entries.append((source, "\n".join(layout.render_insight_items(items))))

    for files in ([p for p in targets["literal"] if p.exists()], targets["chd_content"], targets["glob"]):
        for f in files:
            scanned += 1
            n_sections, items = file_items(f)
            if n_sections:
                with_section += 1
            _add(_rel(f, cr_path), items)

    latest = select_latest_specs(cr_path, xddp_dir, cr)
    previous = read_previous_output(previous_output)
    latest_scanned = 0
    excluded = 0
    carried = []
    no_previous = []
    for rel in latest["files"]:
        f = xddp_dir / rel
        if not f.is_file():
            missing_count += 1
            continue
        if layout.has_insights(layout.read_frontmatter(f)) is False:
            continue
        scanned += 1
        latest_scanned += 1
        docs_file = layout.latest_to_docs_path(docs, rel) if docs is not None else None
        if docs_file is not None and docs_file.is_file() and layout.last_updated_cr(docs_file) == cr:
            if previous is None:
                no_previous.append(rel)
                continue
            carried.append(rel)
            body = previous.get(rel)
            if body is not None:
                with_section += 1
                _add(rel, layout.insight_items(body))
            continue
        n_sections, items = file_items(f)
        if n_sections:
            with_section += 1
        if docs_file is not None and docs_file.is_file():
            _, docs_items = file_items(docs_file)
            docs_keys = {it["key"] for it in docs_items}
            kept = [it for it in items if it["key"] not in docs_keys]
            excluded += len(items) - len(kept)
            items = kept
        _add(rel, items)

    return {
        "entries": entries,
        "scanned": scanned,
        "with_section": with_section,
        "missing": missing_count,
        "latest": {
            "scanned": latest_scanned,
            "excluded": excluded,
            "carried": carried,
            "not_listed": latest["not_listed"],
            "no_previous": no_previous,
            "skipped": latest["skipped"],
        },
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
    latest = result["latest"]
    lines.append(f"## {SUMMARY_HEADING_TEXT}")
    lines.append(f"- 走査ファイル数: {result['scanned']}")
    lines.append(f"- 気づきメモ節ありファイル数: {result['with_section']}")
    lines.append(f"- 抽出エントリ数: {len(result['entries'])}")
    lines.append(f"- 存在しなかった想定ファイル数: {result['missing']}")
    if latest["skipped"]:
        lines.append("- latest-specs: 走査しなかった（progress.md に「工程11 更新仕様書ファイル一覧」の節が無く、"
                     "`last-updated-cr` が今の CR のファイルも無い）")
    else:
        lines.append(f"- latest-specs: 一覧の {latest['scanned']} ファイルを走査、`{{DOCS}}` に既にある "
                     f"{latest['excluded']} 件を除外、前回の収集結果から {len(latest['carried'])} ファイルを引き継ぎ")
    if latest["not_listed"]:
        lines.append(f"- 工程11 の一覧に無いファイル（`last-updated-cr` で見つけた）: "
                     f"{', '.join(latest['not_listed'])}")
    if latest["no_previous"]:
        lines.append(f"- 今の CR が昇格済みで前回の収集結果が無い {len(latest['no_previous'])} ファイル"
                     f"（気づきを集められない）: {', '.join(latest['no_previous'])}")
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

    output_file = Path(args.output_file)
    result = collect(cr_path, xddp_dir, args.cr, repos_keys, affected_repos, args.has_cross,
                     docs=Path(args.docs), previous_output=output_file)
    _write_lines(output_file, render_output(args.cr, result))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect")
    p_collect.add_argument("--cr", required=True)
    p_collect.add_argument("--cr-path", required=True)
    p_collect.add_argument("--xddp-dir", required=True)
    p_collect.add_argument("--docs", required=True)
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
