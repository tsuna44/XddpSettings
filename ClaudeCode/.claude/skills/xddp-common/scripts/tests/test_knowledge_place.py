import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import docs_layout as layout  # noqa: E402
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
        for t in ("localhost:8080/api", "git@github.com:org/repo", "sys/types.h", "nodir/x.c",
                  str(self.repo / "nodir" / "x.c")):
            with self.subTest(t=t):
                self.assertEqual(self.status(t), "not-found")

    def test_absolute_outside_workspace_is_outside_repo(self):
        # R4: ワークスペースの外の絶対パス。リポジトリのルートからの意味でも所在ディレクトリが無ければ outside-repo
        for t in ("/usr/include/stdio.h", "/dev/ttyS0", "/tmp", "/nodir/x.c"):
            with self.subTest(t=t):
                self.assertEqual(self.status(t), "outside-repo")
        self.assertEqual(self.module("/src/db.c"), "src")

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
        # R1: 制約の置き場所にしない予約名と同じ名前のディレクトリは、読まれる fallback に置く
        r = self.place(["_flows/z.c"])
        self.assertEqual(r["module"], "_general")
        self.assertTrue(r["reserved_collision"])
        self.assertEqual(self.place(["_flows/z.c"], fallback="src")["module"], "src")

    def test_general_named_directory_stays(self):
        _mk(self.repo / "_general" / "g.c")
        r = self.place(["_general/g.c"])
        self.assertEqual(r["module"], "_general")
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


SKILLS = Path(__file__).resolve().parents[3]
BOUNDARY = SKILLS / "xddp-rules" / "code-knowledge-boundary.md"


def _entry(eid, targets, title, section="constraint", key=None, **kw):
    fields = {"constraint": {"content": f"{title} の内容", "workaround": "回避"},
              "assumption": {"premise": f"{title} の前提", "reason": "理由"},
              "performance": {"observation": f"{title} の観察", "implication": "示唆"}}[section]
    e = {"id": eid, "targets": targets, "section": section, "title": title, "fields": fields,
         "source": "CR-1 / SPO §5.6"}
    if key is not None:
        e["key"] = key
    e.update(kw)
    return e


class _UpsertBase(_Base):
    def setUp(self):
        super().setUp()
        self.docs = self.ws / "baseline_docs"
        self.know = self.docs / "repo-a" / "knowledge" / "code-knowledge"

    def run_upsert(self, data, *extra, stdin_text=None):
        argv = ["upsert", "--docs", str(self.docs), "--repo", "repo-a", "--repo-root", "repo-a",
                "--workspace-root", str(self.ws), *extra]
        text = stdin_text if stdin_text is not None else json.dumps(data, ensure_ascii=False)
        out, err = io.StringIO(), io.StringIO()
        old = sys.stdin
        sys.stdin = io.StringIO(text)
        try:
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    code = kp.main(argv)
                except SystemExit as e:
                    code = e.code
        finally:
            sys.stdin = old
        return code, (json.loads(out.getvalue()) if code == 0 else None), err.getvalue()

    def ok(self, data, *extra):
        code, out, err = self.run_upsert(data, *extra)
        self.assertEqual(code, 0, err)
        return out

    def read(self, rel):
        return (self.know / rel).read_text(encoding="utf-8")

    def snapshot(self):
        return {p: p.read_text(encoding="utf-8") for p in self.know.rglob("*") if p.is_file()} \
            if self.know.is_dir() else {}


class TestUpsert(_UpsertBase):
    def test_items_in_one_run_are_separate_entries(self):
        # A1-1 の再現の逆: 同じ置き場所・同じ出典の項目が互いに置き換わらない
        out = self.ok([_entry("a", ["src/a.c"], "一つ目", key="SPO-5.6:1"),
                       _entry("b", ["src/db.c"], "二つ目", key="SPO-5.6:2")], "--batch-cr", "CR-1")
        self.assertEqual([(e["file"], e["ck"], e["action"]) for e in out["entries"]],
                         [("src/constraints.md", "CK-001", "added"), ("src/constraints.md", "CK-002", "added")])
        text = self.read("src/constraints.md")
        self.assertIn("### [CK-001] 一つ目\n<!-- key: cr:CR-1:SPO-5.6:1 -->\n**対象:** src/a.c", text)
        self.assertIn("### [CK-002] 二つ目", text)
        self.assertTrue(text.startswith("# src 制約・注意事項\n"))
        self.assertIn("> 更新ルール:", text)
        self.assertNotIn("{タイトル}", text)

    def test_same_key_replaces_and_keeps_ck(self):
        self.ok([_entry("a", ["src/a.c"], "一つ目", key="k1"), _entry("b", ["src/a.c"], "二つ目", key="k2")],
                "--batch-cr", "CR-1")
        out = self.ok([_entry("b", ["src/a.c"], "二つ目・改", key="k2")], "--batch-cr", "CR-1")
        self.assertEqual((out["entries"][0]["ck"], out["entries"][0]["action"]), ("CK-002", "replaced"))
        text = self.read("src/constraints.md")
        self.assertIn("### [CK-002] 二つ目・改", text)
        self.assertNotIn("### [CK-002] 二つ目\n", text)
        self.assertEqual([n["key"] for n in out["not_written"]], ["cr:CR-1:k1"])

    def test_moved_to_other_file(self):
        self.ok([_entry("a", ["src/a.c"], "一つ目", key="k1")], "--batch-cr", "CR-1")
        self.ok([_entry("x", ["lib/net/n.c"], "別", key="k9")], "--batch-cr", "CR-2")
        out = self.ok([_entry("a", ["lib/net/n.c"], "一つ目", key="k1")], "--batch-cr", "CR-1")
        e = out["entries"][0]
        self.assertEqual((e["file"], e["ck"], e["action"]), ("lib/net/constraints.md", "CK-002", "moved"))
        self.assertEqual(e["moved_from"], {"file": "src/constraints.md", "ck": "CK-001"})
        self.assertNotIn("一つ目", self.read("src/constraints.md"))
        self.assertTrue((self.know / "src" / "constraints.md").is_file())
        self.assertEqual(out["emptied"], ["src/constraints.md"])

    def test_section_change_moves_within_file(self):
        self.ok([_entry("a", ["src/a.c"], "項目", key="2.6:1")], "--batch-cr", "CR-1")
        out = self.ok([_entry("a", ["src/a.c"], "項目", section="assumption", key="2.6:1")], "--batch-cr", "CR-1")
        e = out["entries"][0]
        self.assertEqual((e["ck"], e["action"]), ("CK-001", "moved"))
        text = self.read("src/constraints.md")
        self.assertLess(text.index("## 仕様上の暗黙の前提"), text.index("### [CK-001] 項目"))
        self.assertEqual(text.count("[CK-001]"), 1)

    def test_batch_reports_not_written_and_never_deletes(self):
        self.ok([_entry(str(i), ["src/a.c"], f"項目{i}", key=f"SPO-5.6:{i}") for i in (1, 2, 3)],
                "--batch-cr", "CR-1")
        self.ok([_entry("o", ["src/a.c"], "他の CR", key="SPO-5.6:1")], "--batch-cr", "CR-2")
        self.ok([_entry("m", ["src/a.c"], "手での登録")])
        # 途中の1件を除くと、番号がずれて最後の鍵のエントリが not_written に入る
        out = self.ok([_entry("1", ["src/a.c"], "項目1", key="SPO-5.6:1"),
                       _entry("3", ["src/a.c"], "項目3", key="SPO-5.6:2")], "--batch-cr", "CR-1")
        self.assertEqual([n["key"] for n in out["not_written"]], ["cr:CR-1:SPO-5.6:3"])
        text = self.read("src/constraints.md")
        for title in ("項目3", "他の CR", "手での登録"):
            self.assertIn(title, text)
        empty = self.ok([], "--batch-cr", "CR-1")
        self.assertEqual(sorted(n["key"] for n in empty["not_written"]),
                         ["cr:CR-1:SPO-5.6:1", "cr:CR-1:SPO-5.6:2", "cr:CR-1:SPO-5.6:3"])

    def test_keyless_entries_are_untouched(self):
        _mk(self.know / "src" / "constraints.md",
            "# src 制約・注意事項\n\n## 既知の制約・落とし穴\n\n### [CK-001] 人が書いた\n"
            "**対象:** src/a.c\n**内容:** 手で書いた\n\n```sh\n## コメント\n### [CK-009] フェンスの中\n```\n\n"
            "### メモ（人の見出し）\n自由な文章\n")
        out = self.ok([_entry("a", ["src/a.c"], "新規", key="k1")], "--batch-cr", "CR-1")
        self.assertEqual(out["entries"][0]["ck"], "CK-002")
        self.assertEqual(out["not_written"], [])
        text = self.read("src/constraints.md")
        for s_ in ("### [CK-001] 人が書いた", "## コメント\n### [CK-009] フェンスの中", "### メモ（人の見出し）\n自由な文章"):
            self.assertIn(s_, text)

    def test_namespaces_do_not_mix(self):
        self.ok([_entry("m", ["src/a.c"], "手での登録")])
        self.ok([_entry("s", ["src/a.c"], "survey", key="2.6:1")], "--batch-survey", "xddp/survey/S.md")
        for cr in ("manual", "survey", "SURVEY"):
            with self.subTest(cr=cr):
                self.assertEqual(self.ok([], "--batch-cr", cr)["not_written"], [])

    def test_batch_survey_prefix_is_normalized(self):
        (self.ws / "xddp" / "survey").mkdir(parents=True)
        self.ok([_entry("s", ["src/a.c"], "項目", key="2.6:1")], "--batch-survey", "xddp/survey/S.md")
        for path in ("./xddp/survey/S.md", str(self.ws / "xddp" / "survey" / "S.md")):
            with self.subTest(path=path):
                out = self.ok([_entry("s", ["src/a.c"], "項目", key="2.6:1")], "--batch-survey", path)
                self.assertEqual(out["entries"][0]["action"], "replaced")
        self.assertIn("<!-- key: survey:xddp/survey/S.md:2.6:1 -->", self.read("src/constraints.md"))
        code, _, _ = self.run_upsert([], "--batch-survey", "/elsewhere/S.md")
        self.assertEqual(code, 2)

    def test_ll_sections_are_separate(self):
        out = self.ok([_entry("c", ["src/a.c"], "LL", key="LL-CR-1-01:constraint"),
                       _entry("p", ["src/a.c"], "LL", section="assumption", key="LL-CR-1-01:assumption")],
                      "--batch-cr", "CR-1")
        self.assertEqual([e["ck"] for e in out["entries"]], ["CK-001", "CK-002"])

    def test_subjects_are_shown_but_do_not_place(self):
        out = self.ok([_entry("m", [], "対象だけ", subjects=["parse_header(), lib/net/n.c"])])
        self.assertEqual(out["entries"][0]["module"], "_general")
        self.assertIn("**対象:** parse_header(), lib/net/n.c", self.read("_general/constraints.md"))
        out = self.ok([_entry("m", ["src/a.c"], "両方", subjects=["lib/net/n.c"])])
        self.assertEqual(out["entries"][0]["module"], "src")
        self.ok([_entry("e", [], "空")])
        self.assertIn("### [CK-002] 空\n<!-- key: manual:_general/constraints.md:CK-002 -->\n**対象:** —",
                      self.read("_general/constraints.md"))

    def test_replace(self):
        _mk(self.know / "src" / "constraints.md",
            "# src 制約・注意事項\n\n## 既知の制約・落とし穴\n\n### [CK-001] 人が書いた\n**内容:** 古い\n")
        out = self.ok([_entry("m", ["src/a.c"], "書き直し", replace="CK-001")])
        self.assertEqual((out["entries"][0]["ck"], out["entries"][0]["action"]), ("CK-001", "replaced"))
        text = self.read("src/constraints.md")
        self.assertIn("### [CK-001] 書き直し\n<!-- key: manual:src/constraints.md:CK-001 -->", text)
        self.assertNotIn("古い", text)
        code, _, _ = self.run_upsert([_entry("m", ["src/a.c"], "無い番号", replace="CK-007")])
        self.assertEqual(code, 2)

    def test_dry_run(self):
        self.ok([_entry("a", ["src/a.c"], "一つ目")])
        before = self.snapshot()
        out = self.ok([_entry("b", ["src/a.c"], "二つ目"), _entry("c", ["lib/net/n.c"], "三つ目")], "--dry-run")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(out["existing"]["src/constraints.md"],
                         [{"ck": "CK-001", "title": "一つ目", "key": "manual:src/constraints.md:CK-001"}])
        self.assertEqual(out["existing"]["lib/net/constraints.md"], [])
        self.assertEqual([e["action"] for e in out["entries"]], ["added", "added"])

    def test_empty_fields_and_crlf(self):
        e = _entry("a", ["src/a.c"], "本文")
        e["fields"] = {"content": "一行目\r\n\t字下げ\n```sh\n## シェルのコメント\n```", "workaround": ""}
        self.ok([e])
        text = self.read("src/constraints.md")
        self.assertIn("**内容:** 一行目\n\t字下げ\n```sh\n## シェルのコメント\n```", text)
        self.assertIn("**回避策:** —", text)
        self.assertNotIn("\r", text)

    def test_errors_change_nothing(self):
        self.ok([_entry("a", ["src/a.c"], "一つ目")])
        before = self.snapshot()
        bad_cases = {
            "replace の番号が無い": ([_entry("1", ["src/a.c"], "x"), _entry("2", ["src/a.c"], "y", replace="CK-9")], ()),
            "本文の見出しの行": ([_entry("1", ["src/a.c"], "x"),
                          dict(_entry("2", ["src/a.c"], "y"), fields={"content": "## 見出し", "workaround": ""})], ()),
            "鍵の行": ([dict(_entry("1", ["src/a.c"], "y"), fields={"content": "<!-- key: x -->", "workaround": ""})], ()),
            "鍵の重なり": ([_entry("1", ["src/a.c"], "x", key="k"), _entry("2", ["src/a.c"], "y", key="k")],
                       ("--batch-cr", "CR-1")),
            "replace の重なり": ([_entry("1", ["src/a.c"], "x", replace="CK-001"),
                             _entry("2", ["src/a.c"], "y", replace="CK-001")], ()),
            "batch で key が無い": ([_entry("1", ["src/a.c"], "x")], ("--batch-cr", "CR-1")),
            "batch でない key": ([_entry("1", ["src/a.c"], "x", key="k")], ()),
            "batch と replace": ([_entry("1", ["src/a.c"], "x", key="k", replace="CK-001")], ("--batch-cr", "CR-1")),
            "batch の同時指定": ([], ("--batch-cr", "CR-1", "--batch-survey", "xddp/S.md")),
            "fields のキーの欠け": ([dict(_entry("1", ["src/a.c"], "x"), fields={"content": "c"})], ()),
            "節に無いキー": ([dict(_entry("1", ["src/a.c"], "x"), fields={"content": "c", "workaround": "",
                                                                    "premise": "p"})], ()),
            "section の誤り": ([dict(_entry("1", ["src/a.c"], "x"), section="other")], ()),
            "targets の制御文字": ([_entry("1", ["src\network\x0cfoo.c"], "x")], ()),
            "subjects の制御文字": ([_entry("1", [], "x", subjects=["a\nb"])], ()),
            "本文の制御文字": ([dict(_entry("1", ["src/a.c"], "x"), fields={"content": "a\x0cb", "workaround": ""})], ()),
        }
        for fb in ("../x", "/abs", "_structures", "src/../x", "C:/x", "a\\b", "."):
            bad_cases[f"fallback {fb}"] = ([_entry("1", [], "x", fallback=fb)], ())
        for name, (data, extra) in bad_cases.items():
            with self.subTest(name=name):
                code, _, err = self.run_upsert(data, *extra)
                self.assertEqual(code, 2, err)
                self.assertEqual(self.snapshot(), before)
        code, _, err = self.run_upsert([_entry("1", ["src\nfoo.c"], "x")])
        self.assertIn("\\\\", err)

    def test_repo_cross_and_missing_repo_root(self):
        code, _, _ = self.run_upsert([], "--repo-root", "repo-a")
        argv = ["upsert", "--docs", str(self.docs), "--repo", "cross", "--repo-root", "repo-a",
                "--workspace-root", str(self.ws)]
        with redirect_stderr(io.StringIO()):
            sys.stdin, old = io.StringIO("[]"), sys.stdin
            try:
                self.assertEqual(kp.main(argv), 2)
            finally:
                sys.stdin = old
        argv[argv.index("cross")] = "repo-a"
        argv[argv.index("--repo-root") + 1] = "nope"
        with redirect_stderr(io.StringIO()):
            sys.stdin, old = io.StringIO("[]"), sys.stdin
            try:
                self.assertEqual(kp.main(argv), 1)
            finally:
                sys.stdin = old

    def test_reserved_collision_is_written_where_it_is_read(self):
        out = self.ok([_entry("a", ["_flows/z.c"], "衝突")])
        self.assertEqual(out["entries"][0]["module"], "_general")
        self.assertTrue(out["entries"][0]["reserved_collision"])
        self.assertIn("_general", kp.list_places(self.know))
        self.assertIn("_general", kp.applicable_places("_flows/z.c"))


class TestWriterReaderContract(_UpsertBase):
    """書く側（upsert）→ 読む側（list_places・applicable_places・テンプレート・宛先ルーティング表）。"""

    def test_written_places_are_listed_and_applicable(self):
        out = self.ok([_entry("a", ["src/auth/login/a.c"], "深い"), _entry("b", ["./main.c"], "直下"),
                       _entry("c", ["parse()"], "パスなし")])
        places = kp.list_places(self.know)
        for e, f in zip(out["entries"], ("src/auth/login/a.c", "main.c", None)):
            with self.subTest(module=e["module"]):
                self.assertIn(e["module"], places)
                if f:
                    self.assertIn(e["module"], kp.applicable_places(f))

    def test_entry_format_matches_template(self):
        tmpl = kp.parse_constraints(kp.TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual([s_.name for s_ in tmpl.sections], [v[0] for v in kp.SECTIONS.values()])
        for name, (heading, cols) in kp.SECTIONS.items():
            with self.subTest(section=name):
                sec = next(s_ for s_ in tmpl.sections if s_.name == heading)
                sample = next(b for b in sec.blocks if b.kind == "entry")
                labels = [re.match(r"^\*\*(.+?):\*\*", ln).group(1) for ln in sample.lines
                          if re.match(r"^\*\*(.+?):\*\*", ln)]
                self.assertEqual(labels, [kp.TARGET_LABEL] + [c[1] for c in cols] + [kp.SOURCE_LABEL])
                self.assertTrue(kp.KEY_LINE_RE.match(sample.lines[1]))
                rendered = kp._render(1, dict(_entry("x", ["src/a.c"], "t", section=name), subjects=[]), "k")
                self.assertTrue(kp.ENTRY_HEADING_RE.match(rendered[0]))
                self.assertEqual([re.match(r"^\*\*(.+?):\*\*", ln).group(1) for ln in rendered[2:-1]], labels)
        self.assertIn("> 更新ルール:", "\n".join(tmpl.preamble))

    def test_routing_table_paths(self):
        text = BOUNDARY.read_text(encoding="utf-8")
        table = text.split("## 宛先ルーティング表", 1)[1].split("\n## ", 1)[0]
        rows = [ln for ln in table.splitlines() if ln.startswith("| ") and "`{KNOW}" in ln]
        self.assertGreaterEqual(len(rows), 6)
        for row in rows:
            cells = [c.strip() for c in row.strip("|").split("|")]
            with self.subTest(kind=cells[0]):
                for path in re.findall(r"`(\{X?KNOW\}/[^`]+)`", cells[3]):
                    parts = path.split("/")
                    self.assertNotIn("...", path)
                    if parts[1] == "{MODULE}":
                        self.assertEqual(parts[2:], [layout.CONSTRAINTS_FILE])
                    else:
                        self.assertIn(parts[1], layout.SHARED_KNOWLEDGE_DIRS)
                        self.assertEqual(len(parts), 3, path)
                for tpl in re.findall(r"`([\w-]+/templates/[^`]+\.md)`", cells[4]):
                    self.assertTrue((SKILLS / tpl).is_file(), tpl)


if __name__ == "__main__":
    unittest.main()
