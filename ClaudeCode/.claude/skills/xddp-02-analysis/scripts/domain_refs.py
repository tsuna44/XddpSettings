"""
domain_refs.py — xddp-02-analysis Step 0 の決定的処理（既存知識の参照先解決）

`{DOCS}` と latest-specs を直接列挙して、工程2 の参照先（DOMAIN_REF_PATHS）を決める。
AI_INDEX.md は読まない。意味判定（変更要求書からのキーワード抽出）は呼び出し元（LLM）が行い、
その結果を --keywords-file（1行1キーワード）として本スクリプトへ渡す。

- 名前が決まったら、`{DOCS}` 側のファイルがあればそれ、無ければ latest-specs 側のファイルを渡す
  （latest-specs から1件でも入れば DOMAIN_REF_MODE は degraded）。
- ユースケース・モジュール・cross のインタフェースは `{DOCS}` と latest-specs のディレクトリ名の和集合から
  キーワードで選ぶ。共有の知見（`_structures/`・`_constants/`）は直下の `*.md` をすべて渡す。

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

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xddp-common" / "scripts"))
import docs_layout as layout  # noqa: E402
from knowledge_place import GENERAL_PLACE, ROOT_PLACE, applicable_places, list_places  # noqa: E402

DELIMITER_RE = re.compile(r"[-_\s]")
EXTENSION_RE = re.compile(r"\.[A-Za-z0-9]+$")

# キーワードに当たらず {DOCS} 側に1つも無いときに、latest-specs から更新日時の新しい順に読む件数
FALLBACK_TOP_N = 3

# 工程2 で集める共有の知見のディレクトリ（種別名は docs_layout.SHARED_KNOWLEDGE_DIRS）
COLLECTED_SHARED_DIRS = ("_structures", "_constants")


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


def select_constraint_places(places: list[str], keywords: list[str],
                             matched_modules: list[str]) -> list[str]:
    """制約の置き場所のうち工程2 の参照先にするものを返す（code-knowledge の直接列挙から）。

    1. `_general`・`_root`（キーワードによらない）
    2. 置き場所の最後の要素にキーワードが resolve_matches で当たるものと、その祖先の置き場所
    3. 最新仕様のモジュール名（matched_modules）と一致する置き場所
    """
    place_set = set(places)
    selected = {p for p in places if p in (GENERAL_PLACE, ROOT_PLACE)}
    normal = [p for p in places if p not in (GENERAL_PLACE, ROOT_PLACE)]
    last_elems = sorted({p.split("/")[-1] for p in normal})
    matched_last = set(resolve_matches(last_elems, keywords))
    for p in normal:
        if p.split("/")[-1] in matched_last:
            # p 自身と祖先（p の下のファイルに当てはまる置き場所のうち _general・_root 以外）
            for anc in applicable_places(p + "/_"):
                if anc in place_set and anc not in (GENERAL_PLACE, ROOT_PLACE):
                    selected.add(anc)
    selected |= place_set & set(matched_modules)
    return sorted(selected)


def top_n_recent(paths: list[Path], n: int) -> list[Path]:
    existing = [p for p in paths if p.is_file()]
    existing.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return existing[:n]


# ---------------------------------------------------------------------------
# メイン解決ロジック
# ---------------------------------------------------------------------------

class _Names:
    """`{DOCS}` と latest-specs のディレクトリ名の和集合と、名前ごとのファイル（{DOCS} 優先）。"""

    def __init__(self, docs_root: Path, latest_root: Path, filename: str, names_fn=layout.subdir_names):
        self.docs_names = [n for n in names_fn(docs_root)]
        self.files: dict[str, tuple[Path, bool]] = {}
        for n in sorted(set(self.docs_names) | set(names_fn(latest_root))):
            d = docs_root / n / filename
            l_ = latest_root / n / filename
            if d.is_file():
                self.files[n] = (d, False)
            elif l_.is_file():
                self.files[n] = (l_, True)

    @property
    def names(self) -> list[str]:
        return sorted(self.files)


def _related_values(path: Path) -> list[str]:
    try:
        fm = layout.parse_frontmatter(path.read_text(encoding="utf-8"))
    except OSError:
        return []
    return layout.usecase_related_modules(fm)


def _purpose(path: Path) -> str:
    try:
        return layout.usecase_purpose(path.read_text(encoding="utf-8"))
    except OSError:
        return ""


def resolve(workspace_root: Path, xddp_dir: str, docs: Path,
            affected_repos: list[str], is_multi: bool,
            keywords: list[str]) -> dict:
    col = Collector()
    stats = {
        "docs_sourced": 0,
        "latest_specs_sourced": 0,
        "excluded_by_delimiter": 0,
        "fallback_applied": [],
        "unresolved_related_modules": [],
    }
    latest_specs = workspace_root / xddp_dir / "latest-specs"
    areas = list(affected_repos) + ([layout.CROSS_AREA] if is_multi else [])

    def add_docs(path: Path, type_: str) -> None:
        if path.is_file():
            col.add(path, type_)
            stats["docs_sourced"] += 1

    def add_entry(entry: tuple[Path, bool], type_: str) -> None:
        path, from_latest = entry
        col.add(path, type_)
        stats["latest_specs_sourced" if from_latest else "docs_sourced"] += 1

    # --- ユースケース ---
    usecases = _Names(layout.docs_usecases_dir(docs), layout.latest_usecases_dir(latest_specs),
                      layout.USECASE_FILE)
    by_name = set(resolve_matches(usecases.names, keywords))
    by_purpose = {n for n in usecases.names
                  if text_contains_keyword(_purpose(usecases.files[n][0]), keywords)}
    matched_usecases = sorted(by_name | by_purpose)
    if matched_usecases:
        uc_entries = [usecases.files[n] for n in matched_usecases]
    elif not usecases.docs_names:
        latest_uc = [p for p, from_latest in usecases.files.values() if from_latest]
        uc_entries = [(p, True) for p in top_n_recent(latest_uc, FALLBACK_TOP_N)]
        if uc_entries:
            stats["fallback_applied"].append("b")
    else:
        uc_entries = []

    # --- モジュールの仕様（キーワード・当たったユースケースの関連モジュール） ---
    modules = {
        repo: _Names(layout.docs_specs_root(docs, repo), layout.latest_specs_root(latest_specs, repo),
                     layout.MODULE_SPEC_FILE, layout.module_names)
        for repo in affected_repos
    }
    matched_modules: dict[str, set[str]] = {
        repo: set(resolve_matches(modules[repo].names, keywords)) for repo in affected_repos
    }
    for uc in matched_usecases:
        for value in _related_values(usecases.files[uc][0]):
            found = False
            for repo in affected_repos:
                for name in modules[repo].names:
                    if normalize_token(name) == normalize_token(value):
                        matched_modules[repo].add(name)
                        found = True
            if not found:
                stats["unresolved_related_modules"].append(
                    {"repos": list(affected_repos), "usecase": uc, "value": value})

    for entry in uc_entries:
        add_entry(entry, "ユースケース")
    for repo in affected_repos:
        names = sorted(matched_modules[repo])
        if names:
            for name in names:
                add_entry(modules[repo].files[name], "仕様")
        elif not modules[repo].docs_names:
            latest_mod = [p for p, from_latest in modules[repo].files.values() if from_latest]
            picked = top_n_recent(latest_mod, FALLBACK_TOP_N)
            if picked:
                stats["fallback_applied"].append(f"a:{repo}")
            for p in picked:
                add_entry((p, True), "仕様")

    # --- cross のインタフェース仕様 ---
    if is_multi:
        interfaces = _Names(layout.docs_interfaces_dir(docs), layout.latest_interfaces_dir(latest_specs),
                            layout.INTERFACE_SPEC_FILE)
        for name in resolve_matches(interfaces.names, keywords):
            add_entry(interfaces.files[name], "仕様")

    # --- 共有の知見（_structures・_constants の直下の *.md をファイル単位で） ---
    for area in areas:
        ck = layout.code_knowledge_dir(docs, area)
        for dirname in COLLECTED_SHARED_DIRS:
            d = ck / dirname
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                add_docs(f, layout.SHARED_KNOWLEDGE_DIRS[dirname])

    # --- 知見ログ ---
    for area in areas:
        add_docs(docs / area / "knowledge" / "lessons-learned.md", "知見")

    # --- 制約: code-knowledge の直接列挙 ---
    for repo in affected_repos:
        know = layout.code_knowledge_dir(docs, repo)
        for place in select_constraint_places(list_places(know), keywords,
                                              sorted(matched_modules[repo])):
            add_docs(know / place / "constraints.md", "制約")

    # --- 用語集 ---
    add_docs(docs / "glossary.md", "用語")
    for area in areas:
        add_docs(docs / area / "knowledge" / "glossary.md", "用語")

    stats["excluded_by_delimiter"] = col.excluded_by_delimiter

    # --- DOMAIN_REF_PATHS / DOMAIN_REF_MODE ---
    domain_ref_paths = " ; ".join(f"{p} | {t}" for p, t in col.items)
    if not col.items:
        domain_ref_mode = "none"
    elif stats["latest_specs_sourced"] > 0:
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
