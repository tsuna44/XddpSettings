"""
xddp_gate_snapshot.py — Human Review Gate の CHANGED 機械判定（snapshot / diff）

CR フォルダ全体（{CR_PATH} 配下一括）のファイル群について mtime + SHA-256 のスナップショットを
取得し（snapshot）、レビュー完了後に再計算したハッシュとの差分（diff）により、人がファイルを
直接編集したかどうかを機械的に判定する。git 非依存（成果物が git 管理外のワークスペースでも
動作させるため）。差分判定は SHA-256 の一致/不一致で行う（mtime のみだと touch で誤検出するため）。

Usage:
  python3 xddp_gate_snapshot.py snapshot --root CR_PATH --out OUT_JSON
  python3 xddp_gate_snapshot.py diff --snapshot OUT_JSON

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan(root: Path, exclude_abs: set) -> dict:
    files = {}
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        if p.resolve() in exclude_abs:
            continue
        rel = p.relative_to(root).as_posix()
        files[rel] = {"mtime": p.stat().st_mtime, "sha256": _sha256(p)}
    return files


def cmd_snapshot(args) -> None:
    root = Path(args.root)
    if not root.exists():
        _err(f"root ディレクトリが見つかりません: {root}")
    out_path = Path(args.out)
    exclude_abs = {out_path.resolve()}
    files = _scan(root, exclude_abs)
    snapshot = {"root": str(root.resolve()), "files": files}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"ok": True, "file_count": len(files), "out": str(out_path)}, ensure_ascii=False))


def cmd_diff(args) -> None:
    snap_path = Path(args.snapshot)
    if not snap_path.exists():
        _err(f"スナップショットファイルが見つかりません: {snap_path}")
    snapshot = json.loads(snap_path.read_text(encoding="utf-8"))
    root = Path(snapshot["root"])
    if not root.exists():
        _err(f"root ディレクトリが見つかりません: {root}")
    exclude_abs = {snap_path.resolve()}
    current = _scan(root, exclude_abs)
    old_files = snapshot["files"]
    changed_files = set()
    for rel, meta in current.items():
        if rel not in old_files or meta["sha256"] != old_files[rel]["sha256"]:
            changed_files.add(rel)
    for rel in old_files:
        if rel not in current:
            changed_files.add(rel)
    result = sorted(changed_files)
    print(json.dumps({"ok": True, "changed": len(result) > 0, "changed_files": result}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_snapshot = sub.add_parser("snapshot")
    p_snapshot.add_argument("--root", required=True)
    p_snapshot.add_argument("--out", required=True)
    p_snapshot.set_defaults(func=cmd_snapshot)

    p_diff = sub.add_parser("diff")
    p_diff.add_argument("--snapshot", required=True)
    p_diff.set_defaults(func=cmd_diff)

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
