# VCS Commit If Dirty

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## VCS Commit If Dirty

対象リポジトリ群に対し status を確認し、dirty ならコミットする共通ループ本体。

**Input:**
- `REPO_LIST`: 対象リポジトリ名のリスト。呼び出し元は `## Resolve VCS Target Repos` が返した
  `VCS_TARGET_REPOS` を渡すこと（`AFFECTED_REPOS` はマルチリポジトリ構成では `REPOS_KEYS` と
  同一＝全リポジトリであり、CR のスコープ限定にならないため使わない）
- `COMMIT_MESSAGE`: コミットメッセージ（本プロシージャの Bash ステップは `commit "{COMMIT_MESSAGE}"`
  の形でダブルクォートの中に直接埋め込むため、`COMMIT_MESSAGE` にはダブルクォート・バッククォート・
  `$()` を含まない静的定型文のみを渡すこと）
- `ON_FAILURE`（任意, default: `stop`）: 失敗時（`commit` の exit code ≠ 0、または `REPO_STATUS` が
  `unknown`）の扱い。
  - `stop`: エラーを表示して停止する（既定。工程7・工程10の呼び出し元はこれを使う）。
  - `ask`: エラーを表示したうえで続行/中止をユーザーに確認する。「中止」なら残りのリポジトリを
    処理せず、`COMMIT_OUTCOME` = `aborted` として**呼び出し元へ戻る**（プロシージャ内では停止せず、
    中止後の処理——`progress.md` への中断記録等——は呼び出し元の責務とする）。
    「続行」なら当該リポジトリのコミットを行わないまま次のリポジトリへ進む。
    `xddp-close` の最終コミットのみが使う（設計判断の詳細は `docs/adr/ADR-0011-vcs-abstraction.md`
    Decision 20 を参照）。
- `VCS_TYPE`（暗黙）: `## CR Resolution`/`## Load Config` 経由で解決済みの値をそのまま参照する
  （`MD2EXCEL_PYTHON_BIN` と同じ扱いのため、apply 呼び出し時に明示的に渡す必要はない）
- `REPOS_MAP`（暗黙）: 同上

**Output:**（`ON_FAILURE` 省略時（`stop`）は失敗時にプロシージャ内で停止するため、呼び出し元へ制御が
戻る場合の `COMMIT_OUTCOME` は必ず `ok` になり、既存の呼び出し元は出力を参照しなくてよい）
- `COMMIT_OUTCOME`: `ok`（全リポジトリを処理し、失敗による中断・スキップが無かった）／
  `partial`（`ask` で「続行」が選ばれ、コミットされなかったリポジトリがある）／
  `aborted`（`ask` で「中止」が選ばれ、残りのリポジトリを処理していない）
- `UNCOMMITTED_REPOS`: **status を確認したうえでコミットされなかった**リポジトリ名のリスト
  （`ok` の場合は空）。`aborted` の場合、中止時点で未処理だった残りのリポジトリは status 確認自体を
  行っていない（clean かもしれない）ため、**このリストには含めない**。
- `UNPROCESSED_REPOS`: `aborted` の場合に、中止によって status 確認すら行わなかった残りの
  リポジトリ名のリスト（`ok`／`partial` の場合は空）

**Process:**
Initialize `COMMIT_OUTCOME` = `ok`, `UNCOMMITTED_REPOS` = 空リスト, `UNPROCESSED_REPOS` = 空リスト。
For each `{repo}` in `{REPO_LIST}`:
  Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_vcs.py status --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE}`
  → let `REPO_STATUS`.
  If `REPO_STATUS` is `dirty`:
    Bash: `PY=$(command -v python3 || command -v python) && "$PY" ~/.claude/skills/xddp-common/scripts/xddp_vcs.py commit "{COMMIT_MESSAGE}" --repo {REPOS_MAP[repo]} --vcs-type {VCS_TYPE}`
    If exit code ≠ 0:
      If `ON_FAILURE` is `ask`: エラーを表示し、続行/中止を確認する。
        中止なら `COMMIT_OUTCOME` = `aborted`、`UNCOMMITTED_REPOS` に `{repo}` を追加し、
        `UNPROCESSED_REPOS` に `{REPO_LIST}` の未処理の残りリポジトリを設定して、ループを抜けて
        呼び出し元へ戻る（プロシージャ内では停止しない。残りのリポジトリは status 確認自体を
        行っていないため `UNCOMMITTED_REPOS` とは区別する）。
        続行なら `COMMIT_OUTCOME` = `partial`、`UNCOMMITTED_REPOS` に `{repo}` を追加し、
        次の `{repo}` へ進む。
      Else（`stop`。既定）: report the error and stop.
  If `REPO_STATUS` is `unknown`:
    If `ON_FAILURE` is `ask`: 上記 exit code ≠ 0 と同じ扱い（エラー表示＋続行/中止の確認、および
      `COMMIT_OUTCOME`／`UNCOMMITTED_REPOS`／`UNPROCESSED_REPOS` の更新）とする（中止時は exit code ≠ 0
      の場合と同様に `UNPROCESSED_REPOS` へ `{REPO_LIST}` の未処理の残りリポジトリを設定する）。
    Else（`stop`。既定）: Report error and stop.
    （既定は「停止」に確定する。本プロシージャは commit という副作用を伴う処理であり、status が不明な
    状態で commit を試みるとコミット漏れ・意図しない内容の巻き込みに気付けないまま進行するリスクが
    ある。「status 確認等の読み取り専用処理は続行を許容し、commit/branch/revert 等の副作用を伴う処理は
    安全側に倒して停止する」という本設計の原則（`docs/adr/ADR-0011-vcs-abstraction.md` Decision 15）と
    整合させる。`ON_FAILURE: ask` はこの原則の例外ではなく、「AI が黙って先へ進まない」という原則の核を
    保ったまま、判断を人に委ねる第3の選択肢である。`xddp-close` のように、停止することで失われる下流
    処理（成果物昇格・CR 完了記録）がある呼び出し元にのみ適用する）

ループ終了後（`COMMIT_OUTCOME` によって文面を分ける——`aborted` では処理を「続行」していないため、
`partial` と同じ文面では事実と食い違う）:
  If `COMMIT_OUTCOME` is `partial`:
    Warn: "⚠️ 未コミットのまま処理を続行したリポジトリ: {UNCOMMITTED_REPOS を列挙}"
  If `COMMIT_OUTCOME` is `aborted`:
    Warn: "⚠️ コミット処理を中止しました。未コミットのリポジトリ: {UNCOMMITTED_REPOS を列挙}／
    未処理（status 未確認）のリポジトリ: {UNPROCESSED_REPOS を列挙。空の場合は「なし」}"
Return `COMMIT_OUTCOME`, `UNCOMMITTED_REPOS`, `UNPROCESSED_REPOS`.
