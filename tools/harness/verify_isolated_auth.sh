#!/usr/bin/env bash
# verify_isolated_auth.sh
# ---------------------------------------------------------------------------
# PLAN-20260725-smoke-full-api-key-auth / 親プラン 3.5 step 0 検証B の実機確認ツール。
#
# 目的: 隔離 HOME + CLAUDE_CODE_OAUTH_TOKEN で
#   (A) 非対話認証が実際に成立する（"Not logged in" にならない）
#   (B-1) 隔離 HOME 配下へ setup.sh でデプロイしたスキル定義が配置される（決定的）
#   (B-2) デプロイ済み user-scope スキルが claude -p 単発モードで解決される
# ことを実測確認する。実利用者の ~/.claude/ は一切変更しない。
#
# 使い方（トークンはこのスクリプトに書かず、実行者のシェルで export する）:
#   claude setup-token                              # ブラウザで OAuth 認可 → 1年有効トークン発行
#   export CLAUDE_CODE_OAUTH_TOKEN='sk-ant-oat...'  # 発行された値を貼る（チャット等に貼らない）
#   bash tools/harness/verify_isolated_auth.sh
#
# 環境変数による上書き:
#   VERIFY_MODEL   起動モデル（既定: claude-haiku-4-5-20251001。トークン消費を抑えるため小型）
#   VERIFY_SKILL   解決確認するスキル名（既定: xddp.status）
#
# 前提: Pro/Max 契約なら CLAUDE_CODE_OAUTH_TOKEN 使用で追加課金なし（サブスク枠を消費。
#       「追加課金なし」は公式明言ではなく妥当な推論＝plan Section 1 の留意事項参照）。
# 参照: PLAN-20260725-smoke-full-api-key-auth / PLAN-20260725-p2-test-harness Section 3.5・5
# ---------------------------------------------------------------------------
set -uo pipefail

# --- リポジトリ位置をスクリプト自身の位置から解決（tools/harness/ の2階層上）---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
SETUP="$REPO/ClaudeCode/setup.sh"
MODEL="${VERIFY_MODEL:-claude-haiku-4-5-20251001}"
SKILL_NAME="${VERIFY_SKILL:-xddp.status}"

fail() { echo "❌ $*" >&2; exit 1; }

# --- 0. 前提チェック -------------------------------------------------------
command -v claude >/dev/null 2>&1 || fail "claude CLI が見つかりません"
command -v python3 >/dev/null 2>&1 || fail "python3 が見つかりません（応答JSON解析に使用）"
[[ -f "$SETUP" ]] || fail "setup.sh が見つかりません: $SETUP"
if [[ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]]; then
  fail "CLAUDE_CODE_OAUTH_TOKEN が未設定です。\n   claude setup-token で発行し export してから再実行してください。"
fi
echo "✓ 前提OK: repo=$REPO"
echo "✓ 前提OK: claude=$(claude --version 2>/dev/null) / model=$MODEL / skill=$SKILL_NAME"

# --- 1. 隔離 HOME を作成し setup.sh でデプロイ -----------------------------
TMPHOME="$(mktemp -d "${TMPDIR:-/tmp}/xddp-verifyB.XXXXXX")"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/xddp-verifyB-ws.XXXXXX")"
cleanup() { rm -rf "$TMPHOME" "$WORKDIR"; }
trap cleanup EXIT
echo "✓ 隔離HOME: $TMPHOME"
echo "✓ 作業ディレクトリ: $WORKDIR"

echo "--- setup.sh デプロイ（隔離HOMEへ）---"
if ! HOME="$TMPHOME" bash "$SETUP" >/dev/null 2>&1; then
  fail "setup.sh のデプロイに失敗しました"
fi

# 決定的証拠: スキルファイルが隔離HOME配下に配置されたか（LLM非依存）
SKILL_FILE="$TMPHOME/.claude/skills/$SKILL_NAME/SKILL.md"
[[ -f "$SKILL_FILE" ]] || fail "デプロイ後にスキルが見つかりません: $SKILL_FILE"
echo "✓ (B-1) スキルファイル配置を確認: ~/.claude/skills/$SKILL_NAME/SKILL.md"
echo "✓ 実 HOME ($HOME) は未変更（HOME を差し替えて実行）"

# claude を隔離HOMEで起動する共通ヘルパ。auth/PATH/HOME のみ渡す。
run_claude() {
  local prompt="$1"
  env -i \
    HOME="$TMPHOME" \
    PATH="$PATH" \
    CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
    claude -p --output-format json --model "$MODEL" "$prompt" \
    2>/dev/null
}

# --- 2. 検証A: 認証成立 ----------------------------------------------------
echo "--- (A) 認証成立チェック ---"
AUTH_JSON="$(run_claude 'Reply with exactly the token OK and nothing else.')"
[[ -n "$AUTH_JSON" ]] || fail "claude から応答がありません（認証/起動失敗の可能性）"

if grep -qiE 'not logged in|please run /login|invalid api key|authentication' <<<"$AUTH_JSON"; then
  python3 -c 'import sys,json; d=json.load(sys.stdin); print("  result:", d.get("result"))' <<<"$AUTH_JSON" 2>/dev/null || true
  fail "(A) 認証が成立していません（ログイン要求/認証エラーを検出）"
fi

AUTH_EVAL="$(python3 - "$AUTH_JSON" <<'PY'
import sys, json
try:
    d = json.loads(sys.argv[1])
except Exception as e:
    print(f"PARSEFAIL {e}"); sys.exit(0)
is_err = d.get("is_error", d.get("subtype") == "error")
res = (d.get("result") or "").strip()
cost = d.get("total_cost_usd")
print(f"OK is_error={is_err} cost={cost} result={res!r}")
PY
)"
echo "  $AUTH_EVAL"
case "$AUTH_EVAL" in
  "OK is_error=False"*|"OK is_error=None"*) echo "✓ (A) 認証成立（is_error=false・ログイン要求なし）" ;;
  PARSEFAIL*) fail "(A) 応答JSONを解釈できませんでした: $AUTH_EVAL" ;;
  *) fail "(A) 応答は返るが is_error=true です: $AUTH_EVAL" ;;
esac

# --- 3. 検証B-2: デプロイ済みスキルが解決される ---------------------------
echo "--- (B-2) デプロイ済みスキルの解決チェック ---"
SKILL_JSON="$(run_claude "Do you have a skill or slash command named $SKILL_NAME available to you right now? Answer with exactly AVAILABLE:yes or AVAILABLE:no and nothing else. Do not use any tools.")"
SKILL_RESULT="$(python3 - "$SKILL_JSON" <<'PY'
import sys, json
try:
    d = json.loads(sys.argv[1]); print((d.get("result") or "").strip())
except Exception: print("")
PY
)"
echo "  モデル応答: ${SKILL_RESULT:-（空）}"
if grep -qiE 'AVAILABLE:\s*yes' <<<"$SKILL_RESULT"; then
  echo "✓ (B-2) デプロイ済み $SKILL_NAME スキルがランタイムに解決された"
elif grep -qiE 'AVAILABLE:\s*no' <<<"$SKILL_RESULT"; then
  echo "⚠️ (B-2) モデルは $SKILL_NAME を認識しませんでした。"
  echo "   → (B-1) のファイル配置は成立しているため、-p 単発モードでの user-scope"
  echo "      スキル注入挙動を人が確認してください（誤判定/モデル差の可能性）。"
else
  echo "⚠️ (B-2) 判定不能（応答が yes/no 形式でない）。人が上記応答を確認してください。"
fi

echo ""
echo "=== 検証B 完了 ==="
echo "  (A) 認証成立: 上記参照"
echo "  (B-1) スキル配置: OK（決定的）"
echo "  (B-2) スキル解決: 上記参照"
echo "  隔離HOME・作業ディレクトリは自動削除されます。"
