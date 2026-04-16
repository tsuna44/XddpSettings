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
done < <(find "$SRC" -type f -print0 | sort -z)

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
