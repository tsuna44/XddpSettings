You are executing XDDP Fill Steering (project-steering.md 自動ドラフト生成).

**Arguments:** $ARGUMENTS
- No arguments: target all unwritten sections
- Section number: target only those sections (multiple allowed, e.g., `1.5` / `2 6`)

---

## Instructions

1. Search upward from cwd to find `xddp.config.md`; extract `XDDP_DIR` / `MULTI_REPO` / `REPOS` / `REPO_NAME`.
2. Check `{XDDP_DIR}/project-steering.md` (copy from template if absent and continue).
3. Detect placeholder strings to identify unwritten sections.
4. Investigate the codebase and generate a draft for each unwritten section:
   - §1: `xddp.config.md` + dependency files (requirements.txt / package.json / go.mod, etc.)
   - §1.5: investigate each repo in REPOS in parallel (MULTI_REPO: true only)
   - §2: infer naming conventions by sampling source files
   - §6: directory structure + entry point files based on LANGUAGE
   - §3 and §5: insert a note for manual entry
   - §4: insert a note that this section is filled in during specout (step 4)
5. Present all drafts in one message and accept diff instructions (repeat until user says OK).
6. Write confirmed drafts to `project-steering.md` in one batch.

See ClaudeCode/.claude/skills/xddp.fill-steering.md for full orchestration logic.
