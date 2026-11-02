"""specout_fieldtrace.py の C のアダプタ（C++ のアダプタの土台を兼ねる）。

tree-sitter の構文木から、型の定義・フィールドの参照・写し・丸ごとの写し・書き出しの事実を取り出す。
受け手の型は、引数・ローカル変数・ファイルスコープの変数の宣言、メンバーの連鎖、typedef から求める。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specout_slice as SL  # noqa: E402
from specout_fieldtrace import (BYTES, Facts, FieldCopy, FunctionKey, MemberRef, SinkCall,  # noqa: E402
                                TypeDef, WholeCopy, all_fields, strip_templates)

SINKS = {"fwrite", "write", "send", "sendto", "sendmsg", "printf", "fprintf", "dprintf", "snprintf", "sprintf",
         "vfprintf", "vsnprintf", "puts", "fputs", "fputc", "putc", "syslog"}
COPY_FUNCS = {"memcpy", "memmove"}
SPECIFIERS = ("struct_specifier", "class_specifier", "union_specifier")
FILE_SCOPE_PARENTS = ("translation_unit", "declaration_list", "linkage_specification", "preproc_if",
                      "preproc_ifdef", "preproc_else", "preproc_elif", "namespace_definition")


def line_of(n) -> int:
    return n.start_point[0] + 1


def same(a, b) -> bool:
    return a is not None and b is not None and a.start_byte == b.start_byte and a.end_byte == b.end_byte \
        and a.type == b.type


def strip_value(n):
    """括弧・キャストを外した値の節。"""
    for _ in range(8):
        if n is None:
            return None
        if n.type == "parenthesized_expression" and n.named_children:
            n = n.named_children[0]
            continue
        if n.type == "cast_expression":
            n = n.child_by_field_name("value")
            continue
        return n
    return n


def strip_addr(n):
    """`&x`・`(T*)&x`・`x` から x。"""
    n = strip_value(n)
    if n is not None and n.type == "pointer_expression" and n.child_by_field_name("operator") is not None \
            and SL.txt(n.child_by_field_name("operator")) == "&":
        return strip_value(n.child_by_field_name("argument"))
    return n


def call_name(fn):
    """呼び出しの関数の節から名前（修飾・テンプレート引数を除く。メソッドはメソッド名）。"""
    if fn is None:
        return None
    t = fn.type
    if t == "identifier":
        return SL.txt(fn)
    if t == "qualified_identifier":
        return call_name(fn.child_by_field_name("name"))
    if t == "template_function":
        return call_name(fn.child_by_field_name("name"))
    if t == "field_expression":
        f = fn.child_by_field_name("field")
        return SL.txt(f) if f is not None else None
    return None


class CAdapter:
    lang = "c"
    sinks = SINKS

    def __init__(self, ctx):
        self.ctx = ctx
        self.repo = SL.Repo(ctx.repo_path, ctx.excludes, ctx.h_as)
        self.facts = Facts()
        self._fields_cache = {}

    # -- 共通 --
    def fields(self, t) -> dict:
        if t not in self._fields_cache:
            self._fields_cache[t] = all_fields(self.facts, t)
        return self._fields_cache[t]

    def canon(self, name):
        return self.facts.canon(strip_templates(name)) if name else None

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
        self.prepare()
        for rel, sf in sfs:
            for f in sf.funcs():
                self.scan_function(rel, sf, f)
        return self.facts

    def prepare(self) -> None:
        """型の索引の後・関数の走査の前に呼ばれる（C++ が Repo の索引を作る）。"""

    # -- 型の索引 --
    def spec_name(self, n):
        """型の名前。`typedef struct tag {…} Name;` は typedef の名前を正とし、タグ名を別名にする（コード・CHD は typedef の名前で書くため）。"""
        nm = n.child_by_field_name("name")
        tag = SL._plain_type_name(nm) if nm is not None else None
        p = n.parent
        if p is not None and p.type == "type_definition":
            for d in p.children_by_field_name("declarator"):
                name = SL.c_decl(d)[0]
                if name:
                    if tag and tag != name:
                        self.facts.aliases[tag] = name
                    return name
        return tag

    def type_name(self, tn):
        return SL._plain_type_node(tn) if tn is not None else None

    def _add_fields(self, td: TypeDef, body) -> None:
        for m in body.named_children:
            if m.type == "template_declaration":
                m = next((c for c in reversed(m.named_children)
                          if c.type in ("field_declaration", "function_definition", "declaration")), None)
                if m is None:
                    continue
            if m.type == "field_declaration":
                tn = m.child_by_field_name("type")
                decls = m.children_by_field_name("declarator")
                if not decls and tn is not None and tn.type in SPECIFIERS and tn.child_by_field_name("name") is None:
                    inner = tn.child_by_field_name("body")
                    if inner is not None:          # 名前の無い構造体・共用体のメンバーは外側のフィールドとして数える
                        self._add_fields(td, inner)
                    continue
                for d in decls:
                    nm, _p, _r, _a, fd = SL.c_decl(d)
                    if not nm:
                        continue
                    if fd is not None:
                        td.methods.add(nm)
                    else:
                        td.fields[nm] = self.type_name(tn)
            elif m.type in ("function_definition", "declaration"):
                for d in ([m.child_by_field_name("declarator")] if m.type == "function_definition"
                          else m.children_by_field_name("declarator")):
                    if d is None:
                        continue
                    nm, _p, _r, _a, fd = SL.c_decl(d)
                    if nm and fd is not None:
                        td.methods.add(nm)

    def index_file(self, rel: str, sf) -> None:
        for n in SL.walk(sf.root):
            t = n.type
            if t in SPECIFIERS:
                body = n.child_by_field_name("body")
                name = self.spec_name(n) if body is not None else None
                if not name:
                    continue
                td = TypeDef(name, rel, line_of(n))
                for c in n.named_children:
                    if c.type == "base_class_clause":
                        for b in c.named_children:
                            if b.type in ("type_identifier", "qualified_identifier", "template_type"):
                                bn = SL._plain_type_node(b)
                                if bn:
                                    td.bases.append(bn)
                self._add_fields(td, body)
                one = Facts()
                one.types[name] = td
                self.facts.merge(one)
            elif t == "type_definition":
                target = self.type_name(n.child_by_field_name("type"))
                for d in n.children_by_field_name("declarator"):
                    nm = SL.c_decl(d)[0]
                    if nm and target and nm != target:
                        self.facts.aliases.setdefault(nm, target)
            elif t == "alias_declaration":
                nm = n.child_by_field_name("name")
                target = self.type_name(n.child_by_field_name("type"))
                if nm is not None and target and SL.txt(nm) != target:
                    self.facts.aliases.setdefault(SL.txt(nm), target)
            elif t == "declaration" and n.parent is not None and n.parent.type in FILE_SCOPE_PARENTS:
                tp = self.type_name(n.child_by_field_name("type"))
                for d in n.children_by_field_name("declarator"):
                    nm, _p, _r, _a, fd = SL.c_decl(d)
                    if nm and fd is None and tp:
                        self.facts.global_vars.setdefault(nm, tp)

    # -- 関数 --
    def qname(self, f) -> str:
        return f.name

    def current_class(self, f):
        return None

    def scope(self, f) -> dict:
        """引数・ローカル変数の名前 → 型の素の名前。"""
        out = {}
        d = f.node.child_by_field_name("declarator")
        fd = SL.c_decl(d)[4] if d is not None else None
        plist = fd.child_by_field_name("parameters") if fd is not None else None
        for p in (plist.named_children if plist is not None else []):
            if p.type not in ("parameter_declaration", "optional_parameter_declaration"):
                continue
            pd = p.child_by_field_name("declarator")
            nm = SL.c_decl(pd)[0] if pd is not None else None
            if nm:
                out[nm] = self.type_name(p.child_by_field_name("type"))
        for x in SL.walk(f.body, stop={"lambda_expression", "function_definition"}):
            if x.type == "declaration":
                tp = self.type_name(x.child_by_field_name("type"))
                for dd in x.children_by_field_name("declarator"):
                    nm = SL.c_decl(dd)[0]
                    if nm:
                        out[nm] = tp if tp != "auto" else self._auto_type(dd, f, out)
            elif x.type == "for_range_loop":
                dd = x.child_by_field_name("declarator")
                nm = SL.c_decl(dd)[0] if dd is not None else None
                if nm:
                    out[nm] = self.type_name(x.child_by_field_name("type"))
        return out

    def _auto_type(self, d, f, scope):
        if d is not None and d.type == "init_declarator":
            return self.etype(d.child_by_field_name("value"), f, scope)
        return None

    def etype(self, n, f, scope):
        """式の型（型の表の名前）。決まらなければ None。"""
        n = strip_value(n) if n is not None and n.type != "cast_expression" else n
        if n is None:
            return None
        t = n.type
        if t == "identifier":
            nm = SL.txt(n)
            if nm in scope:
                return self.canon(scope[nm])
            m = self.member_type(f, nm)
            if m is not None:
                return m
            return self.canon(self.facts.global_vars.get(nm))
        if t == "field_expression":
            base = self.etype(n.child_by_field_name("argument"), f, scope)
            fld = n.child_by_field_name("field")
            if base and fld is not None:
                return self.canon(self.fields(base).get(SL.txt(fld)))
            return None
        if t in ("pointer_expression", "subscript_expression"):
            return self.etype(n.child_by_field_name("argument"), f, scope)
        if t == "parenthesized_expression":
            return self.etype(n.named_children[0] if n.named_children else None, f, scope)
        if t == "cast_expression":
            return self.canon(self.type_name(n.child_by_field_name("type")))
        if t == "this":
            return self.current_class(f)
        return None

    def member_type(self, f, name):
        """メソッドの中の修飾なしのメンバーの型（C は無し）。"""
        return None

    def implicit_member(self, x, f, scope):
        """修飾なしの名前 x がメソッドのクラスのフィールドなら、そのクラス（C は無し）。"""
        return None

    def is_write(self, x) -> bool:
        p = x.parent
        if p is None:
            return False
        if p.type == "assignment_expression" and same(p.child_by_field_name("left"), x):
            return True
        return p.type == "update_expression"

    def scan_function(self, rel: str, sf, f) -> None:
        fk = FunctionKey(rel, self.qname(f), line_of(f.node))
        self.facts.functions.add(fk)
        scope = self.scope(f)
        for x in SL.walk(f.body, stop={"lambda_expression", "function_definition"}):
            t = x.type
            if t == "field_expression":
                self._field_ref(x, f, scope, fk)
            elif t == "identifier":
                cls = self.implicit_member(x, f, scope)
                if cls:
                    self.facts.refs.append(MemberRef(fk, cls, SL.txt(x), self.is_write(x), line_of(x), implicit=True))
            elif t == "assignment_expression":
                self._assignment(x, f, scope, fk, rel)
            elif t == "init_declarator":
                self._init_declarator(x, f, scope, fk, rel)
            elif t == "call_expression":
                self._call(x, f, scope, fk, rel)
            elif t == "compound_literal_expression":
                tp = self.canon(self.type_name(x.child_by_field_name("type")))
                v = x.child_by_field_name("value")
                if tp and v is not None:
                    self._initializer(v, tp, f, scope, fk)
            elif t == "binary_expression":
                self._shift_sink(x, f, scope, fk)
        self.scan_extra(f, scope, fk, rel)

    def scan_extra(self, f, scope, fk, rel) -> None:
        """C++ のメンバー初期化子並び等（C は無し）。"""

    def _field_ref(self, x, f, scope, fk) -> None:
        fld = x.child_by_field_name("field")
        if fld is None or fld.type != "field_identifier":
            return
        p = x.parent
        if p is not None and p.type == "call_expression" and same(p.child_by_field_name("function"), x):
            return   # メソッドの呼び出し
        recv = self.etype(x.child_by_field_name("argument"), f, scope)
        self.facts.refs.append(MemberRef(fk, recv, SL.txt(fld), self.is_write(x), line_of(x)))

    def _member_target(self, n, f, scope):
        """代入の左辺・右辺がフィールドなら (型, フィールド名)、そうでなければ None。"""
        n = strip_value(n)
        if n is None:
            return None
        if n.type == "field_expression":
            fld = n.child_by_field_name("field")
            if fld is None or fld.type != "field_identifier":
                return None
            return self.etype(n.child_by_field_name("argument"), f, scope), SL.txt(fld)
        if n.type == "identifier":
            cls = self.implicit_member(n, f, scope)
            if cls:
                return cls, SL.txt(n)
        return None

    def _assignment(self, x, f, scope, fk, rel) -> None:
        op = x.child_by_field_name("operator")
        if op is not None and SL.txt(op) != "=":
            return
        left, right = x.child_by_field_name("left"), x.child_by_field_name("right")
        lt, rt = self._member_target(left, f, scope), self._member_target(right, f, scope)
        if lt and rt:
            self.facts.copies.append(FieldCopy(fk, rt[0], rt[1], lt[0], lt[1], "assign", line_of(x)))
            return
        rv = strip_value(right)
        if rv is None or rv.type == "call_expression":
            return
        lty, rty = self.etype(left, f, scope), self.etype(rv, f, scope)
        if lty and rty:
            self.facts.wholes.append(WholeCopy(fk, rel, rty, lty, "assign", line_of(x)))

    def _initializer(self, v, tp, f, scope, fk) -> None:
        """初期化子並び（位置・指示付き）からの写し。"""
        order = list(self.fields(tp).keys())
        idx = 0
        for e in v.named_children:
            dst_field, val = None, e
            if e.type == "initializer_pair":
                ds = e.child_by_field_name("designator")
                ds = ds if ds is not None else (e.named_children[0] if e.named_children else None)
                if ds is not None and ds.type == "field_designator" and ds.named_children:
                    dst_field = SL.txt(ds.named_children[0])
                val = e.child_by_field_name("value")
            else:
                dst_field = order[idx] if idx < len(order) else None
                idx += 1
            src = self._member_target(val, f, scope)
            if src and dst_field:
                self.facts.copies.append(FieldCopy(fk, src[0], src[1], tp, dst_field, "init", line_of(e)))

    def _ctor_args(self, args, tp, f, scope, fk, rel, line) -> None:
        srcs = [self._member_target(a, f, scope) for a in args.named_children]
        for s in srcs:
            if s:
                self.facts.copies.append(FieldCopy(fk, s[0], s[1], tp, None, "ctor-args", line))
        if len(args.named_children) == 1 and not srcs[0]:
            st = self.etype(args.named_children[0], f, scope)
            if st:
                self.facts.wholes.append(WholeCopy(fk, rel, st, tp, "copy-init", line))

    def _init_declarator(self, x, f, scope, fk, rel) -> None:
        decl = x.parent
        if decl is None or decl.type != "declaration":
            return
        tp = self.canon(self.type_name(decl.child_by_field_name("type")))
        v = x.child_by_field_name("value")
        if tp is None or v is None:
            return
        if v.type == "initializer_list":
            self._initializer(v, tp, f, scope, fk)
        elif v.type == "argument_list":
            self._ctor_args(v, tp, f, scope, fk, rel, line_of(x))
        else:
            vv = strip_value(v)
            if vv is not None and vv.type != "call_expression":
                st = self.etype(vv, f, scope)
                if st and st != tp:
                    self.facts.wholes.append(WholeCopy(fk, rel, st, tp, "init", line_of(x)))
                elif st:
                    self.facts.wholes.append(WholeCopy(fk, rel, st, tp, "init", line_of(x)))

    def is_type_call(self, fn):
        """呼び出しの関数の節が型の名前（コンストラクタの呼び出し・関数形式のキャスト）なら型の表の名前。"""
        return None

    def _call(self, x, f, scope, fk, rel) -> None:
        fn = x.child_by_field_name("function")
        name = call_name(fn)
        args = x.child_by_field_name("arguments")
        if name in COPY_FUNCS and args is not None and len(args.named_children) >= 2:
            dst, src = strip_addr(args.named_children[0]), strip_addr(args.named_children[1])
            st = self.etype(src, f, scope)
            dt = self.etype(dst, f, scope)
            if st:
                self.facts.wholes.append(WholeCopy(fk, rel, st, dt or BYTES, name, line_of(x)))
            if not dt:
                self.facts.sinks.append(SinkCall(fk, name, line_of(x)))
            return
        if name in self.sinks:
            self.facts.sinks.append(SinkCall(fk, name, line_of(x)))
            return
        tp = self.is_type_call(fn)
        if tp and args is not None:
            self._ctor_args(args, tp, f, scope, fk, rel, line_of(x))

    def _shift_sink(self, x, f, scope, fk) -> None:
        op = x.child_by_field_name("operator")
        if op is None or SL.txt(op) != "<<":
            return
        p = x.parent
        if p is not None and p.type == "binary_expression" and p.child_by_field_name("operator") is not None \
                and SL.txt(p.child_by_field_name("operator")) == "<<":
            return
        left = x
        while left is not None and left.type == "binary_expression":
            left = left.child_by_field_name("left")
        if left is None:
            return
        text = SL.txt(left)
        stream = text.split("::")[-1] in ("cout", "cerr", "clog")
        if not stream:
            ty = self.stream_type_name(left, f, scope)
            stream = bool(ty) and "stream" in ty.lower()
        if stream:
            self.facts.sinks.append(SinkCall(fk, "operator<<", line_of(x)))

    def stream_type_name(self, n, f, scope):
        n = strip_value(n)
        if n is not None and n.type == "identifier":
            return scope.get(SL.txt(n)) or self.facts.global_vars.get(SL.txt(n))
        return None
