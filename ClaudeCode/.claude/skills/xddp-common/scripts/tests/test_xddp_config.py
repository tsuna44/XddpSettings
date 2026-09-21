import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import xddp_config as mod  # noqa: E402

MINIMAL_CONFIG = """# XDDP プロジェクト設定

```
XDDP_DIR: xddp
```

```
REPOS:
  repo-a: ../repo-a
  repo-b: ../repo-b
```
"""

FULL_CONFIG = """# XDDP プロジェクト設定

```
XDDP_DIR: my-xddp
DOCS_DIR: my-docs
```

```
DEVELOPMENT_MODE: new
CR_PROFILE: quick
```

```
REPOS:
  repo-a: ../repo-a
```

```
SPECOUT_EXCLUDE_PATTERNS: tests/,vendor/
SPECOUT_INCLUDE_EXTENSIONS: .py
SPECOUT_MAX_WAVE_DEPTH: 5
```

```
SPECOUT_BACKEND: rg
SPECOUT_BACKEND.repo-a: ctags
```

```
VERIFY_LINT_COMMAND: ruff check .
VERIFY_LINT_COMMAND.repo-a: golangci-lint run
VERIFY_TOOL_TIMEOUT_SEC: 120
```

```
VCS_TYPE: bogus
VCS_AUTO_BRANCH: false
```

```
TEST_FRAMEWORK_REPOS:
  repo-a: pytest
```

```
# 1エントリの例（コメントのため無視される）:
# REPOS:
#   my-app: ../my-app
# SPECOUT_MAX_AFFECTED_FILES: 999
```
"""


class ParseRawTestCase(unittest.TestCase):
    def test_parses_simple_and_nested_keys(self):
        raw = mod.parse_raw(MINIMAL_CONFIG)
        self.assertEqual(raw["XDDP_DIR"], "xddp")
        self.assertEqual(raw["REPOS"], {"repo-a": "../repo-a", "repo-b": "../repo-b"})

    def test_ignores_commented_lines(self):
        raw = mod.parse_raw(FULL_CONFIG)
        self.assertNotIn("SPECOUT_MAX_AFFECTED_FILES", raw)
        # コメント化された REPOS: ブロックが実値を上書きしていないこと
        self.assertEqual(raw["REPOS"], {"repo-a": "../repo-a"})

    def test_parses_dot_suffix_override_keys(self):
        raw = mod.parse_raw(FULL_CONFIG)
        self.assertEqual(raw["SPECOUT_BACKEND.repo-a"], "ctags")
        self.assertEqual(raw["VERIFY_LINT_COMMAND.repo-a"], "golangci-lint run")


class BuildBundleTestCase(unittest.TestCase):
    def test_defaults_when_config_minimal(self):
        raw = mod.parse_raw(MINIMAL_CONFIG)
        bundle, warnings = mod.build_bundle(raw, Path("/ws"))
        self.assertEqual(bundle["XDDP_DIR"], "xddp")
        self.assertEqual(bundle["DOCS_DIR"], "baseline_docs")
        self.assertEqual(bundle["DEVELOPMENT_MODE"], "change")
        self.assertEqual(bundle["CR_PROFILE"], "full")
        self.assertEqual(bundle["MIN_COVERAGE"], 80)
        self.assertEqual(bundle["VCS_TYPE"], "auto")
        self.assertEqual(bundle["VCS_AUTO_BRANCH"], True)
        self.assertEqual(bundle["REPOS_KEYS"], ["repo-a", "repo-b"])
        self.assertTrue(bundle["IS_MULTI"])
        self.assertEqual(bundle["DOCS"], str(Path("/ws") / "baseline_docs"))
        self.assertEqual(warnings, [])

    def test_alias_output_names(self):
        raw = mod.parse_raw(FULL_CONFIG)
        bundle, _ = mod.build_bundle(raw, Path("/ws"))
        self.assertEqual(bundle["EXCLUDE_PATTERNS"], "tests/,vendor/")
        self.assertEqual(bundle["INCLUDE_EXTENSIONS"], ".py")
        self.assertEqual(bundle["MAX_WAVE_DEPTH"], 5)
        self.assertNotIn("SPECOUT_EXCLUDE_PATTERNS", bundle)
        self.assertNotIn("SPECOUT_INCLUDE_EXTENSIONS", bundle)
        self.assertNotIn("SPECOUT_MAX_WAVE_DEPTH", bundle)

    def test_repo_override_dicts(self):
        raw = mod.parse_raw(FULL_CONFIG)
        bundle, _ = mod.build_bundle(raw, Path("/ws"))
        self.assertEqual(bundle["SPECOUT_BACKEND"], "rg")
        self.assertEqual(bundle["SPECOUT_BACKEND_OVERRIDES"], {"repo-a": "ctags"})
        self.assertEqual(bundle["VERIFY_LINT_COMMAND_OVERRIDES"], {"repo-a": "golangci-lint run"})
        self.assertEqual(bundle["VERIFY_BUILD_COMMAND_OVERRIDES"], {})
        self.assertEqual(bundle["VERIFY_TOOL_TIMEOUT_SEC"], 120)

    def test_invalid_vcs_type_falls_back_to_none_with_warning(self):
        raw = mod.parse_raw(FULL_CONFIG)
        bundle, warnings = mod.build_bundle(raw, Path("/ws"))
        self.assertEqual(bundle["VCS_TYPE"], "none")
        self.assertTrue(any("VCS_TYPE" in w for w in warnings))

    def test_bool_key_false(self):
        raw = mod.parse_raw(FULL_CONFIG)
        bundle, _ = mod.build_bundle(raw, Path("/ws"))
        self.assertEqual(bundle["VCS_AUTO_BRANCH"], False)

    def test_test_framework_repos_dict(self):
        raw = mod.parse_raw(FULL_CONFIG)
        bundle, _ = mod.build_bundle(raw, Path("/ws"))
        self.assertEqual(bundle["TEST_FRAMEWORK_REPOS"], {"repo-a": "pytest"})

    def test_invalid_int_falls_back_to_default_with_warning(self):
        raw = {"MIN_COVERAGE": "not-a-number"}
        bundle, warnings = mod.build_bundle(raw, Path("/ws"))
        self.assertEqual(bundle["MIN_COVERAGE"], 80)
        self.assertTrue(any("MIN_COVERAGE" in w for w in warnings))


class CliTestCase(unittest.TestCase):
    def test_load_exit_3_when_config_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            parser = mod.build_parser()
            args = parser.parse_args(["load", "--start-dir", tmp])
            with self.assertRaises(SystemExit) as cm:
                args.func(args)
            self.assertEqual(cm.exception.code, 3)

    def test_load_finds_config_upward_and_prints_json(self):
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "xddp.config.md").write_text(MINIMAL_CONFIG, encoding="utf-8")
            sub = root / "repo-a" / "src"
            sub.mkdir(parents=True)
            parser = mod.build_parser()
            args = parser.parse_args(["load", "--start-dir", str(sub)])
            buf = io.StringIO()
            with redirect_stdout(buf):
                args.func(args)
            bundle = json.loads(buf.getvalue())
            self.assertEqual(bundle["WORKSPACE_ROOT"], str(root.resolve()))
            self.assertEqual(bundle["REPOS_KEYS"], ["repo-a", "repo-b"])

    def test_list_keys_does_not_require_config_file(self):
        import io
        from contextlib import redirect_stdout

        parser = mod.build_parser()
        args = parser.parse_args(["load", "--list-keys"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            args.func(args)
        keys = json.loads(buf.getvalue())
        self.assertTrue(any(k["key"] == "XDDP_DIR" for k in keys))


if __name__ == "__main__":
    unittest.main()
