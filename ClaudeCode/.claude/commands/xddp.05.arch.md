You are executing XDDP Step 05: Implementation Approach Design.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.05.arch** skill:

1. Invoke `xddp-architect-agent` to create `{CR}/05_architecture/DSN-{CR}.md`.
2. Run AI review loop (up to 5 rounds) using `xddp-reviewer` agent.
3. **Human review gate**: pause for human review of `DSN-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Update `{CR}/progress.md`: step 6 ✅, next → `/xddp.06.design {CR}`.

See `.claude/skills/xddp.05.arch.md` for full orchestration logic.
