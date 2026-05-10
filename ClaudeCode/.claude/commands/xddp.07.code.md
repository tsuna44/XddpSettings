You are executing XDDP Step 07: Coding + Static Verification.

**Arguments:** $ARGUMENTS = [CR_NUMBER]（省略可。省略時は XDDP_DIR 配下から自動検出）

Delegate to the **xddp.07.code** skill:

1. Read `xddp.coding.rules.md` → `CODING_RULES`。
   Read `{XDDP_DIR}/project-steering.md` → `STEERING_CONTEXT`（存在しない場合は空）。
   両方を coder-agent・verifier-agent に渡す。
2. Read `xddp.config.md` to extract `MULTI_REPO` and `REPOS_MAP` (マルチリポジトリ対応).
3. Invoke `xddp-coder-agent` (with `REPOS_MAP`, `STEERING_CONTEXT`) to implement source code changes per CHD.
   - CHD の `リポジトリ:` フィールドと `REPOS_MAP` を参照して対象ファイルを解決する。
4. Invoke `xddp-verifier-agent` to run static verification.
5. If NG: attempt one auto-fix round, then re-verify.
6. Update `{CR}/progress.md`: step 9 (コーディング) ✅, step 10 (静的検証) ✅ (or 🔁), next → `/xddp.08.test {CR}`.
   - 設計ミスによる NG の場合は `/xddp.06.design {CR}` へのロールバックを案内する.

See `.claude/skills/xddp.07.code.md` for full orchestration logic.
