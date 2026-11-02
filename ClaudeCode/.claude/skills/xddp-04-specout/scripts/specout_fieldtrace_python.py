"""specout_fieldtrace.py の Python のアダプタ。

型の定義は class（dataclass・NamedTuple の注釈つきのフィールド、__slots__、__init__ の中の self.x =）。
受け手の型は self・引数の型注釈・同じ関数の中の `x = T(...)`・`x: T = ...`・`copy.copy(y)` から求め、決まらなければ None。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specout_slice as SL  # noqa: E402
from specout_fieldtrace import (BYTES, Facts, FieldCopy, FunctionKey, MemberRef, SinkCall,  # noqa: E402
                                TypeDef, WholeCopy, all_fields)

SINK_CALLS = {"print"}
SINK_METHODS = {"write", "writelines", "send", "sendall", "sendto"}
SINK_QUALIFIED = {("struct", "pack"), ("struct", "pack_into"), ("json", "dump"), ("json", "dumps"),
                  ("pickle", "dump"), ("pickle", "dumps"), ("marshal", "dump"), ("marshal", "dumps")}
LOG_OBJECTS = {"logging", "logger", "log", "LOGGER", "LOG"}
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "critical", "exception", "log"}
SAME_TYPE_CALLS = {"copy", "deepcopy", "replace"}                  # copy.copy・copy.deepcopy・dataclasses.replace
TO_BYTES_CALLS = {"dumps", "dump", "asdict", "astuple", "vars"}     # pickle.dumps・dataclasses.asdict 等


def line_of(n) -> int:
    return n.start_point[0] + 1


def same(a, b) -> bool:
    return a is not None and b is not None and a.start_byte == b.start_byte and a.end_byte == b.end_byte \
        and a.type == b.type


def ann_name(n):
    """型注釈の節から素の型名（`Optional[T]`・`list[T]` は T を取らず、外側の名前。`"T"` は T）。"""
    if n is None:
        return None
    if n.type == "type" and n.named_children:
        n = n.named_children[0]
    t = n.type
    if t == "identifier":
        return SL.txt(n)
    if t == "attribute":
        a = n.child_by_field_name("attribute")
        return SL.txt(a) if a is not None else None
    if t == "string":
        s = SL.txt(n).strip("'\"")
        return s.split(".")[-1] if s.replace(".", "").replace("_", "").isalnum() else None
    if t in ("subscript", "generic_type"):
        if t == "subscript":
            v = n.child_by_field_name("value")
            outer = SL.txt(v) if v is not None else ""
            if outer.split(".")[-1] == "Optional":
                subs = n.children_by_field_name("subscript")
                return ann_name(subs[0]) if subs else None
            return outer.split(".")[-1] or None
        return ann_name(n.named_children[0]) if n.named_children else None
    return None


def call_parts(fn):
    """呼び出しの関数の節から (修飾の最後, 名前)。`a.b.c(...)` は ('b', 'c')、`f(...)` は (None, 'f')。"""
    if fn is None:
        return None, None
    if fn.type == "identifier":
        return None, SL.txt(fn)
    if fn.type == "attribute":
        obj, attr = fn.child_by_field_name("object"), fn.child_by_field_name("attribute")
        q = None
        if obj is not None:
            q = SL.txt(obj) if obj.type == "identifier" else (
                SL.txt(obj.child_by_field_name("attribute")) if obj.type == "attribute" else None)
        return q, (SL.txt(attr) if attr is not None else None)
    return None, None


class PythonAdapter:
    lang = "python"

    def __init__(self, ctx):
        self.ctx = ctx
        self.repo = SL.Repo(ctx.repo_path, ctx.excludes, ctx.h_as)
        self.facts = Facts()
        self._fields_cache = {}

    def fields(self, t) -> dict:
        if t not in self._fields_cache:
            self._fields_cache[t] = all_fields(self.facts, t)
        return self._fields_cache[t]

    def canon(self, name):
        return self.facts.canon(name) if name else None

    def collect(self) -> Facts:
        sfs = []
        for rel in self.ctx.files:
            try:
                sfs.append((rel, self.repo.file(rel)))
            except (OSError, ValueError):
                continue
        for rel, sf in sfs:
            self.index_file(rel, sf)
        self._fields_cache.clear()
        for rel, sf in sfs:
            for f in sf.funcs():
                self.scan_function(rel, f)
        return self.facts

    # -- 型の索引 --
    def index_file(self, rel: str, sf) -> None:
        for n in SL.walk(sf.root):
            if n.type != "class_definition":
                continue
            nm = n.child_by_field_name("name")
            body = n.child_by_field_name("body")
            if nm is None or body is None:
                continue
            td = TypeDef(SL.txt(nm), rel, line_of(n))
            sup = n.child_by_field_name("superclasses")
            for b in (sup.named_children if sup is not None else []):
                if b.type in ("identifier", "attribute"):
                    bn = ann_name(b)
                    if bn and bn not in ("object", "NamedTuple", "Enum", "IntEnum"):
                        td.bases.append(bn)
            for st in body.named_children:
                d = st.child_by_field_name("definition") if st.type == "decorated_definition" else st
                if d is not None and d.type == "function_definition":
                    fname = SL.txt(d.child_by_field_name("name"))
                    td.methods.add(fname)
                    if fname == "__init__":
                        self._init_fields(td, d)
                    continue
                if st.type != "expression_statement":
                    continue
                for a in st.named_children:
                    if a.type != "assignment":
                        continue
                    left = a.child_by_field_name("left")
                    if left is None or left.type != "identifier":
                        continue
                    name = SL.txt(left)
                    if name == "__slots__":
                        right = a.child_by_field_name("right")
                        for s in (SL.walk(right) if right is not None else []):
                            if s.type == "string":
                                td.fields.setdefault(SL.txt(s).strip("'\""), None)
                    elif a.child_by_field_name("type") is not None:
                        td.fields[name] = ann_name(a.child_by_field_name("type"))
            one = Facts()
            one.types[td.name] = td
            self.facts.merge(one)

    def _init_fields(self, td: TypeDef, d) -> None:
        for x in SL.walk(d.child_by_field_name("body"), stop={"function_definition", "class_definition"}):
            if x.type != "assignment":
                continue
            left = x.child_by_field_name("left")
            if left is None or left.type != "attribute":
                continue
            obj, attr = left.child_by_field_name("object"), left.child_by_field_name("attribute")
            if obj is None or attr is None or SL.txt(obj) != "self":
                continue
            ty = ann_name(x.child_by_field_name("type"))
            right = x.child_by_field_name("right")
            if ty is None and right is not None and right.type == "call":
                ty = call_parts(right.child_by_field_name("function"))[1]
            td.fields.setdefault(SL.txt(attr), ty)

    # -- 関数 --
    def scope(self, f) -> dict:
        out = {}
        params = f.node.child_by_field_name("parameters")
        for p in (params.named_children if params is not None else []):
            if p.type in ("typed_parameter", "typed_default_parameter"):
                ids = [c for c in p.named_children if c.type == "identifier"]
                if ids:
                    out[SL.txt(ids[0])] = ann_name(p.child_by_field_name("type"))
        for x in SL.walk(f.body, stop={"function_definition", "class_definition", "lambda"}):
            if x.type != "assignment":
                continue
            left = x.child_by_field_name("left")
            if left is None or left.type != "identifier":
                continue
            ty = ann_name(x.child_by_field_name("type"))
            if ty is None:
                ty = self.etype(x.child_by_field_name("right"), f, out)
            if ty:
                out[SL.txt(left)] = ty
        return out

    def etype(self, n, f, scope):
        if n is None:
            return None
        t = n.type
        if t == "identifier":
            nm = SL.txt(n)
            if nm == "self" and f.cls:
                return self.canon(f.cls)
            return self.canon(scope.get(nm))
        if t == "attribute":
            base = self.etype(n.child_by_field_name("object"), f, scope)
            attr = n.child_by_field_name("attribute")
            if base and attr is not None:
                return self.canon(self.fields(base).get(SL.txt(attr)))
            return None
        if t == "parenthesized_expression" and n.named_children:
            return self.etype(n.named_children[0], f, scope)
        if t == "call":
            q, name = call_parts(n.child_by_field_name("function"))
            if name in SAME_TYPE_CALLS:
                args = n.child_by_field_name("arguments")
                a0 = args.named_children[0] if (args is not None and args.named_children) else None
                return self.etype(a0, f, scope)
            return self.canon(name)
        return None

    def qname(self, f) -> str:
        return f"{f.cls}::{f.name}" if f.cls else f.name

    def scan_function(self, rel: str, f) -> None:
        fk = FunctionKey(rel, self.qname(f), line_of(f.node))
        self.facts.functions.add(fk)
        scope = self.scope(f)
        for x in SL.walk(f.body, stop={"function_definition", "class_definition", "lambda"}):
            t = x.type
            if t == "attribute":
                self._attr_ref(x, f, scope, fk)
            elif t == "assignment":
                self._assignment(x, f, scope, fk)
            elif t == "call":
                self._call(x, f, scope, fk, rel)

    def _attr_ref(self, x, f, scope, fk) -> None:
        attr = x.child_by_field_name("attribute")
        if attr is None:
            return
        p = x.parent
        if p is not None and p.type == "call" and same(p.child_by_field_name("function"), x):
            return
        recv = self.etype(x.child_by_field_name("object"), f, scope)
        write = p is not None and p.type == "assignment" and same(p.child_by_field_name("left"), x)
        self.facts.refs.append(MemberRef(fk, recv, SL.txt(attr), write, line_of(x)))

    def _member(self, n, f, scope):
        if n is None or n.type != "attribute":
            return None
        attr = n.child_by_field_name("attribute")
        if attr is None:
            return None
        return self.etype(n.child_by_field_name("object"), f, scope), SL.txt(attr)

    def _assignment(self, x, f, scope, fk) -> None:
        lt = self._member(x.child_by_field_name("left"), f, scope)
        rt = self._member(x.child_by_field_name("right"), f, scope)
        if lt and rt:
            self.facts.copies.append(FieldCopy(fk, rt[0], rt[1], lt[0], lt[1], "assign", line_of(x)))

    def _call(self, x, f, scope, fk, rel) -> None:
        q, name = call_parts(x.child_by_field_name("function"))
        args = x.child_by_field_name("arguments")
        argv = args.named_children if args is not None else []
        if (q, name) in SINK_QUALIFIED or (q is None and name in SINK_CALLS) or (q is not None and name in SINK_METHODS) \
                or (q in LOG_OBJECTS and name in LOG_METHODS):
            self.facts.sinks.append(SinkCall(fk, f"{q}.{name}" if q else name, line_of(x)))
        if name in TO_BYTES_CALLS and argv:
            st = self.etype(argv[0], f, scope)
            if st:
                self.facts.wholes.append(WholeCopy(fk, rel, st, BYTES, f"{q}.{name}" if q else name, line_of(x)))
            return
        if name in SAME_TYPE_CALLS and argv:
            st = self.etype(argv[0], f, scope)
            if st:
                self.facts.wholes.append(WholeCopy(fk, rel, st, st, f"{q}.{name}" if q else name, line_of(x)))
            return
        tp = self.canon(name)
        if not tp:
            return
        order = list(self.fields(tp).keys())
        pos = 0
        for a in argv:
            if a.type == "keyword_argument":
                kn, kv = a.child_by_field_name("name"), a.child_by_field_name("value")
                src = self._member(kv, f, scope)
                if src and kn is not None:
                    self.facts.copies.append(FieldCopy(fk, src[0], src[1], tp, SL.txt(kn), "kwargs", line_of(a)))
            else:
                src = self._member(a, f, scope)
                if src:
                    dst = order[pos] if pos < len(order) else None
                    self.facts.copies.append(FieldCopy(fk, src[0], src[1], tp, dst, "args", line_of(a)))
                pos += 1
