You are executing XDDP Fill Steering (project-steering ファイル 自動ドラフト生成).

**Arguments:** $ARGUMENTS
- 1st token (optional): target — `shared` / `cross` / `{repo-name}` / `all` (default: `all`)
- Remaining tokens (optional): section numbers to fill (e.g., `2 5`); omit to fill all unwritten sections

---

## Instructions

1. Search upward from cwd to find `xddp.config.md`; extract `XDDP_DIR` and `REPOS:` list.
2. Parse TARGET_REPO from arguments (default: `all`). Validate:
   - `shared` → `{XDDP_DIR}/project-steering.md`
   - `cross` → `{XDDP_DIR}/project-steering-cross.md` (only if REPOS: ≥2 entries)
   - `{repo-name}` → `{XDDP_DIR}/project-steering-{repo-name}.md` (must exist in REPOS:)
   - `all` → all three types above (shared + per-repo for each entry + cross if ≥2 entries)
   Create from the appropriate template if the file does not exist.
3. Detect placeholder strings to identify unwritten sections in each target file.
4. Investigate and generate drafts for each unwritten section:
   - **Shared steering**: §1.5 リポジトリ構成 (REPOS: list + dependencies); §2 naming; §5 prohibitions; §6 architecture
   - **Per-repo steering**: §1 メタデータ (LANGUAGE/FRAMEWORK/TEST_FRAMEWORK from build files); §2 naming by sampling source; §3 ADR candidates; §6 directory structure
   - **Cross steering**: §1 repos table with provider/consumer roles; §2 API versioning rules; §3 interface naming; §4 error codes; §5 auth method
5. Present all drafts in one message and accept diff instructions (repeat until user says OK).
6. Write confirmed drafts to target files in one batch.

See ClaudeCode/.claude/skills/xddp.fill-steering.md for full orchestration logic.
