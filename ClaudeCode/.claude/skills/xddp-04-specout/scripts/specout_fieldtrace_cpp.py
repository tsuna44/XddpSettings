"""specout_fieldtrace.py の C++ のアダプタ。

C のアダプタの事実の取り出しに、次を足す: 判定エンジン（specout_slice.Repo）の受け手の型の解決（決まらないときだけ）、
メソッドの中の修飾なしのメンバー（暗黙の this。基底クラスのメンバーを含む）、メンバー初期化子並びの写し、
型の名前の呼び出し（コンストラクタの引数）、ストリームへの出力。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specout_slice as SL  # noqa: E402
from specout_fieldtrace import FieldCopy, strip_templates  # noqa: E402
from specout_fieldtrace_c import SINKS, CAdapter, call_name, line_of, same, strip_value  # noqa: E402

CPP_SINKS = SINKS | {"format", "format_to", "print", "println"}


class CppAdapter(CAdapter):
    lang = "cpp"
    sinks = CPP_SINKS

    def prepare(self) -> None:
        try:
            self.repo.build_index()
            self._repo_ok = True
        except Exception:  # noqa: BLE001 — 索引を作れなくても自前の解決で続ける
            self._repo_ok = False

    def qname(self, f) -> str:
        if f.cls:
            return f"{strip_templates(f.cls).split('::')[-1]}::{f.name}"
        return f.name

    def current_class(self, f):
        return self.canon(f.cls) if f.cls else None

    def member_type(self, f, name):
        cls = self.current_class(f)
        if cls and name in self.fields(cls):
            return self.canon(self.fields(cls)[name])
        return None

    def implicit_member(self, x, f, scope):
        cls = self.current_class(f)
        if not cls:
            return None
        nm = SL.txt(x)
        if nm in scope or nm not in self.fields(cls):
            return None
        p = x.parent
        if p is not None:
            if p.type == "call_expression" and same(p.child_by_field_name("function"), x):
                return None
            if p.type == "field_expression" and same(p.child_by_field_name("field"), x):
                return None      # `a.x` の x（フィールド名の位置）。受け手の位置（`x.begin()` の x）は暗黙のメンバー
            if p.type == "qualified_identifier":
                return None
        return cls

    def etype(self, n, f, scope):
        t = super().etype(n, f, scope)
        if t is not None or n is None or not getattr(self, "_repo_ok", False):
            return t
        if n.type not in ("identifier", "field_expression", "call_expression", "this", "subscript_expression",
                          "pointer_expression", "parenthesized_expression", "new_expression", "qualified_identifier"):
            return None
        try:
            key = self.repo.expr_class(n, f)
        except Exception:  # noqa: BLE001
            return None
        return self.canon(key.split("::")[-1]) if key and key != SL.AMBIGUOUS else None

    def is_type_call(self, fn):
        if fn is None or fn.type not in ("identifier", "qualified_identifier", "template_function", "type_identifier"):
            return None
        return self.canon(call_name(fn))

    def scan_extra(self, f, scope, fk, rel) -> None:
        cls = self.current_class(f)
        if not cls:
            return
        for x in SL.walk(f.node, stop={"compound_statement"}):
            if x.type != "field_initializer":
                continue
            nm = next((c for c in x.named_children if c.type == "field_identifier"), None)
            args = next((c for c in x.named_children if c.type in ("argument_list", "initializer_list")), None)
            if nm is None or args is None or len(args.named_children) != 1:
                continue
            src = self._member_target(args.named_children[0], f, scope)
            if src:
                self.facts.copies.append(FieldCopy(fk, src[0], src[1], cls, SL.txt(nm), "member-init", line_of(x)))

    def stream_type_name(self, n, f, scope):
        n = strip_value(n)
        ty = super().stream_type_name(n, f, scope)
        if ty:
            return ty
        if n is not None and n.type == "identifier" and getattr(self, "_repo_ok", False):
            try:
                return self.repo.var_type(SL.txt(n), f)
            except Exception:  # noqa: BLE001
                return None
        return None
