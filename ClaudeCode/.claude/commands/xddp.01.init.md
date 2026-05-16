You are executing XDDP Step 01: Initialize CR Workspace.

**Arguments:** $ARGUMENTS
- 1st token: CR number (e.g., `REQ-2026-001`)
- 2nd token (optional): path to the requirements file

Delegate to the **xddp.01.init** skill:

1. Locate the requirements file.
2. Create directory structure under `{CR}/`.
3. Copy requirements file into `{CR}/01_requirements/`.
4. Create `latest-specs/` with a README (per-repo subdirs `latest-specs/{repo}/` and `latest-specs/cross/interfaces/`) if not already present.
5. Copy `~/.claude/templates/xddp.config.md` to `./xddp.config.md` if not already present.
5.5. Read `DOCS_DIR` from `xddp.config.md` (default: `baseline_docs`) and `REPOS:` list.
     For each repo in REPOS: create `{DOCS}/{repo}/specs/` / `{DOCS}/{repo}/knowledge/` /
     `{DOCS}/{repo}/design/` / `{DOCS}/{repo}/test/`.
     If REPOS: has ≥2 entries, also create `{DOCS}/cross/specs/` / `{DOCS}/cross/knowledge/` /
     `{DOCS}/cross/design/` / `{DOCS}/cross/test/`.
     Create `{DOCS}/AI_INDEX.md` if absent.
6. Copy per-repo and shared steering files:
   - `~/.claude/templates/project-steering-template.md` → `{XDDP_DIR}/project-steering.md` (shared, if absent)
   - For each repo in REPOS: copy `project-steering-repo-template.md` → `{XDDP_DIR}/project-steering-{repo}.md` (if absent)
   - If REPOS: ≥2: copy `project-steering-cross-template.md` → `{XDDP_DIR}/project-steering-cross.md` (if absent)
7. Create `{CR}/progress.md` from template (step 1 ✅, all others ⬜).
8. Report in Japanese and show next command: `/xddp.02.analysis {CR}`.
   - Prompt to configure `REPOS:` in `xddp.config.md` and fill in per-repo steering files.
   - Remind that `cross` is a reserved directory name and must not appear as a REPOS: key.

See `.claude/skills/xddp.01.init.md` for full orchestration logic.
