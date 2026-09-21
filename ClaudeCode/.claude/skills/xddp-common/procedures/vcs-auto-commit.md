# VCS Auto-Commit

> xddp-common の共通プロシージャ。呼び出し元スキルから apply される。

## VCS Auto-Commit

指定ステップの自動コミットを行う共通手順。`VCS_COMMIT_ON_STEP` に対象ステップが含まれる場合のみ
`## VCS Commit If Dirty` を呼び出す。

**Input:**
- `PROCESS_STEP`: `VCS_COMMIT_ON_STEP` と照合する工程番号（例: `7`, `10`。`## Progress Update` の
  `STEP_NUM`（例: `10a`/`10b`/`10c`）とは意味が異なるため、同名の `STEP_NUM` ではなく `PROCESS_STEP`
  という別名を用いる。呼び出し元 SKILL.md で `## Progress Update` と `## VCS Auto-Commit` の呼び出しが
  近接していても、コピー&ペースト時に誤って `## Progress Update` のステップ識別子（`10a` 等）を
  渡してしまうリスクを構造的に排除するため）
- `REPO_LIST`: 対象リポジトリ名のリスト（`## VCS Commit If Dirty` と同一契約。呼び出し元は
  `VCS_TARGET_REPOS` を渡す）
- `COMMIT_MESSAGE`: コミットメッセージ（例: `{CR} 工程7コーディング完了`）
- `VCS_TYPE`（暗黙）, `VCS_COMMIT_ON_STEP`（暗黙）: `## VCS Commit If Dirty` と同じ扱い

**Process:**
1. If `VCS_TYPE` is `none`: 何もせず終了する。
2. Let `COMMIT_STEPS` = `VCS_COMMIT_ON_STEP` をカンマ区切りで分割し、前後の空白を除去したリスト。
   `none` または空の場合は空リスト。
3. If `{PROCESS_STEP}` is not in `COMMIT_STEPS`: 何もせず終了する。
4. Read `~/.claude/skills/xddp-common/procedures/vcs-commit-if-dirty.md`,
   apply "## VCS Commit If Dirty" with REPO_LIST: {REPO_LIST}, COMMIT_MESSAGE: {COMMIT_MESSAGE}.
