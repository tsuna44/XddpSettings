"""
spec_version_delta.py — xddp-11-specs の入力の一覧（sources）と、Step MOD の機械的先決基準（更新要否・バージョン下限）

工程4a のモジュール資料の配置（統合パス・分割パス・索引）は、書く側の `specout_bfs.module_docs` で読む。
工程11（SKILL・mod-agent・precheck・レビュー）・工程5・6・survey は、`sources` の一覧だけを見る。
latest-specs のディレクトリ名・`module-dir`・シーケンス図のファイル名の規則は `docs_layout.py` にある。
`xddp-specs-mod-agent.md` の「既存ファイルの更新判断」項目1（生成前の要否判断）と
「バージョン判定の下限」（生成後の版数下限判定）を数える行為として決定的に実装する。

Usage:
  python3 spec_version_delta.py sources --spo-dir {CR_PATH}/04_specout/{repo} --cr CR \
      --latest-specs {XDDP_DIR}/latest-specs/{repo} [--docs-specs {DOCS}/{repo}/specs] [--repo REPO] \
      [--repo-path REPO_PATH [--exclude PATTERNS] [--include-ext EXTS] [--xddp-dir XDDP_DIR]] [--chd FILE ...] \
      [--out-dir DIR] [--module-template FILE] [--today YYYY-MM-DD] --out OUT_JSON
  python3 spec_version_delta.py spec-dir --latest-specs DIR [--docs-specs DIR] --name NAME [--module-dir DIR]
  python3 spec_version_delta.py seq-names --spo FILE --kind overview|cross|module
  python3 spec_version_delta.py precheck --existing DIR --sources OUT_JSON \
      [--line-change-threshold-pct 20] --out OUT_JSON
  python3 spec_version_delta.py compare --baseline DIR --current DIR [--modules NAMES] --out OUT_JSON

sources: モジュールごとに spec_dir（latest-specs のディレクトリ名）・module_dir・layout・source_files（資料。どの配置でも
  1つ。`--out-dir` を渡すと統合パス・索引は分割パスと同じ形に直して `{out-dir}/{name}-spo.md` に書く。渡さなければ
  統合パス・索引の source_files は空）・sequences（§4.5 の小見出しとファイル名）・existing_spec を返す。ほかに
  overview_sequences・missing_docs・chd_only・chd_unmatched（`--chd`）・missing_module_dirs と
  protected_by_concurrent_cr（`--repo-path`）・conflicts を返す。
spec-dir: `docs_layout.resolve_spec_dir` の CLI。stdout に {"spec_dir", "duplicates"}（重複は stderr にも出す）。
seq-names: SPO サマリー §3（overview）・cross SPO §3（cross）・モジュール資料／SURVEY の §4.5（module）の小見出しとファイル名の一覧。
precheck の出力: {"ok": true, "force_update_files": [...], "diagnostics": {...}}
  既存のファイルの SPO から作る節（EXISTING_COMPARED_SECTIONS）だけを、資料の対応する節と比べる。
compare の出力:   {"ok": true, "version_floors": {...}, "rewritten_files": [...], "diagnostics": {...}}
  compare はバージョン下限を下回るファイルのフロントマター `version:`・§1 の「バージョン」行・
  「変更履歴」テーブルの直近エントリ（最終行）のバージョン列を実際に書き換える。`--modules`（カンマ区切りの
  spec_dir）を渡すと、その下のファイルだけを対象にする。

終了コード: 0 正常 / 1 入力の不正（台帳の書式不正・テンプレートが無い等。stderr にメッセージ）。
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xddp-common" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xddp-04-specout" / "scripts"))
import docs_layout  # noqa: E402
import specout_bfs  # noqa: E402

DEFAULT_MODULE_TEMPLATE = (Path(__file__).resolve().parents[2] / "xddp-04-specout" / "templates"
                           / "04_specout-module-template.md")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)```", re.S)
EDGE_TOKEN_RE = re.compile(r"-{1,2}[.\-]{0,2}[|ox*]{0,1}-?>{1,2}|\.\.\|?>")
NODE_TOKEN_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?=[\[\(\{])")
PARTICIPANT_RE = re.compile(r"^\s*(?:participant|actor)\s+(\S+)")

# 資料（分割パスの形。`04_specout-module-template.md`）の節のうち、各ファイルの材料になる節
FILE_TO_SPO_SECTION = {
    # 「既存仕様の文書化」（`## 3.`）は仕様書がない場合の代替セクション。存在すれば含める
    # （xddp-11-specs/SKILL.md Step MOD の spec.md 生成規則に対応）。
    "spec.md": {"level": 2, "names": ["現状仕様", "既存仕様の文書化（仕様書がない場合）"], "prefixes": ["2.", "3."]},
    "structure.md": {"level": 3, "names": ["データ型関連図", "データ構造", "PAD（問題分析図）"], "prefixes": []},
    "state-machine.md": {"level": 3, "names": ["状態遷移図"], "prefixes": []},
}
SEQUENCE_PARENT_HEADING = {"level": 3, "names": ["モジュール内シーケンス図"], "prefixes": []}
OVERVIEW_SEQUENCE_HEADING = {"level": 2, "names": ["モジュール間シーケンス図"], "prefixes": []}
CROSS_SEQUENCE_HEADING = {"level": 2, "names": ["シーケンス図"], "prefixes": []}
SEQUENCE_FILE_KIND = "sequence"
DEFAULT_SEQ_FILE = "main-seq.md"

# 既存のファイル（`11_module-*-template.md`）のうち、SPO から作る節（文書概要・関連ドキュメント・気づき・変更履歴を除く）。
# precheck はこの節だけを比べる。名前はテンプレートの `## N.` の見出し（番号を除く）とテストで突き合わせる。
EXISTING_COMPARED_SECTIONS = {
    "spec.md": ["機能概要", "入出力", "処理フロー", "正常系・異常系", "制約・前提条件"],
    "structure.md": ["データ型関連図", "データ構造定義表", "PAD（問題分析図）"],
    "state-machine.md": ["状態一覧", "状態遷移図", "遷移条件詳細"],
    SEQUENCE_FILE_KIND: ["シナリオ説明", "シーケンス図"],
}
EXISTING_COMPARED_TEMPLATES = {
    "spec.md": "11_module-spec-template.md",
    "structure.md": "11_module-structure-template.md",
    "state-machine.md": "11_module-state-machine-template.md",
    SEQUENCE_FILE_KIND: "11_module-sequence-template.md",
}


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


def _is_na(body: str) -> bool:
    lines = [ln.strip() for ln in body.splitlines()
             if ln.strip() and ln.strip() != "---" and not ln.strip().startswith(("<!--", ">"))]
    return not lines or lines[0].startswith("対象外")


def sequence_subsections(text: str, parent: dict, stem_fn=docs_layout.seq_file_stem) -> list | None:
    """`parent` の見出しの子見出し（レベル+1）を [{"heading", "file", "body"}] で返す。親の見出しが無ければ None。

    ファイル名は `stem_fn(見出し, 順番)` + `-seq.md`（`docs_layout.seq_file_stem`。cross は `cross_seq_stem`）。
    子見出しが無く本文が「対象外」でなければ [{"heading": "", "file": "main-seq.md"}]（SKILL.md の
    「見出しなし・単一の場合は main-seq.md をデフォルトとする」規則）。
    """
    lines = text.splitlines()
    for idx, lvl, name in iter_headings(lines):
        if lvl != parent["level"] or not matches_heading(name, parent["names"], parent["prefixes"]):
            continue
        body_end = idx + 1
        while body_end < len(lines):
            m = HEADING_RE.match(lines[body_end])
            if m and len(m.group(1)) <= lvl:
                break
            body_end += 1
        body_lines = lines[idx + 1:body_end]
        subs = [(sidx, sname) for sidx, slvl, sname in iter_headings(body_lines) if slvl == lvl + 1]
        if not subs:
            body = "\n".join(body_lines)
            return [] if _is_na(body) else [{"heading": "", "file": DEFAULT_SEQ_FILE, "body": body}]
        out = []
        for i, (sidx, sname) in enumerate(subs):
            end = subs[i + 1][0] if i + 1 < len(subs) else len(body_lines)
            out.append({"heading": sname, "file": f"{stem_fn(sname, i + 1)}-seq.md",
                        "body": "\n".join(body_lines[sidx + 1:end])})
        return out
    return None


def extract_sequence_subsection(text: str, seq_file: str) -> str | None:
    """資料の `### 4.5 モジュール内シーケンス図` の小見出しのうち、ファイル名が `seq_file`（`{語幹}-seq.md`）になるものの本文。
    ファイル名は NFC にそろえて比べる。小見出しが1つだけで `main-seq.md` を引いたときはその1件を返す。"""
    subs = sequence_subsections(text, SEQUENCE_PARENT_HEADING)
    if not subs:
        return None
    want = docs_layout.nfc(seq_file)
    for s in subs:
        if docs_layout.nfc(s["file"]) == want:
            return s["body"]
    if len(subs) == 1 and want == DEFAULT_SEQ_FILE:
        return subs[0]["body"]
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

def existing_compared_text(existing_text: str, kind: str) -> tuple[str, bool]:
    """既存のファイルのうち比べる節（EXISTING_COMPARED_SECTIONS[kind]。`## N.` の見出し）の本文。
    戻り値: (本文, 節が見つかったか)。1つも見つからなければファイルの全体を返す。"""
    found = extract_sections(existing_text, {"level": 2, "names": EXISTING_COMPARED_SECTIONS[kind], "prefixes": []})
    return (found, True) if found is not None else (existing_text, False)


def precheck(existing_root: Path, sources: dict, threshold_pct: float) -> dict:
    """`sources` の一覧のモジュール（SPO のあるもの）について、latest-specs の既存のファイルと資料を比べる。"""
    force_update_files: list[str] = []
    diagnostics: dict[str, dict] = {}

    if not existing_root.is_dir():
        return {"ok": True, "force_update_files": [], "diagnostics": {}}

    for mod in sources.get("modules", []):
        module = mod["spec_dir"]
        module_dir = existing_root / module
        if not module_dir.is_dir():
            continue
        files = mod.get("source_files") or []
        if not files or not Path(files[0]).is_file():
            diagnostics[module] = {"skipped": "no_spo_file"}
            continue
        spo_text = Path(files[0]).read_text(encoding="utf-8")

        targets: list[tuple[str, dict | None, str]] = []
        for filename, spec in FILE_TO_SPO_SECTION.items():
            targets.append((filename, spec, filename))
        seq_dir = module_dir / "sequences"
        if seq_dir.is_dir():
            for seq_file in sorted(seq_dir.glob("*-seq.md")):
                targets.append((f"sequences/{seq_file.name}", None, SEQUENCE_FILE_KIND))

        for rel_name, spec, kind in targets:
            existing_file = module_dir / rel_name
            if not existing_file.is_file():
                continue
            existing_text, sections_found = existing_compared_text(existing_file.read_text(encoding="utf-8"), kind)

            if spec is not None:
                spo_section = extract_sections(spo_text, spec)
            else:
                spo_section = extract_sequence_subsection(spo_text, Path(rel_name).name)

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
            if not sections_found:
                diagnostics[key]["existing_sections_not_found"] = True
            if mermaid_changed or text_changed:
                force_update_files.append(f"{module}/{rel_name}")

    return {"ok": True, "force_update_files": force_update_files, "diagnostics": diagnostics}


def _write_json(path, result: dict) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _read_json(path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        _err(f"JSON を読めません: {path}（{e}）")


def cmd_precheck(args) -> None:
    result = precheck(Path(args.existing), _read_json(args.sources), args.line_change_threshold_pct)
    _write_json(args.out, result)
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


OVERVIEW_VERSION_ROW_RE = re.compile(r"^(\|\s*バージョン\s*\|\s*)[0-9]+\.[0-9]+\.[0-9]+(\s*\|\s*)$")


def rewrite_overview_version(text: str, new_version: str) -> str:
    """`## 1. 文書概要` の表の `| バージョン | x.y.z |` の行を書き換える（節の外の行は触らない）。"""
    lines = text.split("\n")
    in_overview = False
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            in_overview = len(m.group(1)) == 2 and normalize_heading_text(m.group(2)) == "文書概要"
            continue
        if in_overview:
            mm = OVERVIEW_VERSION_ROW_RE.match(line)
            if mm:
                lines[i] = f"{mm.group(1)}{new_version}{mm.group(2)}"
                break
    return "\n".join(lines)


def rewrite_version(text: str, new_version: str) -> str:
    if VERSION_LINE_RE.search(text):
        text = VERSION_LINE_RE.sub(lambda m: f'{m.group(1)}"{new_version}"', text, count=1)
    text = rewrite_overview_version(text, new_version)
    text = rewrite_changelog_latest_version(text, new_version)
    return text


def compare(baseline_root: Path, current_root: Path, modules: list[str] | None = None) -> dict:
    """`modules`（spec_dir の一覧）を渡すと、その下のファイルだけに下限を当てはめる（SPO で確かめたモジュール）。"""
    version_floors: dict[str, dict] = {}
    rewritten_files: list[str] = []
    diagnostics: dict[str, str] = {}

    if not baseline_root.is_dir():
        return {"ok": True, "version_floors": {}, "rewritten_files": [], "diagnostics": {}}

    for baseline_file in sorted(baseline_root.rglob("*.md")):
        rel = baseline_file.relative_to(baseline_root)
        if modules is not None and (len(rel.parts) < 2 or rel.parts[0] not in modules):
            continue
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
    modules = None if args.modules is None else [m.strip() for m in args.modules.split(",") if m.strip()]
    result = compare(Path(args.baseline), Path(args.current), modules)
    _write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False))


# ---------------------------------------------------------------------------
# sources（工程11 の入力の一覧）・spec-dir・seq-names
# ---------------------------------------------------------------------------

CHD_FILE_TABLE_HEADING = "変更対象ファイル一覧"
CHD_PATH_COLUMN = "ファイルパス"
CHD_KIND_COLUMN = "変更種別"
CHD_REPO_COLUMN = "リポジトリ"
_PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")


def in_module(file_path: str, module_dir: str) -> bool:
    """`file_path` が `module_dir`（`module-dir` の値）の範囲にあるか。`.` は直下のファイルだけ。
    1ファイルのモジュール（`module_dir` がファイルのパス）は、そのパスと一致するときだけ。"""
    if not module_dir:
        return False
    if module_dir == ".":
        return file_path not in ("", ".") and "/" not in file_path
    return file_path == module_dir or file_path.startswith(module_dir + "/")


def _longest(file_path: str, dirs: dict) -> str:
    """{名前: module-dir} のうち `file_path` を範囲に持つ最長のものの名前（無ければ空）。"""
    best, best_len = "", -1
    for name, md in dirs.items():
        if in_module(file_path, md):
            length = 0 if md == "." else len(md)
            if length > best_len:
                best, best_len = name, length
    return best


def _existing_module_dirs(root) -> dict:
    """{ディレクトリ名: module-dir}（`module-dir` が空のものも空文字列で含む）。root が無ければ空。"""
    if not root or not Path(root).is_dir():
        return {}
    return {d: docs_layout.spec_module_dir(Path(root) / d) for d in docs_layout.module_names(root)}


def _table_rows(lines: list[str], start: int, end: int) -> tuple[list[str], list[list[str]]]:
    """[start, end) の最初の表の (見出しのセル, 行のセル)。"""
    header, rows = [], []
    for ln in lines[start:end]:
        s = ln.strip()
        if not s.startswith("|"):
            if header:
                break
            continue
        cells = [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", s.strip("|"))]
        if not header:
            header = cells
        elif re.match(r"^:?-{3,}:?$", cells[0] or "---") and all(re.match(r"^:?-{3,}:?$", c) for c in cells if c):
            continue
        else:
            rows.append(cells)
    return header, rows


def chd_changed_files(chd_files: list[str], repo: str, repo_path: str) -> list[dict]:
    """CHD の「## 2. 変更対象ファイル一覧」の行 [{"file", "kind"}]（列は見出しの名前で引く。「リポジトリ」列があれば
    `repo` の行だけ。パスは `specout_bfs._norm_path` で `REPO_PATH` 相対にする。プレースホルダーの行は除く）。"""
    out, seen = [], set()
    for chd in chd_files:
        path = Path(chd)
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").split("\n")
        start = next((i for i, ln in enumerate(lines)
                      if re.match(r"^##\s+", ln) and CHD_FILE_TABLE_HEADING in ln), None)
        if start is None:
            continue
        end = next((i for i in range(start + 1, len(lines)) if re.match(r"^##\s+", lines[i])), len(lines))
        header, rows = _table_rows(lines, start + 1, end)
        if CHD_PATH_COLUMN not in header:
            continue
        ip, ik = header.index(CHD_PATH_COLUMN), header.index(CHD_KIND_COLUMN) if CHD_KIND_COLUMN in header else None
        ir = header.index(CHD_REPO_COLUMN) if CHD_REPO_COLUMN in header else None
        for cells in rows:
            if ip >= len(cells):
                continue
            raw = cells[ip].strip().strip("`").strip()
            if not raw or _PLACEHOLDER_RE.search(raw):
                continue
            if ir is not None and ir < len(cells):
                r = cells[ir].strip().strip("`")
                if r and not _PLACEHOLDER_RE.search(r) and r != repo:
                    continue
            f = specout_bfs._norm_path(raw, repo_path)
            kind = cells[ik].strip() if ik is not None and ik < len(cells) else ""
            if f not in seen:
                seen.add(f)
                out.append({"file": f, "kind": kind})
    return out


def _source_text(mod: dict, template_text: str, cr: str, today: str) -> str:
    """資料を分割パスと同じ形の本文にする（統合パス・索引は変換、分割パスは元のファイル）。"""
    if mod["layout"] == "integrated":
        return specout_bfs.integrated_module_doc(mod["spo"], mod["name"], mod["module_dir"], template_text, cr, today)
    if mod["layout"] == "index":
        return specout_bfs.index_module_doc(mod["files"][0], mod["files"][1:], mod["name"], mod["module_dir"],
                                            template_text, cr, today)
    return Path(mod["files"][0]).read_text(encoding="utf-8")


def _seq_list(subs) -> list:
    return [{"heading": x["heading"], "file": x["file"]} for x in (subs or [])]


def sources(args) -> dict:
    spo_dir = Path(args.spo_dir)
    repo = args.repo or spo_dir.name
    repo_path = args.repo_path or ""
    latest = Path(args.latest_specs)
    docs = Path(args.docs_specs) if args.docs_specs else None
    roots = [latest] + ([docs] if docs else [])
    docs_info = specout_bfs.module_docs(spo_dir, args.cr, repo_path)
    need_text = any(m["layout"] in ("integrated", "index") for m in docs_info["modules"])
    template_text = ""
    if need_text:
        tpl = Path(args.module_template) if args.module_template else DEFAULT_MODULE_TEMPLATE
        if not tpl.is_file():
            _err(f"モジュール資料のテンプレートがありません: {tpl}")
        template_text = tpl.read_text(encoding="utf-8")
    out_dir = Path(args.out_dir) if args.out_dir else None
    modules, conflicts = [], []
    for m in docs_info["modules"]:
        spec_dir, dups = docs_layout.resolve_spec_dir(m["name"], m["module_dir"], roots)
        if dups:
            conflicts.append({"kind": "duplicate_module_dir", "module": m["name"], "module_dir": m["module_dir"],
                              "spec_dir": spec_dir, "duplicates": dups})
        try:
            text = _source_text(m, template_text, args.cr, args.today or "")
        except (OSError, ValueError) as e:
            _err(f"モジュール資料を読めません（{m['name']}）: {e}")
        if m["layout"] == "split":
            source_files = list(m["files"])
        elif out_dir is not None:
            target = out_dir / f"{m['name']}-spo.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            source_files = [str(target)]
        else:
            source_files = []
        existing = next((str(Path(r) / spec_dir / docs_layout.MODULE_SPEC_FILE) for r in roots
                         if (Path(r) / spec_dir / docs_layout.MODULE_SPEC_FILE).is_file()), "")
        modules.append({"name": m["name"], "spec_dir": spec_dir, "module_dir": m["module_dir"],
                        "layout": m["layout"], "source_files": source_files,
                        "sequences": _seq_list(sequence_subsections(text, SEQUENCE_PARENT_HEADING)),
                        "existing_spec": existing})
    # ケバブ名の衝突（同じ spec_dir に別の module-dir）
    existing_dirs = {}
    for r in reversed(roots):
        existing_dirs.update(_existing_module_dirs(r))
    by_dir = {}
    for m in modules:
        by_dir.setdefault(m["spec_dir"], set()).add(m["module_dir"])
        md_existing = existing_dirs.get(m["spec_dir"], "")
        if md_existing and md_existing != docs_layout.norm_module_dir(m["module_dir"]):
            by_dir[m["spec_dir"]].add(md_existing)
    for spec_dir, dirs in sorted(by_dir.items()):
        if len({docs_layout.norm_module_dir(d) for d in dirs}) > 1:
            conflicts.append({"kind": "spec_dir_collision", "spec_dir": spec_dir, "module_dirs": sorted(dirs)})
    spo_summary = spo_dir / f"SPO-{args.cr}.md"
    overview_sequences = (_seq_list(sequence_subsections(spo_summary.read_text(encoding="utf-8"),
                                                         OVERVIEW_SEQUENCE_HEADING))
                          if spo_summary.is_file() else [])
    result = {"ok": True, "repo": repo, "repo_layout": docs_info["layout"], "modules": modules,
              "missing_docs": docs_info["missing"], "overview_sequences": overview_sequences,
              "chd_only": [], "chd_unmatched": [], "missing_module_dirs": [], "protected_by_concurrent_cr": [],
              "conflicts": conflicts}
    # SPO の無いモジュール（CHD だけで当たるもの）
    if args.chd:
        spo_dirs = {m["name"]: docs_layout.norm_module_dir(m["module_dir"]) for m in modules}
        known = {}
        for r in reversed(roots):   # 先の root（latest-specs）の名前を優先する
            known.update({d: md for d, md in _existing_module_dirs(r).items() if md})
        spo_spec_dirs = {m["spec_dir"] for m in modules}
        chd_only = {}
        for row in chd_changed_files(args.chd, repo, repo_path):
            f = row["file"]
            if _longest(f, spo_dirs):
                continue
            hit = _longest(f, {d: md for d, md in known.items() if d not in spo_spec_dirs})
            if hit:
                chd_only.setdefault(hit, {"spec_dir": hit, "module_dir": known[hit], "files": []})["files"].append(f)
            else:
                result["chd_unmatched"].append(f)
        result["chd_only"] = [chd_only[k] for k in sorted(chd_only)]
    # 母体から消えたモジュール（廃止候補）
    if repo_path:
        listed = specout_bfs.list_repo_files(repo_path, specout_bfs._split_csv(args.exclude or ""),
                                             specout_bfs._split_csv(args.include_ext or ""))
        for d, md in sorted(_existing_module_dirs(latest).items()):
            if not md:
                continue
            target = Path(repo_path) / md
            if md != "." and not target.exists():
                reason = "母体にディレクトリ・ファイルが無い"
            elif any(in_module(f, md) for f in listed):
                continue
            else:
                reason = "母体に対象のファイルが無い"
            last_cr = docs_layout.last_updated_cr(latest / d / docs_layout.MODULE_SPEC_FILE)
            entry = {"spec_dir": d, "module_dir": md, "reason": reason}
            if (args.xddp_dir and last_cr and last_cr != args.cr
                    and docs_layout.cr_in_progress(args.xddp_dir, last_cr)):
                result["protected_by_concurrent_cr"].append({**entry, "last_updated_cr": last_cr})
            else:
                result["missing_module_dirs"].append(entry)
    return result


def cmd_sources(args) -> None:
    result = sources(args)
    _write_json(args.out, result)
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in result.items()}, ensure_ascii=False))


def cmd_spec_dir(args) -> None:
    roots = [Path(args.latest_specs)] + ([Path(args.docs_specs)] if args.docs_specs else [])
    spec_dir, dups = docs_layout.resolve_spec_dir(args.name, args.module_dir or "", roots)
    for d in dups:
        print(f"同じ module-dir の既存のディレクトリが複数あります（{spec_dir} を使う）: {d}", file=sys.stderr)
    print(json.dumps({"ok": True, "spec_dir": spec_dir, "duplicates": dups}, ensure_ascii=False))


def cmd_seq_names(args) -> None:
    path = Path(args.spo)
    if not path.is_file():
        _err(f"SPO がありません: {path}")
    text = path.read_text(encoding="utf-8")
    if args.kind == "cross":
        subs = sequence_subsections(text, CROSS_SEQUENCE_HEADING, docs_layout.cross_seq_stem)
    elif args.kind == "module":
        subs = sequence_subsections(text, SEQUENCE_PARENT_HEADING)
    else:
        subs = sequence_subsections(text, OVERVIEW_SEQUENCE_HEADING)
    print(json.dumps({"ok": True, "sequences": _seq_list(subs)}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="xddp-11-specs の入力の一覧と Step MOD 機械的先決基準")
    sub = parser.add_subparsers(dest="command", required=True)

    p_src = sub.add_parser("sources", help="工程11 の入力の一覧（モジュール資料・latest-specs のディレクトリ名）を作る")
    p_src.add_argument("--spo-dir", required=True, help="{CR_PATH}/04_specout/{repo}")
    p_src.add_argument("--cr", required=True)
    p_src.add_argument("--latest-specs", required=True, help="{XDDP_DIR}/latest-specs/{repo}")
    p_src.add_argument("--docs-specs", help="{DOCS}/{repo}/specs")
    p_src.add_argument("--repo", help="リポジトリ名（既定は --spo-dir の名前）")
    p_src.add_argument("--repo-path", help="REPO_PATH（廃止候補・CHD のパスの正規化に使う）")
    p_src.add_argument("--exclude", help="SPECOUT_EXCLUDE_PATTERNS（カンマ区切り）")
    p_src.add_argument("--include-ext", help="SPECOUT_INCLUDE_EXTENSIONS（カンマ区切り）")
    p_src.add_argument("--xddp-dir", help="{XDDP_DIR}（並行 CR 保護の判定に使う）")
    p_src.add_argument("--chd", nargs="*", default=[], help="CHD の本文ファイル（## Discover CHD Files の結果）")
    p_src.add_argument("--out-dir", help="統合パス・索引の資料を分割パスの形に直して書く先")
    p_src.add_argument("--module-template", help="04_specout-module-template.md（既定はスクリプトの位置から決める）")
    p_src.add_argument("--today", help="直した資料の日付（既定は SPO・索引の作成日）")
    p_src.add_argument("--out", required=True)
    p_src.set_defaults(func=cmd_sources)

    p_dir = sub.add_parser("spec-dir", help="latest-specs のディレクトリ名を決める（resolve_spec_dir）")
    p_dir.add_argument("--latest-specs", required=True)
    p_dir.add_argument("--docs-specs")
    p_dir.add_argument("--name", required=True)
    p_dir.add_argument("--module-dir", default="")
    p_dir.set_defaults(func=cmd_spec_dir)

    p_seq = sub.add_parser("seq-names", help="SPO のシーケンス図の小見出しとファイル名")
    p_seq.add_argument("--spo", required=True)
    p_seq.add_argument("--kind", choices=["overview", "cross", "module"], required=True)
    p_seq.set_defaults(func=cmd_seq_names)

    p_precheck = sub.add_parser("precheck", help="既存ファイルの更新要否を機械判定する")
    p_precheck.add_argument("--existing", required=True, help="latest-specs/{repo} のパス")
    p_precheck.add_argument("--sources", required=True, help="sources の出力 JSON")
    p_precheck.add_argument("--line-change-threshold-pct", type=float, default=20.0)
    p_precheck.add_argument("--out", required=True)
    p_precheck.set_defaults(func=cmd_precheck)

    p_compare = sub.add_parser("compare", help="バージョン下限を算出し必要なら自動書き換える")
    p_compare.add_argument("--baseline", required=True)
    p_compare.add_argument("--current", required=True)
    p_compare.add_argument("--modules", help="対象にする spec_dir（カンマ区切り。SPO のあるモジュール）")
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
