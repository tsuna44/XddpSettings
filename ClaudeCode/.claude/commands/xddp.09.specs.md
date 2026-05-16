You are executing XDDP Step 09: Generate/Update Latest Specifications.

**Arguments:** $ARGUMENTS = [CR_NUMBER] (optional; auto-detected from XDDP_DIR if omitted)

Delegate to the **xddp.09.specs** skill:

0. Read `REPOS:` from `xddp.config.md`. Identify AFFECTED_REPOS and HAS_CROSS.
A. For each repo in AFFECTED_REPOS: read SPO, CHD, CRS to determine changed modules.
   Update or create spec files in `latest-specs/{repo}/{module}/{name}-spec.md`.
   - If spec exists: apply CHD changes, increment version, add 変更履歴 entry.
   - If new: create from `09_specification-template.md`, synthesise from SPO + CRS + CHD. Version: 1.0.
A-cross (when HAS_CROSS): update or create interface specs in `latest-specs/cross/interfaces/`.
   - SemVer: `breaking: true` → MAJOR+1, new fields → MINOR+1, doc-only → PATCH+1.
A2. Run AI review loops (up to `REVIEW_MAX_ROUNDS.SPEC` rounds) for all repo and cross/interfaces specs.
A3. **Human review gate**: pause for confirmation of all updated spec files.
B. Update `{CR}/progress.md`:
   - Step 15 ✅; record all updated files in "工程15 更新仕様書ファイル一覧" (with `{repo}/` prefix).
   - Next: `/xddp.close {CR}`.

See `.claude/skills/xddp.09.specs.md` for full orchestration logic.
