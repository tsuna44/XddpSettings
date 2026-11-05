"""docs_layout.py — `{DOCS}`・latest-specs の配置とフロントマターの読み取り（単一定義）

`promote.py`（close）・`domain_refs.py`（工程2）・`ai_index.py`（AI_INDEX）が import する。
サブコマンドなし・標準ライブラリのみ。

配置（latest-specs の `{area}/` は `{DOCS}` の `{area}/specs/` に当たる。`area` は repo 名・`system`・`cross`）:
  {DOCS}/{repo}/specs/{module}/spec.md            latest-specs/{repo}/{module}/spec.md
  {DOCS}/system/specs/use-cases/{uc}/description.md   latest-specs/system/use-cases/{uc}/description.md
  {DOCS}/cross/specs/interfaces/{name}/spec.md    latest-specs/cross/interfaces/{name}/spec.md
  {DOCS}/{area}/knowledge/code-knowledge/{_structures|_constants|_flows}/
"""

import re
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

# cross のインタフェース仕様のフロントマター `breaking:` の語彙
BREAKING_KEY = "breaking"
BREAKING_VALUES = ("true", "false")

USECASE_PURPOSE_HEADING_RE = re.compile(r"^##\s*(?:\d+\.\s*)?目的・ゴール\s*$", re.MULTILINE)
RELATED_MODULES_KEY = "related-modules"
LAST_UPDATED_CR_KEY = "last-updated-cr"


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
