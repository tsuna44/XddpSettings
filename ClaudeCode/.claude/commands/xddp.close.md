You are executing XDDP Close: CR Closeout & Knowledge Capture.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.close** skill:

0.5. Pre-close sync (Step C0):
     (1) Check for un-fetched source code commits → prompt git pull if found
     (2) git pull for {DOCS_DIR}/
     (3) Pull other CRs' approved specs from docs/{repo}/specs/ into latest-specs/
         (files modified by this CR are protected from overwrite)
     (4) If source changes found, recommend re-running /xddp.09.specs {CR}
1. Precondition check: verify step 15 (最新仕様書作成) is complete.
2. Collect "気づき・提案メモ" entries from all phase documents.
3. Append non-current-CR entries to `improvement-backlog.md`.
4. Analyze lessons learned across the CR and append LL entries to `lessons-learned.md`.
   - Extraction perspectives: requirements analysis gaps, approach design decisions, test-discovered issues, process improvements
5. Promote approved specs (Step C2): copy `latest-specs/` → `{DOCS_DIR}/{REPO_NAME}/specs/` and update the repo row in `{DOCS_DIR}/AI_INDEX.md`.
5.5. Promote lessons learned (Step C3): append this CR's LL entries to `{DOCS_DIR}/{REPO_NAME}/knowledge/lessons-learned.md`.
5.6. Apply lessons to project-steering.md (Step C3.5): append this CR's LL entries to the relevant sections based on tags. `#方式検討`/`#設計` → Section 3/4, `#コーディング` → Section 4, `#テスト` → Section 4, prohibitions → Section 5. `#プロセス` etc. are excluded. Dedup check applies. Skip if `project-steering.md` not found.
6. Promote design documents (Step C4): copy DSN and CHD to `{DOCS_DIR}/{REPO_NAME}/design/` and update AI_INDEX.md design table.
6.5. Promote test specs (Step C5): copy TSP to `{DOCS_DIR}/{REPO_NAME}/test/` and update the test spec column in AI_INDEX.md.
7. Promote project-steering (Step C6): copy `{XDDP_DIR}/project-steering.md` to
   `{DOCS_DIR}/{REPO_NAME}/project-steering.md` and update the "共通知識" table in AI_INDEX.md.
   Skip if file does not exist.
8. **Human review gate**: wait for user confirmation (backlog, lessons, promoted specs).
8. Record close information in `{CR}/progress.md`.

See `ClaudeCode/.claude/skills/xddp.close.md` for full orchestration logic.
