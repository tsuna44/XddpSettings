import argparse
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import xddp_vcs as mod  # noqa: E402

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "xddp_vcs.py"


def _git(repo: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def _init_repo(repo: Path, initial_branch: str = "main") -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "symbolic-ref", "HEAD", f"refs/heads/{initial_branch}")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    return repo


def _write(repo: Path, relpath: str, content: str = "x") -> None:
    p = repo / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _commit_all(repo: Path, message: str = "commit") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _ns(ignore_path=None) -> argparse.Namespace:
    return argparse.Namespace(ignore_path=ignore_path or [])


class RepoTestCaseBase(unittest.TestCase):
    """初期コミット1件を持つ標準リポジトリ（main ブランチ）を用意する共通 setUp。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        _init_repo(self.repo)
        _write(self.repo, "a.txt", "1")
        _commit_all(self.repo, "init")

    def tearDown(self):
        self.tmp.cleanup()


class GitBranchBasicTestCase(RepoTestCaseBase):
    def test_create_and_switch_basic(self):
        code = mod.git_branch(self.repo, "feature/x", "auto", _ns())
        self.assertEqual(code, 0)
        branch = _git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.assertEqual(branch, "feature/x")

    def test_idempotent_second_call_switches_to_existing(self):
        mod.git_branch(self.repo, "feature/x", "auto", _ns())
        code = mod.git_branch(self.repo, "feature/x", "auto", _ns())
        self.assertEqual(code, 0)
        branch = _git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.assertEqual(branch, "feature/x")

    def test_new_branch_branches_from_base_ref_not_current_head(self):
        # 別 CR の作業ブランチを模擬する: feature/CR-other に固有のコミットBを追加する
        _git(self.repo, "switch", "-c", "feature/CR-other")
        _write(self.repo, "b.txt", "2")
        _commit_all(self.repo, "commit B")
        commit_b = _git(self.repo, "rev-parse", "HEAD").stdout.strip()

        code = mod.git_branch(self.repo, "feature/CR-new", "auto", _ns())
        self.assertEqual(code, 0)

        result = _git(self.repo, "merge-base", "--is-ancestor", commit_b, "HEAD")
        self.assertNotEqual(result.returncode, 0, "新ブランチが別CRブランチのコミットを含んでいる")

    def test_switch_existing_branch_ignores_nonexistent_base_ref(self):
        mod.git_branch(self.repo, "feature/target", "auto", _ns())
        _git(self.repo, "switch", "main")
        code = mod.git_branch(self.repo, "feature/target", "nonexistent-ref", _ns())
        self.assertEqual(code, 0)
        branch = _git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.assertEqual(branch, "feature/target")

    def test_branch_create_when_same_name_tag_exists(self):
        _git(self.repo, "tag", "feature/tagged")
        code = mod.git_branch(self.repo, "feature/tagged", "auto", _ns())
        self.assertEqual(code, 0)
        detached_check = _git(self.repo, "symbolic-ref", "-q", "HEAD")
        self.assertEqual(detached_check.returncode, 0, "HEAD が detached になっている")
        # rev-parse --abbrev-ref・symbolic-ref --short はタグとの同名衝突時に "heads/" 接頭辞を
        # 付けて曖昧さを解消して表示するため、ブランチ名の直接取得には --show-current を使う。
        branch = _git(self.repo, "branch", "--show-current").stdout.strip()
        self.assertEqual(branch, "feature/tagged")


class DirtyGateTestCase(RepoTestCaseBase):
    def test_new_branch_blocked_when_dirty(self):
        _write(self.repo, "a.txt", "changed")
        code = mod.git_branch(self.repo, "feature/new", "auto", _ns())
        self.assertNotEqual(code, 0)
        result = _git(self.repo, "show-ref", "--verify", "--quiet", "refs/heads/feature/new")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.repo / "a.txt").read_text(), "changed")

    def test_existing_branch_switch_blocked_when_dirty_and_different_branch(self):
        mod.git_branch(self.repo, "feature/target", "auto", _ns())
        _git(self.repo, "switch", "main")
        _write(self.repo, "a.txt", "dirty-on-main")
        code = mod.git_branch(self.repo, "feature/target", "auto", _ns())
        self.assertNotEqual(code, 0)
        branch = _git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.assertEqual(branch, "main")
        self.assertEqual((self.repo / "a.txt").read_text(), "dirty-on-main")

    def test_existing_branch_switch_allowed_when_dirty_and_same_branch(self):
        mod.git_branch(self.repo, "feature/target", "auto", _ns())
        _write(self.repo, "a.txt", "dirty-on-target")
        code = mod.git_branch(self.repo, "feature/target", "auto", _ns())
        self.assertEqual(code, 0)
        branch = _git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.assertEqual(branch, "feature/target")


class IgnorePathTestCase(RepoTestCaseBase):
    def _make_dirty_xddp_dir(self):
        _write(self.repo, "xddp/note.md", "x")

    def _make_dirty_other_file(self):
        _write(self.repo, "src/a.py", "x")

    def test_new_branch_with_ignore_path_succeeds(self):
        self._make_dirty_xddp_dir()
        code = mod.git_branch(
            self.repo, "feature/x", "auto", _ns([str(self.repo / "xddp")])
        )
        self.assertEqual(code, 0)

    def test_new_branch_without_ignore_path_blocked(self):
        self._make_dirty_xddp_dir()
        code = mod.git_branch(self.repo, "feature/x", "auto", _ns())
        self.assertNotEqual(code, 0)

    def test_new_branch_with_ignore_path_still_blocked_by_other_dirty_file(self):
        self._make_dirty_xddp_dir()
        self._make_dirty_other_file()
        code = mod.git_branch(
            self.repo, "feature/x", "auto", _ns([str(self.repo / "xddp")])
        )
        self.assertNotEqual(code, 0)

    def test_existing_branch_switch_with_ignore_path_succeeds(self):
        mod.git_branch(self.repo, "feature/target", "auto", _ns())
        _git(self.repo, "switch", "main")
        self._make_dirty_xddp_dir()
        code = mod.git_branch(
            self.repo, "feature/target", "auto", _ns([str(self.repo / "xddp")])
        )
        self.assertEqual(code, 0)

    def test_existing_branch_switch_without_ignore_path_blocked(self):
        mod.git_branch(self.repo, "feature/target", "auto", _ns())
        _git(self.repo, "switch", "main")
        self._make_dirty_xddp_dir()
        code = mod.git_branch(self.repo, "feature/target", "auto", _ns())
        self.assertNotEqual(code, 0)

    def test_existing_branch_switch_ignore_path_still_blocked_by_other_dirty(self):
        mod.git_branch(self.repo, "feature/target", "auto", _ns())
        _git(self.repo, "switch", "main")
        self._make_dirty_xddp_dir()
        self._make_dirty_other_file()
        code = mod.git_branch(
            self.repo, "feature/target", "auto", _ns([str(self.repo / "xddp")])
        )
        self.assertNotEqual(code, 0)

    def test_resolve_ignore_pathspecs_outside_worktree_and_nonexistent(self):
        outside = self.repo.parent
        nonexistent = self.repo / "does-not-exist"
        result = mod.resolve_ignore_pathspecs(self.repo, [str(outside), str(nonexistent)])
        self.assertEqual(result, [])

    def test_resolve_ignore_pathspecs_inside_worktree(self):
        self._make_dirty_xddp_dir()
        result = mod.resolve_ignore_pathspecs(self.repo, [str(self.repo / "xddp")])
        self.assertEqual(result, [":(exclude)xddp"])


class ResolveBaseRefTestCase(unittest.TestCase):
    def test_origin_head_not_stripped(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _init_repo(Path(td), initial_branch="trunk")
            _write(repo, "a.txt", "1")
            _commit_all(repo, "init")
            sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
            _git(repo, "update-ref", "refs/remotes/origin/main", sha)
            _git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
            result = mod.resolve_base_ref(repo, "auto")
            self.assertEqual(result, "origin/main")

    def test_main_fallback_when_no_origin(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _init_repo(Path(td), initial_branch="main")
            _write(repo, "a.txt", "1")
            _commit_all(repo, "init")
            result = mod.resolve_base_ref(repo, "auto")
            self.assertEqual(result, "main")

    def test_master_fallback_when_no_main(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _init_repo(Path(td), initial_branch="master")
            _write(repo, "a.txt", "1")
            _commit_all(repo, "init")
            result = mod.resolve_base_ref(repo, "auto")
            self.assertEqual(result, "master")

    def test_head_fallback_with_warning_when_nothing_resolves(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _init_repo(Path(td), initial_branch="trunk")
            _write(repo, "a.txt", "1")
            _commit_all(repo, "init")
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                result = mod.resolve_base_ref(repo, "auto")
            self.assertEqual(result, "HEAD")
            self.assertIn("base ref を解決できない", buf.getvalue())

    def test_non_auto_value_passthrough(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _init_repo(Path(td))
            result = mod.resolve_base_ref(repo, "develop")
            self.assertEqual(result, "develop")


class ZeroCommitTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = _init_repo(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_branch_create_with_no_commits_succeeds(self):
        code = mod.git_branch(self.repo, "feature/CR-new", "auto", _ns())
        self.assertEqual(code, 0)
        branch = _git(self.repo, "symbolic-ref", "--short", "HEAD").stdout.strip()
        self.assertEqual(branch, "feature/CR-new")

    def test_branch_create_with_no_commits_does_not_call_resolve_base_ref(self):
        with mock.patch.object(
            mod, "resolve_base_ref", side_effect=AssertionError("must not be called")
        ) as spy:
            code = mod.git_branch(self.repo, "feature/CR-new", "auto", _ns())
        spy.assert_not_called()
        self.assertEqual(code, 0)

    def test_revert_with_no_commits_succeeds(self):
        code = mod.git_revert(self.repo, untracked=False)
        self.assertEqual(code, 0)

    def test_revert_with_no_commits_and_untracked_removes_files(self):
        _write(self.repo, "junk.txt", "x")
        code = mod.git_revert(self.repo, untracked=True)
        self.assertEqual(code, 0)
        self.assertFalse((self.repo / "junk.txt").exists())


class GitCommitTestCase(RepoTestCaseBase):
    def test_commit_prints_status_before_commit(self):
        _write(self.repo, "b.txt", "new")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = mod.git_commit(self.repo, "add b")
        self.assertEqual(code, 0)
        self.assertIn("b.txt", buf.getvalue())
        subject = _git(self.repo, "log", "-1", "--format=%s").stdout.strip()
        self.assertEqual(subject, "add b")

    def test_commit_message_with_quotes_and_backticks(self):
        _write(self.repo, "c.txt", "new")
        message = 'foo "bar" `baz`'
        code = mod.git_commit(self.repo, message)
        self.assertEqual(code, 0)
        subject = _git(self.repo, "log", "-1", "--format=%s").stdout.strip()
        self.assertEqual(subject, message)


class GitRevertTestCase(RepoTestCaseBase):
    def test_revert_resets_tracked_changes(self):
        _write(self.repo, "a.txt", "modified")
        code = mod.git_revert(self.repo, untracked=False)
        self.assertEqual(code, 0)
        self.assertEqual((self.repo / "a.txt").read_text(), "1")

    def test_revert_prints_untracked_list_before_clean(self):
        _write(self.repo, "junk.txt", "x")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = mod.git_revert(self.repo, untracked=True)
        self.assertEqual(code, 0)
        self.assertIn("junk.txt", buf.getvalue())
        self.assertFalse((self.repo / "junk.txt").exists())


class GitStatusTestCase(RepoTestCaseBase):
    def test_clean_and_dirty(self):
        self.assertEqual(mod.git_status(self.repo), "clean")
        _write(self.repo, "a.txt", "changed")
        self.assertEqual(mod.git_status(self.repo), "dirty")

    def test_status_returns_unknown_on_nonzero_exit(self):
        fake = subprocess.CompletedProcess(
            args=["git", "status", "--short"], returncode=128, stdout="", stderr="fatal"
        )
        with mock.patch.object(mod, "_run_git", return_value=fake):
            result = mod.git_status(self.repo)
        self.assertEqual(result, "unknown")


class GitBinaryMissingTestCase(unittest.TestCase):
    def test_branch_missing_git_binary(self):
        with mock.patch.object(mod, "_run_git", side_effect=FileNotFoundError()):
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                code = mod.git_branch(Path("/tmp"), "x", "auto", _ns())
        self.assertNotEqual(code, 0)
        self.assertIn("git コマンドが見つかりません", buf.getvalue())

    def test_commit_missing_git_binary(self):
        with mock.patch.object(mod, "_run_git", side_effect=FileNotFoundError()):
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                code = mod.git_commit(Path("/tmp"), "msg")
        self.assertNotEqual(code, 0)
        self.assertIn("git コマンドが見つかりません", buf.getvalue())

    def test_revert_missing_git_binary(self):
        with mock.patch.object(mod, "_run_git", side_effect=FileNotFoundError()):
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                code = mod.git_revert(Path("/tmp"), untracked=False)
        self.assertNotEqual(code, 0)
        self.assertIn("git コマンドが見つかりません", buf.getvalue())

    def test_status_missing_git_binary_returns_unknown(self):
        with mock.patch.object(mod, "_run_git", side_effect=FileNotFoundError()):
            result = mod.git_status(Path("/tmp"))
        self.assertEqual(result, "unknown")


class ResolveVcsTypeTestCase(unittest.TestCase):
    def test_auto_with_git_repo(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _init_repo(Path(td))
            args = argparse.Namespace(vcs_type="auto", repo=str(repo))
            self.assertEqual(mod.resolve_vcs_type(args), "git")

    def test_auto_without_git_repo_falls_back_to_none(self):
        with tempfile.TemporaryDirectory() as td:
            args = argparse.Namespace(vcs_type="auto", repo=td)
            self.assertEqual(mod.resolve_vcs_type(args), "none")

    def test_auto_with_svn_only_repo_falls_back_to_none(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / ".svn").mkdir()
            args = argparse.Namespace(vcs_type="auto", repo=td)
            self.assertEqual(mod.resolve_vcs_type(args), "none")

    def test_explicit_value_bypasses_detection(self):
        args = argparse.Namespace(vcs_type="git", repo="/does/not/exist")
        self.assertEqual(mod.resolve_vcs_type(args), "git")


class CliDispatchTestCase(unittest.TestCase):
    def test_cmd_detect_prints_vcs_type(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _init_repo(Path(td))
            parser = mod.build_parser()
            args = parser.parse_args(["detect", "--repo", str(repo), "--vcs-type", "auto"])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                args.func(args)
            self.assertEqual(buf.getvalue().strip(), "git")

    def test_vcs_type_svn_rejected_by_argparse(self):
        parser = mod.build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["detect", "--repo", ".", "--vcs-type", "svn"])

    def test_repo_required(self):
        parser = mod.build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["detect"])

    def test_base_ref_required_for_branch(self):
        parser = mod.build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["branch", "x", "--repo", "."])

    def test_branch_positional_required(self):
        parser = mod.build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["branch", "--repo", ".", "--base-ref", "auto"])

    def test_commit_positional_required(self):
        parser = mod.build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["commit", "--repo", "."])

    def test_none_vcs_type_branch_commit_revert_are_noop_success(self):
        parser = mod.build_parser()
        cases = [
            ["branch", "x", "--repo", "/does/not/exist", "--vcs-type", "none", "--base-ref", "auto"],
            ["commit", "msg", "--repo", "/does/not/exist", "--vcs-type", "none"],
            ["revert", "--repo", "/does/not/exist", "--vcs-type", "none"],
        ]
        for argv in cases:
            args = parser.parse_args(argv)
            with self.assertRaises(SystemExit) as cm:
                args.func(args)
            self.assertEqual(cm.exception.code, 0, msg=f"failed for {argv}")

    def test_none_vcs_type_status_prints_clean(self):
        parser = mod.build_parser()
        args = parser.parse_args(["status", "--repo", "/does/not/exist", "--vcs-type", "none"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            args.func(args)
        self.assertEqual(buf.getvalue().strip(), "clean")

    def test_help_does_not_error(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        for sub in ["detect", "branch", "commit", "revert", "status"]:
            proc = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), sub, "--help"], capture_output=True, text=True
            )
            self.assertEqual(proc.returncode, 0, msg=f"{sub} --help failed: {proc.stderr}")
            self.assertIn("--repo", proc.stdout)


if __name__ == "__main__":
    unittest.main()
