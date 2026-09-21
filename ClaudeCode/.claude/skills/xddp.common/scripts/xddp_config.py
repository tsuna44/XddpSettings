"""
xddp_config.py — xddp.config.md パース CLI

`xddp.config.md`（フェンス付きコードブロック内の `KEY: value` 行・ネストしたマッピング・
`KEY.{repo}: value` 形式のリポジトリ別上書き）を解析し、CR に依存しない標準設定バンドルを
JSON で出力する。`## Load Config` の Process を機械化したもの。標準ライブラリのみに依存する。

Usage:
  python3 xddp_config.py load --format json --start-dir .
  python3 xddp_config.py load --list-keys

Output: 成功時は stdout に設定バンドル JSON。不正値の警告は stderr（1行1件）。
        失敗時は exit code 非0 + stderr にメッセージ。

終了コード: 0=成功 / 1=実行時エラー / 2=使用法エラー（argparse既定）/ 3=xddp.config.md 未検出。
"""

import argparse
import json
import re
import sys
from pathlib import Path

CONFIG_FILENAME = "xddp.config.md"

TOP_HEADER_RE = re.compile(r"^([A-Z][A-Z0-9_]*):\s*$")
# キー本体は大文字英数字・アンダースコアのみだが、`.{repo}` サフィックス（repo名は
# 実フォルダ名そのもの＝小文字・ハイフンを含みうる）を許容する。
TOP_KV_RE = re.compile(r"^([A-Z][A-Z0-9_]*(?:\.[A-Za-z0-9_-]+)?):\s*(.*)$")
SUB_KV_RE = re.compile(r"^\s+([^\s:][^:]*):\s*(.*)$")

SIMPLE_DEFAULTS = {
    "XDDP_DIR": "xddp",
    "DOCS_DIR": "baseline_docs",
    "DEVELOPMENT_MODE": "change",
    "CR_PROFILE": "full",
    "MIN_COVERAGE": 80,
    "TEST_COVERAGE_TARGET": "C1",
    "SPECOUT_EXCLUDE_PATTERNS": (
        "tests/,test/,__tests__/,spec/,specs/,__mocks__/,fixtures/,vendor/,node_modules/"
    ),
    "SPECOUT_INCLUDE_EXTENSIONS": "",
    "SPECOUT_MAX_WAVE_DEPTH": 10,
    "SPECOUT_MAX_AFFECTED_FILES": 20,
    "SPECOUT_MAX_FILES_PER_MODULE": 10,
    "SPECOUT_DIAGRAM_LEVEL": "standard",
    "SPECOUT_SEQUENCE_LEVELS": "module, class",
    "SPECOUT_BACKEND": "auto",
    "SPECOUT_CLASSIFY_CHUNK_SIZE": 40,
    "SPECOUT_CLASSIFY_PARALLEL": 4,
    "SPECOUT_HIT_FILTER": "conservative",
    "DESIGN_MAX_SP_PER_FILE": 10,
    "DESIGN_MAX_SYMBOLS_PER_FILE": 30,
    "TEST_FRAMEWORK": "auto",
    "MD2EXCEL_PYTHON_BIN": "",
    "VCS_TYPE": "auto",
    "VCS_BRANCH_PREFIX": "feature/",
    "VCS_AUTO_BRANCH": True,
    "VCS_COMMIT_ON_STEP": "7,10",
    "VCS_BASE_BRANCH": "auto",
    "VERIFY_LINT_COMMAND": "",
    "VERIFY_BUILD_COMMAND": "",
    "VERIFY_TYPECHECK_COMMAND": "",
    "VERIFY_TOOL_TIMEOUT_SEC": 600,
}

# `xddp.04.specout/SKILL.md` 本文が既に使用している短縮エイリアス名（`## Load Config` の
# 既存出力と一致させるため、パース元のキー名とは別名で出力する）
ALIASES = {
    "SPECOUT_EXCLUDE_PATTERNS": "EXCLUDE_PATTERNS",
    "SPECOUT_INCLUDE_EXTENSIONS": "INCLUDE_EXTENSIONS",
    "SPECOUT_MAX_WAVE_DEPTH": "MAX_WAVE_DEPTH",
}

INT_KEYS = {
    "MIN_COVERAGE", "SPECOUT_MAX_WAVE_DEPTH", "SPECOUT_MAX_AFFECTED_FILES",
    "SPECOUT_MAX_FILES_PER_MODULE", "SPECOUT_CLASSIFY_CHUNK_SIZE", "SPECOUT_CLASSIFY_PARALLEL",
    "DESIGN_MAX_SP_PER_FILE", "DESIGN_MAX_SYMBOLS_PER_FILE", "VERIFY_TOOL_TIMEOUT_SEC",
}
BOOL_KEYS = {"VCS_AUTO_BRANCH"}
VALID_VCS_TYPES = ("auto", "git", "none")

# リポジトリ単位上書き（`{KEY}.{repo}: value`）を持つキー
OVERRIDE_BASES = (
    "SPECOUT_BACKEND", "VERIFY_LINT_COMMAND", "VERIFY_BUILD_COMMAND", "VERIFY_TYPECHECK_COMMAND",
)

KEY_DOCS = [
    {"key": "WORKSPACE_ROOT", "default": "(computed)", "consumer": "xddp.config.md のあるディレクトリ。全スキル"},
    {"key": "XDDP_DIR", "default": "xddp", "consumer": "CR Resolution・全スキル"},
    {"key": "DOCS_DIR", "default": "baseline_docs", "consumer": "xddp.close・xddp.11.specs 等"},
    {"key": "DOCS", "default": "(computed = WORKSPACE_ROOT/DOCS_DIR)", "consumer": "同上"},
    {"key": "REPOS_MAP", "default": "{}", "consumer": "全スキル（マルチリポジトリ解決）"},
    {"key": "REPOS_KEYS", "default": "[]", "consumer": "同上"},
    {"key": "IS_MULTI", "default": "(computed = len(REPOS_KEYS) >= 2)", "consumer": "cross/ 成果物生成判定"},
    {"key": "DEVELOPMENT_MODE", "default": "change", "consumer": "xddp.04.specout（new でスキップ）"},
    {"key": "CR_PROFILE", "default": "full", "consumer": "xddp.set-profile。CR単位上書きは CR Resolution Step 1.X が別途解決"},
    {"key": "MIN_COVERAGE", "default": "80", "consumer": "xddp.10.test-run"},
    {"key": "TEST_COVERAGE_TARGET", "default": "C1", "consumer": "xddp.09.test"},
    {"key": "EXCLUDE_PATTERNS", "default": "tests/,test/,...", "consumer": "xddp.04.specout Discovery BFS"},
    {"key": "INCLUDE_EXTENSIONS", "default": "(空)", "consumer": "xddp.04.specout Discovery BFS"},
    {"key": "MAX_WAVE_DEPTH", "default": "10", "consumer": "xddp.04.specout Discovery BFS"},
    {"key": "SPECOUT_MAX_AFFECTED_FILES", "default": "20", "consumer": "xddp.04.specout（CR分割警告）"},
    {"key": "SPECOUT_MAX_FILES_PER_MODULE", "default": "10", "consumer": "xddp.04.specout（モジュールファイル分割）"},
    {"key": "SPECOUT_DIAGRAM_LEVEL", "default": "standard", "consumer": "xddp.04.specout / xddp.11.specs"},
    {"key": "SPECOUT_SEQUENCE_LEVELS", "default": "module, class", "consumer": "xddp.04.specout"},
    {"key": "SPECOUT_BACKEND", "default": "auto", "consumer": "xddp.04.specout discovery-setup"},
    {"key": "SPECOUT_BACKEND_OVERRIDES", "default": "{}", "consumer": "同上（repo単位上書き）"},
    {"key": "SPECOUT_CLASSIFY_CHUNK_SIZE", "default": "40", "consumer": "xddp.04.specout 波ループ"},
    {"key": "SPECOUT_CLASSIFY_PARALLEL", "default": "4", "consumer": "xddp.04.specout 波ループ"},
    {"key": "SPECOUT_HIT_FILTER", "default": "conservative", "consumer": "xddp.04.specout Discovery BFS"},
    {"key": "DESIGN_MAX_SP_PER_FILE", "default": "10", "consumer": "xddp.06.design（CHDバッチ分割）"},
    {"key": "DESIGN_MAX_SYMBOLS_PER_FILE", "default": "30", "consumer": "xddp.06.design（人レビュー警告）"},
    {"key": "TEST_FRAMEWORK", "default": "auto", "consumer": "xddp.09.test"},
    {"key": "TEST_FRAMEWORK_REPOS", "default": "{}", "consumer": "xddp.09.test（repo単位上書き）"},
    {"key": "MD2EXCEL_PYTHON_BIN", "default": "(空)", "consumer": "xddp.md2excel / xddp.excel2md / Regenerate CRS Excel"},
    {"key": "VCS_TYPE", "default": "auto", "consumer": "xddp.07.code/08.verify/10.test-run/close の VCS 操作"},
    {"key": "VCS_BRANCH_PREFIX", "default": "feature/", "consumer": "同上"},
    {"key": "VCS_AUTO_BRANCH", "default": "true", "consumer": "同上"},
    {"key": "VCS_COMMIT_ON_STEP", "default": "7,10", "consumer": "同上"},
    {"key": "VCS_BASE_BRANCH", "default": "auto", "consumer": "同上"},
    {"key": "VERIFY_LINT_COMMAND", "default": "(空)", "consumer": "Run Verification Tools（工程8）"},
    {"key": "VERIFY_LINT_COMMAND_OVERRIDES", "default": "{}", "consumer": "同上（repo単位上書き）"},
    {"key": "VERIFY_BUILD_COMMAND", "default": "(空)", "consumer": "同上"},
    {"key": "VERIFY_BUILD_COMMAND_OVERRIDES", "default": "{}", "consumer": "同上（repo単位上書き）"},
    {"key": "VERIFY_TYPECHECK_COMMAND", "default": "(空)", "consumer": "同上"},
    {"key": "VERIFY_TYPECHECK_COMMAND_OVERRIDES", "default": "{}", "consumer": "同上（repo単位上書き）"},
    {"key": "VERIFY_TOOL_TIMEOUT_SEC", "default": "600", "consumer": "同上（コマンド毎の個別タイムアウト）"},
]


def _err(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def find_config(start_dir: Path) -> Path | None:
    cur = start_dir.resolve()
    for cand in [cur, *cur.parents]:
        candidate = cand / CONFIG_FILENAME
        if candidate.exists():
            return candidate
    return None


def parse_raw(text: str) -> dict:
    """フェンス付きコードブロック内の KEY: value / ネストマッピングを素朴に抽出する。

    コメント行（`#` 始まり）はネストの有無によらず読み飛ばす（テンプレートの記入例除外）。
    """
    raw: dict = {}
    in_fence = False
    current_nested = None
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            current_nested = None
            continue
        if not in_fence:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[0].isspace():
            if current_nested is not None:
                m = SUB_KV_RE.match(line)
                if m:
                    raw.setdefault(current_nested, {})
                    raw[current_nested][m.group(1).strip()] = m.group(2).strip()
            continue
        m_header = TOP_HEADER_RE.match(line)
        if m_header:
            current_nested = m_header.group(1)
            raw.setdefault(current_nested, {})
            continue
        current_nested = None
        m_kv = TOP_KV_RE.match(line)
        if m_kv:
            raw[m_kv.group(1)] = m_kv.group(2).strip()
    return raw


def build_bundle(raw: dict, workspace_root: Path):
    warnings: list[str] = []
    out: dict = {"WORKSPACE_ROOT": str(workspace_root)}

    repos_raw = raw.get("REPOS")
    repos_map = dict(repos_raw) if isinstance(repos_raw, dict) else {}
    out["REPOS_MAP"] = repos_map
    out["REPOS_KEYS"] = list(repos_map.keys())
    out["IS_MULTI"] = len(out["REPOS_KEYS"]) >= 2

    for key, default in SIMPLE_DEFAULTS.items():
        val = raw.get(key)
        if val is None or val == "":
            resolved = default
        elif key in INT_KEYS:
            try:
                resolved = int(val)
            except ValueError:
                warnings.append(
                    f"{key} の値 `{val}` は整数として解釈できません。既定値 {default} を使用します。"
                )
                resolved = default
        elif key in BOOL_KEYS:
            low = str(val).strip().lower()
            if low in ("true", "false"):
                resolved = (low == "true")
            else:
                warnings.append(
                    f"{key} の値 `{val}` は true/false ではありません。既定値 {default} を使用します。"
                )
                resolved = default
        else:
            resolved = val
        out[ALIASES.get(key, key)] = resolved

    if out["VCS_TYPE"] not in VALID_VCS_TYPES:
        warnings.append(
            f"VCS_TYPE の値 `{out['VCS_TYPE']}` は認識できません"
            f"（有効値: {'/'.join(VALID_VCS_TYPES)}）。none として扱います。"
        )
        out["VCS_TYPE"] = "none"

    out["DOCS"] = str(workspace_root / out["DOCS_DIR"])

    tfr_raw = raw.get("TEST_FRAMEWORK_REPOS")
    out["TEST_FRAMEWORK_REPOS"] = dict(tfr_raw) if isinstance(tfr_raw, dict) else {}

    for base in OVERRIDE_BASES:
        prefix = base + "."
        overrides = {
            k[len(prefix):]: v for k, v in raw.items()
            if isinstance(k, str) and isinstance(v, str) and k.startswith(prefix)
        }
        out[base + "_OVERRIDES"] = overrides

    return out, warnings


def cmd_load(args) -> None:
    if args.list_keys:
        print(json.dumps(KEY_DOCS, ensure_ascii=False, indent=2))
        return
    config_path = find_config(Path(args.start_dir))
    if config_path is None:
        _err(
            f"xddp.config.md が見つかりません（{Path(args.start_dir).resolve()} から上方探索）。",
            code=3,
        )
        return
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as e:
        _err(f"xddp.config.md の読み込みに失敗しました: {e}")
        return
    raw = parse_raw(text)
    bundle, warnings = build_bundle(raw, config_path.parent.resolve())
    for w in warnings:
        print(f"⚠️ {w}", file=sys.stderr)
    print(json.dumps(bundle, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_load = sub.add_parser("load")
    p_load.add_argument("--start-dir", default=".",
                        help="xddp.config.md を上方探索する起点ディレクトリ（既定: カレントディレクトリ）")
    p_load.add_argument("--format", default="json", choices=["json"])
    p_load.add_argument("--list-keys", action="store_true",
                        help="設定を読み込まず、出力キー名・既定値・消費者の一覧を表示する")
    p_load.set_defaults(func=cmd_load)

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
