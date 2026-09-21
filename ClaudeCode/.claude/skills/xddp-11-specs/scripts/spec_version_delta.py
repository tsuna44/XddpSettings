"""
spec_version_delta.py — xddp-11-specs Step MOD の機械的先決基準（更新要否・バージョン下限）

`xddp-specs-mod-agent.md` の「既存ファイルの更新判断」項目1（生成前の要否判断）と
「バージョン判定の機械的先決基準」（生成後の版数下限判定）を数える行為として決定的に実装する。
対応関係・閾値の意味論は SKILL.md / エージェント定義の記述をそのまま踏襲する。

Usage:
  python3 spec_version_delta.py precheck --existing DIR --spo DIR \
      [--line-change-threshold-pct 20] --out OUT_JSON
  python3 spec_version_delta.py compare --baseline DIR --current DIR --out OUT_JSON

precheck の出力: {"ok": true, "force_update_files": [...], "diagnostics": {...}}
compare の出力:   {"ok": true, "version_floors": {...}, "rewritten_files": [...], "diagnostics": {...}}
  compare はバージョン下限を下回るファイルのフロントマター `version:` と、
  「変更履歴」テーブルの直近エントリ（最終行）のバージョン列を実際に書き換える。

失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import json
import re
import sys
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)```", re.S)
EDGE_TOKEN_RE = re.compile(r"-{1,2}[.\-]{0,2}[|ox*]{0,1}-?>{1,2}|\.\.\|?>")
NODE_TOKEN_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?=[\[\(\{])")
PARTICIPANT_RE = re.compile(r"^\s*(?:participant|actor)\s+(\S+)")

FILE_TO_SPO_SECTION = {
    # 「既存仕様の文書化」（`## 3.`）は仕様書がない場合の代替セクション。存在すれば含める
    # （xddp-11-specs/SKILL.md Step MOD の spec.md 生成規則に対応）。
    "spec.md": {"level": 2, "names": ["現状仕様", "既存仕様の文書化（仕様書がない場合）"], "prefixes": ["2.", "3."]},
    "structure.md": {"level": 3, "names": ["クラス図", "データ構造", "PAD（問題分析図）"], "prefixes": []},
    "state-machine.md": {"level": 3, "names": ["状態遷移図"], "prefixes": []},
}
SEQUENCE_PARENT_HEADING = {"level": 3, "names": ["モジュール内シーケンス図"], "prefixes": []}


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 見出し解析
# ---------------------------------------------------------------------------

def iter_headings(lines: list[str]):
    for idx, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            yield idx, len(m.group(1)), m.group(2).strip()


def section_body(lines: list[str], start_idx: int, level: int) -> str:
    end = start_idx + 1
    while end < len(lines):
        m = HEADING_RE.match(lines[end])
        if m and len(m.group(1)) <= level:
            break
        end += 1
    return "\n".join(lines[start_idx + 1:end])


HEADING_NUMBER_PREFIX_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)*\.?\s*")


def normalize_heading_text(name: str) -> str:
    """見出し先頭の番号（`4.3 ` 等）を除去した比較用テキストを返す。"""
    return HEADING_NUMBER_PREFIX_RE.sub("", name).strip()


def matches_heading(name: str, names: list[str], prefixes: list[str]) -> bool:
    if name in names or normalize_heading_text(name) in names:
        return True
    return any(name.startswith(p) for p in prefixes)


def extract_sections(text: str, spec: dict) -> str | None:
    """spec = {"level": int, "names": [...], "prefixes": [...]}。1件も一致しなければ None。"""
    lines = text.splitlines()
    parts = []
    for idx, lvl, name in iter_headings(lines):
        if lvl != spec["level"]:
            continue
        if matches_heading(name, spec["names"], spec["prefixes"]):
            parts.append(section_body(lines, idx, lvl))
    if not parts:
        return None
    return "\n".join(parts)


def kebabify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "", s)
    return s.strip("-")


def extract_sequence_subsection(text: str, feature: str) -> str | None:
    """`### モジュール内シーケンス図` の子見出し（レベル+1）をケバブ変換して feature と照合する。

    見出しなし・単一の場合は feature=="main" のときに限りその1件を返す（SKILL.md の
    「見出しなし・単一の場合は main-seq.md をデフォルトとする」規則に対応）。
    """
    lines = text.splitlines()
    parent = SEQUENCE_PARENT_HEADING
    for idx, lvl, name in iter_headings(lines):
        if lvl != parent["level"] or not matches_heading(name, parent["names"], parent["prefixes"]):
            continue
        body_start = idx + 1
        body_end = body_start
        while body_end < len(lines):
            m = HEADING_RE.match(lines[body_end])
            if m and len(m.group(1)) <= lvl:
                break
            body_end += 1
        body_lines = lines[body_start:body_end]
        sub_level = lvl + 1
        subsections = []
        for sidx, slvl, sname in iter_headings(body_lines):
            if slvl == sub_level:
                subsections.append((sidx, sname))
        if not subsections:
            return "\n".join(body_lines) if feature == "main" else None
        for i, (sidx, sname) in enumerate(subsections):
            if kebabify(sname) == feature:
                end = subsections[i + 1][0] if i + 1 < len(subsections) else len(body_lines)
                return "\n".join(body_lines[sidx + 1:end])
        if len(subsections) == 1 and feature == "main":
            sidx = subsections[0][0]
            return "\n".join(body_lines[sidx + 1:])
        return None
    return None


# ---------------------------------------------------------------------------
# Mermaid ノード/エッジ計数・行数計数
# ---------------------------------------------------------------------------

def mermaid_metrics(text: str) -> dict:
    nodes: set[str] = set()
    edges = 0
    blocks = MERMAID_BLOCK_RE.findall(text)
    for block in blocks:
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("%%"):
                continue
            edges += len(EDGE_TOKEN_RE.findall(stripped))
            for m in NODE_TOKEN_RE.finditer(stripped):
                nodes.add(m.group(1))
            pm = PARTICIPANT_RE.match(stripped)
            if pm:
                nodes.add(pm.group(1))
    return {"node_count": len(nodes), "edge_count": edges, "block_count": len(blocks)}


def text_line_count(text: str, exclude_mermaid: bool = True) -> int:
    if exclude_mermaid:
        text = MERMAID_BLOCK_RE.sub("", text)
    return len([l for l in text.splitlines() if l.strip()])


def line_change_pct(old_text: str, new_text: str) -> float:
    old_n = text_line_count(old_text)
    new_n = text_line_count(new_text)
    if old_n == 0:
        return 100.0 if new_n > 0 else 0.0
    return abs(new_n - old_n) / old_n * 100.0


# ---------------------------------------------------------------------------
# precheck
# ---------------------------------------------------------------------------

def _spo_file_for_module(spo_dir: Path, module: str) -> Path | None:
    p = spo_dir / f"{module}-spo.md"
    return p if p.is_file() else None


def precheck(existing_root: Path, spo_dir: Path, threshold_pct: float) -> dict:
    force_update_files: list[str] = []
    diagnostics: dict[str, dict] = {}

    if not existing_root.is_dir():
        return {"ok": True, "force_update_files": [], "diagnostics": {}}

    for module_dir in sorted(p for p in existing_root.iterdir() if p.is_dir()):
        module = module_dir.name
        if module in ("overview",):
            continue
        spo_file = _spo_file_for_module(spo_dir, module)
        if spo_file is None:
            diagnostics[module] = {"skipped": "no_spo_file"}
            continue
        spo_text = spo_file.read_text(encoding="utf-8")

        targets: list[tuple[str, dict | None, str | None]] = []
        for filename, spec in FILE_TO_SPO_SECTION.items():
            targets.append((filename, spec, None))
        seq_dir = module_dir / "sequences"
        if seq_dir.is_dir():
            for seq_file in sorted(seq_dir.glob("*-seq.md")):
                feature = seq_file.stem[: -len("-seq")]
                targets.append((f"sequences/{seq_file.name}", None, feature))

        for rel_name, spec, feature in targets:
            existing_file = module_dir / rel_name
            if not existing_file.is_file():
                continue
            existing_text = existing_file.read_text(encoding="utf-8")

            if spec is not None:
                spo_section = extract_sections(spo_text, spec)
            else:
                spo_section = extract_sequence_subsection(spo_text, feature)

            key = f"{module}/{rel_name}"
            if spo_section is None:
                diagnostics[key] = {"skipped": "no_matching_spo_section"}
                continue

            old_metrics = mermaid_metrics(existing_text)
            new_metrics = mermaid_metrics(spo_section)
            mermaid_changed = (
                old_metrics["node_count"] != new_metrics["node_count"]
                or old_metrics["edge_count"] != new_metrics["edge_count"]
            )
            pct = line_change_pct(existing_text, spo_section)
            text_changed = pct >= threshold_pct

            diagnostics[key] = {
                "mermaid_changed": mermaid_changed,
                "old_mermaid": old_metrics,
                "new_mermaid": new_metrics,
                "line_change_pct": round(pct, 2),
            }
            if mermaid_changed or text_changed:
                force_update_files.append(f"{module}/{rel_name}")

    return {"ok": True, "force_update_files": force_update_files, "diagnostics": diagnostics}


def cmd_precheck(args) -> None:
    result = precheck(Path(args.existing), Path(args.spo), args.line_change_threshold_pct)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=False))


# ---------------------------------------------------------------------------
# compare（版数下限算出・自動書き換え）
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.S)
VERSION_LINE_RE = re.compile(r'^(version:\s*)"?([0-9]+\.[0-9]+\.[0-9]+)"?\s*$', re.M)
CHANGELOG_HEADING_RE = re.compile(r"^#{1,6}\s+.*変更履歴.*$", re.M)


def parse_frontmatter(text: str) -> tuple[dict, int]:
    """(frontmatter dict, フロントマターブロックの終端インデックス) を返す。無ければ ({}, 0)。"""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, 0
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm, m.end()


def bump_version(version: str, level: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if level == "MAJOR":
        return f"{major + 1}.0.0"
    if level == "MINOR":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def version_tuple(v: str) -> tuple[int, int, int]:
    a, b, c = (int(x) for x in v.split("."))
    return a, b, c


def determine_bump_level(baseline_text: str, current_text: str) -> str | None:
    """セクション数・見出し名の変化から版数下限カテゴリを決定する。差分なしなら None。"""
    baseline_lines = baseline_text.splitlines()
    current_lines = current_text.splitlines()
    baseline_headings = [(lvl, name) for _, lvl, name in iter_headings(baseline_lines)]
    current_headings = [(lvl, name) for _, lvl, name in iter_headings(current_lines)]

    if baseline_text == current_text:
        return None
    if len(current_headings) < len(baseline_headings):
        return "MAJOR"
    if len(current_headings) > len(baseline_headings):
        return "MINOR"
    baseline_names = [n for _, n in baseline_headings]
    current_names = [n for _, n in current_headings]
    if baseline_names != current_names:
        return "MINOR"
    return "PATCH"


def rewrite_changelog_latest_version(text: str, new_version: str) -> str:
    """`変更履歴` テーブルの最終データ行のバージョン列（1列目）を書き換える。"""
    m = CHANGELOG_HEADING_RE.search(text)
    if not m:
        return text
    lines = text.splitlines(keepends=True)
    heading_line_idx = text[: m.start()].count("\n")
    table_row_idxs = []
    for i in range(heading_line_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            break
        if stripped.startswith("|") and not re.match(r"^\|[\s:-]+\|", stripped):
            table_row_idxs.append(i)
    if len(table_row_idxs) < 2:
        return text
    last_row_idx = table_row_idxs[-1]
    row = lines[last_row_idx]
    cells = row.strip().strip("|").split("|")
    if not cells:
        return text
    cells[0] = f" {new_version} "
    lines[last_row_idx] = "|" + "|".join(cells) + "|\n"
    return "".join(lines)


def rewrite_version(text: str, new_version: str) -> str:
    if VERSION_LINE_RE.search(text):
        text = VERSION_LINE_RE.sub(lambda m: f'{m.group(1)}"{new_version}"', text, count=1)
    text = rewrite_changelog_latest_version(text, new_version)
    return text


def compare(baseline_root: Path, current_root: Path) -> dict:
    version_floors: dict[str, dict] = {}
    rewritten_files: list[str] = []
    diagnostics: dict[str, str] = {}

    if not baseline_root.is_dir():
        return {"ok": True, "version_floors": {}, "rewritten_files": [], "diagnostics": {}}

    for baseline_file in sorted(baseline_root.rglob("*.md")):
        rel = baseline_file.relative_to(baseline_root)
        current_file = current_root / rel
        if not current_file.is_file():
            diagnostics[str(rel)] = "removed_in_current"
            continue

        baseline_text = baseline_file.read_text(encoding="utf-8")
        current_text = current_file.read_text(encoding="utf-8")

        baseline_fm, _ = parse_frontmatter(baseline_text)
        current_fm, _ = parse_frontmatter(current_text)
        baseline_version = baseline_fm.get("version")
        current_version = current_fm.get("version")
        if not baseline_version or not current_version:
            diagnostics[str(rel)] = "no_version_frontmatter"
            continue

        level = determine_bump_level(baseline_text, current_text)
        if level is None:
            continue

        floor_version = bump_version(baseline_version, level)
        version_floors[str(rel)] = {
            "level": level,
            "baseline_version": baseline_version,
            "current_version": current_version,
            "floor_version": floor_version,
        }

        if version_tuple(current_version) < version_tuple(floor_version):
            rewritten_text = rewrite_version(current_text, floor_version)
            current_file.write_text(rewritten_text, encoding="utf-8")
            rewritten_files.append(str(rel))
            version_floors[str(rel)]["rewritten_to"] = floor_version

    return {
        "ok": True,
        "version_floors": version_floors,
        "rewritten_files": rewritten_files,
        "diagnostics": diagnostics,
    }


def cmd_compare(args) -> None:
    result = compare(Path(args.baseline), Path(args.current))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=False))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="xddp-11-specs Step MOD 機械的先決基準")
    sub = parser.add_subparsers(dest="command", required=True)

    p_precheck = sub.add_parser("precheck", help="既存ファイルの更新要否を機械判定する")
    p_precheck.add_argument("--existing", required=True, help="latest-specs/{repo} のパス")
    p_precheck.add_argument("--spo", required=True, help="{repo}/modules/ ディレクトリのパス")
    p_precheck.add_argument("--line-change-threshold-pct", type=float, default=20.0)
    p_precheck.add_argument("--out", required=True)
    p_precheck.set_defaults(func=cmd_precheck)

    p_compare = sub.add_parser("compare", help="バージョン下限を算出し必要なら自動書き換える")
    p_compare.add_argument("--baseline", required=True)
    p_compare.add_argument("--current", required=True)
    p_compare.add_argument("--out", required=True)
    p_compare.set_defaults(func=cmd_compare)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
