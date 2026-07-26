# PLAN-20260725-smoke-full-api-key-auth

作成日: 2026-07-25
ステータス: **実装完了**（2026-07-26）

---

## 1. 背景・目的

`plans/PLAN-20260725-p2-test-harness.md`（P2 テストハーネス）の確認項目5実施（2026-07-25）で、
`tools/harness/smoke_full.py` の `_invoke_phase`（Section 3.2 実行モデル step 1〜2）が前提とする
「一時ディレクトリに `HOME` を切り替えて `setup.sh` デプロイ」方式が、**認証情報を引き継げず
実行時に必ず失敗する**ことを前提スパイク（同プラン Section 3.5 step 0）で実測した。

- 検証（`env={"HOME": 一時dir}` で `claude -p` を起動）: `"result":"Not logged in · Please run /login"`
  で失敗。この環境の OAuth/セッション認証情報は実 `HOME`（`~/.claude/`）配下にあり、`ANTHROPIC_API_KEY`
  環境変数も未設定のため、`HOME` を丸ごと差し替えると認証手段が失われる。
- 一方、モデル適用機構（frontmatter `model:` によるサブエージェント別モデル上書き）自体は
  プロジェクトスコープの `.claude/agents/` 配置で正しく機能することを別途確認済み（同スパイク検証A）。

是正案は3案検討し、以下の理由で **非対話環境変数認証（`CLAUDE_CODE_OAUTH_TOKEN` を優先、未設定時は
`ANTHROPIC_API_KEY` にフォールバック）採用**を選ぶ。

| 案 | 内容 | 不採用/採用理由 |
|---|---|---|
| (a) 認証ファイル選択的コピー | 実 `HOME` の認証関連ファイルを隔離 HOME へコピー/シンボリックリンク | 不採用。ファイル配置が非公開の内部実装詳細であり将来の Claude Code バージョンアップで壊れやすい。認証情報ファイルを扱うこと自体のリスクも高い |
| (b) プロジェクトスコープ配置（HOME 維持） | `HOME` を差し替えず、検証対象スキルを作業ディレクトリの `.claude/skills`・`.claude/agents` に配置 | 不採用（保留）。認証は温存できるが、実 `~/.claude/` に同名スキルが存在する場合にどちらが解決されるか（プロジェクトスコープ優先か）が Claude Code のバージョン依存で未検証。環境ごとに解決結果が変わりうるため他者の環境での再現性に欠ける |
| **(c) 非対話環境変数認証（採用）** | `_invoke_phase` の起動時 env に `CLAUDE_CODE_OAUTH_TOKEN`（優先）または `ANTHROPIC_API_KEY`（フォールバック）を渡し、隔離 HOME のまま非対話認証する | 採用。いずれも Claude Code の公式な非対話認証経路。バージョン非依存で挙動が安定し、他者の環境でも「トークン/キーを用意する」という明示的な一手順で再現できる |

(c) の内訳として2方式があり、**`CLAUDE_CODE_OAUTH_TOKEN` を優先方式に採用**する（Pro/Max 契約者が
校正ラン・full-run スモークを実行しても追加課金が発生しないようにするため）。

| 方式 | 生成方法 | 課金 | 隔離 HOME での動作 |
|---|---|---|---|
| **`CLAUDE_CODE_OAUTH_TOKEN`（優先）** | `claude setup-token`（1年間有効な OAuth トークンを生成） | **Claude Pro/Max 契約のサブスク枠を消費。追加課金なし** | 環境変数として渡すのみで動作（`~/.claude/` 実体ファイルのコピー不要）。ただし `--bare` モードでは非サポート（本ハーネスは `claude -p` を使用し `--bare` は使わないため影響なし） |
| `ANTHROPIC_API_KEY`（フォールバック） | Anthropic Console で発行 | API 従量課金（Pro/Max 契約とは別体系） | 同上 |

（出典: Claude Code 公式ドキュメント
https://code.claude.com/docs/en/authentication.md （"Generate a long-lived token" 節）・
https://code.claude.com/docs/en/costs.md
（claude-code-guide エージェント経由で2026-07-25 に一次確認、2026-07-26 に出典URLを追記）。
ドキュメントには `CLAUDE_CODE_OAUTH_TOKEN` が「Claude サブスクリプションで認証する」こと、
Pro/Max 契約は使用量がサブスクリプションに含まれセッションコスト表示が課金に無関係であることが
明記されている一方、`ANTHROPIC_API_KEY` との課金比較として「追加課金が発生しない」と明示的に
述べた記述は確認できていない。上記2点からの妥当な推論として「追加課金なし」と判断しているが、
公式文書で明言された事実そのものではない点に留意すること。
隔離 HOME + 環境変数のみでの完全動作は理論上の整理であり、実機での full 検証は未実施）

**目的:** `_invoke_phase` を非対話環境変数認証に切り替え、隔離 HOME 方式のまま認証を成立させる。
**Pro/Max 契約者に追加課金が発生しないよう** `CLAUDE_CODE_OAUTH_TOKEN` を優先し、未設定時のみ
`ANTHROPIC_API_KEY`（API 従量課金）にフォールバックする。本プランは **コード変更のみ**（校正ラン
本体は対象外。運用者が `claude setup-token` でトークンを発行するか、`ANTHROPIC_API_KEY` を用意した
上で別途実施する）。

なお、呼び出しループが未実装の現時点（3.3 参照）では、`main` に追加する認証環境変数未設定チェック
（3.2）が、既存の「校正ラン完了後に有効化されます」メッセージ（exit 4）より先に評価される（未設定
ユーザーは exit 4 ではなく exit 5 を先に見る）。意図した暫定動作であり、詳細と理由は 3.2 を参照。

---

## 2. 変更対象ファイル

| ファイル | 変更種別 | 概要 |
|---|---|---|
| `tools/harness/smoke_full.py` | 修正 | `_invoke_phase` に `auth_env`（dict）引数を追加し `env` にマージする。`main` に認証環境変数解決（`CLAUDE_CODE_OAUTH_TOKEN` 優先・`ANTHROPIC_API_KEY` フォールバック）と両方未設定時の検出（明示エラーで停止）を追加 |
| `tools/harness/smoke_config.md` | 修正 | 実行要件に `CLAUDE_CODE_OAUTH_TOKEN`（優先・Pro/Max契約で追加課金なし）／`ANTHROPIC_API_KEY`（フォールバック・API従量課金）を明記 |
| `README.md` | 修正 | 「開発時テストハーネス（make）」節の実行要件に `CLAUDE_CODE_OAUTH_TOKEN`（優先・追加課金なし）／`ANTHROPIC_API_KEY`（フォールバック）を追記（`smoke-full`/`smoke-calibrate` のみ必須） |
| `plans/PLAN-20260725-p2-test-harness.md` | 修正 | Section 3.2/3.4（隔離実行の認証方式）に本プランへの参照を追記し、Section 5 確認項目「サブエージェントのモデル適用機構」行を本プラン実施後に再検証する旨へ更新 |
| `tools/harness/tests/test_smoke_full.py` | 修正 | `_resolve_auth_env()` 用の新設テストクラス `TestResolveAuthEnv`（4ケース）を追加（3.7参照） |
| `Makefile` | 修正 | 冒頭コメントの実行要件行に非対話認証用の環境変数（`CLAUDE_CODE_OAUTH_TOKEN`優先／`ANTHROPIC_API_KEY`フォールバック）の要件を追記（3.8参照） |

### 既存 unittest への影響（確認済み・regression なし）

- `tools/harness/tests/test_smoke_full.py` の既存 unittest（`TestBudgetTracker` 等）は `_invoke_phase`
  の実 LLM 起動経路をモック対象外としており（ファイル冒頭コメントに明記）、`_invoke_phase` のシグネチャ
  変更による regression はない。ただし `_resolve_auth_env()` は本プランで新規追加する純ロジックのため、
  3.7 で新設テストクラスを追加する（変更不要ではなくなった。指摘#9対応）。

---

## 3. 変更内容

### 3.1. `tools/harness/smoke_full.py` — `_invoke_phase`

**変更前:**
```python
def _invoke_phase(phase: str, workspace: Path, model: str,
                  home: Path) -> dict:
    """1工程をヘッドレスで起動し応答 JSON を返す（plan 3.2 実行モデル step 2）。
    ...
    """
    env = {"HOME": str(home)}
    cmd = ["claude", "-p", "--output-format", "json", "--model", model,
           f"/xddp.{phase}"]  # 実スラッシュコマンド名はスパイクで確定
    proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True,
                          text=True, env=env)
```

**変更後:**
```python
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
```

**（既存docstring注記の扱いについて）** `変更後` のdocstringは `変更前` の1〜2段落目（スパイク未検証
仮定の警告文）を一切削除・変更せず、そのまま維持したうえで3段落目以降に認証まわりの説明を追記する
（`...` による省略表記は用いない。実ファイルの原文と完全一致させるため）。

（本ブロックの `os.environ.get("PATH", "")` はファイル先頭の import 群への `import os` 追加を前提とする。
3.1 のコード自体は `import os` を追加するステップを含まない——追加は 3.2 の指示（3.2のコードブロック
直後の注記）でのみ行う。3.1・3.2 は同一ファイル `smoke_full.py` への変更であり、3.1 と 3.2 のどちらを
先に適用しても、`import os` の追加は 3.2 の指示に従って1回だけ行われるため最終的に1行のみ追加される）。

**理由:** 親プラン（`plans/PLAN-20260725-p2-test-harness.md`）Section 3.5 step 0 の実測どおり、
`HOME` 差し替えのみでは認証情報が失われる。認証用環境変数を明示的に渡すことで、隔離 HOME
（＝実利用者の `~/.claude/` を汚さない）を維持したまま認証を成立させる。`CLAUDE_CODE_OAUTH_TOKEN`
を優先することで、Pro/Max 契約者が校正ラン・full-run スモークを実行しても API 従量課金による
追加課金が発生しないようにする。

### 3.2. `tools/harness/smoke_full.py` — `main`（事前チェック追加。アンカー: `_resolve_auth_env` は
`_invoke_phase`（3.1で内容変更・位置は不変。実ファイル278-296行目）の直後、`def main(...)`（実ファイル
299行目）の直前に新設する。`claude_available()`（274-275行目）は本節の変更対象ではない）

**変更前:**
```python
if not claude_available():
    print("❌ full-run スモークは `claude` CLI を必要とします（未導入/認証未了）。\n"
          "   `make test`（L1〜L3・0トークン）は影響を受けません。", file=sys.stderr)
    return 3
```

**変更後:**

`_resolve_auth_env` は**モジュールレベル関数**として、既存の `_invoke_phase`（3.1で内容変更・位置は
不変）の直後・`def main(...)` の直前に新設する（`claude_available()` の直後ではない。`claude_available()`
と `_invoke_phase` の間ではなく `_invoke_phase` と `main` の間に挿入するため、`claude_available()` は
本コードブロックに含めない）。`main` 内部の既存コード（`if not claude_available(): ...
return 3`）はそのまま維持し、その直後（`return 3` の後・「LLM 起動経路は…」の `print` の前）に
認証チェックを **4スペースインデントを保って** 挿入する。

```python
def _resolve_auth_env() -> dict | None:
    """非対話認証用の環境変数を解決する（CLAUDE_CODE_OAUTH_TOKEN 優先＝Pro/Max契約消費で
    追加課金なし。未設定時のみ ANTHROPIC_API_KEY＝API従量課金にフォールバック）。"""
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return {"CLAUDE_CODE_OAUTH_TOKEN": os.environ["CLAUDE_CODE_OAUTH_TOKEN"]}
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {"ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"]}
    return None


def main(argv=None) -> int:
    # ...（既存の引数解析・--phase 検証は変更なし）...

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

    # ...（既存の exit 4 メッセージ・return 4 は変更なし）...
```
（ファイル先頭の import 群に `import os` を追加）

**理由:** 認証用環境変数が未設定のまま `_invoke_phase` を呼ぶと認証エラーで空振りし、原因が
分かりにくい失敗になる。既存の `claude` 未導入検出と同じパターンで事前に明示エラー停止する。
`CLAUDE_CODE_OAUTH_TOKEN` を優先解決することで、Pro/Max 契約者は `ANTHROPIC_API_KEY` を用意しな
くても（＝追加課金を発生させなくても）実行できる。

**補足（挿入順序について）:** 現行 `main` は `_invoke_phase` を実際には呼び出しておらず、両チェックを
通過した後は必ず「校正ラン完了後に有効化されます」（exit 4、3.3 で申し送る呼び出しループ実装まで
不変）で停止する。そのため認証環境変数（`CLAUDE_CODE_OAUTH_TOKEN`/`ANTHROPIC_API_KEY`）が両方とも
未設定の場合は、この exit 4 に到達する前に本チェック（exit 5）が先に評価される。呼び出しループ未
実装の現時点では意図した動作であり、実害はない（どちらの exit でも full-run は実行されない）。
むしろ校正ラン着手前に運用者が満たすべき前提条件（`claude setup-token` によるトークン発行、または
`ANTHROPIC_API_KEY` の用意）を早期に案内する効果がある。呼び出しループ実装後も評価順序
（`claude` 未導入 > 認証環境変数未設定 > その他の起動処理）はそのまま維持する設計とする。

### 3.3. 呼び出しループへの申し送り（本プランのスコープ外）

`main` の実行ループ（`--phase`/`--all`/`--calibrate` から `_invoke_phase` を実際に呼ぶ部分）は
親プラン Section 3.5 step 1 以降（校正ラン本体）で実装される未着手部分であり、本プランの対象外。
実装時は `_invoke_phase(phase, workspace, model, home, auth_env)`（`auth_env = _resolve_auth_env()`。
`CLAUDE_CODE_OAUTH_TOKEN` 優先・`ANTHROPIC_API_KEY` フォールバック）の形で呼び出すことをここに明記し、
実装者が本プランの結論を踏まえられるようにする。

### 3.4. `README.md`（アンカー: `#### 開発時テストハーネス（make）` 節の「実行要件」行）

**Before:**
```
- **実行要件:** `python3`（標準ライブラリのみ）・GNU make。`smoke-full*`／`smoke-calibrate` のみ `claude` CLI が必要（未導入時は明示エラーで停止。`make test` は影響を受けない）。
```

**After:**
```
- **実行要件:** `python3`（標準ライブラリのみ）・GNU make。`smoke-full*`／`smoke-calibrate` のみ `claude` CLI と非対話認証用の環境変数（`CLAUDE_CODE_OAUTH_TOKEN`＝`claude setup-token`で発行・Pro/Max契約消費で追加課金なし、優先。未設定時は `ANTHROPIC_API_KEY`＝API従量課金にフォールバック。隔離HOME実行のため必須。PLAN-20260725-smoke-full-api-key-auth Section 3.2 参照）が必要（いずれも未設定/未導入時は明示エラーで停止。`make test` は影響を受けない）。
```

**理由:** 実行要件の一覧が `claude` CLI のみを挙げており、本プランで追加する認証環境変数
（`CLAUDE_CODE_OAUTH_TOKEN`/`ANTHROPIC_API_KEY`）の要件が欠落していたため。

### 3.5. `tools/harness/smoke_config.md`（アンカー: 冒頭「役割分担（重要）」ブロックと「未確定（校正待ち）」
ブロックの両方の後・「## トークン予算」見出しの前に新規節を挿入）

**Before:** 冒頭に「役割分担（重要）」blockquote（6-9行目）・「未確定（校正待ち）」blockquote
（11-15行目）の2つの独立した注記ブロックが連続し、その直後に「## トークン予算」見出し（17行目）が
続く（認証要件の記載なし）。挿入は**両方の注記ブロックの後**（16行目相当・見出しの直前）に行い、
2つの前置き注記のあいだに割り込ませてはならない。

**After（挿入する実文）:**
```
## 実行要件（認証）

`smoke-full*`／`smoke-calibrate` は隔離 HOME 実行のため非対話認証用の環境変数が必須（OAuth/セッション
認証は隔離 HOME に引き継がれない。PLAN-20260725-smoke-full-api-key-auth 参照）。
`CLAUDE_CODE_OAUTH_TOKEN`（`claude setup-token` で発行。Claude Pro/Max 契約のサブスク枠を消費し
追加課金なし）を優先し、未設定時のみ `ANTHROPIC_API_KEY`（API従量課金）にフォールバックする。
両方とも未設定の場合は `smoke_full.py` が明示エラー（exit 5）で停止する。
（「追加課金なし」は Anthropic 公式ドキュメントに基づく妥当な推論であり、公式文書で明言された
事実そのものではない点に留意すること）
```

**理由:** `smoke_config.md` はハーネスレベルの設定ファイルであり、本プランで `smoke_full.py` に追加する
実行時要件（`CLAUDE_CODE_OAUTH_TOKEN`/`ANTHROPIC_API_KEY`）を利用者が参照する一次情報として明記する
必要がある。Pro/Max 契約者が追加課金なしで運用できる方式を優先方式として明記することが重要。

### 3.6. `plans/PLAN-20260725-p2-test-harness.md`（3箇所）

**箇所1（アンカー: Section 3.2「実行モデル」step 1 の末尾）**

**Before:**
```
1. **隔離環境の準備**: 一時ディレクトリ（scratchpad）に `HOME` を切り、`ClaudeCode/setup.sh` でスキルをそこへデプロイ（実利用者の `~/.claude/` を汚さない）。`test-fixtures/scratch-workspace-min` の該当**工程シード**を作業コピーする（single 版シードは参照母体 `multi/svc-a`・`svc-b` を相対レイアウトを保って同伴コピーする — 3.2「隔離コピー時の母体解決規則」参照）。
```

**After（末尾に追記）:**
```
1. **隔離環境の準備**: 一時ディレクトリ（scratchpad）に `HOME` を切り、`ClaudeCode/setup.sh` でスキルをそこへデプロイ（実利用者の `~/.claude/` を汚さない）。`test-fixtures/scratch-workspace-min` の該当**工程シード**を作業コピーする（single 版シードは参照母体 `multi/svc-a`・`svc-b` を相対レイアウトを保って同伴コピーする — 3.2「隔離コピー時の母体解決規則」参照）。**認証:** 隔離 HOME では OAuth/セッション認証を引き継げないため非対話認証用の環境変数を用いる。`CLAUDE_CODE_OAUTH_TOKEN`（`claude setup-token` で発行・Pro/Max契約消費で追加課金なし）を優先し、未設定時は `ANTHROPIC_API_KEY`（API従量課金）にフォールバックする（PLAN-20260725-smoke-full-api-key-auth で是正済み。3.5 step 0 実測で HOME 差し替えのみでは "Not logged in" になることを確認）。
```

**箇所2（アンカー: Section 3.4「full-run スモークの隔離実行」冒頭の箇条書き1行目）**

**Before:**
```
- **隔離 HOME**: `HOME` を一時ディレクトリに差し替えて `setup.sh` デプロイ → 実利用者の `~/.claude/` を変更しない。
```

**After:**
```
- **隔離 HOME**: `HOME` を一時ディレクトリに差し替えて `setup.sh` デプロイ → 実利用者の `~/.claude/` を変更しない。認証は `CLAUDE_CODE_OAUTH_TOKEN`（優先・Pro/Max契約消費で追加課金なし）または `ANTHROPIC_API_KEY`（フォールバック）による非対話認証（PLAN-20260725-smoke-full-api-key-auth 参照）。
```

**箇所3（アンカー: Section 5「サブエージェントのモデル適用機構」確認項目行）**

**Before:**
```
- [ ] **サブエージェントのモデル適用機構（3.2）が母体エージェント定義を改変せず効く**ことを確認（`--model` 継承／隔離HOMEへの `model:` 注入で意図したモデルが使われ、リポジトリの `agents/*.md` が変更されないこと）— frontmatter注入自体はプロジェクトスコープ配置で有効性を確認済み（3.5 step 0 検証A）だが、**隔離HOME経由での再現は認証未解決のため未確認**。認証伝搬の是正後に再検証が必要
```

**After:**
```
- [ ] **サブエージェントのモデル適用機構（3.2）が母体エージェント定義を改変せず効く**ことを確認（`--model` 継承／隔離HOMEへの `model:` 注入で意図したモデルが使われ、リポジトリの `agents/*.md` が変更されないこと）— frontmatter注入自体はプロジェクトスコープ配置で有効性を確認済み（3.5 step 0 検証A）。**隔離HOME経由での認証は `CLAUDE_CODE_OAUTH_TOKEN` 優先（`ANTHROPIC_API_KEY` フォールバック）採用で是正済み（PLAN-20260725-smoke-full-api-key-auth）**。運用者が校正ラン着手時に実機で再検証する
```

**理由:** 親プランは本プランの前提となったスパイクの実施結果を記録しており、認証是正が別プラン
（本プラン）に切り出された経緯が書かれている。本プラン実装後に参照が更新されないと、親プランの
読者が「認証未解決のまま」という古い状態を読み続けることになる。

### 3.7. `tools/harness/tests/test_smoke_full.py`（アンカー: `TestConfigLoader` クラス末尾・
`if __name__ == "__main__":` ガードの直前）

**Before（現状の末尾。138行）:**
```python
    def test_missing_file_returns_defaults(self):
        cfg = sf.load_smoke_config(Path("/nonexistent/smoke_config.md"))
        self.assertNotIn("SMOKE_TOKEN_BUDGET", cfg)


if __name__ == "__main__":
    unittest.main()
```

**After:**
```python
    def test_missing_file_returns_defaults(self):
        cfg = sf.load_smoke_config(Path("/nonexistent/smoke_config.md"))
        self.assertNotIn("SMOKE_TOKEN_BUDGET", cfg)


class TestResolveAuthEnv(unittest.TestCase):
    def setUp(self):
        self._orig_oauth = os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
        self._orig_key = os.environ.pop("ANTHROPIC_API_KEY", None)

    def tearDown(self):
        if self._orig_oauth is not None:
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = self._orig_oauth
        else:
            os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
        if self._orig_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = self._orig_key
        else:
            os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_both_unset_returns_none(self):
        self.assertIsNone(sf._resolve_auth_env())

    def test_oauth_token_only(self):
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = "tok"
        self.assertEqual(sf._resolve_auth_env(), {"CLAUDE_CODE_OAUTH_TOKEN": "tok"})

    def test_api_key_only(self):
        os.environ["ANTHROPIC_API_KEY"] = "key"
        self.assertEqual(sf._resolve_auth_env(), {"ANTHROPIC_API_KEY": "key"})

    def test_both_set_prefers_oauth_token(self):
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = "tok"
        os.environ["ANTHROPIC_API_KEY"] = "key"
        self.assertEqual(sf._resolve_auth_env(), {"CLAUDE_CODE_OAUTH_TOKEN": "tok"})


if __name__ == "__main__":
    unittest.main()
```
（ファイル先頭の import 群に `import os` を追加）

**理由:** 指摘#9対応。`_resolve_auth_env()`（3.2で新設）は `BudgetTracker`／`resolve_phase()`
（いずれも既存の `TestBudgetTracker`／`TestPhaseResolution` で unittest 済み）と同種の純ロジックで
あり、CLAUDE.md「決定的処理はスクリプト・意味判定はLLM」の方針に沿って同様に unittest 化する。
既存の `setUp`/`tearDown` で環境変数を退避・復元することで、他のテスト実行や実行環境の既存設定
（開発者が実際に `CLAUDE_CODE_OAUTH_TOKEN` 等を設定している場合）を汚染しない。

### 3.8. `Makefile`（アンカー: 冒頭コメントの「実行要件」行、現行10行目）

**Before:**
```
# 実行要件: python3（標準ライブラリのみ）・GNU make。smoke-full* のみ `claude` CLI が必要。
```

**After:**
```
# 実行要件: python3（標準ライブラリのみ）・GNU make。smoke-full*／smoke-calibrate のみ `claude` CLI と
# 非対話認証用の環境変数（CLAUDE_CODE_OAUTH_TOKEN優先・追加課金なし／ANTHROPIC_API_KEYフォールバック）が必要。
```

**理由:** `README.md`（3.4）・`smoke_config.md`（3.5）には認証環境変数の要件を反映するが、`Makefile`
冒頭コメントのみ更新対象から漏れていた（指摘#20対応）。実害は限定的（未設定時は `smoke_full.py` の
ランタイムエラーメッセージが要件を案内する）が、ドキュメント間の整合性のため揃える。

---

## 4. 影響範囲

- **影響するスキル・コマンド**: なし（`tools/harness/` のみ変更。`ClaudeCode/.claude/` のスキル・
  エージェント定義は無改変）。
- **影響する工程**: なし。
- **後方互換性**: 考慮不要。`_invoke_phase` は校正ラン未実施のため実運用での呼び出し実績がなく、
  シグネチャ変更が既存呼び出し元を壊すことはない（呼び出しループ自体が未実装）。
- **コスト**: 実装は 0 トークン（コード編集のみ）。Section 5 の再検証（運用者が任意で実施）は、
  `CLAUDE_CODE_OAUTH_TOKEN`（`claude setup-token` で発行）を使えば Claude Pro/Max 契約のサブスク枠
  消費のみで **追加課金は発生しない**。`ANTHROPIC_API_KEY` にフォールバックした場合のみ、少額の
  API 従量課金が発生する。
- **ドメイン中立性**: 認証方式の変更のみで、ドメイン固有の記述は含まない。

---

## 5. 確認項目

- [ ] `make test` が引き続き緑（`tools/harness/tests` の既存 unittest および新設 `TestResolveAuthEnv`
      （3.7）に regression がないこと）
- [ ] `CLAUDE_CODE_OAUTH_TOKEN`・`ANTHROPIC_API_KEY` が両方とも未設定時に `make smoke-full`/
      `make smoke-calibrate` が明示エラー（exit 5）で停止し、`make test` は影響を受けないことを
      ローカルで確認
- [ ] `CLAUDE_CODE_OAUTH_TOKEN` のみ設定時に、`ANTHROPIC_API_KEY` へフォールバックせず
      `CLAUDE_CODE_OAUTH_TOKEN` が優先解決されることを `_resolve_auth_env()` のユニットテストで確認
- [ ] `claude` 未導入時のエラー（exit 3）が認証環境変数チェック（exit 5）より先に評価される順序が
      保たれていることを確認
- [x] 3.5 step 0 検証Bの再実施（**2026-07-26 実機確認済み**）: 隔離 HOME + `CLAUDE_CODE_OAUTH_TOKEN`
      で実際に認証が成立し（`is_error=false`／`result='OK'`／ログイン要求なし）、隔離 HOME 配下へ
      `setup.sh` でデプロイしたスキル定義（`~/.claude/skills/xddp.status/SKILL.md`）が (B-1) ファイル
      配置（決定的）・(B-2) ランタイム解決（`claude -p` 単発モードで user-scope スキルが注入され
      `AVAILABLE:yes`）ともに成立することを実測。`claude` バージョン 2.1.218。実施時に懸念していた
      「-p 単発での user-scope スキル注入可否」「初回フォルダ信頼ダイアログのブロック」はいずれも問題
      なしと確認。認証コールの表示コストは $0.0231664（`--output-format json` の表示値。Pro/Max サブ
      スク枠消費のため追加課金には至らない想定＝Section 1 留意どおり公式明言ではない）
- [ ] `README.md`（3.4）・`smoke_config.md`（3.5）・親プラン Section 3.2/3.4/5（3.6）・`Makefile`
      （3.8）が、それぞれの Before/After どおりに反映されていること
- [ ] 特定ドメインへの偏りがないか（該当なし・認証方式の変更のみ）

---

## 6. レビュー

AIレビュー結果: [plans/review/PLAN-20260725-smoke-full-api-key-auth-review.md](review/PLAN-20260725-smoke-full-api-key-auth-review.md)

---

## 7. 承認

| 項目 | 内容 |
|---|---|
| 承認者 | |
| 承認日 | |
| 備考 | |
