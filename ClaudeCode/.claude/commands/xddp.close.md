You are executing XDDP Close: CR Closeout & Knowledge Capture.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.close** skill:

0. Precondition check: verify step 15 (最新仕様書作成) is ✅ complete.
C-Pre. All-repos git status check:
   - For each repo in REPOS_KEYS: run `git status --short`; warn if uncommitted changes exist.
   - Ask user to continue or abort before proceeding.
C0. Pre-close sync (parallel-CR support):
   (1) `git fetch origin` + check for un-merged remote commits → prompt `git pull` if found.
   (2) git pull `{DOCS_DIR}/`.
   (3) Pull baseline → `latest-specs/` (protected files identified from "工程15 更新仕様書ファイル一覧").
   (4) If source changes found, offer to re-run `/xddp.09.specs {CR}`.
A. Collect "気づき・提案メモ" entries from all per-repo and cross/ phase documents.
B. Append non-current-CR entries to `improvement-backlog.md`.
   - Tag each IDEA with `repo:` field (auto-detect: repo-specific→{repo-name}, inter-repo→cross, unclear→unknown).
   - Flag `repo: unknown` entries in closeout report.
C. Analyse lessons learned; append LL entries to `lessons-learned.md`.
   - Tag each LL with `repo:` field (same logic as IDEA).
   - `repo: unknown` entries are NOT promoted; listed as "要確認 LL".
C2. Promote per-repo + cross/ specs: copy `latest-specs/{repo}/` → `{DOCS}/{repo}/specs/`, `latest-specs/cross/interfaces/` → `{DOCS}/cross/specs/`.
   - Upsert AI_INDEX.md per-repo rows.
   - If breaking interface change (cross/CHD `breaking: true`): add ⚠️ annotation + LL warning to ALL affected repos.
C3. Promote LL by `repo:` field:
   - `repo: {repo-name}` → `{DOCS}/{repo}/knowledge/lessons-learned.md`
   - `repo: cross` → `{DOCS}/cross/knowledge/lessons-learned.md`
   - `repo: unknown` → skip (listed in report)
C3.5. Apply LL to per-repo/cross steering files based on tags and `repo:` field.
   `#方式検討`/`#設計` → Section 3/4, `#コーディング` → Section 4, `#テスト` → Section 4, prohibitions → Section 5.
   Dedup check applies. `repo: unknown` skipped.
C4. Promote design documents (DSN, CHD) to `{DOCS}/{repo}/design/` and `{DOCS}/cross/design/` (if HAS_CROSS).
C5. Promote test specs (TSP, TRS) to `{DOCS}/{repo}/test/` and `{DOCS}/cross/test/` (if HAS_CROSS).
C6. Promote steering files: shared `project-steering.md` → `{DOCS}/project-steering.md`;
   per-repo `project-steering-{repo}.md` → `{DOCS}/{repo}/project-steering.md`;
   cross `project-steering-cross.md` → `{DOCS}/cross/project-steering.md` (if HAS_CROSS).
   Update AI_INDEX.md "共通知識" table per repo + cross.
D. **Human review gate**: confirm backlog, lessons, promoted specs, "要確認 LL/IDEA" lists.
E. Record close info in `{CR}/progress.md` (closeout date, IDEA/LL counts, status ✅ 完了).

See `ClaudeCode/.claude/skills/xddp.close.md` for full orchestration logic.
