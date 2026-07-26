#!/usr/bin/env python3
"""smoke_full.py — L4/L5 full-run スモーク（LLM 使用・予算ガード付き）

スキルのオーケストレーション（L4）と成果物の構造的健全性（L5）を、実際に LLM で
スキルを起動して検証する。トークンは予算ガードで構造的にキャップする。

**重要（実装状況）:** 本ファイルは plan Section 3.2/3.4/3.5 の設計に沿った骨格である。
純ロジック（構造性質抽出・予算積算・上限判定・ゴールデン照合・環境依存フィールド正規化）は
実装済みで `tools/harness/tests/test_smoke_full.py` が 0 トークンで検証する。

一方、実 LLM を起動する経路（`claude -p --output-format json` によるスキル起動・
サブエージェントのモデル適用・隔離 HOME への setup.sh デプロイ）は、plan 3.5 step 0 の
「前提スパイク」で以下の未検証仮定を先に確認してから有効化する:
  - `claude -p --output-format json` が対象スラッシュコマンド（工程スキル）を起動できるか
  - 返却 JSON に `usage` と `total_cost_usd` が含まれるか
  - サブエージェント消費が親の `usage` に積算されるか
  - `--model` 継承／隔離HOMEへの `model:` 注入が実際に効くか
スパイク結果が想定と異なる場合は、`_invoke_phase` / `BudgetTracker` の積算方式を
先に是正する。ゴールデン値・工程別モデル・`SMOKE_TOKEN_BUDGET` は校正ラン（3.5）で
実測確定するまで確定値を持たない（`smoke_config.md` は校正後に書き込む）。

参照: plans/PLAN-20260725-p2-test-harness.md Section 3.2, 3.4, 3.5
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

# 構造アサートで検出する未置換トークン（検査C2。plan 3.1）。
UNREPLACED_TOKEN_RE = re.compile(r"\{[A-Z][A-Z0-9_]*\}")


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
        if key == "SMOKE_TOKEN_BUDGET":
            try:
                cfg["SMOKE_TOKEN_BUDGET"] = float(val)
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


def _invoke_phase(phase: str, workspace: Path, model: str,
                  home: Path, auth_env: dict) -> dict:
    """1工程をヘッドレスで起動し応答 JSON を返す（plan 3.2 実行モデル step 2）。

    ※ この関数は 3.5 step 0 スパイクで挙動確認するまで load-bearing な未検証仮定を含む
    （スラッシュコマンド起動可否・usage 積算範囲）。スパイク前は smoke 実行を許可しない
    （main が claude 未導入/未校正を検出して停止する）。

    隔離 HOME では OAuth/セッション認証情報を引き継げないため、非対話認証用の環境変数
    （`auth_env` = `CLAUDE_CODE_OAUTH_TOKEN` 優先／`ANTHROPIC_API_KEY` フォールバック。
    解決は `main` の `_resolve_auth_env` が担う）を用いる（是正の経緯:
    PLAN-20260725-smoke-full-api-key-auth。認証失敗の実測: 親プラン
    plans/PLAN-20260725-p2-test-harness.md Section 3.5 step 0 で HOME 差し替え
    のみでは "Not logged in" になることを確認済み）。`CLAUDE_CODE_OAUTH_TOKEN` は
    Claude Pro/Max 契約のサブスク枠を消費し追加課金は発生しない（`claude setup-token` で発行）。
    """
    env = {"HOME": str(home), "PATH": os.environ.get("PATH", ""), **auth_env}
    cmd = ["claude", "-p", "--output-format", "json", "--model", model,
           f"/xddp.{phase}"]  # 実スラッシュコマンド名はスパイクで確定
    proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True,
                          text=True, env=env)
    try:
        resp = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        resp = {}
    resp["_phase"] = phase
    return resp


def _resolve_auth_env() -> dict | None:
    """非対話認証用の環境変数を解決する（CLAUDE_CODE_OAUTH_TOKEN 優先＝Pro/Max契約消費で
    追加課金なし。未設定時のみ ANTHROPIC_API_KEY＝API従量課金にフォールバック）。"""
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return {"CLAUDE_CODE_OAUTH_TOKEN": os.environ["CLAUDE_CODE_OAUTH_TOKEN"]}
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {"ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"]}
    return None


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
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)

    # --phase 解決の検証（LLM 非依存・ここまではトークン0）
    if args.phase:
        try:
            seed = resolve_phase(args.phase, args.multi)
            print(f"phase '{args.phase}' -> seeds/{seed}/")
        except ValueError as e:
            print(f"❌ {e}", file=sys.stderr)
            return 2

    if not claude_available():
        print("❌ full-run スモークは `claude` CLI を必要とします（未導入/認証未了）。\n"
              "   `make test`（L1〜L3・0トークン）は影響を受けません。", file=sys.stderr)
        return 3

    auth_env = _resolve_auth_env()
    if auth_env is None:
        print("❌ full-run スモークは隔離 HOME 実行のため非対話認証の環境変数が必須です\n"
              "   （隔離 HOME では OAuth セッションを引き継げないため。親プラン 3.5 step 0 実測で確認済み）。\n"
              "   Pro/Max契約なら追加課金なしの CLAUDE_CODE_OAUTH_TOKEN（`claude setup-token` で発行）を、\n"
              "   なければ ANTHROPIC_API_KEY（API従量課金）を設定してください。\n"
              "   `make test`（L1〜L3・0トークン）は影響を受けません。", file=sys.stderr)
        return 5

    # LLM 起動経路は 3.5 step 0 スパイク＋校正（smoke_config.md 確定）完了後に有効化する。
    print("⚠️ full-run スモークの LLM 起動経路は校正ラン（plan 3.5）完了後に有効化されます。\n"
          "   手順: (1) step 0 前提スパイク → (2) ゴールデン確定 → (3) 偽失敗率測定 →\n"
          "   (4) smoke_config.md に工程別モデル・SMOKE_TOKEN_BUDGET を書き込む。",
          file=sys.stderr)
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
