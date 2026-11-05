"""ai_index.py — `{DOCS}/AI_INDEX.md` の作り直し

AI_INDEX は `{DOCS}` の中身の索引。`build` は `{DOCS}` を走査して、管理する節を作り直す。
AI_INDEX を書くのはこのスクリプトだけ（01-init・close・survey・update-knowledge が実行する）。

Usage:
  python3 ai_index.py build --docs DOCS --repos-keys r1,r2 [--is-multi]

- `{DOCS}` が無ければ何もしない（stdout の JSON の `skipped` が true）。
- AI_INDEX.md が無ければ作る。内容が変わらなければ書かない。
- 管理しない節（人が足した節）は、内容を変えずに管理する節の後ろに元の順で残す。
- 行が500行を超えたら、CR の値を持つ行をアーカイブ候補（`archive_candidates`）として返す。

Output: stdout に JSON 1オブジェクト（{"ok": true, "skipped", "changed", "path", "line_count",
        "sections": {見出し: 行数}, "archive_candidates": [{"section", "key", "cr", "file"}]}）。
        失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docs_layout as layout  # noqa: E402
from knowledge_place import list_places  # noqa: E402

AI_INDEX_FILE = "AI_INDEX.md"
ARCHIVE_LINE_THRESHOLD = 500
EMPTY = "—"

TITLE_LINES = [
    "# AI向けナビゲーションインデックス",
    "",
    "> `{DOCS_DIR}` の中身の索引。`ai_index.py build` が `{DOCS_DIR}` を走査して下の節を作り直す"
    "（01-init・close・survey・update-knowledge が実行する）。",
    "> 下の節を手で直しても、次の作り直しで戻る。ここに無い見出しの節（人が足した節）は残る。",
]

H_USECASES = "## ユースケース一覧"
H_REPO_SPECS = "## リポジトリ別仕様書"
H_MODULES = "## モジュール別最新仕様"
H_INTERFACES = "## クロスインタフェース一覧"
H_CODE_KNOWLEDGE = "## code-knowledge インデックス"
H_CRS = "## 変更要求仕様書（CRS）ナビゲーション"
H_TESTS = "## テスト仕様（TSP）・テスト結果（TRS）"
H_GLOSSARY = "## 用語集"
H_COMMON = "## 共通知識"
H_GUIDE = "## 知識参照ガイド"

MANAGED_HEADINGS = (H_USECASES, H_REPO_SPECS, H_MODULES, H_INTERFACES, H_CODE_KNOWLEDGE,
                    H_CRS, H_TESTS, H_GLOSSARY, H_COMMON, H_GUIDE)
RETIRED_HEADINGS = ("## 設計書ナビゲーション", "## リポジトリ別設計書・テスト仕様書",
                    "## 工程11 AI_INDEX先行更新セクション")

HEADERS = {
    H_USECASES: ["ユースケース", "目的（1行）", "description", "関連モジュール", "最終更新CR"],
    H_REPO_SPECS: ["リポジトリ", "バージョン", "overview", "モジュール数", "最終更新CR"],
    H_MODULES: ["リポジトリ", "モジュール", "spec", "structure", "state", "最終更新CR"],
    H_INTERFACES: ["インタフェース", "spec", "schema", "バージョン", "最終更新の破壊的変更", "最終更新CR"],
    H_CODE_KNOWLEDGE: ["知りたいこと", "参照先"],
    H_CRS: ["リポジトリ", "CR", "CRS"],
    H_TESTS: ["リポジトリ", "CR", "TSP", "TRS"],
    H_GLOSSARY: ["対象", "参照先"],
    H_COMMON: ["対象", "project-rulebook"],
}

# CR の値を持つ列（アーカイブ候補の対象）
CR_COLUMN = {
    H_USECASES: "最終更新CR",
    H_REPO_SPECS: "最終更新CR",
    H_MODULES: "最終更新CR",
    H_INTERFACES: "最終更新CR",
    H_CRS: "CR",
    H_TESTS: "CR",
}

GUIDE_LINES = [
    "> `{repo}` は `xddp.config.md` の `REPOS:` のリポジトリ名。具体的なファイルは各節の表のリンクを参照する。",
    "",
    "| 知りたいこと | 参照先パターン |",
    "|---|---|",
    "| 現在の機能仕様 | `{DOCS_DIR}/{repo}/specs/{module}/spec.md`（「モジュール別最新仕様」の表） |",
    "| ユースケース | `{DOCS_DIR}/system/specs/use-cases/{usecase}/description.md`（「ユースケース一覧」の表） |",
    "| リポジトリ間のインタフェース | `{DOCS_DIR}/cross/specs/interfaces/{interface}/spec.md`（「クロスインタフェース一覧」の表） |",
    "| 変更要求の根拠 | `{DOCS_DIR}/{repo}/crs/CRS-{CR}.md`（「変更要求仕様書（CRS）ナビゲーション」の表） |",
    "| コードの制約・共有の知見 | `{DOCS_DIR}/{repo}/knowledge/code-knowledge/`（「code-knowledge インデックス」の表） |",
    "| 過去の実装パターン・知見 | `{XDDP_DIR}/lessons-learned.md`（作業中）／`{DOCS_DIR}/{repo}/knowledge/lessons-learned.md`"
    "（クローズ済み）。タグ例: `#方式検討` `#設計` `#コーディング` `#リスク` `#テスト` `#プロセス` |",
    "| プロジェクト規約・禁止事項 | `{DOCS_DIR}/project-rulebook.md`・`{DOCS_DIR}/{repo}/project-rulebook.md`"
    "・`{DOCS_DIR}/cross/project-rulebook.md`（「共通知識」の表） |",
    "| テスト仕様・テスト結果 | `{DOCS_DIR}/{repo}/test/`（「テスト仕様（TSP）・テスト結果（TRS）」の表） |",
    "| 用語 | 「用語集」の表 |",
]

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
TRS_TARGET_CR_RE = re.compile(r"^\*\*対象CR[：:]\*\*\s*(\S+)")
SURVEY_DATE_RE = re.compile(r"^SURVEY-(\d{4})-?(\d{2})-?(\d{2})")


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _cell(value: str) -> str:
    return value.replace("|", r"\|")


def _join_row(cells: list) -> str:
    return "| " + " | ".join(_cell(c) for c in cells) + " |"


def _link(label: str, target: str) -> str:
    return f"[{label}]({target})"


def _or_empty(value: str) -> str:
    return value if value else EMPTY


def _fm_str(fm: dict, key: str) -> str:
    val = fm.get(key, "")
    return val if isinstance(val, str) else ""


def _rel(docs: Path, path: Path) -> str:
    return path.relative_to(docs).as_posix()


# ---------------------------------------------------------------------------
# 用語数
# ---------------------------------------------------------------------------


def glossary_term_count(path: Path) -> int:
    """`## 用語一覧` の見出しの下の最初の表のデータ行数。"""
    if not path.is_file():
        return 0
    lines = path.read_text(encoding="utf-8").split("\n")
    try:
        i = next(k for k, l in enumerate(lines) if l.strip() == "## 用語一覧") + 1
    except StopIteration:
        return 0
    while i < len(lines) and not lines[i].startswith("## ") and not lines[i].strip().startswith("|"):
        i += 1
    if i >= len(lines) or not lines[i].strip().startswith("|"):
        return 0
    j = i
    while j < len(lines) and lines[j].strip().startswith("|"):
        j += 1
    return max(0, j - (i + 2))


# ---------------------------------------------------------------------------
# 行の作り方（各行は (cells, 行のもとのファイル)）
# ---------------------------------------------------------------------------


def _usecase_rows(docs: Path) -> list:
    rows = []
    uc_root = layout.docs_usecases_dir(docs)
    for name in layout.subdir_names(uc_root):
        desc = uc_root / name / layout.USECASE_FILE
        if not desc.is_file():
            continue
        text = desc.read_text(encoding="utf-8")
        fm = layout.parse_frontmatter(text)
        related = layout.usecase_related_modules(fm)
        rows.append(([
            name,
            _or_empty(layout.usecase_purpose(text)),
            _link(layout.USECASE_FILE, _rel(docs, desc)),
            ", ".join(related) if related else EMPTY,
            _or_empty(_fm_str(fm, layout.LAST_UPDATED_CR_KEY)),
        ], desc))
    return rows


def _modules_with_spec(specs_root: Path) -> list:
    return [m for m in layout.module_names(specs_root)
            if (specs_root / m / layout.MODULE_SPEC_FILE).is_file()]


def _repo_spec_rows(docs: Path, repos: list) -> list:
    rows = []
    for repo in repos:
        specs_root = layout.docs_specs_root(docs, repo)
        if not specs_root.is_dir():
            continue
        overview = specs_root / layout.OVERVIEW_DIR
        arch = overview / layout.OVERVIEW_ARCHITECTURE_FILE
        fm = layout.read_frontmatter(arch)
        version = _fm_str(fm, "version")
        rows.append(([
            _link(repo, _rel(docs, specs_root) + "/"),
            f"v{version}" if version else EMPTY,
            _link("overview", _rel(docs, overview) + "/") if overview.is_dir() else EMPTY,
            f"{len(_modules_with_spec(specs_root))} モジュール",
            _or_empty(layout.last_updated_cr(arch)),
        ], arch if arch.is_file() else specs_root))
    return rows


def _module_rows(docs: Path, repos: list) -> list:
    rows = []
    for repo in repos:
        specs_root = layout.docs_specs_root(docs, repo)
        for module in _modules_with_spec(specs_root):
            mdir = specs_root / module
            spec = mdir / layout.MODULE_SPEC_FILE
            structure = mdir / layout.MODULE_STRUCTURE_FILE
            state = mdir / layout.MODULE_STATE_FILE
            rows.append(([
                repo,
                module,
                _link(layout.MODULE_SPEC_FILE, _rel(docs, spec)),
                _link(layout.MODULE_STRUCTURE_FILE, _rel(docs, structure)) if structure.is_file() else EMPTY,
                _link(layout.MODULE_STATE_FILE, _rel(docs, state)) if state.is_file() else EMPTY,
                _or_empty(layout.last_updated_cr(spec)),
            ], spec))
    return rows


def _interface_rows(docs: Path) -> list:
    rows = []
    if_root = layout.docs_interfaces_dir(docs)
    for name in layout.subdir_names(if_root):
        spec = if_root / name / layout.INTERFACE_SPEC_FILE
        if not spec.is_file():
            continue
        schema = if_root / name / layout.INTERFACE_SCHEMA_FILE
        fm = layout.read_frontmatter(spec)
        version = _fm_str(fm, "version")
        rows.append(([
            name,
            _link(layout.INTERFACE_SPEC_FILE, _rel(docs, spec)),
            _link(layout.INTERFACE_SCHEMA_FILE, _rel(docs, schema)) if schema.is_file() else EMPTY,
            f"v{version}" if version else EMPTY,
            "⚠️ あり" if layout.is_breaking(fm) else EMPTY,
            _or_empty(_fm_str(fm, layout.LAST_UPDATED_CR_KEY)),
        ], spec))
    return rows


def _code_knowledge_rows(docs: Path, areas: list) -> list:
    rows = []
    for area in areas:
        ck = layout.code_knowledge_dir(docs, area)
        if not ck.is_dir():
            continue
        for place in list_places(ck):
            target = ck / place / "constraints.md"
            rows.append(([f"{area}/{place} 制約・注意事項", _link("constraints.md", _rel(docs, target))],
                         target))
        for dirname, kind in layout.SHARED_KNOWLEDGE_DIRS.items():
            d = ck / dirname
            if d.is_dir():
                rows.append(([f"{area} {kind}", _link(f"{dirname}/", _rel(docs, d) + "/")], d))
    return rows


def _crs_rows(docs: Path, areas: list) -> list:
    rows = []
    for area in areas:
        crs_dir = Path(docs) / area / "crs"
        if not crs_dir.is_dir():
            continue
        for f in sorted(crs_dir.glob("CRS-*.md")):
            if not f.is_file():
                continue
            cr = f.stem[len("CRS-"):]
            rows.append(([area, cr, _link(f.name, _rel(docs, f))], f))
    return rows


def _trs_target_cr(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").split("\n")[:30]:
            m = TRS_TARGET_CR_RE.match(line.strip())
            if m:
                return m.group(1)
    except OSError:
        pass
    return ""


def trs_cr(path: Path, known_crs) -> str:
    """`TRS-{CR}-{接尾辞}.md` の CR。

    既知の CR（同じ repo の TSP・CRS の CR）のうち前方一致する最長のもの → 本文の `**対象CR：**` の値
    → ファイル名の最後の `-` の前まで、の順に決める。
    """
    stem = path.stem[len("TRS-"):]
    matches = [cr for cr in known_crs if stem.startswith(cr + "-")]
    if matches:
        return max(matches, key=len)
    target = _trs_target_cr(path)
    if target and stem.startswith(target + "-"):
        return target
    return stem.rsplit("-", 1)[0] if "-" in stem else stem


def _test_rows(docs: Path, areas: list) -> list:
    rows = []
    for area in areas:
        test_dir = Path(docs) / area / "test"
        if not test_dir.is_dir():
            continue
        tsp_by_cr = {}
        for f in sorted(test_dir.glob("TSP-*.md")):
            cr = f.stem[len("TSP-"):]
            if area == layout.CROSS_AREA and cr.endswith("-cross"):
                cr = cr[:-len("-cross")]
            tsp_by_cr.setdefault(cr, []).append(f)
        crs_dir = Path(docs) / area / "crs"
        known = set(tsp_by_cr)
        if crs_dir.is_dir():
            known |= {f.stem[len("CRS-"):] for f in crs_dir.glob("CRS-*.md")}
        trs_by_cr = {}
        for f in sorted(test_dir.glob("TRS-*.md")):
            trs_by_cr.setdefault(trs_cr(f, known), []).append(f)
        for cr in sorted(set(tsp_by_cr) | set(trs_by_cr)):
            tsps = tsp_by_cr.get(cr, [])
            trss = trs_by_cr.get(cr, [])
            rows.append(([
                area,
                cr,
                ", ".join(_link(f.name, _rel(docs, f)) for f in tsps) if tsps else EMPTY,
                ", ".join(_link(f.name, _rel(docs, f)) for f in trss) if trss else EMPTY,
            ], (tsps or trss)[0]))
    return rows


def _glossary_rows(docs: Path, areas: list) -> list:
    rows = []
    targets = [("プロジェクト共通", Path(docs) / "glossary.md")]
    targets += [(area, Path(docs) / area / "knowledge" / "glossary.md") for area in areas]
    for label, path in targets:
        if path.is_file():
            rows.append(([label, f"{_link('glossary.md', _rel(docs, path))}（用語数: {glossary_term_count(path)}）"],
                         path))
    return rows


def _common_rows(docs: Path, areas: list) -> list:
    rows = []
    targets = [("プロジェクト共通", Path(docs) / "project-rulebook.md")]
    targets += [(area, Path(docs) / area / "project-rulebook.md") for area in areas]
    for label, path in targets:
        if path.is_file():
            rows.append(([label, _link("project-rulebook.md", _rel(docs, path))], path))
    return rows


# ---------------------------------------------------------------------------
# 既存の AI_INDEX の節の分割
# ---------------------------------------------------------------------------


def split_sections(lines: list) -> list:
    """`## ` の見出しで節に分ける（フェンスの中の行は見出しにしない）。

    戻り値: [(見出しの行, 本文の行のリスト)]。最初の見出しより前は捨てる。
    """
    sections = []
    current = None
    fence = None
    for line in lines:
        m = FENCE_RE.match(line)
        if fence is None and m:
            fence = m.group(1)[0]
        elif fence is not None and m and m.group(1)[0] == fence:
            fence = None
        elif fence is None and line.startswith("## "):
            current = (line.rstrip(), [])
            sections.append(current)
            continue
        if current is not None:
            current[1].append(line)
    return sections


def _kept_sections(path: Path) -> list:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").split("\n")
    kept = []
    for heading, body in split_sections(lines):
        if heading.strip() in MANAGED_HEADINGS or heading.strip() in RETIRED_HEADINGS:
            continue
        while body and not body[-1].strip():
            body = body[:-1]
        kept.append([heading] + body)
    return kept


# ---------------------------------------------------------------------------
# アーカイブ候補
# ---------------------------------------------------------------------------


def _archive_sort_key(item: dict):
    cr = item["cr"]
    if cr.startswith("CR-"):
        return (0, cr)
    m = SURVEY_DATE_RE.match(cr)
    date = "".join(m.groups()) if m else "99999999"
    return (1, date, cr)


def _archive_candidates(docs: Path, table_rows: dict) -> list:
    out = []
    for heading, rows in table_rows.items():
        column = CR_COLUMN.get(heading)
        if column is None:
            continue
        idx = HEADERS[heading].index(column)
        for cells, src in rows:
            cr = cells[idx]
            if cr.startswith(("CR-", "SURVEY-")):
                out.append({"section": heading[3:], "key": cells[0], "cr": cr, "file": _rel(docs, src)})
    out.sort(key=_archive_sort_key)
    return out


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def render(docs: Path, repos_keys: list, is_multi: bool):
    """AI_INDEX の行と、節ごとの行（cells, 行のもとのファイル）を返す。"""
    docs = Path(docs)
    areas = list(repos_keys) + ([layout.CROSS_AREA] if is_multi else [])
    table_rows = {
        H_USECASES: _usecase_rows(docs),
        H_REPO_SPECS: _repo_spec_rows(docs, repos_keys),
        H_MODULES: _module_rows(docs, repos_keys),
    }
    if is_multi or layout.docs_interfaces_dir(docs).is_dir():
        table_rows[H_INTERFACES] = _interface_rows(docs)
    table_rows[H_CODE_KNOWLEDGE] = _code_knowledge_rows(docs, areas)
    table_rows[H_CRS] = _crs_rows(docs, areas)
    table_rows[H_TESTS] = _test_rows(docs, areas)
    table_rows[H_GLOSSARY] = _glossary_rows(docs, areas)
    table_rows[H_COMMON] = _common_rows(docs, areas)

    lines = list(TITLE_LINES)
    for heading in MANAGED_HEADINGS:
        if heading == H_GUIDE:
            lines += ["", heading, ""] + GUIDE_LINES
            continue
        if heading not in table_rows:
            continue
        header = HEADERS[heading]
        lines += ["", heading, "", _join_row(header), "|" + "---|" * len(header)]
        lines += [_join_row(cells) for cells, _ in table_rows[heading]]
    for section in _kept_sections(docs / AI_INDEX_FILE):
        lines += [""] + section
    return lines, table_rows


def build(docs, repos_keys: list, is_multi: bool) -> dict:
    docs = Path(docs)
    path = docs / AI_INDEX_FILE
    if not docs.is_dir():
        return {"ok": True, "skipped": True, "changed": False, "path": str(path), "line_count": 0,
                "sections": {}, "archive_candidates": []}
    lines, table_rows = render(docs, repos_keys, is_multi)
    text = "\n".join(lines) + "\n"
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    changed = old != text
    if changed:
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    archive = _archive_candidates(docs, table_rows) if len(lines) > ARCHIVE_LINE_THRESHOLD else []
    return {
        "ok": True,
        "skipped": False,
        "changed": changed,
        "path": str(path),
        "line_count": len(lines),
        "sections": {h[3:]: len(rows) for h, rows in table_rows.items()},
        "archive_candidates": archive,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_build(args) -> None:
    repos = [r.strip() for r in args.repos_keys.split(",") if r.strip()]
    print(json.dumps(build(Path(args.docs), repos, args.is_multi), ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI_INDEX.md を {DOCS} から作り直す")
    sub = parser.add_subparsers(dest="command", required=True)
    p_build = sub.add_parser("build", help="{DOCS} を走査して AI_INDEX.md の管理する節を作り直す")
    p_build.add_argument("--docs", required=True)
    p_build.add_argument("--repos-keys", required=True, help="カンマ区切りのリポジトリ名一覧（全 repo）")
    p_build.add_argument("--is-multi", action="store_true")
    p_build.set_defaults(func=cmd_build)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except Exception as e:  # noqa: BLE001 — CLI境界でのエラーはstderrへ集約する
        _err(f"AI_INDEX.md の作り直しに失敗しました: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
