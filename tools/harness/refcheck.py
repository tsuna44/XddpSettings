#!/usr/bin/env python3
"""refcheck.py — XDDP ツール自身の参照整合リント（L1・L3／トークン0）

自然言語プログラム（スキル・エージェント定義）は「コンパイラも型検査もない」ため、
機械検証が容易なのは参照整合性のみである。本スクリプトは以下4種を純 Python で静的検査する。

- 検査A: `apply "## X"` が参照先ファイルに実在する見出しを指すか（L1）
- 検査B: `subagent_type=xddp-XXX` がエージェント定義に解決し、引数契約が整合するか（L1）
- 検査C: テンプレートプレースホルダーの整合（L1・warning 中心＝過検出回避）
- 検査D: スキルの決定的スクリプト呼び出しが実在サブコマンド・フラグに解決するか（L3）

検査対象は `ClaudeCode/.claude/` のソース（`~/.claude/` のデプロイ済みコピーではない）。
LLM は一切起動しない（トークン0）。違反があれば exit code 非0。

出力契約:
  --json 指定時: stdout に {"ok": bool, "violations": [...], "counts": {...}} を出力。
  既定: 人可読サマリを stdout に出力。
  error を1件でも含めば exit 1、warning のみなら exit 0。

参照: plans/PLAN-20260725-p2-test-harness.md Section 3.1
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 共通ユーティリティ
# ---------------------------------------------------------------------------

# スキルが参照する `~/.claude/` を、リポジトリ内の編集元へ読み替えるプレフィックス
HOME_CLAUDE_PREFIX = "~/.claude/"
REPO_CLAUDE_PREFIX = "ClaudeCode/.claude/"

# 検査Dで機械照合する決定的スクリプト（argparse を持つもの）。
# excel_dump.py・crs_md2excel.py は argparse 非使用のため対象外。
DETERMINISTIC_SCRIPTS = {
    "specout_bfs.py",
    "specout_verify_counts.py",
    "chd_sp_coverage.py",
    "artifact_lint.py",
    "xddp_gate_snapshot.py",
    "xddp_progress.py",
}

HEADING_RE = re.compile(r"^#{2,}\s+(.*\S)\s*$")
APPLY_RE = re.compile(r'apply\s+"(#{2,}\s*[^"]+)"')
READ_TARGET_RE = re.compile(r"Read\s+`([^`]+)`")
SUBAGENT_RE = re.compile(r"subagent_type[=:]\s*`?([a-z][a-z0-9-]*)`?")
# ペイロードキー行（フェンス内の `KEY: value`。列0開始・非インデント）
PAYLOAD_KEY_RE = re.compile(r"^([A-Z][A-Z0-9_]*):")
# エージェント Inputs 節の宣言行（`- \`KEY\`: ...`）
INPUT_DECL_RE = re.compile(r"^\s*-\s+`([A-Z][A-Z0-9_]*)`")
# テンプレートプレースホルダー（独立トークン `{UPPER_SNAKE}`）
PLACEHOLDER_RE = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")

# 検査C の例示除外リスト（plan 3.1「{DB}・{GPIO} 等のドメイン例示を error 判定しない」）。
# これらはテンプレート内で「記入例」として置かれる図・データ構造の説明トークンであり、
# スキルが実行時に置換する制御プレースホルダーではない。実測（2026-07-25）で確定。
# 変更時は test_refcheck.py の該当ケースも更新すること。
DOMAIN_EXAMPLE_PLACEHOLDERS = {
    # データモデル・状態機械の記入例
    "ENTITY_A", "ENTITY_B", "STATE_A", "STATE_B", "STATE_C",
    # 組み込み・Web の I/F 記入例
    "DB", "GPIO", "UART", "UART1", "ADDRESS", "RESOURCE", "METHOD",
    # 汎用の記入例プレースホルダー
    "M", "N", "NNN", "YYYY", "DATE", "DOMAIN", "ERROR_TYPE", "CONST_NAME",
    "SIDE_EFFECTS_DFD_PLACEHOLDER",
}
FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")


def _v(check, severity, file, line, message):
    return {
        "check": check,
        "severity": severity,
        "file": file,
        "line": line,
        "message": message,
    }


def normalize_heading(text: str) -> str:
    """見出しを比較用に正規化する。

    - 先頭の `#` 記号と空白を除去
    - 末尾の可変サフィックス（`(UR-016)`・`（up to N rounds）` 等の括弧補足）を1つ除去

    例: `## Regenerate CRS Excel (UR-016)` を `apply "## Regenerate CRS Excel"` と一致させる。
    """
    text = text.lstrip("#").strip()
    text = re.sub(r"\s*[\(（][^()（）]*[\)）]\s*$", "", text)
    return text.strip()


def extract_headings(path: Path) -> set[str]:
    headings = set()
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            m = HEADING_RE.match(raw)
            if m:
                headings.add(normalize_heading(m.group(1)))
    except OSError:
        pass
    return headings


def resolve_claude_path(ref: str, repo_root: Path) -> Path | None:
    """`~/.claude/...` または相対パス表記をリポジトリ内の実ファイルへ解決する。

    プレースホルダー（`{...}`）を含むパスは静的解決不能のため None を返す。
    """
    if "{" in ref:
        return None
    if ref.startswith(HOME_CLAUDE_PREFIX):
        return repo_root / (REPO_CLAUDE_PREFIX + ref[len(HOME_CLAUDE_PREFIX):])
    return None


# ---------------------------------------------------------------------------
# ターゲット探索
# ---------------------------------------------------------------------------

def discover_skill_md(skills_dir: Path) -> list[Path]:
    return sorted(p for p in skills_dir.rglob("*.md"))


def discover_agent_md(agents_dir: Path) -> list[Path]:
    return sorted(p for p in agents_dir.glob("*.md"))


# ---------------------------------------------------------------------------
# 検査A: apply 見出し整合
# ---------------------------------------------------------------------------

def check_a_apply_headings(md_files: list[Path], repo_root: Path) -> list[dict]:
    violations: list[dict] = []
    heading_cache: dict[Path, set[str]] = {}

    def headings_for(path: Path) -> set[str]:
        if path not in heading_cache:
            heading_cache[path] = extract_headings(path)
        return heading_cache[path]

    for path in md_files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        rel = str(path.relative_to(repo_root))
        for idx, line in enumerate(lines):
            for am in APPLY_RE.finditer(line):
                ref_heading = normalize_heading(am.group(1))
                # 対象ファイル解決: 当該行から上方向へ最も近い Read `<path>` を採用
                target_path, target_rel = _nearest_read_target(
                    lines, idx, path, repo_root
                )
                if target_path is None:
                    # Read が無ければ自ファイル内見出しを指すものとみなす
                    target_path, target_rel = path, rel
                if not target_path.exists():
                    violations.append(_v(
                        "A", "error", rel, idx + 1,
                        f'apply "## {ref_heading}" の Read 対象 {target_rel} が存在しない',
                    ))
                    continue
                if ref_heading not in headings_for(target_path):
                    violations.append(_v(
                        "A", "error", rel, idx + 1,
                        f'apply "## {ref_heading}" に一致する見出しが {target_rel} に無い',
                    ))
    return violations


def _nearest_read_target(lines, idx, self_path: Path, repo_root: Path):
    """apply 行 idx から上方向（同一行を含む）で最も近い Read `<path>` を解決する。"""
    for i in range(idx, -1, -1):
        m = READ_TARGET_RE.search(lines[i])
        if not m:
            continue
        ref = m.group(1)
        resolved = resolve_claude_path(ref, repo_root)
        if resolved is None:
            # 解決不能（プレースホルダー等）。この Read は無視して更に上を探す
            continue
        try:
            return resolved, str(resolved.relative_to(repo_root))
        except ValueError:
            return resolved, str(resolved)
    return None, None


# ---------------------------------------------------------------------------
# 検査B: subagent_type + 引数契約
# ---------------------------------------------------------------------------

INPUT_KEY_RE = re.compile(r"`([A-Z][A-Z0-9_]*)`")


def _parse_agent_inputs(path: Path):
    """エージェント定義から (required_keys, optional_keys, has_inputs_section) を返す。

    入力宣言は複数の記法を採る:
      - `` - `CR_NUMBER`, `CR_PATH`, `TODAY` `` … カンマ区切り複数キー（すべて必須）
      - `` - `MODULE_SCOPE`: 説明 `` … 単一キー＋説明
      - `` - `SPO_DIR` (MODE=update のみ): 説明 `` … 条件付き（任意扱い）
      - `` - `DESIGN_FEEDBACK` (optional, ...): 説明 `` … 明示的任意
    キーは各宣言バレットの「コロン前セグメント」からのみ抽出する（説明中の
    バッククォートトークンをキーと誤認しないため）。
    """
    required: set[str] = set()
    optional: set[str] = set()
    has_section = False
    section = None  # None / "required" / "optional"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return required, optional, has_section
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            low = stripped.lower()
            if "inputs (provided by the caller)" in low:
                section, has_section = "required", True
            elif "optional input" in low:
                section = "optional"
            else:
                section = None
            continue
        if section is None or not stripped.startswith("- "):
            continue
        # コロン前を「キーセグメント」とし、そこからのみキーを抽出
        key_segment = line.split(":", 1)[0]
        keys = INPUT_KEY_RE.findall(key_segment)
        if not keys:
            continue
        seg_low = key_segment.lower()
        is_optional = (
            section == "optional"
            or "optional" in seg_low
            or "のみ" in key_segment  # 条件付き（MODE=xxx のみ 等）
        )
        for key in keys:
            (optional if is_optional else required).add(key)
    return required, optional, has_section


def _parse_payload_keys(lines, start_idx):
    """subagent_type 行の直後にあるフェンスブロックから渡すキーを抽出する。

    戻り値 (passed_required, passed_optional, parsed)。
    parsed=False はフェンスが見つからずパース不能（best-effort で warning 対象）。
    """
    # フェンス開始を探す（subagent_type 行から数行以内）
    n = len(lines)
    fence_start = None
    for i in range(start_idx, min(start_idx + 4, n)):
        if lines[i].strip().startswith("```"):
            fence_start = i
            break
    if fence_start is None:
        return set(), set(), False
    passed_required: set[str] = set()
    passed_optional: set[str] = set()
    for i in range(fence_start + 1, n):
        line = lines[i]
        if line.strip().startswith("```"):
            break
        # 条件付きキー: 行頭に `（... の場合のみ ...）` を伴う → optional
        conditional = bool(re.match(r"^\s*[（(].*(のみ|only|場合).*[）)]", line))
        m = PAYLOAD_KEY_RE.match(line)
        if m:
            key = m.group(1)
            if conditional:
                passed_optional.add(key)
            else:
                passed_required.add(key)
            continue
        # 条件付きプレフィックス直後にキーが続くケース: `（... のみ追加）KEY: value`
        cm = re.match(r"^\s*[（(][^）)]*[）)]\s*([A-Z][A-Z0-9_]*):", line)
        if cm:
            passed_optional.add(cm.group(1))
    return passed_required, passed_optional, True


def check_b_subagents(skill_files: list[Path], agents_dir: Path, repo_root: Path) -> list[dict]:
    violations: list[dict] = []
    agent_cache: dict[str, tuple] = {}

    def agent_info(name: str):
        if name not in agent_cache:
            apath = agents_dir / f"{name}.md"
            if not apath.exists():
                agent_cache[name] = None
            else:
                req, opt, has_section = _parse_agent_inputs(apath)
                # エージェント本文全体に現れる UPPER_SNAKE トークン集合。
                # 入力を複数サブセクション（Config Inputs 等）に分けて宣言する
                # エージェントの過検出を避けるため、本文言及も「既知」とみなす。
                try:
                    body_tokens = set(INPUT_KEY_RE.findall(
                        apath.read_text(encoding="utf-8")))
                except OSError:
                    body_tokens = set()
                agent_cache[name] = (apath, req, opt, has_section, body_tokens)
        return agent_cache[name]

    for path in skill_files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        rel = str(path.relative_to(repo_root))
        for idx, line in enumerate(lines):
            m = SUBAGENT_RE.search(line)
            if not m:
                continue
            name = m.group(1)
            info = agent_info(name)
            if info is None:
                violations.append(_v(
                    "B", "error", rel, idx + 1,
                    f"subagent_type={name} に対応するエージェント定義が agents/ に無い",
                ))
                continue
            apath, req, opt, has_section, body_tokens = info
            if not has_section:
                violations.append(_v(
                    "B", "warning", rel, idx + 1,
                    f"{name} は '### Inputs (provided by the caller)' 節を持たず契約照合をスキップ（best-effort）",
                ))
                continue
            passed_req, passed_opt, parsed = _parse_payload_keys(lines, idx)
            if not parsed:
                violations.append(_v(
                    "B", "warning", rel, idx + 1,
                    f"subagent_type={name} の pass ブロックが定型でなく契約照合をスキップ（best-effort）",
                ))
                continue
            # 「必須キーの欠落」検査は意図的に実施しない（過検出回避）:
            # spec-writer（create/update/update-design）等の多モードエージェントは
            # 単一の Inputs 節に全モードのキーを宣言し、conditional 入力も多いため、
            # モード別の必須集合を静的に厳密照合できず、ほぼ全件が偽陽性になる
            # （実測: この検査は 73 件の偽警告を生む）。plan 3.1「確実な誤りのみ／
            # 過検出で運用を破綻させない」に従い本方向は L4/L5 full-run スモーク
            # （実起動でエージェントが失敗する）に委ね、静的リントでは扱わない。
            #
            # エージェント本文のどこにも現れないキーを渡している（誤記/廃止候補）→ warning。
            # 一部エージェントは caller 注入のタスクブロック（CLASSIFICATION_TASK 等）を
            # 名前で参照しないため、error にすると正当な呼び出しを誤検出する。best-effort。
            known = req | opt | body_tokens
            for key in sorted(passed_req - known):
                violations.append(_v(
                    "B", "warning", rel, idx + 1,
                    f"呼び出し側が渡す `{key}` が {name} 定義のどこにも現れない（誤記/廃止キー候補 or caller注入タスク）",
                ))
    return violations


def check_agent_name_frontmatter(agent_files: list[Path], repo_root: Path) -> list[dict]:
    """エージェント frontmatter の name: とファイル名の一致を確認（検査B補助）。"""
    violations: list[dict] = []
    for path in agent_files:
        rel = str(path.relative_to(repo_root))
        name_val = None
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                mm = re.match(r"^name:\s*(\S+)", raw)
                if mm:
                    name_val = mm.group(1)
                    break
        except OSError:
            continue
        if name_val is not None and name_val != path.stem:
            violations.append(_v(
                "B", "error", rel, 1,
                f"frontmatter name: {name_val} がファイル名 {path.stem} と一致しない",
            ))
    return violations


# ---------------------------------------------------------------------------
# 検査C: テンプレートプレースホルダー（warning 中心）
# ---------------------------------------------------------------------------

def check_c_placeholders(skills_dir: Path, repo_root: Path) -> list[dict]:
    """テンプレートに現れるプレースホルダーの静的整合。

    ドメイン例示（{DB}・{GPIO} 等）と制御プレースホルダーの機械判別は困難なため、
    本検査は warning のみを出し exit code を汚さない（過検出回避。plan 3.1 検査C）。
    実際の未置換トークン検査（C2）は full-run スモークの構造アサートで実施する。
    """
    violations: list[dict] = []
    template_files = sorted(skills_dir.rglob("templates/*.md"))
    if not template_files:
        return violations
    # スキル本文（テンプレート以外）で言及されるプレースホルダー名の集合
    mentioned: set[str] = set()
    for path in skills_dir.rglob("*.md"):
        if "/templates/" in str(path).replace("\\", "/"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        mentioned.update(PLACEHOLDER_RE.findall(text))
    for path in template_files:
        rel = str(path.relative_to(repo_root))
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        tokens = set(PLACEHOLDER_RE.findall(text))
        # どのスキル本文からも言及されず、かつ既知のドメイン例示でもないプレースホルダー
        # = 置換漏れ候補（warning）。ドメイン例示は除外リストで抑止（過検出回避）。
        for tok in sorted(tokens - mentioned - DOMAIN_EXAMPLE_PLACEHOLDERS):
            violations.append(_v(
                "C", "warning", rel, 0,
                f"プレースホルダー {{{tok}}} はどのスキル本文からも言及されない（置換漏れ候補。誤検出なら例示除外リストへ追加）",
            ))
    return violations


# ---------------------------------------------------------------------------
# 検査D: スクリプト↔スキル結線（L3）
# ---------------------------------------------------------------------------

class ArgparseIntrospector:
    """対象スクリプトを `--help` サブプロセスで解析し、サブコマンド・フラグを取得する。

    plan 3.1 検査D の既定方式（移植性の高い --help サブプロセス方式）。
    """

    def __init__(self):
        self._top: dict[Path, dict] = {}
        self._sub: dict[tuple[Path, str], set[str]] = {}

    @staticmethod
    def _run_help(args: list[str]) -> str:
        try:
            proc = subprocess.run(
                args, capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return (proc.stdout or "") + "\n" + (proc.stderr or "")

    def top(self, script: Path) -> dict:
        if script in self._top:
            return self._top[script]
        out = self._run_help([sys.executable, str(script), "--help"])
        subcommands: set[str] = set()
        # usage 行または positional の `{a,b,c}` からサブコマンドを抽出
        for m in re.finditer(r"\{([a-z0-9,_-]+)\}", out):
            parts = [p for p in m.group(1).split(",") if p]
            # サブコマンド候補（複数要素 or ハイフン含む）のみ採用
            if len(parts) >= 2 or any("-" in p for p in parts):
                subcommands.update(parts)
        flags = set(FLAG_RE.findall(out))
        info = {"subcommands": subcommands, "flags": flags, "available": bool(out.strip())}
        self._top[script] = info
        return info

    def sub_flags(self, script: Path, sub: str) -> set[str]:
        key = (script, sub)
        if key in self._sub:
            return self._sub[key]
        out = self._run_help([sys.executable, str(script), sub, "--help"])
        flags = set(FLAG_RE.findall(out))
        self._sub[key] = flags
        return flags


def _find_script_path(script_name: str, skills_dir: Path) -> Path | None:
    matches = list(skills_dir.rglob(f"scripts/{script_name}"))
    return matches[0] if matches else None


def _extract_script_calls(lines, scripts=DETERMINISTIC_SCRIPTS):
    """スキル本文から決定的スクリプト呼び出しを (line_idx, script, subcommand, flags) で返す。

    複数行 `\\` 継続を論理行に結合してから解析する。
    """
    # 論理行結合
    logical = []  # (start_idx, text)
    buf = ""
    start = None
    for idx, line in enumerate(lines):
        s = line.rstrip("\n")
        if start is None:
            start = idx
        if s.endswith("\\"):
            buf += s[:-1] + " "
            continue
        buf += s
        logical.append((start, buf))
        buf = ""
        start = None
    if buf:
        logical.append((start if start is not None else 0, buf))

    calls = []
    for start_idx, text in logical:
        for sm in re.finditer(r"([a-z_]+\.py)\b", text):
            name = sm.group(1)
            if name not in scripts:
                continue
            rest = text[sm.end():]
            # rest の先頭トークン列を解析。バッククォート・引用符終端で打ち切る
            rest = rest.split("`")[0]
            tokens = rest.split()
            subcommand = None
            flags = []
            for tok in tokens:
                if tok.startswith("--"):
                    fm = FLAG_RE.match(tok.strip("[]"))
                    if fm:
                        flags.append(fm.group(0))
                elif re.fullmatch(r"[a-z][a-z0-9-]*", tok) and subcommand is None and not flags:
                    subcommand = tok
                # プレースホルダー値・引用値はスキップ
            calls.append((start_idx, name, subcommand, flags))
    return calls


def check_d_script_wiring(skill_files: list[Path], skills_dir: Path, repo_root: Path,
                          introspector: ArgparseIntrospector | None = None,
                          deterministic_scripts=DETERMINISTIC_SCRIPTS) -> list[dict]:
    violations: list[dict] = []
    introspector = introspector or ArgparseIntrospector()
    script_paths: dict[str, Path | None] = {}

    for path in skill_files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        rel = str(path.relative_to(repo_root))
        for line_idx, name, subcommand, flags in _extract_script_calls(lines, deterministic_scripts):
            if name not in script_paths:
                script_paths[name] = _find_script_path(name, skills_dir)
            spath = script_paths[name]
            if spath is None:
                violations.append(_v(
                    "D", "warning", rel, line_idx + 1,
                    f"{name} の実体が scripts/ に見つからず結線照合をスキップ",
                ))
                continue
            top = introspector.top(spath)
            if not top["available"]:
                violations.append(_v(
                    "D", "warning", rel, line_idx + 1,
                    f"{name} の --help 解析に失敗し結線照合をスキップ",
                ))
                continue
            has_subs = bool(top["subcommands"])
            if has_subs:
                if subcommand is None:
                    # 表・散文中の言及等。サブコマンド無し呼び出しは警告に留める
                    continue
                if subcommand not in top["subcommands"]:
                    violations.append(_v(
                        "D", "error", rel, line_idx + 1,
                        f"{name} {subcommand} は未定義サブコマンド（有効: {sorted(top['subcommands'])}）",
                    ))
                    continue
                valid_flags = introspector.sub_flags(spath, subcommand)
            else:
                valid_flags = top["flags"]
            for flag in flags:
                if flag not in valid_flags:
                    label = f"{name} {subcommand}".strip()
                    violations.append(_v(
                        "D", "error", rel, line_idx + 1,
                        f"{label} に未定義フラグ {flag}（有効: {sorted(valid_flags)}）",
                    ))
    return violations


# ---------------------------------------------------------------------------
# ランナー
# ---------------------------------------------------------------------------

def run(repo_root: Path, checks="ABCD", introspector: ArgparseIntrospector | None = None) -> list[dict]:
    skills_dir = repo_root / "ClaudeCode/.claude/skills"
    agents_dir = repo_root / "ClaudeCode/.claude/agents"
    skill_files = discover_skill_md(skills_dir) if skills_dir.exists() else []
    agent_files = discover_agent_md(agents_dir) if agents_dir.exists() else []

    violations: list[dict] = []
    if "A" in checks:
        violations += check_a_apply_headings(skill_files + agent_files, repo_root)
    if "B" in checks:
        violations += check_agent_name_frontmatter(agent_files, repo_root)
        violations += check_b_subagents(skill_files, agents_dir, repo_root)
    if "C" in checks:
        violations += check_c_placeholders(skills_dir, repo_root)
    if "D" in checks:
        violations += check_d_script_wiring(skill_files, skills_dir, repo_root, introspector)
    return violations


def summarize(violations: list[dict]):
    errors = [v for v in violations if v["severity"] == "error"]
    warnings = [v for v in violations if v["severity"] == "warning"]
    return {"errors": len(errors), "warnings": len(warnings), "total": len(violations)}


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "ClaudeCode/.claude/skills").exists():
            return cand
    return cur


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="XDDP ツール参照整合リント（L1・L3）")
    parser.add_argument("--root", type=Path, default=None,
                        help="リポジトリルート（既定: このスクリプトから自動探索）")
    parser.add_argument("--checks", default="ABCD",
                        help="実行する検査（A/B/C/D の部分集合。既定: ABCD）")
    parser.add_argument("--json", action="store_true", help="機械可読 JSON を出力")
    args = parser.parse_args(argv)

    repo_root = args.root.resolve() if args.root else _find_repo_root(Path(__file__).parent)
    violations = run(repo_root, checks=args.checks.upper())
    counts = summarize(violations)
    ok = counts["errors"] == 0

    if args.json:
        print(json.dumps({"ok": ok, "counts": counts, "violations": violations},
                         ensure_ascii=False, indent=2))
    else:
        for v in violations:
            mark = "❌" if v["severity"] == "error" else "⚠️"
            loc = f"{v['file']}:{v['line']}" if v["line"] else v["file"]
            print(f"{mark} [{v['check']}] {loc}  {v['message']}")
        status = "OK" if ok else "NG"
        print(f"\nrefcheck: {status}  errors={counts['errors']} warnings={counts['warnings']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
