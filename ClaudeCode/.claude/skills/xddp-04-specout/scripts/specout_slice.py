"""
specout_slice.py — 波紋調査（Discovery BFS）のヒット判定エンジン

`specout_bfs.py search` が書いたスライス用チャンク（`wave-{N}-hits-chunk-S.json`）のヒットを、LLM を使わずに
決定的に判定する。判定エンジンは2つ。どちらで判定するかは `bfs-state.json` の `slice_engine`（`init` が保存）で決まる。

  slice  tree-sitter による関数内の静的スライス（完全スライス・computed）。影響が関数の外へ出る経路（出口）を
         求め、呼び出し元（含む関数）・グローバル変数の読み手（`root.field`）・関数の外の値（マクロ名・初期化した
         変数名・代入先の名前）を次の波のシンボルにする。呼び出し先はリポジトリ全体の定義索引から副作用の要約を
         求める（深さ3まで）。
  rule   標準ライブラリのみ。コメント・文字列の中のヒット・goto のラベル名・プロトタイプ宣言の引数名を偽陽性とし、
         それ以外はヒット行を含む関数を次の波のシンボルにする。関数の外・関数の宣言部のヒットは伝播させない。

出口の種類（slice）:
  return / exception        影響を受けた return・yield・throw・raise         → 呼び出し元へ伝播
  out                       ポインタ/参照引数・self/this 経由の書き込み       → 呼び出し元へ伝播
  heap / state / unknown    出所不明のポインタ経由・static ローカル・解析不能 → 呼び出し元へ伝播（保守的）
  closure                   Python の外側関数のローカルへの書き込み           → 呼び出し元へ伝播
  global                    グローバル変数への書き込み                         → その変数名（読み手を探す）

次の波のシンボル名は修飾を外した識別子（`ns::Class::method` → `method`、`f<T>` → `f`、コンストラクタはクラス名）。
ヘッダ以外のファイルの static・無名名前空間の関数と変数、そのファイルで定義したマクロ（ヘッダに同名のマクロが無いもの）は、
`name[FILE:path]`（そのファイルの中だけを検索する）として送る。
デストラクタ・演算子オーバーロードは呼び出し箇所に名前が現れないため伝播させず、grep 未対応パターンとして返す。
関数ポインタ経由の呼び出しも grep 未対応パターンとして返す。

Usage:
  python3 specout_slice.py probe [--out PROBE_JSON]
  python3 specout_slice.py seed-summary --path STATE_JSON [--symbols SYMS] --out SUMMARIES_JSON
  python3 specout_slice.py classify --path STATE_JSON --hits SLICE_CHUNK_JSON --out CLASS_JSON
  python3 specout_slice.py callslot-candidates --engine slice|rule --seed-candidates SEED_MD --repo-path REPO \
      [--exclude P] [--include-ext E] [--slice-h-as auto|c|cpp] [--max-per-field N] --cr CR --repo NAME \
      --list-out LIST_MD --json-out LIST_JSON
  python3 specout_slice.py callslot-choose --candidates-json LIST_JSON --choice none|recommended|selected \
      [--symbols 'X,Y'] --today DATE --out SEEDS_JSON
  python3 specout_slice.py callslot-choose --revalidate --candidates-json LIST_JSON [--no-start] --today DATE --out SEEDS_JSON
  python3 specout_slice.py callslot-choose --mark-started --out SEEDS_JSON

callslot-candidates は、候補表の採用したシードが関数ポインタの欄に登録されている（`x->f = シード`・`x.f = シード`・
`.f = シード`）とき、同じ欄に登録される別の関数（同じ呼び出し口の関数）と、そのうちシードと同じ関数・変数・定数を使う
もの（おすすめ）・呼び出し口（欄の関数を呼ぶ箇所）を求め、人向けの全量 LIST_MD と全件の LIST_JSON を書く。
照合の鍵は --engine slice で「型名＋フィールド名」、rule で「フィールド名」だけ。採用したシード・設定・母体のファイルの
指紋が前回と同じなら走査せず、前回の LIST_JSON から stdout を作る。候補表は書き換えない。
callslot-choose は人の選択（行わない・おすすめで行う・選んで行う）を検証して SEEDS_JSON に書く。

callslot-candidates・callslot-choose 以外が書き込むのは --out のファイルだけ（bfs-state.json と discovery-log.md は書かない）。
終了コード: 0 = 成功 / 1 = 実行時エラー / 2 = 使用法エラー（argparse 既定）/ 5 = 判定エンジンが使えない
（state の slice_engine が slice なのに tree-sitter を import できない。stderr に原因のモジュールを書く）。
tree-sitter は構文解析を行う関数の中で import する（--help・probe・rule は tree-sitter が無くても動く）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import zlib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from specout_bfs import SCOPE_CLASS, _entry_scope_kind, _parse_entry, list_repo_files, summary_key  # noqa: E402
import specout_log_values as LV  # noqa: E402
import specout_macros as MAC  # noqa: E402

EXIT_ENGINE_UNAVAILABLE = 5

# 言語表（拡張子 → 言語）。スライス判定・規則判定の対象拡張子であり、search の判定先の振り分けにも使う。
# C/C++ の部分は specout_macros.C_CXX_EXT_LANG。`.h` は state の slice_h_as（c / cpp）で決める。
EXT_LANG = dict(MAC.C_CXX_EXT_LANG, **{".py": "python"})
ENGINE_EXTS = sorted(EXT_LANG)

UP_KINDS = {"return", "exception", "out", "heap", "state", "unknown", "closure"}
HEADER_EXTS = (".h", ".hh", ".hpp", ".hxx")
# ファイルスコープの宣言を入れ子の中まで走査するときに入る節（関数の本体・クラスの本体には入らない）。
FILE_SCOPE_CONTAINERS = {"preproc_ifdef", "preproc_if", "preproc_else", "preproc_elif", "preproc_elifdef",
                         "linkage_specification", "declaration_list", "namespace_definition"}
# 同一性の印（classification エントリの identity）
IDENTITY_RESOLVED = "resolved"
IDENTITY_NAME_ONLY = "name-only"
IDENTITY_NONE = "—"
SEED_TYPES = {"identifier", "type_identifier", "field_identifier", "namespace_identifier"}

# 言語標準ライブラリの既知関数（ドメイン非依存）
PURE = {
    "c": {"strlen", "strcmp", "strncmp", "strcasecmp", "strncasecmp", "memcmp", "strchr", "strrchr",
          "strstr", "abs", "labs", "isdigit", "isalpha", "isspace", "isalnum", "isupper", "islower",
          "toupper", "tolower", "atoi", "atol", "strtol", "strtoul", "sizeof", "offsetof", "htons",
          "htonl", "ntohs", "ntohl", "assert"},
    "python": {"len", "isinstance", "issubclass", "str", "int", "float", "bool", "repr", "hash", "id",
               "type", "abs", "min", "max", "sum", "sorted", "reversed", "any", "all", "range",
               "enumerate", "zip", "map", "filter", "list", "dict", "set", "tuple", "frozenset",
               "round", "format", "ord", "chr", "hasattr", "getattr", "callable", "iter",
               "get", "keys", "values", "items", "startswith", "endswith", "strip", "lstrip",
               "rstrip", "split", "join", "lower", "upper", "replace", "find", "count", "index",
               "copy", "encode", "decode"},
}
PURE["cpp"] = PURE["c"] | {"size", "empty", "length", "begin", "end", "cbegin", "cend", "find",
                           "count", "at", "c_str", "data", "front", "back", "min", "max"}
# 引数（位置）または receiver を書き換える既知関数
WRITERS = {
    "c": {"memcpy": [0], "memmove": [0], "memset": [0], "strcpy": [0], "strncpy": [0],
          "strcat": [0], "strncat": [0], "sprintf": [0], "snprintf": [0], "strlcpy": [0],
          "strlcat": [0], "fgets": [0], "fread": [0]},
    "python": {m: ["recv"] for m in ("append", "extend", "insert", "pop", "remove", "clear",
                                     "update", "add", "discard", "setdefault", "sort", "reverse",
                                     "popitem")},
}
WRITERS["cpp"] = dict(WRITERS["c"], **{m: ["recv"] for m in (
    "push_back", "emplace_back", "insert", "erase", "clear", "push", "pop", "emplace", "resize",
    "assign", "swap", "reset")})


# ---------------------------------------------------------------------------
# tree-sitter（遅延 import）
# ---------------------------------------------------------------------------

class EngineUnavailable(Exception):
    """tree-sitter または文法パッケージを import できない。"""


_TS = None


def _ts() -> dict:
    """tree-sitter の Parser を言語ごとに作る（初回だけ import する）。失敗は EngineUnavailable。"""
    global _TS
    if _TS is not None:
        return _TS
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_c
        import tree_sitter_cpp
        import tree_sitter_python
        langs = {
            "c": Language(tree_sitter_c.language()),
            "cpp": Language(tree_sitter_cpp.language()),
            "python": Language(tree_sitter_python.language()),
        }
        _TS = {"parser": {k: Parser(v) for k, v in langs.items()}}
    except Exception as e:  # noqa: BLE001 — ImportError 以外（版の不整合等）も「使えない」として扱う
        raise EngineUnavailable(f"{type(e).__name__}: {e}") from e
    return _TS


def walk(n, stop=None):
    stack = [n]
    while stack:
        x = stack.pop()
        yield x
        if stop and x is not n and x.type in stop:
            continue
        stack.extend(reversed(x.children))


def txt(n):
    return n.text.decode("utf-8", "replace")


def lang_of(path, h_as="c"):
    lang = MAC.c_cxx_lang(path, h_as)
    if lang is not None:
        return lang
    return EXT_LANG.get(os.path.splitext(path)[1])


def is_header(path) -> bool:
    return os.path.splitext(path)[1] in HEADER_EXTS


def _storage(decl) -> set:
    return {txt(c) for c in decl.children if c.type == "storage_class_specifier"}


def _file_scope_nodes(root):
    """ファイルスコープの節を、#ifdef・extern "C"・名前空間の中まで入って返す。
    [(節, 無名名前空間の中か, extern "C" の中か)]。関数の本体・クラスの本体には入らない。"""
    out = []
    stack = [(c, False, False) for c in reversed(root.named_children)]
    while stack:
        n, anon, linkage = stack.pop()
        if n.type in FILE_SCOPE_CONTAINERS:
            a = anon or (n.type == "namespace_definition" and n.child_by_field_name("name") is None)
            lk = linkage or n.type == "linkage_specification"
            kids = [c for c in n.named_children if c.type not in ("comment", "preproc_arg")]
            stack.extend((c, a, lk) for c in reversed(kids))
            continue
        out.append((n, anon, linkage))
    return out


def _at_file_scope(node) -> bool:
    """node の親から translation_unit までが、ファイルスコープの入れ子（#ifdef・extern "C"・名前空間）だけか。"""
    p = node.parent
    while p is not None:
        if p.type == "translation_unit":
            return True
        if p.type not in FILE_SCOPE_CONTAINERS:
            return False
        p = p.parent
    return False


# ---------------------------------------------------------------------------
# ファイル・関数（slice）
# ---------------------------------------------------------------------------

@dataclass
class Param:
    name: str
    idx: int
    ptr: bool = False   # ポインタ・配列（C/C++）。Python は常に True（オブジェクト参照）
    ref: bool = False   # C++ 参照
    type: str | None = None   # C++: 宣言の素の型名（受け手のクラスを決めるため）
    qual: tuple = ()          # C++: 宣言の型の名前空間の修飾（_type_qual）
    elem: object = None       # C++: コンテナの要素の型（_elem_of_type）


@dataclass
class Local:
    static: bool = False
    ptr: bool = False
    ref: bool = False
    array: bool = False
    fresh: bool = True  # Python: 束縛がすべて新規リテラル/コンテナ
    type: str | None = None   # C++: 宣言の素の型名
    elem: object = None       # C++: コンテナの要素の型（_elem_of_type）
    init: object = None       # C++: auto の初期化子の節
    rng: object = None        # C++: 範囲 for の対象の式の節


@dataclass
class Func:
    name: str
    node: object
    body: object
    lang: str
    path: str
    params: dict = field(default_factory=dict)
    is_method: bool = False
    shift: int = 0       # Python メソッド（self/cls）の引数ずれ
    cls: str | None = None
    outer: set = field(default_factory=set)       # Python: 外側関数のローカル・引数（クロージャ）
    static_kw: bool = False   # 定義の構文が static（C/C++ の static・無名名前空間。メソッド・修飾名の定義は False）
    locs_cache: object = None  # collect_locals の結果（受け手のクラスを決めるときの宣言の型の参照用）


_FOR_MACRO = re.compile(rb"\bfor\s*\(\s*([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*\)")
_STMT_LOOP_CAND = re.compile(rb"^([ \t]+)([A-Za-z_]\w*)[ \t]*\(")
_NOT_MACRO = {b"if", b"while", b"for", b"switch", b"return", b"sizeof", b"do", b"else",
              b"catch", b"decltype", b"static_assert", b"alignas", b"alignof", b"requires", b"noexcept", b"throw"}
_OPEN_BRACE_ONLY = re.compile(rb"[ \t]*\{[ \t]*\r?")
_CLASS_HEAD = re.compile(rb"\b(?:class|struct)[ \t]+((?:[A-Za-z_]\w*[ \t]+)*[A-Za-z_]\w*)[ \t\r]*(?:[:{]|$)", re.M)
_COMMENT_ONLY = re.compile(rb"(?://|/\*|\*(?:[ \t/]|$))")
_TEMPLATE_TAIL = re.compile(rb"\btemplate[ \t]*<.*>[ \t]*$")
_TRAILING_IDENT = re.compile(rb"([A-Za-z_]\w*)$")


def _match_paren_bytes(line: bytes, open_idx: int) -> int:
    depth = 0
    for k in range(open_idx, len(line)):
        ch = line[k]
        if ch == 0x28:
            depth += 1
        elif ch == 0x29:
            depth -= 1
            if depth == 0:
                return k
    return -1


def _prev_code_line(lines: list, idx: int):
    """idx より前の、空行・コメントだけの行・プリプロセッサ指令の行を除いた最も近い行（前後の空白を除く）。無ければ None。"""
    for k in range(idx - 1, -1, -1):
        t = re.sub(rb"/\*.*?\*/|//.*$", b"", lines[k]).strip()
        raw = lines[k].strip()
        if not t or raw.startswith(b"#") or _COMMENT_ONLY.match(raw):
            continue
        return t
    return None


def preprocess_c(src: bytes) -> bytes:
    """構文を作るループマクロ（for (MACRO(...)) / MACRO(...) {）を、構文解析できる形に書き換える。
    文のループマクロは、引数が1行に収まり `{` が同じ行の末尾（K&R 形式）か次の行に `{` だけ（Allman 形式）のもの。
    コンストラクタ（同じファイルの class / struct の名前）・`template <…>` の直後・`)` の後に `{` 以外が続くもの・
    直前の行が `else`・`do` 以外の識別子で終わるもの（戻り値の型を前の行に書く関数定義）は書き換えない。
    改行は変えない（行番号を保つ）。__xddp_iter は全引数を読み書きする擬似関数として扱う。"""
    src = _FOR_MACRO.sub(lambda m: b"for (;__xddp_iter(" + m.group(2) + b");)", src)
    lines = src.split(b"\n")
    class_names = None
    for idx, line in enumerate(lines):
        m = _STMT_LOOP_CAND.match(line)
        if m is None or m.group(2) in _NOT_MACRO:
            continue
        close = _match_paren_bytes(line, m.end() - 1)
        if close < 0:
            continue
        args = line[m.end():close]
        if any(c in args for c in b";{}"):
            continue
        rest = line[close + 1:]
        cr = b"\r" if rest.endswith(b"\r") else b""
        if _OPEN_BRACE_ONLY.fullmatch(rest):
            allman = False
        elif not rest.strip() and idx + 1 < len(lines) and _OPEN_BRACE_ONLY.fullmatch(lines[idx + 1]):
            allman = True
        else:
            continue
        if class_names is None:
            class_names = {w for h in _CLASS_HEAD.findall(src) for w in h.split()}
        if m.group(2) in class_names:
            continue
        prev = _prev_code_line(lines, idx)
        if prev is not None:
            if _TEMPLATE_TAIL.search(prev):
                continue
            tm = _TRAILING_IDENT.search(prev)
            if tm is not None and tm.group(1) not in (b"else", b"do"):
                continue
        head = m.group(1) + b"for (;__xddp_iter(" + args + b");)"
        lines[idx] = head + cr if allman else head + b" {" + cr
    return b"\n".join(lines)


class SourceFile:
    def __init__(self, path, lang, neutral=frozenset()):
        self.path = path
        self.lang = lang
        self.orig_src = Path(path).read_bytes()   # 前処理の前のテキスト（置き換えたマクロへのヒットの判定に使う）
        self.src = self.orig_src
        if lang in ("c", "cpp"):
            self.src = preprocess_c(MAC.apply_table(self.src, neutral))
        self.tree = _ts()["parser"][lang].parse(self.src)
        self.root = self.tree.root_node
        self._funcs = None
        self._imports = None
        self._lexed = None

    def lexed(self):
        """前処理の前のテキストの字句の走査（コメント・文字列・プリプロセッサ指令の範囲）。"""
        if self._lexed is None:
            self._lexed = MAC.lex(self.orig_src)
        return self._lexed

    def py_imports(self):
        if self._imports is None:
            self._imports = set()
            if self.lang == "python":
                for n in walk(self.root, stop={"function_definition", "class_definition"}):
                    if n.type == "import_statement":
                        for c in n.named_children:
                            if c.type == "dotted_name":
                                self._imports.add(txt(c).split(".")[0])
                            elif c.type == "aliased_import":
                                self._imports.add(txt(c.child_by_field_name("alias")))
                    elif n.type == "import_from_statement":
                        for c in n.children_by_field_name("name"):
                            nm = c.child_by_field_name("alias") if c.type == "aliased_import" else c
                            if nm is not None:
                                self._imports.add(txt(nm).split(".")[-1])
        return self._imports

    def funcs(self):
        if self._funcs is None:
            self._funcs = [f for f in (_make_func(n, self) for n in walk(self.root)
                                       if n.type == "function_definition") if f]
        return self._funcs

    def func_at(self, node):
        """node を含む最も内側の関数定義。"""
        best = None
        for f in self.funcs():
            if f.node.start_byte <= node.start_byte and node.end_byte <= f.node.end_byte:
                if best is None or f.node.start_byte >= best.node.start_byte:
                    best = f
        return best


@lru_cache(maxsize=400)
def load(path, lang, neutral=frozenset()):
    """`neutral` は置き換えるマクロの表（specout_macros.table_key の形。空なら置き換えない）。"""
    return SourceFile(path, lang, neutral)


_DECL_WRAPPERS = ("pointer_declarator", "reference_declarator", "parenthesized_declarator",
                  "attributed_declarator", "array_declarator", "init_declarator")


def c_decl(d):
    """宣言子をたどって (名前, ptr, ref, array, function_declarator) を返す。"""
    ptr = ref = array = False
    fd = None
    while d is not None:
        t = d.type
        if t == "function_declarator":
            fd = fd or d
            d = d.child_by_field_name("declarator")
            continue
        if t in _DECL_WRAPPERS:
            ptr |= t == "pointer_declarator"
            ref |= t == "reference_declarator"
            array |= t == "array_declarator"
            nd = d.child_by_field_name("declarator")
            if nd is None:
                nd = next((c for c in d.named_children
                           if c.type.endswith("declarator") or c.type in
                           ("identifier", "field_identifier", "qualified_identifier")), None)
            d = nd
            continue
        if t in ("identifier", "field_identifier", "destructor_name", "operator_name",
                 "type_identifier"):
            return txt(d), ptr, ref, array, fd
        if t in ("qualified_identifier", "template_function"):
            nm = d.child_by_field_name("name")
            if nm is None:
                return txt(d).split("::")[-1], ptr, ref, array, fd
            d = nm
            continue
        ids = [x for x in walk(d) if x.type == "identifier"]
        return (txt(ids[0]) if ids else None), ptr, ref, array, fd
    return None, ptr, ref, array, fd


def _make_func(n, sf):
    body = n.child_by_field_name("body")
    if body is None:
        return None
    if sf.lang == "python":
        name = txt(n.child_by_field_name("name"))
        f = Func(name, n, body, sf.lang, sf.path)
        idx = 0
        for p in n.child_by_field_name("parameters").named_children:
            pn = None
            if p.type == "identifier":
                pn = txt(p)
            elif p.type in ("default_parameter", "typed_default_parameter"):
                pn = txt(p.child_by_field_name("name"))
            elif p.type in ("typed_parameter", "list_splat_pattern", "dictionary_splat_pattern"):
                ids = [c for c in p.named_children if c.type == "identifier"]
                pn = txt(ids[0]) if ids else None
            if pn:
                f.params[pn] = Param(pn, idx, ptr=True)
                idx += 1
        par = n.parent
        if par is not None and par.type == "decorated_definition":
            par = par.parent
        if par is not None and par.type == "block" and par.parent is not None \
                and par.parent.type == "class_definition":
            f.is_method = True
            f.cls = txt(par.parent.child_by_field_name("name"))
            first = next(iter(f.params), None)
            if first in ("self", "cls"):
                f.shift = 1
        return f
    name, _, _, _, fd = c_decl(n.child_by_field_name("declarator"))
    if not name:
        return None
    f = Func(name, n, body, sf.lang, sf.path)
    d = n.child_by_field_name("declarator")
    head = txt(d).split("(")[0]
    f.is_method = sf.lang == "cpp" and ("::" in head or any(
        a.type == "field_declaration_list" for a in _ancestors(n)))
    in_class = any(a.type == "field_declaration_list" for a in _ancestors(n))
    if "::" not in head and not in_class:
        f.static_kw = "static" in _storage(n) or any(
            a.type == "namespace_definition" and a.child_by_field_name("name") is None for a in _ancestors(n))
    if f.is_method:
        if "::" in head:
            f.cls = _qualifier_name(d, head)
        else:
            for a in _ancestors(n):
                if a.type in ("class_specifier", "struct_specifier"):
                    nm = a.child_by_field_name("name")
                    f.cls = _plain_type_node(nm) if nm is not None else None
                    break
    if fd is not None:
        plist = fd.child_by_field_name("parameters")
        idx = 0
        for p in (plist.named_children if plist else []):
            if p.type not in ("parameter_declaration", "optional_parameter_declaration"):
                continue
            pd = p.child_by_field_name("declarator")
            if pd is None:
                idx += 1
                continue
            pn, ptr, ref, array, _ = c_decl(pd)
            if pn:
                tn = p.child_by_field_name("type") if sf.lang == "cpp" else None
                f.params[pn] = Param(pn, idx, ptr=ptr or array, ref=ref,
                                     type=_plain_type_node(tn) if tn is not None else None,
                                     qual=_type_qual(tn) if tn is not None else (),
                                     elem=_elem_of_type(tn) if tn is not None else None)
            idx += 1
    return f


SMART_POINTERS = {"shared_ptr", "unique_ptr", "weak_ptr"}


def _plain_type_node(n):
    """型の節から素の型名（const・*・&・テンプレート引数・名前空間の修飾を除く。`std::shared_ptr<T>`・`unique_ptr<T>`・
    `weak_ptr<T>` は T）。取れなければ None。"""
    for _ in range(16):
        if n is None:
            return None
        t = n.type
        if t == "type_descriptor":
            n = n.child_by_field_name("type")
            continue
        if t == "qualified_identifier":
            n = n.child_by_field_name("name")
            continue
        if t == "template_type":
            nm = n.child_by_field_name("name")
            base = txt(nm) if nm is not None else None
            if base in SMART_POINTERS:
                args = n.child_by_field_name("arguments")
                n = args.named_children[0] if (args is not None and args.named_children) else None
                continue
            return base
        if t in ("type_identifier", "primitive_type", "namespace_identifier", "identifier"):
            return txt(n)
        if t in ("class_specifier", "struct_specifier"):
            n = n.child_by_field_name("name")
            continue
        return None
    return None


SEQ_CONTAINERS = {"vector", "list", "deque", "set", "unordered_set", "multiset", "unordered_multiset", "array",
                  "span", "initializer_list", "forward_list"}
MAP_CONTAINERS = {"map", "unordered_map", "multimap", "unordered_multimap"}


def _type_qual(n):
    """型の節の名前空間の修飾（`fmt::formatter<T>` は ('fmt',)）。スマートポインタは中の型の修飾。"""
    q = []
    for _ in range(16):
        if n is None:
            return tuple(q)
        t = n.type
        if t == "type_descriptor":
            n = n.child_by_field_name("type")
            continue
        if t == "qualified_identifier":
            sc = n.child_by_field_name("scope")
            if sc is not None:
                nm = _plain_type_name(sc)
                if nm:
                    q.append(nm)
            n = n.child_by_field_name("name")
            continue
        if t == "template_type":
            nm = n.child_by_field_name("name")
            if nm is not None and txt(nm) in SMART_POINTERS:
                args = n.child_by_field_name("arguments")
                n = args.named_children[0] if (args is not None and args.named_children) else None
                q = []
                continue
            return tuple(q)
        if t in ("class_specifier", "struct_specifier"):
            n = n.child_by_field_name("name")
            continue
        return tuple(q)
    return tuple(q)


def _elem_of_type(n):
    """コンテナの型の節の要素の型: ('seq', 素の型名, 修飾) / ('map', (キー), (値)) / None。"""
    for _ in range(16):
        if n is None:
            return None
        t = n.type
        if t == "type_descriptor":
            n = n.child_by_field_name("type")
            continue
        if t == "qualified_identifier":
            n = n.child_by_field_name("name")
            continue
        if t == "template_type":
            nm = n.child_by_field_name("name")
            base = txt(nm) if nm is not None else None
            args = n.child_by_field_name("arguments")
            a = [c for c in (args.named_children if args is not None else ()) if c.type == "type_descriptor"]
            if base in SEQ_CONTAINERS and a:
                return ("seq", _plain_type_node(a[0]), _type_qual(a[0]))
            if base in MAP_CONTAINERS and len(a) >= 2:
                return ("map", (_plain_type_node(a[0]), _type_qual(a[0])), (_plain_type_node(a[1]), _type_qual(a[1])))
            return None
        return None
    return None


def _ns_of(node, rel):
    """node を囲む名前空間とクラスの経路（外側から）。inline 名前空間は数えない。無名名前空間はファイルごとの名前。"""
    parts = []
    for a in _ancestors(node):
        if a.type == "namespace_definition":
            if any(c.type == "inline" for c in a.children):
                continue
            nm = a.child_by_field_name("name")
            if nm is None:
                parts.append("anon_%d" % (zlib.crc32(rel.encode()) % 1000000))
            else:
                parts.extend(reversed([p for p in re.findall(r"[A-Za-z_]\w*", txt(nm)) if p != "inline"]))
        elif a.type in ("class_specifier", "struct_specifier"):
            nm = _plain_type_node(a.child_by_field_name("name"))
            if nm:
                parts.append(nm)
                parts.extend(reversed(_type_qual(a.child_by_field_name("name"))))
    return tuple(reversed(parts))


def _plain_type_name(n):
    """型の名前の節から、テンプレート引数・修飾を除いた素の名前。"""
    if n is None:
        return None
    if n.type == "template_type":
        nm = n.child_by_field_name("name")
        return txt(nm) if nm is not None else None
    if n.type in ("namespace_identifier", "type_identifier", "identifier"):
        return txt(n)
    ids = re.findall(r"[A-Za-z_]\w*", txt(n).split("<")[0])
    return ids[-1] if ids else None


def _head_qual(f):
    """クラスの外の定義 `a::b::X::foo` の X より前の修飾 ('a', 'b')。"""
    head = txt(f.node.child_by_field_name("declarator")).split("(")[0]
    for _ in range(8):
        h2 = re.sub(r"<[^<>]*>", "", head)
        if h2 == head:
            break
        head = h2
    parts = [re.findall(r"[A-Za-z_]\w*", p)[-1] for p in head.split("::") if re.findall(r"[A-Za-z_]\w*", p)]
    return tuple(parts[:-2])


def _qualifier_name(d, head: str):
    """クラスの外の定義の宣言子から、関数名の直前の修飾子（最も内側の qualified_identifier の scope）の素の名前。
    `a::b::X::foo` は X、`X<T>::foo` は X。木から取れなければテキストの最後の修飾子から識別子を取る。"""
    while d is not None:
        if d.type == "qualified_identifier":
            inner = d
            while True:
                nm = inner.child_by_field_name("name")
                if nm is not None and nm.type == "qualified_identifier":
                    inner = nm
                    continue
                break
            name = _plain_type_name(inner.child_by_field_name("scope"))
            if name:
                return name
            break
        if d.type == "function_declarator" or d.type in _DECL_WRAPPERS:
            nd = d.child_by_field_name("declarator")
            if nd is None:
                nd = next((c for c in d.named_children
                           if c.type.endswith("declarator") or c.type == "qualified_identifier"), None)
            d = nd
            continue
        break
    ids = re.findall(r"[A-Za-z_]\w*", head.split("::")[-2].split("<")[0])
    return ids[-1] if ids else None


def _ancestors(n):
    p = n.parent
    while p is not None:
        yield p
        p = p.parent


# ---------------------------------------------------------------------------
# 左辺値（書き込み先）の解析
# ---------------------------------------------------------------------------

def lvals(n, lang):
    """書き込み先ノード → [(root名 or None, kind('var'|'through'|'member'), via, field)]。
    via: True=ポインタ経由('->','*')、False='.'、'index'=添字。
    field: root 直下のフィールド名（グローバル構造体をフィールド単位で追うため）。"""
    t = n.type
    if t == "identifier":
        return [(txt(n), "var", False, None)]
    if t == "this":
        return [("this", "member", True, None)]
    if lang == "python":
        if t == "attribute":
            obj = n.child_by_field_name("object")
            fl = txt(n.child_by_field_name("attribute")) if obj.type == "identifier" else None
            return [(r, "through", True, fl or f0) for r, _, _, f0 in lvals(obj, lang)]
        if t == "subscript":
            return [(r, "through", True, f0) for r, _, _, f0 in lvals(n.child_by_field_name("value"), lang)]
        if t in ("pattern_list", "tuple_pattern", "list_pattern", "tuple", "list",
                 "parenthesized_expression", "list_splat_pattern", "list_splat"):
            out = []
            for c in n.named_children:
                out += lvals(c, lang)
            return out
        return [(None, "through", True, None)]
    # C / C++
    if t == "field_expression":
        arg = n.child_by_field_name("argument")
        arrow = any(c.type == "->" for c in n.children)
        if arg is not None and arg.type == "this":
            fn = n.child_by_field_name("field")
            return [("this", "member", True, txt(fn) if fn is not None else None)]
        if arg is None:
            return [(None, "through", True, None)]
        fn = n.child_by_field_name("field")
        fl = txt(fn) if (fn is not None and arg.type == "identifier") else None
        return [(r, "member" if k == "member" else "through", v or arrow, fl or f0)
                for r, k, v, f0 in lvals(arg, lang)]
    if t == "pointer_expression":
        if n.children and n.children[0].type == "*":
            return [(r, "member" if k == "member" else "through", True, f0)
                    for r, k, _, f0 in lvals(n.child_by_field_name("argument"), lang)]
        return []
    if t == "subscript_expression":
        arg = n.child_by_field_name("argument")
        return [(r, "member" if k == "member" else "through", v if v is True else "index", f0)
                for r, k, v, f0 in lvals(arg, lang)]
    if t == "parenthesized_expression":
        return lvals(n.named_children[0], lang) if n.named_children else []
    if t == "cast_expression":
        return lvals(n.child_by_field_name("value"), lang)
    if t in ("qualified_identifier",):
        return [(txt(n).split("::")[-1], "var", False, None)]
    if t == "update_expression":
        return lvals(n.child_by_field_name("argument"), lang)
    if t == "binary_expression":   # ポインタ演算 p + k
        op = n.child_by_field_name("operator")
        if op is not None and txt(op) in ("+", "-"):
            return [(r, "member" if k == "member" else "through", True, f0)
                    for r, k, _, f0 in lvals(n.child_by_field_name("left"), lang)]
    if t == "conditional_expression":
        return lvals(n.child_by_field_name("consequence"), lang) + \
            lvals(n.child_by_field_name("alternative"), lang)
    if t in _LITERALS:
        return []
    return [(None, "through", True, None)]


_LITERALS = {"null", "number_literal", "string_literal", "char_literal", "true", "false",
             "concatenated_string", "sizeof_expression", "nullptr", "integer", "float", "string",
             "none"}
_C_KEYWORDS = {"if", "while", "for", "switch", "return", "sizeof", "do", "else", "case",
               "defined", "typeof", "__typeof__", "_Generic", "alignof"}


def arg_written(arg, lang):
    """呼び出し先が引数を書き換える場合の、呼び出し元側の書き込み先。"""
    if arg.type in _LITERALS:
        return []
    if lang != "python" and arg.type == "pointer_expression" and arg.children \
            and arg.children[0].type == "&":
        return lvals(arg.child_by_field_name("argument"), lang)
    if arg.type == "identifier":
        # Python: オブジェクト参照。C/C++: ポインタ変数または配列の暗黙変換（配列なら局所）
        return [(txt(arg), "through", True if lang == "python" else "index", None)]
    return [(r, "member" if k == "member" else "through", True, f0) for r, k, _, f0 in lvals(arg, lang)]


def recv_written(call, recv, lang):
    """メソッド呼び出しの receiver が書き換えられる場合の書き込み先。"""
    if lang == "python":
        return arg_written(recv, lang)
    fn = call.child_by_field_name("function")
    arrow = fn is not None and any(c.type == "->" for c in fn.children)
    return [(r, "member" if k == "member" else "through", True if arrow else v, f0)
            for r, k, v, f0 in lvals(recv, lang)] if recv.type != "identifier" else \
        [(txt(recv), "through", True if arrow else False, None)]


# ---------------------------------------------------------------------------
# 文単位（unit）への分解
# ---------------------------------------------------------------------------

@dataclass
class Unit:
    id: int
    nodes: list            # 識別子を走査するノード群
    kind: str              # stmt / cond / jump / goto / ret / raise / nested
    controls: tuple
    start: int
    defs: list = field(default_factory=list)      # [(root, kind, via, field)]
    uses: set = field(default_factory=set)
    calls: list = field(default_factory=list)
    value_return: bool = False
    has_error: bool = False


_C_STMT_SIMPLE = {"expression_statement", "declaration", "return_statement", "throw_statement",
                  "goto_statement", "break_statement", "continue_statement"}
_PY_NESTED = {"function_definition", "class_definition", "decorated_definition"}


class UnitBuilder:
    def __init__(self, func: Func):
        self.f = func
        self.lang = func.lang
        self.units: list[Unit] = []

    def add(self, nodes, kind, controls, start):
        u = Unit(len(self.units), [n for n in nodes if n is not None], kind, tuple(controls), start)
        self.units.append(u)
        return u

    def build(self):
        if self.lang == "python":
            self.py(self.f.body, [])
        else:
            self.c(self.f.body, [])
        for u in self.units:
            scan(u, self.lang)
        return self.units

    # C / C++ -------------------------------------------------------------
    def c(self, n, ctl):
        if n is None:
            return
        t = n.type
        if t in ("compound_statement", "preproc_if", "preproc_ifdef", "preproc_else",
                 "preproc_elif", "preproc_elifdef", "else_clause", "translation_unit"):
            for ch in n.named_children:
                if ch.type in ("comment", "preproc_arg", "identifier") and t.startswith("preproc"):
                    continue
                self.c(ch, ctl)
            return
        if t == "if_statement":
            cond = self.add([n.child_by_field_name("condition")], "cond", ctl, n.start_byte)
            self.c(n.child_by_field_name("consequence"), ctl + [cond.id])
            self.c(n.child_by_field_name("alternative"), ctl + [cond.id])
            return
        if t in ("while_statement", "switch_statement", "do_statement"):
            cond = self.add([n.child_by_field_name("condition")], "cond", ctl, n.start_byte)
            self.c(n.child_by_field_name("body"), ctl + [cond.id])
            return
        if t == "for_statement":
            init = n.child_by_field_name("initializer")
            if init is not None:
                self.add([init], "stmt", ctl, init.start_byte)
            cond = self.add([n.child_by_field_name("condition")], "cond", ctl, n.start_byte)
            upd = n.child_by_field_name("update")
            if upd is not None:
                self.add([upd], "stmt", ctl + [cond.id], upd.start_byte)
            self.c(n.child_by_field_name("body"), ctl + [cond.id])
            return
        if t == "for_range_loop":
            h = self.add([n.child_by_field_name("right")], "cond", ctl, n.start_byte)
            dn, *_ = c_decl(n.child_by_field_name("declarator"))
            if dn:
                h.defs.append((dn, "var", False, None))
            self.c(n.child_by_field_name("body"), ctl + [h.id])
            return
        if t == "case_statement":
            for ch in n.named_children:
                if ch.type.endswith("statement") or ch.type in ("declaration", "compound_statement"):
                    self.c(ch, ctl)
            return
        if t == "labeled_statement":
            for ch in n.named_children:
                if ch.type != "statement_identifier":
                    self.c(ch, ctl)
            return
        if t == "try_statement":
            body = n.child_by_field_name("body")
            pseudo = self.add([body], "cond", ctl, n.start_byte)  # 例外の発生有無
            self.c(body, ctl)
            for ch in n.named_children:
                if ch.type == "catch_clause":
                    self.c(ch.child_by_field_name("body"), ctl + [pseudo.id])
            return
        if t in _C_STMT_SIMPLE or t.endswith("_statement"):
            kind = {"return_statement": "ret", "throw_statement": "raise",
                    "goto_statement": "goto", "break_statement": "jump",
                    "continue_statement": "jump"}.get(t, "stmt")
            u = self.add([n], kind, ctl, n.start_byte)
            if kind == "ret":
                u.value_return = any(c.is_named and c.type != "comment" for c in n.children)
            return
        if t == "comment":
            return
        u = self.add([n], "stmt", ctl, n.start_byte)
        u.has_error = n.has_error

    # Python --------------------------------------------------------------
    def py(self, n, ctl):
        if n is None:
            return
        t = n.type
        if t in ("block", "module"):
            for ch in n.named_children:
                self.py(ch, ctl)
            return
        if t in ("if_statement", "elif_clause"):
            cond = self.add([n.child_by_field_name("condition")], "cond", ctl, n.start_byte)
            self.py(n.child_by_field_name("consequence"), ctl + [cond.id])
            for alt in n.children_by_field_name("alternative"):
                self.py(alt, ctl + [cond.id])
            return
        if t == "else_clause":
            self.py(n.child_by_field_name("body"), ctl)
            return
        if t == "while_statement":
            cond = self.add([n.child_by_field_name("condition")], "cond", ctl, n.start_byte)
            self.py(n.child_by_field_name("body"), ctl + [cond.id])
            self.py(n.child_by_field_name("alternative"), ctl + [cond.id])
            return
        if t == "for_statement":
            h = self.add([n.child_by_field_name("right")], "cond", ctl, n.start_byte)
            h.defs += lvals(n.child_by_field_name("left"), "python")
            self.py(n.child_by_field_name("body"), ctl + [h.id])
            self.py(n.child_by_field_name("alternative"), ctl + [h.id])
            return
        if t == "with_statement":
            for item in walk(n.children[1] if len(n.children) > 1 else n):
                if item.type == "with_item":
                    h = self.add([item.child_by_field_name("value")], "stmt", ctl, item.start_byte)
                    val = item.child_by_field_name("value")
                    if val is not None and val.type == "as_pattern":
                        tgt = val.child_by_field_name("alias") or next(
                            (c for c in val.named_children if c.type == "as_pattern_target"), None)
                        if tgt is not None:
                            for c in tgt.named_children or [tgt]:
                                h.defs += lvals(c, "python")
                        h.nodes = [val.named_children[0]]
            self.py(n.child_by_field_name("body"), ctl)
            return
        if t == "try_statement":
            body = n.child_by_field_name("body")
            pseudo = self.add([body], "cond", ctl, n.start_byte)
            self.py(body, ctl)
            for ch in n.named_children:
                if ch.type in ("except_clause", "except_group_clause"):
                    blk = [c for c in ch.named_children if c.type == "block"]
                    for ap in ch.named_children:
                        if ap.type == "as_pattern":
                            u = self.add([ap.named_children[0]], "stmt", ctl + [pseudo.id],
                                         ap.start_byte)
                            for tg in ap.named_children[1:]:
                                for c in tg.named_children or [tg]:
                                    u.defs += lvals(c, "python")
                    for b in blk:
                        self.py(b, ctl + [pseudo.id])
                elif ch.type in ("else_clause", "finally_clause"):
                    for b in ch.named_children:
                        if b.type == "block":
                            self.py(b, ctl + [pseudo.id])
            return
        if t == "match_statement":
            cond = self.add([n.child_by_field_name("subject")], "cond", ctl, n.start_byte)
            self.py(n.child_by_field_name("body"), ctl + [cond.id])
            return
        if t in ("case_clause",):
            self.py(n.child_by_field_name("consequence"), ctl)
            return
        if t in _PY_NESTED:
            u = self.add([n], "nested", ctl, n.start_byte)
            d = n.child_by_field_name("definition") if t == "decorated_definition" else n
            nm = d.child_by_field_name("name") if d is not None else None
            if nm is not None:
                u.defs.append((txt(nm), "var", False, None))
            return
        if t in ("global_statement", "nonlocal_statement", "comment"):
            return
        kind = {"return_statement": "ret", "raise_statement": "raise", "break_statement": "jump",
                "continue_statement": "jump"}.get(t, "stmt")
        u = self.add([n], kind, ctl, n.start_byte)
        if kind == "ret":
            u.value_return = bool(n.named_children)
        u.has_error = n.has_error


_ASSIGN_PY = {"assignment", "augmented_assignment", "named_expression"}


def scan(u: Unit, lang):
    """unit の uses / defs / calls を求める。"""
    defonly = set()
    excl = set()
    for root in u.nodes:
        for x in walk(root, stop=_PY_NESTED if lang == "python" and root.type not in _PY_NESTED
                      else None):
            t = x.type
            if x.has_error and t == "ERROR":
                u.has_error = True
            if lang == "python":
                if t == "attribute":
                    a = x.child_by_field_name("attribute")
                    if a is not None:
                        excl.add(a.start_byte)
                elif t == "keyword_argument":
                    a = x.child_by_field_name("name")
                    if a is not None:
                        excl.add(a.start_byte)
                elif t == "yield" and u.kind == "stmt":
                    u.kind, u.value_return = "ret", True
                if t in _ASSIGN_PY:
                    left = x.child_by_field_name("left") or x.child_by_field_name("name")
                    if left is not None:
                        lv = lvals(left, lang)
                        u.defs += lv
                        if t != "augmented_assignment":
                            for y in walk(left):
                                if y.type == "identifier" and y.parent is not None and \
                                        y.parent.type not in ("attribute", "subscript"):
                                    defonly.add(y.start_byte)
                                if y.type in ("attribute", "subscript"):
                                    break
                if t == "call":
                    u.calls.append(x)
                if t in ("import_statement", "import_from_statement"):
                    # import は名前を束縛する（`from m import f as g` の後の `g(...)` は f の検索ではヒットしない）
                    for name in _py_import_bindings(x):
                        u.defs.append((name, "var", False, None))
            else:
                if t == "assignment_expression":
                    left = x.child_by_field_name("left")
                    op = x.child_by_field_name("operator")
                    u.defs += lvals(left, lang)
                    if left.type == "identifier" and op is not None and txt(op) == "=":
                        defonly.add(left.start_byte)
                elif t == "update_expression":
                    u.defs += lvals(x.child_by_field_name("argument"), lang)
                elif t == "init_declarator":
                    dn, *_ = c_decl(x.child_by_field_name("declarator"))
                    if dn:
                        u.defs.append((dn, "var", False, None))
                    for y in walk(x.child_by_field_name("declarator")):
                        if y.type == "identifier":
                            defonly.add(y.start_byte)
                elif t == "declaration":
                    for d in x.children_by_field_name("declarator"):
                        if d.type != "init_declarator":
                            for y in walk(d):
                                if y.type == "identifier":
                                    defonly.add(y.start_byte)
                elif t == "call_expression":
                    u.calls.append(x)
            if t == "identifier" and x.start_byte not in defonly and x.start_byte not in excl:
                u.uses.add(txt(x))
    # defonly は走査順の都合で後から確定するものがあるため再計算
    if defonly:
        u.uses = set()
        for root in u.nodes:
            for x in walk(root, stop=_PY_NESTED if lang == "python" and root.type not in _PY_NESTED
                          else None):
                if x.type == "identifier" and x.start_byte not in defonly and \
                        x.start_byte not in excl:
                    u.uses.add(txt(x))


# ---------------------------------------------------------------------------
# ローカル変数の収集
# ---------------------------------------------------------------------------

_FRESH_PY = {"list", "dictionary", "set", "list_comprehension", "dictionary_comprehension",
             "set_comprehension", "tuple", "integer", "float", "string", "true", "false", "none"}


def collect_locals(f: Func):
    locs: dict[str, Local] = {}
    py_globals = set()
    if f.lang == "python":
        outer = set()
        for a in _ancestors(f.node):
            if a.type == "function_definition":
                for pp in a.child_by_field_name("parameters").named_children:
                    ids = [y for y in walk(pp) if y.type == "identifier"]
                    if ids:
                        outer.add(txt(ids[0]))
                for y in walk(a.child_by_field_name("body"), stop={"function_definition", "class_definition"}):
                    if y.type in ("assignment", "augmented_assignment"):
                        outer |= {r for r, k, *_ in lvals(y.child_by_field_name("left"), "python")
                                  if k == "var" and r}
        f.outer = outer
        nonlocal_names = set()
        for x in walk(f.body, stop={"function_definition", "class_definition", "lambda"}):
            t = x.type
            if t == "global_statement":
                py_globals |= {txt(c) for c in x.named_children if c.type == "identifier"}
            elif t == "nonlocal_statement":
                names_ = {txt(c) for c in x.named_children if c.type == "identifier"}
                f.outer |= names_
                nonlocal_names |= names_
            names, fresh = [], False
            if t == "assignment":
                left, right = x.child_by_field_name("left"), x.child_by_field_name("right")
                if left is not None and left.type == "identifier":
                    names = [txt(left)]
                    fresh = right is not None and (right.type in _FRESH_PY or (
                        right.type == "call" and txt(right.child_by_field_name("function"))
                        in ("list", "dict", "set", "tuple", "str", "int")))
                elif left is not None:
                    names = [r for r, k, *_ in lvals(left, "python") if k == "var" and r]
            elif t in ("for_statement", "for_in_clause"):
                names = [r for r, k, *_ in lvals(x.child_by_field_name("left"), "python")
                         if k == "var" and r]
            elif t == "as_pattern_target":
                names = [r for c in (x.named_children or [x])
                         for r, k, *_ in lvals(c, "python") if k == "var" and r]
            elif t == "named_expression":
                names = [txt(x.child_by_field_name("name"))]
            elif t in ("aliased_import",):
                names = [txt(x.child_by_field_name("alias"))]
            elif t in ("function_definition", "class_definition") and x is not f.node:
                names = [txt(x.child_by_field_name("name"))]
            for nm in names:
                if nm in f.params:
                    continue
                L = locs.setdefault(nm, Local(ptr=True))
                L.fresh = L.fresh and fresh
        for g in py_globals | nonlocal_names:
            locs.pop(g, None)
        return locs, py_globals
    for x in walk(f.body):
        t = x.type
        if t == "declaration":
            storage = _storage(x)
            if "extern" in storage:
                continue   # ブロックスコープの extern 宣言はローカル変数ではない（外部から見える名前）
            static = "static" in storage
            tnode = x.child_by_field_name("type")
            tp = _plain_type_node(tnode) if f.lang == "cpp" else None
            el = _elem_of_type(tnode) if f.lang == "cpp" else None
            for d in x.children_by_field_name("declarator"):
                nm, ptr, ref, array, fd = c_decl(d)
                if nm and fd is None:
                    init = d.child_by_field_name("value") if (f.lang == "cpp" and tp is None
                                                              and d.type == "init_declarator") else None
                    locs[nm] = Local(static=static, ptr=ptr, ref=ref, array=array, type=tp, elem=el, init=init)
        elif t == "for_range_loop":
            nm, ptr, ref, array, _ = c_decl(x.child_by_field_name("declarator"))
            if nm:
                tp = _plain_type_node(x.child_by_field_name("type")) if f.lang == "cpp" else None
                locs[nm] = Local(ptr=ptr, ref=ref, array=array, type=tp,
                                 rng=x.child_by_field_name("right") if (f.lang == "cpp" and tp is None) else None)
        elif t == "parameter_declaration":  # lambda / catch の引数
            d = x.child_by_field_name("declarator")
            if d is not None:
                nm, ptr, ref, array, _ = c_decl(d)
                if nm:
                    locs[nm] = Local(ptr=ptr, ref=ref, array=array)
    return locs, py_globals


# ---------------------------------------------------------------------------
# 呼び出し先の解決（リポジトリ全体の定義索引）
# ---------------------------------------------------------------------------

@dataclass
class ClassInfo:
    """C++ のクラス・構造体（本体のある定義）1つ。名前はテンプレート引数・名前空間を除いた素の名前。"""
    name: str
    file: str
    bases: list = field(default_factory=list)     # [(基底クラスの素の名前, 名前空間で修飾されているか)]
    methods: dict = field(default_factory=dict)   # {名前: 宣言に virtual・override・final があるか}
    members: dict = field(default_factory=dict)   # {名前: 宣言の素の型名 or None}
    ns: tuple = ()                                # 囲む名前空間・クラスの経路
    key: str = ""                                 # クラスの鍵（素の名前、名前空間をまたいで重なれば ns::名前）
    bases_q: list = field(default_factory=list)   # [(素の名前, 修飾)]
    member_q: dict = field(default_factory=dict)  # {名前: 修飾}
    member_elem: dict = field(default_factory=dict)  # {名前: 要素の型}
    ret: dict = field(default_factory=dict)       # {メソッド名: (素の戻り値の型, 修飾) or None}
    files: list = field(default_factory=list)
    reliable: bool = True                         # 定義のファイルに構文解析の誤りが無い（名前空間の経路を信用できる）
    partial: set = field(default_factory=set)     # まとめた版の一部にしか無いメソッド・メンバー


AMBIGUOUS = "\x00ambiguous"
_CLASS_TEXT_RE = re.compile(rb"\b(?:class|struct)\s+((?:[A-Za-z_]\w*\s+)*[A-Za-z_]\w*)")
_ENUM_BEFORE_TEXT_RE = re.compile(rb"\benum\s+$")
# クラス・構造体の定義（本体の前の基底の句の有無。テンプレートの特殊化の引数・宣言を飾る語を許す）
_CLASS_DEF_TEXT_RE = re.compile(rb"\b(?:class|struct)\s+(?:[A-Za-z_]\w*\s+)*?([A-Za-z_]\w*)\s*(?:<[^;{]*?>)?\s*"
                                rb"(?:final\s*)?([:{])")
_USING_TEXT_RE = re.compile(rb"\busing\s+([A-Za-z_]\w*)\s*=\s*([^;]+);")
_TYPEDEF_TEXT_RE = re.compile(rb"\btypedef\s+([^;{}]+?)\s+([A-Za-z_]\w*)\s*;")
_BRACE_TYPEDEF_TEXT_RE = re.compile(rb"\}\s*([A-Za-z_]\w*)\s*;")
_DEFINE_IDENT_TEXT_RE = re.compile(rb"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)[ \t]+([A-Za-z_]\w*)[ \t]*$", re.M)
VALUE_KIND_NAMES = {"value", "variable", "macro"}
REL_RESOLVED = "resolved"
REL_NAME_ONLY = "name-only"
REL_OTHER = "other-class"


class Repo:
    def __init__(self, root, excludes=None, h_as="c", policy="optimistic", max_depth=3):
        self.root = os.path.abspath(root)
        self.excludes = list(excludes or [])
        self.h_as = h_as
        self.policy = policy          # 'strict' | 'optimistic'（外部関数の扱い）
        self.ignore_re = None         # 影響なしとみなす呼び出し（ログ・メモリ確保等。プロジェクト設定）
        self.max_depth = max_depth
        self._index = None            # name -> [(relpath, start_byte)]
        self._macros = None           # name -> (params, body)
        self._summ = {}
        self.stats = {"external_assumed_pure": 0, "external_unknown": 0, "depth_limit": 0}
        # リンケージの索引（build_index が作る）
        self.internal = {}            # 内部リンケージ {名前: {ファイル}}（ヘッダ以外の static・無名名前空間・マクロ）
        self.visible = set()          # 外部から見える名前（extern の変数の宣言・ヘッダのファイルスコープの変数の宣言とマクロ）
        self.file_decls = {}          # ファイル内の宣言 {ファイル: {変数名}}（static かどうかによらない）
        self.file_scope_names = set()  # 全ファイルのファイルスコープの変数名（関数ポインタの呼び出しの判定用）
        self.static_fwd = {}          # static 関数の前方宣言 {ファイル: {名前}}（ヘッダ以外）
        self.ext_defs_in_file = {}    # ファイル内の外部リンケージの定義 {ファイル: {名前}}
        self.ext_def_count = {}       # 外部リンケージの定義の数 {名前: 件数}
        self.py_globals = set()       # Python のモジュールのトップレベルの代入の左辺
        # C++ のクラスの索引（build_index が作る）
        self.classes = {}             # {素のクラス名: [ClassInfo]}（同じ素の名前のクラスが複数あれば2件以上）
        self.aliases = {}             # 型の別名 {別名: 素の型名 | AMBIGUOUS}
        self.file_var_types = {}      # ファイルスコープの変数の型 {ファイル: {変数名: 素の型名}}
        self.global_var_types = {}    # {変数名: {素の型名}}
        self._chain = {}
        self._subclasses = None
        self._text_classes = None
        self._text_types = None       # (別名の右辺 {名前: [テキスト]}, 基底の句 {クラス名: 持つか}, 本体つきの typedef の名前)
        self._text_defines = {}       # {マクロ名: {本体の識別子}}（`#define 名前 識別子` の形だけ）
        self.ns_macro = {}            # 名前空間名のマクロ → 置き換え先の識別子（_finalize_classes が作る）
        self._neutral = None          # 置き換えるマクロの表 {名前: specout_macros.Neutral}（最初の構文解析の前に作る）
        self._neutral_key = frozenset()

    def neutral(self) -> dict:
        """置き換えるマクロの表（宣言を飾るマクロ・名前空間マクロ）。リポジトリの全 C/C++ ファイルの事前走査から作る。"""
        if self._neutral is None:
            self._neutral = MAC.neutralize_table(self.root)
            self._neutral_key = MAC.table_key(self._neutral)
        return self._neutral

    def code_files(self):
        return [p for p in list_repo_files(self.root, self.excludes) if lang_of(p, self.h_as)]

    def file(self, rel):
        lang = lang_of(rel, self.h_as)
        if lang in ("c", "cpp"):
            self.neutral()
            return load(os.path.join(self.root, rel), lang, self._neutral_key)
        return load(os.path.join(self.root, rel), lang)

    def rel(self, path) -> str:
        """関数・ファイルのパス（絶対・相対のどちらでもよい）をリポジトリからの相対パスにする。"""
        if not os.path.isabs(path):
            return path.replace(os.sep, "/")
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def build_index(self):
        self._index, self._macros = {}, {}
        self.internal, self.visible = {}, set()
        self.file_decls, self.file_scope_names = {}, set()
        self.static_fwd, self.ext_defs_in_file, self.ext_def_count = {}, {}, {}
        self.py_globals = set()
        self.classes, self.aliases, self.file_var_types, self.global_var_types = {}, {}, {}, {}
        self.class_keys_by_bare, self.ns_names, self.enum_names, self.free_ret = {}, set(), set(), {}
        self._fcls, self._fctx, self._sites = {}, {}, {}
        self._chain, self._subclasses = {}, None
        out_of_class = []      # クラスの外のメソッドの定義 [(クラス名, メソッド名)]
        defs = {}              # 外部リンケージの定義 {名前: {鍵}}
        nonheader_macros = {}  # ヘッダ以外のファイルのマクロ {名前: {ファイル}}
        header_macros = set()
        file_funcs = {}        # {ファイル: [Func]}（外部リンケージの定義の判定は static_fwd がそろってから行う）
        var_defs = {}          # {ファイル: {外部リンケージの変数名}}

        def _add(d, k, v):
            d.setdefault(k, set()).add(v)

        for rel in self.code_files():
            try:
                sf = self.file(rel)
            except (OSError, ValueError):
                continue
            header = is_header(rel)
            if sf.lang == "python":
                for n in sf.root.named_children:
                    if n.type == "expression_statement":
                        for a in n.named_children:
                            if a.type in ("assignment", "augmented_assignment"):
                                for r, *_ in lvals(a.child_by_field_name("left"), "python"):
                                    if r:
                                        self.py_globals.add(r)
                                        _add(defs, r, ("py", rel))
                    d = n.child_by_field_name("definition") if n.type == "decorated_definition" else n
                    if d is not None and d.type == "class_definition":
                        nm = d.child_by_field_name("name")
                        if nm is not None:
                            _add(defs, txt(nm), ("py", rel))
                for f in sf.funcs():
                    if f.is_method:
                        _add(defs, f.name, ("m", f.cls, f.name))
                    elif _py_module_level(f.node):
                        _add(defs, f.name, ("py", rel))
                    self._index.setdefault(f.name, []).append((rel, f.node.start_byte))
                continue
            decls = self.file_decls.setdefault(rel, set())
            if sf.lang == "cpp":
                self._index_classes(sf, rel)
                out_of_class += [(f.cls, f.name, _ns_of(f.node, rel), _head_qual(f))
                                 for f in sf.funcs() if f.is_method and f.cls
                                 and "::" in txt(f.node.child_by_field_name("declarator")).split("(")[0]]
            for n, anon, linkage in _file_scope_nodes(sf.root):
                if n.type == "declaration" and sf.lang == "cpp":
                    tp = _plain_type_node(n.child_by_field_name("type"))
                    for d in n.children_by_field_name("declarator"):
                        nm, _, _, _, fd = c_decl(d)
                        if nm and fd is None and tp:
                            self.file_var_types.setdefault(rel, {})[nm] = tp
                            self.global_var_types.setdefault(nm, set()).add(tp)
                if n.type == "declaration":
                    storage = _storage(n)
                    for d in n.children_by_field_name("declarator"):
                        nm, _, _, _, fd = c_decl(d)
                        if not nm:
                            continue
                        qualified = any(x.type == "qualified_identifier" for x in walk(d))
                        if "extern" in storage or linkage or header:
                            # 書き込み先の解決に使うため変数だけ（関数の宣言は書き込み先にならない）
                            if fd is None:
                                self.visible.add(nm)
                        elif not qualified and ("static" in storage or anon):
                            _add(self.internal, nm, rel)
                        if fd is None:
                            decls.add(nm)
                            if header:
                                if "extern" not in storage:
                                    _add(defs, nm, ("v", rel))
                            elif "static" not in storage and "extern" not in storage and not anon \
                                    and not qualified:
                                _add(var_defs, rel, nm)
                        elif "static" in storage and not header and not qualified:
                            _add(self.static_fwd, rel, nm)
            # 関数の本体の中のブロックスコープの extern 宣言も外部から見える名前とする
            for n in walk(sf.root):
                if n.type == "declaration" and "extern" in _storage(n) and not _at_file_scope(n):
                    for d in n.children_by_field_name("declarator"):
                        nm, _, _, _, fd = c_decl(d)
                        if nm and fd is None:
                            self.visible.add(nm)
            self.file_scope_names |= decls
            funcs = sf.funcs()
            file_funcs[rel] = [(f.name, f.static_kw, f.is_method, f.cls, f.node.start_byte) for f in funcs]
            for f in funcs:
                self._index.setdefault(f.name, []).append((rel, f.node.start_byte))
                if f.static_kw and not header:
                    _add(self.internal, f.name, rel)
            for n in walk(sf.root, stop={"function_definition"}):
                if n.type in ("preproc_def", "preproc_function_def"):
                    nm = n.child_by_field_name("name")
                    if nm is None:
                        continue
                    if header:
                        header_macros.add(txt(nm))
                        self.visible.add(txt(nm))
                    else:
                        _add(nonheader_macros, txt(nm), rel)
                    if n.type == "preproc_function_def":
                        ps = n.child_by_field_name("parameters")
                        val = n.child_by_field_name("value")
                        params = [txt(c) for c in ps.named_children] if ps else []
                        self._macros[txt(nm)] = (params, txt(val) if val is not None else "")
        for nm, files in nonheader_macros.items():
            if nm not in header_macros:
                for rel in files:
                    _add(self.internal, nm, rel)
        for nm in header_macros:
            _add(defs, nm, ("macro", nm))
        # 外部リンケージの関数の定義（前方宣言だけが static の関数は内部リンケージ）
        for rel, funcs in file_funcs.items():
            header = is_header(rel)
            for name, static_kw, is_method, cls, sb in funcs:
                static_def = not header and (static_kw or (not is_method and name in self.static_fwd.get(rel, ())))
                if static_def:
                    continue
                _add(self.ext_defs_in_file, rel, name)
                _add(defs, name, ("m", cls, name) if is_method else ("f", rel, sb))
        for rel, names in var_defs.items():
            for nm in names:
                _add(self.ext_defs_in_file, rel, nm)
                _add(defs, nm, ("v", rel))
        self.ext_def_count = {nm: len(keys) for nm, keys in defs.items()}
        self._finalize_classes()
        for cname, mname, ctx, qual in out_of_class:
            info = self.class_info(self.cls_key(cname, ctx, qual))
            if info is not None and info != AMBIGUOUS:
                info.methods.setdefault(mname, False)
        load.cache_clear()

    # -- C++ のクラスの索引 ----------------------------------------------------

    def _add_alias(self, name, target) -> None:
        if not name or not target or name == target:
            return
        cur = self.aliases.get(name)
        if cur is None:
            self.aliases[name] = target
        elif cur != target:
            self.aliases[name] = AMBIGUOUS

    def _index_classes(self, sf, rel) -> None:
        """クラス・構造体（本体のある定義）の基底クラス・メソッド・メンバー変数と、型の別名（using・typedef）を記録する。"""
        for n in walk(sf.root):
            t = n.type
            if t == "alias_declaration":
                nm = n.child_by_field_name("name")
                self._add_alias(txt(nm) if nm is not None else None, _plain_type_node(n.child_by_field_name("type")))
                continue
            if t == "type_definition":
                target = _plain_type_node(n.child_by_field_name("type"))
                for d in n.children_by_field_name("declarator"):
                    self._add_alias(c_decl(d)[0], target)
                continue
            if t == "namespace_definition":
                nm = n.child_by_field_name("name")
                if nm is not None:
                    self.ns_names.update(re.findall(r"[A-Za-z_]\w*", txt(nm)))
            elif t == "namespace_alias_definition":
                nm = n.child_by_field_name("name")
                if nm is not None:
                    self.ns_names.add(txt(nm))
            elif t == "enum_specifier":
                nm = n.child_by_field_name("name")
                if nm is not None:
                    self.enum_names.add(_plain_type_name(nm))
            elif t in ("function_definition", "declaration") and not any(
                    a.type == "field_declaration_list" for a in _ancestors(n)):
                for d in ([n.child_by_field_name("declarator")] if t == "function_definition"
                          else n.children_by_field_name("declarator")):
                    if d is None:
                        continue
                    fnm, _, _, _, fdd = c_decl(d)
                    if fnm and fdd is not None and fdd.child_by_field_name("declarator") is not None \
                            and fdd.child_by_field_name("declarator").type == "identifier":
                        tn = n.child_by_field_name("type")
                        self.free_ret.setdefault(fnm, set()).add(
                            (_plain_type_node(tn), _type_qual(tn), _ns_of(n, rel)))
            if t not in ("class_specifier", "struct_specifier"):
                continue
            body = n.child_by_field_name("body")
            name = _plain_type_node(n.child_by_field_name("name"))
            if body is None or not name:
                continue
            info = ClassInfo(name, rel)
            info.ns = _ns_of(n, rel) + _type_qual(n.child_by_field_name("name"))
            info.files = [rel]
            info.reliable = not sf.root.has_error
            for c in n.named_children:
                if c.type != "base_class_clause":
                    continue
                for b in c.named_children:
                    if b.type in ("type_identifier", "qualified_identifier", "template_type"):
                        bn = _plain_type_node(b)
                        if bn:
                            info.bases.append((bn, b.type == "qualified_identifier"))
                            info.bases_q.append((bn, _type_qual(b)))
            for m in body.named_children:
                if m.type == "template_declaration":
                    m = next((c for c in reversed(m.named_children)
                              if c.type in ("field_declaration", "function_definition", "declaration")), None)
                    if m is None:
                        continue
                if m.type not in ("field_declaration", "function_definition", "declaration"):
                    continue
                virt = any(c.type == "virtual" for c in m.children)
                for d in m.children_by_field_name("declarator"):
                    mn, _, _, _, fd = c_decl(d)
                    if not mn:
                        continue
                    if fd is not None:
                        v = virt or any(c.type == "virtual_specifier" for c in fd.children)
                        info.methods[mn] = info.methods.get(mn, False) or v
                        tn = m.child_by_field_name("type")
                        if tn is not None:
                            r = (_plain_type_node(tn), _type_qual(tn))
                            info.ret[mn] = r if info.ret.get(mn, r) == r else None
                    elif m.type == "field_declaration":
                        tn = m.child_by_field_name("type")
                        info.members[mn] = _plain_type_node(tn)
                        info.member_q[mn] = _type_qual(tn)
                        info.member_elem[mn] = _elem_of_type(tn)
            self.classes.setdefault(name, []).append(info)

    def _ensure_index(self) -> None:
        if self._index is None:
            self.build_index()

    def class_info(self, name):
        """クラスの索引のクラス（鍵、または名前空間をまたいで重ならない素の名前）。索引に無ければ None、
        素の名前が名前空間をまたいで重なれば AMBIGUOUS。"""
        self._ensure_index()
        infos = self.classes.get(name)
        if infos:
            return infos[0] if len(infos) == 1 else AMBIGUOUS
        if len(self.class_keys_by_bare.get(name, ())) > 1:
            return AMBIGUOUS
        return None

    def is_class(self, name) -> bool:
        """名前がクラスの索引にあるか（鍵、または素の名前）。"""
        self._ensure_index()
        return bool(name) and (name in self.classes or name in self.class_keys_by_bare)

    def _finalize_classes(self) -> None:
        """同じ名前空間の同名クラス（条件コンパイル・プラットフォーム別の定義）を1つにまとめ、名前空間をまたいで
        素の名前が重なるクラスは鍵を ns::名前 にする。基底クラスを鍵にする。"""
        self.ns_macro = {}
        if any(len({i.ns for i in infos}) > 1 for infos in self.classes.values()):
            if self._text_classes is None:
                self._scan_text()
            self.ns_macro = {nm: next(iter(b)) for nm, b in self._text_defines.items()
                             if nm in self.ns_names and len(b) == 1}
        groups, self.classes, self.class_keys_by_bare = self.classes, {}, {}
        for infos in groups.values():
            for i in infos:
                i.ns = self._norm_ns(i.ns)
        for bare, infos in groups.items():
            if len(infos) > 1 and not all(i.reliable for i in infos):
                # 構文解析の誤りのあるファイルの定義を含む: 名前空間の経路を信用できないため分けもまとめもしない（AMBIGUOUS）
                for i in infos:
                    i.key = bare
                self.classes[bare] = list(infos)
                self.class_keys_by_bare[bare] = [bare]
                continue
            by_ns = {}
            for i in infos:
                by_ns.setdefault(i.ns, []).append(i)
            merged = [self._merge_infos(lst) for lst in by_ns.values()]
            for m in merged:
                if len(merged) == 1:
                    m.key = bare
                elif m.ns:
                    m.key = "::".join(m.ns + (bare,))
                else:
                    m.key = "::" + bare   # 名前空間に属さないクラス
                self.classes[m.key] = [m]
            self.class_keys_by_bare[bare] = [m.key for m in merged]
        for infos in self.classes.values():
            if len(infos) != 1:
                continue
            info = infos[0]
            info.bases = [(self.cls_key(b, info.ns, q), qq) for (b, q), (_b, qq) in zip(info.bases_q, info.bases)]

    @staticmethod
    def _merge_infos(lst):
        """同じ素の名前・同じ名前空間の ClassInfo を1つにまとめる（基底クラス・メソッドは和、型が違えば None、
        一部の版にしか無いメソッド・メンバーは partial）。"""
        base = lst[0]
        if len(lst) > 1:
            names = [set(i.methods) | set(i.members) for i in lst]
            base.partial = set().union(*names) - set.intersection(*names)
        for o in lst[1:]:
            for b, bq in zip(o.bases, o.bases_q):
                if b not in base.bases:
                    base.bases.append(b)
                    base.bases_q.append(bq)
            for k, v in o.methods.items():
                base.methods[k] = base.methods.get(k, False) or v
            for k, v in o.members.items():
                if k in base.members and base.members[k] != v:
                    base.members[k] = None
                else:
                    base.members.setdefault(k, v)
                    base.member_q.setdefault(k, o.member_q.get(k, ()))
                    base.member_elem.setdefault(k, o.member_elem.get(k))
            for k, v in o.ret.items():
                base.ret[k] = v if base.ret.get(k, v) == v else None
            base.files += o.files
        return base

    def entry_class(self, x_cls):
        """エントリ `[CLASS:…]` のクラス名を索引の鍵にする（`a::X` は鍵の経路の末尾との照合。決まらなければそのまま）。"""
        self._ensure_index()
        if not x_cls or x_cls in self.classes or "::" not in x_cls:
            return x_cls
        parts = x_cls.split("::")
        qual = self._norm_ns(tuple(parts[:-1]))
        c = [k for k in self.class_keys_by_bare.get(parts[-1], ())
             if self.classes[k][0].ns[-len(qual):] == qual]
        return c[0] if len(c) == 1 else x_cls

    def _norm_ns(self, t):
        return tuple(self.ns_macro.get(p, p) for p in t)

    def cls_key(self, bare, ctx=(), qual=()):
        """型の素の名前を、参照した場所の名前空間 ctx・修飾 qual からクラスの鍵にする。決まらなければ素の名前。"""
        self._ensure_index()
        if not bare:
            return bare
        if bare in self.classes and "::" in bare:
            return bare
        keys = self.class_keys_by_bare.get(bare)
        if not keys:
            return bare
        if len(keys) == 1:
            return keys[0]
        infos = [self.classes[k][0] for k in keys]
        qual = self._norm_ns(tuple(q for q in qual if q))
        if ctx is None and not qual:
            return bare   # 参照した場所の経路を信用できない（構文解析の誤りのあるファイル）
        ctx = self._norm_ns(tuple(ctx or ()))
        if qual:
            c = [i for i in infos if i.ns[-len(qual):] == qual]
            if len(c) == 1:
                return c[0].key
            if c:
                infos = c
        for k in range(len(ctx), -1, -1):
            c = [i for i in infos if i.ns == ctx[:k]]
            if len(c) == 1:
                return c[0].key
        return bare

    def fcls(self, f):
        """メソッド f のクラスの鍵（C++）。それ以外は f.cls。"""
        if f is None or f.lang != "cpp" or not f.is_method or not f.cls:
            return f.cls if f is not None else None
        k = (f.path, f.node.start_byte)
        if k in self._fcls:
            return self._fcls[k]
        rel = self.rel(f.path)
        err = self.file_error(f.path)
        key = None
        for a in _ancestors(f.node):
            if a.type in ("class_specifier", "struct_specifier"):
                key = self.cls_key(f.cls, None if err else _ns_of(a, rel) + _type_qual(a.child_by_field_name("name")))
                break
            if a.type in ("compound_statement",):
                break
        if key is None:
            key = self.cls_key(f.cls, None if err else _ns_of(f.node, rel), _head_qual(f))
        self._fcls[k] = key
        return key

    def file_error(self, path) -> bool:
        """ファイルに構文解析の誤りがあるか（名前空間・クラスの入れ子を信用できない）。"""
        return self.file(self.rel(path)).root.has_error

    def fctx(self, f):
        """関数 f の本体から見た名前空間・クラスの経路。構文解析の誤りのあるファイルでは None（経路を使わない）。"""
        if f is None:
            return ()
        k = (f.path, f.node.start_byte)
        if k not in self._fctx and self.file_error(f.path):
            self._fctx[k] = None
        if k not in self._fctx:
            ctx = _ns_of(f.node, self.rel(f.path))
            info = self.class_info(self.fcls(f)) if self.is_cpp_method(f) else None
            if info is not None and info != AMBIGUOUS:
                ctx = info.ns + (info.name,)
            self._fctx[k] = ctx
        return self._fctx[k]

    def _type_key(self, t, ctx, qual=()):
        if not t or t == "auto":
            return None
        r = self.resolve_type(t)
        if r is None:
            return None
        return self.cls_key(r, ctx, qual if r == t else ())

    def _elem_key(self, el, ctx):
        if not el or el[0] != "seq":
            return None
        return self._type_key(el[1], ctx, el[2])

    def _local_site(self, f, name, at):
        """関数 f の中で、出現 at から見える name のローカル変数の宣言（最も内側のスコープ）。
        戻り値: ("decl", 宣言の節, 宣言子) / ("range", 範囲 for の節) / None（見える宣言が無い・決まらない）。
        at が None なら、宣言が1つだけのときその宣言。"""
        sites = self._site_table(f).get(name, [])
        if at is None:
            return sites[0][2] if len(sites) == 1 else None
        vis = [(sc.start_byte, sb, site) for sc, sb, site in sites
               if sc.start_byte <= at.start_byte < sc.end_byte and (site[0] in ("range", "param") or sb < at.start_byte)]
        if not vis:
            return None
        vis.sort(key=lambda v: (v[0], v[1]))
        return vis[-1][2]

    def _site_table(self, f):
        """関数 f の本体の中で宣言した名前 → [(見える範囲の節, 宣言の位置, 宣言)]。宣言は ("decl", 宣言の節, 宣言子) /
        ("range", 範囲 for の節) / ("param", 引数の宣言の節)〔lambda・catch の引数〕/ ("unknown",)〔構造化束縛〕。"""
        key = (f.path, f.node.start_byte)
        table = self._sites.get(key)
        if table is not None:
            return table
        table = {}
        for n in walk(f.body):
            if n.type == "declaration" and n.parent is not None:
                scope = n.parent
                while scope.type in ("init_statement", "condition_clause") and scope.parent is not None:
                    scope = scope.parent   # if・while・switch の初期化・条件の宣言は文全体から見える
                for d in n.children_by_field_name("declarator"):
                    side = d.child_by_field_name("declarator") if d.type == "init_declarator" else d
                    for sb in (walk(side, stop={"lambda_expression"}) if side is not None else ()):
                        if sb.type == "structured_binding_declarator":
                            for idn in sb.named_children:
                                if idn.type == "identifier":
                                    table.setdefault(txt(idn), []).append((scope, n.start_byte, ("unknown",)))
                            break
                    else:
                        nm, _, _, _, fd = c_decl(d)
                        if nm and fd is None:
                            table.setdefault(nm, []).append((scope, n.start_byte, ("decl", n, d)))
            elif n.type == "for_range_loop":
                dcl = n.child_by_field_name("declarator")
                sb = next((y for y in walk(dcl) if y.type == "structured_binding_declarator"), None) \
                    if dcl is not None else None
                if sb is not None:
                    for idn in sb.named_children:
                        if idn.type == "identifier":
                            table.setdefault(txt(idn), []).append((n, n.start_byte, ("unknown",)))
                    continue
                nm = c_decl(dcl)[0]
                if nm:
                    table.setdefault(nm, []).append((n, n.start_byte, ("range", n)))
            elif n.type in ("parameter_declaration", "optional_parameter_declaration"):
                # lambda・catch 自身の引数の並びだけ（関数型・関数ポインタの引数名は変数ではない）
                pl = n.parent
                owner = pl.parent if pl is not None else None
                scope = None
                if owner is not None and owner.type == "catch_clause":
                    scope = owner
                elif owner is not None and owner.type == "abstract_function_declarator" and \
                        owner.parent is not None and owner.parent.type == "lambda_expression":
                    scope = owner.parent.child_by_field_name("body")   # キャプチャの並びは外側の名前を見る
                d = n.child_by_field_name("declarator")
                nm = c_decl(d)[0] if d is not None else None
                if scope is not None and nm:
                    table.setdefault(nm, []).append((scope, n.start_byte, ("param", n)))
        self._sites[key] = table
        return table

    def _site_class(self, site, f, depth):
        ctx = self.fctx(f)
        if site[0] == "unknown":
            return None
        if site[0] == "param":
            tn = site[1].child_by_field_name("type")
            return self._type_key(_plain_type_node(tn), ctx, _type_qual(tn))
        if site[0] == "decl":
            _k, n, d = site
            tn = n.child_by_field_name("type")
            tp = _plain_type_node(tn)
            if tp:
                return self._type_key(tp, ctx, _type_qual(tn))
            v = d.child_by_field_name("value") if d.type == "init_declarator" else None
            return self.expr_class(v, f, depth + 1) if v is not None else None
        loop = site[1]
        tn = loop.child_by_field_name("type")
        tp = _plain_type_node(tn)
        if tp:
            return self._type_key(tp, ctx, _type_qual(tn))
        el = self.container_elem(loop.child_by_field_name("right"), f, depth + 1)
        return self._elem_key(el[0], el[1]) if el else None

    def var_class(self, name, f, depth=0, at=None):
        """関数 f の中の名前 name の型のクラスの鍵（引数・ローカル変数〔auto の初期化子・範囲 for を含む〕・メンバー変数・
        ファイルスコープの変数）。決まらなければ None。"""
        if f is None or depth > 8:
            return None
        ctx = self.fctx(f)
        if name in self._site_table(f):
            # 関数の本体の中で宣言した名前: 出現から見える宣言（引数より内側）。見えなければ、引数でない限り決めない
            site = self._local_site(f, name, at)
            if site is not None:
                return self._site_class(site, f, depth)
            if at is None or name not in f.params:
                return None
        if name in f.params:
            return self._type_key(f.params[name].type, ctx, f.params[name].qual)
        if self.is_cpp_method(f):
            d, _ok = self.declaring(self.fcls(f), name)
            if d is not None:
                info = self.class_info(d)
                return self._type_key(info.members.get(name), info.ns + (info.name,), info.member_q.get(name, ()))
        t = self.file_var_types.get(self.rel(f.path), {}).get(name)
        if t:
            return self._type_key(t, ctx)
        ts = self.global_var_types.get(name) or ()
        return self._type_key(next(iter(ts)), ctx) if len(ts) == 1 else None

    def container_elem(self, n, f, depth=0):
        """範囲 for の対象の式 n の要素の型: (要素の型, 文脈) / None。"""
        if n is None or depth > 8:
            return None
        ctx = self.fctx(f)
        if n.type == "identifier":
            nm = txt(n)
            if nm in self._site_table(f):
                site = self._local_site(f, nm, n)
                if site is not None:
                    return (_elem_of_type(site[1].child_by_field_name("type")), ctx) if site[0] == "decl" else None
                if nm not in f.params:
                    return None
            if nm in f.params:
                return (f.params[nm].elem, ctx)
            if self.is_cpp_method(f):
                d, _ok = self.declaring(self.fcls(f), nm)
                if d is not None:
                    info = self.class_info(d)
                    return (info.member_elem.get(nm), info.ns + (info.name,))
            return None
        if n.type == "field_expression":
            arg, fld = n.child_by_field_name("argument"), n.child_by_field_name("field")
            owner = self.fcls(f) if (arg is not None and arg.type == "this") else self.expr_class(arg, f, depth + 1)
            if owner and fld is not None and self.class_info(owner) not in (None, AMBIGUOUS):
                d, _ok = self.declaring(owner, txt(fld))
                if d is not None:
                    info = self.class_info(d)
                    return (info.member_elem.get(txt(fld)), info.ns + (info.name,))
        return None

    def method_ret(self, cls, name):
        d, _ok = self.declaring(cls, name)
        if d is None:
            return None
        info = self.class_info(d)
        r = info.ret.get(name)
        if not r:
            return None
        return self._type_key(r[0], info.ns + (info.name,), r[1])

    def expr_class(self, n, f, depth=0):
        """式 n の型のクラスの鍵（決まらなければ None）。"""
        if n is None or depth > 8:
            return None
        t = n.type
        if t == "identifier":
            return self.var_class(txt(n), f, depth + 1, at=n)
        if t == "this":
            return self.fcls(f)
        if t in ("parenthesized_expression", "pointer_expression"):
            c = n.child_by_field_name("argument") if t == "pointer_expression" else None
            c = c if c is not None else (n.named_children[0] if n.named_children else None)
            return self.expr_class(c, f, depth + 1)
        if t == "qualified_identifier":
            # Base<M>::member_（基底クラスで修飾したメンバー変数）
            sc, nm = n.child_by_field_name("scope"), n.child_by_field_name("name")
            if sc is None or nm is None or nm.type != "identifier":
                return None
            owner = self.cls_key(self.resolve_type(_plain_type_name(sc)), self.fctx(f))
            if self.class_info(owner) in (None, AMBIGUOUS):
                return None
            d, _ok = self.declaring(owner, txt(nm))
            if d is None:
                return None
            info = self.class_info(d)
            if txt(nm) not in info.members:
                return None
            return self._type_key(info.members.get(txt(nm)), info.ns + (info.name,), info.member_q.get(txt(nm), ()))
        if t == "new_expression":
            tn = n.child_by_field_name("type")
            return self._type_key(_plain_type_node(tn), self.fctx(f), _type_qual(tn))
        if t == "subscript_expression":
            a = n.child_by_field_name("argument")
            el = self.container_elem(a, f, depth + 1)
            return self._elem_key(el[0], el[1]) if el else None
        if t == "field_expression":
            arg, fld = n.child_by_field_name("argument"), n.child_by_field_name("field")
            if fld is None:
                return None
            if txt(fld) in ("first", "second") and arg is not None and arg.type == "identifier" and f is not None:
                site = self._local_site(f, txt(arg), arg)
                if site is not None and site[0] == "range" and _plain_type_node(site[1].child_by_field_name("type")) is None:
                    el = self.container_elem(site[1].child_by_field_name("right"), f, depth + 1)
                    if el and el[0] and el[0][0] == "map":
                        kv = el[0][1] if txt(fld) == "first" else el[0][2]
                        return self._type_key(kv[0], el[1], kv[1])
            owner = self.fcls(f) if (arg is not None and arg.type == "this") else self.expr_class(arg, f, depth + 1)
            if owner and self.class_info(owner) not in (None, AMBIGUOUS):
                d, _ok = self.declaring(owner, txt(fld))
                if d is not None:
                    info = self.class_info(d)
                    if txt(fld) in info.members:
                        return self._type_key(info.members.get(txt(fld)), info.ns + (info.name,),
                                              info.member_q.get(txt(fld), ()))
            return None
        if t == "call_expression":
            fn = n.child_by_field_name("function")
            if fn is None:
                return None
            if fn.type == "field_expression":
                arg, fld = fn.child_by_field_name("argument"), fn.child_by_field_name("field")
                owner = self.fcls(f) if (arg is not None and arg.type == "this") else self.expr_class(arg, f, depth + 1)
                if owner and fld is not None and self.class_info(owner) not in (None, AMBIGUOUS):
                    return self.method_ret(owner, txt(fld))
                return None
            if fn.type in ("qualified_identifier", "template_function", "identifier"):
                inner, qual = fn, []
                while inner is not None and inner.type == "qualified_identifier":
                    sc = inner.child_by_field_name("scope")
                    if sc is not None:
                        qual.append(_plain_type_name(sc))
                    inner = inner.child_by_field_name("name")
                if inner is None:
                    return None
                if inner.type == "template_function":
                    nm = txt(inner.child_by_field_name("name"))
                    if nm in ("make_shared", "make_unique"):
                        args = inner.child_by_field_name("arguments")
                        a = args.named_children[0] if (args is not None and args.named_children) else None
                        return self._type_key(_plain_type_node(a), self.fctx(f), _type_qual(a))
                    return None
                nm = txt(inner)
                if qual:
                    sc = self.cls_key(self.resolve_type(qual[-1]), self.fctx(f), tuple(qual[:-1]))
                    if self.class_info(sc) not in (None, AMBIGUOUS):
                        return self.method_ret(sc, nm)
                elif self.is_cpp_method(f):
                    d, _ok = self.declaring(self.fcls(f), nm)
                    if d is not None:
                        return self.method_ret(d, nm)
                if self.is_class(nm):
                    return self.cls_key(nm, self.fctx(f), tuple(qual))
                rs = {(b, q, ns) for b, q, ns in self.free_ret.get(nm, ()) if b}
                if len({b for b, _q, _ns in rs}) == 1:
                    b, q, ns = next(iter(rs))
                    return self._type_key(b, ns, q)
            return None
        return None

    def resolve_type(self, name):
        """型の別名を深さ8までたどった素の型名。別名が別の型を指して決められなければ None。"""
        self._ensure_index()
        for _ in range(8):
            if name is None:
                return None
            v = self.aliases.get(name)
            if v is None:
                return name
            if v == AMBIGUOUS:
                return None
            name = v
        return None

    def _scan_text(self) -> None:
        """リポジトリの全 C/C++ ファイル（除外したファイルを含む）のテキストを走査する（構文解析はしない）。"""
        names, aliases, has_base, brace_typedefs, defines = set(), {}, {}, set(), {}
        dec = lambda b: b.decode("utf-8", "replace")   # noqa: E731
        for rel in MAC.iter_c_cxx_files(self.root):
            try:
                with open(os.path.join(self.root, rel), "rb") as fh:
                    src = fh.read()
            except OSError:
                continue
            for m in _CLASS_TEXT_RE.finditer(src):
                if _ENUM_BEFORE_TEXT_RE.search(src, max(0, m.start() - 16), m.start()):
                    continue   # `enum class 名前`・`enum struct 名前` は列挙型でクラスではない
                names.update(dec(w) for w in m.group(1).split())
            for m in _CLASS_DEF_TEXT_RE.finditer(src):
                nm = dec(m.group(1))
                has_base[nm] = has_base.get(nm, False) or m.group(2) == b":"
            for m in _USING_TEXT_RE.finditer(src):
                aliases.setdefault(dec(m.group(1)), []).append(dec(m.group(2)).strip())
            for m in _TYPEDEF_TEXT_RE.finditer(src):
                aliases.setdefault(dec(m.group(2)), []).append(dec(m.group(1)).strip())
            brace_typedefs.update(dec(m.group(1)) for m in _BRACE_TYPEDEF_TEXT_RE.finditer(src))
            for m in _DEFINE_IDENT_TEXT_RE.finditer(src):
                defines.setdefault(dec(m.group(1)), set()).add(dec(m.group(2)))
        self._text_defines = defines
        self._text_classes = names
        self._text_types = (aliases, has_base, brace_typedefs)

    def _text_class_names(self) -> set:
        """リポジトリの全 C/C++ ファイル（除外したファイルを含む）のテキストの `class 名前`・`struct 名前` の名前。"""
        if self._text_classes is None:
            self._scan_text()
        return self._text_classes

    def _text_type_defs(self):
        if self._text_types is None:
            self._scan_text()
        return self._text_types

    def outside_receiver(self, x, f, x_cls) -> bool:
        """出現 x（`obj.foo`／`obj->foo` の foo）の受け手 obj の型が、X と関係を持ちえないリポジトリの外の型か。
        obj の宣言の型を、型の別名（テキストの `using`・`typedef` のすべての定義）でたどった終端の型がすべて、クラスの索引に無く、
        X とその継承の連鎖の名前・テンプレート引数のどれでもなく、リポジトリのテキストに定義が無いか基底の句を持たない定義だけの型のとき真
        （`std::string`・`std::vector`・`std::function` 等。基底の句を持つ定義・本体つきの typedef の名前・`auto`・`decltype` は偽）。"""
        p = x.parent
        if p is None or p.type != "field_expression" or p.child_by_field_name("field") != x:
            return False
        arg = p.child_by_field_name("argument")
        if arg is None or arg.type != "identifier":
            return False
        t0 = self.var_type(txt(arg), f)
        if not t0 or t0 == "auto":
            return False
        aliases, has_base, brace_typedefs = self._text_type_defs()
        excluded = self._chain_names(x_cls) | {x_cls} | _template_param_names(x)
        todo, seen = [t0], set()
        while todo:
            t = todo.pop()
            if t in seen:
                continue
            seen.add(t)
            if len(seen) > 16:
                return False
            rhs = aliases.get(t, [])
            idx = self.aliases.get(t)
            if idx is not None and idx != AMBIGUOUS:
                rhs = rhs + [idx]
            if rhs:
                for r in rhs:
                    nt = _text_type_name(r)
                    if nt is None:
                        return False
                    todo.append(nt)
                continue
            if t in excluded or self.is_class(t) or t in brace_typedefs or has_base.get(t, False):
                return False
        return True

    def _chain_names(self, cls) -> set:
        """クラスの継承の連鎖の名前（索引に無い基底クラスの名前を含む）。"""
        seen, todo = set(), [cls]
        while todo:
            for info in self.classes.get(todo.pop(), ()):
                for b, _q in info.bases:
                    if b not in seen:
                        seen.add(b)
                        todo.append(b)
        return seen

    def _base_state(self, name, qualified) -> str:
        """基底クラスの状態: indexed（索引にあり一意）/ external（名前空間で修飾され、リポジトリのどこにも定義が無い）/
        unindexed（それ以外: テンプレート引数・同名のクラスが複数・除外したディレクトリのクラス等）。"""
        info = self.class_info(name)
        if info is not None and info != AMBIGUOUS:
            return "indexed"
        if info is None and qualified and name not in self._text_class_names():
            return "external"
        return "unindexed"

    def chain(self, name):
        """継承の連鎖: (索引にある祖先クラスの一覧, 索引に無い基底クラスがあるか, 外部のクラスがあるか)。"""
        if name in self._chain:
            return self._chain[name]
        ancestors, unindexed, external = [], False, False
        queue = [name]
        while queue:
            info = self.class_info(queue.pop(0))
            if info is None or info == AMBIGUOUS:
                continue
            for b, q in info.bases:
                st = self._base_state(b, q)
                if st == "indexed":
                    if b != name and b not in ancestors:
                        ancestors.append(b)
                        queue.append(b)
                elif st == "external":
                    external = True
                else:
                    unindexed = True
        self._chain[name] = (ancestors, unindexed, external)
        return self._chain[name]

    def declares(self, cname, member) -> bool:
        info = self.class_info(cname)
        return info is not None and info != AMBIGUOUS and (member in info.methods or member in info.members)

    def _partial(self, cname, member) -> bool:
        info = self.class_info(cname)
        return info is not None and info != AMBIGUOUS and member in info.partial

    def declaring(self, cname, member):
        """cname 自身またはその基底クラスのうち member を宣言した最も近いクラス。戻り値 (クラス or None, 決まったか)。
        途中で索引に無い基底クラスに当たる・cname が索引に無いか同名が複数なら (None, False)。継承の連鎖がすべて索引にあり、
        どこにも宣言が無ければ (None, True)。"""
        info = self.class_info(cname)
        if info is None or info == AMBIGUOUS:
            return None, False
        if self.declares(cname, member):
            return (None, False) if self._partial(cname, member) else (cname, True)
        level, seen = [cname], {cname}
        while level:
            nxt, found = [], []
            for c in level:
                for b, q in self.class_info(c).bases:
                    st = self._base_state(b, q)
                    if st == "unindexed":
                        return None, False
                    if st == "external" or b in seen:
                        continue
                    seen.add(b)
                    (found if self.declares(b, member) else nxt).append(b)
            if found:
                if len(set(found)) != 1 or self._partial(found[0], member):
                    return None, False
                return found[0], True
            level = nxt
        return None, True

    def method_virtual(self, cname, method):
        """クラス cname のメソッドの virtual: True（宣言の virtual・override・final、または索引にある基底クラスで virtual）/
        None（不明: 連鎖に外部のクラス・索引に無い基底クラスがあり指定子が無い）/ False。"""
        info = self.class_info(cname)
        if info is None or info == AMBIGUOUS:
            return None
        if info.methods.get(method):
            return True
        ancestors, unindexed, external = self.chain(cname)
        if any(self.class_info(a).methods.get(method) for a in ancestors):
            return True
        return None if (unindexed or external) else False

    def subclasses(self, cname) -> list:
        """索引にある cname の派生クラス（同名のクラスが複数ある名前を除く）。"""
        if self._subclasses is None:
            self._ensure_index()
            sub = {}
            for n, infos in self.classes.items():
                if len(infos) != 1:
                    continue
                for a in self.chain(n)[0]:
                    sub.setdefault(a, []).append(n)
            self._subclasses = sub
        return sorted(self._subclasses.get(cname, ()))

    def is_cpp_method(self, f) -> bool:
        """C++ のメソッド（宣言子の修飾子またはクラス本体のクラスが索引にある）。名前空間で修飾した自由関数は False。"""
        return f is not None and f.lang == "cpp" and f.is_method and self.is_class(self.fcls(f))

    def var_type(self, name, f):
        """関数 f の中の名前 name の宣言の素の型名（引数・ローカル変数・含むクラスのメンバー変数・ファイルスコープの変数）。"""
        if f is None:
            return None
        if name in f.params:
            return f.params[name].type
        if f.locs_cache is None:
            f.locs_cache = collect_locals(f)[0]
        if name in f.locs_cache:
            return f.locs_cache[name].type
        if self.is_cpp_method(f):
            d, _ok = self.declaring(self.fcls(f), name)
            if d is not None:
                return self.class_info(d).members.get(name)
        t = self.file_var_types.get(self.rel(f.path), {}).get(name)
        if t:
            return t
        ts = self.global_var_types.get(name) or ()
        return next(iter(ts)) if len(ts) == 1 else None

    def receiver(self, x, f, name):
        """出現 x（メソッド名・メンバー名）の受け手のクラス。戻り値: ("class", クラスの鍵) / ("free", None)〔メソッドの
        出現になりえない: 名前空間・列挙・`::` の修飾、修飾子・名前空間・列挙子の名前、自由関数の宣言、メソッドでない関数の中の
        修飾なしの出現、メソッドの本体の中の修飾なしの名前で、含むクラスの継承の連鎖がすべて索引にあり、どこにも宣言が無い〕/
        (None, None)〔決められない〕。"""
        x0 = x
        if any(a.type == "ERROR" for a in _ancestors(x0)):
            return None, None   # 構文解析の誤りの中は節の種類が誤りうるため決めない
        while x.parent is not None and x.parent.type in ("template_function", "dependent_name", "template_method") \
                and x.parent.child_by_field_name("name") in (x, None):
            x = x.parent
        p = x.parent
        if p is None:
            return None, None
        rel = self.rel(f.path) if f is not None else ""
        top = x
        while top.parent is not None:
            top = top.parent
        file_err = top.has_error
        ctx = None if file_err else (self.fctx(f) if f is not None else _ns_of(x, rel))
        # A: 修飾子・名前空間の名前・列挙子の宣言・using namespace
        if p.type == "qualified_identifier" and p.child_by_field_name("scope") == x:
            return "free", None
        if p.type in ("namespace_definition", "namespace_alias_definition", "nested_namespace_specifier",
                      "enumerator", "using_declaration") and p.child_by_field_name("value") != x:
            return "free", None
        if x0.type == "namespace_identifier":
            return "free", None
        if p.type == "qualified_identifier" and p.child_by_field_name("name") == x:
            scope = p.child_by_field_name("scope")
            if scope is None:
                return "free", None   # ::foo
            qual, a = [], p.parent
            while a is not None and a.type == "qualified_identifier":
                sc = a.child_by_field_name("scope")
                if sc is not None:
                    qual.insert(0, _plain_type_name(sc))
                a = a.parent
            sn = _plain_type_name(scope)
            y = self.resolve_type(sn)
            if y is None:
                return None, None
            key = self.cls_key(y, ctx, tuple(qual))
            if self.is_class(key):
                return "class", key
            if (sn in self.ns_names or sn in self.enum_names or sn == "std") and (
                    sn == "std" or sn not in self._text_class_names()):
                return "free", None
            return "class", key
        if p.type == "field_expression" and p.child_by_field_name("field") == x:
            arg = p.child_by_field_name("argument")
            if arg is not None and arg.type == "this":
                return self._implicit_receiver(f, name)
            if arg is not None and arg.type == "identifier":
                t = self.var_class(txt(arg), f, at=arg)
                return ("class", t) if t else (None, None)
            t = self.expr_class(arg, f) if f is not None else None   # E
            return ("class", t) if t else (None, None)
        if p.type == "field_initializer":
            k = self.fcls(f) if f is not None else None
            return ("class", k) if k else (None, None)
        for a in _ancestors(x):
            if a.type in ("compound_statement", "translation_unit"):
                break
            if a.type == "field_declaration_list":
                k = a.parent
                cname = _plain_type_node(k.child_by_field_name("name")) if k is not None else None
                if not cname:
                    return None, None
                return "class", self.cls_key(cname, None if file_err else
                                             _ns_of(k, rel) + _type_qual(k.child_by_field_name("name")))
        # B: 自由関数の宣言・定義の名前
        if p.type == "function_declarator" and p.child_by_field_name("declarator") == x and x.type == "identifier":
            return ("free", None) if not file_err else (None, None)
        if x0.type == "identifier":
            # B: メソッドでない関数の中の修飾なしの名前（this が無い）
            if not file_err and f is not None and f.lang == "cpp" and not self.is_cpp_method(f) and (
                    not f.is_method or (f.cls in self.ns_names and not self.is_class(f.cls)
                                        and f.cls not in self._text_class_names())):
                return "free", None
            return self._implicit_receiver(f, name)
        return None, None

    def _implicit_receiver(self, f, name):
        if not self.is_cpp_method(f):
            return None, None
        d, ok = self.declaring(self.fcls(f), name)
        if d is not None:
            return "class", d
        return ("free", None) if ok else (None, None)

    def class_relation(self, x_cls, status, c_cls, name, is_method=True) -> str:
        """エントリ `name[CLASS:x_cls]` と、受け手のクラス（receiver の結果）の関係から判定する（resolved / name-only /
        other-class）。偽陽性にするのは、継承の連鎖がすべて索引にあり関係が無いと決まったときだけ。"""
        if not self.is_class(x_cls) or status is None:
            return REL_NAME_ONLY
        if status == "free":
            return REL_OTHER
        if self.class_info(x_cls) == AMBIGUOUS or self.class_info(c_cls) in (None, AMBIGUOUS):
            return REL_NAME_ONLY
        if c_cls == x_cls:
            return REL_RESOLVED
        anc_c, un_c, _ext_c = self.chain(c_cls)
        anc_x, un_x, _ext_x = self.chain(x_cls)
        if x_cls in anc_c:
            d, _ok = self.declaring(c_cls, name)
            if d == x_cls:
                return REL_RESOLVED
            return REL_OTHER if d is not None else REL_NAME_ONLY
        if is_method and c_cls in anc_x:
            d, _ok = self.declaring(c_cls, name)
            v = self.method_virtual(d, name) if d is not None else None
            if v is True:
                return REL_RESOLVED
            if v is None:
                return REL_NAME_ONLY
        if un_c or un_x:
            return REL_NAME_ONLY
        return REL_OTHER

    def class_defs(self, fs, name, x_cls):
        """クラス x_cls を指定した要約に使う定義: x_cls から name を宣言した最も近いクラス D の定義と、name が D で
        virtual（不明を含む）なら x_cls の派生クラスの override。決まらなければ None（全定義に戻す）。"""
        if self.class_info(x_cls) in (None, AMBIGUOUS):
            return None
        d, _ok = self.declaring(x_cls, name)
        if d is None:
            return None
        chosen = [f for f in fs if f.lang == "cpp" and self.fcls(f) == d]
        if self.method_virtual(d, name) is not False:
            subs = set(self.subclasses(x_cls))
            chosen += [f for f in fs if f.lang == "cpp" and self.fcls(f) in subs]
        return chosen or None

    def is_static_def(self, f: Func) -> bool:
        """関数の定義が内部リンケージか（ヘッダ以外のファイルで、定義が static・無名名前空間、または
        同じファイルに static の前方宣言がある）。"""
        if is_header(f.path):
            return False
        if f.static_kw:
            return True
        if f.is_method:
            return False
        if self._index is None:
            self.build_index()
        return f.name in self.static_fwd.get(self.rel(f.path), ())

    def resolve_global(self, name, path):
        """ファイル `path` の中で、関数のローカル・引数でない名前 `name` が何を指すか。
        戻り値: ("file", ファイル, True) ＝ そのファイルの内部リンケージ／("extern", None, True) ＝ 外部から見える／
        ("file", ファイル, False) ＝ そのファイルの static でない定義（extern の宣言が見えない）／None ＝ 解決できない。"""
        if self._index is None:
            self.build_index()
        rel = self.rel(path)
        if lang_of(rel, self.h_as) == "python":
            return ("extern", None, True) if name in self.py_globals else None
        if rel in self.internal.get(name, ()):
            return ("file", rel, True)
        if name in self.visible:
            return ("extern", None, True)
        if name in self.file_decls.get(rel, ()):
            return ("file", rel, False)
        return None

    def file_internal(self, name, rel) -> bool:
        """ファイル `rel`（ヘッダ以外）の内部リンケージに `name` があるか。"""
        if self._index is None:
            self.build_index()
        return rel in self.internal.get(name, ())

    def defs(self, name):
        if self._index is None:
            self.build_index()
        out = []
        for rel, sb in self._index.get(name, []):
            sf = self.file(rel)
            for f in sf.funcs():
                if f.node.start_byte == sb:
                    out.append(f)
        return out

    def select_defs(self, name, caller=None):
        """呼び出し元のファイル `caller` から呼べる定義。戻り値: (定義のリスト, キャッシュの鍵の一部)。
        caller の static な定義があればそれだけ、無ければ static でない定義とヘッダの定義。
        caller が None、または絞った結果が0件なら全定義。"""
        fs = self.defs(name)
        if caller is None or not fs:
            return fs, "all"
        crel = self.rel(caller)
        own = [f for f in fs if self.rel(f.path) == crel and self.is_static_def(f)]
        if own:
            return own, crel
        rest = [f for f in fs if not self.is_static_def(f)]
        if rest:
            return rest, "non-static"
        return fs, "all"

    def macro(self, name):
        if self._macros is None:
            self.build_index()
        return self._macros.get(name)

    def is_function(self, name):
        if self._index is None:
            self.build_index()
        return name in self._index

    # 呼び出し先の要約（その関数が外部に与えうる影響。全入力が変化したと仮定）
    def ignored(self, name):
        return bool(self.ignore_re and name and self.ignore_re.fullmatch(name))

    def summary(self, name, depth=0, cls=None, caller=None):
        """呼び出し先 name の要約。cls（C++）はクラスの索引で、cls から name を宣言した最も近いクラス D の定義と
        （virtual なら）cls の派生クラスの override で要約する。決まらなければ全定義で要約し、`cls_fallback` を付ける。
        Python のメソッドは同じクラスの定義があればそれだけ、無ければ全定義。"""
        fs, sel = self.select_defs(name, caller)
        fallback = False
        if cls is not None and fs:
            if any(f.lang == "cpp" for f in fs):
                chosen = self.class_defs(fs, name, cls)
                if chosen is None:
                    fallback = True
                else:
                    fs = chosen
            else:
                same = [f for f in fs if f.cls == cls]
                if same:
                    fs = same
                else:
                    cls = None
        key = (name, cls, sel)
        if key in self._summ:
            return self._summ[key]
        if not fs:
            return None
        extra = {"cls_fallback": True} if fallback else {}
        if depth > self.max_depth:
            self.stats["depth_limit"] += 1
            return {"returns": True, "out": set(), "globals": set(), "name_only": set(),
                    "side": self.policy == "strict", "def_count": len(fs), **extra}
        self._summ[key] = {"returns": False, "out": set(), "globals": set(), "name_only": set(), "side": False,
                           "def_count": len(fs), **extra}
        acc = {"returns": False, "out": set(), "globals": set(), "name_only": set(), "side": False,
               "closure": set(), "def_count": len(fs), **extra}
        for f in fs:
            r = analyze_function(f, self, seeds=None, depth=depth + 1)
            acc["closure"] |= r.closure
            acc["returns"] |= r.returns
            acc["out"] |= r.out
            acc["globals"] |= r.globals
            acc["name_only"] |= r.name_only
            acc["side"] |= r.side
        self._summ[key] = acc
        return acc


def _py_module_level(node) -> bool:
    """Python の関数定義がモジュールのトップレベル（デコレータ付きを含む）か。"""
    p = node.parent
    if p is not None and p.type == "decorated_definition":
        p = p.parent
    return p is not None and p.type == "module"


# ---------------------------------------------------------------------------
# 関数内スライス本体
# ---------------------------------------------------------------------------

@dataclass
class Result:
    escapes: list = field(default_factory=list)   # [(kind, detail, line)]
    affected_units: int = 0
    total_units: int = 0
    has_error: bool = False
    fp_calls: list = field(default_factory=list)  # 影響を受けた関数ポインタ経由の呼び出し [(line, text)]
    name_only: set = field(default_factory=set)   # global の出口のうち、extern の宣言が見えない名前（Repo.resolve_global の手順3）

    @property
    def returns(self):
        return any(k == "return" for k, _, _ in self.escapes)

    @property
    def out(self):
        return {d for k, d, _ in self.escapes if k == "out"}

    @property
    def globals(self):
        return {d for k, d, _ in self.escapes if k == "global"}

    @property
    def closure(self):
        return {d for k, d, _ in self.escapes if k == "closure"}

    @property
    def side(self):
        return any(k in ("heap", "state", "unknown", "exception") for k, _, _ in self.escapes)

    @property
    def push_up(self):
        return any(k in UP_KINDS for k, _, _ in self.escapes)


def classify_write(root, kind, via, f: Func, locs, py_globals, fld=None, repo=None):
    """書き込み1つの出口。global の書き込み先は、書き込んだ関数のファイルから見える宣言で解決する:
    外部から見える名前は `g`、そのファイルの内部リンケージは `g[FILE:path]`、extern の宣言が見えない
    static でない定義は `g[FILE:path]`（3つ目の要素 True＝名前の一致のみ）、見える宣言が無い名前（マクロで宣言した
    ローカル変数等）は unknown（呼び出し元へ）。C++ のメソッド（クラスが索引にある）の中で、含むクラスまたはその基底クラス B の
    メンバー変数への書き込み（暗黙の this・`this->m`・型の分かる `obj.m`）は `m[CLASS:B]`（B が同名で複数なら名前の一致のみ）。
    それ以外の C++ のメソッドの global は暗黙の this のメンバーと区別できないため、名前の一致のみとする。"""
    out = _classify_write(root, kind, via, f, locs, py_globals, fld)
    if repo is None:
        return out
    res = []
    if repo.is_cpp_method(f) and fld and root is not None and (root == "this" or root in f.params or root in locs):
        # C++ のメソッドの中の this->m・obj.m（obj の宣言の型がクラス）への書き込み: 今の出口に加えて、メンバーの読み手を追う
        # （C の構造体・名前空間の自由関数の中の書き込みは P2 の扱いのまま）
        owner = repo.fcls(f) if root == "this" else (
            repo.var_class(root, f) or repo.cls_key(repo.resolve_type(repo.var_type(root, f)), repo.fctx(f)))
        e = _member_entry(repo, owner, fld)
        if e is not None:
            res.append(e)
    member_like = f.lang == "cpp" and f.is_method
    for k, d in out:
        if k != "global":
            res.append((k, d))
            continue
        if repo.is_cpp_method(f):
            e = _member_entry(repo, repo.fcls(f), d.split(".")[0])
            if e is not None:
                res.append(e)
                continue
        hit = repo.resolve_global(d.split(".")[0], f.path)
        if hit is None:
            res.append(("unknown", f"undeclared {d}"))
        elif hit[0] == "extern":
            res.append(("global", d, member_like))
        else:
            res.append(("global", f"{d}[FILE:{hit[1]}]", member_like or not hit[2]))
    return res


def _member_entry(repo, owner, name):
    """クラス owner（またはその基底クラス）のメンバー変数 name への書き込みの出口 ("global", "name[CLASS:B]", 名前の一致のみ)。
    メンバー変数と決まらなければ None。"""
    if not owner or not repo.is_class(owner):
        return None
    d, _ok = repo.declaring(owner, name)
    if d is None:
        return None
    info = repo.class_info(d)
    if name not in info.members:
        return None
    return ("global", f"{name}[CLASS:{d}]", repo.class_info(d) == AMBIGUOUS)


def _classify_write(root, kind, via, f: Func, locs, py_globals, fld=None):
    g = f"{root}.{fld}" if (fld and root) else root
    if root is None:
        return [("unknown", "write-through-expression")]
    if f.lang == "python":
        if root in f.params:
            return [("out", f.params[root].idx)] if kind != "var" else []
        if root in py_globals:
            return [("global", g)]
        if root not in locs and root in getattr(f, "outer", ()):
            return [("closure", root)]
        if root in locs:
            return [] if (kind == "var" or locs[root].fresh) else [("heap", root)]
        return [("global", g)] if kind != "var" else []
    if kind == "member":
        return [("out", "this")]
    if root in f.params:
        P = f.params[root]
        if kind == "var":
            return [("out", P.idx)] if P.ref else []
        if via is True or via == "index":
            return [("out", P.idx)] if (P.ptr or P.ref or via is True) else []
        return [("out", P.idx)] if P.ref else []
    if root in locs:
        L = locs[root]
        if L.static:
            return [("state", root)]
        if kind == "var":
            return [("heap", root)] if L.ref else []
        if via is True:
            return [("heap", root)]
        if via == "index":
            return [] if (L.array and not L.ptr) else [("heap", root)]
        return [("heap", root)] if L.ref else []
    if f.lang == "cpp" and f.is_method:
        return [("global", g), ("out", "this")]
    return [("global", g)]


def _callee(call, lang):
    fn = call.child_by_field_name("function")
    if fn is None:
        return None, None
    t = fn.type
    if t == "identifier":
        return txt(fn), None
    if lang == "python" and t == "attribute":
        return txt(fn.child_by_field_name("attribute")), fn.child_by_field_name("object")
    if t == "field_expression":
        fl = fn.child_by_field_name("field")
        return (txt(fl) if fl is not None else None), fn.child_by_field_name("argument")
    if t in ("qualified_identifier", "template_function"):
        return txt(fn).split("::")[-1].split("<")[0], None
    return None, None


def _callee_name_node(call):
    """呼び出しの関数名の識別子の節（`foo`・`obj.foo`・`X::foo`・`foo<T>` の foo）。"""
    fn = call.child_by_field_name("function")
    for _ in range(6):
        if fn is None:
            return None
        t = fn.type
        if t in ("identifier", "field_identifier"):
            return fn
        if t == "field_expression":
            fn = fn.child_by_field_name("field")
        elif t in ("qualified_identifier", "template_function", "template_method"):
            fn = fn.child_by_field_name("name")
        else:
            return None
    return None


def _union_summaries(parts):
    """要約の和（None を除く）。1つも無ければ None。"""
    parts = [x for x in parts if x]
    if not parts:
        return None
    acc = {"returns": False, "out": set(), "globals": set(), "name_only": set(), "side": False, "closure": set()}
    for x in parts:
        acc["returns"] |= bool(x.get("returns"))
        acc["side"] |= bool(x.get("side"))
        for k in ("out", "globals", "name_only", "closure"):
            acc[k] |= set(x.get(k) or ())
    return acc


def _args(call, lang):
    al = call.child_by_field_name("arguments")
    if al is None:
        return [], {}
    pos, kw = [], {}
    for c in al.named_children:
        if c.type == "comment":
            continue
        if lang == "python" and c.type == "keyword_argument":
            kw[txt(c.child_by_field_name("name"))] = c.child_by_field_name("value")
        else:
            pos.append(c)
    return pos, kw


def _ids(n):
    return {txt(x) for x in walk(n) if x.type == "identifier"} if n is not None else set()


def _is_function_pointer_call(call, f: Func, repo, locs) -> bool:
    """C / C++ の呼び出しが関数ポインタ経由か（呼び出し先の名前で定義を引けない形）。"""
    if f.lang == "python":
        return False
    fn = call.child_by_field_name("function")
    if fn is None:
        return False
    t = fn.type
    if t in ("parenthesized_expression", "pointer_expression", "subscript_expression", "call_expression"):
        return True
    if t == "identifier":
        nm = txt(fn)
        if nm in f.params or nm in locs:
            return True
        return bool(repo is not None and f.lang == "c" and nm in repo.file_scope_names
                    and not repo.is_function(nm) and repo.macro(nm) is None)
    if t == "field_expression" and f.lang == "c" and repo is not None:
        fl = fn.child_by_field_name("field")
        nm = txt(fl) if fl is not None else None
        return bool(nm and not repo.is_function(nm) and repo.macro(nm) is None
                    and nm not in PURE["c"] and nm not in WRITERS["c"])
    return False


def _callee_globals(summ):
    """呼び出し先の要約の globals のうち、呼び出し元の出口に加えるもの。メンバー変数 `m[CLASS:B]` は加えない
    （送るのはヒットした関数の中の直接の書き込みだけ。呼び出し先の中のメンバーの変化は out(this)・受け手への書き込みで伝わる）。"""
    no = summ.get("name_only") or ()
    return [("global", g, g in no) for g in summ.get("globals", ()) if _entry_scope_kind(g) != SCOPE_CLASS]


def call_effects(call, f: Func, repo: Repo, locs, py_globals, seed_summ, depth):
    """影響を受けた呼び出し1つが、呼び出し元の外へ出す影響。"""
    lang = f.lang
    name, recv = _callee(call, lang)
    if repo is not None and repo.ignored(name):
        return [], []
    pos, kw = _args(call, lang)
    if name == "__xddp_iter":
        w = []
        for a in pos:
            w += lvals(a, lang) if a.type != "pointer_expression" else arg_written(a, lang)
        return [], w
    esc = []
    writes = []   # (root, kind, via, field)

    self_recv = recv is not None and recv.type in ("identifier", "this") and \
        txt(recv) in ("self", "cls", "this")
    module_recv = lang == "python" and recv is not None and recv.type == "identifier" and \
        txt(recv) in load(f.path, lang).py_imports() and txt(recv) not in locs
    status, c_cls = (None, None)
    if lang == "cpp" and repo is not None and name is not None and not module_recv:
        x = _callee_name_node(call)
        if x is not None:
            status, c_cls = repo.receiver(x, f, name)
    class_keys = [k for k in seed_summ if k.startswith(name + "[CLASS:")] if (name and lang == "cpp") else []
    d_cls = repo.declaring(c_cls, name)[0] if (status == "class" and repo.class_info(c_cls) not in (None, AMBIGUOUS)) \
        else None
    if module_recv:
        summ = None   # import したモジュールの関数（リポジトリのメソッドではない）
    elif d_cls is not None:
        # 受け手のクラス C と、C から name を宣言した最も近いクラス D が決まった: D と（virtual なら）C の派生クラスの override
        targets = [d_cls]
        if repo.method_virtual(d_cls, name) is not False:
            targets += [k for k in repo.subclasses(c_cls) if repo.declares(k, name)]
        parts = [seed_summ.get(f"{name}[CLASS:{k}]") for k in targets]
        if any(x_ is None for x_ in parts):
            parts.append(repo.summary(name, depth, cls=c_cls, caller=f.path))
        summ = _union_summaries(parts)
    elif class_keys:
        # 決まらない: 波の素名の要約と全クラスの要約の和に、全定義の要約を加える（波には一部のクラスの分しか無いため）
        parts = ([seed_summ[name]] if name in seed_summ else []) + [seed_summ[k] for k in class_keys]
        parts.append(repo.summary(name, depth, caller=f.path) if repo is not None else None)
        summ = _union_summaries(parts)
    elif name is not None and name in seed_summ:
        summ = seed_summ[name]
    elif (recv is not None and not self_recv and lang in ("python", "cpp") and
          (name in PURE.get(lang, ()) or name in WRITERS.get(lang, {}))):
        summ = None   # 言語標準のメソッド名は標準ライブラリとして扱う（下の外部処理へ）
    else:
        summ = repo.summary(name, depth, cls=f.cls if (self_recv and lang == "python") else None, caller=f.path) \
            if (name and repo is not None) else None
    if summ is None and name and lang != "python" and repo is not None:
        mac = repo.macro(name)
        if mac is not None:
            params, body = mac
            for i, p in enumerate(params):
                if i < len(pos) and re.search(
                        r"(\(\s*%s\s*\)|\b%s\b)\s*(\+\+|--|[-+*/%%&|^]?=(?!=)|<<=|>>=)" %
                        (re.escape(p), re.escape(p)), body) or \
                        (i < len(pos) and re.search(
                            r"((\+\+|--)\s*\(?\s*%s\b|(^|[(,]\s*)&\s*\(?\s*%s\b)"
                            % (re.escape(p), re.escape(p)), body)):
                    writes += lvals(pos[i], lang) if pos[i].type != "pointer_expression" \
                        else arg_written(pos[i], lang)
            for inner in set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", body)) - set(params) - {name} \
                    - _C_KEYWORDS:
                if repo.ignored(inner):
                    continue
                s2 = repo.summary(inner, depth + 1, caller=f.path)
                if s2 is not None:
                    esc += _callee_globals(s2)
                    if s2["side"]:
                        esc.append(("unknown", f"macro {name}->{inner}"))
            return esc, writes
    if summ is not None:
        shift = 0
        if lang == "python" and recv is not None:
            fs = repo.defs(name) if repo is not None else []
            shift = 1 if any(x.shift for x in fs) else 0
        for o in summ["out"]:
            if o == "this" or (lang == "python" and shift and o == 0):
                if recv is not None:
                    writes += recv_written(call, recv, lang)
                elif lang == "cpp" and status == "class" and repo.is_cpp_method(f):
                    writes.append(("this", "member", True, None))   # this を省いたメソッドの呼び出し: 呼び出し元の this
                continue
            i = o - shift if isinstance(o, int) else None
            if i is not None and 0 <= i < len(pos):
                writes += arg_written(pos[i], lang)
            elif i is not None and lang == "python":
                for a in kw.values():
                    writes += arg_written(a, lang)
        esc += _callee_globals(summ)
        writes += [(c, "var", False, None) for c in summ.get("closure", ())]
        if summ["side"]:
            esc.append(("unknown", f"call {name}"))
        return esc, writes
    # 外部（定義なし）
    if name in PURE.get(lang, ()):
        return esc, writes
    wr = WRITERS.get(lang, {}).get(name)
    if wr:
        for i in wr:
            if i == "recv":
                if recv is not None:
                    writes += recv_written(call, recv, lang)
            elif i < len(pos):
                writes += arg_written(pos[i], lang)
        return esc, writes
    if repo is not None and repo.policy == "strict":
        repo.stats["external_unknown"] += 1
        esc.append(("unknown", f"external {name}"))
    else:
        if repo is not None:
            repo.stats["external_assumed_pure"] += 1
        for a in pos:
            if lang != "python" and a.type == "pointer_expression" and a.children \
                    and a.children[0].type == "&":
                writes += arg_written(a, lang)
    return esc, writes


def _add_escape(res: Result, e, line) -> None:
    """出口 (種類, 詳細[, 名前の一致のみ]) を res に加える。"""
    res.escapes.append((e[0], e[1], line))
    if len(e) > 2 and e[2]:
        res.name_only.add(e[1])


def analyze_function(f: Func, repo: Repo | None, seeds=None, seed_summ=None, depth=0,
                     extra_taint=(), return_type_hit=False):
    """seeds=None なら全文が影響を受けたと仮定（呼び出し先の要約用）。
    seeds: 影響の起点となる識別子ノードの集合（start_byte の集合）。"""
    seed_summ = seed_summ or {}
    units = UnitBuilder(f).build()
    locs, py_globals = collect_locals(f)
    res = Result(total_units=len(units))
    res.has_error = any(u.has_error for u in units)
    A = set()
    # 汚染名 -> 最初に汚染された位置（バイト）。流れ依存の近似: 定義より後ろの使用、
    # または定義と同じループ内の使用だけを影響ありとする（goto がある関数は全体をループ扱い）
    T: dict[str, set] = {}
    for k_, p_ in extra_taint:
        T.setdefault(k_, set()).add(p_)
    forced_from = None
    loops, excl, exits = [], [], []
    for n in walk(f.body):
        t = n.type
        if t in ("for_statement", "while_statement", "do_statement", "for_range_loop"):
            loops.append((n.start_byte, n.end_byte))
        elif t == "if_statement":
            c_ = n.child_by_field_name("consequence")
            for alt in n.children_by_field_name("alternative"):
                if c_ is not None:
                    excl.append((c_.start_byte, c_.end_byte, alt.start_byte, alt.end_byte))
        if t in ("compound_statement", "block"):
            kids = [k for k in n.named_children if k.type != "comment"]
            if kids and kids[-1].type in ("return_statement", "throw_statement", "raise_statement"):
                exits.append((n.start_byte, n.end_byte))
    if any(u.kind == "goto" for u in units):
        loops.append((f.body.start_byte, f.body.end_byte))
        exits = []

    def taint(name, pos):
        if not name:
            return False
        ps = T.setdefault(name, set())
        if pos in ps:
            return False
        ps.add(pos)
        return True

    def _reach1(p0, pos):
        if p0 < 0:
            return True
        if any(a <= p0 < b and a <= pos < b for a, b in loops):
            return True
        if p0 >= pos:
            return False
        if any(a <= p0 < b and not (a <= pos < b) for a, b in exits):
            return False   # return で終わるブロック内の定義は、ブロックの外へ届かない
        if any(ca <= p0 < cb and aa <= pos < ab for ca, cb, aa, ab in excl):
            return False   # if の then 側の定義は else 側へ届かない
        return True

    def reaches(name, pos):
        return any(_reach1(p0, pos) for p0 in T.get(name, ()))

    def uses_tainted(names, pos):
        return any(reaches(n, pos) for n in names)

    def unit_has_seed(u):
        for nd in u.nodes:
            for x in walk(nd):
                if x.start_byte in seeds and x.type in SEED_TYPES:
                    return True
        return False

    if seeds is None:
        A = {u.id for u in units}
        for u in units:
            for d in u.defs:
                taint(d[0], -1)
    else:
        for u in units:
            if unit_has_seed(u):
                A.add(u.id)
                for d in u.defs:
                    taint(d[0], u.start)

    def ctl_affected(u):
        return any(c in A for c in u.controls) or (forced_from is not None and u.start > forced_from)

    changed = True
    while changed:
        changed = False
        for u in units:
            if u.id in A:
                for d in u.defs:
                    changed |= taint(d[0], u.start)
                continue
            if uses_tainted(u.uses, u.start) or ctl_affected(u):
                A.add(u.id)
                for d in u.defs:
                    taint(d[0], u.start)
                changed = True
        for u in units:
            if u.id in A and u.kind in ("jump", "ret", "raise", "goto") and \
                    (ctl_affected(u) or u.kind == "goto"):
                pos = -1 if u.kind == "goto" else u.start
                if forced_from is None or pos < forced_from:
                    forced_from = pos
                    changed = True

    res.affected_units = len(A)
    if return_type_hit:
        res.escapes.append(("return", "return-type", f.node.start_point[0] + 1))
    grew = False
    for u in units:
        if u.id not in A:
            continue
        line = (u.nodes[0].start_point[0] + 1) if u.nodes else 0
        if u.kind == "ret" and u.value_return:
            res.escapes.append(("return", f.name, line))
        if u.kind == "raise":
            res.escapes.append(("exception", f.name, line))
        # 入れ子の関数/クラス定義そのものは副作用を持たない（中身は呼び出し時に要約で評価）
        for r, k, v, fl in u.defs:
            for e in classify_write(r, k, v, f, locs, py_globals, fl, repo):
                _add_escape(res, e, line)
        ca = ctl_affected(u) or seeds is None
        for call in u.calls:
            if not ca:
                pos, kw = _args(call, f.lang)
                _, recv = _callee(call, f.lang)
                tainted = set()
                for a in pos + list(kw.values()) + ([recv] if recv is not None else []):
                    tainted |= _ids(a)
                fn = call.child_by_field_name("function")
                is_seed_call = seeds is not None and fn is not None and any(
                    x.start_byte in seeds for x in walk(fn))
                seed_in_args = seeds is not None and any(
                    x.start_byte in seeds for a in pos + list(kw.values()) for x in walk(a))
                if not (uses_tainted(tainted, u.start) or is_seed_call or seed_in_args):
                    continue
            if seeds is not None and _is_function_pointer_call(call, f, repo, locs):
                res.fp_calls.append((call.start_point[0] + 1, txt(call)[:80]))
            esc, writes = call_effects(call, f, repo, locs, py_globals, seed_summ, depth)
            for e in esc:
                _add_escape(res, e, line)
            for r, k, v, fl in writes:
                grew |= taint(r, u.start)
                for e in classify_write(r, k, v, f, locs, py_globals, fl, repo):
                    _add_escape(res, e, line)
    # 呼び出しによる書き込みで汚染が増えた場合は、その汚染を初期値として再計算する
    if grew and seeds is not None:
        return analyze_function(f, repo, seeds=seeds, seed_summ=seed_summ, depth=depth,
                                extra_taint=tuple((k_, p_) for k_, ps in T.items() for p_ in ps),
                                return_type_hit=return_type_hit)
    return res


# ---------------------------------------------------------------------------
# ヒット1件の判定（slice）
# ---------------------------------------------------------------------------

@dataclass
class HitVerdict:
    status: str                  # fp / self-def / file-scope / sliced / write-only
    func: Func | None = None
    push_up: bool = False
    push_values: set = field(default_factory=set)
    escapes: list = field(default_factory=list)
    result: Result | None = None
    note: str = ""
    identity: str | None = None    # `[CLASS:…]` のエントリで受け手のクラスから決めた同一性（それ以外は None）


def _nodes_on_line(root, row):
    stack = [root]
    while stack:
        x = stack.pop()
        if x.end_point[0] < row or x.start_point[0] > row:
            continue
        yield x
        stack.extend(x.children)


def judge_hit(repo: Repo, rel, line_no, symbol, seed_summ=None, entry=None, kind=None, is_seed=False):
    """ヒット1件の判定。`entry` は検索したエントリ文字列（`x` / `x[FILE:p]` / `x[MEDIUM:p]` / `x[CLASS:X]`）、`kind` は
    検索したシンボルの種類（function / value / variable / macro。分からなければ None）、`is_seed` はその波のシードか。
    `x[CLASS:X]` のエントリは出現ごとに受け手のクラスを決め、X と関係の無いクラスの出現を偽陽性（other-class）にする。"""
    ctx = {}
    v = _judge_hit(repo, rel, line_no, symbol, seed_summ, entry, kind, is_seed, ctx)
    if v.status != "fp" and "identity" in ctx:
        v.identity = ctx["identity"]
    return v


def _judge_hit(repo: Repo, rel, line_no, symbol, seed_summ, entry, kind, is_seed, ctx):
    sf = repo.file(rel)
    row = line_no - 1
    if _other_static(repo, rel, symbol, entry, is_seed):
        return HitVerdict("fp", note="other-static")
    x_cls = repo.entry_class(_parse_entry(entry)[1]) if (entry and _entry_scope_kind(entry) == SCOPE_CLASS) else None
    occ_all = [x for x in find_occurrences(sf, row, symbol) if not foreign_module_attr(repo, sf, x, symbol)]
    occ, reasons = [], []
    for x in occ_all:
        why = _excluded_occurrence(sf, x, symbol, kind, class_entry=x_cls is not None)
        if why:
            reasons.append(why)
        else:
            occ.append(x)
    if x_cls is not None and occ:
        kept, rels = [], []
        for x in occ:
            if kind == "function" and _not_method_occurrence(sf, x, symbol):
                reasons.append(LV.NOTE_OTHER_CLASS)
                continue
            fx = sf.func_at(x)
            status, c_cls = repo.receiver(x, fx, symbol)
            r = repo.class_relation(x_cls, status, c_cls, symbol, is_method=kind not in VALUE_KIND_NAMES)
            if r == REL_NAME_ONLY and repo.outside_receiver(x, fx, x_cls):
                r = REL_OTHER
            if r == REL_OTHER:
                reasons.append(LV.NOTE_OTHER_CLASS)
            else:
                kept.append(x)
                rels.append(r)
        occ = kept
        ctx["identity"] = IDENTITY_RESOLVED if REL_RESOLVED in rels else IDENTITY_NAME_ONLY
    if occ_all and not occ:
        return HitVerdict("fp", note=",".join(sorted(set(reasons))))
    if not occ:
        # マクロ本体（#define X ... symbol ...）。置き換えたマクロ（名前空間マクロ・宣言を飾るマクロ）の名前は送らない
        for x in _nodes_on_line(sf.root, row):
            if x.type == "preproc_arg" and re.search(r"\b%s\b" % re.escape(symbol), txt(x)):
                d = x.parent
                nm = d.child_by_field_name("name") if d is not None else None
                if nm is not None and txt(nm) != symbol:
                    if sf.lang in ("c", "cpp") and txt(nm) in repo.neutral():
                        return HitVerdict("file-scope", note="macro-def")
                    return HitVerdict("file-scope", push_values={txt(nm)}, note="macro-def")
                return HitVerdict("file-scope", note="declaration")
        # 置き換えたマクロ自体の出現（前処理後の木には無い）。元のテキストでコメント・文字列の外に出現があれば関係あり
        if sf.lang in ("c", "cpp") and symbol in repo.neutral():
            directive, in_code = MAC.line_has_code_occurrence(sf.lexed(), line_no, symbol)
            if not directive and in_code:
                return HitVerdict("file-scope", note=LV.NOTE_NEUTRALIZED_MACRO)
        return HitVerdict("fp", note="comment/string/include")
    o = occ[0]
    f = sf.func_at(o)
    if f is None:
        return _file_scope(sf, o, symbol)
    is_value = not (seed_summ and summary_key(entry or symbol) in seed_summ)
    if is_value and all(_write_only(x, sf.lang) for x in occ):
        return HitVerdict("write-only", func=f, note="value overwritten, not read")
    seeds = {x.start_byte for x in occ}
    # 関数ヘッダ内のヒット
    if o.start_byte < f.body.start_byte:
        if sf.lang == "python":
            nm = f.node.child_by_field_name("name")
            if nm is not None and nm.start_byte == o.start_byte:
                return HitVerdict("self-def", func=f)
        d = f.node.child_by_field_name("declarator")
        name_node = None
        if d is not None:
            for x in walk(d):
                if x.type in ("identifier", "field_identifier") and txt(x) == f.name:
                    name_node = x
                    break
        if name_node is not None and name_node.start_byte == o.start_byte:
            return HitVerdict("self-def", func=f)
        taint = set()
        in_params = False
        for a in _ancestors(o):
            if a.type in ("parameter_declaration", "typed_parameter", "default_parameter",
                          "typed_default_parameter"):
                in_params = True
                dd = a.child_by_field_name("declarator") or a.child_by_field_name("name")
                if dd is not None:
                    nm, *_ = c_decl(dd) if sf.lang != "python" else (txt(dd),)
                    if nm:
                        taint.add(nm)
                break
        r = analyze_function(f, repo, seeds=set(), seed_summ=seed_summ,
                             extra_taint=tuple((t, -1) for t in taint),
                             return_type_hit=not in_params)
    else:
        r = analyze_function(f, repo, seeds=seeds, seed_summ=seed_summ)
    v = HitVerdict("sliced", func=f, result=r, escapes=r.escapes)
    v.push_up = r.push_up
    v.push_values = r.globals
    return v


def _text_type_name(text):
    """型のテキスト（`std::basic_string<char>`・`const T &` 等）の素の型名。`decltype` 等で決められなければ None。"""
    if "decltype" in text or "typeof" in text:
        return None
    text = re.sub(r"\b(const|volatile|typename|struct|class|union|enum)\b", " ", text.split("<")[0])
    ids = re.findall(r"[A-Za-z_]\w*", text.replace("*", " ").replace("&", " "))
    return ids[-1] if ids else None


def _template_param_names(x) -> set:
    """出現 x を囲むテンプレートの型引数の名前。"""
    names = set()
    for a in _ancestors(x):
        if a.type == "template_declaration":
            ps = a.child_by_field_name("parameters")
            for c in (ps.named_children if ps is not None else ()):
                names.update(txt(y) for y in walk(c) if y.type == "type_identifier")
    return names


_DECL_WRAPPERS = ("pointer_declarator", "reference_declarator", "array_declarator", "parenthesized_declarator")


def _not_method_occurrence(sf, x, symbol) -> bool:
    """メソッドのエントリ（種類 function の `[CLASS:…]`）の出現 x が、メソッドではなく変数・引数の名前か:
    引数の宣言子・変数の宣言子（ローカル・メンバー・ファイルスコープ）、同じ名前の引数・ローカル変数のある関数の中の素の出現、
    呼ばずに参照する `obj.m`（呼び出しの関数の位置でも `&` の対象でもない。データメンバー）。"""
    if _is_param_name(sf, x):
        return True
    n, p = x, x.parent
    while p is not None and p.type in _DECL_WRAPPERS and p.child_by_field_name("declarator") == n:
        n, p = p, p.parent
    if p is not None and p.type == "init_declarator" and p.child_by_field_name("declarator") == n:
        return True
    if p is not None and p.type in ("declaration", "field_declaration") and \
            any(c == n for c in p.children_by_field_name("declarator")):
        return True
    if _is_bare_occurrence(x) and _is_shadowed(sf, x, symbol):
        return True
    p = x.parent
    if p is not None and p.type == "field_expression" and p.child_by_field_name("field") == x:
        g = p.parent
        called = g is not None and g.type == "call_expression" and g.child_by_field_name("function") == p
        return not called and not (g is not None and g.type == "pointer_expression")
    return False


def _other_static(repo: Repo, rel, symbol, entry, is_seed) -> bool:
    """修飾なしのエントリのヒットが、ヒットしたファイル自身の内部リンケージ（別物の static）の名前か。
    そのファイルに同名の外部リンケージの定義（関数・メソッド・変数）もあれば別物と決められないため偽にする。"""
    if is_seed or (entry is not None and entry != symbol):
        return False
    root = symbol.split(".")[0]
    return repo.file_internal(root, rel) and root not in repo.ext_defs_in_file.get(rel, ())


_PARAM_DECLS = ("parameter_declaration", "optional_parameter_declaration")
_PY_PARAM_LISTS = ("parameters", "lambda_parameters")


def _is_member_name(sf, x) -> bool:
    """出現 x が構造体のメンバー名・属性名か（C: field_identifier、Python: import 名から始まらない属性の名前）。"""
    if sf.lang == "c":
        return x.type == "field_identifier"
    if sf.lang != "python":
        return False
    p = x.parent
    if p is None or p.type != "attribute" or p.child_by_field_name("attribute") != x:
        return False
    obj = p.child_by_field_name("object")
    while obj is not None and obj.type == "attribute":
        obj = obj.child_by_field_name("object")
    return not (obj is not None and obj.type == "identifier" and txt(obj) in sf.py_imports())


def _is_param_name(sf, x) -> bool:
    """出現 x が引数の宣言子の名前そのものか（既定値の式の中は含めない）。"""
    if sf.lang == "python":
        p = x.parent
        if p is None or x.type != "identifier":
            return False
        if p.type in _PY_PARAM_LISTS:
            return True
        if p.type in ("default_parameter", "typed_default_parameter"):
            return p.child_by_field_name("name") == x
        if p.type == "typed_parameter":
            first = next((c for c in p.named_children if c.type == "identifier"), None)
            return first == x
        if p.type in ("list_splat_pattern", "dictionary_splat_pattern"):
            return p.parent is not None and p.parent.type in _PY_PARAM_LISTS
        return False
    for a in _ancestors(x):
        if a.type in _PARAM_DECLS:
            d = a.child_by_field_name("declarator")
            if d is None or not (d.start_byte <= x.start_byte and x.end_byte <= d.end_byte):
                return False
            nm, *_ = c_decl(d)
            return nm == txt(x)
        if a.type in ("compound_statement", "function_definition", "translation_unit", "field_declaration_list"):
            return False
    return False


def _is_shadowed(sf, x, symbol) -> bool:
    """出現 x を含む関数に、シンボル（root.field は根の名前）と同じ名前のローカル変数・引数があるか。"""
    f = sf.func_at(x)
    if f is None:
        return False
    root = symbol.split(".")[0]
    if root in f.params:
        return True
    locs, _ = collect_locals(f)
    return root in locs


def _is_bare_occurrence(x) -> bool:
    """出現 x が修飾も受け手も無い素の名前か（`this->m`・`obj.m`・`X::m`・初期化子並びのメンバー名ではない）。"""
    p = x.parent
    if p is None:
        return True
    if p.type == "field_expression" and p.child_by_field_name("field") == x:
        return False
    if p.type == "qualified_identifier" and p.child_by_field_name("name") == x:
        return False
    return p.type != "field_initializer"


def _excluded_occurrence(sf, x, symbol, kind, class_entry=False):
    """変数のシンボルの出現のうち、構文上の位置で別の名前と決まるもの（note を返す。無ければ None）。
    `[CLASS:…]` のエントリでは、同じ名前の引数・ローカル変数による除外を素の出現だけに当てる。"""
    if kind != "variable":
        return None
    if class_entry and not _is_bare_occurrence(x):
        return None
    if "." not in symbol and _is_member_name(sf, x):
        return "member-name"
    if _is_param_name(sf, x):
        return "param-name"
    if _is_shadowed(sf, x, symbol):
        return "shadowed-local"
    return None


def find_occurrences(sf, row, symbol):
    """行 row 上のシンボル出現ノード。symbol が 'root.field' のときはフィールド参照に限定する。"""
    if "." in symbol:
        root, fld = symbol.split(".", 1)
        out = []
        for x in _nodes_on_line(sf.root, row):
            if x.child_count or txt(x) != fld or x.start_point[0] != row:
                continue
            p = x.parent
            if p is None:
                continue
            if p.type == "field_expression" and p.child_by_field_name("field") == x:
                a = p.child_by_field_name("argument")
            elif p.type == "attribute" and p.child_by_field_name("attribute") == x:
                a = p.child_by_field_name("object")
            else:
                continue
            if a is not None and a.type == "identifier" and txt(a) == root:
                out.append(x)
        return out
    return [x for x in _nodes_on_line(sf.root, row)
            if x.child_count == 0 and x.type in SEED_TYPES and txt(x) == symbol
            and x.start_point[0] == row]


def foreign_module_attr(repo, sf, x, symbol):
    """Python: `mod.symbol` の mod が import 名で、symbol の定義がそのモジュールに無ければ別物。"""
    if sf.lang != "python":
        return False
    p = x.parent
    if p is None or p.type != "attribute" or p.child_by_field_name("attribute") != x:
        return False
    obj = p.child_by_field_name("object")
    if obj is None or obj.type != "identifier" or txt(obj) not in sf.py_imports():
        return False
    defs = repo.defs(symbol)
    mod = txt(obj)
    return not any(d.cls is None and os.path.splitext(os.path.basename(d.path))[0] == mod
                   for d in defs)


def _write_only(x, lang):
    """x が単純代入（=）の左辺の書き込み先そのもの（読まれない）か。"""
    cur = x
    while cur.parent is not None and cur.parent.type in (
            "field_expression", "attribute", "subscript_expression", "subscript",
            "parenthesized_expression", "pointer_expression", "pattern_list", "tuple_pattern"):
        p = cur.parent
        # 添字・オブジェクト側（読まれる側）に居るなら書き込み先ではない
        if p.type in ("subscript_expression", "subscript") and \
                p.child_by_field_name("index" if lang != "python" else "subscript") == cur:
            return False
        if p.type in ("field_expression", "attribute") and cur is not p.child_by_field_name(
                "field" if p.type == "field_expression" else "attribute"):
            return False
        cur = p
    p = cur.parent
    if p is None:
        return False
    if lang == "python":
        return p.type == "assignment" and p.child_by_field_name("left") == cur
    if p.type == "assignment_expression" and p.child_by_field_name("left") == cur:
        op = p.child_by_field_name("operator")
        return op is not None and txt(op) == "="
    return False


def _py_import_bindings(stmt) -> list:
    """Python の import 文が束縛する名前（`import a.b` は a、`import a as b`・`from m import x as y` は別名、`from m import x` は x）。"""
    names = []
    targets = stmt.children_by_field_name("name") if stmt.type == "import_from_statement" else stmt.named_children
    for c in targets:
        if c.type == "aliased_import":
            al = c.child_by_field_name("alias")
            if al is not None:
                names.append(txt(al))
        elif c.type == "dotted_name":
            parts = txt(c).split(".")
            names.append(parts[-1] if stmt.type == "import_from_statement" else parts[0])
    return names


def _file_scope(sf, o, symbol):
    for a in _ancestors(o):
        t = a.type
        if t == "aliased_import" and sf.lang == "python":
            # モジュール本体・クラス本体の `from m import x as y`: 別名 y への束縛（代入と同じ扱い）
            nm = a.child_by_field_name("name")
            al = a.child_by_field_name("alias")
            if nm is not None and al is not None and nm.start_byte <= o.start_byte < nm.end_byte \
                    and txt(al) != symbol:
                return HitVerdict("file-scope", push_values={txt(al)}, note="module/class-assign")
            break
        if t == "declaration" and _at_file_scope(a):
            names = set()
            for d in a.children_by_field_name("declarator"):
                if d.type == "init_declarator":
                    nm, *_ = c_decl(d)
                    if nm:
                        names.add(nm)
            return HitVerdict("file-scope", push_values=names, note="global-init")
        if t in ("assignment", "augmented_assignment") and sf.lang == "python":
            names = {r for r, k, *_ in lvals(a.child_by_field_name("left"), "python")
                     if r and r != symbol}
            return HitVerdict("file-scope", push_values=names, note="module/class-assign")
    return HitVerdict("file-scope", note="declaration")


# ---------------------------------------------------------------------------
# 規則判定（rule。標準ライブラリのみ）
# ---------------------------------------------------------------------------

_C_NOT_FUNC = {"if", "for", "while", "switch", "catch", "return", "sizeof", "do", "else", "case",
               "defined", "typeof", "__typeof__", "__typeof", "decltype", "alignof", "_Alignof",
               "alignas", "_Alignas", "__declspec", "__attribute__", "static_assert", "_Static_assert",
               "int", "char", "void", "short", "long", "float", "double", "signed", "unsigned", "bool",
               "auto", "const", "volatile", "struct", "union", "enum", "class", "new", "delete",
               "throw", "noexcept"}
_C_CANDIDATE = re.compile(
    r"(operator\s*(?:\(\s*\)|\[\s*\]|new\b|delete\b|[^\s(A-Za-z0-9_]+|[A-Za-z_][\w:<>\s*&]*?)|~?[A-Za-z_]\w*)"
    r"\s*(?:<[^<>;{}]*(?:<[^<>;{}]*>[^<>;{}]*)*>)?\s*\(")
_C_CONTAINER = re.compile(r"\b(namespace|class|struct|union)\b[^(){};=]*$|\bextern\s*\"\s*\"\s*$|\bnamespace\s*$")
_C_ATTR = re.compile(r"__attribute__\s*\(\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)\)")


def _blank(chars: list, start: int, end: int) -> None:
    for k in range(start, end):
        if chars[k] != "\n":
            chars[k] = " "


def _strip_c_like(src: str, keep_preprocessor: bool) -> str:
    """C / C++: コメントと文字列/文字リテラルの中身を空白にする（改行と位置は保つ）。`keep_preprocessor` が
    False なら前処理指令の行も空白にする（関数の範囲を波かっこで数えるため）。"""
    out = list(src)
    n = len(src)
    i = 0
    line_start = True
    while i < n:
        c = src[i]
        nx = src[i + 1] if i + 1 < n else ""
        if line_start and c == "#" and not keep_preprocessor:
            j = i
            while j < n:
                if src[j] == "\n":
                    if j > 0 and src[j - 1] == "\\":
                        j += 1
                        continue
                    break
                if src[j] == "/" and j + 1 < n and src[j + 1] == "*":
                    k = src.find("*/", j + 2)
                    j = n if k < 0 else k + 2
                    continue
                j += 1
            _blank(out, i, j)
            i = j
            continue
        if c == "/" and nx == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            _blank(out, i, j)
            i = j
            continue
        if c == "/" and nx == "/":
            j = src.find("\n", i)
            j = n if j < 0 else j
            _blank(out, i, j)
            i = j
            continue
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            _blank(out, i + 1, min(j, n))
            i = j + 1
            line_start = False
            continue
        if c == "\n":
            line_start = True
        elif not c.isspace():
            line_start = False
        i += 1
    return "".join(out)


def _strip_python(src: str) -> str:
    """Python: コメントと文字列の中身を空白にする（改行と位置は保つ）。f 文字列は式を含むため残す（安全側）。"""
    out = list(src)
    n = len(src)
    i = 0
    while i < n:
        c = src[i]
        if c == "#":
            j = src.find("\n", i)
            j = n if j < 0 else j
            _blank(out, i, j)
            i = j
            continue
        if c in "\"'":
            k = i - 1
            prefix = ""
            while k >= 0 and src[k].isalpha() and len(prefix) < 2:
                prefix = src[k] + prefix
                k -= 1
            is_f = "f" in prefix.lower() and (k < 0 or not (src[k].isalnum() or src[k] == "_"))
            quote = src[i:i + 3] if src[i:i + 3] in ('"""', "'''") else c
            j = i + len(quote)
            while j < n:
                if src[j] == "\\" and "r" not in prefix.lower():
                    j += 2
                    continue
                if src.startswith(quote, j):
                    break
                if len(quote) == 1 and src[j] == "\n":
                    break
                j += 1
            if not is_f:
                _blank(out, i + len(quote), min(j, n))
            i = min(j + len(quote), n)
            continue
        i += 1
    return "".join(out)


def _line_offsets(text: str) -> list:
    offs = [0]
    for m in re.finditer("\n", text):
        offs.append(m.end())
    return offs


def _symbol_regex(symbol: str):
    if "." in symbol:
        root, fld = symbol.split(".", 1)
        return re.compile(r"\b%s\s*(?:\.|->)\s*%s\b" % (re.escape(root), re.escape(fld)))
    return re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(symbol))


def _match_paren(code: str, open_idx: int) -> int:
    depth = 0
    for k in range(open_idx, len(code)):
        ch = code[k]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return k
    return -1


def _c_func_name(head: str):
    """関数定義の頭部（直前の `;` `{` `}` から `{` まで）から、関数名（修飾・テンプレート引数を外した名前）と
    引数リストの開き括弧・閉じ括弧の位置を返す。関数定義でなければ None。"""
    h = _C_ATTR.sub(lambda m: " " * len(m.group(0)), head)
    stripped = h.rstrip()
    if not stripped or stripped.endswith(("=", ",", "(", "[")):
        return None
    depth = 0
    for k, ch in enumerate(h):
        if ch == "(":
            depth += 1
            continue
        if ch == ")":
            depth -= 1
            continue
        if depth != 0:
            continue
        if ch == "=" and not h.startswith("==", k) and (k == 0 or h[k - 1] not in "=!<>") \
                and not re.search(r"operator\s*$", h[:k]):
            return None   # 初期化子（`x = {`）
        if k > 0 and (h[k - 1].isalnum() or h[k - 1] == "_"):
            continue
        m = _C_CANDIDATE.match(h, k)
        if not m:
            continue
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        if name in _C_NOT_FUNC:
            continue
        open_idx = m.end() - 1
        close_idx = _match_paren(h, open_idx)
        if close_idx < 0:
            return None
        return name, open_idx, close_idx
    return None


@dataclass
class RuleFunc:
    name: str
    head_start: int   # 頭部の最初の非空白文字の位置
    body_open: int    # 本体の `{`（Python は本体の先頭行の先頭）
    body_close: int   # 本体の終わり（`}` の位置。Python は本体の最後の行の末尾）
    params: tuple = ()  # 引数リストの (開き括弧, 閉じ括弧) の位置（C / C++）


def _c_rule_functions(code: str) -> list:
    """C / C++: 波かっこの対応から関数本体の範囲を求める（コメント・文字列・前処理指令は除去済みの code）。"""
    funcs = []
    stack = []   # [("func"|"container"|"other", RuleFunc|None)]
    boundary = 0
    for i, ch in enumerate(code):
        if ch == ";":
            boundary = i + 1
        elif ch == "{":
            kind, rf = "other", None
            if not any(k == "func" for k, _ in stack):
                head = code[boundary:i]
                found = _c_func_name(head)
                if found is not None:
                    name, po, pc = found
                    hs = boundary + (len(head) - len(head.lstrip()))
                    rf = RuleFunc(name, hs, i, -1, (boundary + po, boundary + pc))
                    kind = "func"
                elif _C_CONTAINER.search(head):
                    kind = "container"
            stack.append((kind, rf))
            boundary = i + 1
        elif ch == "}":
            if stack:
                kind, rf = stack.pop()
                if kind == "func" and rf is not None:
                    rf.body_close = i
                    funcs.append(rf)
            boundary = i + 1
    return funcs


_PY_DEF = re.compile(r"^([ \t]*)(?:async[ \t]+)?def[ \t]+([A-Za-z_]\w*)[ \t]*\(")


def _py_rule_functions(code: str) -> list:
    """Python: インデントと `def` から関数本体の範囲を求める（コメント・文字列は除去済みの code）。"""
    lines = code.split("\n")
    offs = _line_offsets(code)
    funcs = []
    for idx, line in enumerate(lines):
        m = _PY_DEF.match(line)
        if not m:
            continue
        indent = len(m.group(1).expandtabs())
        # 引数リストの終わり（括弧の対応）と、その後の `:` を探す
        start = offs[idx] + m.end() - 1
        close = _match_paren(code, start)
        if close < 0:
            continue
        colon = code.find(":", close)
        if colon < 0:
            continue
        colon_line = code.count("\n", 0, colon)
        rest = code[colon + 1:offs[colon_line + 1] if colon_line + 1 < len(offs) else len(code)]
        if rest.strip():
            body_open = colon + 1            # 1行の関数（def f(): return x）
            body_close = offs[colon_line] + len(lines[colon_line])
        else:
            body_open = offs[colon_line + 1] if colon_line + 1 < len(offs) else len(code)
            last = colon_line
            for j in range(colon_line + 1, len(lines)):
                if not lines[j].strip():
                    continue
                expanded = lines[j].expandtabs()
                if len(expanded) - len(expanded.lstrip()) <= indent:
                    break
                last = j
            body_close = offs[last] + len(lines[last])
        funcs.append(RuleFunc(m.group(2), offs[idx] + len(m.group(1)), body_open, body_close))
    return funcs


@dataclass
class RuleVerdict:
    status: str                 # fp / rule / self-def / file-scope
    func: RuleFunc | None = None
    note: str = ""


class RuleFile:
    def __init__(self, path: str, lang: str):
        src = Path(path).read_text(encoding="utf-8", errors="replace")
        self.lang = lang
        if lang == "python":
            self.code = _strip_python(src)
            self.struct = self.code
            self.funcs = _py_rule_functions(self.code)
        else:
            self.code = _strip_c_like(src, keep_preprocessor=True)
            self.struct = _strip_c_like(src, keep_preprocessor=False)
            self.funcs = _c_rule_functions(self.struct)
        self.offs = _line_offsets(self.code)

    def line_span(self, line_no: int):
        s = self.offs[line_no - 1] if 0 < line_no <= len(self.offs) else len(self.code)
        e = self.offs[line_no] - 1 if line_no < len(self.offs) else len(self.code)
        return s, e

    def innermost(self, pos: int, in_body: bool):
        best = None
        for f in self.funcs:
            lo, hi = (f.body_open, f.body_close) if in_body else (f.head_start, f.body_open)
            if lo <= pos <= hi and (best is None or f.head_start >= best.head_start):
                best = f
        return best


_LABEL_DEF = re.compile(r"^\s*$")


def _is_label(code: str, line_start: int, s: int, e: int) -> bool:
    """C / C++: 出現位置 [s, e) が goto のラベル名（`goto X;` / `X:`）か。"""
    before = code[line_start:s]
    if re.search(r"\bgoto\s*$", before):
        return True
    after = code[e:e + 3]
    return bool(_LABEL_DEF.match(before) and re.match(r"\s*:(?!:)", after))


def _is_prototype_param_name(code: str, s: int, e: int) -> bool:
    """C / C++: 出現位置がファイルスコープのプロトタイプ宣言（`;` で終わる）の引数名か。"""
    start = max(code.rfind(";", 0, s), code.rfind("{", 0, s), code.rfind("}", 0, s)) + 1
    end = code.find(";", e)
    if end < 0 or "{" in code[e:end]:
        return False
    found = _c_func_name(code[start:end])
    if found is None:
        return False
    _name, po, pc = found
    if not (start + po < s and e <= start + pc):
        return False
    params = code[start + po + 1:start + pc]
    rel = s - (start + po + 1)
    depth = 0
    seg_start = 0
    segs = []
    for k, ch in enumerate(params):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            segs.append((seg_start, k))
            seg_start = k + 1
    segs.append((seg_start, len(params)))
    for a, b in segs:
        if a <= rel < b:
            seg = params[a:b].split("=")[0]
            seg = re.sub(r"\[[^\]]*\]", "", seg)
            ids = [(m.start(), m.group(0)) for m in re.finditer(r"[A-Za-z_]\w*", seg)]
            ids = [x for x in ids if x[1] not in ("const", "volatile", "restrict", "struct", "union",
                                                  "enum", "unsigned", "signed")]
            return len(ids) >= 2 and a + ids[-1][0] == rel
    return False


_INCLUDE_LINE = re.compile(r"^\s*#\s*(?:include|import)\b")


def rule_judge(rf: RuleFile, line_no: int, symbol: str) -> RuleVerdict:
    s_line, e_line = rf.line_span(line_no)
    line_code = rf.code[s_line:e_line]
    if rf.lang != "python" and _INCLUDE_LINE.match(line_code):
        return RuleVerdict("fp", note="include")
    rx = _symbol_regex(symbol)
    occ = [(m.start() + s_line, m.end() + s_line) for m in rx.finditer(line_code)]
    if not occ:
        return RuleVerdict("fp", note="comment/string")
    if rf.lang != "python":
        real = [(s, e) for s, e in occ if not _is_label(rf.code, s_line, s, e)]
        if not real:
            return RuleVerdict("fp", note="label")
        occ = real
    body_hit, head_hit = None, None
    for s, _e in occ:
        fb = rf.innermost(s, in_body=True)
        fh = rf.innermost(s, in_body=False)
        if fh is not None and (fb is None or fh.head_start > fb.head_start):
            head_hit = head_hit or fh      # 入れ子の関数の宣言部（外側の関数の本体の中にある）
        elif fb is not None and body_hit is None:
            body_hit = fb
    if body_hit is not None:
        return RuleVerdict("rule", func=body_hit)
    if head_hit is not None:
        return RuleVerdict("self-def", func=head_hit)
    if rf.lang != "python" and all(_is_prototype_param_name(rf.struct, s, e) for s, e in occ):
        return RuleVerdict("fp", note="prototype-param")
    return RuleVerdict("file-scope", note="declaration")


# ---------------------------------------------------------------------------
# classification エントリの組み立て
# ---------------------------------------------------------------------------

def _unpropagated_name(name: str):
    """次の波で追えない関数名（デストラクタ・演算子オーバーロード）なら pattern の値を返す。"""
    if name.startswith("~"):
        return "destructor"
    if name.startswith("operator") and not re.fullmatch(r"operator\w+", name):
        return "operator-overload"
    return None


def _summary_json(r: Result) -> dict:
    return {"returns": bool(r.returns), "out": sorted(r.out, key=str), "globals": [],
            "side": bool(r.side), "closure": sorted(r.closure)}


def _escapes_json(escapes: list) -> list:
    seen = set()
    out = []
    for k, d, ln in escapes:
        key = (k, str(d))
        if key in seen:
            continue
        seen.add(key)
        out.append([k, d, ln])
    return out


def _entry(hit: dict, classification: str, next_symbols: list, enclosing: str, note: str,
           slice_info: dict, rng, summaries: dict, kinds: dict = None, name_only=()) -> dict:
    nxt = list(dict.fromkeys(next_symbols))
    return {
        "line_id": hit["line_id"], "classification": classification,
        "next_symbols": nxt, "enclosing_function": enclosing,
        "is_external_api": False, "note": note, "slice": slice_info,
        "enclosing_range": rng, "next_symbol_summaries": summaries,
        "next_symbol_kinds": {e: k for e, k in (kinds or {}).items() if e in nxt},
        "name_only_symbols": sorted(e for e in name_only if e in nxt),
        "identity": IDENTITY_NONE if classification == "false-positive" else IDENTITY_NAME_ONLY,
    }


def _base(entry: str) -> str:
    return _parse_entry(entry)[0]


_C_STATIC_HEAD = re.compile(r"\bstatic\b")

# 次の波へ送らない言語の予約語（構文解析の誤りで「含む関数」・シンボルになったもの）。C のファイルに C++ の予約語を当てない。
_C_RESERVED = frozenset({"struct", "union", "enum", "typedef", "if", "else", "for", "while", "do", "switch",
                         "case", "default", "return", "sizeof"})
_CXX_RESERVED = _C_RESERVED | {"namespace", "class", "template", "typename", "using", "public", "private",
                               "protected", "friend", "operator", "alignof", "decltype", "static_assert", "try",
                               "catch", "throw", "new", "delete"}


def _reserved_words(lang: str):
    if lang == "cpp":
        return _CXX_RESERVED
    if lang == "c":
        return _C_RESERVED
    return frozenset()


def _parse_artifact(unsupported: list, rel: str, word: str) -> None:
    """予約語が関数名・シンボルになった箇所。ファイルと予約語の組ごとに cmd_classify が1件にまとめ、注記に件数を書く。"""
    unsupported.append({"pattern": LV.PATTERN_PARSE_ARTIFACT, "location": f"{rel} ({word})", "keyword": word})


def _drop_reserved(entries: list, lang: str, rel: str, unsupported: list) -> list:
    """次の波のシンボル（エントリ文字列）から、根の名前が予約語のものを除き parse-artifact として返す。"""
    words = _reserved_words(lang)
    out = []
    for e in entries:
        root = _base(e).split(".")[0]
        if root in words:
            _parse_artifact(unsupported, rel, root)
        else:
            out.append(e)
    return out


def entry_from_rule(hit: dict, v: RuleVerdict, rf: RuleFile, unsupported: list, note_prefix: str = "rule") -> dict:
    info = {"engine": "rule", "status": v.status, "escapes": []}
    if v.status == "fp":
        info["status"] = "fp"
        return _entry(hit, "false-positive", [], "", f"{note_prefix}: {v.note}", info, None, {})
    f = v.func
    rng = None
    if f is not None:
        rng = [rf.code.count("\n", 0, f.head_start) + 1, rf.code.count("\n", 0, max(f.body_close, 0)) + 1]
    if v.status == "rule":
        nxt = []
        pattern = _unpropagated_name(f.name)
        if f.name in _reserved_words(rf.lang):
            _parse_artifact(unsupported, hit["file"], f.name)
        elif pattern:
            unsupported.append({"pattern": pattern, "location": f"{hit['file']}:{hit['line_no']}",
                                "note": f"{f.name} の呼び出し元は名前で検索できない"})
        else:
            # 規則判定は索引を持たないため、関数ヘッダの static だけで決める（ヘッダの static は修飾しない）
            static = rf.lang != "python" and not is_header(hit["file"]) and \
                bool(_C_STATIC_HEAD.search(rf.code[f.head_start:f.params[0] if f.params else f.body_open]))
            nxt = [f"{f.name}[FILE:{hit['file']}]" if static else f.name]
        return _entry(hit, "propagation-direct", nxt, f.name, f"{note_prefix}: enclosing", info, rng, {},
                      kinds={e: "function" for e in nxt})
    if v.status == "self-def":
        return _entry(hit, "propagation-direct", [], f.name if f else "", f"{note_prefix}: self-def", info, rng, {})
    info["file_scope"] = v.note
    return _entry(hit, "propagation-direct", [], "", f"file-scope:{v.note}", info, None, {})


def _file_scope_values(repo: Repo, rel: str, v: HitVerdict) -> tuple:
    """関数の外のヒットから送る値（エントリ文字列）と種類・名前の一致のみのエントリ。"""
    out, kinds, name_only = [], {}, set()
    for x in sorted(v.push_values):
        if v.note == "global-init" and repo is not None:
            hit = repo.resolve_global(x, rel)
            e = f"{x}[FILE:{hit[1]}]" if (hit is not None and hit[0] == "file") else x
            if hit is not None and hit[0] == "file" and not hit[2]:
                name_only.add(e)
            kinds[e] = "variable"
        elif v.note == "macro-def":
            e = f"{x}[FILE:{rel}]" if (repo is not None and repo.file_internal(x, rel)) else x
            kinds[e] = "macro"
        else:
            e = x
            kinds[e] = "value"
        out.append(e)
    return out, kinds, name_only


def entry_from_slice(hit: dict, v: HitVerdict, unsupported: list, repo: Repo = None) -> dict:
    sym = hit["symbol"]
    if v.status == "fp":
        return _entry(hit, "false-positive", [], "", f"slice: {v.note}",
                      {"engine": "slice", "status": "fp", "escapes": []}, None, {})
    f = v.func
    rng = [f.node.start_point[0] + 1, f.node.end_point[0] + 1] if f is not None else None
    enclosing = f.name if f is not None else ""
    lang = lang_of(hit["file"], repo.h_as if repo is not None else "c")
    if v.status == "file-scope":
        values, kinds, name_only = _file_scope_values(repo, hit["file"], v)
        nxt = _drop_reserved([x for x in values if _base(x) != sym], lang, hit["file"], unsupported)
        info = {"engine": "slice", "status": "file-scope", "escapes": [], "file_scope": v.note,
                "propagates": bool(nxt)}
        return _entry(hit, "propagation-direct", nxt, "", f"file-scope:{v.note}", info, None, {},
                      kinds=kinds, name_only=name_only)
    if v.status in ("self-def", "write-only"):
        info = {"engine": "slice", "status": v.status, "escapes": []}
        return _entry(hit, "propagation-direct", [], enclosing, f"slice: {v.status}", info, rng, {})
    r = v.result
    nxt = []
    kinds = {}
    summaries = {}
    class_name_only = set()
    if v.push_up:
        pattern = _unpropagated_name(f.name)
        if f.name in _reserved_words(lang):
            _parse_artifact(unsupported, hit["file"], f.name)
        elif pattern:
            unsupported.append({"pattern": pattern, "location": f"{hit['file']}:{hit['line_no']}",
                                "note": f"{f.name} の呼び出し元は名前で検索できない"})
        else:
            if repo is not None and repo.is_cpp_method(f) and f.name != f.cls:
                # C++ のメソッドの呼び出し元はクラスを付けて追う（コンストラクタは今どおり型名で追う）
                e = f"{f.name}[CLASS:{repo.fcls(f)}]"
                if repo.class_info(repo.fcls(f)) == AMBIGUOUS:
                    class_name_only.add(e)
            elif repo is not None and repo.is_static_def(f):
                e = f"{f.name}[FILE:{hit['file']}]"
            else:
                e = f.name
            nxt.append(e)
            kinds[e] = "function"
            summaries[summary_key(e)] = _summary_json(r)
    for g in _drop_reserved(sorted(v.push_values), lang, hit["file"], unsupported):
        nxt.append(g)
        kinds.setdefault(g, "variable")
    for ln, text in r.fp_calls:
        unsupported.append({"pattern": "function-pointer-call", "location": f"{hit['file']}:{ln}",
                            "note": text.replace("\n", " ")})
    escape_kinds = sorted({k for k, _, _ in r.escapes})
    info = {"engine": "slice", "status": "sliced", "escapes": _escapes_json(r.escapes)}
    note = f"slice: escape={','.join(escape_kinds)}" if escape_kinds else "slice: closed"
    return _entry(hit, "propagation-direct", nxt, enclosing, note, info, rng, summaries,
                  kinds=kinds, name_only=r.name_only | class_name_only)


def slice_identity(repo: Repo, hit: dict, is_seed: bool, verdict=None) -> str:
    """スライス判定のヒット1件の同一性（偽陽性以外）。`[CLASS:…]` のエントリは受け手のクラスから決めた値（決められなければ
    name-only）。`[FILE:…]` のエントリ、または素名の外部リンケージの定義が1件以下なら resolved。シードは他のファイルの
    同名の static にも届くため、その名前を内部リンケージに持つファイルの数も足して数える。"""
    entry = hit.get("entry") or hit["symbol"]
    if _entry_scope_kind(entry) == SCOPE_CLASS:
        return (verdict.identity if (verdict is not None and verdict.identity) else None) or IDENTITY_NAME_ONLY
    if entry.endswith("]") and "[FILE:" in entry:
        return IDENTITY_RESOLVED
    root = hit["symbol"].split(".")[0]
    count = repo.ext_def_count.get(root, 0)
    if is_seed:
        count += len(repo.internal.get(root, ()))
    return IDENTITY_RESOLVED if count <= 1 else IDENTITY_NAME_ONLY


# ---------------------------------------------------------------------------
# 同じ呼び出し口の関数（callslot-candidates）
# ---------------------------------------------------------------------------
# シードの関数が関数ポインタの欄（`x->f = シード`・`x.f = シード`・指示付き初期化子 `.f = シード`）に登録されているとき、
# 同じ欄に登録される別の関数（同じ呼び出し口の関数）を決定的に集める。照合の鍵は判定エンジンで切り替える:
# slice は「左辺の型＋フィールド名」（型を求められない登録は「型未確認」）、rule は「フィールド名」だけ（全件「型未確認」）。

CALLSLOT_REG_RE = re.compile(
    r"(?:->|\.)[ \t]*([A-Za-z_]\w*)[ \t]*=(?!=)\s*&?[ \t]*([A-Za-z_]\w*)[ \t]*(?=[;,}\)\r\n]|$)")
CALLSLOT_CALL_NAME_RE = re.compile(r"\b([A-Za-z_]\w*)[ \t]*\(")
CALLSLOT_NOT_FUNC = frozenset({"NULL", "nullptr", "None", "true", "false", "True", "False", "this", "self"})
CALLSLOT_COMMON_MIN_POPULATION = 4   # 決まり文句を求める母数の下限（これ未満では決まり文句を除かない）
CALLSLOT_LIST_CAP = 30               # --max-per-field 0（無制限）のときに提示・stdout で列挙する件数
CALLSLOT_SHOW = 3                    # 提示で行を示す登録・呼び出し口の数
CALLSLOT_TYPE_UNKNOWN = "型未確認"
CALLSLOT_BODY_MISSING = "本体を確認できず"
CALLSLOT_NO_CALL_SITE = "呼び出し口を見つけられず（マクロ・別の名前の経由等）"
CALLSLOT_TEXT_TYPES = re.compile(r"\b(?:struct|union|enum|class)\s+([A-Za-z_]\w*)")
_CALLSLOT_TAG_DEF = re.compile(r"\b(?:struct|union|class)\s+([A-Za-z_]\w*)\s*(?:final\s*)?(?::[^;{}]*)?\{")
_CALLSLOT_TYPEDEF_NAMED = re.compile(
    r"\btypedef\s+(?:const\s+)?(?:(?:struct|union|enum|class)\s+)?([A-Za-z_]\w*)\s*\**\s*([A-Za-z_]\w*)\s*;")
_CALLSLOT_TYPEDEF_BODY = re.compile(r"\btypedef\s+(?:struct|union|class)\s*([A-Za-z_]\w*)?\s*\{")
_CALLSLOT_C_ID = re.compile(r"(?<![\w.>])\b[A-Za-z_]\w*\b")
_CALLSLOT_PY_ID = re.compile(r"(?<![\w.])\b[A-Za-z_]\w*\b")
_CALLSLOT_C_LOCAL = re.compile(r"\b(?:struct\s+\w+|\w+)\s*\**\s*([A-Za-z_]\w*)\s*[;=\[,)]")
_CALLSLOT_PY_ASSIGN = re.compile(r"(?m)^[ \t]*([A-Za-z_]\w*)[ \t]*(?::[^=\n]*)?=(?!=)")
_CALLSLOT_PY_FOR = re.compile(r"\bfor[ \t]+([\w \t,()]+?)[ \t]+in\b")
_CALLSLOT_PY_AS = re.compile(r"\bas[ \t]+([A-Za-z_]\w*)")
_CALLSLOT_PY_KWARG = re.compile(r"[(,][ \t\n]*([A-Za-z_]\w*)[ \t]*=(?!=)")
_CALLSLOT_DIRECTIVE = re.compile(r"[ \t]*#[ \t]*([A-Za-z_]\w*)?")
_CALLSLOT_C_KW = frozenset("""
auto break case char const continue default do double else enum extern float for goto if inline int long register
restrict return short signed sizeof static struct switch typedef union unsigned void volatile while _Bool _Complex
bool alignas alignof asm catch class constexpr const_cast decltype delete dynamic_cast explicit export friend mutable
namespace new noexcept nullptr operator private protected public reinterpret_cast static_assert static_cast template
this thread_local throw try typeid typename using virtual wchar_t override final defined __attribute__ typeof
__typeof__ NULL true false
""".split())
_CALLSLOT_PY_KW = frozenset("""
False None True and as assert async await break class continue def del elif else except finally for from global if
import in is lambda nonlocal not or pass raise return try while with yield self cls
""".split())


def _callslot_first_branch(code_pp: str) -> str:
    """前処理指令の行を残した本文（コメント・文字列は空白）から、波かっこを数えるための写しを作る:
    条件コンパイルの各深さで `#elif`・`#else` から同じ深さの `#endif` までを空白にし、前処理指令の行も空白にする
    （改行と文字の位置は保つ）。"""
    out = list(code_pp)
    stack = []          # 深さごとの「2つ目以降の枝の中か」
    pos = 0
    n = len(code_pp)
    in_directive = False
    while pos <= n:
        end = code_pp.find("\n", pos)
        if end < 0:
            end = n
        line = code_pp[pos:end]
        if in_directive or line.lstrip().startswith("#"):
            if not in_directive:
                m = _CALLSLOT_DIRECTIVE.match(line)
                word = (m.group(1) or "") if m else ""
                if word in ("if", "ifdef", "ifndef"):
                    stack.append(False)
                elif word in ("elif", "else", "elifdef", "elifndef"):
                    if stack:
                        stack[-1] = True
                elif word == "endif":
                    if stack:
                        stack.pop()
            _blank(out, pos, end)
            in_directive = line.rstrip().endswith("\\")
        elif any(stack):
            _blank(out, pos, end)
        pos = end + 1
    return "".join(out)


def _callslot_match_brace(text: str, open_idx: int) -> int:
    depth = 0
    for k in range(open_idx, len(text)):
        ch = text[k]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return k
    return -1


_CALLSLOT_AFTER_PARAMS = re.compile(r"[^;{}()]*")


class _CallslotScan:
    """母体の C / C++ / Python のファイルの字句の走査結果と、本体・型を求めるための遅延キャッシュ。"""

    def __init__(self, root: str, files: list, h_as: str, engine: str, excludes: list):
        self.root = root
        self.h_as = h_as
        self.engine = engine
        self.codes = {}            # {rel: (lang, 前処理指令の行を残した本文)}
        self.regs = {}             # {フィールド名: [(右辺の名前, rel, 行, 位置)]}
        self.called = {}           # {名前: {`名前(` が出現するファイル}}
        self.tag_files = {}        # {型名（タグ・本体つき typedef の別名）: {定義のあるファイル}}
        self.aliases = {}          # {typedef の別名: 元の名前}
        self._nopp = {}
        self._braces = {}
        self._lines = {}
        self._static = {}
        self._repo = Repo(root, excludes=excludes, h_as=h_as) if engine == "slice" else None
        self._member = {}
        self._anon = {}              # {名前の無い構造体のメンバーの型名 `型.メンバー`: 本体の節}
        self._global_type = {}
        for rel in files:
            lang = lang_of(rel, h_as)
            if lang is None:
                continue
            try:
                src = Path(root, rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            code = _strip_c_like(src, True) if lang in ("c", "cpp") else _strip_python(src)
            self.codes[rel] = (lang, code)
            for m in CALLSLOT_CALL_NAME_RE.finditer(code):
                self.called.setdefault(m.group(1), set()).add(rel)
            offs = None
            for m in CALLSLOT_REG_RE.finditer(code):
                if m.group(2) in CALLSLOT_NOT_FUNC:
                    continue
                if offs is None:
                    offs = _line_offsets(code)
                line = _bisect_line(offs, m.start())
                self.regs.setdefault(m.group(1), []).append((m.group(2), rel, line, m.start()))
            if lang in ("c", "cpp"):
                for m in _CALLSLOT_TAG_DEF.finditer(code):
                    self.tag_files.setdefault(m.group(1), set()).add(rel)
                for m in _CALLSLOT_TYPEDEF_NAMED.finditer(code):
                    if m.group(1) != m.group(2):
                        self.aliases.setdefault(m.group(2), m.group(1))
                for m in _CALLSLOT_TYPEDEF_BODY.finditer(code):
                    close = _callslot_match_brace(code, m.end() - 1)
                    if close < 0:
                        continue
                    am = re.match(r"\s*\**\s*([A-Za-z_]\w*)\s*[;,\[]", code[close + 1:close + 200])
                    if not am:
                        continue
                    if m.group(1):
                        if am.group(1) != m.group(1):
                            self.aliases.setdefault(am.group(1), m.group(1))
                    else:
                        self.tag_files.setdefault(am.group(1), set()).add(rel)

    # --- 行・本文 ---

    def line_text(self, rel: str, line: int) -> str:
        if rel not in self._lines:
            try:
                self._lines[rel] = Path(self.root, rel).read_text(encoding="utf-8", errors="replace").split("\n")
            except OSError:
                self._lines[rel] = []
        lines = self._lines[rel]
        return lines[line - 1].strip() if 0 < line <= len(lines) else ""

    def nopp(self, rel: str) -> str:
        if rel not in self._nopp:
            try:
                src = Path(self.root, rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                src = ""
            self._nopp[rel] = _strip_c_like(src, False)
        return self._nopp[rel]

    def braces(self, rel: str) -> str:
        if rel not in self._braces:
            self._braces[rel] = _callslot_first_branch(self.codes[rel][1])
        return self._braces[rel]

    def symbol(self, name: str, rel: str) -> str:
        """候補の表記: C のソース（ヘッダでない）で、そのファイルに `static … 名前(` があれば `名前[FILE:rel]`。"""
        key = (name, rel)
        if key not in self._static:
            lang, code = self.codes[rel]
            static = lang == "c" and not is_header(rel) and re.search(
                r"\bstatic\b[^;{}()=]*\b%s[ \t]*\(" % re.escape(name), code) is not None
            self._static[key] = f"{name}[FILE:{rel}]" if static else name
        return self._static[key]

    # --- 本体の名前（処理の起点になる名前） ---

    def body_names(self, name: str, files: list):
        """関数 name の本体で使う関数・変数・定数の名前（ローカル変数・引数・フィールド名・予約語・型名・自分の名前を除く）。
        files の順に定義を探す。本体を取り出せなければ None。"""
        if self.engine == "slice":
            for rel in files:
                names = self._ts_body_names(name, rel)
                if names is not None:
                    return names
        for rel in files:
            names = self._rule_body_names(name, rel)
            if names is not None:
                return names
        return None

    def _rule_body_names(self, name: str, rel: str):
        lang = self.codes[rel][0]
        if lang == "python":
            code = self.codes[rel][1]
            for rf in _py_rule_functions(code):
                if rf.name != name:
                    continue
                head = code[rf.head_start:rf.body_open]
                po = head.find("(")
                pc = _match_paren(head, po) if po >= 0 else -1
                params = head[po + 1:pc] if pc > po else ""
                body = code[rf.body_open:rf.body_close]
                locs = set(_CALLSLOT_PY_ID.findall(params))
                locs |= set(_CALLSLOT_PY_ASSIGN.findall(body)) | set(_CALLSLOT_PY_AS.findall(body))
                locs |= set(_CALLSLOT_PY_KWARG.findall(body))
                for m in _CALLSLOT_PY_FOR.finditer(body):
                    locs |= set(_CALLSLOT_PY_ID.findall(m.group(1)))
                return set(_CALLSLOT_PY_ID.findall(body)) - _CALLSLOT_PY_KW - locs - {name} - CALLSLOT_NOT_FUNC
            return None
        code = self.nopp(rel)
        braces = self.braces(rel)
        for m in re.finditer(r"(?m)^[^\n;{}]*?\b%s[ \t]*\(" % re.escape(name), code):
            po = m.end() - 1
            pc = _match_paren(code, po)
            if pc < 0:
                continue
            k = _CALLSLOT_AFTER_PARAMS.match(code, pc + 1).end()
            if k >= len(code) or code[k] != "{" or braces[k] != "{":
                continue
            close = _callslot_match_brace(braces, k)
            if close < 0:
                return None   # 閉じない（本体を確認できない）
            body = code[k:close + 1]
            params = code[po + 1:pc]
            ids = set(_CALLSLOT_C_ID.findall(body))
            locs = set(_CALLSLOT_C_LOCAL.findall(body)) | set(_CALLSLOT_C_ID.findall(params))
            types = set(CALLSLOT_TEXT_TYPES.findall(body))
            return ids - _CALLSLOT_C_KW - locs - types - {name} - CALLSLOT_NOT_FUNC
        return None

    def _ts_file(self, rel: str):
        try:
            return self._repo.file(rel)
        except (OSError, ValueError):
            return None

    def _ts_body_names(self, name: str, rel: str):
        sf = self._ts_file(rel)
        if sf is None:
            return None
        for f in sf.funcs():
            if f.name != name:
                continue
            locs = collect_locals(f)[0]
            names = set()
            for x in walk(f.body):
                if x.type != "identifier":
                    continue
                p = x.parent
                if f.lang == "python" and p is not None:
                    if p.type == "attribute" and _same_node(p.child_by_field_name("attribute"), x):
                        continue
                    if p.type == "keyword_argument" and _same_node(p.child_by_field_name("name"), x):
                        continue
                nm = txt(x)
                if nm in f.params or nm in locs or nm == name:
                    continue
                names.add(nm)
            kw = _CALLSLOT_PY_KW if f.lang == "python" else _CALLSLOT_C_KW
            return names - kw - CALLSLOT_NOT_FUNC
        return None

    # --- 左辺の型（slice） ---

    def canon(self, t):
        seen = set()
        while t in self.aliases and t not in seen:
            seen.add(t)
            t = self.aliases[t]
        return t

    def known(self, t) -> bool:
        return t is not None and self.canon(t) in self.tag_files

    def reg_type(self, rel: str, line: int, field: str, name: str):
        """登録（`x->f = name`・`x.f = name`・`.f = name`）の左辺の型（素の型名。typedef は元の名前にする）。求められなければ None。"""
        lang = self.codes[rel][0]
        if lang not in ("c", "cpp"):
            return None
        sf = self._ts_file(rel)
        if sf is None:
            return None
        for x in _nodes_on_line(sf.root, line - 1):
            if x.type != "field_identifier" or txt(x) != field or x.start_point[0] != line - 1:
                continue
            p = x.parent
            if p is None:
                continue
            if p.type == "field_expression":
                a = p.parent
                if a is None or a.type != "assignment_expression" or not _same_node(a.child_by_field_name("left"), p):
                    continue
                if _rhs_name(a.child_by_field_name("right")) != name:
                    continue
                t = self._expr_type(p.child_by_field_name("argument"), sf, rel, 0)
                return self.canon(t) if t else None
            if p.type == "field_designator":
                pair = p.parent
                if pair is None or pair.type != "initializer_pair":
                    continue
                if _rhs_name(pair.child_by_field_name("value")) != name:
                    continue
                t = self._pair_owner_type(pair, sf, rel, 0)
                return self.canon(t) if t else None
        return None

    def _pair_owner_type(self, pair, sf, rel, depth):
        """指示付き初期化子の対 pair の最後の指示子を除いた部分が指す型（`.a.b = x` なら a の型の b の型）。"""
        t = self._init_list_type(pair.parent, sf, rel, depth)
        designators = [c for c in pair.children_by_field_name("designator")]
        for d in designators[:-1]:
            if t is None:
                return None
            if d.type == "field_designator":
                fi = next((c for c in d.named_children if c.type == "field_identifier"), None)
                if fi is None:
                    return None
                t = self.member_type(t, txt(fi))
        return t

    def _init_list_type(self, lst, sf, rel, depth):
        if lst is None or depth > 12:
            return None
        par = lst.parent
        if par is None:
            return None
        if par.type == "init_declarator":
            decl = par.parent
            if decl is None or decl.type != "declaration":
                return None
            return _plain_type_node(decl.child_by_field_name("type"))
        if par.type == "initializer_pair":
            owner = self._pair_owner_type(par, sf, rel, depth + 1)
            last = list(par.children_by_field_name("designator"))
            if owner is None or not last:
                return None
            d = last[-1]
            if d.type != "field_designator":
                return owner   # 配列の添字の指示子（要素の型は配列の型と同じに扱う）
            fi = next((c for c in d.named_children if c.type == "field_identifier"), None)
            return self.member_type(owner, txt(fi)) if fi is not None else None
        if par.type == "initializer_list":
            return self._init_list_type(par, sf, rel, depth + 1)   # 配列の要素
        if par.type == "compound_literal_expression":
            return _plain_type_node(par.child_by_field_name("type"))
        return None

    def _expr_type(self, e, sf, rel, depth):
        if e is None or depth > 8:
            return None
        t = e.type
        if t == "identifier":
            return self._name_type(txt(e), e, sf, rel)
        if t == "this":
            f = sf.func_at(e)
            return f.cls if f is not None else None
        if t in ("parenthesized_expression",):
            inner = e.named_children[0] if e.named_children else None
            return self._expr_type(inner, sf, rel, depth + 1)
        if t == "pointer_expression":
            return self._expr_type(e.child_by_field_name("argument"), sf, rel, depth + 1)
        if t == "subscript_expression":
            return self._expr_type(e.child_by_field_name("argument"), sf, rel, depth + 1)
        if t == "field_expression":
            owner = self._expr_type(e.child_by_field_name("argument"), sf, rel, depth + 1)
            fld = e.child_by_field_name("field")
            return self.member_type(owner, txt(fld)) if (owner and fld is not None) else None
        return None

    def _name_type(self, name, node, sf, rel):
        f = sf.func_at(node)
        if f is not None:
            for x in walk(f.node):
                if x.type not in ("parameter_declaration", "declaration", "optional_parameter_declaration"):
                    continue
                for d in x.children_by_field_name("declarator"):
                    nm, _, _, _, fd = c_decl(d)
                    if nm == name and fd is None:
                        return _plain_type_node(x.child_by_field_name("type"))
        for n, _anon, _lk in _file_scope_nodes(sf.root):
            if n.type != "declaration":
                continue
            for d in n.children_by_field_name("declarator"):
                nm, _, _, _, fd = c_decl(d)
                if nm == name and fd is None:
                    return _plain_type_node(n.child_by_field_name("type"))
        return self.global_type(name)

    def global_type(self, name):
        """ファイルスコープの変数の宣言（他のファイル・ヘッダの `extern` 宣言を含む）から型名を字句で求める。
        型名が1つに決まらなければ None。"""
        if name in self._global_type:
            return self._global_type[name]
        pat = re.compile(
            r"(?m)^[ \t]*(?:(?:extern|static|const|volatile|_Thread_local|thread_local)\s+)*"
            r"(?:(?:struct|union|enum|class)\s+)?([A-Za-z_]\w*)[\s\*&]+(?:const\s+)?%s\s*(?:\[[^\]\n]*\]\s*)*[;=,]"
            % re.escape(name))
        found = set()
        for rel, (lang, code) in self.codes.items():
            if lang not in ("c", "cpp") or name not in code:
                continue
            for m in pat.finditer(code):
                if m.group(1) not in _CALLSLOT_C_KW and m.group(1) not in ("return", "goto", "case", "else"):
                    found.add(self.canon(m.group(1)))
        self._global_type[name] = next(iter(found)) if len(found) == 1 else None
        return self._global_type[name]

    def member_type(self, owner, member):
        """型 owner（素の型名）のメンバー member の型。定義が見つからなければ None。"""
        if owner is None:
            return None
        key = (self.canon(owner), member)
        if key in self._member:
            return self._member[key]
        result = None
        for body in self._type_bodies(key[0]):
            for fd in body.named_children:
                if fd.type != "field_declaration":
                    continue
                if not any(c_decl(d)[0] == member for d in fd.children_by_field_name("declarator")):
                    continue
                tnode = fd.child_by_field_name("type")
                if tnode is not None and tnode.type in ("struct_specifier", "union_specifier") \
                        and tnode.child_by_field_name("name") is None \
                        and tnode.child_by_field_name("body") is not None:
                    # 名前の無い構造体のメンバー: `型.メンバー` を型名として扱う
                    result = f"{key[0]}.{member}"
                    self._anon[result] = tnode.child_by_field_name("body")
                    self.tag_files.setdefault(result, set())
                else:
                    result = _plain_type_node(tnode)
                break
            if result:
                break
        self._member[key] = self.canon(result) if result else None
        return self._member[key]

    def _type_bodies(self, tag):
        """型名 tag の定義の本体（field_declaration_list）の節。"""
        if tag in self._anon:
            yield self._anon[tag]
            return
        for rel in sorted(self.tag_files.get(tag, ())):
            sf = self._ts_file(rel)
            if sf is None:
                continue
            for n in walk(sf.root):
                if n.type not in ("struct_specifier", "union_specifier", "class_specifier"):
                    continue
                nm = n.child_by_field_name("name")
                body = None
                if nm is not None and _plain_type_node(nm) == tag:
                    body = n.child_by_field_name("body")
                elif nm is None and n.parent is not None and n.parent.type == "type_definition":
                    if tag in [c_decl(d)[0] for d in n.parent.children_by_field_name("declarator")]:
                        body = n.child_by_field_name("body")
                if body is not None:
                    yield body


def _same_node(a, b) -> bool:
    return a is not None and b is not None and a.start_byte == b.start_byte and a.end_byte == b.end_byte \
        and a.type == b.type


def _rhs_name(n):
    """登録の右辺（`name`・`&name`）の名前。"""
    if n is None:
        return None
    if n.type == "pointer_expression":
        n = n.child_by_field_name("argument")
    return txt(n) if n is not None and n.type == "identifier" else None


def _bisect_line(offs: list, pos: int) -> int:
    lo, hi = 0, len(offs)
    while lo < hi:
        mid = (lo + hi) // 2
        if offs[mid] <= pos:
            lo = mid + 1
        else:
            hi = mid
    return lo


def _callslot_targets(adopted: list, scan: _CallslotScan) -> list:
    """対象にするシード: 素の名前・`名前[FILE:p]`・`名前[MEDIUM:p]` で、`名前(` の出現が母体にあるもの。
    [(シード, 素の名前, 登録箇所を限るファイル | None)]"""
    out = []
    for s in adopted:
        kind = _entry_scope_kind(s)
        if kind == SCOPE_CLASS:
            continue
        name, scope = _parse_entry(s)
        if "." in name or "::" in name or name not in scan.called:
            continue
        out.append((s, name, scope if kind is not None else None))
    return out


def find_callslot_functions(repo_path: str, adopted: list, engine: str, excludes: list, include_ext: list,
                            h_as: str, max_per_field: int) -> dict:
    """採用したシード（候補表の ☑ の行のシンボル）の同じ呼び出し口の関数を求める（ファイルは書かない）。"""
    files = list_repo_files(repo_path, excludes, include_ext or None)
    scan = _CallslotScan(repo_path, files, h_as, engine, excludes)
    targets = _callslot_targets(adopted, scan)

    def _seed_site(name, rel):
        return any(name == n and (scope is None or scope == rel) for _s, n, scope in targets)

    type_cache = {}

    def _type(name, rel, line, fld):
        if engine != "slice":
            return None
        key = (name, rel, line, fld)
        if key not in type_cache:
            type_cache[key] = scan.reg_type(rel, line, fld, name)
        return type_cache[key]

    # 鍵（型, フィールド名）ごとのシードとその登録
    groups = {}
    for seed, name, scope in targets:
        for fld, sites in scan.regs.items():
            for v, rel, line, _pos in sites:
                if v != name or (scope is not None and rel != scope):
                    continue
                key = (_type(v, rel, line, fld), fld)
                g = groups.setdefault(key, {"seeds": [], "seed_sites": [], "seed_files": {}})
                if seed not in g["seeds"]:
                    g["seeds"].append(seed)
                g["seed_sites"].append((seed, rel, line))
                g["seed_files"].setdefault(seed, [])
                if rel not in g["seed_files"][seed]:
                    g["seed_files"][seed].append(rel)

    # 呼び出し口（字句の一致）
    fields = sorted({fld for _t, fld in groups})
    call_sites = {fld: [] for fld in fields}
    if fields:
        alt = "|".join(re.escape(f) for f in fields)
        call_re = re.compile(r"\(\s*\*\s*[^()]*?(?:->|\.)\s*(%s)\s*\)\s*\(|(?:->|\.)\s*(%s)\s*\(" % (alt, alt))
        for rel in sorted(scan.codes):
            code = scan.codes[rel][1]
            offs = None
            for m in call_re.finditer(code):
                fld = m.group(1) or m.group(2)
                if offs is None:
                    offs = _line_offsets(code)
                call_sites[fld].append((rel, _bisect_line(offs, m.start())))

    body_cache = {}

    def _body(name, files):
        key = (name, tuple(files))
        if key not in body_cache:
            body_cache[key] = scan.body_names(name, files)
        return body_cache[key]

    def _files_for(symbol, hints):
        name, scope = _parse_entry(symbol)
        if scope is not None:
            return [scope]
        rest = sorted(scan.called.get(name, set()) - set(hints))
        return list(dict.fromkeys(list(hints) + rest))

    def _site(rel, line):
        return {"file": rel, "line": line, "text": scan.line_text(rel, line)}

    out_groups = []
    for (gtype, fld), g in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0] or "")):
        cands = {}
        mismatched = []
        for v, rel, line, _pos in scan.regs.get(fld, ()):
            if _seed_site(v, rel) or v not in scan.called:
                continue
            rt = _type(v, rel, line, fld)
            typed = gtype is not None and rt is not None and rt == gtype
            if gtype is not None and rt is not None and rt != gtype and scan.known(rt) and scan.known(gtype):
                mismatched.append({"name": scan.symbol(v, rel), "file": rel, "line": line, "type": rt})
                continue
            sym = scan.symbol(v, rel)
            c = cands.setdefault(sym, {"symbol": sym, "sites": [], "typed": False})
            c["sites"].append((rel, line))
            c["typed"] = c["typed"] or typed
        # 本体の名前と決まり文句（母数はシードを含む、本体を取り出せたもの全部）
        seed_ids = {}
        for seed in g["seeds"]:
            seed_ids[seed] = _body(_parse_entry(seed)[0], _files_for(seed, g["seed_files"][seed]))
        cand_ids = {}
        for sym, c in cands.items():
            cand_ids[sym] = _body(_parse_entry(sym)[0], _files_for(sym, [r for r, _l in c["sites"]]))
        population = [x for x in list(seed_ids.values()) + list(cand_ids.values()) if x is not None]
        common = set()
        if len(population) >= CALLSLOT_COMMON_MIN_POPULATION:
            counts = {}
            for ids in population:
                for t in ids:
                    counts[t] = counts.get(t, 0) + 1
            common = {t for t, c in counts.items() if c * 2 > len(population)}
        seed_names = set()
        for ids in seed_ids.values():
            seed_names |= (ids or set())
        seed_names -= common
        cand_list = []
        for sym in sorted(cands):
            c = cands[sym]
            ids = cand_ids[sym]
            shared = sorted((ids or set()) & seed_names)
            cand_list.append({"symbol": sym,
                              "sites": [_site(r, l) for r, l in sorted(c["sites"])],
                              "type": gtype if c["typed"] else None,
                              "recommended": bool(shared), "shared_names": shared, "body_found": ids is not None})
        rec_count = sum(1 for c in cand_list if c["recommended"])
        over = bool(max_per_field and rec_count > max_per_field)
        if over:
            for c in cand_list:
                c["recommended"] = False
        cand_list.sort(key=lambda c: (not c["recommended"], c["symbol"]))
        cs = sorted(call_sites.get(fld, []))
        out_groups.append({
            "seeds": list(g["seeds"]), "seed": ", ".join(g["seeds"]), "field": fld, "type": gtype,
            "seed_sites": [dict(_site(r, l), seed=s) for s, r, l in sorted(g["seed_sites"], key=lambda x: (x[1], x[2]))],
            "seed_body_found": {s: ids is not None for s, ids in seed_ids.items()},
            "call_sites": [_site(r, l) for r, l in cs[:CALLSLOT_SHOW]], "call_site_count": len(cs),
            "common_names": sorted(common), "candidate_count": len(cand_list), "recommended_count": rec_count,
            "over_limit": over, "candidates": cand_list,
            "type_mismatch": sorted(mismatched, key=lambda x: (x["file"], x["line"])),
        })
    all_syms = sorted({c["symbol"] for g in out_groups for c in g["candidates"]})
    recommended = sorted({c["symbol"] for g in out_groups for c in g["candidates"] if c["recommended"]})
    return {
        "engine": engine, "seed_count": len(targets), "candidate_count": len(all_syms), "recommended": recommended,
        "over_limit": [{"seed": g["seed"], "field": g["field"], "type": g["type"],
                        "candidate_count": g["candidate_count"], "recommended_count": g["recommended_count"]}
                       for g in out_groups if g["over_limit"]],
        "groups": out_groups, "scanned_file_count": len(scan.codes), "max_per_field": max_per_field,
    }


def _callslot_code(s: str) -> str:
    s = s.replace("\n", " ")
    if not s:
        return "—"
    return f"`` {s} ``" if "`" in s else f"`{s}`"


def _callslot_cell(s: str) -> str:
    return s.replace("|", "\\|")


def _callslot_markdown(result: dict, cr: str, repo: str) -> str:
    slice_mode = result["engine"] == "slice"
    lines = [
        f"# 同じ呼び出し口の関数 — {cr} / {repo}",
        "",
        "> `specout_slice.py callslot-candidates` が書く（手で編集しない）。照合: "
        + ("型名＋フィールド名（tree-sitter。型を求められない登録はフィールド名だけで照合し「型未確認」）" if slice_mode
           else "フィールド名だけ（tree-sitter なし。全件「型未確認」）") + "。",
        ">",
        "> **同じ呼び出し口の関数**は、シードと同じ関数ポインタの欄に登録される別の関数（登録する側の関数ではない）。",
        "> 例: `ops_a->on_connect = a_on_connect;`・`ops_b->on_connect = b_on_connect;` があり、`(*ops->on_connect)(ops);`（呼び出し口）で呼ばれるとき、",
        "> シード `a_on_connect` に対して `b_on_connect` が同じ呼び出し口の関数。呼び出しが関数ポインタ経由のため、波紋調査ではシードから届かない。",
        f"> 調べる場合は、シード確認で「`{repo}`: 同じ呼び出し口の関数: おすすめで行う」か「`{repo}`: 同じ呼び出し口の関数: `X`, `Y` で行う」と答える。",
        "> おすすめ（☆）は、シードの本体で使う関数・変数・定数の名前（決まり文句を除く）を1つ以上使う同じ呼び出し口の関数。",
        "",
    ]
    if not result["groups"]:
        lines.append(f"同じ呼び出し口の関数はありません（対象にしたシード: {result['seed_count']} 件。"
                     f"走査したファイル: {result['scanned_file_count']} 件）。")
        return "\n".join(lines) + "\n"
    for g in result["groups"]:
        key = f"{g['type']}.{g['field']}" if g["type"] else g["field"]
        tail = f"。おすすめが上限 {result['max_per_field']} 件を超えるため、おすすめにしない" if g["over_limit"] else ""
        seeds = ", ".join(f"`{s}`" for s in g["seeds"])
        lines.append(f"## {seeds} — フィールド `{key}`（{g['candidate_count']} 件・おすすめ {g['recommended_count']} 件{tail}）")
        for s in g["seed_sites"]:
            lines.append(f"> シードの登録: `{s['file']}:{s['line']}` {_callslot_code(s['text'])}")
        if g["call_sites"]:
            for s in g["call_sites"]:
                lines.append(f"> 呼び出し口: `{s['file']}:{s['line']}` {_callslot_code(s['text'])}")
            if g["call_site_count"] > len(g["call_sites"]):
                lines.append(f"> 呼び出し口: ほか {g['call_site_count'] - len(g['call_sites'])} 箇所")
        else:
            lines.append(f"> 呼び出し口: {CALLSLOT_NO_CALL_SITE}")
        missing = [s for s, ok in g["seed_body_found"].items() if not ok]
        if missing:
            lines.append("> シードの本体を確認できず: " + ", ".join(f"`{s}`" for s in missing)
                         + "（おすすめを決められない）")
        if g["common_names"]:
            lines.append("> 決まり文句として比べなかった名前: " + ", ".join(f"`{n}`" for n in g["common_names"]))
        else:
            lines.append(f"> 決まり文句として比べなかった名前: なし（本体を取り出せた関数が {CALLSLOT_COMMON_MIN_POPULATION} 件未満、"
                         "または半数を超える本体に出る名前が無い）")
        lines += ["", "| 候補 | 登録箇所 | 型 | おすすめ | シードと共有する名前 |", "|---|---|---|---|---|"]
        for c in g["candidates"]:
            site = c["sites"][0]
            where = f"`{site['file']}:{site['line']}`" + (f"（ほか {len(c['sites']) - 1} 箇所）" if len(c["sites"]) > 1 else "")
            if not c["body_found"]:
                shared = CALLSLOT_BODY_MISSING
            else:
                shared = ", ".join(f"`{n}`" for n in c["shared_names"]) or "—"
            lines.append(f"| `{_callslot_cell(c['symbol'])}` | {where} | {c['type'] or CALLSLOT_TYPE_UNKNOWN} | "
                         f"{'☆' if c['recommended'] else ''} | {shared} |")
        lines.append("")
    if slice_mode:
        lines += ["## 型が異なるため同じ呼び出し口の関数にしなかった登録（`slice` のみ）", "",
                  "| シード | フィールド | 名前 | 登録箇所 | 型 |", "|---|---|---|---|---|"]
        rows = [(g, m) for g in result["groups"] for m in g["type_mismatch"]]
        for g, m in rows:
            lines.append(f"| {', '.join(f'`{s}`' for s in g['seeds'])} | `{g['type']}.{g['field']}` | "
                         f"`{_callslot_cell(m['name'])}` | `{m['file']}:{m['line']}` | {m['type']} |")
        if not rows:
            lines.append("| — | — | — | — | — |")
        lines.append("")
    return "\n".join(lines)


def _callslot_stdout(result: dict) -> dict:
    """提示に使う要約（鍵ごとの候補をおすすめ→その他の順に上限の件数まで。超えた分は omitted_count）。"""
    cap = result.get("max_per_field") or CALLSLOT_LIST_CAP
    out = {k: v for k, v in result.items() if k not in ("groups", "fingerprint")}
    out["groups"] = []
    for g in result["groups"]:
        gg = {k: v for k, v in g.items() if k not in ("candidates", "type_mismatch")}
        gg["candidates"] = g["candidates"][:cap]
        gg["omitted_count"] = max(0, len(g["candidates"]) - cap)
        gg["type_mismatch_count"] = len(g["type_mismatch"])
        out["groups"].append(gg)
    return out


def _callslot_fingerprint(repo_path: str, adopted: list, conf: dict, files: list) -> str:
    h = hashlib.sha256()
    here = Path(__file__).resolve().parent
    for name in ("specout_slice.py", "specout_bfs.py", "specout_macros.py"):
        try:
            h.update(hashlib.sha256((here / name).read_bytes()).hexdigest().encode())
        except OSError:
            h.update(b"-")
    h.update(json.dumps({"seeds": sorted(set(adopted)), "conf": conf}, ensure_ascii=False, sort_keys=True).encode())
    for rel in files:
        try:
            st = os.stat(os.path.join(repo_path, rel))
            h.update(f"{rel}\0{st.st_size}\0{st.st_mtime_ns}\n".encode())
        except OSError:
            h.update(f"{rel}\0-\n".encode())
    return h.hexdigest()


def _write_text_atomic(path: str, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=f".{p.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write_json_atomic(path: str, obj) -> None:
    _write_text_atomic(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def cmd_callslot_candidates(args) -> None:
    from specout_bfs import _parse_seed_candidates, _seed_adopted_symbols, _split_csv, resolve_h_as
    engine = args.engine
    if engine == "slice":
        _require_engine()
    seeds = _parse_seed_candidates(Path(args.seed_candidates))
    adopted = _seed_adopted_symbols(seeds)
    excludes = _split_csv(args.exclude)
    include_ext = _split_csv(args.include_ext)
    h_as = resolve_h_as(args.slice_h_as, args.repo_path, excludes)
    max_per_field = int(args.max_per_field)
    if max_per_field < 0:
        _err(f"--max-per-field は 0 以上の整数にしてください: {args.max_per_field}")
    files = list_repo_files(args.repo_path, excludes, include_ext or None)
    conf = {"engine": engine, "exclude": excludes, "include_ext": include_ext, "h_as": h_as,
            "max_per_field": max_per_field, "cr": args.cr, "repo": args.repo, "repo_path": os.path.abspath(args.repo_path)}
    fp = _callslot_fingerprint(args.repo_path, adopted, conf, files)
    prev = None
    jp = Path(args.json_out)
    if jp.is_file() and Path(args.list_out).is_file():
        try:
            prev = json.loads(jp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prev = None
    if prev is not None and prev.get("fingerprint") == fp:
        out = _callslot_stdout(prev)
        out["cached"] = True
        print(json.dumps(out, ensure_ascii=False))
        return
    result = find_callslot_functions(args.repo_path, adopted, engine, excludes, include_ext, h_as, max_per_field)
    result["list_file"] = str(args.list_out)
    result["fingerprint"] = fp
    _write_text_atomic(args.list_out, _callslot_markdown(result, args.cr, args.repo))
    _write_json_atomic(args.json_out, result)
    out = _callslot_stdout(result)
    out["cached"] = False
    print(json.dumps(out, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 同じ呼び出し口の関数の選択（callslot-choose。標準ライブラリのみ）
# ---------------------------------------------------------------------------

CALLSLOT_CHOICES = ("none", "recommended", "selected")


def _callslot_load_candidates(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        _err(f"同じ呼び出し口の関数の候補ファイルが見つかりません: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        _err(f"同じ呼び出し口の関数の候補ファイルを読めません: {p}（{e}）")
    if not isinstance(data, dict) or not isinstance(data.get("groups"), list):
        _err(f"同じ呼び出し口の関数の候補ファイルの形式が不正です: {p}")
    return data


def _callslot_record(choice: str, symbols: list, cands: dict, pending: bool, today: str) -> dict:
    return {"choice": choice, "symbols": list(symbols), "candidate_count": int(cands.get("candidate_count") or 0),
            "recommended_count": len(cands.get("recommended") or []), "pending": bool(pending), "decided": today}


def _callslot_split_symbols(text: str) -> list:
    return [s.strip().strip("`").strip() for s in (text or "").split(",") if s.strip().strip("`").strip()]


def cmd_callslot_choose(args) -> None:
    out = Path(args.out)
    modes = [bool(args.choice), bool(args.revalidate), bool(args.mark_started)]
    if sum(modes) != 1:
        _err("--choice・--revalidate・--mark-started のいずれか1つを指定してください", 2)
    if args.mark_started:
        if not out.is_file():
            _err(f"同じ呼び出し口の関数の選択の記録が見つかりません: {out}")
        try:
            rec = json.loads(out.read_text(encoding="utf-8"))
        except ValueError as e:
            _err(f"同じ呼び出し口の関数の選択の記録を読めません: {out}（{e}）")
        rec["pending"] = False
        _write_json_atomic(str(out), rec)
        print(json.dumps(rec, ensure_ascii=False))
        return
    if not args.candidates_json:
        _err("--candidates-json を指定してください", 2)
    cands = _callslot_load_candidates(args.candidates_json)
    all_syms = {c["symbol"] for g in cands["groups"] for c in g.get("candidates") or []}
    recommended = list(cands.get("recommended") or [])
    if args.choice:
        if args.no_start:
            _err("--no-start は --revalidate と一緒に指定してください", 2)
        if args.choice == "selected":
            syms = _callslot_split_symbols(args.symbols)
            if not syms:
                _err("--choice selected には --symbols を指定してください", 2)
            unknown = [s for s in syms if s not in all_syms]
            if unknown:
                _err("同じ呼び出し口の関数の候補にありません: " + ", ".join(unknown)
                     + f"（候補の全量: {cands.get('list_file') or args.candidates_json}）")
        elif args.symbols:
            _err("--symbols は --choice selected のときだけ指定できます", 2)
        if args.choice == "recommended":
            if not recommended:
                _err("おすすめの同じ呼び出し口の関数がありません（「行わない」か「`X`, `Y` で行う」を選んでください）")
            syms = recommended
        elif args.choice == "none":
            syms = []
        rec = _callslot_record(args.choice, syms, cands, args.choice != "none", args.today)
        _write_json_atomic(str(out), rec)
        print(json.dumps(dict(rec, downgraded=False, missing=[]), ensure_ascii=False))
        return
    # --revalidate
    old = None
    if out.is_file():
        try:
            old = json.loads(out.read_text(encoding="utf-8"))
        except ValueError as e:
            _err(f"同じ呼び出し口の関数の選択の記録を読めません: {out}（{e}）")
    choice = (old or {}).get("choice") or "none"
    if choice not in CALLSLOT_CHOICES:
        _err(f"同じ呼び出し口の関数の選択の記録の choice が不正です: {out}（{choice}）")
    pending = bool((old or {}).get("pending")) and not args.no_start
    old_syms = list((old or {}).get("symbols") or [])
    downgraded, missing = False, []
    if choice == "recommended":
        syms = recommended
        if not syms:
            downgraded, missing = True, old_syms
    elif choice == "selected":
        syms = old_syms
        missing = [s for s in syms if s not in all_syms]
        downgraded = bool(missing) or not syms
    else:
        syms = []
    if downgraded:
        choice, syms, pending = "none", [], False
    rec = _callslot_record(choice, syms, cands, pending if choice != "none" else False, args.today)
    _write_json_atomic(str(out), rec)
    print(json.dumps(dict(rec, downgraded=downgraded, missing=missing), ensure_ascii=False))


# ---------------------------------------------------------------------------
# state の読み込み
# ---------------------------------------------------------------------------

def _load_state(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        _err(f"bfs-state.json が見つかりません: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _err(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def _make_repo(data: dict) -> Repo:
    repo = Repo(data["repo_path"], excludes=data.get("exclude_patterns") or [],
                h_as=data.get("slice_h_as") or "c")
    pattern = data.get("slice_ignore_calls") or ""
    if pattern:
        repo.ignore_re = re.compile(pattern)
    return repo


def _require_engine() -> None:
    try:
        _ts()
    except EngineUnavailable as e:
        _err(f"判定エンジン（tree-sitter）を使えません: {e}", EXIT_ENGINE_UNAVAILABLE)


def _write_json(path: str, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# サブコマンド
# ---------------------------------------------------------------------------

def cmd_probe(args) -> None:
    try:
        _ts()
        result = {"ok": True, "engine": "slice", "engine_exts": ENGINE_EXTS, "warning": None}
    except EngineUnavailable as e:
        result = {"ok": True, "engine": "unavailable", "engine_exts": ENGINE_EXTS,
                  "warning": f"tree-sitter を import できません（{e}）"}
    if args.out:
        _write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False))


def _summary_out(s: dict) -> dict:
    return {"returns": bool(s.get("returns")), "out": sorted(s.get("out") or (), key=str),
            "globals": sorted(s.get("globals") or ()), "side": bool(s.get("side")),
            "closure": sorted(s.get("closure") or ()), "name_only": sorted(s.get("name_only") or ())}


def _union_summary(a: dict, b: dict) -> dict:
    out = {}
    for k in ("out", "globals", "closure", "name_only"):
        merged = {str(v): v for v in list(a.get(k) or ()) + list(b.get(k) or ())}
        out[k] = [merged[x] for x in sorted(merged)]
    return {"returns": bool(a.get("returns") or b.get("returns")), "out": out["out"], "globals": out["globals"],
            "side": bool(a.get("side") or b.get("side")), "closure": out["closure"], "name_only": out["name_only"]}


def cmd_seed_summary(args) -> None:
    data = _load_state(args.path)
    if (data.get("slice_engine") or "rule") != "slice":
        _err("seed-summary は state の slice_engine が slice のときだけ使えます"
             f"（現在: {data.get('slice_engine') or 'rule'}）")
    _require_engine()
    if args.symbols is not None:
        targets = [s.strip() for s in args.symbols.split(",") if s.strip()]
    else:
        targets = list(data.get("seed_summary_pending") or [])
    repo = _make_repo(data)
    repo.build_index()
    summaries = {}
    globals_ = set()
    name_only = set()
    for target in targets:
        # `x[FILE:p]`（候補表で人がファイルを指定したシード）は p から呼べる定義、`x[CLASS:X]` は X の定義
        # （と virtual なら X の派生クラスの override）で要約する。修飾なしは全定義。
        sym, scope = _parse_entry(target)
        if not repo.is_function(sym):
            continue
        if _entry_scope_kind(target) == SCOPE_CLASS:
            s = repo.summary(sym, cls=repo.entry_class(scope))
        else:
            s = repo.summary(sym, caller=scope if (scope and "[FILE:" in target) else None)
        if s is None:
            continue
        out = _summary_out(s)
        g = set(s.get("globals") or ())
        no = set(s.get("name_only") or ())
        if (not scope or s.get("cls_fallback")) and s.get("def_count", 1) >= 2:
            no |= g   # 同名の定義を2件以上混ぜた要約から出たグローバル
        out["name_only"] = sorted(no)
        key = summary_key(target)
        summaries[key] = _union_summary(summaries[key], out) if key in summaries else out
        globals_ |= g
        name_only |= no
    payload = {"targets": targets, "summaries": summaries, "globals": sorted(globals_),
               "name_only": sorted(name_only)}
    _write_json(args.out, payload)
    print(json.dumps({"ok": True, "summaries_file": str(args.out), "targets": targets,
                      "globals": payload["globals"]}, ensure_ascii=False))


def cmd_classify(args) -> None:
    t_start = time.monotonic()
    data = _load_state(args.path)
    engine = data.get("slice_engine") or "rule"
    chunk = json.loads(Path(args.hits).read_text(encoding="utf-8"))
    hits = chunk.get("hits") or []
    summaries = chunk.get("frontier_summaries") or {}
    classification = []
    unsupported = []
    index_build_ms = 0
    if hits:
        repo_path = data["repo_path"]
        h_as = data.get("slice_h_as") or "c"
        repo = None
        if engine == "slice":
            _require_engine()
            repo = _make_repo(data)
            t0 = time.monotonic()
            repo.build_index()
            index_build_ms = int((time.monotonic() - t0) * 1000)
        rule_files = {}

        def _rule_file(rel: str, lang: str) -> RuleFile:
            if rel not in rule_files:
                rule_files[rel] = RuleFile(os.path.join(repo_path, rel), lang)
            return rule_files[rel]

        kinds = chunk.get("frontier_kinds") or {}
        seed_keys = set(chunk.get("seed_keys") or [])
        for hit in hits:
            rel = hit["file"]
            lang = lang_of(rel, h_as)
            if lang is None:
                _err(f"スライス用チャンクに判定できない拡張子のヒットがあります: {rel}（{hit['line_id']}）")
            if engine == "slice":
                key = summary_key(hit.get("entry") or hit["symbol"])
                is_seed = key in seed_keys
                try:
                    v = judge_hit(repo, rel, hit["line_no"], hit["symbol"], seed_summ=summaries,
                                  entry=hit.get("entry"), kind=kinds.get(key), is_seed=is_seed)
                    entry = entry_from_slice(hit, v, unsupported, repo)
                    if entry["classification"] != "false-positive":
                        entry["identity"] = slice_identity(repo, hit, is_seed, v)
                    classification.append(entry)
                    continue
                except EngineUnavailable as e:
                    _err(f"判定エンジン（tree-sitter）を使えません: {e}", EXIT_ENGINE_UNAVAILABLE)
                except Exception as e:  # noqa: BLE001 — 解析の失敗は規則判定で代わりに判定する（取りこぼさない）
                    rf = _rule_file(rel, lang)
                    entry = entry_from_rule(hit, rule_judge(rf, hit["line_no"], hit["symbol"]), rf,
                                            unsupported, note_prefix=f"slice-error {type(e).__name__}; rule")
                    entry["slice"]["engine"] = "slice"
                    classification.append(entry)
                    continue
            rf = _rule_file(rel, lang)
            classification.append(entry_from_rule(hit, rule_judge(rf, hit["line_no"], hit["symbol"]), rf,
                                                  unsupported))
    seen = {}
    merged = []
    for u in unsupported:
        key = (u["pattern"], u["location"])
        if key not in seen:
            seen[key] = dict(u)
            merged.append(seen[key])
        seen[key]["count"] = seen[key].get("count", 0) + 1
    for u in merged:
        n = u.pop("count")
        word = u.pop("keyword", None)
        if u["pattern"] == LV.PATTERN_PARSE_ARTIFACT:
            u["note"] = f"構文解析の誤りで予約語 {word} が関数名・シンボルになった（{n} 件。次の波へ送らない）"
    out = {"chunk_id": chunk.get("chunk_id", ""), "classification": classification,
           "unsupported_patterns": merged,
           "elapsed_ms": int((time.monotonic() - t_start) * 1000), "index_build_ms": index_build_ms}
    _write_json(args.out, out)
    print(json.dumps({"ok": True, "out": str(args.out), "classified": len(classification),
                      "engine": engine, "unsupported_patterns": len(merged),
                      "elapsed_ms": out["elapsed_ms"], "index_build_ms": index_build_ms}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_probe = sub.add_parser("probe")
    p_probe.add_argument("--out", default=None)
    p_probe.set_defaults(func=cmd_probe)

    p_seed = sub.add_parser("seed-summary")
    p_seed.add_argument("--path", required=True)
    p_seed.add_argument("--symbols", default=None)
    p_seed.add_argument("--out", required=True)
    p_seed.set_defaults(func=cmd_seed_summary)

    p_cls = sub.add_parser("classify")
    p_cls.add_argument("--path", required=True)
    p_cls.add_argument("--hits", required=True)
    p_cls.add_argument("--out", required=True)
    p_cls.set_defaults(func=cmd_classify)

    p_cs = sub.add_parser("callslot-candidates")
    p_cs.add_argument("--engine", required=True, choices=["slice", "rule"])
    p_cs.add_argument("--seed-candidates", required=True)
    p_cs.add_argument("--repo-path", required=True)
    p_cs.add_argument("--exclude", default="")
    p_cs.add_argument("--include-ext", default="")
    p_cs.add_argument("--slice-h-as", default="auto")
    p_cs.add_argument("--max-per-field", default="30")
    p_cs.add_argument("--cr", required=True)
    p_cs.add_argument("--repo", required=True)
    p_cs.add_argument("--list-out", required=True)
    p_cs.add_argument("--json-out", required=True)
    p_cs.set_defaults(func=cmd_callslot_candidates)

    p_ch = sub.add_parser("callslot-choose")
    p_ch.add_argument("--candidates-json", default=None)
    p_ch.add_argument("--choice", choices=list(CALLSLOT_CHOICES), default=None)
    p_ch.add_argument("--symbols", default=None)
    p_ch.add_argument("--revalidate", action="store_true")
    p_ch.add_argument("--no-start", action="store_true")
    p_ch.add_argument("--mark-started", action="store_true")
    p_ch.add_argument("--today", default="")
    p_ch.add_argument("--out", required=True)
    p_ch.set_defaults(func=cmd_callslot_choose)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — CLI境界でのエラーはstderrへ集約する
        _err(f"予期しないエラーが発生しました: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
