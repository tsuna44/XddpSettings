You are executing XDDP Step 02: Requirements Analysis.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.02.analysis** skill:

0. Import knowledge from DOCS_DIR: read `{DOCS_DIR}/shared/glossary.md`, `lessons-learned.md`,
   and `{REPO_NAME}/specs/` for term consistency, similar CR references, and spec conflict checks.
   Record files used and relevant findings in the ANA's "参照した既存ドキュメント" section.
1. Invoke `xddp-analyst-agent` to create `{CR}/02_analysis/ANA-{CR}.md`.
   - In section "2. 要求レベル分類", classify each UR as UR / SR / SP and generate CRS expressions and rationale.
2. Run AI review loop (up to `REVIEW_MAX_ROUNDS.ANA` rounds from `xddp.config.md`, default 2) using `xddp-reviewer` agent.
   - Each round: review → fix with `xddp-analyst-agent` if 🔴/🟡 found.
3. **Human review gate**: pause for human review of `ANA-{CR}.md`.
   - If changes made: run one final AI review pass.
3.5. **Extract project-steering candidates** (Step B3):
     - Idempotency check: skip if {CR} entry already exists in 変更履歴.
     - Extract naming conventions, ADRs, prohibitions, and cross-cutting patterns from req (cross-cutting only).
     - Present candidates with category labels; append to the relevant heading after user approval.
     - Skip if `project-steering.md` not found. Skip silently if 0 candidates.
4. Update `{CR}/progress.md`: step 2 ✅, next → `/xddp.03.req {CR}`.

See `.claude/skills/xddp.02.analysis.md` for full orchestration logic.
