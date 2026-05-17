#!/usr/bin/env bash
# setup.sh — Copy .claude/* to ~/.claude/, skipping existing files.
#            Also removes old XDDP skill/command files from previous numbering scheme.

set -euo pipefail

SRC="$(cd "$(dirname "$0")/.claude" && pwd)"
DEST="$HOME/.claude"

# --- Step 0: Remove old XDDP files that conflict with current numbering scheme ---
OLD_XDDP_FILES=(
  "skills/xddp-specout-feedback.md"
  "skills/xddp-tm-generate.md"
  "skills/xddp-coding.md"
  "skills/xddp-verify.md"
  "skills/xddp-test-feedback.md"
  "skills/xddp-specout.md"
  "skills/xddp-testcase.md"
  "skills/xddp.01.req.start.md"
  "skills/xddp.02.req.review.md"
  "skills/xddp.03.spec.start.md"
  "skills/xddp.04.spec.review.md"
  "skills/xddp.05.design.start.md"
  "skills/xddp.06.design.review.md"
  "skills/xddp.07.code.start.md"
  "skills/xddp.08.code.review.md"
  "skills/xddp.09.test.spec.md"
  "skills/xddp.10.test.review.md"
  "skills/xddp.11.test.code.md"
  "commands/xddp.01.req.start.md"
  "commands/xddp.02.req.review.md"
  "commands/xddp.03.spec.start.md"
  "commands/xddp.04.spec.review.md"
  "commands/xddp.05.design.start.md"
  "commands/xddp.06.design.review.md"
  "commands/xddp.07.code.start.md"
  "commands/xddp.08.code.review.md"
  "commands/xddp.09.test.spec.md"
  "commands/xddp.10.test.review.md"
  "commands/xddp.11.test.code.md"

  # Old flat skill files (replaced by skills/<name>/SKILL.md format)
  "skills/xddp.01.init.md"
  "skills/xddp.02.analysis.md"
  "skills/xddp.03.req.md"
  "skills/xddp.04.specout.md"
  "skills/xddp.05.arch.md"
  "skills/xddp.06.design.md"
  "skills/xddp.07.code.md"
  "skills/xddp.08.test.md"
  "skills/xddp.09.specs.md"
  "skills/xddp.close.md"
  "skills/xddp.common.md"
  "skills/xddp.excel2md.md"
  "skills/xddp.fill-steering.md"
  "skills/xddp.md2excel.md"
  "skills/xddp.review.md"
  "skills/xddp.revise.md"
  "skills/xddp.status.md"

  # Old templates directory files (dispersed to skills/xddp.templates/, skills/xddp.rules/, skills/xddp.md2excel/scripts/)
  "templates/00_progress-management-template.md"
  "templates/01_req-lite-template.md"
  "templates/01_req-template.md"
  "templates/02_req-analysis-memo-template.md"
  "templates/03_change-req-spec-template.md"
  "templates/04_specout-cross-module-template.md"
  "templates/04_specout-module-template.md"
  "templates/04_specout-template.md"
  "templates/05_design-approach-memo-template.md"
  "templates/06_change-design-document-template.md"
  "templates/07_test-specification-template.md"
  "templates/08_test-results-template.md"
  "templates/09_specification-template.md"
  "templates/10_improvement-backlog-template.md"
  "templates/crs_md2excel.py"
  "templates/interface-spec-template.md"
  "templates/lessons-learned-template.md"
  "templates/project-steering-cross-template.md"
  "templates/project-steering-repo-template.md"
  "templates/project-steering-template.md"
  "templates/review-template.md"
  "templates/xddp.arch.rules.md"
  "templates/xddp.coding.rules.md"
  "templates/xddp.config.md"
  "templates/xddp.design.rules.md"
  "templates/xddp.skill-template.md"
)

cleaned=()
for rel in "${OLD_XDDP_FILES[@]}"; do
  old_file="$DEST/$rel"
  if [[ -e "$old_file" ]]; then
    rm "$old_file"
    cleaned+=("$rel")
  fi
done

if [[ ${#cleaned[@]} -gt 0 ]]; then
  echo "✗ Removed old XDDP files (${#cleaned[@]}):"
  for f in "${cleaned[@]}"; do
    echo "    $f"
  done
  echo ""
fi

# --- Step 0.5: Remove stale XDDP skill directories ---
OLD_XDDP_DIRS=(
  "skills/xddp-coding"
  "skills/xddp-conflict-check"
  "skills/xddp-specout"
  "skills/xddp-specout-feedback"
  "skills/xddp-test-feedback"
  "skills/xddp-testcase"
  "skills/xddp-tm-generate"
  "skills/xddp-verify"
)

cleaned_dirs=()
for rel in "${OLD_XDDP_DIRS[@]}"; do
  old_dir="$DEST/$rel"
  if [[ -d "$old_dir" || -L "$old_dir" ]]; then
    rm -rf "$old_dir"
    cleaned_dirs+=("$rel/")
  fi
done

if [[ ${#cleaned_dirs[@]} -gt 0 ]]; then
  echo "✗ Removed old XDDP directories (${#cleaned_dirs[@]}):"
  for d in "${cleaned_dirs[@]}"; do
    echo "    $d"
  done
  echo ""
fi

# --- Step 0.6: Remove old templates directory if empty ---
OLD_TEMPLATES_DIR="$DEST/templates"
if [[ -d "$OLD_TEMPLATES_DIR" ]]; then
  rm -rf "$OLD_TEMPLATES_DIR/__pycache__"
  rmdir "$OLD_TEMPLATES_DIR" 2>/dev/null && \
    echo "✗ Removed old templates directory: templates/" || \
    echo "! templates/ not empty — kept (may contain user files)"
  echo ""
fi

skipped=()
copied=()
updated=()

while IFS= read -r -d '' src_file; do
  rel="${src_file#"$SRC/"}"
  dest_file="$DEST/$rel"

  if [[ ! -e "$dest_file" ]]; then
    mkdir -p "$(dirname "$dest_file")"
    cp "$src_file" "$dest_file"
    copied+=("$rel")
  elif [[ "$src_file" -nt "$dest_file" ]]; then
    cp "$src_file" "$dest_file"
    updated+=("$rel")
  else
    skipped+=("$rel")
  fi
done < <(find "$SRC" -type f -not -name "CLAUDE.md" -not -path "*/__pycache__/*" -not -name "*.pyc" -print0 | sort -z)

echo "=== XDDP Setup ==="
echo ""

if [[ ${#copied[@]} -gt 0 ]]; then
  echo "✓ Copied (${#copied[@]} files):"
  for f in "${copied[@]}"; do
    echo "    $f"
  done
  echo ""
fi

if [[ ${#updated[@]} -gt 0 ]]; then
  echo "↑ Updated (${#updated[@]} files):"
  for f in "${updated[@]}"; do
    echo "    $f"
  done
  echo ""
fi

if [[ ${#skipped[@]} -gt 0 ]]; then
  echo "! Skipped — up to date (${#skipped[@]} files):"
  for f in "${skipped[@]}"; do
    echo "    $f"
  done
  echo ""
fi

if [[ ${#copied[@]} -eq 0 && ${#updated[@]} -eq 0 && ${#skipped[@]} -eq 0 ]]; then
  echo "No files found in $SRC"
fi
