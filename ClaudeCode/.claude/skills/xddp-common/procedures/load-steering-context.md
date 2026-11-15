# Load Steering Context

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## Load Steering Context

プロジェクト規約ファイル（project-rulebook.md 系）を読み込んで RULEBOOK_CONTEXT を構築する共通手順。

**Input:**
- `XDDP_DIR`: XDDPディレクトリのパス
- `REPO_NAME`（任意）: リポジトリ名。指定時は project-rulebook-{REPO_NAME}.md も読み込む
- `INCLUDE_CROSS`（任意, default: false）: true の場合 project-rulebook-cross.md も読み込む

cross の成果物（`cross/` の DSN・CHD・TSP 等）を扱うときは `REPO_NAME` を渡さず `INCLUDE_CROSS: true` にする（共通＋cross）。
リポジトリの成果物を扱うときは `REPO_NAME: {repo}` を渡す（共通＋`project-rulebook-{repo}.md`。構成によらない）。

**Process:**
1. Read `{XDDP_DIR}/project-rulebook.md` (if exists). Set as base RULEBOOK_CONTEXT.
2. If `REPO_NAME` is provided: Read `{XDDP_DIR}/project-rulebook-{REPO_NAME}.md` (if exists). Append to RULEBOOK_CONTEXT.
3. If `INCLUDE_CROSS` = true: Read `{XDDP_DIR}/project-rulebook-cross.md` (if exists). Append to RULEBOOK_CONTEXT.
4. If none of the files exist: RULEBOOK_CONTEXT = empty (proceed without constraints).
5. Return `RULEBOOK_CONTEXT`.
