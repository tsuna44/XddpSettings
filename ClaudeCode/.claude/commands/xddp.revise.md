You are executing XDDP Revise: Apply Human Review Comments to a Document (人レビュー指摘の反映).

Delegate to the **xddp.revise** skill:
1. Resolve arguments: [CR_NUMBER] (optional) DOCUMENT_TYPE (analysis/req/specout/arch/design/test or file path) [REPO_NAME] (optional; for arch/design/test in multi-repo)
2. Identify target document path (multi-repo: include {REPO_NAME} in path; ask user if omitted and IS_MULTI)
3. Ask user for review comments and wait for input
4. Apply revisions minimally; preserve structure
5. Record revisions in review file (append or create)
6. Update version history in target document
7. Display summary in Japanese

See `.claude/skills/xddp.revise/SKILL.md` for full orchestration logic.
