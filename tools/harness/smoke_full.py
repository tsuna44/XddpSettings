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
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

# --phase が受理する工程ラベル（plan 3.3「PHASE の受理値」）。
# 工程08は xddp.07 に統合、工程01は --all 専用のため --phase 対象外。
PHASE_LABELS = ["02", "03", "04", "05", "06", "07", "09", "10", "11", "close"]
# multi 版シードを持つ工程（cross 生成が絡む）。他工程での --multi 指定はエラー。
MULTI_PHASES = {"04", "05", "06", "11"}
# quick 版シードを持つ工程（CR_PROFILE: quick で成果物の構造が変わる工程のみ。
# 03 は quick で工程2に統合され実行されないためシード対象外。07/09/10/11/close は
# quick でも成果物構造がほぼ同一のためシード非対応）。他工程での --profile quick はエラー。
QUICK_PHASES = {"02", "04", "05", "06"}

# Anthropic互換の第三者エンドポイント利用時に `claude` CLI へ素通しする環境変数
# （ANTHROPIC_BASE_URL と組み合わせて使うモデルエイリアス上書き。未設定のキーは転送しない）。
PASSTHROUGH_ENV_KEYS = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
)

# `--model` に渡すエイリアス → 上書き先モデルIDを持つ環境変数。実モデル（effective model）の
# 解決に使う（ゴールデンのプロファイル分離・レポート表示用）。
MODEL_ALIAS_ENV_KEYS = {
    "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
}

# 認証環境変数の探索順。ANTHROPIC_BASE_URL が設定されている（＝第三者エンドポイントへ向ける）
# 場合は CLAUDE_CODE_OAUTH_TOKEN を**候補から外す**（Anthropic サブスクの資格情報を第三者の
# エンドポイントへ送らないため。加えて第三者側では OAuth トークンは認証に使えない）。
ANTHROPIC_AUTH_ORDER = (
    "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
THIRD_PARTY_AUTH_ORDER = ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY")

# ゴールデンを第三者プロバイダ別に分離するサブディレクトリ（seed 名と衝突しない固定名）。
GOLDEN_PROVIDERS_SUBDIR = "providers"

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

# artifact_lint（決定的な CRS 構造チェック。setup.sh のデプロイ対象）を直接 import する
# （`ClaudeCode/.claude/skills/xddp.common/scripts/tests/test_artifact_lint.py` と同じ bare-import
# 慣行。tools/harness は開発時メタツールでデプロイ対象外だが、既存の決定的チェックを
# smoke_full.py に重複実装しないためここでのみ依存する。8論点1参照）。
sys.path.insert(0, str(REPO_ROOT / "ClaudeCode" / ".claude" / "skills" / "xddp.common" / "scripts"))
import artifact_lint  # noqa: E402

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


# 応答 JSON から拾うトークン種別（`usage` 直下。欠落は 0 として扱う）。
USAGE_TOKEN_KEYS = ("input_tokens", "output_tokens",
                    "cache_creation_input_tokens", "cache_read_input_tokens")
# 応答 JSON から拾う付随計測値（存在するときだけ記録する）。
USAGE_EXTRA_KEYS = ("duration_ms", "duration_api_ms", "num_turns")


def extract_usage(resp: dict) -> dict:
    """`claude -p --output-format json` の応答から計測値を取り出す。

    第三者エンドポイントは `usage`／`total_cost_usd` を返さない場合があるため、欠落は 0 と
    して扱い `reported` フラグで「エンドポイントが計測値を返したか」を区別する
    （予算ガードを外しても計測だけは残す・その計測が空振りしたことも記録する）。
    """
    usage = resp.get("usage") or {}
    out = {k: int(usage.get(k, 0) or 0) for k in USAGE_TOKEN_KEYS}
    out["total_tokens"] = sum(out[k] for k in USAGE_TOKEN_KEYS)
    out["cost_usd"] = float(resp.get("total_cost_usd", 0.0) or 0.0)
    for k in USAGE_EXTRA_KEYS:
        if resp.get(k) is not None:
            out[k] = resp[k]
    out["reported"] = bool(out["total_tokens"] or out["cost_usd"])
    return out


class BudgetTracker:
    """各工程起動の usage/total_cost_usd を積算し、上限超過で中断させる。

    plan 3.2 実行モデル step 3・3.4「予算ガードの二重化」。
    サブエージェント消費が親 usage に積算されるか（3.5 step 0 ③）は要スパイク確認。
    積算されない場合は add_response のトークン加算方式をここで是正する。

    `budget_usd=None` は**上限なし（計測のみ）**を表す。第三者エンドポイント経由では
    Anthropic の USD 単価に基づく上限が意味を持たないため、ガードは外して積算だけ行う
    （暴走防止は `max_phases`＝`SMOKE_MAX_PHASES` が担う）。
    """

    def __init__(self, budget_usd: float | None, max_phases: int | None = None):
        self.budget_usd = budget_usd  # None = 上限なし（計測のみ）
        self.max_phases = max_phases
        self.total_cost_usd = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0
        self.phases_run = 0
        # エンドポイントが usage/コストを返さなかった工程数（計測の空振りを可視化する）。
        self.unreported_phases = 0
        self.history: list[dict] = []

    @property
    def unlimited(self) -> bool:
        return self.budget_usd is None

    def can_start(self, estimated_usd: float) -> bool:
        """工程開始前チェック: 残予算 < 想定単価 なら False（起動しない）。

        上限なし（`budget_usd is None`）のときは工程数上限のみで判定する。
        """
        if self.max_phases is not None and self.phases_run >= self.max_phases:
            return False
        if self.budget_usd is None:
            return True
        return (self.budget_usd - self.total_cost_usd) >= estimated_usd

    def add_response(self, resp: dict) -> None:
        """claude -p の応答 JSON から usage/コストを積算し、超過なら例外。

        上限なし（`budget_usd is None`）のときは積算のみ行い例外を送出しない。
        """
        u = extract_usage(resp)
        self.input_tokens += u["input_tokens"]
        self.output_tokens += u["output_tokens"]
        self.cache_creation_input_tokens += u["cache_creation_input_tokens"]
        self.cache_read_input_tokens += u["cache_read_input_tokens"]
        self.total_cost_usd += u["cost_usd"]
        self.phases_run += 1
        if not u["reported"]:
            self.unreported_phases += 1
        self.history.append({
            "phase": resp.get("_phase"),
            **u,
            "cumulative_usd": self.total_cost_usd,
        })
        if self.budget_usd is not None and self.total_cost_usd > self.budget_usd:
            raise BudgetExceeded(
                f"累積 ${self.total_cost_usd:.4f} が上限 ${self.budget_usd:.4f} を超過")

    def snapshot(self) -> dict:
        return {
            "total_cost_usd": round(self.total_cost_usd, 6),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "total_tokens": (self.input_tokens + self.output_tokens
                             + self.cache_creation_input_tokens
                             + self.cache_read_input_tokens),
            "phases_run": self.phases_run,
            "unreported_phases": self.unreported_phases,
            "budget_usd": self.budget_usd,   # None = 上限なし（計測のみ）
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
# golden required_headings ⊆ テンプレート H2 見出し の突合検証（純ロジック・テスト対象。plan 3.2）
# ---------------------------------------------------------------------------

# H2 見出しのみを対象とする（H3 以下は要求件数等で可変なため対象外。3.2 手順1）。
H2_HEADING_RE = re.compile(r"^##\s+(.*\S)\s*$")

# 工程 → 主テンプレートパス（`ClaudeCode/.claude/skills/` からの相対パス）。
# 05/06/11 は1工程に複数テンプレートがあり主従の切り分けが自明ではないため対象外とする（8論点4）。
PHASE_TEMPLATE_MAP = {
    "02": "xddp.02.analysis/templates/02_req-analysis-memo-template.md",
    "03": "xddp.03.req/templates/03_change-req-spec-template.md",
    "09": "xddp.09.test/templates/09_test-specification-template.md",
    "10": "xddp.10.test-run/templates/10_test-results-template.md",
}


def extract_template_headings(template_path: Path) -> list[str]:
    """テンプレート .md の H2 見出し（"## " 始まり）のみを抽出する（3.2 手順1）。"""
    headings = []
    for line in Path(template_path).read_text(encoding="utf-8").splitlines():
        m = H2_HEADING_RE.match(line)
        if m:
            headings.append(m.group(1))
    return headings


def verify_golden_required_headings(phase: str, *, golden_dir: Path = GOLDEN_ROOT,
                                     repo_root: Path = REPO_ROOT) -> list[str]:
    """golden の required_headings がテンプレート H2 見出しの部分集合であることを検査する（3.2 手順3）。

    `make test`（L1〜L3相当・0トークン）の回帰対象。`PHASE_TEMPLATE_MAP` に無い工程、
    golden ファイルが存在しない工程、golden に `required_headings` キーが無い（未設定の）工程は
    検査をスキップし空リストを返す（3.5「未設定なら検査をスキップする」前提）。single variant の
    golden のみを対象とする。
    """
    template_rel = PHASE_TEMPLATE_MAP.get(phase)
    if not template_rel:
        return []
    golden_path = Path(golden_dir) / f"phase{phase}-single.json"
    if not golden_path.exists():
        return []
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    required = golden.get("required_headings")
    if not required:
        return []
    template_path = (Path(repo_root) / "ClaudeCode" / ".claude" / "skills" / template_rel)
    template_headings = set(extract_template_headings(template_path))
    orphans = sorted(set(required) - template_headings)
    if orphans:
        return [f"phase{phase}: golden required_headings がテンプレートに存在しない見出しを含む: "
                f"{orphans}"]
    return []


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


def resolve_phase(phase: str, multi: bool, profile: str = "full") -> str:
    """--phase / --multi / --profile を seeds ディレクトリ名へ解決する（plan 3.2 解決規則）。"""
    if phase not in PHASE_LABELS:
        raise ValueError(
            f"未定義の PHASE '{phase}'。受理値: {PHASE_LABELS}（工程01は --all 専用）")
    if multi and phase not in MULTI_PHASES:
        raise ValueError(
            f"--multi は {sorted(MULTI_PHASES)} のみ受理（cross 生成が絡む工程）")
    if profile not in ("full", "quick"):
        raise ValueError(f"未定義の --profile '{profile}'（full/quick のみ受理）")
    if profile == "quick" and phase not in QUICK_PHASES:
        raise ValueError(
            f"--profile quick は {sorted(QUICK_PHASES)} のみ受理"
            "（quick で成果物構造が変わる工程のみシードを用意している）")
    variant = "multi" if multi else "single"
    if profile == "quick":
        variant += "-quick"
    # 数値工程はそのまま、非数値ラベル（close）はシード名に合わせて先頭大文字化
    label = phase if phase.isdigit() else phase.capitalize()
    return f"phase{label}-{variant}"


# ---------------------------------------------------------------------------
# LLM 起動経路（要スパイク確認。既定では claude 未導入を検出して停止）
# ---------------------------------------------------------------------------

def claude_available() -> bool:
    return shutil.which("claude") is not None


# ---------------------------------------------------------------------------
# プロバイダ解決（第三者 Anthropic 互換エンドポイント。純ロジック・テスト対象）
# ---------------------------------------------------------------------------

# `ANTHROPIC_BASE_URL` に誤って完全な messages エンドポイントを設定した場合の末尾。
# `claude` CLI はベースURLに `/v1/messages` を連結するため、そのまま渡すと二重連結になる。
# 末尾 `/v1` 単独は剥がさない（CLI の連結規則を実測確認していないため。`/v1` を含む
# マウントポイントを正当に使う構成を壊さないよう保守側に倒す）。
_BASE_URL_ENDPOINT_SUFFIX_RE = re.compile(r"/v1/messages/*$")
_SLUG_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def normalize_base_url(url: str | None) -> str:
    """`ANTHROPIC_BASE_URL` を CLI が期待するベースURL形へ正規化する。

    末尾の `/v1/messages`（＝完全な messages エンドポイントの貼り付け）と余分な末尾
    スラッシュを取り除く。空/未設定はそのまま空文字を返す。
    """
    u = (url or "").strip()
    if not u:
        return ""
    return _BASE_URL_ENDPOINT_SUFFIX_RE.sub("", u).rstrip("/")


def resolve_effective_model(model: str, env: dict | None = None) -> str:
    """`--model` のエイリアスを実モデルIDへ解決する（未上書きならエイリアスのまま）。

    `sonnet`/`opus`/`haiku` は `ANTHROPIC_DEFAULT_*_MODEL` で上書きされうるため、
    ゴールデンのプロファイル分離とレポート表示では解決後の実モデルIDを使う。
    """
    env = os.environ if env is None else env
    key = MODEL_ALIAS_ENV_KEYS.get((model or "").strip().lower())
    if key and env.get(key):
        return env[key]
    return model


def _slug(text: str) -> str:
    """ディレクトリ名に使える安全な slug へ（英数 `.` `_` `-` 以外は `-` へ畳む）。"""
    s = _SLUG_UNSAFE_RE.sub("-", (text or "").strip()).strip("-.")
    return s or "unknown"


def provider_slug(base_url: str, model: str, env: dict | None = None) -> str:
    """第三者エンドポイント＋実モデルの組をゴールデン分離用の slug にする。"""
    host = urlsplit(normalize_base_url(base_url)).hostname or "unknown-host"
    return f"{_slug(host)}__{_slug(resolve_effective_model(model, env))}"


def resolve_golden_dir(golden_root, model: str, env: dict | None = None) -> Path:
    """ゴールデンの配置先を解決する（第三者エンドポイント利用時のみプロファイル分離）。

    `ANTHROPIC_BASE_URL` 未設定（Anthropic 公式）は従来どおり `golden/{seed}.json` の平坦配置。
    設定時は `golden/providers/{host}__{実モデル}/{seed}.json` へ分離し、Sonnet で校正済みの
    ゴールデンを別モデルの `--update-golden` が上書き破壊しないようにする。
    """
    env = os.environ if env is None else env
    base = (env.get("ANTHROPIC_BASE_URL") or "").strip()
    if not base:
        return Path(golden_root)
    return Path(golden_root) / GOLDEN_PROVIDERS_SUBDIR / provider_slug(base, model, env)


def describe_provider(auth_env: dict | None = None, env: dict | None = None) -> dict:
    """実行に使うエンドポイント・認証変数を要約する（値は含めない。レポート/診断用）。"""
    env = os.environ if env is None else env
    base = normalize_base_url(env.get("ANTHROPIC_BASE_URL"))
    return {
        "endpoint": base or "anthropic-default",
        "third_party": bool(base),
        "auth_var": next(iter(auth_env or {}), None),
    }


def _phase_command(phase: str, cr: str, title: str) -> str:
    """工程ラベルを実スラッシュコマンド文字列（引数込み）へ（PHASE_COMMANDS 正準表）。

    init（01）のみ CR番号＋タイトルを取り、他工程は CR番号のみを取る（各スキルの CR Resolution）。
    未登録ラベルは従来の `/xddp.{phase}` へフォールバック（回帰時に気付けるよう残す）。
    """
    cmd = PHASE_COMMANDS.get(phase, f"/xddp.{phase}")
    if phase == "01":
        return f"{cmd} {cr} {title}"
    return f"{cmd} {cr}"


def _build_claude_env(home: Path, auth_env: dict) -> dict:
    """claude 起動用の環境変数を組み立てる（`_invoke_phase`/`_resume_phase` 共通）。

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
    if "ANTHROPIC_BASE_URL" in passthrough_env:
        raw = passthrough_env["ANTHROPIC_BASE_URL"]
        normalized = normalize_base_url(raw)
        if normalized != raw:
            print(f"⚠️ ANTHROPIC_BASE_URL を正規化しました: {raw} → {normalized}\n"
                  "   （CLI がベースURLに /v1/messages を連結するため、"
                  "完全なエンドポイントURLは二重連結になります）", file=sys.stderr)
        passthrough_env["ANTHROPIC_BASE_URL"] = normalized
    return {"HOME": str(home), "PATH": os.environ.get("PATH", ""),
            **auth_env, **passthrough_env}


def _run_claude(cmd: list[str], workspace: Path, phase: str, env: dict) -> dict:
    """claude サブプロセスを起動し、応答 JSON をパースして診断キーを付与する
    （`_invoke_phase`/`_resume_phase` 共通。コマンド列の可変部分は呼び出し側が組み立てる）。
    """
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


def _invoke_phase(phase: str, workspace: Path, model: str,
                  home: Path, auth_env: dict, *,
                  cr: str = HARVEST_CR, title: str = HARVEST_TITLE) -> dict:
    """1工程をヘッドレスで起動し応答 JSON を返す（plan 3.2 実行モデル step 2）。

    ※ スラッシュコマンド起動可否・usage 積算範囲は 3.5 step 0 スパイクで確認済み。
    unittest では本関数をモック応答へ差し替えて 0 トークンで検証する（実 LLM は起動しない）。
    """
    env = _build_claude_env(home, auth_env)
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
    return _run_claude(cmd, workspace, phase, env)


# xddp.04.specout/SKILL.md「## Step 0.5 (confirmation gate): Present scope to user」の
# 確認文言と完全一致させる（行番号ではなく見出し名で参照する。CLAUDE.md「相互参照のルール」と
# 同じ理由＝行番号は編集のたびにずれ、参照が追従しなくなる）。乖離した場合は検出が効かなく
# なるだけで誤判定にはならない（fail-safe。旧来どおり golden_missing 相当の "violations" 扱い）。
GATE_MARKER = "よろしければ「OK」と入力してください"


def _is_specout_gate_stop(resp: dict) -> bool:
    """応答が specout Step 0.5 の確認ゲートで停止したものかを判定する（phase 04 専用）。"""
    if resp.get("stop_reason") != "end_turn":
        return False
    return GATE_MARKER in str(resp.get("result", ""))


def _resume_phase(session_id: str, workspace: Path, model: str, phase: str,
                   home: Path, auth_env: dict) -> dict:
    """Step 0.5 確認ゲートで停止したセッションを "OK" で1回だけ再開する（`run_phase` 専用）。

    single バリアントの seed は母体 `../multi/svc-a` を参照するため、`_invoke_phase` と
    同じ `--add-dir` 判定を再掲する（`--resume` がディレクトリ許可スコープをセッションから
    引き継ぐ保証はドキュメント上確認できないため、fail-safe として明示的に付与し直す設計判断）。
    """
    env = _build_claude_env(home, auth_env)
    cmd = ["claude", "-p", "--output-format", "json", "--model", model,
           "--resume", session_id]
    multi_dir = Path(workspace).parent / "multi"
    if multi_dir.is_dir():
        cmd += ["--add-dir", str(multi_dir)]
    cmd += ["--dangerously-skip-permissions", "OK"]
    return _run_claude(cmd, workspace, phase, env)


def _merge_usage(a: dict, b: dict) -> dict:
    """`extract_usage` が返す2つの計測辞書を合算する（resume の2回呼び出し分専用）。

    - `USAGE_TOKEN_KEYS` の各キーと `total_tokens`／`cost_usd`: 単純加算する。
    - `reported`（bool）: 加算せず OR（どちらか一方でも報告があれば True）。
    - `USAGE_EXTRA_KEYS`（duration_ms/duration_api_ms/num_turns。存在するときだけ記録される
      計測値）: 両方に存在すれば加算、片方にしか存在しなければ存在する側の値をそのまま採用する
      （欠落側を 0 として扱うと実測値を薄めてしまうため）。
    """
    out = {k: a.get(k, 0) + b.get(k, 0) for k in USAGE_TOKEN_KEYS}
    out["total_tokens"] = sum(out[k] for k in USAGE_TOKEN_KEYS)
    out["cost_usd"] = a.get("cost_usd", 0.0) + b.get("cost_usd", 0.0)
    out["reported"] = bool(a.get("reported")) or bool(b.get("reported"))
    for k in USAGE_EXTRA_KEYS:
        if k in a and k in b:
            out[k] = a[k] + b[k]
        elif k in a:
            out[k] = a[k]
        elif k in b:
            out[k] = b[k]
    return out


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


def _resolve_auth_env(env: dict | None = None) -> dict | None:
    """非対話認証用の環境変数を解決する（送信先に応じて探索順を切り替える）。

    - `ANTHROPIC_BASE_URL` **未設定**（Anthropic 公式）: `ANTHROPIC_AUTH_ORDER` ＝
      `CLAUDE_CODE_OAUTH_TOKEN` 優先（Pro/Max契約消費で追加課金なし）→ `ANTHROPIC_API_KEY`
      （API従量課金）→ `ANTHROPIC_AUTH_TOKEN`。
    - `ANTHROPIC_BASE_URL` **設定済み**（Anthropic互換の第三者エンドポイント）:
      `THIRD_PARTY_AUTH_ORDER` ＝ `ANTHROPIC_AUTH_TOKEN` → `ANTHROPIC_API_KEY`。
      `CLAUDE_CODE_OAUTH_TOKEN` は**候補から外す**（Anthropic サブスクの資格情報を第三者の
      エンドポイントへ送らないため。普段 OAuth トークンを export している環境で
      第三者エンドポイントを指定すると、旧実装では OAuth が優先され誤送信していた）。
    """
    env = os.environ if env is None else env
    order = (THIRD_PARTY_AUTH_ORDER if (env.get("ANTHROPIC_BASE_URL") or "").strip()
             else ANTHROPIC_AUTH_ORDER)
    for key in order:
        if env.get(key):
            return {key: env[key]}
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


DOCS_DIR_CONFIG_RE = re.compile(r"^DOCS_DIR:\s*(\S+)\s*$", re.MULTILINE)


def _read_docs_dir_from_config(ws, docs_dir_default: str = "baseline_docs") -> str:
    """ワークスペースルートの `xddp.config.md` から `DOCS_DIR:` を読む（見つからなければ既定値）。

    パース対象のフェンスドコードブロック形式（``` \\n DOCS_DIR: value \\n ``` ）は
    `ClaudeCode/.claude/skills/xddp.common/SKILL.md`「## Load Config」の
    `DOCS_DIR`（default: `baseline_docs`）解決仕様と同じ入力を読む。本スクリプトは
    `tools/harness/`（開発時メタツール・デプロイ対象外）側の独立実装であり、CLAUDE.md
    「決定的処理はスクリプト」節が対象とするスキル本体側の重複回避方針とは別管理でよい。
    """
    cfg_path = Path(ws) / "xddp.config.md"
    if not cfg_path.exists():
        return docs_dir_default
    m = DOCS_DIR_CONFIG_RE.search(cfg_path.read_text(encoding="utf-8"))
    return m.group(1) if m else docs_dir_default


XDDP_DIR_CONFIG_RE = re.compile(r"^XDDP_DIR:\s*(\S+)\s*$", re.MULTILINE)


def _read_xddp_dir_from_config(ws, xddp_dir_default: str = "xddp") -> str:
    """ワークスペースルートの `xddp.config.md` から `XDDP_DIR:` を読む（見つからなければ既定値）。

    `_read_docs_dir_from_config()` と同一パターン（`DOCS_DIR:` → `XDDP_DIR:`）。
    未設定時のフォールバック値 `"xddp"` は `DEFAULT_PHASE_ARTIFACT_GLOB` のリテラル既定値と揃える。
    """
    cfg_path = Path(ws) / "xddp.config.md"
    if not cfg_path.exists():
        return xddp_dir_default
    m = XDDP_DIR_CONFIG_RE.search(cfg_path.read_text(encoding="utf-8"))
    return m.group(1) if m else xddp_dir_default


# CRS を生成・更新する工程のみ CRS 構造チェック対象とする（plan Section 3.1）。
CRS_LINT_PHASES = {"03", "04", "06"}


def lint_crs_if_present(ws, phase: str) -> list[str]:
    """CRS 構造チェック（`artifact_lint._lint_crs()` の error issue）を違反文字列にして返す（3.1(a)）。

    CRS の実体パスは `{XDDP_DIR}/CR-*/03_change-requirements/CRS-*.md`。`resolve_artifact_dir()`
    は工程別ディレクトリの glob のみを返しファイル名パターンは解決しないため、ここで別途解決する。
    phase03/04/06（`CRS_LINT_PHASES`）以外の工程、または CRS ファイルが存在しない場合は
    常に空リストを返す（no-op）。warning level issue は advisory 扱いのため対象外とする（8論点2）。
    """
    if phase not in CRS_LINT_PHASES:
        return []
    xddp_dir = _read_xddp_dir_from_config(ws)
    matches = sorted(Path(ws).glob(f"{xddp_dir}/CR-*/03_change-requirements/CRS-*.md"))
    if not matches:
        return []
    result = artifact_lint.lint_file(matches[0], "CRS")
    issues = result.get("crs", {}).get("issues", [])
    return [f"CRS構造違反[{i['check']}]: {i['message']}"
            for i in issues if i.get("level") == "error"]


def resolve_artifact_dir(ws, phase: str, cfg: dict | None = None) -> Path:
    """工程 NN の成果物ディレクトリを解決する（plan 4.3「成果物ディレクトリの特定」）。

    cfg の `phase_artifacts[phase]`（B で確定する正準表）を優先し、無ければ
    `DEFAULT_PHASE_ARTIFACT_GLOB` を使う。glob が一致しなければ ws ルートを返す。

    close フェーズのみ特別扱いする: 成果物の実出力は CR ディレクトリではなく
    `{WORKSPACE_ROOT}/{DOCS_DIR}`（既定 `baseline_docs`）であるため、`cfg` に明示的な
    上書き（`phase_artifacts.close`）が無い限り `DOCS_DIR` を解決して返す
    （優先順位: cfg 上書き > close 専用 DOCS_DIR 解決 > `DEFAULT_PHASE_ARTIFACT_GLOB`。
    promote.py 化により baseline_docs 側の出力が決定的になったことが前提。
    PLAN-20260829-close-promote-script-and-smoke Stage 2）。
    """
    cfg = cfg or {}
    cfg_override = cfg.get("phase_artifacts", {}).get(phase)
    if phase == "close" and not cfg_override:
        docs_dir = _read_docs_dir_from_config(ws)
        docs_path = Path(ws) / docs_dir
        return docs_path if docs_path.is_dir() else Path(ws)
    globpat = cfg_override or DEFAULT_PHASE_ARTIFACT_GLOB.get(phase)
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
        result["usage"] = extract_usage(resp)          # 計測（トークン・所要時間・報告有無）
        result["cost_usd"] = result["usage"]["cost_usd"]
        budget.add_response(resp)  # 超過なら BudgetExceeded（呼び出し側で exit 7）
        # phase 04 の Step 0.5 確認ゲート停止を検出したら "OK" で1回だけ resume する。
        # 上の budget.add_response(resp) で1回目分の計上は完了済み。resume は独立した
        # 2回目の起動として budget に追加計上する。result["usage"]/["cost_usd"] は
        # 両呼び出しの合算値に更新する。
        if (phase == "04" and not _invoke_failed(resp)
                and _is_specout_gate_stop(resp)):
            resume_resp = _resume_phase(resp.get("session_id", ""), ws, model, phase,
                                         home, auth_env or {})
            if debug_dir is not None:
                (Path(debug_dir) / f"{seed_name}-resume.json").write_text(
                    json.dumps(resume_resp, ensure_ascii=False, indent=2),
                    encoding="utf-8")
            result["usage"] = _merge_usage(result["usage"], extract_usage(resume_resp))
            result["cost_usd"] = result["usage"]["cost_usd"]
            budget.add_response(resume_resp)  # 2回目分を追加計上（超過なら BudgetExceeded）
            resp = resume_resp  # 以降の失敗判定・プロパティ抽出は resume 後の状態を正とする
        # 起動失敗（is_error/非0/セッション上限）はゴールデン書き出し・照合へ進ませない
        # （成果物が無いのに偽ゴールデン/偽失敗を作らない。resume 後の失敗もここで検出する）。
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
            violations += lint_crs_if_present(ws, phase)
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
            r["usage"] = extract_usage(resp)           # 計測（トークン・所要時間・報告有無）
            r["cost_usd"] = r["usage"]["cost_usd"]
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
    """--all / --phase から (phase, variant) タスク列を組み立てる（plan 4.4）。

    `--profile quick` は `--phase` 単体指定のみ対応（`--all` は未対応。main() で事前に exit 2）。
    """
    if args.all:
        tasks: list[tuple[str, str]] = [("01", "single")]
        tasks += [(p, "single") for p in PHASE_LABELS]
        # cross 生成が絡む 04/11 は single に加えて multi でも起動する。
        tasks += [(p, "multi") for p in sorted(MULTI_PHASES)]
        return tasks
    variant = "multi" if args.multi else "single"
    if getattr(args, "profile", "full") == "quick":
        variant += "-quick"
    return [(args.phase, variant)]


def _print_report(results: list[dict], budget: BudgetTracker, as_json: bool,
                  provider: dict | None = None) -> None:
    """実行工程・累積コスト・違反・偽失敗率を出力する（plan 4.4 レポート・3.4 可観測性）。

    `provider`（`describe_provider` の戻り）を渡すと、どのエンドポイント・どの認証変数で
    走ったかを先頭に出力する。第三者エンドポイント経由の `violations` を「異常」と
    「モデル差分」に切り分けるために必要な情報（G6）。
    """
    snap = budget.snapshot()
    if as_json:
        payload = {"results": results, "budget": snap}
        if provider:
            payload["provider"] = provider
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if provider:
        print(f"プロバイダ: endpoint={provider['endpoint']} "
              f"auth={provider.get('auth_var')}"
              + ("  ※第三者エンドポイント（ゴールデンはプロファイル別）"
                 if provider.get("third_party") else ""))
    for r in results:
        model_disp = r["model"]
        if r.get("effective_model") and r["effective_model"] != r["model"]:
            model_disp = f"{r['model']}→{r['effective_model']}"
        line = f"[{r['seed']}] mode={r['mode']} model={model_disp} -> {r.get('status')}"
        if r.get("cost_usd") is not None:
            line += f" (${r['cost_usd']:.4f})"
        u = r.get("usage")
        if u:
            line += (f" in={u['input_tokens']} out={u['output_tokens']}"
                     f" cache_r={u['cache_read_input_tokens']}"
                     f" cache_w={u['cache_creation_input_tokens']}")
            if u.get("duration_ms") is not None:
                line += f" {u['duration_ms'] / 1000:.1f}s"
            if not u["reported"]:
                line += "  ※エンドポイントが usage/コストを返しませんでした"
        print(line)
        for v in r.get("violations", []) or []:
            print(f"    ✗ {v}")
    calibrated = [r for r in results if r.get("mode") == "calibrate"]
    if calibrated:
        failures = sum(1 for r in calibrated if r.get("false_failure"))
        print(f"偽失敗率: {failures}/{len(calibrated)}")
    limit_disp = ("上限なし（計測のみ）" if snap["budget_usd"] is None
                  else f"上限 ${snap['budget_usd']:.4f}")
    print(f"累積コスト: ${snap['total_cost_usd']:.4f} / {limit_disp}"
          f"（工程数 {snap['phases_run']}）")
    print(f"累積トークン: in={snap['input_tokens']} out={snap['output_tokens']} "
          f"cache_read={snap['cache_read_input_tokens']} "
          f"cache_write={snap['cache_creation_input_tokens']} "
          f"合計={snap['total_tokens']}")
    if snap["unreported_phases"]:
        print(f"⚠️ {snap['unreported_phases']}/{snap['phases_run']} 工程で "
              "usage/total_cost_usd が返りませんでした"
              "（エンドポイントが計測値を報告していません）。")


def write_metrics(path, results: list[dict], provider: dict | None = None,
                  timestamp: str | None = None) -> int:
    """工程別の計測値を JSONL へ**追記**する（ラン間の比較・傾向把握用）。

    1行1工程。`usage` を持つ（＝実起動した）工程のみ書き出す。戻り値は書き出した行数。
    """
    rows = [r for r in results if r.get("usage")]
    if not rows:
        return 0
    ts = timestamp or datetime.datetime.now().isoformat(timespec="seconds")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({
                "timestamp": ts,
                "endpoint": (provider or {}).get("endpoint"),
                "phase": r.get("phase"),
                "seed": r.get("seed"),
                "variant": r.get("variant"),
                "mode": r.get("mode"),
                "model": r.get("model"),
                "effective_model": r.get("effective_model"),
                "status": r.get("status"),
                **r["usage"],
            }, ensure_ascii=False) + "\n")
    return len(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="XDDP L4/L5 full-run スモーク（LLM・予算ガード）")
    parser.add_argument("--phase", help=f"単一工程（{'/'.join(PHASE_LABELS)}）")
    parser.add_argument("--all", action="store_true", help="init→close を順に通す")
    parser.add_argument("--multi", action="store_true",
                        help=f"multi 版シードを使う（{sorted(MULTI_PHASES)} のみ）")
    parser.add_argument("--profile", choices=["full", "quick"], default="full",
                        help=f"CR_PROFILE 別シードを使う（既定 full。quick は "
                             f"{sorted(QUICK_PHASES)} のみ・--phase 単体指定限定。"
                             "--all との併用は未対応）")
    parser.add_argument("--calibrate", action="store_true",
                        help="校正ラン（偽失敗率・トークン実測）")
    parser.add_argument("--model", help="校正時のモデル指定（haiku/sonnet 等）")
    parser.add_argument("--update-golden", action="store_true",
                        help="構造性質を再収集してゴールデンを更新")
    parser.add_argument("--harvest", action="store_true",
                        help="ハーベスト（no-assert。シード起こし・立ち上がり確認。B 専用）")
    parser.add_argument("--budget", type=float, default=None,
                        help="予算上限を明示指定（USD。config 値より優先。"
                             "第三者エンドポイントでは既定で上限なしだが本指定で上限を付けられる）")
    parser.add_argument("--metrics-out", type=Path, default=None,
                        help="工程別の計測値（トークン・所要時間・コスト）を JSONL へ追記する")
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

    if args.all and args.profile == "quick":
        print("❌ --all --profile quick は未対応です（quick は --phase 単体指定と組み合わせてください）。",
              file=sys.stderr)
        return 2

    # --phase 解決の検証（LLM 非依存・ここまではトークン0。exit 2）
    if args.phase:
        try:
            seed_name = resolve_phase(args.phase, args.multi, args.profile)
        except ValueError as e:
            print(f"❌ {e}", file=sys.stderr)
            return 2
        # シード未整備を起動前に検出する（未整備だと stage_workspace が空ワークスペース起動
        # ＝phase01 init 相当にフォールバックし、意図しない工程を偽装起動してしまうため）。
        if args.phase != "01" and not (SEEDS_ROOT / seed_name).exists():
            print(f"❌ シードが存在しません: {SEEDS_ROOT / seed_name}\n"
                  "   先に該当シードを用意してください。", file=sys.stderr)
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
              "   ANTHROPIC_AUTH_TOKEN か ANTHROPIC_API_KEY を設定してください\n"
              "   （CLAUDE_CODE_OAUTH_TOKEN は Anthropic サブスクの資格情報のため、\n"
              "   第三者エンドポイント指定時は意図的に候補から外しています）。\n"
              "   ANTHROPIC_DEFAULT_SONNET_MODEL 等のモデルエイリアス上書きは自動転送されます。\n"
              "   `make test`（L1〜L3・0トークン）は影響を受けません。", file=sys.stderr)
        return 5

    provider = describe_provider(auth_env)
    if provider["third_party"]:
        print(f"ℹ️ 第三者エンドポイントで実行します: endpoint={provider['endpoint']} "
              f"auth={provider['auth_var']}\n"
              f"   ゴールデンは {GOLDEN_ROOT}/{GOLDEN_PROVIDERS_SUBDIR}/ 配下の"
              "プロファイル別ディレクトリを使います\n"
              "   （Sonnet 校正済みゴールデンは上書きされません。初回は golden_missing で"
              "停止するので --update-golden で確定してください）。", file=sys.stderr)

    cfg = load_smoke_config(SMOKE_CONFIG_PATH)

    if args.calibrate:
        mode = "calibrate"
    elif args.update_golden:
        mode = "update-golden"
    elif args.harvest:
        mode = "harvest"
    else:
        mode = "assert"

    # 実効予算の解決。
    # 第三者エンドポイントでは Anthropic の USD 単価に基づく上限が意味を持たない
    # （応答が total_cost_usd を返さない場合もある）ため、`--budget` を明示しない限り
    # **上限なし（計測のみ）** とし実効予算ゲート（exit 6）を適用しない。
    # 暴走防止は SMOKE_MAX_PHASES（工程数上限）が担い、トークンは計測して報告する。
    if provider["third_party"] and not args.budget:
        budget_usd = None
        print("ℹ️ 第三者エンドポイントのため USD 予算ガードは適用しません（計測のみ）。\n"
              f"   暴走防止は工程数上限 SMOKE_MAX_PHASES={cfg.get('SMOKE_MAX_PHASES')} が担います"
              "（上限を付けたい場合は --budget を明示）。", file=sys.stderr)
    else:
        # 実効予算ゲート（exit 6）: LLM を予算上限なしに起動しない不変条件。
        budget_usd = resolve_effective_budget(mode, cfg, args.budget)
        if budget_usd <= 0:
            print("❌ 実効予算が未供給です（LLM を予算上限なしに起動しません）。\n"
                  "   校正済みなら smoke_config.md の SMOKE_TOKEN_BUDGET を、\n"
                  "   ブートストラップ（B: --harvest／--update-golden／--calibrate）なら\n"
                  "   smoke_config.md の SMOKE_CALIBRATE_BUDGET か CLI --budget を与えてください。\n"
                  "   校正手順は B（--harvest でシード）→ C（--update-golden でゴールデン）→\n"
                  "   D（--calibrate で偽失敗率・SMOKE_TOKEN_BUDGET 確定）の順。", file=sys.stderr)
            return 6

    budget = BudgetTracker(budget_usd, max_phases=cfg.get("SMOKE_MAX_PHASES"))

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
            for r in results:  # エイリアス→実モデルの対応をレポートへ載せる（G6）
                r["effective_model"] = resolve_effective_model(r["model"])
            for r in results:  # 中断判定（連鎖ハーベストは打ち切り位置を報告する）
                if r.get("status") == "budget_skip":
                    print(f"⚠️ [{r['seed']}] 残予算不足で以降を中断します。", file=sys.stderr)
                    break
                if r.get("status") == "invoke_error":
                    print(f"❌ [{r['seed']}] スキル起動が失敗（{r.get('error')}）。"
                          "連鎖を中断しました。", file=sys.stderr)
                    exit_code = 9
                    break
            _print_report(results, budget, args.json, provider)
            _write_metrics_if_requested(args.metrics_out, results, provider)
            return exit_code
        for phase, variant in _build_tasks(args):
            model = resolve_model(phase, cfg, args.model)
            # ゴールデンは第三者エンドポイント利用時のみプロファイル別ディレクトリへ分離する
            # （Sonnet 校正済みゴールデンを別モデルの --update-golden が壊さないため）。
            r = run_phase(phase, variant=variant, model=model,
                          budget=budget, mode=mode, auth_env=auth_env, cfg=cfg,
                          golden_dir=resolve_golden_dir(GOLDEN_ROOT, model),
                          debug_dir=args.harvest_debug)
            r["effective_model"] = resolve_effective_model(model)
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

    _print_report(results, budget, args.json, provider)
    _write_metrics_if_requested(args.metrics_out, results, provider)
    return exit_code


def _write_metrics_if_requested(metrics_out, results: list[dict],
                                provider: dict | None) -> None:
    """`--metrics-out` 指定時のみ計測 JSONL を追記し、書き出し先を通知する。"""
    if not metrics_out:
        return
    n = write_metrics(metrics_out, results, provider)
    print(f"計測を {metrics_out} へ {n} 行追記しました。", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
