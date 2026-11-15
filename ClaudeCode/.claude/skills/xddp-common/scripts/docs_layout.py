"""docs_layout.py — `{DOCS}`・latest-specs の配置とフロントマターの読み取り・気づき・提案メモの節（単一定義）

`promote.py`・`collect_insights.py`（close）・`domain_refs.py`（工程2）・`ai_index.py`（AI_INDEX）・
`artifact_lint.py`（レビューの機械検査）が import する。サブコマンドなし・標準ライブラリのみ。

気づき・提案メモの節（`## 気づき・提案メモ`。番号・見出しの水準・全角空白は問わない）の検出・項目の定義
（数えない行・「なし」の語・表の行の取り方）と、フロントマター `has_insights` の読み方・期待値の規則を置く。

配置（latest-specs の `{area}/` は `{DOCS}` の `{area}/specs/` に当たる。`area` は repo 名・`system`・`cross`）:
  {DOCS}/{repo}/specs/{module}/spec.md            latest-specs/{repo}/{module}/spec.md
  {DOCS}/system/specs/use-cases/{uc}/description.md   latest-specs/system/use-cases/{uc}/description.md
  {DOCS}/cross/specs/interfaces/{name}/spec.md    latest-specs/cross/interfaces/{name}/spec.md
  {DOCS}/{area}/knowledge/code-knowledge/{_structures|_constants|_flows}/

工程11 の入力と記録の約束（`spec_version_delta.py`・`spec_changes.py`・`promote.py`・`collect_insights.py` が使う）:
  - モジュール仕様のディレクトリ名（`module_spec_dir_name`・`resolve_spec_dir`）と、同一性のキー `module-dir`
  - シーケンス図のファイル名（`seq_file_stem`）
  - progress.md の「## 工程11 更新仕様書ファイル一覧」「## 工程11 削除した仕様書ファイル一覧」の読み書き
  - 進行中の CR の判定（`cr_in_progress`。並行 CR 保護）
"""

import re
import unicodedata
from pathlib import Path

SYSTEM_AREA = "system"
CROSS_AREA = "cross"
OVERVIEW_DIR = "overview"
MODULE_SPEC_FILE = "spec.md"
MODULE_STRUCTURE_FILE = "structure.md"
MODULE_STATE_FILE = "state-machine.md"
OVERVIEW_ARCHITECTURE_FILE = "architecture.md"
USECASE_DIR = "use-cases"
USECASE_FILE = "description.md"
INTERFACE_DIR = "interfaces"
INTERFACE_SPEC_FILE = "spec.md"
INTERFACE_SCHEMA_FILE = "schema.md"

# code-knowledge の共有の知見のディレクトリ名 → 種別名
SHARED_KNOWLEDGE_DIRS = {
    "_structures": "共有構造体",
    "_constants": "共有定数",
    "_flows": "機能間フロー",
}
# code-knowledge で制約（constraints.md）の置き場所にしないディレクトリ名（共有の知見と `_cochange`）
NON_CONSTRAINT_KNOWLEDGE_DIRS = tuple(dict.fromkeys([*SHARED_KNOWLEDGE_DIRS, "_cochange"]))
# code-knowledge の制約のファイル名（`{KNOW}/{MODULE}/constraints.md`）
CONSTRAINTS_FILE = "constraints.md"

# cross のインタフェース仕様のフロントマター `breaking:` の語彙
BREAKING_KEY = "breaking"
BREAKING_VALUES = ("true", "false")

USECASE_PURPOSE_HEADING_RE = re.compile(r"^##\s*(?:\d+\.\s*)?目的・ゴール\s*$", re.MULTILINE)
RELATED_MODULES_KEY = "related-modules"
LAST_UPDATED_CR_KEY = "last-updated-cr"

# モジュール仕様の同一性のキー（`REPO_PATH` 相対のモジュールディレクトリ。1ファイルのモジュールはそのファイル、
# リポジトリ直下のファイルのモジュールは `.`、範囲が決まらなければ空）
MODULE_DIR_KEY = "module-dir"
# モジュール仕様のディレクトリ名に使えない名前（latest-specs の `{repo}/` 直下の予約名）
RESERVED_SPEC_DIRS = (OVERVIEW_DIR, CROSS_AREA, SYSTEM_AREA)
RESERVED_SPEC_DIR_PREFIX = "mod-"

# progress.md の節
STEP11_UPDATED_HEADING = "## 工程11 更新仕様書ファイル一覧"
STEP11_DELETED_HEADING = "## 工程11 削除した仕様書ファイル一覧"
NEXT_COMMAND_HEADING = "## 次に実行すべきコマンド"
CR_CLOSE_HEADING = "## CR クローズ"
CR_ABORT_HEADING = "## CR 中止"
STEP11_UPDATED_COMMENT = "<!-- spec_changes.py record が作り直す（工程11 の最初の実行の時点と比べて、足した・内容が変わったファイル）。手で直さない -->"
STEP11_DELETED_COMMENT = "<!-- spec_changes.py record が作り直す（工程11 の最初の実行の時点にあって、今は無いファイル）。手で直さない -->"
_LIST_ITEM_RE = re.compile(r"^\s*[-*]\s+`?([^`\s]+)`?")


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------


def docs_specs_root(docs, area: str) -> Path:
    """`{DOCS}/{area}/specs`（latest-specs の `{area}/` の写し先）。"""
    return Path(docs) / area / "specs"


def latest_specs_root(latest_specs, area: str) -> Path:
    """latest-specs の `{area}/`。"""
    return Path(latest_specs) / area


def docs_usecases_dir(docs) -> Path:
    return docs_specs_root(docs, SYSTEM_AREA) / USECASE_DIR


def latest_usecases_dir(latest_specs) -> Path:
    return latest_specs_root(latest_specs, SYSTEM_AREA) / USECASE_DIR


def docs_interfaces_dir(docs) -> Path:
    return docs_specs_root(docs, CROSS_AREA) / INTERFACE_DIR


def latest_interfaces_dir(latest_specs) -> Path:
    return latest_specs_root(latest_specs, CROSS_AREA) / INTERFACE_DIR


def code_knowledge_dir(docs, area: str) -> Path:
    return Path(docs) / area / "knowledge" / "code-knowledge"


def subdir_names(root) -> list:
    """root 直下のディレクトリ名（名前の順）。root が無ければ空。"""
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


def module_names(specs_root) -> list:
    """モジュールのディレクトリ名（`overview` を除く）。"""
    return [n for n in subdir_names(specs_root) if n != OVERVIEW_DIR]


# ---------------------------------------------------------------------------
# フロントマター
# ---------------------------------------------------------------------------


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _inline_list(val: str):
    """`[]`・`[a, b]`・`["a", "b"]` をリストにする。リストの書式でなければ None。"""
    if not (val.startswith("[") and val.endswith("]")):
        return None
    inner = val[1:-1].strip()
    if not inner:
        return []
    return [_unquote(x) for x in inner.split(",") if x.strip()]


def parse_frontmatter(text: str) -> dict:
    """先頭 `---`〜`---` のフロントマターを読む（外部依存なし）。

    `key: value`（引用符を外す）・`key: [a, b]`・`key:` の後の `  - a` の行（リスト）に対応する。
    リストの要素の引用符も外す。ネストしたマップ等は対象外。
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}
    result = {}
    i = 1
    while i < end:
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            items = []
            j = i + 1
            while j < end and re.match(r"^\s*-\s+", lines[j]):
                items.append(_unquote(re.sub(r"^\s*-\s+", "", lines[j])))
                j += 1
            if items:
                result[key] = items
                i = j
                continue
            result[key] = ""
            i += 1
            continue
        as_list = _inline_list(val)
        result[key] = as_list if as_list is not None else _unquote(val)
        i += 1
    return result


def read_frontmatter(path) -> dict:
    path = Path(path)
    if not path.is_file():
        return {}
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def last_updated_cr(path) -> str:
    """フロントマターの `last-updated-cr`。無ければ空文字。"""
    val = read_frontmatter(path).get(LAST_UPDATED_CR_KEY, "")
    return val if isinstance(val, str) else ""


def latest_to_docs_path(docs, rel_latest) -> Path:
    """`latest-specs/{area}/{path}`（`latest-specs/` は省いてもよい）→ `{DOCS}/{area}/specs/{path}`。"""
    parts = Path(rel_latest).parts
    if parts and parts[0] == "latest-specs":
        parts = parts[1:]
    if len(parts) < 2:
        raise ValueError(f"latest-specs の相対パスではありません: {rel_latest}")
    return docs_specs_root(docs, parts[0]).joinpath(*parts[1:])


# ---------------------------------------------------------------------------
# 工程11: モジュール仕様のディレクトリ名・同一性・シーケンス図のファイル名
# ---------------------------------------------------------------------------

_HEADING_NUMBER_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)*\.?\s*")
_SEQ_STEM_DROP_RE = re.compile(r"[^0-9a-z\-々぀-ヿ㐀-䶿一-鿿]")


def nfc(text: str) -> str:
    """Unicode の NFC（macOS のファイル名は NFD で返りうるので、名前を比べる前にそろえる）。"""
    return unicodedata.normalize("NFC", text or "")


def norm_module_dir(value) -> str:
    """`module-dir` の値（SURVEY の「ディレクトリ」欄の値も）を比べる形にする。

    `REPO_PATH` 相対・`/` 区切り・末尾の `/` なし。`.`・`./` は `.`（リポジトリ直下のファイルのモジュール）。
    空・プレースホルダー（`{…}`）・文字列でない値は空（範囲が決まらない）。
    """
    if not isinstance(value, str):
        return ""
    s = value.strip().strip("`").strip().replace("\\", "/")
    if not s or _BRACE_PLACEHOLDER_RE.search(s):
        return ""
    while s.startswith("./"):
        s = s[2:]
    s = s.rstrip("/")
    if s in ("", "."):
        return "."
    parts = [p for p in s.split("/") if p not in ("", ".")]
    return "/".join(parts) if parts else "."


def module_spec_dir_name(name: str) -> str:
    """モジュール名から latest-specs のディレクトリ名を作る（`resolve_spec_dir` で既存のものが無いとき）。

    キャメルケースを区切り、`/`・`_`・空白を `-` に、小文字にし、連続する `-` を1つにする。
    予約名（`overview`・`cross`・`system`）と一致すれば `mod-` を付ける。
    """
    s = (name or "").strip()
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)
    s = re.sub(r"[/_\s]+", "-", s).lower()
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if s in RESERVED_SPEC_DIRS:
        s = RESERVED_SPEC_DIR_PREFIX + s
    return s


def spec_module_dir(spec_dir) -> str:
    """モジュール仕様のディレクトリの spec.md の `module-dir`（`norm_module_dir` 済み。無ければ空）。"""
    return norm_module_dir(read_frontmatter(Path(spec_dir) / MODULE_SPEC_FILE).get(MODULE_DIR_KEY, ""))


def resolve_spec_dir(name: str, module_dir, roots) -> tuple:
    """モジュールを書く latest-specs のディレクトリ名を決める。戻り値: (ディレクトリ名, 重複の一覧)。

    `roots`（latest-specs の `{repo}/`、`{DOCS}/{repo}/specs` の順。無い root は飛ばす）の既存の spec.md の
    `module-dir` が `module_dir` と一致するディレクトリがあれば、その名前を使う。先の root にあるものを優先し、
    同じ root に複数あれば名前の順で最初のものを選ぶ。選ばなかった一致（選んだものと名前が違うもの）は
    `{root}/{名前}` の形で重複として返す。`module_dir` が空か一致が無ければ `module_spec_dir_name(name)`。
    """
    md = norm_module_dir(module_dir)
    if md:
        matches = []
        for root in roots:
            if not root:
                continue
            for d in module_names(root):
                if spec_module_dir(Path(root) / d) == md:
                    matches.append((Path(root), d))
        if matches:
            chosen = matches[0][1]
            dups = [str(r / d) for r, d in matches if d != chosen]
            return chosen, dups
    return module_spec_dir_name(name), []


def seq_file_stem(heading: str, index: int) -> str:
    """シーケンス図の小見出しからファイル名の語幹（`{語幹}-seq.md`）を作る。

    NFC に正規化し、見出しの番号を除き、英字を小文字に、空白・`_`・`/`・`／` を `-` にし、英数字・`-`・かな・漢字以外を除く。
    空になれば `seq-{index}`（`index` は小見出しの順番。1始まり）。
    """
    t = _HEADING_NUMBER_RE.sub("", nfc(heading).strip())
    t = re.sub(r"[\s_/／]+", "-", t.lower())
    t = re.sub(r"-{2,}", "-", _SEQ_STEM_DROP_RE.sub("", t)).strip("-")
    return t or f"seq-{index}"


CROSS_SEQ_LEVEL_SUFFIX = "レベルのシーケンス図"


def cross_seq_stem(heading: str, index: int) -> str:
    """cross SPO §3 の小見出し（`### 3.1 {レベル名}レベルのシーケンス図`）からファイル名の語幹を作る。
    レベル名（「レベルのシーケンス図」の前。後ろの `（…）` の注記は除く）を `seq_file_stem` に通す。"""
    t = _HEADING_NUMBER_RE.sub("", nfc(heading).strip())
    if CROSS_SEQ_LEVEL_SUFFIX in t:
        t = t.split(CROSS_SEQ_LEVEL_SUFFIX, 1)[0]
    return seq_file_stem(t, index)


# ---------------------------------------------------------------------------
# 工程11: progress.md の記録の節・進行中の CR
# ---------------------------------------------------------------------------


def _section_span(lines: list, heading: str):
    """`heading` の節の範囲 (見出しの行, 次の `## ` の行)。無ければ None。"""
    for i, line in enumerate(lines):
        if line.strip() == heading:
            j = i + 1
            while j < len(lines) and not lines[j].startswith("## "):
                j += 1
            return i, j
    return None


def read_step11_list(progress_text: str, heading: str):
    """progress.md の `heading`（工程11 の更新一覧・削除一覧）の `latest-specs/…` のパス。節が無ければ None。"""
    lines = progress_text.split("\n")
    span = _section_span(lines, heading)
    if span is None:
        return None
    out = []
    for item in lines[span[0] + 1:span[1]]:
        m = _LIST_ITEM_RE.match(item)
        if m and m.group(1).startswith("latest-specs/"):
            out.append(m.group(1))
    return out


def read_step11_lists(progress_path) -> dict:
    """{"updated": 更新一覧, "deleted": 削除一覧}（progress.md・節が無ければ None）。"""
    path = Path(progress_path)
    if not path.is_file():
        return {"updated": None, "deleted": None}
    text = path.read_text(encoding="utf-8")
    return {"updated": read_step11_list(text, STEP11_UPDATED_HEADING),
            "deleted": read_step11_list(text, STEP11_DELETED_HEADING)}


def _step11_block(heading: str, comment: str, paths: list, separator: bool) -> list:
    items = [f"- {p}" for p in paths] or ["（なし）"]
    block = [heading, "", comment, "", *items, ""]
    return block + ["---", ""] if separator else block


def write_step11_lists(progress_text: str, updated: list, deleted: list) -> str:
    """progress.md の工程11 の更新一覧・削除一覧の節を作り直した本文を返す。

    節が無ければ作る（更新一覧は「## 次に実行すべきコマンド」の前〔無ければ末尾〕、削除一覧は更新一覧の後）。
    """
    lines = progress_text.split("\n")
    for heading, comment, paths in ((STEP11_UPDATED_HEADING, STEP11_UPDATED_COMMENT, updated),
                                    (STEP11_DELETED_HEADING, STEP11_DELETED_COMMENT, deleted)):
        span = _section_span(lines, heading)
        if span is not None:
            i, j = span
            separator = any(ln.strip() == "---" for ln in lines[i + 1:j])
            lines[i:j] = _step11_block(heading, comment, paths, separator or j < len(lines))
            continue
        if heading == STEP11_DELETED_HEADING:
            prev = _section_span(lines, STEP11_UPDATED_HEADING)
            at = prev[1]
        else:
            nxt = _section_span(lines, NEXT_COMMAND_HEADING)
            at = nxt[0] if nxt is not None else len(lines)
        if at == len(lines):
            while lines and not lines[-1].strip():
                lines.pop()
            lines[len(lines):] = ["", "---", ""] + _step11_block(heading, comment, paths, False)
        else:
            lines[at:at] = _step11_block(heading, comment, paths, True)
    return "\n".join(lines)


def cr_in_progress(xddp_dir, cr: str) -> bool:
    """CR が進行中か（並行 CR 保護）。progress.md があり、「## CR クローズ」「## CR 中止」のどちらの節も無いとき真。"""
    if not cr:
        return False
    path = Path(xddp_dir) / cr / "progress.md"
    if not path.is_file():
        return False
    heads = {ln.strip() for ln in path.read_text(encoding="utf-8").split("\n")}
    return CR_CLOSE_HEADING not in heads and CR_ABORT_HEADING not in heads


def in_progress_crs(xddp_dir, exclude: str = "") -> list:
    """`{XDDP_DIR}` 直下の進行中の CR（`cr_in_progress`。名前の順。`exclude` を除く）。"""
    root = Path(xddp_dir)
    if not root.is_dir():
        return []
    return [p.name for p in sorted(root.iterdir())
            if p.is_dir() and p.name != exclude and cr_in_progress(root, p.name)]


# ---------------------------------------------------------------------------
# 気づき・提案メモ
# ---------------------------------------------------------------------------

INSIGHTS_HEADING_TEXT = "気づき・提案メモ"
HAS_INSIGHTS_KEY = "has_insights"
# 気づきメモの節を持たない latest-specs のファイル（ファイル名で決める。それ以外は節を持つ）
NO_INSIGHTS_NAMES = {INTERFACE_SCHEMA_FILE, "crud.md", "dfd.md"}
NO_INSIGHTS_SUFFIX = "-seq.md"
# 表の外の行・表の `内容` のセルがこの語だけなら未記入（末尾の `。` は無視）
INSIGHT_NONE_WORDS = {"なし", "（なし）", "(なし)", "特になし"}
# 項目の比べ方で使う表の列（無ければ `#` 以外の全部の列）
INSIGHT_KEY_COLUMNS = ("種別", "内容", "対応方針")
INSIGHT_CONTENT_COLUMN = "内容"

_HEADING_RE = re.compile(r"^(#{1,6})\s*(.*)$")
_ORDINAL_PREFIX_RE = re.compile(r"^\d+[.．]\s*")
_BRACE_PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")
_TABLE_SEPARATOR_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


def has_placeholder(text: str) -> bool:
    """テンプレートのプレースホルダー（`{…}`）を含むか（見本の行を数えないために使う）。"""
    return bool(_BRACE_PLACEHOLDER_RE.search(text or ""))


def _normalize_heading_text(text: str) -> str:
    t = text.replace("　", " ").strip()
    t = _ORDINAL_PREFIX_RE.sub("", t)
    return t.strip()


def find_insight_sections(text: str) -> list:
    """「気づき・提案メモ」の見出しの配下の本文（行のリスト）をすべて返す。

    見出しの水準（##/### 等）を問わず検出し、次の同じかより上の水準の見出しの手前までを本文とする。
    """
    lines = text.split("\n")
    n = len(lines)
    bodies = []
    i = 0
    while i < n:
        m = _HEADING_RE.match(lines[i])
        if m and _normalize_heading_text(m.group(2)) == INSIGHTS_HEADING_TEXT:
            level = len(m.group(1))
            j = i + 1
            while j < n:
                m2 = _HEADING_RE.match(lines[j])
                if m2 and len(m2.group(1)) <= level:
                    break
                j += 1
            bodies.append(lines[i + 1:j])
            i = j
        else:
            i += 1
    return bodies


def _strip_html_comments(lines: list) -> list:
    """HTML コメント（`<!--` 〜 `-->`。複数行を含む）を除いた行のリスト。"""
    text = re.sub(r"<!--.*?-->", "", "\n".join(lines), flags=re.DOTALL)
    if "<!--" in text:  # 閉じないコメントは、そこから後ろを除く
        text = text[:text.index("<!--")]
    return text.split("\n")


def _split_cells(line: str) -> list:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith(r"\|"):
        s = s[:-1]
    return [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def _is_none_word(text: str) -> bool:
    return text.strip().rstrip("。") in INSIGHT_NONE_WORDS


def insight_items(body_lines: list) -> list:
    """気づき・提案メモの節の本文から項目を取り出す。

    戻り値: [{"key": 比べる文字列, "line": 元の行, "table": 表のヘッダーと区切りの行（表の外なら None）}]。
    数えない行: HTML コメントの中・空行・`>` の引用行（テンプレートの案内文）・`---`・表のヘッダー行と区切り行・
    表の外の「なし」の語だけの行・表の `{…}` のプレースホルダーを含む行・`内容` のセルが「なし」の語の行。
    """
    lines = _strip_html_comments(body_lines)
    items = []
    i = 0
    n = len(lines)
    while i < n:
        s = lines[i].strip()
        if s.startswith("|"):
            block = []
            while i < n and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            if len(block) >= 2 and _TABLE_SEPARATOR_RE.match(block[1]):
                header, rows = block[:2], block[2:]
            else:
                header, rows = None, block
            names = _split_cells(header[0]) if header else []
            for row in rows:
                if _BRACE_PLACEHOLDER_RE.search(row):
                    continue
                cells = _split_cells(row)
                by_name = dict(zip(names, cells))
                if INSIGHT_CONTENT_COLUMN in by_name and _is_none_word(by_name[INSIGHT_CONTENT_COLUMN]):
                    continue
                if names and all(c in by_name for c in INSIGHT_KEY_COLUMNS):
                    key_cells = [by_name[c] for c in INSIGHT_KEY_COLUMNS]
                elif names:
                    key_cells = [c for name, c in zip(names, cells) if name != "#"]
                else:
                    key_cells = cells
                key = "|".join(re.sub(r"\s+", " ", c) for c in key_cells)
                items.append({"key": key, "line": row, "table": header})
            continue
        i += 1
        if not s or s.startswith(">") or s == "---" or _is_none_word(s):
            continue
        items.append({"key": s, "line": s, "table": None})
    return items


def render_insight_items(items: list) -> list:
    """insight_items の項目（絞り込んだ後でもよい）を本文の行に戻す。表の行には表のヘッダーと区切りを付ける。"""
    out = []
    prev = object()
    for item in items:
        table = item["table"]
        if out and table is prev:
            out.append(item["line"])
            continue
        if out:
            out.append("")
        if table is not None:
            out.extend(table)
        out.append(item["line"])
        prev = table
    return out


def has_insights(fm: dict):
    """フロントマターの `has_insights`（True／False）。キーが無いか値が true・false 以外なら None。"""
    val = fm.get(HAS_INSIGHTS_KEY)
    if not isinstance(val, str):
        return None
    v = val.strip().lower()
    if v == "true":
        return True
    if v == "false":
        return False
    return None


def expected_has_insights(path) -> bool:
    """latest-specs のファイルが気づき・提案メモの節を持つべきか（ファイル名で決める）。"""
    name = Path(path).name
    return not (name in NO_INSIGHTS_NAMES or name.endswith(NO_INSIGHTS_SUFFIX))


# ---------------------------------------------------------------------------
# ユースケース
# ---------------------------------------------------------------------------


def usecase_purpose(text: str) -> str:
    """`目的・ゴール` の見出しの直後の最初の段落の1行。無ければ空文字。"""
    m = USECASE_PURPOSE_HEADING_RE.search(text)
    if not m:
        return ""
    for line in text[m.end():].split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith(("---", "#")):
            return ""
        return s
    return ""


def usecase_related_modules(fm: dict) -> list:
    """フロントマターの `related-modules` をリストで返す（空要素は除く）。"""
    val = fm.get(RELATED_MODULES_KEY)
    if val is None:
        return []
    if isinstance(val, str):
        val = [val] if val else []
    return [v for v in val if v]


# ---------------------------------------------------------------------------
# cross のインタフェース仕様の破壊的変更
# ---------------------------------------------------------------------------


def breaking_value(fm: dict):
    """`breaking:` の値（小文字・引用符なし）。キーが無ければ None。"""
    if BREAKING_KEY not in fm:
        return None
    val = fm[BREAKING_KEY]
    return val.strip().lower() if isinstance(val, str) else str(val).lower()


def is_breaking(fm: dict) -> bool:
    return breaking_value(fm) == "true"
