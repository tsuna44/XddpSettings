You are executing XDDP Step 06: Change Design Document + CRS Feedback.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.06.design** skill:

0. Reference past CHDs from DOCS_DIR: read up to 3 past `{DOCS_DIR}/{REPO_NAME}/design/CHD-*.md`
   related to the DSN and extract change patterns for the same components.
   Record files read and key patterns in the CHD's "参照した過去設計書" section.
1. Invoke `xddp-designer-agent` to create `{CR}/06_design/CHD-{CR}.md`.
   - Detailed design in Chapter 3 is written at **SP (spec item) granularity** (not file granularity).
   - Auto-select and insert Mermaid diagrams based on change content (class, function call, sequence, flowchart, state, ER).
   - Create a traceability matrix (SP × file × function) in Chapter 4.
   - Warn user if >500 lines changed (CR split recommended).
2. Run AI review loop (up to `REVIEW_MAX_ROUNDS.CHD` rounds from `xddp.config.md`, default 2) using `xddp-reviewer` agent.
3. **Human review gate**: pause for human review of `CHD-{CR}.md`.
   - If changes made: run one final AI review pass.
4. Feed design findings back to CRS via `xddp-spec-writer-agent` (MODE=update).
5. Regenerate `{CR}/03_change-requirements/CRS-{CR}.xlsx` if CRS was updated (UR-016).
6. Update `{CR}/progress.md`: steps 7 and 8 ✅, next → `/xddp.07.code {CR}`.

See `.claude/skills/xddp.06.design.md` for full orchestration logic.
