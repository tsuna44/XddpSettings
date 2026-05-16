You are executing XDDP Step 05: Implementation Approach Design.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.05.arch** skill:

0. Read `REPOS:` from `xddp.config.md`. Identify AFFECTED_REPOS and HAS_CROSS.
   Reference past DSNs from DOCS_DIR: read up to 3 past `{DOCS}/{repo}/design/DSN-*.md`
   per affected repo, and `{DOCS}/cross/design/` if HAS_CROSS.
A-cross (API-first, when HAS_CROSS): generate `{CR_PATH}/05_architecture/cross/DSN-{CR}-cross.md` first.
   Covers inter-repo approach, interface design, implementation dependency order, and cross-repo risks.
A. For each repo in AFFECTED_REPOS: invoke `xddp-architect-agent` to create `{CR_PATH}/05_architecture/{repo}/DSN-{CR}.md`.
   - Read per-repo steering (`project-steering-{repo}.md`) as STEERING_CONTEXT.
   - Pass cross/DSN as ADDITIONAL_REFS so per-repo designs honor interface contracts.
   - Consider ≥3 implementation alternatives with meaningfully different approaches.
   - Auto-select and insert 1–3 Mermaid diagrams.
1. Run per-repo AI review loops (up to `REVIEW_MAX_ROUNDS.DSN` rounds from `xddp.config.md`, default 2).
2. **Human review gate**: pause for human review of per-repo DSN files and cross/DSN.
   - If changes made: run one final AI review pass per repo.
3. Feed architecture decisions back to CRS via `xddp-spec-writer-agent` (MODE=update). Regenerate Excel if CRS changed.
4. Update `{CR}/progress.md`: step 6 ✅, next → `/xddp.06.design {CR}`.

See `.claude/skills/xddp.05.arch.md` for full orchestration logic.
