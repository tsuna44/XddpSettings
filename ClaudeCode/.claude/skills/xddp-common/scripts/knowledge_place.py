"""knowledge_place.py — code-knowledge の知見の置き場所（MODULE）を決め、制約のエントリを書く CLI・関数群

知見（制約・落とし穴等）の対象の表記（ファイルパス・ディレクトリ・識別子）から、
`{DOCS}/{repo}/knowledge/code-knowledge/{MODULE}/` の置き場所 `{MODULE}` を決定的に決める。
`upsert` は、決めた置き場所の `constraints.md` へ制約のエントリを書く（採番・鍵による照合・節と欄の書式）。
約束事は `xddp-rules/code-knowledge-boundary.md`「## 知見の置き場所（MODULE）」、
設計根拠は docs/adr/ADR-0033-constraints-module-key.md・ADR-0037-constraints-entry-keys.md を参照。

Usage:
  python3 knowledge_place.py place --repo-root REPO_ROOT --workspace-root WORKSPACE_ROOT [--input FILE]

  入力（--input のファイル、省略時は stdin）:
    [{"id": "...", "targets": ["src/db.go:45", "parse_header()"], "fallback": "_general"}, ...]
  stdout（JSON 1行）:
    [{"id": "...", "module": "src", "reserved_collision": false,
      "targets": [{"raw": "src/db.go:45", "status": "placed", "rel": "src/db.go", "place": "src"},
                  {"raw": "parse_header()", "status": "no-path"}]}, ...]
  status: placed / no-path / url / outside-repo / not-found

  python3 knowledge_place.py upsert --docs DOCS --repo REPO --repo-root REPO_ROOT --workspace-root WORKSPACE_ROOT
      [--input FILE] [--batch-cr CR_NUMBER | --batch-survey SURVEY_FILE] [--dry-run]

  入力（--input のファイル、省略時は stdin。空のリストでもよい）:
    [{"id": "...", "targets": [...], "subjects": [...], "fallback": "_general",
      "section": "constraint|assumption|performance", "title": "...",
      "fields": {"content": "...", "workaround": "..."}, "source": "...",
      "key": "...",            # --batch のときは必須、それ以外は指定できない
      "replace": "CK-NNN"}, ...]  # --batch でないときだけ。置き換える既存のエントリ
    fields のキー: constraint=content・workaround / assumption=premise・reason / performance=observation・implication
  鍵: --batch-cr は "cr:{CR_NUMBER}:{key}"、--batch-survey は "survey:{WORKSPACE_ROOT からの相対パス}:{key}"、
      --batch が無ければ "manual:{file}:CK-NNN"（スクリプトが付ける）
  stdout（JSON 1行）:
    {"entries": [{place の要素 + "file", "ck", "action": "added|replaced|moved", ["moved_from": {"file", "ck"}]}],
     "not_written": [{"file", "ck", "key", "title"}],   # --batch の接頭辞の鍵で、今回の入力に無いもの（消さない）
     "emptied": ["{file}"],                             # 移動でエントリが無くなった constraints.md（消さない）
     ["existing": {"{file}": [{"ck", "title", "key"}]}]}  # --dry-run のときだけ（何も書かない）

  終了コード（両サブコマンド）: 0＝成功、1＝--repo-root のディレクトリ・constraints テンプレートが無い、
  2＝引数・入力 JSON の誤り（upsert は、2 のときどのファイルも変えない）。

関数（他スクリプトが sys.path 経由で import する）:
  list_places(know_dir)     : {KNOW} の下の constraints.md の置き場所の一覧（予約名の下を除く）
  applicable_places(rel)    : リポジトリのルートからの相対パスのファイルに当てはまる置き場所
  place_entries(...)        : place サブコマンドの本体
  parse_constraints(text)   : constraints.md を節・エントリに切り出す

標準ライブラリのみ。
"""

import argparse
import json
import os
import posixpath
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docs_layout as layout  # noqa: E402

ROOT_PLACE = "_root"
GENERAL_PLACE = "_general"
# 列挙（list_places）で constraints.md の置き場所として扱わない第1要素
NON_CONSTRAINT_DIRS = layout.NON_CONSTRAINT_KNOWLEDGE_DIRS
# 置き場所の第1要素として予約された名前
RESERVED = (ROOT_PLACE, GENERAL_PLACE) + NON_CONSTRAINT_DIRS

URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
DRIVE_RE = re.compile(r"^([A-Za-z]):/")

# 制約のエントリの節（語彙 → 節の見出し・欄〔入力のキー, 欄名〕）。テンプレートと突き合わせるテストがある
SECTIONS = {
    "constraint": ("既知の制約・落とし穴", (("content", "内容"), ("workaround", "回避策"))),
    "assumption": ("仕様上の暗黙の前提", (("premise", "前提"), ("reason", "理由"))),
    "performance": ("パフォーマンス・非機能特性", (("observation", "観察"), ("implication", "示唆"))),
}
TARGET_LABEL = "対象"
SOURCE_LABEL = "出典"
EMPTY_VALUE = "—"
KEY_LINE_RE = re.compile(r"^<!-- key: (.*) -->\s*$")
ENTRY_HEADING_RE = re.compile(r"^### \[CK-(\d+)\]\s*(.*)$")
CK_RE = re.compile(r"^\[?CK-(\d+)\]?$")
SECTION_HEADING_RE = re.compile(r"^## ")
SUB_HEADING_RE = re.compile(r"^### ")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
BODY_FORBIDDEN_RE = re.compile(r"^(#{1,6} |<!-- key:)")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
BODY_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TEMPLATE = (Path(__file__).resolve().parents[2] / "xddp-close" / "templates"
            / "code-knowledge-constraints-template.md")
CONTROL_HINT = "JSON の `\\` は `\\\\` と書く（パスは `/` で区切ってよい）"


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

    # (候補の絶対パス, 見つからないとき not-found にするか)
    candidates = []
    if _is_abs(s):
        first = _norm(s)
        candidates.append((first, True))
        # リポジトリのルートからのパスの意味で `/` を付けた表記（ワークスペースの下の実在の
        # 絶対パスでない場合だけ）。見つからなければワークスペースの外の絶対パスとして outside-repo にする
        if s.startswith("/") and not _under(first, workspace_root) and not _under(first, repo_root):
            candidates.append((_norm(repo_root + "/" + s.lstrip("/")), False))
    else:
        candidates.append((_norm(repo_root + "/" + s), True))
        candidates.append((_norm(workspace_root + "/" + s), True))

    any_under = False
    for cand, counts in candidates:
        if not _under(cand, repo_root):
            continue
        any_under = any_under or counts
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


def _module_of(placed_dirs: list, fallback: str):
    """(module, reserved_collision) を返す。placed_dirs はリポジトリ直下を "" で表す。

    共通の先頭の第1要素が制約の置き場所にしない予約名なら、読まれる fallback に置く。
    """
    if not placed_dirs:
        return fallback, False
    if all(d == "" for d in placed_dirs):
        return ROOT_PLACE, False
    if any(d == "" for d in placed_dirs):
        return GENERAL_PLACE, False
    common = posixpath.commonpath(placed_dirs)
    if not common:
        return GENERAL_PLACE, False
    first = common.split("/")[0]
    if first in NON_CONSTRAINT_DIRS:
        return fallback, True
    return common, first in RESERVED


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


# ---------------------------------------------------------------------------
# 入力の検証
# ---------------------------------------------------------------------------


def _check_line(value: str, what: str) -> None:
    if CONTROL_RE.search(value):
        raise InputError(f"{what} に制御文字があります。{CONTROL_HINT}")


def _validate(data) -> list:
    if not isinstance(data, list):
        raise InputError("入力 JSON はリストである必要があります")
    for i, e in enumerate(data):
        if not isinstance(e, dict):
            raise InputError(f"入力 JSON の要素 {i} がオブジェクトではありません")
        if not isinstance(e.get("id"), str):
            raise InputError(f"入力 JSON の要素 {i} の id が文字列ではありません")
        _check_line(e["id"], f"入力 JSON の要素 {i} の id")
        t = e.get("targets")
        if not isinstance(t, list) or not all(isinstance(x, str) for x in t):
            raise InputError(f"入力 JSON の要素 {i} の targets が文字列のリストではありません")
        for x in t:
            _check_line(x, f"入力 JSON の要素 {i} の targets")
        fb = e.get("fallback")
        if fb is not None and (not isinstance(fb, str) or not fb):
            raise InputError(f"入力 JSON の要素 {i} の fallback が空でない文字列ではありません")
        if fb is not None:
            _check_line(fb, f"入力 JSON の要素 {i} の fallback")
    return data


def _valid_fallback(fb: str) -> bool:
    """upsert の fallback（書き先のディレクトリ）として受け付けるか。"""
    if fb in (GENERAL_PLACE, ROOT_PLACE):
        return True
    if "\\" in fb or fb.startswith("/") or re.match(r"^[A-Za-z]:", fb):
        return False
    parts = fb.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return False
    return parts[0] not in NON_CONSTRAINT_DIRS


def _normalize_body(value: str, what: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    if BODY_CONTROL_RE.search(value):
        raise InputError(f"{what} に改行・タブ以外の制御文字があります。{CONTROL_HINT}")
    in_fence = False
    for line in value.split("\n"):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence and BODY_FORBIDDEN_RE.match(line):
            raise InputError(f"{what} に見出し・鍵の行と同じ形の行があります（コード片はフェンスで囲む）: {line}")
    return value


def _validate_upsert(data, batch: bool) -> list:
    _validate(data)
    keys, replaces = set(), set()
    for i, e in enumerate(data):
        where = f"入力 JSON の要素 {i}"
        subjects = e.get("subjects", [])
        if not isinstance(subjects, list) or not all(isinstance(x, str) for x in subjects):
            raise InputError(f"{where} の subjects が文字列のリストではありません")
        for x in subjects:
            _check_line(x, f"{where} の subjects")
        e["subjects"] = subjects
        fb = e.get("fallback") or GENERAL_PLACE
        if not _valid_fallback(fb):
            raise InputError(f"{where} の fallback が置き場所として使えません（_general・_root か、"
                             f"リポジトリのルートからの相対パスで予約名で始まらないもの）: {fb}")
        section = e.get("section")
        if section not in SECTIONS:
            raise InputError(f"{where} の section が {', '.join(SECTIONS)} のどれでもありません")
        title = e.get("title")
        if not isinstance(title, str) or not title.strip():
            raise InputError(f"{where} の title が空でない文字列ではありません")
        _check_line(title, f"{where} の title")
        fields = e.get("fields")
        want = [k for k, _ in SECTIONS[section][1]]
        if not isinstance(fields, dict) or sorted(fields) != sorted(want):
            raise InputError(f"{where} の fields のキーは {', '.join(want)} である必要があります")
        for k in want:
            if not isinstance(fields[k], str):
                raise InputError(f"{where} の fields.{k} が文字列ではありません")
            fields[k] = _normalize_body(fields[k], f"{where} の fields.{k}")
        source = e.get("source")
        if not isinstance(source, str):
            raise InputError(f"{where} の source が文字列ではありません")
        e["source"] = _normalize_body(source, f"{where} の source")
        key = e.get("key")
        replace = e.get("replace")
        if batch:
            if not isinstance(key, str) or not key:
                raise InputError(f"{where} に key がありません（--batch-cr・--batch-survey のときは必須）")
            _check_line(key, f"{where} の key")
            if key in keys:
                raise InputError(f"入力の中で key が重なっています: {key}")
            keys.add(key)
            if replace is not None:
                raise InputError(f"{where}: replace は --batch-cr・--batch-survey と同時に使えません")
        else:
            if key is not None:
                raise InputError(f"{where}: key は --batch-cr・--batch-survey のときだけ指定できます")
            if replace is not None:
                if not isinstance(replace, str):
                    raise InputError(f"{where} の replace が文字列ではありません")
                _check_line(replace, f"{where} の replace")
                m = CK_RE.match(replace.strip())
                if not m:
                    raise InputError(f"{where} の replace が CK-NNN の形ではありません: {replace}")
                e["_replace_n"] = int(m.group(1))
    return data


# ---------------------------------------------------------------------------
# constraints.md の切り出しと組み立て
# ---------------------------------------------------------------------------


class _Block:
    """節の中のまとまり。kind は "entry"（`### [CK-NNN]`）か "raw"（それ以外の `### ` の見出しの範囲）。"""

    def __init__(self, kind, lines, n=None, title=None, key=None):
        self.kind, self.lines, self.n, self.title, self.key = kind, lines, n, title, key


class _Section:
    def __init__(self, heading, name):
        self.heading, self.name, self.head_lines, self.blocks = heading, name, [], []


class _Doc:
    def __init__(self):
        self.preamble, self.sections = [], []

    def entries(self):
        for sec in self.sections:
            for b in sec.blocks:
                if b.kind == "entry":
                    yield sec, b

    def max_n(self):
        return max((b.n for _, b in self.entries()), default=0)

    def text(self) -> str:
        out = list(self.preamble)
        for sec in self.sections:
            out.append(sec.heading)
            out.extend(sec.head_lines)
            for b in sec.blocks:
                out.extend(b.lines)
        while out and out[-1] == "":
            out.pop()
        return "\n".join(out) + "\n"


def parse_constraints(text: str) -> _Doc:
    """constraints.md を節・エントリに切り出す。フェンスのコードブロックの中は見出しとして扱わない。"""
    doc = _Doc()
    cur_lines = doc.preamble
    sec = None
    in_fence = False
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence and SECTION_HEADING_RE.match(line):
            sec = _Section(line, line[3:].strip())
            doc.sections.append(sec)
            cur_lines = sec.head_lines
            continue
        elif not in_fence and sec is not None and SUB_HEADING_RE.match(line):
            m = ENTRY_HEADING_RE.match(line)
            if m:
                key = None
                if i + 1 < len(lines):
                    km = KEY_LINE_RE.match(lines[i + 1])
                    key = km.group(1) if km else None
                block = _Block("entry", [line], int(m.group(1)), m.group(2).strip(), key)
            else:
                block = _Block("raw", [line])
            sec.blocks.append(block)
            cur_lines = block.lines
            continue
        cur_lines.append(line)
    return doc


def _template_skeleton(module: str) -> _Doc:
    """テンプレートから見本のエントリを除いた骨組み（見出しの置き場所を埋める）。"""
    doc = parse_constraints(TEMPLATE.read_text(encoding="utf-8").replace("{置き場所}", module))
    for sec in doc.sections:
        sec.blocks = [b for b in sec.blocks if b.kind != "entry"]
    return doc


def _join(values) -> str:
    return ", ".join(values) if values else EMPTY_VALUE


def _render(n: int, entry: dict, key: str) -> list:
    _, cols = SECTIONS[entry["section"]]
    lines = [f"### [CK-{n:03d}] {entry['title'].strip()}", f"<!-- key: {key} -->",
             f"**{TARGET_LABEL}:** {_join(entry['targets'] + entry['subjects'])}"]
    for k, label in cols:
        lines.append(f"**{label}:** {entry['fields'][k] or EMPTY_VALUE}")
    lines.append(f"**{SOURCE_LABEL}:** {entry['source'] or EMPTY_VALUE}")
    lines.append("")
    return lines


def _section_of(doc: _Doc, name: str) -> _Section:
    heading = SECTIONS[name][0]
    for sec in doc.sections:
        if sec.name == heading:
            return sec
    sec = _Section(f"## {heading}", heading)
    sec.head_lines = [""]
    if doc.sections:
        last = doc.sections[-1]
        tail = last.blocks[-1].lines if last.blocks else last.head_lines
        if not tail or tail[-1] != "":
            tail.append("")
    elif doc.preamble and doc.preamble[-1] != "":
        doc.preamble.append("")
    doc.sections.append(sec)
    return sec


def _append(sec: _Section, block: _Block) -> None:
    tail = sec.blocks[-1].lines if sec.blocks else sec.head_lines
    if tail and tail[-1] != "":
        tail.append("")
    sec.blocks.append(block)


def _remove(doc: _Doc, block: _Block) -> None:
    for sec in doc.sections:
        if block in sec.blocks:
            sec.blocks.remove(block)
            return


# ---------------------------------------------------------------------------
# upsert
# ---------------------------------------------------------------------------


def _batch_prefix(args, ws: str) -> str:
    if args.batch_cr is not None:
        cr = args.batch_cr.strip()
        if not cr:
            raise InputError("--batch-cr が空です")
        _check_line(cr, "--batch-cr")
        return f"cr:{cr}:"
    if args.batch_survey is not None:
        _check_line(args.batch_survey, "--batch-survey")
        path = _abs_dir(args.batch_survey.strip(), ws)
        if not _under(path, ws) or path == ws:
            raise InputError(f"--batch-survey のファイルがワークスペースの下にありません: {args.batch_survey}")
        return f"survey:{_rel(path, ws)}:"
    return ""


def upsert(data, docs, repo, repo_root, workspace_root, prefix="", dry_run=False) -> tuple:
    """(出力, 書くファイル {Path: 内容}) を返す。data は _validate_upsert 済み。何も書かない。"""
    know = layout.code_knowledge_dir(docs, repo)
    placed = place_entries(data, repo_root, workspace_root)
    docs_cache = {}

    def load(rel_file):
        if rel_file not in docs_cache:
            p = know / rel_file
            docs_cache[rel_file] = parse_constraints(p.read_text(encoding="utf-8")) if p.is_file() else None
        return docs_cache[rel_file]

    def file_of(module):
        return f"{module}/{layout.CONSTRAINTS_FILE}"

    existing_files = [file_of(pl) for pl in list_places(know)]
    original_existing = {}
    for result, entry in zip(placed, data):
        f = file_of(result["module"])
        if f not in original_existing:
            doc = load(f)
            original_existing[f] = [{"ck": f"CK-{b.n:03d}", "title": b.title, "key": b.key}
                                    for _, b in (doc.entries() if doc else [])]

    changed = set()
    removed_from = set()
    replaced = set()
    written_keys = set()
    out_entries = []
    for result, entry in zip(placed, data):
        f = file_of(result["module"])
        doc = load(f)
        if doc is None:
            doc = _template_skeleton(result["module"])
            docs_cache[f] = doc
        target_sec = _section_of(doc, entry["section"])
        row = dict(result, file=f)
        if prefix:
            key = prefix + entry["key"]
            written_keys.add(key)
            found = []
            for ef in dict.fromkeys(existing_files + [f]):
                d = load(ef)
                if d is None:
                    continue
                for sec, b in d.entries():
                    if b.key == key:
                        found.append((ef, d, sec, b))
            same = [x for x in found if x[0] == f]
            primary = (same or found or [None])[0]
            for ef, d, sec, b in found:
                if (ef, b) != (primary[0], primary[3]):
                    _remove(d, b)
                    changed.add(ef)
                    removed_from.add(ef)
            if primary is None:
                n = doc.max_n() + 1
                _append(target_sec, _Block("entry", _render(n, entry, key), n, entry["title"], key))
                row.update(ck=f"CK-{n:03d}", action="added")
            elif primary[0] == f:
                _, _, sec, b = primary
                new = _Block("entry", _render(b.n, entry, key), b.n, entry["title"], key)
                if sec is target_sec:
                    sec.blocks[sec.blocks.index(b)] = new
                    row.update(ck=f"CK-{b.n:03d}", action="replaced")
                else:
                    _remove(doc, b)
                    _append(target_sec, new)
                    row.update(ck=f"CK-{b.n:03d}", action="moved",
                               moved_from={"file": f, "ck": f"CK-{b.n:03d}"})
            else:
                ef, d, sec, b = primary
                _remove(d, b)
                changed.add(ef)
                removed_from.add(ef)
                n = doc.max_n() + 1
                _append(target_sec, _Block("entry", _render(n, entry, key), n, entry["title"], key))
                row.update(ck=f"CK-{n:03d}", action="moved", moved_from={"file": ef, "ck": f"CK-{b.n:03d}"})
        elif "_replace_n" in entry:
            hit = [(sec, b) for sec, b in doc.entries() if b.n == entry["_replace_n"]]
            if not hit:
                raise InputError(f"replace の CK-{entry['_replace_n']:03d} が {f} にありません")
            sec, b = hit[0]
            if (f, b.n) in replaced:
                raise InputError(f"入力の中で replace が重なっています: {f} CK-{b.n:03d}")
            replaced.add((f, b.n))
            key = f"manual:{f}:CK-{b.n:03d}"
            new = _Block("entry", _render(b.n, entry, key), b.n, entry["title"], key)
            if sec is target_sec:
                sec.blocks[sec.blocks.index(b)] = new
                row.update(ck=f"CK-{b.n:03d}", action="replaced")
            else:
                _remove(doc, b)
                _append(target_sec, new)
                row.update(ck=f"CK-{b.n:03d}", action="moved", moved_from={"file": f, "ck": f"CK-{b.n:03d}"})
        else:
            n = doc.max_n() + 1
            key = f"manual:{f}:CK-{n:03d}"
            _append(target_sec, _Block("entry", _render(n, entry, key), n, entry["title"], key))
            row.update(ck=f"CK-{n:03d}", action="added")
        changed.add(f)
        out_entries.append(row)

    not_written = []
    if prefix:
        for ef in sorted(set(existing_files) | changed):
            d = load(ef)
            if d is None:
                continue
            for _, b in d.entries():
                if b.key and b.key.startswith(prefix) and b.key not in written_keys:
                    not_written.append({"file": ef, "ck": f"CK-{b.n:03d}", "key": b.key, "title": b.title})
    emptied = sorted(ef for ef in removed_from if not any(True for _ in docs_cache[ef].entries()))
    output = {"entries": out_entries, "not_written": not_written, "emptied": emptied}
    if dry_run:
        output["existing"] = original_existing
        return output, {}
    return output, {know / ef: docs_cache[ef].text() for ef in sorted(changed)}


def _write_all(files: dict) -> None:
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".constraints-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise


# ---------------------------------------------------------------------------
# 読む側（列挙・当てはまる置き場所）
# ---------------------------------------------------------------------------


def list_places(know_dir) -> list:
    """`{KNOW}` の下の constraints.md の置き場所（KNOW からの相対パス）を並べて返す。

    相対パスの第1要素が制約の置き場所にしない予約名（docs_layout.NON_CONSTRAINT_KNOWLEDGE_DIRS）のものは除く。
    """
    know = Path(know_dir)
    if not know.is_dir():
        return []
    places = set()
    for p in know.rglob(layout.CONSTRAINTS_FILE):
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


def _read_input(args):
    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    return json.loads(raw)


def cmd_place(args) -> int:
    try:
        data = _validate(_read_input(args))
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


def cmd_upsert(args) -> int:
    if args.repo == layout.CROSS_AREA:
        print("--repo cross には制約を置きません（{XKNOW} に constraints.md を置かない）", file=sys.stderr)
        return 2
    ws = _abs_dir(args.workspace_root)
    root = _abs_dir(args.repo_root, ws)
    try:
        prefix = _batch_prefix(args, ws)
        data = _validate_upsert(_read_input(args), bool(prefix))
    except (OSError, json.JSONDecodeError, InputError) as e:
        print(f"入力の誤り: {e}", file=sys.stderr)
        return 2
    if not os.path.isdir(root):
        print(f"--repo-root のディレクトリがありません: {root}", file=sys.stderr)
        return 1
    if not TEMPLATE.is_file():
        print(f"constraints のテンプレートがありません: {TEMPLATE}（setup.sh を実行してください）", file=sys.stderr)
        return 1
    try:
        output, files = upsert(data, args.docs, args.repo, args.repo_root, args.workspace_root,
                               prefix=prefix, dry_run=args.dry_run)
    except InputError as e:
        print(f"入力の誤り: {e}", file=sys.stderr)
        return 2
    _write_all(files)
    print(json.dumps(output, ensure_ascii=False))
    return 0


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        sys.exit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    p = sub.add_parser("place", help="知見の対象の表記から置き場所を決める")
    p.add_argument("--repo-root", required=True)
    p.add_argument("--workspace-root", required=True)
    p.add_argument("--input")
    p.set_defaults(func=cmd_place)
    u = sub.add_parser("upsert", help="置き場所を決めて constraints.md に制約のエントリを書く")
    u.add_argument("--docs", required=True)
    u.add_argument("--repo", required=True)
    u.add_argument("--repo-root", required=True)
    u.add_argument("--workspace-root", required=True)
    u.add_argument("--input")
    g = u.add_mutually_exclusive_group()
    g.add_argument("--batch-cr", help="クローズの CR 番号（鍵の接頭辞 cr:{CR}:）")
    g.add_argument("--batch-survey", help="昇格する SURVEY ファイル（鍵の接頭辞 survey:{相対パス}:）")
    u.add_argument("--dry-run", action="store_true", help="何も書かず、書いたらどうなるかと既存のエントリを返す")
    u.set_defaults(func=cmd_upsert)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
