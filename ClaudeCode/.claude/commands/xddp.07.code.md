You are executing XDDP Step 07: Coding + Static Verification.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.07.code** skill:

1. Read `xddp.coding.rules.md` → `CODING_RULES`.
   Read `{XDDP_DIR}/project-steering.md` → `STEERING_CONTEXT` (empty if not found).
   Pass both to coder-agent and verifier-agent.
2. Read `xddp.config.md` to extract `MULTI_REPO` and `REPOS_MAP` (multi-repo support).
3. Invoke `xddp-coder-agent` (with `REPOS_MAP`, `STEERING_CONTEXT`) to implement source code changes per CHD.
   - Resolve target files using the `リポジトリ:` field in CHD and `REPOS_MAP`.
4. Invoke `xddp-verifier-agent` to run static verification.
5. If NG: attempt one auto-fix round, then re-verify.
6. Update `{CR}/progress.md`: step 9 (コーディング) ✅, step 10 (静的検証) ✅ (or 🔁), next → `/xddp.08.test {CR}`.
   - If NG is due to a design error, guide the user to roll back to `/xddp.06.design {CR}`.

See `.claude/skills/xddp.07.code.md` for full orchestration logic.
