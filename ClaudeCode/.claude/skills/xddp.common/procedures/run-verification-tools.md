# Run Verification Tools

> xddp.common の共通プロシージャ。呼び出し元スキルから apply される。

## Run Verification Tools

REPO 単位で lint/build/typecheck の実コマンドを実行する共通手順。
`xddp.07.code` Step B・`xddp.08.verify` Step A・`xddp.10.test-run` b-1（実装バグ再検証）の
3箇所から呼ばれる（いずれも `xddp-verifier-agent` を呼ぶ箇所と1対1で対応する。cross は対象外）。

**Input:**
- `REPO_NAME`, `REPO_PATH`（= REPOS_MAP[REPO_NAME]）, `CR_PATH`, `CR`
- `VERIFY_LINT_COMMAND`, `VERIFY_LINT_COMMAND_OVERRIDES`,
  `VERIFY_BUILD_COMMAND`, `VERIFY_BUILD_COMMAND_OVERRIDES`,
  `VERIFY_TYPECHECK_COMMAND`, `VERIFY_TYPECHECK_COMMAND_OVERRIDES`,
  `VERIFY_TOOL_TIMEOUT_SEC`（いずれも暗黙。`## Load Config`/`## CR Resolution` 経由で解決済みの値をそのまま使う）

**Output:** `TOOL_RESULTS_FILE`（生成したレポートのパス。何も設定されていない場合、または
  レポートが生成されなかった場合は空文字列）, `TOOL_ALL_PASS`（boolean。未設定＝true）,
  `TOOL_USAGE_ERROR`（boolean。未設定＝false）, `TOOL_USAGE_ERROR_DETAIL`（使用法エラー時の
  Bash 呼び出し stderr 全文。それ以外は空文字列）

**Process:**
1. Let `LINT_CMD` = `VERIFY_LINT_COMMAND_OVERRIDES.get(REPO_NAME, VERIFY_LINT_COMMAND)`.
   `BUILD_CMD`・`TYPECHECK_CMD` も同様に解決する。
2. If `LINT_CMD`・`BUILD_CMD`・`TYPECHECK_CMD` が全て空文字列: `TOOL_RESULTS_FILE` = 空文字列,
   `TOOL_ALL_PASS` = true, `TOOL_USAGE_ERROR` = false, `TOOL_USAGE_ERROR_DETAIL` = 空文字列として
   終了する（スクリプトを起動しない — 何も設定していない既存 CR の挙動を変えないため）。
3. Let `OUTPUT_FILE` = `{CR_PATH}/08_code-review/TOOLRUN-{CR}-{REPO_NAME}.md`.
4. Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp.common/scripts/xddp_verify_tools.py run --repo-path {REPO_PATH} --output {OUTPUT_FILE} --timeout-sec {VERIFY_TOOL_TIMEOUT_SEC} {--lint "{LINT_CMD}" があれば付与} {--build "{BUILD_CMD}" があれば付与} {--typecheck "{TYPECHECK_CMD}" があれば付与}`
   （このBash呼び出し自体の stderr をオーケストレータが保持しておく——手順5で使用する）
5. 終了コードで `TOOL_RESULTS_FILE`/`TOOL_ALL_PASS`/`TOOL_USAGE_ERROR`/`TOOL_USAGE_ERROR_DETAIL` を
   決定する:
   - exit code `0`: `TOOL_RESULTS_FILE` = `OUTPUT_FILE`, `TOOL_ALL_PASS` = true,
     `TOOL_USAGE_ERROR` = false, `TOOL_USAGE_ERROR_DETAIL` = 空文字列。
   - exit code `1`（設定されたコマンドのいずれかが非0終了・タイムアウト含む＝真の検証失敗。
     `xddp_verify_tools.py` は `run` サブコマンド全体を try/except で包み、`OUTPUT_FILE` への
     書き出しが実際に完了した場合のみ exit `1` を返す——この分岐では `OUTPUT_FILE` が必ず存在する）:
     `TOOL_RESULTS_FILE` = `OUTPUT_FILE`, `TOOL_ALL_PASS` = false, `TOOL_USAGE_ERROR` = false,
     `TOOL_USAGE_ERROR_DETAIL` = 空文字列。
   - exit code `2`（(a) argparse が起動直後のコマンドライン解析段階で使用法エラーを検出し
     `sys.exit(2)` する場合、または (b) `run` サブコマンド本体で捕捉されない例外——存在しない
     `--repo-path` の指定・`OUTPUT_FILE` 書き込み権限がない等——が発生し try/except が
     exit `2` にフォールバックさせる場合。いずれも `OUTPUT_FILE` への書き出しが完了する前に
     終了するため、この分岐では `OUTPUT_FILE` は**作成されない、または不完全なまま残る可能性がある**
     ものとして扱う）または想定外の終了コード:
     `TOOL_RESULTS_FILE` = 空文字列（存在するか保証できないファイルパスを後続に渡さない — 手順2の
     「未設定」時と同じ空文字列規約に揃える）, `TOOL_ALL_PASS` = false, `TOOL_USAGE_ERROR` = true,
     `TOOL_USAGE_ERROR_DETAIL` = 手順4の Bash 呼び出しの stderr 全文。
     （exit `1` と `2` を区別する理由: `1` はコード自体の欠陥であり呼び出し元の既存NG分類
     ——実装バグ／設計エラー——にそのまま乗せてよいが、`2` はスクリプト呼び出し自体の異常
     （使用法エラー・内部例外いずれも）であり、コード修正でも設計書修正でも解消しない。両者を
     区別せず一律 NG として実装バグ/設計エラーの二択に流し込むと、利用者が的外れな対応を
     とってしまう。使用法エラーと内部例外を `2` という同一の exit code に統合する理由は、
     いずれも「`OUTPUT_FILE` の完成を保証できない」という同じ性質を持ち、呼び出し元から見た
     扱い（ファイルパスを渡さず stderr を渡す）が完全に同一になるため、区別する実益がないこと）
6. Return `TOOL_RESULTS_FILE`, `TOOL_ALL_PASS`, `TOOL_USAGE_ERROR`, `TOOL_USAGE_ERROR_DETAIL`.
