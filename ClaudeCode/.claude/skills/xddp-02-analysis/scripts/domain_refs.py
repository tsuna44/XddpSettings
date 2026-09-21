"""
domain_refs.py — xddp-02-analysis Step 0 の決定的処理（既存知識の参照先解決）

SKILL.md Step 0 の手順 3-1/3-1a/3-1b/3-2/3-3/3-4/3-5/3-6・4 を移植する。
意味判定（手順 3-0: 変更要求書からのキーワード抽出）は呼び出し元（LLM）が行い、
その結果を --keywords-file（1行1キーワード）として本スクリプトへ渡す。

Usage:
  python3 domain_refs.py resolve --workspace-root PATH --xddp-dir REL --docs PATH \
      --affected-repos csv [--is-multi] --keywords-file PATH --out OUT_JSON

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import json
import re
import sys
from pathlib import Path

DELIMITER_RE = re.compile(r"[-_\s]")
EXTENSION_RE = re.compile(r"\.[A-Za-z0-9]+$")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
TABLE_ROW_RE = re.compile(r"^\s*\|")
TABLE_SEP_RE = re.compile(r"^[\s|:-]+$")

# 手順3-4 の更新日時上位N件補完の上限
FALLBACK_TOP_N = 3

# code-knowledge の _structures/_constants ラベル（promote.py update_ai_index() と同一の対応）
CODE_KNOWLEDGE_SPECIAL_DIRS = {
    "_structures": "共有構造体",
    "_constants": "共有定数",
}


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def normalize_token(s: str) -> str:
    """手順3-2 の照合正規化規則: 区切り文字（- _ 空白）と拡張子を除去し小文字化する。"""
    s = EXTENSION_RE.sub("", s.strip())
    s = DELIMITER_RE.sub("", s)
    return s.lower()


def resolve_matches(candidates: list[str], keywords: list[str]) -> list[str]:
    """候補名リストをキーワード集合と照合する（完全一致優先・0件時のみ部分一致フォールバック）。

    完全一致には文字数制限を適用しない。部分一致は双方の正規化後文字列が3文字以上の場合のみ。
    """
    kw_norms = [normalize_token(k) for k in keywords if k.strip()]
    if not kw_norms:
        return []
    exact = [c for c in candidates if normalize_token(c) in kw_norms]
    if exact:
        return exact
    partial = []
    for c in candidates:
        cn = normalize_token(c)
        if len(cn) < 3:
            continue
        for kn in kw_norms:
            if len(kn) < 3:
                continue
            if cn in kn or kn in cn:
                partial.append(c)
                break
    return partial


def text_contains_keyword(text: str, keywords: list[str]) -> bool:
    """自由文（目的列等）にキーワードのいずれかが正規化後に部分文字列として含まれるか。"""
    tn = normalize_token(text)
    if not tn:
        return False
    for k in keywords:
        kn = normalize_token(k)
        if kn and kn in tn:
            return True
    return False


def read_keywords(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        _err(f"keywords-file の読み込みに失敗しました: {path} ({e})")
    return [l.strip() for l in lines if l.strip()]


# ---------------------------------------------------------------------------
# Markdown テーブル解析（AI_INDEX.md 用の軽量パーサ）
# ---------------------------------------------------------------------------

def find_section(text: str, heading: str) -> str | None:
    """`## {heading}` セクションの本文（見出し行を除く、次の `## ` 見出しの直前まで）を返す。"""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == f"## {heading}":
            start = i + 1
            break
    if start is None:
        return None
    end = start
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    return "\n".join(lines[start:end])


def parse_markdown_table(section_text: str) -> tuple[list[str], list[list[str]]] | None:
    """`| a | b |` 形式のテーブルをヘッダ行・データ行に分解する。不正形式は None。"""
    table_lines = [l for l in section_text.splitlines() if TABLE_ROW_RE.match(l)]
    if len(table_lines) < 2:
        return None

    def split_row(line: str) -> list[str]:
        cells = line.strip().strip("|").split("|")
        return [c.strip() for c in cells]

    header = split_row(table_lines[0])
    if not TABLE_SEP_RE.match(table_lines[1]):
        return None
    rows = [split_row(l) for l in table_lines[2:]]
    # 列数がヘッダと一致しない行は破棄せず不足分を空文字で埋める（軽微な崩れを許容）
    normalized_rows = []
    for r in rows:
        if len(r) < len(header):
            r = r + [""] * (len(header) - len(r))
        normalized_rows.append(r)
    return header, normalized_rows


def extract_link_path(cell: str) -> str | None:
    m = MD_LINK_RE.search(cell)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# 収集結果の格納
# ---------------------------------------------------------------------------

class Collector:
    def __init__(self):
        self._seen: set[str] = set()
        self.items: list[tuple[str, str]] = []  # (abs_path, type)
        self.excluded_by_delimiter = 0

    def add(self, path: Path, type_: str) -> None:
        abs_path = str(path.resolve())
        if "|" in abs_path or ";" in abs_path or "|" in type_ or ";" in type_:
            self.excluded_by_delimiter += 1
            return
        key = f"{abs_path}\x00{type_}"
        if key in self._seen:
            return
        self._seen.add(key)
        self.items.append((abs_path, type_))


def top_n_recent(paths: list[Path], n: int) -> list[Path]:
    existing = [p for p in paths if p.is_file()]
    existing.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return existing[:n]


# ---------------------------------------------------------------------------
# メイン解決ロジック
# ---------------------------------------------------------------------------

def resolve(workspace_root: Path, xddp_dir: str, docs: Path,
            affected_repos: list[str], is_multi: bool,
            keywords: list[str]) -> dict:
    col = Collector()
    stats = {
        "docs_sourced": 0,
        "latest_specs_sourced": 0,
        "excluded_by_delimiter": 0,
        "ai_index_present": False,
        "fallback_applied": [],
        "ai_index_malformed_sections": [],
    }

    latest_specs_root = workspace_root / xddp_dir / "latest-specs"

    ai_index_path = docs / "AI_INDEX.md"
    ai_index_present = ai_index_path.is_file()
    stats["ai_index_present"] = ai_index_present
    ai_index_text = ""
    if ai_index_present:
        try:
            ai_index_text = ai_index_path.read_text(encoding="utf-8")
        except OSError:
            ai_index_present = False
            stats["ai_index_present"] = False

    docs_system_specs_exists = (docs / "system" / "specs").is_dir()
    docs_repo_specs_exists = {r: (docs / r / "specs").is_dir() for r in affected_repos}

    matched_usecases: list[str] = []
    matched_modules: dict[str, list[str]] = {r: [] for r in affected_repos}

    def add_docs(path: Path, type_: str) -> None:
        if path.is_file():
            col.add(path, type_)
            stats["docs_sourced"] += 1

    if ai_index_present:
        # --- 3-2.1: ユースケース一覧 ---
        section = find_section(ai_index_text, "ユースケース一覧")
        parsed = parse_markdown_table(section) if section is not None else None
        usecase_ok = False
        if parsed:
            header, rows = parsed
            if "ユースケース" in header and "目的（1行）" in header:
                idx_uc = header.index("ユースケース")
                idx_purpose = header.index("目的（1行）")
                idx_related = header.index("関連モジュール") if "関連モジュール" in header else None
                names = [r[idx_uc] for r in rows if r[idx_uc] and not r[idx_uc].startswith("（")]
                by_name = set(resolve_matches(names, keywords))
                by_purpose = {
                    r[idx_uc] for r in rows
                    if r[idx_uc] in names and text_contains_keyword(r[idx_purpose], keywords)
                }
                matched_usecases = sorted(by_name | by_purpose)
                usecase_ok = True
                if idx_related is not None:
                    for r in rows:
                        if r[idx_uc] in matched_usecases and r[idx_related] not in ("", "—"):
                            for m in re.split(r"[、,]\s*", r[idx_related]):
                                m = m.strip()
                                if m:
                                    for repo in affected_repos:
                                        matched_modules.setdefault(repo, []).append(m)
        if section is not None and not usecase_ok:
            stats["ai_index_malformed_sections"].append("ユースケース一覧")

        for uc in matched_usecases:
            add_docs(docs / "system" / "specs" / "use-cases" / uc / "description.md", "ユースケース")

        # --- 3-2.2: モジュール別最新仕様 ---
        section = find_section(ai_index_text, "モジュール別最新仕様")
        parsed = parse_markdown_table(section) if section is not None else None
        module_ok = False
        if parsed:
            header, rows = parsed
            if "リポジトリ" in header and "モジュール" in header:
                idx_repo = header.index("リポジトリ")
                idx_mod = header.index("モジュール")
                module_ok = True
                for repo in affected_repos:
                    repo_mod_names = [r[idx_mod] for r in rows if r[idx_repo] == repo and r[idx_mod]]
                    by_kw = resolve_matches(repo_mod_names, keywords)
                    matched_modules[repo] = sorted(set(by_kw) | set(matched_modules.get(repo, [])))
        if section is not None and not module_ok:
            stats["ai_index_malformed_sections"].append("モジュール別最新仕様")

        for repo in affected_repos:
            for mod in matched_modules.get(repo, []):
                add_docs(docs / repo / "specs" / mod / "spec.md", "仕様")

        # --- 3-2.3: code-knowledge インデックス ---
        section = find_section(ai_index_text, "code-knowledge インデックス")
        parsed = parse_markdown_table(section) if section is not None else None
        ck_ok = False
        if parsed:
            header, rows = parsed
            if "知りたいこと" in header and "参照先" in header:
                ck_ok = True
                idx_label = header.index("知りたいこと")
                idx_ref = header.index("参照先")
                label_to_ref = {r[idx_label]: r[idx_ref] for r in rows}
                for repo in affected_repos:
                    for mod in matched_modules.get(repo, []):
                        label = f"{repo}/{mod} 制約・注意事項"
                        if label in label_to_ref:
                            link = extract_link_path(label_to_ref[label])
                            if link:
                                add_docs(docs / link, "制約")
                    for special_dir, type_name in CODE_KNOWLEDGE_SPECIAL_DIRS.items():
                        label = f"{repo} {type_name}"
                        if label not in label_to_ref:
                            continue
                        special_path = docs / repo / "knowledge" / "code-knowledge" / special_dir
                        if special_path.is_dir():
                            col.add(special_path, type_name)
                            stats["docs_sourced"] += 1
        if section is not None and not ck_ok:
            stats["ai_index_malformed_sections"].append("code-knowledge インデックス")

        # --- 3-2.4: lessons-learned.md（索引の有無によらず実施） ---
        for repo in affected_repos:
            add_docs(docs / repo / "knowledge" / "lessons-learned.md", "知見")

        # --- 3-2.5: クロスインタフェース一覧・lessons-learned（IS_MULTI のみ） ---
        if is_multi:
            add_docs(docs / "cross" / "knowledge" / "lessons-learned.md", "知見")
            section = find_section(ai_index_text, "クロスインタフェース一覧")
            parsed = parse_markdown_table(section) if section is not None else None
            if parsed:
                header, rows = parsed
                if "インタフェース" in header:
                    idx_if = header.index("インタフェース")
                    if_names = [r[idx_if] for r in rows if r[idx_if]]
                    matched_ifs = resolve_matches(if_names, keywords)
                    for name in matched_ifs:
                        add_docs(docs / "cross" / "specs" / "interfaces" / name / "spec.md", "仕様")
                elif section is not None:
                    stats["ai_index_malformed_sections"].append("クロスインタフェース一覧")
    else:
        # --- 3-1a: 索引なし直接列挙 ---
        if docs_system_specs_exists:
            uc_dir = docs / "system" / "specs" / "use-cases"
            names = [p.name for p in uc_dir.iterdir() if p.is_dir()] if uc_dir.is_dir() else []
            matched_usecases = resolve_matches(names, keywords)
            for uc in matched_usecases:
                add_docs(uc_dir / uc / "description.md", "ユースケース")

        for repo in affected_repos:
            if not docs_repo_specs_exists.get(repo):
                continue
            specs_dir = docs / repo / "specs"
            names = [p.name for p in specs_dir.iterdir() if p.is_dir()] if specs_dir.is_dir() else []
            matched = resolve_matches(names, keywords)
            matched_modules[repo] = matched
            for mod in matched:
                add_docs(specs_dir / mod / "spec.md", "仕様")

        if is_multi:
            cross_specs_dir = docs / "cross" / "specs"
            if cross_specs_dir.is_dir():
                names = [p.name for p in cross_specs_dir.iterdir() if p.is_dir()]
                matched = resolve_matches(names, keywords)
                for name in matched:
                    add_docs(cross_specs_dir / name / "spec.md", "仕様")

        # 3-2 項目4・5（索引に依存しないため索引なしでも実施）
        for repo in affected_repos:
            add_docs(docs / repo / "knowledge" / "lessons-learned.md", "知見")
        if is_multi:
            add_docs(docs / "cross" / "knowledge" / "lessons-learned.md", "知見")

    # --- 3-1b: 用語集の直接収集（AI_INDEX の有無によらず常に実施） ---
    add_docs(docs / "glossary.md", "用語")
    for repo in affected_repos:
        add_docs(docs / repo / "knowledge" / "glossary.md", "用語")
    if is_multi:
        add_docs(docs / "cross" / "knowledge" / "glossary.md", "用語")

    # --- 3-4: フォールバック列挙（{DOCS} 側の該当ディレクトリ自体が存在しない場合） ---
    for repo in affected_repos:
        if docs_repo_specs_exists.get(repo):
            continue
        stats["fallback_applied"].append(f"a:{repo}")
        ls_repo_dir = latest_specs_root / repo
        names = [p.name for p in ls_repo_dir.iterdir() if p.is_dir()] if ls_repo_dir.is_dir() else []
        matched = resolve_matches(names, keywords)
        candidate_paths = [ls_repo_dir / m / "spec.md" for m in matched]
        if not matched and ls_repo_dir.is_dir():
            all_paths = [p / "spec.md" for p in ls_repo_dir.iterdir() if p.is_dir()]
            candidate_paths = top_n_recent(all_paths, FALLBACK_TOP_N)
        for p in candidate_paths:
            if p.is_file():
                col.add(p, "仕様")
                stats["latest_specs_sourced"] += 1

    if not docs_system_specs_exists:
        stats["fallback_applied"].append("b")
        ls_uc_dir = latest_specs_root / "system" / "use-cases"
        names = [p.name for p in ls_uc_dir.iterdir() if p.is_dir()] if ls_uc_dir.is_dir() else []
        matched = resolve_matches(names, keywords)
        candidate_paths = [ls_uc_dir / m / "description.md" for m in matched]
        if not matched and ls_uc_dir.is_dir():
            all_paths = [p / "description.md" for p in ls_uc_dir.iterdir() if p.is_dir()]
            candidate_paths = top_n_recent(all_paths, FALLBACK_TOP_N)
        for p in candidate_paths:
            if p.is_file():
                col.add(p, "ユースケース")
                stats["latest_specs_sourced"] += 1

    stats["excluded_by_delimiter"] = col.excluded_by_delimiter

    # --- 4: DOMAIN_REF_PATHS / DOMAIN_REF_MODE ---
    domain_ref_paths = " ; ".join(f"{p} | {t}" for p, t in col.items)
    has_docs_sourced = stats["docs_sourced"] > 0
    has_latest_specs_sourced = stats["latest_specs_sourced"] > 0
    if not col.items:
        domain_ref_mode = "none"
    elif has_latest_specs_sourced:
        domain_ref_mode = "degraded"
    else:
        domain_ref_mode = "normal"

    return {
        "ok": True,
        "domain_ref_paths": domain_ref_paths,
        "domain_ref_mode": domain_ref_mode,
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_resolve(args) -> None:
    workspace_root = Path(args.workspace_root)
    if not workspace_root.is_dir():
        _err(f"workspace-root ディレクトリが見つかりません: {workspace_root}")
    docs = Path(args.docs)
    affected_repos = [r.strip() for r in args.affected_repos.split(",") if r.strip()]
    keywords = read_keywords(Path(args.keywords_file))

    result = resolve(
        workspace_root=workspace_root,
        xddp_dir=args.xddp_dir,
        docs=docs,
        affected_repos=affected_repos,
        is_multi=args.is_multi,
        keywords=keywords,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="xddp-02-analysis Step 0 決定的処理")
    sub = parser.add_subparsers(dest="command", required=True)

    p_resolve = sub.add_parser("resolve", help="既存知識の参照先を解決する")
    p_resolve.add_argument("--workspace-root", required=True)
    p_resolve.add_argument("--xddp-dir", required=True)
    p_resolve.add_argument("--docs", required=True)
    p_resolve.add_argument("--affected-repos", required=True, help="カンマ区切りのリポジトリ名一覧")
    p_resolve.add_argument("--is-multi", action="store_true")
    p_resolve.add_argument("--keywords-file", required=True)
    p_resolve.add_argument("--out", required=True)
    p_resolve.set_defaults(func=cmd_resolve)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
