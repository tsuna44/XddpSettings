# ADR-0015: 工程8静的検証における実ツール実行の設計判断

Status: Accepted
Date: 2026-09-12

## Context

`docs/xddp-tool-analysis-2026-08.md`（2026-09-06 追跡調査時点）§3-4「工程8の実ツール実行」が、
lint・ビルド・型検査を実行する記述が `xddp.07.code`/`xddp.08.verify` にない、AI エージェント
（`xddp-verifier-agent`）の目視レビューだけで「静的検証」を名乗っている、と指摘していた。
`PLAN-20260912-verify-real-tool-execution.md` はこの不足機能を解消する実装プランであり、
本 ADR はその策定過程で確定した設計判断を記録する。

## Decision

### Decision 1（コマンドは設定ファイルで明示指定し、自動判定はしない）

XDDP は「適用ドメインの中立性」（`CLAUDE.md`）を必須要件とし、対象言語・ビルドツールを一切
前提にできない（Web／組み込み／業務システム等が混在しうる）。`package.json` の有無等からの
自動推測は誤判定・誤実行のリスクが高く安全側ではないため、`TEST_FRAMEWORK: auto` のような
自動検出モードは持たせない。`VERIFY_LINT_COMMAND`/`VERIFY_BUILD_COMMAND`/`VERIFY_TYPECHECK_COMMAND`
を `xddp.config.md` で明示指定する方式とし、未設定時は「実行しない（➖ 未設定）」のみとする
（既存 CR の動作は変化しない）。

### Decision 2（PASS/FAIL 判定は終了コードで決定的に行う）

`CLAUDE.md`「開発ルール」の「決定的処理はスクリプト・意味判定はLLM」に従い、実行コマンドの
成否はプロセスの終了コードという機械的事実で判定する。オーケストレータ（各 SKILL.md）は
`xddp_verify_tools.py` の終了コードのみで NG を確定し、`xddp-verifier-agent` の報告文
（Section J）は人向けの説明・要約に留める。両者が食い違うケースを想定し、SKILL 側の判定を
常に優先させる（`TOOL_ALL_PASS`/`TOOL_ALL_PASS_BY_REPO` を明示的な真偽値として返す設計）。

加えて、スクリプト呼び出し自体の異常（使用法エラー・内部例外。終了コード `2`）と、設定された
コマンドの真の検証失敗（終了コード `1`）を区別する。両者を区別せず一律 NG として「実装バグ」
「設計エラー」の二択に流し込むと、利用者が的外れな対応（存在しないコードやCHDの修正）を
とってしまうため、`TOOL_USAGE_ERROR` を独立した出力とし、使用法エラーは既存のNG分類には
含めず専用の案内メッセージで扱う。

### Decision 3（cross/ 検証は対象外）

cross は複数リポジトリのインタフェース契約を照合する合成文書であり、単体でビルド・lint できる
実体を持たない。per-repo 検証（`xddp.07.code` Step B／`xddp.08.verify` Step A／`xddp.10.test-run`
b-1）にのみ実ツール実行を追加し、Step B-cross／Step A-cross（cross-repo interface verification）
は変更しない。

### Decision 4（`.{repo}` 上書き方式の再利用）

マルチリポジトリでは言語・ビルドツールがリポジトリごとに異なるのが通例のため、
`SPECOUT_BACKEND.{repo}` で確立済みの「グローバル既定値＋リポジトリ単位サフィックス上書き」の
記法をそのまま再利用し（`VERIFY_LINT_COMMAND.{repo}` 等）、新しい設定解決方式を増やさない。

### Decision 5（タイムアウトと出力量の制限）

ビルドコマンドはハングしうるため、各コマンド（lint/build/typecheck）に個別に既定 600 秒の
タイムアウトを設ける（3コマンド合計の共有バジェットではない）。子プロセスがさらに孫プロセスを
fork するケースでも確実に終了させるため、新規プロセスグループで起動し、タイムアウト時は
プロセスグループ全体を SIGKILL する（POSIX 前提。Windows では `proc.kill()` のみのベストエフォート
終了になる既知の制限とする）。レビュー入力に渡す出力は末尾 N 行に切り詰める
（`--max-output-lines`。ビルド/lint エラーは通常末尾に集中するため）。

## Consequences

- 新規スクリプト `xddp_verify_tools.py` と新規設定キー（`VERIFY_*`）が追加されるが、未設定時は
  既存 CR の動作を変えない（後方互換）。
- `xddp-verifier-agent` の Output Format に Section J が追加され、総合判定基準が「A〜I」から
  「A〜J」に変わる。
- `xddp_verify_tools.py` の終了コード `1`（検証失敗）と `2`（使用法エラー・内部例外）を呼び出し元
  SKILL.md が区別してハンドリングする必要があり、`## Run Verification Tools`（`xddp.common/SKILL.md`）
  という共通手続きに一元化した。
- 極端に冗長な出力を吐くコマンドに対しては、`proc.communicate()` が全量を先にメモリへ読み込む
  ため、キャプチャ自体の上限がなくメモリ消費が増大しうる。ストリーミング処理による改善は本プランの
  スコープ外とし、実運用で問題が顕在化した場合の改善課題として残す。
