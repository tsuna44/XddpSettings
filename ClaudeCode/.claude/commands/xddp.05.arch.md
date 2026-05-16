You are executing XDDP Step 05: Implementation Approach Design.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.05.arch** skill:

0. Reference past DSNs from DOCS_DIR: read up to 3 past `{DOCS_DIR}/{REPO_NAME}/design/DSN-*.md`
   related to the CRS and extract approach rationale and rejected alternatives.
   Record files read and key insights in the DSN's "参照した過去設計書" section.
1. Invoke `xddp-architect-agent` to create `{CR}/05_architecture/DSN-{CR}.md`.
   - Consider **3 or more** implementation alternatives with meaningfully different approaches.
   - Auto-select and insert **1–3 Mermaid diagrams** based on the nature of the change (scope diagram, DFD, sequence, class, flowchart, state, ER, etc.).
2. Run AI review loop (up to `REVIEW_MAX_ROUNDS.DSN` rounds from `xddp.config.md`, default 2) using `xddp-reviewer` agent.
3. **Human review gate**: pause for human review of `DSN-{CR}.md`.
   - If changes made: run one final AI review pass.
4. **Feed architecture decision back to CRS**: use `xddp-spec-writer-agent` to reflect constraints, unnecessary requirements, and new requirements revealed by the adopted approach. Regenerate Excel if CRS changed.
5. Update `{CR}/progress.md`: step 6 ✅, next → `/xddp.06.design {CR}`.

See `.claude/skills/xddp.05.arch.md` for full orchestration logic.
