You are executing XDDP Step 02: Requirements Analysis.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.02.analysis** skill:

1. Invoke `xddp-analyst-agent` to create `{CR}/02_analysis/ANA-{CR}.md`.
2. Run AI review loop (up to 5 rounds) using `xddp-reviewer` agent.
   - Each round: review → fix with `xddp-analyst-agent` if 🔴/🟡 found.
3. **Human review gate**: pause for human review of `ANA-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Update `{CR}/progress.md`: step 2 ✅, next → `/xddp.03.req {CR}`.

See `.claude/skills/xddp.02.analysis.md` for full orchestration logic.
