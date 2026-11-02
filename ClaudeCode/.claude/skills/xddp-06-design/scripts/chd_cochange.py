#!/usr/bin/env python3
"""一緒に直す候補（工程6 Step A2.5）と CHD §4・§4.1 の照合・入力の記録と古さの判定。

  chd_cochange.py check --candidates CANDIDATES_JSON --design-dir DIR --repo REPO --cr CR
                        [--human-out HUMAN_MD] [--metrics METRICS_JSONL --today DATE]
  chd_cochange.py record --design-dir DIR --specout-dir DIR --repos KEYS --repo REPO --cr CR --params-key KEY --out INPUTS_JSON
  chd_cochange.py status --design-dir DIR --specout-dir DIR --repos KEYS --repo REPO --cr CR --params-key KEY --recorded INPUTS_JSON
  chd_cochange.py invalidate --work-dir DIR --human-out HUMAN_MD

候補（specout_fieldtrace.py candidates の cochange-candidates.json）のうち確認対象と上限超過を、repo の全バッチの §4（変更）・
§4.1（変更にしなかったもの）と照合する。1つの候補が複数の場所で処理済みなら §4 ＞ §4.1 不要 ＞ §4.1 確認できず の順で1つに決める。
終了コード: 0＝成功／1＝§4 の表の書式の誤り・入力の誤り／2＝使い方の誤り／4＝§4.1 の表の書式の誤り。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chd_regression import (  # noqa: E402
    _FormatErrors,
    _section4_rows,
    _strip_code,
    _table_rows,
    _col,
    _write_json,
    collect_elements,
)
from chd_sp_coverage import _find_table_start, resolve_chd_content_files  # noqa: E402

FIELDTRACE_DIR = Path(__file__).resolve().parents[2] / "xddp-04-specout" / "scripts"

EXCLUDED_HEADING = "### 4.1 一緒に直す候補のうち変更にしなかったもの"
COL_CANDIDATE, COL_KIND, COL_ORIGIN, COL_JUDGE, COL_REASON = "候補", "候補の種類", "起点（変更シンボル）", "判断", "理由"
JUDGE_UNNEEDED, JUDGE_UNCONFIRMED = "不要", "確認できず"
STATUS_S4, STATUS_UNNEEDED, STATUS_UNCONFIRMED, STATUS_OPEN = "§4", "§4.1 不要", "§4.1 確認できず", "未処理"
PRIORITY = {STATUS_S4: 0, STATUS_UNNEEDED: 1, STATUS_UNCONFIRMED: 2}
REQUIRED, OVER_LIMIT = "required", "over-limit"
HEAD_MAX = 10
DIGEST_GLOB = "cochange-digest-*"
WORK_FILES = ("cochange-candidates.json", "cochange-inputs.json", "cochange-elements.json")
STALE_NOTE = "> ⚠️ 最新の一緒に直す候補の算出に失敗した。この表は前回の算出の結果で、今の CHD §4 と合わない。"


class _Section41Errors(Exception):
    def __init__(self, lines):
        super().__init__("\n".join(lines))
        self.lines = lines


def _err(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------------------
# 変更シンボルの正規化と一致
# ---------------------------------------------------------------------------

def _strip_templates(s: str) -> str:
    out, depth = [], 0
    for ch in s:
        if ch == "<":
            depth += 1
        elif ch == ">" and depth:
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def symbol_parts(sym: str) -> list:
    """`(…)`（`operator()` の `()` は残す）と `<…>` を除き、`::` で分ける。"""
    s = _strip_code(sym).strip()
    if not s.endswith("operator()"):
        m = re.search(r"\([^()]*\)\s*(?:const)?\s*$", s)
        if m:
            s = s[:m.start()].rstrip()
    return [p.strip() for p in _strip_templates(s).split("::") if p.strip()]


def suffix_match(sym_parts: list, key_parts: list, type_names: set) -> bool:
    """key_parts が sym_parts の末尾に一致し、残りの前置きがすべて名前空間（型名でない）か。"""
    n = len(key_parts)
    if n == 0 or len(sym_parts) < n or sym_parts[-n:] != key_parts:
        return False
    return not any(p in type_names for p in sym_parts[:-n])


def split_key(key: str):
    """キーを (ファイル, 名前の要素) に分ける。最初の `::` の前がファイル。ファイルだけのキーは (ファイル, [])。"""
    if "::" not in key:
        return key, []
    f, rest = key.split("::", 1)
    return f, [p for p in rest.split("::") if p]


def s4_matches(cand: dict, row: dict, type_names: set) -> bool:
    f, parts = split_key(cand["key"])
    if row["file"] != f:
        return False
    if not parts:
        return True
    sp = symbol_parts(row["symbol"])
    if cand.get("kind") == "型":
        return suffix_match(sp, parts, type_names) or (len(sp) > 1 and suffix_match(sp[:-1], parts, type_names))
    return suffix_match(sp, parts, type_names)


# ---------------------------------------------------------------------------
# §4・§4.1 の読み取り
# ---------------------------------------------------------------------------

def section41_rows(path: Path) -> list:
    """§4.1 の行: [{key, judge, file, line}]。「なし」・表が無ければ []。書式の誤りは _Section41Errors。"""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").split("\n")
    start = _find_table_start(lines, EXCLUDED_HEADING)
    if start is None:
        return []
    rows = _table_rows(lines, start)
    if not rows:
        return []
    hdr_line, header = rows[0]
    cols = {"cand": _col(header, COL_CANDIDATE), "judge": _col(header, COL_JUDGE)}
    missing = [n for k, n in (("cand", COL_CANDIDATE), ("judge", COL_JUDGE)) if cols[k] is None]
    if missing:
        raise _Section41Errors([f"{path.resolve()}\t{hdr_line}\t§4.1 の表に列が無い（{'・'.join(missing)}）"])
    out, errors = [], []
    for line_no, cells in rows[1:]:
        if len(cells) <= max(cols.values()):
            errors.append(f"{path.resolve()}\t{line_no}\t§4.1 の列が足りない")
            continue
        key = _strip_code(cells[cols["cand"]]).strip()
        judge = _strip_code(cells[cols["judge"]]).strip()
        if not key or key in ("-", "—"):
            continue
        if judge not in (JUDGE_UNNEEDED, JUDGE_UNCONFIRMED):
            errors.append(f"{path.resolve()}\t{line_no}\t§4.1 の判断が許可された値でない（{judge or '空'}。値は "
                          f"{JUDGE_UNNEEDED}／{JUDGE_UNCONFIRMED}）")
            continue
        out.append({"key": key, "judge": judge, "file": str(path), "line": line_no})
    if errors:
        raise _Section41Errors(errors)
    return out


def repo_sections(design_dir: Path, repo: str, cr: str):
    """(§4 の行, §4.1 の行)。§4 の書式の誤りは _FormatErrors、§4.1 は _Section41Errors。"""
    _index, content = resolve_chd_content_files(design_dir, repo, cr)
    s4_errors, s4, s41, s41_errors = [], [], [], []
    for f in content:
        p = Path(f)
        for r in _section4_rows(p, repo, p.name, s4_errors):
            r["batch_file"] = str(p)
            s4.append(r)
        try:
            s41 += section41_rows(p)
        except _Section41Errors as e:
            s41_errors += e.lines
    if s4_errors:
        raise _FormatErrors(s4_errors)
    if s41_errors:
        raise _Section41Errors(s41_errors)
    return s4, s41


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def check(cands: dict, s4: list, s41: list) -> dict:
    type_names = set(cands.get("type_names") or [])
    rows = cands.get("candidates") or []
    keys = {r["key"] for r in rows}
    status, conflicts = {}, []
    s41_by_key = {}
    for r in s41:
        s41_by_key.setdefault(r["key"], []).append(r)
    for c in rows:
        places = []
        if any(s4_matches(c, r, type_names) for r in s4):
            places.append((STATUS_S4, "§4"))
        for r in s41_by_key.get(c["key"], []):
            places.append((STATUS_UNNEEDED if r["judge"] == JUDGE_UNNEEDED else STATUS_UNCONFIRMED,
                           f"§4.1 {Path(r['file']).name}:{r['line']}"))
        if not places:
            status[c["key"]] = STATUS_OPEN
            continue
        status[c["key"]] = min((p[0] for p in places), key=lambda s: PRIORITY[s])
        s41_places = [p for p in places if p[0] != STATUS_S4]
        if (any(p[0] == STATUS_S4 for p in places) and s41_places) or len(s41_places) > 1:
            conflicts.append({"key": c["key"], "places": [p[1] for p in places]})
    required = [c for c in rows if c.get("treatment") == REQUIRED]
    over = [c for c in rows if c.get("treatment") == OVER_LIMIT]
    unmapped = [{"key": c["key"], "batch_file": c.get("batch_file")} for c in required if status[c["key"]] == STATUS_OPEN]
    over_open = [c for c in over if status[c["key"]] == STATUS_OPEN]
    head = [{"key": c["key"], "tags": c.get("tags", []), "distance": c.get("distance"), "batch_name": c.get("batch_name")}
            for c in over_open if c.get("table") == 2][:HEAD_MAX]
    unknown = sorted(k for k in s41_by_key if k not in keys)
    return {
        "ok": True, "unmapped": unmapped, "unknown": unknown, "conflicts": conflicts,
        "mapped_count": sum(1 for c in required if status[c["key"]] == STATUS_S4),
        "excluded_count": sum(1 for c in required if status[c["key"]] == STATUS_UNNEEDED),
        "unconfirmed_count": sum(1 for c in required if status[c["key"]] == STATUS_UNCONFIRMED),
        "over_limit_open_by_table": {"1": sum(1 for c in over_open if c.get("table") == 1),
                                     "2": sum(1 for c in over_open if c.get("table") == 2)},
        "over_limit_open_head": head,
        "_status": status,
        "_counts": {"required": len(required), "over_limit": len(over),
                    "over_limit_handled": len(over) - len(over_open),
                    "name_only_far": sum(1 for c in rows if c.get("treatment") == "name-only-far"),
                    "by_kind": {k: sum(1 for c in rows if c.get("kind") == k) for k in ("関数", "型", "ファイル")}},
    }


def cmd_check(args) -> None:
    try:
        cands = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        _err(f"--candidates を読めません: {args.candidates}（{e}）")
    try:
        s4, s41 = repo_sections(Path(args.design_dir), args.repo, args.cr)
    except _FormatErrors as e:
        _err(str(e), 1)
    except _Section41Errors as e:
        _err(str(e), 4)
    res = check(cands, s4, s41)
    status, counts = res.pop("_status"), res.pop("_counts")
    if args.human_out:
        sys.path.insert(0, str(FIELDTRACE_DIR))
        try:
            from specout_fieldtrace import render_human
        except ImportError as e:
            _err(f"specout_fieldtrace.py を読み込めません（setup.sh を実行してください）: {e}")
        hp = Path(args.human_out)
        hp.parent.mkdir(parents=True, exist_ok=True)
        hp.write_text(render_human(cands, status), encoding="utf-8")
    if args.metrics:
        line = {"event": "cochange_summary", "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                "date": args.today or "", "repo": args.repo, "engine": cands.get("engine"),
                "after_coding": bool(cands.get("after_coding")),
                "candidate_count_by_kind": counts["by_kind"], "required_count": counts["required"],
                "over_limit_count": counts["over_limit"], "name_only_far_count": counts["name_only_far"],
                "name_only_count": sum(1 for c in cands.get("candidates") or [] if c.get("identity") == "name-only"),
                "mapped_count": res["mapped_count"], "excluded_count": res["excluded_count"],
                "unconfirmed_count": res["unconfirmed_count"], "unmapped_count": len(res["unmapped"]),
                "over_limit_handled_count": counts["over_limit_handled"],
                "over_limit_open_count": counts["over_limit"] - counts["over_limit_handled"]}
        mp = Path(args.metrics)
        mp.parent.mkdir(parents=True, exist_ok=True)
        with open(mp, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(json.dumps(res, ensure_ascii=False))


# ---------------------------------------------------------------------------
# record / status / invalidate
# ---------------------------------------------------------------------------

def fingerprint(args) -> str:
    design_dir = Path(args.design_dir)
    repos = [r for r in args.repos.split(",") if r]
    try:
        _rel, elements = collect_elements(design_dir, Path(args.specout_dir), repos, args.repo, args.cr)
        _s4, s41 = repo_sections(design_dir, args.repo, args.cr)
    except _FormatErrors as e:
        _err(str(e), 1)
    except _Section41Errors as e:
        _err(str(e), 4)
    material = {
        "elements": [e for e in elements if e.get("repo") == args.repo],
        "section41": sorted((r["key"], r["judge"], Path(r["file"]).name) for r in s41),
        "params_key": args.params_key,
    }
    return hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def cmd_record(args) -> None:
    fp = fingerprint(args)
    _write_json(Path(args.out), {"cr": args.cr, "repo": args.repo, "fingerprint": fp,
                                 "recorded_at": datetime.datetime.now().isoformat(timespec="seconds")})
    print(json.dumps({"ok": True, "fingerprint": fp}, ensure_ascii=False))


def cmd_status(args) -> None:
    fp = fingerprint(args)
    rec = Path(args.recorded)
    if not rec.is_file():
        print(json.dumps({"ok": True, "stale": False, "recorded": False}, ensure_ascii=False))
        return
    try:
        recorded = json.loads(rec.read_text(encoding="utf-8")).get("fingerprint")
    except ValueError:
        recorded = None
    print(json.dumps({"ok": True, "stale": recorded != fp, "recorded": True}, ensure_ascii=False))


def cmd_invalidate(args) -> None:
    work = Path(args.work_dir)
    removed = []
    if work.is_dir():
        for p in sorted(work.glob(DIGEST_GLOB)) + [work / n for n in WORK_FILES]:
            if p.is_file():
                p.unlink()
                removed.append(str(p))
    noted = False
    if args.human_out and Path(args.human_out).is_file():
        p = Path(args.human_out)
        text = p.read_text(encoding="utf-8")
        if STALE_NOTE not in text:
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(STALE_NOTE + "\n\n" + text)
            noted = True
    print(json.dumps({"ok": True, "removed": removed, "human_out_noted": noted}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check")
    p.add_argument("--candidates", required=True)
    p.add_argument("--design-dir", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--cr", required=True)
    p.add_argument("--human-out")
    p.add_argument("--metrics")
    p.add_argument("--today")
    p.set_defaults(func=cmd_check)

    def _common(q):
        q.add_argument("--design-dir", required=True)
        q.add_argument("--specout-dir", required=True)
        q.add_argument("--repos", required=True)
        q.add_argument("--repo", required=True)
        q.add_argument("--cr", required=True)
        q.add_argument("--params-key", required=True)

    p = sub.add_parser("record")
    _common(p)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_record)
    p = sub.add_parser("status")
    _common(p)
    p.add_argument("--recorded", required=True)
    p.set_defaults(func=cmd_status)
    p = sub.add_parser("invalidate")
    p.add_argument("--work-dir", required=True)
    p.add_argument("--human-out")
    p.set_defaults(func=cmd_invalidate)
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
