"""
chd_regression.py — CHD の回帰の範囲（工程6 Step A3）の決定的処理 CLI

CHD「## 4. トレーサビリティマトリクス」から回帰の起点（変更シンボル）の一覧を作り（elements）、
`specout_bfs.py regression-candidates` が出した回帰の候補と CHD「## 7. 確認項目」の確認種別「回帰」の行・
「### 7.1 回帰の候補のうち確認項目にしなかったもの」の対応を照合する（check）。Step A3 の入力の指紋を記録し（record）、
今の入力と比べて回帰の範囲が古いかを判定する（status）。算出に失敗した repo の古い要約と入力の記録を消す（invalidate）。
CHD ファイルの解決と表の読み方は `chd_sp_coverage.py` と共有する。標準ライブラリのみ。

Usage:
  python3 chd_regression.py elements --design-dir DESIGN_DIR --specout-dir SPECOUT_DIR --repos a,b --repo REPO --cr CR
      --out ELEMENTS_JSON
  python3 chd_regression.py check --candidates CANDIDATES_JSON --design-dir DESIGN_DIR --repo REPO --cr CR
  python3 chd_regression.py record --design-dir DESIGN_DIR --specout-dir SPECOUT_DIR --repos a,b --repo REPO --cr CR
      --params-key KEY --out INPUTS_JSON
  python3 chd_regression.py status --design-dir DESIGN_DIR --specout-dir SPECOUT_DIR --repos a,b --repo REPO --cr CR
      --params-key KEY --recorded INPUTS_JSON
  python3 chd_regression.py invalidate --work-dir WORK_DIR [--human-out HUMAN_MD]

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        elements・record・status は、関係する repo（--repo と、--repo に採用した `cross-{repo}-*` の調査がある repo）の
        CHD §4 の書式の誤りで終了コード 1（stderr に1行1件 `{バッチファイルの絶対パス}\\t{行番号}\\t{理由}`）。
        check は CHD §7・§7.1 の表の書式の誤りで終了コード 1（照合の結果によらず、それ以外は終了コード 0）。
        status は入力の記録が無ければ {"stale": false, "recorded": false}。
"""

import argparse
import datetime
import hashlib
import json
import posixpath
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chd_sp_coverage import (  # noqa: E402
    TM_HEADING,
    _find_table_start,
    _split_row,
    resolve_chd_content_files,
)

KINDS = ("関数", "データ構造", "変数", "定数", "インタフェース")
CHANGES = ("追加", "振る舞い", "シグネチャ", "削除")
KIND_INTERFACE = "インタフェース"
CONFIRM_HEADING = "## 7. 確認項目（テスト観点）"
EXCLUDED_HEADING = "### 7.1 回帰の候補のうち確認項目にしなかったもの"
CONFIRM_KIND_REGRESSION = "回帰"
CANDIDATE_COLUMN = "回帰の候補"
NO_VALUE = ("", "-", "—")
DIGEST_GLOB = "regression-digest-*.md"
INPUTS_FILE = "regression-inputs.json"
STALE_NOTE = "> ⚠️ 最新の回帰の範囲の算出に失敗した。この表は前回の算出の結果で、今の CHD §4 と合わない。"
NAME_RULE = ("識別子は1行に1つ。型のメンバー（メソッド・フィールド）は言語によらず `{型名}::{名前}`、グローバル変数のフィールドは"
             "`{変数名}.{フィールド名}`。名前の中の空白・`<…>`・`(…)` はそのまま書いてよい。`<…>`・`(…)` の外の `,`・`、` は区切り")


class _FormatErrors(Exception):
    def __init__(self, lines):
        super().__init__("\n".join(lines))
        self.lines = lines


def _err(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def _split_csv(raw: str) -> list:
    return [s.strip() for s in (raw or "").split(",") if s.strip()]


def split_names(cell: str) -> list:
    """`<…>`・`(…)` の外の `,`・`、` で区切る（空白は区切りにしない）。"""
    out, cur, depth = [], [], 0
    for c in cell or "":
        if c in "<(":
            depth += 1
        elif c in ">)":
            depth = max(0, depth - 1)
        if depth == 0 and c in ",、":
            out.append("".join(cur))
            cur = []
            continue
        cur.append(c)
    out.append("".join(cur))
    return [s.strip().strip("`").strip() for s in out if s.strip().strip("`").strip()]


def _strip_code(s: str) -> str:
    s = (s or "").strip()
    if len(s) >= 2 and s.startswith("`") and s.endswith("`"):
        s = s[1:-1].strip()
    return s


def norm_file(raw: str) -> str:
    """リポジトリのルートからの相対パスに正規化する（`/` 区切り・先頭の `./` を除く。specout_bfs.py の _norm_path と同じ規則）。"""
    s = _strip_code(raw).replace("\\", "/")
    s = posixpath.normpath(s) if s else s
    return "." if s in ("", ".") else s


def norm_key(raw: str) -> str:
    """候補のキー（`{ファイル}::{関数}`／`{ファイル}`）の正規化。最初の `::` の前をファイルとして正規化する。"""
    s = _strip_code(raw)
    if "::" in s:
        f, rest = s.split("::", 1)
        return f"{norm_file(f)}::{rest.strip()}"
    return norm_file(s)


def _is_relative(raw: str) -> bool:
    s = _strip_code(raw).replace("\\", "/")
    if s.startswith("/") or re.match(r"^[A-Za-z]:/", s):
        return False
    return ".." not in s.split("/")


def _table_rows(lines: list, start: int) -> list:
    """表の行（区切り行を除く）を [(ファイルの行番号, セル)] で返す。最初の要素はヘッダ。"""
    out, i = [], start
    while i < len(lines) and lines[i].strip().startswith("|"):
        cells = _split_row(lines[i])
        if not (cells and all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cells)):
            out.append((i + 1, cells))
        i += 1
    return out


def _col(header: list, name: str, prefix: bool = False):
    for i, c in enumerate(header):
        if c == name or (prefix and c.startswith(name)):
            return i
    return None


def _section4_rows(path: Path, repo: str, batch: str, errors: list) -> list:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").split("\n")
    start = _find_table_start(lines, TM_HEADING)
    if start is None:
        return []
    rows = _table_rows(lines, start)
    if not rows:
        return []
    hdr_line, header = rows[0]
    cols = {"sp": _col(header, "仕様ID"), "file": _col(header, "変更ファイル"),
            "symbol": _col(header, "変更シンボル", prefix=True), "kind": _col(header, "種別"),
            "change": _col(header, "変更の内容")}
    missing = [k for k, n in (("kind", "種別"), ("change", "変更の内容"), ("symbol", "変更シンボル"),
                              ("file", "変更ファイル"), ("sp", "仕様ID")) if cols[k] is None]
    if missing:
        names = {"kind": "種別", "change": "変更の内容", "symbol": "変更シンボル", "file": "変更ファイル", "sp": "仕様ID"}
        errors.append(f"{path.resolve()}\t{hdr_line}\t第4章の表に列が足りない（{'・'.join(names[k] for k in missing)}）。"
                      f"列は「仕様ID・仕様名・変更ファイル・変更シンボル・種別・変更の内容」")
        return []
    out = []
    for line_no, cells in rows[1:]:
        if len(cells) < len(header):
            errors.append(f"{path.resolve()}\t{line_no}\t列が足りない（{len(cells)} 列。表は {len(header)} 列）")
            continue
        raw_file = cells[cols["file"]]
        if _strip_code(raw_file) in NO_VALUE:
            continue
        raw_symbol = cells[cols["symbol"]]
        if _strip_code(raw_symbol) in NO_VALUE:
            continue
        kind, change = _strip_code(cells[cols["kind"]]), _strip_code(cells[cols["change"]])
        bad = False
        if not _is_relative(raw_file):
            errors.append(f"{path.resolve()}\t{line_no}\t変更ファイルがリポジトリのルートからの相対パスでない"
                          f"（{_strip_code(raw_file)}。先頭の `./`・絶対パス・`..` を使わない）")
            bad = True
        if kind not in KINDS:
            errors.append(f"{path.resolve()}\t{line_no}\t種別が許可された値でない（{kind or '空'}。"
                          f"値は {'／'.join(KINDS)}）")
            bad = True
        if change not in CHANGES:
            errors.append(f"{path.resolve()}\t{line_no}\t変更の内容が許可された値でない（{change or '空'}。"
                          f"値は {'／'.join(CHANGES)}）")
            bad = True
        names = [_strip_code(raw_symbol)] if kind == KIND_INTERFACE else split_names(raw_symbol)
        if len(names) != 1:
            errors.append(f"{path.resolve()}\t{line_no}\t1つのセルに複数の変更シンボルがある（{_strip_code(raw_symbol)}）。"
                          f"行を分ける。{NAME_RULE}")
            bad = True
        if bad:
            continue
        out.append({"repo": repo, "batch_name": batch, "sp": _strip_code(cells[cols["sp"]]),
                    "file": norm_file(raw_file), "symbol": names[0], "kind": kind, "change": change})
    return out


def _adopted_runs(specout_dir: Path, repo: str) -> list:
    path = specout_dir / repo / "ripple" / "runs.json"
    if not path.is_file():
        return []
    try:
        reg = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        _err(f"調査の記録を JSON として読めません: {path}")
    return [r["run"] for r in reg.get("runs") or [] if isinstance(r, dict) and r.get("adopted") is True
            and isinstance(r.get("run"), str)]


def relevant_repos(repos: list, repo: str, specout_dir: Path) -> list:
    """--repo と、--repo に採用した `cross-{その repo}-*` の調査がある他の repo（cross は除く）。"""
    adopted = _adopted_runs(specout_dir, repo)
    others = [r for r in repos if r not in (repo, "cross") and any(n.startswith(f"cross-{r}-") for n in adopted)]
    return [repo] + others


def collect_elements(design_dir: Path, specout_dir: Path, repos: list, repo: str, cr: str) -> tuple:
    """(関係する repo, 変更シンボルの一覧)。関係する repo の §4 の書式の誤りは _FormatErrors。"""
    rel = relevant_repos(repos, repo, specout_dir)
    errors, elements = [], []
    for r in rel:
        _index, content = resolve_chd_content_files(design_dir, r, cr)
        for f in content:
            elements += _section4_rows(Path(f), r, Path(f).name, errors)
    if errors:
        raise _FormatErrors(errors)
    return rel, elements


def _elements_or_exit(args) -> tuple:
    try:
        return collect_elements(Path(args.design_dir), Path(args.specout_dir), _split_csv(args.repos), args.repo,
                                args.cr)
    except _FormatErrors as e:
        print("\n".join(e.lines), file=sys.stderr)
        sys.exit(1)


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def cmd_elements(args) -> None:
    rel, elements = _elements_or_exit(args)
    _write_json(Path(args.out), {"cr": args.cr, "repo": args.repo, "relevant_repos": rel, "elements": elements})
    print(json.dumps({"ok": True, "relevant_repos": rel, "element_count": len(elements), "out": args.out},
                     ensure_ascii=False))


def _keys_in_section(path: Path, heading: str, need_kind: bool) -> list:
    """§7（need_kind: 確認種別「回帰」の行だけ）・§7.1 の「回帰の候補」列のキー。書式の誤りは _FormatErrors。"""
    lines = path.read_text(encoding="utf-8").split("\n")
    start = _find_table_start(lines, heading)
    if start is None:
        return []
    rows = _table_rows(lines, start)
    if not rows:
        return []
    hdr_line, header = rows[0]
    ci, ki = _col(header, CANDIDATE_COLUMN), _col(header, "確認種別")
    data = rows[1:]
    if need_kind and ki is None:
        raise _FormatErrors([f"{path.resolve()}\t{hdr_line}\t第7章の表に「確認種別」列が無い"])
    if ci is None:
        if need_kind and any(len(c) > ki and _strip_code(c[ki]) == CONFIRM_KIND_REGRESSION for _l, c in data):
            raise _FormatErrors([f"{path.resolve()}\t{hdr_line}\t確認種別「回帰」の行があるが「回帰の候補」列が無い"])
        if not need_kind:
            raise _FormatErrors([f"{path.resolve()}\t{hdr_line}\t第7.1節の表に「回帰の候補」列が無い"])
        return []
    keys = []
    for line_no, cells in data:
        if len(cells) != len(header):
            raise _FormatErrors([f"{path.resolve()}\t{line_no}\t列の数が表の見出しと合わない"])
        if need_kind and _strip_code(cells[ki]) != CONFIRM_KIND_REGRESSION:
            continue
        keys += [norm_key(k) for k in split_names(cells[ci]) if _strip_code(k) not in NO_VALUE]
    return keys


def cmd_check(args) -> None:
    try:
        data = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
        cands = data["candidates"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        _err(f"回帰の候補の JSON を読めません: {args.candidates}（{e}）")
    all_keys = {norm_key(c["key"]) for c in cands}
    required = sorted({norm_key(c["key"]) for c in cands if c.get("required")})
    _index, content = resolve_chd_content_files(Path(args.design_dir), args.repo, args.cr)
    in7, in71 = set(), set()
    try:
        for f in content:
            p = Path(f)
            if not p.exists():
                continue
            in7.update(_keys_in_section(p, CONFIRM_HEADING, True))
            in71.update(_keys_in_section(p, EXCLUDED_HEADING, False))
    except _FormatErrors as e:
        print("\n".join(e.lines), file=sys.stderr)
        sys.exit(1)
    mapped = [k for k in required if k in in7]
    excluded = [k for k in required if k not in in7 and k in in71]
    unmapped = [k for k in required if k not in in7 and k not in in71]
    unknown = sorted((in7 | in71) - all_keys)
    print(json.dumps({"ok": True, "unmapped": unmapped, "unknown": unknown, "mapped_count": len(mapped),
                      "excluded_count": len(excluded)}, ensure_ascii=False))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def fingerprint(args) -> str:
    rel, elements = _elements_or_exit(args)
    specout_dir = Path(args.specout_dir)
    repo_dir = specout_dir / args.repo
    runs = sorted(_adopted_runs(specout_dir, args.repo))
    material = {
        "relevant_repos": rel,
        "elements": elements,
        "adopted_runs": runs,
        "discovery_logs": {r: _sha256_file(repo_dir / "ripple" / r / "discovery-log.md") for r in runs},
        "no_ripple": (repo_dir / "work" / "no-ripple.json").is_file(),
        "params_key": args.params_key,
    }
    return hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def cmd_record(args) -> None:
    fp = fingerprint(args)
    _write_json(Path(args.out), {"cr": args.cr, "repo": args.repo, "fingerprint": fp,
                                 "recorded_at": datetime.datetime.now().isoformat(timespec="seconds")})
    print(json.dumps({"ok": True, "fingerprint": fp}, ensure_ascii=False))


def cmd_status(args) -> None:
    rec_path = Path(args.recorded)
    recorded = None
    if rec_path.is_file():
        try:
            recorded = json.loads(rec_path.read_text(encoding="utf-8")).get("fingerprint")
        except (ValueError, AttributeError):
            recorded = None
    fp = fingerprint(args)
    if not recorded:
        print(json.dumps({"ok": True, "stale": False, "recorded": False}, ensure_ascii=False))
        return
    print(json.dumps({"ok": True, "stale": recorded != fp, "recorded": True}, ensure_ascii=False))


def cmd_invalidate(args) -> None:
    work = Path(args.work_dir)
    removed = []
    if work.is_dir():
        for p in sorted(work.glob(DIGEST_GLOB)) + [work / INPUTS_FILE]:
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

    def _common(p):
        p.add_argument("--design-dir", required=True)
        p.add_argument("--specout-dir", required=True)
        p.add_argument("--repos", required=True)
        p.add_argument("--repo", required=True)
        p.add_argument("--cr", required=True)

    p_el = sub.add_parser("elements")
    _common(p_el)
    p_el.add_argument("--out", required=True)
    p_el.set_defaults(func=cmd_elements)

    p_ck = sub.add_parser("check")
    p_ck.add_argument("--candidates", required=True)
    p_ck.add_argument("--design-dir", required=True)
    p_ck.add_argument("--repo", required=True)
    p_ck.add_argument("--cr", required=True)
    p_ck.set_defaults(func=cmd_check)

    p_rec = sub.add_parser("record")
    _common(p_rec)
    p_rec.add_argument("--params-key", required=True)
    p_rec.add_argument("--out", required=True)
    p_rec.set_defaults(func=cmd_record)

    p_st = sub.add_parser("status")
    _common(p_st)
    p_st.add_argument("--params-key", required=True)
    p_st.add_argument("--recorded", required=True)
    p_st.set_defaults(func=cmd_status)

    p_inv = sub.add_parser("invalidate")
    p_inv.add_argument("--work-dir", required=True)
    p_inv.add_argument("--human-out", default=None)
    p_inv.set_defaults(func=cmd_invalidate)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — CLI境界でのエラーはstderrへ集約する
        _err(f"予期しないエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
