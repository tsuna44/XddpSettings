"""
xddp_verify_tools.py — lint/build/typecheck 実ツール実行・結果レポート生成

工程7（`xddp.07.code` Step B）・工程8（`xddp.08.verify` Step A）・工程10b
（`xddp.10.test-run` b-1 実装バグ再検証）の3箇所から共通手続き `xddp.common/SKILL.md`
「## Run Verification Tools」経由で呼ばれる決定的処理スクリプト。`--lint`/`--build`/`--typecheck`
のうち指定されたコマンドだけを REPO を cwd として実行し、終了コードで PASS/FAIL を機械的に判定する
（LLM の報告文に依存しない。設計根拠は docs/adr/ADR-0015-verify-real-tool-execution.md 参照）。

Usage:
  python3 xddp_verify_tools.py run --repo-path REPO --output OUTPUT.md
      [--lint CMD] [--build CMD] [--typecheck CMD]
      [--timeout-sec N] [--max-output-lines N]

Behavior:
  - `--timeout-sec N` は指定された各コマンド（lint/build/typecheck）それぞれに個別に適用される
    タイムアウトであり、3コマンド合計の共有バジェットではない。3コマンドをすべて指定した場合、
    最悪ケースでは合計で最大 3×N 秒までブロックしうる。
  - 指定されなかった種別は結果表で「➖ 未設定」として記録する（実行しない）。
  - 各コマンドの exit code・stdout+stderr（末尾 max_output_lines 行に切り詰め、切り詰めた場合は
    その旨を明記）を OUTPUT.md に Markdown テーブル＋fenced code block で書き出す。
  - タイムアウト時は「⏱️ タイムアウト（{timeout_sec}秒）」として FAIL 扱いにする。

既知の制限:
  - プロセスグループでの強制終了（`os.killpg` + `SIGKILL`）は POSIX 前提。`start_new_session=True`
    は Windows では効果がなく、Windows では `proc.kill()` のみのベストエフォート終了になる
    （孫プロセスが残留しうる）。
  - `proc.communicate(timeout=timeout_sec)` は子プロセスの stdout+stderr 全量を先にメモリへ
    読み込んでから `--max-output-lines` で末尾に切り詰める。極端に冗長な出力を吐くコマンドに対しては
    キャプチャ自体の上限がなくメモリ消費が増大しうる（ストリーミング処理は本スクリプトのスコープ外）。

Exit code:
  0 = 実行された全コマンドが exit 0（何も指定されなかった場合も 0）。OUTPUT.md 書き出し済み。
  1 = 実行されたいずれかのコマンドが非0終了（タイムアウト含む）。OUTPUT.md 書き出し済み。
  2 = 使用法エラー（argparse 既定）、または本体で捕捉した想定外の例外。OUTPUT.md の存在は保証されない。
"""

import argparse
import os
import signal
import subprocess
import sys
import traceback
from pathlib import Path

IS_POSIX = os.name == "posix"

STATUS_LABELS = {
    "not_configured": "➖ 未設定",
    "pass": "✅ PASS",
    "fail": "❌ FAIL",
}


def _timeout_label(timeout_sec: int) -> str:
    return f"⏱️ タイムアウト（{timeout_sec}秒）"


def _truncate(output: str, max_lines: int) -> tuple:
    lines = output.splitlines()
    if len(lines) <= max_lines:
        return output, False
    return "\n".join(lines[-max_lines:]), True


def run_command(name: str, cmd: str, repo_path: Path, timeout_sec: int) -> dict:
    """1つのコマンドを repo_path を cwd として実行し、結果を dict で返す。

    ハングした子プロセスが孫プロセスをさらに fork するケースでも確実に終了させるため、
    新規プロセスグループで起動し（POSIX）、タイムアウト時はプロセスグループ全体を SIGKILL する。
    """
    proc = subprocess.Popen(
        cmd,
        shell=True,
        cwd=str(repo_path),
        start_new_session=IS_POSIX,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        output, _ = proc.communicate(timeout=timeout_sec)
        exit_code = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        if IS_POSIX:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
        output, _ = proc.communicate()
        exit_code = None
        timed_out = True

    if timed_out:
        status = "timeout"
    elif exit_code == 0:
        status = "pass"
    else:
        status = "fail"

    return {
        "name": name,
        "cmd": cmd,
        "status": status,
        "exit_code": exit_code,
        "output": output or "",
    }


def _status_label(result: dict, timeout_sec: int) -> str:
    if result["status"] == "timeout":
        return _timeout_label(timeout_sec)
    return STATUS_LABELS[result["status"]]


def build_report(repo_path: Path, results: list, timeout_sec: int, max_output_lines: int) -> str:
    lines = ["# 実ツール実行結果", "", f"- repo: `{repo_path}`", f"- timeout_sec: {timeout_sec}", ""]
    lines.append("| ツール | コマンド | 結果 | exit code |")
    lines.append("|---|---|---|---|")
    for r in results:
        cmd_display = r["cmd"] if r["cmd"] else "-"
        exit_display = r["exit_code"] if r["exit_code"] is not None else "-"
        lines.append(f"| {r['name']} | `{cmd_display}` | {_status_label(r, timeout_sec)} | {exit_display} |")
    lines.append("")

    for r in results:
        if r["status"] == "not_configured":
            continue
        lines.append(f"## {r['name']}")
        lines.append("")
        lines.append("```")
        lines.append(f"$ {r['cmd']}")
        truncated_output, was_truncated = _truncate(r["output"], max_output_lines)
        if was_truncated:
            lines.append(f"...（末尾 {max_output_lines} 行のみ表示。それ以前の出力は切り詰め済み）")
        if truncated_output:
            lines.append(truncated_output)
        lines.append("```")
        lines.append("")

    return "\n".join(lines) + "\n"


def cmd_run(args) -> None:
    repo_path = Path(args.repo_path)
    output_path = Path(args.output)

    specs = [("lint", args.lint), ("build", args.build), ("typecheck", args.typecheck)]
    results = []
    for name, cmd in specs:
        if not cmd:
            results.append({"name": name, "cmd": None, "status": "not_configured", "exit_code": None, "output": ""})
        else:
            results.append(run_command(name, cmd, repo_path, args.timeout_sec))

    report = build_report(repo_path, results, args.timeout_sec, args.max_output_lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    any_fail = any(r["status"] in ("fail", "timeout") for r in results)
    sys.exit(1 if any_fail else 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run")
    p_run.add_argument("--repo-path", required=True)
    p_run.add_argument("--output", required=True)
    p_run.add_argument("--lint", default=None)
    p_run.add_argument("--build", default=None)
    p_run.add_argument("--typecheck", default=None)
    p_run.add_argument("--timeout-sec", type=int, default=600)
    p_run.add_argument("--max-output-lines", type=int, default=200)
    p_run.set_defaults(func=cmd_run)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 — CLI境界: 想定外の例外は exit code 2 に統合する
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
