#!/usr/bin/env python3
"""run_all.py — XDDP 開発時テストハーネスの集約ランナー（`make test` の実体）

L1〜L3（0トークン層）を単一エントリポイントから一括実行する。**LLM は起動しない。**

1. unit: `ClaudeCode/.claude/skills/**/scripts/tests/` と `tools/harness/tests/` の
   全 unittest を実行する（各スクリプト同梱テスト＋ハーネス自身のテスト）。
   各テストは兄弟スクリプトを `sys.path` 注入で bare import するため、テストディレクトリ
   ごとに独立サブプロセスで discover し、モジュール名衝突を避ける。
2. lint: `refcheck.py`（検査A/B/C/D）を実行する。

いずれかのステップが失敗すれば exit code 非0。

出力契約:
  --only {unit,lint} : 片方のみ実行（省略時は unit→lint 両方）。
  --json             : {"ok": bool, "unit": {...}, "lint": {...}} を stdout。

参照: plans/PLAN-20260725-p2-test-harness.md Section 3.3
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import refcheck


def find_test_dirs(repo_root: Path) -> list[Path]:
    dirs: list[Path] = []
    skills = repo_root / "ClaudeCode/.claude/skills"
    if skills.exists():
        dirs.extend(sorted(p for p in skills.rglob("scripts/tests") if p.is_dir()))
    harness_tests = repo_root / "tools/harness/tests"
    if harness_tests.is_dir():
        dirs.append(harness_tests)
    return dirs


def run_unit(repo_root: Path) -> dict:
    test_dirs = find_test_dirs(repo_root)
    results = []
    ok = True
    for d in test_dirs:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover",
             "-s", str(d), "-p", "test_*.py", "-t", str(d)],
            capture_output=True, text=True,
        )
        passed = proc.returncode == 0
        ok = ok and passed
        # unittest はサマリを stderr に出す
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        summary = tail[-1] if tail else ""
        results.append({
            "dir": str(d.relative_to(repo_root)),
            "ok": passed,
            "summary": summary,
            "output": proc.stderr if not passed else "",
        })
    return {"ok": ok, "suites": results}


def run_lint(repo_root: Path) -> dict:
    violations = refcheck.run(repo_root)
    counts = refcheck.summarize(violations)
    return {
        "ok": counts["errors"] == 0,
        "counts": counts,
        "violations": violations,
    }


def _print_unit(unit: dict):
    print("=== unit (unittest) ===")
    for s in unit["suites"]:
        mark = "✅" if s["ok"] else "❌"
        print(f"{mark} {s['dir']}  {s['summary']}")
        if not s["ok"] and s["output"]:
            print(s["output"])
    print()


def _print_lint(lint: dict):
    print("=== lint (refcheck) ===")
    for v in lint["violations"]:
        mark = "❌" if v["severity"] == "error" else "⚠️"
        loc = f"{v['file']}:{v['line']}" if v["line"] else v["file"]
        print(f"{mark} [{v['check']}] {loc}  {v['message']}")
    c = lint["counts"]
    print(f"refcheck: errors={c['errors']} warnings={c['warnings']}")
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="XDDP 開発時テストハーネス（make test）")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--only", choices=["unit", "lint"], default=None,
                        help="片方のみ実行（既定: 両方）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo_root = (args.root.resolve() if args.root
                 else refcheck._find_repo_root(Path(__file__).parent))

    result: dict = {"ok": True}
    if args.only in (None, "unit"):
        result["unit"] = run_unit(repo_root)
        result["ok"] = result["ok"] and result["unit"]["ok"]
    if args.only in (None, "lint"):
        result["lint"] = run_lint(repo_root)
        result["ok"] = result["ok"] and result["lint"]["ok"]

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if "unit" in result:
            _print_unit(result["unit"])
        if "lint" in result:
            _print_lint(result["lint"])
        print("run_all:", "OK ✅" if result["ok"] else "NG ❌")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
