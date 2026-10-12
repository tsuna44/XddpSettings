"""
specout_macros.py — C/C++ のマクロの事前走査と種類の判定（波紋調査のスライス判定の前処理）

`specout_slice.py`（構文解析の前にマクロを置き換える）と `specout_bfs.py`（`init` が置き換えたマクロの数を
state と discovery-log に書く）が共有する。サブコマンドは持たない。標準ライブラリのみ。

- C/C++ の拡張子と言語の対応（`C_CXX_EXT_LANG`・`c_cxx_lang`）。`.h` の言語は呼び出し元が渡す（state の slice_h_as）。
- コメント・文字列・プリプロセッサ指令の字句の走査（`lex`）。構文解析はしない。
- リポジトリの `#define` の事前走査（`collect_definitions`）と、置き換えるマクロの表（`neutralize_table`）:
  オブジェクト形式のマクロのうち、すべての定義が同じ1つの種類（名前空間マクロ・宣言を飾るマクロ）に当たるもの、
  および空の定義を持つ「構造を開く側・閉じる側」の組（`empty_pairs`。両方を空にする）。
- 置き換え（`apply_table`）: 同じ行の中だけで置き換え、改行を変えない。プリプロセッサ指令の行・コメント・文字列の中は置き換えない。
"""

from __future__ import annotations

import bisect
import os
import re
from dataclasses import dataclass
from functools import lru_cache

# C/C++ の拡張子と言語（`.h` は呼び出し元が state の slice_h_as で決める）。拡張子の大文字・小文字は区別する。
C_CXX_EXT_LANG = {".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp",
                  ".hh": "cpp", ".hxx": "cpp"}
C_CXX_EXTS = tuple(sorted(C_CXX_EXT_LANG))
CPP_EXTS = tuple(sorted(e for e, lang in C_CXX_EXT_LANG.items() if lang == "cpp"))
VCS_DIRS = {".git", ".svn", ".hg", ".bzr", "CVS"}

KIND_NAMESPACE = "namespace"
KIND_DECORATOR = "decorator"
KIND_EMPTY_PAIR = "empty-pair"
MAX_DEPTH = 8

# 宣言を飾るマクロの本体に現れてよい語（この一覧の外の語を含む本体は宣言を飾るマクロにしない）。
_DECORATOR_WORDS = {
    "inline", "__inline", "__inline__", "__forceinline", "constexpr", "consteval", "constinit", "static",
    "extern", "const", "volatile", "noexcept", "explicit", "virtual", "export", "thread_local", "_Thread_local",
    "_Noreturn", "__cdecl", "__stdcall", "__fastcall", "__thiscall", "__vectorcall",
}
# 置き換えても残す語。virtual は定義の1つでも含めば、それ以外はすべての定義が含むときだけ残す。
_KEEP_IF_ALL = ("static", "extern", "thread_local")
_KEEP_IF_ANY = ("virtual",)


def c_cxx_lang(path: str, h_as: str = "c"):
    """ファイルの言語（`c` / `cpp`。C/C++ でなければ None）。`.h` は h_as。"""
    ext = os.path.splitext(path)[1]
    if ext == ".h":
        return h_as
    return C_CXX_EXT_LANG.get(ext)


def iter_c_cxx_files(root: str) -> list:
    """リポジトリのルートの下の C/C++ の拡張子のファイル（相対パス・`/` 区切り・昇順）。VCS のディレクトリを除く。
    除外パターン（SPECOUT_EXCLUDE_PATTERNS）は当てない（マクロの定義の出所を減らさないため）。"""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in VCS_DIRS]
        for name in filenames:
            if os.path.splitext(name)[1] in C_CXX_EXT_LANG:
                out.append(os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/"))
    return sorted(out)


# ---------------------------------------------------------------------------
# 字句の走査（コメント・文字列・プリプロセッサ指令）
# ---------------------------------------------------------------------------

_SIG = re.compile(rb'/\*|//|"|\'|\n')
_DIRECTIVE_START = re.compile(rb"[ \t]*#")
_STR_STOP = re.compile(rb'["\\\n]')
_CHR_STOP = re.compile(rb"['\\\n]")
_RAW_PREFIX = re.compile(rb"(?:u8|u|U|L)?R$")
_IDENT_BYTES = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_")


class Lexed:
    """`lex` の結果。spans＝コメント・文字列・文字リテラルの範囲、directives＝プリプロセッサ指令の範囲（継続行を含む）。"""

    def __init__(self, src: bytes, spans: list, directives: list):
        self.src = src
        self.spans = spans
        self.directives = directives
        self._span_starts = [s for s, _ in spans]
        self._dir_starts = [s for s, _ in directives]
        self._line_offs = None

    @staticmethod
    def _inside(starts, ranges, pos) -> bool:
        k = bisect.bisect_right(starts, pos) - 1
        return k >= 0 and ranges[k][0] <= pos < ranges[k][1]

    def in_comment_or_string(self, pos: int) -> bool:
        return self._inside(self._span_starts, self.spans, pos)

    def in_directive(self, pos: int) -> bool:
        return self._inside(self._dir_starts, self.directives, pos)

    def line_span(self, line_no: int):
        """1 始まりの行番号の (開始, 終了)（終了は改行の位置）。範囲外なら None。"""
        if self._line_offs is None:
            offs = [0]
            offs.extend(m.end() for m in re.finditer(rb"\n", self.src))
            self._line_offs = offs
        if not 0 < line_no <= len(self._line_offs):
            return None
        s = self._line_offs[line_no - 1]
        e = self._line_offs[line_no] - 1 if line_no < len(self._line_offs) else len(self.src)
        return s, e


def _escaped_newline(src: bytes, i: int) -> bool:
    return (i >= 1 and src[i - 1] == 0x5C) or (i >= 2 and src[i - 1] == 0x0D and src[i - 2] == 0x5C)


def _token_start(src: bytes, i: int) -> int:
    k = i
    while k > 0 and (src[k - 1] in _IDENT_BYTES or src[k - 1] == 0x27):
        k -= 1
    return k


def lex(src: bytes) -> Lexed:
    """C/C++ のソースの字句の走査。コメント（行・ブロック）・文字列（生文字列を含む）・文字リテラルの範囲と、
    プリプロセッサ指令（行頭の空白の後が `#` の行と、その継続行 `\\`。指令の中のブロックコメントが改行をまたぐ場合を含む）の範囲を返す。
    数字の区切り（`1'000`）は文字リテラルにしない。"""
    n = len(src)
    spans, directives = [], []
    dir_start = 0 if _DIRECTIVE_START.match(src, 0) else None
    i = 0
    while True:
        m = _SIG.search(src, i)
        if m is None:
            break
        i = m.start()
        tok = m.group(0)
        if tok == b"\n":
            if dir_start is not None and not _escaped_newline(src, i):
                directives.append((dir_start, i))
                dir_start = None
            if dir_start is None and _DIRECTIVE_START.match(src, i + 1):
                dir_start = i + 1
            i += 1
            continue
        if tok == b"/*":
            j = src.find(b"*/", i + 2)
            j = n if j < 0 else j + 2
            spans.append((i, j))
            i = j
            continue
        if tok == b"//":
            j = src.find(b"\n", i)
            j = n if j < 0 else j
            spans.append((i, j))
            i = j
            continue
        if tok == b'"':
            pre = src[max(0, i - 3):i]
            rm = _RAW_PREFIX.search(pre)
            if rm is not None and (i - len(rm.group(0)) == 0 or src[i - len(rm.group(0)) - 1] not in _IDENT_BYTES):
                paren = src.find(b"(", i + 1, i + 18)
                if paren >= 0:
                    delim = src[i + 1:paren]
                    end = src.find(b")" + delim + b'"', paren + 1)
                    j = n if end < 0 else end + len(delim) + 2
                    spans.append((i, j))
                    i = j
                    continue
            j = i + 1
            while True:
                s = _STR_STOP.search(src, j)
                if s is None:
                    j = n
                    break
                if s.group(0) == b"\\":
                    j = s.start() + 2
                    continue
                j = s.start() + (1 if s.group(0) == b'"' else 0)
                break
            spans.append((i, j))
            i = j
            continue
        # 文字リテラル（数字の区切りを除く）
        if i > 0 and src[i - 1] in _IDENT_BYTES:
            k = _token_start(src, i)
            if 0x30 <= src[k] <= 0x39:
                i += 1
                continue
        j = i + 1
        while True:
            s = _CHR_STOP.search(src, j)
            if s is None:
                j = n
                break
            if s.group(0) == b"\\":
                j = s.start() + 2
                continue
            j = s.start() + (1 if s.group(0) == b"'" else 0)
            break
        spans.append((i, j))
        i = j
    if dir_start is not None:
        directives.append((dir_start, n))
    return Lexed(src, spans, directives)


# ---------------------------------------------------------------------------
# マクロの定義の事前走査
# ---------------------------------------------------------------------------

_DEFINE = re.compile(r"[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)(\()?")
_CONDITIONAL = re.compile(r"[ \t]*#[ \t]*(if|ifdef|ifndef|elif|elifdef|elifndef|else|endif)\b")


def _directive_text(lx: Lexed, start: int, end: int) -> str:
    """指令の範囲のテキスト（コメントを空白にし、継続行 `\\` を連結する）。"""
    pieces = []
    pos = start
    k = bisect.bisect_left(lx._span_starts, start)
    while k < len(lx.spans) and lx.spans[k][0] < end:
        s, e = lx.spans[k]
        pieces.append(lx.src[pos:s])
        if lx.src[s:s + 2] in (b"/*", b"//"):
            pieces.append(b" ")
        else:
            pieces.append(lx.src[s:min(e, end)])
        pos = min(e, end)
        k += 1
    pieces.append(lx.src[pos:end])
    text = b"".join(pieces).decode("utf-8", "replace")
    return re.sub(r"\\\r?\n", " ", text)


def macro_definitions(src: bytes, with_branch: bool = False) -> list:
    """ソースの `#define` の定義 [(名前, 引数のリスト または None〔オブジェクト形式〕, 本体)]。
    コメント・文字列の中の `#define` は拾わない。本体の空白は1つにまとめる。
    `with_branch` なら4つ目の要素に、定義のある条件コンパイルの枝の番号（ファイルの中で一意。条件の外は 0）を加える。"""
    if b"define" not in src:
        return []
    lx = lex(src)
    out = []
    branches, counter = [], 0
    for s, e in lx.directives:
        text = _directive_text(lx, s, e)
        m = _DEFINE.match(text)
        if m is None:
            c = _CONDITIONAL.match(text) if with_branch else None
            if c is not None:
                if c.group(1) == "endif":
                    if branches:
                        branches.pop()
                else:
                    counter += 1
                    if c.group(1).startswith("if"):
                        branches.append(counter)
                    elif branches:
                        branches[-1] = counter
            continue
        name = m.group(1)
        rest = text[m.end():]
        params = None
        if m.group(2):
            close = rest.find(")")
            if close < 0:
                continue
            params = [p.strip() for p in rest[:close].split(",") if p.strip()]
            rest = rest[close + 1:]
        body = " ".join(rest.split())
        out.append((name, params, body, branches[-1] if branches else 0) if with_branch else (name, params, body))
    return out


def collect_definitions(root: str, with_places: bool = False) -> dict:
    """リポジトリの C/C++ のファイル（除外パターンを当てない）のマクロの定義 {名前: [(引数 or None, 本体)]}
    （`with_places` なら [(引数 or None, 本体, (ファイル, 条件コンパイルの枝の番号))]）。
    同じ名前の定義は事前走査で見つけた順（ファイルのパスの昇順・ファイルの中の出現順）。"""
    defs = {}
    for rel in iter_c_cxx_files(root):
        try:
            with open(os.path.join(root, rel), "rb") as fh:
                src = fh.read()
        except OSError:
            continue
        for d in macro_definitions(src, with_branch=with_places):
            defs.setdefault(d[0], []).append((d[1], d[2], (rel, d[3])) if with_places else (d[1], d[2]))
    return defs


# ---------------------------------------------------------------------------
# 種類の判定
# ---------------------------------------------------------------------------

_IDENT = re.compile(r"[A-Za-z_]\w*")
_NS_OPEN = re.compile(r"(?:inline\s+)?namespace\s+(?:inline\s+)?[A-Za-z_]\w*"
                      r"(?:\s*::\s*(?:inline\s+)?[A-Za-z_]\w*)*\s*\{")


def _match_close(text: str, pos: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    for k in range(pos, len(text)):
        if text[k] == open_ch:
            depth += 1
        elif text[k] == close_ch:
            depth -= 1
            if depth == 0:
                return k
    return -1


def _split_args(text: str) -> list:
    args, depth, start = [], 0, 0
    for k, ch in enumerate(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(text[start:k].strip())
            start = k + 1
    args.append(text[start:].strip())
    return args if (len(args) > 1 or args[0]) else []


def _substitute(body: str, params: list, args: list) -> str:
    mapping = {}
    for i, p in enumerate(params):
        if p == "...":
            mapping["__VA_ARGS__"] = ", ".join(args[i:])
        elif p.endswith("..."):
            mapping[p[:-3]] = ", ".join(args[i:])
        else:
            mapping[p] = args[i] if i < len(args) else ""
    return _IDENT.sub(lambda m: mapping.get(m.group(0), m.group(0)), body)


@dataclass(frozen=True)
class _Res:
    kind: str                 # decor / open / close
    any_words: frozenset = frozenset()
    all_words: frozenset = frozenset()
    count: int = 0
    expansion: str = ""


def _combine_seq(items: list):
    if not items:
        return _Res("decor")
    kinds = {r.kind for r in items}
    if len(kinds) != 1:
        return None
    kind = kinds.pop()
    if kind == "decor":
        return _Res("decor", frozenset().union(*(r.any_words for r in items)),
                    frozenset().union(*(r.all_words for r in items)))
    return _Res(kind, count=sum(r.count for r in items), expansion=" ".join(r.expansion for r in items))


def _combine_defs(results: list):
    """マクロの定義ごとの判定をまとめる。すべての定義が同じ種類（名前空間マクロは同じ側・同じ段数）のときだけ当たる。"""
    if not results or any(r is None for r in results):
        return None
    kinds = {r.kind for r in results}
    if len(kinds) != 1:
        return None
    kind = kinds.pop()
    if kind == "decor":
        return _Res("decor", frozenset().union(*(r.any_words for r in results)),
                    frozenset.intersection(*(r.all_words for r in results)))
    if len({r.count for r in results}) != 1:
        return None
    best = results[0]
    for r in results[1:]:
        if len(r.expansion) > len(best.expansion):
            best = r
    return best


class _Evaluator:
    def __init__(self, defs: dict):
        self.defs = defs

    def macro(self, name: str, depth: int, stack: frozenset):
        ds = self.defs.get(name)
        if not ds or depth > MAX_DEPTH or name in stack:
            return None
        if any(p is not None for p, _ in ds):
            return None
        return _combine_defs([self.seq(body, depth + 1, stack | {name}) for _, body in ds])

    def invoke(self, name: str, args: list, depth: int, stack: frozenset):
        ds = self.defs.get(name)
        if not ds or depth > MAX_DEPTH or name in stack or any(p is None for p, _ in ds):
            return None
        r = _combine_defs([self.seq(_substitute(body, params, args), depth + 1, stack | {name})
                           for params, body in ds])
        return r if (r is not None and r.kind == "decor") else None

    def seq(self, body: str, depth: int, stack: frozenset):
        items = []
        pos = 0
        n = len(body)
        while True:
            while pos < n and body[pos].isspace():
                pos += 1
            if pos >= n:
                break
            if body.startswith("[[", pos):
                end = _match_close(body, pos, "[", "]")
                if end < 0:
                    return None
                items.append(_Res("decor"))
                pos = end + 1
                continue
            m = _NS_OPEN.match(body, pos)
            if m is not None:
                items.append(_Res("open", count=1, expansion=" ".join(m.group(0).split())))
                pos = m.end()
                continue
            if body[pos] == "}":
                items.append(_Res("close", count=1, expansion="}"))
                pos += 1
                continue
            m = _IDENT.match(body, pos)
            if m is None:
                return None
            word = m.group(0)
            pos = m.end()
            if word in ("__attribute__", "__declspec"):
                while pos < n and body[pos].isspace():
                    pos += 1
                if pos >= n or body[pos] != "(":
                    return None
                end = _match_close(body, pos, "(", ")")
                if end < 0:
                    return None
                items.append(_Res("decor"))
                pos = end + 1
                continue
            if word in _DECORATOR_WORDS:
                items.append(_Res("decor", frozenset({word}), frozenset({word})))
                continue
            ds = self.defs.get(word)
            if not ds:
                return None
            k = pos
            while k < n and body[k].isspace():
                k += 1
            if k < n and body[k] == "(" and all(p is not None for p, _ in ds):
                end = _match_close(body, k, "(", ")")
                if end < 0:
                    return None
                r = self.invoke(word, _split_args(body[k + 1:end]), depth, stack)
                pos = end + 1
            else:
                r = self.macro(word, depth, stack)
            if r is None:
                return None
            items.append(r)
        return _combine_seq(items)


@dataclass(frozen=True)
class Neutral:
    kind: str           # KIND_NAMESPACE / KIND_DECORATOR
    replacement: str    # 置き換える文字列（宣言を飾るマクロは残す語。空なら同じ長さの空白）


def classify_definitions(defs: dict) -> dict:
    """マクロの定義 {名前: [(引数 or None, 本体)]} から、置き換えるマクロの表 {名前: Neutral}。"""
    ev = _Evaluator(defs)
    out = {}
    for name in sorted(defs):
        r = ev.macro(name, 0, frozenset())
        if r is None:
            continue
        if r.kind == "decor":
            kept = [w for w in _KEEP_IF_ALL if w in r.all_words] + [w for w in _KEEP_IF_ANY if w in r.any_words]
            out[name] = Neutral(KIND_DECORATOR, " ".join(kept))
        else:
            out[name] = Neutral(KIND_NAMESPACE, r.expansion)
    return out


_TRY = re.compile(r"try")
_EXPORT_OPEN = re.compile(r"export\s*\{")
_CATCH = re.compile(r"catch\s*\(")


def _structure_role(body: str, ev: _Evaluator, name: str):
    """空でない定義の本体1つの役割: "open"（`export {`・`try`・名前空間を開く）/ "close"（`}`・`catch (…) {…}`）/
    "decor"（宣言を飾る語だけ）。どれにも当たらなければ None。"""
    if _TRY.fullmatch(body) or _EXPORT_OPEN.fullmatch(body):
        return "open"
    m = _CATCH.match(body)
    if m is not None:
        end = _match_close(body, m.end() - 1, "(", ")")
        rest = body[end + 1:].strip() if end >= 0 else ""
        if rest.startswith("{") and _match_close(rest, 0, "{", "}") == len(rest) - 1:
            return "close"
        return None
    r = ev.seq(body, 1, frozenset({name}))
    return r.kind if r is not None else None


def empty_pairs(defs: dict, table: dict) -> dict:
    """空の定義を持つ「構造を開く側・閉じる側」の組のマクロ {名前: Neutral(KIND_EMPTY_PAIR, "")}。
    `defs` は `collect_definitions(root, with_places=True)`、`table` は `classify_definitions` の結果（そこにあるマクロは除く）。
    対象はオブジェクト形式で、空の定義を1つ以上持ち、空でない定義がすべて開く側（と宣言を飾る語）か、すべて閉じる側（と宣言を飾る語）の
    マクロ。開く側 O と閉じる側 K は、O と K の空の定義が同じ場所（同じファイルの同じ条件コンパイルの枝）にあり、かつ空でない定義どうしも
    同じ場所にあるときに組とし、組の相手があるマクロだけを空にする（片方だけに空の定義がある組は置き換えない）。"""
    ev = _Evaluator({n: [(p, b) for p, b, _f in ds] for n, ds in defs.items()})
    role, empty_places, full_places = {}, {}, {}
    for name in sorted(defs):
        ds = defs[name]
        if name in table or any(p is not None for p, _b, _f in ds) or all(b for _p, b, _f in ds):
            continue
        roles = set()
        for _p, b, _f in ds:
            if b:
                roles.add(_structure_role(b, ev, name))
        roles.discard("decor")
        if len(roles) != 1 or None in roles:
            continue
        role[name] = roles.pop()
        empty_places[name] = {w for _p, b, w in ds if not b}
        full_places[name] = {w for _p, b, w in ds if b}
    opens = [n for n in role if role[n] == "open"]
    closes = [n for n in role if role[n] == "close"]
    out = {}
    for o in opens:
        for k in closes:
            if empty_places[o] & empty_places[k] and full_places[o] & full_places[k]:
                out[o] = out[k] = Neutral(KIND_EMPTY_PAIR, "")
    return out


def neutralize_table(root: str) -> dict:
    """リポジトリの置き換えるマクロの表 {名前: Neutral}。同じ入力から決定的に同じ結果になる。"""
    defs = collect_definitions(root, with_places=True)
    table = classify_definitions({n: [(p, b) for p, b, _f in ds] for n, ds in defs.items()})
    table.update(empty_pairs(defs, table))
    return table


def table_counts(table: dict) -> dict:
    """state の preprocess（置き換えたマクロの件数）。"""
    ns = sum(1 for v in table.values() if v.kind == KIND_NAMESPACE)
    ep = sum(1 for v in table.values() if v.kind == KIND_EMPTY_PAIR)
    return {"neutralized_macros": len(table), "namespace": ns, "decorator": len(table) - ns - ep, "empty_pair": ep}


# ---------------------------------------------------------------------------
# 置き換え
# ---------------------------------------------------------------------------

def table_key(table: dict) -> frozenset:
    """置き換えの表の、キャッシュの鍵にできる形（名前と置き換え文字列の組）。"""
    return frozenset((name, v.replacement) for name, v in table.items())


_IDENT_RX = re.compile(rb"[A-Za-z_][A-Za-z0-9_]*")


@lru_cache(maxsize=8)
def _replacements(key: frozenset) -> dict:
    repl = {}
    for name, value in key:
        b = value.encode()
        nb = name.encode()
        repl[nb] = b + b" " * (len(nb) - len(b)) if len(b) < len(nb) else b
    return repl


@lru_cache(maxsize=256)
def _names_regex(names: frozenset):
    ordered = sorted(names, key=lambda s: (-len(s), s))
    return re.compile(rb"(?<![A-Za-z0-9_])(?:" + b"|".join(re.escape(x) for x in ordered) + rb")(?![A-Za-z0-9_])")


def _on_directive_line(src: bytes, pos: int) -> bool:
    """pos の行がプリプロセッサ指令の行（行頭の空白の後が `#`）か、その継続行か（字句の走査をしない簡易な判定。
    ブロックコメントの中の `#` の行も指令とみなすが、どちらも置き換えない位置なので結果は変わらない）。"""
    start = src.rfind(b"\n", 0, pos) + 1
    while True:
        if _DIRECTIVE_START.match(src, start):
            return True
        if start == 0 or not _escaped_newline(src, start - 1):
            return False
        start = src.rfind(b"\n", 0, start - 1) + 1


def apply_table(src: bytes, key: frozenset) -> bytes:
    """置き換えの表（`table_key` の形）でソースのマクロを置き換える。同じ行の中だけで置き換え、改行を変えない。
    プリプロセッサ指令の行（継続行を含む）・コメント・文字列の中は置き換えない。"""
    if not key:
        return src
    repl = _replacements(key)
    present = frozenset(_IDENT_RX.findall(src)) & repl.keys()
    if not present:
        return src
    matches = [m for m in _names_regex(frozenset(present)).finditer(src) if not _on_directive_line(src, m.start())]
    if not matches:
        return src
    lx = lex(src)
    pieces = []
    pos = 0
    for m in matches:
        s = m.start()
        if lx.in_comment_or_string(s) or lx.in_directive(s):
            continue
        pieces.append(src[pos:s])
        pieces.append(repl[m.group(0)])
        pos = m.end()
    if not pieces:
        return src
    pieces.append(src[pos:])
    return b"".join(pieces)


def line_has_code_occurrence(lx: Lexed, line_no: int, name: str) -> tuple:
    """行 `line_no` について (プリプロセッサ指令の行か, コメント・文字列の外に `name` の単語の出現があるか)。"""
    span = lx.line_span(line_no)
    if span is None:
        return False, False
    s, e = span
    first = s
    while first < e and lx.src[first] in (0x20, 0x09):
        first += 1
    if lx.in_directive(first if first < e else s):
        return True, False
    rx = re.compile(rb"(?<![A-Za-z0-9_])" + re.escape(name.encode()) + rb"(?![A-Za-z0-9_])")
    return False, any(not lx.in_comment_or_string(m.start()) for m in rx.finditer(lx.src, s, e))
