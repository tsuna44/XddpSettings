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

書き込むのは --out のファイルだけ（bfs-state.json と discovery-log.md は書かない）。
終了コード: 0 = 成功 / 1 = 実行時エラー / 2 = 使用法エラー（argparse 既定）/ 5 = 判定エンジンが使えない
（state の slice_engine が slice なのに tree-sitter を import できない。stderr に原因のモジュールを書く）。
tree-sitter は構文解析を行う関数の中で import する（--help・probe・rule は tree-sitter が無くても動く）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
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


@dataclass
class Local:
    static: bool = False
    ptr: bool = False
    ref: bool = False
    array: bool = False
    fresh: bool = True  # Python: 束縛がすべて新規リテラル/コンテナ
    type: str | None = None   # C++: 宣言の素の型名


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
                f.params[pn] = Param(pn, idx, ptr=ptr or array, ref=ref,
                                     type=_plain_type_node(p.child_by_field_name("type")) if sf.lang == "cpp" else None)
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
            tp = _plain_type_node(x.child_by_field_name("type")) if f.lang == "cpp" else None
            for d in x.children_by_field_name("declarator"):
                nm, ptr, ref, array, fd = c_decl(d)
                if nm and fd is None:
                    locs[nm] = Local(static=static, ptr=ptr, ref=ref, array=array, type=tp)
        elif t == "for_range_loop":
            nm, ptr, ref, array, _ = c_decl(x.child_by_field_name("declarator"))
            if nm:
                locs[nm] = Local(ptr=ptr, ref=ref, array=array,
                                 type=_plain_type_node(x.child_by_field_name("type")) if f.lang == "cpp" else None)
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


AMBIGUOUS = "\x00ambiguous"
_CLASS_TEXT_RE = re.compile(rb"\b(?:class|struct)\s+((?:[A-Za-z_]\w*\s+)*[A-Za-z_]\w*)")
# クラス・構造体の定義（本体の前の基底の句の有無。テンプレートの特殊化の引数・宣言を飾る語を許す）
_CLASS_DEF_TEXT_RE = re.compile(rb"\b(?:class|struct)\s+(?:[A-Za-z_]\w*\s+)*?([A-Za-z_]\w*)\s*(?:<[^;{]*?>)?\s*"
                                rb"(?:final\s*)?([:{])")
_USING_TEXT_RE = re.compile(rb"\busing\s+([A-Za-z_]\w*)\s*=\s*([^;]+);")
_TYPEDEF_TEXT_RE = re.compile(rb"\btypedef\s+([^;{}]+?)\s+([A-Za-z_]\w*)\s*;")
_BRACE_TYPEDEF_TEXT_RE = re.compile(rb"\}\s*([A-Za-z_]\w*)\s*;")
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
                out_of_class += [(f.cls, f.name) for f in sf.funcs() if f.is_method and f.cls
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
        for cname, mname in out_of_class:
            infos = self.classes.get(cname)
            if infos and len(infos) == 1:
                infos[0].methods.setdefault(mname, False)
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
            if t not in ("class_specifier", "struct_specifier"):
                continue
            body = n.child_by_field_name("body")
            name = _plain_type_node(n.child_by_field_name("name"))
            if body is None or not name:
                continue
            info = ClassInfo(name, rel)
            for c in n.named_children:
                if c.type != "base_class_clause":
                    continue
                for b in c.named_children:
                    if b.type in ("type_identifier", "qualified_identifier", "template_type"):
                        bn = _plain_type_node(b)
                        if bn:
                            info.bases.append((bn, b.type == "qualified_identifier"))
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
                    elif m.type == "field_declaration":
                        info.members[mn] = _plain_type_node(m.child_by_field_name("type"))
            self.classes.setdefault(name, []).append(info)

    def _ensure_index(self) -> None:
        if self._index is None:
            self.build_index()

    def class_info(self, name):
        """索引のクラス（同じ素の名前のクラスが1つだけのとき）。索引に無ければ None、複数あれば AMBIGUOUS。"""
        self._ensure_index()
        infos = self.classes.get(name)
        if not infos:
            return None
        return infos[0] if len(infos) == 1 else AMBIGUOUS

    def is_class(self, name) -> bool:
        """名前がクラスの索引にあるか（同じ素の名前のクラスが複数ある場合を含む）。"""
        self._ensure_index()
        return bool(name) and name in self.classes

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
        names, aliases, has_base, brace_typedefs = set(), {}, {}, set()
        dec = lambda b: b.decode("utf-8", "replace")   # noqa: E731
        for rel in MAC.iter_c_cxx_files(self.root):
            try:
                with open(os.path.join(self.root, rel), "rb") as fh:
                    src = fh.read()
            except OSError:
                continue
            for m in _CLASS_TEXT_RE.finditer(src):
                names.update(dec(w) for w in m.group(1).split())
            for m in _CLASS_DEF_TEXT_RE.finditer(src):
                nm = dec(m.group(1))
                has_base[nm] = has_base.get(nm, False) or m.group(2) == b":"
            for m in _USING_TEXT_RE.finditer(src):
                aliases.setdefault(dec(m.group(1)), []).append(dec(m.group(2)).strip())
            for m in _TYPEDEF_TEXT_RE.finditer(src):
                aliases.setdefault(dec(m.group(2)), []).append(dec(m.group(1)).strip())
            brace_typedefs.update(dec(m.group(1)) for m in _BRACE_TYPEDEF_TEXT_RE.finditer(src))
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

    def declaring(self, cname, member):
        """cname 自身またはその基底クラスのうち member を宣言した最も近いクラス。戻り値 (クラス or None, 決まったか)。
        途中で索引に無い基底クラスに当たる・cname が索引に無いか同名が複数なら (None, False)。継承の連鎖がすべて索引にあり、
        どこにも宣言が無ければ (None, True)。"""
        info = self.class_info(cname)
        if info is None or info == AMBIGUOUS:
            return None, False
        if self.declares(cname, member):
            return cname, True
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
                return (found[0], True) if len(set(found)) == 1 else (None, False)
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
        return f is not None and f.lang == "cpp" and f.is_method and self.is_class(f.cls)

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
            d, _ok = self.declaring(f.cls, name)
            if d is not None:
                return self.class_info(d).members.get(name)
        t = self.file_var_types.get(self.rel(f.path), {}).get(name)
        if t:
            return t
        ts = self.global_var_types.get(name) or ()
        return next(iter(ts)) if len(ts) == 1 else None

    def receiver(self, x, f, name):
        """出現 x（メソッド名・メンバー名）の受け手のクラス。戻り値: ("class", クラス名) / ("free", None)〔メソッドの本体の中の
        修飾なしの名前で、含むクラスの継承の連鎖がすべて索引にあり、どこにも宣言が無い〕/ (None, None)〔決められない〕。"""
        p = x.parent
        if p is None:
            return None, None
        if p.type == "qualified_identifier" and p.child_by_field_name("name") == x:
            y = self.resolve_type(_plain_type_name(p.child_by_field_name("scope")))
            return ("class", y) if y else (None, None)
        if p.type == "field_expression" and p.child_by_field_name("field") == x:
            arg = p.child_by_field_name("argument")
            if arg is not None and arg.type == "this":
                return self._implicit_receiver(f, name)
            if arg is not None and arg.type == "identifier":
                t = self.resolve_type(self.var_type(txt(arg), f))
                return ("class", t) if t else (None, None)
            return None, None
        if p.type == "field_initializer":
            return ("class", f.cls) if (f is not None and f.cls) else (None, None)
        for a in _ancestors(x):
            if a.type in ("compound_statement", "translation_unit"):
                break
            if a.type == "field_declaration_list":
                k = a.parent
                cname = _plain_type_node(k.child_by_field_name("name")) if k is not None else None
                return ("class", cname) if cname else (None, None)
        if x.type == "identifier":
            return self._implicit_receiver(f, name)
        return None, None

    def _implicit_receiver(self, f, name):
        if not self.is_cpp_method(f):
            return None, None
        d, ok = self.declaring(f.cls, name)
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
        chosen = [f for f in fs if f.lang == "cpp" and f.cls == d]
        if self.method_virtual(d, name) is not False:
            subs = set(self.subclasses(x_cls))
            chosen += [f for f in fs if f.lang == "cpp" and f.cls in subs]
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
        owner = f.cls if root == "this" else repo.resolve_type(repo.var_type(root, f))
        e = _member_entry(repo, owner, fld)
        if e is not None:
            res.append(e)
    member_like = f.lang == "cpp" and f.is_method
    for k, d in out:
        if k != "global":
            res.append((k, d))
            continue
        if repo.is_cpp_method(f):
            e = _member_entry(repo, f.cls, d.split(".")[0])
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
    return ("global", f"{name}[CLASS:{d}]", len(repo.classes.get(d, ())) > 1)


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
    x_cls = _parse_entry(entry)[1] if (entry and _entry_scope_kind(entry) == SCOPE_CLASS) else None
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
                e = f"{f.name}[CLASS:{f.cls}]"
                if len(repo.classes.get(f.cls, ())) > 1:
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
            s = repo.summary(sym, cls=scope)
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
