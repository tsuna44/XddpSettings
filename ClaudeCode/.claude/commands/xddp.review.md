You are executing XDDP Review: Standalone AI Review of a human-edited artifact (単体AIレビュー).

**Arguments:** $ARGUMENTS = CR_NUMBER DOCUMENT_TYPE
- CR_NUMBER: e.g., `REQ-2026-001`
- DOCUMENT_TYPE: one of `analysis`, `req`, `specout`, `arch`, `design`, `test`, or a file path

If DOCUMENT_TYPE is omitted, ask the user which document to review.

---

## Instructions

1. Resolve TARGET_FILE, REFERENCE_FILES, and OUTPUT_FILE from DOCUMENT_TYPE using the mapping table in the skill.
2. Verify TARGET_FILE exists; stop with an error if not found.
3. Invoke `xddp-reviewer` agent (REVIEW_ROUND: 1) and write result to OUTPUT_FILE.
4. Report 総合判定, issue counts, and result file path in Japanese.
   - If issues remain, suggest `/xddp.revise` for applying fixes or re-running `/xddp.review` after manual edits.

See `.claude/skills/xddp.review.md` for full orchestration logic.
