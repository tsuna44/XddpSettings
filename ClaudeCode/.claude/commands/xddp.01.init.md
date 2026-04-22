You are executing XDDP Step 01: Initialize CR Workspace.

**Arguments:** $ARGUMENTS
- 1st token: CR number (e.g., `REQ-2026-001`)
- 2nd token (optional): path to the requirements file

Delegate to the **xddp.01.init** skill:

1. Locate the requirements file.
2. Create directory structure under `{CR}/`.
3. Copy requirements file into `{CR}/01_requirements/`.
4. Create `latest-specs/` with a README if not already present.
5. Copy `~/.claude/templates/xddp.config.md` to `./xddp.config.md` if not already present.
6. Copy `~/.claude/templates/project-steering-template.md` to `./project-steering.md` if not already present.
7. Create `{CR}/progress.md` from template (step 1 ✅, all others ⬜).
8. Report in Japanese and show next command: `/xddp.02.analysis {CR}`.
   - マルチリポジトリの場合は `xddp.config.md` の `MULTI_REPO` / `REPOS:` 設定と `project-steering.md` の「1.5 リポジトリ構成」への記入を促す。

See `.claude/skills/xddp.01.init.md` for full orchestration logic.
