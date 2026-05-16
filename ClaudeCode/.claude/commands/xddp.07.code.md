You are executing XDDP Step 07: Coding + Static Verification.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.07.code** skill:

0. Read `REPOS:` from `xddp.config.md`. Identify AFFECTED_REPOS and HAS_CROSS.
   Load `xddp.coding.rules.md` → `CODING_RULES`.
   If HAS_CROSS: read "実装依存関係" table from cross/CHD to determine IMPL_ORDER via topological sort.
   - If a circular dependency is detected: alert user ("⛔ 循環依存が検出されました") and stop.
   If not HAS_CROSS: IMPL_ORDER = AFFECTED_REPOS in REPOS: definition order.
0.5. Create per-repo progress table in `progress.md` for step 9 (when IS_MULTI).
A. For each repo in IMPL_ORDER (sequentially): invoke `xddp-coder-agent` with:
   - `REPO_NAME`, `REPO_PATH`, per-repo `CHD_FILE`, `OUTPUT_MEMO=CODING-{CR}-{repo}.md`
   - `CODING_RULES`, `STEERING_CONTEXT` (shared + per-repo), cross/CHD as `ADDITIONAL_REFS`
B. For each repo: invoke `xddp-verifier-agent` with per-repo `VERIFY-{CR}-{repo}.md` output.
   - Pass `CODING_RULES`, `STEERING_CONTEXT`, cross/CHD as `ADDITIONAL_REFS`.
B-cross (when HAS_CROSS): invoke `xddp-verifier-agent` with `REPO_NAME: cross` to verify all
   cross/CHD interface commitments across all per-repo coding memos (`CODING_MEMOS`).
C. If all ✅: update progress.md steps 9-10 ✅, next → `/xddp.08.test {CR}`.
   If ❌ implementation bug: auto-fix and re-verify once.
   If ❌ design error: guide user to `/xddp.06.design {CR}` (do not fix code).

See `.claude/skills/xddp.07.code.md` for full orchestration logic.
