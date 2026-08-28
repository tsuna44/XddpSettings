"""
xddp_vcs.py — VCS（バージョン管理システム）抽象層 CLI

XDDP 工程7（コーディング）・工程8（静的検証）・工程10（テスト実行）・xddp.close（クローズ）から
呼び出される、ブランチ作成/切替・コミット・巻き戻し・状態確認の決定的処理スクリプト。
VCS 種別ごとの実処理は種別プレフィックス付きの関数群（`git_*`）に分離し、CLI のサブコマンド
処理（`cmd_*`）は `resolve_vcs_type()` が解決した種別文字列を見て対応する関数へ委譲するだけの
薄いディスパッチ層とする。将来 SVN 等の VCS を追加する場合は、新規関数群1組の追加と
`resolve_vcs_type()`／各 `cmd_*` への1 case 追加、および `--vcs-type` の `choices` への追加のみで
対応でき、CLI ディスパッチ層・呼び出し元 SKILL.md の変更は不要（本プランでは Git/None のみ実装）。

設計判断の詳細は docs/adr/ADR-0011-vcs-abstraction.md を参照。

Usage:
  python3 xddp_vcs.py detect --repo REPO [--vcs-type {auto,git,none}]
  python3 xddp_vcs.py branch BRANCH --repo REPO [--vcs-type {auto,git,none}]
      --base-ref BASE_REF [--ignore-path PATH ...]
  python3 xddp_vcs.py commit MESSAGE --repo REPO [--vcs-type {auto,git,none}]
  python3 xddp_vcs.py revert --repo REPO [--vcs-type {auto,git,none}] [--untracked]
  python3 xddp_vcs.py status --repo REPO [--vcs-type {auto,git,none}]

Output:
  detect: VCS 種別文字列（`git`/`none`）を stdout に出力。
  status: `clean`/`dirty`/`unknown` のいずれかを stdout に出力。
  branch/commit/revert: 実行内容（監査ログ）を stdout に出力し、exit code で成否を返す
  （0=成功、非0=失敗。標準出力に JSON は出力しない——他の決定的処理スクリプトと異なり、
  呼び出し元 SKILL.md は exit code のみを見て分岐するため）。
"""

import argparse
import subprocess
import sys
from pathlib import Path

GIT_NOT_FOUND_MESSAGE = "git コマンドが見つかりません"


def _run_git(args: list, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# git 種別
# ---------------------------------------------------------------------------

def git_detect(repo: Path) -> bool:
    """{repo}/.git の存在確認。"""
    return (repo / ".git").exists()


def resolve_ignore_pathspecs(repo: Path, ignore_paths: list) -> list:
    """`--ignore-path` に渡された各パスのうち、`repo` のワークツリー内にあるものだけを
    リポジトリ相対パスへ正規化し、dirty 判定用の除外パススペック
    （`':(exclude){rel}'` 形式）のリストとして返す。ワークツリー外のパス・存在しない
    パスは黙って除外する。
    """
    pathspecs: list = []
    try:
        repo_resolved = repo.resolve()
    except OSError:
        return pathspecs
    for raw in ignore_paths:
        try:
            resolved = Path(raw).resolve()
        except OSError:
            continue
        if not resolved.exists():
            continue
        try:
            rel = resolved.relative_to(repo_resolved)
        except ValueError:
            continue
        pathspecs.append(f":(exclude){rel.as_posix()}")
    return pathspecs


def _is_dirty(repo: Path, ignore_pathspecs: list) -> bool:
    result = _run_git(["status", "--porcelain", "--", ".", *ignore_pathspecs], repo)
    return bool(result.stdout.strip())


def resolve_base_ref(repo: Path, base_ref: str) -> str:
    """`--base-ref` の値が `auto` の場合のみ実行時に具体的な ref 名へ解決する（`auto` 以外は
    そのまま返す）。解決順序: origin/HEAD → main → master → 現在の HEAD（警告付き）。
    """
    if base_ref != "auto":
        return base_ref

    result = _run_git(["symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD"], repo)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    result = _run_git(["rev-parse", "--verify", "-q", "main"], repo)
    if result.returncode == 0:
        return "main"

    result = _run_git(["rev-parse", "--verify", "-q", "master"], repo)
    if result.returncode == 0:
        return "master"

    print("⚠️ base ref を解決できないため現在の HEAD を起点にします", file=sys.stderr)
    return "HEAD"


def git_branch(repo: Path, branch_name: str, base_ref: str, args: argparse.Namespace) -> int:
    """ブランチ作成/切替。新規作成時、コミットが1件以上存在する場合は解決済みの起点 ref
    （`resolve_base_ref()`）から分岐する。コミット0件（unborn HEAD）の場合は起点解決自体を
    行わず、開始点なしでブランチを作成する。新規作成時・別ブランチからの切替時はいずれも、
    作業ツリーが dirty な場合はブランチ作成/切替を行わず非ゼロの exit code を返す。既に対象
    ブランチ上にいる場合の切替（真の冪等ケース）は dirty 状態によらず成功する。
    """
    try:
        ignore_pathspecs = resolve_ignore_pathspecs(repo, getattr(args, "ignore_path", None) or [])

        has_commit = _run_git(["rev-parse", "--verify", "-q", "HEAD"], repo).returncode == 0
        exists = _run_git(
            ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"], repo
        ).returncode == 0

        if not exists:
            if _is_dirty(repo, ignore_pathspecs):
                print(
                    "作業ツリーに未コミットの変更が残っているため新規ブランチを作成できません。"
                    "先にコミットするか `git stash` 等で退避してください"
                    "（XDDP 成果物ディレクトリ配下は判定対象から除外済みです）。",
                    file=sys.stderr,
                )
                return 1
            if has_commit:
                resolved_base_ref = resolve_base_ref(repo, base_ref)
                create_args = ["switch", "-c", branch_name, resolved_base_ref]
                fallback_args = ["checkout", "-b", branch_name, resolved_base_ref]
            else:
                create_args = ["switch", "-c", branch_name]
                fallback_args = ["checkout", "-b", branch_name]
            result = _run_git(create_args, repo)
            if result.returncode != 0:
                result = _run_git(fallback_args, repo)
            if result.returncode != 0:
                print(result.stderr, file=sys.stderr)
                return 1
            return 0

        # `rev-parse --abbrev-ref` はタグと同名のブランチが存在する場合に "heads/{branch}" を
        # 返して曖昧さを解消するため使わない（`show-current` は常にブランチ名のみを返す）。
        current = _run_git(["branch", "--show-current"], repo)
        current_branch = current.stdout.strip() if current.returncode == 0 else None
        if current_branch != branch_name:
            if _is_dirty(repo, ignore_pathspecs):
                print(
                    "作業ツリーに未コミットの変更が残っているため、別ブランチからの切替を"
                    "中止しました。先にコミットするか `git stash` 等で退避してください。",
                    file=sys.stderr,
                )
                return 1
        result = _run_git(["switch", branch_name], repo)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return 1
        return 0
    except FileNotFoundError:
        print(GIT_NOT_FOUND_MESSAGE, file=sys.stderr)
        return 1


def git_commit(repo: Path, message: str) -> int:
    try:
        status = _run_git(["status", "--short"], repo)
        print(status.stdout, end="")
        add = _run_git(["add", "-A"], repo)
        if add.returncode != 0:
            print(add.stderr, file=sys.stderr)
            return 1
        commit = _run_git(["commit", "-m", message], repo)
        if commit.returncode != 0:
            print(commit.stderr, file=sys.stderr)
            return 1
        return 0
    except FileNotFoundError:
        print(GIT_NOT_FOUND_MESSAGE, file=sys.stderr)
        return 1


def git_revert(repo: Path, untracked: bool) -> int:
    try:
        has_commit = _run_git(["rev-parse", "--verify", "-q", "HEAD"], repo).returncode == 0
        if has_commit:
            reset = _run_git(["reset", "--hard", "HEAD"], repo)
            if reset.returncode != 0:
                print(reset.stderr, file=sys.stderr)
                return 1
        if untracked:
            dry_run = _run_git(["clean", "-fdn"], repo)
            print(dry_run.stdout, end="")
            clean = _run_git(["clean", "-fd"], repo)
            if clean.returncode != 0:
                print(clean.stderr, file=sys.stderr)
                return 1
        return 0
    except FileNotFoundError:
        print(GIT_NOT_FOUND_MESSAGE, file=sys.stderr)
        return 1


def git_status(repo: Path) -> str:
    """'clean' / 'dirty' / 'unknown' のいずれかを返す。"""
    try:
        result = _run_git(["status", "--short"], repo)
    except FileNotFoundError:
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    return "dirty" if result.stdout.strip() else "clean"


# ---------------------------------------------------------------------------
# ディスパッチ
# ---------------------------------------------------------------------------

def resolve_vcs_type(args: argparse.Namespace) -> str:
    """--vcs-type の値から実際に使う VCS 種別文字列（'git'/'none'）を決定する。"""
    if args.vcs_type != "auto":
        return args.vcs_type
    return "git" if git_detect(Path(args.repo)) else "none"


def cmd_detect(args: argparse.Namespace) -> None:
    print(resolve_vcs_type(args))


def cmd_branch(args: argparse.Namespace) -> None:
    vcs_type = resolve_vcs_type(args)
    if vcs_type == "git":
        code = git_branch(Path(args.repo), args.branch, args.base_ref, args)
    else:
        code = 0
    sys.exit(code)


def cmd_commit(args: argparse.Namespace) -> None:
    vcs_type = resolve_vcs_type(args)
    if vcs_type == "git":
        code = git_commit(Path(args.repo), args.message)
    else:
        code = 0
    sys.exit(code)


def cmd_revert(args: argparse.Namespace) -> None:
    vcs_type = resolve_vcs_type(args)
    if vcs_type == "git":
        code = git_revert(Path(args.repo), args.untracked)
    else:
        code = 0
    sys.exit(code)


def cmd_status(args: argparse.Namespace) -> None:
    vcs_type = resolve_vcs_type(args)
    status = git_status(Path(args.repo)) if vcs_type == "git" else "clean"
    print(status)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", required=True)
    common.add_argument("--vcs-type", choices=["auto", "git", "none"], default="auto")

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_detect = sub.add_parser("detect", parents=[common])
    p_detect.set_defaults(func=cmd_detect)

    p_branch = sub.add_parser("branch", parents=[common])
    p_branch.add_argument("branch")
    p_branch.add_argument("--base-ref", required=True)
    p_branch.add_argument("--ignore-path", action="append", default=[])
    p_branch.set_defaults(func=cmd_branch)

    p_commit = sub.add_parser("commit", parents=[common])
    p_commit.add_argument("message")
    p_commit.set_defaults(func=cmd_commit)

    p_revert = sub.add_parser("revert", parents=[common])
    p_revert.add_argument("--untracked", action="store_true")
    p_revert.set_defaults(func=cmd_revert)

    p_status = sub.add_parser("status", parents=[common])
    p_status.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — CLI境界でのエラーはstderrへ集約する
        print(f"予期しないエラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
