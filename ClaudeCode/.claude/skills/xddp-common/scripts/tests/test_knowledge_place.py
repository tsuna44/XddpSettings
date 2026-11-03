import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import knowledge_place as kp  # noqa: E402


def _mk(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class _Base(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp()).resolve()
        self.repo = self.ws / "repo-a"
        for f in ("src/auth/login/a.c", "src/main/java/com/example/auth/X.java",
                  "Drivers/uart/uart.c", "lib/net/n.c", "main.c", "src/db.c", "src/a.c",
                  "src/old/keep.c", "src/a/x.c", "src/b/y.c", "_flows/z.c"):
            _mk(self.repo / f)
        _mk(self.ws / "repo-a-sdk" / "x.c")
        _mk(self.ws / "repo-b" / "src" / "a.c")

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def place(self, targets, repo_root="repo-a", fallback=None):
        entry = {"id": "k1", "targets": targets}
        if fallback:
            entry["fallback"] = fallback
        return kp.place_entries([entry], repo_root, str(self.ws))[0]

    def module(self, *targets, **kw):
        return self.place(list(targets), **kw)["module"]

    def status(self, target, **kw):
        return self.place([target], **kw)["targets"][0]["status"]


class TestPlaceExamples(_Base):
    """プランの例の表（3.0.1）。"""

    def test_file_places_are_containing_directory(self):
        self.assertEqual(self.module("src/auth/login/a.c"), "src/auth/login")
        self.assertEqual(self.module("src/main/java/com/example/auth/X.java"),
                         "src/main/java/com/example/auth")
        self.assertEqual(self.module("Drivers/uart/uart.c"), "Drivers/uart")
        self.assertEqual(self.module("src/a.c"), "src")

    def test_directory(self):
        self.assertEqual(self.module("lib/net/"), "lib/net")
        self.assertEqual(self.module("lib/net"), "lib/net")

    def test_dot_slash_root_file(self):
        self.assertEqual(self.module("./main.c"), "_root")

    def test_no_path_goes_to_fallback(self):
        for t in ("main.c:45", "parse_header()", "config.timeout", "com.example.Foo", "os.path.join"):
            with self.subTest(t=t):
                r = self.place([t])
                self.assertEqual(r["targets"][0]["status"], "no-path")
                self.assertEqual(r["module"], "_general")
        self.assertEqual(self.module("parse_header()", fallback="src-auth"), "src-auth")

    def test_line_and_anchor_and_backslash(self):
        self.assertEqual(self.module("src\\db.c:45"), "src")
        self.assertEqual(self.module("`src/a.c#L10`"), "src")
        r = self.place(["src/db.c:45"])["targets"][0]
        self.assertEqual((r["status"], r["rel"], r["place"]), ("placed", "src/db.c", "src"))

    def test_root_relative_slash(self):
        self.assertEqual(self.module("/src/db.c"), "src")

    def test_absolute_under_repo_with_various_repo_roots(self):
        abs_t = str(self.repo / "src" / "a.c")
        for rr in ("../repo-a", "./repo-a", "repo-a", "repo-a/", str(self.repo), str(self.repo) + "/"):
            with self.subTest(repo_root=rr):
                if rr.startswith("../"):
                    # `../repo-a` はワークスペースの下のディレクトリから見た書き方。ワークスペースを1段下げる
                    r = kp.place_entries([{"id": "k", "targets": [abs_t]}], rr,
                                         str(self.ws / "sub"))[0]
                else:
                    r = self.place([abs_t], repo_root=rr)
                self.assertEqual(r["module"], "src")

    def test_workspace_relative(self):
        self.assertEqual(self.module("repo-a/src/a.c"), "src")

    def test_outside_repo(self):
        self.assertEqual(self.status("../repo-b/src/a.c"), "outside-repo")
        self.assertEqual(self.status(str(self.ws / "repo-a-sdk" / "x.c")), "outside-repo")

    def test_url(self):
        self.assertEqual(self.status("http://host/api"), "url")
        self.assertEqual(self.status("file:///x"), "url")

    def test_not_found(self):
        for t in ("localhost:8080/api", "git@github.com:org/repo", "sys/types.h", "/dev/ttyS0", "/tmp"):
            with self.subTest(t=t):
                self.assertEqual(self.status(t), "not-found")

    def test_deleted_file(self):
        self.assertEqual(self.module("src/old/x.c"), "src/old")
        self.assertEqual(self.status("src/gone/x.c"), "not-found")

    def test_multiple_targets(self):
        self.assertEqual(self.module("src/a/x.c", "src/b/y.c"), "src")
        self.assertEqual(self.module("src/a/x.c", "./main.c"), "_general")
        self.assertEqual(self.module("./main.c", "./main.c"), "_root")
        self.assertEqual(self.module("Drivers/uart/uart.c", "lib/net/n.c"), "_general")
        self.assertEqual(self.module("src/auth/login/a.c", "parse()"), "src/auth/login")

    def test_directory_boundary(self):
        # repo-a-sdk は repo-a の下ではない（前方一致はディレクトリ境界で判定）
        self.assertEqual(self.status(str(self.ws / "repo-a-sdk" / "x.c")), "outside-repo")
        self.assertEqual(self.module("src/auth/login/a.c", "src/au/x.c"), "src/auth/login")

    def test_repo_root_itself(self):
        self.assertEqual(self.module("./"), "_root")


class TestReservedCollision(_Base):
    def test_reserved_first_component(self):
        r = self.place(["_flows/z.c"])
        self.assertEqual(r["module"], "_flows")
        self.assertTrue(r["reserved_collision"])

    def test_sentinels_are_not_collisions(self):
        self.assertFalse(self.place(["parse()"])["reserved_collision"])
        self.assertFalse(self.place(["./main.c"])["reserved_collision"])
        self.assertFalse(self.place(["src/a.c"])["reserved_collision"])


class TestDrivePaths(unittest.TestCase):
    """ドライブ付きのパス（OS によらず文字列として扱う。実体の確認は差し替える）。"""

    def setUp(self):
        self.dirs = {"c:/ws", "c:/ws/repo-a", "c:/ws/repo-a/src", "c:/other"}
        self.files = {"c:/ws/repo-a/src/a.c", "c:/other/a.c"}

    def _isdir(self, p):
        return p in self.dirs

    def _exists(self, p):
        return p in self.dirs or p in self.files

    def _place(self, target, repo_root="C:\\ws\\repo-a"):
        return kp.place_entries([{"id": "k", "targets": [target]}], repo_root, "C:\\ws",
                                isdir=self._isdir, exists=self._exists)[0]

    def test_drive_absolute_with_line(self):
        self.assertEqual(self._place("C:\\ws\\repo-a\\src\\a.c:45")["module"], "src")
        self.assertEqual(self._place("c:/WS/repo-a/src/a.c")["targets"][0]["status"], "outside-repo")

    def test_drive_case_insensitive(self):
        self.assertEqual(self._place("c:\\ws\\repo-a\\src\\a.c", repo_root="C:/ws/repo-a")["module"], "src")

    def test_drive_outside(self):
        self.assertEqual(self._place("C:\\other\\a.c")["targets"][0]["status"], "outside-repo")

    def test_drive_relative_repo_root(self):
        self.assertEqual(self._place("src/a.c", repo_root="repo-a")["module"], "src")


class TestCli(_Base):
    def _run(self, argv, stdin=None):
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        if stdin is not None:
            sys.stdin = io.StringIO(stdin)
        try:
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    code = kp.main(argv)
                except SystemExit as e:
                    code = e.code
        finally:
            sys.stdin = old_stdin
        return code, out.getvalue(), err.getvalue()

    def test_input_file(self):
        inp = self.ws / "in.json"
        inp.write_text(json.dumps([{"id": "a", "targets": ["src/a.c"]}]), encoding="utf-8")
        code, out, _ = self._run(["place", "--repo-root", "repo-a", "--workspace-root", str(self.ws),
                                  "--input", str(inp)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)[0]["module"], "src")

    def test_stdin(self):
        code, out, _ = self._run(["place", "--repo-root", str(self.repo), "--workspace-root", str(self.ws)],
                                 stdin=json.dumps([{"id": "a", "targets": ["`$x` 'q'", "./main.c"]}]))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)[0]["module"], "_root")

    def test_missing_repo_root_exit_1(self):
        code, _, err = self._run(["place", "--repo-root", "nope", "--workspace-root", str(self.ws)],
                                 stdin="[]")
        self.assertEqual(code, 1)
        self.assertIn("--repo-root", err)

    def test_bad_json_exit_2(self):
        for bad in ("{", "{}", '[{"id": 1, "targets": []}]', '[{"id": "a", "targets": "x"}]',
                    '[{"id": "a", "targets": [], "fallback": ""}]'):
            with self.subTest(bad=bad):
                code, _, _ = self._run(["place", "--repo-root", "repo-a", "--workspace-root", str(self.ws)],
                                       stdin=bad)
                self.assertEqual(code, 2)

    def test_bad_args_exit_2(self):
        code, _, _ = self._run(["place", "--repo-root", "repo-a"])
        self.assertEqual(code, 2)


class TestReadSide(unittest.TestCase):
    def setUp(self):
        self.know = Path(tempfile.mkdtemp())
        for rel in ("src/auth/login", "src", "_general", "_root", "_flows/x", "_structures",
                    "_constants", "_cochange/src", "lib/_flows"):
            _mk(self.know / rel / "constraints.md")
        _mk(self.know / "constraints.md")
        _mk(self.know / "docs" / "other.md")

    def tearDown(self):
        shutil.rmtree(self.know, ignore_errors=True)

    def test_list_places(self):
        self.assertEqual(kp.list_places(self.know),
                         ["_general", "_root", "lib/_flows", "src", "src/auth/login"])

    def test_list_places_missing_dir(self):
        self.assertEqual(kp.list_places(self.know / "none"), [])

    def test_applicable_places(self):
        self.assertEqual(kp.applicable_places("src/auth/login/a.c"),
                         ["_general", "src/auth/login", "src/auth", "src"])
        self.assertEqual(kp.applicable_places("main.c"), ["_general", "_root"])
        self.assertEqual(kp.applicable_places("./main.c"), ["_general", "_root"])
        self.assertNotIn("src/au", kp.applicable_places("src/auth/a.c"))


if __name__ == "__main__":
    unittest.main()
