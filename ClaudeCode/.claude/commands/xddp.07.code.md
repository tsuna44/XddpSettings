You are executing XDDP Step 07: Coding + Static Verification.

**Arguments:** $ARGUMENTS = CR_NUMBER

Delegate to the **xddp.07.code** skill:

1. Read `xddp.config.md` to extract `MULTI_REPO` and `REPOS_MAP` (マルチリポジトリ対応).
2. Invoke `xddp-coder-agent` (with `REPOS_MAP`) to implement source code changes per CHD.
   - CHD の `リポジトリ:` フィールドと `REPOS_MAP` を参照して対象ファイルを解決する。
3. Invoke `xddp-verifier-agent` to run static verification.
4. If NG: attempt one auto-fix round, then re-verify.
5. Update `{CR}/progress.md`: step 9 (コーディング) ✅, step 10 (静的検証) ✅ (or 🔁), next → `/xddp.08.test {CR}`.
   - 設計ミスによる NG の場合は `/xddp.06.design {CR}` へのロールバックを案内する.

See `.claude/skills/xddp.07.code.md` for full orchestration logic.
