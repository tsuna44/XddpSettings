You are executing XDDP Step 06: Change Design Document + CRS Feedback.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.06.design** skill:

0. Read `REPOS:` from `xddp.config.md`. Identify AFFECTED_REPOS and HAS_CROSS.
   Reference past CHDs from DOCS_DIR: read up to 3 past `{DOCS}/{repo}/design/CHD-*.md` per affected repo,
   and past cross CHDs from `{DOCS}/cross/design/` if HAS_CROSS.
A-cross (API-first, when HAS_CROSS): generate `{CR_PATH}/06_design/cross/CHD-{CR}-cross.md` first.
   Must include "実装依存関係" table (provider → consumer) and "インタフェース変更サマリ" table.
A. For each repo in AFFECTED_REPOS: invoke `xddp-designer-agent` to create `{CR_PATH}/06_design/{repo}/CHD-{CR}.md`.
   - Read per-repo steering (`project-steering-{repo}.md`) as STEERING_CONTEXT.
   - Pass cross/CHD as ADDITIONAL_REFS so per-repo designs conform to the interface contract.
   - Detailed design in Chapter 3 is written at SP granularity.
   - Auto-select and insert Mermaid diagrams (class, sequence, state, ER, etc.).
   - Create traceability matrix (SP × file × function) in Chapter 4.
   - Warn if >500 lines changed (CR split recommended).
1. Run per-repo AI review loops (up to `REVIEW_MAX_ROUNDS.CHD` rounds from `xddp.config.md`, default 2).
2. **Human review gate**: pause for human review of per-repo CHD files and cross/CHD.
   - If changes made: run one final AI review pass per repo.
3. Feed design findings back to CRS via `xddp-spec-writer-agent` (MODE=update). Regenerate Excel if CRS changed.
4. Update `{CR}/progress.md`: steps 7 and 8 ✅, next → `/xddp.07.code {CR}`.

See `.claude/skills/xddp.06.design.md` for full orchestration logic.
