"""
xddp_metrics.py — 工程別テレメトリ CLI（レビューラウンド数・所要時間）

実行中の XDDP スキルセッションから実測可能な2指標のみを {CR_PATH}/metrics.jsonl へ
1行1イベントの append-only JSONL で記録する。トークン数・コストは対象外
（`tools/harness/smoke_full.py` の headless 校正ラン専用。docs/xddp-tool-analysis-2026-08.md 参照）。

Usage:
  python3 xddp_metrics.py phase-start --cr-path CR_PATH --step STEP
  python3 xddp_metrics.py record --cr-path CR_PATH --step STEP --event {review_loop|phase_complete}
      [--document-type TYPE] [--review-rounds N] [--review-max-rounds N]
      [--review-outcome {converged|max_rounds_exhausted|skipped}] [--target TEXT] [--note TEXT]

Output: 成功時は stdout に JSON 1オブジェクト（{"ok": true, ...}）。
        失敗時は exit code 非0 + stderr にメッセージ。
"""

import argparse
import datetime
import json
import sys
from pathlib import Path


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def _now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _marker_path(cr_path: str, step: str) -> Path:
    return Path(cr_path) / f".phase-metrics-{step}.json"


def _metrics_path(cr_path: str) -> Path:
    return Path(cr_path) / "metrics.jsonl"


def cmd_phase_start(args) -> None:
    marker = _marker_path(args.cr_path, args.step)
    marker.write_text(
        json.dumps({"step": args.step, "started_at": _now_iso()}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "step": args.step}, ensure_ascii=False))


def cmd_record(args) -> None:
    entry = {"timestamp": _now_iso(), "step": args.step, "event": args.event}
    for key, val in (
        ("document_type", args.document_type),
        ("review_rounds", args.review_rounds),
        ("review_max_rounds", args.review_max_rounds),
        ("review_outcome", args.review_outcome),
        ("target", args.target),
        ("note", args.note),
    ):
        if val is not None:
            entry[key] = val

    if args.event == "phase_complete":
        marker = _marker_path(args.cr_path, args.step)
        if marker.exists():
            try:
                started = json.loads(marker.read_text(encoding="utf-8"))["started_at"]
                delta = datetime.datetime.now() - datetime.datetime.fromisoformat(started)
                entry["duration_ms"] = int(delta.total_seconds() * 1000)
            except (json.JSONDecodeError, KeyError, ValueError):
                pass  # マーカー破損時は duration_ms 省略のみで継続（テレメトリは工程本体を止めない）
            marker.unlink(missing_ok=True)

    path = _metrics_path(args.cr_path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, **entry}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_phase_start = sub.add_parser("phase-start")
    p_phase_start.add_argument("--cr-path", required=True)
    p_phase_start.add_argument("--step", required=True)
    p_phase_start.set_defaults(func=cmd_phase_start)

    p_record = sub.add_parser("record")
    p_record.add_argument("--cr-path", required=True)
    p_record.add_argument("--step", required=True)
    p_record.add_argument("--event", required=True, choices=["review_loop", "phase_complete"])
    p_record.add_argument("--document-type", default=None)
    p_record.add_argument("--review-rounds", type=int, default=None)
    p_record.add_argument("--review-max-rounds", type=int, default=None)
    p_record.add_argument(
        "--review-outcome", default=None,
        choices=["converged", "max_rounds_exhausted", "skipped"],
    )
    p_record.add_argument("--target", default=None)
    p_record.add_argument("--note", default=None)
    p_record.set_defaults(func=cmd_record)

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
