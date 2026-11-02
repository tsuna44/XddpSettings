"""specout_fieldtrace.py の規則判定のアダプタ（tree-sitter を使わない。標準ライブラリのみ）。

C / C++ / Python のファイルを字句で読み、型の定義（struct・class の本体の宣言）・フィールドの参照（`.f`・`->f`）・
フィールドからフィールドへの代入・`memcpy` の `sizeof(型)`・書き出しの呼び出しを取り出す。受け手の型は決めない
（本体はフィールドの名前で数え、候補はすべて name-only になる）。関数の範囲は判定エンジンの規則判定と同じ（specout_slice.RuleFile）。
"""
from __future__ import annotations

import bisect
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specout_slice as SL  # noqa: E402
from specout_fieldtrace import (BYTES, Facts, FieldCopy, FunctionKey, MemberRef, SinkCall,  # noqa: E402
                                TypeDef, WholeCopy, lang_of)

ID = r"[A-Za-z_]\w*"
C_TYPE_HEAD = re.compile(rf"\b(struct|class|union)\s+(?:{ID}\s+)*?({ID})?\s*(?:final\s*)?(?::\s*([^{{;]*))?\{{")
C_TYPEDEF_TAIL = re.compile(rf"^\s*({ID})\s*;")
C_TYPEDEF_ALIAS = re.compile(rf"\btypedef\s+(?:struct|class|union)\s+({ID})\s+({ID})\s*;")
C_MEMBER_REF = re.compile(rf"(?:\.|->)\s*({ID})\b(?!\s*\()")
C_FIELD_COPY = re.compile(rf"(?:\.|->)\s*({ID})\s*=(?!=)\s*[\w\s\[\]\(\)\*&]*?(?:\.|->)\s*({ID})\s*;")
C_SIZEOF_COPY = re.compile(rf"\b(memcpy|memmove)\s*\(([^;]*?)\bsizeof\s*\(?\s*(?:struct\s+)?({ID})\s*\)?")
C_SINK = re.compile(r"\b(fwrite|write|send|sendto|sendmsg|printf|fprintf|dprintf|snprintf|sprintf|vfprintf|puts|fputs|"
                    r"syslog|format|print)\s*\(")
C_STREAM = re.compile(r"\b(?:std\s*::\s*)?(cout|cerr|clog)\s*<<")
PY_CLASS = re.compile(rf"^([ \t]*)class\s+({ID})\s*(?:\(([^)]*)\))?\s*:", re.M)
PY_FIELD_ANN = re.compile(rf"^[ \t]+({ID})\s*:\s*[^=\n]+(?:=.*)?$", re.M)
PY_SELF_ATTR = re.compile(rf"\bself\.({ID})\s*(?::[^=\n]+)?=(?!=)")
PY_DEF = re.compile(rf"^[ \t]+def\s+({ID})", re.M)
PY_MEMBER_REF = re.compile(rf"\.({ID})\b(?!\s*\()")
PY_FIELD_COPY = re.compile(rf"\.({ID})\s*=(?!=)\s*{ID}(?:\.{ID})*\.({ID})\s*$", re.M)
PY_SINK = re.compile(r"(?:\bprint|\.write|\.writelines|\.send|\.sendall|\.sendto|\bstruct\.pack(?:_into)?|"
                     r"\b(?:json|pickle|marshal)\.dumps?|\b(?:logging|logger|log)\.(?:debug|info|warning|warn|error|"
                     r"critical|exception|log))\s*\(")
QUALIFIER_WORDS = {"public", "protected", "private", "virtual"}


def _match_brace(code: str, open_idx: int) -> int:
    depth = 0
    for k in range(open_idx, len(code)):
        ch = code[k]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return k
    return -1


def _top_level(body: str) -> str:
    """入れ子の波かっこの中身を空白にした本体（メンバーの宣言だけを残す）。"""
    out, depth = [], 0
    for ch in body:
        if ch == "{":
            depth += 1
            out.append(" ")
        elif ch == "}":
            depth = max(0, depth - 1)
            out.append(";" if depth == 0 else " ")
        else:
            out.append(ch if depth == 0 else " ")
    return "".join(out)


class RuleAdapter:
    lang = "rule"

    def __init__(self, ctx):
        self.ctx = ctx
        self.facts = Facts()
        self.class_spans = {}   # {ファイル: [(開始, 終了, クラス名)]}

    def collect(self) -> Facts:
        rfs = []
        for rel in self.ctx.files:
            lang = lang_of(rel, self.ctx.h_as)
            try:
                rfs.append((rel, lang, SL.RuleFile(os.path.join(self.ctx.repo_path, rel), lang)))
            except (OSError, ValueError):
                continue
        for rel, lang, rf in rfs:
            if lang == "python":
                self._py_types(rel, rf)
            else:
                self._c_types(rel, rf)
        for rel, lang, rf in rfs:
            for fn in rf.funcs:
                self._scan(rel, lang, rf, fn)
        return self.facts

    # -- 型 --
    def _add_type(self, td: TypeDef) -> None:
        one = Facts()
        one.types[td.name] = td
        self.facts.merge(one)

    def _line(self, rf, pos: int) -> int:
        return bisect.bisect_right(rf.offs, pos)

    def _c_types(self, rel: str, rf) -> None:
        code = rf.struct
        for m in C_TYPEDEF_ALIAS.finditer(code):
            self.facts.aliases.setdefault(m.group(2), m.group(1))
        for m in C_TYPE_HEAD.finditer(code):
            open_idx = m.end() - 1
            close = _match_brace(code, open_idx)
            if close < 0:
                continue
            tag = m.group(2)
            name = tag
            before = code[max(0, m.start() - 40):m.start()]
            tail = C_TYPEDEF_TAIL.match(code[close + 1:close + 80])
            if re.search(r"\btypedef\s*$", before) and tail:
                name = tail.group(1)
                if tag and tag != name:
                    self.facts.aliases[tag] = name
            if not name:
                continue
            td = TypeDef(name, rel, self._line(rf, m.start()))
            if m.group(3):
                for b in m.group(3).split(","):
                    words = [w for w in re.findall(ID, b.split("<")[0]) if w not in QUALIFIER_WORDS]
                    if words:
                        td.bases.append(words[-1])
            for stmt in _top_level(code[open_idx + 1:close]).split(";"):
                s = re.sub(r"\b(?:public|protected|private)\s*:", " ", stmt).strip()
                if not s:
                    continue
                fm = re.search(rf"({ID})\s*\(", s)
                if fm and not re.search(r"\(\s*\*", s):
                    td.methods.add(fm.group(1))
                    continue
                if re.match(r"(?:using|typedef|friend|enum|static_assert|template)\b", s):
                    continue
                s = re.sub(r"=.*$", "", s)
                s = re.sub(r"\[[^\]]*\]", "", s)
                s = re.sub(r":\s*\d+\s*$", "", s)
                parts = s.split(",")
                first = re.findall(ID, parts[0])
                if len(first) < 2:      # 型と名前がそろわない文（マクロ等）は宣言とみなさない
                    continue
                td.fields.setdefault(first[-1], None)
                for part in parts[1:]:
                    ids = re.findall(ID, part)
                    if ids:
                        td.fields.setdefault(ids[-1], None)
            self._add_type(td)
            if rel.endswith((".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h")):
                self.class_spans.setdefault(rel, []).append((open_idx, close, name))

    def _py_types(self, rel: str, rf) -> None:
        code = rf.code
        for m in PY_CLASS.finditer(code):
            indent = len(m.group(1).expandtabs())
            start = m.end()
            end = len(code)
            for lm in re.finditer(r"^([ \t]*)\S", code[start:], re.M):
                if len(lm.group(1).expandtabs()) <= indent and lm.start() > 0:
                    end = start + lm.start()
                    break
            block = code[start:end]
            td = TypeDef(m.group(2), rel, self._line(rf, m.start()))
            for b in (m.group(3) or "").split(","):
                words = re.findall(ID, b)
                if words and words[-1] not in ("object", "NamedTuple", "Enum", "IntEnum"):
                    td.bases.append(words[-1])
            body_indent = None
            for fm in PY_FIELD_ANN.finditer(block):
                line_indent = len(fm.group(0)) - len(fm.group(0).lstrip())
                if body_indent is None:
                    body_indent = line_indent
                if line_indent == body_indent and fm.group(1) not in ("return",):
                    td.fields.setdefault(fm.group(1), None)
            for sm in PY_SELF_ATTR.finditer(block):
                td.fields.setdefault(sm.group(1), None)
            td.methods |= set(PY_DEF.findall(block))
            self._add_type(td)
            self.class_spans.setdefault(rel, []).append((start, end, m.group(2)))

    # -- 関数 --
    def _qname(self, rel: str, lang: str, rf, fn) -> tuple:
        head = rf.struct[fn.head_start:fn.body_open]
        if lang != "python":
            qm = re.search(rf"({ID})\s*(?:<[^<>]*>)?\s*::\s*~?({ID})\s*\(", head)
            if qm:
                return f"{qm.group(1)}::{qm.group(2)}", qm.group(1)
        for s, e, cls in self.class_spans.get(rel, []):
            if s <= fn.head_start <= e:
                return f"{cls}::{fn.name}", cls
        return fn.name, None

    def _scan(self, rel: str, lang: str, rf, fn) -> None:
        qname, cls = self._qname(rel, lang, rf, fn)
        fk = FunctionKey(rel, qname, self._line(rf, fn.head_start))
        self.facts.functions.add(fk)
        body_start, body = fn.body_open, rf.code[fn.body_open:fn.body_close]
        ref_re, copy_re, sink_re = ((PY_MEMBER_REF, PY_FIELD_COPY, PY_SINK) if lang == "python"
                                    else (C_MEMBER_REF, C_FIELD_COPY, C_SINK))
        for m in ref_re.finditer(body):
            write = bool(re.match(r"\s*=(?!=)", body[m.end():m.end() + 3]))
            self.facts.refs.append(MemberRef(fk, None, m.group(1), write, self._line(rf, body_start + m.start())))
        if lang != "python" and cls and self.facts.types.get(cls):
            fields = self.facts.types[cls].fields
            for m in re.finditer(rf"(?<![\.\w>:])({ID})\b(?!\s*\()", body):
                if m.group(1) in fields:
                    self.facts.refs.append(MemberRef(fk, None, m.group(1), False,
                                                     self._line(rf, body_start + m.start()), implicit=True))
        for m in copy_re.finditer(body):
            self.facts.copies.append(FieldCopy(fk, None, m.group(2), None, m.group(1), "assign",
                                               self._line(rf, body_start + m.start())))
        if lang != "python":
            for m in C_SIZEOF_COPY.finditer(body):
                self.facts.wholes.append(WholeCopy(fk, rel, m.group(3), BYTES, m.group(1),
                                                   self._line(rf, body_start + m.start())))
            for m in C_STREAM.finditer(body):
                self.facts.sinks.append(SinkCall(fk, "operator<<", self._line(rf, body_start + m.start())))
        for m in sink_re.finditer(body):
            self.facts.sinks.append(SinkCall(fk, m.group(0).rstrip("( ").strip("."),
                                             self._line(rf, body_start + m.start())))
