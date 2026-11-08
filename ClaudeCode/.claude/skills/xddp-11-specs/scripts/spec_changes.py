"""
spec_changes.py — 工程11 の latest-specs の変更の記録（基準との比較）・`{DOCS}` にだけある既存の仕様の写し・中止の後片付け

latest-specs の変更は、LLM が書く一覧ではなく、工程11 の最初の実行の時点の状態（基準）と今の状態を比べて記録する。
基準は `{CR_PATH}/.latest-specs-baseline.json`（latest-specs の全ファイルの `latest-specs/…` の相対パスと SHA-256）。
progress.md の「## 工程11 更新仕様書ファイル一覧」「## 工程11 削除した仕様書ファイル一覧」は `record` が作り直す
（節の見出しと読み書きは `docs_layout.py`）。close の C0-3（`promote.py sync-baseline`）・C0-4・`collect_insights.py`・
中止（`revert`）がこの記録を読む。

Usage:
  python3 spec_changes.py seed --xddp-dir XDDP_DIR --cr CR --docs DOCS --areas a1,a2,...
      `{DOCS}/{area}/specs` にあって、latest-specs に無く、基準にも無いファイルを latest-specs へ写す
      （基準にあって今は無いファイルは今の CR の削除なので写さない。進行中の他の CR の削除一覧にあるものも写さない）。
      基準があれば、写したファイルを基準にも足す。工程11 Step 0 で snapshot の前に実行する。
  python3 spec_changes.py snapshot --xddp-dir XDDP_DIR --cr CR
      基準が無いときだけ書く（あれば何もしない）。
  python3 spec_changes.py record --xddp-dir XDDP_DIR --cr CR [--dry-run]
      基準と今の latest-specs を比べ、progress.md の2つの節を作り直す（`--dry-run` は書かない）。
  python3 spec_changes.py revert --xddp-dir XDDP_DIR --cr CR --docs DOCS [--dry-run]
      中止した CR の latest-specs の変更を、他の CR の変更を消さない安全な向きのものだけ元に戻す:
        - 変更したファイル: 基準の SHA-256 が `{DOCS}` の写しと一致し、今の `last-updated-cr` が今の CR のときだけ
          `{DOCS}` の内容に戻す
        - 削除したファイル: 基準の SHA-256 が `{DOCS}` の写しと一致するときだけ `{DOCS}` から戻す
        - 足したファイル: `last-updated-cr` が今の CR のときだけ消す
      それ以外は戻さず、理由とともに `kept` に返す。戻した後は record で progress.md の節を作り直す。

Output: stdout へ JSON 1行。
  seed:     {"ok", "copied": [...], "skipped_deleted_by_this_cr": [...], "skipped_deleted_by_other_cr": [{"path", "cr"}]}
  snapshot: {"ok", "created": bool, "files": N}
  record:   {"ok", "updated": [...], "deleted": [...], "written": bool}
  revert:   {"ok", "restored": [...], "removed": [...], "kept": [{"path", "reason"}], "dry_run": bool}

終了コード: 0 正常 / 1 入力の不正（record・revert で基準が無い・壊れている、progress.md が無い等。stderr にメッセージ）。
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xddp-common" / "scripts"))
import docs_layout  # noqa: E402

BASELINE_FILE = ".latest-specs-baseline.json"
LATEST_DIR = "latest-specs"


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def baseline_path(xddp_dir, cr: str) -> Path:
    return Path(xddp_dir) / cr / BASELINE_FILE


def scan_latest(xddp_dir) -> dict:
    """{`latest-specs/…` の相対パス: SHA-256}（隠しファイル・隠しディレクトリを除く）。"""
    root = Path(xddp_dir) / LATEST_DIR
    if not root.is_dir():
        return {}
    out = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and not any(part.startswith(".") for part in rel.parts):
            out[f"{LATEST_DIR}/{rel.as_posix()}"] = sha256(p)
    return out


def load_baseline(xddp_dir, cr: str, required: bool = True):
    """基準の {相対パス: SHA-256}。無ければ（`required` なら exit 1）None。壊れていれば exit 1。"""
    path = baseline_path(xddp_dir, cr)
    if not path.is_file():
        if required:
            _err(f"latest-specs の基準がありません: {path}（工程11 を実行していない CR です。"
                 f"/xddp-11-specs {cr} を先に実行してください）")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        _err(f"latest-specs の基準を JSON として読めません: {path}（{e}）")
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
        _err(f"latest-specs の基準の形式が不正です（{{\"files\": {{相対パス: SHA-256}}}}）: {path}")
    return dict(files)


def save_baseline(xddp_dir, cr: str, files: dict) -> None:
    path = baseline_path(xddp_dir, cr)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"cr": cr, "files": dict(sorted(files.items()))}, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


def docs_copy(docs, rel: str) -> Path:
    return docs_layout.latest_to_docs_path(docs, rel)


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _remove_empty_parents(path: Path, stop: Path) -> None:
    d = path.parent
    while d != stop and stop in d.parents and d.is_dir() and not any(d.iterdir()):
        d.rmdir()
        d = d.parent


# ---------------------------------------------------------------------------
# seed
# ---------------------------------------------------------------------------


def other_crs_deleted(xddp_dir, cr: str) -> dict:
    """進行中の他の CR の削除一覧 {`latest-specs/…`: CR}。"""
    out = {}
    for other in docs_layout.in_progress_crs(xddp_dir, exclude=cr):
        for rel in docs_layout.read_step11_lists(Path(xddp_dir) / other / "progress.md")["deleted"] or []:
            out.setdefault(rel, other)
    return out


def seed(xddp_dir, cr: str, docs, areas: list) -> dict:
    xddp_dir = Path(xddp_dir)
    base = load_baseline(xddp_dir, cr, required=False)
    others = other_crs_deleted(xddp_dir, cr)
    copied, by_this, by_other = [], [], []
    for area in areas:
        src_root = docs_layout.docs_specs_root(docs, area)
        if not src_root.is_dir():
            continue
        for src in sorted(src_root.rglob("*")):
            rel_in = src.relative_to(src_root)
            if not src.is_file() or any(part.startswith(".") for part in rel_in.parts):
                continue
            rel = f"{LATEST_DIR}/{area}/{rel_in.as_posix()}"
            dst = xddp_dir / rel
            if dst.exists():
                continue
            if base is not None and rel in base:
                by_this.append(rel)
                continue
            if rel in others:
                by_other.append({"path": rel, "cr": others[rel]})
                continue
            _copy(src, dst)
            copied.append(rel)
            if base is not None:
                base[rel] = sha256(dst)
    if base is not None and copied:
        save_baseline(xddp_dir, cr, base)
    return {"ok": True, "copied": copied, "skipped_deleted_by_this_cr": by_this,
            "skipped_deleted_by_other_cr": by_other}


# ---------------------------------------------------------------------------
# snapshot・record
# ---------------------------------------------------------------------------


def snapshot(xddp_dir, cr: str) -> dict:
    if baseline_path(xddp_dir, cr).is_file():
        return {"ok": True, "created": False, "files": len(load_baseline(xddp_dir, cr))}   # 壊れていれば止める
    files = scan_latest(xddp_dir)
    save_baseline(xddp_dir, cr, files)
    return {"ok": True, "created": True, "files": len(files)}


def changes(xddp_dir, cr: str) -> dict:
    """{"updated": 足した・内容が変わった, "deleted": 基準にあって今は無い, "baseline", "current"}。"""
    base = load_baseline(xddp_dir, cr)
    current = scan_latest(xddp_dir)
    updated = sorted(p for p, h in current.items() if base.get(p) != h)
    deleted = sorted(p for p in base if p not in current)
    return {"updated": updated, "deleted": deleted, "baseline": base, "current": current}


def record(xddp_dir, cr: str, dry_run: bool = False) -> dict:
    ch = changes(xddp_dir, cr)
    written = False
    if not dry_run:
        progress = Path(xddp_dir) / cr / "progress.md"
        if not progress.is_file():
            _err(f"progress.md がありません: {progress}")
        text = progress.read_text(encoding="utf-8")
        new = docs_layout.write_step11_lists(text, ch["updated"], ch["deleted"])
        if new != text:
            progress.write_text(new, encoding="utf-8")
            written = True
    return {"ok": True, "updated": ch["updated"], "deleted": ch["deleted"], "written": written}


# ---------------------------------------------------------------------------
# revert（中止の後片付け）
# ---------------------------------------------------------------------------


def revert(xddp_dir, cr: str, docs, dry_run: bool = False) -> dict:
    xddp_dir = Path(xddp_dir)
    ch = changes(xddp_dir, cr)
    base = ch["baseline"]
    restored, removed, kept = [], [], []

    def _docs_matches_baseline(rel: str):
        src = docs_copy(docs, rel)
        if not src.is_file():
            return None, "`{DOCS}` に写しが無い"
        if sha256(src) != base[rel]:
            return None, "基準の時点で `{DOCS}` と違う（他の CR の未昇格の変更を含みうる）"
        return src, ""

    for rel in ch["updated"]:
        path = xddp_dir / rel
        owner = docs_layout.last_updated_cr(path)
        if rel in base:
            src, reason = _docs_matches_baseline(rel)
            if src is None:
                kept.append({"path": rel, "reason": reason})
            elif owner != cr:
                kept.append({"path": rel, "reason": f"`last-updated-cr` が別の CR（{owner or 'なし'}）"})
            else:
                restored.append(rel)
                if not dry_run:
                    _copy(src, path)
        elif owner == cr:
            removed.append(rel)
            if not dry_run:
                path.unlink()
                _remove_empty_parents(path, xddp_dir / LATEST_DIR)
        else:
            kept.append({"path": rel, "reason": f"足したファイルの `last-updated-cr` が別の CR（{owner or 'なし'}）"})
    for rel in ch["deleted"]:
        src, reason = _docs_matches_baseline(rel)
        if src is None:
            kept.append({"path": rel, "reason": reason})
        else:
            restored.append(rel)
            if not dry_run:
                _copy(src, xddp_dir / rel)
    if not dry_run:
        record(xddp_dir, cr)
    return {"ok": True, "restored": sorted(restored), "removed": sorted(removed), "kept": kept, "dry_run": dry_run}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _split(raw: str) -> list:
    return [s.strip() for s in (raw or "").split(",") if s.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("seed")
    p.add_argument("--xddp-dir", required=True)
    p.add_argument("--cr", required=True)
    p.add_argument("--docs", required=True)
    p.add_argument("--areas", required=True, help="今の CR の repo・cross（HAS_CROSS）・system（カンマ区切り）")
    p.set_defaults(func=lambda a: seed(a.xddp_dir, a.cr, a.docs, _split(a.areas)))

    p = sub.add_parser("snapshot")
    p.add_argument("--xddp-dir", required=True)
    p.add_argument("--cr", required=True)
    p.set_defaults(func=lambda a: snapshot(a.xddp_dir, a.cr))

    p = sub.add_parser("record")
    p.add_argument("--xddp-dir", required=True)
    p.add_argument("--cr", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=lambda a: record(a.xddp_dir, a.cr, a.dry_run))

    p = sub.add_parser("revert")
    p.add_argument("--xddp-dir", required=True)
    p.add_argument("--cr", required=True)
    p.add_argument("--docs", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=lambda a: revert(a.xddp_dir, a.cr, a.docs, a.dry_run))
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(args.func(args), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
