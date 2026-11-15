"""rulebook_files.py — project-rulebook（共通・repo 別・cross）のファイルの作成・未記入の判定・DOCS との同期 CLI

3種の project-rulebook の節の定義（SECTIONS）を持ち、テンプレートからの作成・DOCS からの戻し・
未記入の節の判定・記入済みのドメイン制約の抽出・DOCS への写しと競合の判定を決定的に行う。
設計根拠は docs/adr/ADR-0038-rulebook-writers-and-sync.md を参照。

ファイルの対応（kind ごと）:
  shared: {XDDP_DIR}/project-rulebook.md          ↔ {DOCS}/project-rulebook.md
  repo:   {XDDP_DIR}/project-rulebook-{repo}.md   ↔ {DOCS}/{repo}/project-rulebook.md（構成によらない）
  cross:  {XDDP_DIR}/project-rulebook-cross.md    ↔ {DOCS}/cross/project-rulebook.md（REPOS_KEYS が2つ以上のときだけ）

同期の基準: {XDDP_DIR}/.rulebook-sync.json に、{XDDP_DIR} 側のファイル名ごとに「最後に {XDDP_DIR} と DOCS を
そろえたときの内容の SHA-256」を持つ。

Usage:
  python3 rulebook_files.py ensure --kind {shared|repo|cross} --xddp-dir XDDP_DIR --docs DOCS
      [--repo REPO] [--cr CR] --today YYYY-MM-DD --repos-keys r1,r2
    {XDDP_DIR} に無ければ DOCS の写しを戻し（copied-from-docs）、DOCS にも無ければテンプレートから作る
    （created-from-template。置き換えるのは {REPO_NAME}・§7 の初期行の {INIT_DATE}・{INIT_CR} だけ。
    --cr が無ければ {INIT_CR} は「—」）。{XDDP_DIR} にあれば DOCS と比べる:
    DOCS に無い→exists / 内容が同じ→same / この作業場所だけ変わった→exists /
    DOCS だけ変わった→DOCS を写す（updated-from-docs）/ 両方変わった・基準が無くて違う→conflict（書かない）。
    stdout: {"file": ..., "action": ...}

  python3 rulebook_files.py unfilled --kind {shared|repo|cross} --file FILE --repos-keys r1,r2
    節ごとの記入箇所の状態。stdout: [{"number", "heading", "state", "unfilled_items", "draft"}, ...]
    state: unfilled（すべて未記入）/ partial（一部未記入）/ filled / missing（見出しが無い）/
           not-applicable（マルチ構成だけの節をシングル構成で判定したとき）
    記入箇所の無い節（7. 変更履歴）は出力しない。

  python3 rulebook_files.py domain-constraints --file FILE
    共通ファイルの「ドメイン制約」の表のうち、制約内容がプレースホルダーでも「該当なし」でもない行を、
    表の見出しの行と一緒に stdout に出す。無ければ何も出さない。

  python3 rulebook_files.py promote --xddp-dir XDDP_DIR --docs DOCS --repos-keys r1,r2
    共通・repo 別（すべて）・cross（REPOS_KEYS が2つ以上のとき）を DOCS と同期する。
    stdout: [{"file", "docs_file", "action", "error"}, ...]
    action: absent / copied / same / updated-from-docs / conflict / failed

  python3 rulebook_files.py diff --xddp-dir XDDP_DIR --docs DOCS --file FILE_NAME
    {XDDP_DIR}/FILE_NAME と対応する DOCS のファイルの unified diff を stdout に出す。

  python3 rulebook_files.py resolve --xddp-dir XDDP_DIR --docs DOCS --file FILE_NAME --take {xddp|docs}
    xddp: {XDDP_DIR} を DOCS に写す / docs: DOCS を {XDDP_DIR} に写す。どちらも基準を更新する。
    stdout: {"file", "docs_file", "action": "resolved", "take"}

  FILE_NAME は project-rulebook.md / project-rulebook-{repo}.md / project-rulebook-cross.md。

終了コード: 0＝成功、2＝引数の誤り（kind と構成の食い違い・REPOS_KEYS に無い repo・ファイルが無い等）。
  promote は個々のファイルの失敗を出力に書き、終了コードは 0。
"""

import argparse
import difflib
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
TEMPLATES = {
    "shared": TEMPLATES_DIR / "project-rulebook-template.md",
    "repo": TEMPLATES_DIR / "project-rulebook-repo-template.md",
    "cross": TEMPLATES_DIR / "project-rulebook-cross-template.md",
}
SYNC_FILE = ".rulebook-sync.json"
NOT_APPLICABLE = "該当なし"

# 節の定義。heading は `## ` の後ろの文字列（テンプレートと完全一致させる。テストで確かめる）。
# draft: fill-rulebook がコード調査から起こすか。multi_only: マルチ構成だけの節。
# single_draft: シングル構成でも起こすか（False ならシングル構成では起こさない）。
SECTIONS = {
    "shared": [
        {"number": "1", "heading": "1. プロジェクト概要", "draft": True},
        {"number": "1.5", "heading": "1.5 リポジトリ構成（REPOS: に複数エントリがある場合のみ記入）",
         "draft": True, "multi_only": True},
        {"number": "1.6", "heading": "1.6 ドメイン制約", "draft": False},
        {"number": "2", "heading": "2. 命名規約", "draft": True, "single_draft": False},
        {"number": "3", "heading": "3. アーキテクチャ決定記録（ADR）", "draft": True, "single_draft": False},
        {"number": "4", "heading": "4. 既存パターン・慣習", "draft": True, "single_draft": False},
        {"number": "5", "heading": "5. 禁止事項・注意事項", "draft": False},
        {"number": "6", "heading": "6. モジュール構成メモ", "draft": True, "single_draft": False},
        {"number": "7", "heading": "7. 変更履歴", "draft": False},
    ],
    "repo": [
        {"number": "1", "heading": "1. リポジトリ基本情報", "draft": True},
        {"number": "2", "heading": "2. アーキテクチャ概要", "draft": True},
        {"number": "3", "heading": "3. 命名規約", "draft": True},
        {"number": "4", "heading": "4. コーディング規約・既存パターン", "draft": True},
        {"number": "5", "heading": "5. アーキテクチャ決定記録（ADR）", "draft": True},
        {"number": "6", "heading": "6. 禁止事項・注意事項", "draft": False},
        {"number": "7", "heading": "7. 変更履歴", "draft": False},
    ],
    "cross": [
        {"number": "1", "heading": "1. 対象リポジトリ一覧", "draft": True},
        {"number": "2", "heading": "2. API バージョニング規約", "draft": False},
        {"number": "3", "heading": "3. インタフェース命名規則", "draft": True},
        {"number": "4", "heading": "4. エラーコード・ステータスコード体系", "draft": True},
        {"number": "5", "heading": "5. サービス間認証方式", "draft": True},
        {"number": "6", "heading": "6. インタフェース変更手順", "draft": False},
        {"number": "7", "heading": "7. 変更履歴", "draft": False},
    ],
}

PLACEHOLDER_RE = re.compile(r"^（.+をここに(?:記述|記録)する）\s*$")
EXAMPLE_ROW_RE = re.compile(r"^\|\s*（例）")
CODE_VALUE_RE = re.compile(r"^([A-Z_]+):\s*(.*?)\s*$")
DOMAIN_PLACEHOLDER = "{制約内容}"


class UsageError(Exception):
    """引数の誤り（終了コード 2）。"""


# ---------------------------------------------------------------------------
# ファイルの対応
# ---------------------------------------------------------------------------


def split_keys(raw: str) -> list:
    return [k.strip() for k in (raw or "").split(",") if k.strip()]


def is_multi(repos_keys: list) -> bool:
    return len(repos_keys) >= 2


def xddp_name(kind: str, repo=None) -> str:
    if kind == "shared":
        return "project-rulebook.md"
    if kind == "repo":
        return f"project-rulebook-{repo}.md"
    return "project-rulebook-cross.md"


def docs_rel(kind: str, repo=None) -> str:
    if kind == "shared":
        return "project-rulebook.md"
    if kind == "repo":
        return f"{repo}/project-rulebook.md"
    return "cross/project-rulebook.md"


def kind_of_name(name: str):
    """{XDDP_DIR} 側のファイル名から (kind, repo) を返す。"""
    if name == "project-rulebook.md":
        return "shared", None
    if name == "project-rulebook-cross.md":
        return "cross", None
    m = re.fullmatch(r"project-rulebook-(.+)\.md", name)
    if m:
        return "repo", m.group(1)
    raise UsageError(f"project-rulebook のファイル名ではありません: {name}")


def targets(repos_keys: list) -> list:
    """同期の対象 [(kind, repo)]。repo 別は構成によらず、cross はマルチ構成だけ。"""
    out = [("shared", None)] + [("repo", r) for r in repos_keys]
    if is_multi(repos_keys):
        out.append(("cross", None))
    return out


def validate_kind(kind: str, repo, repos_keys: list) -> None:
    if not repos_keys:
        raise UsageError("--repos-keys が空です")
    if kind == "cross" and not is_multi(repos_keys):
        raise UsageError("cross の rulebook は REPOS: が2つ以上のときだけ扱います")
    if kind == "repo":
        if not repo:
            raise UsageError("--kind repo には --repo が要ります")
        if repo not in repos_keys:
            raise UsageError(f"--repo {repo} は REPOS: のキーにありません（{', '.join(repos_keys)}）")


# ---------------------------------------------------------------------------
# 同期の基準と判定
# ---------------------------------------------------------------------------


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_base(xddp_dir: Path) -> dict:
    path = Path(xddp_dir) / SYNC_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_base(xddp_dir: Path, base: dict) -> None:
    path = Path(xddp_dir) / SYNC_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(base, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def judge(x_data: bytes, d_data: bytes, base_hash) -> str:
    """両方あるときの判定: same / docs-changed / xddp-changed / conflict。"""
    hx, hd = _hash(x_data), _hash(d_data)
    if hx == hd:
        return "same"
    if base_hash is None:
        return "conflict"
    if hd == base_hash:
        return "xddp-changed"
    if hx == base_hash:
        return "docs-changed"
    return "conflict"


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


# ---------------------------------------------------------------------------
# ensure
# ---------------------------------------------------------------------------


def render_template(kind: str, repo, cr, today: str) -> str:
    text = TEMPLATES[kind].read_text(encoding="utf-8")
    if kind == "repo":
        text = text.replace("{REPO_NAME}", repo)
    return text.replace("{INIT_DATE}", today).replace("{INIT_CR}", cr or "—")


def ensure(kind: str, xddp_dir: Path, docs: Path, repos_keys: list, today: str, repo=None, cr=None) -> dict:
    validate_kind(kind, repo, repos_keys)
    xddp_dir, docs = Path(xddp_dir), Path(docs)
    name = xddp_name(kind, repo)
    x_path, d_path = xddp_dir / name, docs / docs_rel(kind, repo)
    base = load_base(xddp_dir)
    if not x_path.exists():
        if d_path.is_file():
            _copy(d_path, x_path)
            base[name] = _hash(x_path.read_bytes())
            save_base(xddp_dir, base)
            action = "copied-from-docs"
        else:
            x_path.parent.mkdir(parents=True, exist_ok=True)
            x_path.write_text(render_template(kind, repo, cr, today), encoding="utf-8")
            action = "created-from-template"
        return {"file": str(x_path), "action": action}
    if not d_path.is_file():
        return {"file": str(x_path), "action": "exists"}
    verdict = judge(x_path.read_bytes(), d_path.read_bytes(), base.get(name))
    if verdict == "same":
        base[name] = _hash(x_path.read_bytes())
        save_base(xddp_dir, base)
        action = "same"
    elif verdict == "docs-changed":
        _copy(d_path, x_path)
        base[name] = _hash(x_path.read_bytes())
        save_base(xddp_dir, base)
        action = "updated-from-docs"
    elif verdict == "xddp-changed":
        action = "exists"
    else:
        action = "conflict"
    return {"file": str(x_path), "action": action}


# ---------------------------------------------------------------------------
# promote / resolve / diff
# ---------------------------------------------------------------------------


def promote(xddp_dir: Path, docs: Path, repos_keys: list) -> list:
    xddp_dir, docs = Path(xddp_dir), Path(docs)
    base = load_base(xddp_dir)
    results = []
    for kind, repo in targets(repos_keys):
        name = xddp_name(kind, repo)
        x_path, d_path = xddp_dir / name, docs / docs_rel(kind, repo)
        item = {"file": name, "docs_file": docs_rel(kind, repo), "kind": kind, "repo": repo,
                "action": "", "error": None}
        try:
            if not x_path.exists():
                item["action"] = "absent"
            elif not d_path.exists():
                _copy(x_path, d_path)
                base[name] = _hash(x_path.read_bytes())
                item["action"] = "copied"
            else:
                verdict = judge(x_path.read_bytes(), d_path.read_bytes(), base.get(name))
                if verdict == "same":
                    base[name] = _hash(x_path.read_bytes())
                    item["action"] = "same"
                elif verdict == "xddp-changed":
                    _copy(x_path, d_path)
                    base[name] = _hash(x_path.read_bytes())
                    item["action"] = "copied"
                elif verdict == "docs-changed":
                    _copy(d_path, x_path)
                    base[name] = _hash(x_path.read_bytes())
                    item["action"] = "updated-from-docs"
                else:
                    item["action"] = "conflict"
        except Exception as e:  # noqa: BLE001
            item["action"] = "failed"
            item["error"] = str(e)
        results.append(item)
    try:
        save_base(xddp_dir, base)
    except OSError:
        pass
    return results


def _paths_for(xddp_dir: Path, docs: Path, name: str):
    kind, repo = kind_of_name(name)
    return Path(xddp_dir) / name, Path(docs) / docs_rel(kind, repo), docs_rel(kind, repo)


def resolve(xddp_dir: Path, docs: Path, name: str, take: str) -> dict:
    x_path, d_path, rel = _paths_for(xddp_dir, docs, name)
    src, dst = (x_path, d_path) if take == "xddp" else (d_path, x_path)
    if not src.is_file():
        raise UsageError(f"写す元のファイルがありません: {src}")
    _copy(src, dst)
    base = load_base(xddp_dir)
    base[name] = _hash(x_path.read_bytes())
    save_base(xddp_dir, base)
    return {"file": name, "docs_file": rel, "action": "resolved", "take": take}


def diff(xddp_dir: Path, docs: Path, name: str) -> str:
    x_path, d_path, rel = _paths_for(xddp_dir, docs, name)

    def _lines(p: Path) -> list:
        return p.read_text(encoding="utf-8").splitlines(keepends=True) if p.is_file() else []

    return "".join(difflib.unified_diff(_lines(d_path), _lines(x_path),
                                        fromfile=f"DOCS/{rel}", tofile=f"XDDP_DIR/{name}"))


# ---------------------------------------------------------------------------
# 節の解析・未記入の判定
# ---------------------------------------------------------------------------


def _fence_flags(lines: list) -> list:
    """各行がコードブロックの中（開始・終了の行を含む）かどうか。"""
    flags, inside = [], False
    for line in lines:
        if line.lstrip().startswith("```"):
            flags.append(True)
            inside = not inside
        else:
            flags.append(inside)
    return flags


def _heading_mask(lines: list) -> list:
    """見出しとして扱わない行（コードブロック・HTML コメントの中）。"""
    fences = _fence_flags(lines)
    flags, in_comment = [], False
    for line, fenced in zip(lines, fences):
        if not fenced and not in_comment and "<!--" in line:
            in_comment = "-->" not in line.split("<!--", 1)[1]
            flags.append(True)
        elif in_comment:
            flags.append(True)
            if "-->" in line:
                in_comment = False
        else:
            flags.append(fenced)
    return flags


def split_sections(text: str) -> dict:
    """`## ` 見出し → 節の本文の行（見出しの行は含まない）。コードブロック・HTML コメントの中は見出しにしない。"""
    lines = text.splitlines()
    flags = _heading_mask(lines)
    sections, current = {}, None
    for line, fenced in zip(lines, flags):
        if not fenced and line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def split_regions(body: list) -> list:
    """節の本文を [(領域の名前, 行)] に分ける。最初の領域（名前 None）は最初の `### ` より前。"""
    flags = _heading_mask(body)
    regions = [(None, [])]
    for line, fenced in zip(body, flags):
        if not fenced and line.startswith("### "):
            regions.append((line[4:].strip(), []))
        else:
            regions[-1][1].append(line)
    return regions


def _code_values(lines: list) -> dict:
    """コードブロックの中の `KEY: 値` の行（KEY は大文字・`_` だけ。例のコメント行 `# …` は当たらない）。"""
    out = {}
    for line, fenced in zip(lines, _fence_flags(lines)):
        if fenced and not line.lstrip().startswith("```"):
            m = CODE_VALUE_RE.match(line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def _is_placeholder_value(value: str) -> bool:
    return value.startswith("（") and value.endswith("）")


def _table_rows(lines: list) -> list:
    return [ln for ln in lines if ln.lstrip().startswith("|")]


def _cells(row: str) -> list:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _domain_rows(lines: list) -> list:
    """ドメイン制約の表の [(種別, 制約内容, 行)]（見出し・区切りの行を除く）。"""
    rows = _table_rows(lines)
    if len(rows) < 2:
        return []
    header = _cells(rows[0])
    idx = next((i for i, h in enumerate(header) if "制約内容" in h), None)
    if idx is None:
        return []
    out = []
    for row in rows[2:]:
        cells = _cells(row)
        if len(cells) > idx:
            out.append((cells[0], cells[idx], row))
    return out


def template_items(kind: str, heading: str) -> list:
    """テンプレートの節から記入箇所の一覧を作る。[(種類, 領域の名前, 名前)]"""
    sections = split_sections(TEMPLATES[kind].read_text(encoding="utf-8"))
    body = sections.get(heading)
    if body is None:
        return []
    items = []
    for region_name, lines in split_regions(body):
        label = region_name or heading
        if any(PLACEHOLDER_RE.match(ln) for ln in lines):
            items.append(("placeholder", region_name, label))
        if any(EXAMPLE_ROW_RE.match(ln) for ln in lines):
            items.append(("example-rows", region_name, f"{label} の表"))
        for key, value in _code_values(lines).items():
            if _is_placeholder_value(value):
                items.append(("code-value", region_name, key))
        for kind_cell, content, _row in _domain_rows(lines):
            if content == DOMAIN_PLACEHOLDER:
                items.append(("domain-row", region_name, kind_cell))
    return items


def _item_state(item: tuple, regions: dict):
    """True=未記入 / False=記入済み / None=判定しない（ファイルにその領域・項目が無い）。"""
    typ, region_name, name = item
    lines = regions.get(region_name)
    if lines is None:
        return None
    if typ == "placeholder":
        return any(PLACEHOLDER_RE.match(ln) for ln in lines)
    if typ == "example-rows":
        return any(EXAMPLE_ROW_RE.match(ln) for ln in lines)
    if typ == "code-value":
        values = _code_values(lines)
        if name not in values:
            return None
        return _is_placeholder_value(values[name])
    if typ == "domain-row":
        for kind_cell, content, _row in _domain_rows(lines):
            if kind_cell == name:
                return content == DOMAIN_PLACEHOLDER
        return None
    return None


def section_draft(sec: dict, repos_keys: list) -> bool:
    if not sec.get("draft"):
        return False
    if not is_multi(repos_keys):
        if sec.get("multi_only") or sec.get("single_draft") is False:
            return False
    return True


def unfilled(kind: str, text: str, repos_keys: list) -> list:
    sections = split_sections(text)
    out = []
    for sec in SECTIONS[kind]:
        items = template_items(kind, sec["heading"])
        if not items:
            continue
        entry = {"number": sec["number"], "heading": sec["heading"], "state": "",
                 "unfilled_items": [], "draft": section_draft(sec, repos_keys)}
        if sec.get("multi_only") and not is_multi(repos_keys):
            entry["state"] = "not-applicable"
            out.append(entry)
            continue
        body = sections.get(sec["heading"])
        if body is None:
            entry["state"] = "missing"
            out.append(entry)
            continue
        regions = {name: lines for name, lines in split_regions(body)}
        states = []
        for item in items:
            st = _item_state(item, regions)
            if st is None:
                continue
            states.append(st)
            if st:
                entry["unfilled_items"].append(item[2])
        if states and all(states):
            entry["state"] = "unfilled"
        elif any(states):
            entry["state"] = "partial"
        else:
            entry["state"] = "filled"
        out.append(entry)
    return out


def domain_constraints(text: str) -> str:
    sections = split_sections(text)
    heading = next((h for h in sections if "ドメイン制約" in h), None)
    if heading is None:
        return ""
    lines = sections[heading]
    rows = _table_rows(lines)
    if len(rows) < 2:
        return ""
    filled = [row for _kind, content, row in _domain_rows(lines)
              if content and content != DOMAIN_PLACEHOLDER and content != NOT_APPLICABLE]
    if not filled:
        return ""
    return "\n".join([rows[0], rows[1]] + filled) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="project-rulebook のファイルの作成・未記入の判定・DOCS との同期")
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("ensure", help="無ければ作る・DOCS の更新を取り込む")
    pe.add_argument("--kind", required=True, choices=["shared", "repo", "cross"])
    pe.add_argument("--xddp-dir", required=True)
    pe.add_argument("--docs", required=True)
    pe.add_argument("--repo")
    pe.add_argument("--cr")
    pe.add_argument("--today", required=True)
    pe.add_argument("--repos-keys", required=True)

    pu = sub.add_parser("unfilled", help="節ごとの記入箇所の状態")
    pu.add_argument("--kind", required=True, choices=["shared", "repo", "cross"])
    pu.add_argument("--file", required=True)
    pu.add_argument("--repos-keys", required=True)

    pd = sub.add_parser("domain-constraints", help="記入済みのドメイン制約の行")
    pd.add_argument("--file", required=True)

    pp = sub.add_parser("promote", help="DOCS への写しと競合の判定")
    pp.add_argument("--xddp-dir", required=True)
    pp.add_argument("--docs", required=True)
    pp.add_argument("--repos-keys", required=True)

    pf = sub.add_parser("diff", help="XDDP_DIR と DOCS の差分")
    pf.add_argument("--xddp-dir", required=True)
    pf.add_argument("--docs", required=True)
    pf.add_argument("--file", required=True)

    pr = sub.add_parser("resolve", help="競合の解消")
    pr.add_argument("--xddp-dir", required=True)
    pr.add_argument("--docs", required=True)
    pr.add_argument("--file", required=True)
    pr.add_argument("--take", required=True, choices=["xddp", "docs"])
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "ensure":
            out = ensure(args.kind, Path(args.xddp_dir), Path(args.docs), split_keys(args.repos_keys),
                         args.today, repo=args.repo, cr=args.cr)
            print(json.dumps(out, ensure_ascii=False))
        elif args.cmd == "unfilled":
            path = Path(args.file)
            if not path.is_file():
                raise UsageError(f"ファイルがありません: {path}")
            keys = split_keys(args.repos_keys)
            if not keys:
                raise UsageError("--repos-keys が空です")
            print(json.dumps(unfilled(args.kind, path.read_text(encoding="utf-8"), keys), ensure_ascii=False))
        elif args.cmd == "domain-constraints":
            path = Path(args.file)
            if path.is_file():
                sys.stdout.write(domain_constraints(path.read_text(encoding="utf-8")))
        elif args.cmd == "promote":
            keys = split_keys(args.repos_keys)
            if not keys:
                raise UsageError("--repos-keys が空です")
            print(json.dumps(promote(Path(args.xddp_dir), Path(args.docs), keys), ensure_ascii=False))
        elif args.cmd == "diff":
            sys.stdout.write(diff(Path(args.xddp_dir), Path(args.docs), args.file))
        elif args.cmd == "resolve":
            out = resolve(Path(args.xddp_dir), Path(args.docs), args.file, args.take)
            print(json.dumps(out, ensure_ascii=False))
    except UsageError as e:
        print(f"rulebook_files.py: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
