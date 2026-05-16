You are executing XDDP Review: Standalone AI Review of a human-edited artifact (単体AIレビュー).

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional) DOCUMENT_TYPE [REPO_NAME]
- CR_NUMBER: e.g., `CR-2026-001` (optional; auto-detected from XDDP_DIR if omitted)
- DOCUMENT_TYPE: one of `analysis`, `req`, `specout`, `arch`, `design`, `test`, or a file path
- REPO_NAME: optional; which repo's artifact to review (for specout/arch/design/test). If omitted and IS_MULTI, ask the user.

If DOCUMENT_TYPE is omitted, ask the user which document to review.

---

## Instructions

1. Resolve TARGET_FILE, REFERENCE_FILES, and OUTPUT_FILE from DOCUMENT_TYPE using the mapping table in the skill.
   - Per-repo artifacts (specout/arch/design/test): use `{CR_PATH}/{step}/{repo}/` paths.
   - Review output files: stored under `{CR_PATH}/{step}/{repo}/review/`.
   - Single-repo or non-repo-specific artifacts: use flat paths as before.
2. Verify TARGET_FILE exists; stop with an error if not found.
3. Invoke `xddp-reviewer` agent (REVIEW_ROUND: 1) and write result to OUTPUT_FILE.
4. Report 総合判定, issue counts, and result file path in Japanese.
   - If issues remain, suggest `/xddp.revise` for applying fixes or re-running `/xddp.review` after manual edits.

See `.claude/skills/xddp.review.md` for full orchestration logic.
