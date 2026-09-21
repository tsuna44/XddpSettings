# Load Steering Context

> xddp.common の共通プロシージャ。呼び出し元スキルから apply される。

## Load Steering Context

プロジェクト規約ファイル（project-rulebook.md 系）を読み込んで RULEBOOK_CONTEXT を構築する共通手順。

**Input:**
- `XDDP_DIR`: XDDPディレクトリのパス
- `REPO_NAME`（任意）: リポジトリ名。指定時は project-rulebook-{REPO_NAME}.md も読み込む
- `INCLUDE_CROSS`（任意, default: false）: true の場合 project-rulebook-cross.md も読み込む

**Process:**
1. Read `{XDDP_DIR}/project-rulebook.md` (if exists). Set as base RULEBOOK_CONTEXT.
2. If `REPO_NAME` is provided: Read `{XDDP_DIR}/project-rulebook-{REPO_NAME}.md` (if exists). Append to RULEBOOK_CONTEXT.
3. If `INCLUDE_CROSS` = true: Read `{XDDP_DIR}/project-rulebook-cross.md` (if exists). Append to RULEBOOK_CONTEXT.
4. If none of the files exist: RULEBOOK_CONTEXT = empty (proceed without constraints).
5. Return `RULEBOOK_CONTEXT`.
