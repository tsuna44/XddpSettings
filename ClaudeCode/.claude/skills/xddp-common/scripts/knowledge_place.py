"""knowledge_place.py — code-knowledge の知見の置き場所（MODULE）を決める CLI・関数群

知見（制約・落とし穴等）の対象の表記（ファイルパス・ディレクトリ・識別子）から、
`{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/` の置き場所 `{MODULE}` を決定的に決める。
約束事は `xddp-rules/code-knowledge-boundary.md`「## 知見の置き場所（MODULE）」、
設計根拠は docs/adr/ADR-0033-constraints-module-key.md を参照。

Usage:
  python3 knowledge_place.py place --repo-root REPO_ROOT --workspace-root WORKSPACE_ROOT [--input FILE]

  入力（--input のファイル、省略時は stdin）:
    [{"id": "...", "targets": ["src/db.go:45", "parse_header()"], "fallback": "_general"}, ...]
  stdout（JSON 1行）:
    [{"id": "...", "module": "src", "reserved_collision": false,
      "targets": [{"raw": "src/db.go:45", "status": "placed", "rel": "src/db.go", "place": "src"},
                  {"raw": "parse_header()", "status": "no-path"}]}, ...]
  status: placed / no-path / url / outside-repo / not-found

  終了コード: 0＝成功、1＝--repo-root のディレクトリが無い、2＝引数・入力 JSON の誤り。

関数（他スクリプトが sys.path 経由で import する）:
  list_places(know_dir)     : {KNOW} の下の constraints.md の置き場所の一覧（予約名の下を除く）
  applicable_places(rel)    : リポジトリのルートからの相対パスのファイルに当てはまる置き場所
  place_entries(...)        : place サブコマンドの本体

標準ライブラリのみ。
"""

import argparse
import json
import os
import posixpath
import re
import sys
from pathlib import Path

ROOT_PLACE = "_root"
GENERAL_PLACE = "_general"
# 置き場所の第1要素として予約された名前
RESERVED = ("_root", "_general", "_structures", "_constants", "_flows", "_cochange")
# 列挙（list_places）で constraints.md の置き場所として扱わない第1要素
NON_CONSTRAINT_DIRS = ("_structures", "_constants", "_flows", "_cochange")

URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
DRIVE_RE = re.compile(r"^([A-Za-z]):/")


class InputError(Exception):
    pass


# ---------------------------------------------------------------------------
# パスの正規化
# ---------------------------------------------------------------------------


def _slash(p: str) -> str:
    return p.replace("\\", "/")


def _is_abs(p: str) -> bool:
    return p.startswith("/") or bool(DRIVE_RE.match(p))


def _norm(p: str) -> str:
    """`.`・`..` を解決し、ドライブ名を小文字に揃える（シンボリックリンクは解決しない）。"""
    m = DRIVE_RE.match(p)
    if m:
        rest = posixpath.normpath("/" + p[3:])
        return m.group(1).lower() + ":" + rest
    return posixpath.normpath(p)


def _abs_dir(p: str, base: str = None) -> str:
    p = _slash(p)
    if not _is_abs(p):
        base = _slash(base) if base else _slash(os.getcwd())
        if not _is_abs(base):
            base = _slash(os.path.abspath(base))
        p = base.rstrip("/") + "/" + p
    return _norm(p)


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def _rel(path: str, root: str) -> str:
    if path == root:
        return ""
    return path[len(root.rstrip("/")) + 1:]


# ---------------------------------------------------------------------------
# 対象の表記1つの扱い
# ---------------------------------------------------------------------------


def _strip_target(raw: str) -> str:
    s = raw.strip().strip("`").strip()
    s = _slash(s)
    last = s.rfind("/")
    head, tail = s[:last + 1], s[last + 1:]
    cut = [i for i in (tail.find(":"), tail.find("#")) if i >= 0]
    if cut:
        tail = tail[:min(cut)]
    return head + tail


def place_target(raw: str, repo_root: str, workspace_root: str,
                 isdir=os.path.isdir, exists=os.path.exists) -> dict:
    """対象の表記1つの置き場所を決める。repo_root・workspace_root は正規化済みの絶対パス。"""
    out = {"raw": raw}
    s0 = _slash(str(raw).strip().strip("`").strip())
    if URL_RE.match(s0):
        out["status"] = "url"
        return out
    s = _strip_target(raw)
    if "/" not in s:
        out["status"] = "no-path"
        return out
    dir_hint = s.endswith("/")
    dot_slash = s.startswith("./")

    candidates = []
    if _is_abs(s):
        first = _norm(s)
        candidates.append(first)
        # リポジトリのルートからのパスの意味で `/` を付けた表記（ワークスペースの下の実在の
        # 絶対パスでない場合だけ）
        if s.startswith("/") and not _under(first, workspace_root) and not _under(first, repo_root):
            candidates.append(_norm(repo_root + "/" + s.lstrip("/")))
    else:
        candidates.append(_norm(repo_root + "/" + s))
        candidates.append(_norm(workspace_root + "/" + s))

    any_under = False
    for cand in candidates:
        if not _under(cand, repo_root):
            continue
        any_under = True
        rel = _rel(cand, repo_root)
        if exists(cand):
            is_dir = isdir(cand)
        else:
            is_dir = dir_hint
        if is_dir:
            if rel == "":
                place_dir = ""
            elif isdir(cand):
                place_dir = rel
            else:
                continue
        else:
            parent = posixpath.dirname(rel)
            if parent == "":
                if not (exists(cand) or dot_slash):
                    continue
                place_dir = ""
            elif isdir(repo_root + "/" + parent):
                place_dir = parent
            else:
                continue
        out["status"] = "placed"
        out["rel"] = rel if rel else "."
        out["place"] = place_dir if place_dir else ROOT_PLACE
        out["_dir"] = place_dir
        return out
    out["status"] = "not-found" if any_under else "outside-repo"
    return out


def _common_dir(dirs: list) -> str:
    parts = [d.split("/") for d in dirs]
    common = []
    for comps in zip(*parts):
        if all(c == comps[0] for c in comps):
            common.append(comps[0])
        else:
            break
    return "/".join(common)


def _module_of(placed_dirs: list, fallback: str):
    """(module, reserved_collision) を返す。placed_dirs はリポジトリ直下を "" で表す。"""
    if not placed_dirs:
        return fallback, False
    if all(d == "" for d in placed_dirs):
        return ROOT_PLACE, False
    if any(d == "" for d in placed_dirs):
        return GENERAL_PLACE, False
    common = _common_dir(placed_dirs)
    if not common:
        return GENERAL_PLACE, False
    return common, common.split("/")[0] in RESERVED


def place_entries(entries, repo_root: str, workspace_root: str,
                  isdir=os.path.isdir, exists=os.path.exists) -> list:
    """place サブコマンドの本体。entries は入力 JSON（検証済み）。"""
    ws = _abs_dir(workspace_root)
    root = _abs_dir(repo_root, ws)
    results = []
    for entry in entries:
        targets = [place_target(t, root, ws, isdir=isdir, exists=exists) for t in entry["targets"]]
        placed = [t["_dir"] for t in targets if t["status"] == "placed"]
        module, collision = _module_of(placed, entry.get("fallback") or GENERAL_PLACE)
        for t in targets:
            t.pop("_dir", None)
        results.append({"id": entry["id"], "module": module, "reserved_collision": collision,
                        "targets": targets})
    return results


def _validate(data) -> list:
    if not isinstance(data, list):
        raise InputError("入力 JSON はリストである必要があります")
    for i, e in enumerate(data):
        if not isinstance(e, dict):
            raise InputError(f"入力 JSON の要素 {i} がオブジェクトではありません")
        if not isinstance(e.get("id"), str):
            raise InputError(f"入力 JSON の要素 {i} の id が文字列ではありません")
        t = e.get("targets")
        if not isinstance(t, list) or not all(isinstance(x, str) for x in t):
            raise InputError(f"入力 JSON の要素 {i} の targets が文字列のリストではありません")
        fb = e.get("fallback")
        if fb is not None and (not isinstance(fb, str) or not fb):
            raise InputError(f"入力 JSON の要素 {i} の fallback が空でない文字列ではありません")
    return data


# ---------------------------------------------------------------------------
# 読む側（列挙・当てはまる置き場所）
# ---------------------------------------------------------------------------


def list_places(know_dir) -> list:
    """`{KNOW}` の下の constraints.md の置き場所（KNOW からの相対パス）を並べて返す。

    相対パスの第1要素が `_structures`・`_constants`・`_flows`・`_cochange` のものは除く。
    """
    know = Path(know_dir)
    if not know.is_dir():
        return []
    places = set()
    for p in know.rglob("constraints.md"):
        if not p.is_file():
            continue
        rel = p.parent.relative_to(know).as_posix()
        if rel in ("", "."):
            continue
        if rel.split("/")[0] in NON_CONSTRAINT_DIRS:
            continue
        places.add(rel)
    return sorted(places)


def applicable_places(rel_file: str) -> list:
    """リポジトリのルートからの相対パスのファイルに当てはまる置き場所（深い順・_general を先頭）。"""
    rel = posixpath.normpath(_slash(rel_file).lstrip("/"))
    while rel.startswith("./"):
        rel = rel[2:]
    result = [GENERAL_PLACE]
    parent = posixpath.dirname(rel)
    if parent in ("", "."):
        result.append(ROOT_PLACE)
        return result
    parts = parent.split("/")
    for i in range(len(parts), 0, -1):
        result.append("/".join(parts[:i]))
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_place(args) -> int:
    try:
        raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
        data = _validate(json.loads(raw))
    except (OSError, json.JSONDecodeError, InputError) as e:
        print(f"入力 JSON の誤り: {e}", file=sys.stderr)
        return 2
    ws = _abs_dir(args.workspace_root)
    root = _abs_dir(args.repo_root, ws)
    if not os.path.isdir(root):
        print(f"--repo-root のディレクトリがありません: {root}", file=sys.stderr)
        return 1
    print(json.dumps(place_entries(data, args.repo_root, args.workspace_root), ensure_ascii=False))
    return 0


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        sys.exit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("place", help="知見の対象の表記から置き場所を決める")
    p.add_argument("--repo-root", required=True)
    p.add_argument("--workspace-root", required=True)
    p.add_argument("--input")
    p.set_defaults(func=cmd_place)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
