#!/usr/bin/env python3
"""一緒に直す候補（工程6 Step A2.5）。

CHD §4 で型のフィールドを追加・変更・削除する行（起点の要素）から、同じ型とその写し先の型のフィールドを並べて扱う関数・
写し先の型・形の一致が前提の丸ごとの写しを、決定的に列挙する。足す必要があるかの判断は LLM（designer）が行う。

  python3 specout_fieldtrace.py candidates --elements-file ELEMENTS_JSON --repo REPO --repo-path PATH \\
      --design-dir DESIGN_DIR --cr CR --engine slice|rule [--slice-h-as auto|c|cpp] [--exclude PATTERNS] \\
      [--include-ext EXTS] [--min-fields N] [--max-depth N] [--after-coding] --out-dir OUT_DIR --human-out HUMAN_MD

出力: {OUT_DIR}/cochange-candidates.json（全候補）・{OUT_DIR}/cochange-digest-{バッチファイル名}（確認対象のあるバッチだけ）・
HUMAN_MD（全量。LLM には渡さない）。stdout は JSON。
終了コード: 0＝成功（候補0件を含む）／1＝入力の誤り／2＝使い方の誤り／5＝--engine slice なのに tree-sitter を import できない。

本体は言語に依存しない。言語ごとの事実（型の定義・フィールドの参照・写し・丸ごとの写し・書き出し）はアダプタ
（specout_fieldtrace_c.py・specout_fieldtrace_cpp.py・specout_fieldtrace_python.py・specout_fieldtrace_rule.py）が返す。
言語を足すときは、アダプタを作って ADAPTERS に1行足し、tests/fixtures/fieldtrace/{言語}/ に標準の題材を置く。
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from specout_bfs import _split_csv, list_repo_files, resolve_h_as  # noqa: E402
import specout_macros as MAC  # noqa: E402

DIGEST_MAX_ROWS = 30   # 要約の表ごとの上限（回帰の要約と同じ値）
HEAD_MAX = 10          # 報告に並べる上限超過の先頭の件数
BYTES = "\x00bytes"    # 丸ごとの写しの写し先がバイト列・型の決まらないバッファ

TARGET_KINDS = ("データ構造", "変数")
TARGET_CHANGES = ("追加", "シグネチャ", "削除")

TAG_ENUM = "並べて扱う"
TAG_COPY = "写し"
TAG_SINK = "書き出し"
TAG_WHOLE = "丸ごとの写し"
TAG_ORIGIN_REF = "起点のフィールドを参照"
TAG_ORIGIN_SEEN = "起点のフィールドを参照済み"
TAG_TYPE = "写し先の型"

KIND_FUNC = "関数"
KIND_TYPE = "型"
KIND_FILE = "ファイル"

REQUIRED = "required"
OVER_LIMIT = "over-limit"
NAME_ONLY_FAR = "name-only-far"
TREATMENT_LABEL = {REQUIRED: "確認対象", OVER_LIMIT: "上限超過", NAME_ONLY_FAR: "遠い名前の一致のみ"}

# 言語 → (モジュール, クラス)。--engine rule のときは RULE_ADAPTER がすべての言語を扱う。
ADAPTERS = {
    "c": ("specout_fieldtrace_c", "CAdapter"),
    "cpp": ("specout_fieldtrace_cpp", "CppAdapter"),
    "python": ("specout_fieldtrace_python", "PythonAdapter"),
}
RULE_ADAPTER = ("specout_fieldtrace_rule", "RuleAdapter")
EXT_LANG = dict(MAC.C_CXX_EXT_LANG, **{".py": "python"})


# ---------------------------------------------------------------------------
# アダプタが返す事実
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FunctionKey:
    file: str      # リポジトリのルートからの相対パス（/ 区切り）
    qname: str     # クラスの修飾だけを付けた名前（メソッドは {クラス}::{名前}。名前空間・<…>・(…) は付けない）
    line: int

    def key(self) -> str:
        return f"{self.file}::{self.qname}"


@dataclass
class TypeDef:
    name: str                                    # 素の名前（名前空間・テンプレート引数を除く）
    file: str
    line: int
    fields: dict = field(default_factory=dict)   # {フィールド名: 型の素の名前 or None}（宣言順）
    bases: list = field(default_factory=list)    # 基底の型の素の名前
    methods: set = field(default_factory=set)


@dataclass
class MemberRef:
    func: FunctionKey
    recv: str | None     # 受け手の型（決められなければ None）
    field: str
    write: bool
    line: int
    implicit: bool = False


@dataclass
class FieldCopy:
    func: FunctionKey
    src: str | None
    src_field: str
    dst: str | None
    dst_field: str | None   # None＝写し先のフィールドとの対応が決まらない（コンストラクタの引数等）
    form: str
    line: int


@dataclass
class WholeCopy:
    func: FunctionKey | None
    file: str
    src: str | None
    dst: str | None         # BYTES＝バイト列・型の決まらないバッファ
    method: str
    line: int


@dataclass
class SinkCall:
    func: FunctionKey
    name: str
    line: int


@dataclass
class Facts:
    types: dict = field(default_factory=dict)        # {素の名前: TypeDef}
    aliases: dict = field(default_factory=dict)      # {別名: 素の名前}
    global_vars: dict = field(default_factory=dict)  # {変数名: 型の素の名前}
    refs: list = field(default_factory=list)
    copies: list = field(default_factory=list)
    wholes: list = field(default_factory=list)
    sinks: list = field(default_factory=list)
    functions: set = field(default_factory=set)

    def merge(self, o: "Facts") -> None:
        for k, t in o.types.items():
            cur = self.types.get(k)
            if cur is None:
                self.types[k] = t
            else:   # 同じ素の名前の定義（条件コンパイル等）はフィールドをまとめる
                for fn, ft in t.fields.items():
                    cur.fields.setdefault(fn, ft)
                cur.bases += [b for b in t.bases if b not in cur.bases]
                cur.methods |= t.methods
        for k, v in o.aliases.items():
            self.aliases.setdefault(k, v)
        for k, v in o.global_vars.items():
            self.global_vars.setdefault(k, v)
        self.refs += o.refs
        self.copies += o.copies
        self.wholes += o.wholes
        self.sinks += o.sinks
        self.functions |= o.functions

    def canon(self, name):
        """型の名前を、別名をたどって型の表の名前にする（表に無ければ None）。"""
        for _ in range(8):
            if not name:
                return None
            if name in self.types:
                return name
            nxt = self.aliases.get(name)
            if nxt is None or nxt == name:
                return None
            name = nxt
        return None


class AdapterContext:
    """アダプタに渡す共通の情報。"""

    def __init__(self, repo_path: str, files: list, h_as: str, excludes: list, engine: str):
        self.repo_path = repo_path
        self.files = files          # このアダプタが扱うファイル（リポジトリ相対）
        self.h_as = h_as
        self.excludes = excludes
        self.engine = engine


def _load_adapter(spec):
    mod, cls = spec
    return getattr(importlib.import_module(mod), cls)


def lang_of(rel: str, h_as: str):
    lang = MAC.c_cxx_lang(rel, h_as)
    if lang is not None:
        return lang
    return EXT_LANG.get(os.path.splitext(rel)[1])


def collect_facts(repo_path: str, files: list, h_as: str, excludes: list, engine: str) -> Facts:
    by_lang = {}
    for rel in files:
        lang = lang_of(rel, h_as)
        if lang in ADAPTERS:
            by_lang.setdefault(lang, []).append(rel)
    facts = Facts()
    if engine == "rule":
        all_files = [f for fs in by_lang.values() for f in fs]
        ad = _load_adapter(RULE_ADAPTER)(AdapterContext(repo_path, all_files, h_as, excludes, engine))
        facts.merge(ad.collect())
        return facts
    for lang in ("c", "cpp", "python"):
        if lang not in by_lang:
            continue
        ad = _load_adapter(ADAPTERS[lang])(AdapterContext(repo_path, by_lang[lang], h_as, excludes, engine))
        facts.merge(ad.collect())
    return facts


# ---------------------------------------------------------------------------
# 起点の要素
# ---------------------------------------------------------------------------

def strip_templates(s: str) -> str:
    out, depth = [], 0
    for ch in s:
        if ch == "<":
            depth += 1
        elif ch == ">" and depth:
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def strip_params(s: str) -> str:
    s = s.strip()
    if s.endswith("operator()"):
        return s
    m = re.search(r"\([^()]*\)\s*(?:const)?\s*$", s)
    return s[:m.start()].rstrip() if m else s


def split_qual(s: str) -> list:
    return [p for p in strip_templates(strip_params(s)).split("::") if p]


@dataclass
class Origin:
    element: dict
    type: str | None          # 起点の型（型の表の名前）。決まらなければ None（名前だけで探す）
    field: str | None
    change: str
    order: int


def origins_from_elements(elements: list, repo: str, facts: Facts):
    """(起点の一覧, 起点にしなかった行, 定義が見つからない起点の型)。"""
    origins, skipped, unresolved = [], [], []
    for i, el in enumerate(elements):
        if el.get("repo") != repo or el.get("kind") not in TARGET_KINDS:
            continue
        change = el.get("change")
        sym = el.get("symbol", "")
        parts = split_qual(sym)
        if not parts:
            continue
        if el["kind"] == "変数" and len(parts) == 1 and "." in parts[0]:
            if change not in TARGET_CHANGES:
                continue
            var, fld = parts[0].split(".", 1)
            fld = fld.split(".")[0].split("->")[0]
            t = facts.canon(facts.global_vars.get(var))
            origins.append(Origin(el, t, fld, change, i))
            if t is None:
                unresolved.append(f"{sym}（変数 {var} の型を決められない。フィールドの名前だけで探す）")
            continue
        if len(parts) == 1:
            if el["kind"] == "データ構造" and change == "シグネチャ":
                t = facts.canon(parts[0])
                if t is None:
                    unresolved.append(parts[0])
                    continue
                origins.append(Origin(el, t, None, change, i))
            continue
        if change not in TARGET_CHANGES:
            continue
        last, prev = parts[-1], parts[-2]
        t_last = facts.canon(last)
        if el["kind"] == "データ構造" and change == "シグネチャ" and t_last is not None:
            origins.append(Origin(el, t_last, None, change, i))
            continue
        t = facts.canon(prev)
        if t is None:
            unresolved.append(prev)
            continue
        td = facts.types[t]
        if last in td.methods and last not in all_fields(facts, t):
            skipped.append({"symbol": sym, "reason": f"{prev} のメソッド（フィールドでない）"})
            continue
        origins.append(Origin(el, t, last, change, i))
    return origins, skipped, sorted(set(unresolved))


# ---------------------------------------------------------------------------
# 関係する型・候補
# ---------------------------------------------------------------------------

def all_fields(facts: Facts, t: str, _seen=None) -> dict:
    """型のフィールドの集合（基底の型のフィールドを含む）。{名前: 型}。"""
    _seen = _seen or set()
    if t in _seen or t not in facts.types:
        return {}
    _seen.add(t)
    out = {}
    for b in facts.types[t].bases:
        bt = facts.canon(b)
        if bt:
            for k, v in all_fields(facts, bt, _seen).items():
                out.setdefault(k, v)
    for k, v in facts.types[t].fields.items():
        out[k] = v
    return out


def threshold(min_fields: int, n: int) -> int:
    return max(1, min(min_fields, n))


class Tracer:
    def __init__(self, facts: Facts, min_fields: int, max_depth: int, name_only_mode: bool):
        self.f = facts
        self.min_fields = min_fields
        self.max_depth = max_depth
        self.name_only_mode = name_only_mode   # 規則判定: 受け手の型を決めず、フィールドの名前で数える
        self._fields = {t: all_fields(facts, t) for t in facts.types}
        self.children, self.containers = {}, {}
        for t, td in facts.types.items():
            for b in td.bases:
                bt = facts.canon(b)
                if bt and bt != t:
                    self.children.setdefault(bt, set()).add(t)
            for ft in td.fields.values():
                ct = facts.canon(ft)
                if ct and ct != t:
                    self.containers.setdefault(ct, set()).add(t)
        self.copies_by_func = {}
        for c in facts.copies:
            self.copies_by_func.setdefault(c.func, []).append(c)
        self.refs_by_func = {}
        for r in facts.refs:
            self.refs_by_func.setdefault(r.func, []).append(r)
        self.sink_funcs = {s.func for s in facts.sinks}
        self.wholes = facts.wholes

    def fields(self, t) -> dict:
        return self._fields.get(t, {})

    def thr(self, t) -> int:
        return threshold(self.min_fields, len(self.fields(t)))

    def _copy_edges(self, r):
        """関数ごとの写しの辺 r→T: [(関数, T, 写したフィールドの数, resolved, 対応未確定あり)]。"""
        out = []
        fr = self.fields(r)
        for func, cs in self.copies_by_func.items():
            groups = {}
            for c in cs:
                if c.src == r and c.dst and c.dst != r:
                    if c.src_field in fr:
                        groups.setdefault((self.f.canon(c.dst) or c.dst, True), []).append(c)
                elif self.name_only_mode and c.src is None and c.src_field in fr and c.dst_field:
                    for t in self.f.types:
                        if t != r and c.dst_field in self.fields(t):
                            groups.setdefault((t, False), []).append(c)
            for (t, resolved), lst in groups.items():
                if t not in self.f.types:
                    continue
                n_src = len({c.src_field for c in lst})
                thr = threshold(self.min_fields, min(len(fr), len(self.fields(t))))
                if n_src >= thr:
                    out.append((func, t, n_src, resolved, any(c.dst_field is None for c in lst)))
        return out

    def relevant(self, origin_type: str):
        """{型: (距離, 経路, resolved, 写しで届いたか)} と、写し・丸ごとの写しの関数の理由。"""
        rel = {origin_type: (0, [origin_type], True, False)}
        func_reasons = []
        queue = [origin_type]
        while queue:
            r = queue.pop(0)
            d, path, res, _ = rel[r]
            if d >= self.max_depth:
                continue

            def add(t, how_copy, resolved):
                if t not in rel or rel[t][0] > d + 1:
                    rel[t] = (d + 1, path + [t], res and resolved, how_copy)
                    queue.append(t)

            for func, t, n_src, resolved, unresolved_map in self._copy_edges(r):
                func_reasons.append((func, TAG_COPY, d, r, res and resolved, n_src, unresolved_map))
                add(t, True, resolved)
            for t in sorted(self.containers.get(r, ())):
                add(t, False, True)
            for t in sorted(self.children.get(r, ())):
                add(t, False, True)
            for w in self.wholes:
                src = self.f.canon(w.src) if w.src else None
                if src != r:
                    continue
                dst = self.f.canon(w.dst) if (w.dst and w.dst != BYTES) else None
                if dst == r:
                    continue
                if w.func is not None:
                    func_reasons.append((w.func, TAG_WHOLE, d, r, res and not self.name_only_mode, 0, False))
                else:
                    func_reasons.append((FunctionKey(w.file, "", w.line), TAG_WHOLE, d, r,
                                         res and not self.name_only_mode, 0, False))
                if dst:
                    add(dst, False, not self.name_only_mode)
        return rel, func_reasons

    def enum_reasons(self, rel: dict):
        """並べて扱う関数: [(関数, 距離, 型, resolved, 参照したフィールド, N)]。"""
        out = []
        for func, refs in self.refs_by_func.items():
            for t, (d, _p, tres, _c) in rel.items():
                ft = self.fields(t)
                if not ft:
                    continue
                resolved = {r.field for r in refs if r.recv is not None and self.f.canon(r.recv) == t and r.field in ft}
                thr = self.thr(t)
                if len(resolved) >= thr:
                    out.append((func, d, t, tres and not self.name_only_mode, sorted(resolved), len(ft)))
                    continue
                if self.name_only_mode or resolved:
                    named = resolved | {r.field for r in refs if r.recv is None and r.field in ft}
                    if len(named) >= thr:
                        out.append((func, d, t, False, sorted(named), len(ft)))
        return out

    def origin_refs(self, origin: Origin, rel: dict):
        """起点のフィールドを参照する関数: {関数: (参照の数, resolved)}。"""
        out = {}
        if origin.field is None:
            return out
        types = {t for t, v in rel.items() if not v[3]} if origin.type else set()   # 写しで届いた型は除く
        for func, refs in self.refs_by_func.items():
            n, res = 0, False
            for r in refs:
                if r.field != origin.field:
                    continue
                rt = self.f.canon(r.recv) if r.recv else None
                if rt is not None and rt in types:
                    n, res = n + 1, True
                elif rt is None and (self.name_only_mode or origin.type is None):
                    n += 1
            if n:
                out[func] = (n, res and not self.name_only_mode)
        return out


@dataclass
class Candidate:
    key: str
    kind: str
    file: str
    symbol: str
    defs: list = field(default_factory=list)
    tags: set = field(default_factory=set)
    distance: int = 99
    path: list = field(default_factory=list)
    resolved: bool = False
    fields_ref: list = field(default_factory=list)
    n_fields: int = 0
    ratio: float = 0.0
    ref_count: int = 0
    origins: list = field(default_factory=list)     # [(元素の順番, 起点の変更シンボル, 距離)]
    unresolved_copy: bool = False
    only_origin_ref: bool = True

    def note_origin(self, origin: Origin, d: int):
        self.origins.append((origin.order, origin.element.get("symbol", ""), d))


def build_candidates(facts: Facts, origins: list, min_fields: int, max_depth: int, name_only_mode: bool):
    tr = Tracer(facts, min_fields, max_depth, name_only_mode)
    cands = {}

    def get(key, kind, file, symbol):
        c = cands.get(key)
        if c is None:
            c = cands[key] = Candidate(key, kind, file, symbol)
        return c

    def func_cand(func: FunctionKey):
        if not func.qname:
            c = get(func.file, KIND_FILE, func.file, "")
        else:
            c = get(func.key(), KIND_FUNC, func.file, func.qname)
        if func.line not in c.defs:
            c.defs.append(func.line)
        return c

    for origin in origins:
        if origin.type is None:
            rel = {t: (0, [t], False, False) for t in facts.types if origin.field in tr.fields(t)}
            freasons = []
        else:
            rel, freasons = tr.relevant(origin.type)
        # 写し先の型
        for t, (d, path, res, by_copy) in rel.items():
            if not by_copy:
                continue
            td = facts.types[t]
            c = get(f"{td.file}::{t}", KIND_TYPE, td.file, t)
            c.tags.add(TAG_TYPE)
            c.only_origin_ref = False
            _better(c, d, path, res)
            c.n_fields = len(tr.fields(t))
            c.note_origin(origin, d)
        # 写し・丸ごとの写しを含む関数
        for func, tag, d, r, res, n_src, unresolved_map in freasons:
            c = func_cand(func)
            c.tags.add(tag)
            c.only_origin_ref = False
            c.unresolved_copy |= unresolved_map
            _better(c, d, rel[r][1], res)
            c.note_origin(origin, d)
        # 並べて扱う関数
        for func, d, t, res, flds, n in tr.enum_reasons(rel):
            c = func_cand(func)
            c.tags.add(TAG_ENUM)
            c.only_origin_ref = False
            if _better(c, d, rel[t][1], res) or not c.fields_ref:
                c.fields_ref, c.n_fields = flds, n
                c.ratio = len(flds) / n if n else 0.0
            c.note_origin(origin, d)
        # 起点のフィールドを参照する関数（削除・シグネチャ）／参照済みの印（追加）
        for func, (cnt, res) in tr.origin_refs(origin, rel).items():
            if origin.change in ("削除", "シグネチャ"):
                c = func_cand(func)
                c.tags.add(TAG_ORIGIN_REF)
                c.ref_count = max(c.ref_count, cnt)
                _better(c, 0, [origin.type or origin.field], res)
                c.note_origin(origin, 0)
            else:
                key = func.key() if func.qname else func.file
                if key in cands:
                    cands[key].tags.add(TAG_ORIGIN_SEEN)
    for c in cands.values():
        if c.kind != KIND_TYPE:
            fk = [k for k in tr.sink_funcs if k.key() == c.key]
            if fk:
                c.tags.add(TAG_SINK)
    return cands


def _better(c: Candidate, d: int, path: list, resolved: bool) -> bool:
    """距離が近ければ（同じなら resolved を優先して）距離・経路・同一性を更新する。更新したら True。"""
    if d < c.distance:
        c.distance, c.path, c.resolved = d, list(path), resolved
        return True
    if d == c.distance and resolved and not c.resolved:
        c.path, c.resolved = list(path), True
        return True
    return False


# ---------------------------------------------------------------------------
# 確認対象・要約・全量
# ---------------------------------------------------------------------------

def _sort_key_table2(c: Candidate):
    return (c.distance, TAG_SINK not in c.tags, TAG_COPY not in c.tags, c.kind != KIND_TYPE,
            TAG_WHOLE not in c.tags, -c.ratio, c.key)


def _sort_key_table1(c: Candidate):
    return (-c.ref_count, c.key)


def assign(cands: dict, origins: list, elements: list, design_dir: Path, repo: str):
    """確認の条件・表・書き先のバッチ・要約での扱い・順位を決める。戻り値は書き出し用の dict の一覧。"""
    batch_order = []
    for el in elements:
        b = el.get("batch_name")
        if el.get("repo") == repo and b and b not in batch_order:
            batch_order.append(b)
    rows = []
    for c in cands.values():
        nearest = sorted(c.origins, key=lambda o: (o[2], o[0]))[0]
        el = elements[nearest[0]]
        batch = el.get("batch_name")
        meets = c.distance <= 1 or c.resolved
        table = 1 if c.only_origin_ref else 2
        rows.append({"c": c, "batch_name": batch, "batch_file": str(design_dir / repo / batch),
                     "meets": meets, "table": table, "origin_symbols": sorted({o[1] for o in c.origins})})
    for batch in batch_order + sorted({r["batch_name"] for r in rows} - set(batch_order)):
        for table, keyf in ((1, _sort_key_table1), (2, _sort_key_table2)):
            group = sorted([r for r in rows if r["batch_name"] == batch and r["table"] == table and r["meets"]],
                           key=lambda r: keyf(r["c"]))
            for i, r in enumerate(group):
                r["rank"] = i + 1
                r["treatment"] = REQUIRED if i < DIGEST_MAX_ROWS else OVER_LIMIT
    for r in rows:
        if not r["meets"]:
            r["treatment"], r["rank"] = NAME_ONLY_FAR, None
    order = {b: i for i, b in enumerate(batch_order)}
    rows.sort(key=lambda r: (order.get(r["batch_name"], 99), r["table"], r["rank"] if r["rank"] else 10**6, r["c"].key))
    return [_row_json(r) for r in rows]


def _row_json(r) -> dict:
    c = r["c"]
    return {"key": c.key, "kind": c.kind, "file": c.file, "symbol": c.symbol, "lines": sorted(c.defs),
            "overloads": len(c.defs), "tags": sorted(c.tags), "distance": c.distance, "path": "→".join(c.path),
            "identity": "resolved" if c.resolved else "name-only", "fields_ref": c.fields_ref, "n_fields": c.n_fields,
            "ratio": round(c.ratio, 3), "ref_count": c.ref_count, "table": r["table"], "treatment": r["treatment"],
            "rank": r["rank"], "batch_name": r["batch_name"], "batch_file": r["batch_file"],
            "origins": r["origin_symbols"], "unresolved_copy": c.unresolved_copy}


def _cell(s) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def _tags_text(row) -> str:
    return "・".join(t for t in row.get("tags", [])) or "—"


def _fields_text(row) -> str:
    if row.get("kind") == KIND_TYPE:
        return f"—／{row.get('n_fields', 0)}"
    if row.get("fields_ref"):
        return f"{', '.join(row['fields_ref'])}（{len(row['fields_ref'])}/{row.get('n_fields', 0)}）"
    if row.get("ref_count"):
        return f"起点のフィールド {row['ref_count']} 回"
    return "—"


def _note_text(row) -> str:
    notes = []
    if row.get("unresolved_copy"):
        notes.append("写し先のフィールドとの対応が未確定の写しを含む（コンストラクタの引数等。コードで確かめる）")
    if row.get("overloads", 1) > 1:
        notes.append(f"オーバーロード {row['overloads']}（行 {', '.join(map(str, row.get('lines', [])))}）")
    return "。".join(notes) or "—"


def render_digest(batch_name: str, rows: list, after_coding: bool, human_out: str) -> str:
    req = [r for r in rows if r["treatment"] == REQUIRED]
    over = [r for r in rows if r["treatment"] == OVER_LIMIT]
    far = [r for r in rows if r["treatment"] == NAME_ONLY_FAR]
    lines = [f"# 一緒に直す候補の要約（{batch_name}）", "",
             "> `specout_fieldtrace.py candidates` が書く（手で編集しない）。確認対象の候補ごとに、起点の変更に合わせて変える必要があるかを判断し、"
             "変えるなら §4 に足し、変えないなら §4.1 に理由を書く。キーは §4.1 の「候補」列にそのまま写す。"]
    if after_coding:
        lines.append("> 工程7 の後のコード（変更後）から求めた。")
    lines.append("")
    for table, title in ((1, "表1 起点のフィールドを参照するだけの関数"),
                         (2, "表2 並べて扱う関数・写しを含む関数・写し先の型・丸ごとの写しを含む関数")):
        t_req = [r for r in req if r["table"] == table]
        t_over = [r for r in over if r["table"] == table]
        if not t_req and not t_over:
            continue
        lines += [f"## {title}（確認対象 {len(t_req)} 件・上限超過 {len(t_over)} 件）", "",
                  "| 順位 | キー | 候補の種類 | 印 | 参照したフィールド／N | 距離 | 経路 | 同一性 | 起点 | 備考 |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for r in t_req:
            lines.append(f"| {r['rank']} | `{_cell(r['key'])}` | {r['kind']} | {_cell(_tags_text(r))} | {_cell(_fields_text(r))} | "
                         f"{r['distance']} | {_cell(r['path'])} | {r['identity']} | {_cell(', '.join(r['origins']))} | "
                         f"{_cell(_note_text(r))} |")
        lines.append("")
    lines.append(f"確認対象にしなかった候補: 上限超過 {len(over)} 件・遠い名前の一致のみ {len(far)} 件（全量: {human_out}）")
    lines.append("")
    return "\n".join(lines)


def render_human(data: dict, status: dict | None = None) -> str:
    """全量（人向け）。status は {キー: 処理}（chd_cochange.py check が渡す。無ければ全行 未処理）。"""
    status = status or {}
    rows = data["candidates"]

    def proc(r):
        return status.get(r["key"], "未処理")

    head = sorted([r for r in rows if r.get("treatment") == OVER_LIMIT and proc(r) == "未処理"],
                  key=lambda r: (r.get("batch_name") or "", r.get("table") or 0, r.get("rank") or 0))
    rest = [r for r in rows if r not in head]
    lines = [f"# 一緒に直す候補の全量（{data.get('cr', '')} / {data.get('repo', '')}）", "",
             "> `specout_fieldtrace.py candidates` が書き、`chd_cochange.py check --human-out` が「処理」列を書き換える（手で編集しない）。"
             "LLM には渡さない。未処理の上限超過（designer が確認しなかった候補）を先頭にまとめる。",
             f"> 判定エンジン: {data.get('engine')}。閾値: {data.get('params', {}).get('min_fields')}・深さ: "
             f"{data.get('params', {}).get('max_depth')}。" + ("工程7 の後のコードから求めた。" if data.get("after_coding") else ""),
             ""]
    if data.get("origins"):
        lines += ["## 起点の要素", "", "| 変更シンボル | 種別 | 変更の内容 | 起点の型 | 起点のフィールド | バッチ |", "|---|---|---|---|---|---|"]
        for o in data["origins"]:
            lines.append(f"| `{_cell(o['symbol'])}` | {o['kind']} | {o['change']} | {_cell(o['type'] or '（型未確認）')} | "
                         f"{_cell(o['field'] or '—')} | {_cell(o['batch_name'])} |")
        lines.append("")
    lines += [f"## 候補（{len(rows)} 件。未処理の上限超過 {len(head)} 件を先頭に置く）", "",
              "| 処理 | 要約での扱い | 表 | 書き先のバッチ | キー | 候補の種類 | 印 | 参照したフィールド／N | 距離 | 経路 | 同一性 | 起点 | 備考 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in head + rest:
        lines.append(f"| {proc(r)} | {TREATMENT_LABEL.get(r.get('treatment'), r.get('treatment'))} | 表{r.get('table')} | "
                     f"{_cell(r.get('batch_name', ''))} | `{_cell(r['key'])}` | "
                     f"{r.get('kind', '')} | {_cell(_tags_text(r))} | {_cell(_fields_text(r))} | {r.get('distance', '')} | "
                     f"{_cell(r.get('path', ''))} | {r.get('identity', '')} | {_cell(', '.join(r.get('origins', [])))} | "
                     f"{_cell(_note_text(r))} |")
    if not rows:
        lines.append("| — | — | — | — | なし | — | — | — | — | — | — | — | — |")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _err(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def cmd_candidates(args) -> None:
    try:
        el_data = json.loads(Path(args.elements_file).read_text(encoding="utf-8"))
        elements = el_data["elements"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        _err(f"--elements-file を読めません: {args.elements_file}（{e}）")
    if not Path(args.repo_path).is_dir():
        _err(f"--repo-path がありません: {args.repo_path}")
    if args.min_fields < 1 or args.max_depth < 0:
        _err("--min-fields は 1 以上、--max-depth は 0 以上の整数にしてください", 2)
    excludes = _split_csv(args.exclude)
    include_ext = _split_csv(args.include_ext)
    h_as = resolve_h_as(args.slice_h_as, args.repo_path, excludes)
    files = list_repo_files(args.repo_path, excludes, include_ext or None)
    engine = args.engine
    if engine == "slice":
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import specout_slice as SL
            SL._ts()
        except Exception as e:  # noqa: BLE001
            _err(f"tree-sitter を import できません（--engine slice）: {e}", 5)
    facts = collect_facts(args.repo_path, files, h_as, excludes, engine)
    origins, skipped, unresolved = origins_from_elements(elements, args.repo, facts)
    cands = build_candidates(facts, origins, args.min_fields, args.max_depth, engine == "rule")
    design_dir = Path(args.design_dir)
    rows = assign(cands, origins, elements, design_dir, args.repo)
    data = {"cr": args.cr, "repo": args.repo, "engine": engine, "after_coding": bool(args.after_coding),
            "params": {"min_fields": args.min_fields, "max_depth": args.max_depth},
            "origins": [{"symbol": o.element.get("symbol"), "kind": o.element.get("kind"), "change": o.change,
                         "type": o.type, "field": o.field, "batch_name": o.element.get("batch_name")} for o in origins],
            "type_names": sorted(set(facts.types) | set(facts.aliases)),
            "candidates": rows}
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("cochange-digest-*"):
        old.unlink()
    (out_dir / "cochange-candidates.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                                                     encoding="utf-8")
    batches = []
    for batch in dict.fromkeys(r["batch_name"] for r in rows):
        brows = [r for r in rows if r["batch_name"] == batch]
        req = [r for r in brows if r["treatment"] == REQUIRED]
        over = [r for r in brows if r["treatment"] == OVER_LIMIT]
        digest = None
        if req:
            digest = out_dir / f"cochange-digest-{batch}"
            digest.write_text(render_digest(batch, brows, bool(args.after_coding), args.human_out), encoding="utf-8")
        batches.append({"batch_file": brows[0]["batch_file"], "digest_file": str(digest) if digest else None,
                        "required_count": len(req), "over_limit_count": len(over),
                        "over_limit_by_table": {"1": sum(1 for r in over if r["table"] == 1),
                                                "2": sum(1 for r in over if r["table"] == 2)},
                        "name_only_far_count": sum(1 for r in brows if r["treatment"] == NAME_ONLY_FAR)})
    human = Path(args.human_out)
    human.parent.mkdir(parents=True, exist_ok=True)
    human.write_text(render_human(data), encoding="utf-8")
    warning = None
    if engine == "rule":
        warning = "規則判定（受け手の型を決めず、フィールドの名前で数える）で算出した。名前の一致だけの候補を含む"
    print(json.dumps({"ok": True, "engine": engine, "engine_warning": warning,
                      "target_elements": [o.element.get("symbol") for o in origins], "skipped_elements": skipped,
                      "unresolved_types": unresolved, "batches": batches}, ensure_ascii=False))


def build_parser():
    p = argparse.ArgumentParser(description="一緒に直す候補（工程6 Step A2.5）")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("--elements-file", required=True)
    c.add_argument("--repo", required=True)
    c.add_argument("--repo-path", required=True)
    c.add_argument("--design-dir", required=True)
    c.add_argument("--cr", required=True)
    c.add_argument("--engine", required=True, choices=["slice", "rule"])
    c.add_argument("--slice-h-as", default="auto")
    c.add_argument("--exclude", default="")
    c.add_argument("--include-ext", default="")
    c.add_argument("--min-fields", type=int, default=3)
    c.add_argument("--max-depth", type=int, default=4)
    c.add_argument("--after-coding", action="store_true")
    c.add_argument("--out-dir", required=True)
    c.add_argument("--human-out", required=True)
    c.set_defaults(func=cmd_candidates)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
