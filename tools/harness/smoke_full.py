#!/usr/bin/env python3
"""smoke_full.py — L4/L5 full-run スモーク（LLM 使用・予算ガード付き）

スキルのオーケストレーション（L4）と成果物の構造的健全性（L5）を、実際に LLM で
スキルを起動して検証する。トークンは予算ガードで構造的にキャップする。

**重要（実装状況）:** 純ロジック（構造性質抽出・予算積算・上限判定・ゴールデン照合・
環境依存フィールド正規化）とオーケストレーションループ（隔離ステージング → 工程起動 →
予算ガード → 構造アサート → 後片付け）は実装済みで、`tools/harness/tests/test_smoke_full.py`
が `_invoke_phase`（実 LLM 起動）と `subprocess`（setup.sh）をモックして 0 トークンで検証する
（実装: 子プラン PLAN-20260726-smoke-full-runner-enablement A。設計: 親プラン Section 3.2）。

実 LLM を起動する `_invoke_phase`（`claude -p --output-format json` によるスキル起動）は
plan 3.5 step 0 の前提スパイクで挙動確認済み（スラッシュコマンド起動可否・usage 積算範囲・
`--model` 継承・隔離HOMEへの `model:` 注入）。ゴールデン値・工程別モデル・`SMOKE_TOKEN_BUDGET`
は校正ラン（子プラン B/C/D）で実測確定するまで確定値を持たない（`smoke_config.md` は確定後に
書き込む）。予算未供給（`SMOKE_TOKEN_BUDGET`／`SMOKE_CALIBRATE_BUDGET`／`--budget` がいずれも
0・未指定）の通常ランは実効予算ゲート（exit 6）で停止する。exit コード表は 4.5 相当を参照。

参照: plans/PLAN-20260725-p2-test-harness.md Section 3.2, 3.4, 3.5;
      plans/PLAN-20260726-smoke-full-runner-enablement.md Section 4
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --phase が受理する工程ラベル（plan 3.3「PHASE の受理値」）。
# 工程08は xddp.07 に統合、工程01は --all 専用のため --phase 対象外。
PHASE_LABELS = ["02", "03", "04", "05", "06", "07", "09", "10", "11", "close"]
# multi 版シードを持つ工程（cross 生成が絡む）。他工程での --multi 指定はエラー。
MULTI_PHASES = {"04", "11"}

# Anthropic互換の第三者エンドポイント利用時に `claude` CLI へ素通しする環境変数
# （ANTHROPIC_BASE_URL と組み合わせて使うモデルエイリアス上書き。未設定のキーは転送しない）。
PASSTHROUGH_ENV_KEYS = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
)

# 工程ラベル → 実スラッシュコマンド名（正準表。plan 3.3/§7 リスク「実コマンド名の確定」）。
# スキル名がそのままコマンド名（例: xddp.02.analysis → /xddp.02.analysis）。
PHASE_COMMANDS = {
    "01": "/xddp.01.init",
    "02": "/xddp.02.analysis",
    "03": "/xddp.03.req",
    "04": "/xddp.04.specout",
    "05": "/xddp.05.arch",
    "06": "/xddp.06.design",
    "07": "/xddp.07.code",
    "09": "/xddp.09.test",
    "10": "/xddp.10.test-run",
    "11": "/xddp.11.specs",
    "close": "/xddp.close",
}
# ハーベスト/スモークで使う CR 識別子・タイトル（既存フィクスチャ 960/961 と衝突しない番号）。
HARVEST_CR = "CR-2026-970"
HARVEST_TITLE = "スモーク検証用CR"

# 構造アサートで検出する未置換トークン（検査C2。plan 3.1）。
UNREPLACED_TOKEN_RE = re.compile(r"\{[A-Z][A-Z0-9_]*\}")

# リポジトリ・フィクスチャの正準パス（`tools/harness/smoke_full.py` からの相対解決）。
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SETUP_SH = REPO_ROOT / "ClaudeCode" / "setup.sh"
FIXTURES_ROOT = REPO_ROOT / "test-fixtures" / "scratch-workspace-min"
SEEDS_ROOT = FIXTURES_ROOT / "seeds"
MULTI_SRC = FIXTURES_ROOT / "multi"
# 連鎖ハーベストの起点 ws に置く config（`REPOS: svc-a: ../multi/svc-a` を持つ）。
# init は既存 config を尊重する（`if not exists`）ため、これを置くと母体解決が効いた
# CR を新規作成でき、以降の specout が `../multi/svc-a/src/mod_a2.py` へ到達する。
SINGLE_BASE_CONFIG = FIXTURES_ROOT / "single" / "xddp.config.md"
GOLDEN_ROOT = REPO_ROOT / "test-fixtures" / "golden"
SMOKE_CONFIG_PATH = REPO_ROOT / "tools" / "harness" / "smoke_config.md"

# 1工程起動の想定単価（can_start の事前予算チェック用。cfg で上書き可）。
DEFAULT_PHASE_EST_USD = 0.10

# 工程 → 成果物ディレクトリ glob（ワークスペースルート相対）。B 生成物で実パスを確認し
# 必要なら smoke_config.md の phase_artifacts で上書きする（plan 4.3「成果物ディレクトリの特定」・
# Section 3.3 リスク「成果物パスの工程対応」）。
DEFAULT_PHASE_ARTIFACT_GLOB = {
    "01": "xddp/CR-*/01_requirements",
    "02": "xddp/CR-*/02_analysis",
    "03": "xddp/CR-*/03_change-requirements",
    "04": "xddp/CR-*/04_specout",
    "05": "xddp/CR-*/05_architecture",
    "06": "xddp/CR-*/06_design",
    "07": "xddp/CR-*/07_coding",
    "09": "xddp/CR-*/09_test-spec",
    "10": "xddp/CR-*/10_test-results",
    "11": "xddp/latest-specs",
    "close": "xddp/CR-*",
}


# ---------------------------------------------------------------------------
# 予算ガード（純ロジック・テスト対象）
# ---------------------------------------------------------------------------

class BudgetExceeded(Exception):
    """累積コストが上限を超過したことを表す。"""


class BudgetTracker:
    """各工程起動の usage/total_cost_usd を積算し、上限超過で中断させる。

    plan 3.2 実行モデル step 3・3.4「予算ガードの二重化」。
    サブエージェント消費が親 usage に積算されるか（3.5 step 0 ③）は要スパイク確認。
    積算されない場合は add_response のトークン加算方式をここで是正する。
    """

    def __init__(self, budget_usd: float, max_phases: int | None = None):
        self.budget_usd = budget_usd
        self.max_phases = max_phases
        self.total_cost_usd = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.phases_run = 0
        self.history: list[dict] = []

    def can_start(self, estimated_usd: float) -> bool:
        """工程開始前チェック: 残予算 < 想定単価 なら False（起動しない）。"""
        if self.max_phases is not None and self.phases_run >= self.max_phases:
            return False
        return (self.budget_usd - self.total_cost_usd) >= estimated_usd

    def add_response(self, resp: dict) -> None:
        """claude -p の応答 JSON から usage/コストを積算し、超過なら例外。"""
        usage = resp.get("usage", {}) or {}
        self.input_tokens += int(usage.get("input_tokens", 0) or 0)
        self.output_tokens += int(usage.get("output_tokens", 0) or 0)
        self.total_cost_usd += float(resp.get("total_cost_usd", 0.0) or 0.0)
        self.phases_run += 1
        self.history.append({
            "phase": resp.get("_phase"),
            "cost_usd": float(resp.get("total_cost_usd", 0.0) or 0.0),
            "cumulative_usd": self.total_cost_usd,
        })
        if self.total_cost_usd > self.budget_usd:
            raise BudgetExceeded(
                f"累積 ${self.total_cost_usd:.4f} が上限 ${self.budget_usd:.4f} を超過")

    def snapshot(self) -> dict:
        return {
            "total_cost_usd": round(self.total_cost_usd, 6),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "phases_run": self.phases_run,
            "budget_usd": self.budget_usd,
            "history": self.history,
        }


# ---------------------------------------------------------------------------
# 構造性質の抽出（純ロジック・テスト対象。L5）
# ---------------------------------------------------------------------------

HEADING_RE = re.compile(r"^#{1,6}\s+(.*\S)\s*$")
FRONTMATTER_KEY_RE = re.compile(r"^([a-zA-Z][\w-]*):")
# SP-ID・UR-ID など成果物 ID（plan 3.2 構造性質「ID 集合」）
ID_RE = re.compile(r"\b((?:SP|UR|SR|CR)-[0-9A-Za-z-]+)\b")


def extract_structural_properties(path: Path) -> dict:
    """成果物ファイル/ディレクトリから構造性質を抽出する（散文は見ない）。

    返す構造性質（plan 3.2「工程別に検証する構造性質」の共通部分）:
      - headings: 見出しテキスト集合
      - frontmatter_keys: 先頭 YAML フロントマターのキー集合
      - ids: 出現する成果物 ID 集合（SP/UR/SR/CR）
      - unreplaced_tokens: `{UPPER_SNAKE}` 未置換トークン集合（C2。空であるべき）
      - table_count / mermaid_count: 構造要素の件数
    """
    files = sorted(path.rglob("*.md")) if path.is_dir() else [path]
    # AI レビュー副産物（`review/` サブディレクトリ・`.review-brief.md`）は主成果物ではなく
    # 実行ごとに構造が大きく変動するため、構造性質・ゴールデン照合から除外する
    # （ゴールデンの脆さ＝偽失敗を低減。plan 5.2 C の実測で判明）。
    files = [f for f in files
             if "review" not in f.parts and f.name != ".review-brief.md"]
    headings: set[str] = set()
    fm_keys: set[str] = set()
    ids: set[str] = set()
    unreplaced: set[str] = set()
    table_rows = 0
    mermaid = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        fm_keys |= _frontmatter_keys(text)
        for line in text.splitlines():
            hm = HEADING_RE.match(line)
            if hm:
                headings.add(hm.group(1).strip())
            if line.lstrip().startswith("|") and line.rstrip().endswith("|"):
                table_rows += 1
            ids |= set(ID_RE.findall(line))
            unreplaced |= set(UNREPLACED_TOKEN_RE.findall(line))
        mermaid += len(re.findall(r"```mermaid", text))
    return {
        "headings": sorted(headings),
        "frontmatter_keys": sorted(fm_keys),
        "ids": sorted(ids),
        "unreplaced_tokens": sorted(unreplaced),
        "table_row_count": table_rows,
        "mermaid_count": mermaid,
    }


def _frontmatter_keys(text: str) -> set[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return set()
    keys: set[str] = set()
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = FRONTMATTER_KEY_RE.match(line)
        if m:
            keys.add(m.group(1))
    return keys


# 照合時に無視する環境/実行依存フィールド（plan 3.2「正規化してから照合」）。
def normalize_properties(props: dict) -> dict:
    """日付・絶対パス・トークン数等の実行依存要素を照合前に除去/正規化する。"""
    out = dict(props)
    # 見出し・ID から日付や絶対パスを含む可変要素を正規化
    out["headings"] = sorted(_normalize_text(h) for h in props.get("headings", []))
    out["ids"] = sorted(set(props.get("ids", [])))
    return out


_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_ABSPATH_RE = re.compile(r"(/[^ \t]+)+")


def _normalize_text(s: str) -> str:
    s = _DATE_RE.sub("{DATE}", s)
    return s.strip()


# ---------------------------------------------------------------------------
# ゴールデン照合（純ロジック・テスト対象）
# ---------------------------------------------------------------------------

def compare_to_golden(actual: dict, golden: dict, required_headings=None) -> list[str]:
    """構造性質をゴールデンと照合し、違反メッセージの一覧を返す（空 = 合格）。

    - required_headings: ゴールデンが必須と定める見出し集合の部分集合検査。
    - unreplaced_tokens が非空なら常に違反（C2: 未置換トークン残存）。
    - ids: ゴールデンが定める ID 集合との一致（過不足を報告）。
    """
    violations: list[str] = []
    a = normalize_properties(actual)
    g = normalize_properties(golden) if golden else {}

    if a.get("unreplaced_tokens"):
        violations.append(
            f"未置換トークンが残存: {a['unreplaced_tokens']}")

    req = set(required_headings or g.get("required_headings", []))
    have = set(a.get("headings", []))
    missing = req - have
    if missing:
        violations.append(f"必須見出しが欠落: {sorted(missing)}")

    if "ids" in g:
        exp, act = set(g["ids"]), set(a.get("ids", []))
        if exp - act:
            violations.append(f"期待 ID が欠落: {sorted(exp - act)}")

    for key in ("frontmatter_keys",):
        if key in g:
            missing_keys = set(g[key]) - set(a.get(key, []))
            if missing_keys:
                violations.append(f"{key} 欠落: {sorted(missing_keys)}")

    return violations


# ---------------------------------------------------------------------------
# smoke_config.md ローダ
# ---------------------------------------------------------------------------

def load_smoke_config(path: Path) -> dict:
    """smoke_config.md の簡易 `KEY: value` 設定を読む（ハーネスレベル config）。"""
    cfg: dict = {"models": {}, "seeds": {}}
    if not path.exists():
        return cfg
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        m = re.match(r"^-?\s*`?([A-Z_][A-Z0-9_]*)`?\s*[:=]\s*(.+)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip("`")
        # 行末インラインコメント（` # ...`）を除去してから数値化する
        # （smoke_config.md は `KEY: 0.0   # 説明` 形式で注記を持つため）。
        val = re.sub(r"\s+#.*$", "", val).strip().strip("`")
        if key in ("SMOKE_TOKEN_BUDGET", "SMOKE_CALIBRATE_BUDGET"):
            try:
                cfg[key] = float(val)
            except ValueError:
                pass
        elif key == "SMOKE_MAX_PHASES":
            try:
                cfg["SMOKE_MAX_PHASES"] = int(val)
            except ValueError:
                pass
    return cfg


def resolve_phase(phase: str, multi: bool) -> str:
    """--phase / --multi を seeds ディレクトリ名へ解決する（plan 3.2 解決規則）。"""
    if phase not in PHASE_LABELS:
        raise ValueError(
            f"未定義の PHASE '{phase}'。受理値: {PHASE_LABELS}（工程01は --all 専用）")
    if multi and phase not in MULTI_PHASES:
        raise ValueError(
            f"--multi は {sorted(MULTI_PHASES)} のみ受理（cross 生成が絡む工程）")
    variant = "multi" if multi else "single"
    # 数値工程はそのまま、非数値ラベル（close）はシード名に合わせて先頭大文字化
    label = phase if phase.isdigit() else phase.capitalize()
    return f"phase{label}-{variant}"


# ---------------------------------------------------------------------------
# LLM 起動経路（要スパイク確認。既定では claude 未導入を検出して停止）
# ---------------------------------------------------------------------------

def claude_available() -> bool:
    return shutil.which("claude") is not None


def _phase_command(phase: str, cr: str, title: str) -> str:
    """工程ラベルを実スラッシュコマンド文字列（引数込み）へ（PHASE_COMMANDS 正準表）。

    init（01）のみ CR番号＋タイトルを取り、他工程は CR番号のみを取る（各スキルの CR Resolution）。
    未登録ラベルは従来の `/xddp.{phase}` へフォールバック（回帰時に気付けるよう残す）。
    """
    cmd = PHASE_COMMANDS.get(phase, f"/xddp.{phase}")
    if phase == "01":
        return f"{cmd} {cr} {title}"
    return f"{cmd} {cr}"


def _invoke_phase(phase: str, workspace: Path, model: str,
                  home: Path, auth_env: dict, *,
                  cr: str = HARVEST_CR, title: str = HARVEST_TITLE) -> dict:
    """1工程をヘッドレスで起動し応答 JSON を返す（plan 3.2 実行モデル step 2）。

    ※ スラッシュコマンド起動可否・usage 積算範囲は 3.5 step 0 スパイクで確認済み。
    unittest では本関数をモック応答へ差し替えて 0 トークンで検証する（実 LLM は起動しない）。

    隔離 HOME では OAuth/セッション認証情報を引き継げないため、非対話認証用の環境変数
    （`auth_env` = `CLAUDE_CODE_OAUTH_TOKEN` 優先／`ANTHROPIC_API_KEY` フォールバック／
    `ANTHROPIC_AUTH_TOKEN`（Anthropic互換の第三者エンドポイント向け）フォールバック。
    解決は `main` の `_resolve_auth_env` が担う）を用いる（是正の経緯:
    PLAN-20260725-smoke-full-api-key-auth。認証失敗の実測: 親プラン
    plans/PLAN-20260725-p2-test-harness.md Section 3.5 step 0 で HOME 差し替え
    のみでは "Not logged in" になることを確認済み）。`CLAUDE_CODE_OAUTH_TOKEN` は
    Claude Pro/Max 契約のサブスク枠を消費し追加課金は発生しない（`claude setup-token` で発行）。

    Anthropic互換の第三者エンドポイント（`ANTHROPIC_BASE_URL` を独自のAPIサーバに向け、
    `ANTHROPIC_DEFAULT_SONNET_MODEL` 等でモデルエイリアスを上書きする構成）を使う場合は、
    `PASSTHROUGH_ENV_KEYS` に列挙した環境変数のうち実行環境で設定済みのものだけを
    サブプロセスへ転送する。
    """
    passthrough_env = {k: os.environ[k] for k in PASSTHROUGH_ENV_KEYS if os.environ.get(k)}
    env = {"HOME": str(home), "PATH": os.environ.get("PATH", ""),
           **auth_env, **passthrough_env}
    command = _phase_command(phase, cr, title)
    cmd = ["claude", "-p", "--output-format", "json", "--model", model]
    # single 版シードは母体 `../multi/svc-a`（temp/multi）を参照するため tool アクセスを許可する。
    # 注意: `--add-dir <dirs...>` は可変長。直後にプロンプトを置くとそれもディレクトリとして
    # 飲み込まれ「Input must be provided ...」になる（2026-07-26 実測）。必ず後段に別オプション
    # （--dangerously-skip-permissions）を挟んでからプロンプトを最後の位置引数として渡す。
    multi_dir = Path(workspace).parent / "multi"
    if multi_dir.is_dir():
        cmd += ["--add-dir", str(multi_dir)]
    # 隔離ワークスペース（temp/ws）での throwaway 実行のため権限バイパスで Write を通す。
    cmd += ["--dangerously-skip-permissions", command]
    proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True,
                          text=True, env=env)
    try:
        resp = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        resp = {"_parse_error": True, "_stdout": (proc.stdout or "")[:4000]}
    resp["_phase"] = phase
    resp["_returncode"] = proc.returncode
    # 診断用: 非0 終了 or 空 stdout のとき stderr を残す（空振り原因の切り分け）。
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        resp["_stderr"] = (proc.stderr or "")[:4000]
    return resp


def _invoke_failed(resp: dict) -> bool:
    """claude 応答が失敗（`is_error` / 非0終了 / セッション上限等）かを判定する。

    失敗応答（例: 「You've hit your session limit」）でも成果物は生成されないため、
    ゴールデン書き出し・構造照合・偽失敗判定へ進ませてはならない（偽ゴールデン/偽失敗の防止。
    2026-07-26 C バッチで session limit により露見）。
    """
    if resp.get("is_error") is True:
        return True
    rc = resp.get("_returncode")
    return rc is not None and rc != 0


def _resolve_auth_env() -> dict | None:
    """非対話認証用の環境変数を解決する（CLAUDE_CODE_OAUTH_TOKEN 優先＝Pro/Max契約消費で
    追加課金なし。未設定時は ANTHROPIC_API_KEY＝API従量課金、それも未設定時は
    ANTHROPIC_AUTH_TOKEN＝Anthropic互換の第三者エンドポイント（ANTHROPIC_BASE_URL と組み合わせて
    使うBearerトークン認証）にフォールバック）。"""
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return {"CLAUDE_CODE_OAUTH_TOKEN": os.environ["CLAUDE_CODE_OAUTH_TOKEN"]}
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {"ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"]}
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return {"ANTHROPIC_AUTH_TOKEN": os.environ["ANTHROPIC_AUTH_TOKEN"]}
    return None


# ---------------------------------------------------------------------------
# オーケストレーション（隔離ステージング・モデル注入・工程ランナー。plan 4.1〜4.3）
# ---------------------------------------------------------------------------

def _seed_name(phase: str, variant: str) -> str:
    """工程ラベルと variant を seeds ディレクトリ名へ（resolve_phase と同じ規則）。"""
    label = phase if phase.isdigit() else phase.capitalize()
    return f"phase{label}-{variant}"


def _copy_multi_motherbase(multi_src: Path, dst: Path) -> None:
    """single 版シードの `../multi/svc-*` を同伴コピーする（母体・plan 4.1）。"""
    dst.mkdir(parents=True, exist_ok=True)
    for entry in sorted(Path(multi_src).glob("svc-*")):
        if entry.is_dir():
            shutil.copytree(entry, dst / entry.name)


def stage_workspace(seed_dir, temp, *, repo_root: Path = REPO_ROOT,
                    multi_src: Path = MULTI_SRC, run_setup: bool = True):
    """隔離ステージングを組み立てる（plan 4.1「隔離コピー時の母体解決規則」）。

    固定レイアウト `{temp}/ws`（ワークスペースルート）+ `{temp}/multi`（single のみ母体同伴）
    + `{temp}/home`（setup.sh デプロイ先）。single 版シードの `REPOS: svc-a: ../multi/svc-a`
    を `{temp}/ws` 基準 depth=1 で解決させる。multi 版シードは母体内包のため同伴しない。
    戻り値 `(home, ws)`。実利用者の `~/.claude/` は無改変（HOME を差し替えるため）。
    """
    seed_dir = Path(seed_dir)
    temp = Path(temp)
    ws = temp / "ws"
    home = temp / "home"
    if seed_dir.exists():
        shutil.copytree(seed_dir, ws)
    else:
        # init（phase01）は前工程シード非依存で空ワークスペースから起動する（plan 4.4）。
        ws.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    variant = "multi" if seed_dir.name.endswith("-multi") else "single"
    if variant == "single" and Path(multi_src).exists():
        _copy_multi_motherbase(Path(multi_src), temp / "multi")
    if run_setup:
        # 隔離 HOME にスキル・エージェントをデプロイ（実利用者の ~/.claude/ は触らない）。
        subprocess.run(["bash", str(repo_root / "ClaudeCode" / "setup.sh")],
                       env={"HOME": str(home), "PATH": os.environ.get("PATH", "")},
                       capture_output=True, text=True, check=False)
    return home, ws


def _set_frontmatter_model(text: str, model: str) -> str:
    """frontmatter の `model:` を設定/置換する（frontmatter が無ければ何もしない）。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return text
    block = lines[1:end]
    replaced = False
    for j, line in enumerate(block):
        if re.match(r"^\s*model\s*:", line):
            block[j] = f"model: {model}"
            replaced = True
            break
    if not replaced:
        block.append(f"model: {model}")
    new_lines = ["---", *block, "---", *lines[end + 1:]]
    return "\n".join(new_lines) + ("\n" if text.endswith("\n") else "")


def inject_agent_models(home, model_map: dict) -> list[str]:
    """隔離 HOME 側 agents の frontmatter に `model:` を注入する（plan 4.2）。

    `model_map`: `{agent_stem: model}`（`"*"` で全 agents に一律指定）。空 map は no-op
    （工程全体を単一モデルで回す場合は `_invoke_phase` の `--model` 継承で足りる）。
    母体リポジトリの `agents/*.md` は触らず、`{home}/.claude/agents/*.md` のみ書き換える。
    戻り値は変更した agents ファイル名の一覧。
    """
    if not model_map:
        return []
    agents_dir = Path(home) / ".claude" / "agents"
    if not agents_dir.is_dir():
        return []
    changed: list[str] = []
    for f in sorted(agents_dir.glob("*.md")):
        model = model_map.get(f.stem) or model_map.get("*")
        if not model:
            continue
        text = f.read_text(encoding="utf-8")
        new = _set_frontmatter_model(text, model)
        if new != text:
            f.write_text(new, encoding="utf-8")
            changed.append(f.name)
    return changed


def resolve_artifact_dir(ws, phase: str, cfg: dict | None = None) -> Path:
    """工程 NN の成果物ディレクトリを解決する（plan 4.3「成果物ディレクトリの特定」）。

    cfg の `phase_artifacts[phase]`（B で確定する正準表）を優先し、無ければ
    `DEFAULT_PHASE_ARTIFACT_GLOB` を使う。glob が一致しなければ ws ルートを返す。
    """
    cfg = cfg or {}
    globpat = cfg.get("phase_artifacts", {}).get(phase) or DEFAULT_PHASE_ARTIFACT_GLOB.get(phase)
    if not globpat:
        return Path(ws)
    dirs = [m for m in sorted(Path(ws).glob(globpat)) if m.is_dir()]
    return dirs[0] if dirs else Path(ws)


def resolve_model(phase: str, cfg: dict, override: str | None) -> str:
    """工程別モデルを解決する（`--model` 明示 > cfg models[phase] > 既定 sonnet）。"""
    if override:
        return override
    return cfg.get("models", {}).get(phase) or cfg.get("SMOKE_DEFAULT_MODEL") or "sonnet"


def resolve_effective_budget(mode: str, cfg: dict, cli_budget) -> float:
    """実効予算を解決する（plan 4.4 実効予算ゲート）。

    `--budget`（明示）> `SMOKE_TOKEN_BUDGET`（校正確定値・assert 優先）/
    `SMOKE_CALIBRATE_BUDGET`（校正用・bootstrap 優先）。いずれも 0・未指定なら 0 を返す
    （呼び出し側で exit 6）。LLM を予算上限なしに起動しないための不変条件。
    """
    if cli_budget and float(cli_budget) > 0:
        return float(cli_budget)
    token = float(cfg.get("SMOKE_TOKEN_BUDGET", 0) or 0)
    calib = float(cfg.get("SMOKE_CALIBRATE_BUDGET", 0) or 0)
    if mode == "assert":
        return token if token > 0 else calib
    return calib if calib > 0 else token


def run_phase(phase: str, *, variant: str = "single", model: str = "sonnet",
              budget: BudgetTracker, mode: str = "assert",
              seeds_root: Path = SEEDS_ROOT, golden_dir: Path = GOLDEN_ROOT,
              repo_root: Path = REPO_ROOT, multi_src: Path = MULTI_SRC,
              auth_env: dict | None = None, cfg: dict | None = None,
              est_usd: float = DEFAULT_PHASE_EST_USD, invoke=None,
              debug_dir: Path | None = None) -> dict:
    """1工程を隔離 HOME で起動し、構造性質を照合/収集する（plan 4.3）。

    `mode`:
      - `harvest`: 成果物を生成するのみ（ゴールデン照合も書き込みもしない。B の立ち上げ）。
      - `assert`（既定）: ゴールデン未確定なら停止（status=golden_missing → exit 8。偽赤を作らない）。
        あれば `compare_to_golden` で違反一覧を得る。
      - `update-golden`: 構造性質を `golden/{seed}.json` に書き出す（校正前でも実行可）。
      - `calibrate`: ゴールデンと照合し偽失敗有無・トークンを記録する（書き込まない）。

    予算: `can_start` が False なら起動せず status=budget_skip。`add_response` の超過は
    `BudgetExceeded` を送出し呼び出し側で中断（exit 7）。temp は finally で破棄。
    """
    cfg = cfg or {}
    invoke = invoke or _invoke_phase
    seed_name = _seed_name(phase, variant)
    result = {"phase": phase, "variant": variant, "mode": mode,
              "model": model, "seed": seed_name}

    golden_path = Path(golden_dir) / f"{seed_name}.json"
    # assert/calibrate はゴールデン未確定を起動前に検出し、無駄な消費・偽赤を避ける。
    if mode in ("assert", "calibrate") and not golden_path.exists():
        result["status"] = "golden_missing"
        result["golden_path"] = str(golden_path)
        return result

    if not budget.can_start(est_usd):
        result["status"] = "budget_skip"
        return result

    temp = Path(tempfile.mkdtemp(prefix=f"smoke-{seed_name}-"))
    try:
        seed_dir = Path(seeds_root) / seed_name
        home, ws = stage_workspace(seed_dir, temp, repo_root=repo_root,
                                   multi_src=multi_src)
        inject_agent_models(home, cfg.get("model_map", {}))
        resp = invoke(phase, ws, model, home, auth_env or {})
        if debug_dir is not None:
            Path(debug_dir).mkdir(parents=True, exist_ok=True)
            (Path(debug_dir) / f"{seed_name}.json").write_text(
                json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
        result["cost_usd"] = float(resp.get("total_cost_usd", 0.0) or 0.0)
        budget.add_response(resp)  # 超過なら BudgetExceeded（呼び出し側で exit 7）
        # 起動失敗（is_error/非0/セッション上限）はゴールデン書き出し・照合へ進ませない
        # （成果物が無いのに偽ゴールデン/偽失敗を作らない）。
        if _invoke_failed(resp):
            result["status"] = "invoke_error"
            result["error"] = (str(resp.get("result", "")) or
                               str(resp.get("_stderr", "")))[:200]
            return result
        props = normalize_properties(
            extract_structural_properties(resolve_artifact_dir(ws, phase, cfg)))
        result["properties"] = props

        if mode == "harvest":
            result["status"] = "harvested"
        elif mode == "update-golden":
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            merged = dict(props)
            if golden_path.exists():
                try:
                    prev = json.loads(golden_path.read_text(encoding="utf-8"))
                    # 成果物から再抽出できない手書きキー（required_headings 等）を引き継ぐ。
                    # 抽出できるキーは props の新しい値で上書きする。
                    for key, value in prev.items():
                        merged.setdefault(key, value)
                except (json.JSONDecodeError, OSError) as e:
                    print(f"警告: 既存golden {golden_path} の読み取りに失敗したため手書きキーを"
                          f"引き継がずに全置換します: {e}", file=sys.stderr)
            golden_path.write_text(
                json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            result["status"] = "golden_written"
            result["golden_path"] = str(golden_path)
        else:  # assert / calibrate（golden 存在は上で確認済み）
            golden = json.loads(golden_path.read_text(encoding="utf-8"))
            violations = compare_to_golden(props, golden)
            result["violations"] = violations
            if mode == "calibrate":
                result["status"] = "calibrated"
                result["false_failure"] = bool(violations)
            else:
                result["status"] = "violations" if violations else "ok"
        return result
    finally:
        shutil.rmtree(temp, ignore_errors=True)


# single チェーンの起動順（工程01=init から close まで。工程08は 07 に統合済み）。
HARVEST_SINGLE_CHAIN = ["01", "02", "03", "04", "05", "06", "07", "09", "10", "11", "close"]


def _snapshot_ws(ws, dest) -> None:
    """ワークスペースルート `ws` の中身を `dest` へ複製する（既存 dest は置換）。

    `ws`（`{temp}/ws`）のみを複製し、兄弟の `{temp}/multi`（母体）・`{temp}/home`
    （setup.sh デプロイ先）は含めない＝現行 `stage_workspace` の分離と対称。
    """
    ws = Path(ws)
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ws, dest)


def run_harvest_chain(*, budget: BudgetTracker, model_resolver,
                      auth_env: dict | None = None, cfg: dict | None = None,
                      seeds_out: Path = SEEDS_ROOT, base_config: Path = SINGLE_BASE_CONFIG,
                      repo_root: Path = REPO_ROOT, multi_src: Path = MULTI_SRC,
                      seeds_root: Path = SEEDS_ROOT, invoke=None,
                      est_usd: float = DEFAULT_PHASE_EST_USD,
                      debug_dir: Path | None = None) -> list[dict]:
    """single チェーンを1つの永続 ws で連鎖起動し、各工程入口状態を seeds へ切り出す（plan 5.1）。

    `run_phase`（工程独立・seed から起動・temp 破棄）と異なり、ws を1つだけ作り
    `01→02→…→close` を**同じ ws 上で順に起動**する（前工程の成果物が次工程の入力になる）。
    各工程を起動した**直後（予算計上の前）に** ws を**次工程**の `seeds/phase{NN}-single/` へ
    スナップショット（＝「次工程の直前まで完了した入口状態」。工程01の出力は phase02-single へ入る）。
    予算計上前に切り出すため、`add_response` の超過（`BudgetExceeded`）で temp が破棄されても
    生成済み成果物を失わない。起点 ws には `base_config`（`REPOS: svc-a: ../multi/svc-a`）を置き、
    init に母体解決の効いた CR を新規作成させる。生成物は「生」シードで、人が最小化して確定する。

    予算: `can_start` が False の工程は起動せず status=budget_skip で打ち切り。
    `add_response` の超過は `BudgetExceeded` を送出し呼び出し側で中断（exit 7）。
    戻り値は工程別 result dict の一覧（`_print_report` がそのまま扱える）。temp は finally で破棄。
    """
    cfg = cfg or {}
    invoke = invoke or _invoke_phase
    seeds_out = Path(seeds_out)
    results: list[dict] = []
    temp = Path(tempfile.mkdtemp(prefix="smoke-harvest-chain-"))
    try:
        # 存在しない single seed 名で空 ws を組む（single 名なので母体 multi/ を同伴。plan 4.1）。
        stage_seed = Path(seeds_root) / "phase01-single"
        home, ws = stage_workspace(stage_seed, temp, repo_root=repo_root,
                                   multi_src=multi_src)
        # init が母体解決の効いた CR を作れるよう、起点に config を置く（init は既存 config を尊重）。
        if Path(base_config).exists():
            shutil.copy2(base_config, ws / "xddp.config.md")
        inject_agent_models(home, cfg.get("model_map", {}))
        chain = HARVEST_SINGLE_CHAIN
        for i, phase in enumerate(chain):
            label = phase if phase.isdigit() else phase.capitalize()
            r = {"phase": phase, "variant": "single", "mode": "harvest",
                 "model": model_resolver(phase), "seed": f"phase{label}-single"}
            if not budget.can_start(est_usd):
                r["status"] = "budget_skip"
                results.append(r)
                break
            resp = invoke(phase, ws, r["model"], home, auth_env or {})
            if debug_dir is not None:
                # 生レスポンス（result/is_error/_returncode/_stderr）を保存して空振り原因を切り分ける。
                Path(debug_dir).mkdir(parents=True, exist_ok=True)
                (Path(debug_dir) / f"phase{label}.json").write_text(
                    json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
            r["cost_usd"] = float(resp.get("total_cost_usd", 0.0) or 0.0)
            if _invoke_failed(resp):
                # 起動失敗（セッション上限等）はゴミ seed を作らず連鎖を中断する。
                r["status"] = "invoke_error"
                r["error"] = (str(resp.get("result", "")) or
                              str(resp.get("_stderr", "")))[:200]
                results.append(r)
                budget.add_response(resp)
                break
            # この工程の出力を「次工程の入口状態」として**予算計上の前に**スナップショットする。
            # add_response の超過（BudgetExceeded）で temp が破棄されても生成済み成果物を失わないため。
            if i + 1 < len(chain):
                nxt = chain[i + 1]
                nlabel = nxt if nxt.isdigit() else nxt.capitalize()
                dest = seeds_out / f"phase{nlabel}-single"
                _snapshot_ws(ws, dest)
                r["next_seed_path"] = str(dest)
            r["status"] = "harvested"
            results.append(r)
            budget.add_response(resp)  # 超過なら BudgetExceeded（次工程シードは保存済み）
        return results
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _build_tasks(args) -> list[tuple[str, str]]:
    """--all / --phase から (phase, variant) タスク列を組み立てる（plan 4.4）。"""
    if args.all:
        tasks: list[tuple[str, str]] = [("01", "single")]
        tasks += [(p, "single") for p in PHASE_LABELS]
        # cross 生成が絡む 04/11 は single に加えて multi でも起動する。
        tasks += [(p, "multi") for p in sorted(MULTI_PHASES)]
        return tasks
    return [(args.phase, "multi" if args.multi else "single")]


def _print_report(results: list[dict], budget: BudgetTracker, as_json: bool) -> None:
    """実行工程・累積コスト・違反・偽失敗率を出力する（plan 4.4 レポート・3.4 可観測性）。"""
    snap = budget.snapshot()
    if as_json:
        print(json.dumps({"results": results, "budget": snap},
                         ensure_ascii=False, indent=2))
        return
    for r in results:
        line = f"[{r['seed']}] mode={r['mode']} model={r['model']} -> {r.get('status')}"
        if r.get("cost_usd") is not None:
            line += f" (${r['cost_usd']:.4f})"
        print(line)
        for v in r.get("violations", []) or []:
            print(f"    ✗ {v}")
    calibrated = [r for r in results if r.get("mode") == "calibrate"]
    if calibrated:
        failures = sum(1 for r in calibrated if r.get("false_failure"))
        print(f"偽失敗率: {failures}/{len(calibrated)}")
    print(f"累積コスト: ${snap['total_cost_usd']:.4f} / 上限 ${snap['budget_usd']:.4f}"
          f"（工程数 {snap['phases_run']}）")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="XDDP L4/L5 full-run スモーク（LLM・予算ガード）")
    parser.add_argument("--phase", help=f"単一工程（{'/'.join(PHASE_LABELS)}）")
    parser.add_argument("--all", action="store_true", help="init→close を順に通す")
    parser.add_argument("--multi", action="store_true",
                        help=f"multi 版シードを使う（{sorted(MULTI_PHASES)} のみ）")
    parser.add_argument("--calibrate", action="store_true",
                        help="校正ラン（偽失敗率・トークン実測）")
    parser.add_argument("--model", help="校正時のモデル指定（haiku/sonnet 等）")
    parser.add_argument("--update-golden", action="store_true",
                        help="構造性質を再収集してゴールデンを更新")
    parser.add_argument("--harvest", action="store_true",
                        help="ハーベスト（no-assert。シード起こし・立ち上がり確認。B 専用）")
    parser.add_argument("--budget", type=float, default=None,
                        help="予算上限を明示指定（USD。config 値より優先）")
    parser.add_argument("--harvest-out", type=Path, default=None,
                        help="連鎖ハーベスト（--all --harvest）の seed 出力先（既定 seeds/）")
    parser.add_argument("--harvest-debug", type=Path, default=None,
                        help="連鎖ハーベストの各工程の生レスポンス JSON を保存する診断ディレクトリ")
    parser.add_argument("--json", action="store_true", help="機械可読レポートを出力")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.all and not args.phase:
        print("❌ --all か --phase NN を指定してください。", file=sys.stderr)
        return 2

    # --phase 解決の検証（LLM 非依存・ここまではトークン0。exit 2）
    if args.phase:
        try:
            resolve_phase(args.phase, args.multi)
        except ValueError as e:
            print(f"❌ {e}", file=sys.stderr)
            return 2

    # claude 導入（exit 3）
    if not claude_available():
        print("❌ full-run スモークは `claude` CLI を必要とします（未導入/認証未了）。\n"
              "   `make test`（L1〜L3・0トークン）は影響を受けません。", file=sys.stderr)
        return 3

    # 認証（exit 5）
    auth_env = _resolve_auth_env()
    if auth_env is None:
        print("❌ full-run スモークは隔離 HOME 実行のため非対話認証の環境変数が必須です\n"
              "   （隔離 HOME では OAuth セッションを引き継げないため。親プラン 3.5 step 0 実測で確認済み）。\n"
              "   Pro/Max契約なら追加課金なしの CLAUDE_CODE_OAUTH_TOKEN（`claude setup-token` で発行）を、\n"
              "   なければ ANTHROPIC_API_KEY（API従量課金）を設定してください。\n"
              "   Anthropic互換の第三者エンドポイント（ANTHROPIC_BASE_URL）を使う場合は\n"
              "   ANTHROPIC_AUTH_TOKEN を設定してください（ANTHROPIC_DEFAULT_SONNET_MODEL 等の\n"
              "   モデルエイリアス上書きも ANTHROPIC_BASE_URL とあわせて自動転送されます）。\n"
              "   `make test`（L1〜L3・0トークン）は影響を受けません。", file=sys.stderr)
        return 5

    cfg = load_smoke_config(SMOKE_CONFIG_PATH)

    if args.calibrate:
        mode = "calibrate"
    elif args.update_golden:
        mode = "update-golden"
    elif args.harvest:
        mode = "harvest"
    else:
        mode = "assert"

    # 実効予算ゲート（exit 6）: LLM を予算上限なしに起動しない不変条件。
    effective_budget = resolve_effective_budget(mode, cfg, args.budget)
    if effective_budget <= 0:
        print("❌ 実効予算が未供給です（LLM を予算上限なしに起動しません）。\n"
              "   校正済みなら smoke_config.md の SMOKE_TOKEN_BUDGET を、\n"
              "   ブートストラップ（B: --harvest／--update-golden／--calibrate）なら\n"
              "   smoke_config.md の SMOKE_CALIBRATE_BUDGET か CLI --budget を与えてください。\n"
              "   校正手順は B（--harvest でシード）→ C（--update-golden でゴールデン）→\n"
              "   D（--calibrate で偽失敗率・SMOKE_TOKEN_BUDGET 確定）の順。", file=sys.stderr)
        return 6

    budget = BudgetTracker(effective_budget, max_phases=cfg.get("SMOKE_MAX_PHASES"))

    results: list[dict] = []
    exit_code = 0
    try:
        # --all --harvest は連鎖ハーベスト（single チェーンを1 ws で通し seed を切り出す。plan 5.1）。
        if args.all and mode == "harvest":
            results = run_harvest_chain(
                budget=budget,
                model_resolver=lambda p: resolve_model(p, cfg, args.model),
                auth_env=auth_env, cfg=cfg,
                seeds_out=(args.harvest_out or SEEDS_ROOT),
                debug_dir=args.harvest_debug)
            for r in results:
                if r.get("status") == "budget_skip":
                    print(f"⚠️ [{r['seed']}] 残予算不足で以降を中断します。", file=sys.stderr)
                    break
                if r.get("status") == "invoke_error":
                    print(f"❌ [{r['seed']}] スキル起動が失敗（{r.get('error')}）。"
                          "連鎖を中断しました。", file=sys.stderr)
                    exit_code = 9
                    break
            _print_report(results, budget, args.json)
            return exit_code
        for phase, variant in _build_tasks(args):
            r = run_phase(phase, variant=variant,
                          model=resolve_model(phase, cfg, args.model),
                          budget=budget, mode=mode, auth_env=auth_env, cfg=cfg,
                          debug_dir=args.harvest_debug)
            results.append(r)
            if r["status"] == "golden_missing":
                print(f"❌ [{r['seed']}] ゴールデン未確定（{r.get('golden_path')}）。\n"
                      "   assert の前に `--update-golden`（C）で確定してください。\n"
                      "   B のシード起こしは `--harvest`（no-assert）を使います。",
                      file=sys.stderr)
                exit_code = 8
                break
            if r["status"] == "budget_skip":
                print(f"⚠️ [{r['seed']}] 残予算不足で以降を中断します。", file=sys.stderr)
                break
            if r["status"] == "invoke_error":
                print(f"❌ [{r['seed']}] スキル起動が失敗しました（{r.get('error')}）。\n"
                      "   セッション上限・認証・レート制限等を確認してください"
                      "（ゴールデンは書き込んでいません）。", file=sys.stderr)
                exit_code = 9
                break
            if r["status"] == "violations":
                exit_code = 1
    except BudgetExceeded as e:
        print(f"❌ 予算超過で中断: {e}", file=sys.stderr)
        exit_code = 7

    _print_report(results, budget, args.json)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
