"""試作: 関数内スライスによる波紋判定（C / C++ / Python、tree-sitter 使用）。

ある行に変更シンボルが現れたとき、その影響が関数の外へ出るか（＝呼び出し元へ伝播させる必要が
あるか）を、関数内の保守的な（流れ非依存の）データ依存・制御依存解析で判定する。

出口（escape）の種類:
  return     値を返す return/yield が影響を受ける           → 呼び出し元へ伝播
  exception  throw/raise が影響を受ける                      → 呼び出し元へ伝播
  out        ポインタ/参照引数・self/this 経由の書き込み     → 呼び出し元へ伝播
  heap       出所不明のポインタ（ローカル）経由の書き込み    → 呼び出し元へ伝播（保守的）
  state      static ローカル変数への書き込み                 → 呼び出し元へ伝播（次回呼び出しが変わる）
  unknown    解析できない呼び出し・書き込み                  → 呼び出し元へ伝播（保守的）
  global     グローバル変数への書き込み                      → その変数名を次のシンボルにする（読む側を探す）
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache

from tree_sitter import Language, Parser
import tree_sitter_c
import tree_sitter_cpp
import tree_sitter_python

_LANG = {
    "c": Language(tree_sitter_c.language()),
    "cpp": Language(tree_sitter_cpp.language()),
    "python": Language(tree_sitter_python.language()),
}
_PARSER = {k: Parser(v) for k, v in _LANG.items()}

EXT_LANG = {".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp",
            ".hh": "cpp", ".hxx": "cpp", ".py": "python"}

UP_KINDS = {"return", "exception", "out", "heap", "state", "unknown", "closure"}

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

SEED_TYPES = {"identifier", "type_identifier", "field_identifier", "namespace_identifier"}


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


# ---------------------------------------------------------------------------
# ファイル・関数
# ---------------------------------------------------------------------------
@dataclass
class Param:
    name: str
    idx: int
    ptr: bool = False   # ポインタ・配列（C/C++）。Python は常に True（オブジェクト参照）
    ref: bool = False   # C++ 参照


@dataclass
class Local:
    static: bool = False
    ptr: bool = False
    ref: bool = False
    array: bool = False
    fresh: bool = True  # Python: 束縛がすべて新規リテラル/コンテナ


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


class SourceFile:
    def __init__(self, path, lang):
        self.path = path
        self.lang = lang
        self.src = open(path, "rb").read()
        if lang in ("c", "cpp"):
            self.src = preprocess_c(self.src)
        self.tree = _PARSER[lang].parse(self.src)
        self.root = self.tree.root_node
        self._funcs = None

    def py_imports(self):
        if getattr(self, "_imports", None) is None:
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


_FOR_MACRO = re.compile(rb"\bfor\s*\(\s*([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*\)")
_STMT_LOOP_MACRO = re.compile(rb"^([ \t]+)([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*(\{?)\s*$", re.M)
_NOT_MACRO = {b"if", b"while", b"for", b"switch", b"return", b"sizeof", b"do", b"else"}


def preprocess_c(src: bytes) -> bytes:
    """構文を作るループマクロ（for (MACRO(...)) / MACRO(...) {）を、構文解析できる形に書き換える。
    改行は変えない（行番号を保つ）。__xddp_iter は全引数を読み書きする擬似関数として扱う。"""
    src = _FOR_MACRO.sub(lambda m: b"for (;__xddp_iter(" + m.group(2) + b");)", src)

    def stmt(m):
        if m.group(2) in _NOT_MACRO or not m.group(4):
            return m.group(0)
        return m.group(1) + b"for (;__xddp_iter(" + m.group(3) + b");) {"
    return _STMT_LOOP_MACRO.sub(stmt, src)


def lang_of(path, h_as="c"):
    ext = os.path.splitext(path)[1]
    if ext == ".h":
        return h_as
    return EXT_LANG.get(ext)


@lru_cache(maxsize=400)
def load(path, lang):
    return SourceFile(path, lang)


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
    if f.is_method:
        if "::" in head:
            f.cls = head.split("::")[-2].strip().lstrip("*&")
        else:
            for a in _ancestors(n):
                if a.type in ("class_specifier", "struct_specifier"):
                    nm = a.child_by_field_name("name")
                    f.cls = txt(nm) if nm is not None else None
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
                f.params[pn] = Param(pn, idx, ptr=ptr or array, ref=ref)
            idx += 1
    return f


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
            return [("this", "member", True, None)]
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
    defs: list = field(default_factory=list)      # [(root, kind, via)]
    uses: set = field(default_factory=set)
    calls: list = field(default_factory=list)
    value_return: bool = False
    has_error: bool = False


_C_STMT_SIMPLE = {"expression_statement", "declaration", "return_statement", "throw_statement",
                  "goto_statement", "break_statement", "continue_statement"}
_PY_STMT_SIMPLE = {"expression_statement", "return_statement", "raise_statement", "assert_statement",
                   "delete_statement", "pass_statement", "break_statement", "continue_statement",
                   "import_statement", "import_from_statement", "print_statement",
                   "exec_statement", "type_alias_statement"}
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
        if t in ("while_statement", "switch_statement"):
            cond = self.add([n.child_by_field_name("condition")], "cond", ctl, n.start_byte)
            self.c(n.child_by_field_name("body"), ctl + [cond.id])
            return
        if t == "do_statement":
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


_ASSIGN_C = {"assignment_expression", "update_expression", "init_declarator"}
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
                if t == "as_pattern_target" or t == "for_in_clause":
                    pass
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
        for x in walk(f.body, stop={"function_definition", "class_definition", "lambda"}):
            t = x.type
            if t == "global_statement":
                py_globals |= {txt(c) for c in x.named_children if c.type == "identifier"}
            elif t == "nonlocal_statement":
                f.outer |= {txt(c) for c in x.named_children if c.type == "identifier"}
                f.nonlocal_ = getattr(f, "nonlocal_", set()) | \
                    {txt(c) for c in x.named_children if c.type == "identifier"}
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
        for g in py_globals | getattr(f, "nonlocal_", set()):
            locs.pop(g, None)
        return locs, py_globals
    for x in walk(f.body):
        t = x.type
        if t == "declaration":
            static = any(c.type == "storage_class_specifier" and txt(c) == "static"
                         for c in x.children)
            for d in x.children_by_field_name("declarator"):
                nm, ptr, ref, array, fd = c_decl(d)
                if nm and fd is None:
                    locs[nm] = Local(static=static, ptr=ptr, ref=ref, array=array)
        elif t == "for_range_loop":
            nm, ptr, ref, array, _ = c_decl(x.child_by_field_name("declarator"))
            if nm:
                locs[nm] = Local(ptr=ptr, ref=ref, array=array)
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
DEFAULT_EXCLUDES = ["tests/", "test/", "__tests__/", "spec/", "specs/", "__mocks__/", "fixtures/",
                    "vendor/", "node_modules/"]


class Repo:
    def __init__(self, root, excludes=None, h_as="c", policy="optimistic", max_depth=3):
        self.root = os.path.abspath(root)
        self.excludes = DEFAULT_EXCLUDES if excludes is None else excludes
        self.h_as = h_as
        self.policy = policy          # 'strict' | 'optimistic'（外部関数の扱い）
        self.ignore_re = None         # 影響なしとみなす呼び出し（ログ・メモリ確保等。プロジェクト設定）
        self.max_depth = max_depth
        self._index = None            # name -> [(relpath, start_byte)]
        self._macros = None           # name -> (params, body)
        self._summ = {}
        self.stats = {"external_assumed_pure": 0, "external_unknown": 0, "depth_limit": 0}

    def code_files(self):
        out = subprocess.run(["git", "-C", self.root, "ls-files"], capture_output=True,
                             text=True).stdout.split("\n")
        if not any(out):   # git 管理外（または未追跡）ならディレクトリを直接列挙する
            out = [os.path.relpath(os.path.join(dp, fn), self.root)
                   for dp, _, fns in os.walk(self.root) if "/." not in dp for fn in fns]
        res = []
        for p in out:
            if not p or lang_of(p, self.h_as) is None:
                continue
            if any(("/" + ex) in ("/" + p) for ex in self.excludes):
                continue
            res.append(p)
        return res

    def file(self, rel):
        return load(os.path.join(self.root, rel), lang_of(rel, self.h_as))

    def build_index(self):
        global GLOBAL_NAMES
        self._index, self._macros = {}, {}
        GLOBAL_NAMES = set()
        for rel in self.code_files():
            try:
                sf = self.file(rel)
            except (OSError, ValueError):
                continue
            for n in sf.root.named_children:
                if n.type == "declaration":
                    for d in n.children_by_field_name("declarator"):
                        nm, _, _, _, fd = c_decl(d)
                        if nm and fd is None:
                            GLOBAL_NAMES.add(nm)
                elif n.type == "expression_statement" and sf.lang == "python":
                    for a in n.named_children:
                        if a.type in ("assignment", "augmented_assignment"):
                            GLOBAL_NAMES.update(r for r, *_ in lvals(a.child_by_field_name("left"),
                                                                     "python") if r)
            for f in sf.funcs():
                self._index.setdefault(f.name, []).append((rel, f.node.start_byte))
            if sf.lang != "python":
                for n in walk(sf.root, stop={"function_definition"}):
                    if n.type == "preproc_function_def":
                        nm = n.child_by_field_name("name")
                        ps = n.child_by_field_name("parameters")
                        val = n.child_by_field_name("value")
                        params = [txt(c) for c in ps.named_children] if ps else []
                        self._macros[txt(nm)] = (params, txt(val) if val is not None else "")
        load.cache_clear()

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

    def summary(self, name, depth=0, cls=None):
        fs = self.defs(name)
        if cls is not None:
            same = [f for f in fs if f.cls == cls]
            if same:
                fs = same
            else:
                cls = None
        key = (name, cls)
        if key in self._summ:
            return self._summ[key]
        if not fs:
            return None
        if depth > self.max_depth:
            self.stats["depth_limit"] += 1
            return {"returns": True, "out": set(), "globals": set(),
                    "side": self.policy == "strict"}
        self._summ[key] = {"returns": False, "out": set(), "globals": set(), "side": False}
        acc = {"returns": False, "out": set(), "globals": set(), "side": False, "closure": set()}
        for f in fs:
            r = analyze_function(f, self, seeds=None, depth=depth + 1)
            acc["closure"] |= r.closure
            acc["returns"] |= r.returns
            acc["out"] |= r.out
            acc["globals"] |= r.globals
            acc["side"] |= r.side
        self._summ[key] = acc
        return acc


# ---------------------------------------------------------------------------
# 関数内スライス本体
# ---------------------------------------------------------------------------
@dataclass
class Result:
    escapes: list = field(default_factory=list)   # [(kind, detail, line)]
    affected_units: int = 0
    total_units: int = 0
    has_error: bool = False

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


GLOBAL_NAMES: set | None = None   # リポジトリ内でファイルスコープ宣言のある名前（Repo.build_index が設定）


def classify_write(root, kind, via, f: Func, locs, py_globals, fld=None):
    out = _classify_write(root, kind, via, f, locs, py_globals, fld)
    if GLOBAL_NAMES is None:
        return out
    # 宣言が見つからない「グローバル」はマクロ宣言のローカル等の誤解析とみなし、unknown（上へ）にする
    return [("unknown", f"undeclared {d}") if (k == "global" and d.split(".")[0] not in GLOBAL_NAMES)
            else (k, d) for k, d in out]


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
    writes = []   # (root, kind, via)

    self_recv = recv is not None and recv.type in ("identifier", "this") and \
        txt(recv) in ("self", "cls", "this")
    module_recv = lang == "python" and recv is not None and recv.type == "identifier" and \
        txt(recv) in load(f.path, lang).py_imports() and txt(recv) not in locs
    if module_recv:
        summ = None   # import したモジュールの関数（リポジトリのメソッドではない）
    elif name is not None and name in seed_summ:
        summ = seed_summ[name]
        kind = "seed"
    elif (recv is not None and not self_recv and lang in ("python", "cpp") and
                         (name in PURE.get(lang, ()) or name in WRITERS.get(lang, {}))):
        summ = None   # 言語標準のメソッド名は標準ライブラリとして扱う（下の外部処理へ）
    else:
        summ = repo.summary(name, depth, cls=f.cls if self_recv else None) \
            if (name and repo is not None) else None
        kind = "repo" if summ is not None else None
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
                s2 = repo.summary(inner, depth + 1)
                if s2 is not None:
                    esc += [("global", g) for g in s2["globals"]]
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
                continue
            i = o - shift if isinstance(o, int) else None
            if i is not None and 0 <= i < len(pos):
                writes += arg_written(pos[i], lang)
            elif i is not None and lang == "python":
                for a in kw.values():
                    writes += arg_written(a, lang)
        esc += [("global", g) for g in summ["globals"]]
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
            for e in classify_write(r, k, v, f, locs, py_globals, fl):
                res.escapes.append((e[0], e[1], line))
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
            esc, writes = call_effects(call, f, repo, locs, py_globals, seed_summ, depth)
            for e in esc:
                res.escapes.append((e[0], e[1], line))
            for r, k, v, fl in writes:
                grew |= taint(r, u.start)
                for e in classify_write(r, k, v, f, locs, py_globals, fl):
                    res.escapes.append((e[0], e[1], line))
    # 呼び出しによる書き込みで汚染が増えた場合は、その汚染を初期値として再計算する
    if grew and seeds is not None:
        return analyze_function(f, repo, seeds=seeds, seed_summ=seed_summ, depth=depth,
                                extra_taint=tuple((k_, p_) for k_, ps in T.items() for p_ in ps),
                                return_type_hit=return_type_hit)
    return res


# ---------------------------------------------------------------------------
# ヒット1件の判定
# ---------------------------------------------------------------------------
@dataclass
class HitVerdict:
    status: str                  # fp / self-def / file-scope / sliced / no-function
    func: str | None = None
    push_up: bool = False
    push_values: set = field(default_factory=set)
    escapes: list = field(default_factory=list)
    result: Result | None = None
    note: str = ""


def _nodes_on_line(root, row):
    stack = [root]
    while stack:
        x = stack.pop()
        if x.end_point[0] < row or x.start_point[0] > row:
            continue
        yield x
        stack.extend(x.children)


def judge_hit(repo: Repo, rel, line_no, symbol, seed_summ=None):
    sf = repo.file(rel)
    row = line_no - 1
    occ = [x for x in find_occurrences(sf, row, symbol) if not foreign_module_attr(repo, sf, x, symbol)]
    if not occ:
        # マクロ本体（#define X ... symbol ...）
        for x in _nodes_on_line(sf.root, row):
            if x.type == "preproc_arg" and re.search(r"\b%s\b" % re.escape(symbol), txt(x)):
                d = x.parent
                nm = d.child_by_field_name("name") if d is not None else None
                if nm is not None and txt(nm) != symbol:
                    return HitVerdict("file-scope", push_values={txt(nm)}, note="macro-def")
                return HitVerdict("file-scope", note="macro-self")
        return HitVerdict("fp", note="comment/string/include")
    o = occ[0]
    f = sf.func_at(o)
    if f is None:
        return _file_scope(sf, o, symbol)
    is_value = not (seed_summ and symbol in seed_summ)
    if is_value and all(_write_only(x, sf.lang) for x in occ):
        return HitVerdict("write-only", func=f.name, note="value overwritten, not read")
    seeds = {x.start_byte for x in occ}
    # 関数ヘッダ内のヒット
    if o.start_byte < f.body.start_byte:
        if sf.lang == "python":
            nm = f.node.child_by_field_name("name")
            if nm is not None and nm.start_byte == o.start_byte:
                return HitVerdict("self-def", func=f.name)
        d = f.node.child_by_field_name("declarator")
        name_node = None
        if d is not None:
            for x in walk(d):
                if x.type in ("identifier", "field_identifier") and txt(x) == f.name:
                    name_node = x
                    break
        if name_node is not None and name_node.start_byte == o.start_byte:
            return HitVerdict("self-def", func=f.name)
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
    v = HitVerdict("sliced", func=f.name, result=r, escapes=r.escapes)
    v.push_up = r.push_up
    v.push_values = r.globals
    return v


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


def _file_scope(sf, o, symbol):
    for a in _ancestors(o):
        t = a.type
        if t == "declaration" and a.parent is not None and a.parent.type == "translation_unit":
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
