You are executing XDDP Step 06: Change Design Document + CRS Feedback.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.06.design** skill:

1. Invoke `xddp-designer-agent` to create `{CR}/06_design/CHD-{CR}.md`.
   - Warn user if >500 lines changed (CR split recommended).
2. Run AI review loop (up to 5 rounds) using `xddp-reviewer` agent.
3. **Human review gate**: pause for human review of `CHD-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Feed design findings back to CRS via `xddp-spec-writer-agent` (MODE=update).
5. Regenerate `{CR}/03_change-requirements/CRS-{CR}.xlsx` if CRS was updated (UR-016).
6. Update `{CR}/progress.md`: steps 7 and 8 ✅, next → `/xddp.07.code {CR}`.

See `.claude/skills/xddp.06.design.md` for full orchestration logic.
